"""Bounded, feedback-driven local Qwen recovery harness v2; never a campaign reroll.

This is a SEPARATE harness.  It reuses the v1 primitives (ROOT, CASES, CONTRACTS,
sha, dump, validate, protected_hashes, checked_process, native_acceptance) without
modifying recovery/generation_v1.py, and it starts from the preserved v1 GENERATED
artifacts (evidence/generation-recovery-v1/<task>/task.py) rather than from
corrected fixtures.

Differences from v1:
  * the contract prompt explicitly states the shapes the v1 runs got wrong
    (migrate_many must return a list, expense_report must return
    {'totals': dict, 'grand_total': Decimal, 'count': int}, expenses CSV has two
    required columns plus an optional currency column, empty input still
    validates bounds, None is invalid rather than absent);
  * every case runs in ONE persistent Claude session (--resume <exact sid>) with
    at most three predeclared native user repair turns;
  * each later prompt carries the REAL prior test stdout/stderr and explicit
    failure counts (never fabricated, never a reference implementation);
  * a plan.json is predeclared before any inference happens.

Qualification: no attempt here replaces campaign 19/21.  qualifying session
increment is 0 and full goal complete is False.
"""
import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from recovery import generation_v1 as v1  # noqa: E402  (path bootstrap above)

# Reused v1 primitives.
ROOT = v1.ROOT
CASES = v1.CASES
CONTRACTS = v1.CONTRACTS
sha = v1.sha
dump = v1.dump
validate = v1.validate
protected_hashes = v1.protected_hashes
checked_process = v1.checked_process
native_acceptance = v1.native_acceptance

ENDPOINT = 'http://127.0.0.1:8090'
MODEL = 'qwen3.8-27b'
ENDPOINT_EXACT = '8090/qwen3.8-27b'

CASE_ORDER = ('engineering', 'migration', 'expenses')
V1_EVIDENCE = ROOT / 'evidence' / 'generation-recovery-v1'
BASELINES = {task: V1_EVIDENCE / task / 'task.py' for task in CASE_ORDER}

MAX_REPAIR_TURNS = 3
MAX_TURNS_PER_INVOCATION = 12
INVOCATION_TIMEOUT_SECONDS = 240
FEEDBACK_LIMIT = 18000
RETRIES = 0

TERMINAL_REASONS = ('cli_failure', 'parse_failure', 'session_failure', 'protected_source_failure', 'native_failure', 'artifact_integrity_failure')

PROMPT_CLARIFICATIONS = {
    'engineering': (
        'CLARIFICATIONS (must hold exactly): both bounds are validated even when the input '
        'collection is EMPTY; an empty input still raises ValueError for reversed bounds and '
        'TypeError for invalid bound types; None is an INVALID value, not an absent optional '
        'value; a valid empty report is count 0, min None, max None, sum 0.'
    ),
    'migration': (
        'CLARIFICATIONS (must hold exactly): migrate_many(iterable) must return a concrete LIST '
        'of dictionaries, never a generator or iterator; explicit None values are INVALID, not '
        'absent; reject conflicting unit keys even when both are equal or None; keep input '
        'dictionaries unmutated and return independent dictionaries.'
    ),
    'expenses': (
        'CLARIFICATIONS (must hold exactly): the CSV header has TWO required columns, category '
        'and amount, plus an OPTIONAL third currency column; expense_report(csv_text) must '
        "return a dict with exactly the keys 'totals' (a dict mapping category to Decimal), "
        "'grand_total' (a Decimal quantized to two decimals) and 'count' (an int of nonblank "
        'records) - not a flattened report and not a tuple; aggregate before quantizing to '
        '0.01 with ROUND_HALF_EVEN.'
    ),
}

WORKSPACE_RULES = (
    'WORKSPACE RULES: use only the native Read and Edit tools and only on task.py in this '
    'workspace; use pure stdlib; do not read any other file and do not run commands; edit the '
    'existing file in place with Edit (Read task.py first); never write a brand new file.'
)


# --------------------------------------------------------------------------
# Pure helpers: feedback construction, prompt clarification, session validation
# --------------------------------------------------------------------------

def truncate_text(text, limit):
    """Return (bounded_text, truncated). Never raises; text may be None."""
    text = '' if text is None else str(text)
    limit = int(limit)
    if limit <= 0:
        return '', bool(text)
    if len(text) <= limit:
        return text, False
    return text[:limit] + '\n...[TRUNCATED]', True


