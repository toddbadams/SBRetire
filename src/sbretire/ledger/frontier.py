"""Efficient frontier of the priced sleeve and the re-weighting analysis (F-029; portfolio-data §21–§24).

Analysis, not advice: every figure is estimated from past monthly returns.
"""

from __future__ import annotations

import csv
import datetime as dt
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.performance import monthly_rate
from sbretire.ledger.returns import MonthlyReturn, ReturnsReport, add_months

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


@dataclass(frozen=True)
class FrontierReport:
    """Everything ``sbretire portfolio frontier`` prints and writes."""

    report: ReturnsReport
    estimates: Estimates
    cap: float
    risk_free: float
    target_kind: TargetKind
    points: list[Mix]
    today: Mix
    minimum: Mix
    best: Mix
    target: Mix
    within: Mix
    household: dict[str, tuple[float, float, float]]
    trades: list[Trade]
    halves: tuple[Mix, Mix, float]
    min_trade: float
    warnings: list[str]

    @property
    def sleeve_share(self) -> float:
        sleeve = sum(self.report.series_values[s] for s in self.estimates.series)
        return sleeve / self.report.total_gbp if self.report.total_gbp else 0.0


def build_frontier(
    report: ReturnsReport,
    accounts: Sequence[AccountConfig],
    risk_free: float,
    cap: float,
    covariance: Covariance,
    target_kind: TargetKind,
    min_trade: float,
) -> FrontierReport:
    """Estimate the sleeve, find the mixes, plan the trades and test the target's stability (§21–§24).

    Raises ``ValueError`` with fewer than 2 full-history series or an infeasible ``cap``.
    """
    est = estimate(report.returns, report.series_values, report.first, report.last, covariance)
    _check_cap(est, cap)
    points = frontier(est, cap, risk_free)
    today = mix(est, est.today, risk_free)
    minimum = min_variance(est, cap, risk_free)
    best = max_sharpe(est, cap, risk_free)
    target = target_mix(est, cap, risk_free, target_kind)
    weights = dict(zip(est.series, target.weights.tolist(), strict=True))
    sleeve_values = {s: report.series_values[s] for s in est.series}
    household = household_trades(sleeve_values, weights)

    owner_of = {ref: s for s, refs in report.series_holdings.items() if s in sleeve_values for ref in refs}
    holdings: dict[str, dict[str, float]] = defaultdict(dict)
    for ref, value in report.holding_values.items():
        if ref in owner_of and value > 0:
            account = ref.split(":", 1)[0]
            holdings[account][owner_of[ref]] = holdings[account].get(owner_of[ref], 0.0) + value
    by_id = {a.id: a for a in accounts}
    costs: dict[str, tuple[float, float]] = {}
    warnings = [
        f"today's weight of {s} ({w:.1%}) is above max_weight {cap:.0%}"
        for s, w in zip(est.series, est.today, strict=True) if w > cap + 1e-9
    ]  # fmt: skip
    for account in holdings:
        config = by_id.get(account)
        if config is None or config.trading is None:
            if len(holdings[account]) > 1:
                warnings.append(f"account {account} has no trading costs in accounts.yaml; its trades cost 0")
            continue
        rate = (
            1.0 if config.currency == "GBP" else (report.usd_gbp or 0.0) if config.currency == "USD" else 0.0
        )
        costs[account] = (config.trading.fee_per_trade * rate, config.trading.cost_rate)
    plan = within_account_targets(holdings, weights)
    trades = plan_trades(holdings, plan, costs, min_trade)
    achieved = {s: 0.0 for s in est.series}
    traded = {(t.account, t.series): t.target_gbp for t in trades}
    for account, held in holdings.items():
        for series, value in held.items():
            achieved[series] += traded.get((account, series), value)
    unheld = {s: v for s, v in sleeve_values.items() if not any(s in held for held in holdings.values())}
    for series, value in unheld.items():
        achieved[series] += value
    within = mix(est, np.array([achieved[s] for s in est.series]), risk_free)
    halves = sensitivity(est, cap, risk_free, target_kind)
    return FrontierReport(
        report, est, cap, risk_free, target_kind, points, today, minimum, best, target, within, household,
        trades, halves, min_trade, warnings,
    )  # fmt: skip


