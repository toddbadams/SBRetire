---
id: F-027
type: feature
parent: portfolio-analysis
status: in-progress
complexity: 5
created: 2026-10-18
updated: 2026-10-18
---
# F-027 Performance and Drawdown Report

## 1. Purpose

Show how **today's portfolio mix** would have performed over the last five years:

- annualised return, volatility and Sharpe ratio;
- the worst drawdown, with when it started, bottomed and recovered;
- rolling 12-month return and volatility;
- the same figures for each price series.

`sbretire portfolio performance` builds on F-026's monthly GBP returns and F-025's valuation. It prints the summary
and writes `output/portfolio/performance.csv` (one row per month) and `performance_series.csv` (one row per
series). The Sharpe frontier (F-029) and the Portfolio page (F-030) use the same figures.

**Not in this feature** (user, 2026-10-18): time- and money-weighted returns of the accounts themselves since
January 2026. They need account values rebuilt backwards from today's holdings through the ledger, and HL and
Vanguard name securities differently in transactions and holdings. They move to a new **F-031**.

Epic `portfolio-analysis`; requested by the user on 2026-10-18.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Risk-free rate | `risk_free_rate` (annual, a fraction, 0 ≤ r < 0.2) at the top of `data/prices/securities.yaml`; `--risk-free R` overrides it for one run. Neither → exit 2 asking for it. Monthly: `(1 + r)^(1/12) − 1` | One Bank Rate figure (epic), next to the price files it is used with | user 2026-10-18 |
| 2 | Weights | Today's GBP value of each series (the sum of the holdings it prices) and of all cash, from the newest folder's valuation. Holdings in no series, or whose series has no file, are left out; their share is reported | Back-test of current weights (epic) | epic |
| 3 | Missing months | Each month uses today's weights among the series with a return that month, rescaled with cash to 100%. Cash always earns the monthly risk-free rate. Each month records the share of the household value it covered | Uses all the data without inventing returns | user 2026-10-18 |
| 4 | Metrics | Over n months of portfolio returns `r_t`: **annual return** = `Π(1 + r_t)^(12/n) − 1`; **annual volatility** = sample standard deviation × √12; **Sharpe** = `12 × mean(r_t − r_f) / (√12 × sd(r_t))`; **max drawdown** = the largest fall of the wealth index (1 at the start, × (1 + r_t) each month) from a previous peak, with peak, trough and recovery months (recovery `None` if not regained); **rolling 12 months**: the compounded return and the annualised volatility of each 12-month run, from the 12th month | Standard definitions, stated once | this brief |
| 5 | Per series | The same metrics for each series over its own months with a return (series with fewer than 12 returns show `n/a` volatility and Sharpe) | Inputs to F-029; shows which holdings drive risk | this brief |
| 6 | Output | `sbretire portfolio performance [--root] [--accounts] [--prices] [--output-dir] [--months 60] [--usd-gbp R] [--risk-free R]` prints the summary and writes `performance.csv` (`month`, `portfolio_return`, `wealth_index`, `drawdown`, `covered_share`, `rolling_12m_return`, `rolling_12m_volatility`) and `performance_series.csv` (`series`, `name`, `weight`, `months`, `annual_return`, `annual_volatility`, `sharpe`, `max_drawdown`). Exit 0 ok, 1 unreadable, 2 invalid | Same pattern as the other portfolio commands | this brief |
| 7 | Historical, not a forecast | The summary says the figures are a back-test of today's mix over past prices, not a forecast or advice | Epic "analysis, not advice" | epic |
| 8 | Tests | Known answers: constant returns (zero volatility, Sharpe undefined → `None`), alternating returns (closed-form mean and sd), a hand-built drawdown with recovery, re-weighting when one series has a gap, cash at the risk-free rate | Closed-form checks | this brief |

## 3. Context

