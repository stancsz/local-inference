def normalize_settings(settings):
    normalized = dict(settings)
    allowed = {'name', 'timeout_ms', 'timeout_seconds', 'retries'}
    unknown = set(normalized) - allowed
    if unknown:
        raise ValueError(f'unknown settings keys: {", ".join(sorted(unknown))}')
    if 'name' in normalized:
        name = normalized['name']
        if not isinstance(name, str):
            raise TypeError('name must be a string')
        normalized['name'] = name.strip() or 'default'
    else:
        normalized['name'] = 'default'
    if 'timeout_ms' in normalized and 'timeout_seconds' in normalized:
        raise ValueError('timeout_ms and timeout_seconds cannot be used together')
    if 'timeout_ms' in normalized:
        timeout_ms = normalized.pop('timeout_ms')
        if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or timeout_ms < 0:
            raise ValueError('timeout_ms must be a nonnegative integer')
        normalized['timeout_seconds'] = timeout_ms / 1000
    if 'timeout_seconds' in normalized:
        timeout_seconds = normalized['timeout_seconds']
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds < 0:
            raise ValueError('timeout_seconds must be a nonnegative number')
    else:
        normalized['timeout_seconds'] = 30
    if 'retries' in normalized:
        retries = normalized['retries']
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise ValueError('retries must be a nonnegative integer')
    else:
        normalized['retries'] = 0
    return normalized


def migrate_many(iterable):
    return [normalize_settings(item) for item in iterable]
