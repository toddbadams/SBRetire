"""Charles Schwab transaction history export (F-024).

Quoted CSV, newest row first, US dates (MM/DD/YYYY), USD amounts with ``$``. ``Amount`` is the cash effect
(net of ``Fees & Comm``); quantities are unsigned, so sells are negated here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from sbretire.ledger.accounts import AccountConfig
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
