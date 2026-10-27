"""Regression artifact for the deterministic expense-validation recovery fixture.

Scope: this proves that the recorded baseline artifacts still fail the three
contract checks that the new candidate (recovery/expenses_v1.py) passes. It is
NOT a retroactive pass of any recorded model attempt and NOT evidence that any
model learned the fixes.

Baseline artifacts are read as bytes and compiled in memory only; no artifact
is mutated, written or re-saved.
"""

import gzip
import hashlib
import importlib.util
import types
import pytest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = ROOT / "recovery" / "expenses_v1.py"
OPENCODE_GZ_PATH = ROOT / "evidence/stress-failures/opencode-expenses-r1/workspace-task.py.gz"
CLAUDE_PATH = ROOT / "evidence/stress-sessions/claude-expenses-r0/task.py"

CSV_GROUPING = "category,amount\nFood,1.00\nfood,2.00\n"
CSV_MISSING_CELL = "category,amount\nFood\n"
CSV_EXTRA_CELL = "category,amount\nFood,1.00,extra\n"


def _load_from_bytes(source_bytes, name):
    module = types.ModuleType(name)
    exec(compile(source_bytes, name, "exec"), module.__dict__)
    return module


def _opencode_baseline():
    return _load_from_bytes(gzip.decompress(OPENCODE_GZ_PATH.read_bytes()), "baseline_opencode_expenses")


def _claude_baseline():
    return _load_from_bytes(CLAUDE_PATH.read_bytes(), "baseline_claude_expenses")


def _candidate():
    spec = importlib.util.spec_from_file_location("recovery_expenses_v1", CANDIDATE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check_case_insensitive_grouping(module):
    expected = dict(Food=Decimal("3.00"))
    actual = module.expense_totals(CSV_GROUPING)
    assert actual == expected, "expected %r, got %r" % (expected, actual)


def _check_missing_amount_cell(module):
    try:
        result = module.expense_totals(CSV_MISSING_CELL)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError("expected ValueError, got %s: %s" % (type(exc).__name__, exc))
    raise AssertionError("expected ValueError, got result %r" % (result,))


def _check_extra_cell(module):
    try:
        result = module.expense_totals(CSV_EXTRA_CELL)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError("expected ValueError, got %s: %s" % (type(exc).__name__, exc))
    raise AssertionError("expected ValueError, got result %r" % (result,))


CONTRACT_CHECKS = (
    ("case_insensitive_grouping", _check_case_insensitive_grouping),
    ("missing_amount_cell_raises_value_error", _check_missing_amount_cell),
    ("extra_cell_raises_value_error", _check_extra_cell),
)


@pytest.mark.parametrize('api',('expense_totals','expense_report'))
@pytest.mark.parametrize('row',(',','  ,  ', ',,'))
def test_delimited_empty_cells_still_require_an_amount_and_valid_width(api,row):
    with pytest.raises(ValueError):
        getattr(_candidate(),api)('category,amount\n'+row+'\n')


def test_truly_empty_lines_remain_ignored():
    result=_candidate().expense_report('category,amount\n\nFood,1.00\n\n')
    assert result=={'totals':{'Food':Decimal('1.00')},'grand_total':Decimal('1.00'),'count':1}


def _evaluate(module):
    results = dict()
    for name, check in CONTRACT_CHECKS:
        try:
            check(module)
        except AssertionError:
            results[name] = False
        else:
            results[name] = True
    return results


def test_candidate_passes_all_three_contract_checks():
    results = _evaluate(_candidate())
    failed = sorted(name for name, ok in results.items() if not ok)
    assert failed == [], "candidate failed contract checks: %r" % (failed,)


def test_opencode_baseline_still_fails_contract_checks():
    results = _evaluate(_opencode_baseline())
    assert results["case_insensitive_grouping"] is False, "baseline unexpectedly groups case-insensitively"
    assert results["missing_amount_cell_raises_value_error"] is False, "baseline unexpectedly raised ValueError"
    assert results["extra_cell_raises_value_error"] is False, "baseline unexpectedly raised ValueError"


def test_claude_baseline_still_fails_contract_checks():
    results = _evaluate(_claude_baseline())
    assert results["missing_amount_cell_raises_value_error"] is False, "baseline unexpectedly raised ValueError"
    assert results["extra_cell_raises_value_error"] is False, "baseline unexpectedly raised ValueError"


def test_baseline_artifacts_are_unchanged():
    before = (
        hashlib.sha256(OPENCODE_GZ_PATH.read_bytes()).hexdigest(),
        hashlib.sha256(CLAUDE_PATH.read_bytes()).hexdigest(),
    )
    _opencode_baseline()
    _claude_baseline()
    after = (
        hashlib.sha256(OPENCODE_GZ_PATH.read_bytes()).hexdigest(),
        hashlib.sha256(CLAUDE_PATH.read_bytes()).hexdigest(),
    )
    assert before == after


def test_candidate_valid_control_cases():
    module = _candidate()
    data = "category,amount\nFood,1.005\nfood,2.00\nTransit,3.00\n"
    assert module.expense_totals(data) == dict(Food=Decimal("3.00"), Transit=Decimal("3.00"))
    assert module.expense_totals("category,amount\n A ,1\na,2\n") == dict(A=Decimal("3.00"))
    assert module.expense_totals("category,amount\nrefund,-2\n")["refund"] == Decimal("-2.00")
    assert list(module.expense_totals("category,amount\nb,1\na,2\n")) == ["b", "a"]
    expected_quoted = dict()
    expected_quoted["Food, home"] = Decimal("1.00")
    assert module.expense_totals("category,amount\n\"Food, home\",1.00\n") == expected_quoted
    report = module.expense_report("category,amount\nx,1.00\nx,2.00\n")
    assert report["count"] == 2
    assert report["grand_total"] == Decimal("3.00")
    assert module.expense_totals(data) == module.expense_totals(data)


def test_candidate_extended_contract():
    module = _candidate()
    assert module.expense_totals("category,amount\nx,1.005\nx,0.005\n") == dict(x=Decimal("1.01"))
    assert module.expense_totals("category,amount\n FOOD ,2.125\nfood,-0.005\n") == dict(FOOD=Decimal("2.12"))
    for invalid in ("NaN", "Infinity", "garbage", ""):
        try:
            module.expense_totals("category,amount\nx," + invalid + "\n")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for amount %r" % (invalid,))
    for bad in (
        "category,amount,currency\nx,1,USD\ny,2,CAD\n",
        "amount\n1\n",
        "category,amount,amount\nx,1,2\n",
    ):
        try:
            module.expense_totals(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for input %r" % (bad,))
    report = module.expense_report("category,amount\nz,1.005\n\na,2.00\nz,0.005\n")
    assert list(report["totals"]) == ["z", "a"]
    assert report["count"] == 3
    assert report["grand_total"] == Decimal("3.01")
