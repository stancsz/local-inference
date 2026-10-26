"""Mandatory CPU Sift boundary in front of llama.cpp's native Messages API."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import time
import urllib.error
import urllib.request

from sift import CompactionError
from sift.dynamic import compact_dynamic

BASE = os.environ.get('INFERENCE_URL', 'http://127.0.0.1:8091')
WINDOW = int(os.environ.get('CONTEXT_SIZE', '28672'))
TARGET = int(os.environ.get('SIFT_TARGET', '24576'))
LOCK = threading.Lock()
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def upstream(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type':'application/json'})
    return OPENER.open(req, timeout=600)

def count(payload):
    with upstream('/v1/messages/count_tokens', payload) as response:
        return json.load(response)['input_tokens']

def compact(payload):
    """Use inexpensive selection estimates; enforce final native template token count."""
    p = deepcopy(payload)
    output = min(p.get('max_tokens', 4096), 4096)
    if type(output) is not int or output <= 0:
        raise ValueError('max_tokens must be a positive integer')
    p['max_tokens'] = output
    p['model'] = 'qwen3.8-27b'
    # Sift protects leading system messages as well as current user/tool work.
    messages = p['messages']
    if p.get('system'):
        messages = [{'role':'system','content':p['system']}] + messages
    fixed = {k:v for k,v in p.items() if k not in ('messages','system')}
    overhead = count(dict(fixed, messages=[{'role':'user','content':'x'}], system=p.get('system', '')))
    def estimate(items):
        # Conservative UTF-8 estimate explicitly includes message structure.
        return (len(json.dumps(items,ensure_ascii=False).encode()) + 1)//2
    started = time.monotonic()
    result = compact_dynamic(messages, estimate, context_window=WINDOW,
        output_reserve=output, preferred_target=TARGET, fixed_tokens=overhead,
        raw_limit=4_000_000, protocol='anthropic')
    selected = result.messages
    if selected and selected[0]['role']=='system':
        p['system'] = selected[0]['content']
        selected = selected[1:]
    p['messages'] = selected
    actual = count(p)
    if actual + output > WINDOW:
        raise CompactionError('native tokenizer count exceeds available context')
    audit = dict(result.audit, native_input_tokens=actual, output_reserve=output,
        compaction_seconds=round(time.monotonic()-started,4),
        selection_counting='utf8-bytes/2 estimate', raw_limit_estimate=4_000_000)
    return p, audit

class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, fmt, *args):
        print(json.dumps({'event':'http','status':args[1] if len(args)>1 else ''}),flush=True)
    def send_json(self, status, obj):
        body=json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path not in ('/health','/healthz','/v1/models'):
            return self.send_json(404,{'error':'not_found'})
        try:
            with upstream('/v1/models' if self.path=='/v1/models' else '/health') as response:
                self.send_json(response.status,json.load(response))
        except Exception as error:
            self.send_json(503,{'error':type(error).__name__})
    def do_POST(self):
        if self.path not in ('/v1/messages','/v1/messages/count_tokens'):
            return self.send_json(404,{'error':'only_anthropic_messages_supported'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 32*1024*1024:
                return self.send_json(413,{'error':'body_limit'})
            raw=self.rfile.read(length)
            payload=json.loads(raw)
            if self.path.endswith('/count_tokens'):
                return self.send_json(200,{'input_tokens':count(payload)})
            with LOCK:
                forwarded,audit=compact(payload)
                print(json.dumps({'event':'compaction',**audit}),flush=True)
                with upstream(self.path,forwarded) as response:
                    self.send_response(response.status)
                    self.send_header('Content-Type',response.headers.get('Content-Type','application/json'))
                    self.send_header('Connection','close')
                    self.end_headers()
                    self.close_connection=True
                    while chunk:=response.read1(65536):
                        self.wfile.write(chunk)
                        self.wfile.flush()
        except urllib.error.HTTPError as error:
            self.send_json(error.code,{'error':'upstream_error','detail':error.read(4096).decode(errors='replace')})
        except (CompactionError,ValueError,KeyError,TypeError) as error:
            self.send_json(422,{'error':'compaction_rejected','detail':str(error)})
        except (BrokenPipeError,ConnectionResetError):
            pass
        except Exception as error:
            self.send_json(502,{'error':type(error).__name__})

if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',8090),Handler).serve_forever()
