from csv import DictReader
from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
from io import StringIO


def _parse_rows(csv_text):
    totals = {}
    order = []
    currencies = set()
    count = 0
    reader = DictReader(StringIO(csv_text))
    fieldnames = reader.fieldnames
    if fieldnames is None:
        raise ValueError('missing header')
    seen = set()
    for fn in fieldnames:
        if fn in seen:
            raise ValueError('duplicate header')
        seen.add(fn)
    if 'category' not in seen or 'amount' not in seen:
        raise ValueError('missing required header')
    for row in reader:
        if not row or all((v is None or not v.strip()) for v in row.values()):
            continue
        category_raw = row.get('category')
        amount_raw = row.get('amount')
        if category_raw is None or amount_raw is None:
            raise ValueError('malformed row')
        currency_raw = row.get('currency')
        if currency_raw is not None and currency_raw.strip():
            currencies.add(currency_raw.strip())
        category = category_raw.strip()
        if not category:
            raise ValueError('malformed row')
        try:
            amount = Decimal(amount_raw)
        except InvalidOperation:
            raise ValueError('malformed amount')
        if not amount.is_finite():
            raise ValueError('non-finite amount')
        key = category.lower()
        if key not in totals:
            totals[key] = {'label': category, 'total': Decimal('0')}
            order.append(key)
        totals[key]['total'] += amount
        count += 1
    if len(currencies) > 1:
        raise ValueError('mixed currencies')
    return totals, order, count


def expense_totals(csv_text):
    totals, order, _ = _parse_rows(csv_text)
    return {
        totals[key]['label']: totals[key]['total'].quantize(
            Decimal('0.01'), rounding=ROUND_HALF_EVEN
        )
        for key in order
    }


def expense_report(csv_text):
    totals, order, count = _parse_rows(csv_text)
    grand = sum((totals[key]['total'] for key in order), Decimal('0'))
    return {
        'totals': {
            totals[key]['label']: totals[key]['total'].quantize(
                Decimal('0.01'), rounding=ROUND_HALF_EVEN
            )
            for key in order
        },
        'grand_total': grand.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN),
        'count': count,
    }
