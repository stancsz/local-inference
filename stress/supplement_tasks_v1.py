"""Prospective non-expense workloads; original campaign definitions stay frozen."""
import json
import random
from textwrap import indent

TASKS = ('incident_log', 'release_manifest')

REQUIREMENTS = {
    'incident_log': [
        "Implement audit_events(jsonl_text): ignore blank lines; return {'count':int,'ok':int,'errors':int,'total_duration_ms':number,'services':dict}. Each JSON object has service,status,duration_ms. Count statuses 'ok' and 'error'.",
        "Strip service whitespace, preserve case and first-seen service order; group matching stripped service names.",
        "Invalid JSON, non-object rows, missing required fields and non-string text raise ValueError. Extra metadata is allowed.",
        "service must be a nonempty stripped string; status exactly 'ok' or 'error'; duration_ms finite nonnegative int/float excluding bool. All invalid fields raise ValueError.",
        "services maps each name to exactly {'count':int,'errors':int,'duration_ms':number}; preserve inputs and aggregate before reporting.",
        "Empty/blank logs return zero counts and empty services; accept zero durations and Unicode services; be deterministic.",
        "Implement audit_file(path): read UTF8 JSONL and return audit_events output without modifying the file.",
        "Implement render_markdown(report): deterministic string beginning '# Incident summary\\n'; include lines 'Count: <count>', 'OK: <ok>', 'Errors: <errors>' and service names.",
        "Keep all earlier behavior for new seeded batches and repeated rendering; do not hardcode fixture values.",
    ],
    'release_manifest': [
        "Implement audit_manifest(records) accepting iterable of dictionaries and returning {'files':int,'bytes':int,'components':dict,'paths':sortedlist}. Required fields path,size_bytes,sha256; optional component defaults 'app'.",
        "Paths are sorted; component strings are stripped and grouped case-sensitively in first-seen order; components map to exactly {'files':int,'bytes':int}.",
        "path must be nonempty relative POSIX text: reject absolute paths, backslashes, empty segments, '.' and '..' segments, and duplicate paths with ValueError.",
        "size_bytes nonnegative int excluding bool; sha256 exactly64 hexadecimal characters (case-insensitive); component nonempty string. Missing/unknown keys, invalid records or fields raise ValueError.",
        "Support generators and independent output dictionaries; never mutate records. Empty manifest has zero counts and empty components/paths.",
        "Implement compare_manifests(old,new)->{'added':sortedpaths,'removed':sortedpaths,'changed':sortedpaths}; changed means size, lowercase SHA or stripped/default component differs. Validate both sides; no input mutation.",
        "Implement audit_file(path): read UTF8 JSON array and return audit_manifest result without changing the file; invalid JSON/root raises ValueError.",
        "Implement render_markdown(report): deterministic string beginning '# Release manifest\\n', with lines 'Files: <files>', 'Bytes: <bytes>' and component names.",
        "Preserve all earlier behavior across new seeded paths, hashes and component changes; no hardcoded fixture values.",
    ],
}


def initial_source(task):
    if task not in TASKS:
        raise ValueError('unknown supplement task')
    name = 'audit_events' if task == 'incident_log' else 'audit_manifest'
    return f'def {name}(value):\n    return {{}}\n'


