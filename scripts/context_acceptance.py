"""Exercise 256k/1M histories and native downstream compaction counts."""
import json
import math
from pathlib import Path
import sys
import time
import urllib.request
from setup_env import gateway_key

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
import budget as proxy

def main():
    records=[]
    for size in (256_000,1_000_000):
        # Approximately size tokens using a deliberately labelled 4-char estimate.
        # Old completed turns carry evidence; latest task remains small and immutable.
        history=[]
        line='Historical deployment log: service green, request completed. '
        for index in range(100):
            text=(line*((size*4//100)//len(line)+1))[:size*4//100]
            history.extend([{'role':'user','content':f'Record {index}: '+text},{'role':'assistant','content':'Recorded.'}])
        history[80]['content']+=' Critical deployment answer: release uses port 8090. '
        query='What port does the critical deployment answer specify? Reply PORT=<number> using only earlier evidence.'
        history.append({'role':'user','content':query})
        payload={'model':'qwen3.8-27b','system':'Keep deployment evidence exact.','messages':history,'max_tokens':128}
        raw_native=proxy.count(payload)
        if raw_native < size:
            multiplier=(size+2048)/raw_native
            for item in history[:-1]:
                if item['role']=='user':
                    text=item['content']
                    item['content']=(text*math.ceil(multiplier))[:math.ceil(len(text)*multiplier)]
            raw_native=proxy.count(payload)
        assert raw_native>=size
        started=time.monotonic()
        forwarded,audit=proxy.compact(payload)
        assert forwarded['messages'][-1]['content']==query
        assert 'release uses port 8090' in json.dumps(forwarded['messages']),'Compaction dropped the evidence'
        assert audit['native_input_tokens']+128<=proxy.WINDOW
        request=urllib.request.Request('http://127.0.0.1:8090/v1/messages',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+gateway_key()})
        with urllib.request.urlopen(request,timeout=900) as response:
            native_header=response.headers.get('x-local-sift-native-input-tokens')
            output=json.load(response)
        live=[json.loads(line) for line in (ROOT/'evidence/gateway-audit.jsonl').read_text().splitlines() if line.strip()]
        live=next(row for row in reversed(live) if row.get('raw_request_sha256')==proxy.request_digest(payload))
        assert live['native_input_tokens']==audit['native_input_tokens'],'Live and independently calculated compaction counts differ'
        usage=output.get('usage',{})
        assert usage.get('input_tokens',0)+usage.get('cache_read_input_tokens',0)==live['native_input_tokens'],'Provider usage differs from native count'
        answer=''.join(b.get('text','') for b in output.get('content',[]))
        records.append({'minimum_raw_native_tokens':size,'raw_native_tokens':raw_native,'serialized_bytes':len(json.dumps(payload).encode()),'audit':audit,'live_audit':live,'answer':answer,'passed':'PORT=8090' in answer,'seconds':round(time.monotonic()-started,2),'usage':output.get('usage')})
        (ROOT/'evidence/context-acceptance.json').write_text(json.dumps(records,indent=2))
        print(json.dumps(records[-1]),flush=True)
    raise SystemExit(0 if all(r['passed'] for r in records) else 1)

if __name__=='__main__': main()
