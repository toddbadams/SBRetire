"""F-009.1 — path classification and success metrics (simulation-conventions §7; SPEC §11, §17.2)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from sbretire.metrics import PathClass, SuccessMetrics, classify_paths
from sbretire.simulation import PathOutcomes


def _outcomes(depleted: list[bool], censored: list[bool]) -> PathOutcomes:
    """Hand-built outcomes: a depleted path ran out in month 5; uncensored paths end at month 100."""
    depletion = np.where(depleted, 5, -1).astype(np.int64)
    cens = np.array(censored, dtype=bool)
    return PathOutcomes(
        depletion_month=depletion,
        shortfall=np.where(depleted, 100.0, 0.0),
        household_end_month=np.where(cens, -1, 100).astype(np.int64),
        censored=cens,
        final_balance=np.where(depleted, 0.0, 1000.0),
    )


def test_classify_paths_table() -> None:
    outcomes = _outcomes(depleted=[False, True, True, False], censored=[False, False, True, True])
    classes = classify_paths(outcomes)
    assert classes.dtype == np.int8
    assert classes.tolist() == [
        PathClass.SUCCESSFUL,
        PathClass.FAILED,
        PathClass.FAILED,
        PathClass.UNRESOLVED,
    ]


def test_censored_paths_never_count_as_success() -> None:
    only_unresolved = SuccessMetrics.from_outcomes(_outcomes(depleted=[False] * 5, censored=[True] * 5))
    assert only_unresolved.n_successful == 0
    assert only_unresolved.n_unresolved == 5
    assert only_unresolved.n_completed == 0
    assert only_unresolved.conservative_success_rate == 0.0
    assert only_unresolved.conservative_standard_error == 0.0
    assert only_unresolved.completed_success_rate is None
    assert only_unresolved.completed_standard_error is None
    assert only_unresolved.unresolved_share == 1.0

    mixed = SuccessMetrics.from_outcomes(_outcomes(depleted=[False, False], censored=[False, True]))
    assert (mixed.n_successful, mixed.n_unresolved) == (1, 1)
    assert (
        mixed.conservative_success_rate == 0.5
    )  # the censored path is in the denominator, not the numerator
    assert mixed.completed_success_rate == 1.0


def test_success_metrics_hand_computed() -> None:
    # 10 paths: 6 successful, 2 failed (one with someone alive at the horizon), 2 unresolved.
    depleted = [False] * 6 + [True, True] + [False, False]
    censored = [False] * 6 + [False, True] + [True, True]
    metrics = SuccessMetrics.from_outcomes(_outcomes(depleted, censored))
    assert (metrics.n_paths, metrics.n_successful, metrics.n_failed, metrics.n_unresolved) == (10, 6, 2, 2)
    assert metrics.n_completed == 8
    assert metrics.conservative_success_rate == pytest.approx(0.6)
    assert metrics.conservative_standard_error == pytest.approx(math.sqrt(0.6 * 0.4 / 10))
    assert metrics.completed_success_rate == pytest.approx(0.75)
    assert metrics.completed_standard_error == pytest.approx(math.sqrt(0.75 * 0.25 / 8))
    assert metrics.unresolved_share == pytest.approx(0.2)
