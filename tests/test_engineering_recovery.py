# Regression artifact for the deterministic clamp recovery fixture.
#
# Scope: proves the recorded baseline bytes still exhibit the recorded defect
# and that the new candidate (recovery/clamp_v1.py) rejects malformed bounds
# even for empty inputs. NOT a retroactive pass of any recorded model attempt
# and NOT evidence that any model learned the fixes.
#
# Baseline artifacts are read as bytes and compiled in memory only; no artifact
# is mutated, written or re-saved.

import hashlib
import importlib.util
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = ROOT / "recovery" / "clamp_v1.py"
BASELINE_PATH = ROOT / "evidence" / "stress-sessions" / "opencode-engineering-r2" / "task.py"

BASELINE_SHA256 = "5e21df06a3f66f8c27a2141e2af3e4f0d043804eec3259d9ee5dc18a71f5cbf0"


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_from_bytes(source_bytes, name):
    module = types.ModuleType(name)
    exec(compile(source_bytes, name, "exec"), module.__dict__)
    return module


@pytest.fixture(scope="module")
def candidate():
    return _load_module(CANDIDATE_PATH, "clamp_candidate_v1")


@pytest.fixture(scope="module")
def baseline():
    return _load_from_bytes(BASELINE_PATH.read_bytes(), "clamp_baseline_r2")


# --- baseline integrity / defect detection --------------------------------

def test_baseline_bytes_unchanged():
    digest = hashlib.sha256(BASELINE_PATH.read_bytes()).hexdigest()
    assert digest == BASELINE_SHA256


def test_baseline_exhibits_recorded_empty_input_defect(baseline):
    # The frozen baseline silently accepts malformed bounds on empty input.
    assert baseline.clamp_all([]) == []
    assert baseline.clamp_report([]) == {"count": 0, "min": None, "max": None, "sum": 0}
    for bad_lower in (float("nan"), False):
        # Defect present: the baseline silently accepts malformed bounds.
        assert baseline.clamp_all([], lower=bad_lower, upper=10) == []
        assert baseline.clamp_report([], lower=bad_lower, upper=10) == {
            "count": 0, "min": None, "max": None, "sum": 0,
        }
    # Reversed bounds (lower=5 > upper=2) are also silently accepted.
    assert baseline.clamp_all([], lower=5, upper=2) == []
    assert baseline.clamp_report([], lower=5, upper=2) == {
        "count": 0, "min": None, "max": None, "sum": 0,
    }
# --- empty input must still validate both bounds --------------------------

@pytest.mark.parametrize("bad_lower", [float("nan"), float("inf"), False, "0", None])
def test_clamp_all_empty_validates_lower(candidate, bad_lower):
    with pytest.raises((TypeError, ValueError)):
        candidate.clamp_all([], lower=bad_lower, upper=10)


@pytest.mark.parametrize("bad_upper", [float("nan"), float("-inf"), True, "100", None])
def test_clamp_all_empty_validates_upper(candidate, bad_upper):
    with pytest.raises((TypeError, ValueError)):
        candidate.clamp_all([], lower=0, upper=bad_upper)


@pytest.mark.parametrize("bad_lower", [float("nan"), float("inf"), False, "0", None])
def test_clamp_report_empty_validates_lower(candidate, bad_lower):
    with pytest.raises((TypeError, ValueError)):
        candidate.clamp_report([], lower=bad_lower, upper=10)


@pytest.mark.parametrize("bad_upper", [float("nan"), float("-inf"), True, "100", None])
def test_clamp_report_empty_validates_upper(candidate, bad_upper):
    with pytest.raises((TypeError, ValueError)):
        candidate.clamp_report([], lower=0, upper=bad_upper)


def test_clamp_all_empty_generator_validates_bounds(candidate):
    with pytest.raises((TypeError, ValueError)):
        candidate.clamp_all((x for x in []), lower=5, upper=2)
    with pytest.raises((TypeError, ValueError)):
        candidate.clamp_report((x for x in []), lower=float("nan"), upper=10)


def test_clamp_empty_reversed_bounds(candidate):
    with pytest.raises(ValueError):
        candidate.clamp_all([], lower=5, upper=2)
    with pytest.raises(ValueError):
        candidate.clamp_report([], lower=5, upper=2)
    with pytest.raises(ValueError):
        candidate.clamp_all((x for x in []), lower=5, upper=2)
    with pytest.raises(ValueError):
        candidate.clamp_report((x for x in []), lower=5, upper=2)


def test_clamp_all_empty_specific_error_types(candidate):
    with pytest.raises(TypeError):
        candidate.clamp_all([], lower=False, upper=10)
    with pytest.raises(TypeError):
        candidate.clamp_report([], lower=0, upper=True)
    with pytest.raises(ValueError):
        candidate.clamp_all([], lower=float("nan"), upper=10)
    with pytest.raises(ValueError):
        candidate.clamp_report([], lower=0, upper=float("inf"))
    with pytest.raises(ValueError):
        candidate.clamp_all([], lower=5, upper=2)
    with pytest.raises(ValueError):
        candidate.clamp_report([], lower=5, upper=2)


