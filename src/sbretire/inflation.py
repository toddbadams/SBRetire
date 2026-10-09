"""Inflation: the price-index seam (SPEC §6)."""

from __future__ import annotations

from typing import Protocol

from sbretire.portfolio import FloatArray


class PriceIndex(Protocol):
    def level(self, month: int) -> FloatArray: ...


class FlatPriceIndex:
    def __init__(self, n_paths: int) -> None:
        self.n_paths = n_paths

    def level(self, month: int) -> FloatArray:
        raise NotImplementedError
