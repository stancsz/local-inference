"""Prospective workload oracles are checked before any native model attempt."""
import ast
import io
import json
import math
from pathlib import Path
import sys
import types
import unittest

import pytest

from stress.supplement_tasks_v1 import TASKS, initial_source, stage


def incident_reference():
    def audit_events(text):
        if not isinstance(text, str): raise ValueError('text')
        report = dict(count=0, ok=0, errors=0, total_duration_ms=0, services={})
        for line in text.splitlines():
            if not line.strip(): continue
            try:
                row = json.loads(line)
                service, status, duration = row['service'], row['status'], row['duration_ms']
            except (ValueError, TypeError, KeyError): raise ValueError('record')
            if not isinstance(service, str) or not service.strip() or status not in ('ok', 'error'): raise ValueError('fields')
            if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration < 0 or isinstance(duration, float) and not math.isfinite(duration): raise ValueError('duration')
            group = report['services'].setdefault(service.strip(), dict(count=0, errors=0, duration_ms=0))
            report['count'] += 1
            report['ok'] += status == 'ok'
            report['errors'] += status == 'error'
            report['total_duration_ms'] += duration
            group['count'] += 1
            group['errors'] += status == 'error'
            group['duration_ms'] += duration
        return report
    def render(report):
        return '# Incident summary\n' + '\n'.join([f"Count: {report['count']}", f"OK: {report['ok']}", f"Errors: {report['errors']}", *report['services']])
    return types.SimpleNamespace(audit_events=audit_events, audit_file=lambda path: audit_events(Path(path).read_text(encoding='utf-8')), render_markdown=render)


def manifest_reference():
    def normalized(records):
        result = {}
        try:
            for row in records:
                if not isinstance(row, dict) or set(row) - {'path', 'size_bytes', 'sha256', 'component'}: raise ValueError('record')
                path, size, digest = row['path'], row['size_bytes'], row['sha256']
                component = row.get('component', 'app')
                if not isinstance(path, str) or path.startswith('/') or '\\' in path or any(p in ('', '.', '..') for p in path.split('/')) or path in result: raise ValueError('path')
                if type(size) is not int or size < 0: raise ValueError('size')
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest.lower()): raise ValueError('hash')
                if not isinstance(component, str) or not component.strip(): raise ValueError('component')
                result[path] = size, digest.lower(), component.strip()
        except (TypeError, KeyError): raise ValueError('manifest')
        return result
    def audit_manifest(records):
        normalized_rows = normalized(records)
        groups = {}
        for size, digest, component in normalized_rows.values():
            group = groups.setdefault(component, dict(files=0, bytes=0))
            group['files'] += 1
            group['bytes'] += size
        return dict(files=len(normalized_rows), bytes=sum(r[0] for r in normalized_rows.values()), components=groups, paths=sorted(normalized_rows))
    def compare(old, new):
        a, b = normalized(old), normalized(new)
        return dict(added=sorted(b.keys()-a.keys()), removed=sorted(a.keys()-b.keys()), changed=sorted(p for p in a.keys() & b.keys() if a[p] != b[p]))
    def audit_file(path):
        rows = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(rows, list): raise ValueError('root')
        return audit_manifest(rows)
    def render(report):
        return '# Release manifest\n' + '\n'.join([f"Files: {report['files']}", f"Bytes: {report['bytes']}", *report['components']])
    return types.SimpleNamespace(audit_manifest=audit_manifest, compare_manifests=compare, audit_file=audit_file, render_markdown=render)


def run_definition(definition, implementation, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, 'task', implementation)
    (tmp_path / 'evidence.json').write_text(json.dumps({'acceptance_delay_seconds': 12345}))
    namespace = {'__name__': 'oracle_test'}
    exec(compile(definition['tests'], 'supplement-test', 'exec'), namespace)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(namespace['Acceptance'])
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream).run(suite)
    return result, stream.getvalue()


@pytest.mark.parametrize('task', TASKS)
@pytest.mark.parametrize('number', range(9))
def test_each_stage_accepts_reference_and_has_distinct_hidden_data(task, number, tmp_path, monkeypatch):
    public = stage(task, number, 2026102701 + number)
    hidden = stage(task, number, 2026102701 + number + 100003)
    assert public == stage(task, number, 2026102701 + number)
    assert public['tests'] != hidden['tests']
    reference = incident_reference() if task == 'incident_log' else manifest_reference()
    for definition in (public, hidden):
        checked, output = run_definition(definition, reference, tmp_path, monkeypatch)
        assert checked.wasSuccessful(), output
    broken = types.ModuleType('broken')
    exec(initial_source(task), broken.__dict__)
    checked, output = run_definition(public, broken, tmp_path, monkeypatch)
    assert not checked.wasSuccessful()


def test_full_stages_detect_false_success_and_invalid_inputs(tmp_path, monkeypatch):
    for task in TASKS:
        stub = types.SimpleNamespace(audit_events=lambda text: {}, audit_manifest=lambda rows: {})
        checked, output = run_definition(stage(task, 8, 2026102702), stub, tmp_path, monkeypatch)
        assert not checked.wasSuccessful()


@pytest.mark.parametrize('args', [('bad', 0, 1), ('incident_log', -1, 1), ('incident_log', True, 1), ('release_manifest', 1, True)])
def test_definition_rejects_invalid_inputs(args):
    with pytest.raises(ValueError): stage(*args)


def test_driver_preserves_frozen_run_acceptance():
    root = Path(__file__).resolve().parents[1]
    old = ast.parse((root / 'stress/cli_campaign.py').read_text(encoding='utf-8'))
    new = ast.parse((root / 'stress/supplement_campaign_v1.py').read_text(encoding='utf-8'))
    a = next(node for node in old.body if isinstance(node, ast.FunctionDef) and node.name == 'run')
    b = next(node for node in new.body if isinstance(node, ast.FunctionDef) and node.name == 'run')
    for node in ast.walk(b):
        if isinstance(node, ast.ImportFrom) and node.module == 'stress.supplement_tasks_v1':
            node.module = 'stress.acceptance_tasks'
        if isinstance(node, ast.Constant) and node.value == 'Use the explicitly authorized 127.0.0.1:8090/v1 route':
            node.value = 'Use the explicitly authorized 127.0.0.1:4000/v1 route'
    assert ast.dump(a) == ast.dump(b)
