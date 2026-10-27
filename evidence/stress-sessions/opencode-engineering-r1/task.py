import math

def _validate_bound(b, name):
    if isinstance(b, bool) or not isinstance(b, (int, float)):
        raise TypeError(f"{name} must be int or float")
    if not math.isfinite(b):
        raise ValueError(f"{name} must be finite")

def clamp(value, lower=0, upper=100):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be int or float")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    _validate_bound(lower, "lower")
    _validate_bound(upper, "upper")
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    return max(lower, min(value, upper))

def clamp_all(iterable, lower=0, upper=100):
    items = list(iterable)
    return [clamp(v, lower, upper) for v in items]

def clamp_report(iterable, lower=0, upper=100):
    items = list(iterable)
    values = [clamp(v, lower, upper) for v in items]
    if not values:
        return {'count': 0, 'min': None, 'max': None, 'sum': 0}
    return {'count': len(values), 'min': min(values), 'max': max(values), 'sum': sum(values)}
