"""Version 3 campaign harness: immutable per-turn snapshots and unchanged gates.

These tests never run inference. They exercise the snapshot machinery
directly and compare the copied harness against the frozen v2 harness to
prove that no gate, approval setting, sandbox setting, tool catalog, call ID
or protected instruction was weakened.
"""
import hashlib
import inspect
import json
from pathlib import Path
import re
import subprocess

import pytest

from stress import campaign_v3, cli_acceptance, native_v3, portable_campaign_v2

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workspace(tmp_path):
    space = tmp_path / "workspace"
    space.mkdir()
    (space / "task.py").write_bytes(b"def clamp(value):\n    return value\n")
    (space / "test_task.py").write_bytes(b"import unittest\r\nclass T(unittest.TestCase):\r\n    pass\r\n")
    (space / "evidence.json").write_bytes(b'{"acceptance_delay_seconds":37}\n')
    return space


def test_snapshot_is_byte_exact(tmp_path, workspace):
    root = tmp_path / "campaign"
    root.mkdir()
    campaign_v3.archive_snapshot(root, workspace, 0, "native")
    directory = campaign_v3.snapshot_directory(root, 0, "native")
    for name in campaign_v3.SNAPSHOT_FILES:
        assert (directory / name).read_bytes() == (workspace / name).read_bytes(), name


def test_snapshot_records_content_hashes(tmp_path, workspace):
    root = tmp_path / "campaign"
    root.mkdir()
    manifest = campaign_v3.archive_snapshot(root, workspace, 3, "hidden")
    stored = json.loads((campaign_v3.snapshot_directory(root, 3, "hidden") / "hashes.json").read_text())
    assert stored == manifest
    for name in campaign_v3.SNAPSHOT_FILES:
        expected = hashlib.sha256((workspace / name).read_bytes()).hexdigest()
        assert manifest["sha256"][name] == expected, name
    assert manifest["turn"] == 4 and manifest["label"] == "hidden"


def test_snapshot_is_immutable_and_never_overwritten(tmp_path, workspace):
    root = tmp_path / "campaign"
    root.mkdir()
    campaign_v3.archive_snapshot(root, workspace, 0, "native")
    directory = campaign_v3.snapshot_directory(root, 0, "native")
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    with pytest.raises(FileExistsError):
        campaign_v3.archive_snapshot(root, workspace, 0, "native")
    after = {path.name: path.read_bytes() for path in directory.iterdir()}
    assert before == after


def test_snapshot_does_not_modify_the_workspace(tmp_path, workspace):
    root = tmp_path / "campaign"
    root.mkdir()
    before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in workspace.iterdir()}
    campaign_v3.archive_snapshot(root, workspace, 0, "native")
    after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in workspace.iterdir()}
    assert before == after
    assert sorted(path.name for path in workspace.iterdir()) == ["evidence.json", "task.py", "test_task.py"]


def test_failed_attempt_is_retained(tmp_path, workspace):
    """A turn phase that raises still leaves its immutable snapshot behind."""
    root = tmp_path / "campaign"
    root.mkdir()
    with pytest.raises(RuntimeError):
        with campaign_v3.archived_turn(root, workspace, 1, "native"):
            (workspace / "task.py").write_bytes(b"broken")
            raise RuntimeError("native turn failed")
    directory = campaign_v3.snapshot_directory(root, 1, "native")
    assert (directory / "task.py").read_bytes() == b"broken"
    manifest = json.loads((directory / "hashes.json").read_text())
    assert manifest["sha256"]["task.py"] == hashlib.sha256(b"broken").hexdigest()


def test_both_turn_phases_are_archived(tmp_path, workspace):
    root = tmp_path / "campaign"
    root.mkdir()
    with campaign_v3.archived_turn(root, workspace, 0, "native") as native:
        pass
    with campaign_v3.archived_turn(root, workspace, 0, "hidden") as hidden:
        pass
    assert native["label"] == "native" and hidden["label"] == "hidden"
    assert native["turn"] == hidden["turn"] == 1
    assert campaign_v3.snapshot_directory(root, 0, "native").is_dir()
    assert campaign_v3.snapshot_directory(root, 0, "hidden").is_dir()


