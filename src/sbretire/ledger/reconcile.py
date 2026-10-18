"""Cash reconciliation against the exports' running balances (F-024; brief §2 #9)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Final

from sbretire.ledger.model import LedgerRow

_TOLERANCE: Final = 0.005  # half a penny


def reconcile_cash(rows: Sequence[LedgerRow]) -> list[str]:
    """Problems found checking cumulative ledger cash against each stated running balance; empty means clean.

    Rows are grouped by account and source file and taken in chronological ``sequence``. The opening cash
    (before the export's first row) is inferred from the first stated balance; every later stated balance must
    then match the running total. Only the first break per account and file is reported.
    """
    groups: dict[tuple[str, str], list[LedgerRow]] = defaultdict(list)
    for row in rows:
        groups[row.account, row.source_file].append(row)
    problems = []
    for (account, source), group in groups.items():
        cash, opening = 0.0, None
        for row in sorted(group, key=lambda r: r.sequence):
            cash += row.cash_change
            if row.stated_balance is None:
                continue
            if opening is None:
                opening = row.stated_balance - cash
            elif abs(opening + cash - row.stated_balance) > _TOLERANCE:
                problems.append(
                    f"{account} ({source} row {row.source_row}): ledger cash {opening + cash:.2f} "
                    f"but the export states {row.stated_balance:.2f}"
                )
                break
    return problems
