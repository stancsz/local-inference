def normalize_settings(mapping):
    settings = dict(mapping)
    allowed = {'name', 'timeout_ms', 'timeout_seconds', 'retries'}
    unknown = set(settings) - allowed
    if unknown:
        raise ValueError(f'unknown keys: {sorted(unknown)}')
    if 'name' in settings:
        name = settings.pop('name')
        if not isinstance(name, str):
            raise TypeError('name must be a string')
        name = name.strip()
        if not name:
            name = 'default'
        settings['name'] = name
    if 'timeout_ms' in settings and 'timeout_seconds' in settings:
        raise ValueError('cannot specify both timeout_ms and timeout_seconds')
    if 'timeout_ms' in settings:
        ms = settings.pop('timeout_ms')
        if isinstance(ms, bool) or not isinstance(ms, int) or ms < 0:
            raise ValueError('timeout_ms must be a nonnegative integer')
        settings['timeout_seconds'] = ms / 1000
    if 'timeout_seconds' in settings:
        ts = settings['timeout_seconds']
        if isinstance(ts, bool) or not isinstance(ts, (int, float)) or ts < 0:
            raise ValueError('timeout_seconds must be nonnegative')
    if 'retries' in settings:
        r = settings['retries']
        if isinstance(r, bool) or not isinstance(r, int) or r < 0:
            raise ValueError('retries must be a nonnegative integer')
    settings.setdefault('name', 'default')
    settings.setdefault('timeout_seconds', 30)
    settings.setdefault('retries', 0)
    return settings

def migrate_many(iterable):
    return [normalize_settings(m) for m in iterable]
