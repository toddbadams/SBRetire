"""Seed resolution and Random Streams (SPEC §10.3; simulation-conventions §4).

All randomness in a run descends from one ``numpy.random.SeedSequence``. Each stochastic component draws
from its own Random Stream on a fixed child index, so consuming more draws in one component never shifts
another's. Streams are created once per run and their draws reused across optimisation candidates (Common
Random Numbers).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

import numpy as np

SeedSource = Literal["config", "generated"]

MORTALITY_STREAM: Final = 0
"""Child index of the mortality Random Stream; never reuse or reorder."""
INFLATION_STREAM: Final = 1
"""Child index of the inflation Random Stream; a future component takes the next unused index."""


@dataclass(frozen=True)
class ResolvedSeed:
    """The run's root seed and where it came from (recorded in Run Metadata)."""

    value: int
    """Non-negative; up to 128 bits when generated."""
    source: SeedSource


def resolve_seed(configured: int | None) -> ResolvedSeed:
    """Use ``model.random_seed`` if set, else a 128-bit seed from OS entropy (configuration §8)."""
    if configured is not None:
        return ResolvedSeed(configured, "config")
    entropy = np.random.SeedSequence().entropy
    assert isinstance(entropy, int)
    return ResolvedSeed(entropy, "generated")


def _stream(seed: ResolvedSeed, index: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed.value, spawn_key=(index,))))


@dataclass(frozen=True)
class RandomStreams:
    """Independent mortality and inflation generators for one run."""

    seed: ResolvedSeed
    mortality: np.random.Generator
    inflation: np.random.Generator

    @classmethod
    def from_seed(cls, seed: ResolvedSeed) -> RandomStreams:
        """Fresh generators at their initial state; equal seeds give identical draws."""
        return cls(seed, _stream(seed, MORTALITY_STREAM), _stream(seed, INFLATION_STREAM))
