"""One genuinely active, persisted, multi-turn native CLI session (v3).

Provenance
----------
This runner is a separately versioned copy of the frozen v2 harness
(`stress/portable_campaign_v2.py`). It keeps every v2 gate unchanged - nine
substantive turns, more than 185 active seconds, 240 second per-turn
deadline, immutable public tests, hidden tests, retained historical source,
compaction/context accounting and native evidence - and adds:

* native evidence from `stress.native_v3`, whose successful unittest
  recognition accepts any positive test count instead of the v2 hardcoded
  `Ran 2 tests` marker, and
* immutable per-turn snapshots of `task.py`, `test_task.py` and
  `evidence.json` plus their content hashes, archived immediately after each
  native turn and after each hidden-test check, including failed turns.

The v2 harness and every sealed v2 receipt are left untouched: this module
never reinterprets old evidence. Source hashes describe the Sift modules
imported at run time in this epoch and are not expected to match the sealed
v2 epoch.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse

from stress.proxy_capture_v2 import make_app
from stress.cli_acceptance import child_command, codex_sandbox_readiness, executable
from stress.native_v3 import native_evidence

# Sealed campaign limits. These are identical to the v2 harness defaults and
# must never be weakened.
MINIMUM_SECONDS = 185
MINIMUM_SECONDS_FLOOR = 180
MINIMUM_TURNS = 9
TURN_TIMEOUT = 240
MAX_TURNS = 32

# Immutable per-turn archive contents.
SNAPSHOT_FILES = ("task.py", "test_task.py", "evidence.json")


def session_id(client, events):
    for event in events:
        if client == "codex" and event.get("type") == "thread.started":
            return event.get("thread_id")
        found = event.get("session_id" if client == "claude" else "sessionID")
        if found:
            return found
    return None


def source_hashes():
    """Hash the current local sources, including the Sift modules in use.

    The Sift modules are imported here, so the recorded hashes identify the
    Sift candidate that is actually loaded in this epoch rather than an
    earlier sealed epoch.
    """
    from sift import core, dynamic, litellm_proxy, litellm_responses
    from stress import portable_tasks_v2 as acceptance_tasks, cli_acceptance, supplement_tasks_v1, fixture_probe_v2, proxy_capture_v2, native_v3
    hashes={module.__name__: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for module in (core, dynamic, litellm_proxy, litellm_responses, acceptance_tasks, cli_acceptance, supplement_tasks_v1, fixture_probe_v2, proxy_capture_v2, native_v3)}
    hashes['stress.portable_campaign_v2']=hashlib.sha256(Path(__file__).resolve().parents[1].joinpath('stress/portable_campaign_v2.py').read_bytes()).hexdigest()
    hashes['stress.native_v3']=hashlib.sha256(Path(native_v3.__file__).read_bytes()).hexdigest()
    hashes['stress.campaign_v3']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    root=Path(__file__).resolve().parents[1]
    hashes['stress.cli_campaign']=hashlib.sha256((root/'stress/cli_campaign.py').read_bytes()).hexdigest()
    hashes['stress.acceptance_tasks']=hashlib.sha256((root/'stress/acceptance_tasks.py').read_bytes()).hexdigest()
    hashes.update({name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                   for name in ('app/budget.py','app/gateway.py','gateway.yaml')})
    return hashes


def sift_provenance():
    """The Sift modules this epoch actually imports, with their paths."""
    from sift import core, dynamic, litellm_proxy, litellm_responses
    return {module.__name__: str(Path(module.__file__).resolve())
            for module in (core, dynamic, litellm_proxy, litellm_responses)}


def snapshot_directory(root: Path, number: int, label: str) -> Path:
    """The immutable directory holding one archived turn snapshot."""
    return root / "snapshots" / f"turn-{number:02d}-{label}"


def archive_snapshot(root: Path, workspace: Path, number: int, label: str) -> dict:
    """Archive the per-turn workspace files and their hashes, once.

    The snapshot is write-once: an existing snapshot is never overwritten and
    never modified. The workspace itself is only read, never changed.
    """
    directory = snapshot_directory(root, number, label)
    if directory.exists():
        raise FileExistsError(f"snapshot already exists: {directory}")
    directory.mkdir(parents=True)
    hashes = {}
    for name in SNAPSHOT_FILES:
        source = workspace / name
        if not source.exists():
            hashes[name] = None
            continue
        data = source.read_bytes()
        (directory / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    manifest = {"turn": number + 1, "label": label, "files": list(SNAPSHOT_FILES), "sha256": hashes}
    (directory / "hashes.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


@contextlib.contextmanager
def archived_turn(root: Path, workspace: Path, number: int, label: str):
    """Archive the immutable workspace state at the end of one turn phase.

    The archive is written even when the wrapped phase fails, so failed and
    timed-out attempts are retained. The workspace is only read.
    """
    holder = {}
    try:
        yield holder
    finally:
        holder.update(archive_snapshot(root, workspace, number, label))


def parse_events(stdout):
    events = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            pass
    return events


def run(args):
    import uvicorn
    from stress.portable_tasks_v2 import initial_source, stage
    if urlparse(args.upstream_base_url).geturl() != "http://127.0.0.1:8090/v1":
        raise ValueError("Use the explicitly authorized 127.0.0.1:8090/v1 route")
    key = os.environ[args.api_key_env]
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=False)
    workspace = root / "workspace"
    workspace.mkdir()
    (workspace / "task.py").write_text(initial_source(args.task), encoding="utf-8")
    (workspace / "evidence.json").write_text('{"acceptance_delay_seconds":null}\n',encoding="utf-8")
    audits, turns = [], []
    snapshots = []
    gateway_log=Path(__file__).resolve().parents[1]/'evidence/gateway-audit.jsonl'
    gateway_start=len(gateway_log.read_text().splitlines()) if gateway_log.exists() else 0
    frozen = source_hashes()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(make_app(args.upstream_base_url, key, args.model, args.target, audits, capture_dir=root/"requests"),
                                         access_log=False, log_level="critical"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    started = time.monotonic()
    active = 0.0
    identifier = None
    failure = None
    client_version = subprocess.check_output([executable(args.client), "--version"], text=True, timeout=10).strip()
    receipt = {"accepted": False, "client": args.client, "client_version": client_version,
               "task": args.task, "seed": args.seed, "minimum_seconds": args.minimum_seconds,
               "model": args.model, "upstream": args.upstream_base_url, "target": args.target,
               "source_sha256": frozen, "sift_provenance": sift_provenance(),
               "turns": turns, "audits": audits, "snapshots": snapshots}

    def checkpoint():
        receipt['native_gateway_audits']=[json.loads(line) for line in gateway_log.read_text().splitlines()[gateway_start:] if line.strip()] if gateway_log.exists() else []
        receipt.update(active_client_seconds=round(active, 3), elapsed_seconds=round(time.monotonic()-started, 3),
                       session_id=identifier, failure=failure)
        temporary = root / "result.tmp"
        temporary.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        temporary.replace(root / "result.json")

    try:
        deadline = time.monotonic() + 15
        while not server.started and time.monotonic() < deadline:
            time.sleep(.02)
        if not server.started:
            raise RuntimeError("Acceptance proxy failed to start")
        for number in range(args.max_turns):
            if source_hashes() != frozen:
                raise RuntimeError("Source changed during the campaign session")
            definition = stage(args.task, number, args.seed + number)
            test_file = workspace / "test_task.py"
            test_file.write_text(definition["tests"], encoding="utf-8")
            expected_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
            prompt = (f"Task {args.task}, turn {number+1}: {definition['requirement']}\n"
                      "This is a real follow-up in the same isolated synthetic workspace; do not delegate or use network. "
                      "Read task.py and the newly updated test_task.py with native Read tools, run baseline tests as a separate shell call, "
                      "then fix task.py using native Edit tools if needed. Never modify test_task.py. "
                      "Keep evidence.json's acceptance_delay_seconds equal to the APPROVED setting in archived conversation evidence. "
                      "evidence.json is already seeded with a null value. Read it and use native Edit to replace null with the approved historical value; do not guess. "
                      f"For baseline and final tests run exactly \"{Path(sys.executable).as_posix()}\" -m unittest -q "
                      "as a standalone shell tool call (PowerShell may prefix &); no cd, redirection, pipes or combined commands. "
                      "A baseline failure is expected when requirements expand. Continue to fix it, then execute final tests and report actual results.")
            if args.client == "codex":
                prompt = prompt.replace("native Read tools", "native shell reads").replace("native Edit tools", "native apply_patch or standalone PowerShell Set-Content -Path FILE -Value CONTENT").replace("native Edit", "native apply_patch or standalone PowerShell Set-Content -Path FILE -Value CONTENT")
            command, env = child_command(args.client, executable(args.client), root / "client-home",
                                         f"http://127.0.0.1:{port}/v1", args.model, prompt,
                                         persist=True, session_id=identifier)
            if number == 0 and args.client == "codex":
                receipt["sandbox_readiness"] = codex_sandbox_readiness(executable(args.client), root, workspace, env)
                if not receipt["sandbox_readiness"]["passed"]:
                    raise RuntimeError("Codex sandbox readiness failed before inference")
                from stress.fixture_probe_v2 import probe
                receipt["fixture_readiness"]=probe(executable(args.client),root,workspace,env)
                if not receipt["fixture_readiness"]["passed"]:
                    raise RuntimeError("Portable fixture readiness failed before inference")
            turn_started = time.monotonic()
            native_manifest = {}
            with archived_turn(root, workspace, number, "native") as native_manifest:
                process = subprocess.Popen(command, cwd=workspace, env=env, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
                timed_out = False
                try:
                    stdout, stderr = process.communicate(timeout=args.turn_timeout)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
                    else:
                        process.kill()
                    stdout, stderr = process.communicate(timeout=15)
                duration = time.monotonic() - turn_started
                active += duration
                stdout, stderr = stdout.replace(key, "[REDACTED]"), stderr.replace(key, "[REDACTED]")
                (root / f"turn-{number:02}.jsonl").write_text(stdout, encoding="utf-8")
                (root / f"turn-{number:02}.stderr.txt").write_text(stderr, encoding="utf-8")
            snapshots.append(native_manifest)
            events = parse_events(stdout)
            returned_id = session_id(args.client, events)
            if identifier is None:
                identifier = returned_id
            native = native_evidence(args.client, events, workspace)
            # A second, different set of cases is never shown to the agent.
            hidden = stage(args.task, number, args.seed + number + 100003)["tests"]
            hidden_manifest = {}
            with archived_turn(root, workspace, number, "hidden") as hidden_manifest:
                checked = subprocess.run([sys.executable, "-c", hidden], cwd=workspace, capture_output=True, text=True, timeout=15)
                (root / f"turn-{number:02}.hidden-tests.txt").write_text(checked.stdout + checked.stderr, encoding="utf-8")
            snapshots.append(hidden_manifest)
            try:
                evidence = json.loads((workspace / "evidence.json").read_text())
                gold = isinstance(evidence, dict) and evidence.get("acceptance_delay_seconds") == 37
            except (OSError, ValueError):
                gold = False
            passed = (not timed_out and process.returncode == 0 and identifier is not None
                      and returned_id == identifier and native["terminal_success"] and native["final_passed"]
                      and (number != 0 or native["workflow_ordered"])
                      and native["unmatched_results"] == 0 and native["completed"] == native["calls"]
                      and checked.returncode == 0 and gold
                      and hashlib.sha256(test_file.read_bytes()).hexdigest() == expected_hash)
            turns.append({"number": number+1, "accepted": passed, "duration_seconds": round(duration, 3),
                          "client_exit": process.returncode, "timed_out": timed_out, "native": native,
                          "hidden_tests_exit": checked.returncode, "historical_gold_passed": gold,
                          "public_tests_sha256": expected_hash,
                          "snapshots": {"native": native_manifest, "hidden": hidden_manifest}})
            checkpoint()
            print(json.dumps({"client": args.client, "task": args.task, "turn": number+1,
                              "accepted": passed, "active_seconds": round(active, 2)}), flush=True)
            if not passed:
                failure = "native turn, hidden tests, history fact, or session continuity failed"
                break
            if active > args.minimum_seconds and len(turns) >= args.minimum_turns:
                compacted = [a for a in audits if a.get("compacted") is True]
                receipt["accepted"] = (bool(compacted) and any(a.get("tool_results", 0) for a in audits)
                    and all(a.get("gold_retained") and a["forwarded_tokens"] <= args.target for a in compacted)
                    and all(a.get("upstream_status") == 200 for a in audits) and source_hashes() == frozen)
                native_rows=receipt.get('native_gateway_audits',[])
                receipt['accepted']=receipt['accepted'] and bool(native_rows) and all(
                    row['native_input_tokens']+row['output_reserve']+row['decoder_headroom']<=row['context_window']
                    for row in native_rows)
                if not receipt["accepted"]:
                    failure = "compaction, retained historical source, upstream status, or source provenance failed"
                break
        else:
            failure = "maximum turns reached before the required active duration"
    except Exception as error:
        failure = type(error).__name__ + ": " + str(error).replace(key, "[REDACTED]")
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        sock.close()
        checkpoint()
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("claude", "opencode", "codex"), required=True)
    parser.add_argument("--task", choices=("incident_log", "release_manifest", "expense_audit"), required=True)
    parser.add_argument("--seed", type=int, default=831)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--upstream-base-url", default="http://127.0.0.1:8090/v1")
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key-env", default="SIFT_ACCEPTANCE_API_KEY")
    parser.add_argument("--target", type=int, default=32768)
    parser.add_argument("--minimum-seconds", type=float, default=MINIMUM_SECONDS)
    parser.add_argument("--minimum-turns", type=int, default=MINIMUM_TURNS)
    parser.add_argument("--max-turns", type=int, default=MAX_TURNS)
    parser.add_argument("--turn-timeout", type=int, default=TURN_TIMEOUT)
    args = parser.parse_args()
    expected='qwen3.8-27b-codex' if args.client=='codex' else 'qwen3.8-27b'
    if args.model is None: args.model=expected
    if args.model!=expected:
        parser.error('This campaign requires the pinned local Qwen alias for the selected client')
    if args.minimum_seconds <= MINIMUM_SECONDS_FLOOR or args.minimum_turns < MINIMUM_TURNS:
        parser.error("Acceptance sessions require >180 active seconds and multiple user turns")
    receipt = run(args)
    print(json.dumps({key: value for key, value in receipt.items() if key not in {"turns", "audits", "source_sha256"}}, indent=2))
    raise SystemExit(0 if receipt["accepted"] else 1)


if __name__ == "__main__":
    main()
