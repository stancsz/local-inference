import unittest

from contextlib import contextmanager
from pathlib import Path
import shutil
import uuid

@contextmanager
def _workspace_fixture():
    root=Path.cwd().resolve()
    directory=root/('.sift-fixture-'+uuid.uuid4().hex)
    directory.mkdir(mode=0o755)
    try:
        yield str(directory)
    finally:
        resolved=directory.resolve()
        assert resolved==directory and resolved.parent==root and not directory.is_symlink()
        shutil.rmtree(directory)


class Acceptance(unittest.TestCase):
    def test_behavior(self):
        import task,json,tempfile
        from pathlib import Path
        data='{"service": "api", "status": "ok", "duration_ms": 9}'
        r=task.audit_events(data)
        self.assertEqual((r['count'],r['ok'],r['errors'],r['total_duration_ms']),(1,1,0,9))
        data='\n'.join([json.dumps({'service':' api ','status':'ok','duration_ms':2}),json.dumps({'service':'api','status':'error','duration_ms':3})])
        r=task.audit_events(data)
        self.assertEqual(list(r['services']),['api'])
        for bad in ('not-json','[]','null','{}',None,True,123,{},[]):
            with self.assertRaises(ValueError): task.audit_events(bad)
        self.assertEqual(task.audit_events('\n'+data+'\n\n')['count'],2)
        for key,values in [('duration_ms',[None,True,False,-1,-0.5,float('nan'),float('inf'),'2']),('service',[None,True,'  ']),('status',[None,'fail',True])]:
            for value in values:
                record={'service':'api','status':'ok','duration_ms':1};record[key]=value
                with self.assertRaises(ValueError): task.audit_events(json.dumps(record))
        self.assertEqual(r['services']['api'],{'count':2,'errors':1,'duration_ms':5})
        self.assertEqual(task.audit_events(json.dumps({'service':'x','status':'ok','duration_ms':0,'metadata':123}))['count'],1)
        self.assertEqual(task.audit_events('  \n'),{'count':0,'ok':0,'errors':0,'total_duration_ms':0,'services':{}})
        self.assertEqual(task.audit_events(json.dumps({'service':'分析','status':'ok','duration_ms':0}))['total_duration_ms'],0)
        with _workspace_fixture() as folder:
            path=Path(folder)/'events.jsonl';path.write_text('{"service": "分析", "status": "error", "duration_ms": 171.5}\n{"service": "分析", "status": "error", "duration_ms": 67.0}\n{"service": "分析", "status": "error", "duration_ms": 216.5}\n{"service": " api ", "status": "ok", "duration_ms": 66.0}\n{"service": "worker", "status": "error", "duration_ms": 338.5}\n{"service": "分析", "status": "error", "duration_ms": 129.0}\n{"service": "分析", "status": "ok", "duration_ms": 239.0}\n{"service": "worker", "status": "ok", "duration_ms": 62.0}\n{"service": " api ", "status": "error", "duration_ms": 238.5}\n{"service": "worker", "status": "error", "duration_ms": 120.0}\n{"service": "分析", "status": "ok", "duration_ms": 209.0}\n{"service": " api ", "status": "error", "duration_ms": 145.5}\n{"service": "分析", "status": "error", "duration_ms": 249.0}\n{"service": "worker", "status": "ok", "duration_ms": 232.0}\n{"service": "分析", "status": "ok", "duration_ms": 118.5}\n{"service": "分析", "status": "error", "duration_ms": 96.5}\n{"service": "分析", "status": "ok", "duration_ms": 277.0}',encoding='utf-8')
            before=path.read_bytes()
            self.assertEqual(task.audit_file(path),{'count': 17, 'ok': 7, 'errors': 10, 'total_duration_ms': 2975.5, 'services': {'分析': {'count': 10, 'errors': 6, 'duration_ms': 1773.0}, 'api': {'count': 3, 'errors': 2, 'duration_ms': 450.0}, 'worker': {'count': 4, 'errors': 2, 'duration_ms': 752.5}}})
            self.assertEqual(path.read_bytes(),before)
        report=task.audit_events('{"service": "分析", "status": "error", "duration_ms": 171.5}\n{"service": "分析", "status": "error", "duration_ms": 67.0}\n{"service": "分析", "status": "error", "duration_ms": 216.5}\n{"service": " api ", "status": "ok", "duration_ms": 66.0}\n{"service": "worker", "status": "error", "duration_ms": 338.5}\n{"service": "分析", "status": "error", "duration_ms": 129.0}\n{"service": "分析", "status": "ok", "duration_ms": 239.0}\n{"service": "worker", "status": "ok", "duration_ms": 62.0}\n{"service": " api ", "status": "error", "duration_ms": 238.5}\n{"service": "worker", "status": "error", "duration_ms": 120.0}\n{"service": "分析", "status": "ok", "duration_ms": 209.0}\n{"service": " api ", "status": "error", "duration_ms": 145.5}\n{"service": "分析", "status": "error", "duration_ms": 249.0}\n{"service": "worker", "status": "ok", "duration_ms": 232.0}\n{"service": "分析", "status": "ok", "duration_ms": 118.5}\n{"service": "分析", "status": "error", "duration_ms": 96.5}\n{"service": "分析", "status": "ok", "duration_ms": 277.0}')
        rendered=task.render_markdown(report)
        self.assertIsInstance(rendered,str)
        self.assertTrue(rendered.startswith('# Incident summary\n'))
        for label,value in [('Count',report['count']),('OK',report['ok']),('Errors',report['errors'])]:
            self.assertIn(f'{label}: {value}',rendered)
        for service in report['services']: self.assertIn(service,rendered)
        self.assertEqual(task.render_markdown(report),rendered)
        self.assertEqual(task.audit_events('{"service": "分析", "status": "error", "duration_ms": 171.5}\n{"service": "分析", "status": "error", "duration_ms": 67.0}\n{"service": "分析", "status": "error", "duration_ms": 216.5}\n{"service": " api ", "status": "ok", "duration_ms": 66.0}\n{"service": "worker", "status": "error", "duration_ms": 338.5}\n{"service": "分析", "status": "error", "duration_ms": 129.0}\n{"service": "分析", "status": "ok", "duration_ms": 239.0}\n{"service": "worker", "status": "ok", "duration_ms": 62.0}\n{"service": " api ", "status": "error", "duration_ms": 238.5}\n{"service": "worker", "status": "error", "duration_ms": 120.0}\n{"service": "分析", "status": "ok", "duration_ms": 209.0}\n{"service": " api ", "status": "error", "duration_ms": 145.5}\n{"service": "分析", "status": "error", "duration_ms": 249.0}\n{"service": "worker", "status": "ok", "duration_ms": 232.0}\n{"service": "分析", "status": "ok", "duration_ms": 118.5}\n{"service": "分析", "status": "error", "duration_ms": 96.5}\n{"service": "分析", "status": "ok", "duration_ms": 277.0}'),{'count': 17, 'ok': 7, 'errors': 10, 'total_duration_ms': 2975.5, 'services': {'分析': {'count': 10, 'errors': 6, 'duration_ms': 1773.0}, 'api': {'count': 3, 'errors': 2, 'duration_ms': 450.0}, 'worker': {'count': 4, 'errors': 2, 'duration_ms': 752.5}}})
        self.assertEqual(list(task.audit_events('{"service": "分析", "status": "error", "duration_ms": 171.5}\n{"service": "分析", "status": "error", "duration_ms": 67.0}\n{"service": "分析", "status": "error", "duration_ms": 216.5}\n{"service": " api ", "status": "ok", "duration_ms": 66.0}\n{"service": "worker", "status": "error", "duration_ms": 338.5}\n{"service": "分析", "status": "error", "duration_ms": 129.0}\n{"service": "分析", "status": "ok", "duration_ms": 239.0}\n{"service": "worker", "status": "ok", "duration_ms": 62.0}\n{"service": " api ", "status": "error", "duration_ms": 238.5}\n{"service": "worker", "status": "error", "duration_ms": 120.0}\n{"service": "分析", "status": "ok", "duration_ms": 209.0}\n{"service": " api ", "status": "error", "duration_ms": 145.5}\n{"service": "分析", "status": "error", "duration_ms": 249.0}\n{"service": "worker", "status": "ok", "duration_ms": 232.0}\n{"service": "分析", "status": "ok", "duration_ms": 118.5}\n{"service": "分析", "status": "error", "duration_ms": 96.5}\n{"service": "分析", "status": "ok", "duration_ms": 277.0}')['services']),['分析', 'api', 'worker'])
    def test_evidence(self):
        import json
        from pathlib import Path
        value=json.loads(Path('evidence.json').read_text())['acceptance_delay_seconds']
        self.assertIs(type(value),int)

if __name__=='__main__':
    unittest.main()
