"""Verify native JSON-schema constraints and OpenAI output-budget normalization."""
import json
from pathlib import Path
import urllib.request
import urllib.error
from setup_env import gateway_key, ROOT

def main():
    schema={'type':'object','properties':{'marker':{'type':'string','const':'LOCAL_OPENAI_OK'}},'required':['marker'],'additionalProperties':False}
    body={'model':'qwen3.8-27b','messages':[{'role':'user','content':'Return the JSON object required by the response schema.'}],'max_completion_tokens':128,'seed':42,'response_format':{'type':'json_schema','json_schema':{'name':'marker','strict':True,'schema':schema}}}
    req=urllib.request.Request('http://127.0.0.1:8090/v1/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+gateway_key(),'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=300) as response: result=json.load(response)
    parsed=json.loads(result['choices'][0]['message']['content'])
    passed=parsed=={'marker':'LOCAL_OPENAI_OK'} and result['usage']['completion_tokens']<=128
    cap_body={'model':'qwen3.8-27b','messages':[{'role':'user','content':'Count from 1 to 1000, one number per line. Keep going until the limit.'}],'max_completion_tokens':16,'temperature':0}
    cap_request=urllib.request.Request('http://127.0.0.1:8090/v1/chat/completions',data=json.dumps(cap_body).encode(),headers={'Authorization':'Bearer '+gateway_key(),'Content-Type':'application/json'})
    with urllib.request.urlopen(cap_request,timeout=60) as response: capped=json.load(response)
    cap_passed=capped['usage']['completion_tokens']==16 and capped['choices'][0]['finish_reason']=='length'
    bad=urllib.request.Request('http://127.0.0.1:8090/v1/chat/completions',data=json.dumps(dict(body,system='System instructions must not be duplicated.')).encode(),headers={'Authorization':'Bearer '+gateway_key(),'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(bad,timeout=30) as response: rejected=response.status
    except urllib.error.HTTPError as error:
        rejected=error.code
    passed=passed and rejected==422 and cap_passed
    (ROOT/'evidence/openai-smoke.json').write_text(json.dumps({'passed':passed,'request':body,'response':result,'schema_assertion':parsed=={'marker':'LOCAL_OPENAI_OK'},'cap_request':cap_body,'cap_response':capped,'output_limit_assertion':cap_passed,'invalid_top_level_system_status':rejected,'purpose':'Submitted schema yields the exact const absent from user text; a long-generation request stops at the exact requested 16-token limit; malformed OpenAI system is rejected'},indent=2))
    print('OpenAI JSON schema and token limit passed' if passed else 'FAILED',flush=True)
    raise SystemExit(0 if passed else 1)

if __name__=='__main__': main()
