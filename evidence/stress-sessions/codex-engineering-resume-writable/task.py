import math


def _validate_bound(name, bound):
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise TypeError(f"{name} must be an int or float")
    if not math.isfinite(bound):
        raise ValueError(f"{name} must be finite")


def clamp(value, lower=0, upper=100):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be an int or float")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    _validate_bound("lower", lower)
    _validate_bound("upper", upper)
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    return max(lower, min(value, upper))


def clamp_all(iterable, lower=0, upper=100):
    _validate_bound("lower", lower)
    _validate_bound("upper", upper)
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    return [clamp(x, lower, upper) for x in iterable]


def clamp_report(iterable, lower=0, upper=100):
    values = clamp_all(iterable, lower, upper)
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "sum": sum(values),
    }
