from csv import DictReader
from io import StringIO
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation, InvalidOperation as _IO

def _validate_header(csv_text):
    import csv as _csv
    reader = _csv.reader(StringIO(csv_text))
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("Empty CSV: no header row")
    fields = [h.strip() for h in header]
    for f in ('category', 'amount'):
        if f not in fields:
            raise ValueError(f"Missing required header: {f!r}")
    seen = set()
    for f in fields:
        if f in seen:
            raise ValueError(f"Duplicate header: {f!r}")
        seen.add(f)
    return fields

def expense_totals(csv_text):
    _validate_header(csv_text)
    totals = {}
    currencies = set()
    has_currency = False
    for row in DictReader(StringIO(csv_text)):
        category = row['category'].strip()
        raw = row['amount'].strip()
        try:
            amount = Decimal(raw)
        except (InvalidOperation, ValueError, ArithmeticError):
            raise ValueError(f"Malformed amount: {raw!r}")
        if not amount.is_finite():
            raise ValueError(f"Non-finite amount: {raw!r}")
        if 'currency' in row:
            has_currency = True
            cur = (row['currency'] or '').strip()
            if cur:
                currencies.add(cur)
        key = category.lower()
        if key not in totals:
            totals[key] = {'label': category, 'total': Decimal('0')}
        totals[key]['total'] += amount
    if has_currency and len(currencies) > 1:
        raise ValueError(f"Mixed currencies: {sorted(currencies)}")
    return {v['label']: v['total'].quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN) for v in totals.values()}

def expense_report(csv_text):
    totals = expense_totals(csv_text)
    count = 0
    for row in DictReader(StringIO(csv_text)):
        if row['category'].strip() or row['amount'].strip():
            count += 1
    grand_total = sum(totals.values(), Decimal('0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    return {'totals': totals, 'grand_total': grand_total, 'count': count}
