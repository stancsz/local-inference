"""The v3 diagnostic reuses frozen failures and never auto-launches inference."""
import json
from pathlib import Path

from recovery.expense_feedback_v3 import ROOT, BASELINE, PROBES, additional_checks, sha


def test_additional_checks_detect_all_six_preserved_failures():
    before = BASELINE.read_bytes()
    checks = additional_checks(BASELINE)
    assert len(checks) == 6 and not any(c['passed'] for c in checks)
    assert BASELINE.read_bytes() == before


def test_same_checks_accept_deterministic_control():
    checks = additional_checks(ROOT / 'recovery/expenses_v1.py')
    assert len(checks) == 6 and all(c['passed'] for c in checks)


def test_baseline_is_the_frozen_v2_generated_artifact():
    record = json.loads((ROOT / 'evidence/feedback-recovery-v2.json').read_text(encoding='utf-8'))
    expense = next(c for c in record['parent_artifact_review'] if c['task'] == 'expenses')
    assert sha(BASELINE.read_bytes()) == expense['turns'][-1]['generated_sha256']
    assert PROBES.exists()