def _incident(n, seed):
    rng = random.Random(seed)
    events = [{'service': rng.choice([' api ', 'worker', '分析']), 'status': rng.choice(['ok', 'error']), 'duration_ms': rng.randint(0, 700) / 2} for _ in range(17)]
    services = {}
    for row in events:
        service = services.setdefault(row['service'].strip(), {'count': 0, 'errors': 0, 'duration_ms': 0})
        service['count'] += 1
        service['errors'] += row['status'] == 'error'
        service['duration_ms'] += row['duration_ms']
    expected = {'count': len(events), 'ok': sum(r['status'] == 'ok' for r in events), 'errors': sum(r['status'] == 'error' for r in events), 'total_duration_ms': sum(r['duration_ms'] for r in events), 'services': services}
    basic = json.dumps({'service': 'api', 'status': 'ok', 'duration_ms': seed % 71 + 1})
    code = f"data={basic!r}\nr=task.audit_events(data)\nself.assertEqual((r['count'],r['ok'],r['errors'],r['total_duration_ms']),(1,1,0,{seed % 71 + 1}))\n"
    if n >= 1:
        code += "data='\\n'.join([json.dumps({'service':' api ','status':'ok','duration_ms':2}),json.dumps({'service':'api','status':'error','duration_ms':3})])\nr=task.audit_events(data)\nself.assertEqual(list(r['services']),['api'])\n"
    if n >= 2:
        code += "for bad in ('not-json','[]','null','{}',None,True,123,{},[]):\n    with self.assertRaises(ValueError): task.audit_events(bad)\nself.assertEqual(task.audit_events('\\n'+data+'\\n\\n')['count'],2)\n"
    if n >= 3:
        code += "for key,values in [('duration_ms',[None,True,False,-1,-0.5,float('nan'),float('inf'),'2']),('service',[None,True,'  ']),('status',[None,'fail',True])]:\n    for value in values:\n        record={'service':'api','status':'ok','duration_ms':1};record[key]=value\n        with self.assertRaises(ValueError): task.audit_events(json.dumps(record))\n"
    if n >= 4:
        code += "self.assertEqual(r['services']['api'],{'count':2,'errors':1,'duration_ms':5})\nself.assertEqual(task.audit_events(json.dumps({'service':'x','status':'ok','duration_ms':0,'metadata':123}))['count'],1)\n"
    if n >= 5:
        code += "self.assertEqual(task.audit_events('  \\n'),{'count':0,'ok':0,'errors':0,'total_duration_ms':0,'services':{}})\nself.assertEqual(task.audit_events(json.dumps({'service':'分析','status':'ok','duration_ms':0}))['total_duration_ms'],0)\n"
    payload = '\n'.join(json.dumps(r, ensure_ascii=False) for r in events)
    if n >= 6:
        code += f"with tempfile.TemporaryDirectory() as folder:\n    path=Path(folder)/'events.jsonl';path.write_text({payload!r},encoding='utf-8')\n    before=path.read_bytes()\n    self.assertEqual(task.audit_file(path),{expected!r})\n    self.assertEqual(path.read_bytes(),before)\n"
    if n >= 7:
        code += f"report=task.audit_events({payload!r})\nrendered=task.render_markdown(report)\nself.assertIsInstance(rendered,str)\nself.assertTrue(rendered.startswith('# Incident summary\\n'))\nfor label,value in [('Count',report['count']),('OK',report['ok']),('Errors',report['errors'])]:\n    self.assertIn(f'{{label}}: {{value}}',rendered)\nfor service in report['services']: self.assertIn(service,rendered)\nself.assertEqual(task.render_markdown(report),rendered)\n"
    if n >= 8:
        code += f"self.assertEqual(task.audit_events({payload!r}),{expected!r})\nself.assertEqual(list(task.audit_events({payload!r})['services']),{list(services)!r})\n"
    return code


