"""Run the sealed shared-MTP on/off comparison after Codex is terminal."""
import hashlib,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'evidence/shared-mtp-pair-v1'
PLAN=json.loads((ROOT/'evidence/shared-mtp-pair-v1-plan.json').read_text())
FIELDS=('CONTEXT_SIZE','GPU_LAYERS','DRAFT_GPU_LAYERS','DRAFT_TOKENS','UBATCH_SIZE','SPEC_TYPE','MTP_MODEL_PATH','SIFT_TARGET','SIFT_COMPRESSION_RATIO')
def props(path='/props'):
 with urllib.request.urlopen('http://127.0.0.1:8091'+path,timeout=5)as response:return json.load(response)
def snapshot():
 result={}
 for service in ('inference','gateway'):
  row=json.loads(subprocess.check_output(['docker','inspect','local-inference-'+service+'-1']))[0]
  result[service]={'image':row['Image'],'environment':{k:v for item in row['Config']['Env']for k,_,v in [item.partition('=')]if k in FIELDS}}
 return result
def ready():
 deadline=time.monotonic()+180
 while time.monotonic()<deadline:
  try:
   if props()['default_generation_settings']['n_ctx']==40960:
    with urllib.request.urlopen('http://127.0.0.1:8090/health/readiness',timeout=5)as response:
     if response.status==200:return
  except Exception:pass
  time.sleep(1)
 raise TimeoutError('Paired profile readiness did not complete within180 seconds')
def execute(args,name,timeout=660):
 with (OUT/(name+'.stdout.log')).open('x',encoding='utf-8')as out,(OUT/(name+'.stderr.log')).open('x',encoding='utf-8')as err:
  child=subprocess.Popen(args,cwd=ROOT,stdout=out,stderr=err)
  try:code=child.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
   child.wait(timeout=20);raise
 assert code==0,(name,code)
def configure(services,name):
 path=ROOT/'tmp/stress'/('pair-v1-'+name+'.json');path.write_text(json.dumps({'services':services}))
 execute(['docker','compose','-f','compose.yaml','-f',str(path),'up','-d','--no-build','--force-recreate','inference','gateway'],name+'-up',180)
 ready()
def main():
 assert json.loads((ROOT/'evidence/codex-shared-mtp-v1-state.json').read_text())['status']=='terminal','Refuse to mutate a live campaign runtime'
 assert not any(s['is_processing']for s in props('/slots')),'Inference slot is busy'
 assert props()['default_generation_settings']['n_ctx']==40960
 assert hashlib.sha256((ROOT/'scripts/benchmark.py').read_bytes()).hexdigest()==PLAN['script_sha256']
 assert hashlib.sha256((ROOT/'docker/start-inference.sh').read_bytes()).hexdigest()==PLAN['startup_sha256']
 OUT.mkdir(exist_ok=False)
 original=snapshot();assert original['inference']['environment']['SPEC_TYPE']=='draft-mtp'
 assert not original['inference']['environment'].get('MTP_MODEL_PATH')
 record={'plan':'evidence/shared-mtp-pair-v1-plan.json','pid':os.getpid(),'original':original,'arms':[],'qualification_increment':0,'full_goal':'NOT_READY'}
 (OUT/'producer').mkdir()
 for source in (Path(__file__),ROOT/'scripts/benchmark.py',ROOT/'docker/start-inference.sh'):
  (OUT/'producer'/source.name).write_bytes(source.read_bytes())
 def save():(OUT/'state.json').write_text(json.dumps(record,indent=2))
 save()
 try:
  for name,spec in (('shared-on','draft-mtp'),('off','none')):
   settings=json.loads(json.dumps(original));settings['inference']['environment']['SPEC_TYPE']=spec
   configure(settings,name)
   label='shared-pair-v1-'+name
   execute([sys.executable,'scripts/benchmark.py','--label',label,'--tokens','256'],name+'-benchmark')
   source=ROOT/'evidence'/('benchmark-'+label+'.json');samples=json.loads(source.read_text())
   assert len(samples)==2 and all(row['usage']['completion_tokens']==256 for row in samples)
   for row in samples:
    accepted=row['timings'].get('draft_n_accepted',0)
    assert accepted>0 if spec=='draft-mtp'else accepted==0
   (OUT/(name+'.json')).write_bytes(source.read_bytes())
   record['arms'].append({'name':name,'average_decode_tok_s':sum(row['timings']['predicted_per_second']for row in samples)/2,'draft_accepted':[row['timings'].get('draft_n_accepted',0)for row in samples]});save()
 except Exception as error:
  record['error']=str(error);save()
 finally:
  try:
   configure(original,'restore')
   assert snapshot()==original
   actual=subprocess.check_output(['docker','exec','local-inference-inference-1','cat','/start-inference.sh'])
   assert hashlib.sha256(actual).hexdigest()==PLAN['startup_sha256']
   execute([sys.executable,'scripts/local_smoke.py','--output',str(OUT/'restored-local.json')],'restored-local',240)
   execute([sys.executable,'scripts/openai_smoke.py','--output',str(OUT/'restored-openai.json')],'restored-openai',420)
   record['restored']=True
  except Exception as error:record.update(restored=False,restoration_error=str(error))
  record['status']='terminal'
  if len(record['arms'])==2:record['decode_ratio_on_over_off']=record['arms'][0]['average_decode_tok_s']/record['arms'][1]['average_decode_tok_s']
  save()
 print(json.dumps(record),flush=True)
if __name__=='__main__':main()
