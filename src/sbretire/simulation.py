"""Path loop: monthly simulation of every Path at once (SPEC §10.2; simulation-conventions §2).

The engine only does the portfolio accounting. Who is alive comes from each person's Death Month; how much
income arrives and how much must be spent each month comes from an injected :class:`HouseholdCashFlows`.
The month loop is the only Python loop — every step inside it is an array operation over paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from sbretire.portfolio import BoolArray, FloatArray, apply_month, monthly_return_rates

IntArray = NDArray[np.int64]


class HouseholdCashFlows(Protocol):
    """Monthly income and Required Spending in nominal GBP, one value per path.

    ``alive`` has shape (2, n_paths): who is alive at the start of ``month``. Providers are evaluated for
    every path; the engine applies the results only to paths still running.
    """

    def income(self, month: int, alive: BoolArray) -> FloatArray: ...

    def spending(self, month: int, alive: BoolArray) -> FloatArray: ...


class MonthObserver(Protocol):
    """Called after each simulated month's cash flows.

    ``balance`` is the closing balance (0 for depleted paths, frozen for ended ones); ``active`` marks the
    paths that were still running at the start of ``month``.
    """

    def __call__(self, month: int, balance: FloatArray, alive: BoolArray, active: BoolArray) -> None: ...


@dataclass(frozen=True)
class PathOutcomes:
    """What happened on each path (arrays of length n_paths)."""

    depletion_month: IntArray  # month of Depletion, -1 if never
    shortfall: FloatArray  # unmet spending in the Depletion month, 0 if never depleted (nominal GBP)
    household_end_month: IntArray  # first month both people are dead, -1 if not within the horizon
    censored: BoolArray  # at least one person alive at the horizon
    final_balance: FloatArray  # balance when the path stopped (0 if depleted), nominal GBP


def simulate_paths(
    *,
    starting_balance: float,
    annual_return: float | FloatArray,
    death_month: IntArray,
    horizon_months: int,
    cash_flows: HouseholdCashFlows,
    observer: MonthObserver | None = None,
) -> PathOutcomes:
    """Simulate every path month by month from the As-Of month (month 0).

    ``death_month[p, i]`` is the first month person ``p`` is dead on path ``i``; a value ≥ ``horizon_months``
    means alive at the horizon. ``annual_return`` is one fixed annual effective return, or one per path
    (n_paths,) for the return search (F-011). Each month: alive update → income and spending due → return
    on the opening balance → add income → funding test → spend (simulation-conventions §2). A path stops at
    Depletion or Household End; the loop stops early once no path is running.
    """
    death_month = np.asarray(death_month, dtype=np.int64)
    if death_month.ndim != 2 or death_month.shape[0] != 2:
        raise ValueError(f"death_month must have shape (2, n_paths) (got {death_month.shape})")
    if (death_month < 0).any():
        raise ValueError("death_month values must be non-negative month indices")
    if horizon_months <= 0:
        raise ValueError(f"horizon_months must be positive (got {horizon_months})")

    n_paths = death_month.shape[1]
    rate = monthly_return_rates(annual_return, n_paths)
    last_death = death_month.max(axis=0)
    censored = last_death >= horizon_months

    balance = np.full(n_paths, float(starting_balance), dtype=np.float64)
    depleted = np.zeros(n_paths, dtype=np.bool_)
    depletion_month = np.full(n_paths, -1, dtype=np.int64)
    shortfall = np.zeros(n_paths, dtype=np.float64)

    for month in range(horizon_months):
        alive = month < death_month
        active = ~depleted & alive.any(axis=0)
        if not active.any():
            break
        income, spending = cash_flows.income(month, alive), cash_flows.spending(month, alive)
        result = apply_month(balance, rate, income, spending)
        newly_depleted = active & result.depleted
        balance = np.where(active, result.balance, balance)
        depletion_month[newly_depleted] = month
        shortfall[newly_depleted] = result.shortfall[newly_depleted]
        depleted |= newly_depleted
        if observer is not None:
            observer(month, balance, alive, active)

    return PathOutcomes(
        depletion_month=depletion_month,
        shortfall=shortfall,
        household_end_month=np.where(censored, -1, last_death).astype(np.int64),
        censored=censored,
        final_balance=balance,
    )
