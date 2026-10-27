"""Version 3 native evidence: generalized successful unittest recognition.

Provenance
----------
`native_evidence` below is copied from the frozen v2 harness
(`stress/cli_acceptance.py`) and is attributed here with the single intended
behavioural change:

* v2 recognized a successful native unittest run only when the tool output
  literally contained ``Ran 2 tests`` plus ``OK``. The portable v2/v3 fixtures
  legitimately run one, three or four tests, so a genuinely successful native
  turn could be misrecognized as a failure. v3 recognizes any *positive*
  test count and still rejects failures, errors, skipped-only runs, zero-test
  runs, quoted prose and failed tool executions.

The v2 module is deliberately left untouched: sealed campaign receipts keep
their original meaning and are never reinterpreted. Every other native check
(write recognition, workflow ordering, terminal success, session continuity)
is preserved byte-for-byte from v2.

This module never runs inference. It only inspects already captured native
event streams.
"""
import re
from pathlib import Path

from stress.cli_acceptance import fixture_write_name, shell_write_targets

ATTRIBUTION = {
    "origin": "stress/cli_acceptance.py::native_evidence",
    "copied_on": "2026-10-27",
    "change": "successful unittest recognition generalized from 'Ran 2 tests' to any positive test count",
}

# A genuine unittest summary is reported on its own lines. Anchoring the
# patterns to whole lines rejects prose that merely quotes the summary.
_SUMMARY_LINE = re.compile(r"^Ran (\d+) tests?(?: in [0-9.]+s)?[ \t]*$", re.M)
_OK_LINE = re.compile(r"^OK(?: \([^\r\n]*\))?[ \t]*$", re.M)
_SKIPPED_COUNT = re.compile(r"skipped=(\d+)")
_FAILURE_MARKER = re.compile(r"\bFAILED\b|\bERROR\b")


def unittest_outcome(output) -> dict | None:
    """Recognize a genuine successful unittest summary in native tool output.

    Returns the recognized test count and skip count, or None when the output
    is not a standalone successful unittest run.
    """
    if not isinstance(output, str):
        return None
    output = output.replace('\r\n', '\n')
    summary = _SUMMARY_LINE.search(output)
    ok = _OK_LINE.search(output)
    if summary is None or ok is None:
        return None
    count = int(summary.group(1))
    if count <= 0:
        # A run that executed no test is never evidence of a passed fixture.
        return None
    if _FAILURE_MARKER.search(output):
        # Any failure or error marker disqualifies the run, even when an
        # "OK" line is also present.
        return None
    skipped = _SKIPPED_COUNT.search(ok.group(0))
    skipped_count = int(skipped.group(1)) if skipped else 0
    if skipped_count >= count:
        # Skipped-only runs prove nothing about the fixture.
        return None
    return {"tests": count, "skipped": skipped_count}


