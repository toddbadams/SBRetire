"""Seed resolution and Random Streams (SPEC §10.3; simulation-conventions §4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

import numpy as np

SeedSource = Literal["config", "generated"]
MORTALITY_STREAM: Final = 0
INFLATION_STREAM: Final = 1


@dataclass(frozen=True)
class ResolvedSeed:
    value: int
    source: SeedSource


def resolve_seed(configured: int | None) -> ResolvedSeed:
    raise NotImplementedError


@dataclass(frozen=True)
class RandomStreams:
    seed: ResolvedSeed
    mortality: np.random.Generator
    inflation: np.random.Generator

    @classmethod
    def from_seed(cls, seed: ResolvedSeed) -> RandomStreams:
        raise NotImplementedError
