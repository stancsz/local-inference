def normalize_settings(settings):
    normalized = dict(settings)
    unknown = set(normalized) - {'name', 'timeout_ms', 'timeout_seconds', 'retries'}
    if unknown:
        raise ValueError('unknown settings keys: %s' % ', '.join(sorted(unknown)))
    raw_name = normalized.pop('name', None)
    if raw_name is None:
        normalized['name'] = 'default'
    elif not isinstance(raw_name, str):
        raise TypeError('name must be a string')
    else:
        normalized['name'] = raw_name.strip() or 'default'
    if 'timeout_ms' in normalized:
        if 'timeout_seconds' in normalized:
            raise ValueError('timeout_ms and timeout_seconds are mutually exclusive')
        timeout_ms = normalized.pop('timeout_ms')
        if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int):
            raise TypeError('timeout_ms must be an integer')
        if timeout_ms < 0:
            raise ValueError('timeout_ms must be nonnegative')
        normalized['timeout_seconds'] = timeout_ms / 1000
    if 'timeout_seconds' in normalized and normalized['timeout_seconds'] < 0:
        raise ValueError('timeout_seconds must be nonnegative')
    normalized.setdefault('timeout_seconds', 30)
    retries = normalized.pop('retries', None)
    if retries is None:
        normalized['retries'] = 0
    elif isinstance(retries, bool) or not isinstance(retries, int):
        raise TypeError('retries must be an integer')
    elif retries < 0:
        raise ValueError('retries must be nonnegative')
    else:
        normalized['retries'] = retries
    return normalized


def migrate_many(items):
    return [normalize_settings(item) for item in items]
