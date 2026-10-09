"""F-006.3 — AR(1) lognormal draws and the monthly-compounding StochasticPriceIndex.

F-006 brief §2 #2, #7, #9, #10; simulation-conventions §5; SPEC §6, §17.1.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from sbretire.inflation import Ar1LognormalParams, StochasticPriceIndex, draw_annual_rates
from sbretire.randomness import RandomStreams, ResolvedSeed

EXAMPLE = Ar1LognormalParams(
    log_mean=0.0277, ar1_coefficient=0.6179, innovation_sd=0.0154, initial_rate=0.034
)


def _inflation_stream(seed: int) -> np.random.Generator:
    return RandomStreams.from_seed(ResolvedSeed(seed, "config")).inflation


def test_stochastic_price_index_zero_inflation_constant() -> None:
    zero = Ar1LognormalParams(log_mean=0.0, ar1_coefficient=0.6, innovation_sd=0.0, initial_rate=0.0)
    rates = draw_annual_rates(_inflation_stream(1), zero, n_paths=4, n_years=5)
    assert rates.shape == (5, 4)
    np.testing.assert_array_equal(rates, 0.0)
    index = StochasticPriceIndex(rates)
    for month in range(0, 61):
        np.testing.assert_array_equal(index.level(month), np.ones(4))


def test_stochastic_price_index_monthly_compounding() -> None:
    rates = np.array([[0.02, 0.10], [0.05, -0.03], [0.0, 0.07]])  # (3 years, 2 paths)
    index = StochasticPriceIndex(rates)
    np.testing.assert_array_equal(index.level(0), [1.0, 1.0])
    for k in range(4):
        expected = np.prod(1 + rates[:k], axis=0)
        np.testing.assert_allclose(index.level(12 * k), expected, rtol=1e-14)
    for month in range(36):
        k, within = divmod(month, 12)
        expected = np.prod(1 + rates[:k], axis=0) * (1 + rates[k]) ** (within / 12)
        np.testing.assert_allclose(index.level(month), expected, rtol=1e-14)
    np.testing.assert_allclose(index.level(6), [1.02**0.5, 1.10**0.5], rtol=1e-14)
    assert index.level(5).dtype == np.float64


@settings(max_examples=60, deadline=None)
@given(
    log_mean=st.floats(-0.2, 0.2),
    phi=st.floats(-0.99, 0.99),
    sigma=st.floats(0.0, 0.2),
    initial=st.floats(-0.9, 1.0),
    seed=st.integers(0, 2**32),
)
def test_draw_annual_rates_positive_growth(
    log_mean: float, phi: float, sigma: float, initial: float, seed: int
) -> None:
    params = Ar1LognormalParams(
        log_mean=log_mean, ar1_coefficient=phi, innovation_sd=sigma, initial_rate=initial
    )
    rates = draw_annual_rates(_inflation_stream(seed), params, n_paths=50, n_years=40)
    assert np.all(1 + rates > 0)
    assert np.all(np.isfinite(rates))
    index = StochasticPriceIndex(rates)
    for month in (0, 1, 13, 240, 479, 480):
        level = index.level(month)
        assert np.all(level > 0) and np.all(np.isfinite(level))


def test_draw_annual_rates_seed_42_known_answer_and_prefix() -> None:
    rates = draw_annual_rates(_inflation_stream(42), EXAMPLE, n_paths=3, n_years=60)
    # Independently computed from SeedSequence(42, spawn_key=(1,)) standard normals (F-006 brief §2 #9).
    np.testing.assert_allclose(
        rates[0], [0.05186284610536719, 0.041415010613522645, 0.01066121315610454], rtol=1e-12
    )
    np.testing.assert_allclose(
        rates[1], [0.025686522889023698, 0.057966066211359024, -0.01792314003042322], rtol=1e-12
    )
    short = draw_annual_rates(_inflation_stream(42), EXAMPLE, n_paths=3, n_years=10)
    np.testing.assert_array_equal(short, rates[:10])
    again = draw_annual_rates(_inflation_stream(42), EXAMPLE, n_paths=3, n_years=60)
    np.testing.assert_array_equal(again, rates)


def test_draw_annual_rates_deterministic_path() -> None:
    params = Ar1LognormalParams(log_mean=0.025, ar1_coefficient=0.5, innovation_sd=0.0, initial_rate=0.08)
    rates = draw_annual_rates(_inflation_stream(3), params, n_paths=2, n_years=8)
    x_initial = math.log1p(0.08)
    for year in range(8):
        expected = math.expm1(0.025 + 0.5 ** (year + 1) * (x_initial - 0.025))
        np.testing.assert_allclose(rates[year], [expected, expected], rtol=1e-13)


def test_draw_annual_rates_statistics_match_parameters() -> None:
    params = Ar1LognormalParams(
        log_mean=0.0277, ar1_coefficient=0.6179, innovation_sd=0.0154, initial_rate=0.0281
    )
    x = np.log1p(draw_annual_rates(_inflation_stream(7), params, n_paths=100_000, n_years=60))
    assert x.mean() == pytest.approx(params.log_mean, abs=0.001)
    d = x - params.log_mean
    lagged, current = d[:-1].ravel(), d[1:].ravel()
    phi = float(lagged @ current / (lagged @ lagged))
    assert phi == pytest.approx(params.ar1_coefficient, abs=0.01)
    residual_sd = float(np.std(current - phi * lagged))
    assert residual_sd == pytest.approx(params.innovation_sd, abs=0.0005)


def test_stochastic_price_index_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="greater than -1"):
        StochasticPriceIndex(np.array([[0.02], [-1.0]]))
    with pytest.raises(ValueError, match="finite"):
        StochasticPriceIndex(np.array([[0.02], [np.nan]]))
    with pytest.raises(ValueError, match="2-D"):
        StochasticPriceIndex(np.array([0.02, 0.03]))
    index = StochasticPriceIndex(np.array([[0.02, 0.03]]))
    with pytest.raises(ValueError, match="month"):
        index.level(-1)
    with pytest.raises(ValueError, match="month"):
        index.level(13)
    np.testing.assert_allclose(index.level(12), [1.02, 1.03])
    constant = StochasticPriceIndex.constant(n_paths=2, n_years=3, annual_rate=0.02)
    np.testing.assert_allclose(constant.level(36), [1.02**3, 1.02**3])
    with pytest.raises(ValueError, match="n_paths"):
        draw_annual_rates(_inflation_stream(1), EXAMPLE, n_paths=0, n_years=3)
