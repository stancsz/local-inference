"""Prove text and native tool continuation through this gateway only."""
import json
from pathlib import Path
import time
import http.client
import urllib.request
from setup_env import gateway_key

ROOT=Path(__file__).resolve().parents[1]
def request(body):
    req=urllib.request.Request('http://127.0.0.1:8090/v1/messages',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+gateway_key(),'Content-Type':'application/json','anthropic-version':'2023-06-01'})
    with urllib.request.urlopen(req,timeout=180) as response: return json.load(response)

def main():
    receipts={}
    for url in ['http://127.0.0.1:8091/health','http://127.0.0.1:8090/health/readiness']:
        deadline=time.monotonic()+90
        while True:
            try:
                req=urllib.request.Request(url,headers={'Authorization':'Bearer '+gateway_key()} if ':8090/' in url else {})
                with urllib.request.urlopen(req,timeout=3) as response:
                    if response.status==200: break
            except (OSError,urllib.error.HTTPError,http.client.HTTPException):
                if time.monotonic()>=deadline: raise
                time.sleep(2)
    start=time.monotonic()
    body={'model':'qwen3.8-27b','max_tokens':256,'messages':[{'role':'user','content':'Reply exactly LOCAL_QWEN_SIFT_OK'}]}
    first=request(body)
    assert 'LOCAL_QWEN_SIFT_OK' in json.dumps(first['content']),first
    receipts['text']=first
    body={'model':'qwen3.8-27b','max_tokens':512,'messages':[{'role':'user','content':'Call route_marker with marker LOCAL_QWEN_TOOL_OK. After the tool result reply exactly that marker.'}],'tools':[{'name':'route_marker','description':'Return a harmless marker','input_schema':{'type':'object','properties':{'marker':{'type':'string'}},'required':['marker']}}],'tool_choice':{'type':'tool','name':'route_marker'}}
    tool=request(body)
    call=next(x for x in tool['content'] if x['type']=='tool_use')
    assert call['name']=='route_marker' and call['input']['marker']=='LOCAL_QWEN_TOOL_OK'
    body['messages'] += [{'role':'assistant','content':tool['content']},{'role':'user','content':[{'type':'tool_result','tool_use_id':call['id'],'content':'LOCAL_QWEN_TOOL_OK'}]}]
    body.pop('tool_choice')
    final=request(body)
    assert 'LOCAL_QWEN_TOOL_OK' in json.dumps(final['content'])
    receipts.update(tool=tool,continuation=final,seconds=round(time.monotonic()-start,3),passed=True,endpoint='http://127.0.0.1:8090/v1/messages')
    (ROOT/'evidence/local-smoke.json').write_text(json.dumps(receipts,indent=2))
    print('Local gateway text and tool continuation passed',flush=True)

if __name__=='__main__': main()
