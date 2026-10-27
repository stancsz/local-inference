"""Capture is observational and records exact historical source, not headers."""
import ast
import gzip
import inspect
import json

from stress.cli_acceptance import make_app as original_factory
from stress.proxy_capture_v2 import capture_snapshot, make_app


def test_capture_preserves_messages_and_exposes_source_index(tmp_path):
    messages = [{'role':'system','content':'private-prefix'}, {'role':'user','content':'Earlier conversation, lossily excerpted\n[message 2 user] acceptance_delay_seconds=37'}]
    before=json.dumps(messages)
    entry={'gold_retained':False}
    capture_snapshot(tmp_path,0,messages,entry)
    result=json.loads(gzip.decompress((tmp_path/'00000.json.gz').read_bytes()))
    assert result['gold_retained'] is False
    assert result['needle_matches'][0]['lines']==['[message 2 user] acceptance_delay_seconds=37']
    assert 'private-prefix' not in json.dumps(result)
    assert json.dumps(messages)==before


def test_factory_dataflow_is_identical_after_stripping_observer():
    old=ast.parse(inspect.getsource(original_factory)).body[0]
    new=ast.parse(inspect.getsource(make_app)).body[0]
    new.args.args=new.args.args[:-1]
    new.args.defaults=[]
    class Normalize(ast.NodeTransformer):
        def visit_If(self,node):
            if ast.dump(node.test).find("id='capture_dir'")>=0:return None
            return self.generic_visit(node)
        def visit_Try(self,node):
            if any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='capture_snapshot' for n in ast.walk(node)):
                return None
            return self.generic_visit(node)
    new=Normalize().visit(new)
    assert ast.dump(old)==ast.dump(new)