def _manifest(n, seed):
    rng = random.Random(seed)
    rows = [{'path': f'bin/{seed % 100000}-{i}.dat', 'size_bytes': rng.randrange(0, 30000), 'sha256': f'{rng.getrandbits(256):064x}', 'component': rng.choice([' app ', 'docs', '工具'])} for i in range(11)]
    components = {}
    for row in rows:
        group = components.setdefault(row['component'].strip(), {'files': 0, 'bytes': 0})
        group['files'] += 1
        group['bytes'] += row['size_bytes']
    expected = {'files': len(rows), 'bytes': sum(r['size_bytes'] for r in rows), 'components': components, 'paths': sorted(r['path'] for r in rows)}
    size_a, size_b = seed % 71 + 1, seed % 89 + 2
    code = f"sample=[{{'path':'b','size_bytes':{size_a},'sha256':'a'*64}},{{'path':'a','size_bytes':{size_b},'sha256':'B'*64}}]\nr=task.audit_manifest(sample)\nself.assertEqual((r['files'],r['bytes']),(2,{size_a+size_b}))\n"
    if n >= 1:
        code += f"self.assertEqual(r['paths'],['a','b'])\nself.assertEqual(r['components'],{{'app':{{'files':2,'bytes':{size_a+size_b}}}}})\n"
    if n >= 2:
        code += "for path in ('','/x','a\\\\b','a//b','./a','a/../b',None):\n    row=dict(sample[0],path=path)\n    with self.assertRaises(ValueError): task.audit_manifest([row])\nwith self.assertRaises(ValueError): task.audit_manifest([sample[0],sample[0]])\n"
    if n >= 3:
        code += "for key,values in [('size_bytes',[-1,True,False,None,1.5]),('sha256',[None,'z'*64,'a'*63]),('component',[None,True,'  '])]:\n    for value in values:\n        row=dict(sample[0]);row[key]=value\n        with self.assertRaises(ValueError): task.audit_manifest([row])\nfor row in ({},dict(sample[0],surprise=1),'not-object'):\n    with self.assertRaises(ValueError): task.audit_manifest([row])\n"
    if n >= 4:
        code += f"rows={rows!r}\nbefore=json.dumps(rows,sort_keys=True)\nreport=task.audit_manifest(row for row in rows)\nself.assertEqual(report,{expected!r})\nself.assertEqual(json.dumps(rows,sort_keys=True),before)\nself.assertEqual(task.audit_manifest([]),{{'files':0,'bytes':0,'components':{{}},'paths':[]}})\n"
    if n >= 5:
        code += "old=[dict(sample[0]),dict(sample[1])]\nnew=[dict(sample[0],size_bytes=sample[0]['size_bytes']+1),{'path':'c','size_bytes':0,'sha256':'c'*64}]\nself.assertEqual(task.compare_manifests(old,new),{'added':['c'],'removed':['a'],'changed':['b']})\nself.assertEqual(task.compare_manifests(sample,sample),{'added':[],'removed':[],'changed':[]})\nself.assertEqual(task.compare_manifests([sample[0]],[dict(sample[0],sha256='A'*64,component=' app ')]),{'added':[],'removed':[],'changed':[]})\nwith self.assertRaises(ValueError): task.compare_manifests([{}],[])\nwith self.assertRaises(ValueError): task.compare_manifests([],[{}])\n"
    if n >= 6:
        code += f"with tempfile.TemporaryDirectory() as folder:\n    path=Path(folder)/'release.json';path.write_text(json.dumps({rows!r},ensure_ascii=False),encoding='utf-8')\n    before=path.read_bytes()\n    self.assertEqual(task.audit_file(path),{expected!r})\n    self.assertEqual(path.read_bytes(),before)\n    for bad in ('not-json','{{}}','null'):\n        path.write_text(bad,encoding='utf-8')\n        with self.assertRaises(ValueError): task.audit_file(path)\n"
    if n >= 7:
        code += f"report=task.audit_manifest({rows!r})\nrendered=task.render_markdown(report)\nself.assertTrue(rendered.startswith('# Release manifest\\n'))\nself.assertIn(f\"Files: {{report['files']}}\",rendered)\nself.assertIn(f\"Bytes: {{report['bytes']}}\",rendered)\nfor component in report['components']: self.assertIn(component,rendered)\nself.assertEqual(task.render_markdown(report),rendered)\n"
    if n >= 8:
        code += f"self.assertEqual(task.audit_manifest({rows!r}),{expected!r})\nself.assertEqual(list(task.audit_manifest({rows!r})['components']),{list(components)!r})\nnew=[dict(row) for row in {rows!r}]\nnew[0]['sha256']='f'*64\nself.assertEqual(task.compare_manifests({rows!r},new)['changed'],[new[0]['path']])\n"
    return code


def stage(task, number, seed):
    if task not in TASKS or type(number) is not int or number < 0 or type(seed) is not int:
        raise ValueError('invalid supplement task, stage or seed')
    n = min(number, 8)
    body = "import task,json,tempfile\nfrom pathlib import Path\n" + (_incident(n, seed) if task == 'incident_log' else _manifest(n, seed))
    tests = 'import unittest\n\nclass Acceptance(unittest.TestCase):\n    def test_behavior(self):\n' + indent(body, '        ')
    tests += "    def test_evidence(self):\n        import json\n        from pathlib import Path\n        value=json.loads(Path('evidence.json').read_text())['acceptance_delay_seconds']\n        self.assertIs(type(value),int)\n\nif __name__=='__main__':\n    unittest.main()\n"
    return {'requirement': ' '.join(REQUIREMENTS[task][:n+1]) + ' Read and repair the current implementation, then execute tests. Use only workspace task.py, test_task.py and evidence.json; do not inspect the parent project or solution/reference files.', 'tests': tests}
