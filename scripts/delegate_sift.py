"""Bounded, isolated Claude worker via the owner's local LiteLLM route."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:4000'

def request(path, body, key):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + key, 'x-api-key': key, 'Content-Type': 'application/json', 'anthropic-version': '2023-06-01'})
    return json.load(urllib.request.urlopen(req, timeout=100))

def main():
    master = os.environ['GATEWAY_MASTER_KEY']
    alias = 'local-inference-worker-' + uuid.uuid4().hex[:12]
    key = request('/key/generate', {'key_alias': alias, 'models': ['default'], 'duration': '20m', 'max_budget': 0.5, 'budget_duration': '20m', 'max_parallel_requests': 2}, master)['key']
    try:
        with tempfile.TemporaryDirectory(prefix='local-inference-claude-') as config:
            env = dict(os.environ)
            for name in ['GATEWAY_MASTER_KEY', 'EXPERTS_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDECODE']:
                env.pop(name, None)
            env.update(ANTHROPIC_API_KEY=key, ANTHROPIC_BASE_URL=BASE, ANTHROPIC_MODEL='default', ANTHROPIC_DEFAULT_OPUS_MODEL='default', ANTHROPIC_DEFAULT_SONNET_MODEL='default', ANTHROPIC_DEFAULT_HAIKU_MODEL='default', CLAUDE_CONFIG_DIR=config, CLAUDE_CODE_DISABLE_1M_CONTEXT='1', CLAUDE_CODE_MAX_CONTEXT_TOKENS='256000', API_TIMEOUT_MS='100000', CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
            args = ['claude.cmd', '--bare', '-p', '--model', 'default', '--output-format', 'json', '--max-turns', '2']
            smoke = subprocess.run(args + ['Return exactly LOCAL_INFERENCE_ROUTE_OK'], env=env, capture_output=True, text=True, timeout=150)
            (ROOT/'evidence/worker-smoke.json').write_text(json.dumps({'exit_code':smoke.returncode,'stdout':smoke.stdout,'stderr':smoke.stderr}))
            if smoke.returncode or 'LOCAL_INFERENCE_ROUTE_OK' not in smoke.stdout:
                raise RuntimeError('CLI route smoke failed; see sanitized receipt')
            body = {'model':'default','max_tokens':2048,'messages':[{'role':'user','content':'Call route_marker with marker LOCAL_INFERENCE_TOOL_OK'}], 'tools':[{'name':'route_marker','description':'Return marker','input_schema':{'type':'object','properties':{'marker':{'type':'string'}},'required':['marker']}}], 'tool_choice':{'type':'tool','name':'route_marker'}}
            first = request('/v1/messages', body, key)
            (ROOT/'evidence/worker-tool-first.json').write_text(json.dumps(first,indent=2))
            call = next(x for x in first['content'] if x['type']=='tool_use')
            body['messages'] += [{'role':'assistant','content':first['content']},{'role':'user','content':[{'type':'tool_result','tool_use_id':call['id'],'content':'LOCAL_INFERENCE_TOOL_OK'}]}]
            body.pop('tool_choice')
            second = request('/v1/messages', body, key)
            if 'LOCAL_INFERENCE_TOOL_OK' not in json.dumps(second['content']):
                raise RuntimeError('Native tool continuation failed')
            (ROOT/'evidence/worker-tool-smoke.json').write_text(json.dumps({'first':first,'continuation':second},indent=2))
            prompt = '''Implement a small pure dynamic compaction adapter in this Sift repository. First inspect src/sift/core.py compact_messages, __init__.py, and relevant existing tests. Only write src/sift/dynamic.py and tests/test_dynamic.py. Do not modify other files or commit. API: compact_dynamic(messages, count_tokens, *, context_window=69632, output_reserve=4096, min_target=24576, max_target=65536, preferred_target=32768, fixed_tokens=0, raw_limit=1050000, protocol="openai"). Count request overhead via fixed_tokens, validate all integer limits strictly, compute available=context_window-output_reserve-fixed_tokens; fail closed below min_target; target=min(preferred_target,max_target,available) clamped to min_target. Delegate compaction to existing compact_messages with passed protocol, preserve its guarantees, add chosen target/context/reserve/fixed count to audit. No new dependencies or network. Test normal/no-op, bounded targets, overhead/reserve failure, malformed config, and anthropic tool groups with real compactor. Run focused tests. Handoff actual checks and limits. You have authority for these scoped reversible writes; parent owns acceptance. Do not spawn agents or ask for permission. Five-minute artifact checkpoint, handoff within eight minutes.'''
            args = ['claude.cmd','--bare','-p','--model','default','--output-format','stream-json','--verbose','--max-turns','24','--permission-mode','acceptEdits','--allowedTools','Read,Glob,Grep,Edit,Write,Bash(python -m pytest *)']
            with (ROOT/'tmp/worker.jsonl').open('w') as out, (ROOT/'tmp/worker.stderr.log').open('w') as err:
                done = subprocess.run(args, input=prompt, text=True, cwd=ROOT.parent/'sift', env=env, stdout=out, stderr=err, timeout=480)
            (ROOT/'evidence/worker-exit.json').write_text(json.dumps({'exit_code':done.returncode,'alias':alias,'route':BASE,'model':'default'}))
    finally:
        request('/key/delete', {'key_aliases':[alias]}, master)
        info = request('/key/list', {'page':1,'size':100}, master) if False else None
        print('Task-scoped key revoked', flush=True)

if __name__ == '__main__':
    main()
