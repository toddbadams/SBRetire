"""F-011.1 — a per-path annual return through the engine (F-011 brief §2 #6)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from sbretire.simulation import PathOutcomes, simulate_paths

from cash_flow_doubles import constant

RETURNS = np.array([-0.3, -0.02, 0.0, 0.03, 0.07, 0.25])
DEATHS = np.array([[40, 400, 150, 10, 600, 90], [200, 30, 150, 700, 20, 300]], dtype=np.int64)


def _run(
    annual_return: Any, deaths: NDArray[np.int64], spending: float = 2_500.0, income: float = 400.0
) -> PathOutcomes:
    n_paths = deaths.shape[1]
    return simulate_paths(
        starting_balance=300_000.0,
        annual_return=annual_return,
        death_month=deaths,
        horizon_months=720,
        cash_flows=constant(n_paths, spending=spending, income=income),
    )


def test_simulate_paths_per_path_return_matches_scalar_runs() -> None:
    together = _run(RETURNS, DEATHS)
    for path, annual_return in enumerate(RETURNS):
        alone = _run(float(annual_return), DEATHS[:, path : path + 1])
        assert together.depletion_month[path] == alone.depletion_month[0]
        assert together.household_end_month[path] == alone.household_end_month[0]
        assert together.censored[path] == alone.censored[0]
        assert together.final_balance[path] == pytest.approx(alone.final_balance[0], rel=1e-12)
        assert together.shortfall[path] == pytest.approx(alone.shortfall[0], rel=1e-12)
    assert len(set(together.depletion_month.tolist())) > 1  # the returns really differ in effect


def test_simulate_paths_scalar_return_unchanged() -> None:
    scalar = _run(0.04, DEATHS)
    array = _run(np.full(6, 0.04), DEATHS)
    for name in ("depletion_month", "shortfall", "household_end_month", "censored", "final_balance"):
        np.testing.assert_array_equal(getattr(scalar, name), getattr(array, name))


@pytest.mark.parametrize(
    "annual_return",
    [-1.0, -1.5, np.array([0.02, -1.0, 0.03, 0.0, 0.0, 0.0]), np.array([0.02, 0.03]), np.full((2, 6), 0.02)],
)
def test_simulate_paths_rejects_bad_return(annual_return: Any) -> None:
    with pytest.raises(ValueError, match="annual_return"):
        _run(annual_return, DEATHS)
