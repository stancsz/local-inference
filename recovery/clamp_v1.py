"""Deterministic clamp recovery fixture (version 1).

Separately versioned code-repair artifact. It is NOT a retroactive pass of any
recorded model attempt and NOT evidence that any model learned the fixes.
Pure stdlib: math only. No I/O, no globals mutated, deterministic.

Contract:

* clamp(value, lower=0, upper=100) clamps inclusively into [lower, upper].
* clamp_all(iterable, ...) returns the clamped values in input order.
* clamp_report(iterable, ...) returns count/min/max/sum.
* BOTH bounds are validated before any input is processed, so malformed
  bounds are rejected even for empty iterables:

  - bounds must be non-bool int/float  -> TypeError
  - bounds must be finite              -> ValueError
  - lower must not exceed upper        -> ValueError

* values must be non-bool int/float     -> TypeError
* values must be finite                -> ValueError
* inputs are never mutated; iterators/generators are consumed once.
"""

import math

__all__ = ["clamp", "clamp_all", "clamp_report"]


def _validate_bound(bound, name):
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise TypeError("%s must be int or float" % (name,))
    # Integers are finite; converting large integers to float can overflow.
    if isinstance(bound, float) and not math.isfinite(bound):
        raise ValueError("%s must be finite" % (name,))


def _validate_bounds(lower, upper):
    """Shared validation of both bounds; raises before any input is read."""
    _validate_bound(lower, "lower")
    _validate_bound(upper, "upper")
    if lower > upper:
        raise ValueError("lower must not exceed upper")


def _validate_value(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be int or float")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("value must be finite")


def clamp(value, lower=0, upper=100):
    """Return value clamped inclusively into [lower, upper]."""
    _validate_value(value)
    _validate_bounds(lower, upper)
    return max(lower, min(upper, value))


def clamp_all(iterable, lower=0, upper=100):
    """Return the list of clamped values, preserving input order."""
    _validate_bounds(lower, upper)
    return [clamp(item, lower, upper) for item in list(iterable)]


def clamp_report(iterable, lower=0, upper=100):
    """Return count/min/max/sum over the clamped values."""
    _validate_bounds(lower, upper)
    values = [clamp(item, lower, upper) for item in list(iterable)]
    count = len(values)
    if count == 0:
        return {"count": 0, "min": None, "max": None, "sum": 0}
    return {"count": count, "min": min(values), "max": max(values), "sum": sum(values)}
