"""Runner contracts for the daily acceptance harness (inference is mocked)."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import daily_acceptance as validators  # noqa: E402
import daily_artifacts as runner  # noqa: E402

TASK = "model-audit"
KEY = "sk-unit-test-key-not-a-real-credential"


def model_audit_body(sources, total=None):
    manifest = sources["manifest"]
    basenames = validators.manifest_basenames(manifest)
    body = {
        "repository": manifest["repository"],
        "revision": manifest["revision"],
        "total_weight_bytes": total
        if total is not None
        else validators.manifest_total_bytes(manifest),
        "quantization": {"main": "IQ3_XXS", "mtp": "Q4_0"},
        "configured_context_size": sources["context"],
        "limitations": ["Disk size only: " + ", ".join(f["file"] for f in manifest["files"])],
        "artifacts": basenames,
    }
    return json.dumps(body, indent=2)


class FakeCli:
    """A scripted native CLI that emits the same event shapes as the real one."""

    def __init__(self, artifact, bodies, root=ROOT, session="sess-1", timeouts=None, omit_session=False, mutate=None):
        self.artifact = Path(artifact)
        self.bodies = list(bodies)
        self.root = Path(root)
        self.session = session
        self.timeouts = set(timeouts or [])
        self.omit_session = omit_session
        self.mutate = mutate
        self.calls = []

    def __call__(self, args, env, prompt, cwd, stdout_path, stderr_path, timeout):
        index = len(self.calls)
        self.calls.append({"args": list(args), "env": dict(env), "prompt": prompt})
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        if index in self.timeouts:
            return -1, True
        body = self.bodies[index]
        events = []
        for number, relative in enumerate(validators.REQUIRED_SOURCES[TASK], start=1):
            path = self.root / relative
            content = path.read_text(encoding="utf-8")
            lines = content.count("\n") + 1
            events.append(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {"type": "tool_use", "id": f"r{number}", "name": "Read", "input": {"file_path": str(path)}}
                        ]
                    },
                    "tool_use_result": {
                        "type": "text",
                        "file": {
                            "filePath": str(path),
                            "startLine": 1,
                            "numLines": lines,
                            "totalLines": lines,
                            "content": content,
                        },
                    },
                }
            )
            events.append(
                {
                    "type": "user",
                    "message": {"content": [{"type": "tool_result", "tool_use_id": f"r{number}", "content": "ok"}]},
                }
            )
        current = self.artifact.read_text(encoding="utf-8") if self.artifact.exists() else ""
        events.append(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "e1",
                            "name": "Edit",
                            "input": {"file_path": str(self.artifact), "old_string": current, "new_string": body},
                        }
                    ]
                },
            }
        )
        events.append(
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "e1", "content": "ok"}]}}
        )
        result = {"type": "result", "result": "wrote the artifact MODEL_AUDIT_DONE", "is_error": False}
        if not self.omit_session:
            result["session_id"] = self.session
        events.append(result)
        with stdout_path.open("w", encoding="utf-8") as stream:
            for event in events:
                stream.write(json.dumps(event) + "\n")
        self.artifact.write_text(body, encoding="utf-8")
        if self.mutate:
            target = self.root / self.mutate
            target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        return 0, False


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.sources = validators.load_sources(ROOT)
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.outdir = self.tmp / "run"
        self.artifact = self.outdir / TASK / validators.ARTIFACT_NAMES[TASK]
        patcher = mock.patch.dict(os.environ, {"LOCAL_GATEWAY_KEY": KEY})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_runner(self, fake, tasks=(TASK,), expect=0):
        original = runner.invoke_cli
        runner.invoke_cli = fake
        try:
            code = runner.main(["--output-dir", str(self.outdir), "--task", *tasks])
        finally:
            runner.invoke_cli = original
        self.assertEqual(code, expect)
        return json.loads((self.outdir / "run-summary.json").read_text(encoding="utf-8"))

    def test_first_phase_success_runs_once(self):
        fake = FakeCli(self.artifact, [model_audit_body(self.sources)])
        summary = self.run_runner(fake)
        row = summary["tasks"][0]
        self.assertTrue(row["passed"], row["final_errors"])
        self.assertEqual(row["repairs_used"], 0)
        self.assertEqual(len(row["phases"]), 1)
        self.assertEqual(row["phases"][0]["kind"], "generate")
        self.assertEqual(row["final_errors"], [])
        self.assertEqual(summary["nine_turn_qualification_increment"], 0)

    def test_failed_check_triggers_one_prescribed_repair(self):
        broken = model_audit_body(self.sources, total=1)
        good = model_audit_body(self.sources)
        fake = FakeCli(self.artifact, [broken, good])
        summary = self.run_runner(fake)
        row = summary["tasks"][0]
        self.assertTrue(row["passed"], row["final_errors"])
        self.assertEqual(row["repairs_used"], 1)
        self.assertEqual(len(row["phases"]), 2)
        self.assertEqual(row["phases"][1]["kind"], "repair")
        self.assertIn("total_weight_bytes", fake.calls[1]["prompt"])
        self.assertIn("--resume", fake.calls[1]["args"])
        self.assertIn("sess-1", fake.calls[1]["args"])

    def test_repair_count_is_bounded_at_two(self):
        broken = model_audit_body(self.sources, total=1)
        fake = FakeCli(self.artifact, [broken, broken, broken])
        summary = self.run_runner(fake, expect=1)
        row = summary["tasks"][0]
        self.assertFalse(row["passed"])
        self.assertEqual(row["repairs_used"], 2)
        self.assertEqual(len(row["phases"]), 3)
        self.assertTrue(row["final_errors"])
        self.assertTrue(summary["remaining_failures"])

    def test_route_permissions_and_turn_budget_are_unchanged(self):
        fake = FakeCli(self.artifact, [model_audit_body(self.sources)])
        self.run_runner(fake)
        args = fake.calls[0]["args"]
        env = fake.calls[0]["env"]
        self.assertEqual(args[args.index("--allowedTools") + 1], "Read,Edit,Bash(python -c *)")
        self.assertEqual(args[args.index("--tools") + 1], "Read,Edit,Bash")
        self.assertEqual(args[args.index("--permission-mode") + 1], "acceptEdits")
        self.assertEqual(args[args.index("--max-turns") + 1], "10")
        self.assertEqual(args[args.index("--model") + 1], "qwen3.8-27b")
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "http://127.0.0.1:8090")
        self.assertEqual(env["ANTHROPIC_MODEL"], "qwen3.8-27b")
        self.assertIn("CLAUDE_CONFIG_DIR", env)
        self.assertNotIn("GATEWAY_MASTER_KEY", env)
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", env)

    def test_isolated_config_dir_is_shared_across_phases_and_key_is_never_archived(self):
        broken = model_audit_body(self.sources, total=1)
        good = model_audit_body(self.sources)
        fake = FakeCli(self.artifact, [broken, good])
        self.run_runner(fake)
        self.assertEqual(fake.calls[0]["env"]["CLAUDE_CONFIG_DIR"], fake.calls[1]["env"]["CLAUDE_CONFIG_DIR"])
        for path in self.outdir.rglob("*"):
            if path.is_file():
                self.assertNotIn(KEY, path.read_text(encoding="utf-8", errors="replace"))

    def test_missing_session_id_fails_closed_without_a_repair(self):
        fake = FakeCli(self.artifact, [model_audit_body(self.sources)], omit_session=True)
        summary = self.run_runner(fake, expect=1)
        row = summary["tasks"][0]
        self.assertFalse(row["passed"])
        self.assertEqual(len(row["phases"]), 1)
        self.assertTrue(any("session" in error for error in row["final_errors"]), row["final_errors"])

    def test_revisions_are_written_once_per_phase(self):
        broken = model_audit_body(self.sources, total=1)
        good = model_audit_body(self.sources)
        fake = FakeCli(self.artifact, [broken, good])
        self.run_runner(fake)
        revisions = self.outdir / TASK / "revisions"
        self.assertEqual(sorted(p.name for p in revisions.glob("rev-*.txt")), ["rev-0.txt", "rev-1.txt"])
        self.assertEqual((revisions / "rev-0.txt").read_text(encoding="utf-8"), broken)
        self.assertEqual((revisions / "rev-1.txt").read_text(encoding="utf-8"), good)
        self.assertNotEqual(
            (revisions / "rev-0.sha256").read_text(encoding="utf-8"),
            (revisions / "rev-1.sha256").read_text(encoding="utf-8"),
        )
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), good)

    def test_timeout_is_archived_and_reported(self):
        fake = FakeCli(self.artifact, [model_audit_body(self.sources)], timeouts={0})
        summary = self.run_runner(fake, expect=1)
        row = summary["tasks"][0]
        self.assertFalse(row["passed"])
        self.assertTrue(row["phases"][0]["timed_out"])
        self.assertTrue(any("timed out" in error for error in row["final_errors"]), row["final_errors"])
        self.assertTrue((self.outdir / TASK / "phase-0" / "stdout.jsonl").exists())
        self.assertTrue((self.outdir / TASK / "phase-0" / "phase.json").exists())

    def test_existing_output_directory_is_refused(self):
        self.outdir.mkdir(parents=True)
        code = runner.main(["--output-dir", str(self.outdir), "--task", TASK])
        self.assertEqual(code, 2)
        self.assertFalse((self.outdir / "run-summary.json").exists())

    def test_changed_source_is_detected(self):
        temp_root = self.tmp / "root"
        (temp_root / "evidence").mkdir(parents=True)
        for relative in ("README.md", "compose.yaml", "gateway.yaml"):
            shutil.copy(ROOT / relative, temp_root / relative)
        for relative in ("evidence/model-manifest.json", "evidence/host-vram.json", "evidence/runtime-vram.json"):
            shutil.copy(ROOT / relative, temp_root / relative)
        fake = FakeCli(
            self.artifact,
            [model_audit_body(self.sources)],
            root=temp_root,
            mutate="evidence/model-manifest.json",
        )
        original_root = runner.ROOT
        runner.ROOT = temp_root
        try:
            summary = self.run_runner(fake, expect=1)
        finally:
            runner.ROOT = original_root
        self.assertTrue(summary["sources_changed_during_run"])
        self.assertTrue(
            any("source file changed" in error for error in summary["remaining_failures"][-1]["errors"]),
            summary["remaining_failures"],
        )


if __name__ == "__main__":
    unittest.main()