def test_missing_workspace_file_is_recorded_not_faked(tmp_path, workspace):
    root = tmp_path / "campaign"
    root.mkdir()
    (workspace / "evidence.json").unlink()
    manifest = campaign_v3.archive_snapshot(root, workspace, 0, "native")
    assert manifest["sha256"]["evidence.json"] is None
    assert not (campaign_v3.snapshot_directory(root, 0, "native") / "evidence.json").exists()


def test_campaign_uses_the_v3_native_evidence():
    assert campaign_v3.native_evidence is native_v3.native_evidence
    assert campaign_v3.native_evidence is not cli_acceptance.native_evidence


def test_source_hashes_include_the_new_modules_and_the_current_sift():
    hashes = campaign_v3.source_hashes()
    for name in ("stress.native_v3", "stress.campaign_v3", "stress.portable_campaign_v2",
                 "stress.cli_acceptance", "sift.core", "sift.dynamic",
                 "sift.litellm_proxy", "sift.litellm_responses"):
        assert name in hashes, name
        assert re.fullmatch(r"[0-9a-f]{64}", hashes[name]), name
    provenance = campaign_v3.sift_provenance()
    assert Path(provenance["sift.core"]).exists()
    assert provenance["sift.core"].endswith("core.py")


def test_sealed_campaign_limits_are_not_weakened():
    assert campaign_v3.MINIMUM_SECONDS == 185
    assert campaign_v3.MINIMUM_SECONDS_FLOOR == 180
    assert campaign_v3.MINIMUM_TURNS == 9
    assert campaign_v3.TURN_TIMEOUT == 240
    v2 = inspect.getsource(portable_campaign_v2)
    assert 'default=185' in v2 and 'default=9' in v2 and 'default=240' in v2
    assert 'args.minimum_seconds <= 180' in v2 and 'args.minimum_turns < 9' in v2


def _extract(source, pattern):
    match = re.search(pattern, source, re.S)
    assert match, pattern
    return match.group(0)


def test_acceptance_gate_prompt_and_client_invocation_are_unchanged():
    """Boundary proof: the copied gate, prompt and client call are identical."""
    v2 = inspect.getsource(portable_campaign_v2.run)
    v3 = inspect.getsource(campaign_v3.run)
    gate = r"passed = \(not timed_out and process\.returncode == 0.*?== expected_hash\)"
    assert _extract(v2, gate) == _extract(v3, gate)
    prompt = r'prompt = \(f"Task \{args\.task\}.*?report actual results\."\)'
    assert _extract(v2, prompt) == _extract(v3, prompt)
    invocation = r"command, env = child_command\(.*?session_id=identifier\)"
    assert _extract(v2, invocation) == _extract(v3, invocation)
    helper = inspect.getsource(cli_acceptance.child_command)
    for fragment in ("approval_policy", "sandbox_mode", "--allowedTools", "--permission-mode",
                     "model_catalog_json", "wire_api"):
        assert fragment in helper, fragment
    assert "def child_command" not in inspect.getsource(campaign_v3)
    assert "approval_policy" not in inspect.getsource(campaign_v3)
    assert "sandbox_mode" not in inspect.getsource(campaign_v3)


def test_campaign_does_not_bypass_preflight_or_permissions():
    source = inspect.getsource(campaign_v3)
    assert "--dangerously-bypass" not in source
    assert "dangerously-bypass" not in source
    assert "preflight" not in source.lower()


@pytest.mark.parametrize("relative", ["stress/cli_acceptance.py", "stress/portable_campaign_v2.py"])
def test_frozen_harnesses_are_unmodified(relative):
    """The v2 sources must be byte identical to their sealed revision."""
    completed = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=ROOT,
                               capture_output=True)
    if completed.returncode != 0:
        pytest.skip("git history unavailable")
    stored = completed.stdout.replace(b"\r\n", b"\n")
    current = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
    assert current == stored, relative
