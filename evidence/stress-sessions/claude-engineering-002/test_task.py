import unittest

class Acceptance(unittest.TestCase):
    def test_behavior(self):
        import task
        self.assertEqual(task.clamp(-3), 0)
        self.assertEqual(task.clamp(120), 100)
        self.assertEqual(task.clamp(7, 5, 9), 7)
        for x in (True, '2', None):
            with self.assertRaises(TypeError): task.clamp(x)
        with self.assertRaises(ValueError): task.clamp(1, 5, 2)
        with self.assertRaises(ValueError): task.clamp(float('inf'))
        self.assertEqual(task.clamp_all([-1, 4, 120]), [0, 4, 100])
        self.assertEqual(task.clamp_report([]), {'count': 0, 'min': None, 'max': None, 'sum': 0})
        self.assertEqual(task.clamp_report([2, 8])['sum'], 10)
        with self.assertRaises((TypeError, ValueError)): task.clamp(1, float('nan'), 4)
        it = iter([1, 101]); self.assertEqual(task.clamp_all(it), [1, 100])
        self.assertEqual(task.clamp_all([116, -142, -58, 126, -91, -84, 143, 6, -85, 119, -196, -43, 42, -193, 58, -196]), [max(0, min(100, x)) for x in [116, -142, -58, 126, -91, -84, 143, 6, -85, 119, -196, -43, 42, -193, 58, -196]])
    def test_evidence(self):
        import json
        from pathlib import Path
        value = json.loads(Path('evidence.json').read_text())['acceptance_delay_seconds']
        self.assertIs(type(value), int)

if __name__ == '__main__':
    unittest.main()
