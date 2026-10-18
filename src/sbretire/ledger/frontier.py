"""Efficient frontier of the priced sleeve and the re-weighting analysis (F-029; portfolio-data §21–§24).

Analysis, not advice: every figure is estimated from past monthly returns.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from sbretire.ledger.performance import monthly_rate
from sbretire.ledger.returns import MonthlyReturn, add_months

Covariance = Literal["shrunk", "sample"]


def ledoit_wolf(samples: NDArray[np.float64]) -> tuple[NDArray[np.float64], float]:
    """(covariance, intensity): the sample covariance (÷ T) shrunk towards ``m·I``, ``m`` its mean variance.

    Ledoit & Wolf (2004), "Honey, I shrunk the sample covariance matrix": intensity ``min(b̄², d²) / d²`` with
    ``d²`` the distance of the sample covariance from the target and ``b̄²`` the estimation noise.
    """
    t, n = samples.shape
    centred = samples - samples.mean(axis=0)
    sample = centred.T @ centred / t
    m = float(np.trace(sample)) / n
    target = m * np.eye(n)
    d2 = float(np.sum((sample - target) ** 2)) / n
    outer = np.einsum("ti,tj->tij", centred, centred)
    b_bar2 = float(np.sum((outer - sample) ** 2)) / n / t**2
    shrink = 0.0 if d2 == 0.0 else min(b_bar2, d2) / d2
    return shrink * target + (1.0 - shrink) * sample, shrink


@dataclass(frozen=True)
class Estimates:
    """Annual expected returns and covariance of the priced sleeve, and today's sleeve weights."""

    series: list[str]
    mean: NDArray[np.float64]
    """Annual: 12 × the mean monthly return."""
    cov: NDArray[np.float64]
    """Annual: 12 × the monthly covariance (Ledoit-Wolf shrunk or sample)."""
    shrinkage: float | None
    today: NDArray[np.float64]
    """Today's weights within the sleeve (sum 1)."""
    returns: NDArray[np.float64]
    """Monthly returns, months × series, for re-estimating on sub-windows."""
    covariance: Covariance = "shrunk"


def estimate(
    returns: Sequence[MonthlyReturn],
    values: Mapping[str, float],
    first: dt.date,
    last: dt.date,
    covariance: Covariance = "shrunk",
) -> Estimates:
    """Estimates over the priced sleeve: series with today's value > 0 and a return in every month (§21).

    The sample option uses the n − 1 sample covariance; the shrunk option Ledoit-Wolf's (÷ T) estimate.
    """
    months: list[dt.date] = []
    month = first
    while month <= last:
        months.append(month)
        month = add_months(month, 1)
    by_series: dict[str, dict[dt.date, float]] = defaultdict(dict)
    for row in returns:
        if row.return_gbp is not None:
            by_series[row.series][row.month] = row.return_gbp
    sleeve = [
        series for series, value in values.items()
        if value > 0 and all(month in by_series.get(series, {}) for month in months)
    ]  # fmt: skip
    matrix = np.array([[by_series[s][m] for s in sleeve] for m in months], dtype=np.float64).reshape(
        len(months), len(sleeve)
    )
    shrinkage: float | None
    if covariance == "shrunk" and sleeve:
        monthly_cov, shrinkage = ledoit_wolf(matrix)
    else:
        monthly_cov = np.cov(matrix, rowvar=False, ddof=1).reshape(len(sleeve), len(sleeve))
        shrinkage = None
    weights = np.array([values[s] for s in sleeve], dtype=np.float64)
    today = weights / weights.sum() if weights.size else weights
    return Estimates(
        sleeve, 12.0 * matrix.mean(axis=0), 12.0 * monthly_cov, shrinkage, today, matrix, covariance
    )


@dataclass(frozen=True)
class Mix:
    """Sleeve weights and their annual return, volatility and Sharpe ratio (None when volatility is zero)."""

    weights: NDArray[np.float64]
    annual_return: float
    volatility: float
    sharpe: float | None


_TOL: Final = 1e-12


def mix(est: Estimates, weights: NDArray[np.float64], risk_free: float) -> Mix:
    """Annual return ``w·μ``, volatility ``√(wᵀΣw)`` and Sharpe ``(w·μ − 12·r_f,month) / σ`` (§22)."""
    w = np.clip(np.asarray(weights, dtype=np.float64), 0.0, None)
    w = w / w.sum()
    ret = float(w @ est.mean)
    vol = float(np.sqrt(max(float(w @ est.cov @ w), 0.0)))
    excess = ret - 12.0 * monthly_rate(risk_free)
    return Mix(w, ret, vol, excess / vol if vol > 1e-12 else None)


