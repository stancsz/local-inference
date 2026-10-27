"""Deterministic expense-validation recovery fixture (version 1).

Separately versioned code-repair artifact. It is NOT a retroactive pass of any
recorded model attempt and NOT evidence that any model learned the fixes.
Pure stdlib: csv + decimal only. No I/O, no globals mutated, deterministic.

Contract (see stress/contract_probe.py and stress/acceptance_tasks.py, both
frozen and unmodified):

* header must contain 'category' and 'amount'; duplicate headers rejected.
* data rows must have exactly as many cells as the header; a missing cell or
  an unlabelled extra cell raises ValueError.
* amounts must be present, non-empty and finite decimals.
* categories are stripped, grouped case-insensitively, and the first observed
  spelling and ordering are preserved.
* sums are aggregated before HALF_EVEN quantisation to 0.01.
* a currency column is optional; mixing currencies raises ValueError.
"""

from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN

__all__ = ["expense_totals", "expense_report"]

_CENT = Decimal("0.01")
_REQUIRED = ("category", "amount")
_CURRENCY = "currency"


def _read_rows(csv_text):
    """Return (header, data_rows) with the header validated."""
    if not isinstance(csv_text, str):
        raise ValueError("CSV input must be text")
    reader = csv.reader(io.StringIO(csv_text, newline=""))
    rows = list(reader)
    if not rows:
        raise ValueError("Empty CSV: no header row")
    header = [field.strip() for field in rows[0]]
    for name in _REQUIRED:
        if name not in header:
            raise ValueError("Missing required header: %r" % (name,))
    seen = set()
    for name in header:
        if name in seen:
            raise ValueError("Duplicate header: %r" % (name,))
        seen.add(name)
    return header, rows[1:]


def _blank_row(row):
    # Delimiters create cells: even empty cells must satisfy width/amount checks.
    return not row


def _parse_amount(raw):
    text = raw.strip()
    if not text:
        raise ValueError("Missing amount")
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError, ArithmeticError):
        raise ValueError("Malformed amount: %r" % (raw,))
    if not amount.is_finite():
        raise ValueError("Non-finite amount: %r" % (raw,))
    return amount


def expense_totals(csv_text):
    """Return dict mapping category label to Decimal total (0.01 HALF_EVEN)."""
    header, rows = _read_rows(csv_text)
    width = len(header)
    index = dict((name, position) for position, name in enumerate(header))
    has_currency = _CURRENCY in index

    order = []
    labels = {}
    sums = {}
    currencies = set()
    for number, row in enumerate(rows, start=2):
        if _blank_row(row):
            continue
        if len(row) < width:
            raise ValueError(
                "Row %d has %d cell(s), expected %d: missing cell"
                % (number, len(row), width)
            )
        if len(row) > width:
            raise ValueError(
                "Row %d has %d cell(s), expected %d: unlabelled extra cell"
                % (number, len(row), width)
            )
        label = row[index["category"]].strip()
        amount = _parse_amount(row[index["amount"]])
        if has_currency:
            currency = row[index[_CURRENCY]].strip()
            if currency:
                currencies.add(currency)
        key = label.casefold()
        if key not in sums:
            sums[key] = Decimal("0")
            labels[key] = label
            order.append(key)
        sums[key] = sums[key] + amount

    if has_currency and len(currencies) > 1:
        raise ValueError("Mixed currencies: %s" % (sorted(currencies),))
    result = dict()
    for key in order:
        label = labels[key]
        result[label] = sums[key].quantize(_CENT, rounding=ROUND_HALF_EVEN)
    return result


def expense_report(csv_text):
    """Return dict with totals, grand_total (Decimal) and count (int)."""
    totals = expense_totals(csv_text)
    _header, rows = _read_rows(csv_text)
    count = sum(1 for row in rows if not _blank_row(row))
    grand_total = sum(totals.values(), Decimal("0")).quantize(
        _CENT, rounding=ROUND_HALF_EVEN
    )
    return dict(totals=totals, grand_total=grand_total, count=count)
