"""F-003.1 — month indexing from the As-Of month (F-003 brief §2 #8)."""

from __future__ import annotations

from datetime import date

import pytest

from sbretire.timeline import month_index, month_start

AS_OF = date(2026, 10, 1)


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        (date(2026, 10, 1), 0),
        (date(2026, 11, 1), 1),
        (date(2026, 12, 1), 2),
        (date(2027, 1, 1), 3),
        (date(2027, 10, 1), 12),
        (date(2036, 10, 1), 120),
        (date(2026, 9, 1), -1),
        (date(2024, 4, 1), -30),
    ],
)
def test_month_index_counts_calendar_months(when: date, expected: int) -> None:
    assert month_index(AS_OF, when) == expected


@pytest.mark.parametrize("index", [-30, -1, 0, 1, 2, 3, 12, 289, 1199])
def test_month_start_inverts_month_index(index: int) -> None:
    assert month_index(AS_OF, month_start(AS_OF, index)) == index
    assert month_start(AS_OF, index).day == 1


def test_month_start_examples() -> None:
    assert month_start(AS_OF, 289) == date(2050, 11, 1)
    assert month_start(AS_OF, 3) == date(2027, 1, 1)
