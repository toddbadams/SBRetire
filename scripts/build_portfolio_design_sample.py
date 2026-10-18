"""Build a SYNTHETIC portfolio sample for the Claude Design hand-off (portfolio-analysis epic).

Usage:
    uv run python scripts/build_portfolio_design_sample.py

Writes docs/design/sample/portfolio/portfolio.json and portfolio.js (window.SBRETIRE_PORTFOLIO). Every
holding, account, amount and return is invented from fixed assumptions and seed: no personal data is read.
The layout is the draft portfolio.json (schema_version "0.1-draft") in docs/design/portfolio-design-handoff.md
and F-030 fixes the final schema.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "design" / "sample" / "portfolio"
MONTHS = 60
RISK_FREE = 0.04
MAX_WEIGHT = 0.25
Array = NDArray[np.float64]

ACCOUNTS = [
    ("brokerage", "US brokerage", "Example Broker A", "taxable", "person_1", "USD"),
    ("platform", "Investment account", "Example Platform B", "taxable", "person_1", "GBP"),
    ("isa", "Stocks & Shares ISA", "Example Platform C", "isa", "person_2", "GBP"),
    ("pension", "Personal pension", "Example Platform C", "pension", "person_2", "GBP"),
    ("sipp", "SIPP", "Example Platform D", "sipp", "person_2", "GBP"),
]
# id, name, account, asset class, currency, annual mean, annual vol, value GBP
HOLDINGS = [
    ("glob_eq", "Global All-Cap Equity Index (Acc)", "sipp", "Equity", "GBP", 0.085, 0.15, 160_000),
    ("us_eq", "US Large Cap Equity ETF", "sipp", "Equity", "USD", 0.10, 0.17, 95_000),
    ("uk_eq", "UK All-Share Index Fund (Acc)", "platform", "Equity", "GBP", 0.06, 0.14, 70_000),
    ("em_eq", "Emerging Markets Equity ETF", "isa", "Equity", "USD", 0.07, 0.20, 40_000),
    ("multi40", "Multi-Asset 40% Equity Fund (Acc)", "isa", "Multi-asset", "GBP", 0.045, 0.08, 60_000),
    ("target35", "Target Date 2035 Fund (Acc)", "pension", "Multi-asset", "GBP", 0.055, 0.10, 45_000),
    ("gilts", "UK Gilts Index Fund", "platform", "Bonds", "GBP", 0.025, 0.07, 55_000),
    ("tech_stock", "Example Tech Corp", "brokerage", "Equity", "USD", 0.14, 0.28, 30_000),
    ("staples_stock", "Example Consumer Staples Co", "brokerage", "Equity", "USD", 0.06, 0.16, 25_000),
]
CASH = {"brokerage": 4_000.0, "platform": 2_500.0, "isa": 150.0, "pension": 50.0, "sipp": 1_200.0}
SECTORS = [
    "Technology",
    "Financials",
    "Health Care",
    "Industrials",
    "Consumer Staples",
    "Consumer Discretionary",
    "Energy",
    "Other",
]
REGIONS = [
    "North America",
    "United Kingdom",
    "Europe ex-UK",
    "Japan",
    "Asia Pacific ex-Japan",
    "Emerging Markets",
]


def _months(end_year: int = 2026, end_month: int = 9) -> list[str]:
    out = []
    year, month = end_year, end_month
    for _ in range(MONTHS):
        out.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return out[::-1]


BETAS = [1.0, 1.05, 0.85, 1.1, 0.45, 0.6, 0.05, 1.3, 0.6]  # exposure to one market factor
MARKET_VOL = 0.15


def _assumptions() -> tuple[Array, Array]:
    """Annual mean returns and a one-factor covariance matrix matching each holding's stated volatility."""
    mean = np.array([h[5] for h in HOLDINGS])
    vol = np.array([h[6] for h in HOLDINGS])
    beta = np.array(BETAS)
    systematic = np.outer(beta, beta) * MARKET_VOL**2
    idiosyncratic = np.clip(vol**2 - np.diag(systematic), 0.0005, None)
    cov: Array = systematic + np.diag(idiosyncratic)
    return mean, cov


