"""Synthetic backend capacity test; separate from Sift and real CLI task quality."""
import json
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
def post(path,body):
    req=urllib.request.Request('http://127.0.0.1:8091'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=900) as response: return json.load(response)

def main():
    unit=post('/tokenize',{'content':'Deployment log record: service healthy, request complete.\n','add_special':False})['tokens']
    tokens=(unit*(65536//len(unit)+1))[:65536]
    start=time.monotonic()
    result=post('/completion',{'prompt':tokens,'n_predict':4096,'ignore_eos':True,'temperature':0,'seed':42,'cache_prompt':False})
    receipt={k:v for k,v in result.items() if k not in ('content','tokens','generation_settings','prompt')}
    receipt.update(input_token_ids=len(tokens),seconds=round(time.monotonic()-start,3),host_gpu_mib=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader'],text=True).strip(),purpose='Synthetic exact capacity; no claim of productivity or coherent long output')
    receipt['passed']=len(tokens)==65536 and result.get('tokens_predicted')==4096 and result.get('truncated') is False
    (ROOT/'evidence/capacity-64k-4k.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt),flush=True)
    raise SystemExit(0 if receipt['passed'] else 1)

if __name__=='__main__': main()
