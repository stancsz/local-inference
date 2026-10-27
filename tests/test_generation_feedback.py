"""Focused policy checks for the bounded v2 feedback harness (no inference launched)."""
import json
from pathlib import Path

import pytest

from recovery.generation_feedback_v2 import (
    BASELINES,
    CASE_ORDER,
    FEEDBACK_LIMIT,
    INVOCATION_TIMEOUT_SECONDS,
    MAX_REPAIR_TURNS,
    MAX_TURNS_PER_INVOCATION,
    build_feedback,
    build_prompt,
    classify_turn,
    extract_session_id,
    make_plan,
    summarize_behavior,
    summarize_failures,
    summarize_regressions,
    truncate_text,
    validate_session,
)
from recovery.generation_v1 import CONTRACTS


def behavior_json(failed_stages=1, failed_probes=2):
    return json.dumps({
        'behavior_stages': [{'stage': i, 'passed': i > failed_stages} for i in range(1, 10)],
        'additional_probes': [{'name': 'p%d' % i, 'passed': i > failed_probes} for i in range(1, 5)],
    })


def record(label='turn-1', behavior=behavior_json(), regression='3 failed, 5 passed', passed=False):
    return {
        'label': label,
        'passed': passed,
        'behavior_stdout': behavior,
        'behavior_stderr': 'traceback text',
        'regression_stdout': regression,
        'regression_stderr': '',
    }


def test_truncate_text_bounds_and_flags():
    assert truncate_text('abcdef', 10) == ('abcdef', False)
    text, truncated = truncate_text('abcdef', 3)
    assert text.startswith('abc') and truncated and 'TRUNCATED' in text
    assert truncate_text('', 5) == ('', False)
    assert truncate_text('x', 0) == ('', True)


def test_feedback_counts_are_explicit_and_retained_under_truncation():
    feedback = build_feedback([record()], limit=FEEDBACK_LIMIT)
    assert 'behavior stages failed 1/9' in feedback
    assert 'probes failed 2/4' in feedback
    assert 'regression tests failed 3' in feedback
    assert 'total failures 6' in feedback
    assert 'traceback text' in feedback

    tiny = build_feedback([record()], limit=200)
    assert len(tiny) <= 200
    assert 'total failures 6' in tiny  # explicit counts survive truncation


def test_feedback_retains_real_output_and_reports_unparseable_counts():
    feedback = build_feedback([record(behavior='not json', regression='no tests ran')], limit=4000)
    assert 'behavior counts unavailable' in feedback
    assert 'total failures unknown' in feedback
    assert 'not json' in feedback


def test_summarize_helpers():
    assert summarize_behavior('not json') is None
    assert summarize_behavior(behavior_json())['stages_failed'] == 1
    assert summarize_regressions('2 failed, 1 passed') == {'tests_failed': 2, 'tests_passed': 1}
    assert summarize_regressions('nothing here') is None
    counts = summarize_failures(behavior_json(), '1 failed')
    assert counts['total_failures'] == 1 + 2 + 1


def test_session_validation_consistent_resume_missing_and_mismatched():
    assert validate_session(None, 'sid-1', 1)['ok']
    assert validate_session('sid-1', 'sid-1', 2)['ok']
    assert validate_session('sid-1', 'sid-1', 2)['reason'] == 'resumed_session'
    missing = validate_session('sid-1', None, 2)
    assert not missing['ok'] and missing['reason'] == 'session_id_missing'
    mismatch = validate_session('sid-1', 'sid-2', 2)
    assert not mismatch['ok'] and mismatch['reason'] == 'session_id_mismatch'


def test_extract_session_id_reads_init_event():
    events = [{'type': 'system', 'subtype': 'init', 'session_id': 'abc'},
              {'type': 'result', 'subtype': 'success'}]
    assert extract_session_id('\n'.join(json.dumps(e) for e in events)) == 'abc'
    assert extract_session_id('{"type":"result"}') is None
    assert extract_session_id('not json') is None


def test_plan_is_bounded_and_predeclared():
    plan = make_plan()
    assert plan['case_order'] == ['engineering', 'migration', 'expenses']
    assert plan['max_repair_turns_per_case'] == MAX_REPAIR_TURNS == 3
    assert plan['max_turns_per_invocation'] == MAX_TURNS_PER_INVOCATION == 12
    assert plan['invocation_timeout_seconds'] == INVOCATION_TIMEOUT_SECONDS == 240
    assert plan['retries'] == 0
    assert plan['qualifying_session_increment'] == 0
    assert plan['full_goal_complete'] is False
    assert plan['endpoint_exact'] == '8090/qwen3.8-27b'


def test_baselines_are_preserved_v1_generated_artifacts():
    assert list(CASE_ORDER) == ['engineering', 'migration', 'expenses']
    for task in CASE_ORDER:
        path = BASELINES[task]
        assert path.exists(), task
        assert path.parent.name == task
        assert 'generation-recovery-v1' in path.parts


