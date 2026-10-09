"""Calendar months relative to the As-Of month (simulation-conventions §1).

Month 0 is the As-Of month; every date in a scenario maps to a whole month index so income dates, deaths and
reporting years share one clock.
"""

from __future__ import annotations

from datetime import date


def month_index(as_of: date, when: date) -> int:
    """Number of calendar months from the As-Of month to ``when``'s month (negative if earlier)."""
    return (when.year - as_of.year) * 12 + (when.month - as_of.month)


def month_start(as_of: date, index: int) -> date:
    """First day of the month ``index`` months after the As-Of month (inverse of :func:`month_index`)."""
    total = as_of.year * 12 + (as_of.month - 1) + index
    return date(total // 12, total % 12 + 1, 1)
