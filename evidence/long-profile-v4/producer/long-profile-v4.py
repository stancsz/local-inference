"""Bounded local profile experiment; restore exact original images/settings."""
import hashlib,json,os,subprocess,sys,threading,time,urllib.request
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'evidence/long-profile-v4'
OUT.mkdir(exist_ok=False)
STOP=threading.Event()
STAGE='initial'
SAMPLES=[]
LIMIT=14_000_000_000/(1024**2)
PYTHON=sys.executable
STATE={'pid':os.getpid(),'started':datetime.now(timezone.utc).isoformat(),'status':'preparing',
       'limit_bytes':14_000_000_000,'limit_mib':LIMIT,'cases':[],
       'qualification_increment':0,'full_goal':'NOT_READY'}
STATE['advisor_council']='Unavailable: NORTHSTAR_COUNCIL_MODEL is unset; no substitute provider/model selected.'

def save():
    (OUT/'state.json').write_text(json.dumps(STATE,indent=2),encoding='utf-8')

def stage(name):
    global STAGE
    STAGE=name
    STATE['stage']=name
    save()
    print(name,flush=True)

def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8091'+path,timeout=5)as response:
        return json.load(response)

def gpu():
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=memory.total,memory.used,memory.free','--format=csv,noheader,nounits'],text=True,timeout=10)
    total,used,free=[int(x.strip())for x in raw.strip().split(',')]
    return {'at':datetime.now(timezone.utc).isoformat(),'stage':STAGE,'total_mib':total,'used_mib':used,'free_mib':free}

def sample():
    with (OUT/'gpu-samples.jsonl').open('w',encoding='utf-8')as stream:
        while not STOP.is_set():
            try:
                row=gpu();SAMPLES.append(row)
            except Exception as error:
                row={'at':datetime.now(timezone.utc).isoformat(),'stage':STAGE,'sampling_error':str(error)}
            stream.write(json.dumps(row)+'\n');stream.flush()
            STOP.wait(1)

def execute(args,label,timeout=120,env=None):
    with (OUT/(label+'.stdout.log')).open('w',encoding='utf-8')as out,(OUT/(label+'.stderr.log')).open('w',encoding='utf-8')as err:
        result=subprocess.run(args,cwd=ROOT,stdout=out,stderr=err,timeout=timeout,env=env)
    return result.returncode

def compose(override,*args,label):
    code=execute(['docker','compose','-f','compose.yaml','-f',str(override),*args],label,180)
    if code:raise RuntimeError(label+' failed: '+str(code))

def ready():
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        try:
            get('/health')
            return
        except Exception:time.sleep(2)
    raise TimeoutError('Backend readiness exceeded 180 seconds')

def config():
    result={}
    allowed={'CONTEXT_SIZE','GPU_LAYERS','DRAFT_GPU_LAYERS','DRAFT_TOKENS','UBATCH_SIZE','SPEC_TYPE','SIFT_TARGET','SIFT_COMPRESSION_RATIO','LLAMA_ARG_OVERRIDE_TENSOR'}
    for service in ('inference','gateway'):
        data=json.loads(subprocess.check_output(['docker','inspect','local-inference-'+service+'-1']))[0]
        settings={k:v for k,v in (item.split('=',1)for item in data['Config']['Env'])if k in allowed}
        result[service]={'image':data['Image'],'environment':settings}
    return result

def canonical_source(source):
    prefix='/run/desktop/mnt/host/'
    if source.startswith(prefix):
        remainder=source[len(prefix):]
        assert len(remainder)>2 and remainder[1]=='/'
        source=remainder[0]+':/'+remainder[2:]
    if len(source)>2 and source[1]==':':
        return source.replace(chr(92),'/').casefold()
    return source

def mounts():
    result={}
    for service in ('gateway','inference'):
        data=json.loads(subprocess.check_output(['docker','inspect','local-inference-'+service+'-1']))[0]
        result[service]=sorted([{k:v for k,v in m.items() if k in ('Type','Source','Destination','RW')} for m in data['Mounts']],key=lambda m:m['Destination'])
    for service in result:
        for mount in result[service]:
            mount['Source']=canonical_source(mount['Source'])
    return result

