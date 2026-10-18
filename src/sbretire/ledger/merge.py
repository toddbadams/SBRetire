"""Monthly export folders and the merged ledger (F-024; portfolio-data §2–§3)."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Final

_MONTHS: Final = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
_FOLDER: Final = re.compile(r"(?P<month>[a-z]{3})-(?P<year>\d{2})")


def month_folders(root: Path) -> list[tuple[date, Path]]:
    """Every ``<mon>-<yy>`` folder under ``root`` (``oct-26`` → 2026-10-01), oldest first; others ignored."""
    found = []
    for path in root.iterdir():
        match = _FOLDER.fullmatch(path.name)
        if path.is_dir() and match and match["month"] in _MONTHS:
            found.append((date(2000 + int(match["year"]), _MONTHS.index(match["month"]) + 1, 1), path))
    return sorted(found)