def summarize_behavior(stdout):
    """Explicit failure counts from the unchanged behavior check output, or None."""
    try:
        data = json.loads(stdout)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    stages = data.get('behavior_stages')
    probes = data.get('additional_probes')
    if not isinstance(stages, list) or not isinstance(probes, list):
        return None
    return {
        'stages_total': len(stages),
        'stages_failed': sum(1 for s in stages if isinstance(s, dict) and not s.get('passed')),
        'probes_total': len(probes),
        'probes_failed': sum(1 for p in probes if isinstance(p, dict) and not p.get('passed')),
    }


def summarize_regressions(stdout):
    """Explicit failure counts from pytest output, or None when unparseable."""
    if not isinstance(stdout, str):
        return None
    failed = re.search(r'(\d+) failed', stdout)
    passed = re.search(r'(\d+) passed', stdout)
    if not failed and not passed:
        return None
    return {
        'tests_failed': int(failed.group(1)) if failed else 0,
        'tests_passed': int(passed.group(1)) if passed else 0,
    }


def summarize_failures(behavior_stdout, regressions_stdout):
    """Total explicit failure counts; None when a section cannot be parsed."""
    behavior = summarize_behavior(behavior_stdout)
    regressions = summarize_regressions(regressions_stdout)
    total = None
    if behavior is not None and regressions is not None:
        total = behavior['stages_failed'] + behavior['probes_failed'] + regressions['tests_failed']
    return {'behavior': behavior, 'regressions': regressions, 'total_failures': total}


def _record_counts(record):
    """Explicit counts for one validation record (behavior stdout + regression stdout)."""
    return summarize_failures(record.get('behavior_stdout', record.get('stdout', '')),
                              record.get('regression_stdout', ''))


def build_feedback(records, limit=FEEDBACK_LIMIT):
    """Build bounded, REAL feedback text from actual validation records.

    ``records`` is a list of dicts with keys: label, passed, behavior_stdout,
    regression_stdout, behavior_stderr, regression_stderr.  The header with the
    explicit failure counts is always retained, even when the body is truncated.
    """
    records = list(records or [])
    header_lines = ['PRIOR ACTUAL TEST FEEDBACK (real runs of this workspace, not examples):']
    for record in records:
        counts = _record_counts(record)
        behavior = counts['behavior']
        regressions = counts['regressions']
        if behavior is None:
            behavior_text = 'behavior counts unavailable'
        else:
            behavior_text = ('behavior stages failed %d/%d, probes failed %d/%d'
                             % (behavior['stages_failed'], behavior['stages_total'],
                                behavior['probes_failed'], behavior['probes_total']))
        if regressions is None:
            regression_text = 'regression counts unavailable'
        else:
            regression_text = 'regression tests failed %d, passed %d' % (
                regressions['tests_failed'], regressions['tests_passed'])
        if counts['total_failures'] is None:
            total_text = 'total failures unknown'
        else:
            total_text = 'total failures %d' % counts['total_failures']
        header_lines.append('- %s: %s; %s; %s' % (
            record.get('label', 'run'),
            'PASSED' if record.get('passed') else 'FAILED',
            behavior_text, regression_text))
        header_lines.append('  ' + total_text)
    header = '\n'.join(header_lines) + '\n'

    sections = []
    for record in records:
        section = '===== %s =====\n' % record.get('label', 'run')
        for name, key in (('behavior stdout', 'behavior_stdout'), ('regression stdout', 'regression_stdout'),
                          ('behavior stderr', 'behavior_stderr'), ('regression stderr', 'regression_stderr')):
            body = record.get(key)
            if body:
                section += '--- %s ---\n%s\n' % (name, body)
        sections.append(section)

    body_text = '\n'.join(sections)
    full = header + body_text
    if len(full) <= limit:
        return full
    # Keep the header (explicit counts) and fill the remainder with real output.
    remaining = max(0, limit - len(header))
    kept = []
    for section in sections:
        if remaining <= 0:
            break
        if len(section) <= remaining:
            kept.append(section)
            remaining -= len(section)
        else:
            bounded, _ = truncate_text(section, remaining)
            kept.append(bounded)
            remaining = 0
    text = header + '\n'.join(kept)
    if len(text) > limit:
        # Truncate from the tail so the explicit counts in the header survive.
        text = text[:limit]
    return text


