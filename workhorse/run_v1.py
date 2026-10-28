"""Run a sealed task pack through native Claude/local Qwen, preserving failures."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import daily_artifacts as native
from setup_env import gateway_key

ROUTE='http://127.0.0.1:8090'
MODEL='qwen3.8-27b'
PHASE_SECONDS=180
MAX_REPAIRS=1
MAX_MODEL_TURNS=10

def digest(data):return hashlib.sha256(data).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
def dump(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
def normalized(text):return text.replace('\r\n','\n').replace('\r','\n')
def path_at(workspace,value):
 path=Path(value)
 return (path if path.is_absolute()else workspace/path).resolve()

def inspect_native(events,workspace,artifact,previous,required_reads):
 """Bind successful native reads/edits to the actual single permitted artifact."""
 successful=native.successful_tool_ids(events);current=normalized(previous)
 reads=set();tools=[];errors=0;edits=0;violations=[]
 for event in events:
  if event.get('type')=='user':
   errors+=sum(bool(b.get('is_error'))for b in event.get('message',{}).get('content',[])if isinstance(b,dict)and b.get('type')=='tool_result')
  if event.get('type')!='assistant':continue
  for block in event.get('message',{}).get('content',[]):
   if not isinstance(block,dict)or block.get('type')!='tool_use':continue
   name=block.get('name');arguments=block.get('input',{});done=block.get('id')in successful
   if done:tools.append(name)
   if name in ('Read','Edit','Write'):
    target=path_at(workspace,arguments.get('file_path',''))
    if not target.is_relative_to(workspace.resolve()):violations.append('outside workspace '+str(target))
    if name=='Read'and done:reads.add(target)
    if name in ('Edit','Write')and target!=artifact.resolve():violations.append('unexpected writable path '+str(target))
    if name=='Write':violations.append('unexpected Write tool; existing artifact requires Edit')
    if name=='Edit'and done and target==artifact.resolve():
     old=normalized(arguments.get('old_string',''));new=normalized(arguments.get('new_string',''))
     if not old or old not in current:violations.append('edit cannot reconstruct previous bytes')
     else:current=current.replace(old,new,-1 if arguments.get('replace_all')else 1);edits+=1
   elif name=='Bash':
    command=arguments.get('command','').strip()
    if command not in ('python -m unittest -q','python -m unittest -q test_public'):violations.append('unexpected command '+command)
   else:violations.append('unexpected tool '+str(name))
 terminal=native.final_result(events)
 actual=normalized(artifact.read_text(encoding='utf-8'))
 missing=sorted(str(p.relative_to(workspace))for p in required_reads-reads)
 return {'terminal_success':bool(terminal)and not terminal.get('is_error',False),
         'session_id':terminal.get('session_id'),'successful_tools':tools,'tool_errors':errors,
         'successful_edits':edits,'edit_reconstruction_matches':edits>0 and current==actual,
         'missing_reads':missing,'scope_violations':violations,'usage':terminal.get('usage'),
         'model_usage':terminal.get('modelUsage'),'reported_cost_usd':terminal.get('total_cost_usd')}

def run(output):
 from workhorse.cases_v1 import CASES,check
 output=output.resolve();output.mkdir(parents=True,exist_ok=False)
 sealed=json.loads((ROOT/'evidence/workhorse-v1-plan.json').read_text())
 sources={name:digest((ROOT/name).read_bytes())for name in sealed['source_sha256']}
 assert sources==sealed['source_sha256'],'sealed evaluation source changed'
 assert [c['id']for c in CASES]==sealed['case_ids'],'sealed case order changed'
 assert [PHASE_SECONDS,MAX_REPAIRS,MAX_MODEL_TURNS]==sealed['limits'],'sealed limits changed'
 plan={'version':1,'recorded_at':stamp(),'route':ROUTE,'model':MODEL,'case_ids':[c['id']for c in CASES],
       'source_sha256':sources,'phase_deadline_seconds':PHASE_SECONDS,'maximum_repair_phases':MAX_REPAIRS,
       'maximum_model_turns_per_phase':MAX_MODEL_TURNS,'case_order':'sealed listed order, all once',
       'candidate_policy':'native generation only; one same-session real-check feedback; no manual artifact repair or reroll',
       'permissions':'isolated test client acceptEdits; Read/Edit, plus narrowly allowed unittest command for Python tasks; normal launcher unchanged',
       'scope':'Representative synthetic work tasks plus a frozen real-module enhancement; not live customer outcomes or long-session qualification. No cloud comparison; escalation recommendations are based on observed local limits, not measured cloud superiority.',
       'sealed_plan_sha256':digest((ROOT/'evidence/workhorse-v1-plan.json').read_bytes()),
       'execution_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
 dump(output/'plan.json',plan)
 state={'status':'running','started_at':stamp(),'plan':plan,'cases':[]};dump(output/'state.json',state)
 for case in CASES:
  folder=output/case['id'];workspace=folder/'workspace';workspace.mkdir(parents=True)
  for name,text in case['files'].items():
   path=workspace/name;assert path.resolve().is_relative_to(workspace.resolve())
   path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(text.encode('utf-8'))
  artifact=workspace/case['artifact'];assert artifact.is_file()
  immutable={name:digest((workspace/name).read_bytes())for name in case['files']if name!=case['artifact']}
  before=artifact.read_text(encoding='utf-8');row={'id':case['id'],'category':case['category'],'difficulty':case['difficulty'],'phases':[],'accepted':False}
  state['active_case']=case['id'];state['cases'].append(row);dump(output/'state.json',state)
  session=None;required_reads={workspace/name for name in case['files']}
  base_prompt=(case['prompt']+'\nWork in '+workspace.as_posix()+'. Read every provided file with native Read before editing. '
      'The only writable artifact is '+artifact.as_posix()+'. Use native Edit to update the existing artifact; no Write tool. '
      'Do not access parent directories, evaluator sources, reference artifacts or external services. '
      +('You may run exactly python -m unittest -q or python -m unittest -q test_public in this working directory. '\
         if case['kind']=='python'else 'Do not use Bash or execute commands. ')
      +'Complete the actual file and end with WORKHORSE_DONE. Do not claim unrun tests passed.')
  prompt=base_prompt
  config=folder/'client';config.mkdir()
  env=native.build_env(config,gateway_key());env['ANTHROPIC_API_KEY']=gateway_key()
  env['ANTHROPIC_AUTH_TOKEN']='';env.pop('ANTHROPIC_AUTH_TOKEN',None)
  env['CLAUDE_CODE_MAX_RETRIES']='0';env['API_TIMEOUT_MS']='180000'
  # Supporting API credentials are never inherited by product test clients.
  for key in list(env):
   if any(word in key.upper()for word in ('SECRET','TOKEN','KEY','PASSWORD'))and key!='ANTHROPIC_API_KEY':env.pop(key,None)
  for phase in range(MAX_REPAIRS+1):
   phase_dir=folder/f'phase-{phase}';phase_dir.mkdir()
   (phase_dir/'prompt.txt').write_text(prompt,encoding='utf-8')
   tools='Read,Edit,Bash'if case['kind']=='python'else 'Read,Edit'
   allowed='Read,Edit,Bash(python -m unittest *)'if case['kind']=='python'else 'Read,Edit'
   args=['claude.cmd','--bare','-p','--model',MODEL,'--output-format','stream-json','--verbose','--max-turns',str(MAX_MODEL_TURNS),
         '--permission-mode','acceptEdits','--tools',tools,'--allowedTools',allowed]
   if session:args+=['--resume',session]
   started=time.monotonic();code,timed_out=native.invoke_cli(args,env,prompt,workspace,phase_dir/'stdout.jsonl',phase_dir/'stderr.log',PHASE_SECONDS)
   seconds=time.monotonic()-started;events=native.parse_events(phase_dir/'stdout.jsonl')
   observed=inspect_native(events,workspace,artifact,before,required_reads if phase==0 else set())
   if session and observed['session_id']!=session:observed['scope_violations'].append('session continuity lost')
   session=observed['session_id']or session
   unchanged=all(digest((workspace/name).read_bytes())==value for name,value in immutable.items())
   try:checks=check(case['id'],workspace)
   except Exception as error:checks=[{'name':'checker execution','passed':False,'error':str(error)}]
   assert checks and all(isinstance(c.get('passed'),bool)for c in checks)
   accepted=(code==0 and not timed_out and observed['terminal_success']and observed['edit_reconstruction_matches']
             and not observed['missing_reads']and not observed['scope_violations']and unchanged and all(c['passed']for c in checks))
   snapshot=phase_dir/artifact.name;snapshot.write_bytes(artifact.read_bytes())
   result={'phase':phase,'seconds':seconds,'exit_code':code,'timed_out':timed_out,'native':observed,'immutable_sources_unchanged':unchanged,
           'checks':checks,'accepted':accepted,'artifact_sha256':digest(artifact.read_bytes()),'recorded_at':stamp()}
   dump(phase_dir/'result.json',result);row['phases'].append(result);row['accepted']=accepted;row['session_id']=session
   state['observed_at']=stamp();dump(output/'state.json',state);print(json.dumps({'case':case['id'],'phase':phase,'accepted':accepted,'seconds':round(seconds,2),'checks_failed':[c['name']for c in checks if not c['passed']]}),flush=True)
   if accepted:break
   if timed_out or code!=0 or not observed['terminal_success']or observed['scope_violations']or not unchanged:row['stopped_reason']='native/timeout/scope failure';break
   # Feedback uses the actual unchanged checker output, never a reference implementation.
   failed=[c for c in checks if not c['passed']]
   prompt='Continue the same task/session. The evaluator found these actual failures:\n'+json.dumps(failed,ensure_ascii=False)+'\n'+base_prompt
   before=artifact.read_text(encoding='utf-8')
  row['first_pass']=row['phases'][0]['accepted'];row['total_active_seconds']=sum(p['seconds']for p in row['phases'])
  dump(folder/'result.json',row)
 assert all(digest((ROOT/name).read_bytes())==value for name,value in sources.items())
 state.update(status='terminal',finished_at=stamp(),active_case=None,first_pass_count=sum(c['first_pass']for c in state['cases']),final_pass_count=sum(c['accepted']for c in state['cases']))
 dump(output/'state.json',state);print(json.dumps({'terminal':True,'first_pass':state['first_pass_count'],'final_pass':state['final_pass_count'],'cases':len(CASES)}),flush=True)
 return 0

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);options=parser.parse_args()
 raise SystemExit(run(options.output))
