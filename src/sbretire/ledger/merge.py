"""Monthly export folders and the merged ledger (F-024; portfolio-data §2–§3)."""

from __future__ import annotations

import dataclasses
import fnmatch
import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

from sbretire.ledger.accounts import AccountConfig, Provider
from sbretire.ledger.model import LedgerRow
from sbretire.ledger.parsers import hl, ii, schwab, vanguard

_MONTHS: Final = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
_FOLDER: Final = re.compile(r"(?P<month>[a-z]{3})-(?P<year>\d{2})")
PARSERS: Final[dict[Provider, Callable[[Path, AccountConfig], list[LedgerRow]]]] = {
    "schwab": schwab.parse,
    "hl": hl.parse,
    "vanguard": vanguard.parse,
    "ii": ii.parse,
}


@dataclass(frozen=True)
class Export:
    """One parsed transaction file for one account; ``source_file`` on its rows is ``<folder>/<file>``."""

    month: date
    account: AccountConfig
    rows: list[LedgerRow]


def month_folders(root: Path) -> list[tuple[date, Path]]:
    """Every ``<mon>-<yy>`` folder under ``root`` (``oct-26`` → 2026-10-01), oldest first; others ignored."""
    found = []
    for path in root.iterdir():
        match = _FOLDER.fullmatch(path.name)
        if path.is_dir() and match and match["month"] in _MONTHS:
            found.append((date(2000 + int(match["year"]), _MONTHS.index(match["month"]) + 1, 1), path))
    return sorted(found)


def read_exports(root: Path, accounts: Sequence[AccountConfig]) -> list[Export]:
    """Parse every account's transaction files in every month folder, oldest folder first.

    Raises ``UnknownTransaction`` (naming ``<folder>/<file>`` and the row) on the first unclassified row.
    """
    exports = []
    for month, folder in month_folders(root):
        names = sorted(path.name for path in folder.iterdir() if path.is_file())
        for account in accounts:
            matched = [name for name in names if any(fnmatch.fnmatch(name, p) for p in account.transactions)]
            for name in matched:
                rows = PARSERS[account.provider](folder / name, account)
                source = f"{folder.name}/{name}"
                rows = [dataclasses.replace(row, source_file=source) for row in rows]
                exports.append(Export(month, account, rows))
    return exports


def merge_exports(exports: Sequence[Export]) -> list[LedgerRow]:
    """The union of the exports with overlapping months de-duplicated (portfolio-data §3).

    Rows match on ``LedgerRow.fingerprint``. The newest folder's rows are kept; an older folder adds a row
    only where it holds more copies of that fingerprint than the newer folders (so true repeats within one
    file survive). Sorted by account, then date, then position in the source file.
    """
    kept: list[LedgerRow] = []
    taken: Counter[tuple[object, ...]] = Counter()
    for month in sorted({export.month for export in exports}, reverse=True):
        folder_rows = [row for export in exports if export.month == month for row in export.rows]
        here = Counter(row.fingerprint() for row in folder_rows)
        added: Counter[tuple[object, ...]] = Counter()
        for row in folder_rows:
            key = row.fingerprint()
            if added[key] < here[key] - taken[key]:
                added[key] += 1
                kept.append(row)
        taken = taken | here
    return sorted(kept, key=lambda r: (r.account, r.date, r.source_file, r.sequence))


def build_ledger(root: Path, accounts: Sequence[AccountConfig]) -> list[LedgerRow]:
    """Every account's transactions from every month folder under ``root``, merged and de-duplicated."""
    return merge_exports(read_exports(root, accounts))
