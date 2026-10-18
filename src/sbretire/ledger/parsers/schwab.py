"""Charles Schwab transaction history export (F-024).

Quoted CSV, newest row first, US dates (MM/DD/YYYY), USD amounts with ``$``. ``Amount`` is the cash effect
(net of ``Fees & Comm``); quantities are unsigned, so sells are negated here.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.holdings import Holding, HoldingsError, HoldingsExport
from sbretire.ledger.model import Flow, LedgerRow, TransactionType, UnknownTransaction
from sbretire.ledger.parsers._common import csv_rows, day, money, read_text

# action -> (type, flow); MoneyLink Transfer is decided by the sign of the amount
ACTIONS: Final[dict[str, tuple[TransactionType, Flow]]] = {
    "Buy": ("buy", "none"),
    "Sell": ("sell", "none"),
    "Qualified Dividend": ("dividend", "none"),
    "Credit Interest": ("interest", "none"),
    "Foreign Tax Paid": ("tax_withheld", "none"),
    "ADR Mgmt Fee": ("fee", "none"),
    "Cash Merger": ("corporate_action", "none"),
    "Cash Merger Adj": ("corporate_action", "none"),
}


def parse(path: Path, account: AccountConfig) -> list[LedgerRow]:
    """Every transaction in a Schwab history export, in file order; unknown actions raise."""
    table = csv_rows(read_text(path))
    header, body = table[0], [row for row in table[1:] if any(cell.strip() for cell in row)]
    col = {name: index for index, name in enumerate(header)}
    rows = []
    for offset, record in enumerate(body):
        line = offset + 2
        action = record[col["Action"]].strip()
        cash = money(record[col["Amount"]]) or 0.0
        if action == "MoneyLink Transfer":
            kind: TransactionType = "transfer_in" if cash > 0 else "transfer_out"
            flow: Flow = "external"
        elif action in ACTIONS:
            kind, flow = ACTIONS[action]
        else:
            raise UnknownTransaction(path, line, action)
        quantity = money(record[col["Quantity"]]) or 0.0
        if kind == "sell":
            quantity = -abs(quantity)
        rows.append(
            LedgerRow(
                account=account.id,
                owner=account.owner,
                wrapper=account.wrapper,
                date=day(record[col["Date"]], "%m/%d/%Y"),
                settle_date=None,
                type=kind,
                flow=flow,
                security_key=record[col["Symbol"]].strip(),
                security_name=record[col["Description"]].strip(),
                quantity_change=quantity,
                price=money(record[col["Price"]]),
                cash_change=cash,
                fees=money(record[col["Fees & Comm"]]) or 0.0,
                currency=account.currency,
                reference="",
                source_file=path.name,
                source_row=line,
                sequence=len(body) - offset,
            )
        )
    return rows


_AS_OF: Final = re.compile(r"as of .*?(?P<date>\d{4}/\d{2}/\d{2})")
_CASH: Final = "Cash & Cash Investments"
_TOTAL: Final = "Positions Total"


def parse_holdings(path: Path, account: AccountConfig) -> HoldingsExport:
    """A Schwab positions export: securities and the cash line, dated from the title (portfolio-data §7).

    Raises ``HoldingsError`` when securities + cash differ from "Positions Total" by more than a cent.
    """
    lines = read_text(path).splitlines()
    found = _AS_OF.search(lines[0]) if lines else None
    if found is None:
        raise HoldingsError(path, "no 'as of <date>' in the title line")
    valuation_date = day(found["date"], "%Y/%m/%d")
    start = next((i for i, line in enumerate(lines) if line.startswith('"Symbol"')), None)
    if start is None:
        raise HoldingsError(path, "no Symbol header row")
    table = csv_rows("\n".join(lines[start:]))
    col = {name: index for index, name in enumerate(table[0])}
    holdings, total = [], None
    for offset, record in enumerate(table[1:]):
        if not any(cell.strip() for cell in record):
            continue
        line = start + 2 + offset
        symbol = record[col["Symbol"]].strip()
        value = money(record[col["Mkt Val (Market Value)"]]) or 0.0
        if symbol == _TOTAL:
            total = value
            continue
        cash = symbol == _CASH
        holdings.append(
            Holding(
                account=account.id,
                owner=account.owner,
                wrapper=account.wrapper,
                valuation_date=valuation_date,
                date_stated=True,
                kind="cash" if cash else "security",
                security_key="" if cash else symbol,
                security_name=symbol if cash else record[col["Description"]].strip(),
                quantity=0.0 if cash else money(record[col["Qty (Quantity)"]]) or 0.0,
                price=None if cash else money(record[col["Price"]]),
                value=value,
                currency=account.currency,
                source_file=path.name,
                source_row=line,
            )
        )
    summed = round(sum(holding.value for holding in holdings), 2)
    if total is None or abs(summed - total) > 0.005:
        stated = "missing" if total is None else f"{total:.2f}"
        raise HoldingsError(path, f"positions add up to {summed:.2f} but Positions Total is {stated}")
    return HoldingsExport(account.id, holdings)
