"""F-018.1 — results_guide.md content (F-018 brief §2 #1–#7).

A seeded 300-path run of tests/fixtures/scenarios/valid_minimal.yaml (seed 21, budget 3,000/month, return 4 %,
survivor factors 0.7 household / 0.65 for sam), plus a synthetic context with an infeasible budget row and a
no-solution return row.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from sbretire.inputs_report import INPUT_COLUMNS, scenario_input_rows
from sbretire.monte_carlo import run_monte_carlo
from sbretire.optimization import (
    BudgetResult,
    ReturnResult,
    maximum_sustainable_budgets,
    path_budget_thresholds,
    path_return_thresholds,
    required_returns,
)
from sbretire.reporting import ANNUAL_COLUMNS, LIFESTYLE_COLUMNS, SUSTAINABILITY_COLUMNS, round_return_up
from sbretire.results_guide import COLUMN_GUIDE, GuideContext, results_guide_markdown

from annual_fixtures import seeded

SECTIONS = (
    "## Your results",
    "## How the figures are calculated",
    "## Assumptions",
    "## Limitations",
    "## Columns",
    "## Inputs",
)


def _context() -> GuideContext:
    scenario, inputs = seeded(300, 3_000)
    targets = scenario.model.confidence_levels
    return GuideContext(
        config=Path("config/example.yaml"),
        scenario=scenario,
        seed=inputs.seed,
        input_rows=scenario_input_rows(scenario, inputs.seed),
        metrics=run_monte_carlo(scenario, inputs).metrics,
        budgets=maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), targets),
        returns=required_returns(path_return_thresholds(scenario, inputs), targets),
    )


def _section(text: str, heading: str) -> str:
    """From ``heading`` to the next heading of the same or a higher level (subsections included)."""
    start = text.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    following = re.search(rf"^#{{1,{level}}} ", text[start + level :], re.M)
    return text[start : start + level + following.start()] if following else text[start:]


def test_column_guide_matches_csv_columns() -> None:
    expected = {
        "inputs.csv": INPUT_COLUMNS,
        "annual_results.csv": ANNUAL_COLUMNS,
        "sustainability_results.csv": SUSTAINABILITY_COLUMNS,
        "lifestyle_results.csv": LIFESTYLE_COLUMNS,
    }
    assert set(COLUMN_GUIDE) == set(expected)
    for file_name, columns in expected.items():
        assert tuple(COLUMN_GUIDE[file_name]) == columns, file_name
        for column, (unit, meaning) in COLUMN_GUIDE[file_name].items():
            assert unit.strip() and meaning.strip(), (file_name, column)


def test_results_guide_reports_run_figures() -> None:
    context = _context()
    text = results_guide_markdown(context)
    results = _section(text, "## Your results")
    m = context.metrics
    assert f"{m.n_paths:,} simulated futures" in results
    assert f"seed {context.seed.value}" in results
    for count in (m.n_successful, m.n_failed, m.n_unresolved):
        assert f"{count:,}" in results
    assert f"{m.conservative_success_rate:.2%}" in results
    assert f"{m.conservative_standard_error:.3%}" in results
    assert m.completed_success_rate is not None
    assert f"{m.completed_success_rate:.2%}" in results
    for budget in context.budgets:
        assert budget.maximum_monthly_budget_today is not None
        assert f"{budget.target_probability:.0%}" in results
        assert f"{math.floor(budget.maximum_monthly_budget_today):,}" in results
    for found in context.returns:
        assert found.required_annual_return is not None
        assert f"{round_return_up(found.required_annual_return):.2%}" in results

    infeasible = BudgetResult(
        0.99, None, None, None, None, 0.4, 1.0, False, 7, "infeasible: only 6 of 10 paths"
    )
    unreachable = ReturnResult(
        3_000.0, 0.99, None, None, None, 0.4, 0.0001, False, 9, "no solution within bounds"
    )
    synthetic = GuideContext(
        context.config,
        context.scenario,
        context.seed,
        context.input_rows,
        context.metrics,
        [infeasible],
        [unreachable],
    )
    results = _section(results_guide_markdown(synthetic), "## Your results")
    assert "infeasible: only 6 of 10 paths" in results
    assert "no solution within bounds" in results


def test_results_guide_calculations_use_scenario_values() -> None:
    context = _context()
    scenario, m = context.scenario, context.metrics
    calculations = _section(results_guide_markdown(context), "## How the figures are calculated")
    monthly = (1 + scenario.portfolio.annual_return) ** (1 / 12) - 1
    assert f"{monthly:.4%}" in calculations
    assert "3,000" in calculations
    assert "0.7" in calculations and "0.65" in calculations  # household and sam's own survivor factor
    i = scenario.inflation
    parameters = (i.log_mean, i.ar1_coefficient, i.innovation_sd, i.initial_rate)
    for value in parameters:
        assert repr(value) in calculations
    assert f"{m.n_successful:,} / {m.n_paths:,}" in calculations
    assert f"{m.n_successful:,} / {m.n_completed:,}" in calculations
    assert f"{m.conservative_standard_error:.3%}" in calculations
    assert f"{context.budgets[0].iterations}" in calculations
    assert f"{context.returns[0].iterations}" in calculations


def test_results_guide_sections_columns_and_inputs() -> None:
    context = _context()
    text = results_guide_markdown(context)
    assert text.startswith("# ")
    positions = [text.index(heading + "\n") for heading in SECTIONS]
    assert positions == sorted(positions)
    columns = _section(text, "## Columns")
    for file_name, guide in COLUMN_GUIDE.items():
        table = _section(columns, f"### `{file_name}`")
        for column in guide:
            assert f"`{column}`" in table, (file_name, column)
    inputs = text[text.index("## Inputs") :]
    for row in context.input_rows:
        assert f"`{row.item}`" in inputs, row.item
        assert row.value in inputs, row.item
