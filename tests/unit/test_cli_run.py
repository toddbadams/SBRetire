"""F-009.3 — ``sbretire run``: Monte Carlo summary and run_metadata.json (F-009 brief §2 #5–#6).

Fixture tests/fixtures/scenarios/valid_minimal.yaml: 1,000 paths, 60-year horizon, seed 7, budget 3,000/month,
with the real ONS mortality and CPI files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from sbretire import __version__
from sbretire.__main__ import main
from sbretire.config import load_scenario
from sbretire.metadata import config_sha256, file_sha256
from sbretire.monte_carlo import draw_random_inputs, run_monte_carlo
from sbretire.mortality import load_mortality_table
from sbretire.randomness import ResolvedSeed

from scenario_helpers import set_at

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "scenarios" / "valid_minimal.yaml"


def _absolute_data(raw: dict[str, Any]) -> dict[str, Any]:
    raw = set_at(raw, "mortality.data_file", str(ROOT / "data" / "ons_mortality.csv"))
    return set_at(raw, "inflation.data_file", str(ROOT / "data" / "uk_cpi.csv"))


def _write(tmp_path: Path, raw: dict[str, Any]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "scenario.yaml"
    path.write_text(yaml.safe_dump(_absolute_data(raw), sort_keys=False), encoding="utf-8")
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
    assert f"+/- {expected.conservative_standard_error:.2%}" in out
    assert "denominator: all 1,000 paths" in out
    assert f"denominator: {expected.n_completed:,} completed paths" in out
    assert "3,000" in out and "today" in out
    assert "seed 7 (config)" in out
    assert "not a confidence interval" in out
    assert (out_dir / "run_metadata.json").is_file()


def test_cli_run_writes_metadata(
    tmp_path: Path, valid_raw: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    config = _write(tmp_path, valid_raw)
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

    generated = _write(tmp_path / "null", set_at(valid_raw, "model.random_seed", None))
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
