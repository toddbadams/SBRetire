"""F-003.1 — the PriceIndex seam and zero-inflation baseline (SPEC §6, §17.1)."""

from __future__ import annotations

import numpy as np

from sbretire.inflation import AnnualStepPriceIndex, FlatPriceIndex, PriceIndex


def test_flat_price_index_is_constant() -> None:
    index: PriceIndex = FlatPriceIndex(n_paths=5)
    for month in (0, 1, 11, 12, 600, 1199):
        level = index.level(month)
        assert level.shape == (5,)
        assert level.dtype == np.float64
        np.testing.assert_array_equal(level, np.ones(5))


def test_annual_step_index_steps_on_anniversaries() -> None:
    index = AnnualStepPriceIndex(n_paths=3, annual_rate=0.02)
    for month in (0, 5, 11):
        np.testing.assert_array_equal(index.level(month), np.ones(3))
    for month in (12, 23):
        np.testing.assert_allclose(index.level(month), np.full(3, 1.02))
    np.testing.assert_allclose(index.level(24), np.full(3, 1.02**2))
    np.testing.assert_allclose(index.level(12 * 30 + 7), np.full(3, 1.02**30))


def test_annual_step_index_zero_rate_is_flat() -> None:
    index = AnnualStepPriceIndex(n_paths=2, annual_rate=0.0)
    for month in (0, 12, 600):
        np.testing.assert_array_equal(index.level(month), np.ones(2))
