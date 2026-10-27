import json
import re

_HEX_RE = re.compile(r'^[0-9a-fA-F]{64}$')

def _validate_record(rec):
    if not isinstance(rec, dict):
        raise ValueError('record must be a dict')
    expected_keys = {'path', 'size_bytes', 'sha256', 'component'}
    actual_keys = set(rec.keys())
    if actual_keys != expected_keys and not (actual_keys <= expected_keys and {'path', 'size_bytes', 'sha256'} <= actual_keys):
        raise ValueError('invalid keys')
    extra = actual_keys - expected_keys
    if extra:
        raise ValueError('unknown key')
    for required in ('path', 'size_bytes', 'sha256'):
        if required not in rec:
            raise ValueError(f'missing key {required}')
    size = rec['size_bytes']
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError('invalid size_bytes')
    sha = rec['sha256']
    if not isinstance(sha, str) or not _HEX_RE.match(sha):
        raise ValueError('invalid sha256')
    path = rec['path']
    if not isinstance(path, str) or path == '':
        raise ValueError('invalid path')
    if '\\' in path or path.startswith('/'):
        raise ValueError('invalid path')
    segments = path.split('/')
    if any(seg == '' for seg in segments):
        raise ValueError('invalid path')
    if any(seg in ('.', '..') for seg in segments):
            raise ValueError('invalid path')
    if 'component' in rec:
        comp = rec['component']
        if not isinstance(comp, str) or comp.strip() == '':
            raise ValueError('invalid component')
        component = comp.strip()
    else:
        component = 'app'
    return path, size, component

def _index_records(records):
    index = {}
    for rec in records:
        path, size, component = _validate_record(rec)
        if path in index:
            raise ValueError('duplicate path')
        index[path] = (size, rec['sha256'].lower(), component)
    return index

def compare_manifests(old, new):
    old_idx = _index_records(old)
    new_idx = _index_records(new)
    old_paths = set(old_idx)
    new_paths = set(new_idx)
    added = sorted(new_paths - old_paths)
    removed = sorted(old_paths - new_paths)
    changed = sorted(p for p in old_paths & new_paths if old_idx[p] != new_idx[p])
    return {'added': added, 'removed': removed, 'changed': changed}

def audit_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError('root must be a list')
    return audit_manifest(data)

def render_markdown(report):
    lines = ['# Release manifest', '', f"Files: {report['files']}", f"Bytes: {report['bytes']}", '']
    for name, stats in report['components'].items():
        lines.append(f"- {name}: {stats['files']} files, {stats['bytes']} bytes")
    return '\n'.join(lines) + '\n'

def audit_manifest(records):
    files = 0
    bytes_ = 0
    components = {}
    paths = []
    seen = set()
    for rec in records:
        path, size, component = _validate_record(rec)
        if path in seen:
            raise ValueError('duplicate path')
        seen.add(path)
        files += 1
        bytes_ += size
        if component not in components:
            components[component] = {'files': 0, 'bytes': 0}
        components[component]['files'] += 1
        components[component]['bytes'] += size
        paths.append(path)
    return {
        'files': files,
        'bytes': bytes_,
        'components': components,
        'paths': sorted(paths),
    }
