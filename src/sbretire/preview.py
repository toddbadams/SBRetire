"""Deterministic preview run (F-015): one Path with chosen death ages and constant inflation.

A **deterministic illustration**, never a sustainability estimate (SPEC §14).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
from numpy.typing import NDArray

from sbretire.config import Scenario
from sbretire.timeline import month_index


def death_months_from_ages(scenario: Scenario, ages: tuple[int, int]) -> NDArray[np.int64]:
    """Death Months, shape (2, 1), from death ages in ``scenario.people`` order.

    Each person is dead from the start of the month of that birthday. An age at or below their age at the
    As-Of month (Death Month ≤ 0) is rejected; an age beyond the horizon leaves them alive at the horizon.
    """
    as_of = scenario.model.as_of_date
    months = []
    for person, age in zip(scenario.people, ages, strict=True):
        birthday = date(person.date_of_birth.year + age, person.date_of_birth.month, 1) if age > 0 else as_of
        month = month_index(as_of, birthday)
        if age <= 0 or month <= 0:
            raise ValueError(f"death age for {person.id} must be greater than their current age (got {age})")
        months.append(month)
    return np.array(months, dtype=np.int64).reshape(2, 1)


@dataclass(frozen=True)
class PreviewYear:
    year: int
    months: int
    age_person_1: int | None
    age_person_2: int | None
    income: float
    spending: float
    investment_return: float
    net_withdrawal: float
    balance_end: float
    balance_end_today: float
    price_index: float


@dataclass(frozen=True)
class PreviewResult:
    rows: tuple[PreviewYear, ...]
    depletion_month: int | None
    depletion_date: date | None
    shortfall: float
    household_end_date: date | None
    final_balance: float
    final_balance_today: float


def run_preview(scenario: Scenario, death_ages: tuple[int, int]) -> PreviewResult:
    raise NotImplementedError
