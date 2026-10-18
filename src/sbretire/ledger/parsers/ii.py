"""stub"""

from __future__ import annotations

from pathlib import Path

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.model import LedgerRow


def parse(path: Path, account: AccountConfig) -> list[LedgerRow]:
    return []
