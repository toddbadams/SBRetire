"""``portfolio.json``: every portfolio analysis in one document for the Portfolio page (F-030; §25).

Each analysis section has ``available``; with missing inputs it is ``{"available": false, "reason": …}``.
Invalid configuration (a bad map or factsheet) still raises, so the command exits 2.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Final

import numpy as np

from sbretire.ledger.account_returns import AccountReturn, build_account_returns
from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.exposure import DIMENSIONS, build_exposure
from sbretire.ledger.extras import (
    calendar,
    correlation,
    drawdown_episodes,
    income_by_month,
    risk_contribution,
)
from sbretire.ledger.frontier import Covariance, FrontierReport, Mix, TargetKind, build_frontier
from sbretire.ledger.holdings import Holding
from sbretire.ledger.merge import build_ledger
from sbretire.ledger.model import UnknownTransaction
from sbretire.ledger.performance import Performance, build_performance, monthly_rate
from sbretire.ledger.returns import ReturnsReport, build_returns, window

SCHEMA_VERSION: Final = "1.1"
JS_PREFIX: Final = "window.SBRETIRE_PORTFOLIO = "
PAGE_FILES: Final = {
    "portfolio.html": ("portfolio", "portfolio.html"),
    "portfolio-view.css": ("portfolio", "portfolio-view.css"),
    "portfolio-view.js": ("portfolio", "portfolio-view.js"),
    "viewer.css": ("viewer", "viewer.css"),
    "theme.css": ("theme.css",),
}
"""Page files copied into the output folder, and where each lives under ``sbretire/web`` (viewer §4)."""


@dataclass(frozen=True)
class ReportOptions:
    """Inputs and settings for ``sbretire portfolio report`` (the options of the other portfolio commands)."""

    root: Path
    prices: Path
    factsheets: Path
    months: int = 60
    usd_gbp: float | None = None
    risk_free: float | None = None
    max_weight: float | None = None
    covariance: Covariance = "shrunk"
    target: TargetKind = "same-risk"
    min_trade: float = 50.0
    synthetic: bool = False


def _off(reason: str) -> dict[str, object]:
    return {"available": False, "reason": reason}


def _ym(month: dt.date | None) -> str | None:
    return None if month is None else f"{month:%Y-%m}"


def _num(value: float | None) -> float | None:
    return None if value is None or not np.isfinite(value) else float(value)


def _mix(item: Mix, series: Sequence[str]) -> dict[str, object]:
    return {
        "return": float(item.annual_return),
        "volatility": float(item.volatility),
        "sharpe": _num(item.sharpe),
        "weights": {s: float(w) for s, w in zip(series, item.weights, strict=True)},
    }


def build_portfolio_document(options: ReportOptions, accounts: Sequence[AccountConfig]) -> dict[str, object]:
    """Run every analysis whose inputs exist and assemble ``portfolio.json`` (schema 1.0, §25)."""
    report = build_returns(options.root, accounts, options.prices, options.months, options.usd_gbp)
    exposure_report = build_exposure(
        options.root, accounts, options.prices, options.factsheets, options.usd_gbp
    )
    today = exposure_report.today
    valuation = today.valuation
    warnings: list[str] = list(dict.fromkeys([*report.warnings, *exposure_report.warnings]))
    risk_free = options.risk_free if options.risk_free is not None else report.risk_free_rate
    cap = options.max_weight if options.max_weight is not None else report.max_weight

    by_account = valuation.by_account()
    dates = valuation.dates()
    total = valuation.total_gbp()
    span = sorted(on for on, _ in dates.values())
    names = {a.id: a for a in accounts}
    document: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "synthetic": options.synthetic,
        "folder": today.folder,
        "settings": {
            "months": options.months,
            "first": _ym(report.first),
            "last": _ym(report.last),
            "risk_free_rate": risk_free,
            "max_weight": cap,
            "usd_gbp": today.usd_gbp,
            "usd_gbp_source": today.rate_source if today.usd_gbp is not None else None,
            "covariance": options.covariance,
            "target": options.target,
            "min_trade_gbp": options.min_trade,
        },
        "people": sorted({a.owner for a in accounts}),
        "total": {
            "value_gbp": total,
            "cash_gbp": round(sum(today.cash.values()), 2),
            "by_owner": valuation.by_owner(),
            "starting_balance": round(total),
            "starting_balance_yaml": f"starting_balance: {round(total)}  # sbretire portfolio report: "
            f"{today.folder}, {span[0].isoformat()} to {span[-1].isoformat()}",
        },
        "accounts": [
            {
                "id": account_id,
                "name": names[account_id].name if account_id in names else account_id,
                "provider": names[account_id].provider if account_id in names else "",
                "wrapper": names[account_id].wrapper if account_id in names else "",
                "owner": names[account_id].owner if account_id in names else "",
                "currency": names[account_id].currency if account_id in names else "GBP",
                "securities_gbp": securities,
                "cash_gbp": cash,
                "value_gbp": round(securities + cash, 2),
                "valuation_date": dates[account_id][0].isoformat(),
                "date_assumed": not dates[account_id][1],
            }
            for account_id, (securities, cash) in by_account.items()
        ],
    }

    performance = _performance(report, risk_free)
    frontier = _frontier(report, accounts, risk_free, cap, options)
    document["holdings"] = _holdings(report, valuation.holdings, total, performance)
    document["exposure"] = _exposure(exposure_report, options.prices)
    document["performance"] = _performance_section(performance, report, risk_free)
    document["frontier"], document["risk"], document["rebalance"] = _frontier_sections(frontier, report)
    document["income"] = _income(options, accounts, today.folder, today.usd_gbp)
    document["account_returns"] = _account_returns(options, accounts)
    if isinstance(frontier, FrontierReport):
        warnings += frontier.warnings
    document["warnings"] = list(dict.fromkeys(warnings))
    document["data_files"] = [
        {
            "series": series,
            "file": prices.path.name,
            "sha256": prices.sha256,
            "first": prices.first.isoformat(),
            "last": prices.last.isoformat(),
            "rows": prices.rows,
            "basis": prices.basis,
        }
        for series, prices in report.files
    ]
    return document


def _performance(report: ReturnsReport, risk_free: float | None) -> Performance | str:
    if not report.series_values:
        return "no price history yet: add price files and data/prices/securities.yaml (see README)"
    if risk_free is None:
        return "no risk-free rate: set risk_free_rate in securities.yaml or pass --risk-free"
    return build_performance(report, risk_free, "securities.yaml")


def _frontier(
    report: ReturnsReport,
    accounts: Sequence[AccountConfig],
    risk_free: float | None,
    cap: float,
    options: ReportOptions,
) -> FrontierReport | str:
    if risk_free is None:
        return "no risk-free rate: set risk_free_rate in securities.yaml or pass --risk-free"
    try:
        return build_frontier(
            report, accounts, risk_free, cap, options.covariance, options.target, options.min_trade
        )
    except ValueError as exc:
        return str(exc)


def _holdings(
    report: ReturnsReport, holdings: Sequence[Holding], total: float, performance: Performance | str
) -> list[dict[str, object]]:
    series_of = {ref: s for s, refs in report.series_holdings.items() for ref in refs}
    status = {row.series: row for row in report.coverage if row.series}
    metrics = {} if isinstance(performance, str) else {s.series: s.metrics for s in performance.series}
    rows: list[tuple[float, dict[str, object]]] = []
    for holding in holdings:
        if holding.kind != "security":
            continue
        ref = f"{holding.account}:{holding.security_key}"
        series = series_of.get(ref)
        value = report.holding_values.get(ref, 0.0)
        found = metrics.get(series) if series else None
        covered = status.get(series) if series else None
        rows.append(
            (
                value,
                {
                    "ref": ref,
                    "account": holding.account,
                    "security_key": holding.security_key,
                    "name": holding.security_name,
                    "series": series,
                    "value_gbp": round(value, 2),
                    "weight": value / total if total else 0.0,
                    "return_ann": _num(found.annual_return) if found else None,
                    "volatility_ann": _num(found.annual_volatility) if found else None,
                    "sharpe": _num(found.sharpe) if found else None,
                    "history_months": covered.months if covered else 0,
                    "status": covered.status if covered else "missing",
                },
            )
        )
    return [row for _, row in sorted(rows, key=lambda item: -item[0])]


def _exposure(report: object, prices: Path) -> dict[str, object]:
    if not (prices / "securities.yaml").exists():
        return _off(
            "no data/prices/securities.yaml: add factsheets and stock sectors to look through the funds"
        )
    exposure = report.exposure  # type: ignore[attr-defined]
    total = exposure.total_gbp or 1.0
    return {
        "available": True,
        "tables": {
            dimension: [
                {"label": label, "value_gbp": round(value, 2), "share": value / total}
                for label, value in sorted(exposure.tables[dimension].items(), key=lambda i: -i[1])
            ]
            for dimension in DIMENSIONS
        },
        "approximated_currency_share": exposure.approximated_currency_gbp / total,
        "top_holdings": [
            {"name": n, "value_gbp": round(v, 2), "share": v / total} for n, v in exposure.top_holdings
        ],
    }


def _performance_section(
    performance: Performance | str, report: ReturnsReport, risk_free: float | None
) -> dict[str, object]:
    if isinstance(performance, str):
        return _off(performance)
    m = performance.metrics
    months = [b.month for b in performance.months]
    values = [b.portfolio_return for b in performance.months]
    return {
        "available": True,
        "metrics": {
            "months": m.months,
            "annual_return": _num(m.annual_return),
            "annual_volatility": _num(m.annual_volatility),
            "sharpe": _num(m.sharpe),
            "max_drawdown": m.max_drawdown,
            "peak": _ym(m.peak),
            "trough": _ym(m.trough),
            "recovery": _ym(m.recovery),
        },
        "months": [
            {
                "month": _ym(b.month),
                "return": b.portfolio_return,
                "wealth": performance.wealth[i],
                "drawdown": performance.drawdown[i],
                "covered": b.covered_share,
                "rolling_12m_return": performance.rolling_return[i],
                "rolling_12m_volatility": performance.rolling_volatility[i],
            }
            for i, b in enumerate(performance.months)
        ],
        "calendar": calendar(months, values),
        "drawdowns": drawdown_episodes(months, values),
        "series": [
            {
                "series": s.series,
                "name": s.name,
                "weight": s.weight,
                "months": s.metrics.months,
                "annual_return": _num(s.metrics.annual_return),
                "annual_volatility": _num(s.metrics.annual_volatility),
                "sharpe": _num(s.metrics.sharpe),
                "max_drawdown": s.metrics.max_drawdown,
            }
            for s in performance.series
        ],
    }


def _frontier_sections(
    frontier: FrontierReport | str, report: ReturnsReport
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    if isinstance(frontier, str):
        return _off(frontier), _off(frontier), _off(frontier)
    est = frontier.estimates
    series = est.series
    rf = 12.0 * monthly_rate(frontier.risk_free)
    section: dict[str, object] = {
        "available": True,
        "series": series,
        "names": {s: report.series_names.get(s, s) for s in series},
        "sleeve_share": frontier.sleeve_share,
        "max_weight": frontier.cap,
        "covariance": est.covariance,
        "shrinkage": _num(est.shrinkage),
        "target_kind": frontier.target_kind,
        "risk_free": rf,
        "points": [
            {"return": p.annual_return, "volatility": p.volatility, "sharpe": _num(p.sharpe)}
            for p in frontier.points
        ],
        "mixes": {
            "today": _mix(frontier.today, series),
            "min_variance": _mix(frontier.minimum, series),
            "max_sharpe": _mix(frontier.best, series),
            "target": _mix(frontier.target, series),
            "within_accounts": _mix(frontier.within, series),
        },
        "holdings_points": [
            {"series": s, "return": float(est.mean[i]), "volatility": float(np.sqrt(est.cov[i, i]))}
            for i, s in enumerate(series)
        ],
        "turnover": frontier.halves[2],
    }
    shares = risk_contribution(est.today, est.cov)
    risk: dict[str, object] = {
        "available": True,
        "series": series,
        "correlation": correlation(est.cov).tolist(),
        "contribution": [
            {"series": s, "weight": float(est.today[i]), "risk_share": float(shares[i])}
            for i, s in enumerate(series)
        ],
    }
    rebalance: dict[str, object] = {
        "available": True,
        "target_kind": frontier.target_kind,
        "household": [
            {"series": s, "current_gbp": round(c, 2), "target_gbp": round(t, 2), "trade_gbp": round(d, 2)}
            for s, (c, t, d) in frontier.household.items()
        ],
        "within": [
            {
                "account": t.account,
                "series": t.series,
                "current_gbp": round(t.current_gbp, 2),
                "target_gbp": round(t.target_gbp, 2),
                "trade_gbp": round(t.trade_gbp, 2),
                "cost_gbp": round(t.cost_gbp, 2),
            }
            for t in frontier.trades
        ],
        "total_cost_gbp": round(sum(t.cost_gbp for t in frontier.trades), 2),
        "min_trade_gbp": frontier.min_trade,
    }
    return section, risk, rebalance


def _income(
    options: ReportOptions, accounts: Sequence[AccountConfig], folder: str, usd_gbp: float | None
) -> dict[str, object]:
    try:
        rows = build_ledger(options.root, accounts)
    except UnknownTransaction as exc:
        return _off(f"the transaction exports could not be read: {exc}")
    first, last = window(folder, 12)
    months = income_by_month(rows, first, last, usd_gbp)
    totals: dict[str, float] = {}
    for key in ("dividends_gbp", "interest_gbp", "fees_gbp", "tax_withheld_gbp"):
        amount = 0.0
        for month in months:
            value = month[key]
            amount += value if isinstance(value, float) else 0.0
        totals[key] = round(amount, 2)
    return {"available": True, "first": _ym(first), "last": _ym(last), "months": months, "totals": totals}


def _point(item: AccountReturn) -> dict[str, object]:
    return {
        "account": item.account, "currency": item.currency, "available": item.available,
        "reason": item.reason,
        "start": item.start.isoformat() if item.start else None,
        "end": item.end.isoformat() if item.end else None,
        "start_value": item.start_value, "end_value": item.end_value, "net_flows": item.net_flows,
        "twr": _num(item.twr), "mwr_period": _num(item.mwr_period), "mwr_annual": _num(item.mwr_annual),
        "points": [{"date": day.isoformat(), "value": value, "external_flow": flow, "return": _num(ret)}
                   for day, value, flow, ret in item.points],
    }  # fmt: skip


def _account_returns(options: ReportOptions, accounts: Sequence[AccountConfig]) -> dict[str, object]:
    if not (options.prices / "securities.yaml").exists():
        return _off("no price history yet: add price files and data/prices/securities.yaml (see README)")
    try:
        result = build_account_returns(options.root, accounts, options.prices, options.usd_gbp)
    except UnknownTransaction as exc:
        return _off(f"the transaction exports could not be read: {exc}")
    return {
        "available": True,
        "accounts": [_point(a) for a in result.accounts],
        "household": _point(result.household),
        "unmatched": [{"account": a, "security": k} for a, k in result.unmatched],
    }


def write_portfolio_files(document: Mapping[str, object], output_dir: Path) -> list[Path]:
    """``portfolio/portfolio.json`` and ``portfolio.js``, and the page files beside them (viewer §4)."""
    folder = output_dir / "portfolio"
    folder.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2)
    json_path = folder / "portfolio.json"
    json_path.write_text(text + "\n", encoding="utf-8", newline="\n")
    js_path = folder / "portfolio.js"
    compact = json.dumps(document, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    js_path.write_text(JS_PREFIX + compact + ";\n", encoding="utf-8", newline="\n")
    web = resources.files("sbretire").joinpath("web")
    written = [json_path, js_path]
    for name, parts in PAGE_FILES.items():
        target = output_dir / name
        target.write_bytes(web.joinpath(*parts).read_bytes())
        written.append(target)
    return written
