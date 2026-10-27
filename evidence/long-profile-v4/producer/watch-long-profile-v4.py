"""Read-only observations every 30 seconds until the existing controller ends."""
import json,runpy,time
from pathlib import Path
root=Path(__file__).resolve().parent
deadline=time.monotonic()+7200
while time.monotonic()<deadline:
    try:
        runpy.run_path(str(root/'observe-long-profile-v4.py'))
        state=json.loads((root.parents[1]/'evidence/long-profile-v4/state.json').read_text())
        if state['status']=='terminal':break
    except Exception as error:
        print(json.dumps({'observation_error':str(error)}),flush=True)
    time.sleep(30)