def _check_cap(est: Estimates, cap: float) -> None:
    if len(est.series) < 2:
        raise ValueError(
            f"the frontier needs at least 2 priced series with a full history (found {len(est.series)})"
        )
    if cap * len(est.series) < 1.0 - 1e-12:
        raise ValueError(
            f"max_weight {cap:g} × {len(est.series)} series < 1: no mix can add up to 100%; raise max_weight"
        )


def _solve(
    est: Estimates,
    cap: float,
    objective: Callable[[NDArray[np.float64]], float],
    starts: Sequence[NDArray[np.float64]],
    extra: Sequence[dict[str, object]] = (),
) -> NDArray[np.float64]:
    """SLSQP over long-only capped weights summing to 1, from each start; the best feasible result."""
    n = len(est.series)
    constraints = [{"type": "eq", "fun": lambda w: float(np.sum(w)) - 1.0}, *extra]
    best: NDArray[np.float64] | None = None
    best_value = np.inf
    for start in starts:
        result = minimize(
            objective, start, method="SLSQP", bounds=[(0.0, cap)] * n, constraints=constraints,
            options={"ftol": _TOL, "maxiter": 1000},
        )  # fmt: skip
        w = np.clip(result.x, 0.0, cap)
        feasible = abs(w.sum() - 1.0) < 1e-6 and all(
            float(c["fun"](w)) >= -1e-7 if c["type"] == "ineq" else abs(float(c["fun"](w))) < 1e-6  # type: ignore[operator]
            for c in extra
        )
        if feasible and float(objective(w)) < best_value:
            best, best_value = w, float(objective(w))
    if best is None:
        raise ValueError("the optimiser found no feasible mix")
    return best


def _equal(est: Estimates) -> NDArray[np.float64]:
    return np.full(len(est.series), 1.0 / len(est.series))


def min_variance(est: Estimates, cap: float, risk_free: float = 0.0) -> Mix:
    """The lowest-volatility long-only mix with every weight ≤ ``cap`` (§22)."""
    _check_cap(est, cap)
    w = _solve(est, cap, lambda w: float(w @ est.cov @ w), [_equal(est), np.clip(est.today, 0, cap)])
    return mix(est, w, risk_free)


def _greedy_max_return(est: Estimates, cap: float) -> NDArray[np.float64]:
    """The highest-return mix under the cap: fill the best-returning series to the cap, in order."""
    w = np.zeros(len(est.series))
    left = 1.0
    for i in np.argsort(-est.mean):
        w[i] = min(cap, left)
        left -= w[i]
        if left <= 1e-12:
            break
    return w


def frontier(est: Estimates, cap: float, risk_free: float, points: int = 21) -> list[Mix]:
    """``points`` minimum-variance mixes, from the minimum-variance return to the highest the cap allows."""
    low = min_variance(est, cap, risk_free)
    top = _greedy_max_return(est, cap)
    high = float(top @ est.mean)
    mixes = [low]
    previous = low.weights
    for target in np.linspace(low.annual_return, high, points)[1:-1]:
        aim = float(target)
        w = _solve(
            est, cap, lambda w: float(w @ est.cov @ w), [previous, top],
            extra=[{"type": "eq", "fun": lambda w, aim=aim: float(w @ est.mean) - aim}],
        )  # fmt: skip
        mixes.append(mix(est, w, risk_free))
        previous = w
    mixes.append(mix(est, top, risk_free))
    return mixes


def max_sharpe(est: Estimates, cap: float, risk_free: float) -> Mix:
    """The mix with the highest Sharpe ratio, searched from every frontier point (§22)."""
    points = frontier(est, cap, risk_free)
    excess = 12.0 * monthly_rate(risk_free)

    def negative_sharpe(w: NDArray[np.float64]) -> float:
        vol = float(np.sqrt(max(float(w @ est.cov @ w), 1e-18)))
        return -(float(w @ est.mean) - excess) / vol

    w = _solve(est, cap, negative_sharpe, [m.weights for m in points])
    best = mix(est, w, risk_free)
    for point in points:  # never worse than the frontier itself
        if (point.sharpe or -np.inf) > (best.sharpe or -np.inf):
            best = point
    return best


