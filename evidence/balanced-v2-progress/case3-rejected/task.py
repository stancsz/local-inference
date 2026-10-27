from csv import reader
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext


def _quantize_cents(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)


def _finite_decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError('amount must be a finite decimal number') from None


def _nonblank(value):
    return value is not None and value.strip() != ''


def expense_totals(csv_text):
    if not isinstance(csv_text, str):
        raise ValueError('csv_text must be a string')

    rows = list(reader(csv_text.splitlines()))
    if not rows:
        raise ValueError('CSV must include a header row')

    header = rows[0]
    if len(header) not in (2, 3):
        raise ValueError('header must be category,amount or category,amount,currency')

    if header[0].strip() != 'category':
        raise ValueError('header must start with category')
    if header[1].strip() != 'amount':
        raise ValueError('second header must be amount')
    if len(header) == 3 and header[2].strip() != 'currency':
        raise ValueError('optional third header must be currency')

    if len(set(str(cell).strip() for cell in header)) != len(header):
        raise ValueError('duplicate header columns')

    has_currency = len(header) == 3
    totals = {}
    count = 0
    seen_currencies = set()

    for line_number, row in enumerate(rows[1:], start=2):
        if not row or all(cell.strip() == '' for cell in row):
            continue

        if len(row) == 2:
            category, amount, currency = row[0], row[1], ''
        elif len(row) == 3:
            category, amount, currency = row
        else:
            raise ValueError('each row must have two or three cells')

        category = category.strip()
        currency = currency.strip()

        if not category:
            raise ValueError('category is required')
        if not _nonblank(amount):
            raise ValueError('amount is required')

        if has_currency:
            if currency:
                if not _nonblank(currency):
                    raise ValueError('currency must be a single nonblank value')
                seen_currencies.add(currency)
        elif currency:
            raise ValueError('currency column is not present')

        amount_value = _finite_decimal(amount)
        if not amount_value.is_finite():
            raise ValueError('amount must be finite')

        totals[category] = totals.get(category, Decimal('0')) + amount_value
        count += 1

    with localcontext() as context:
        context.prec = 50
        quantized_totals = {
            category: _quantize_cents(total)
            for category, total in totals.items()
        }
        grand_total = _quantize_cents(sum(totals.values(), Decimal('0')))

    if len(seen_currencies) > 1:
        raise ValueError('all nonblank currency values must match globally')

    return quantized_totals