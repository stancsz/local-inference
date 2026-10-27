import math

def _validate_bound(bound):
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise TypeError("bound must be int or float")
    if isinstance(bound, int):
        return
    if not math.isfinite(bound):
        raise ValueError("bound must be finite")

def _validate_bounds(lower, upper):
    _validate_bound(lower)
    _validate_bound(upper)
    if lower > upper:
        raise ValueError("lower must not exceed upper")

def _clamp_value(value, lower, upper):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be int or float")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("value must be finite")
    return max(lower, min(upper, value))

def clamp(value, lower=0, upper=100):
    _validate_bounds(lower, upper)
    return _clamp_value(value, lower, upper)

def clamp_all(iterable, lower=0, upper=100):
    _validate_bounds(lower, upper)
    return [_clamp_value(v, lower, upper) for v in iterable]

def clamp_report(iterable, lower=0, upper=100):
    _validate_bounds(lower, upper)
    values = [_clamp_value(v, lower, upper) for v in iterable]
    count = len(values)
    if count == 0:
        return {'count': 0, 'min': None, 'max': None, 'sum': 0}
    return {'count': count, 'min': min(values), 'max': max(values), 'sum': sum(values)}
