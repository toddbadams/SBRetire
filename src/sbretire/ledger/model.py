"""Ledger rows: one normalised shape for every provider's transactions (F-024)."""

from __future__ import annotations

from typing import Final

LEDGER_COLUMNS: Final[tuple[str, ...]] = ()


class UnknownTransaction(ValueError):
    pass
