import math

def _validate_bound(bound):
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise TypeError("bound must be int or float")
    if not math.isfinite(bound):
        raise ValueError("bound must be finite")

def clamp(value, lower=0, upper=100):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be int or float")
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    _validate_bound(lower)
    _validate_bound(upper)
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    return max(lower, min(upper, value))

def clamp_all(iterable, lower=0, upper=100):
    return [clamp(v, lower, upper) for v in list(iterable)]

def clamp_report(iterable, lower=0, upper=100):
    items = list(iterable)
    values = [clamp(v, lower, upper) for v in items]
    count = len(values)
    if count == 0:
        return {'count': 0, 'min': None, 'max': None, 'sum': 0}
    return {'count': count, 'min': min(values), 'max': max(values), 'sum': sum(values)}