def test_prompt_states_explicit_shapes_and_marker():
    prompt = build_prompt('migration', 2, 'PRIOR ACTUAL TEST FEEDBACK', 'RECOVERY_MIGRATION_DONE')
    assert CONTRACTS['migration'] in prompt
    assert 'must return a concrete LIST' in prompt
    assert 'PRIOR ACTUAL TEST FEEDBACK' in prompt
    assert 'RECOVERY_MIGRATION_DONE' in prompt
    expenses = build_prompt('expenses', 1, '', 'RECOVERY_EXPENSES_DONE')
    assert "'totals'" in expenses and "'grand_total'" in expenses and "'count'" in expenses
    assert 'OPTIONAL third currency column' in expenses
    engineering = build_prompt('engineering', 1, '', 'RECOVERY_ENGINEERING_DONE')
    assert 'even when the input' in engineering


def test_classify_turn_failure_handling():
    good_process = {'exit_code': 0, 'timed_out': False}
    native = {'passed': True}
    validation = {'behavior': {'passed': True}, 'regressions': {'passed': True}}
    ok = classify_turn(good_process, True, True, True, native, validation)
    assert ok['passed'] and ok['continue_allowed']

    failing_validation = classify_turn(good_process, True, True, True, native, {'behavior': {'passed': False}})
    assert not failing_validation['passed']
    assert failing_validation['continue_allowed']  # validation failure allows next turn

    for process, parsed, session_ok, protected_ok, reason in [
        ({'exit_code': 1, 'timed_out': False}, True, True, True, 'cli_failure'),
        (good_process, False, True, True, 'parse_failure'),
        (good_process, True, False, True, 'session_failure'),
        (good_process, True, True, False, 'protected_source_failure'),
    ]:
        verdict = classify_turn(process, parsed, session_ok, protected_ok, native, validation)
        assert not verdict['passed']
        assert not verdict['continue_allowed']
        assert verdict['terminal_reason'] == reason


def test_import_does_not_launch_inference(tmp_path):
    import recovery.generation_feedback_v2 as harness
    assert callable(harness.run)
    assert harness.RETRIES == 0
    assert not (tmp_path / 'result.json').exists()


def test_validate_is_unchanged_and_fails_closed_on_preserved_artifact(tmp_path):
    from recovery.generation_v1 import validate
    candidate = tmp_path / 'task.py'
    candidate.write_bytes(BASELINES['expenses'].read_bytes())
    original = BASELINES['expenses'].read_bytes()
    results = validate('expenses', candidate, tmp_path)
    assert not results['regressions']['passed']
    assert not results['behavior']['passed']
    assert candidate.read_bytes() == original


def test_resumed_turn_cannot_silently_start_a_new_session():
    assert not validate_session(None, 'new-session', 2)['ok']


def test_conflicting_init_and_terminal_session_ids_fail_closed():
    text = '\n'.join(json.dumps(e) for e in [
        {'type': 'system', 'subtype': 'init', 'session_id': 'one'},
        {'type': 'result', 'session_id': 'two'},
    ])
    assert extract_session_id(text) is None


def test_native_scope_or_binding_failure_is_terminal():
    verdict = classify_turn({'exit_code': 0}, True, True, True, {'passed': False}, {'regressions': {'passed': False}})
    assert not verdict['passed'] and not verdict['continue_allowed']


def test_generated_mutation_during_validation_cannot_pass(tmp_path, monkeypatch):
    import recovery.generation_feedback_v2 as harness
    good = {'behavior': {'passed': True}, 'regressions': {'passed': True}}
    def fake_validate(task, candidate, folder):
        if folder.name.startswith('turn-'):
            candidate.write_text('unexpected validation-time rewrite', encoding='utf-8')
        return good
    init = json.dumps({'type': 'system', 'subtype': 'init', 'session_id': 'fixed'})
    monkeypatch.setattr(harness, 'validate', fake_validate)
    monkeypatch.setattr(harness, 'native_acceptance', lambda *a: {'passed': True})
    monkeypatch.setattr(harness, 'checked_process', lambda *a, **k: ({'exit_code': 0, 'timed_out': False}, init.encode(), b''))
    result = harness.run_case('engineering', tmp_path, 'test-only-key', harness.protected_hashes())
    assert not result['passed']
    assert result['terminal_reason'] == 'artifact_integrity_failure'


def test_process_error_is_preserved_as_case_failure(tmp_path, monkeypatch):
    import recovery.generation_feedback_v2 as harness
    monkeypatch.setattr(harness, 'checked_process', lambda *a, **k: (_ for _ in ()).throw(OSError('missing executable')))
    result = harness.run_case('engineering', tmp_path, 'test-only-key', harness.protected_hashes())
    assert not result['passed']
    assert (tmp_path / 'engineering' / 'failure.json').exists()
    assert (tmp_path / 'engineering' / 'revision-1-after.py').exists()
