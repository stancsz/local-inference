"""New workload epoch with workspace-inherited fixture directories."""
from stress import supplement_tasks_v1 as supplement
from stress import acceptance_tasks as original

TASKS = ('incident_log', 'release_manifest', 'expense_audit')

FIXTURE_SOURCE = '''
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

'''


def initial_source(task):
    if task not in TASKS: raise ValueError('unknown portable workload')
    return original.initial_source('expenses') if task == 'expense_audit' else supplement.initial_source(task)


def stage(task, number, seed):
    if task not in TASKS or type(number) is not int or number < 0 or type(seed) is not int:
        raise ValueError('invalid portable workload, stage or seed')
    definition = dict(original.stage('expenses', number, seed) if task == 'expense_audit' else supplement.stage(task, number, seed))
    tests = definition['tests'].replace('import unittest\n', 'import unittest\n' + FIXTURE_SOURCE, 1)
    tests = tests.replace('tempfile.TemporaryDirectory()', '_workspace_fixture()')
    if task == 'expense_audit':
        head, marker, tail = tests.partition('\nif __name__')
        assert marker
        amount = seed % 87 + 1
        category = 'seed-' + str(seed % 100000)
        extra = f"    def test_seeded_total(self):\n        import task\n        from decimal import Decimal\n        self.assertEqual(task.expense_totals('category,amount\\n{category},{amount}.00\\n'),{{{category!r}:Decimal('{amount}.00')}})\n"
        if number >= 8:
            extra += '''    def test_additional_contracts(self):
        import task
        from decimal import Decimal
        for name in ('expense_totals','expense_report'):
            fn=getattr(task,name)
            for rows in ('x,1,\\ny,2,USD\\n','x,1,USD\\ny,2,\\n'):
                result=fn('category,amount,currency\\n'+rows)
                totals=result if name=='expense_totals' else result['totals']
                self.assertEqual(totals,{'x':Decimal('1.00'),'y':Decimal('2.00')})
            for bad in ('','category,amount\\nFood\\n','category,amount\\nFood,1,extra\\n','category,amount\\n,\\n','category,amount,amount\\nx,1,2\\n'):
                with self.assertRaises(ValueError): fn(bad)
        for amount in ('NaN','Infinity','garbage'):
            with self.assertRaises(ValueError): task.expense_totals('category,amount\\nx,'+amount+'\\n')
        self.assertEqual(task.expense_totals('category,amount\\n"Food, home",1.00\\n'),{'Food, home':Decimal('1.00')})
        report=task.expense_report('category,amount\\nx,1.005\\nx,0.005\\n')
        self.assertEqual(set(report),{'totals','grand_total','count'})
        self.assertIs(type(report['count']),int)
        self.assertIsInstance(report['grand_total'],Decimal)
        self.assertEqual(report['grand_total'].as_tuple().exponent,-2)
        self.assertEqual(report['grand_total'],Decimal('1.01'))
'''
        tests = head + extra + marker + tail
        definition['requirement'] += " Report shape is exactly {'totals':dict,'grand_total':Decimal fixed to two decimal places,'count':int}; CSV has two required columns and optional currency. Compare only NONBLANK currencies globally, allow blank cells with one nonblank currency. Empty CSV, duplicate headers, missing/extra cells, delimited empty rows and malformed/nonfinite amounts raise ValueError. Read only workspace task.py/test_task.py/evidence.json; no parent-project/reference files."
    definition['tests'] = tests
    return definition
