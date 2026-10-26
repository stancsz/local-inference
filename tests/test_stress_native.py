"""Native workflow evidence must describe actual ordered file operations."""
from copy import deepcopy

import pytest

from stress.cli_acceptance import native_evidence, fixture_write_name, shell_write_targets, child_command


def command(identifier, text, output="", exit_code=0):
    return {"type": "item.completed", "item": {"id": identifier, "type": "command_execution",
            "command": text, "aggregated_output": output, "exit_code": exit_code,
            "status": "completed" if exit_code == 0 else "failed"}}


def workflow():
    return [
        command("read", "Get-Content task.py; Get-Content test_task.py"),
        command("baseline", '"C:/Python/python.exe" -m unittest -q', "Ran 2 tests\nFAILED (failures=2)", 1),
        command("task", '"C:/PowerShell/pwsh.exe" -Command "Set-Content -Path .\\\\task.py -Value \'def clamp(value): return value\'"'),
        command("fact", "Set-Content -LiteralPath './evidence.json' -Value '{\"acceptance_delay_seconds\":37}'"),
        command("final", '"C:/PowerShell/pwsh.exe" -Command \'& "C:/Python/python.exe" -m unittest -q\'', "Ran 2 tests\nOK"),
        {"type": "turn.completed"},
    ]


def test_successful_native_powershell_writes_are_ordered():
    found = native_evidence("codex", workflow())
    assert found["written_files"] == ["evidence.json", "task.py"]
    assert found["workflow_ordered"] and found["final_passed"] and found["terminal_success"]


def test_cli_rendered_concatenated_powershell_quotes():
    text = '''"C:\\PowerShell\\pwsh.exe" -Command "Set-Content -Path .\\\\task.py -Value 'def clamp(value):
    return value
' -NoNewline:"'$false' '''.strip()
    assert [fixture_write_name(p) for p in shell_write_targets(text)] == ["task.py"]


@pytest.mark.parametrize("text", [
    "Get-Content task.py", "Write-Output 'Set-Content -Path task.py -Value x'",
    "echo task.py > unrelated.txt", "Set-Content -Path unrelated.txt -Value task.py",
    "Set-Content -Path ../task.py -Value x", "Set-Content -Path C:/other/task.py -Value x",
    "Set-Content -Path subdir/task.py -Value x", "Set-Content -Path ./task.py.backup -Value x",
])
def test_path_mentions_and_other_targets_are_not_writes(text):
    assert not any(fixture_write_name(p) for p in shell_write_targets(text))


def test_failed_writer_does_not_pass():
    events = workflow()
    events[2]["item"].update(exit_code=1, status="failed")
    found = native_evidence("codex", events)
    assert found["written_files"] == ["evidence.json"]
    assert not found["workflow_ordered"]


@pytest.mark.parametrize("order", [(2, 0, 1, 3, 4, 5), (0, 1, 2, 4, 3, 5)])
def test_write_before_baseline_or_after_final_rejected(order):
    events = workflow()
    assert not native_evidence("codex", [events[i] for i in order])["workflow_ordered"]


def test_earlier_final_does_not_hide_later_shell_write():
    events = workflow()
    events.insert(2, {"type": "item.completed", "item": {"id": "edit", "type": "file_change",
        "status": "completed", "changes": [{"path": "task.py"}]}})
    events[-2], events[-3] = events[-3], events[-2]
    assert not native_evidence("codex", events)["workflow_ordered"]


def test_started_events_are_not_completed_writes():
    events = deepcopy(workflow())
    events[2]["type"] = "item.started"
    assert not native_evidence("codex", events)["workflow_ordered"]


def test_absolute_writes_must_match_exact_workspace(tmp_path):
    inside = tmp_path / 'workspace'
    inside.mkdir()
    events = workflow()
    for index, filename in ((2, 'task.py'), (3, 'evidence.json')):
        events[index]['item']['command'] = f'Set-Content -Path "{inside / filename}" -Value x'
    assert native_evidence('codex', events, inside)['workflow_ordered']
    assert not native_evidence('codex', events, tmp_path / 'other')['workflow_ordered']
    events[2]['item']['command'] = f'Set-Content -Path "{inside}/../task.py" -Value x'
    assert not native_evidence('codex', events, inside)['workflow_ordered']


def test_codex_resume_keeps_explicit_workspace_permissions(tmp_path):
    home = tmp_path / 'client-home'
    home.mkdir()
    (home / 'models.json').write_text('{}')
    for identifier in (None, '00000000-0000-0000-0000-000000000001'):
        command, env = child_command('codex', 'codex', home, 'http://127.0.0.1:12345/v1',
            'qwen3.8-27b-codex', 'test', persist=True, session_id=identifier)
        assert 'sandbox_mode="workspace-write"' in command
        assert '--dangerously-bypass-approvals-and-sandbox' not in command
        assert 'model_providers.sift_acceptance.base_url="http://127.0.0.1:12345/v1"' in command
        assert ('resume' in command) == bool(identifier)
