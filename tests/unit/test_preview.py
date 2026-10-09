"""F-015 — deterministic preview (F-015 brief).

Fixture tests/fixtures/scenarios/valid_minimal.yaml: As-Of 2026-10-01, horizon 60 years (720 months);
alex born 1958-03-01 (68 at As-Of), sam born 1962-07-15 (64 at As-Of).
"""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from sbretire.config import Scenario, parse_scenario
from sbretire.preview import (
    PreviewResult,
    PreviewYear,
    death_months_from_ages,
    run_preview,
    write_preview_csv,
)

from scenario_helpers import set_at


def scenario(raw: dict[str, Any]) -> Scenario:
    return parse_scenario(raw, base_dir=Path(".")).scenario


def test_death_months_from_ages_uses_birthday_month(valid_raw: dict[str, Any]) -> None:
    months = death_months_from_ages(scenario(valid_raw), (90, 90))
    # alex 90 -> 2048-03 = (2048-2026)*12 + (3-10) = 257; sam 90 -> 2052-07 = 26*12 - 3 = 309
    assert months.shape == (2, 1)
    assert months[:, 0].tolist() == [257, 309]
    assert death_months_from_ages(scenario(valid_raw), (69, 65))[:, 0].tolist() == [5, 9]


def test_death_months_from_ages_validates_range(valid_raw: dict[str, Any]) -> None:
    s = scenario(valid_raw)
    for ages in ((68, 90), (90, 64), (0, 90), (-5, 90)):
        with pytest.raises(ValueError, match="current age"):
            death_months_from_ages(s, ages)
    # beyond the horizon: alex 130 -> 2088-03 = 737 >= 720 (alive at the horizon)
    assert death_months_from_ages(s, (130, 130))[0, 0] >= 720


def preview_raw(raw: dict[str, Any], *, inflation: float = 0.0, annual_return: float = 0.0) -> dict[str, Any]:
    raw = set_at(raw, "inflation.log_mean", math.log1p(inflation))
    return set_at(raw, "portfolio.annual_return", annual_return)


def by_year(result: PreviewResult) -> dict[int, PreviewYear]:
    return {row.year: row for row in result.rows}


def test_run_preview_aggregates_calendar_years(valid_raw: dict[str, Any]) -> None:
    result = run_preview(scenario(preview_raw(valid_raw)), (130, 130))
    rows = by_year(result)
    first = rows[2026]  # Oct-Dec: annuity 3 x 500; spending 3 x 3000
    assert (first.months, first.age_person_1, first.age_person_2) == (3, 68, 64)
    assert (first.income, first.spending, first.net_withdrawal) == (1500.0, 9000.0, 7500.0)
    assert (first.investment_return, first.balance_end, first.price_index) == (0.0, 492_500.0, 1.0)
    second = rows[2027]  # pension starts Jan 2027: income 12 x (1000 + 500); spending 12 x 3000
    assert (second.months, second.income, second.spending) == (12, 18_000.0, 36_000.0)
    assert second.balance_end == 492_500.0 - 18_000.0
    assert result.rows[0].year == 2026


def test_run_preview_reports_depletion(valid_raw: dict[str, Any]) -> None:
    result = run_preview(scenario(preview_raw(valid_raw)), (130, 130))
    # same path as tests/integration/test_cash_flows_end_to_end.py path 2
    assert result.depletion_month == 289
    assert result.depletion_date == date(2050, 11, 1)
    assert result.shortfall == 2000.0
    assert result.rows[-1].year == 2050
    assert result.rows[-1].months == 11  # Jan..Nov 2050
    assert result.rows[-1].balance_end == 0.0
    assert result.final_balance == 0.0
    assert result.household_end_date is None


def test_preview_uses_monthly_compounding(valid_raw: dict[str, Any], tmp_path: Path) -> None:
    """Index compounds monthly from the As-Of month at the median rate (simulation-conventions §5)."""
    result = run_preview(scenario(preview_raw(valid_raw, inflation=0.02)), (130, 130))
    rows = by_year(result)
    # last simulated month of each calendar year: Dec 2026 = month 2, Dec 2027 = 14, Dec 2028 = 26
    assert rows[2026].price_index == pytest.approx(1.02 ** (2 / 12), rel=1e-12)
    assert rows[2027].price_index == pytest.approx(1.02 ** (14 / 12), rel=1e-12)
    assert rows[2028].price_index == pytest.approx(1.02 ** (26 / 12), rel=1e-12)
    for row in result.rows:
        assert row.balance_end_today == pytest.approx(row.balance_end / row.price_index)
    # Spending in Oct-Dec 2026: 3000 x 1.02^(t/12) for t = 0, 1, 2
    assert rows[2026].spending == pytest.approx(sum(3000 * 1.02 ** (t / 12) for t in range(3)), rel=1e-12)
    write_preview_csv(result, tmp_path / "preview.csv")
    lines = (tmp_path / "preview.csv").read_text(encoding="utf-8").splitlines()
    assert lines[2].endswith(f",{1.02 ** (14 / 12):.6f}")


def test_run_preview_investment_return_matches_closed_form(valid_raw: dict[str, Any]) -> None:
    raw = set_at(preview_raw(valid_raw, annual_return=0.05), "budget.monthly_amount_today", 0)
    raw = set_at(raw, "income", [])
    result = run_preview(scenario(raw), (130, 130))
    rows = by_year(result)
    r_m = 1.05 ** (1 / 12) - 1
    start = 500_000.0
    assert rows[2026].investment_return == pytest.approx(start * ((1 + r_m) ** 3 - 1))
    assert rows[2027].investment_return == pytest.approx(start * (1 + r_m) ** 3 * 0.05)
    assert rows[2027].balance_end == pytest.approx(start * 1.05 ** (15 / 12))


def test_run_preview_household_end_and_ages(valid_raw: dict[str, Any]) -> None:
    # alex 70 -> dead from 2028-03 (month 17); sam 66 -> dead from 2028-07 (month 21)
    raw = set_at(preview_raw(valid_raw), "portfolio.starting_balance", 5_000_000)
    result = run_preview(scenario(raw), (70, 66))
    rows = by_year(result)
    assert result.household_end_date == date(2028, 7, 1)
    assert result.depletion_month is None and result.depletion_date is None
    assert result.rows[-1].year == 2028
    assert rows[2028].months == 6  # Jan..Jun 2028
    assert (rows[2027].age_person_1, rows[2027].age_person_2) == (69, 65)
    assert (rows[2028].age_person_1, rows[2028].age_person_2) == (None, 66)
