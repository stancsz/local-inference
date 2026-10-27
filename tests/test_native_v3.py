"""Version 3 native evidence: generalized successful unittest recognition.

The v2 harness (frozen, sealed receipts) is never modified. These tests
prove that the v3 copy differs from v2 only in the successful unittest
recognition and that the v3 recognition is neither too permissive nor too
strict.
"""
import inspect

import pytest

from stress import cli_acceptance, native_v3
from stress.native_v3 import native_evidence, unittest_outcome


def test_windows_native_crlf_summary_is_recognized():
    assert unittest_outcome('Ran 3 tests in 0.004s\r\n\r\nOK\r\n') == {'tests':3,'skipped':0}


def command(identifier, text, output="", exit_code=0):
    return {"type": "item.completed", "item": {"id": identifier, "type": "command_execution",
            "command": text, "aggregated_output": output, "exit_code": exit_code,
            "status": "completed" if exit_code == 0 else "failed"}}


def workflow(count=2, output=None):
    """The ordinary successful native workflow with `count` public tests."""
    final = output if output is not None else f"Ran {count} tests\nOK"
    return [
        command("read", "Get-Content task.py; Get-Content test_task.py"),
        command("baseline", '"C:/Python/python.exe" -m unittest -q', "Ran 2 tests\nFAILED (failures=2)", 1),
        command("task", '"C:/PowerShell/pwsh.exe" -Command "Set-Content -Path .\\\\task.py -Value \'def clamp(value): return value\'"'),
        command("fact", "Set-Content -LiteralPath './evidence.json' -Value '{\"acceptance_delay_seconds\":37}'"),
        command("final", '"C:/PowerShell/pwsh.exe" -Command \'& "C:/Python/python.exe" -m unittest -q\'', final),
        {"type": "turn.completed"},
    ]


@pytest.mark.parametrize("count", [1, 2, 3, 4, 7, 12])
def test_successful_native_run_is_recognized_for_any_positive_count(count):
    found = native_evidence("codex", workflow(count))
    assert found["final_passed"], count
    assert found["workflow_ordered"], count
    assert found["terminal_success"], count
    assert found["written_files"] == ["evidence.json", "task.py"], count


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_realistic_unittest_summary_with_duration_is_recognized(count):
    found = native_evidence("codex", workflow(count, f"Ran {count} tests in 0.004s\n\nOK\n"))
    assert found["final_passed"], count
    assert found["workflow_ordered"], count


def test_v2_harness_is_unchanged_and_still_narrow():
    """The frozen v2 recognition keeps its literal two-test marker."""
    assert cli_acceptance.native_evidence("codex", workflow(3))["final_passed"] is False
    assert cli_acceptance.native_evidence("codex", workflow(2))["final_passed"] is True


@pytest.mark.parametrize("output", [
    "Ran 0 tests in 0.001s\n\nOK",
    "Ran 2 tests\nFAILED (failures=1)",
    "Ran 2 tests\nFAILED (errors=1)",
    "Ran 2 tests\nERROR: test_clamp",
    "Ran 2 tests\nOK (skipped=2)",
    "Ran 3 tests\nOK (skipped=3)",
])
def test_failed_error_skipped_and_zero_test_runs_are_rejected(output):
    assert unittest_outcome(output) is None
    found = native_evidence("codex", workflow(2, output))
    assert found["final_passed"] is False
    assert found["workflow_ordered"] is False


@pytest.mark.parametrize("output", [
    '"Ran 2 tests"',
    '"Ran 2 tests\nOK"',
    'The command printed "Ran 2 tests" and then "OK"',
    'Ran 2 tests is what the output said, so OK',
    '{"stdout": "Ran 2 tests\\nOK"}',
])
def test_quoted_prose_is_not_a_unittest_summary(output):
    assert unittest_outcome(output) is None
    assert native_evidence("codex", workflow(2, output))["final_passed"] is False


def test_failed_tool_execution_is_not_a_successful_final():
    events = workflow(3)
    events[4]["item"]["exit_code"] = 1
    events[4]["item"]["status"] = "failed"
    found = native_evidence("codex", events)
    assert found["final_passed"] is False
    assert found["workflow_ordered"] is False


def test_non_unittest_command_output_is_not_accepted():
    events = workflow(3)
    events[4]["item"]["command"] = '"C:/Python/python.exe" -m pytest -q'
    assert native_evidence("codex", events)["final_passed"] is False


def test_combined_command_output_is_not_accepted():
    events = workflow(3)
    events[4]["item"]["command"] = '"C:/Python/python.exe" -m unittest -q && echo done'
    assert native_evidence("codex", events)["final_passed"] is False


def test_claude_client_recognition_is_generalized_too():
    events = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "call-1", "name": "Bash",
            "input": {"command": '"C:/Python/python.exe" -m unittest -q'}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "call-1",
            "content": "Ran 3 tests in 0.01s\n\nOK"}]}},
        {"type": "result", "subtype": "success"},
    ]
    found = native_evidence("claude", events)
    assert found["final_passed"] is True
    assert found["terminal_success"] is True


def test_claude_failed_run_is_rejected():
    events = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "call-1", "name": "Bash",
            "input": {"command": '"C:/Python/python.exe" -m unittest -q'}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "call-1",
            "content": "Ran 3 tests\nFAILED (failures=1)"}]}},
        {"type": "result", "subtype": "success"},
    ]
    assert native_evidence("claude", events)["final_passed"] is False


V2_RECOGNITION = 'if completed.get(key) and "Ran 2 tests" in output and re.search(r"\\bOK\\b", output):'
V3_RECOGNITION = "if completed.get(key) and unittest_outcome(output) is not None:"


def test_v3_copy_differs_from_v2_only_in_the_recognition_line():
    """Boundary proof: the copied function is otherwise byte identical."""
    v2_source = inspect.getsource(cli_acceptance.native_evidence)
    v3_source = inspect.getsource(native_v3.native_evidence)
    assert V2_RECOGNITION in v2_source
    assert V3_RECOGNITION in v3_source
    assert v2_source.replace(V2_RECOGNITION, "RECOGNITION") == v3_source.replace(V3_RECOGNITION, "RECOGNITION")


def test_v3_module_records_its_provenance():
    assert native_v3.ATTRIBUTION["origin"] == "stress/cli_acceptance.py::native_evidence"
    assert "stress/cli_acceptance.py" in native_v3.__doc__
