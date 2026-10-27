import math


def _validate_bound(bound):
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise TypeError("bound must be an int or float")
    if not math.isfinite(bound):
        raise ValueError("bound must be finite")


def clamp(value, lower=0, upper=100):
    _validate_bound(lower)
    _validate_bound(upper)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be an int or float")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    if value < lower:
        return lower
    if value > upper:
        return upper
    return value


def clamp_all(iterable, lower=0, upper=100):
    items = list(iterable)
    return [clamp(v, lower, upper) for v in items]


def clamp_report(iterable, lower=0, upper=100):
    values = clamp_all(iterable, lower, upper)
    count = len(values)
    if count == 0:
        return {"count": 0, "min": None, "max": None, "sum": 0}
    return {
        "count": count,
        "min": min(values),
        "max": max(values),
        "sum": sum(values),
    }
