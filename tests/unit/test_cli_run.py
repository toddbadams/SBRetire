"""F-009.3 — ``sbretire run``: Monte Carlo summary and run_metadata.json (F-009 brief §2 #5–#6).

Fixture tests/fixtures/scenarios/valid_minimal.yaml: 1,000 paths, 60-year horizon, seed 7, budget 3,000/month,
with the real ONS mortality and CPI files.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
import yaml

from sbretire import __version__
from sbretire.__main__ import main
from sbretire.config import load_scenario
from sbretire.inputs_report import scenario_input_rows, write_inputs_csv
from sbretire.metadata import config_sha256, file_sha256
from sbretire.monte_carlo import draw_random_inputs, run_monte_carlo
from sbretire.mortality import load_mortality_table
from sbretire.optimization import (
    maximum_sustainable_budgets,
    path_budget_thresholds,
    path_return_thresholds,
    required_returns,
)
from sbretire.randomness import ResolvedSeed
from sbretire.reporting import (
    annual_results,
    write_annual_results_csv,
    write_lifestyle_results_csv,
    write_sustainability_results_csv,
)
from sbretire.results_guide import GuideContext, write_results_guide

from scenario_helpers import set_at

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "valid_minimal.yaml"


def _absolute_data(raw: dict[str, Any]) -> dict[str, Any]:
    raw = set_at(raw, "mortality.data_file", str(ROOT / "data" / "ons_mortality.csv"))
    return set_at(raw, "inflation.data_file", str(ROOT / "data" / "uk_cpi.csv"))


def _write(tmp_path: Path, raw: dict[str, Any]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "scenario.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def test_cli_run_prints_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "out"
    assert main(["run", "--config", str(FIXTURE), "--output-dir", str(out_dir)]) == 0
    out = capsys.readouterr().out
    assert out.isascii()

    scenario = load_scenario(FIXTURE).scenario
    expected = run_monte_carlo(
        scenario,
        draw_random_inputs(
            scenario, load_mortality_table(scenario.mortality.data_file), ResolvedSeed(7, "config")
        ),
    ).metrics
    assert "1,000 paths" in out
    assert f"successful {expected.n_successful:,}" in out
    assert f"failed {expected.n_failed:,}" in out
    assert f"unresolved {expected.n_unresolved:,}" in out
    assert f"Conservative success rate     {expected.conservative_success_rate:.2%}" in out
    assert f"+/- {expected.conservative_standard_error:.3%}" in out
    assert "denominator: all 1,000 paths" in out
    assert f"denominator: {expected.n_completed:,} completed paths" in out
    assert "3,000" in out and "today" in out
    assert "seed 7 (config)" in out
    assert "not a confidence interval" in out
    assert (out_dir / "run_metadata.json").is_file()


def test_cli_run_writes_metadata(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    config = _write(tmp_path, _absolute_data(valid_raw))
    out_dir = tmp_path / "out"
    assert main(["run", "--config", str(config), "--output-dir", str(out_dir)]) == 0
    meta = json.loads((out_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert meta["seed"] == 7 and meta["seed_source"] == "config"
    assert meta["software_version"] == __version__
    assert meta["config_sha256"] == config_sha256(load_scenario(config).scenario)
    assert meta["simulation_count"] == 1_000
    records = {record["role"]: record for record in meta["data_files"]}
    assert set(records) == {"mortality", "inflation"}
    assert records["mortality"]["sha256"] == file_sha256(ROOT / "data" / "ons_mortality.csv")
    assert records["mortality"]["version"] == "2024-based (published 2026-05-15)"
    assert records["inflation"]["sha256"] == file_sha256(ROOT / "data" / "uk_cpi.csv")
    assert records["inflation"]["version"] == "D7G7 (released 2026-09-16)"

    generated = _write(tmp_path / "null", set_at(_absolute_data(valid_raw), "model.random_seed", None))
    assert main(["run", "--config", str(generated), "--output-dir", str(tmp_path / "out2")]) == 0
    meta2 = json.loads((tmp_path / "out2" / "run_metadata.json").read_text(encoding="utf-8"))
    assert meta2["seed_source"] == "generated"
    assert 0 <= meta2["seed"] < 2**128
    assert f"seed {meta2['seed']} (generated)" in capsys.readouterr().out


def test_cli_run_rejects_bad_data(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    missing = _write(
        tmp_path / "missing", set_at(_absolute_data(valid_raw), "mortality.data_file", "nope.csv")
    )
    assert main(["run", "--config", str(missing), "--output-dir", str(tmp_path / "out")]) == 2
    assert "mortality.data_file" in capsys.readouterr().err

    short_cpi = tmp_path / "uk_cpi.csv"
    short_cpi.write_text("year,annual_rate\n" + "".join(f"{y},0.02\n" for y in range(1989, 2010)), "utf-8")
    gapped = _write(
        tmp_path / "gapped", set_at(_absolute_data(valid_raw), "inflation.data_file", str(short_cpi))
    )
    assert main(["run", "--config", str(gapped), "--output-dir", str(tmp_path / "out")]) == 2
    assert "inflation.source_period" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_cli_run_prints_maximum_budgets(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    raw = set_at(_absolute_data(valid_raw), "model.confidence_levels", [0.5, 0.9])
    config = _write(tmp_path / "feasible", raw)
    assert main(["run", "--config", str(config), "--output-dir", str(tmp_path / "out")]) == 0
    out = capsys.readouterr().out
    assert out.isascii()

    scenario = load_scenario(config).scenario
    inputs = draw_random_inputs(
        scenario, load_mortality_table(scenario.mortality.data_file), ResolvedSeed(7, "config")
    )
    expected = maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), [0.5, 0.9])
    assert "Maximum sustainable budget" in out and "tolerance 1 GBP/month" in out
    for result in expected:
        assert (
            result.maximum_monthly_budget_today is not None and result.maximum_annual_budget_today is not None
        )
        assert result.estimated_success_probability is not None and result.standard_error is not None
        row = next(
            line for line in out.splitlines() if line.lstrip().startswith(f"{result.target_probability:.0%}")
        )
        assert f"{math.floor(result.maximum_monthly_budget_today):,}" in row  # rounded down (B-011.1)
        assert f"{math.floor(result.maximum_annual_budget_today):,}" in row
        assert f"{result.estimated_success_probability:.2%} +/- {result.standard_error:.3%}" in row
        assert f"{result.unresolved_fraction:.2%}" in row
        assert row.rstrip().endswith("yes")
    assert f"{expected[0].iterations} engine runs" in out

    short = set_at(set_at(raw, "model.horizon_years", 10), "model.confidence_levels", [0.01, 0.9])
    config = _write(tmp_path / "short", short)
    assert main(["run", "--config", str(config), "--output-dir", str(tmp_path / "out2")]) == 0
    out = capsys.readouterr().out
    row = next(line for line in out.splitlines() if line.lstrip().startswith("90%"))
    assert "infeasible" in row


def test_cli_run_prints_required_returns(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    raw = set_at(_absolute_data(valid_raw), "model.confidence_levels", [0.5, 0.9])
    raw = set_at(raw, "budget.monthly_amount_today", 4_000)
    config = _write(tmp_path / "returns", raw)
    assert main(["run", "--config", str(config), "--output-dir", str(tmp_path / "out")]) == 0
    out = capsys.readouterr().out
    assert out.isascii()

    scenario = load_scenario(config).scenario
    inputs = draw_random_inputs(
        scenario, load_mortality_table(scenario.mortality.data_file), ResolvedSeed(7, "config")
    )
    expected = required_returns(path_return_thresholds(scenario, inputs), [0.5, 0.9])
    section = out[out.index("Required return") :]
    assert "4,000 GBP/month" in section and "tolerance 0.01 percentage points" in section
    assert f"{expected[0].iterations} engine runs" in section
    for result in expected:
        assert result.required_annual_return is not None
        assert result.estimated_success_probability is not None and result.standard_error is not None
        row = next(
            line
            for line in section.splitlines()
            if line.lstrip().startswith(f"{result.target_probability:.0%}")
        )
        assert f"{_ceil_percent(result.required_annual_return):.2%}" in row  # rounded up (B-011.1)
        assert f"{result.estimated_success_probability:.2%} +/- {result.standard_error:.3%}" in row
        assert f"{result.unresolved_fraction:.2%}" in row
        assert row.rstrip().endswith("yes")

    hopeless = set_at(set_at(raw, "budget.monthly_amount_today", 100_000), "model.confidence_levels", [0.5])
    config = _write(tmp_path / "hopeless", hopeless)
    assert main(["run", "--config", str(config), "--output-dir", str(tmp_path / "out2")]) == 0
    section = capsys.readouterr().out
    section = section[section.index("Required return") :]
    row = next(line for line in section.splitlines() if line.lstrip().startswith("50%"))
    assert "no solution" in row


def _ceil_percent(annual_return: float) -> float:
    """Round up to the next 0.01 % (tolerating float noise just above a grid point)."""
    return math.ceil(round(annual_return * 10_000, 9)) / 10_000


def _row(out: str, section: str, target: str) -> str:
    text = out[out.index(section) :]
    return next(line for line in text.splitlines() if line.lstrip().startswith(target))


def test_cli_run_budget_display_rounds_down(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    raw = set_at(_absolute_data(valid_raw), "model.confidence_levels", [0.9])
    config = _write(tmp_path / "budget", raw)
    assert main(["run", "--config", str(config), "--output-dir", str(tmp_path / "out")]) == 0
    row = _row(capsys.readouterr().out, "Maximum sustainable budget", "90%")

    scenario = load_scenario(config).scenario
    inputs = draw_random_inputs(
        scenario, load_mortality_table(scenario.mortality.data_file), ResolvedSeed(7, "config")
    )
    (result,) = maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), [0.9])
    assert result.maximum_monthly_budget_today is not None and result.maximum_annual_budget_today is not None
    monthly, annual = row.split()[1:3]
    assert monthly == f"{math.floor(result.maximum_monthly_budget_today):,}"
    assert annual == f"{math.floor(result.maximum_annual_budget_today):,}"
    printed = float(monthly.replace(",", ""))
    assert printed <= result.maximum_monthly_budget_today
    rate = run_monte_carlo(scenario, inputs, monthly_budget_today=printed).metrics.conservative_success_rate
    assert rate >= 0.9


def test_cli_run_return_display_rounds_up(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    raw = set_at(_absolute_data(valid_raw), "model.confidence_levels", [0.5, 0.9])
    raw = set_at(raw, "budget.monthly_amount_today", 4_000)
    config = _write(tmp_path / "return", raw)
    assert main(["run", "--config", str(config), "--output-dir", str(tmp_path / "out")]) == 0
    out = capsys.readouterr().out

    scenario = load_scenario(config).scenario
    inputs = draw_random_inputs(
        scenario, load_mortality_table(scenario.mortality.data_file), ResolvedSeed(7, "config")
    )
    for result in required_returns(path_return_thresholds(scenario, inputs), [0.5, 0.9]):
        assert result.required_annual_return is not None
        printed_text = _row(out, "Required return", f"{result.target_probability:.0%}").split()[1]
        assert printed_text == f"{_ceil_percent(result.required_annual_return):.2%}"
        printed = float(printed_text.rstrip("%")) / 100
        assert printed >= result.required_annual_return - 1e-12
        rate = run_monte_carlo(scenario, inputs, annual_return=printed).metrics.conservative_success_rate
        assert rate >= result.target_probability


def test_cli_run_writes_annual_results(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    config = _write(tmp_path / "annual", _absolute_data(valid_raw))
    out_dir = tmp_path / "out"
    assert main(["run", "--config", str(config), "--output-dir", str(out_dir)]) == 0
    annual = out_dir / "annual_results.csv"
    assert annual.is_file() and (out_dir / "run_metadata.json").is_file()
    assert f"Wrote {annual}" in capsys.readouterr().out

    scenario = load_scenario(config).scenario
    inputs = draw_random_inputs(
        scenario, load_mortality_table(scenario.mortality.data_file), ResolvedSeed(7, "config")
    )
    expected = write_annual_results_csv(annual_results(scenario, inputs), tmp_path / "expected.csv")
    assert annual.read_bytes() == expected.read_bytes()


OUTPUT_FILES = (
    "inputs.csv",
    "annual_results.csv",
    "sustainability_results.csv",
    "lifestyle_results.csv",
    "run_metadata.json",
    "results_guide.md",
)


def test_cli_run_writes_all_outputs(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    raw = set_at(_absolute_data(valid_raw), "model.confidence_levels", [0.5, 0.9])
    config = _write(tmp_path / "all", raw)
    out_dir = tmp_path / "out"
    assert main(["run", "--config", str(config), "--output-dir", str(out_dir)]) == 0
    out = capsys.readouterr().out
    for name in OUTPUT_FILES:
        assert (out_dir / name).is_file(), name
        assert f"Wrote {out_dir / name}" in out

    scenario = load_scenario(config).scenario
    inputs = draw_random_inputs(
        scenario, load_mortality_table(scenario.mortality.data_file), ResolvedSeed(7, "config")
    )
    targets = [0.5, 0.9]
    expected = tmp_path / "expected"
    write_lifestyle_results_csv(
        maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), targets),
        expected / "lifestyle.csv",
    )
    write_sustainability_results_csv(
        run_monte_carlo(scenario, inputs).metrics,
        scenario.portfolio.annual_return,
        required_returns(path_return_thresholds(scenario, inputs), targets),
        expected / "sustainability.csv",
    )
    assert (out_dir / "lifestyle_results.csv").read_bytes() == (expected / "lifestyle.csv").read_bytes()
    assert (out_dir / "sustainability_results.csv").read_bytes() == (
        expected / "sustainability.csv"
    ).read_bytes()


def test_cli_run_prints_inputs_and_writes_csv(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    config = _write(tmp_path / "inputs", set_at(_absolute_data(valid_raw), "model.confidence_levels", [0.9]))
    out_dir = tmp_path / "out"
    assert main(["run", "--config", str(config), "--output-dir", str(out_dir)]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"Inputs ({config}):")
    assert out.index("Monthly budget: 3,000") < out.index("SBRetire Monte Carlo")
    assert "Random seed used: 7 config" in out
    rows = scenario_input_rows(load_scenario(config).scenario, ResolvedSeed(7, "config"))
    expected = write_inputs_csv(rows, tmp_path / "expected_inputs.csv")
    assert (out_dir / "inputs.csv").read_bytes() == expected.read_bytes()
    assert f"Wrote {out_dir / 'inputs.csv'}" in out


def test_cli_run_writes_results_guide(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    config = _write(tmp_path / "guide", set_at(_absolute_data(valid_raw), "model.confidence_levels", [0.9]))
    for name in ("first", "second"):
        assert main(["run", "--config", str(config), "--output-dir", str(tmp_path / name)]) == 0
    guide = tmp_path / "first" / "results_guide.md"
    assert f"Wrote {guide}" in capsys.readouterr().out
    assert guide.read_bytes() == (tmp_path / "second" / "results_guide.md").read_bytes()

    scenario = load_scenario(config).scenario
    seed = ResolvedSeed(7, "config")
    inputs = draw_random_inputs(scenario, load_mortality_table(scenario.mortality.data_file), seed)
    context = GuideContext(
        config=config,
        scenario=scenario,
        seed=seed,
        input_rows=scenario_input_rows(scenario, seed),
        metrics=run_monte_carlo(scenario, inputs).metrics,
        budgets=maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), [0.9]),
        returns=required_returns(path_return_thresholds(scenario, inputs), [0.9]),
    )
    expected = write_results_guide(context, tmp_path / "expected.md")
    assert guide.read_bytes() == expected.read_bytes()


def test_cli_run_csvs_reproducible(tmp_path: Path, valid_raw: dict[str, Any]) -> None:
    raw = set_at(_absolute_data(valid_raw), "model.confidence_levels", [0.9])
    config = _write(tmp_path / "repro", raw)
    for name in ("first", "second"):
        assert main(["run", "--config", str(config), "--output-dir", str(tmp_path / name)]) == 0
    for name in (name for name in OUTPUT_FILES if name.endswith(".csv")):
        assert (tmp_path / "first" / name).read_bytes() == (tmp_path / "second" / name).read_bytes(), name
    first = json.loads((tmp_path / "first" / "run_metadata.json").read_text(encoding="utf-8"))
    second = json.loads((tmp_path / "second" / "run_metadata.json").read_text(encoding="utf-8"))
    first.pop("created_at")
    second.pop("created_at")
    assert first == second


def test_cli_run_unwritable_output_dir(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = tmp_path / "not_a_directory"
    blocker.write_text("x", encoding="utf-8")
    config = _write(tmp_path / "blocked", set_at(_absolute_data(valid_raw), "model.confidence_levels", [0.9]))
    target = blocker / "out"
    assert main(["run", "--config", str(config), "--output-dir", str(target)]) == 1
    captured = capsys.readouterr()
    assert "cannot write" in captured.err and str(target) in captured.err
    assert "Wrote" not in captured.out
