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
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

from sbretire import __version__
from sbretire.optimization import BudgetResult, ReturnResult
from sbretire.reporting import ANNUAL_COLUMNS, AnnualRow, money_down, return_up
from sbretire.results_guide import COLUMN_GUIDE, GuideContext
from sbretire.timeline import month_start

SCHEMA_VERSION: Final = "1.0"
RUN_NAME_RULE: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
RUN_NAME_HELP: Final = "1-64 letters, digits, '-' or '_', starting with a letter or digit"
RUN_OUTPUT_FILES: Final = (
    "inputs.csv",
    "annual_results.csv",
    "sustainability_results.csv",
    "lifestyle_results.csv",
    "lifestyle_reserve_results.csv",
    "run_metadata.json",
    "results_guide.md",
    "results.json",
)
"""Every file a run can write; ``--overwrite`` removes only these from a run folder."""
RUNS_JS_PREFIX: Final = "window.SBRETIRE_RUNS = "
_WINDOWS_RESERVED: Final = frozenset(
    {"CON", "PRN", "AUX", "NUL"} | {f"{device}{n}" for device in ("COM", "LPT") for n in range(1, 10)}
)


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
    """A required-return row. The success figures are at the solved return r*, so they are named
    ``*_at_required_return``: sustainability_results.csv uses the plain names for the configured return."""
    return {
        "target_probability": result.target_probability,
        "monthly_budget_today": result.monthly_budget_today,
        "required_annual_return": return_up(result.required_annual_return),
        "success_probability_at_required_return": result.estimated_success_probability,
        "standard_error_at_required_return": result.standard_error,
        "unresolved_fraction_at_required_return": result.unresolved_fraction,
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


def check_run_name(name: str) -> str | None:
    """None when ``name`` is a valid run name (a safe folder name everywhere), else what is wrong with it."""
    if not RUN_NAME_RULE.fullmatch(name):
        return f"invalid run name {name!r}: use {RUN_NAME_HELP}"
    if name.upper() in _WINDOWS_RESERVED:
        return f"invalid run name {name!r}: it is a reserved device name on Windows"
    return None


def _index_entry(results: dict[str, Any]) -> dict[str, Any]:
    run, summary, first = results["run"], results["summary"], results["budgets"][0]
    return {
        "name": run["name"],
        "created_at": run["created_at"],
        "config_file": run["config_file"],
        "paths": run["paths"],
        "monthly_budget_today": run["monthly_budget_today"],
        "annual_return": run["annual_return"],
        "conservative_success_rate": summary["conservative_success_rate"],
        "conservative_standard_error": summary["conservative_standard_error"],
        "first_target_probability": first["target_probability"],
        "first_target_maximum_monthly_budget_today": first["maximum_monthly_budget_today"],
    }


def refresh_runs_index(runs_dir: Path) -> tuple[Path, Path]:
    """Rebuild ``index.json`` and ``runs.js`` in ``runs_dir`` from every ``<name>/results.json`` on disk.

    ``runs.js`` assigns ``window.SBRETIRE_RUNS = {schema_version, index, runs}`` so a page opened from disk
    (``file://``) can load every run with a ``<script>`` tag. Runs are listed newest first, then by name; a
    folder whose ``results.json`` is missing is skipped, and an unreadable one is skipped with a warning.
    """
    runs: dict[str, dict[str, Any]] = {}
    entries: list[dict[str, Any]] = []
    for folder in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
        source = folder / "results.json"
        if not source.is_file():
            continue
        try:
            results = json.loads(source.read_text(encoding="utf-8"))
            entry = _index_entry(results)
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            print(f"warning: skipping {source} in the runs index: {exc}", file=sys.stderr)
            continue
        runs[folder.name] = results
        entries.append({**entry, "name": folder.name})  # the folder name is the run's name
    index = sorted(sorted(entries, key=lambda e: e["name"]), key=lambda e: e["created_at"], reverse=True)
    index_path = runs_dir / "index.json"
    write_results_json({"schema_version": SCHEMA_VERSION, "runs": index}, index_path)
    payload = {"schema_version": SCHEMA_VERSION, "index": index, "runs": runs}
    script = RUNS_JS_PREFIX + json.dumps(payload, ensure_ascii=False, allow_nan=False) + ";\n"
    js_path = runs_dir / "runs.js"
    js_path.write_bytes(script.encode("utf-8"))
    return index_path, js_path