- **F-026 gives:**
  - `build_returns` → `ReturnsReport` with `returns` (a `MonthlyReturn` per series and month) and `coverage`;
  - `load_securities` → `SecuritiesConfig`, which this feature extends with `risk_free_rate`;
  - the 60-month window ending the month before the newest folder.
- **F-025 gives:** `read_holdings`, `value_holdings` and `Valuation.value_gbp`.
- **NumPy** is available. Sample standard deviation uses `ddof=1`.

## 4. Touch-points

**New:** `src/sbretire/ledger/performance.py` (metrics, back-test, CSVs, summary), tests
`tests/unit/test_performance_*.py`.

**Modified:**
- `src/sbretire/ledger/prices.py`: `risk_free_rate`.
- `src/sbretire/ledger/returns.py`: the weights the back-test needs, i.e. the series values and cash from the
  valuation.
- `config/securities.example.yaml`.
- `src/sbretire/__main__.py`: `portfolio performance`.
- `README.md`.
- `docs/THESAURUS.md`: Back-test, Drawdown, Sharpe Ratio.
- `docs/decisions/portfolio-data.md`: §15–§17.
- `docs/epics/portfolio-analysis.md` and `roadmap.md`: the F-031 row.

## 5. Interfaces

```python
# sbretire/ledger/performance.py
@dataclass(frozen=True)
class Metrics:
    months: int
    annual_return: float | None
    annual_volatility: float | None
    sharpe: float | None
    max_drawdown: float  # a fraction ≥ 0
    peak: dt.date | None
    trough: dt.date | None
    recovery: dt.date | None


def monthly_rate(annual: float) -> float: ...
def metrics(months: Sequence[dt.date], returns: Sequence[float], risk_free: float) -> Metrics: ...
def drawdowns(
    returns: Sequence[float],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]: ...  # wealth, drawdown
def rolling(returns: Sequence[float], window: int = 12) -> tuple[list[float | None], list[float | None]]: ...


@dataclass(frozen=True)
class BacktestMonth:
    month: dt.date
    portfolio_return: float
    covered_share: float


def backtest(
    weights: Mapping[str, float],
    cash: float,
    total: float,
    returns: Sequence[MonthlyReturn],
    first: dt.date,
    last: dt.date,
    risk_free: float,
) -> list[BacktestMonth]: ...
```

## 6. Plan of Work

1. `risk_free_rate`, plus the metric functions with known-answer tests.
2. The back-test of today's weights: re-weighting, cash at the risk-free rate, covered share.
3. `sbretire portfolio performance`: summary, `performance.csv`, `performance_series.csv`.
4. Docs, the F-031 roadmap row, and a local run.

## 7. Validation

- **T1:** metrics on hand-built series: constant 1% a month; alternating +2%/−1%; a 10% fall then recovery;
  rolling windows; re-weighting with a gap; cash at the risk-free rate.
- **T2:** the command on the F-026 synthetic holdings and price files: summary lines, CSV columns and rows, and
  exit 2 without a risk-free rate.
- **T3:** the real holdings run (`check:`). With no price files yet, the back-test is all cash at the risk-free
  rate, which is reported as such.

## 8. Decision Log

- 2026-10-18 — §2 #1 and #3 come from the user's answers: the rate goes in `securities.yaml` with a `--risk-free`
  override, and the back-test re-weights what is priced. Deferring TWR/MWR to F-031 is also the user's choice.
  The rest is mine.

## 9. Surprises

## 10. Tasks

### F-027.1 Risk-free rate and performance metrics
- **Status**: Verification
- **Depends on**: —

`risk_free_rate` in `SecuritiesConfig` (validated), `ledger/performance.py` metric functions. §2 #1, #4.

