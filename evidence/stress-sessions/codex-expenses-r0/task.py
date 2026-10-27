def expense_totals(csv_text):
    import csv
    from decimal import Decimal, ROUND_HALF_EVEN
    totals = {}
    reader = csv.DictReader(csv_text.splitlines())
    fieldnames = reader.fieldnames or []
    _validate_headers(fieldnames)
    has_currency = "currency" in fieldnames
    currency = None
    for row in reader:
        category = (row["category"] or "").strip()
        amount_raw = (row["amount"] or "").strip()
        if not category and not amount_raw:
            continue
        if not category or not amount_raw:
            raise ValueError("malformed row")
        if has_currency:
            cur = (row["currency"] or "").strip()
            if cur:
                if currency is None:
                    currency = cur
                elif cur != currency:
                    raise ValueError("mixed currencies")
        key = category.lower()
        try:
            amount = Decimal(amount_raw)
        except ArithmeticError:
            raise ValueError(f"malformed amount: {amount_raw}")
        if not amount.is_finite():
            raise ValueError(f"non-finite amount: {amount_raw}")
        if key not in totals:
            totals[key] = (category, Decimal("0"))
        totals[key] = (totals[key][0], totals[key][1] + amount)
    return {label: total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            for key, (label, total) in totals.items()}


def expense_report(csv_text):
    from decimal import Decimal, ROUND_HALF_EVEN
    import csv
    totals = {}
    count = 0
    reader = csv.DictReader(csv_text.splitlines())
    fieldnames = reader.fieldnames or []
    _validate_headers(fieldnames)
    has_currency = "currency" in fieldnames
    currency = None
    for row in reader:
        category = (row["category"] or "").strip()
        amount_raw = (row["amount"] or "").strip()
        if not category and not amount_raw:
            continue
        if not category or not amount_raw:
            raise ValueError("malformed row")
        if has_currency:
            cur = (row["currency"] or "").strip()
            if cur:
                if currency is None:
                    currency = cur
                elif cur != currency:
                    raise ValueError("mixed currencies")
        key = category.lower()
        try:
            amount = Decimal(amount_raw)
        except ArithmeticError:
            raise ValueError(f"malformed amount: {amount_raw}")
        if not amount.is_finite():
            raise ValueError(f"non-finite amount: {amount_raw}")
        if key not in totals:
            totals[key] = (category, Decimal("0"))
        totals[key] = (totals[key][0], totals[key][1] + amount)
        count += 1
    totals_out = {label: total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
                  for key, (label, total) in totals.items()}
    grand_total = sum((total for _, total in totals.values()), Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return {"totals": totals_out, "grand_total": grand_total, "count": count}


def _validate_headers(fieldnames):
    seen = set()
    for name in fieldnames:
        if name in seen:
            raise ValueError(f"duplicate header: {name}")
        seen.add(name)
    for required in ("category", "amount"):
        if required not in seen:
            raise ValueError(f"missing required header: {required}")
