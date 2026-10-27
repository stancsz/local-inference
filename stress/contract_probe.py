"""Additional final-artifact probes; never rewrite frozen matrix outcomes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PREFIX = '''import json, sys, math
from decimal import Decimal
sys.path.insert(0, sys.argv[1])
import task
results=[]
def equal(actual, expected):
    assert actual == expected, repr(actual) + ' != ' + repr(expected)
def raises(fn, *types):
    try: fn()
    except types: return
    raise AssertionError('expected ' + '/'.join(t.__name__ for t in types))
def check(name, fn):
    try:
        fn()
        results.append({'name':name, 'passed':True})
    except Exception as error:
        results.append({'name':name, 'passed':False, 'error':type(error).__name__+': '+str(error)})
'''
PROBES = {
    'engineering': '''
for name in ('clamp_all', 'clamp_report'):
    fn=getattr(task,name)
    check(name+' empty invalid lower', lambda fn=fn: raises(lambda:fn([],float('nan'),4),ValueError))
    check(name+' empty reversed bounds', lambda fn=fn: raises(lambda:fn([],5,2),ValueError))
    check(name+' empty bool bound', lambda fn=fn: raises(lambda:fn([],False,4),TypeError))
check('single-use generator',lambda:equal(task.clamp_all((x for x in [-7,3,105])),[0,3,100]))
check('generator report',lambda:equal(task.clamp_report((x for x in [-7,3,105])),{'count':3,'min':0,'max':100,'sum':103}))
check('finite value validation',lambda:raises(lambda:task.clamp(float('nan')),ValueError))
''',
    'migration': '''
for invalid in (None, True, 1.5, '1000'):
    check('invalid milliseconds '+repr(invalid),lambda invalid=invalid:raises(lambda:task.normalize_settings({'timeout_ms':invalid}),TypeError,ValueError))
check('negative milliseconds',lambda:raises(lambda:task.normalize_settings({'timeout_ms':-1}),ValueError))
check('negative seconds',lambda:raises(lambda:task.normalize_settings({'timeout_seconds':-1}),ValueError))
for invalid in (None, 17, True):
    check('non-string name '+repr(invalid),lambda invalid=invalid:raises(lambda:task.normalize_settings({'name':invalid}),TypeError,ValueError))
check('conflicting time units',lambda:raises(lambda:task.normalize_settings({'timeout_ms':1000,'timeout_seconds':1}),ValueError))
check('unknown key',lambda:raises(lambda:task.normalize_settings({'surprise':1}),ValueError))
check('boolean retries',lambda:raises(lambda:task.normalize_settings({'retries':False}),TypeError,ValueError))
def copies():
    original={'name':' X ','timeout_ms':3721,'retries':2}
    output=task.normalize_settings(original)
    equal(original,{'name':' X ','timeout_ms':3721,'retries':2})
    equal(output,{'name':'X','timeout_seconds':3.721,'retries':2})
    equal(task.normalize_settings(output),output)
    batch=task.migrate_many(x for x in [original,original])
    equal(batch,[output,output])
    assert batch[0] is not batch[1]
    batch[0]['name']='changed'
    equal(batch[1]['name'],'X')
check('nonmutation idempotency generator and independent copies',copies)
''',
    'expenses': '''
check('aggregate before HALF_EVEN rounding',lambda:equal(task.expense_totals('category,amount\\nx,1.005\\nx,0.005\\n'),{'x':Decimal('1.01')}))
check('strip group preserve first spelling',lambda:equal(task.expense_totals('category,amount\\n FOOD ,2.125\\nfood,-0.005\\n'),{'FOOD':Decimal('2.12')}))
for invalid in ('NaN','Infinity','garbage'):
    check('invalid amount '+invalid,lambda invalid=invalid:raises(lambda:task.expense_totals('category,amount\\nx,'+invalid+'\\n'),ValueError))
check('mixed currency',lambda:raises(lambda:task.expense_totals('category,amount,currency\\nx,1,USD\\ny,2,CAD\\n'),ValueError))
check('missing header',lambda:raises(lambda:task.expense_totals('amount\\n1\\n'),ValueError))
check('duplicate header',lambda:raises(lambda:task.expense_totals('category,amount,amount\\nx,1,2\\n'),ValueError))
def report():
    result=task.expense_report('category,amount\\nz,1.005\\n\\na,2.00\\nz,0.005\\n')
    equal(list(result['totals']),['z','a'])
    equal(result['count'],3)
    equal(result['grand_total'],Decimal('3.01'))
check('report blank rows order and exact total',report)
''',
}


def main():
    rows=[]
    for path in sorted((ROOT/'tmp/stress/sessions').glob('*/result.json')):
        record=json.loads(path.read_text())
        if not record.get('accepted'):continue
        workspace=path.parent/'workspace'
        source=workspace/'task.py'
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        script=PREFIX+PROBES[record['task']]+"\nprint(json.dumps(results))\n"
        tested=subprocess.run([sys.executable,'-I','-c',script,str(workspace)],capture_output=True,text=True,timeout=20)
        assert before==hashlib.sha256(source.read_bytes()).hexdigest(), 'Probe changed task source'
        checks=json.loads(tested.stdout) if tested.returncode==0 else [{'name':'probe execution','passed':False,'error':tested.stderr}]
        rows.append({'receipt':path.relative_to(ROOT).as_posix(),'client':record['client'],'task':record['task'],
            'original_workflow_accepted':True,'task_sha256':before,'all_additional_checks_passed':all(c['passed'] for c in checks),'checks':checks})
    output={'probe_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope':'Additional selected completed-artifact contract probes, independent of CLI-visible public fixtures and applied uniformly to all completed artifacts. These are posthoc coverage checks, not a general accuracy estimate. Original frozen workflow receipts are unchanged; a workflow PASS alone does not certify all task edge cases.',
        'sessions':rows,'sessions_with_additional_failures':sum(not r['all_additional_checks_passed'] for r in rows)}
    (ROOT/'evidence/stress-contract-probes.json').write_text(json.dumps(output,indent=2))
    print(json.dumps({'probed_sessions':len(rows),'sessions_with_additional_failures':output['sessions_with_additional_failures']}))


if __name__=='__main__':main()
