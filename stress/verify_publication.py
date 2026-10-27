"""Offline byte and native-trace reconciliation; never calls inference."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]


def byte_identity(published,original,indexed,recorded_sha256):
    if published!=original or published!=indexed or hashlib.sha256(published).hexdigest()!=recorded_sha256:
        raise ValueError('Published fixture byte identity mismatch')


def main(*,write=True):
    sys.path.insert(0,str(ROOT/'tmp/stress/sift-candidate/src'))
    from stress.cli_campaign import parse_events,session_id,source_hashes
    from stress.cli_acceptance import native_evidence
    from stress.acceptance_tasks import stage
    campaign=json.loads((ROOT/'evidence/stress-campaign.json').read_text())
    manifest=json.loads((ROOT/'evidence/stress-published.json').read_text())
    byte_proof=json.loads((ROOT/'evidence/stress-fixture-byte-integrity.json').read_text())['after']
    recorded={row['file']:row for row in byte_proof['files']}
    probes={row['receipt']:row for row in json.loads((ROOT/'evidence/stress-contract-probes.json').read_text())['sessions']}
    frozen=source_hashes()
    assert frozen==campaign['source_sha256']
    image=subprocess.check_output(['docker','inspect','--format','{{.Image}}','local-inference-gateway-1'],text=True).strip()
    assert image==campaign['gateway_image']
    checked=[];identifiers=set();trace_count=0;native_count=0
    for entry in manifest['sessions']:
        compressed=ROOT/entry['receipt']
        raw=gzip.decompress(compressed.read_bytes())
        assert hashlib.sha256(raw).hexdigest()==entry['receipt_raw_sha256']
        record=json.loads(raw)
        original=ROOT/'tmp/stress/sessions'/compressed.parent.name
        assert raw==(original/'result.json').read_bytes()
        assert record['accepted'] and len(record['turns'])==9 and record['active_client_seconds']>180
        assert abs(sum(t['duration_seconds'] for t in record['turns'])-record['active_client_seconds'])<.05
        assert record['upstream']=='http://127.0.0.1:8090/v1'
        assert record['session_id'] not in identifiers
        identifiers.add(record['session_id'])
        for number,turn in enumerate(record['turns']):
            trace=entry['traces'][number]
            blob=gzip.decompress((ROOT/trace['file']).read_bytes())
            assert hashlib.sha256(blob).hexdigest()==trace['raw_sha256']
            assert blob==(original/f'turn-{number:02}.jsonl').read_bytes()
            events=parse_events(blob.decode('utf-8'))
            assert session_id(record['client'],events)==record['session_id']
            native=native_evidence(record['client'],events,original/'workspace')
            assert native==turn['native'] and native['terminal_success'] and native['final_passed']
            assert native['calls']==native['completed'] and native['unmatched_results']==0
            assert turn['accepted'] and turn['hidden_tests_exit']==0 and turn['historical_gold_passed']
            expected=stage(record['task'],number,record['seed']+number)['tests'].encode()
            assert turn['public_tests_sha256'] in {hashlib.sha256(expected).hexdigest(),hashlib.sha256(expected.replace(b'\n',b'\r\n')).hexdigest()}
            trace_count+=1
        for audit in record['native_gateway_audits']:
            assert audit['native_input_tokens']+audit['output_reserve']+audit['decoder_headroom']<=audit['context_window']
            native_count+=1
        for name in ('task.py','test_task.py','evidence.json'):
            path=compressed.parent/name
            relative=path.relative_to(ROOT).as_posix()
            evidence=recorded[relative]
            blob=path.read_bytes()
            indexed=subprocess.check_output(['git','show',':'+relative])
            byte_identity(blob,(original/'workspace'/name).read_bytes(),indexed,evidence['published_sha256'])
            assert evidence['index_sha256']==evidence['original_workspace_sha256']==evidence['published_sha256']
            if name=='test_task.py':assert hashlib.sha256(blob).hexdigest()==record['turns'][-1]['public_tests_sha256']
            if name=='task.py':assert hashlib.sha256(blob).hexdigest()==probes[(original/'result.json').relative_to(ROOT).as_posix()]['task_sha256']
            if name=='evidence.json':assert json.loads(blob)['acceptance_delay_seconds']==37
            checked.append({'file':relative,'sha256':hashlib.sha256(blob).hexdigest(),'matches_record_original_index':True})
    rejected=json.loads((ROOT/'evidence/stress-rejected.json').read_text())
    rejected_files=0
    for attempt in rejected['attempts']:
        assert not attempt['accepted']
        for item in attempt['files']:
            blob=(ROOT/item['file']).read_bytes()
            assert hashlib.sha256(blob).hexdigest()==item['compressed_sha256']
            assert hashlib.sha256(gzip.decompress(blob)).hexdigest()==item['raw_sha256']
            rejected_files+=1
    assert len(checked)==len(recorded)
    result={'captured_at':datetime.now(timezone.utc).isoformat(),'owner':'commander offline reconciliation; not independent acceptance',
        'verdict':'PASS for published byte/trace reconciliation only','published_sessions':len(identifiers),
        'published_native_turns':trace_count,'published_fixtures':len(checked),'fixture_mismatches':0,
        'recorded_public_test_hashes_checked':trace_count,'native_budget_checks':native_count,
        'rejected_attempts':len(rejected['attempts']),'rejected_archived_files':rejected_files,
        'live_frozen_sources_match':True,'gateway_image':image,'fixtures':checked,
        'scope':'All published accepted epochs, including two historical gateway/harness epochs; not a homogeneous current-matrix count. Rejected bytes are checked without reclassifying outcomes. No inference or task-artifact edits.'}
    if write:
        (ROOT/'evidence/stress-published-fixture-review.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('fixtures','scope','owner','gateway_image')}))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--check-only',action='store_true',help='Verify and print results without writing evidence')
    args=parser.parse_args()
    main(write=not args.check_only)
