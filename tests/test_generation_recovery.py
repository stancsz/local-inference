"""Policy checks for the opt-in, single-attempt generation harness."""
from pathlib import Path

import pytest

from recovery.generation_v1 import native_acceptance, validate, CASES, ROOT


def events(path):
    return [
        {'message': {'content': [{'type': 'tool_use', 'id': 'read', 'name': 'Read', 'input': {'file_path': str(path)}}]}},
        {'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'read', 'content': 'before'}]}},
        {'message': {'content': [{'type': 'tool_use', 'id': 'edit', 'name': 'Edit', 'input': {'file_path': str(path), 'old_string': 'before', 'new_string': 'after'}}]}},
        {'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'edit', 'content': 'updated'}]}},
        {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'DONE'},
    ]


def accept(trace, folder, before=b'before', after=b'after', code=0, timeout=False):
    return native_acceptance(trace, folder, before, after, code, timeout, 'DONE')


def test_completed_native_edits_bind_to_source(tmp_path):
    result = accept(events(tmp_path / 'task.py'), tmp_path)
    assert result['passed'] and result['native_edit_reconstruction_matches']


@pytest.mark.parametrize('failure', ['missing-edit', 'failed-edit', 'error-content', 'missing-read', 'missing-result', 'wrong-path', 'wrong-tool', 'no-marker', 'nonzero', 'timeout', 'unchanged', 'fabricated-source', 'wrong-old-string'])
def test_fail_closed_native_policy(tmp_path, failure):
    trace = events(tmp_path / 'task.py')
    options = {}
    if failure == 'missing-edit': trace = trace[:2] + trace[-1:]
    if failure == 'failed-edit': trace[3]['message']['content'][0]['is_error'] = True
    if failure == 'error-content': trace[3]['message']['content'][0]['content'] = '<tool_use_error>failure</tool_use_error>'
    if failure == 'missing-read': trace = trace[2:]
    if failure == 'missing-result': trace.pop(3)
    if failure == 'wrong-path': trace[2]['message']['content'][0]['input']['file_path'] = str(tmp_path / 'elsewhere.py')
    if failure == 'wrong-tool': trace[2]['message']['content'][0]['name'] = 'Bash'
    if failure == 'no-marker': trace[-1]['result'] = 'other'
    if failure == 'nonzero': options['code'] = 1
    if failure == 'timeout': options['timeout'] = True
    if failure == 'unchanged': options['after'] = b'before'
    if failure == 'fabricated-source': options['after'] = b'not produced by the native edit'
    if failure == 'wrong-old-string': trace[2]['message']['content'][0]['input']['old_string'] = 'other'
    assert not accept(trace, tmp_path, **options)['passed']


def test_relative_task_path_and_crlf_normalization(tmp_path):
    trace = events(Path('task.py'))
    trace[2]['message']['content'][0]['input'].update(old_string='before\n', new_string='after\n')
    assert accept(trace, tmp_path, before=b'before\r\n', after=b'after\n')['passed']


def test_real_regression_override_rejects_bad_artifact_and_keeps_sources(tmp_path):
    candidate = tmp_path / 'task.py'
    baseline = ROOT / CASES['migration'][0]
    original = baseline.read_bytes()
    candidate.write_bytes(original)
    results = validate('migration', candidate, tmp_path)
    assert not results['regressions']['passed']
    assert not results['behavior']['passed']
    assert 'failed' in (tmp_path / 'regressions.stdout').read_text()
    assert baseline.read_bytes() == candidate.read_bytes() == original
