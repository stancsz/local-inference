"""Independently verify and publish completed native-session evidence."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

from stress.cli_acceptance import native_evidence
from stress.cli_campaign import parse_events,session_id
from stress.acceptance_tasks import stage
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from setup_env import ROOT,gateway_key


def publish(path):
    raw=path.read_bytes();record=json.loads(raw)
    if not record.get('accepted'):return None
    turns=record['turns']
    assert len(turns)>=9 and record['active_client_seconds']>180
    assert abs(sum(t['duration_seconds'] for t in turns)-record['active_client_seconds'])<.05
    assert record['upstream']=='http://127.0.0.1:8090/v1'
    destination=ROOT/'evidence/stress-sessions'/path.parent.name
    destination.mkdir(parents=True,exist_ok=True)
    secrets=[gateway_key(),*[os.environ.get(n,'') for n in ('GATEWAY_MASTER_KEY','EXPERTS_API_KEY','ADVISOR_API_KEY')]]
    traces=[]
    for index,turn in enumerate(turns):
        source=path.parent/f'turn-{index:02}.jsonl';blob=source.read_bytes()
        assert not any(s and len(s)>12 and s.encode() in blob for s in secrets),'Credential found in native evidence'
        events=parse_events(blob.decode('utf-8'))
        assert session_id(record['client'],events)==record['session_id']
        assert native_evidence(record['client'],events,path.parent/'workspace')==turn['native']
        assert turn['accepted'] and turn['hidden_tests_exit']==0 and turn['historical_gold_passed']
        expected=stage(record['task'],index,record['seed']+index)['tests'].encode()
        # The controller writes public fixture text using Windows newlines.
        expected=expected.replace(b'\n',os.linesep.encode())
        assert hashlib.sha256(expected).hexdigest()==turn['public_tests_sha256']
        target=destination/(source.name+'.gz');target.write_bytes(gzip.compress(blob,mtime=0))
        traces.append({'file':target.relative_to(ROOT).as_posix(),'raw_sha256':hashlib.sha256(blob).hexdigest(),
            'compressed_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'native_calls':turn['native']['calls']})
    native=record['native_gateway_audits']
    assert native and all(r['native_input_tokens']+r['output_reserve']+r['decoder_headroom']<=r['context_window'] for r in native)
    for name in ('task.py','test_task.py','evidence.json'):
        (destination/name).write_bytes((path.parent/'workspace'/name).read_bytes())
    target=destination/'result.json.gz';target.write_bytes(gzip.compress(raw,mtime=0))
    return {'client':record['client'],'task':record['task'],'seed':record['seed'],'session_id':record['session_id'],
        'active_seconds':record['active_client_seconds'],'turns':len(turns),'receipt':target.relative_to(ROOT).as_posix(),
        'receipt_raw_sha256':hashlib.sha256(raw).hexdigest(),'traces':traces,'verified':True}


def main():
    rows=[row for path in sorted((ROOT/'tmp/stress/sessions').glob('*/result.json')) if (row:=publish(path))]
    manifest={'published_verified_sessions':len(rows),'sessions':rows,
        'scope':'Completed accepted sessions only. Full campaign outcome and rejected attempts remain in the controller report; this manifest alone is not a pass-rate claim.'}
    (ROOT/'evidence/stress-published.json').write_text(json.dumps(manifest,indent=2))
    print(f'{len(rows)} completed native sessions independently verified and published')


if __name__=='__main__':main()
