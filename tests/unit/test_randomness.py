"""F-005.1 — Random Streams and seed resolution (F-005 brief §2 #1–#3, simulation-conventions §4)."""

from __future__ import annotations

import numpy as np
import pytest

from sbretire.randomness import RandomStreams, ResolvedSeed, resolve_seed

SEED_42 = ResolvedSeed(42, "config")


def _draws(streams: RandomStreams, n: int = 5) -> tuple[list[float], list[float]]:
    return streams.mortality.random(n).tolist(), streams.inflation.random(n).tolist()


def test_random_streams_fixed_seed_reproduces_draws() -> None:
    first = _draws(RandomStreams.from_seed(SEED_42), 1000)
    second = _draws(RandomStreams.from_seed(SEED_42), 1000)
    assert first == second


@pytest.mark.parametrize("burn", [0, 1, 17, 10_000])
def test_random_streams_consumption_is_independent(burn: int) -> None:
    baseline = RandomStreams.from_seed(SEED_42)
    expected_mortality = baseline.mortality.random(50).tolist()
    expected_inflation = baseline.inflation.random(50).tolist()

    streams = RandomStreams.from_seed(SEED_42)
    streams.inflation.random(burn)
    streams.inflation.normal(size=burn)
    assert streams.mortality.random(50).tolist() == expected_mortality

    streams = RandomStreams.from_seed(SEED_42)
    streams.mortality.random(burn)
    assert streams.inflation.random(50).tolist() == expected_inflation


def test_random_streams_streams_and_seeds_differ() -> None:
    mortality, inflation = _draws(RandomStreams.from_seed(SEED_42), 100)
    assert mortality != inflation
    other_mortality, other_inflation = _draws(RandomStreams.from_seed(ResolvedSeed(43, "config")), 100)
    assert other_mortality != mortality
    assert other_inflation != inflation


def test_resolve_seed_null_generates_reproducible_seed() -> None:
    configured = resolve_seed(7)
    assert configured == ResolvedSeed(7, "config")

    generated = resolve_seed(None)
    assert generated.source == "generated"
    assert isinstance(generated.value, int)
    assert 0 <= generated.value < 2**128
    assert resolve_seed(None).value != generated.value  # fresh OS entropy each time

    original = _draws(RandomStreams.from_seed(generated), 100)
    replayed = _draws(RandomStreams.from_seed(resolve_seed(generated.value)), 100)
    assert replayed == original
    assert resolve_seed(generated.value).source == "config"


def test_random_streams_seed_42_known_answer() -> None:
    """Pins child 0 = mortality and child 1 = inflation (catches reordering or a bit-generator change)."""
    streams = RandomStreams.from_seed(SEED_42)
    np.testing.assert_array_equal(
        streams.mortality.random(3), [0.9167441575549085, 0.9109866676343232, 0.8765925046098457]
    )
    np.testing.assert_array_equal(
        streams.inflation.random(3), [0.4674907799518424, 0.04644889644868733, 0.5955100095961371]
    )
    assert streams.seed == SEED_42
