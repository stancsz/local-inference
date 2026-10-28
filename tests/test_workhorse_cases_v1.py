"""Checker controls stay outside every model task workspace."""
import copy,json,subprocess,sys
from pathlib import Path
import pytest
from workhorse.cases_v1 import CASES,NEGATIVE_ARTIFACTS,check,_EXPECTED

POSITIVE_PYTHON = {'wh01': 'def merge_pages(pages):\n'
         ' out=[]; seen=set()\n'
         ' for page in pages:\n'
         '  for row in page:\n'
         "   if row['id'] not in seen: seen.add(row['id']); out.append(row)\n"
         ' return out\n',
 'wh02': 'import json,re\n'
         'def summarize(lines):\n'
         ' n=bad=0; levels={}; msgs=[]\n'
         ' for line in lines:\n'
         '  if not line.strip(): continue\n'
         '  try: x=json.loads(line)\n'
         '  except ValueError: bad+=1; continue\n'
         '  \n'
         "  if not isinstance(x,dict) or not isinstance(x.get('message'),str): bad+=1; continue\n"
         "  n+=1; level=x.get('level','unknown'); levels[level]=levels.get(level,0)+1; "
         "msg=x.get('message',''); msg=re.sub(r'\\b[\\w.+-]+@[\\w.-]+\\.[A-Za-z]{2,}\\b','[REDACTED]',msg); "
         "msg=re.sub(r'\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b','[REDACTED]',msg); msgs.append(msg)\n"
         " return {'valid':n,'malformed':bad,'by_level':levels,'messages':msgs}\n",
 'wh03': 'from datetime import datetime,timezone\n'
         'def normalize_timestamp(value):\n'
         ' try:\n'
         '  if not isinstance(value,str): return None\n'
         "  if value.endswith('Z'): value=value[:-1]+'+00:00'\n"
         '  d=datetime.fromisoformat(value)\n'
         '  if d.tzinfo is None: return None\n'
         "  return d.astimezone(timezone.utc).replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')\n"
         ' except (ValueError,TypeError): return None\n',
 'wh04': 'def parse_bool(value,default=False):\n'
         ' if type(value) is bool: return value\n'
         ' if isinstance(value,str):\n'
         '  s=value.strip().lower()\n'
         "  if s in ('true','yes','1','on'): return True\n"
         "  if s in ('false','no','0','off'): return False\n"
         ' return default\n',
 'wh05': 'def join_rows(left,right):\n'
         ' index={}\n'
         ' for r in right:\n'
         '  try:\n'
         "   if r['sku'] is not None: index[r['sku']]=r\n"
         '  except (KeyError,TypeError): pass\n'
         ' out=[]\n'
         ' for l in left:\n'
         '  row=dict(l)\n'
         "  try: match=index.get(l['sku']) if l['sku'] is not None else None\n"
         '  except (KeyError,TypeError): match=None\n'
         '  if match:\n'
         '   for k,v in match.items():\n'
         '    if k not in row: row[k]=v\n'
         '  out.append(row)\n'
         ' return out\n',
 'wh06': 'def classify_response(status,body):\n'
         " if type(status)is not int:return {'retry':False,'reason':'permanent'}\n"
         " if status==429:return {'retry':True,'reason':'rate_limited'}\n"
         " if 500<=status<=599:return {'retry':True,'reason':'server_error'}\n"
         " return {'retry':False,'reason':'permanent'}\n",
 'wh13': '"""Compare measured cloud/local token shares; never infer a cloud-only baseline."""\n'
         'import argparse\n'
         'import hashlib\n'
         'import json\n'
         'from pathlib import Path\n'
         '\n'
         '\n'
         'def tokens(path):\n'
         "    text=path.read_text(encoding='utf-8-sig')\n"
         '    try:\n'
         '        document=json.loads(text)\n'
         '    except json.JSONDecodeError:\n'
         '        rows=[json.loads(line) for line in text.splitlines() if line.strip()]\n'
         "        results=[row for row in rows if row.get('type')=='result']\n"
         '        if len(results)!=1:\n'
         "            raise ValueError(f'{path}: require exactly one terminal CLI result')\n"
         '        document=results[0]\n'
         '    if not isinstance(document,dict):\n'
         "        raise ValueError(f'{path}: invalid receipt')\n"
         "    usage=document.get('usage')\n"
         '    if not isinstance(usage,dict):\n'
         "        raise ValueError(f'{path}: missing provider usage')\n"
         "    if 'prompt_tokens' in usage:\n"
         "        fields=('prompt_tokens','completion_tokens')  # Cached tokens already included.\n"
         '    else:\n'
         "        fields=('input_tokens','output_tokens')\n"
         "        fields+=tuple(k for k in ('cache_read_input_tokens','cache_creation_input_tokens') if k in "
         'usage)\n'
         '    values=[usage.get(k) for k in fields]\n'
         '    if any(type(value) is not int or value<0 for value in values):\n'
         "        raise ValueError(f'{path}: incomplete or invalid token usage')\n"
         '    return sum(values)\n'
         '\n'
         '\n'
         'def main():\n'
         '    parser=argparse.ArgumentParser(description=__doc__)\n'
         "    parser.add_argument('--local',type=Path,nargs='+',required=True)\n"
         "    parser.add_argument('--advisor',type=Path,nargs='+',required=True)\n"
         "    parser.add_argument('--baseline-cloud-tokens',type=int)\n"
         '    args=parser.parse_args()\n'
         '    all_paths=args.local+args.advisor\n'
         '    if len({p.resolve() for p in all_paths})!=len(all_paths):\n'
         "        parser.error('Do not count a receipt twice')\n"
         '    if args.baseline_cloud_tokens is not None and args.baseline_cloud_tokens<=0:\n'
         "        parser.error('Baseline must be a positive measured token total for equivalent work')\n"
         '    local=sum(tokens(path) for path in args.local)\n'
         '    cloud=sum(tokens(path) for path in args.advisor)\n'
         '    if not local+cloud:\n'
         "        parser.error('Receipts contain no tokens')\n"
         '    ratio=cloud/(local+cloud)\n'
         '    '
         "report={'local_tokens':local,'cloud_advisor_tokens':cloud,'cloud_token_share_percent':ratio*100,\n"
         "        'cloud_share_at_most_one_percent':ratio<=0.01,\n"
         "        'cloud_token_reduction_percent':None,\n"
         "        'scope':'Supplied provider usage only, including failed attempts when supplied. Cloud "
         'share is not savings against an equivalent cloud-only run. Include every retry/failed receipt; '
         'missing usage prevents a complete accounting claim. Electricity, hardware and price differences '
         "are excluded.'}\n"
         "    report['receipts']=[{'role':role,'path':str(path),'tokens':tokens(path),\n"
         "        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}\n"
         "        for role,paths in [('local',args.local),('advisor',args.advisor)] for path in paths]\n"
         '    if args.baseline_cloud_tokens:\n'
         "        report['measured_baseline_cloud_tokens']=args.baseline_cloud_tokens\n"
         "        report['cloud_token_reduction_percent']=100*(1-cloud/args.baseline_cloud_tokens)\n"
         '    print(json.dumps(report,indent=2))\n'
         '\n'
         '\n'
         '\n'
         'def tokens(path):\n'
         " text=path.read_text(encoding='utf-8-sig')\n"
         ' try:document=json.loads(text)\n'
         ' except json.JSONDecodeError:\n'
         '  rows=[json.loads(line)for line in text.splitlines()if line.strip()]\n'
         "  terminal=[r for r in rows if isinstance(r,dict)and r.get('type')in "
         "('result','response.completed')]\n"
         "  if len(terminal)!=1:raise ValueError('exactly one terminal required')\n"
         '  document=terminal[0]\n'
         ' if isinstance(document,dict)and '
         "document.get('type')=='response.completed':document=document.get('response')\n"
         " if not isinstance(document,dict)or not isinstance(document.get('usage'),dict):raise "
         "ValueError('usage required')\n"
         " usage=document['usage']\n"
         " fields=['prompt_tokens','completion_tokens']if 'prompt_tokens'in usage else "
         "['input_tokens','output_tokens']+[k for k in "
         "('cache_read_input_tokens','cache_creation_input_tokens')if k in usage]\n"
         ' values=[usage.get(k)for k in fields]\n'
         " if any(type(v)is not int or v<0 for v in values):raise ValueError('invalid usage')\n"
         ' return sum(values)\n'
         '\n'
         "if __name__=='__main__':\n"
         '    main()\n'}

