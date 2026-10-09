"""Build the Claude Design sample: two named runs of config/model.example.yaml into docs/design/sample/runs/.

Usage:
    uv run python scripts/build_design_sample.py [--paths N]

Runs ``sbretire run`` twice on the **example** config (never a personal one): ``example-base`` as configured,
and ``example-stretch`` (10,500/month, 4 % return, 12-month End-of-Life Reserve), a plan that fails in some
futures so the charts and tables have something to show. Only each run's ``results.json`` plus the runs
``index.json`` and ``runs.js`` are kept: small, and no personal data.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml

from sbretire.__main__ import main
from sbretire.results_json import refresh_runs_index

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "config" / "model.example.yaml"
SAMPLE = ROOT / "docs" / "design" / "sample" / "runs"
VARIANTS: dict[str, dict[str, Any]] = {
    "example-base": {},
    "example-stretch": {
        "portfolio": {"annual_return": 0.04},
        "budget": {"monthly_amount_today": 10_500, "end_reserve_months": 12},
    },
}


def _config(directory: Path, changes: dict[str, Any], paths: int | None) -> Path:
    raw: dict[str, Any] = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    raw["mortality"]["data_file"] = str(ROOT / "data" / "ons_mortality.csv")
    raw["inflation"]["data_file"] = str(ROOT / "data" / "uk_cpi.csv")
    for section, values in changes.items():
        raw[section].update(values)
    if paths is not None:
        raw["model"]["simulation_count"] = paths
    path = directory / "model.example.yaml"  # same name as the source, so config_file reads as the example
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def build(paths: int | None) -> None:
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        out = work / "out"
        for name, changes in VARIANTS.items():
            config_dir = work / name
            config_dir.mkdir()
            config = _config(config_dir, changes, paths)
            status = main(["run", "--config", str(config), "--output-dir", str(out), "--name", name])
            if status != 0:
                raise SystemExit(f"sample run {name} failed with exit code {status}")
        if SAMPLE.exists():
            shutil.rmtree(SAMPLE)
        for name in VARIANTS:
            (SAMPLE / name).mkdir(parents=True)
            shutil.copyfile(out / "runs" / name / "results.json", SAMPLE / name / "results.json")
    refresh_runs_index(SAMPLE)
    print(f"Design sample written to {SAMPLE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--paths", type=int, help="override model.simulation_count (default: the example's)")
    build(parser.parse_args().paths)
