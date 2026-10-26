"""Read-only independent CLI review, reusing proven LiteLLM route evidence."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
from delegate_sift import request, ROOT, BASE

def main():
    master=os.environ['GATEWAY_MASTER_KEY']
    alias='local-inference-review-'+uuid.uuid4().hex[:10]
    key=request('/key/generate',{'key_alias':alias,'models':['default'],'duration':'15m','max_budget':0.5,'budget_duration':'15m','max_parallel_requests':2},master)['key']
    try:
        with tempfile.TemporaryDirectory(prefix='inference-review-') as config:
            env=dict(os.environ)
            for k in ['GATEWAY_MASTER_KEY','EXPERTS_API_KEY','ANTHROPIC_AUTH_TOKEN','CLAUDECODE']: env.pop(k,None)
            env.update(ANTHROPIC_API_KEY=key,ANTHROPIC_BASE_URL=BASE,ANTHROPIC_MODEL='default',ANTHROPIC_DEFAULT_SONNET_MODEL='default',ANTHROPIC_DEFAULT_OPUS_MODEL='default',ANTHROPIC_DEFAULT_HAIKU_MODEL='default',CLAUDE_CONFIG_DIR=config,CLAUDE_CODE_DISABLE_1M_CONTEXT='1',CLAUDE_CODE_MAX_CONTEXT_TOKENS='256000',API_TIMEOUT_MS='100000')
            prompt='''Read-only independent review. You are not the author of this integration. Inspect app/proxy.py, compose.yaml, scripts/claude_acceptance.py, scripts/context_acceptance.py, ../sift/src/sift/dynamic.py, and evidence/sift-tests.txt. Primary implementation worker wrote only Sift dynamic adapter; parent wrote proxy and harness. Assess concrete correctness bugs: native Anthropic protocol, preserving mandatory system/tool blocks, dynamic input/output/tool budgets, 256k-1M raw handling, exact native final token count, streaming, reproducible Docker and acceptance evidence. Do not run shell, write files, delegate, or request permissions. Use Read tools. Route smoke and native tool continuation already passed at 127.0.0.1:4000 default; do not repeat setup. Return at most 6 actionable findings with paths, actual triggers and severity; distinguish evidence gaps from bugs. Finish within 12 turns/four minutes. Final verdict PASS or NEEDS_FIXES; do not certify live productivity absent runtime receipts.'''
            prompt='Independent source review. Review only the exact files provided below for concrete correctness failures. Do not call tools or implement. Give at most 5 actionable findings with actual triggers, or PASS; distinguish missing live evidence. Keep the answer under 700 words. Prior tool-reader attempt exceeded four-minute wall limit without a verdict; this is one bounded source-packet alternative.\n'
            for path in ['app/budget.py','app/gateway.py','compose.yaml','gateway.yaml','scripts/claude_acceptance.py','scripts/context_acceptance.py','../sift/src/sift/dynamic.py','evidence/proxy-tests.txt','evidence/sift-suite.txt','evidence/claude-acceptance.json','evidence/context-acceptance.json']:
                prompt+='\nFILE '+path+'\n'+(ROOT/path).read_text(encoding='utf-8')+'\n'
            env['CLAUDE_CODE_MAX_OUTPUT_TOKENS']='4096'
            args=['claude.cmd','--bare','-p','--model','default','--output-format','stream-json','--verbose','--max-turns','1','--tools','']
            with (ROOT/'tmp/review.jsonl').open('w',encoding='utf-8') as out,(ROOT/'tmp/review.stderr.log').open('w',encoding='utf-8') as err:
                done=subprocess.run(args,input=prompt,text=True,env=env,cwd=ROOT,stdout=out,stderr=err,timeout=240)
            events=[json.loads(s) for s in (ROOT/'tmp/review.jsonl').read_text(encoding='utf-8').splitlines() if s.startswith('{')]
            final=next((x for x in reversed(events) if x.get('type')=='result'),{})
            (ROOT/'evidence/integration-review.json').write_text(json.dumps({'exit_code':done.returncode,'final':final},indent=2))
    finally:
        request('/key/delete',{'key_aliases':[alias]},master)
        # Listing keys is read-only; persist only whether this task alias remains.
        req=__import__('urllib.request',fromlist=['Request']).Request(BASE+'/key/list?page=1&size=100',headers={'Authorization':'Bearer '+master})
        data=json.load(__import__('urllib.request',fromlist=['urlopen']).urlopen(req,timeout=20))
        absent=alias not in json.dumps(data)
        (ROOT/'evidence/review-key-cleanup.json').write_text(json.dumps({'alias':alias,'absent_after_revoke':absent}))

if __name__=='__main__': main()
