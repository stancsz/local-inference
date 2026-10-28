"""Parent replay/publication of every sealed workhorse outcome; never reruns inference."""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from workhorse.cases_v1 import CASES,check
from workhorse.run_v1 import normalized,path_at
from daily_artifacts import parse_events,successful_tool_ids,final_result

def sha(raw):return hashlib.sha256(raw).hexdigest()

def replay(output):
 output=output.resolve();state=json.loads((output/'state.json').read_text())
 assert state['status']=='terminal'and len(state['cases'])==13
 sealed=json.loads((ROOT/'evidence/workhorse-v2-plan.json').read_text())
 assert [c['id']for c in state['cases']]==sealed['case_ids']
 assert state['plan']['sealed_plan_sha256']==sha((ROOT/'evidence/workhorse-v2-plan.json').read_bytes())
 assert state['plan']['source_sha256']==sealed['source_sha256']
 for name,digest in sealed['source_sha256'].items():assert sha((ROOT/name).read_bytes())==digest,name
 rows=[]
 for case,record in zip(CASES,state['cases']):
  folder=output/case['id'];workspace=folder/'workspace';artifact=workspace/case['artifact']
  for name,text in case['files'].items():
   if name!=case['artifact']:assert (workspace/name).read_bytes()==text.encode('utf-8'),name
  previous=normalized(case['files'][case['artifact']]);session=None
  phases=[]
  for index,phase in enumerate(record['phases']):
   phase_dir=folder/f'phase-{index}';snapshot=phase_dir/artifact.name
   assert sha(snapshot.read_bytes())==phase['artifact_sha256']
   events=parse_events(phase_dir/'stdout.jsonl');successful=successful_tool_ids(events)
   edits=0;read_paths=set()
   for event in events:
    if event.get('type')!='assistant':continue
    for block in event.get('message',{}).get('content',[]):
     if not isinstance(block,dict)or block.get('type')!='tool_use'or block.get('id')not in successful:continue
     if block.get('name')=='Read':read_paths.add(path_at(workspace,block['input']['file_path']))
     if block.get('name')!='Edit':continue
     values=block['input'];target=path_at(workspace,values['file_path']);assert target==artifact
     old=normalized(values['old_string']);new=normalized(values['new_string']);assert old and old in previous
     previous=previous.replace(old,new,-1 if values.get('replace_all')else 1);edits+=1
   terminal=final_result(events)
   required={workspace/name for name in case['files']}if index==0 else set()
   assert sorted(str(p.relative_to(workspace))for p in required-read_paths)==phase['native']['missing_reads']
   if session:assert terminal['session_id']==session
   session=terminal.get('session_id');assert session==phase['native']['session_id']
   if edits:assert previous==normalized(snapshot.read_text(encoding='utf-8'))
   else:assert not phase['native']['edit_reconstruction_matches']
   with tempfile.TemporaryDirectory(prefix='workhorse-parent-',dir=ROOT/'tmp')as temporary:
    work=Path(temporary)
    for name,text in case['files'].items():
     path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(text.encode())
    (work/case['artifact']).write_bytes(snapshot.read_bytes())
    replayed=check(case['id'],work)
   assert [(r['name'],r['passed'])for r in replayed]==[(r['name'],r['passed'])for r in phase['checks']]
   native=phase['native'];criteria={'clean_native_terminal':phase['exit_code']==0 and not phase['timed_out']and bool(terminal)and not terminal.get('is_error'),
    'actual_edit':edits>0 and previous==normalized(snapshot.read_text(encoding='utf-8')),
    'source_reads':not native['missing_reads'],'declared_commands_and_paths':not native['scope_violations'],'sources_unchanged':phase['immutable_sources_unchanged'],
    'hidden_behavior':all(r['passed']for r in replayed)}
   assert all(criteria.values())==phase['accepted']
   phases.append({'phase':index,'seconds':phase['seconds'],'artifact_checks_pass':criteria['hidden_behavior'],'strict_workflow_pass':phase['accepted'],
    'criteria':criteria,'checks':replayed,'native_tools':native['successful_tools'],'tool_errors':native['tool_errors'],
    'missing_reads':native['missing_reads'],'scope_violations':native['scope_violations'],'artifact_sha256':phase['artifact_sha256'],
    'usage':native['usage'],'reported_model_usage':native['model_usage'],'session_id':session})
  assert artifact.read_bytes()==(folder/f'phase-{len(phases)-1}'/artifact.name).read_bytes()
  rows.append({'id':case['id'],'category':case['category'],'difficulty':case['difficulty'],'artifact':case['artifact'],
    'phases':phases,'first_artifact_pass':phases[0]['artifact_checks_pass'],'final_artifact_pass':phases[-1]['artifact_checks_pass'],
    'first_strict_pass':phases[0]['strict_workflow_pass'],'final_strict_pass':phases[-1]['strict_workflow_pass'],
    'total_active_seconds':sum(p['seconds']for p in phases),'repairs':len(phases)-1})
 assert state['first_pass_count']==sum(r['first_strict_pass']for r in rows)
 assert state['final_pass_count']==sum(r['final_strict_pass']for r in rows)
 totals={'cases':13,'first_artifact_pass':sum(r['first_artifact_pass']for r in rows),'final_artifact_pass':sum(r['final_artifact_pass']for r in rows),
  'first_strict_pass':sum(r['first_strict_pass']for r in rows),'final_strict_pass':sum(r['final_strict_pass']for r in rows),
  'repair_phases':sum(r['repairs']for r in rows),'active_seconds':sum(r['total_active_seconds']for r in rows)}
 return {'recorded_at':datetime.now(timezone.utc).isoformat(),'execution_commit':state['plan']['execution_commit'],'sealed_plan':'evidence/workhorse-v2-plan.json','status':'parent replay complete','totals':totals,'cases':rows,
  'limits':['Small hand-authored task set, mostly short inputs. Not a population reliability estimate or repo-scale engineering benchmark.',
   'JSON tasks test typed facts/explicit decisions, not open-ended prose quality or unconstrained architectural judgement.',
   'No cloud matched baseline. Cloud escalation guidance is conditional workflow/risk advice, not measured model superiority.',
   'CLI reported cost/model pricing/context labels are not actual local electricity cost, cloud savings or the native model window. Native context was40960.',
   'Strict command/read contract is reported separately from actual artifact correctness; rejected workflow receipts are never promoted.',
   'Generated Python probes are bounded processes, not an OS security sandbox. Normal caller settings and production source remain unchanged.']}

