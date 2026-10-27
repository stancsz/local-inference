"""Bounded daily acceptance + test-feedback runner for the local Qwen gateway.

Three existing productivity tasks, one native generation each and at most two
prescribed feedback repairs. Inference runs only against the local gateway at
http://127.0.0.1:8090 with the model qwen3.8-27b, using the same isolated
test-client approval and tool settings as ``scripts/claude_acceptance.py``.

The harness never edits generated output itself: it validates the file the
model produced, reports the validator errors back to the same native session
and asks for a correction. Every phase is archived, including failures and
timeouts, and no failure is deleted.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_acceptance
import daily_acceptance as validators
from daily_acceptance import (
    ARTIFACT_NAMES,
    BASELINE_CONTENT,
    MARKERS,
    REQUIRED_SOURCES,
    TASK_NAMES,
    sha256_text,
)
from setup_env import gateway_key

ROOT = Path(__file__).resolve().parents[1]
ROUTE = "http://127.0.0.1:8090"
MODEL = "qwen3.8-27b"
PHASE_TIMEOUT_SECONDS = 240
MAX_TURNS = 10
MAX_REPAIRS = 2
CLI_BINARY = "claude.cmd"


class HarnessError(RuntimeError):
    """Fail-closed condition that stops the task instead of repairing it."""


# --------------------------------------------------------------------------- #
# prompts (same three productivity tasks as scripts/claude_acceptance.py)
# --------------------------------------------------------------------------- #
BASE_PROMPTS = {name: prompt for name, prompt, _file, _marker in claude_acceptance.TASKS}


def build_prompt(task: str, artifact: Path) -> str:
    """Reuse the frozen task prompt and the frozen extra instructions."""
    prompt = BASE_PROMPTS[task]
    filename = artifact.name
    prompt = prompt.replace("tmp/acceptance/" + filename, artifact.as_posix())
    prompt += " The ONLY writable artifact is this exact absolute path: " + artifact.as_posix()
    prompt += ". Do not edit any other file or previous acceptance artifact."
    prompt = prompt.replace("Use the Write tool", "Use the Edit tool")
    prompt = prompt.replace("use the Write tool", "use the Edit tool")
    prompt = prompt.replace("Use Read and Write tools", "Use Read and Edit tools")
    prompt = prompt.replace("native Read and Write", "native Read and Edit")
    prompt += (
        " The output file already contains PENDING_LOCAL_ACCEPTANCE followed by a newline. Read it, then use Edit "
        "to replace its entire contents. This CLI exposes Read and Edit, with no separate Write tool."
    )
    if task != "model-audit":
        prompt += " Do not use Bash."
    if task == "vram-plan":
        prompt += (
            " The gpu CSV order in host-vram.json is name,total,used,free. Include exact machine-checkable lines "
            "host_total_mib=<number>, host_used_mib=<number>, host_free_mib=<number>. Do not swap used and free. "
            "Cite the source filename for each measurement and distinguish the older host snapshot from "
            "runtime-vram.json."
        )
        prompt += (
            " Report only the three largest measured process consumers. If using a process table, use columns "
            "Process | PID | Dedicated MiB and copy exact source values. Do not list other processes or guess PIDs."
        )
        prompt += " Include the exact safety sentence: Never terminate DWM."
    if task == "operator-guide":
        prompt += (
            " Use /health/readiness on port 8090. Document only the current daily default, not optional long "
            "profiles: verify compose.yaml shows 40960 total context, SIFT_TARGET=32768 as the adaptive policy "
            "anchor (not a fixed forwarded budget), 4096 output reserve and 4 draft tokens. Include exact "
            "configuration lines context_window=40960, sift_target=32768, output_reserve=4096, draft_tokens=4. "
            "Explain request-adaptive budgeting and its daily 24576..36608 range when reserving all 4096 output "
            "tokens. Short requests pass unchanged; 36608 is a ceiling, not a required request size. Do not discuss "
            "64k profiles in this short daily runbook."
        )
        prompt += (
            " Aim for 180-220 words and stay under the 350-word hard limit, counting headings and code. Keep "
            "commands and brief explanations only. The Sift target is part of the input budget, never added to it; "
            "a further 256 tokens are held for decoder headroom. A readiness response alone proves process "
            "readiness, not productive work."
        )
        prompt += (
            " Explicitly call the policy adaptive. Put commands in fenced powershell blocks. For logs use exactly: "
            "docker compose logs --no-color gateway > tmp/sift-runtime.log"
        )
    if task == "model-audit":
        prompt += (
            " The quantization field must identify BOTH the main IQ3_XXS and MTP Q4_0 quantizations from their "
            "filenames. Keep all required fields, and verify repository/revision against the manifest."
        )
        prompt += (
            " Include both exact GGUF basenames somewhere in the JSON so each label is traceable to its artifact. "
            "Do not infer Sift policy from SIFT_TARGET alone; omit that discussion unless you read README.md to "
            "verify its adaptive meaning."
        )
        prompt += (
            " If using the optional artifacts object, its only keys must be main_gguf and mtp_gguf, with the "
            "corresponding exact basenames as values (the file name only, without any directory prefix)."
        )
        prompt += (
            " Use Bash with python -c to calculate the exact sum from the manifest; do not calculate the large "
            "integers mentally. Bash is allowed only for that Python calculation. Use Read/Edit for the artifact."
        )
    return prompt


# --------------------------------------------------------------------------- #
# client configuration (unchanged isolated test-client settings)
# --------------------------------------------------------------------------- #
def build_env(config_dir: Path, key: str) -> dict:
    env = dict(os.environ)
    for name in ["GATEWAY_MASTER_KEY", "EXPERTS_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDECODE"]:
        env.pop(name, None)
    env.update(
        ANTHROPIC_API_KEY=key,
        ANTHROPIC_BASE_URL=ROUTE,
        ANTHROPIC_MODEL=MODEL,
        ANTHROPIC_DEFAULT_OPUS_MODEL=MODEL,
        ANTHROPIC_DEFAULT_SONNET_MODEL=MODEL,
        ANTHROPIC_DEFAULT_HAIKU_MODEL=MODEL,
        CLAUDE_CONFIG_DIR=str(config_dir),
        CLAUDE_CODE_DISABLE_1M_CONTEXT="1",
        CLAUDE_CODE_MAX_CONTEXT_TOKENS="1000000",
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
        API_TIMEOUT_MS="600000",
        CLAUDE_CODE_MAX_OUTPUT_TOKENS="4096",
    )
    return env


def build_args(task: str, resume: str = None) -> list:
    tools = "Read,Edit,Bash" if task == "model-audit" else "Read,Edit"
    allowed = "Read,Edit,Bash(python -c *)" if task == "model-audit" else "Read,Edit"
    args = [CLI_BINARY, "--bare"]
    if resume:
        args += ["--resume", resume]
    args += [
        "-p",
        "--model",
        MODEL,
        "--output-format",
        "stream-json",
        "--verbose",
        "--max-turns",
        str(MAX_TURNS),
        "--permission-mode",
        "acceptEdits",
        "--tools",
        tools,
        "--allowedTools",
        allowed,
    ]
    return args


# --------------------------------------------------------------------------- #
# native process handling
# --------------------------------------------------------------------------- #
def invoke_cli(args, env, prompt, cwd, stdout_path: Path, stderr_path: Path, timeout: int) -> tuple:
    """Run one bounded native CLI phase; return (exit_code, timed_out)."""
    popen_kwargs = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        popen_kwargs["start_new_session"] = True
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=out,
            stderr=err,
            text=True,
            cwd=str(cwd),
            env=env,
            **popen_kwargs,
        )
        try:
            process.communicate(input=prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_process_tree(process)
            try:
                process.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
            return -1, True
    return process.returncode, False


def kill_process_tree(process) -> None:
    """Kill the owned process tree (the CLI plus its own children)."""
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            import signal

            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except Exception:  # pragma: no cover - best effort cleanup
        try:
            process.kill()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# native event analysis
# --------------------------------------------------------------------------- #
def parse_events(stdout_path: Path) -> list:
    if not stdout_path.exists():
        return []
    events = []
    for line in stdout_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def final_result(events: list) -> dict:
    for event in reversed(events):
        if event.get("type") == "result":
            return event
    return {}


def tool_calls(events: list) -> list:
    names = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                names.append(block.get("name"))
    return names


def successful_tool_ids(events: list) -> set:
    successful = set()
    for event in events:
        if event.get("type") != "user":
            continue
        for block in event.get("message", {}).get("content", []):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            if block.get("is_error"):
                continue
            if "<tool_use_error>" in str(block.get("content")):
                continue
            successful.add(block.get("tool_use_id"))
    return successful


def first_edit_index(events: list) -> int:
    for index, event in enumerate(events):
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Edit":
                return index
    return None


def reconstruct_revisions(events: list, artifact: Path, base_text: str) -> list:
    """Rebuild the artifact from successful native Edit events.

    Fails closed on an edit that targets another file, an edit whose
    old_string does not match the current artifact state, or a phase without
    any successful native edit.
    """
    artifact = Path(artifact).resolve()
    successful = successful_tool_ids(events)
    current = base_text
    revisions = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if not isinstance(block, dict) or block.get("type") != "tool_use" or block.get("name") != "Edit":
                continue
            arguments = block.get("input", {})
            target = Path(str(arguments.get("file_path", ""))).resolve()
            if target != artifact:
                raise HarnessError(f"native edit targeted {target} instead of {artifact}")
            if block.get("id") not in successful:
                continue
            old = arguments.get("old_string") or ""
            if not old or old not in current:
                raise HarnessError("native edit does not match the prior artifact state")
            new = arguments.get("new_string")
            if new is None:
                raise HarnessError("native edit has no new_string")
            current = current.replace(old, new, -1 if arguments.get("replace_all") else 1)
            revisions.append(current)
    if not revisions:
        raise HarnessError("no successful native Edit event was recorded")
    return revisions


def collect_source_reads(events: list, task: str, artifact: Path) -> tuple:
    """Return (reads, violations) for complete native source reads."""
    allowed = {str((ROOT / name).resolve()) for name in REQUIRED_SOURCES[task]}
    artifact = str(Path(artifact).resolve())
    limit = first_edit_index(events)
    reads = {}
    violations = []
    for index, event in enumerate(events):
        if limit is not None and index >= limit:
            break
        result = event.get("tool_use_result")
        if not isinstance(result, dict) or result.get("type") != "text":
            continue
        file = result.get("file", {})
        original = Path(str(file.get("filePath", "")))
        try:
            resolved = str(original.resolve())
        except OSError:
            continue
        if resolved == artifact:
            continue
        if resolved not in allowed:
            violations.append(f"native read of unexpected file {original}")
            continue
        if file.get("startLine") != 1 or file.get("numLines") != file.get("totalLines"):
            continue
        reads[resolved] = file.get("content", "")
    return reads, violations


# --------------------------------------------------------------------------- #
# task runner
# --------------------------------------------------------------------------- #
def run_task(task: str, outdir: Path, sources: dict, key: str, max_repairs: int) -> dict:
    task_dir = outdir / task
    task_dir.mkdir(parents=True, exist_ok=True)
    revisions_dir = task_dir / "revisions"
    revisions_dir.mkdir(exist_ok=True)
    artifact = task_dir / ARTIFACT_NAMES[task]
    # Baseline: an explicit pending artifact that can never satisfy validation.
    artifact.write_text(BASELINE_CONTENT, encoding="utf-8")
    config_dir = Path(tempfile.mkdtemp(prefix=f"daily-{task}-"))
    phases = []
    current_text = BASELINE_CONTENT
    session_id = None
    errors = []
    baseline_errors = []
    repairs_used = 0
    try:
        for index in range(max_repairs + 1):
            kind = "generate" if index == 0 else "repair"
            phase_dir = task_dir / f"phase-{index}"
            phase_dir.mkdir(parents=True, exist_ok=True)
            prompt = build_prompt(task, artifact) if index == 0 else validators.feedback_prompt(
                task, errors, artifact, MARKERS[task]
            )
            (phase_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
            stdout_path = phase_dir / "stdout.jsonl"
            stderr_path = phase_dir / "stderr.log"
            args = build_args(task, resume=session_id)
            env = build_env(config_dir, key)
            started = time.monotonic()
            exit_code, timed_out = invoke_cli(
                args, env, prompt, ROOT, stdout_path, stderr_path, PHASE_TIMEOUT_SECONDS
            )
            elapsed = round(time.monotonic() - started, 2)
            events = parse_events(stdout_path)
            _redact(stdout_path, key)
            _redact(stderr_path, key)
            result = final_result(events)
            calls = tool_calls(events)
            phase_errors = []
            fatal = None
            if timed_out:
                phase_errors.append(f"phase timed out after {PHASE_TIMEOUT_SECONDS} seconds")
                fatal = "timeout"
            elif exit_code != 0:
                phase_errors.append(f"native CLI exited with code {exit_code}")
                fatal = "exit-code"
            if result.get("is_error", False):
                phase_errors.append("native CLI reported an error result")
                fatal = fatal or "is_error"
            result_text = str(result.get("result", ""))
            if not timed_out and MARKERS[task] not in result_text:
                phase_errors.append(f"the native result does not contain {MARKERS[task]}")
                fatal = fatal or "marker"
            new_session = result.get("session_id")
            if not new_session:
                phase_errors.append(
                    "the native result carries no session id, so a repair could not resume the same session"
                )
                fatal = fatal or "session"
            elif kind == "repair":
                if not session_id:
                    phase_errors.append("no native session id is available to resume")
                    fatal = fatal or "session"
                elif new_session != session_id:
                    phase_errors.append(
                        f"native session discontinuity: resumed {session_id} but the result reports {new_session}"
                    )
                    fatal = fatal or "session"
            try:
                revisions = reconstruct_revisions(events, artifact, current_text)
            except HarnessError as error:
                revisions = []
                phase_errors.append(str(error))
                fatal = fatal or "reconstruction"
            actual_text = artifact.read_text(encoding="utf-8") if artifact.exists() else ""
            if revisions and actual_text.rstrip("\r\n") != revisions[-1].rstrip("\r\n"):
                phase_errors.append("the artifact on disk differs from the reconstructed native edits")
                fatal = fatal or "mismatch"
            reads, violations = collect_source_reads(events, task, artifact)
            for violation in violations:
                phase_errors.append(violation)
                fatal = fatal or "unexpected-read"
            missing_sources = [
                name
                for name in REQUIRED_SOURCES[task]
                if str((ROOT / name).resolve()) not in reads
            ]
            if missing_sources:
                phase_errors.append(
                    "missing complete native source read(s) before the first artifact edit: " + ", ".join(missing_sources)
                )
                fatal = fatal or "source-read"
            validator_errors = []
            if not fatal:
                validator_errors = validators.validate_task_artifact(task, actual_text, sources)
            phase_errors.extend(validator_errors)
            # Preserve the candidate revision and its hash before any further edit.
            revision_path = revisions_dir / f"rev-{index}.txt"
            revision_path.write_text(actual_text, encoding="utf-8")
            revision_hash = sha256_text(actual_text)
            (revisions_dir / f"rev-{index}.sha256").write_text(revision_hash + "\n", encoding="utf-8")
            phase_record = {
                "phase": index,
                "kind": kind,
                "exit_code": exit_code,
                "timed_out": timed_out,
                "seconds": elapsed,
                "session_id": new_session or session_id,
                "native_tools": calls,
                "resumed": bool(kind == "repair"),
                "revision_file": revision_path.relative_to(outdir).as_posix(),
                "artifact_sha256": revision_hash,
                "source_reads": sorted(Path(p).name for p in reads),
                "errors": phase_errors,
                "fatal": fatal,
                "result_text": result_text[:2000],
                "usage": result.get("usage"),
            }
            phases.append(phase_record)
            (phase_dir / "phase.json").write_text(json.dumps(phase_record, indent=2), encoding="utf-8")
            if new_session:
                session_id = new_session
            if revisions:
                current_text = revisions[-1]
            errors = phase_errors
            if index == 0:
                baseline_errors = list(phase_errors)
            if fatal:
                break
            if not validator_errors:
                break
            if index >= max_repairs:
                break
            repairs_used += 1
    finally:
        shutil.rmtree(config_dir, ignore_errors=True)
    return {
        "task": task,
        "artifact": artifact.relative_to(outdir).as_posix(),
        "passed": not errors,
        "baseline_errors": baseline_errors,
        "final_errors": list(errors),
        "repairs_used": repairs_used,
        "phases": phases,
    }


def _redact(path: Path, secret: str) -> None:
    """Never leave the configured key in an archived log."""
    if not secret or not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if secret in text:
        path.write_text(text.replace(secret, "***redacted***"), encoding="utf-8")


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Fresh, task-owned output directory")
    parser.add_argument("--task", action="append", choices=list(TASK_NAMES), help="Restrict to specific tasks")
    parser.add_argument("--max-repairs", type=int, default=MAX_REPAIRS, help="Prescribed feedback repairs (max 2)")
    options = parser.parse_args(argv)
    if options.max_repairs < 0 or options.max_repairs > MAX_REPAIRS:
        parser.error(f"--max-repairs must be between 0 and {MAX_REPAIRS}")
    outdir = options.output_dir.resolve()
    if outdir.exists():
        print(f"output directory already exists: {outdir}. Choose a fresh directory.")
        return 2
    outdir.mkdir(parents=True)
    tasks = [name for name in TASK_NAMES if not options.task or name in options.task]
    sources = validators.load_sources(ROOT)
    harness_hashes = {
        'scripts/' + Path(path).name: validators.file_sha256(Path(path))
        for path in (__file__, validators.__file__, claude_acceptance.__file__)
    }
    (outdir / 'plan.json').write_text(json.dumps({
        'tasks': tasks, 'route': ROUTE, 'model': MODEL,
        'max_repairs': options.max_repairs, 'phase_timeout_seconds': PHASE_TIMEOUT_SECONDS,
        'harness_hashes': harness_hashes, 'source_hashes': sources['hashes'],
        'nine_turn_qualification_increment': 0,
    }, indent=2), encoding='utf-8')
    key = gateway_key()
    started = time.monotonic()
    results = []
    for task in tasks:
        results.append(run_task(task, outdir, sources, key, options.max_repairs))
    # Sources must not change during the run.
    changed = []
    for relative, digest in sources["hashes"].items():
        current = validators.file_sha256(ROOT / relative)
        if current != digest:
            changed.append(relative)
    summary = {
        "route": ROUTE,
        "model": MODEL,
        "base_url": ROUTE,
        "cloud_fallback": False,
        "phase_timeout_seconds": PHASE_TIMEOUT_SECONDS,
        "max_turns": MAX_TURNS,
        "max_repairs_allowed": MAX_REPAIRS,
        "nine_turn_qualification_increment": 0,
        "source_hashes": sources["hashes"],
        "harness_hashes": harness_hashes,
        "sources_changed_during_run": changed,
        "seconds": round(time.monotonic() - started, 2),
        "tasks": results,
        "remaining_failures": [
            {"task": row["task"], "errors": row["final_errors"]} for row in results if not row["passed"]
        ],
    }
    if changed:
        summary["remaining_failures"].append(
            {"task": "sources", "errors": [f"source file changed during the run: {name}" for name in changed]}
        )
    (outdir / "run-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for row in results:
        print(
            json.dumps(
                {
                    "task": row["task"],
                    "passed": row["passed"],
                    "baseline_errors": len(row["baseline_errors"]),
                    "final_errors": len(row["final_errors"]),
                    "repairs_used": row["repairs_used"],
                }
            ),
            flush=True,
        )
    return 0 if not summary["remaining_failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
