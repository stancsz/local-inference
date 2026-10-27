import unittest

class Acceptance(unittest.TestCase):
    def test_behavior(self):
        import task,json,tempfile
        from pathlib import Path
        data='{"service": "api", "status": "ok", "duration_ms": 63}'
        r=task.audit_events(data)
        self.assertEqual((r['count'],r['ok'],r['errors'],r['total_duration_ms']),(1,1,0,63))
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
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'events.jsonl';path.write_text('{"service": "worker", "status": "error", "duration_ms": 304.0}\n{"service": " api ", "status": "ok", "duration_ms": 320.5}\n{"service": "分析", "status": "ok", "duration_ms": 207.0}\n{"service": " api ", "status": "error", "duration_ms": 270.0}\n{"service": "worker", "status": "error", "duration_ms": 24.5}\n{"service": "worker", "status": "error", "duration_ms": 319.0}\n{"service": " api ", "status": "error", "duration_ms": 134.5}\n{"service": " api ", "status": "error", "duration_ms": 117.5}\n{"service": "worker", "status": "ok", "duration_ms": 141.5}\n{"service": " api ", "status": "error", "duration_ms": 89.5}\n{"service": " api ", "status": "ok", "duration_ms": 205.0}\n{"service": " api ", "status": "error", "duration_ms": 39.0}\n{"service": "worker", "status": "ok", "duration_ms": 22.0}\n{"service": "分析", "status": "ok", "duration_ms": 265.5}\n{"service": "worker", "status": "ok", "duration_ms": 302.5}\n{"service": "worker", "status": "error", "duration_ms": 304.0}\n{"service": " api ", "status": "error", "duration_ms": 339.0}',encoding='utf-8')
            before=path.read_bytes()
            self.assertEqual(task.audit_file(path),{'count': 17, 'ok': 7, 'errors': 10, 'total_duration_ms': 3405.0, 'services': {'worker': {'count': 7, 'errors': 4, 'duration_ms': 1417.5}, 'api': {'count': 8, 'errors': 6, 'duration_ms': 1515.0}, '分析': {'count': 2, 'errors': 0, 'duration_ms': 472.5}}})
            self.assertEqual(path.read_bytes(),before)
        report=task.audit_events('{"service": "worker", "status": "error", "duration_ms": 304.0}\n{"service": " api ", "status": "ok", "duration_ms": 320.5}\n{"service": "分析", "status": "ok", "duration_ms": 207.0}\n{"service": " api ", "status": "error", "duration_ms": 270.0}\n{"service": "worker", "status": "error", "duration_ms": 24.5}\n{"service": "worker", "status": "error", "duration_ms": 319.0}\n{"service": " api ", "status": "error", "duration_ms": 134.5}\n{"service": " api ", "status": "error", "duration_ms": 117.5}\n{"service": "worker", "status": "ok", "duration_ms": 141.5}\n{"service": " api ", "status": "error", "duration_ms": 89.5}\n{"service": " api ", "status": "ok", "duration_ms": 205.0}\n{"service": " api ", "status": "error", "duration_ms": 39.0}\n{"service": "worker", "status": "ok", "duration_ms": 22.0}\n{"service": "分析", "status": "ok", "duration_ms": 265.5}\n{"service": "worker", "status": "ok", "duration_ms": 302.5}\n{"service": "worker", "status": "error", "duration_ms": 304.0}\n{"service": " api ", "status": "error", "duration_ms": 339.0}')
        rendered=task.render_markdown(report)
        self.assertIsInstance(rendered,str)
        self.assertTrue(rendered.startswith('# Incident summary\n'))
        for label,value in [('Count',report['count']),('OK',report['ok']),('Errors',report['errors'])]:
            self.assertIn(f'{label}: {value}',rendered)
        for service in report['services']: self.assertIn(service,rendered)
        self.assertEqual(task.render_markdown(report),rendered)
        self.assertEqual(task.audit_events('{"service": "worker", "status": "error", "duration_ms": 304.0}\n{"service": " api ", "status": "ok", "duration_ms": 320.5}\n{"service": "分析", "status": "ok", "duration_ms": 207.0}\n{"service": " api ", "status": "error", "duration_ms": 270.0}\n{"service": "worker", "status": "error", "duration_ms": 24.5}\n{"service": "worker", "status": "error", "duration_ms": 319.0}\n{"service": " api ", "status": "error", "duration_ms": 134.5}\n{"service": " api ", "status": "error", "duration_ms": 117.5}\n{"service": "worker", "status": "ok", "duration_ms": 141.5}\n{"service": " api ", "status": "error", "duration_ms": 89.5}\n{"service": " api ", "status": "ok", "duration_ms": 205.0}\n{"service": " api ", "status": "error", "duration_ms": 39.0}\n{"service": "worker", "status": "ok", "duration_ms": 22.0}\n{"service": "分析", "status": "ok", "duration_ms": 265.5}\n{"service": "worker", "status": "ok", "duration_ms": 302.5}\n{"service": "worker", "status": "error", "duration_ms": 304.0}\n{"service": " api ", "status": "error", "duration_ms": 339.0}'),{'count': 17, 'ok': 7, 'errors': 10, 'total_duration_ms': 3405.0, 'services': {'worker': {'count': 7, 'errors': 4, 'duration_ms': 1417.5}, 'api': {'count': 8, 'errors': 6, 'duration_ms': 1515.0}, '分析': {'count': 2, 'errors': 0, 'duration_ms': 472.5}}})
        self.assertEqual(list(task.audit_events('{"service": "worker", "status": "error", "duration_ms": 304.0}\n{"service": " api ", "status": "ok", "duration_ms": 320.5}\n{"service": "分析", "status": "ok", "duration_ms": 207.0}\n{"service": " api ", "status": "error", "duration_ms": 270.0}\n{"service": "worker", "status": "error", "duration_ms": 24.5}\n{"service": "worker", "status": "error", "duration_ms": 319.0}\n{"service": " api ", "status": "error", "duration_ms": 134.5}\n{"service": " api ", "status": "error", "duration_ms": 117.5}\n{"service": "worker", "status": "ok", "duration_ms": 141.5}\n{"service": " api ", "status": "error", "duration_ms": 89.5}\n{"service": " api ", "status": "ok", "duration_ms": 205.0}\n{"service": " api ", "status": "error", "duration_ms": 39.0}\n{"service": "worker", "status": "ok", "duration_ms": 22.0}\n{"service": "分析", "status": "ok", "duration_ms": 265.5}\n{"service": "worker", "status": "ok", "duration_ms": 302.5}\n{"service": "worker", "status": "error", "duration_ms": 304.0}\n{"service": " api ", "status": "error", "duration_ms": 339.0}')['services']),['worker', 'api', '分析'])
    def test_evidence(self):
        import json
        from pathlib import Path
        value=json.loads(Path('evidence.json').read_text())['acceptance_delay_seconds']
        self.assertIs(type(value),int)

if __name__=='__main__':
    unittest.main()
