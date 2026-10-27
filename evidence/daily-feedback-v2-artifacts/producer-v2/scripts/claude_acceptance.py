"""Run three real productivity tasks with isolated Claude Code against local Sift."""
import json
import re
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import time
from setup_env import gateway_key
from verify_artifacts import publish

ROOT=Path(__file__).resolve().parents[1]

def input_budget_invariant(text):
    return bool(re.search(r'\btarget is part of the input budget(?:,|\s+and(?: is)?)\s+never added to it\b',text,re.I))

def validate_operator_guide(text):
    numeric_text=re.sub(r'(?<=\d),(?=\d)','',text)
    required={'docker compose up -d --build','curl.exe http://127.0.0.1:8090/health/readiness',
        'curl.exe http://127.0.0.1:8091/health','python scripts/claude_acceptance.py',
        'docker compose logs --no-color gateway > tmp/sift-runtime.log','docker compose down'}
    configuration={'context_window=40960','sift_target=32768','output_reserve=4096','draft_tokens=4'}
    commands={line.strip() for block in re.findall(r'```powershell\s*\n(.*?)```',text,re.S) for line in block.splitlines()}
    return (len(text.split())<=350 and required<=commands and commands<=required|configuration
        and all(term in text for term in configuration)
        and all(term in numeric_text.lower() for term in ['adaptive','anchor','24576','36608'])
        and input_budget_invariant(text) and '256 tokens' in text and 'decoder headroom' in text)
TASKS=[
 ('vram-plan', 'Read evidence/host-vram.json, evidence/runtime-vram.json and evidence/model-manifest.json. Then use the Write tool to create tmp/acceptance/vram-plan.md (at most 350 words). Include exact raw model, MTP, and combined disk byte counts from the manifest; distinguish disk size from measured runtime delta. Describe measured host process consumers and safe VRAM reclamation after saving work; never terminate DWM. Include a PowerShell verification command. Do not guess model sizes or contradict runtime evidence; mark unmeasured facts unknown. The output directory already exists. Do not explore other files. End with VRAM_PLAN_DONE.', 'vram-plan.md', 'VRAM_PLAN_DONE'),
 ('model-audit', 'Read evidence/model-manifest.json and compose.yaml. Write tmp/acceptance/model-audit.json with repository, revision, total_weight_bytes (sum downloaded model and MTP byte counts), quantization, configured_context_size (resolve default), and limitations (array). Verify arithmetic using Bash with Python if needed. Do not infer measured GPU residency from file size. Use native Read and Write. End with MODEL_AUDIT_DONE.', 'model-audit.json', 'MODEL_AUDIT_DONE'),
 ('operator-guide', 'Read README.md, compose.yaml and gateway.yaml only. Use the Write tool to create tmp/acceptance/OPERATIONS.md (at most 350 words) with exact commands to start this standalone local LiteLLM Docker stack, check both ports, run scripts/claude_acceptance.py, inspect gateway Sift logs, and stop only this compose project. Explain the configured compaction limit and 4096-token output reserve, and why health is insufficient productivity evidence. The directory exists; do not explore unrelated files. End with OPERATIONS_DONE.', 'OPERATIONS.md', 'OPERATIONS_DONE'),
]

def validate_model_audit(obj, manifest, expected_context):
    required={'repository','revision','total_weight_bytes','quantization','configured_context_size','limitations'}
    if not isinstance(obj,dict) or not required<=set(obj)<=required|{'artifacts'}:
        return False
    if 'artifacts' in obj:
        expected={'main_gguf':next(Path(f['file']).name for f in manifest['files'] if not f['file'].startswith('MTP/')),
                  'mtp_gguf':next(Path(f['file']).name for f in manifest['files'] if f['file'].startswith('MTP/'))}
        if obj['artifacts']!=expected:return False
    quant=obj.get('quantization')
    if isinstance(quant,dict):
        mapping=quant.get('main')=='IQ3_XXS' and quant.get('mtp')=='Q4_0'
    elif isinstance(quant,str):
        mapping=bool(re.search(r'main(?:\s+|[=:]\s*)IQ3_XXS',quant,re.I)) and bool(re.search(r'MTP(?:\s+|[=:]\s*)Q4_0',quant,re.I))
    else:
        return False
    return bool(mapping and obj.get('total_weight_bytes')==sum(x['bytes'] for x in manifest['files'])
        and obj.get('configured_context_size')==expected_context
        and obj.get('repository')==manifest['repository'] and obj.get('revision')==manifest['revision']
        and isinstance(obj.get('limitations'),list) and bool(obj['limitations'])
        and all(Path(f['file']).name in json.dumps(obj) for f in manifest['files']))