def write_override(name,services):
    target=ROOT/'tmp/stress'/name
    target.write_text(json.dumps({'services':services},indent=2),encoding='utf-8')
    return target

def main():
    original=config()
    STATE['original']=original
    STATE['original_mounts']=mounts()
    STATE['mount_comparison']='Canonical Windows/WSL bind aliases; RW/target/type preserved; startup bytes checked'
    STATE['startup_script_sha256']=hashlib.sha256(subprocess.check_output(['docker','exec','local-inference-inference-1','cat','/start-inference.sh'])).hexdigest()
    trace=ROOT/'tmp/stress/start-inference-trace-v4.sh'
    trace.write_bytes((ROOT/'docker/start-inference.sh').read_bytes().replace(b'set -- /app/llama-server',b'set -- /app/llama-server --log-verbosity 4'))
    STATE['original_context']=get('/props')['default_generation_settings']['n_ctx']
    STATE['plan']={'cpu_weight_block_order':[4],'second_case_condition':'No second case or replacement','purpose':'Capacity/task feasibility for the unchanged measured CPU4 profile; prior 20tok/s screen remains failed','prior_short_decode_tps':17.446676546114503,'benchmark_rerun':False,'tensor_override':r'blk\.[0-3]\..*=CPU',
        'context':69888,'sift_target':65536,'draft_tokens':1,'capacity_input':65536,'capacity_output':4096,
        'capacity_timeout_seconds':960,'no_replacements':True,'restore_original':True}
    STATE['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    STATE['source_hashes']={}
    for source in (Path(__file__),ROOT/'scripts/capacity_acceptance.py',ROOT/'scripts/local_smoke.py',ROOT/'scripts/openai_smoke.py',ROOT/'scripts/benchmark.py',ROOT/'scripts/context_acceptance.py',ROOT/'scripts/claude_acceptance.py',ROOT/'scripts/daily_artifacts.py',ROOT/'scripts/daily_acceptance.py',ROOT/'compose.yaml',trace):
        data=source.read_bytes()
        target=OUT/'producer'/source.name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(data)
        STATE['source_hashes'][source.name]=hashlib.sha256(data).hexdigest()
    assert not any(slot['is_processing']for slot in get('/slots')),'Backend is busy; experiment refused'
    assert STATE['original_context']==40960,'Expected daily profile; refusing to overwrite another profile'
    restoration=write_override('long-profile-v4-restore.json',original)
    thread=threading.Thread(target=sample,daemon=True);thread.start()
    env=dict(os.environ)
    env['PYTHONPATH']=str(ROOT.parent/'sift/src')+';'+str(ROOT)+';'+str(ROOT/'app')+';'+str(ROOT/'scripts')
    modified=False
    try:
        stage('stop-for-baseline')
        modified=True
        compose(restoration,'stop','gateway','inference',label='baseline-stop')
        stage('baseline-start');time.sleep(8)
        STATE['baseline_min_mib']=min(r['used_mib']for r in SAMPLES if r['stage']=='baseline-start')
        for layers in (4,):
            case={'gpu_layers':99,'ubatch_size':16,'cpu_weight_blocks':4,'context':69888,'sift_target':65536,'draft_tokens':1,'status':'starting'}
            STATE['cases'].append(case)
            settings=json.loads(json.dumps(original))
            settings['inference']['environment'].update(CONTEXT_SIZE='69888',GPU_LAYERS='99',DRAFT_TOKENS='1',UBATCH_SIZE='16',LLAMA_ARG_OVERRIDE_TENSOR=r'blk\.[0-3]\..*=CPU')
            settings['gateway']['environment'].update(CONTEXT_SIZE='69888',SIFT_TARGET='65536')
            settings['inference']['volumes']=[{'type':'bind','source':trace.as_posix(),'target':'/start-inference.sh','read_only':True}]
            override=write_override('long-profile-v4-'+str(layers)+'.json',settings)
            stage('loading-'+str(layers))
            try:
                compose(override,'up','-d','--no-build','inference','gateway',label=str(layers)+'-up')
                ready();time.sleep(5)
                assert get('/props')['default_generation_settings']['n_ctx']==69888
                loaded=[r['used_mib']for r in SAMPLES if r['stage']=='loading-'+str(layers)]
                case['startup_host_delta_mib']=max(loaded)-STATE['baseline_min_mib']
                if case['startup_host_delta_mib']>LIMIT:
                    case.update(status='memory-bound-missed',tests_not_run='Startup host delta already exceeds the declared limit')
                    continue
                env.update(CONTEXT_SIZE='69888',SIFT_TARGET='65536')
                stage('tests-'+str(layers))
                commands=[('capacity',['scripts/capacity_acceptance.py','--output',str(OUT/'4-capacity.json')],960),
                          ('local',['scripts/local_smoke.py','--output',str(OUT/'4-local.json')],240),
                          ('openai',['scripts/openai_smoke.py','--output',str(OUT/'4-openai.json')],420),
                          ('context',['scripts/context_acceptance.py','--output',str(OUT/'4-context.json')],1800),
                          ('claude-feedback',['scripts/daily_artifacts.py','--output-dir','tmp/long-profile-v4-4-claude'],2300)]
                case['checks']={}
                for name,args,timeout in commands:
                    stage('tests-'+str(layers)+'-'+name)
                    case['checks'][name]=execute([PYTHON,*args],str(layers)+'-'+name,timeout,env)
                    save()
                    if name=='capacity' and case['checks'][name]:break
                measurements=[r['used_mib']for r in SAMPLES if r['stage'].startswith(('loading-'+str(layers),'tests-'+str(layers)))]
                case['peak_host_delta_mib']=max(measurements)-STATE['baseline_min_mib']
                case['host_delta_within_limit']=case['peak_host_delta_mib']<=LIMIT
                case['status']='tested'
                if case['host_delta_within_limit']:break
            except Exception as error:
                case.update(status='error',error=str(error))
            finally:
                execute(['docker','logs','local-inference-inference-1'],str(layers)+'-inference',30)
                compose(override,'stop','gateway','inference',label=str(layers)+'-stop')
                save()
        stage('baseline-end');time.sleep(8)
    except Exception as error:
        STATE['experiment_error']=str(error)
    finally:
        if modified:
            stage('restoring-original')
            try:
                compose(restoration,'up','-d','--no-build','inference','gateway',label='restore-up')
                ready()
                assert hashlib.sha256(subprocess.check_output(['docker','exec','local-inference-inference-1','cat','/start-inference.sh'])).hexdigest()==STATE['startup_script_sha256']
                assert mounts()==STATE['original_mounts'], 'Restored mounts differ from original'
                assert config()==original,'Restored image/environment differ from the original'
                assert get('/props')['default_generation_settings']['n_ctx']==STATE['original_context']
                env.pop('CONTEXT_SIZE',None);env.pop('SIFT_TARGET',None)
                stage('restored-checks')
                STATE['restored_local_smoke_exit']=execute([PYTHON,'scripts/local_smoke.py','--output',str(OUT/'restored-local.json')],'restored-local',240,env)
                STATE['restored_openai_smoke_exit']=execute([PYTHON,'scripts/openai_smoke.py','--output',str(OUT/'restored-openai.json')],'restored-openai',420,env)
                STATE['restored_config']=config()
                STATE['restored']=True
            except Exception as error:
                STATE['restoration_error']=str(error)
                STATE['restored']=False
        STOP.set();thread.join(15)
        baseline=[r['used_mib']for r in SAMPLES if r['stage']in('baseline-start','baseline-end')]
        STATE['baseline_range_mib']=[min(baseline),max(baseline)]if baseline else None
        if baseline:
            for case in STATE['cases']:
                prefix=str(case['cpu_weight_blocks'])
                used=[r['used_mib']for r in SAMPLES if r['stage'].startswith(('loading-'+prefix,'tests-'+prefix))]
                if used:
                    case['conservative_host_delta_mib']=max(used)-min(baseline)
                    case['conservative_host_delta_within_limit']=case['conservative_host_delta_mib']<=LIMIT
        STATE['sample_count']=len(SAMPLES)
        STATE['status']='terminal'
        STATE['memory_scope']='Whole-host occupancy and conservative before/after delta, not isolated per-allocation residency. Desktop drift remains a confound.'
        save();print(json.dumps(STATE),flush=True)

if __name__=='__main__':main()
