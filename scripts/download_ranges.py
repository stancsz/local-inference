"""Bounded range transfers with verified ranges, resumable chunks and SHA256."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REPO='unsloth/Qwen3.8-27B-GGUF'
FILES=['MTP/mtp-Qwen3.8-27B-Q4_0.gguf','Qwen3.8-27B-UD-IQ3_XXS.gguf']
CHUNK=32*1024*1024

def main():
    meta=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}?blobs=true',timeout=30))
    records=[]
    for name in FILES:
        item=next(x for x in meta['siblings'] if x['rfilename']==name)
        size=item['size']
        sha=item['lfs']['sha256']
        directory=ROOT/'tmp/chunks'/Path(name).stem
        directory.mkdir(parents=True,exist_ok=True)
        def get_chunk(start):
            end=min(size,start+CHUNK)-1
            dest=directory/str(start)
            if dest.exists() and dest.stat().st_size==end-start+1:
                return dest
            for attempt in range(3):
                try:
                    url=f'https://huggingface.co/{REPO}/resolve/{meta["sha"]}/{name}?download=true&chunk={start}'
                    req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
                    with urllib.request.urlopen(req,timeout=60) as response:
                        if response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'):
                            raise ValueError('range response mismatch')
                        with dest.open('wb') as out:
                            while data:=response.read(1024*1024): out.write(data)
                    if dest.stat().st_size!=end-start+1: raise ValueError('incomplete range')
                    return dest
                except Exception:
                    if attempt==2: raise
                    time.sleep(1)
        starts=list(range(0,size,CHUNK))
        with concurrent.futures.ThreadPoolExecutor(24) as pool:
            chunks=list(pool.map(get_chunk,starts))
        digest=hashlib.sha256()
        dest=ROOT/'models'/Path(name).name
        with dest.open('wb') as out:
            for chunk in chunks:
                with chunk.open('rb') as inp:
                    while data:=inp.read(4*1024*1024):
                        digest.update(data)
                        out.write(data)
        if digest.hexdigest()!=sha: raise ValueError('SHA256 mismatch')
        records.append({'file':name,'bytes':size,'sha256':sha})
        print(json.dumps(records[-1]),flush=True)
    (ROOT/'evidence/model-manifest.json').write_text(json.dumps({'repository':REPO,'revision':meta['sha'],'files':records},indent=2))

if __name__=='__main__': main()
