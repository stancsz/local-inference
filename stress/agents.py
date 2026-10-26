"""Native Codex sandbox readiness, without model inference or credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


SANDBOX_PROBE = """from pathlib import Path
import errno
import sys
inside, outside = (Path(name) for name in sys.argv[1:])
inside.write_text("sift readiness", encoding="utf-8")
inside.unlink()
try:
    outside.write_text("sift readiness", encoding="utf-8")
except OSError as error:
    if error.errno not in (errno.EACCES, errno.EPERM, errno.EROFS):
        raise
    print("SIFT_SANDBOX_READY")
else:
    outside.unlink()
    raise SystemExit("Sandbox permitted a write outside the workspace")
"""


def sandbox_preflight(args, executable, root, workspace, env):
    outside_directory = root / "sandbox-outside"
    outside_directory.mkdir()
    identifier = uuid.uuid4().hex
    inside = workspace / (".sift-readiness-" + identifier)
    outside = outside_directory / (identifier + ".txt")
    command = [executable, "sandbox", "--permission-profile", ":workspace", "-C", str(workspace)]
    if os.name == "nt":
        command += ["-c", "windows.sandbox=" + json.dumps(args.windows_sandbox)]
    command += ["--", sys.executable, "-c", SANDBOX_PROBE, str(inside), str(outside)]
    probe_env = {name: value for name, value in env.items()
                 if name not in {"SIFT_AGENT_API_KEY", "ANTHROPIC_API_KEY", "SIFT_LOCAL_KEY", "SIFT_ACCEPTANCE_API_KEY"}}
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=workspace, env=probe_env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    timed_out = False
    try:
        try:
            stdout, stderr = process.communicate(timeout=min(20, args.timeout))
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
            else:
                process.kill()
            stdout, stderr = process.communicate(timeout=10)
        return {"exit_code": process.returncode, "timed_out": timed_out,
                "stdout": stdout, "stderr": stderr, "duration_seconds": time.monotonic() - started,
                "passed": (process.returncode == 0 and not timed_out
                           and stdout.strip() == "SIFT_SANDBOX_READY"
                           and not inside.exists() and not outside.exists())}
    finally:
        for path in (inside, outside):
            if path.is_file() or path.is_symlink():
                path.unlink()
