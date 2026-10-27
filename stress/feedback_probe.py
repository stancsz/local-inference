"""Representative offline retention probe; not a captured HTTP replay."""
import asyncio
from copy import deepcopy
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path.cwd()
sys.path[:0]=[str(ROOT/'tmp/stress/sift-candidate/src'),str(ROOT),str(ROOT/'app')]
from stress.cli_acceptance import inject_history,RouteCounter
from stress.acceptance_tasks import stage
from sift.litellm_proxy import SiftLiteLLMHook
import budget

source=ROOT/'tmp/stress/sessions/codex-expenses-r1/turn-00.jsonl'
events=[json.loads(line) for line in source.read_text().splitlines()]
commands=[e['item'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='command_execution']
failed=[item['aggregated_output'] for item in commands if item.get('exit_code')==1 and 'FAIL: test_behavior' in item.get('aggregated_output','')]
assert failed
instruction=stage('expenses',0,2051)['requirement']
tool={'type':'function','function':{'name':'shell_command','description':'Run a shell command','parameters':{'type':'object','properties':{'command':{'type':'string'}},'required':['command']}}}
chat=[{'role':'system','content':'Use the supplied tools to fix the current task.'},{'role':'user','content':instruction}]
responses=deepcopy(chat)
for index,item in enumerate(commands):
    identifier=f'actual-command-{index}'
    arguments=json.dumps({'command':item['command']})
    output=item.get('aggregated_output','')
    chat.extend([{'role':'assistant','content':None,'tool_calls':[{'id':identifier,'type':'function','function':{'name':'shell_command','arguments':arguments}}]},
                 {'role':'tool','tool_call_id':identifier,'content':output}])
    responses.extend([{'type':'function_call','call_id':identifier,'name':'shell_command','arguments':arguments},
                      {'type':'function_call_output','call_id':identifier,'output':output}])

def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,list):
        for item in value:yield from strings(item)
    elif isinstance(value,dict):
        for item in value.values():yield from strings(item)

async def main():
    rows=[]
    hook=SiftLiteLLMHook({'qwen3.8-27b':32768})
    compacted_chat=None
    for protocol,items in [('acompletion',chat),('aresponses',responses)]:
        key='messages' if protocol=='acompletion' else 'input'
        tools=[tool] if key=='messages' else [{'type':'function',**tool['function']}]
        payload={'model':'qwen3.8-27b',key:items,'tools':tools,'max_tokens':4096}
        compacted=await hook._compact(RouteCounter(),inject_history(payload),call_type=protocol,target=32768)
        values=list(strings(compacted))
        checks={'all_actual_failed_test_outputs_retained':all(any(output in value for value in values) for output in failed),
                'current_requirement_retained':instruction in values,
                'all_native_command_outputs_retained':all(any(item.get('aggregated_output','') in value for value in values) for item in commands),
                'complete_current_tool_suffix_unchanged':compacted[key][-len(items[2:]):]==items[2:]}
        assert all(checks.values()),checks
        rows.append({'stage':'first-stage-hook','protocol':protocol,'checks':checks})
        if key=='messages':compacted_chat={k:v for k,v in compacted.items() if k in ('model','messages','tools','max_tokens')}
    forwarded,audit=budget.compact(compacted_chat,'openai')
    values=list(strings(forwarded))
    checks={'all_actual_failed_test_outputs_retained':all(any(output in value for value in values) for output in failed),
            'current_requirement_retained':instruction in values,
            'complete_current_tool_suffix_unchanged':forwarded['messages'][-len(chat[2:]):]==chat[2:],
            'native_bound':audit['native_input_tokens']+audit['output_reserve']+audit['decoder_headroom']<=audit['context_window']}
    assert all(checks.values()),checks
    rows.append({'stage':'native-final-stage','protocol':'openai','checks':checks,'native_audit':audit})
    result={'owner':'commander diagnostic; not independent QA','verdict':'No demonstrated feedback-retention defect in representative envelopes.',
        'source':source.relative_to(ROOT).as_posix(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'actual_completed_commands':len(commands),'actual_failed_test_outputs':len(failed),'checks':rows,
        'limits':['Campaign HTTP request/response bodies were not captured. Native event text is real, but envelopes and tools are reconstructed representative fixtures.',
                  'This checks the hook and an OpenAI final-stage path. It does not replay the actual Codex Responses-to-Chat wire conversion or prove what the model attended to.',
                  'No inference calls, task-artifact edits, acceptance changes or timeout changes were made.'],
        'next_action':'Retain both failures and continue remaining independent fixed cases; no evidenced repair to frozen compaction code.'}
    (ROOT/'evidence/stress-feedback-review.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'checks':len(rows),'commands':len(commands),'failed_test_outputs':len(failed),'all_passed':True}))

asyncio.run(main())
