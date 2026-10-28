"""Parent replay and publication of terminal profile epochs, retaining failures."""
import argparse,gzip,hashlib,json,os,re,subprocess,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import daily_artifacts as native
import daily_acceptance as validator
from profile_memory import summarize_memory,summarize_vm_memory
from setup_env import gateway_key

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    epoch='vm-residency-v1'
    folder=ROOT/'evidence/vm-residency-v1'
    state=json.loads((folder/'state.json').read_text())
    assert state['status']=='terminal'
    samples=[json.loads(x)for x in (folder/'gpu-samples.jsonl').read_text().splitlines()]
    for name,digest in state['source_hashes'].items():assert sha((folder/'producer'/name).read_bytes())==digest
    for name in ('observe-vm-residency-v1.py','watch-vm-residency-v1.py'):
        (folder/'producer'/name).write_bytes((ROOT/'tmp/stress'/name).read_bytes())
    (folder/'producer/profile_memory.py').write_bytes((ROOT/'scripts/profile_memory.py').read_bytes())
    analysis=folder/'analysis-source';analysis.mkdir(exist_ok=True)
    for source in (Path(__file__),ROOT/'scripts/profile_memory.py',ROOT/'scripts/claude_acceptance.py',ROOT/'scripts/daily_acceptance.py'):
        (analysis/source.name).write_bytes(source.read_bytes())
    if epoch=='v2':
        reference=folder/'reference-git-source';reference.mkdir(exist_ok=True)
        for name in ('benchmark.py','context_acceptance.py','claude_acceptance.py'):
            (reference/(name+'.lf')).write_bytes(subprocess.check_output(['git','show',state['source_commit']+':scripts/'+name]))
    cases=[]
    for case in state['cases']:
        identifier=str(case.get('case_id',case.get('cpu_weight_blocks',case['ubatch_size'])))
        memory=summarize_memory(samples,identifier,state['limit_bytes'])
        assert memory['conservative_host_delta_mib']==case['conservative_host_delta_mib']
        capacity_path=folder/(identifier+'-capacity.json')
        capacity=json.loads(capacity_path.read_text())if capacity_path.exists()else None
        if capacity:
            assert capacity['passed']and capacity['input_token_ids']==65536 and capacity['tokens_predicted']==4096 and capacity['truncated']is False
            assert capacity['timings']['draft_n']>0 and capacity['timings']['draft_n_accepted']>0
        benchmark_label='vm-bound-v1-'+identifier
        benchmark_path=ROOT/'evidence'/('benchmark-'+benchmark_label+'.json')
        if benchmark_path.exists():
            (folder/(identifier+'-benchmark.json')).write_bytes(benchmark_path.read_bytes())
        tasks=[]
        source_directory=ROOT/('tmp/vm-residency-v1-'+identifier+'-claude')
        if any(name in case.get('checks',{})for name in ('claude','claude-feedback')):
            assert source_directory.exists(),'Original native replay directory unavailable; no new replay claimed'
        if source_directory.exists():
            summary_path=source_directory/('run-summary.json'if epoch in ('v4','v5','vm-residency-v1')else'claude-acceptance.json')
            raw=json.loads(summary_path.read_text())
            records=raw['tasks']if epoch in ('v4','v5','vm-residency-v1')else raw
            assert {t['task']for t in records}==set(validator.TASK_NAMES)
            for task in records:
                name=task['task']
                artifact=source_directory/name/validator.ARTIFACT_NAMES[name]if epoch in ('v4','v5','vm-residency-v1')else source_directory/validator.ARTIFACT_NAMES[name]
                text=artifact.read_text(encoding='utf-8')
                if epoch not in ('v4','v5','vm-residency-v1'):
                    events=native.parse_events(source_directory/(name+'.jsonl'))
                    reconstructed=native.reconstruct_revisions(events,artifact,validator.BASELINE_CONTENT)[-1]
                    assert reconstructed.rstrip('\r\n')==text.rstrip('\r\n')
                    result=native.final_result(events)
                    assert not result.get('is_error')
                    session=result['session_id']
                else:
                    previous=validator.BASELINE_CONTENT;session=None
                    for phase in task['phases']:
                        events=native.parse_events(source_directory/name/('phase-'+str(phase['phase']))/'stdout.jsonl')
                        result=native.final_result(events)
                        if session:assert result['session_id']==session
                        session=result['session_id']
                        previous=native.reconstruct_revisions(events,artifact,previous)[-1]
                        revision=(source_directory/phase['revision_file']).read_text(encoding='utf-8')
                        assert previous.rstrip('\r\n')==revision.rstrip('\r\n')
                        assert sha(revision.encode())==phase['artifact_sha256']
                    assert previous.rstrip('\r\n')==text.rstrip('\r\n')
                tasks.append({'task':name,'recorded_passed':task['passed'],'session_id':session,
                    'raw_sha256':sha(artifact.read_bytes()),'normalized_text_sha256':sha(text.encode()),
                    'native_edit_reconstruction':True,'parent_current_validation_errors':validator.validate_task_artifact(name,text,validator.load_sources())})
            for source in sorted(source_directory.rglob('*')):
                if not source.is_file():continue
                relative=source.relative_to(source_directory)
                target=folder/'native-artifacts'/identifier/relative.with_name(relative.name+'.gz')
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(gzip.compress(source.read_bytes(),mtime=0))
        logs='\n'.join(p.read_text(encoding='utf-8',errors='replace')for p in (folder/(identifier+'-inference.stdout.log'),folder/(identifier+'-inference.stderr.log'))if p.exists())
        allocations=[line for line in logs.splitlines()if re.search(r'CUDA0.*(?:model|KV|RS|compute) buffer size',line)]
        (folder/(identifier+'-allocation-lines.json')).write_text(json.dumps(allocations,indent=2),encoding='utf-8')
        cases.append({'case_id':identifier,'settings':case,'memory':memory,'capacity':capacity,
            'benchmark_source':benchmark_path.relative_to(ROOT).as_posix() if benchmark_path.exists() else None,
            'benchmark_is_prior_reference':epoch=='v4',
            'tasks':tasks,'passed_task_count':sum(t['recorded_passed']for t in tasks),
            'all_native_tasks_passed':len(tasks)==3 and all(t['recorded_passed']for t in tasks),
            'all_artifacts_pass_current_parent_checks':len(tasks)==3 and all(not t['parent_current_validation_errors']for t in tasks),
            'allocation_log_note':'Raw lines include repeated reservations. Do not sum all lines or interpret them as isolated peak residency.'})
    vm_rows=[json.loads(line)for line in (folder/'vm-counters.jsonl').read_text().splitlines()if line.strip()]
    vm=summarize_vm_memory(vm_rows,32)
    assert vm==state['vm_counter_result']
    selected=[r for r in vm_rows if r.get('stage')=='loading-32'or r.get('stage','').startswith(('loading-32-','tests-32'))]
    vm['peak_all_vm_committed_bytes']=max(sum(c['committed_bytes']for c in r['counters'])for r in selected)
    vm['committed_under_limit']=vm['peak_all_vm_committed_bytes']<14_000_000_000
    for case in cases:case['direct_vm_upper_bound']=vm
    secrets=[gateway_key()]+[v for k,v in os.environ.items()if k.endswith(('_KEY','_TOKEN'))and len(v)>12]
    manifest=[]
    for path in sorted(folder.rglob('*')):
        if not path.is_file()or path.name=='parent-review.json':continue
        raw=path.read_bytes()
        decoded=gzip.decompress(raw)if path.suffix=='.gz'else raw
        assert all(secret.encode()not in decoded for secret in secrets),str(path)
        manifest.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(raw)})
    report={'epoch':epoch,'cases':cases,'qualification_increment':0,'full_goal':'NOT_READY',
        'parent_validation_note':'Current parent checks include the later DedicatedMemory guard; original native acceptance outcomes remain unchanged.',
        'restoration_reported':state.get('restored',False),
        'restoration_followup':'parent-restoration-check.json'if epoch=='v3'else None,
        'measurement_plan':'evidence/vm-residency-v1-plan.json','source_limit':'Producer snapshots and the sealed plan identify the measurement sources. VM usage is a containing-process upper bound, not an exact isolated-container or continuous-time residency measurement.',
        'artifacts':manifest}
    (folder/'parent-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'epoch':epoch,'files':len(manifest),'cases':[{k:v for k,v in c.items()if k in('case_id','passed_task_count','all_native_tasks_passed')}for c in cases]}))

if __name__=='__main__':main()