def build_prompt(task, turn, feedback, marker):
    """Build one prompt: contract + explicit clarification + real feedback + marker."""
    parts = [CONTRACTS[task], PROMPT_CLARIFICATIONS[task], WORKSPACE_RULES]
    if feedback:
        parts.append(feedback)
    parts.append('This is repair turn %d. Make the edits that fix the failures above, then end '
                 'your reply with the exact marker %s.' % (turn, marker))
    return '\n\n'.join(parts) + '\n'


def extract_session_id(text):
    """Require an init ID and consistent terminal IDs."""
    if not isinstance(text, str):
        return None
    ids, initialized = set(), False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue
        if not isinstance(event, dict):
            continue
        initial = event.get('type') == 'system' and event.get('subtype') == 'init'
        if initial or event.get('type') == 'result':
            sid = event.get('session_id')
            if isinstance(sid, str) and sid:
                ids.add(sid)
                initialized = initialized or initial
    return next(iter(ids)) if initialized and len(ids) == 1 else None


def validate_session(requested, observed, turn):
    """Fail closed on a missing or mismatched session id."""
    if not observed:
        return {'ok': False, 'reason': 'session_id_missing', 'session_id': None}
    if turn > 1 and not requested:
        return {'ok': False, 'reason': 'resume_id_missing', 'session_id': observed}
    if requested is None:
        return {'ok': True, 'reason': 'initial_session', 'session_id': observed}
    if observed != requested:
        return {'ok': False, 'reason': 'session_id_mismatch', 'session_id': observed}
    return {'ok': True, 'reason': 'resumed_session', 'session_id': observed}


def make_plan():
    """The predeclared plan; written to plan.json BEFORE any inference."""
    return {
        'version': 2,
        'harness': 'recovery/generation_feedback_v2.py',
        'endpoint': ENDPOINT,
        'endpoint_exact': ENDPOINT_EXACT,
        'model': MODEL,
        'case_order': list(CASE_ORDER),
        'baselines': {task: str(BASELINES[task].relative_to(ROOT)).replace('\\', '/') for task in CASE_ORDER},
        'max_repair_turns_per_case': MAX_REPAIR_TURNS,
        'max_turns_per_invocation': MAX_TURNS_PER_INVOCATION,
        'invocation_timeout_seconds': INVOCATION_TIMEOUT_SECONDS,
        'retries': RETRIES,
        'feedback_char_limit': FEEDBACK_LIMIT,
        'session_policy': 'one persistent session per case; --resume <exact session id> on later turns',
        'terminal_failure_reasons': list(TERMINAL_REASONS),
        'qualifying_session_increment': 0,
        'qualifying_sessions': 19,
        'required_sessions': 21,
        'shortfall': 2,
        'full_goal_complete': False,
        'limits': 'Bounded local diagnostic recovery; does not replace campaign 19/21 and makes no '
                  'general quality, security or final independent acceptance claim.',
    }


def classify_turn(process, parsed, session_ok, protected_ok, native, validation, generated_ok=True):
    """Decide pass / continue / terminal for one turn using predeclared rules."""
    failures = []
    if not process.get('exit_code') == 0 or process.get('timed_out'):
        failures.append('cli_failure')
    if not parsed:
        failures.append('parse_failure')
    if not session_ok:
        failures.append('session_failure')
    if not protected_ok:
        failures.append('protected_source_failure')
    native_passed = bool(native.get('passed')) if isinstance(native, dict) else False
    if not native_passed:
        failures.append('native_failure')
    if not generated_ok:
        failures.append('artifact_integrity_failure')
    validation_passed = bool(validation) and all(r.get('passed') for r in validation.values())
    terminal = [f for f in failures if f in TERMINAL_REASONS]
    return {
        'passed': native_passed and validation_passed and not failures,
        'continue_allowed': not terminal,
        'terminal_reason': terminal[0] if terminal else None,
        'failures': failures,
        'native_passed': native_passed,
        'validation_passed': validation_passed,
    }


def cli_args(session_id):
    args = ['claude.cmd', '--bare', '-p']
    if session_id:
        args += ['--resume', session_id]
    args += ['--model', MODEL, '--output-format', 'stream-json', '--verbose',
             '--max-turns', str(MAX_TURNS_PER_INVOCATION), '--permission-mode', 'acceptEdits',
             '--tools', 'Read,Edit', '--allowedTools', 'Read,Edit']
    return args