def prepare(case,root,candidate=None):
 for name,text in case['files'].items():
  path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(text.encode('utf-8'))
 if candidate is not None:(root/case['artifact']).write_bytes(candidate.encode('utf-8'))

def test_schema_and_coverage():
 assert len(CASES)==13 and len({c['id']for c in CASES})==13
 assert {c['id']for c in CASES}==set(NEGATIVE_ARTIFACTS)
 assert sum(c['kind']=='python'for c in CASES)==7
 for case in CASES:
  assert set(case)=={'id','category','difficulty','files','prompt','artifact','kind'}
  assert 'CONTRACT.md'in case['files'] and case['artifact']in case['files']
  for name in case['files']:assert not Path(name).is_absolute()and '..'not in Path(name).parts

@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_positive_control_and_source_immutability(case,tmp_path):
 value=POSITIVE_PYTHON[case['id']]if case['kind']=='python'else json.dumps(_EXPECTED[case['id']])
 prepare(case,tmp_path,value)
 before={p.relative_to(tmp_path):p.read_bytes()for p in tmp_path.rglob('*')if p.is_file()}
 rows=check(case['id'],tmp_path);assert rows and all(r['passed']for r in rows),rows
 assert {p.relative_to(tmp_path):p.read_bytes()for p in tmp_path.rglob('*')if p.is_file()}==before

