"""F-003.1 — the PriceIndex seam and zero-inflation baseline (SPEC §6, §17.1)."""

from __future__ import annotations

import numpy as np

from sbretire.inflation import FlatPriceIndex, PriceIndex, StochasticPriceIndex


def test_flat_price_index_is_constant() -> None:
    index: PriceIndex = FlatPriceIndex(n_paths=5)
    for month in (0, 1, 11, 12, 600, 1199):
        level = index.level(month)
        assert level.shape == (5,)
        assert level.dtype == np.float64
        np.testing.assert_array_equal(level, np.ones(5))


def test_constant_index_compounds_monthly_not_in_annual_steps() -> None:
    """Replaces the F-015 annual-step tests: simulation-conventions §5 supersedes §3 (F-006)."""
    index: PriceIndex = StochasticPriceIndex.constant(n_paths=3, n_years=31, annual_rate=0.02)
    for month in (0, 5, 11, 12, 23, 24, 12 * 30 + 7):
        np.testing.assert_allclose(index.level(month), np.full(3, 1.02 ** (month / 12)), rtol=1e-13)
    flat = StochasticPriceIndex.constant(n_paths=2, n_years=50, annual_rate=0.0)
    for month in (0, 12, 600):
        np.testing.assert_array_equal(flat.level(month), np.ones(2))
