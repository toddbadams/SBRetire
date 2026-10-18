"""stub"""

from __future__ import annotations

from collections.abc import Sequence

from sbretire.ledger.model import LedgerRow


def reconcile_cash(rows: Sequence[LedgerRow]) -> list[str]:
    return ["not implemented"]
