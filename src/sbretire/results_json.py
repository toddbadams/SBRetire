"""``results.json``: every result of one run in one JSON document (F-021).

Built from the same objects as the CSVs and ``results_guide.md`` (the :class:`GuideContext` and the annual
rows), so it can never disagree with them. Budgets are floored to 0.01 and required returns ceiled to 1e-6
exactly as in the CSVs (B-011.1); everything else is unrounded, with ``null`` where a statistic has no value.
The structure is fixed by ``schemas/results.schema.json`` (``schema_version`` :data:`SCHEMA_VERSION`). The
seed is a string because generated seeds are 128-bit and JavaScript numbers cannot hold them exactly.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

from sbretire import __version__
from sbretire.optimization import BudgetResult, ReturnResult
from sbretire.reporting import ANNUAL_COLUMNS, AnnualRow, money_down, return_up
from sbretire.results_guide import COLUMN_GUIDE, GuideContext
from sbretire.timeline import month_start

SCHEMA_VERSION: Final = "1.0"


def _budget(result: BudgetResult) -> dict[str, Any]:
    return {
        "target_probability": result.target_probability,
        "maximum_monthly_budget_today": money_down(result.maximum_monthly_budget_today),
        "maximum_annual_budget_today": money_down(result.maximum_annual_budget_today),
        "estimated_success_probability": result.estimated_success_probability,
        "standard_error": result.standard_error,
        "unresolved_fraction": result.unresolved_fraction,
        "budget_tolerance": result.budget_tolerance,
        "converged": result.converged,
        "iterations": result.iterations,
        "note": result.note,
    }


def _return(result: ReturnResult) -> dict[str, Any]:
    return {
        "target_probability": result.target_probability,
        "monthly_budget_today": result.monthly_budget_today,
        "required_annual_return": return_up(result.required_annual_return),
        "estimated_success_probability": result.estimated_success_probability,
        "standard_error": result.standard_error,
        "unresolved_fraction": result.unresolved_fraction,
        "return_tolerance": result.return_tolerance,
        "converged": result.converged,
        "iterations": result.iterations,
        "note": result.note,
    }


def build_results(
    context: GuideContext,
    annual: Sequence[AnnualRow],
    *,
    name: str | None,
    config_sha256: str,
    created_at: str,
) -> dict[str, Any]:
    """The run as a JSON-ready dict (schema_version :data:`SCHEMA_VERSION`).

    ``name`` is the ``--name`` of a named run (None otherwise); ``created_at`` an ISO-8601 timestamp.
    """
    s = context.scenario
    model, budget = s.model, s.budget
    last = month_start(model.as_of_date, model.horizon_years * 12 - 1)
    reserve = context.reserve_metrics
    return {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "name": name,
            "created_at": created_at,
            "sbretire_version": __version__,
            "config_file": context.config.name,
            "config_sha256": config_sha256,
            "seed": {"value": str(context.seed.value), "source": context.seed.source},
            "as_of_date": model.as_of_date.isoformat(),
            "horizon_years": model.horizon_years,
            "last_month": f"{last:%Y-%m}",
            "paths": context.metrics.n_paths,
            "monthly_budget_today": budget.monthly_amount_today,
            "annual_return": s.portfolio.annual_return,
            "options": {
                "end_reserve_months": budget.end_reserve_months,
                "spend_at_least_income": budget.spend_at_least_income,
            },
        },
        "people": [{"id": person.id, "name": person.name} for person in s.people],
        "inputs": [dataclasses.asdict(row) for row in context.input_rows],
        "summary": dataclasses.asdict(context.metrics),
        "reserve_summary": None if reserve is None else dataclasses.asdict(reserve),
        "budgets": [_budget(result) for result in context.budgets],
        "reserve_budgets": [_budget(result) for result in context.reserve_budgets],
        "returns": [_return(result) for result in context.returns],
        "annual": [{column: getattr(row, column) for column in ANNUAL_COLUMNS} for row in annual],
        "columns": {
            file_name: {column: {"unit": unit, "meaning": text} for column, (unit, text) in guide.items()}
            for file_name, guide in COLUMN_GUIDE.items()
        },
    }


def write_results_json(results: dict[str, Any], path: Path) -> Path:
    """Write ``results.json``: UTF-8, LF, 2-space indent, strict JSON (no NaN or infinity)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.write_bytes(text.encode("utf-8"))
    return path
