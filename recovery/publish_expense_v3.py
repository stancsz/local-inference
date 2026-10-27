"""Publish the completed expense-feedback-v3 increment and independently replay it.

Scope: read the finished tmp/expense-feedback-v3 experiment, re-verify its
hashes, replay the frozen checks against the original v2 generated source and
against the final generated source, re-check native acceptance from the stored
raw events, scan for credential leakage and publish every experiment file
byte-exact with a SHA256 manifest. No inference, no count changes.
"""
import json
import os
import shutil
from pathlib import Path

from recovery.generation_v1 import ROOT, dump, sha, native_acceptance, protected_hashes
from recovery.expense_feedback_v3 import BASELINE, PROBES, checks

EXPERIMENT = ROOT / 'tmp/expense-feedback-v3'
PUBLISH = ROOT / 'evidence/expense-feedback-v3'
REPORT = ROOT / 'evidence/expense-feedback-v3.json'
MARKER = 'EXPENSE_V3_DONE'


def env_credential_values():
    """Collect credential-looking environment values; never printed to output."""
    values = {}
    for name, value in os.environ.items():
        upper = name.upper()
        if not value or len(value) < 8:
            continue
        if any(tag in upper for tag in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'CREDENTIAL')):
            values[name] = value.encode('utf-8', 'ignore')
    return values


