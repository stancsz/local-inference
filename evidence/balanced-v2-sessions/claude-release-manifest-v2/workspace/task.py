import json
import string
from pathlib import Path

_ALLOWED_KEYS = frozenset({'path', 'size_bytes', 'sha256', 'component'})
_HEX_CHARS = frozenset(string.hexdigits)


def _validate_path(path):
    if not isinstance(path, str) or path == '':
        raise ValueError('path must be nonempty relative POSIX text')
    if path.startswith('/'):
        raise ValueError('path must be relative')
    if '\\' in path:
        raise ValueError('path must not contain backslashes')
    segments = path.split('/')
    for segment in segments:
        if segment == '':
            raise ValueError('path must not contain empty segments')
        if segment in ('.', '..'):
            raise ValueError('path must not contain . or .. segments')
    return path


def _validate_record(record):
    if not isinstance(record, dict):
        raise ValueError('record must be a dict')
    keys = set(record.keys())
    if keys - _ALLOWED_KEYS:
        raise ValueError('record contains unknown keys')
    for required in ('path', 'size_bytes', 'sha256'):
        if required not in keys:
            raise ValueError('record missing required key: %s' % required)

    path = _validate_path(record['path'])

    size_bytes = record['size_bytes']
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int):
        raise ValueError('size_bytes must be a nonnegative int')
    if size_bytes < 0:
        raise ValueError('size_bytes must be nonnegative')

    sha256 = record['sha256']
    if not isinstance(sha256, str) or len(sha256) != 64:
        raise ValueError('sha256 must be exactly 64 characters')
    if not all(c in _HEX_CHARS for c in sha256):
        raise ValueError('sha256 must be hexadecimal')

    component = 'app'
    if 'component' in keys:
        component = record['component']
        if not isinstance(component, str) or component.strip() == '':
            raise ValueError('component must be a nonempty string')
        component = component.strip()

    return path, size_bytes, component


def _index_records(records):
    index = {}
    for record in records:
        path, size_bytes, component = _validate_record(record)
        if path in index:
            raise ValueError('duplicate path')
        index[path] = (size_bytes, record['sha256'].lower(), component)
    return index


def audit_manifest(records):
    files = 0
    total_bytes = 0
    components = {}
    seen_paths = set()
    for record in records:
        path, size_bytes, component = _validate_record(record)
        if path in seen_paths:
            raise ValueError('duplicate path')
        seen_paths.add(path)
        files += 1
        total_bytes += size_bytes
        bucket = components.setdefault(component, {'files': 0, 'bytes': 0})
        bucket['files'] += 1
        bucket['bytes'] += size_bytes
    return {
        'files': files,
        'bytes': total_bytes,
        'components': components,
        'paths': sorted(seen_paths),
    }


def compare_manifests(old, new):
    old_index = _index_records(old)
    new_index = _index_records(new)
    old_paths = set(old_index)
    new_paths = set(new_index)
    return {
        'added': sorted(new_paths - old_paths),
        'removed': sorted(old_paths - new_paths),
        'changed': sorted(p for p in old_paths & new_paths if old_index[p] != new_index[p]),
    }


def audit_file(path):
    try:
        text = Path(path).read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError('could not read manifest file: %s' % exc) from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError('manifest file is not valid JSON: %s' % exc) from exc
    if not isinstance(data, list):
        raise ValueError('manifest root must be a JSON array')
    return audit_manifest(data)


def render_markdown(report):
    lines = ['# Release manifest', '', 'Files: %d' % report['files'], 'Bytes: %d' % report['bytes']]
    for component, bucket in report['components'].items():
        lines.append('')
        lines.append('## %s' % component)
        lines.append('Files: %d' % bucket['files'])
        lines.append('Bytes: %d' % bucket['bytes'])
    return '\n'.join(lines) + '\n'