def build_env(config_dir, key):
    env = {n: v for n, v in os.environ.items() if not n.endswith(('_KEY', '_TOKEN', '_KEY_ID'))}
    env.pop('CLAUDECODE', None)
    env.update(ANTHROPIC_API_KEY=key, ANTHROPIC_BASE_URL=ENDPOINT, ANTHROPIC_MODEL=MODEL,
               ANTHROPIC_DEFAULT_OPUS_MODEL=MODEL, ANTHROPIC_DEFAULT_SONNET_MODEL=MODEL,
               ANTHROPIC_DEFAULT_HAIKU_MODEL=MODEL, CLAUDE_CONFIG_DIR=config_dir,
               CLAUDE_CODE_DISABLE_1M_CONTEXT='1', CLAUDE_CODE_MAX_CONTEXT_TOKENS='1000000',
               CLAUDE_CODE_MAX_OUTPUT_TOKENS='4096', CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1',
               API_TIMEOUT_MS='180000')
    return env


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------

def read_text(path):
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace')
    except Exception:
        return ''


def _run_case(task, output, key, initial_protected):
    folder = output / task
    folder.mkdir(parents=True, exist_ok=False)
    source = BASELINES[task].read_bytes()
    candidate = folder / 'task.py'
    candidate.write_bytes(source)
    (folder / 'baseline.py').write_bytes(source)
    marker = 'RECOVERY_' + task.upper() + '_DONE'

    receipt = {
        'task': task, 'endpoint': ENDPOINT, 'endpoint_exact': ENDPOINT_EXACT, 'model': MODEL,
        'baseline_sha256': sha(source), 'baseline_source': str(BASELINES[task].relative_to(ROOT)).replace('\\', '/'),
        'qualifying_session_increment': 0, 'max_repair_turns': MAX_REPAIR_TURNS, 'turns': [],
        'passed': False, 'terminal_reason': None,
    }

    # Baseline validation with the UNCHANGED validate(); real output, no fabrication.
    baseline_folder = folder / 'baseline-validation'
    baseline_folder.mkdir()
    baseline_validation = validate(task, candidate, baseline_folder)
    receipt['baseline_validation'] = baseline_validation
    dump(folder / 'baseline-validation.json', baseline_validation)

    def record_for(label, folder_path, results):
        return {
            'label': label,
            'passed': bool(results) and all(r.get('passed') for r in results.values()),
            'behavior_stdout': read_text(folder_path / 'behavior.stdout'),
            'behavior_stderr': read_text(folder_path / 'behavior.stderr'),
            'regression_stdout': read_text(folder_path / 'regressions.stdout'),
            'regression_stderr': read_text(folder_path / 'regressions.stderr'),
        }

    feedback = build_feedback([record_for('baseline', baseline_folder, baseline_validation)])

    with tempfile.TemporaryDirectory(prefix='qwen-generation-v2-' + task + '-') as config:
        env = build_env(config, key)
        session_id = None
        for turn in range(1, MAX_REPAIR_TURNS + 1):
            before_bytes = candidate.read_bytes()
            (folder / ('revision-%d-before.py' % turn)).write_bytes(before_bytes)
            prompt = build_prompt(task, turn, feedback, marker)
            (folder / ('prompt-%d.txt' % turn)).write_bytes(prompt.encode('utf-8'))

            process, out, err = checked_process(cli_args(session_id), cwd=folder, env=env, prompt=prompt,
                                                 timeout=INVOCATION_TIMEOUT_SECONDS)
            exposed = key.encode() in out + err
            (folder / ('stdout-%d.txt' % turn)).write_bytes(out.replace(key.encode(), b'[REDACTED]'))
            (folder / ('stderr-%d.txt' % turn)).write_bytes(err.replace(key.encode(), b'[REDACTED]'))
            after_bytes = candidate.read_bytes()
            (folder / ('revision-%d-after.py' % turn)).write_bytes(after_bytes)

            turn_receipt = {
                'turn': turn, 'session_id_requested': session_id,
                'process': {**process, 'command': cli_args(session_id)},
                'prompt_sha256': sha(prompt.encode('utf-8')),
                'before_sha256': sha(before_bytes), 'after_sha256': sha(after_bytes),
            }
            try:
                assert not exposed, 'credential appeared in CLI output; stored trace redacted'
            except AssertionError as error:
                turn_receipt['error'] = str(error)
                dump(folder / ('receipt-%d.json' % turn), turn_receipt)
                receipt['turns'].append(turn_receipt)
                receipt['terminal_reason'] = 'cli_failure'
                break

            events, parsed = [], True
            for line in out.decode('utf-8', errors='replace').splitlines():
                if not line.strip():
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    parsed = False
                    break

            observed = extract_session_id(out.decode('utf-8', errors='replace'))
            session = validate_session(session_id, observed, turn)
            turn_receipt['session_id_observed'] = observed
            turn_receipt['session'] = session
            if session['ok']:
                session_id = session['session_id']

            native = native_acceptance(events, folder, before_bytes, after_bytes,
                                       process['exit_code'], process['timed_out'], marker)
            turn_receipt['native'] = native

            protected_after = protected_hashes()
            protected_ok = initial_protected == protected_after
            turn_receipt['protected_unchanged'] = protected_ok

            turn_folder = folder / ('turn-%d' % turn)
            turn_folder.mkdir()
            validation = validate(task, candidate, turn_folder)
            turn_receipt['validation'] = validation
            turn_receipt['generated_unchanged_during_validation'] = candidate.read_bytes() == after_bytes
            protected_ok = initial_protected == protected_hashes()
            turn_receipt['protected_unchanged'] = protected_ok
            dump(folder / ('turn-%d-validation.json' % turn), validation)

            verdict = classify_turn(process, parsed, session['ok'], protected_ok, native, validation,
                                    turn_receipt['generated_unchanged_during_validation'])
            turn_receipt['verdict'] = verdict
            dump(folder / ('receipt-%d.json' % turn), turn_receipt)
            receipt['turns'].append(turn_receipt)

            if verdict['passed']:
                receipt['passed'] = True
                break
            if not verdict['continue_allowed']:
                receipt['terminal_reason'] = verdict['terminal_reason']
                break
            # Only validation failures allow the next PREDECLARED turn.
            feedback = build_feedback([record_for('turn-%d' % turn, turn_folder, validation)])
        else:
            receipt['terminal_reason'] = receipt['terminal_reason'] or 'turn_budget_exhausted'

    if not receipt['passed']:
        receipt['failure_receipt'] = {
            'task': task,
            'terminal_reason': receipt['terminal_reason'],
            'turns_run': len(receipt['turns']),
            'failure_details': [
                {'turn': t['turn'], 'verdict': t.get('verdict'), 'native_failures': (t.get('native') or {}).get('failures'),
                 'validation': {k: v.get('passed') for k, v in (t.get('validation') or {}).items()}}
                for t in receipt['turns']
            ],
        }
        dump(folder / 'failure.json', receipt['failure_receipt'])
    dump(folder / 'result.json', receipt)
    return receipt


