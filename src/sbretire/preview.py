"""Deterministic preview run (F-015): one Path with chosen death ages and constant inflation.

A **deterministic illustration**, never a sustainability estimate (SPEC §14).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
from numpy.typing import NDArray

from sbretire.cash_flows import ScenarioCashFlows
from sbretire.config import Scenario
from sbretire.inflation import AnnualStepPriceIndex
from sbretire.portfolio import BoolArray, FloatArray, monthly_return_rate
from sbretire.simulation import simulate_paths
from sbretire.timeline import month_index, month_start


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


@dataclass(frozen=True)
class _MonthRecord:
    month: int
    income: float
    spending: float
    investment_return: float  # opening balance x monthly rate
    balance: float  # closing
    alive: tuple[bool, bool]  # at the month's start
    price_index: float


class _RecordingCashFlows:
    """Wraps the Scenario cash flows to remember what the engine asked for in the latest month."""

    def __init__(self, inner: ScenarioCashFlows) -> None:
        self._inner = inner
        self.income_now = 0.0
        self.spending_now = 0.0

    def income(self, month: int, alive: BoolArray) -> FloatArray:
        result = self._inner.income(month, alive)
        self.income_now = float(result[0])
        return result

    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        result = self._inner.spending(month, alive)
        self.spending_now = float(result[0])
        return result


def run_preview(scenario: Scenario, death_ages: tuple[int, int]) -> PreviewResult:
    """Simulate one deterministic Path and aggregate it into calendar-year rows (F-015 brief §2).

    Death Months come from ``death_ages``; inflation is constant at ``inflation.annual_mean`` stepping on
    As-Of anniversaries; the return is the configured fixed ``portfolio.annual_return``. Money is nominal GBP
    except ``balance_end_today`` (deflated by the index at the year's last simulated month).
    """
    as_of = scenario.model.as_of_date
    index = AnnualStepPriceIndex(1, scenario.inflation.annual_mean)
    flows = _RecordingCashFlows(ScenarioCashFlows(scenario, index, n_paths=1))
    rate = monthly_return_rate(scenario.portfolio.annual_return)
    records: list[_MonthRecord] = []
    opening = [scenario.portfolio.starting_balance]

    def observe(month: int, balance: FloatArray, alive: BoolArray, active: BoolArray) -> None:
        records.append(
            _MonthRecord(
                month=month,
                income=flows.income_now,
                spending=flows.spending_now,
                investment_return=opening[0] * rate,
                balance=float(balance[0]),
                alive=(bool(alive[0, 0]), bool(alive[1, 0])),
                price_index=float(index.level(month)[0]),
            )
        )
        opening[0] = float(balance[0])

    out = simulate_paths(
        starting_balance=scenario.portfolio.starting_balance,
        annual_return=scenario.portfolio.annual_return,
        death_month=death_months_from_ages(scenario, death_ages),
        horizon_months=scenario.model.horizon_years * 12,
        cash_flows=flows,
        observer=observe,
    )

    rows = tuple(_year_row(scenario, year, months) for year, months in _by_calendar_year(as_of, records))
    depletion = int(out.depletion_month[0])
    household_end = int(out.household_end_month[0])
    final_balance = float(out.final_balance[0])
    last_index = records[-1].price_index if records else 1.0
    return PreviewResult(
        rows=rows,
        depletion_month=depletion if depletion >= 0 else None,
        depletion_date=month_start(as_of, depletion) if depletion >= 0 else None,
        shortfall=float(out.shortfall[0]),
        household_end_date=month_start(as_of, household_end) if household_end >= 0 else None,
        final_balance=final_balance,
        final_balance_today=final_balance / last_index,
    )


def _by_calendar_year(as_of: date, records: list[_MonthRecord]) -> list[tuple[int, list[_MonthRecord]]]:
    groups: dict[int, list[_MonthRecord]] = {}
    for record in records:
        groups.setdefault(month_start(as_of, record.month).year, []).append(record)
    return sorted(groups.items())


def _year_row(scenario: Scenario, year: int, months: list[_MonthRecord]) -> PreviewYear:
    last = months[-1]
    ages = [
        year - person.date_of_birth.year if alive else None
        for person, alive in zip(scenario.people, last.alive, strict=True)
    ]
    income = sum(m.income for m in months)
    spending = sum(m.spending for m in months)
    return PreviewYear(
        year=year,
        months=len(months),
        age_person_1=ages[0],
        age_person_2=ages[1],
        income=income,
        spending=spending,
        investment_return=sum(m.investment_return for m in months),
        net_withdrawal=spending - income,
        balance_end=last.balance,
        balance_end_today=last.balance / last.price_index,
        price_index=last.price_index,
    )
