"""Native stdin bytes, without making provider calls or generating task artifacts."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import claude_acceptance as acceptance


@pytest.mark.parametrize('prompt',['caf\u00e9 \u2014','\u4e2d\u6587\u4efb\u52a1'])
def test_legacy_cli_prompt_uses_utf8(tmp_path,monkeypatch,prompt):
    destination=tmp_path/'acceptance'
    original_run=subprocess.run
    inputs=[]

    def echo_stdin_bytes(_args,**kwargs):
        inputs.append(kwargs['input'])
        return original_run([sys.executable,'-c','import sys; print(sys.stdin.buffer.read().hex())'],**kwargs)

    monkeypatch.setattr(acceptance.subprocess,'run',echo_stdin_bytes)
    monkeypatch.setattr(acceptance,'ROOT',tmp_path)
    monkeypatch.setattr(acceptance,'gateway_key',lambda:'unit-test-not-a-live-key')
    monkeypatch.setattr(acceptance,'TASKS',[('model-audit',prompt,'model-audit.json','MODEL_AUDIT_DONE')])
    monkeypatch.setattr(sys,'argv',['claude_acceptance.py','--task','model-audit','--output-dir',str(destination)])
    with pytest.raises(SystemExit)as result:
        acceptance.main()
    # The echo process deliberately supplies no CLI events/artifact, hence rejection.
    assert result.value.code==1
    observed=(destination/'model-audit.jsonl').read_text(encoding='utf-8').strip()
    assert observed==inputs[0].encode('utf-8').hex()