def max_return_at(est: Estimates, cap: float, risk_free: float, volatility: float) -> Mix:
    """The highest-return mix with volatility ≤ ``volatility``; minimum variance if that is lower (§22)."""
    low = min_variance(est, cap, risk_free)
    if volatility <= low.volatility:
        return low
    level = volatility**2
    starts = [m.weights for m in frontier(est, cap, risk_free) if m.volatility <= volatility]
    w = _solve(
        est, cap, lambda w: -float(w @ est.mean), starts,
        extra=[{"type": "ineq", "fun": lambda w: level - float(w @ est.cov @ w)}],
    )  # fmt: skip
    return mix(est, w, risk_free)


def household_trades(
    today: Mapping[str, float], target: Mapping[str, float]
) -> dict[str, tuple[float, float, float]]:
    """Series → (today's GBP, target GBP, trade GBP), the sleeve as one portfolio (§23; analysis only)."""
    sleeve = sum(today.values())
    return {
        series: (value, target.get(series, 0.0) * sleeve, target.get(series, 0.0) * sleeve - value)
        for series, value in today.items()
    }


def within_account_targets(
    holdings: Mapping[str, Mapping[str, float]], target: Mapping[str, float]
) -> dict[str, dict[str, float]]:
    """Account → series → target GBP: each account's sleeve re-split over the series it holds (§23).

    Weights are the target's for those series, rescaled to the account; an account whose series all have
    target 0 keeps today's split.
    """
    split: dict[str, dict[str, float]] = {}
    for account, held in holdings.items():
        total = sum(held.values())
        weight = sum(target.get(series, 0.0) for series in held)
        if weight <= 0.0:
            split[account] = dict(held)
        else:
            split[account] = {series: total * target.get(series, 0.0) / weight for series in held}
    return split


def trade_cost(amount_gbp: float, fee_gbp: float, rate: float) -> float:
    """A trade's estimated cost in GBP: the fixed fee plus ``rate × |amount|``; nothing for no trade (§24)."""
    return 0.0 if amount_gbp == 0.0 else fee_gbp + rate * abs(amount_gbp)


@dataclass(frozen=True)
class Trade:
    scope: Literal["household", "account"]
    account: str
    series: str
    current_gbp: float
    target_gbp: float
    trade_gbp: float
    cost_gbp: float


def plan_trades(
    holdings: Mapping[str, Mapping[str, float]],
    targets: Mapping[str, Mapping[str, float]],
    costs: Mapping[str, tuple[float, float]],
    min_trade: float,
) -> list[Trade]:
    """Within-account trades of at least ``min_trade`` GBP; costs from ``costs[account] = (fee GBP, rate)``.

    An account missing from ``costs`` trades at no cost.
    """
    trades = []
    for account, held in holdings.items():
        fee, rate = costs.get(account, (0.0, 0.0))
        for series, value in held.items():
            goal = targets[account].get(series, value)
            amount = goal - value
            if abs(amount) < min_trade:
                continue
            trades.append(
                Trade("account", account, series, value, goal, amount, trade_cost(amount, fee, rate))
            )
    return trades


TargetKind = Literal["same-risk", "max-sharpe", "min-variance"]


def target_mix(est: Estimates, cap: float, risk_free: float, target: TargetKind) -> Mix:
    """The mix the trades move towards (§22): same risk as today (default), max Sharpe or minimum variance."""
    if target == "max-sharpe":
        return max_sharpe(est, cap, risk_free)
    if target == "min-variance":
        return min_variance(est, cap, risk_free)
    return max_return_at(est, cap, risk_free, mix(est, est.today, risk_free).volatility)


def _sub_estimates(est: Estimates, rows: NDArray[np.float64]) -> Estimates:
    if est.covariance == "shrunk":
        monthly_cov, shrinkage = ledoit_wolf(rows)
    else:
        monthly_cov, shrinkage = np.cov(rows, rowvar=False, ddof=1), None
    return Estimates(est.series, 12.0 * rows.mean(axis=0), 12.0 * monthly_cov, shrinkage, est.today, rows,
                     est.covariance)  # fmt: skip


def sensitivity(est: Estimates, cap: float, risk_free: float, target: TargetKind) -> tuple[Mix, Mix, float]:
    """The target re-estimated on each half of the window, and its turnover ``Σ|w₁ − w₂| / 2`` (§24)."""
    half = len(est.returns) // 2
    first = target_mix(_sub_estimates(est, est.returns[:half]), cap, risk_free, target)
    second = target_mix(_sub_estimates(est, est.returns[half:]), cap, risk_free, target)
    return first, second, float(np.abs(first.weights - second.weights).sum() / 2.0)
