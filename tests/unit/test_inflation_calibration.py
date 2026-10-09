"""F-006.2 — AR(1) lognormal calibration from UK CPI (F-006 brief §2 #2–#6; data-and-calibration §2)."""

from __future__ import annotations

import math
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

from sbretire.config import load_scenario
from sbretire.inflation import Ar1LognormalParams, calibrate_inflation, fit_ar1_lognormal, load_cpi_series

ROOT = Path(__file__).resolve().parents[2]
CPI = ROOT / "data" / "uk_cpi.csv"
EXAMPLE = ROOT / "config" / "model.example.yaml"


def test_fit_ar1_lognormal_known_answers() -> None:
    # Hand-computed: x = log(1 + r); μ = mean(x); φ = Σ d_{t-1} d_t / Σ d_{t-1}²; σ = √(Σ e² / (n - 2)).
    rates = [0.01, 0.03, 0.02, 0.04, 0.025]
    x = [math.log1p(r) for r in rates]
    mu = sum(x) / len(x)
    d = [v - mu for v in x]
    phi = sum(a * b for a, b in pairwise(d)) / sum(a * a for a in d[:-1])
    residuals = [b - phi * a for a, b in pairwise(d)]
    sigma = math.sqrt(sum(e * e for e in residuals) / (len(rates) - 2))
    fitted = fit_ar1_lognormal(rates)
    assert fitted.log_mean == pytest.approx(mu, rel=1e-12)
    assert fitted.ar1_coefficient == pytest.approx(phi, rel=1e-12)
    assert fitted.innovation_sd == pytest.approx(sigma, rel=1e-12)
    assert fitted.initial_rate == 0.025
    assert fit_ar1_lognormal(rates, initial_rate=0.05).initial_rate == 0.05

    # Long synthetic AR(1) series with known parameters (seeded) is recovered within tolerance.
    rng = np.random.default_rng(20261009)
    true = Ar1LognormalParams(log_mean=0.03, ar1_coefficient=0.6, innovation_sd=0.015, initial_rate=0.03)
    series = [math.log1p(true.initial_rate)]
    for shock in rng.standard_normal(20_000):
        series.append(
            true.log_mean + true.ar1_coefficient * (series[-1] - true.log_mean) + true.innovation_sd * shock
        )
    synthetic = fit_ar1_lognormal([math.expm1(v) for v in series[1:]])
    assert synthetic.log_mean == pytest.approx(0.03, abs=0.001)
    assert synthetic.ar1_coefficient == pytest.approx(0.6, abs=0.02)
    assert synthetic.innovation_sd == pytest.approx(0.015, abs=0.0003)

    # Real data, 1989–2025.
    cpi = load_cpi_series(CPI)
    real = fit_ar1_lognormal([cpi[year] for year in range(1989, 2026)])
    assert round(real.log_mean, 6) == 0.027742
    assert round(real.ar1_coefficient, 6) == 0.617897
    assert round(real.innovation_sd, 6) == 0.015365
    assert real.initial_rate == 0.034


def test_fit_ar1_lognormal_rejects_degenerate_series() -> None:
    with pytest.raises(ValueError, match="at least 3"):
        fit_ar1_lognormal([0.02, 0.03])
    with pytest.raises(ValueError, match="constant"):
        fit_ar1_lognormal([0.02, 0.02, 0.02, 0.02])
    with pytest.raises(ValueError, match="greater than -1"):
        fit_ar1_lognormal([0.02, -1.0, 0.03])


def test_example_config_matches_calibration() -> None:
    inflation = load_scenario(EXAMPLE).scenario.inflation
    fitted = calibrate_inflation(inflation)
    assert inflation.log_mean == round(fitted.log_mean, 4)
    assert inflation.ar1_coefficient == round(fitted.ar1_coefficient, 4)
    assert inflation.innovation_sd == round(fitted.innovation_sd, 4)
    assert inflation.initial_rate == round(fitted.initial_rate, 4)


def test_load_cpi_series_reads_and_validates(tmp_path: Path) -> None:
    cpi = load_cpi_series(CPI)
    assert cpi[2022] == 0.091 and min(cpi) == 1989 and max(cpi) == 2025
    bad = tmp_path / "cpi.csv"
    for text, fragment in [
        ("year,rate\n2020,0.01\n", "columns"),
        ("year,annual_rate\n2020,0.01\n2022,0.02\n", "contiguous"),
        ("year,annual_rate\n2020,abc\n", "uk_cpi.csv:2"),
        ("year,annual_rate\n2020,-1.0\n", "greater than -1"),
        ("year,annual_rate\n2020,0.01\n2020,0.02\n", "duplicate"),
    ]:
        bad.write_text(text, encoding="utf-8")
        renamed = bad.rename(tmp_path / "uk_cpi.csv")
        with pytest.raises(ValueError, match=fragment):
            load_cpi_series(renamed)
        renamed.rename(bad)