def run_case(task, output, key, initial_protected):
    """Preserve exceptions and let independent cases proceed."""
    try:
        return _run_case(task, output, key, initial_protected)
    except Exception as error:
        folder = output / task
        folder.mkdir(parents=True, exist_ok=True)
        candidate = folder / 'task.py'
        if candidate.exists():
            for before in folder.glob('revision-*-before.py'):
                after = before.with_name(before.name.replace('-before.py', '-after.py'))
                if not after.exists():
                    after.write_bytes(candidate.read_bytes())
        partial = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('receipt-*.json'))]
        receipt = {'task': task, 'passed': False, 'turns': partial, 'qualifying_session_increment': 0,
                   'terminal_reason': 'execution_exception',
                   'error': type(error).__name__ + ': ' + str(error).replace(key, '[REDACTED]')}
        dump(folder / 'failure.json', receipt)
        dump(folder / 'result.json', receipt)
        return receipt


def run(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)  # must be fresh
    initial = protected_hashes()
    dump(output / 'protected-before.json', initial)
    plan = make_plan()
    dump(output / 'plan.json', plan)  # predeclared BEFORE any inference

    sys.path.insert(0, str(ROOT / 'scripts'))
    from setup_env import gateway_key
    key = gateway_key()

    cases = []
    for task in CASE_ORDER:
        receipt = run_case(task, output, key, initial)
        cases.append(receipt)
        print(task + ': ' + ('PASS' if receipt['passed'] else 'FAIL'), flush=True)

    final = protected_hashes()
    dump(output / 'protected-after.json', final)
    summary = {
        'version': 2,
        'diagnostic_recovery': True,
        'plan': plan,
        'cases': cases,
        'passed': all(c['passed'] for c in cases) and initial == final,
        'protected_unchanged': initial == final,
        'qualifying_session_increment': 0,
        'qualifying_sessions': 19,
        'required_sessions': 21,
        'shortfall': 2,
        'full_goal_complete': False,
        'limits': plan['limits'],
    }
    dump(output / 'result.json', summary)
    print(str(output / 'result.json'), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    return 0 if run(args.output_dir)['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
