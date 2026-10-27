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
        import task
        from decimal import Decimal
        data = 'category,amount\nFood,1.005\nfood,2.00\nTransit,3.00\n'
        self.assertEqual(task.expense_totals(data), {'Food': Decimal('3.00'), 'Transit': Decimal('3.00')})
    def test_evidence(self):
        import json
        from pathlib import Path
        value = json.loads(Path('evidence.json').read_text())['acceptance_delay_seconds']
        self.assertIs(type(value), int)
    def test_seeded_total(self):
        import task
        from decimal import Decimal
        self.assertEqual(task.expense_totals('category,amount\nseed-2715,84.00\n'),{'seed-2715':Decimal('84.00')})

if __name__ == '__main__':
    unittest.main()
