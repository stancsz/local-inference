"""An actual native-child preflight must retain token limits while stripping keys."""
import ast
import os
from pathlib import Path
import runpy
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

def test_v2_filter_preserves_numeric_token_settings():
 source=(ROOT/'workhorse/run_v2.py').read_text()
 tree=ast.parse(source)
 # Execute the actual filter statement, rather than a duplicated predicate.
 loop=next(n for n in ast.walk(tree)if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='key')
 env={'ANTHROPIC_API_KEY':'local-key','CLAUDE_CODE_MAX_OUTPUT_TOKENS':'4096',
      'CLAUDE_CODE_MAX_CONTEXT_TOKENS':'1000000','GATEWAY_MASTER_KEY':'must-remove',
      'OTHER_API_TOKEN':'must-remove','APP_SECRET':'must-remove','CLAUDE_CODE_PERMISSION_MODE':'default'}
 before=dict(env);namespace={'env':env}
 exec(compile(ast.Module(body=[loop],type_ignores=[]),'actual-v2-filter','exec'),namespace)
 assert env=={k:before[k]for k in ('ANTHROPIC_API_KEY','CLAUDE_CODE_MAX_OUTPUT_TOKENS','CLAUDE_CODE_MAX_CONTEXT_TOKENS','CLAUDE_CODE_PERMISSION_MODE')}

def test_v1_failure_mechanism_reproduced():
 source=(ROOT/'workhorse/run_v1.py').read_text();tree=ast.parse(source)
 loop=next(n for n in ast.walk(tree)if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='key')
 env={'ANTHROPIC_API_KEY':'local-key','CLAUDE_CODE_MAX_OUTPUT_TOKENS':'4096'}
 exec(compile(ast.Module(body=[loop],type_ignores=[]),'frozen-v1-filter','exec'),{'env':env})
 assert env=={'ANTHROPIC_API_KEY':'local-key'}
