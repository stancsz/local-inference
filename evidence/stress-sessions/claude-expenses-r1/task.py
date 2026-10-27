from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation
import csv
import io

def _validate_header(header):
    if len(header) != len(set(header)):
        raise ValueError("Duplicate headers detected")
    if 'category' not in header or 'amount' not in header:
        raise ValueError("Missing required headers: category and amount")

def expense_totals(csv_text):
    totals = {}
    first_seen = {}
    reader = csv.reader(io.StringIO(csv_text))
    header = [h.strip() for h in next(reader)]
    _validate_header(header)
    currency_idx = header.index('currency') if 'currency' in header else None
    currencies = set()
    for row in reader:
        if not row:
            continue
        category = row[0].strip()
        key = category.lower()
        try:
            amount = Decimal(row[1].strip())
        except InvalidOperation:
            raise ValueError(f"Malformed amount: {row[1].strip()!r}")
        if not amount.is_finite():
            raise ValueError(f"Non-finite amount: {row[1].strip()!r}")
        if currency_idx is not None:
            cur = row[currency_idx].strip()
            if cur:
                currencies.add(cur)
                if len(currencies) > 1:
                    raise ValueError(f"Mixed currencies: {currencies}")
        if key not in first_seen:
            first_seen[key] = category
        totals[key] = totals.get(key, Decimal('0')) + amount
    return {first_seen[key]: total.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN) for key, total in totals.items()}

def expense_report(csv_text):
    totals = {}
    first_seen = {}
    count = 0
    reader = csv.reader(io.StringIO(csv_text))
    header = [h.strip() for h in next(reader)]
    _validate_header(header)
    currency_idx = header.index('currency') if 'currency' in header else None
    currencies = set()
    for row in reader:
        if not row:
            continue
        category = row[0].strip()
        key = category.lower()
        try:
            amount = Decimal(row[1].strip())
        except InvalidOperation:
            raise ValueError(f"Malformed amount: {row[1].strip()!r}")
        if not amount.is_finite():
            raise ValueError(f"Non-finite amount: {row[1].strip()!r}")
        if currency_idx is not None:
            cur = row[currency_idx].strip()
            if cur:
                currencies.add(cur)
                if len(currencies) > 1:
                    raise ValueError(f"Mixed currencies: {currencies}")
        if key not in first_seen:
            first_seen[key] = category
        totals[key] = totals.get(key, Decimal('0')) + amount
        count += 1
    quantized = {first_seen[key]: total.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN) for key, total in totals.items()}
    grand_total = sum(quantized.values(), Decimal('0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    return {'totals': quantized, 'grand_total': grand_total, 'count': count}
