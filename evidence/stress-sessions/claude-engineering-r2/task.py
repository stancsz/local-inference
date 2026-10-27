import math


def _validate_bound(name, bound):
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise TypeError(f"{name} must be an int or float")
    if not math.isfinite(bound):
        raise ValueError(f"{name} must be finite")


def clamp(value, lower=0, upper=100):
    _validate_bound("lower", lower)
    _validate_bound("upper", upper)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be an int or float")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    return min(max(value, lower), upper)


def clamp_all(iterable, lower=0, upper=100):
    _validate_bound("lower", lower)
    _validate_bound("upper", upper)
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    values = list(iterable)
    return [clamp(v, lower, upper) for v in values]


def clamp_report(iterable, lower=0, upper=100):
    _validate_bound("lower", lower)
    _validate_bound("upper", upper)
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    values = [clamp(v, lower, upper) for v in iterable]
    if not values:
        return {"count": 0, "min": None, "max": None, "sum": 0}
    return {"count": len(values), "min": min(values), "max": max(values), "sum": sum(values)}
