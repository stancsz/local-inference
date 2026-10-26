"""Exercise the local Responses bridge, native tools, streaming and Sift counts."""
import json
import urllib.request
from setup_env import gateway_key,ROOT


def request(body):
    req=urllib.request.Request('http://127.0.0.1:8090/v1/responses',data=json.dumps(body).encode(),
        headers={'Authorization':'Bearer '+gateway_key(),'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=180) as response:
        if not body.get('stream'): return json.load(response)
        events=[json.loads(line[6:]) for line in response.read().decode().splitlines()
                if line.startswith('data: ') and line[6:]!='[DONE]']
    final=next(e['response'] for e in events if e.get('type')=='response.completed')
    return final,events


def main():
    audits=ROOT/'evidence/gateway-audit.jsonl'
    before=len(audits.read_text().splitlines()) if audits.exists() else 0
    receipts=[]
    for kind in ('function','custom'):
        marker='LOCAL_RESPONSES_'+kind.upper()+'_OK'
        tool={'type':kind,'name':'route_marker','description':'Return the exact harmless marker'}
        if kind=='function': tool['parameters']={'type':'object','properties':{'marker':{'type':'string'}},'required':['marker']}
        else: tool['format']={'type':'text'}
        body={'model':'qwen3.8-27b-codex','max_output_tokens':512,
            'input':[{'role':'user','content':f'Call route_marker with {marker}. After its result, reply exactly that marker.'}],
            'tools':[tool],'tool_choice':{'type':kind,'name':'route_marker'}}
        first=request(body)
        call_type='function_call' if kind=='function' else 'custom_tool_call'
        call=next(item for item in first['output'] if item['type']==call_type)
        assert marker in call.get('arguments',call.get('input',''))
        output_type='function_call_output' if kind=='function' else 'custom_tool_call_output'
        body['input']+=first['output']+[{'type':output_type,'call_id':call['call_id'],'output':marker}]
        body.pop('tool_choice');body['stream']=True
        final,events=request(body)
        assert marker in json.dumps(final['output'])
        current=[json.loads(line) for line in audits.read_text().splitlines()[before:]]
        assert current and final['usage']['input_tokens']==current[-1]['native_input_tokens'],(final['usage'],current[-1])
        assert all(a['native_input_tokens']+a['output_reserve']+a['decoder_headroom']<=a['context_window'] for a in current)
        receipts.append({'kind':kind,'first':first,'continuation':final,
            'event_types':[event['type'] for event in events],'native_audit':current[-1],'passed':True})
    (ROOT/'evidence/responses-smoke.json').write_text(json.dumps({'passed':True,'checks':receipts},indent=2))
    print('Local Responses function/custom tools, streaming continuation and native counts passed')


if __name__=='__main__':main()
