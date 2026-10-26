"""Sample host GPU occupancy while a verified campaign process is alive."""
import argparse
import ctypes
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pid',required=True,type=int)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x00100000,False,args.pid)
    if not handle:raise RuntimeError('Campaign process handle unavailable')
    samples=[]
    try:
        with (root/'tmp/stress/gpu-samples.jsonl').open('a',encoding='utf-8') as stream:
            while kernel.WaitForSingleObject(handle,0)==258:
                raw=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.total,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=10)
                used,total,free,util=[int(x.strip()) for x in raw.strip().split(',')]
                row={'at':datetime.now(timezone.utc).isoformat(),'used_mib':used,'total_mib':total,'free_mib':free,'utilization_percent':util}
                samples.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
                if kernel.WaitForSingleObject(handle,5000)!=258:break
    finally:
        kernel.CloseHandle(handle)
        summary={'samples':len(samples),'controller_pid':args.pid,'maximum_host_used_mib':max((r['used_mib'] for r in samples),default=None),
            'minimum_host_free_mib':min((r['free_mib'] for r in samples),default=None),
            'first':samples[0] if samples else None,'last':samples[-1] if samples else None,
            'scope':'Total host GPU occupancy, including desktop drift; not per-model allocation or an isolated14GB measurement. Sampling sleep is outside every client active-duration measurement.'}
        (root/'evidence/stress-memory.json').write_text(json.dumps(summary,indent=2))


if __name__=='__main__':main()
