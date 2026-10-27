import io
import csv
from decimal import Decimal, ROUND_HALF_EVEN

_Q = Decimal('0.01')


def _parse_amount(text):
    try:
        value = Decimal(text)
    except ArithmeticError:
        raise ValueError('malformed amount: %r' % text)
    if not value.is_finite():
        raise ValueError('nonfinite amount: %r' % text)
    return value


def _collect(csv_text):
    """Parse the CSV text into (groups, nonblank_count).

    ``groups`` maps a case-insensitive category key to a dict holding the
    first-seen spelling, first-seen order index and the aggregated Decimal
    total (unquantized).
    """
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader)
    if len(header) != 3 or header[0].strip().lower() != 'category' \
            or header[1].strip().lower() != 'amount':
        raise ValueError('CSV must have category,amount[,currency] headers')

    groups = {}
    order = []
    nonblank = 0
    for row in reader:
        if not row:
            # Genuinely blank line: no cells at all.
            continue
        if len(row) != 3:
            raise ValueError('expected 3 cells, got %d' % len(row))
        category_raw, amount_raw, currency_raw = row
        category = category_raw.strip()
        if not category:
            raise ValueError('empty record is invalid')
        nonblank += 1
        amount = _parse_amount(amount_raw.strip())
        currency = currency_raw.strip().lower()
        key = category.lower()
        if key not in groups:
            groups[key] = {'spelling': category, 'total': Decimal('0')}
            order.append(key)
        groups[key]['total'] += amount
        if currency:
            existing = groups[key].get('currency')
            if existing is None:
                groups[key]['currency'] = currency
            elif currency != existing:
                raise ValueError('mixed currencies for category %r' % category)
    return groups, order, nonblank


def expense_totals(csv_text):
    groups, order, _ = _collect(csv_text)
    return {groups[k]['spelling']: groups[k]['total'].quantize(_Q, rounding=ROUND_HALF_EVEN)
            for k in order}


def expense_report(csv_text):
    groups, order, nonblank = _collect(csv_text)
    report = {}
    grand = Decimal('0')
    for k in order:
        value = groups[k]['total']
        grand += value
        report[groups[k]['spelling']] = value.quantize(_Q, rounding=ROUND_HALF_EVEN)
    report['grand_total'] = grand.quantize(_Q, rounding=ROUND_HALF_EVEN)
    report['count'] = nonblank
    return report