def validate_process_rows(text, processes):
    expected={(str(p['process']).lower(),str(p['pid'])):float(p['dedicated_mib']) for p in processes}
    for line in text.splitlines():
        cells=[c.strip().strip('`') for c in line.strip().strip('|').split('|')]
        if len(cells)==3 and cells[1].isdigit():
            try:
                if expected.get((cells[0].lower(),cells[1]))!=float(cells[2]): return False
            except ValueError:
                return False
    return True


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--task',action='append',choices=[t[0] for t in TASKS])
    parser.add_argument('--output-dir',type=Path,help='Fresh task-owned output directory; preserve previous acceptance evidence')
    options=parser.parse_args()
    dest=options.output_dir.resolve() if options.output_dir else ROOT/'tmp/acceptance'
    if options.output_dir:
        dest.relative_to(ROOT.resolve())
    dest.mkdir(parents=True,exist_ok=not bool(options.output_dir))
    receipt_path=dest/'claude-acceptance.json' if options.output_dir else ROOT/'evidence/claude-acceptance.json'
    results=json.loads(receipt_path.read_text()) if options.task and receipt_path.exists() else []
    for name,prompt,filename,marker in TASKS:
        if options.task and name not in options.task: continue
        artifact=dest/filename
        # This installed CLI exposes a unified Edit tool, not a Write tool.
        # Seed an explicit pending artifact, which cannot satisfy validation.
        artifact.write_text('PENDING_LOCAL_ACCEPTANCE\n',encoding='utf-8')
        prompt=prompt.replace('tmp/acceptance/'+filename,artifact.as_posix())
        prompt+=' The ONLY writable artifact is this exact absolute path: '+artifact.as_posix()+'. Do not edit any other file or previous acceptance artifact.'
        prompt=prompt.replace('Use the Write tool','Use the Edit tool').replace('use the Write tool','use the Edit tool').replace('Use Read and Write tools','Use Read and Edit tools').replace('native Read and Write','native Read and Edit')
        prompt+=' The output file already contains PENDING_LOCAL_ACCEPTANCE followed by a newline. Read it, then use Edit to replace its entire contents. This CLI exposes Read and Edit, with no separate Write tool.'
        if name!='model-audit': prompt+=' Do not use Bash.'
        if name=='vram-plan':
            prompt+=' The gpu CSV order in host-vram.json is name,total,used,free. Include exact machine-checkable lines host_total_mib=<number>, host_used_mib=<number>, host_free_mib=<number>. Do not swap used and free. Cite the source filename for each measurement and distinguish the older host snapshot from runtime-vram.json.'
            prompt+=' Report only the three largest measured process consumers. If using a process table, use columns Process | PID | Dedicated MiB and copy exact source values. Do not list other processes or guess PIDs.'
            prompt+=' Include the exact safety sentence: Never terminate DWM.'
        if name=='operator-guide':
            prompt+=' Use /health/readiness on port 8090. Document only the current daily default, not optional long profiles: verify compose.yaml shows 40960 total context, SIFT_TARGET=32768 as the adaptive policy anchor (not a fixed forwarded budget), 4096 output reserve and 4 draft tokens. Include exact configuration lines context_window=40960, sift_target=32768, output_reserve=4096, draft_tokens=4. Explain request-adaptive budgeting and its daily 24576..36608 range when reserving all 4096 output tokens. Short requests pass unchanged; 36608 is a ceiling, not a required request size. Do not discuss 64k profiles in this short daily runbook.'
            prompt+=' Aim for 180-220 words and stay under the 350-word hard limit, counting headings and code. Keep commands and brief explanations only. The Sift target is part of the input budget, never added to it; a further 256 tokens are held for decoder headroom. A readiness response alone proves process readiness, not productive work.'
            prompt+=' Explicitly call the policy adaptive. Put commands in fenced powershell blocks. For logs use exactly: docker compose logs --no-color gateway > tmp/sift-runtime.log'
        if name=='model-audit':
            prompt+=' The quantization field must identify BOTH the main IQ3_XXS and MTP Q4_0 quantizations from their filenames. Keep all required fields, and verify repository/revision against the manifest.'
            prompt+=' Include both exact GGUF basenames somewhere in the JSON so each label is traceable to its artifact. Do not infer Sift policy from SIFT_TARGET alone; omit that discussion unless you read README.md to verify its adaptive meaning.'
            prompt+=' If using the optional artifacts object, its only keys must be main_gguf and mtp_gguf, with the corresponding exact basenames as values.'
            prompt+=' Use Bash with python -c to calculate the exact sum from the manifest; do not calculate the large integers mentally. Bash is allowed only for that Python calculation. Use Read/Edit for the artifact.'
        with tempfile.TemporaryDirectory(prefix='local-qwen-claude-') as config:
            env=dict(os.environ)
            for key in ['GATEWAY_MASTER_KEY','EXPERTS_API_KEY','ANTHROPIC_AUTH_TOKEN','CLAUDECODE']:
                env.pop(key,None)
            env.update(ANTHROPIC_API_KEY=gateway_key(),ANTHROPIC_BASE_URL='http://127.0.0.1:8090',ANTHROPIC_MODEL='qwen3.8-27b',ANTHROPIC_DEFAULT_OPUS_MODEL='qwen3.8-27b',ANTHROPIC_DEFAULT_SONNET_MODEL='qwen3.8-27b',ANTHROPIC_DEFAULT_HAIKU_MODEL='qwen3.8-27b',CLAUDE_CONFIG_DIR=config,CLAUDE_CODE_DISABLE_1M_CONTEXT='1',CLAUDE_CODE_MAX_CONTEXT_TOKENS='1000000',CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1',API_TIMEOUT_MS='600000',CLAUDE_CODE_MAX_OUTPUT_TOKENS='4096')
            tools='Read,Edit,Bash' if name=='model-audit' else 'Read,Edit'
            allowed='Read,Edit,Bash(python -c *)' if name=='model-audit' else 'Read,Edit'
            args=['claude.cmd','--bare','-p','--model','qwen3.8-27b','--output-format','stream-json','--verbose','--max-turns','10','--permission-mode','acceptEdits','--tools',tools,'--allowedTools',allowed]
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
                validation=validate_model_audit(obj,manifest,expected_context)
                passed=passed and validation
            if passed and filename.endswith('.md'):
                text=artifact.read_text(encoding='utf-8')
                passed=len(text.split())<=350
                if name=='vram-plan':
                    passed=passed and all(term in text.lower() for term in ['dwm','never terminate','saving','nvidia-smi','host-vram.json','runtime-vram.json'])
                    processes=json.loads((ROOT/'evidence/host-vram.json').read_text())['processes']
                    passed=passed and validate_process_rows(text,processes)
                if name=='operator-guide':
                    passed=passed and validate_operator_guide(text)
            if passed and name=='vram-plan':
                text=artifact.read_text(encoding='utf-8').replace(',','')
                manifest=json.loads((ROOT/'evidence/model-manifest.json').read_text())
                values=[x['bytes'] for x in manifest['files']]
                validation=all(str(n) in text for n in values+[sum(values)])
                host=json.loads((ROOT/'evidence/host-vram.json').read_text())
                gpu=[int(re.search(r'[0-9]+',x).group()) for x in host['gpu'][0].split(',')[1:]]
                validation=validation and all(re.search(rf'{label}\s*=\s*{number}\b',text) for label,number in zip(['host_total_mib','host_used_mib','host_free_mib'],gpu))
                passed=passed and validation
            results=[r for r in results if r['task']!=name]
            results.append({'task':name,'passed':passed,'exit_code':code,'seconds':round(time.monotonic()-start,2),'native_tools':calls,'artifact':str(artifact.relative_to(ROOT)),'arithmetic_valid':validation,'usage':final.get('usage')})
            if passed: results[-1]=publish(results[-1],trace_directory=dest,destination=dest/'published' if options.output_dir else None)
            receipt_path.write_text(json.dumps(results,indent=2))
            print(json.dumps(results[-1]),flush=True)
    raise SystemExit(0 if all(x['passed'] for x in results) else 1)

if __name__=='__main__': main()
