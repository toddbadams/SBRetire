"""Maximum Sustainable Budget by per-path threshold bisection (SPEC §14; optimization §1).

With one :class:`~sbretire.monte_carlo.RandomInputs` reused for every candidate (Common Random Numbers), a
Path's success is monotone non-increasing in the Budget, so each Path whose household ends within the Horizon
has a threshold: the largest Budget (today's GBP per month) at which it is Successful. All such Paths are
bisected together — each gets its own candidate budget in one vectorised engine run — and the Conservative
Success Rate at a budget B is then the share of Paths whose threshold is at least B. Paths with someone alive
at the Horizon are never Successful at any budget.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

import numpy as np

from sbretire.config import Scenario
from sbretire.metrics import PathClass, classify_paths
from sbretire.monte_carlo import RandomInputs, required_end_balance, run_monte_carlo
from sbretire.portfolio import BoolArray, FloatArray

BUDGET_TOLERANCE: Final = 1.0
"""Bisection stops when every bracket is at most this wide (GBP per month, today's money)."""
BUDGET_CAP: Final = 1_000_000.0
"""Largest budget tried (GBP per month); paths still Successful here are flagged ``capped``."""
_MINIMUM_START: Final = 1_000.0


@dataclass(frozen=True)
class ThresholdSearch:
    """Per-path success thresholds for one Scenario and one set of random inputs."""

    thresholds: FloatArray
    """(n_paths,) largest budget found Successful (feasible end of a ≤ £1 bracket); -inf if it never is."""
    capped: BoolArray
    """(n_paths,) still Successful at :data:`BUDGET_CAP`."""
    iterations: int
    """Engine runs: upper-bound doublings plus bisection rounds."""
    upper_bound: float
    """Final upper bound (GBP per month) at which every completed-by-death path failed, or the cap."""
    scenario: Scenario = field(repr=False)
    inputs: RandomInputs = field(repr=False)
    end_reserve_months: int = 0
    """End-of-Life Reserve applied to success (0 = the V1 test; optimization §3)."""


def _successful(
    scenario: Scenario, inputs: RandomInputs, budgets: FloatArray, end_reserve_months: int = 0
) -> BoolArray:
    outcomes = run_monte_carlo(scenario, inputs, monthly_budget_today=budgets).outcomes
    required = None
    if end_reserve_months:
        required = required_end_balance(inputs, outcomes, budgets, end_reserve_months)
    result: BoolArray = classify_paths(outcomes, required) == PathClass.SUCCESSFUL
    return result


def path_budget_thresholds(
    scenario: Scenario, inputs: RandomInputs, end_reserve_months: int = 0
) -> ThresholdSearch:
    """Bisect every path's success threshold at once (optimization §1).

    Lower bound £0 (always feasible for a path whose household ends in the Horizon); the upper bound starts
    at 2 × the configured Budget (or £1,000) and doubles until every such path fails, capped at
    :data:`BUDGET_CAP`. ``end_reserve_months`` > 0 searches for success leaving the End-of-Life Reserve
    (optimization §3); success stays monotone in the budget, so the same bisection applies.
    """
    n_paths = inputs.n_paths
    completed = inputs.death_months.max(axis=0) < scenario.model.horizon_years * 12
    upper = min(max(2.0 * scenario.budget.monthly_amount_today, _MINIMUM_START), BUDGET_CAP)
    iterations = 0
    while True:
        ok_at_upper = _successful(scenario, inputs, np.full(n_paths, upper), end_reserve_months)
        iterations += 1
        if not np.any(ok_at_upper & completed) or upper >= BUDGET_CAP:
            break
        upper = min(2.0 * upper, BUDGET_CAP)
    capped = completed & ok_at_upper
    active = completed & ~capped
    low = np.zeros(n_paths)
    high = np.full(n_paths, upper)
    while np.any(active & (high - low > BUDGET_TOLERANCE)):
        middle = np.where(active, (low + high) / 2.0, 0.0)
        ok = _successful(scenario, inputs, middle, end_reserve_months)
        iterations += 1
        low = np.where(active & ok, middle, low)
        high = np.where(active & ~ok, middle, high)
    thresholds = np.where(completed, np.where(capped, BUDGET_CAP, low), -np.inf)
    return ThresholdSearch(thresholds, capped, iterations, upper, scenario, inputs, end_reserve_months)


@dataclass(frozen=True)
class BudgetResult:
    """One SPEC §14 row: the Maximum Sustainable Budget for a target probability."""

    target_probability: float
    maximum_monthly_budget_today: float | None
    """B* in today's GBP per month; None when the target is infeasible."""
    maximum_annual_budget_today: float | None
    """12 × B*."""
    estimated_success_probability: float | None
    """Conservative Success Rate at B*, from a confirming run on the same random inputs."""
    standard_error: float | None
    """Binomial SE of that rate; denominator: all paths."""
    unresolved_fraction: float
    """Share of paths never depleted with someone alive at the Horizon, at B* (at £0 when infeasible)."""
    budget_tolerance: float
    converged: bool
    iterations: int
    note: str


def maximum_sustainable_budgets(search: ThresholdSearch, targets: Sequence[float]) -> list[BudgetResult]:
    """B* per target p*: the ⌈p*·N⌉-th largest threshold, confirmed by one run at B* (optimization §1)."""
    n_paths = len(search.thresholds)
    ordered = np.sort(search.thresholds)[::-1]
    unresolved_at_zero = float(np.mean(~np.isfinite(search.thresholds)))
    results = []
    for target in targets:
        needed = math.ceil(target * n_paths)
        if not np.isfinite(ordered[needed - 1]):
            completed = int(np.isfinite(search.thresholds).sum())
            note = (
                f"infeasible: only {completed:,} of {n_paths:,} paths can succeed within the horizon "
                f"({completed / n_paths:.2%}) even at a budget of 0"
            )
            results.append(
                BudgetResult(
                    target,
                    None,
                    None,
                    None,
                    None,
                    unresolved_at_zero,
                    BUDGET_TOLERANCE,
                    False,
                    search.iterations,
                    note,
                )
            )
            continue
        budget = float(ordered[needed - 1])
        metrics = run_monte_carlo(
            search.scenario,
            search.inputs,
            monthly_budget_today=budget,
            end_reserve_months=search.end_reserve_months,
        ).metrics
        at_cap = budget >= BUDGET_CAP
        note = f"reached cap of {BUDGET_CAP:,.0f} GBP/month; the true maximum may be higher" if at_cap else ""
        results.append(
            BudgetResult(
                target_probability=target,
                maximum_monthly_budget_today=budget,
                maximum_annual_budget_today=12.0 * budget,
                estimated_success_probability=metrics.conservative_success_rate,
                standard_error=metrics.conservative_standard_error,
                unresolved_fraction=metrics.unresolved_share,
                budget_tolerance=BUDGET_TOLERANCE,
                converged=not at_cap,
                iterations=search.iterations,
                note=note,
            )
        )
    return results


RETURN_LOWER: Final = -0.5
"""Lowest fixed annual effective return tried (−50 % a year)."""
RETURN_UPPER: Final = 0.5
"""Highest fixed annual effective return tried (+50 % a year)."""
RETURN_TOLERANCE: Final = 0.0001
"""Bisection stops when every bracket is at most this wide (0.01 percentage points of annual return)."""


@dataclass(frozen=True)
class ReturnSearch:
    """Per-path minimum annual returns for one Budget and one set of random inputs (optimization §2)."""

    thresholds: FloatArray
    """(n_paths,) smallest annual return found Successful (feasible end of a bracket); +inf if none."""
    at_lower_bound: BoolArray
    """(n_paths,) Successful even at :data:`RETURN_LOWER`."""
    iterations: int
    """Engine runs: the two bound checks plus bisection rounds."""
    monthly_budget_today: float
    scenario: Scenario = field(repr=False)
    inputs: RandomInputs = field(repr=False)


def _successful_at(scenario: Scenario, inputs: RandomInputs, budget: float, returns: FloatArray) -> BoolArray:
    outcomes = run_monte_carlo(scenario, inputs, monthly_budget_today=budget, annual_return=returns).outcomes
    result: BoolArray = classify_paths(outcomes) == PathClass.SUCCESSFUL
    return result


def path_return_thresholds(
    scenario: Scenario, inputs: RandomInputs, monthly_budget_today: float | None = None
) -> ReturnSearch:
    """Bisect every path's minimum annual return at once, between fixed bounds −50 % and +50 % (§2).

    Success is monotone non-decreasing in the return (balance never negative; return on the opening
    balance), so each path that can succeed in range has a threshold; others get +inf.
    """
    budget = scenario.budget.monthly_amount_today if monthly_budget_today is None else monthly_budget_today
    n_paths = inputs.n_paths
    ok_low = _successful_at(scenario, inputs, budget, np.full(n_paths, RETURN_LOWER))
    ok_high = _successful_at(scenario, inputs, budget, np.full(n_paths, RETURN_UPPER))
    iterations = 2
    active = ok_high & ~ok_low
    low = np.full(n_paths, RETURN_LOWER)
    high = np.full(n_paths, RETURN_UPPER)
    while np.any(active & (high - low > RETURN_TOLERANCE)):
        middle = np.where(active, (low + high) / 2.0, RETURN_UPPER)
        ok = _successful_at(scenario, inputs, budget, middle)
        iterations += 1
        high = np.where(active & ok, middle, high)
        low = np.where(active & ~ok, middle, low)
    thresholds = np.where(ok_low, RETURN_LOWER, np.where(ok_high, high, np.inf))
    return ReturnSearch(thresholds, ok_low, iterations, float(budget), scenario, inputs)


@dataclass(frozen=True)
class ReturnResult:
    """One SPEC §13 row: the minimum fixed annual return reaching a target at a fixed Budget."""

    monthly_budget_today: float
    target_probability: float
    required_annual_return: float | None
    """Annual effective return r*; None when no solution lies within the bounds."""
    estimated_success_probability: float | None
    """Conservative Success Rate at r*, from a confirming run on the same random inputs."""
    standard_error: float | None
    """Binomial SE of that rate; denominator: all paths."""
    unresolved_fraction: float
    return_tolerance: float
    converged: bool
    iterations: int
    note: str


def required_returns(search: ReturnSearch, targets: Sequence[float]) -> list[ReturnResult]:
    """r* per target p*: the ⌈p*·N⌉-th smallest threshold, confirmed by one run at r* (optimization §2)."""
    n_paths = len(search.thresholds)
    ordered = np.sort(search.thresholds)
    results = []
    for target in targets:
        needed = math.ceil(target * n_paths)
        candidate = float(ordered[needed - 1])
        if not np.isfinite(candidate):
            reachable = int(np.isfinite(search.thresholds).sum())
            at_upper = run_monte_carlo(
                search.scenario, search.inputs, search.monthly_budget_today, annual_return=RETURN_UPPER
            ).metrics
            note = (
                f"no solution within bounds: only {reachable:,} of {n_paths:,} paths succeed even at "
                f"+{RETURN_UPPER:.0%} a year"
            )
            results.append(
                ReturnResult(
                    search.monthly_budget_today,
                    target,
                    None,
                    None,
                    None,
                    at_upper.unresolved_share,
                    RETURN_TOLERANCE,
                    False,
                    search.iterations,
                    note,
                )
            )
            continue
        metrics = run_monte_carlo(
            search.scenario, search.inputs, search.monthly_budget_today, annual_return=candidate
        ).metrics
        at_lower = candidate <= RETURN_LOWER
        note = f"at or below {RETURN_LOWER:.0%} a year (the lower search bound)" if at_lower else ""
        results.append(
            ReturnResult(
                monthly_budget_today=search.monthly_budget_today,
                target_probability=target,
                required_annual_return=candidate,
                estimated_success_probability=metrics.conservative_success_rate,
                standard_error=metrics.conservative_standard_error,
                unresolved_fraction=metrics.unresolved_share,
                return_tolerance=RETURN_TOLERANCE,
                converged=not at_lower,
                iterations=search.iterations,
                note=note,
            )
        )
    return results
