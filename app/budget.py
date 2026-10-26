"""Mandatory CPU Sift boundary in front of llama.cpp's native Messages API."""
from copy import deepcopy
import json
import hashlib
import os
import time
import urllib.error
import urllib.request

from sift import CompactionError
from sift.dynamic import compact_dynamic

BASE = os.environ.get('INFERENCE_URL', 'http://127.0.0.1:8091')
WINDOW = int(os.environ.get('CONTEXT_SIZE', '69632'))
TARGET = int(os.environ.get('SIFT_TARGET', '32768'))
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def upstream(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type':'application/json'})
    return OPENER.open(req, timeout=600)

def count(payload, protocol='anthropic'):
    if protocol=='anthropic':
        with upstream('/v1/messages/count_tokens', payload) as response:
            return json.load(response)['input_tokens']
    with upstream('/apply-template',payload) as response:
        prompt=json.load(response)['prompt']
    with upstream('/tokenize',{'content':prompt,'add_special':False,'parse_special':True}) as response:
        return len(json.load(response)['tokens'])

def compact(payload, protocol='anthropic'):
    """Budget and select using the backend's native full-request tokenizer."""
    p = deepcopy(payload)
    output = p.get('max_tokens', 4096)
    if type(output) is not int or not 0 < output <= 4096:
        raise ValueError('max_tokens must be an integer in 1..4096')
    p['max_tokens'] = output
    p['model'] = 'qwen3.8-27b'
    # Sift protects leading system messages as well as current user/tool work.
    messages = p['messages']
    if p.get('system'):
        messages = [{'role':'system','content':p['system']}] + messages
    fixed = {k:v for k,v in p.items() if k not in ('messages','system')}
    cache={}
    def restore(items):
        request=dict(fixed,messages=items)
        if protocol=='anthropic' and items and items[0]['role']=='system':
            request['system']=items[0]['content']
            request['messages']=items[1:]
        return request
    def native(items):
        request=restore(items)
        digest=request_digest(request)
        if digest not in cache:
            cache[digest]=count(request,protocol)
        return cache[digest]
    started = time.monotonic()
    # The counter already includes tools/system/template: subtracting fixed
    # overhead again would double-count it. All target units are native tokens.
    result = compact_dynamic(messages, native, context_window=WINDOW,
        output_reserve=output, preferred_target=TARGET, fixed_tokens=0,
        raw_limit=1_050_000, protocol=protocol)
    p=restore(result.messages)
    actual = count(p,protocol)
    if actual + output > WINDOW:
        raise CompactionError('native tokenizer count exceeds available context')
    audit = dict(result.audit, native_input_tokens=actual, output_reserve=output,
        raw_request_sha256=request_digest(payload),
        compaction_seconds=round(time.monotonic()-started,4),
        selection_counting='native full-request tokenizer', tokenizer_calls=len(cache)+1,
        raw_native_token_limit=1_050_000)
    return p, audit

def request_digest(payload):
    fields={k:payload.get(k,default) for k,default in [('messages',[]),('system',None),('tools',[]),('max_tokens',4096)]}
    return hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

