"""Measure real llama.cpp decode timings; save process and host VRAM separately."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    parser.add_argument('--tokens',type=int,default=256)
    args=parser.parse_args()
    prompt='Write a Python function that reads a JSONL log, counts HTTP errors by service, and prints a sorted JSON summary. Explain error handling concisely.'
    results=[]
    for iteration in range(2):
        body={'model':'qwen3.8-27b','messages':[{'role':'user','content':prompt}],'max_tokens':args.tokens,'temperature':0,'seed':42,'stream':False}
        request=urllib.request.Request('http://127.0.0.1:8091/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        start=time.monotonic()
        with urllib.request.urlopen(request,timeout=600) as response:
            result=json.load(response)
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader'],text=True).strip()
        results.append({'iteration':iteration,'seconds':round(time.monotonic()-start,3),'usage':result.get('usage'),'timings':result.get('timings'),'host_gpu_mib':gpu,'response':result.get('choices')})
        (ROOT/'evidence'/f'benchmark-{args.label}.json').write_text(json.dumps(results,indent=2))
        print(json.dumps({k:v for k,v in results[-1].items() if k!='response'}),flush=True)

if __name__=='__main__': main()
