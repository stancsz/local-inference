"""Opt-in, single-attempt local Qwen code recovery; never a campaign reroll."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'http://127.0.0.1:8090'
MODEL = 'qwen3.8-27b'
CASES = {
    'engineering': ('evidence/stress-sessions/opencode-engineering-r2/task.py', 'tests/test_engineering_recovery.py'),
    'migration': ('evidence/stress-sessions/opencode-migration-r0/task.py', 'tests/test_migration_recovery.py'),
    'expenses': ('evidence/stress-failures/opencode-expenses-r1/workspace-task.py.gz', 'tests/test_expense_recovery.py'),
}
CONTRACTS = {
    'engineering': 'Repair clamp, clamp_all and clamp_report. Inclusive defaults lower=0,upper=100. Values and both bounds must be int/float excluding bool; reject invalid types with TypeError, nonfinite floats or reversed bounds with ValueError. Validate both bounds even for empty input. Integers of arbitrary size are finite. Preserve order, generators, nonmutation, report count/min/max/sum; valid empty report is 0/None/None/0.',
    'migration': "Repair normalize_settings(mapping) and migrate_many(iterable). Only keys name,timeout_ms,timeout_seconds,retries. Missing defaults name='default',timeout_seconds=30,retries=0; explicit None is invalid. Strip string names; empty uses default. Milliseconds nonnegative int excluding bool divided by1000. Seconds nonnegative finite int/float excluding bool. Integers of arbitrary size are finite. Reject conflicting unit keys even if equal or None, unknown keys, invalid values. Retries nonnegative int excluding bool. Invalid types TypeError; negative/nonfinite/conflicting/unknown ValueError. Preserve inputs, idempotency, generator order and independent dictionaries.",
    'expenses': 'Repair expense_totals(csv_text) and expense_report(csv_text). CSV requires unique category,amount headers; optional currency; reject missing/extra cells, malformed/nonfinite amounts, mixed nonblank currencies with ValueError. Skip genuinely blank lines only; delimited empty records are invalid. Decimal arithmetic: aggregate before quantizing to0.01 HALF_EVEN. Strip category whitespace, group case-insensitively preserving first spelling/order. Refunds negative allowed. Quoted comma categories supported. Report totals, grand_total as Decimal to two decimals, count of nonblank records. Preserve inputs.',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def native_acceptance(events, workspace, before, after, code, timed_out, marker):
    """Fail closed on terminal, native tool completion, scope and byte evidence."""
    expected = (Path(workspace) / 'task.py').resolve()
    calls, results, failures = {}, {}, []
    terminal = False
    for event in events:
        message = event.get('message')
        content = message.get('content') if isinstance(message, dict) else None
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use':
                name, arguments = block.get('name'), block.get('input', {})
                raw = arguments.get('file_path', '')
                path = Path(raw)
                path = path.resolve() if path.is_absolute() else (Path(workspace) / path).resolve()
                allowed = name in ('Read', 'Edit') and path == expected
                if not allowed:
                    failures.append('unexpected native tool or file path')
                calls[block['id']] = (name, allowed, arguments)
            elif block.get('type') == 'tool_result':
                results[block['tool_use_id']] = not block.get('is_error', False) and '<tool_use_error>' not in str(block.get('content', ''))
        if event.get('type') == 'result':
            terminal = event.get('subtype') == 'success' and not event.get('is_error', True) and marker in event.get('result', '')
    completed = {name for key, (name, allowed, _) in calls.items() if allowed and results.get(key)}
    reconstructed = before.decode('utf-8').replace('\r\n', '\n')
    for key, (name, allowed, arguments) in calls.items():
        if name == 'Edit' and allowed and results.get(key):
            old, new = arguments.get('old_string', ''), arguments.get('new_string', '')
            if not old or old not in reconstructed:
                failures.append('native edit does not match prior source')
                break
            reconstructed = reconstructed.replace(old, new, -1 if arguments.get('replace_all') else 1)
    reconstruction_matches = reconstructed == after.decode('utf-8').replace('\r\n', '\n')
    if not reconstruction_matches: failures.append('source differs from completed native edits')
    if timed_out: failures.append('host timeout')
    if code != 0: failures.append('nonzero CLI exit')
    if not terminal: failures.append('no successful terminal marker')
    if not {'Read', 'Edit'} <= completed: failures.append('missing completed native Read/Edit')
    if any(not results.get(key) for key in calls): failures.append('incomplete or failed native tool')
    if before == after: failures.append('generated source unchanged')
    return {'passed': not failures, 'failures': failures, 'completed_tools': sorted(completed), 'terminal': terminal, 'native_edit_reconstruction_matches': reconstruction_matches}


def checked_process(args, *, cwd, env=None, prompt=None, timeout=60):
    start = time.monotonic()
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        child = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.PIPE if prompt is not None else subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        timed_out = False
        try:
            child.communicate(None if prompt is None else prompt.encode('utf-8'), timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
            else:
                child.kill()
            child.wait(timeout=20)
        stdout.seek(0)
        stderr.seek(0)
        return {'exit_code': child.returncode, 'timed_out': timed_out, 'elapsed_seconds': time.monotonic() - start}, stdout.read(), stderr.read()


def validate(task, candidate, folder):
    """Run frozen behavior checks and the full matching regression module."""
    helper = "import sys;sys.path.insert(0,sys.argv[1]);from recovery.check_fixture import check_fixture;import json;r=check_fixture(sys.argv[2],sys.argv[3]);print(json.dumps(r));raise SystemExit(0 if r['passed'] else 1)"
    # -I excludes user site; explicitly add only pytest's installed site here.
    import pytest
    pytest_site = str(Path(pytest.__file__).resolve().parents[1])
    driver = """import sys,importlib.util
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import pytest
p=Path(sys.argv[2]);name=p.stem
spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec)
sys.modules[name]=m;spec.loader.exec_module(m);m.CANDIDATE_PATH=Path(sys.argv[3])
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider',str(p),'--import-mode=prepend']))
"""
    commands = {
        'behavior': [sys.executable, '-I', '-B', '-c', helper, str(ROOT), task, str(candidate)],
        'regressions': [sys.executable, '-I', '-B', '-c', driver, pytest_site, str(ROOT / CASES[task][1]), str(candidate)],
    }
    results = {}
    for name, command in commands.items():
        result, out, err = checked_process(command, cwd=folder, timeout=60)
        (folder / (name + '.stdout')).write_bytes(out)
        (folder / (name + '.stderr')).write_bytes(err)
        results[name] = {**result, 'passed': result['exit_code'] == 0 and not result['timed_out'], 'command': command}
    return results


def protected_hashes():
    paths = ['app/budget.py', 'app/gateway.py', 'gateway.yaml', 'stress/cli_acceptance.py', 'stress/cli_campaign.py', 'stress/acceptance_tasks.py', 'stress/contract_probe.py', 'recovery/check_fixture.py', 'evidence/stress-campaign.json']
    paths += [p for pair in CASES.values() for p in pair]
    return {path: sha((ROOT / path).read_bytes()) for path in paths}


def run(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    initial = protected_hashes()
    dump(output / 'protected-before.json', initial)
    sys.path.insert(0, str(ROOT / 'scripts'))
    from setup_env import gateway_key
    key = gateway_key()
    cases = []
    for task, (baseline_path, _) in CASES.items():
        folder = output / task
        folder.mkdir()
        raw = (ROOT / baseline_path).read_bytes()
        source = gzip.decompress(raw) if baseline_path.endswith('.gz') else raw
        candidate = folder / 'task.py'
        candidate.write_bytes(source)
        (folder / 'baseline.py').write_bytes(source)
        marker = 'RECOVERY_' + task.upper() + '_DONE'
        prompt = CONTRACTS[task] + '\nUse Read and Edit on task.py only in this workspace. Repair the code in place, using pure stdlib. Do not read other files or use other tools. End with ' + marker
        (folder / 'prompt.txt').write_text(prompt, encoding='utf-8')
        receipt = {'task': task, 'endpoint': ENDPOINT, 'model': MODEL, 'baseline_sha256': sha(source), 'qualifying_session_increment': 0, 'passed': False}
        try:
            with tempfile.TemporaryDirectory(prefix='qwen-generation-recovery-') as config:
                env = {n: v for n, v in os.environ.items() if not n.endswith(('_KEY', '_TOKEN', '_KEY_ID'))}
                env.pop('CLAUDECODE', None)
                env.update(ANTHROPIC_API_KEY=key, ANTHROPIC_BASE_URL=ENDPOINT, ANTHROPIC_MODEL=MODEL,
                    ANTHROPIC_DEFAULT_OPUS_MODEL=MODEL, ANTHROPIC_DEFAULT_SONNET_MODEL=MODEL, ANTHROPIC_DEFAULT_HAIKU_MODEL=MODEL,
                    CLAUDE_CONFIG_DIR=config, CLAUDE_CODE_DISABLE_1M_CONTEXT='1', CLAUDE_CODE_MAX_CONTEXT_TOKENS='1000000',
                    CLAUDE_CODE_MAX_OUTPUT_TOKENS='4096', CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1', API_TIMEOUT_MS='180000')
                args = ['claude.cmd', '--bare', '-p', '--model', MODEL, '--output-format', 'stream-json', '--verbose', '--max-turns', '12', '--permission-mode', 'acceptEdits', '--tools', 'Read,Edit', '--allowedTools', 'Read,Edit']
                process, out, err = checked_process(args, cwd=folder, env=env, prompt=prompt, timeout=240)
            assert key.encode() not in out + err, 'credential appeared in CLI output'
            (folder / 'native.jsonl').write_bytes(out)
            (folder / 'native.stderr').write_bytes(err)
            events = [json.loads(line) for line in out.decode('utf-8').splitlines() if line.strip()]
            after = candidate.read_bytes()
            receipt.update(process=process, generated_sha256=sha(after), native=native_acceptance(events, folder, source, after, process['exit_code'], process['timed_out'], marker))
            before_validation = protected_hashes()
            receipt['validation'] = validate(task, candidate, folder)
            receipt['generated_unchanged_during_validation'] = candidate.read_bytes() == after
            receipt['protected_unchanged'] = initial == before_validation == protected_hashes()
            receipt['passed'] = receipt['native']['passed'] and all(r['passed'] for r in receipt['validation'].values()) and receipt['protected_unchanged'] and receipt['generated_unchanged_during_validation']
        except Exception as error:
            # Record execution/parse errors as failures, never discard attempts.
            receipt['error'] = type(error).__name__ + ': ' + str(error).replace(key, '[REDACTED]')
            receipt['generated_sha256'] = sha(candidate.read_bytes())
        dump(folder / 'result.json', receipt)
        cases.append(receipt)
        print(task + ': ' + ('PASS' if receipt['passed'] else 'FAIL'), flush=True)
    final = protected_hashes()
    dump(output / 'protected-after.json', final)
    summary = {'version': 1, 'diagnostic_recovery': True, 'cases': cases, 'passed': all(c['passed'] for c in cases) and initial == final,
        'protected_unchanged': initial == final, 'qualifying_session_increment': 0, 'qualifying_sessions': 19, 'required_sessions': 21,
        'shortfall': 2, 'full_goal_complete': False, 'limits': 'Three single-attempt prompted repairs, no long-history injection or long-session qualification; no general quality, security or final independent acceptance claim.'}
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
