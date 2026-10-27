"""Regression artifact for the deterministic migration-settings recovery fixture.

Scope: this proves that the recorded baseline fixture still exhibits the three
recorded validation defects that the new candidate (recovery/migration_v1.py)
repairs. It is NOT a retroactive pass of any recorded model attempt and NOT
evidence that any model learned the fixes.

Baseline artifacts are read as bytes and compiled in memory only; no artifact
is mutated, written or re-saved.
"""

import hashlib
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = ROOT / "recovery" / "migration_v1.py"
BASELINE_PATH = ROOT / "evidence/stress-sessions/opencode-migration-r0/task.py"

DEFAULTS = dict(name="default", timeout_seconds=30, retries=0)


def _load_from_bytes(source_bytes, name):
    module = types.ModuleType(name)
    exec(compile(source_bytes, name, "exec"), module.__dict__)
    return module


def _candidate():
    return _load_from_bytes(CANDIDATE_PATH.read_bytes(), "recovery_migration_v1_candidate")


def _baseline():
    return _load_from_bytes(BASELINE_PATH.read_bytes(), "baseline_opencode_migration_r0")


def _accepted(module, mapping):
    """Return True when module.normalize_settings(mapping) returns without raising."""
    try:
        module.normalize_settings(mapping)
    except Exception:
        return False
    return True


def _raises(module, mapping, types_expected=(TypeError, ValueError)):
    with pytest.raises(types_expected):
        module.normalize_settings(mapping)


# --- recorded defects in the preserved baseline -----------------------------

def test_baseline_accepts_none_timeout_ms():
    assert _accepted(_baseline(), dict(timeout_ms=None)) is True, \
        "baseline unexpectedly rejects timeout_ms=None"


def test_baseline_accepts_negative_timeout_seconds():
    assert _accepted(_baseline(), dict(timeout_seconds=-1)) is True, \
        "baseline unexpectedly rejects timeout_seconds=-1"


def test_baseline_accepts_none_name():
    assert _accepted(_baseline(), dict(name=None)) is True, \
        "baseline unexpectedly rejects name=None"


def test_baseline_artifacts_are_unchanged():
    before = hashlib.sha256(BASELINE_PATH.read_bytes()).hexdigest()
    assert before == "657bb2e1937c2936435f67649492eb396997335d1334e668852adfae64bf2adf"
    _baseline()
    after = hashlib.sha256(BASELINE_PATH.read_bytes()).hexdigest()
    assert before == after


# --- candidate repairs the recorded defects ---------------------------------

def test_candidate_rejects_none_timeout_ms():
    _raises(_candidate(), dict(timeout_ms=None))


def test_candidate_rejects_negative_timeout_seconds():
    _raises(_candidate(), dict(timeout_seconds=-1), (ValueError,))


def test_candidate_rejects_none_name():
    _raises(_candidate(), dict(name=None))


# --- parameterized candidate validation --------------------------------------

INVALID_SETTINGS = [
    dict(timeout_ms=None),
    dict(timeout_ms=True),
    dict(timeout_ms=False),
    dict(timeout_ms=-1),
    dict(timeout_ms=-1000),
    dict(timeout_ms=1.5),
    dict(timeout_ms="1000"),
    dict(timeout_ms=[1000]),
    dict(timeout_seconds=-1),
    dict(timeout_seconds=-0.5),
    dict(timeout_seconds=float("nan")),
    dict(timeout_seconds=float("inf")),
    dict(timeout_seconds=float("-inf")),
    dict(timeout_seconds=True),
    dict(timeout_seconds=False),
    dict(timeout_seconds=None),
    dict(timeout_seconds="30"),
    dict(name=None),
    dict(name=17),
    dict(name=True),
    dict(name=["x"]),
    dict(retries=-1),
    dict(retries=True),
    dict(retries=1.5),
    dict(retries=None),
    dict(timeout_ms=1000, timeout_seconds=1),
    dict(timeout_ms=1000, timeout_seconds=1.0),
    dict(timeout_ms=0, timeout_seconds=0),
    dict(extra=1),
    dict(timeout_millis=10),
]


@pytest.mark.parametrize("mapping", INVALID_SETTINGS)
def test_candidate_rejects_invalid_settings(mapping):
    _raises(_candidate(), mapping)


VALID_SETTINGS = [
    dict(),
    dict(name="worker"),
    dict(name="  worker  "),
    dict(name="   "),
    dict(name="worker", retries=3),
    dict(timeout_seconds=0),
    dict(timeout_seconds=2.5),
    dict(timeout_seconds=30),
    dict(timeout_ms=0),
    dict(timeout_ms=2500),
    dict(timeout_ms=1949),
    dict(timeout_ms=2500, retries=2),
]


