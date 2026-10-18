"""Holdings: what each account held at its valuation date, one shape for every provider (F-025).

Values are in the account's own currency; conversion to GBP happens in the valuation (portfolio-data §8).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Final, Literal

HoldingKind = Literal["security", "cash"]


@dataclass(frozen=True)
class Holding:
    """One security or cash line of a holdings export, normalised."""

    account: str
    owner: str
    wrapper: str
    valuation_date: dt.date | None
    """The export's own date; ``None`` until the valuation assigns one (ii states none)."""
    date_stated: bool
    """False when the valuation date was assumed rather than read from the export."""
    kind: HoldingKind
    security_key: str
    """The provider's symbol, code or fund name; empty for cash."""
    security_name: str
    quantity: float
    price: float | None
    """Per unit, in the account's currency (pounds, never pence); ``None`` for cash."""
    value: float
    """In the account's currency."""
    currency: str
    source_file: str
    source_row: int
    """Line number in the source file."""


HOLDING_COLUMNS: Final[tuple[str, ...]] = tuple(item.name for item in fields(Holding))


@dataclass(frozen=True)
class HoldingsExport:
    """One account's holdings from one export file."""

    account: str
    holdings: list[Holding] = field(default_factory=list)
    stated_fx: tuple[float, dt.date] | None = None
    """GBP per USD and its date, where the export states its own rate (HL's footer)."""


class HoldingsError(ValueError):
    """A holdings export that cannot be read or does not add up; names the file and the figures."""

    def __init__(self, path: Path, problem: str) -> None:
        super().__init__(f"{path.parent.name}/{path.name}: {problem}")
