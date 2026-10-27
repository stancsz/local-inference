import math

_ALLOWED_KEYS = ('name', 'timeout_ms', 'timeout_seconds', 'retries')

def _finite_number(value):
    if isinstance(value, bool):
        raise TypeError('timeout_seconds must be a nonnegative finite number')
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    raise TypeError('timeout_seconds must be a nonnegative finite number')

def normalize_settings(mapping):
    try:
        keys = list(mapping)
    except TypeError:
        raise TypeError('mapping must be a mapping')
    for key in keys:
        if key not in _ALLOWED_KEYS:
            raise ValueError(f'unknown key: {key}')
    result = {}
    name = mapping.get('name')
    if 'name' in mapping:
        if name is None:
            raise ValueError('name must not be None')
        if not isinstance(name, str):
            raise TypeError('name must be a string')
        stripped = name.strip()
        result['name'] = stripped if stripped else 'default'
    else:
        result['name'] = 'default'
    timeout_ms = mapping.get('timeout_ms')
    timeout_seconds = mapping.get('timeout_seconds')
    if 'timeout_ms' in mapping or 'timeout_seconds' in mapping:
        if 'timeout_ms' in mapping and 'timeout_seconds' in mapping:
            raise ValueError('timeout_ms and timeout_seconds cannot both be set')
        if 'timeout_ms' in mapping:
            if timeout_ms is None:
                raise ValueError('timeout_ms must not be None')
            if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int):
                raise TypeError('timeout_ms must be a nonnegative integer')
            if timeout_ms < 0:
                raise ValueError('timeout_ms must be a nonnegative integer')
            result['timeout_seconds'] = timeout_ms / 1000
        else:
            if timeout_seconds is None:
                raise ValueError('timeout_seconds must not be None')
            if not _finite_number(timeout_seconds):
                raise ValueError('timeout_seconds must be a nonnegative finite number')
            if timeout_seconds < 0:
                raise ValueError('timeout_seconds must be a nonnegative finite number')
            result['timeout_seconds'] = timeout_seconds
    else:
        result['timeout_seconds'] = 30
    retries = mapping.get('retries')
    if 'retries' in mapping:
        if retries is None:
            raise ValueError('retries must not be None')
        if isinstance(retries, bool) or not isinstance(retries, int):
            raise TypeError('retries must be a nonnegative integer')
        if retries < 0:
            raise ValueError('retries must be a nonnegative integer')
        result['retries'] = retries
    else:
        result['retries'] = 0
    return result

def migrate_many(iterable):
    return [normalize_settings(m) for m in iterable]
