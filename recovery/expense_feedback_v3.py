"""Bounded diagnostic repair of the two preserved v2 expense findings."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

from recovery.generation_v1 import ROOT, dump, sha, validate, checked_process, native_acceptance, protected_hashes
from recovery.generation_feedback_v2 import build_env, cli_args, extract_session_id, validate_session, CONTRACTS, PROMPT_CLARIFICATIONS, WORKSPACE_RULES

BASELINE = ROOT / 'evidence/feedback-recovery-v2/expenses/task.py'
PROBES = ROOT / 'evidence/feedback-recovery-v2/parent-probes.py'


def additional_checks(candidate):
    result, out, err = checked_process([sys.executable, '-I', '-B', str(PROBES), str(candidate)], cwd=ROOT, timeout=20)
    if result['exit_code'] != 0 or result['timed_out']:
        return [{'name': 'additional-check-execution', 'passed': False, 'process': result}]
    return json.loads(out)['generated']


def checks(candidate, folder):
    original = validate('expenses', candidate, folder)
    extra = additional_checks(candidate)
    dump(folder / 'additional.json', extra)
    return {'listed': original, 'additional': extra,
        'passed': all(c['passed'] for c in original.values()) and all(c['passed'] for c in extra)}


def run(output):
    # Explicit new experiment. The v2 result and all qualifying counts stay frozen.
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    baseline = BASELINE.read_bytes()
    frozen = protected_hashes()
    plan = {'version': 3, 'task_endpoint': 'http://127.0.0.1:8090', 'model': 'qwen3.8-27b',
        'baseline': str(BASELINE.relative_to(ROOT)), 'baseline_sha256': sha(baseline), 'probes_sha256': sha(PROBES.read_bytes()),
        'harness_sha256': sha(Path(__file__).read_bytes()),
        'helper_sha256': {name: sha((ROOT / name).read_bytes()) for name in ('recovery/generation_v1.py', 'recovery/generation_feedback_v2.py')},
        'maximum_repair_turns': 2, 'per_invocation_timeout_seconds': 240, 'per_invocation_model_turns': 12,
        'same_session_required': True, 'retries': 0, 'qualifying_session_increment': 0,
        'limits': 'Diagnostic experiment; neither a v2 outcome rewrite nor a replacement qualifying session.'}
    dump(output / 'plan.json', plan)
    candidate = output / 'task.py'
    candidate.write_bytes(baseline)
    (output / 'baseline.py').write_bytes(baseline)
    baseline_dir = output / 'baseline-checks'
    baseline_dir.mkdir()
    previous = checks(candidate, baseline_dir)
    dump(output / 'baseline-checks.json', previous)
    marker = 'EXPENSE_V3_DONE'
    turns, passed, sid = [], False, None
    sys.path.insert(0, str(ROOT / 'scripts'))
    from setup_env import gateway_key
    key = gateway_key()
    with tempfile.TemporaryDirectory(prefix='expense-feedback-v3-') as config:
        env = build_env(config, key)
        for number in range(1, 3):
            folder = output / f'turn-{number}'
            folder.mkdir()
            before = candidate.read_bytes()
            (folder / 'before.py').write_bytes(before)
            feedback = {'actual_validation': previous,
                'original_behavior_stdout': (baseline_dir / 'behavior.stdout').read_text(encoding='utf-8'),
                'original_regressions_stdout': (baseline_dir / 'regressions.stdout').read_text(encoding='utf-8')}
            prompt = '\n\n'.join([CONTRACTS['expenses'], PROMPT_CLARIFICATIONS['expenses'], WORKSPACE_RULES,
                'Existing requirements: compare only NONBLANK currencies globally. Blank currency cells are allowed alongside one nonblank currency in either order. Empty CSV is a missing-header error and must raise ValueError in both APIs.',
                'Actual test feedback from the current revision (no reference implementation):\n' + json.dumps(feedback, ensure_ascii=False),
                'Read task.py, repair it with Edit, preserve all other behavior. End with ' + marker])
            (folder / 'prompt.txt').write_bytes(prompt.encode('utf-8'))
            receipt = {'turn': number, 'session_requested': sid, 'passed': False, 'before_sha256': sha(before)}
            try:
                process, out, err = checked_process(cli_args(sid), cwd=output, env=env, prompt=prompt, timeout=240)
                assert key.encode() not in out + err, 'credential appeared in CLI output'
                (folder / 'native.jsonl').write_bytes(out)
                (folder / 'native.stderr').write_bytes(err)
                after = candidate.read_bytes()
                (folder / 'after.py').write_bytes(after)
                events = [json.loads(line) for line in out.decode('utf-8').splitlines() if line.strip()]
                observed = extract_session_id(out.decode('utf-8'))
                session = validate_session(sid, observed, number)
                native = native_acceptance(events, output, before, after, process['exit_code'], process['timed_out'], marker)
                receipt.update(process=process, session_observed=observed, session=session, native=native, after_sha256=sha(after))
                if not session['ok'] or not native['passed']:
                    receipt['failure'] = 'native CLI, source binding or persistent session failed'
                    dump(folder / 'result.json', receipt)
                    turns.append(receipt)
                    break
                sid = observed
                previous = checks(candidate, folder)
                intact = candidate.read_bytes() == after and protected_hashes() == frozen and BASELINE.read_bytes() == baseline and sha(PROBES.read_bytes()) == plan['probes_sha256']
                receipt.update(validation=previous, protected_and_generated_unchanged=intact, passed=previous['passed'] and intact)
                passed = receipt['passed']
                dump(folder / 'result.json', receipt)
                turns.append(receipt)
                if passed or not intact: break
                baseline_dir = folder
            except Exception as error:
                receipt['failure'] = type(error).__name__ + ': ' + str(error).replace(key, '[REDACTED]')
                (folder / 'after.py').write_bytes(candidate.read_bytes())
                dump(folder / 'result.json', receipt)
                turns.append(receipt)
                break
    result = {'version': 3, 'passed': passed, 'turns': turns, 'plan': plan, 'final_source_sha256': sha(candidate.read_bytes()),
        'qualifying_session_increment': 0, 'full_goal_complete': False,
        'limits': 'Selected unchanged regressions/behavior/probes plus the6 pre-existing parent checks, not universal model correctness or goal acceptance.'}
    dump(output / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), indent=2))


if __name__ == '__main__': main()
