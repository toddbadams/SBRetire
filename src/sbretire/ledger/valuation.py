"""Valuing the newest month folder's holdings in GBP (F-025)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.holdings import HoldingsExport


class ValuationError(ValueError):
    """stub"""


def read_holdings(root: Path, accounts: Sequence[AccountConfig]) -> tuple[str, list[HoldingsExport]]:
    raise NotImplementedError


def value_holdings(folder: str, exports: Sequence[HoldingsExport], usd_gbp: float | None) -> object:
    raise NotImplementedError
