import unittest

class Acceptance(unittest.TestCase):
    def test_behavior(self):
        import task
        from decimal import Decimal
        data = 'category,amount\nFood,1.005\nfood,2.00\nTransit,3.00\n'
        self.assertEqual(task.expense_totals(data), {'Food': Decimal('3.00'), 'Transit': Decimal('3.00')})
        self.assertEqual(task.expense_totals('category,amount\n A ,1\na,2\n'), {'A': Decimal('3.00')})
        self.assertEqual(task.expense_totals('category,amount\nrefund,-2\n')['refund'], Decimal('-2.00'))
        with self.assertRaises(ValueError): task.expense_totals('category,amount\nx,nope\n')
        with self.assertRaises(ValueError): task.expense_totals('category,amount,currency\nx,1,USD\ny,2,CAD\n')
        r=task.expense_report('category,amount\nx,1.00\nx,2.00\n'); self.assertEqual(r['count'], 2); self.assertEqual(r['grand_total'], Decimal('3.00'))
        with self.assertRaises(ValueError): task.expense_totals('amount\n1\n')
        self.assertEqual(list(task.expense_totals('category,amount\nb,1\na,2\n')), ['b','a'])
        self.assertEqual(task.expense_totals('category,amount\nedge,79.00\n')['edge'], Decimal('79.00'))
        self.assertEqual(task.expense_totals('category,amount\nx,1.005\nx,0.005\n')['x'], Decimal('1.01'))
    def test_evidence(self):
        import json
        from pathlib import Path
        value = json.loads(Path('evidence.json').read_text())['acceptance_delay_seconds']
        self.assertIs(type(value), int)

if __name__ == '__main__':
    unittest.main()
