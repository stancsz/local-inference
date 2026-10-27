_ALLOWED_KEYS = {'name', 'timeout_ms', 'timeout_seconds', 'retries'}

def normalize_settings(settings):
    normalized = dict(settings)
    unknown = set(normalized) - _ALLOWED_KEYS
    if unknown:
        raise ValueError('unknown keys: %s' % ', '.join(sorted(unknown)))
    name = normalized.pop('name', None)
    timeout_ms = normalized.pop('timeout_ms', None)
    timeout_seconds = normalized.pop('timeout_seconds', None)
    if timeout_ms is not None and timeout_seconds is not None:
        raise ValueError('timeout_ms and timeout_seconds cannot both be provided')
    if timeout_ms is not None:
        if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or timeout_ms < 0:
            raise ValueError('timeout_ms must be a nonnegative integer')
        timeout_seconds = timeout_ms / 1000
    if timeout_seconds is not None:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds < 0:
            raise ValueError('timeout_seconds must be a nonnegative number')
    if name is None:
        name = 'default'
    else:
        if not isinstance(name, str):
            raise ValueError('name must be a string')
        name = name.strip()
        if not name:
            name = 'default'
    if timeout_seconds is None:
        timeout_seconds = 30
    normalized['name'] = name
    normalized['timeout_seconds'] = timeout_seconds
    if 'retries' not in normalized:
        normalized['retries'] = 0
    else:
        retries = normalized['retries']
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise ValueError('retries must be a nonnegative integer')
    return normalized

def migrate_many(iterable):
    return [normalize_settings(item) for item in iterable]
