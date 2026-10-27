def audit_manifest(records):
    import re

def _validate_record(record):
    import re

    allowed_keys = {'path', 'size_bytes', 'sha256', 'component'}
    if not isinstance(record, dict):
        raise ValueError('record must be a dict')
    unknown = set(record) - allowed_keys
    if unknown:
        raise ValueError('unknown keys: %s' % sorted(unknown))
    missing = allowed_keys - {'component'} - set(record)
    if missing:
        raise ValueError('missing keys: %s' % sorted(missing))

    path = record['path']
    if not isinstance(path, str) or path == '':
        raise ValueError('path must be nonempty relative POSIX text')
    if '\\' in path or path.startswith('/'):
        raise ValueError('path must be relative POSIX text')
    segments = path.split('/')
    if any(seg == '' or seg == '.' or seg == '..' for seg in segments):
        raise ValueError('path contains empty, ".", or ".." segment')

    size_bytes = record['size_bytes']
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
        raise ValueError('size_bytes must be a nonnegative int')

    sha256 = record['sha256']
    if not isinstance(sha256, str) or len(sha256) != 64 or not re.fullmatch(r'[0-9a-fA-F]{64}', sha256):
        raise ValueError('sha256 must be exactly 64 hexadecimal characters')

    if 'component' in record:
        component = record['component']
        if not isinstance(component, str) or component.strip() == '':
            raise ValueError('component must be a nonempty string')
        component = component.strip()
    else:
        component = 'app'
    return path, size_bytes, sha256.lower(), component

def _index_records(records):
    index = {}
    for record in records:
        path, size_bytes, sha_lower, component = _validate_record(record)
        if path in index:
            raise ValueError('duplicate path')
        index[path] = (size_bytes, sha_lower, component)
    return index

def compare_manifests(old, new):
    old_index = _index_records(old)
    new_index = _index_records(new)
    old_paths = set(old_index)
    new_paths = set(new_index)
    added = sorted(new_paths - old_paths)
    removed = sorted(old_paths - new_paths)
    changed = sorted(p for p in old_paths & new_paths if old_index[p] != new_index[p])
    return {'added': added, 'removed': removed, 'changed': changed}

def audit_file(path):
    import json
    from pathlib import Path
    try:
        text = Path(path).read_text(encoding='utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError('file must be valid UTF-8') from exc
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError('invalid JSON') from exc
    if not isinstance(data, list):
        raise ValueError('JSON root must be an array')
    return audit_manifest(data)

def audit_manifest(records):
    import re

    files = 0
    bytes_total = 0
    components = {}
    seen_paths = set()

    for record in records:
        path, size_bytes, _sha_lower, component = _validate_record(record)
        if path in seen_paths:
            raise ValueError('duplicate path')
        seen_paths.add(path)

        files += 1
        bytes_total += size_bytes
        if component not in components:
            components[component] = {'files': 0, 'bytes': 0}
        components[component]['files'] += 1
        components[component]['bytes'] += size_bytes

    return {
        'files': files,
        'bytes': bytes_total,
        'components': components,
        'paths': sorted(seen_paths),
    }

def render_markdown(report):
    lines = ['# Release manifest', '', 'Files: %d' % report['files'], 'Bytes: %d' % report['bytes'], '']
    for component, stats in report['components'].items():
        lines.append('%s: %d files, %d bytes' % (component, stats['files'], stats['bytes']))
    return '\n'.join(lines) + '\n'