@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_plausible_wrong_candidate_is_rejected(case,tmp_path):
 prepare(case,tmp_path,NEGATIVE_ARTIFACTS[case['id']])
 rows=check(case['id'],tmp_path);assert rows and not all(r['passed']for r in rows),rows

@pytest.mark.parametrize('case',[c for c in CASES if c['kind']=='python'],ids=lambda c:c['id'])
def test_public_tests_actually_run_and_fail_baseline(case,tmp_path):
 prepare(case,tmp_path)
 run=subprocess.run([sys.executable,'-B','-m','unittest','-q'],cwd=tmp_path,capture_output=True,text=True,timeout=15)
 assert run.returncode!=0 and 'Ran'in run.stderr and 'Ran 0 tests'not in run.stderr,(run.stdout,run.stderr)

@pytest.mark.parametrize('case',[c for c in CASES if c['kind']=='json'],ids=lambda c:c['id'])
def test_malformed_json_is_rejected(case,tmp_path):
 prepare(case,tmp_path,'not json')
 assert not all(r['passed']for r in check(case['id'],tmp_path))

def test_bool_is_not_an_integer_fact(tmp_path):
 case=next(c for c in CASES if c['id']=='wh12');value=copy.deepcopy(_EXPECTED['wh12']);value['discrepancy']=True
 prepare(case,tmp_path,json.dumps(value));assert not all(r['passed']for r in check('wh12',tmp_path))

def test_action_order_has_no_meaning(tmp_path):
 case=next(c for c in CASES if c['id']=='wh09');value=copy.deepcopy(_EXPECTED['wh09']);value['next_actions'].reverse()
 prepare(case,tmp_path,json.dumps(value));assert all(r['passed']for r in check('wh09',tmp_path))
