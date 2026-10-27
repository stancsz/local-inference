import unittest

class Acceptance(unittest.TestCase):
    def test_behavior(self):
        import task
        self.assertEqual(task.normalize_settings({}), {'name': 'default', 'timeout_seconds': 30, 'retries': 0})
        self.assertEqual(task.normalize_settings({'name': ' X ', 'timeout_seconds': 4}), {'name': 'X', 'timeout_seconds': 4, 'retries': 0})
        self.assertEqual(task.normalize_settings({'timeout_ms': 2500})['timeout_seconds'], 2.5)
        with self.assertRaises((TypeError, ValueError)): task.normalize_settings({'timeout_ms': True})
        with self.assertRaises(ValueError): task.normalize_settings({'timeout_ms': 1, 'timeout_seconds': 1})
        with self.assertRaises(ValueError): task.normalize_settings({'extra': 1})
        with self.assertRaises((TypeError, ValueError)): task.normalize_settings({'retries': -1})
        d={'name':' A '}; out=task.normalize_settings(d); self.assertEqual(d, {'name':' A '}); self.assertEqual(task.normalize_settings(out), out)
        self.assertEqual(task.migrate_many([{}, {'name':' B '}]), [{'name':'default','timeout_seconds':30,'retries':0},{'name':'B','timeout_seconds':30,'retries':0}])
        self.assertEqual(task.normalize_settings({'timeout_ms': 1949})['timeout_seconds'], 1.949)
    def test_evidence(self):
        import json
        from pathlib import Path
        value = json.loads(Path('evidence.json').read_text())['acceptance_delay_seconds']
        self.assertIs(type(value), int)

if __name__ == '__main__':
    unittest.main()
