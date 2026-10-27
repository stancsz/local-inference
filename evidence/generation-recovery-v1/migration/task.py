import math

_ALLOWED_KEYS = ('name', 'timeout_ms', 'timeout_seconds', 'retries')

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
    if name is None:
        result['name'] = 'default'
    elif not isinstance(name, str):
        raise TypeError('name must be a string')
    else:
        stripped = name.strip()
        result['name'] = stripped if stripped else 'default'
    timeout_ms = mapping.get('timeout_ms')
    timeout_seconds = mapping.get('timeout_seconds')
    if 'timeout_ms' in mapping or 'timeout_seconds' in mapping:
        if 'timeout_ms' in mapping and 'timeout_seconds' in mapping:
            raise ValueError('timeout_ms and timeout_seconds cannot both be set')
        if 'timeout_ms' in mapping:
            if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int):
                raise TypeError('timeout_ms must be a nonnegative integer')
            if timeout_ms < 0:
                raise ValueError('timeout_ms must be a nonnegative integer')
            result['timeout_seconds'] = timeout_ms / 1000
        else:
            if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
                raise TypeError('timeout_seconds must be a nonnegative finite number')
            if not math.isfinite(timeout_seconds) or timeout_seconds < 0:
                raise ValueError('timeout_seconds must be a nonnegative finite number')
            result['timeout_seconds'] = timeout_seconds
    else:
        result['timeout_seconds'] = 30
    retries = mapping.get('retries')
    if retries is None:
        result['retries'] = 0
    elif isinstance(retries, bool) or not isinstance(retries, int):
        raise ValueError('retries must be a nonnegative integer')
    elif retries < 0:
        raise ValueError('retries must be a nonnegative integer')
    else:
        result['retries'] = retries
    return result

def migrate_many(iterable):
    return (normalize_settings(m) for m in iterable)
