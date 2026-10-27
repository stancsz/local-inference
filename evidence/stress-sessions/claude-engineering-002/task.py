import math

def _validate_bound(name, bound):
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise TypeError(f'{name} must be an int or float')
    if not math.isfinite(bound):
        raise ValueError(f'{name} must be finite')

def _validate_bounds(lower, upper):
    _validate_bound('lower', lower)
    _validate_bound('upper', upper)
    if lower > upper:
        raise ValueError('lower must not exceed upper')

def clamp(value, lower=0, upper=100):
    _validate_bound('value', value)
    if not math.isfinite(value):
        raise ValueError('value must be finite')
    _validate_bounds(lower, upper)
    return max(lower, min(value, upper))

def _clamp_values(iterable, lower, upper):
    values = [clamp(v, lower, upper) for v in iterable]
    return values

def clamp_all(iterable, lower=0, upper=100):
    _validate_bounds(lower, upper)
    return _clamp_values(iterable, lower, upper)

def clamp_report(iterable, lower=0, upper=100):
    _validate_bounds(lower, upper)
    values = _clamp_values(iterable, lower, upper)
    if not values:
        return {'count': 0, 'min': None, 'max': None, 'sum': 0}
    return {'count': len(values), 'min': min(values), 'max': max(values), 'sum': sum(values)}