def native_evidence(client: str, events: list[dict], workspace: Path | None = None) -> dict:
    calls, completed = {}, {}
    outputs = {}
    shell_reads = {}
    shell_writes = {}
    shell_write_last = {}
    terminal = False
    errors = []
    for index, event in enumerate(events):
        if event.get("type") == "error":
            errors.append(event.get("error", "native error"))
        if client == "claude":
            message = event.get("message") or {}
            for block in message.get("content", []) if isinstance(message, dict) else []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    calls[block["id"]] = {"name": block.get("name", ""), "input": block.get("input") or {}, "index": index}
                if block.get("type") == "tool_result":
                    completed[block["tool_use_id"]] = not block.get("is_error", False)
                    outputs[block["tool_use_id"]] = str(block.get("content", ""))
            if event.get("type") == "result":
                terminal = event.get("subtype") == "success" and not event.get("is_error", False)
        elif client == "codex":
            item = event.get("item") or {}
            if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                key = item["id"]
                command, output = item.get("command", ""), item.get("aggregated_output", "")
                calls[key] = {"name": "Bash", "input": {"command": command}, "index": index}
                completed[key] = item.get("exit_code") == 0
                outputs[key] = output
                # The native CLI exposes file reads as command executions.
                if completed[key] and re.search(r"Get-Content|\bcat\b|read_text", command):
                    for filename in ("task.py", "test_task.py"):
                        if filename in command:
                            shell_reads.setdefault(filename, index)
                # The native CLI also exposes genuine file writes as command
                # executions. Only completed, successful writes to an exact
                # fixture path are evidence; prose and failed writes are not.
                if completed[key]:
                    for target in shell_write_targets(command):
                        filename = fixture_write_name(target, workspace)
                        if filename:
                            shell_writes.setdefault(filename, index)
                            shell_write_last[filename] = index
            if event.get("type") == "item.completed" and item.get("type") == "file_change":
                key = item["id"]
                calls[key] = {"name": "Edit", "input": {"paths": [c.get("path", "") for c in item.get("changes", [])]}, "index": index}
                completed[key] = item.get("status") == "completed"
            if event.get("type") == "turn.completed":
                terminal = True
            if event.get("type") == "turn.failed":
                terminal = False
                errors.append("turn.failed")
        else:
            part = event.get("part") or {}
            if event.get("type") == "tool_use" and part.get("type") == "tool":
                call_id = part.get("callID", part.get("id"))
                calls[call_id] = {"name": part.get("tool", ""), "input": (part.get("state") or {}).get("input") or {}, "index": index}
                state = part.get("state") or {}
                if state.get("status") in {"completed", "error"}:
                    exit_code = (state.get("metadata") or {}).get("exit")
                    completed[call_id] = state.get("status") == "completed" and exit_code in (None, 0)
                    outputs[call_id] = str(state.get("output", ""))
            if event.get("type") == "step_finish":
                terminal = part.get("reason") == "stop"
    successful = [calls[key]["name"] for key, ok in completed.items() if ok and key in calls]
    read_files, written_files, first_writes, baselines, finals = dict(shell_reads), dict(shell_write_last), dict(shell_writes), [], []
    for key, call in calls.items():
        name, arguments, index = call["name"].lower(), call["input"], call["index"]
        paths = arguments.get("paths") or [arguments.get("file_path", arguments.get("filePath", arguments.get("path", "")))]
        for path in paths:
            filename = str(path).replace("\\", "/").rsplit("/", 1)[-1]
            if client == "codex" and name in {"write", "edit"}:
                filename = fixture_write_name(path, workspace)
            if completed.get(key):
                if name == "read" and filename in {"task.py", "test_task.py"}:
                    read_files.setdefault(filename, index)
                if name in {"write", "edit"} and filename in {"task.py", "evidence.json"}:
                    written_files[filename] = max(written_files.get(filename, index), index)
                    first_writes[filename] = min(first_writes.get(filename, index), index)
        command = arguments.get("command", "")
        if isinstance(command, str):
            wrapper = re.fullmatch(r'''["'].*?(?:pwsh|powershell)\.exe["']\s+(?:-NoProfile\s+)?-Command\s+(["'])(.*)\1''', command, re.I | re.S)
            if wrapper:
                command = wrapper.group(2).strip()
        if name in {"bash", "powershell"} and isinstance(command, str) and re.fullmatch(
            r'\s*(?:&\s*)?(?:"[^"\r\n]+"|[^\s;&|]+)\s+-m\s+unittest\s+-q\s*', command,
        ):
            output = outputs.get(key, "")
            if key in completed and not completed[key] and "FAILED" in output:
                baselines.append(index)
            if completed.get(key) and unittest_outcome(output) is not None:
                finals.append(index)
    ordered = (set(read_files) == {"task.py", "test_task.py"}
               and set(written_files) == {"task.py", "evidence.json"}
               and any(max(read_files.values()) < baseline < min(first_writes.values())
                       and max(written_files.values()) < final for baseline in baselines for final in finals))
    return {"terminal_success": terminal and not errors, "calls": len(calls),
            "completed": len(completed), "successful_tools": successful,
            "unmatched_results": len(set(completed) - set(calls)), "native_errors": len(errors),
            "read_files": sorted(read_files), "written_files": sorted(written_files),
            "baseline_failed": bool(baselines), "final_passed": bool(finals), "workflow_ordered": bool(ordered)}
