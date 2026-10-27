"""Check a pure recovery fixture against frozen code cases, without inference."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stress.acceptance_tasks import TASKS,stage
from stress.contract_probe import PREFIX,PROBES


def check_fixture(task,candidate,seed=97131):
    candidate=Path(candidate).resolve()
    source=candidate.read_bytes()
    digest=hashlib.sha256(source).hexdigest()
    bootstrap=("import sys,types,pathlib\n"
        "task=types.ModuleType('task')\n"
        f"task.__file__={str(candidate)!r}\n"
        "exec(compile(pathlib.Path(task.__file__).read_bytes(),task.__file__,'exec'),task.__dict__)\n"
        "sys.modules['task']=task\n")
    stages=[]
    for number in range(9):
        # A pure fixture has no model conversation: never seed fake evidence37.
        script=bootstrap+"sys.argv=['fixture-check','Acceptance.test_behavior']\n"+stage(task,number,seed+number)['tests']
        tested=subprocess.run([sys.executable,'-I','-B','-c',script],capture_output=True,text=True,timeout=20)
        stages.append({'stage':number+1,'seed':seed+number,'behavior_only':True,
            'passed':tested.returncode==0,'exit':tested.returncode,
            **({'output':tested.stdout+tested.stderr} if tested.returncode else {})})
    prefix=PREFIX.replace('sys.path.insert(0, sys.argv[1])\n','')
    script=bootstrap+prefix+PROBES[task]+'\nprint(json.dumps(results))\n'
    tested=subprocess.run([sys.executable,'-I','-B','-c',script],capture_output=True,text=True,timeout=20)
    extra=json.loads(tested.stdout) if tested.returncode==0 else [{'name':'probe execution','passed':False,'error':tested.stdout+tested.stderr}]
    unchanged=candidate.read_bytes()==source
    return {'task':task,'candidate':str(candidate),'candidate_sha256':digest,
        'behavior_stages':stages,'additional_probes':extra,'source_unchanged':unchanged,
        'passed':unchanged and all(s['passed'] for s in stages) and all(p['passed'] for p in extra),
        'scope':'Offline code behavior only. Historical-evidence tests are excluded; no synthetic evidence file, model inference, task session or campaign-count change.',
        'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',choices=TASKS,required=True)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--seed',type=int,default=97131)
    args=parser.parse_args()
    result=check_fixture(args.task,args.candidate,args.seed)
    print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
