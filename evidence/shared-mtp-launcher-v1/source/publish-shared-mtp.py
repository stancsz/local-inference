"""Publish all outcomes for the shared-weight default, including rejected artifacts."""
import gzip,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import daily_artifacts as native
import daily_acceptance as validator
from setup_env import gateway_key
out=ROOT/'evidence/shared-mtp-launcher-v1'
legacy=ROOT/'tmp/shared-mtp-default-v1-claude'
records=json.loads((legacy/'claude-acceptance.json').read_text())
assert len(records)==3
replay=[]
for record in records:
 name=record['task'];artifact=legacy/validator.ARTIFACT_NAMES[name]
 events=native.parse_events(legacy/(name+'.jsonl'))
 result=native.final_result(events)
 text=artifact.read_text(encoding='utf-8')
 reconstructed=native.reconstruct_revisions(events,artifact,validator.BASELINE_CONTENT)[-1]
 assert reconstructed.rstrip('\r\n')==text.rstrip('\r\n')
 replay.append({'task':name,'recorded_passed':record['passed'],'session_id':result['session_id'],'native_edit_reconstruction':True,'parent_validation_errors':validator.validate_task_artifact(name,text,validator.load_sources())})
feedback=ROOT/'tmp/shared-mtp-default-v1-feedback'
summary=json.loads((feedback/'run-summary.json').read_text())
assert not summary['sources_changed_during_run']
for task in summary['tasks']:
 previous=validator.BASELINE_CONTENT;session=None
 for phase in task['phases']:
  events=native.parse_events(feedback/task['task']/('phase-'+str(phase['phase']))/'stdout.jsonl')
  result=native.final_result(events)
  if session:assert result['session_id']==session
  session=result['session_id']
  previous=native.reconstruct_revisions(events,feedback/task['artifact'],previous)[-1]
  revision=(feedback/phase['revision_file']).read_text(encoding='utf-8')
  assert previous.rstrip('\r\n')==revision.rstrip('\r\n')
  assert hashlib.sha256(revision.encode()).hexdigest()==phase['artifact_sha256']
 assert not validator.validate_task_artifact(task['task'],previous,validator.load_sources())
for source,prefix in ((legacy,'native-one-shot'),(feedback,'native-bounded-feedback')):
 for path in sorted(source.rglob('*')):
  if not path.is_file():continue
  relative=path.relative_to(source)
  target=out/prefix/relative.with_name(relative.name+'.gz');target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(gzip.compress(path.read_bytes(),mtime=0))
for name in ('docker/start-inference.sh','compose.yaml','compose.long.yaml','scripts/claude_local.py','tests/test_inference_launcher.py'):
 target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
(out/'source/publish-shared-mtp.py').write_bytes(Path(__file__).read_bytes())
secrets=[gateway_key()]+[v for k,v in os.environ.items()if k.endswith(('_KEY','_TOKEN'))and len(v)>12]
artifacts=[]
for path in sorted(out.rglob('*')):
 if not path.is_file()or path.name=='parent-review.json':continue
 raw=path.read_bytes();decoded=gzip.decompress(raw)if path.suffix=='.gz'else raw
 assert all(secret.encode()not in decoded for secret in secrets),path
 row={'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest()}
 if path.suffix=='.gz':row={'path':row['path'],'compressed_sha256':row['sha256'],'raw_sha256':hashlib.sha256(decoded).hexdigest()}
 artifacts.append(row)
report={'scope':'Shared-weight MTP startup and explicit separate-model compatibility, actual default runtime and optional long config','project_tests':422,'launcher_tests_before':{'failed':2,'passed':2},'launcher_tests_after':{'passed':4},'one_shot_native':replay,'bounded_feedback':summary,'qualification_increment':0,'full_goal':'NOT_READY','artifacts':artifacts}
(out/'parent-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'files':len(artifacts),'one_shot_passes':sum(r['recorded_passed']for r in replay),'feedback_passes':sum(t['passed']for t in summary['tasks'])}))