@pytest.mark.parametrize("mapping", VALID_SETTINGS)
def test_candidate_accepts_valid_settings(mapping):
    result = _candidate().normalize_settings(mapping)
    assert isinstance(result, dict)
    assert set(result) == set(DEFAULTS)


def test_candidate_defaults_for_missing_keys():
    module = _candidate()
    assert module.normalize_settings(dict()) == DEFAULTS
    assert module.normalize_settings(dict(name=" x ")) == dict(
        name="x", timeout_seconds=30, retries=0)
    assert module.normalize_settings(dict(retries=2)) == dict(
        name="default", timeout_seconds=30, retries=2)


def test_candidate_values_and_stripping():
    module = _candidate()
    assert module.normalize_settings(dict(name=" X ", timeout_seconds=4)) == dict(
        name="X", timeout_seconds=4, retries=0)
    assert module.normalize_settings(dict(name="   "))["name"] == "default"
    assert module.normalize_settings(dict(timeout_ms=2500))["timeout_seconds"] == 2.5
    assert module.normalize_settings(dict(timeout_ms=1949))["timeout_seconds"] == 1.949
    assert module.normalize_settings(dict(timeout_ms=0))["timeout_seconds"] == 0


# --- nonmutation, idempotency, generators and independent copies -------------

def test_candidate_does_not_mutate_input():
    module = _candidate()
    source = dict(name=" A ", timeout_ms=3721, retries=2)
    copy = dict(source)
    module.normalize_settings(source)
    assert source == copy


def test_candidate_output_is_idempotent():
    module = _candidate()
    for mapping in (dict(), dict(name=" X "), dict(timeout_ms=3721, retries=2),
                    dict(name="y", timeout_seconds=1.5)):
        once = module.normalize_settings(mapping)
        assert module.normalize_settings(once) == once


def test_candidate_migrate_many_preserves_order_and_supports_generators():
    module = _candidate()
    expected = [
        dict(name="default", timeout_seconds=30, retries=0),
        dict(name="B", timeout_seconds=30, retries=0),
        dict(name="default", timeout_seconds=2.5, retries=1),
    ]
    inputs = [dict(), dict(name=" B "), dict(timeout_ms=2500, retries=1)]
    assert module.migrate_many(inputs) == expected
    assert module.migrate_many(item for item in inputs) == expected


def test_candidate_migrate_many_returns_independent_dictionaries():
    module = _candidate()
    original = dict(name=" X ", timeout_ms=3721, retries=2)
    batch = module.migrate_many(item for item in [original, original])
    assert len(batch) == 2
    assert batch[0] == batch[1]
    assert batch[0] is not batch[1]
    batch[0]["name"] = "changed"
    assert batch[1]["name"] == "X"
    assert original == dict(name=" X ", timeout_ms=3721, retries=2)


def test_candidate_is_stdlib_only_and_has_expected_api():
    module = _candidate()
    assert callable(module.normalize_settings)
    assert callable(module.migrate_many)
    source = CANDIDATE_PATH.read_text()
    for forbidden in ("import requests", "import numpy", "import torch",
                      "urllib.request", "socket.socket"):
        assert forbidden not in source


def test_candidate_large_integer_seconds_are_finite():
    module = _candidate()
    result = module.normalize_settings(dict(timeout_seconds=10**400))
    assert result == dict(name="default", timeout_seconds=10**400, retries=0)
    assert module.normalize_settings(result) == result


def test_candidate_large_negative_integer_seconds_are_rejected():
    _raises(_candidate(), dict(timeout_seconds=-(10**400)), (ValueError,))


@pytest.mark.parametrize("invalid", [dict(timeout_ms=None), dict(timeout_seconds=-1), dict(name=None)])
def test_candidate_batch_validates_recorded_defects_without_mutation(invalid):
    original = dict(invalid)
    with pytest.raises((TypeError, ValueError)):
        _candidate().migrate_many(item for item in [dict(), invalid])
    assert invalid == original


def test_candidate_rejects_conflicting_units_even_when_none():
    with pytest.raises(ValueError):
        _candidate().normalize_settings(dict(timeout_ms=None, timeout_seconds=None))


def test_candidate_batch_consumes_one_shot_iterable_once():
    class Once:
        used = False

        def __iter__(self):
            assert not self.used
            self.used = True
            yield dict(name=" A ")
            yield dict(timeout_ms=2500)

    assert _candidate().migrate_many(Once()) == [
        dict(name="A", timeout_seconds=30, retries=0),
        dict(name="default", timeout_seconds=2.5, retries=0),
    ]
