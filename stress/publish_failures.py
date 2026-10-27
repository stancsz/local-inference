"""Publish retained rejected runner attempts without reclassifying them."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from setup_env import gateway_key


def main():
    campaign=json.loads((ROOT/'evidence/stress-campaign.json').read_text())
    current={row['receipt'] for row in campaign['sessions']}
    secrets=[gateway_key(),*[os.environ.get(name,'') for name in ('GATEWAY_MASTER_KEY','EXPERTS_API_KEY','ADVISOR_API_KEY')]]
    rows=[]
    for receipt in sorted((ROOT/'tmp/stress/sessions').glob('*/result.json')):
        record=json.loads(receipt.read_text())
        if record.get('accepted') or not record.get('failure'):
            continue
        folder=receipt.parent
        destination=ROOT/'evidence/stress-failures'/folder.name
        destination.mkdir(parents=True,exist_ok=True)
        sources=[receipt,*sorted(folder.glob('turn-*.jsonl')),
                 *sorted(folder.glob('turn-*.stderr.txt')),*sorted(folder.glob('turn-*.hidden-tests.txt'))]
        sources.extend(path for name in ('task.py','test_task.py','evidence.json') if (path:=folder/'workspace'/name).is_file())
        files=[]
        for source in sources:
            raw=source.read_bytes()
            assert not any(secret and len(secret)>12 and secret.encode() in raw for secret in secrets), 'Credential found in rejected evidence'
            name=source.relative_to(folder).as_posix().replace('/','-')+'.gz'
            target=destination/name
            if target.exists():
                assert gzip.decompress(target.read_bytes())==raw, 'Previously archived rejected evidence changed'
            else:
                target.write_bytes(gzip.compress(raw,mtime=0))
            files.append({'file':target.relative_to(ROOT).as_posix(),
                          'raw_sha256':hashlib.sha256(raw).hexdigest(),
                          'compressed_sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
        relative=receipt.relative_to(ROOT).as_posix()
        rows.append({'receipt':relative,'receipt_raw_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),
            'client':record['client'],'task':record['task'],'accepted':False,
            'turns':len(record.get('turns',[])),'active_seconds':record.get('active_client_seconds',0),
            'in_current_controller_outcomes':relative in current,
            'source_matches_current':record.get('source_sha256')==campaign['source_sha256'],
            'files':files})
    result={'retained_rejected_runner_attempts':len(rows),'attempts':rows,
        'scope':'Rejected terminal runner receipts only, including historical setup/compatibility failures and current model stalls. In-progress receipts are excluded. Different source epochs and setup conditions are not one steady-state failure-rate denominator. Original acceptance remains false.'}
    (ROOT/'evidence/stress-rejected.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'archived_rejected_attempts':len(rows),'current_controller_rejections':sum(row['in_current_controller_outcomes'] for row in rows)}))


if __name__=='__main__':main()
