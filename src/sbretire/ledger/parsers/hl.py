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
from sbretire.ledger.holdings import Holding, HoldingsError, HoldingsExport
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


_CREATED: Final = "Spreadsheet created at"
_FOOTNOTES: Final = re.compile(r"(\s+\*\w+)+$")
_FX: Final = re.compile(
    r"(?P<usd>[\d.]+)\s*USD to 100 pence\. Exchange rate correct at (?P<date>\d{2}/\d{2}/\d{4})"
)


def parse_holdings(path: Path, account: AccountConfig) -> HoldingsExport:
    """An HL account summary: securities (pence to pounds), the "Total cash" line and the footer's USD rate.

    Raises ``HoldingsError`` when the securities differ from "Stock value" or the table's Totals row, or
    securities + cash from "Total value", by more than a penny (portfolio-data §7).
    """
    lines = read_text(path).splitlines()
    summary: dict[str, tuple[int, str]] = {}
    for number, record in enumerate(csv_rows("\n".join(lines)), start=1):
        label = record[0].strip() if record else ""
        if label.endswith(":") or label == _CREATED:
            summary[label.rstrip(":")] = (number, record[1].strip() if len(record) > 1 else "")
    if _CREATED not in summary:
        raise HoldingsError(path, f"no '{_CREATED}' line")
    valuation_date = day(summary[_CREATED][1].split()[0], "%d-%m-%Y")
    start = next((i for i, line in enumerate(lines) if line.startswith("Code,")), None)
    if start is None:
        raise HoldingsError(path, "no Code header row")
    table = csv_rows("\n".join(lines[start:]))
    col = {name: index for index, name in enumerate(table[0])}
    holdings, totals = [], None
    for offset, record in enumerate(table[1:]):
        if not any(cell.strip() for cell in record):
            break  # the table ends at a blank line; footnotes follow
        if not record[col["Code"]].strip() and record[col["Stock"]].strip() == "Totals":
            totals = money(record[col["Value (£)"]])
            continue
        pence = money(record[col["Price (pence)"]])
        holdings.append(
            Holding(
                account=account.id,
                owner=account.owner,
                wrapper=account.wrapper,
                valuation_date=valuation_date,
                date_stated=True,
                kind="security",
                security_key=record[col["Code"]].strip(),
                security_name=_FOOTNOTES.sub("", record[col["Stock"]].strip()),
                quantity=money(record[col["Units held"]]) or 0.0,
                price=None if pence is None else round(pence / 100, 10),
                value=money(record[col["Value (£)"]]) or 0.0,
                currency=account.currency,
                source_file=path.name,
                source_row=start + 2 + offset,
            )
        )
    securities = round(sum(holding.value for holding in holdings), 2)
    cash_row, cash_text = summary.get("Total cash", (0, ""))
    cash = money(cash_text) or 0.0
    holdings.append(
        Holding(
            account=account.id,
            owner=account.owner,
            wrapper=account.wrapper,
            valuation_date=valuation_date,
            date_stated=True,
            kind="cash",
            security_key="",
            security_name="Total cash",
            quantity=0.0,
            price=None,
            value=cash,
            currency=account.currency,
            source_file=path.name,
            source_row=cash_row,
        )
    )
    checks = [
        ("Stock value", money(summary.get("Stock value", (0, ""))[1]), securities),
        ("Totals row", totals, securities),
        ("Total value", money(summary.get("Total value", (0, ""))[1]), round(securities + cash, 2)),
    ]
    for label, stated, expected in checks:
        if stated is None or abs(stated - expected) > 0.005:
            shown = "missing" if stated is None else f"{stated:.2f}"
            raise HoldingsError(path, f"{label} is {shown} but the holdings add up to {expected:.2f}")
    stated_fx = None
    for line in lines:
        rate = _FX.search(line)
        if rate:
            stated_fx = (1 / float(rate["usd"]), day(rate["date"], "%d/%m/%Y"))
    return HoldingsExport(account.id, holdings, stated_fx)
