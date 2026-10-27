import io
import csv
from decimal import Decimal

def expense_totals(csv_text):
    reader = csv.reader(io.StringIO(csv_text))
    next(reader)
    totals = {}
    for row in reader:
        if not row:
            continue
        category, amount = row[0], row[1]
        key = category if category in totals else category
        totals[key] = totals.get(key, Decimal('0')) + Decimal(amount)
    return {k: v.quantize(Decimal('0.01')) for k, v in totals.items()}
