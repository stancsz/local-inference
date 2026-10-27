"""New fixture semantics and expanded contracts are verified before model runs."""
import ast
import types
from pathlib import Path

import pytest

from stress.portable_tasks_v2 import TASKS, initial_source, stage
from test_supplement_tasks import incident_reference, manifest_reference, run_definition


def reference(task):
    if task == 'incident_log': return incident_reference()
    if task == 'release_manifest': return manifest_reference()
    module = types.ModuleType('expense_control')
    path = Path(__file__).resolve().parents[1] / 'recovery/expenses_v1.py'
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


@pytest.mark.parametrize('task', TASKS)
@pytest.mark.parametrize('number', range(9))
def test_portable_public_and_hidden_stages_accept_controls(task, number, tmp_path, monkeypatch):
    public = stage(task, number, 2026102711 + number)
    hidden = stage(task, number, 2026102711 + number + 100003)
    assert public['tests'] != hidden['tests']
    assert 'tempfile.TemporaryDirectory()' not in public['tests']
    assert public == stage(task, number, 2026102711 + number)
    for definition in (public, hidden):
        result, output = run_definition(definition, reference(task), tmp_path, monkeypatch)
        assert result.wasSuccessful(), output
    broken = types.ModuleType('broken')
    exec(initial_source(task), broken.__dict__)
    result, output = run_definition(public, broken, tmp_path, monkeypatch)
    assert not result.wasSuccessful()
    assert not list(tmp_path.glob('.sift-fixture-*'))


@pytest.mark.parametrize('task', TASKS)
def test_existing_assertions_are_unchanged_except_fixture_factory(task):
    from stress import supplement_tasks_v1, acceptance_tasks
    original = acceptance_tasks.stage('expenses', 8, 2711) if task == 'expense_audit' else supplement_tasks_v1.stage(task, 8, 2711)
    old_class = next(n for n in ast.parse(original['tests']).body if isinstance(n, ast.ClassDef))
    new_class = next(n for n in ast.parse(stage(task, 8, 2711)['tests']).body if isinstance(n, ast.ClassDef))
    new_methods = {n.name: n for n in new_class.body}
    for old in old_class.body:
        new = new_methods[old.name]
        for node in ast.walk(new):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_workspace_fixture':
                node.func = ast.Attribute(value=ast.Name(id='tempfile', ctx=ast.Load()), attr='TemporaryDirectory', ctx=ast.Load())
        assert ast.dump(old) == ast.dump(new)


def test_new_driver_retains_old_acceptance_plus_fixture_guard():
    root = Path(__file__).resolve().parents[1]
    old = next(n for n in ast.parse((root/'stress/cli_campaign.py').read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='run')
    new = next(n for n in ast.parse((root/'stress/portable_campaign_v2.py').read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='run')
    removed = []
    class Normalize(ast.NodeTransformer):
        def visit_ImportFrom(self, node):
            if node.module=='stress.portable_tasks_v2': node.module='stress.acceptance_tasks'
            if node.module=='stress.fixture_probe_v2':
                removed.append(node)
                return None
            return node
        def visit_Constant(self,node):
            if node.value=='Use the explicitly authorized 127.0.0.1:8090/v1 route': node.value='Use the explicitly authorized 127.0.0.1:4000/v1 route'
            return node
        def visit_Call(self,node):
            node.keywords=[k for k in node.keywords if k.arg!='capture_dir']
            return self.generic_visit(node)
        def visit_Assign(self,node):
            if any(isinstance(t,ast.Subscript) and isinstance(t.slice,ast.Constant) and t.slice.value=='fixture_readiness' for t in node.targets):
                removed.append(node)
                return None
            return self.generic_visit(node)
        def visit_If(self,node):
            if 'fixture_readiness' in ast.dump(node.test):
                removed.append(node)
                return None
            return self.generic_visit(node)
    normalized=Normalize().visit(new)
    assert len(removed)==3
    assert ast.dump(old)==ast.dump(normalized)
