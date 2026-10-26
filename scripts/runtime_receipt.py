"""Record scoped observed GPU delta and actual llama.cpp properties."""
import json
from pathlib import Path
import re
import subprocess
import hashlib
import urllib.request
import argparse
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sift-source',type=Path,default=ROOT.parent/'sift')
    args=parser.parse_args()
    baseline=int(re.search(r'(\d+) MiB',(ROOT/'evidence/gpu-before-inference.txt').read_text()).group(1))
    used=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
    with urllib.request.urlopen('http://127.0.0.1:8091/props') as response: props=json.load(response)
    receipt={'captured_at':datetime.now(timezone.utc).isoformat(),'baseline_host_used_mib':baseline,'loaded_host_used_mib':used,'observed_inference_delta_mib':used-baseline,'observed_inference_delta_bytes':(used-baseline)*1024**2,'under_14_decimal_GB_by_delta':(used-baseline)*1024**2<14_000_000_000,'caveat':'Host delta includes runtime caches/buffers and possible unrelated desktop drift; not per-allocation accounting.','runtime':{k:props[k] for k in ('build_info','model_alias','model_ftype','model_path','total_slots')},'context_window':props['default_generation_settings']['n_ctx']}
    command="Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory | ForEach-Object { if ($_.Name -match '^pid_(\\d+)_') { $process = Get-Process -Id ([int]$Matches[1]) -ErrorAction SilentlyContinue; if ($process.ProcessName -eq 'vmwp') { [pscustomobject]@{instance=$_.Name; dedicated_bytes=[long]$_.DedicatedUsage; shared_bytes=[long]$_.SharedUsage} } } } | ConvertTo-Json -Compress"
    counters=json.loads(subprocess.check_output(['pwsh','-NoProfile','-Command',command],text=True))
    receipt['vmwp_allocation_counters']=counters if isinstance(counters,list) else [counters]
    receipt['allocation_counter_caveat']='WSL VM allocation counters can overlap; they are not physical GPU totals or per-model accounting.'
    code="""import json,hashlib,pathlib,importlib.metadata,sift,sift.core,sift.dynamic,sift.litellm_proxy,sift.litellm_responses
paths=['/app/budget.py','/app/gateway.py','/app/gateway.yaml',*[m.__file__ for m in [sift,sift.core,sift.dynamic,sift.litellm_proxy,sift.litellm_responses]]]
files={n:hashlib.sha256(pathlib.Path(n).read_text(encoding='utf-8').encode()).hexdigest() for n in paths}
raw_files={n:hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest() for n in paths}
print(json.dumps({'files':files,'raw_files':raw_files,'litellm':importlib.metadata.version('litellm')}))
"""
    container=json.loads(subprocess.check_output(['docker','exec','local-inference-gateway-1','python','-c',code],text=True))
    local={n:hashlib.sha256((ROOT/n).read_text(encoding='utf-8').encode()).hexdigest() for n in ['app/budget.py','app/gateway.py','gateway.yaml']}
    assert all(container['files']['/'+n if n.startswith('app/') else '/app/'+n]==value for n,value in local.items())
    sift_hashes={name:hashlib.sha256((args.sift_source/'src/sift'/name).read_text(encoding='utf-8').encode()).hexdigest() for name in ['__init__.py','core.py','dynamic.py','litellm_proxy.py','litellm_responses.py']}
    assert all(value in container['files'].values() for value in sift_hashes.values())
    (ROOT/'evidence/runtime-source-parity.json').write_text(json.dumps({'passed':True,'hash_scope':'UTF-8 source text with universal newlines; raw container hashes also retained. Git checkout CRLF/LF differences are normalized, no other whitespace changes.','local_app_hashes':local,'sift_source':str(args.sift_source),'container':container,'sift_hashes':sift_hashes},indent=2))
    (ROOT/'evidence/runtime-vram.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))

if __name__=='__main__': main()
