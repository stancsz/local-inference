import math

def _validate_bound(bound, name):
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise TypeError(name + " must be an int or float, not " + type(bound).__name__)
    if not math.isfinite(bound):
        raise ValueError(name + " must be finite")

def clamp(value, lower=0, upper=100):
    _validate_bound(lower, "lower")
    _validate_bound(upper, "upper")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be an int or float, not " + type(value).__name__)
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    return max(lower, min(value, upper))

def clamp_all(iterable, lower=0, upper=100):
    _validate_bound(lower, "lower")
    _validate_bound(upper, "upper")
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    values = [clamp(v, lower, upper) for v in iterable]
    return values

def clamp_report(iterable, lower=0, upper=100):
    _validate_bound(lower, "lower")
    _validate_bound(upper, "upper")
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    values = clamp_all(iterable, lower, upper)
    if not values:
        return {"count": 0, "min": None, "max": None, "sum": 0}
    return {"count": len(values), "min": min(values), "max": max(values), "sum": sum(values)}
