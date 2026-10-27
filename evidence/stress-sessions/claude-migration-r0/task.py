_ALLOWED_KEYS = {'name', 'timeout_ms', 'timeout_seconds', 'retries'}

def normalize_settings(settings):
    result = dict(settings)
    unknown = set(result) - _ALLOWED_KEYS
    if unknown:
        raise ValueError(f"unknown keys: {', '.join(sorted(unknown))}")
    if 'name' in result:
        name = result['name']
        if not isinstance(name, str):
            raise TypeError('name must be a string')
        name = name.strip()
        result['name'] = name if name else 'default'
    else:
        result['name'] = 'default'
    if 'timeout_ms' in result and 'timeout_seconds' in result:
        raise ValueError('timeout_ms and timeout_seconds cannot both be provided')
    if 'timeout_ms' in result:
        timeout_ms = result.pop('timeout_ms')
        if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int):
            raise TypeError('timeout_ms must be a nonnegative integer')
        if timeout_ms < 0:
            raise ValueError('timeout_ms must be nonnegative')
        result['timeout_seconds'] = timeout_ms / 1000
    if 'timeout_seconds' in result:
        timeout_seconds = result['timeout_seconds']
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise TypeError('timeout_seconds must be a nonnegative number')
        if timeout_seconds < 0:
            raise ValueError('timeout_seconds must be nonnegative')
    result.setdefault('timeout_seconds', 30)
    if 'retries' in result:
        retries = result['retries']
        if isinstance(retries, bool) or not isinstance(retries, int):
            raise TypeError('retries must be a nonnegative integer')
        if retries < 0:
            raise ValueError('retries must be nonnegative')
    else:
        result['retries'] = 0
    return result

def migrate_many(iterable):
    return [normalize_settings(item) for item in iterable]
