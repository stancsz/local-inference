"""Record scoped observed GPU delta and actual llama.cpp properties."""
import json
from pathlib import Path
import re
import subprocess
import urllib.request
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
def main():
    baseline=int(re.search(r'(\d+) MiB',(ROOT/'evidence/gpu-before-inference.txt').read_text()).group(1))
    used=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
    with urllib.request.urlopen('http://127.0.0.1:8091/props') as response: props=json.load(response)
    receipt={'captured_at':datetime.now(timezone.utc).isoformat(),'baseline_host_used_mib':baseline,'loaded_host_used_mib':used,'observed_inference_delta_mib':used-baseline,'observed_inference_delta_bytes':(used-baseline)*1024**2,'under_14_decimal_GB_by_delta':(used-baseline)*1024**2<14_000_000_000,'caveat':'Host delta includes runtime caches/buffers and possible unrelated desktop drift; not per-allocation accounting.','runtime':{k:props[k] for k in ('build_info','model_alias','model_ftype','model_path','total_slots')},'context_window':props['default_generation_settings']['n_ctx']}
    (ROOT/'evidence/runtime-vram.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))

if __name__=='__main__': main()
