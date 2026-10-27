"""Mandatory Sift callback for the standalone local LiteLLM gateway."""
import asyncio
import json
import threading
import os
import time
from fastapi import HTTPException
from litellm.integrations.custom_logger import CustomLogger
from sift import CompactionError
from budget import compact

PROTOCOLS={'completion':'openai','acompletion':'openai','anthropic_messages':'anthropic','aanthropic_messages':'anthropic'}
FIELDS={'model','messages','system','tools','tool_choice','max_tokens','max_completion_tokens','temperature','top_p','stop','stop_sequences','response_format','seed','reasoning_effort','thinking','parallel_tool_calls'}

def protect_codex_instructions(data):
    """Keep caller instruction updates in Qwen's supported leading block.

    Codex resume emits developer messages between completed turns. Qwen's
    template rejects them there. Preserve every instruction text in order,
    before native Sift counting; never demote instructions into user history.
    """
    items=data.get('input')
    if not isinstance(items,list):return
    updates=[]
    history=[]
    for item in items:
        if (not isinstance(item,dict) or item.get('type','message') != 'message'
                or item.get('role') not in {'developer','system'}):
            history.append(item)
            continue
        content=item.get('content')
        if isinstance(content,str):updates.append(content)
        elif isinstance(content,list) and all(isinstance(b,dict) and b.get('type') in {'input_text','text'} and isinstance(b.get('text'),str) for b in content):
            updates.extend(b['text'] for b in content)
        else:raise HTTPException(422,detail='Local Codex instruction updates require text content')
    if updates:
        initial=data.get('instructions')
        if initial is not None and not isinstance(initial,str):
            raise HTTPException(422,detail='Local Codex instructions require text content')
        data['instructions']='\n\n'.join(([initial] if initial is not None else [])+updates)
        data['input']=history

class LocalSift(CustomLogger):
    def __init__(self,wait_seconds=15):
        super().__init__()
        self.slot=threading.BoundedSemaphore(1)
        self.wait_seconds=wait_seconds

    async def async_pre_call_hook(self,user_api_key_dict,cache,data,call_type):
        if call_type in {'responses','aresponses'}:
            # This dedicated alias translates to Chat Completions on this same
            # gateway. The inner qwen route performs mandatory native Sift.
            # Never hold the slot while waiting for the inner request.
            if data.get('model')!='qwen3.8-27b-codex':
                raise HTTPException(422,detail='Responses requires the local qwen3.8-27b-codex bridge alias')
            if data.get('previous_response_id') or data.get('conversation'):
                raise HTTPException(422,detail='Local Responses requires complete stateless input')
            if data.get('use_chat_completions_api',True) is not True:
                raise HTTPException(422,detail='Local Responses must use the guarded Chat bridge')
            output=data.get('max_output_tokens',4096)
            if type(output) is not int or not 0<output<=4096:
                raise HTTPException(422,detail='max_output_tokens must be an integer in 1..4096')
            protect_codex_instructions(data)
            data['max_output_tokens']=output
            data['use_chat_completions_api']=True
            data['api_base']='http://127.0.0.1:8090/v1'
            data['api_key']=os.environ['LITELLM_MASTER_KEY']
            return data
        protocol=PROTOCOLS.get(call_type)
        if protocol is None:
            raise HTTPException(422,detail='Local gateway supports Chat Completions and Anthropic Messages only')
        deadline=time.monotonic()+self.wait_seconds
        while not self.slot.acquire(blocking=False):
            if time.monotonic()>=deadline:
                raise HTTPException(429,detail='Sift busy',headers={'Retry-After':'1'})
            await asyncio.sleep(.05)
        def run():
            try:
                payload={k:v for k,v in data.items() if k in FIELDS}
                forwarded,audit=compact(payload,protocol)
                data['messages']=forwarded['messages']
                data['max_tokens']=forwarded['max_tokens']
                data.pop('max_completion_tokens',None)
                if 'system' in forwarded: data['system']=forwarded['system']
                data.setdefault('metadata',{})['local_sift']=audit
                print(json.dumps({'event':'local_sift',**audit}),flush=True)
                try:
                    with open(os.environ.get('SIFT_AUDIT_PATH','/evidence/gateway-audit.jsonl'),'a',encoding='utf-8') as stream:
                        stream.write(json.dumps(audit)+'\n')
                except OSError:
                    print(json.dumps({'event':'audit_write_failed','compaction_input_sha256':audit['compaction_input_sha256']}),flush=True)
                return data
            except (CompactionError,ValueError,TypeError,KeyError) as error:
                raise HTTPException(422,detail=f'Sift: {error}') from error
            finally:
                self.slot.release()
        # Slot is held by the running worker even if the client disconnects.
        try:
            task=asyncio.get_running_loop().run_in_executor(None,run)
        except BaseException:
            self.slot.release()
            raise
        task.add_done_callback(lambda future: None if future.cancelled() else future.exception())
        await asyncio.wait((task,))
        return task.result()

local_sift=LocalSift()
