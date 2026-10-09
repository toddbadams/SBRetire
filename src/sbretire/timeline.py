"""Calendar months relative to the As-Of month (simulation-conventions §1).

Month 0 is the As-Of month; every date in a scenario maps to a whole month index so income dates, deaths and
reporting years share one clock.
"""

from __future__ import annotations

from datetime import date


def month_index(as_of: date, when: date) -> int:
    """Number of calendar months from the As-Of month to ``when``'s month (negative if earlier)."""
    return (when.year - as_of.year) * 12 + (when.month - as_of.month)
