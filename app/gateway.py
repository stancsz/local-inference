"""Mandatory Sift callback for the standalone local LiteLLM gateway."""
import asyncio
import json
import threading
import os
from fastapi import HTTPException
from litellm.integrations.custom_logger import CustomLogger
from sift import CompactionError
from budget import compact

PROTOCOLS={'completion':'openai','acompletion':'openai','anthropic_messages':'anthropic','aanthropic_messages':'anthropic'}
FIELDS={'model','messages','system','tools','tool_choice','max_tokens','temperature','top_p','stop','stop_sequences'}

class LocalSift(CustomLogger):
    def __init__(self):
        super().__init__()
        self.slot=threading.BoundedSemaphore(1)

    async def async_pre_call_hook(self,user_api_key_dict,cache,data,call_type):
        protocol=PROTOCOLS.get(call_type)
        if protocol is None:
            raise HTTPException(422,detail='Local gateway supports Chat Completions and Anthropic Messages only')
        if not self.slot.acquire(blocking=False):
            raise HTTPException(429,detail='Sift busy',headers={'Retry-After':'1'})
        def run():
            try:
                payload={k:v for k,v in data.items() if k in FIELDS}
                forwarded,audit=compact(payload,protocol)
                data['messages']=forwarded['messages']
                data['max_tokens']=forwarded['max_tokens']
                if 'system' in forwarded: data['system']=forwarded['system']
                data.setdefault('metadata',{})['local_sift']=audit
                print(json.dumps({'event':'local_sift',**audit}),flush=True)
                with open(os.environ.get('SIFT_AUDIT_PATH','/evidence/gateway-audit.jsonl'),'a',encoding='utf-8') as stream:
                    stream.write(json.dumps(audit)+'\n')
                return data
            except (CompactionError,ValueError,TypeError,KeyError) as error:
                raise HTTPException(422,detail=f'Sift: {error}') from error
            finally:
                self.slot.release()
        # Slot is held by the running worker even if the client disconnects.
        task=asyncio.get_running_loop().run_in_executor(None,run)
        task.add_done_callback(lambda future: None if future.cancelled() else future.exception())
        await asyncio.wait((task,))
        return task.result()

    async def async_post_call_response_headers_hook(self,data,user_api_key_dict,response,request_headers=None,litellm_call_info=None):
        metadata=data.get('litellm_metadata') or data.get('metadata') or {}
        audit=metadata.get('local_sift')
        if not audit: return None
        return {'x-local-sift-native-input-tokens':str(audit['native_input_tokens']),
                'x-local-sift-target':str(audit['target_tokens']),
                'x-local-sift-compacted':str(audit['compacted']).lower()}

local_sift=LocalSift()
