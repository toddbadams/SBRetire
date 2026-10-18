"""Hargreaves Lansdown transaction export (F-024).

Windows-1252 text with a summary preamble (title, client details, valuation time, blank line) before the
``Trade date,…`` table; newest row first; UK dates. The ``Reference`` column says what a row is: ``B…`` buy,
``S…`` sell, or a fixed code (§5 of the F-024 brief). Unit cost is in pence; ``Value (£)`` is the cash effect.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.model import Flow, LedgerRow, TransactionType, UnknownTransaction
from sbretire.ledger.parsers._common import csv_rows, day, money, read_text

REFERENCES: Final[dict[str, tuple[TransactionType, Flow]]] = {
    "INTEREST": ("interest", "none"),
    "Transfer": ("internal_transfer", "internal"),  # from the SIPP income account
    "TRANSFER": ("internal_transfer", "internal"),  # product transfer into the SIPP's drawdown part
    "MANAGE FEE": ("fee", "none"),
    "ID TFC": ("transfer_out", "external"),  # tax-free cash paid to the bank
    "BACS": ("transfer_in", "external"),  # pension transferred in
}
_TRADE: Final = re.compile(r"(?P<side>[BS])\d+")
_NAME: Final = re.compile(r"^(?P<name>.*?)\s+[\d,.]+\s+@\s+[\d,.]+\s*$")


def parse(path: Path, account: AccountConfig) -> list[LedgerRow]:
    """Every transaction in an HL export, in file order; unknown references raise."""
    lines = read_text(path).splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith("Trade date"))
    table = csv_rows("\n".join(lines[start:]))
    col = {name: index for index, name in enumerate(table[0])}
    body = [(start + 2 + offset, row) for offset, row in enumerate(table[1:]) if any(c.strip() for c in row)]
    rows = []
    for offset, (line, record) in enumerate(body):
        reference = record[col["Reference"]].strip()
        description = record[col["Description"]].strip()
        trade = _TRADE.fullmatch(reference)
        name, quantity, price = "", 0.0, None
        if trade:
            kind: TransactionType = "buy" if trade["side"] == "B" else "sell"
            flow: Flow = "none"
            match = _NAME.match(description)
            name = match["name"].strip() if match else description
            units = abs(money(record[col["Quantity"]]) or 0.0)
            quantity = units if kind == "buy" else -units
            pence = money(record[col["Unit cost (p)"]])
            price = None if pence is None else round(pence / 100, 10)
        elif reference in REFERENCES:
            kind, flow = REFERENCES[reference]
        else:
            raise UnknownTransaction(path, line, f"{reference} {description}")
        rows.append(
            LedgerRow(
                account=account.id,
                owner=account.owner,
                wrapper=account.wrapper,
                date=day(record[col["Trade date"]], "%d/%m/%Y"),
                settle_date=day(record[col["Settle date"]], "%d/%m/%Y"),
                type=kind,
                flow=flow,
                security_key=name,
                security_name=name,
                quantity_change=quantity,
                price=price,
                cash_change=money(record[-1]) or 0.0,
                fees=0.0,
                currency=account.currency,
                reference=reference,
                source_file=path.name,
                source_row=line,
                sequence=len(body) - offset,
            )
        )
    return rows
