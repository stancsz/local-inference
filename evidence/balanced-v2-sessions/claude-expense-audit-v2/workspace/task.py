from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
from csv import reader
import io


def _quantize(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)


def expense_totals(csv_text):
    if not isinstance(csv_text, str):
        raise ValueError('csv_text must be a string')
    try:
        rows = list(reader(io.StringIO(csv_text)))
    except (UnicodeDecodeError, UnicodeError):
        raise ValueError('unparseable CSV text')

    if not rows:
        raise ValueError('empty CSV')

    header = rows[0]
    if len(header) < 2:
        raise ValueError('CSV must have at least two required columns')
    for cell in header[:2]:
        if cell is None or cell.strip() == '':
            raise ValueError('CSV header cells must be nonblank')
    if len(set(header[:2])) != 2:
        raise ValueError('duplicate header columns')

    totals = {}
    display = {}
    order = []
    for row in rows[1:]:
        if row is None:
            continue
        if not row or all(cell is None or cell.strip() == '' for cell in row):
            continue
        if len(row) < 2:
            raise ValueError('row has missing cells')
        if len(row) > 2:
            raise ValueError('row has extra cells')
        category = row[0]
        amount_text = row[1]
        if category is None or category.strip() == '':
            raise ValueError('category must be nonblank')
        if amount_text is None or amount_text.strip() == '':
            raise ValueError('amount must be nonblank')
        try:
            amount = Decimal(amount_text.strip())
        except (InvalidOperation, ValueError, ArithmeticError):
            raise ValueError('malformed amount')
        if not amount.is_finite():
            raise ValueError('nonfinite amount')
        key = category.lower()
        if key not in totals:
            totals[key] = Decimal('0')
            display[key] = category
            order.append(key)
        totals[key] += _quantize(amount)
    return {display[key]: _quantize(totals[key]) for key in order}
