"""Inflation: the price-index seam (SPEC §6).

Income and spending read the cumulative **Inflation Index** I_t through :class:`PriceIndex`, one month at a
time, so the stochastic process (F-006) can be swapped in without changing them. I = 1 in the As-Of month,
which is what makes "today's GBP" amounts nominal: nominal = today's amount × I_t.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from sbretire.portfolio import FloatArray


class PriceIndex(Protocol):
    """Cumulative price level per path."""

    def level(self, month: int) -> FloatArray:
        """I_t for ``month`` (0 = As-Of month), shape (n_paths,)."""
        ...


class FlatPriceIndex:
    """Zero inflation: I_t = 1 for every path and month."""

    def __init__(self, n_paths: int) -> None:
        self._ones = np.ones(n_paths, dtype=np.float64)
        self._ones.flags.writeable = False

    def level(self, month: int) -> FloatArray:
        return self._ones