def publish(output,report):
 destination=ROOT/'evidence/workhorse-v2';destination.mkdir(exist_ok=False)
 secrets=[v.encode()for k,v in os.environ.items()if len(v)>12 and any(word in k.upper()for word in ('KEY','TOKEN','SECRET','PASSWORD'))]
 for line in (ROOT/'.env').read_text().splitlines():
  if line.startswith('LOCAL_GATEWAY_KEY='):secrets.append(line.split('=',1)[1].strip().encode())
 artifacts=[]
 for path in sorted(output.rglob('*')):
  if not path.is_file()or 'client'in path.parts or '__pycache__'in path.parts:continue
  raw=path.read_bytes();assert not any(secret and secret in raw for secret in secrets),path
  target=destination/(path.relative_to(output).as_posix()+'.gz');target.parent.mkdir(parents=True,exist_ok=True)
  compressed=gzip.compress(raw,mtime=0);target.write_bytes(compressed)
  artifacts.append({'path':target.relative_to(ROOT).as_posix(),'raw_sha256':sha(raw),'compressed_sha256':sha(compressed)})
 for name in ('workhorse/cases_v1.py','workhorse/run_v2.py','workhorse/review_v2.py','tests/test_workhorse_cases_v1.py','tests/test_workhorse_runner_v1.py','tests/test_workhorse_config_v2.py','tmp/stress/workhorse-full-suite-v2.log'):
  raw=(ROOT/name).read_bytes();target=destination/'producer-source'/(name.replace('/','__')+'.gz');target.parent.mkdir(parents=True,exist_ok=True)
  compressed=gzip.compress(raw,mtime=0);target.write_bytes(compressed);artifacts.append({'path':target.relative_to(ROOT).as_posix(),'raw_sha256':sha(raw),'compressed_sha256':sha(compressed)})
 report['artifacts']=artifacts;report['nonauthor_acceptance']='pending';report['qualification_increment']=0
 with (ROOT/'evidence/workhorse-v2-parent-review.json').open('x',encoding='utf-8')as target:json.dump(report,target,indent=2,ensure_ascii=False)
 return len(artifacts)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--publish',action='store_true');args=p.parse_args()
 report=replay(args.output)
 if args.publish:print({'published_artifacts':publish(args.output,report)})
 print(json.dumps(report['totals']))
