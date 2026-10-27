"""Post-run review of existing CSV requirements, separate from frozen tests."""
import json
from pathlib import Path
import types
import sys
from decimal import Decimal

root = Path(__file__).resolve().parents[2]

def inspect(path):
    source = path.read_bytes()
    module = types.ModuleType('expense_review')
    exec(compile(source, str(path), 'exec'), module.__dict__)
    checks = []
    for api in ('expense_totals', 'expense_report'):
        fn = getattr(module, api)
        for direction, rows in [('blank_first', 'x,1,\ny,2,USD\n'), ('blank_last', 'x,1,USD\ny,2,\n')]:
            try:
                result = fn('category,amount,currency\n' + rows)
                totals = result if api == 'expense_totals' else result['totals']
                assert totals == {'x': Decimal('1.00'), 'y': Decimal('2.00')}
                checks.append({'name': api + '_' + direction, 'passed': True})
            except Exception as error:
                checks.append({'name': api + '_' + direction, 'passed': False, 'error': type(error).__name__ + ': ' + str(error)})
        try:
            fn('')
        except ValueError:
            checks.append({'name': api + '_empty_csv', 'passed': True})
        except Exception as error:
            checks.append({'name': api + '_empty_csv', 'passed': False, 'error': type(error).__name__ + ': ' + str(error)})
        else:
            checks.append({'name': api + '_empty_csv', 'passed': False, 'error': 'accepted headerless CSV'})
    assert path.read_bytes() == source
    return checks

if __name__ == '__main__':
    result = {'scope': 'Post-run probes of pre-existing nonblank-currency and missing-header rules, not changed frozen acceptance',
        'generated': inspect(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / 'evidence/feedback-recovery-v2/expenses/task.py'),
        'reference_control': inspect(root / 'recovery/expenses_v1.py')}
    print(json.dumps(result, indent=2))
