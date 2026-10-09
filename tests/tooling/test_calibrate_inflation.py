"""F-006.2 — scripts/calibrate_inflation.py prints the calibrated inflation block."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sbretire.config import load_scenario
from sbretire.inflation import calibrate_inflation as fit_for

import calibrate_inflation

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "config" / "model.example.yaml"


def test_calibrate_inflation_script_prints_block(capsys: pytest.CaptureFixture[str]) -> None:
    assert calibrate_inflation.main(["--config", str(EXAMPLE)]) == 0
    out = capsys.readouterr().out
    block = yaml.safe_load(out)["inflation"]
    fitted = fit_for(load_scenario(EXAMPLE).scenario.inflation)
    assert block["model"] == "ar1_lognormal"
    assert block["parameter_units"] == "log_annual"
    assert block["log_mean"] == round(fitted.log_mean, 4)
    assert block["ar1_coefficient"] == round(fitted.ar1_coefficient, 4)
    assert block["innovation_sd"] == round(fitted.innovation_sd, 4)
    assert block["initial_rate"] == round(fitted.initial_rate, 4)
    assert "1989-2025" in out
