"""Run three real productivity tasks with isolated Claude Code against local Sift."""
import json
import re
import os
from pathlib import Path
import subprocess
import tempfile
import time
from setup_env import gateway_key

ROOT=Path(__file__).resolve().parents[1]
TASKS=[
 ('vram-plan', 'Read evidence/host-vram.json, evidence/runtime-vram.json and evidence/model-manifest.json. Then use the Write tool to create tmp/acceptance/vram-plan.md (at most 350 words). Include exact raw model, MTP, and combined disk byte counts from the manifest; distinguish disk size from measured runtime delta. Describe measured host process consumers and safe VRAM reclamation after saving work; never terminate DWM. Include a PowerShell verification command. Do not guess model sizes or contradict runtime evidence; mark unmeasured facts unknown. The output directory already exists. Do not explore other files. End with VRAM_PLAN_DONE.', 'vram-plan.md', 'VRAM_PLAN_DONE'),
 ('model-audit', 'Read evidence/model-manifest.json and compose.yaml. Write tmp/acceptance/model-audit.json with repository, revision, total_weight_bytes (sum downloaded model and MTP byte counts), quantization, configured_context_size (resolve default), and limitations (array). Verify arithmetic using Bash with Python if needed. Do not infer measured GPU residency from file size. Use native Read and Write. End with MODEL_AUDIT_DONE.', 'model-audit.json', 'MODEL_AUDIT_DONE'),
 ('operator-guide', 'Read README.md, compose.yaml and gateway.yaml only. Use the Write tool to create tmp/acceptance/OPERATIONS.md (at most 350 words) with exact commands to start this standalone local LiteLLM Docker stack, check both ports, run scripts/claude_acceptance.py, inspect gateway Sift logs, and stop only this compose project. Explain the configured compaction limit and 4096-token output reserve, and why health is insufficient productivity evidence. The directory exists; do not explore unrelated files. End with OPERATIONS_DONE.', 'OPERATIONS.md', 'OPERATIONS_DONE'),
]

def main():
    dest=ROOT/'tmp/acceptance'
    dest.mkdir(parents=True,exist_ok=True)
    results=[]
    for name,prompt,filename,marker in TASKS:
        artifact=dest/filename
        # This installed CLI exposes a unified Edit tool, not a Write tool.
        # Seed an explicit pending artifact, which cannot satisfy validation.
        artifact.write_text('PENDING_LOCAL_ACCEPTANCE\n',encoding='utf-8')
        prompt=prompt.replace('Use the Write tool','Use the Edit tool').replace('use the Write tool','use the Edit tool').replace('Use Read and Write tools','Use Read and Edit tools').replace('native Read and Write','native Read and Edit')
        prompt+=' The output file already contains PENDING_LOCAL_ACCEPTANCE followed by a newline. Read it, then use Edit to replace its entire contents. This CLI exposes Read and Edit, with no separate Write tool. Do not use Bash.'
        if name=='vram-plan':
            prompt+=' The gpu CSV order in host-vram.json is name,total,used,free. Include exact machine-checkable lines host_total_mib=<number>, host_used_mib=<number>, host_free_mib=<number>. Do not swap used and free. Cite the source filename for each measurement and distinguish the older host snapshot from runtime-vram.json.'
        if name=='operator-guide':
            prompt+=' Use /health/readiness on port 8090; /health is a separate provider health probe, not the gateway readiness endpoint. Use current source defaults and describe native-token budgeting.'
        with tempfile.TemporaryDirectory(prefix='local-qwen-claude-') as config:
            env=dict(os.environ)
            for key in ['GATEWAY_MASTER_KEY','EXPERTS_API_KEY','ANTHROPIC_AUTH_TOKEN','CLAUDECODE']:
                env.pop(key,None)
            env.update(ANTHROPIC_API_KEY=gateway_key(),ANTHROPIC_BASE_URL='http://127.0.0.1:8090',ANTHROPIC_MODEL='qwen3.8-27b',ANTHROPIC_DEFAULT_OPUS_MODEL='qwen3.8-27b',ANTHROPIC_DEFAULT_SONNET_MODEL='qwen3.8-27b',ANTHROPIC_DEFAULT_HAIKU_MODEL='qwen3.8-27b',CLAUDE_CONFIG_DIR=config,CLAUDE_CODE_DISABLE_1M_CONTEXT='1',CLAUDE_CODE_MAX_CONTEXT_TOKENS='1000000',CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1',API_TIMEOUT_MS='600000',CLAUDE_CODE_MAX_OUTPUT_TOKENS='4096')
            args=['claude.cmd','--bare','-p','--model','qwen3.8-27b','--output-format','stream-json','--verbose','--max-turns','10','--permission-mode','acceptEdits','--tools','Read,Edit','--allowedTools','Read,Edit']
            start=time.monotonic()
            try:
                with (dest/(name+'.jsonl')).open('w',encoding='utf-8') as out, (dest/(name+'.stderr.log')).open('w',encoding='utf-8') as err:
                    done=subprocess.run(args,input=prompt,text=True,cwd=ROOT,env=env,stdout=out,stderr=err,timeout=900)
                code=done.returncode
            except subprocess.TimeoutExpired:
                code=-1
            lines=(dest/(name+'.jsonl')).read_text(encoding='utf-8').splitlines()
            events=[json.loads(line) for line in lines if line.strip().startswith('{')]
            calls=[block['name'] for event in events if event.get('type')=='assistant' for block in event.get('message',{}).get('content',[]) if block.get('type')=='tool_use']
            final=next((e for e in reversed(events) if e.get('type')=='result'),{})
            passed=code==0 and not final.get('is_error',True) and marker in final.get('result','') and artifact.exists() and 'Edit' in calls and 'Read' in calls and 'PENDING_LOCAL_ACCEPTANCE' not in artifact.read_text(encoding='utf-8')
            validation=None
            if passed and filename.endswith('.json'):
                obj=json.loads(artifact.read_text(encoding='utf-8'))
                manifest=json.loads((ROOT/'evidence/model-manifest.json').read_text())
                expected_context=int(re.search(r'CONTEXT_SIZE:-([0-9]+)',(ROOT/'compose.yaml').read_text()).group(1))
                validation=obj.get('total_weight_bytes')==sum(x['bytes'] for x in manifest['files']) and obj.get('configured_context_size')==expected_context
                passed=passed and validation
            if passed and name=='vram-plan':
                text=artifact.read_text(encoding='utf-8').replace(',','')
                manifest=json.loads((ROOT/'evidence/model-manifest.json').read_text())
                values=[x['bytes'] for x in manifest['files']]
                validation=all(str(n) in text for n in values+[sum(values)])
                host=json.loads((ROOT/'evidence/host-vram.json').read_text())
                gpu=[int(re.search(r'[0-9]+',x).group()) for x in host['gpu'][0].split(',')[1:]]
                validation=validation and all(re.search(rf'{label}\s*=\s*{number}\b',text) for label,number in zip(['host_total_mib','host_used_mib','host_free_mib'],gpu))
                passed=passed and validation
            results.append({'task':name,'passed':passed,'exit_code':code,'seconds':round(time.monotonic()-start,2),'native_tools':calls,'artifact':str(artifact.relative_to(ROOT)),'arithmetic_valid':validation,'usage':final.get('usage')})
            (ROOT/'evidence/claude-acceptance.json').write_text(json.dumps(results,indent=2))
            print(json.dumps(results[-1]),flush=True)
    raise SystemExit(0 if all(x['passed'] for x in results) else 1)

if __name__=='__main__': main()
