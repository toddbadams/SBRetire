"""``ledger.csv`` and the import summary printed by ``sbretire portfolio import`` (F-024; brief §2 #11)."""

from __future__ import annotations

import csv
import dataclasses
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.merge import Export
from sbretire.ledger.model import LEDGER_COLUMNS, LedgerRow
from sbretire.ledger.reconcile import reconcile_cash


def write_ledger_csv(rows: Sequence[LedgerRow], path: Path) -> None:
    """UTF-8, LF line ends, one row per ledger leg in ``LEDGER_COLUMNS`` order; ``None`` written empty."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(LEDGER_COLUMNS)
        for row in rows:
            values = dataclasses.astuple(row)
            writer.writerow("" if value is None else value for value in values)


def reconciliation_problems(exports: Sequence[Export]) -> list[str]:
    """Every export's first break against its own stated running balances (each file is checked alone)."""
    return [problem for export in exports for problem in reconcile_cash(export.rows)]


def format_account_summary(
    account: AccountConfig, rows: Sequence[LedgerRow], exports: Sequence[Export]
) -> str:
    """Rows, date range, counts by type, external flows in and out, and the reconciliation result."""
    facts = (account.name, account.provider, account.owner, account.wrapper, account.currency)
    head = f"{account.id} ({', '.join(facts)})"
    if not rows:
        return f"{head}: 0 rows"
    dates = [row.date for row in rows]
    counts = Counter(row.type for row in rows)
    external = [row.cash_change for row in rows if row.flow == "external"]
    inflow = sum(value for value in external if value > 0)
    outflow = -sum(value for value in external if value < 0)
    lines = [
        f"{head}: {len(rows)} rows, {min(dates).isoformat()} to {max(dates).isoformat()}",
        "  types: " + ", ".join(f"{kind} {counts[kind]}" for kind in sorted(counts)),
        f"  external flows: in {inflow:,.2f}, out {outflow:,.2f} {account.currency}",
        "  reconciliation: " + _reconciliation(exports),
    ]
    return "\n".join(lines)


def _reconciliation(exports: Sequence[Export]) -> str:
    stated = [export for export in exports if any(row.stated_balance is not None for row in export.rows)]
    if not stated:
        return "no running balance in the export"
    problems = reconciliation_problems(stated)
    if problems:
        return "FAILED " + "; ".join(problems)
    balances = sum(row.stated_balance is not None for export in stated for row in export.rows)
    files = "1 file" if len(stated) == 1 else f"{len(stated)} files"
    return f"ok ({files}, {balances} stated balances)"
