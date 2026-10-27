"""Validator contracts for the daily acceptance harness.

The preserved repair-v3-final-claude artifacts are pinned regressions: the
VRAM plan mislabels host_used_mib, the model audit keeps the "MTP/" directory
prefix, and the runbook is correct.
"""
import gzip
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import claude_acceptance  # noqa: E402
import daily_acceptance as validators  # noqa: E402

PRESERVED = ROOT / "evidence/repair-v3-artifacts-v2/short-final"


def preserved_text(name):
    """Read published, immutable receipts instead of ignored local scratch."""
    return gzip.decompress((PRESERVED / (name + '.gz')).read_bytes()).decode('utf-8')


class PreservedArtifactRegressionTests(unittest.TestCase):
    def setUp(self):
        self.sources = validators.load_sources(ROOT)

    def test_vram_plan_with_runtime_used_value_is_rejected(self):
        text = preserved_text('vram-plan.md')
        errors = validators.validate_task_artifact("vram-plan", text, self.sources)
        self.assertTrue(any("host_used_mib" in error for error in errors), errors)
        host_used = validators.gpu_row(self.sources["host"])["used"]
        self.assertTrue(any(str(host_used) in error for error in errors), errors)
        self.assertTrue(any("15252" in error for error in errors), errors)

    def test_model_audit_with_mtp_directory_prefix_is_rejected(self):
        obj = json.loads(preserved_text('model-audit.json'))
        errors = validators.validate_model_audit_report(obj, self.sources["manifest"], self.sources["context"])
        self.assertTrue(any("basename" in error for error in errors), errors)
        self.assertTrue(any("mtp-Qwen3.8-27B-Q4_0.gguf" in error for error in errors), errors)

    def test_preserved_runbook_is_accepted(self):
        text = preserved_text('OPERATIONS.md')
        self.assertEqual(validators.validate_task_artifact("operator-guide", text, self.sources), [])

    def test_preserved_runbook_matches_the_frozen_contract(self):
        text = preserved_text('OPERATIONS.md')
        self.assertTrue(claude_acceptance.validate_operator_guide(text))


class ValidatorNegativeTests(unittest.TestCase):
    def test_feedback_names_all_sources_even_for_a_command_only_error(self):
        feedback = validators.feedback_prompt('vram-plan', ["missing nvidia-smi"], Path('candidate.md'))
        for source in validators.REQUIRED_SOURCES['vram-plan']:
            self.assertIn(source, feedback)
        self.assertIn('Before editing', feedback)

    def setUp(self):
        self.sources = validators.load_sources(ROOT)
        self.manifest = self.sources["manifest"]

    def test_model_audit_wrong_total_bytes_is_actionable(self):
        obj = json.loads(preserved_text('model-audit.json'))
        obj["artifacts"]["mtp_gguf"] = "mtp-Qwen3.8-27B-Q4_0.gguf"
        obj["total_weight_bytes"] = 12304457360
        errors = validators.validate_model_audit_report(obj, self.manifest, self.sources["context"])
        self.assertTrue(any("total_weight_bytes" in error for error in errors), errors)

    def test_model_audit_wrong_context_is_actionable(self):
        obj = json.loads(preserved_text('model-audit.json'))
        obj["artifacts"]["mtp_gguf"] = "mtp-Qwen3.8-27B-Q4_0.gguf"
        obj["configured_context_size"] = 65536
        errors = validators.validate_model_audit_report(obj, self.manifest, self.sources["context"])
        self.assertTrue(any("CONTEXT_SIZE" in error for error in errors), errors)

    def test_swapped_process_pid_is_actionable(self):
        errors = validators.validate_process_rows_report("| dwm | 282312 | 1688.2 |", self.sources["host"]["processes"])
        self.assertTrue(errors)
        self.assertTrue(any("282312" in error for error in errors), errors)

    def test_invented_process_is_actionable(self):
        errors = validators.validate_process_rows_report("| nvcontainer | 4242 | 999.0 |", self.sources["host"]["processes"])
        self.assertTrue(any("not in evidence/host-vram.json" in error for error in errors), errors)

    def test_missing_command_in_runbook_is_actionable(self):
        text = preserved_text('OPERATIONS.md')
        broken = text.replace("docker compose down", "docker compose stop")
        errors = validators.validate_operator_guide_report(broken)
        self.assertTrue(any("docker compose down" in error for error in errors), errors)

    def test_word_limit_is_actionable(self):
        errors = validators.validate_operator_guide_report("word " * 400)
        self.assertTrue(any("350" in error for error in errors), errors)

    def test_frozen_contracts_are_not_weakened(self):
        obj = json.loads(preserved_text('model-audit.json'))
        obj["artifacts"]["mtp_gguf"] = "mtp-Qwen3.8-27B-Q4_0.gguf"
        original = claude_acceptance.validate_model_audit
        claude_acceptance.validate_model_audit = lambda *args, **kwargs: False
        try:
            errors = validators.validate_model_audit_report(obj, self.manifest, self.sources["context"])
        finally:
            claude_acceptance.validate_model_audit = original
        self.assertTrue(any("frozen" in error for error in errors), errors)

    def test_validator_module_performs_no_inference(self):
        source = (ROOT / "scripts/daily_acceptance.py").read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("claude.cmd", source)


class FeedbackTests(unittest.TestCase):
    def test_feedback_reports_errors_and_asks_for_a_correction(self):
        errors = ["the plan must state host_used_mib=2005 from evidence/host-vram.json"]
        prompt = validators.feedback_prompt("vram-plan", errors, Path("tmp/x/vram-plan.md"))
        self.assertIn("host_used_mib=2005", prompt)
        self.assertIn("re-read", prompt.lower())
        self.assertIn("VRAM_PLAN_DONE", prompt)
        self.assertNotIn("PENDING_LOCAL_ACCEPTANCE", prompt)


if __name__ == "__main__":
    unittest.main()
