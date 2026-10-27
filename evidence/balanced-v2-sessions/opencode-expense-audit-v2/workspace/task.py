from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, ROUND_HALF_UP

def expense_totals(csv_text):
    text = csv_text
    if text is None:
        raise ValueError
    lines = text.splitlines()
    if not lines:
        raise ValueError
    header = _split_row(lines[0])
    if len(header) < 2:
        raise ValueError
    if header[0] != 'category' or header[1] != 'amount':
        raise ValueError
    extra_headers = [h for h in header[2:] if h]
    if extra_headers:
        raise ValueError
    totals = {}
    count = 0
    for raw in lines[1:]:
        row = _split_row(raw)
        if len(row) < 2:
            raise ValueError
        category = row[0].strip()
        amount_raw = row[1].strip()
        if amount_raw == '':
            raise ValueError
        amount = _parse_amount(amount_raw)
        key = category
        if key in totals:
            totals[key] += amount
        else:
            totals[key] = amount
        count += 1
    return totals

def _split_row(line):
    parts = line.split(',')
    for i, p in enumerate(parts):
        if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
            parts[i] = p[1:-1]
    return parts

def _parse_amount(s):
    if s == '':
        raise ValueError
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError
    if not d.is_finite():
        raise ValueError
    q = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)
    return q
