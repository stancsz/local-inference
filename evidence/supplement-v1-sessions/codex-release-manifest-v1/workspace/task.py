import json
import re
from pathlib import Path

_HEX64 = re.compile(r'[0-9a-fA-F]{64}')

def _validate_record(record):
    if not isinstance(record, dict):
        raise ValueError('record must be a dict')
    allowed = {'path', 'size_bytes', 'sha256', 'component'}
    unknown = set(record) - allowed
    if unknown:
        raise ValueError('unknown keys: %s' % sorted(unknown))
    missing = {'path', 'size_bytes', 'sha256'} - set(record)
    if missing:
        raise ValueError('missing keys: %s' % sorted(missing))

    path = record['path']
    if not isinstance(path, str):
        raise ValueError('path must be text')
    if path.startswith('/') or '\\' in path:
        raise ValueError('path must be relative POSIX text')
    segments = path.split('/')
    if any(segment in ('', '.', '..') for segment in segments):
        raise ValueError('path has empty, "." or ".." segments')

    size_bytes = record['size_bytes']
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int):
        raise ValueError('size_bytes must be an int')
    if size_bytes < 0:
        raise ValueError('size_bytes must be non-negative')

    sha256 = record['sha256']
    if not isinstance(sha256, str) or not _HEX64.fullmatch(sha256):
        raise ValueError('sha256 must be exactly 64 hexadecimal characters')

    component = record.get('component', 'app')
    if not isinstance(component, str) or not component.strip():
        raise ValueError('component must be a nonempty string')

def audit_manifest(records):
    files = 0
    bytes_total = 0
    components = {}
    seen_paths = set()
    for record in records:
        _validate_record(record)
        path = record['path']
        if path in seen_paths:
            raise ValueError('duplicate path')
        seen_paths.add(path)
        size_bytes = record['size_bytes']
        component = record['component'].strip() if 'component' in record else 'app'
        files += 1
        bytes_total += size_bytes
        entry = components.setdefault(component, {'files': 0, 'bytes': 0})
        entry['files'] += 1
        entry['bytes'] += size_bytes
    return {
        'files': files,
        'bytes': bytes_total,
        'components': components,
        'paths': sorted(seen_paths),
    }

def _index_manifest(records):
    entries = {}
    for record in records:
        _validate_record(record)
        path = record['path']
        if path in entries:
            raise ValueError('duplicate path')
        entries[path] = (
            record['size_bytes'],
            record['sha256'].lower(),
            record['component'].strip() if 'component' in record else 'app',
        )
    return entries

def compare_manifests(old, new):
    old_entries = _index_manifest(old)
    new_entries = _index_manifest(new)
    added = sorted(set(new_entries) - set(old_entries))
    removed = sorted(set(old_entries) - set(new_entries))
    changed = sorted(path for path in set(old_entries) & set(new_entries)
                     if old_entries[path] != new_entries[path])
    return {'added': added, 'removed': removed, 'changed': changed}

def audit_file(path):
    path = Path(path)
    try:
        raw = path.read_text(encoding='utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError('manifest must be UTF-8 JSON') from exc
    try:
        records = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError('manifest must be JSON') from exc
    if not isinstance(records, list):
        raise ValueError('manifest root must be a JSON array')
    return audit_manifest(records)
