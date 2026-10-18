"""interactive investor transaction export (F-024).

UTF-8 with several leading byte-order marks, newest row first, UK dates, quoted ``£1,234.56`` amounts, ``n/a``
for empty cells, separate ``Debit`` and ``Credit`` columns and a ``Running Balance``. The ``Description`` says
what a row is (§5 of the F-024 brief).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.holdings import Holding, HoldingsError, HoldingsExport
from sbretire.ledger.model import Flow, LedgerRow, TransactionType, UnknownTransaction
from sbretire.ledger.parsers._common import csv_rows, day, money, read_text

# "<qty> <issuer> Del <price> S Date <d/m/y>": a purchase settled into the account
_BOUGHT: Final = re.compile(r"\d[\d,.]*\s+.*\bDel\b.*\bS Date\b.*")
_TRANSFER_IN: Final = re.compile(r"Trf from .+")
DESCRIPTIONS: Final[dict[str, tuple[TransactionType, Flow]]] = {"Total Monthly Fee": ("fee", "none")}


def _classify(description: str) -> tuple[TransactionType, Flow] | None:
    if _BOUGHT.fullmatch(description):
        return "buy", "none"
    if _TRANSFER_IN.fullmatch(description):
        return "transfer_in", "external"
    return DESCRIPTIONS.get(description)


def _text(cell: str) -> str:
    value = cell.strip()
    return "" if value == "n/a" else value


def parse(path: Path, account: AccountConfig) -> list[LedgerRow]:
    """Every transaction in an ii export, in file order; unknown descriptions raise."""
    table = csv_rows(read_text(path))
    col = {name: index for index, name in enumerate(table[0])}
    body = [(offset + 2, row) for offset, row in enumerate(table[1:]) if any(cell.strip() for cell in row)]
    rows = []
    for offset, (line, record) in enumerate(body):
        description = record[col["Description"]].strip()
        classified = _classify(description)
        if classified is None:
            raise UnknownTransaction(path, line, description)
        kind, flow = classified
        cash = (money(record[col["Credit"]]) or 0.0) - (money(record[col["Debit"]]) or 0.0)
        settle = _text(record[col["Settlement Date"]])
        rows.append(
            LedgerRow(
                account=account.id,
                owner=account.owner,
                wrapper=account.wrapper,
                date=day(record[col["Date"]], "%d/%m/%Y"),
                settle_date=day(settle, "%d/%m/%Y") if settle else None,
                type=kind,
                flow=flow,
                security_key=_text(record[col["Symbol"]]),
                security_name=description if kind == "buy" else "",
                quantity_change=money(record[col["Quantity"]]) or 0.0,
                price=money(record[col["Price"]]),
                cash_change=round(cash, 2),
                fees=0.0,
                currency=account.currency,
                reference=_text(record[col["Reference"]]),
                source_file=path.name,
                source_row=line,
                sequence=len(body) - offset,
                stated_balance=money(record[col["Running Balance"]]),
            )
        )
    return rows


def parse_holdings(path: Path, account: AccountConfig) -> HoldingsExport:
    """An ii holdings export: securities valued by ``Market Value (£)``; no date and no cash in the file.

    ii's ``Price`` and ``Market Value`` are in the listing currency, so the price kept is value / quantity in
    pounds (portfolio-data §7). The valuation assigns the date; ``cash_from_transactions`` gives the cash.
    """
    table = csv_rows(read_text(path))
    col = {name: index for index, name in enumerate(table[0])}
    holdings = []
    for offset, record in enumerate(table[1:]):
        if not any(cell.strip() for cell in record):
            continue
        quantity = money(record[col["Qty"]]) or 0.0
        value = money(record[col["Market Value (£)"]]) or 0.0
        holdings.append(
            Holding(
                account=account.id,
                owner=account.owner,
                wrapper=account.wrapper,
                valuation_date=None,
                date_stated=False,
                kind="security",
                security_key=record[col["Symbol"]].strip(),
                security_name=record[col["Name"]].strip(),
                quantity=quantity,
                price=round(value / quantity, 10) if quantity else None,
                value=value,
                currency=account.currency,
                source_file=path.name,
                source_row=offset + 2,
            )
        )
    return HoldingsExport(account.id, holdings)


def cash_from_transactions(
    rows: Sequence[LedgerRow], account: AccountConfig, path: Path | None = None
) -> Holding:
    """ii's cash: the newest stated running balance among the account's transaction rows (portfolio-data §7).

    Raises ``HoldingsError`` (naming ``path``, the transactions file) when no row states a balance.
    """
    stated = [row for row in rows if row.account == account.id and row.stated_balance is not None]
    if not stated:
        where = path if path is not None else Path(account.transactions[0])
        raise HoldingsError(where, f"no running balance for {account.id}'s cash")
    latest = max(stated, key=lambda row: row.sequence)
    return Holding(
        account=account.id,
        owner=account.owner,
        wrapper=account.wrapper,
        valuation_date=None,
        date_stated=False,
        kind="cash",
        security_key="",
        security_name="Cash (running balance)",
        quantity=0.0,
        price=None,
        value=latest.stated_balance or 0.0,
        currency=account.currency,
        source_file=latest.source_file,
        source_row=latest.source_row,
    )
