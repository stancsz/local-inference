"""Local routing must not replace the owner's client permissions or config."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import pytest

@pytest.mark.parametrize('configured',[False,True])
def test_local_launcher_preserves_caller_settings(configured):
    root=Path(__file__).resolve().parents[1]
    import sys
    sys.path.insert(0,str(root/'scripts'))
    spec=importlib.util.spec_from_file_location('local_launcher_under_test',root/'scripts/claude_local.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    environment={'CLAUDE_CODE_PERMISSION_MODE':'default','OWNER_SENTINEL':'retained'}
    if configured:environment['CLAUDE_CONFIG_DIR']='owner-config'
    arguments=['--permission-mode','plan','--allowedTools','Read']
    with patch.dict(module.os.environ,environment,clear=True),patch.object(module,'gateway_key',return_value='test-scoped-key'),patch.object(module.sys,'argv',['claude_local.py',*arguments]),patch.object(module.subprocess,'call',return_value=0) as invoke:
        with pytest.raises(SystemExit) as exit:module.main()
    assert exit.value.code==0
    command=invoke.call_args.args[0];env=invoke.call_args.kwargs['env']
    assert command==['claude.cmd','--model','qwen3.8-27b',*arguments]
    assert '--bare' not in command
    assert env.get('CLAUDE_CONFIG_DIR')==environment.get('CLAUDE_CONFIG_DIR')
    assert env['CLAUDE_CODE_PERMISSION_MODE']=='default' and env['OWNER_SENTINEL']=='retained'
    assert env['ANTHROPIC_BASE_URL']=='http://127.0.0.1:8090'
