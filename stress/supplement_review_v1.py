"""Read-only supplement verification and opt-in immutable evidence publication."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def basic_failures(record, expected_sources):
    failures = []
    turns = record.get('turns', [])
    active = record.get('active_client_seconds', 0)
    if not record.get('accepted'): failures.append('runner rejected')
    if len(turns) < 9 or active <= 185: failures.append('long-session threshold')
    if abs(sum(t.get('duration_seconds', 0) for t in turns) - active) >= .05: failures.append('active-time sum')
    if not record.get('session_id'): failures.append('session missing')
    if record.get('upstream') != 'http://127.0.0.1:8090/v1': failures.append('wrong upstream')
    expected_model = 'qwen3.8-27b-codex' if record.get('client') == 'codex' else 'qwen3.8-27b'
    if record.get('model') != expected_model: failures.append('wrong local model alias')
    if record.get('source_sha256') != expected_sources: failures.append('source identity')
    if any(not t.get('accepted') or t.get('timed_out') or t.get('client_exit') != 0 or t.get('hidden_tests_exit') != 0 or not t.get('historical_gold_passed') for t in turns):
        failures.append('failed native/hidden/history turn')
    native = record.get('native_gateway_audits', [])
    if not native or any(a['native_input_tokens'] + a['output_reserve'] + a['decoder_headroom'] > a['context_window'] for a in native):
        failures.append('native context limits')
    audits = record.get('audits', [])
    compacted = [a for a in audits if a.get('compacted') is True]
    if not compacted or not any(a.get('tool_results', 0) for a in audits) or any(not a.get('gold_retained') or a['forwarded_tokens'] > record['target'] for a in compacted) or any(a.get('upstream_status') != 200 for a in audits):
        failures.append('Sift compaction/history/upstream')
    return failures


def review(publish=False):
    from stress.cli_acceptance import native_evidence
    from stress.cli_campaign import parse_events, session_id
    from stress.supplement_tasks_v1 import stage
    root = ROOT / 'tmp/supplement-v1'
    state = json.loads((ROOT / 'evidence/supplement-v1-state.json').read_text(encoding='utf-8'))
    if state['state'] not in ('terminal_review_required', 'terminal_controller_failure'):
        raise RuntimeError('Supplement is still running; no terminal verdict permitted')
    plan = json.loads((ROOT / 'evidence/supplement-v1-plan.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((ROOT / 'evidence/supplement-v1-plan.json').read_bytes()).hexdigest() == state['plan_sha256']
    assert json.loads(subprocess.check_output(['git', 'show', state['plan_commit'] + ':evidence/supplement-v1-plan.json'])) == plan
    expected = {**plan['original_source_sha256'],
        'stress.supplement_tasks_v1': plan['new_source_sha256']['stress/supplement_tasks_v1.py'],
        'stress.supplement_campaign_v1': plan['new_source_sha256']['stress/supplement_campaign_v1.py']}
    for name, digest in plan['new_source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    destination = ROOT / 'evidence/supplement-v1-sessions'
    if publish: destination.mkdir(exist_ok=False)
    manifest, rows = [], []
    sys.path.insert(0, str(ROOT / 'scripts'))
    from setup_env import gateway_key
    secrets = [gateway_key(), *[os.environ.get(n, '') for n in ('GATEWAY_MASTER_KEY', 'EXPERTS_API_KEY', 'ADVISOR_API_KEY')]] if publish else []
    def archive(source, target, zipped=False):
        if not publish: return
        raw = source.read_bytes()
        assert not any(s and len(s) > 12 and s.encode() in raw for s in secrets), str(source)
        target = destination / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gzip.compress(raw, mtime=0) if zipped else raw)
        manifest.append({'file': target.relative_to(ROOT).as_posix(), 'raw_sha256': hashlib.sha256(raw).hexdigest(), 'gzip': zipped})
    for case in plan['cases']:
        folder = root / case['id']
        path = folder / 'result.json'
        record = json.loads(path.read_text(encoding='utf-8'))
        failures = basic_failures(record, expected)
        per_turn = []
        for index, turn in enumerate(record['turns']):
            source = folder / f'turn-{index:02}.jsonl'
            events = parse_events(source.read_text(encoding='utf-8'))
            native = native_evidence(case['client'], events, folder / 'workspace')
            sid = session_id(case['client'], events)
            if native != turn['native'] or sid != record['session_id']: failures.append(f'turn{index+1} native/continuity mismatch')
            if not native['terminal_success'] or not native['final_passed'] or native['unmatched_results'] != 0 or native['completed'] != native['calls'] or (index == 0 and not native['workflow_ordered']):
                failures.append(f'turn{index+1} native acceptance failure')
            generated = stage(case['task'], index, case['seed'] + index)['tests'].encode('utf-8').replace(b'\n', os.linesep.encode())
            if hashlib.sha256(generated).hexdigest() != turn['public_tests_sha256']: failures.append(f'turn{index+1} public fixture hash')
            for event in events:
                # Review task-tool arguments for direct solution-reference access.
                if any(token in json.dumps(event) for token in ('test_supplement_tasks.py', 'incident_reference', 'manifest_reference')):
                    failures.append(f'turn{index+1} solution-reference access')
            definition = stage(case['task'], index, case['seed'] + index + 200003)['tests']
            prefix = "import sys;sys.path.insert(0,sys.argv[1]);sys.argv=['parent-check'];"
            tested = subprocess.run([sys.executable, '-I', '-B', '-c', prefix + definition, str(folder / 'workspace')],
                                    cwd=folder / 'workspace', capture_output=True, timeout=20)
            if tested.returncode: failures.append(f'turn{index+1} final implementation parent-seed failure')
            per_turn.append({'turn': index + 1, 'session_id': sid, 'native_verified': native == turn['native'],
                             'parent_seed_exit': tested.returncode, 'parent_seed_output': (tested.stdout + tested.stderr).decode('utf-8', errors='replace')})
        evidence = json.loads((folder / 'workspace/evidence.json').read_text())
        if type(evidence.get('acceptance_delay_seconds')) is not int or evidence['acceptance_delay_seconds'] != 37:
            failures.append('final history value')
        for source in folder.rglob('*'):
            if source.is_file():
                relative = source.relative_to(folder).as_posix()
                # Caches and isolated CLI profile state are not inference evidence.
                if relative.startswith('client-home/') or '__pycache__' in source.parts: continue
                zipped = source.suffix not in ('.py', '.json')
                archive(source, case['id'] + '/' + relative + ('.gz' if zipped else ''), zipped)
        rows.append({'id': case['id'], 'client': case['client'], 'task': case['task'], 'seed': case['seed'],
            'qualified_by_parent_checks': not failures, 'runner_accepted': record['accepted'],
            'active_seconds': record['active_client_seconds'], 'user_turns': len(record['turns']),
            'session_id': record['session_id'], 'failures': failures, 'turn_review': per_turn,
            'native_budget_checks': len(record.get('native_gateway_audits', [])),
            'final_source_sha256': hashlib.sha256((folder / 'workspace/task.py').read_bytes()).hexdigest()})
    original = json.loads((ROOT / 'evidence/stress-campaign.json').read_text())
    assert original['qualifying_long_sessions'] == 19 and len(original['sessions']) == 22
    assert hashlib.sha256((ROOT / 'evidence/stress-campaign.json').read_bytes()).hexdigest() == plan['original_matrix']['raw_sha256']
    verified_original = 0
    for row in original['sessions']:
        raw = (ROOT / row['receipt']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['sha256'], row['receipt']
        record = json.loads(raw)
        assert record['accepted'] == row['accepted']
        if row['qualifying_long_session']:
            assert not basic_failures(record, plan['original_source_sha256']), row['receipt']
            verified_original += 1
    assert verified_original == 19
    clients = Counter(r['case']['client'] for r in original['sessions'] if r['qualifying_long_session'])
    for row in rows:
        if row['qualified_by_parent_checks']: clients[row['client']] += 1
    samples = [json.loads(line) for line in (root / 'gpu-samples.jsonl').read_text().splitlines() if line.strip()]
    archive(root / 'gpu-samples.jsonl', 'gpu-samples.jsonl.gz', True)
    supplement_count = sum(r['qualified_by_parent_checks'] for r in rows)
    return {'original_matrix_qualifying': 19, 'original_matrix_attempts': 22,
        'supplement_qualifying': supplement_count, 'candidate_aggregate_qualifying': 19 + supplement_count,
        'aggregate_clients': dict(clients), 'cases': rows, 'manifest': manifest,
        'host_gpu_samples': len(samples), 'memory_limit': 'Whole-host samples, not isolated residency or an under14GB proof.',
        'epochs': 'Original matrix and prospective new workload epoch remain separate; identical implementation hash/image identity is required.',
        'full_goal_complete': False, 'final_independent_acceptance': 'pending',
        'known_quality_limits': 'Original12/19 additional-contract failures and residual generated-expense defects remain unrepaired; no reliability or unattended-production approval.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    result = review(args.publish)
    if args.publish:
        path = ROOT / 'evidence/supplement-v1-parent-review.json'
        path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