def write_frontier_csvs(result: FrontierReport, folder: Path) -> None:
    """``frontier.csv``, ``frontier_weights.csv`` and ``trades.csv`` (UTF-8, LF; §24)."""
    folder.mkdir(parents=True, exist_ok=True)
    named = [("today", result.today), ("min_variance", result.minimum), ("max_sharpe", result.best),
             ("target", result.target), ("within_accounts", result.within)]  # fmt: skip
    with (folder / "frontier.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("point", "return", "volatility", "sharpe"))
        for i, point in enumerate(result.points, start=1):
            writer.writerow(
                (i, point.annual_return, point.volatility, "" if point.sharpe is None else point.sharpe)
            )
        for name, item in named:
            writer.writerow(
                (name, item.annual_return, item.volatility, "" if item.sharpe is None else item.sharpe)
            )
    with (folder / "frontier_weights.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("series", "name", *(name for name, _ in named)))
        for i, series in enumerate(result.estimates.series):
            name = result.report.series_names.get(series, series)
            writer.writerow((series, name, *(float(item.weights[i]) for _, item in named)))
    with (folder / "trades.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("scope", "account", "series", "current_gbp", "target_gbp", "trade_gbp", "cost_gbp"))
        for series, (current, goal, amount) in result.household.items():
            writer.writerow(
                ("household", "", series, round(current, 2), round(goal, 2), round(amount, 2), "")
            )
        for trade in result.trades:
            amounts = (trade.current_gbp, trade.target_gbp, trade.trade_gbp, trade.cost_gbp)
            writer.writerow(("account", trade.account, trade.series, *(round(a, 2) for a in amounts)))


_TARGET_LABELS: Final[dict[str, str]] = {
    "same-risk": "target (same risk as today)",
    "max-sharpe": "target (max Sharpe)",
    "min-variance": "target (min variance)",
}


def _row(label: str, item: Mix) -> str:
    sharpe = "n/a" if item.sharpe is None else f"{item.sharpe:.2f}"
    return f"  {label:<30} {item.annual_return:>8.2%} {item.volatility:>11.2%} {sharpe:>7}"


def format_frontier(result: FrontierReport) -> str:
    """The summary: sleeve, caveats, the mixes, their weights, the trades and the sensitivity."""
    report, est = result.report, result.estimates
    months = len(est.returns)
    method = (
        f"Ledoit-Wolf shrunk covariance (intensity {est.shrinkage:.2f})"
        if est.shrinkage is not None else "sample covariance"
    )  # fmt: skip
    lines = [
        f"Efficient frontier of the priced sleeve: {len(est.series)} series, {report.first:%Y-%m} to "
        f"{report.last:%Y-%m} ({months} months), {result.sleeve_share:.1%} of today's value "
        "(cash and other holdings stay as today)",
        f"  Risk from {method}; max weight {result.cap:.0%}; risk-free {result.risk_free:.2%} a year",
        "  Analysis, not advice: estimated from past monthly returns, a noisy guide to the future.",
        "  Moves between accounts or wrappers (pension, ISA, taxable) cannot be made as the household trades",
        "  show; the within-account trades keep each account's money where it is.",
        f"  {'mix':<30} {'return':>8} {'volatility':>11} {'sharpe':>7}",
        _row("today", result.today),
        _row("min variance", result.minimum),
        _row("max Sharpe", result.best),
        _row(_TARGET_LABELS[result.target_kind], result.target),
        _row("within accounts", result.within),
        f"  {'weights':<24} {'today':>7} {'min var':>8} {'max Sh.':>8} {'target':>7} {'within':>7}",
    ]
    for i, series in enumerate(est.series):
        lines.append(
            f"  {series[:24]:<24} {est.today[i]:>7.1%} {result.minimum.weights[i]:>8.1%} "
            f"{result.best.weights[i]:>8.1%} {result.target.weights[i]:>7.1%} "
            f"{result.within.weights[i]:>7.1%}"
        )
    lines.append(f"Trades within accounts (can be made; each at least {result.min_trade:,.0f} GBP):")
    if not result.trades:
        lines.append("  none: each account holds one priced series, or the moves are below the minimum")
    for trade in result.trades:
        lines.append(
            f"  {trade.account:<14} {trade.series[:22]:<22} {trade.trade_gbp:>+14,.2f} GBP  "
            f"cost {trade.cost_gbp:,.2f}"
        )
    if result.trades:
        lines.append(f"  total estimated cost {sum(t.cost_gbp for t in result.trades):,.2f} GBP")
    lines.append("Household trades (analysis only: they would need moves between accounts):")
    for series, (_, _, amount) in result.household.items():
        lines.append(f"  {series[:36]:<36} {amount:>+14,.2f} GBP")
    turnover = result.halves[2]
    lines.append(
        f"Sensitivity: the target estimated on each half of the window differs by a turnover of "
        f"{turnover:.1%} "
        "(0% = identical; high values mean the mix is not reliable)"
    )
    lines += [f"warning: {warning}" for warning in [*report.warnings, *result.warnings]]
    return "\n".join(lines)