# --- non-empty input keeps validating both bounds -------------------------

def test_clamp_all_non_empty_validates_bounds(candidate):
    with pytest.raises(ValueError):
        candidate.clamp_all([1, 2], lower=5, upper=2)
    with pytest.raises(TypeError):
        candidate.clamp_all([1, 2], lower=False, upper=2)


def test_clamp_report_non_empty_validates_bounds(candidate):
    with pytest.raises(ValueError):
        candidate.clamp_report([1, 2], lower=5, upper=2)
    with pytest.raises(TypeError):
        candidate.clamp_report([1, 2], lower=0, upper=False)


# --- single-value clamp ---------------------------------------------------

def test_clamp_inclusive_and_defaults(candidate):
    assert candidate.clamp(-3) == 0
    assert candidate.clamp(120) == 100
    assert candidate.clamp(0) == 0
    assert candidate.clamp(100) == 100
    assert candidate.clamp(7, 5, 9) == 7
    assert candidate.clamp(5, 5, 9) == 5
    assert candidate.clamp(9, 5, 9) == 9


def test_clamp_value_validation(candidate):
    for bad in (True, False, "2", None, [1]):
        with pytest.raises(TypeError):
            candidate.clamp(bad)
    for bad in (float("inf"), float("-inf"), float("nan")):
        with pytest.raises(ValueError):
            candidate.clamp(bad)


def test_clamp_bound_validation(candidate):
    with pytest.raises(TypeError):
        candidate.clamp(1, False, 4)
    with pytest.raises(TypeError):
        candidate.clamp(1, 0, True)
    with pytest.raises(TypeError):
        candidate.clamp(1, "0", 4)
    with pytest.raises(ValueError):
        candidate.clamp(1, float("nan"), 4)
    with pytest.raises(ValueError):
        candidate.clamp(1, 0, float("inf"))
    with pytest.raises(ValueError):
        candidate.clamp(1, 5, 2)


# --- batch invariants -----------------------------------------------------

def test_clamp_all_values_and_order(candidate):
    assert candidate.clamp_all([-1, 4, 120]) == [0, 4, 100]
    assert candidate.clamp_all([]) == []
    assert candidate.clamp_all([5, 6], 5, 9) == [5, 6]
    values = [103, 49, 185, 24, 69, -192, 41, -77, -16, -7, 129, 117, -117, 108, -66, 169]
    assert candidate.clamp_all(values) == [max(0, min(100, v)) for v in values]


def test_clamp_all_value_validation(candidate):
    with pytest.raises(TypeError):
        candidate.clamp_all([1, "2"])
    with pytest.raises(ValueError):
        candidate.clamp_all([1, float("nan")])


def test_clamp_all_does_not_mutate_input(candidate):
    source = [-1, 4, 120]
    copy = list(source)
    candidate.clamp_all(source)
    assert source == copy


def test_clamp_all_single_use_iterator(candidate):
    iterator = iter([1, 101])
    assert candidate.clamp_all(iterator) == [1, 100]
    assert list(iterator) == []


def test_clamp_all_generator_consumed_once(candidate):
    def gen():
        yield 5
        yield 150

    generator = gen()
    assert candidate.clamp_all(generator) == [5, 100]
    assert list(generator) == []


# --- report invariants ----------------------------------------------------

def test_clamp_report_empty_shape(candidate):
    assert candidate.clamp_report([]) == {"count": 0, "min": None, "max": None, "sum": 0}


def test_clamp_report_values(candidate):
    report = candidate.clamp_report([2, 8])
    assert report["count"] == 2
    assert report["min"] == 2
    assert report["max"] == 8
    assert report["sum"] == 10
    assert candidate.clamp_report([-5, 250]) == {"count": 2, "min": 0, "max": 100, "sum": 100}


def test_clamp_report_deterministic(candidate):
    first = candidate.clamp_report([1, 2, 3])
    second = candidate.clamp_report([1, 2, 3])
    assert first == second
    assert first == {"count": 3, "min": 1, "max": 3, "sum": 6}


def test_clamp_report_generator(candidate):
    report = candidate.clamp_report((x for x in [2, 8]))
    assert report == {"count": 2, "min": 2, "max": 8, "sum": 10}


def test_clamp_report_does_not_mutate_input(candidate):
    source = [-1, 4, 120]
    copy = list(source)
    candidate.clamp_report(source)
    assert source == copy


def test_candidate_uses_stdlib_only():
    source = CANDIDATE_PATH.read_text(encoding="utf-8")
    for banned in ("import numpy", "import requests", "import torch", "import pandas"):
        assert banned not in source


def test_large_finite_integer_value_is_supported(candidate):
    assert candidate.clamp(10**400)==100


@pytest.mark.parametrize('api',('clamp_all','clamp_report'))
def test_large_finite_integer_bounds_are_supported(candidate,api):
    lower=10**400
    values=[lower+1]
    result=getattr(candidate,api)(values,lower,lower+2)
    expected=values if api=='clamp_all' else {'count':1,'min':lower+1,'max':lower+1,'sum':lower+1}
    assert result==expected
