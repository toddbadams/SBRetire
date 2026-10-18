"""Vanguard UK transaction export (F-024).

Windows-1252 CSV, oldest row first, ISO dates. One file may hold several accounts (the ``Account`` column; an
account's ``filter`` keeps its rows). An event is two records: an ``Investment`` record carries the units (its
amount is not cash) and a ``Cash`` record carries the money and the running ``Cash Balance`` (brief §2 #8).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.holdings import Holding, HoldingsError, HoldingsExport
from sbretire.ledger.model import Flow, LedgerRow, TransactionType, UnknownTransaction
from sbretire.ledger.parsers._common import csv_rows, day, money, read_text

TYPES: Final[dict[str, tuple[TransactionType, Flow]]] = {
    "Buy": ("buy", "none"),
    "Sell": ("sell", "none"),
    "Sell (Fee)": ("sell", "none"),  # units sold to pay the account fee
    "Account Fee": ("fee", "none"),
    "Interest": ("interest", "none"),
    "Deposit": ("contribution", "external"),
    "Contribution": ("contribution", "external"),
    "Tax Relief": ("tax_relief", "external"),
}


def parse(path: Path, account: AccountConfig) -> list[LedgerRow]:
    """The account's transaction legs in a Vanguard export, in file order; unknown types raise."""
    table = csv_rows(read_text(path))
    col = {name: index for index, name in enumerate(table[0])}
    body = [
        (offset + 2, row)
        for offset, row in enumerate(table[1:])
        if any(cell.strip() for cell in row)
        and (account.filter is None or row[col["Account"]].strip() == account.filter)
    ]
    rows = []
    for sequence, (line, record) in enumerate(body, start=1):
        found = record[col["Transaction Type"]].strip()
        if found not in TYPES:
            raise UnknownTransaction(path, line, found)
        kind, flow = TYPES[found]
        investment = record[col["Record Type"]].strip() == "Investment"
        name = record[col["Investment Name"]].strip() if investment else ""
        rows.append(
            LedgerRow(
                account=account.id,
                owner=account.owner,
                wrapper=account.wrapper,
                date=day(record[col["Date"]], "%Y-%m-%d"),
                settle_date=None,
                type=kind,
                flow=flow,
                security_key=name,
                security_name=name,
                quantity_change=(money(record[col["Quantity"]]) or 0.0) if investment else 0.0,
                price=money(record[col["Price (GBP)"]]) if investment else None,
                cash_change=0.0 if investment else money(record[col["Amount (GBP)"]]) or 0.0,
                fees=0.0,
                currency=account.currency,
                reference="",
                source_file=path.name,
                source_row=line,
                sequence=sequence,
                stated_balance=None if investment else money(record[col["Cash Balance (GBP)"]]),
            )
        )
    return rows


def parse_holdings(path: Path, account: AccountConfig) -> HoldingsExport:
    raise NotImplementedError
