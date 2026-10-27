import ctypes,json,urllib.request
from ctypes import wintypes
from datetime import datetime,timezone
from pathlib import Path
folder=Path(__file__).resolve().parents[2]/'evidence/long-profile-v4'
state=json.loads((folder/'state.json').read_text())
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
kernel.OpenProcess.restype=wintypes.HANDLE
kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
kernel.CloseHandle.argtypes=[wintypes.HANDLE]
handle=kernel.OpenProcess(0x1000,False,state['pid'])
alive=False
if handle:
    code=wintypes.DWORD()
    alive=bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code)))and code.value==259
    kernel.CloseHandle(handle)
row={'at':datetime.now(timezone.utc).isoformat(),'controller_pid':state['pid'],'controller_live':alive,'stage':state['stage'],'status':state['status']}
try:
    with urllib.request.urlopen('http://127.0.0.1:8091/slots',timeout=5)as response:slots=json.load(response)
    row['slots']=[{key:value for key,value in s.items()if key in ('id','is_processing','n_prompt_tokens','next_token')}for s in slots]
except Exception as error:row['backend_observation_error']=str(error)
last=(folder/'gpu-samples.jsonl').read_text().splitlines()[-1]
row['last_gpu_sample']=json.loads(last)
with (folder/'observations.jsonl').open('a',encoding='utf-8')as stream:stream.write(json.dumps(row)+'\n')
print(json.dumps(row))
