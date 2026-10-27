import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


def test_same_basename_at_wrong_path_is_not_native_edit_proof(tmp_path,monkeypatch):
    import verify_artifacts as verifier
    monkeypatch.setattr(verifier,'ROOT',tmp_path)
    output=tmp_path/'output';output.mkdir()
    (output/'model-audit.json').write_text('finished\n')
    events=[{'type':'assistant','message':{'content':[{'type':'tool_use','name':'Edit','id':'edit1','input':{
        'file_path':str(tmp_path/'different/model-audit.json'),'old_string':'PENDING_LOCAL_ACCEPTANCE\n','new_string':'finished\n'}}]}},
        {'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'edit1','content':'success'}]}}]
    (output/'model-audit.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
    with pytest.raises(AssertionError,match='different file'):
        verifier.publish({'task':'model-audit','artifact':'output/model-audit.json'},trace_directory=output,destination=tmp_path/'published')
    assert not (tmp_path/'published').exists()


def test_fresh_acceptance_directory_cannot_overwrite_previous_attempt(tmp_path,monkeypatch):
    import claude_acceptance as runner
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    previous=tmp_path/'previous';previous.mkdir();proof=previous/'proof';proof.write_bytes(b'keep')
    monkeypatch.setattr(sys,'argv',['claude_acceptance.py','--output-dir',str(previous)])
    with pytest.raises(FileExistsError):runner.main()
    assert proof.read_bytes()==b'keep'
