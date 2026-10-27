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
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError('CSV is empty: missing category,amount header')
    if len(header) not in (2, 3):
        raise ValueError('CSV must have category,amount[,currency] headers')
    if header[0].strip().lower() != 'category' \
            or header[1].strip().lower() != 'amount':
        raise ValueError('CSV must have category,amount[,currency] headers')
    if len(header) == 3 and header[2].strip().lower() != 'currency':
        raise ValueError('CSV must have category,amount[,currency] headers')
    if len(set(h.strip().lower() for h in header)) != len(header):
        raise ValueError('duplicate header column')

    ncols = len(header)
    groups = {}
    order = []
    nonblank = 0
    currency = None
    for row in reader:
        if not row:
            # Genuinely blank line: no cells at all.
            continue
        if len(row) != ncols:
            raise ValueError('expected %d cells, got %d' % (ncols, len(row)))
        category_raw = row[0]
        amount_raw = row[1]
        currency_raw = row[2] if ncols == 3 else ''
        category = category_raw.strip()
        if not category:
            raise ValueError('empty record is invalid')
        nonblank += 1
        amount = _parse_amount(amount_raw.strip())
        cur = currency_raw.strip().lower()
        key = category.lower()
        if key not in groups:
            groups[key] = {'spelling': category, 'total': Decimal('0')}
            order.append(key)
        groups[key]['total'] += amount
        # Only nonblank currency cells participate in the global comparison.
        if cur:
            if currency is None:
                currency = cur
            elif cur != currency:
                raise ValueError('mixed currencies: %r and %r' % (currency, cur))
    return groups, order, nonblank


def expense_totals(csv_text):
    groups, order, _ = _collect(csv_text)
    return {groups[k]['spelling']: groups[k]['total'].quantize(_Q, rounding=ROUND_HALF_EVEN)
            for k in order}


def expense_report(csv_text):
    groups, order, nonblank = _collect(csv_text)
    totals = {groups[k]['spelling']: groups[k]['total'].quantize(_Q, rounding=ROUND_HALF_EVEN)
              for k in order}
    grand = sum((groups[k]['total'] for k in order), Decimal('0'))
    return {
        'totals': totals,
        'grand_total': grand.quantize(_Q, rounding=ROUND_HALF_EVEN),
        'count': nonblank,
    }