def _returns(rng: np.random.Generator, mean: Array, cov: Array) -> Array:
    """Monthly returns drawn from the assumptions, with one illustrative market fall."""
    draws: Array = rng.multivariate_normal(mean / 12, cov / 12, size=MONTHS)
    draws[24:28] -= 0.035 * np.array(BETAS)
    return draws


def _stats(weights: Array, mu: Array, cov: Array) -> tuple[float, float, float]:
    ret = float(weights @ mu)
    vol = float(np.sqrt(weights @ cov @ weights))
    return ret, vol, (ret - RISK_FREE) / vol


def _optimise(objective: Any, mu: Array, cov: Array, extra: list[dict[str, Any]]) -> Array:
    n = len(mu)
    result = minimize(
        objective,
        np.full(n, 1 / n),
        bounds=[(0.0, MAX_WEIGHT)] * n,
        constraints=[{"type": "eq", "fun": lambda w: float(np.sum(w) - 1)}, *extra],
        method="SLSQP",
    )
    weights: Array = np.clip(result.x, 0, None)
    return weights / weights.sum()


def _point(weights: Array, mu: Array, cov: Array) -> dict[str, Any]:
    ret, vol, sharpe = _stats(weights, mu, cov)
    ids = [h[0] for h in HOLDINGS]
    return {
        "return": round(ret, 5),
        "volatility": round(vol, 5),
        "sharpe": round(sharpe, 4),
        "weights": {i: round(float(w), 4) for i, w in zip(ids, weights, strict=True) if w > 1e-4},
    }


def _drawdowns(index: Array, months: list[str]) -> tuple[list[float], list[dict[str, Any]]]:
    peak = np.maximum.accumulate(index)
    depth = index / peak - 1
    events: list[dict[str, Any]] = []
    i = 0
    while i < len(index):
        if depth[i] < 0:
            start = i - 1
            j = i
            while j < len(index) and depth[j] < 0:
                j += 1
            trough = start + 1 + int(np.argmin(depth[start + 1 : j]))
            events.append(
                {
                    "start": months[start],
                    "trough": months[trough],
                    "recovery": months[j] if j < len(index) else None,
                    "depth": round(float(depth[trough]), 4),
                    "months_to_trough": trough - start,
                    "months_to_recover": (j - trough) if j < len(index) else None,
                }
            )
            i = j
        else:
            i += 1
    events.sort(key=lambda e: e["depth"])
    return [round(float(d), 4) for d in depth], events[:5]


