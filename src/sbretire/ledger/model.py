"""Ledger rows: one normalised shape for every provider's transactions (F-024; portfolio-data §4).

Quantities and cash are signed from the account's point of view: ``quantity_change`` > 0 means units received,
``cash_change`` > 0 means money into the account's cash. Amounts stay in the account's native currency.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import datetime as dt
from pathlib import Path
from typing import Final, Literal

TransactionType = Literal[
    "buy",
    "sell",
    "dividend",
    "interest",
    "fee",
    "tax_withheld",
    "contribution",
    "tax_relief",
    "transfer_in",
    "transfer_out",
    "internal_transfer",
    "corporate_action",
]
Flow = Literal["external", "internal", "none"]
"""external: money into or out of the household; internal: a move inside one account; none: anything else."""


@dataclass(frozen=True)
class LedgerRow:
    """One transaction leg from a provider export, normalised."""

    account: str
    owner: str
    wrapper: str
    date: dt.date
    settle_date: dt.date | None
    type: TransactionType
    flow: Flow
    security_key: str
    """The provider's identifier for the security (symbol, SEDOL or fund name); empty for cash-only rows."""
    security_name: str
    quantity_change: float
    price: float | None
    """Per unit, in the account's currency (pounds, never pence)."""
    cash_change: float
    fees: float
    currency: str
    reference: str
    source_file: str
    source_row: int
    """Line number in the source file."""
    sequence: int
    """Chronological position within the source file (1 = oldest), whatever order the file lists rows in."""
    stated_balance: float | None = None
    """The export's running cash balance after this row, where the export states one."""

    def fingerprint(self) -> tuple[object, ...]:
        """What makes two rows the same transaction when months' exports overlap (portfolio-data §3)."""
        return (
            self.account,
            self.date,
            self.type,
            self.security_key,
            round(self.quantity_change, 6),
            round(self.cash_change, 2),
            self.reference,
        )


LEDGER_COLUMNS: Final[tuple[str, ...]] = tuple(field.name for field in fields(LedgerRow))


class UnknownTransaction(ValueError):
    """A row the importer cannot classify; the message names the file, row and what was found."""

    def __init__(self, path: Path, row: int, found: str) -> None:
        super().__init__(f"{path.name} row {row}: unknown transaction {found!r}; add it to the parser's map")
