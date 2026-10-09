"""F-003.1 — the PriceIndex seam and zero-inflation baseline (SPEC §6, §17.1)."""

from __future__ import annotations

import numpy as np

from sbretire.inflation import FlatPriceIndex, PriceIndex


def test_flat_price_index_is_constant() -> None:
    index: PriceIndex = FlatPriceIndex(n_paths=5)
    for month in (0, 1, 11, 12, 600, 1199):
        level = index.level(month)
        assert level.shape == (5,)
        assert level.dtype == np.float64
        np.testing.assert_array_equal(level, np.ones(5))
