"""F-013.1 — sustainability_results.csv and lifestyle_results.csv (SPEC §13–§15; F-013 brief §2)."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

from sbretire.metrics import SuccessMetrics
from sbretire.optimization import BudgetResult, ReturnResult
from sbretire.reporting import (
    LIFESTYLE_COLUMNS,
    SUSTAINABILITY_COLUMNS,
    write_lifestyle_results_csv,
    write_sustainability_results_csv,
)

NUMBER = re.compile(r"-?\d+(\.\d+)?")


def _records(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
    raw = path.read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n")
    text = raw.decode("utf-8")
    assert text.isascii()
    lines = text.splitlines()
    assert tuple(lines[0].split(",")) == columns
    return list(csv.DictReader(lines))


def test_lifestyle_results_csv(tmp_path: Path) -> None:
    results = [
        BudgetResult(0.9, 10_458.6934, 125_504.3208, 0.95010, 0.000689, 0.0001, 1.0, True, 27, ""),
        BudgetResult(
            0.99, None, None, None, None, 0.62, 1.0, False, 27, "infeasible: only 3 of 2,000, paths"
        ),
    ]
    path = write_lifestyle_results_csv(results, tmp_path / "out" / "lifestyle_results.csv")
    feasible, infeasible = _records(path, LIFESTYLE_COLUMNS)
    assert feasible["target_probability"] == "0.900000"
    assert feasible["maximum_monthly_budget_today"] == "10458.69"  # floored to 0.01, never above B*
    assert feasible["maximum_annual_budget_today"] == "125504.32"
    assert float(feasible["maximum_monthly_budget_today"]) <= 10_458.6934
    assert feasible["estimated_success_probability"] == "0.950100"
    assert feasible["standard_error"] == "0.000689"
    assert feasible["unresolved_fraction"] == "0.000100"
    assert feasible["budget_tolerance"] == "1.00"
    assert (feasible["converged"], feasible["iterations"], feasible["note"]) == ("true", "27", "")
    for name in (
        "maximum_monthly_budget_today",
        "maximum_annual_budget_today",
        "estimated_success_probability",
    ):
        assert infeasible[name] == ""
    assert infeasible["converged"] == "false"
    assert (
        infeasible["note"] == "infeasible: only 3 of 2,000, paths"
    )  # quoted by the csv module, read back intact
    for record in (feasible,):
        for name in (
            "target_probability",
            "maximum_monthly_budget_today",
            "unresolved_fraction",
            "iterations",
        ):
            assert NUMBER.fullmatch(record[name])


def test_sustainability_results_csv(tmp_path: Path) -> None:
    metrics = SuccessMetrics(
        n_paths=1_000,
        n_successful=900,
        n_failed=60,
        n_unresolved=40,
        n_completed=960,
        conservative_success_rate=0.9,
        conservative_standard_error=math.sqrt(0.9 * 0.1 / 1_000),
        completed_success_rate=0.9375,
        completed_standard_error=math.sqrt(0.9375 * 0.0625 / 960),
        unresolved_share=0.04,
    )
    returns = [
        ReturnResult(7_000.0, 0.9, -0.0550973, 0.9501, 0.0007, 0.04, 0.0001, True, 16, ""),
        ReturnResult(7_000.0, 0.99, None, None, None, 0.04, 0.0001, False, 16, "no solution within bounds"),
    ]
    path = write_sustainability_results_csv(metrics, 0.04, returns, tmp_path / "sustainability_results.csv")
    solved, unsolved = _records(path, SUSTAINABILITY_COLUMNS)
    for record, target in ((solved, "0.900000"), (unsolved, "0.990000")):
        assert record["monthly_budget_today"] == "7000.00"
        assert record["annual_return"] == "0.040000"
        assert record["target_probability"] == target
        assert record["estimated_success_probability"] == "0.937500"  # completed-path rate
        assert record["conservative_success_probability"] == "0.900000"
        assert record["standard_error"] == f"{math.sqrt(0.09 / 1_000):.6f}"
        assert record["unresolved_fraction"] == "0.040000"
    assert solved["required_annual_return"] == "-0.055097"  # ceiled to 1e-6, never below r*
    assert float(solved["required_annual_return"]) >= -0.0550973
    assert (solved["return_tolerance"], solved["converged"], solved["iterations"]) == (
        "0.000100",
        "true",
        "16",
    )
    assert unsolved["required_annual_return"] == ""
    assert (unsolved["converged"], unsolved["note"]) == ("false", "no solution within bounds")
