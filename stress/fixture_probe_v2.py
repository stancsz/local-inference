"""No-inference native sandbox check for the portable test fixture."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from stress.portable_tasks_v2 import FIXTURE_SOURCE


def probe(executable, root, workspace, env):
    outside = root / ('fixture-outside-' + uuid.uuid4().hex + '.txt')
    script = FIXTURE_SOURCE + """
import json,sys
with _workspace_fixture() as folder:
    path=Path(folder)/'data.json'
    path.write_text(json.dumps({'message':'test'}),encoding='utf-8')
    assert json.loads(path.read_text(encoding='utf-8'))=={'message':'test'}
cleaned=not Path(folder).exists()
denied=False
try:Path(sys.argv[1]).write_text('outside',encoding='utf-8')
except PermissionError:denied=True
print(json.dumps({'fixture_cleanup_passed':cleaned,'outside_denied':denied}))
raise SystemExit(0 if cleaned and denied else 1)
"""
    args = [executable, 'sandbox', '--permission-profile', ':workspace', '-C', str(workspace)]
    if os.name == 'nt': args += ['-c', 'windows.sandbox="unelevated"']
    args += ['--', sys.executable, '-c', script, str(outside)]
    scoped_env = {k: v for k, v in env.items() if not any(s in k.upper() for s in ('KEY', 'TOKEN', 'SECRET'))}
    result = subprocess.run(args, cwd=workspace, env=scoped_env, capture_output=True, text=True, timeout=30)
    try:
        details = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        details = {}
    if outside.exists():
        assert outside.resolve().parent == root.resolve()
        outside.unlink()
    return {'passed': result.returncode == 0 and details.get('fixture_cleanup_passed') is True and details.get('outside_denied') is True,
            'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'details': details,
            'scope': 'Native sandbox, no inference or global permission/configuration changes.'}
