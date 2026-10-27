_ALLOWED_KEYS = {'name', 'timeout_ms', 'timeout_seconds', 'retries'}

def normalize_settings(mapping):
    for key in mapping:
        if key not in _ALLOWED_KEYS:
            raise ValueError(f'unknown key: {key}')
    result = dict(mapping)
    name = result.pop('name', None)
    if name is None:
        result['name'] = 'default'
    else:
        if not isinstance(name, str):
            raise TypeError('name must be a string')
        stripped = name.strip()
        result['name'] = stripped if stripped else 'default'
    timeout_ms = result.pop('timeout_ms', None)
    if timeout_ms is not None:
        if 'timeout_seconds' in result:
            raise ValueError('timeout_ms and timeout_seconds cannot both be set')
        if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or timeout_ms < 0:
            raise ValueError('timeout_ms must be a nonnegative integer')
        result['timeout_seconds'] = timeout_ms / 1000
    if 'timeout_seconds' not in result:
        result['timeout_seconds'] = 30
    if 'retries' not in result:
        result['retries'] = 0
    else:
        retries = result['retries']
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise ValueError('retries must be a nonnegative integer')
    return result

def migrate_many(iterable):
    return [normalize_settings(m) for m in iterable]
