"""Deterministic migration-settings recovery fixture (version 1).

Separately versioned code-repair artifact. It is NOT a retroactive pass of any
recorded model attempt and NOT evidence that any model learned the fixes.
Pure stdlib: math only. No I/O, no globals mutated, deterministic.

Contract (see stress/acceptance_tasks.py and stress/contract_probe.py, both
frozen and unmodified):

* Accepted keys are exactly: name, timeout_ms, timeout_seconds, retries.
  Any other key raises ValueError.
* Missing keys receive defaults: name='default', timeout_seconds=30,
  retries=0.
* A key that is present but holds None is invalid; only a missing key gets a
  default. timeout_ms=None, timeout_seconds=None and name=None are rejected.
* timeout_ms and timeout_seconds are mutually exclusive; supplying both is
  rejected even when the two values are equal.
* timeout_ms must be a nonnegative int (bool excluded).
* timeout_seconds must be a nonnegative finite int or float (bool excluded).
* name must be a string; it is stripped and an empty result becomes
  'default'.
* retries must be a nonnegative int (bool excluded).
* Inputs are never mutated and normalized output is idempotent.
* migrate_many(iterable) preserves order, accepts generators and returns
  independent dictionaries.
"""

import math

__all__ = ["normalize_settings", "migrate_many"]

_ALLOWED_KEYS = frozenset(("name", "timeout_ms", "timeout_seconds", "retries"))
_DEFAULT_NAME = "default"
_DEFAULT_TIMEOUT_SECONDS = 30
_DEFAULT_RETRIES = 0


def _validate_name(value):
    if not isinstance(value, str):
        raise TypeError("name must be a string")
    stripped = value.strip()
    return stripped if stripped else _DEFAULT_NAME


def _validate_milliseconds(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("timeout_ms must be an integer number of milliseconds")
    if value < 0:
        raise ValueError("timeout_ms must be nonnegative")
    return value / 1000


def _validate_seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("timeout_seconds must be a number of seconds")
    # Python integers are finite; float conversion can overflow for large ints.
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("timeout_seconds must be finite")
    if value < 0:
        raise ValueError("timeout_seconds must be nonnegative")
    return value


def _validate_retries(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("retries must be an integer")
    if value < 0:
        raise ValueError("retries must be nonnegative")
    return value


def normalize_settings(mapping):
    """Return a validated, normalized settings dictionary for mapping."""
    try:
        items = list(mapping.items())
    except AttributeError:
        raise TypeError("settings must be a mapping")
    for key, _value in items:
        if key not in _ALLOWED_KEYS:
            raise ValueError("unknown key: %s" % (key,))

    has_ms = any(key == "timeout_ms" for key, _value in items)
    has_seconds = any(key == "timeout_seconds" for key, _value in items)
    if has_ms and has_seconds:
        raise ValueError("timeout_ms and timeout_seconds cannot both be set")

    source = dict(items)

    if "name" in source:
        name = _validate_name(source["name"])
    else:
        name = _DEFAULT_NAME

    if has_ms:
        timeout_seconds = _validate_milliseconds(source["timeout_ms"])
    elif has_seconds:
        timeout_seconds = _validate_seconds(source["timeout_seconds"])
    else:
        timeout_seconds = _DEFAULT_TIMEOUT_SECONDS

    if "retries" in source:
        retries = _validate_retries(source["retries"])
    else:
        retries = _DEFAULT_RETRIES

    return dict(name=name, timeout_seconds=timeout_seconds, retries=retries)


def migrate_many(iterable):
    """Return normalized dictionaries for every mapping in iterable, in order."""
    return [normalize_settings(item) for item in iterable]