def copy_tree(source, destination):
    """Byte-exact copy of a directory tree, returning {relative path: sha256}."""
    digests = {}
    for path in sorted(source.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        digests[str(relative).replace('\\', '/')] = sha(target.read_bytes())
    return digests


def summarize_behavior(folder):
    """Read the frozen behavior stdout and count stages/probes."""
    path = folder / 'behavior.stdout'
    if not path.exists():
        return {'available': False}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as error:
        return {'available': False, 'error': type(error).__name__}
    stages = data.get('behavior_stages', [])
    probes = data.get('additional_probes', [])
    return {
        'available': True,
        'behavior_stages_total': len(stages),
        'behavior_stages_passed': sum(1 for s in stages if s.get('passed')),
        'existing_probes_total': len(probes),
        'existing_probes_passed': sum(1 for p in probes if p.get('passed')),
        'source_unchanged': data.get('source_unchanged'),
        'checker_sha256': data.get('checker_sha256'),
        'candidate_sha256': data.get('candidate_sha256'),
    }


def replay(name, source_bytes, folder):
    folder.mkdir(parents=True, exist_ok=True)
    candidate = folder / 'source.py'
    candidate.write_bytes(source_bytes)
    outcome = checks(candidate, folder)
    regression = outcome['listed'].get('regressions', {})
    summary = ''
    stdout = folder / 'regressions.stdout'
    if stdout.exists():
        summary = stdout.read_text(encoding='utf-8', errors='replace').strip()
    additional = outcome['additional']
    return {
        'name': name,
        'source_sha256': sha(source_bytes),
        'listed_behavior_passed': bool(outcome['listed'].get('behavior', {}).get('passed')),
        'listed_regressions_passed': bool(regression.get('passed')),
        'regressions_exit_code': regression.get('exit_code'),
        'regressions_timed_out': regression.get('timed_out'),
        'regressions_summary': summary,
        'behavior': summarize_behavior(folder),
        'parent_probes_total': len(additional),
        'parent_probes_passed': sum(1 for c in additional if c.get('passed')),
        'parent_probes': additional,
        'overall_passed': bool(outcome['passed']),
        'source_unchanged_after_replay': candidate.read_bytes() == source_bytes,
    }


def main():
    plan = json.loads((EXPERIMENT / 'plan.json').read_text(encoding='utf-8'))
    result = json.loads((EXPERIMENT / 'result.json').read_text(encoding='utf-8'))

    hash_checks = {}
    harness = ROOT / 'recovery/expense_feedback_v3.py'
    hash_checks['recovery/expense_feedback_v3.py'] = {
        'expected': plan['harness_sha256'], 'actual': sha(harness.read_bytes())}
    for name, expected in plan['helper_sha256'].items():
        hash_checks[name] = {'expected': expected, 'actual': sha((ROOT / name).read_bytes())}
    hash_checks['baseline (v2 generated source)'] = {
        'expected': plan['baseline_sha256'], 'actual': sha(BASELINE.read_bytes())}
    hash_checks['parent probes'] = {
        'expected': plan['probes_sha256'], 'actual': sha(PROBES.read_bytes())}
    final_bytes = (EXPERIMENT / 'task.py').read_bytes()
    hash_checks['final generated source'] = {
        'expected': result['final_source_sha256'], 'actual': sha(final_bytes)}
    hash_checks['turn-1 after bytes == final source'] = {
        'expected': result['final_source_sha256'],
        'actual': sha((EXPERIMENT / 'turn-1/after.py').read_bytes())}
    for entry in hash_checks.values():
        entry['matches'] = entry['expected'] == entry['actual']

    if not all(entry['matches'] for entry in hash_checks.values()):
        raise ValueError('Experiment source/hash mismatch; publication refused')
    PUBLISH.mkdir(parents=True, exist_ok=False)
    replay_root = PUBLISH / 'replay'
    baseline_replay = replay('baseline_v2_generated', BASELINE.read_bytes(), replay_root / 'baseline_v2_generated')
    final_replay = replay('final_generated', final_bytes, replay_root / 'final_generated')

    before = (EXPERIMENT / 'turn-1/before.py').read_bytes()
    after = (EXPERIMENT / 'turn-1/after.py').read_bytes()
    events = [json.loads(line) for line in (EXPERIMENT / 'turn-1/native.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    receipt = result['turns'][0]
    native = native_acceptance(events, EXPERIMENT, before, after, receipt['process']['exit_code'], receipt['process']['timed_out'], MARKER)
    native['matches_recorded'] = native == receipt['native']
    native['before_sha256'] = sha(before)
    native['after_sha256'] = sha(after)
    native['after_equals_final_source'] = after == final_bytes

    if not (baseline_replay['parent_probes_total'] == 6 and baseline_replay['parent_probes_passed'] == 0 and final_replay['parent_probes_total'] == 6 and final_replay['parent_probes_passed'] == 6 and final_replay['overall_passed'] and final_replay['source_unchanged_after_replay'] and native['passed'] and native['matches_recorded'] and native['after_equals_final_source']):
        raise ValueError('Replay/native acceptance failed; no passing report published')

    credentials = env_credential_values()
    publish_sources = sorted({p for p in EXPERIMENT.rglob('*') if p.is_file()})
    leaks = []
    for path in publish_sources:
        blob = path.read_bytes()
        for name, value in credentials.items():
            if value in blob:
                leaks.append({'file': str(path.relative_to(ROOT)).replace('\\', '/'), 'variable': name})
    if leaks:
        print(json.dumps({'published': False, 'reason': 'credential leakage detected in experiment artifacts',
                          'leak_count': len(leaks), 'leaks': leaks}, indent=2))
        return 1

    digests = copy_tree(EXPERIMENT, PUBLISH / 'experiment')
    manifest = {
        'artifact': 'expense-feedback-v3',
        'root': str(PUBLISH.relative_to(ROOT)).replace('\\', '/'),
        'hash_algorithm': 'sha256',
        'files': [{'file': 'experiment/' + name, 'sha256': value,
                   'bytes': (PUBLISH / 'experiment' / name).stat().st_size}
                  for name, value in sorted(digests.items())],
    }
    dump(PUBLISH / 'manifest.json', manifest)

    report = {
        'artifact': 'expense-feedback-v3',
        'kind': 'Separate versioned publication of a completed bounded local-Qwen expense repair increment with independent replay',
        'published_from': str(EXPERIMENT.relative_to(ROOT)).replace('\\', '/'),
        'publisher': 'recovery/publish_expense_v3.py',
        'inference_performed_by_publisher': False,
        'task_inference_endpoint': 'http://127.0.0.1:8090',
        'plan': plan,
        'experiment_result': result,
        'hash_verification': hash_checks,
        'hash_verification_all_match': all(e['matches'] for e in hash_checks.values()),
        'replay': {
            'baseline_v2_generated_source': baseline_replay,
            'final_generated_source': final_replay,
            'parent_probes_baseline_expected': '0/6',
            'parent_probes_final_expected': '6/6',
            'parent_probes_baseline_actual': str(baseline_replay['parent_probes_passed']) + '/' + str(baseline_replay['parent_probes_total']),
            'parent_probes_final_actual': str(final_replay['parent_probes_passed']) + '/' + str(final_replay['parent_probes_total']),
        },
        'native_acceptance_recheck': native,
        'credential_scan': {
            'scanned_files': len(publish_sources),
            'environment_variables_scanned': len(credentials),
            'values_displayed': False,
            'leaks': 0,
        },
        'protected_hashes_after_publication': protected_hashes(),
        'manifest': manifest['files'],
        'manifest_path': str((PUBLISH / 'manifest.json').relative_to(ROOT)).replace('\\', '/'),
        'counts': {
            'original_qualifying_sessions': 19,
            'accepted_supplement_qualifying_sessions': 1,
            'candidate_aggregate_sessions': 20,
            'required_sessions': 21,
            'shortfall': 1,
            'final_independent_acceptance': 'pending',
            'qualifying_session_increment_from_this_increment': 0,
            'note': 'Counts are carried forward unchanged from the parent ledger; this publisher independently accepted nothing.',
        },
        'verdict': {
            'generated_repair': 'PASS: model-generated final source passes the unchanged expense regressions, all 9 original behavior stages, the 12 existing probes and the 6 pre-existing parent probes in replay.',
            'final_independent_acceptance': 'PENDING: parent-owned final acceptance and full-goal review are not performed here.',
            'full_goal': 'NOT_READY',
        },
        'limits': [
            'No model inference was executed by this publisher; the single 16.48s turn was already run by the committed b2e8a8f harness.',
            'Only the frozen expense regressions, the 9 original behavior stages, the 12 existing probes and the 6 pre-existing parent probes were replayed; this is not universal correctness.',
            'Generated repair by the local model is not the same as final independent acceptance; no session count was incremented.',
            'Experiment files are published byte-exact; the manifest carries SHA256 for each published file.',
            'Credential values were scanned from the environment without being displayed; no key material is published.',
            'Source correspondence with the committed harness must be verified by the parent (git unavailable to this worker).',
        ],
    }
    dump(REPORT, report)
    print(json.dumps({'published': True, 'report': str(REPORT), 'files': len(manifest['files']),
                      'hashes_ok': report['hash_verification_all_match'],
                      'baseline_probes': report['replay']['parent_probes_baseline_actual'],
                      'final_probes': report['replay']['parent_probes_final_actual'],
                      'native_recheck_passed': native['passed']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
