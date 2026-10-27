"""Sequential 21-session local CLI matrix with durable, inspectable receipts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timezone

from stress.cli_campaign import run,source_hashes
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from setup_env import ROOT,gateway_key


def qualifies(receipt):
    return (receipt.get('upstream')=='http://127.0.0.1:8090/v1'
        and receipt.get('active_client_seconds',0)>180
        and len(receipt.get('turns',[]))>=2 and bool(receipt.get('session_id')))


def cases():
    for repeat in range(3):
        tasks=('engineering','migration','expenses') if repeat<2 else ('engineering',)
        for task_index,task in enumerate(tasks):
            for client_index,client in enumerate(('claude','opencode','codex')):
                yield {'client':client,'task':task,'seed':831+repeat*1000+client_index*100+task_index*10,'repeat':repeat}


def reviewed_short_failure(path, expected_sha, frozen):
    """Acknowledge one inspected failure without changing its acceptance outcome."""
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha:
        raise ValueError('Acknowledged failure receipt changed')
    value=json.loads(path.read_text())
    if value.get('accepted') or qualifies(value) or value.get('source_sha256')!=frozen:
        raise ValueError('Acknowledgment requires a rejected short receipt from this source epoch')
    if value.get('upstream')!='http://127.0.0.1:8090/v1' or not value.get('failure'):
        raise ValueError('Acknowledgment requires a terminal local failure')
    return value


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--minimum-turns',type=int,default=9)
    parser.add_argument('--max-turns',type=int,default=32)
    parser.add_argument('--wait-pid',type=int)
    parser.add_argument('--prechecks',action='store_true')
    parser.add_argument('--acknowledge-short-failure',nargs=2,metavar=('RECEIPT','SHA256'))
    parser.add_argument('--extra-opencode-expenses',action='store_true')
    args=parser.parse_args()
    root=ROOT/'tmp/stress/sessions';root.mkdir(parents=True,exist_ok=True)
    status_path=ROOT/'evidence/stress-campaign.json'
    frozen=source_hashes()
    acknowledged=None
    if args.acknowledge_short_failure:
        receipt,sha=args.acknowledge_short_failure
        path=(ROOT/receipt).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('Acknowledged receipt must belong to campaign workspaces')
        acknowledged=(path,reviewed_short_failure(path,sha,frozen))
    plan=list(cases())
    if args.extra_opencode_expenses:
        plan.append({'client':'opencode','task':'expenses','seed':2951,'repeat':2})
    image=subprocess.check_output(['docker','inspect','--format','{{.Image}}','local-inference-gateway-1'],text=True).strip()
    os.environ['SIFT_ACCEPTANCE_API_KEY']=gateway_key()
    rows=[]
    status={'state':'running','controller_pid':os.getpid(),'upstream':'http://127.0.0.1:8090/v1',
        'controller_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'planned_sessions':len(plan),'required_qualifying_sessions':21,'minimum_active_seconds':185,'minimum_user_turns':args.minimum_turns,
        'gateway_image':image,'source_sha256':frozen,'sessions':rows,
        'scope':'Frozen uncommitted Sift candidate; real native CLIs in synthetic evolving workspaces. First-stage Sift hook uses LiteLLM counting; final gateway Sift uses the backend native full-request counter. No scripted idle padding or cloud inference.'}
    if acknowledged:
        status['acknowledged_short_failure']={'receipt':acknowledged[0].relative_to(ROOT).as_posix(),
            'sha256':args.acknowledge_short_failure[1],'accepted':False}
    status['plan']=plan
    def save():
        status['updated_at']=datetime.now(timezone.utc).isoformat()
        status.update(accepted_sessions=sum(row['accepted'] for row in rows),
            qualifying_long_sessions=sum(row['qualifying_long_session'] for row in rows))
        tmp=status_path.with_suffix('.tmp');tmp.write_text(json.dumps(status,indent=2));tmp.replace(status_path)
    save()
    if args.wait_pid:
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.OpenProcess(0x00100000,False,args.wait_pid)
        if not handle: raise RuntimeError('Cannot verify pilot process handle')
        try:
            status['state']='waiting_for_pilot';status['verified_wait_pid']=args.wait_pid;save()
            while kernel.WaitForSingleObject(handle,1000)==258:
                pass
        finally:
            kernel.CloseHandle(handle)
        status['state']='running';status.pop('verified_wait_pid',None);save()
    if args.prechecks:
        status['state']='prechecks';status['prechecks']=[];save()
        for script in ('local_smoke.py','openai_smoke.py','responses_smoke.py','context_acceptance.py','claude_acceptance.py'):
            log=ROOT/'tmp/stress'/('precheck-'+script+'.log')
            with log.open('w',encoding='utf-8') as stream:
                result=subprocess.run([sys.executable,str(ROOT/'scripts'/script)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=1200)
            status['prechecks'].append({'script':script,'exit':result.returncode,'log':str(log.relative_to(ROOT))});save()
            if result.returncode:
                status['state']='attention_required';save();return 1
        status['state']='running';save()
    for number,case in enumerate(plan,1):
        if source_hashes()!=frozen: raise RuntimeError('Campaign source changed; stop before next session')
        current_image=subprocess.check_output(['docker','inspect','--format','{{.Image}}','local-inference-gateway-1'],text=True).strip()
        if current_image!=image: raise RuntimeError('Gateway runtime image changed during campaign')
        label=f"{case['client']}-{case['task']}-r{case['repeat']}"
        status['current_case']={'index':number,**case};save()
        reused=None
        if acknowledged and all(acknowledged[1].get(k)==case[k] for k in ('client','task','seed')):
            reused=acknowledged
        for path in root.glob('*/result.json'):
            if reused:break
            value=json.loads(path.read_text())
            if ((value.get('accepted') or value.get('failure')) and qualifies(value) and value.get('source_sha256')==frozen
                    and all(value.get(k)==case[k] for k in ('client','task','seed'))):
                reused=(path,value);break
        if reused:
            path,result=reused
        else:
            destination=root/label
            if destination.exists():
                destination=root/(label+'-attempt-'+str(int(time.time())))
            options=argparse.Namespace(client=case['client'],task=case['task'],seed=case['seed'],output_dir=destination,
                upstream_base_url='http://127.0.0.1:8090/v1',api_key_env='SIFT_ACCEPTANCE_API_KEY',
                model='qwen3.8-27b-codex' if case['client']=='codex' else 'qwen3.8-27b',target=32768,
                minimum_seconds=185,minimum_turns=args.minimum_turns,max_turns=args.max_turns,turn_timeout=240)
            result=run(options);path=destination/'result.json'
        rows.append({'case':case,'receipt':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'accepted':bool(result['accepted']),'qualifying_long_session':qualifies(result),
            'active_client_seconds':result['active_client_seconds'],'turns':len(result['turns']),
            'failure':result.get('failure'),'reused_existing_accepted_receipt':bool(reused and result['accepted']),
            'reviewed_short_failure':bool(acknowledged and path.resolve()==acknowledged[0])})
        save()
        print(json.dumps({'completed':number,'accepted':status['accepted_sessions'],'qualifying_long_sessions':status['qualifying_long_sessions'],'case':case}),flush=True)
        # Do not repeat a wire/source failure for many cases without inspection.
        reviewed=rows[-1]['reviewed_short_failure']
        if not qualifies(result) and not reviewed:
            status['state']='attention_required';save();return 1
    status['state']='completed';status.pop('current_case',None);save()
    return 0 if status['qualifying_long_sessions']>=21 else 1


if __name__=='__main__':
    # Keep only this controller thread's system-execution request active.
    # Screen settings and the saved Windows power plan are unchanged.
    kernel=None
    if os.name=='nt':
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        if not kernel.SetThreadExecutionState(0x80000001):
            raise RuntimeError('Cannot establish campaign system execution request')
    try:
        raise SystemExit(main())
    finally:
        if kernel:kernel.SetThreadExecutionState(0x80000000)