def build() -> dict[str, Any]:
    rng = np.random.Generator(np.random.PCG64(2030))
    months = _months()
    mu, cov = _assumptions()
    monthly = _returns(rng, mu, cov)
    values = np.array([h[7] for h in HOLDINGS], dtype=float)
    invested = values.sum()
    total = invested + sum(CASH.values())
    current = values / invested

    min_var = _optimise(lambda w: float(w @ cov @ w), mu, cov, [])
    max_sharpe = _optimise(lambda w: -_stats(w, mu, cov)[2], mu, cov, [])
    lo, hi = float(min_var @ mu), float(np.max(mu) * 0.98)
    frontier = [
        _point(
            _optimise(
                lambda w: float(w @ cov @ w),
                mu,
                cov,
                [{"type": "eq", "fun": lambda w, t=t: float(w @ mu - t)}],
            ),
            mu,
            cov,
        )
        for t in np.linspace(lo, hi, 25)
    ]

    portfolio_monthly = monthly @ current
    index = np.cumprod(1 + portfolio_monthly)
    depth, worst = _drawdowns(index, months)
    benchmark = monthly[:, 0]
    rolling = []
    for k in range(11, MONTHS):
        window = portfolio_monthly[k - 11 : k + 1]
        ret12 = float(np.prod(1 + window) - 1)
        vol12 = float(window.std(ddof=1) * np.sqrt(12))
        rolling.append(
            {
                "month": months[k],
                "return": round(ret12, 4),
                "volatility": round(vol12, 4),
                "sharpe": round((ret12 - RISK_FREE) / vol12, 3),
            }
        )

    sector_raw = rng.dirichlet(np.ones(len(SECTORS)) * 2)
    region_raw = np.array([0.58, 0.16, 0.10, 0.05, 0.04, 0.07])
    ids = [h[0] for h in HOLDINGS]
    trades: list[dict[str, Any]] = []
    for (hid, name, account, *_rest), w_now, w_new in zip(HOLDINGS, current, max_sharpe, strict=True):
        delta = (w_new - w_now) * invested
        if abs(delta) > 500:
            trades.append(
                {
                    "holding": hid,
                    "name": name,
                    "account": account,
                    "action": "buy" if delta > 0 else "sell",
                    "value_gbp": round(abs(float(delta)), 2),
                    "est_cost_gbp": round(
                        abs(float(delta)) * (0.0015 if account == "brokerage" else 0.001) + 5, 2
                    ),
                    "cross_account": True,
                }
            )
    by_person: dict[str, float] = {}
    accounts = []
    for aid, name, provider, wrapper, owner, currency in ACCOUNTS:
        value = float(values[[h[2] == aid for h in HOLDINGS]].sum() + CASH[aid])
        by_person[owner] = by_person.get(owner, 0.0) + value
        accounts.append(
            {
                "id": aid,
                "name": name,
                "provider": provider,
                "wrapper": wrapper,
                "owner": owner,
                "currency": currency,
                "value_gbp": round(value, 2),
                "cash_gbp": CASH[aid],
            }
        )

    holdings = []
    for k, (hid, name, account, asset_class, currency, *_rest) in enumerate(HOLDINGS):
        ret, vol = float(mu[k]), float(np.sqrt(cov[k, k]))
        holdings.append(
            {
                "id": hid,
                "name": name,
                "account": account,
                "asset_class": asset_class,
                "currency": currency,
                "value_gbp": float(values[k]),
                "weight": round(float(values[k] / total), 4),
                "return_ann": round(ret, 4),
                "volatility_ann": round(vol, 4),
                "sharpe": round((ret - RISK_FREE) / vol, 3),
                "history_months": 60 if hid != "em_eq" else 38,
            }
        )
    corr: Array = np.asarray(np.corrcoef(monthly, rowvar=False))
    port_vol = float(np.sqrt(current @ cov @ current))
    contribution = current * (cov @ current) / port_vol
    return {
        "schema_version": "0.1-draft",
        "synthetic": True,
        "as_of": "2026-09-30",
        "created_at": "2026-10-18T09:00:00Z",
        "currency": "GBP",
        "settings": {
            "lookback_months": MONTHS,
            "risk_free_rate": RISK_FREE,
            "max_weight": MAX_WEIGHT,
            "return_frequency": "monthly",
        },
        "people": [{"id": "person_1", "name": "Person 1"}, {"id": "person_2", "name": "Person 2"}],
        "total": {
            "value_gbp": round(float(total), 2),
            "by_person": {k: round(v, 2) for k, v in by_person.items()},
            "starting_balance_yaml": f"starting_balance: {round(float(total))}",
        },
        "accounts": accounts,
        "holdings": holdings,
        "exposure": {
            "sector": [
                {"name": s, "weight": round(float(w), 4)} for s, w in zip(SECTORS, sector_raw, strict=True)
            ],
            "region": [
                {"name": r, "weight": round(float(w), 4)} for r, w in zip(REGIONS, region_raw, strict=True)
            ],
            "asset_class": [
                {"name": "Equity", "weight": 0.69},
                {"name": "Multi-asset", "weight": 0.18},
                {"name": "Bonds", "weight": 0.10},
                {"name": "Cash", "weight": 0.03},
            ],
            "currency": [
                {"name": "USD", "weight": 0.52},
                {"name": "GBP", "weight": 0.31},
                {"name": "EUR", "weight": 0.07},
                {"name": "Other", "weight": 0.10},
            ],
            "top_lookthrough": [
                {
                    "name": f"Example Company {c}",
                    "weight": round(0.035 - 0.003 * i, 4),
                    "via": ["glob_eq", "us_eq"] if i else ["glob_eq", "us_eq", "tech_stock"],
                }
                for i, c in enumerate("ABCDEFGHIJ")
            ],
        },
        "performance": {
            "export_period": {"start": "2026-01-01", "end": "2026-09-30", "twr": 0.0612, "mwr": 0.0588},
            "backtest": {
                "start": months[0],
                "end": months[-1],
                "ann_return": round(float(np.prod(1 + portfolio_monthly) ** (12 / MONTHS) - 1), 4),
                "ann_volatility": round(float(portfolio_monthly.std(ddof=1) * np.sqrt(12)), 4),
                "sharpe": round(_stats(current, mu, cov)[2], 3),
                "max_drawdown": min(depth),
                "series": [
                    {
                        "month": m,
                        "index": round(float(v), 4),
                        "benchmark_index": round(float(b), 4),
                        "drawdown": d,
                    }
                    for m, v, b, d in zip(months, index, np.cumprod(1 + benchmark), depth, strict=True)
                ],
            },
            "calendar": [
                {"month": m, "return": round(float(r), 4)}
                for m, r in zip(months, portfolio_monthly, strict=True)
            ],
            "rolling_12m": rolling,
            "drawdowns": worst,
        },
        "income": [
            {
                "month": m,
                "dividends": round(float(rng.uniform(50, 900)), 2),
                "interest": round(float(rng.uniform(0, 40)), 2),
                "fees": round(float(rng.uniform(0, 60)), 2),
            }
            for m in months[-12:]
        ],
        "correlation": {"ids": ids, "matrix": [[round(float(x), 3) for x in row] for row in corr]},
        "risk_contribution": [
            {"holding": i, "weight": round(float(w), 4), "contribution": round(float(c / port_vol), 4)}
            for i, w, c in zip(ids, current, contribution, strict=True)
        ],
        "frontier": {
            "points": frontier,
            "current": _point(current, mu, cov),
            "min_variance": _point(min_var, mu, cov),
            "max_sharpe": _point(max_sharpe, mu, cov),
            "risk_free_rate": RISK_FREE,
            "holdings_points": [
                {"id": i, "return": round(float(mu[k]), 4), "volatility": round(float(np.sqrt(cov[k, k])), 4)}
                for k, i in enumerate(ids)
            ],
        },
        "rebalance": {
            "target": "max_sharpe",
            "trades": trades,
            "total_cost_gbp": round(sum(t["est_cost_gbp"] for t in trades), 2),
            "sharpe_change": round(_stats(max_sharpe, mu, cov)[2] - _stats(current, mu, cov)[2], 3),
            "volatility_change": round(_stats(max_sharpe, mu, cov)[1] - _stats(current, mu, cov)[1], 4),
        },
        "warnings": [
            "Emerging Markets Equity ETF has 38 months of prices; its statistics use that shorter period.",
            "Re-weighting moves money between accounts; pension and SIPP money cannot move elsewhere.",
        ],
        "data_files": [
            {
                "name": "prices/glob_eq.csv",
                "rows": 60,
                "from": months[0],
                "to": months[-1],
                "sha256": "0" * 64,
            }
        ],
    }


def main() -> None:
    sample = build()
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(sample, indent=2) + "\n"
    (OUT / "portfolio.json").write_bytes(text.encode("utf-8"))
    (OUT / "portfolio.js").write_bytes(
        ("window.SBRETIRE_PORTFOLIO = " + json.dumps(sample) + ";\n").encode("utf-8")
    )
    print(f"Wrote {OUT / 'portfolio.json'} and portfolio.js (synthetic)")


if __name__ == "__main__":
    main()
