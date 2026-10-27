import unittest

class Acceptance(unittest.TestCase):
    def test_behavior(self):
        import task,json,tempfile
        from pathlib import Path
        sample=[{'path':'b','size_bytes':62,'sha256':'a'*64},{'path':'a','size_bytes':88,'sha256':'B'*64}]
        r=task.audit_manifest(sample)
        self.assertEqual((r['files'],r['bytes']),(2,150))
        self.assertEqual(r['paths'],['a','b'])
        self.assertEqual(r['components'],{'app':{'files':2,'bytes':150}})
        for path in ('','/x','a\\b','a//b','./a','a/../b',None):
            row=dict(sample[0],path=path)
            with self.assertRaises(ValueError): task.audit_manifest([row])
        with self.assertRaises(ValueError): task.audit_manifest([sample[0],sample[0]])
        for key,values in [('size_bytes',[-1,True,False,None,1.5]),('sha256',[None,'z'*64,'a'*63]),('component',[None,True,'  '])]:
            for value in values:
                row=dict(sample[0]);row[key]=value
                with self.assertRaises(ValueError): task.audit_manifest([row])
        for row in ({},dict(sample[0],surprise=1),'not-object'):
            with self.assertRaises(ValueError): task.audit_manifest([row])
        rows=[{'path': 'bin/2708-0.dat', 'size_bytes': 19420, 'sha256': 'cacb46e3372e105c51b5454eeeb600b7105a32b59745590ed2ee7fc8e72b3845', 'component': ' app '}, {'path': 'bin/2708-1.dat', 'size_bytes': 19297, 'sha256': '417108596961e41039416400a9a8337c499450f77751be20f20a1d4629adfe95', 'component': '工具'}, {'path': 'bin/2708-2.dat', 'size_bytes': 5289, 'sha256': '3570c79dde2e1e067f0c3ddd6d22d9d0acbb2966b7d751132aafb03d751777bf', 'component': ' app '}, {'path': 'bin/2708-3.dat', 'size_bytes': 12174, 'sha256': '1916010b24866bbbc9e1e3e5b82f5388a5382971ef05ab9b67142e3548dd9b20', 'component': 'docs'}, {'path': 'bin/2708-4.dat', 'size_bytes': 21837, 'sha256': 'a9428eabe9d6e2e610f61b5db24e7d96e84aee543c9900869815a5daf227042e', 'component': 'docs'}, {'path': 'bin/2708-5.dat', 'size_bytes': 12666, 'sha256': '26496b28ba47fce11af15259355423ccb8d370861e30cc414d2d8de9eec5465e', 'component': '工具'}, {'path': 'bin/2708-6.dat', 'size_bytes': 13628, 'sha256': '16e03c07f2b9f011fe01ea669cad7125e0eeaedc48b065592231b898e463afa8', 'component': '工具'}, {'path': 'bin/2708-7.dat', 'size_bytes': 10743, 'sha256': '8c6453082d6fd1c22442c4de9634aefdba65c80faf3fa8e51b3168186586232f', 'component': ' app '}, {'path': 'bin/2708-8.dat', 'size_bytes': 26193, 'sha256': 'a0a4aa8631328a8fecdf6d604f0ce91602c0ca2d443be48eedff6282aa8ca73c', 'component': 'docs'}, {'path': 'bin/2708-9.dat', 'size_bytes': 28097, 'sha256': '55aea57ca2bfd7c1cb1542e3513bbdaeae627855316b872152fb6adf9aca5000', 'component': 'docs'}, {'path': 'bin/2708-10.dat', 'size_bytes': 24314, 'sha256': '8cf46b3a24b1979d7fce4df3c6c4ae4726152a2d0469d1aead9a889afa5c91b9', 'component': 'docs'}]
        before=json.dumps(rows,sort_keys=True)
        report=task.audit_manifest(row for row in rows)
        self.assertEqual(report,{'files': 11, 'bytes': 193658, 'components': {'app': {'files': 3, 'bytes': 35452}, '工具': {'files': 3, 'bytes': 45591}, 'docs': {'files': 5, 'bytes': 112615}}, 'paths': ['bin/2708-0.dat', 'bin/2708-1.dat', 'bin/2708-10.dat', 'bin/2708-2.dat', 'bin/2708-3.dat', 'bin/2708-4.dat', 'bin/2708-5.dat', 'bin/2708-6.dat', 'bin/2708-7.dat', 'bin/2708-8.dat', 'bin/2708-9.dat']})
        self.assertEqual(json.dumps(rows,sort_keys=True),before)
        self.assertEqual(task.audit_manifest([]),{'files':0,'bytes':0,'components':{},'paths':[]})
        old=[dict(sample[0]),dict(sample[1])]
        new=[dict(sample[0],size_bytes=sample[0]['size_bytes']+1),{'path':'c','size_bytes':0,'sha256':'c'*64}]
        self.assertEqual(task.compare_manifests(old,new),{'added':['c'],'removed':['a'],'changed':['b']})
        self.assertEqual(task.compare_manifests(sample,sample),{'added':[],'removed':[],'changed':[]})
        self.assertEqual(task.compare_manifests([sample[0]],[dict(sample[0],sha256='A'*64,component=' app ')]),{'added':[],'removed':[],'changed':[]})
        with self.assertRaises(ValueError): task.compare_manifests([{}],[])
        with self.assertRaises(ValueError): task.compare_manifests([],[{}])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'release.json';path.write_text(json.dumps([{'path': 'bin/2708-0.dat', 'size_bytes': 19420, 'sha256': 'cacb46e3372e105c51b5454eeeb600b7105a32b59745590ed2ee7fc8e72b3845', 'component': ' app '}, {'path': 'bin/2708-1.dat', 'size_bytes': 19297, 'sha256': '417108596961e41039416400a9a8337c499450f77751be20f20a1d4629adfe95', 'component': '工具'}, {'path': 'bin/2708-2.dat', 'size_bytes': 5289, 'sha256': '3570c79dde2e1e067f0c3ddd6d22d9d0acbb2966b7d751132aafb03d751777bf', 'component': ' app '}, {'path': 'bin/2708-3.dat', 'size_bytes': 12174, 'sha256': '1916010b24866bbbc9e1e3e5b82f5388a5382971ef05ab9b67142e3548dd9b20', 'component': 'docs'}, {'path': 'bin/2708-4.dat', 'size_bytes': 21837, 'sha256': 'a9428eabe9d6e2e610f61b5db24e7d96e84aee543c9900869815a5daf227042e', 'component': 'docs'}, {'path': 'bin/2708-5.dat', 'size_bytes': 12666, 'sha256': '26496b28ba47fce11af15259355423ccb8d370861e30cc414d2d8de9eec5465e', 'component': '工具'}, {'path': 'bin/2708-6.dat', 'size_bytes': 13628, 'sha256': '16e03c07f2b9f011fe01ea669cad7125e0eeaedc48b065592231b898e463afa8', 'component': '工具'}, {'path': 'bin/2708-7.dat', 'size_bytes': 10743, 'sha256': '8c6453082d6fd1c22442c4de9634aefdba65c80faf3fa8e51b3168186586232f', 'component': ' app '}, {'path': 'bin/2708-8.dat', 'size_bytes': 26193, 'sha256': 'a0a4aa8631328a8fecdf6d604f0ce91602c0ca2d443be48eedff6282aa8ca73c', 'component': 'docs'}, {'path': 'bin/2708-9.dat', 'size_bytes': 28097, 'sha256': '55aea57ca2bfd7c1cb1542e3513bbdaeae627855316b872152fb6adf9aca5000', 'component': 'docs'}, {'path': 'bin/2708-10.dat', 'size_bytes': 24314, 'sha256': '8cf46b3a24b1979d7fce4df3c6c4ae4726152a2d0469d1aead9a889afa5c91b9', 'component': 'docs'}],ensure_ascii=False),encoding='utf-8')
            before=path.read_bytes()
            self.assertEqual(task.audit_file(path),{'files': 11, 'bytes': 193658, 'components': {'app': {'files': 3, 'bytes': 35452}, '工具': {'files': 3, 'bytes': 45591}, 'docs': {'files': 5, 'bytes': 112615}}, 'paths': ['bin/2708-0.dat', 'bin/2708-1.dat', 'bin/2708-10.dat', 'bin/2708-2.dat', 'bin/2708-3.dat', 'bin/2708-4.dat', 'bin/2708-5.dat', 'bin/2708-6.dat', 'bin/2708-7.dat', 'bin/2708-8.dat', 'bin/2708-9.dat']})
            self.assertEqual(path.read_bytes(),before)
            for bad in ('not-json','{}','null'):
                path.write_text(bad,encoding='utf-8')
                with self.assertRaises(ValueError): task.audit_file(path)
    def test_evidence(self):
        import json
        from pathlib import Path
        value=json.loads(Path('evidence.json').read_text())['acceptance_delay_seconds']
        self.assertIs(type(value),int)

if __name__=='__main__':
    unittest.main()