**Acceptance criteria**
- [x] `risk_free_rate` loads from the map and rejects a negative or ≥ 0.2 value with its location; `monthly_rate(0.04)` is (1.04)^(1/12) − 1 — `test_risk_free_rate_config`
- [x] Known answers: constant 1% gives annual return 1.01^12 − 1, zero volatility and Sharpe `None`; alternating +2%/−1% gives the closed-form sample sd × √12 and Sharpe; a fall of 10% then recovery gives max drawdown 0.10 with the right peak, trough and recovery months; rolling 12-month values start at month 12 — `test_metrics_known_answers`

**Notes**
2026-10-18 SecuritiesConfig.risk_free_rate (0 ≤ r < 0.2), ledger/performance.py (monthly_rate, Metrics, drawdowns, metrics, rolling); tests/unit/test_performance_metrics.py (2).

### F-027.2 Back-test of today's weights
- **Status**: Verification
- **Depends on**: F-027.1

`backtest` (§2 #2–#3).

**Acceptance criteria**
- [x] With two series weighted 60/40 and cash, each month's return is the weighted mean, with cash at the monthly risk-free rate; in a month where one series has no return the other and cash are rescaled to 100%, and the covered share falls by that series' weight — `test_backtest_reweights_and_covers`

**Notes**
2026-10-18 ledger/performance.py BacktestMonth, backtest (series with a return that month plus cash rescaled to 100%, cash at the monthly risk-free rate, covered share of today's household value, nothing counted → risk-free); tests/unit/test_performance_backtest.py. The red commit failed on import (no backtest stub) rather than an assertion; noted.

### F-027.3 `sbretire portfolio performance`
- **Status**: Verification
- **Depends on**: F-027.2

The command: weights from the valuation, the summary (with the "historical, not a forecast" note),
`performance.csv` and `performance_series.csv`. §2 #5–#7.

**Acceptance criteria**
- [x] On the F-026 synthetic holdings and price files, the command prints the annual return, volatility, Sharpe, max drawdown with dates and the covered share, and writes both CSVs (UTF-8, LF, columns, one row per month and per series); without a risk-free rate it exits 2 naming `risk_free_rate` — `test_cli_portfolio_performance`

**Notes**
2026-10-18 ReturnsReport gains series_values, series_names, cash_gbp, total_gbp, risk_free_rate; ledger/performance.py build_performance, write_performance_csvs, format_performance; `sbretire portfolio performance` (shared _returns_report with portfolio returns); tests/unit/test_performance_cli.py. Real holdings: all cash at the risk-free rate (no price files yet), exit 0.

### F-027.4 Docs, F-031 and a local run
- **Status**: To Do
- **Depends on**: F-027.3

README section, THESAURUS (Back-test, Drawdown, Sharpe Ratio, sorted), `docs/decisions/portfolio-data.md` §15–§17,
`config/securities.example.yaml` `risk_free_rate`, roadmap and epic row F-031 "Account Returns from the Ledger"
(proposed), local run.

**Acceptance criteria**
- [ ] README documents `portfolio performance` and `risk_free_rate`; THESAURUS defines Back-test, Drawdown and Sharpe Ratio in order; decisions recorded; F-031 is on the roadmap and in the epic — `check: grep -n "portfolio performance" README.md docs/decisions/portfolio-data.md && grep -n "F-031" docs/epics/roadmap.md docs/epics/portfolio-analysis.md`
- [ ] On the real holdings the command runs (all cash while no price files exist, reported), exit 0 (run locally; never committed) — `check: uv run sbretire portfolio performance --usd-gbp 0.7503 --risk-free 0.04`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Risk-free config — `test_risk_free_rate_config`
2. Metrics — `test_metrics_known_answers`
3. Back-test — `test_backtest_reweights_and_covers`
4. CLI — `test_cli_portfolio_performance`
5. Docs and F-031 — `check: grep -n "portfolio performance" README.md docs/decisions/portfolio-data.md && grep -n "F-031" docs/epics/roadmap.md docs/epics/portfolio-analysis.md`
6. Real run — `check: uv run sbretire portfolio performance --usd-gbp 0.7503 --risk-free 0.04`
