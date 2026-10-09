"""Calendar months relative to the As-Of month."""

from __future__ import annotations

from datetime import date


def month_index(as_of: date, when: date) -> int:
    raise NotImplementedError
