"""F-021.1 — results.json: one document per run, validated against schemas/results.schema.json.

Seeded 300-path runs of tests/fixtures/scenarios/valid_minimal.yaml (seed 21, budget 3,000/month), with and
without a 12-month End-of-Life Reserve.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import math
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from sbretire.inputs_report import scenario_input_rows
from sbretire.monte_carlo import run_monte_carlo
from sbretire.optimization import (
    maximum_sustainable_budgets,
    path_budget_thresholds,
    path_return_thresholds,
    required_returns,
)
from sbretire.reporting import ANNUAL_COLUMNS, annual_results
from sbretire.results_guide import COLUMN_GUIDE, GuideContext
from sbretire.results_json import SCHEMA_VERSION, build_results

from annual_fixtures import ROOT, seeded

SCHEMA = json.loads((ROOT / "schemas" / "results.schema.json").read_text(encoding="utf-8"))


def _results(reserve_months: int = 0) -> tuple[dict[str, Any], GuideContext, list[Any]]:
    scenario, inputs = seeded(300, 3_000)
    if reserve_months:
        budget = scenario.budget.model_copy(update={"end_reserve_months": reserve_months})
        scenario = scenario.model_copy(update={"budget": budget})
    targets = scenario.model.confidence_levels
    context = GuideContext(
        config=Path("config/example.yaml"),
        scenario=scenario,
        seed=inputs.seed,
        input_rows=scenario_input_rows(scenario, inputs.seed),
        metrics=run_monte_carlo(scenario, inputs).metrics,
        budgets=maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), targets),
        returns=required_returns(path_return_thresholds(scenario, inputs), targets),
    )
    if reserve_months:
        context = dataclasses.replace(
            context,
            reserve_metrics=run_monte_carlo(scenario, inputs, end_reserve_months=reserve_months).metrics,
            reserve_budgets=maximum_sustainable_budgets(
                path_budget_thresholds(scenario, inputs, end_reserve_months=reserve_months), targets
            ),
        )
    annual = annual_results(scenario, inputs)
    built = build_results(
        context, annual, name="test-run", config_sha256="0" * 64, created_at="2026-10-09T12:00:00+00:00"
    )
    return built, context, annual


def test_results_json_validates_against_schema() -> None:
    for months in (0, 12):
        built, _, _ = _results(months)
        jsonschema.validate(built, SCHEMA)
        assert built["schema_version"] == SCHEMA_VERSION
        json.dumps(built, allow_nan=False)  # strict JSON: no NaN or infinity
    missing = copy.deepcopy(built)
    del missing["annual"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(missing, SCHEMA)
    wrong = copy.deepcopy(built)
    wrong["summary"]["n_paths"] = "300"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(wrong, SCHEMA)
    extra = copy.deepcopy(built)
    extra["budgets"][0]["surprise"] = 1
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(extra, SCHEMA)


def _floor_cents(value: float) -> float:
    return math.floor(round(value * 100, 6)) / 100


def _ceil_micro(value: float) -> float:
    return math.ceil(round(value * 1_000_000, 6)) / 1_000_000


def test_results_json_matches_run_objects() -> None:
    built, context, annual = _results(12)
    m = context.metrics
    assert built["summary"] == {
        "n_paths": m.n_paths,
        "n_successful": m.n_successful,
        "n_failed": m.n_failed,
        "n_unresolved": m.n_unresolved,
        "n_completed": m.n_completed,
        "conservative_success_rate": m.conservative_success_rate,
        "conservative_standard_error": m.conservative_standard_error,
        "completed_success_rate": m.completed_success_rate,
        "completed_standard_error": m.completed_standard_error,
        "unresolved_share": m.unresolved_share,
    }
    assert context.reserve_metrics is not None
    assert built["reserve_summary"]["n_successful"] == context.reserve_metrics.n_successful
    run = built["run"]
    assert (run["name"], run["paths"], run["seed"]) == ("test-run", 300, {"value": 21, "source": "config"})
    assert run["options"] == {"end_reserve_months": 12, "spend_at_least_income": False}
    assert run["config_file"] == "example.yaml"
    for key, results in (("budgets", context.budgets), ("reserve_budgets", context.reserve_budgets)):
        assert len(built[key]) == len(results)
        for row, result in zip(built[key], results, strict=True):
            assert result.maximum_monthly_budget_today is not None
            assert row["maximum_monthly_budget_today"] == _floor_cents(result.maximum_monthly_budget_today)
            assert row["estimated_success_probability"] == result.estimated_success_probability
            assert row["converged"] is result.converged and row["note"] == result.note
    for row, found in zip(built["returns"], context.returns, strict=True):
        assert found.required_annual_return is not None
        assert row["required_annual_return"] == _ceil_micro(found.required_annual_return)
        assert row["monthly_budget_today"] == found.monthly_budget_today
    assert [list(row) for row in built["annual"]] == [list(ANNUAL_COLUMNS)] * len(annual)
    for row, expected in zip(built["annual"], annual, strict=True):
        assert row == {column: getattr(expected, column) for column in ANNUAL_COLUMNS}
    assert built["columns"] == {
        file_name: {column: {"unit": unit, "meaning": meaning} for column, (unit, meaning) in guide.items()}
        for file_name, guide in COLUMN_GUIDE.items()
    }
    assert built["inputs"] == [dataclasses.asdict(row) for row in context.input_rows]
    assert built["people"] == [{"id": "alex", "name": "Alex"}, {"id": "sam", "name": "Sam"}]

    plain, _, _ = _results(0)
    assert plain["reserve_summary"] is None and plain["reserve_budgets"] == []
