---
id: F-029
type: feature
parent: portfolio-analysis
status: in-progress
complexity: 7
created: 2026-10-18
updated: 2026-10-18
---
# F-029 Sharpe Efficient Frontier and Re-Weighting Analysis

## 1. Purpose

Show **how efficient today's mix of holdings has been**, and what a better mix of the same holdings would have
looked like:

- the efficient frontier of the household's priced holdings: long-only, with each holding capped;
- where today's mix sits against it;
- the minimum-variance and maximum-Sharpe mixes;
- the mix with **today's risk and the highest historical return**: the target;
- the trades from today to the target, both as one household portfolio (analysis only) and within each account
  (executable), with estimated costs from each account's fee schedule;
- how much the target moves when it is estimated from each half of the five years.

`sbretire portfolio frontier` builds on F-026's monthly returns, F-027's risk-free rate and today's valuation
(F-025).

**Analysis, not advice** (epic). The figures are a model calculation from past returns, under stated assumptions.
The page and the CLI say so, and say that moves between wrappers (pension ↔ ISA ↔ taxable) cannot be made as shown.

Epic `portfolio-analysis`; requested by the user on 2026-10-18.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Universe | Series with a return in **every** month of the window and a positive value today are optimised: the "priced sleeve". Short-history and unpriced holdings and cash stay at today's GBP values. Their share is reported | A covariance needs a common window; frozen parts stay visible | this brief |
| 2 | Estimates | Annual expected return = 12 × mean monthly return. Annual covariance = 12 × the **Ledoit–Wolf** shrinkage estimate: the sample covariance shrunk towards a scaled identity, with the intensity from the Ledoit–Wolf (2004) formula. `--covariance sample` uses the raw sample covariance | Stabler weights with ~36 series and 60 months; the user chose shrinkage | user 2026-10-18 |
| 3 | Constraints | Long-only, weights sum to 1 over the sleeve, each weight ≤ `max_weight`: in `securities.yaml`, default 0.25, `--max-weight` overrides. `max_weight × n < 1` is an error (exit 2). Today's weights above the cap are flagged | Stops concentration in past winners | user 2026-10-18 |
| 4 | Mixes | **Minimum variance**. **Frontier**: 21 points from the minimum-variance return to the highest return reachable under the cap. **Maximum Sharpe**: the highest `(return − r_f) / volatility`, with `r_f` from F-027's `risk_free_rate`. **Target** (`--target same-risk`, default): the highest return with volatility ≤ today's sleeve volatility, falling back to minimum variance if today's volatility is below it. `--target max-sharpe` and `--target min-variance` switch it. Solved with SciPy SLSQP | Keeps the risk the household lives with | user 2026-10-18 |
| 5 | Household trades | Per series: target weight × sleeve value − today's value, in GBP. Labelled **analysis only**: these may need moves between accounts and wrappers | Treats the household as one portfolio (epic) | epic |
| 6 | Within-account trades | Per account: the account's sleeve value is re-split over the series **it already holds**, in proportion to the target weights of those series (kept as today if they are all 0). Trades below `--min-trade` (default £50) are skipped. The resulting household mix's historical return, volatility and Sharpe are reported beside the target's | Executable without moving money between wrappers | epic |
| 7 | Costs | `trading: {fee_per_trade, cost_rate}` on each account in `accounts.yaml`: a fixed fee per trade in the account's currency (converted to GBP) plus `cost_rate × |trade|` covering spread, stamp duty and FX. An account without `trading` costs 0, with a warning | Per-account fee schedules (epic) | user 2026-10-18 |
| 8 | Sensitivity | The target is re-estimated from the first and the second half of the window. Its turnover between the halves, `Σ|w₁ − w₂| / 2`, is reported as an instability measure | Estimation error (epic risk) | epic |
| 9 | Output | `sbretire portfolio frontier [--root] [--accounts] [--prices] [--output-dir] [--months 60] [--usd-gbp R] [--risk-free R] [--max-weight W] [--covariance shrunk|sample] [--target same-risk|max-sharpe|min-variance] [--min-trade 50]` prints the summary and caveats and writes three files: `frontier.csv` (`point`, `return`, `volatility`, `sharpe`, plus rows `today`, `min_variance`, `max_sharpe`, `target`, `within_accounts`), `frontier_weights.csv` (`series`, `name`, `today`, `min_variance`, `max_sharpe`, `target`, `within_accounts`) and `trades.csv` (`scope` household/account, `account`, `series`, `current_gbp`, `target_gbp`, `trade_gbp`, `cost_gbp`). Exit 0 ok, 1 unreadable, 2 invalid (no risk-free rate, fewer than 2 priced series, infeasible cap) | Same pattern as the other portfolio commands | this brief |
| 10 | Tests | Known answers: two uncorrelated assets (closed-form minimum variance `w₁ = σ₂²/(σ₁²+σ₂²)`), a binding cap, the Ledoit–Wolf intensity on a hand-built sample, same-risk ≥ today's return at ≤ today's volatility, within-account splits and costs by hand | Closed-form checks | this brief |

## 3. Context

- **F-026** gives the `MonthlyReturn` rows and `today_values`.
- **F-027** gives `risk_free_rate` and the metrics.
- **F-024** gives `AccountConfig`; this feature adds `trading` to it.
- **SciPy** is a project dependency (`scipy.optimize.minimize`, method SLSQP).
- **Randomness:** none. All solver starts are deterministic.

## 4. Touch-points

**New:**
- `src/sbretire/ledger/frontier.py`: universe, estimates, optimiser, trades, sensitivity, CSVs and summary.
- Tests: `tests/unit/test_frontier_*.py`.

**Modified:**
- `src/sbretire/ledger/accounts.py`: `trading`.
- `src/sbretire/ledger/prices.py`: `max_weight`.
- `config/accounts.example.yaml` and `config/securities.example.yaml`.
- `src/sbretire/__main__.py`: `portfolio frontier`.
- `README.md`.
- `docs/THESAURUS.md`: Efficient Frontier, Priced Sleeve, Target Mix.
- `docs/decisions/portfolio-data.md`: §21–§24.

## 5. Interfaces

```python
# sbretire/ledger/frontier.py
def ledoit_wolf(samples: NDArray[np.float64]) -> tuple[NDArray[np.float64], float]: ...  # (cov, shrinkage)


@dataclass(frozen=True)
class Estimates:
    series: list[str]
    mean: NDArray[np.float64]  # annual
    cov: NDArray[np.float64]  # annual
    shrinkage: float | None


@dataclass(frozen=True)
class Mix:
    weights: NDArray[np.float64]
    annual_return: float
    volatility: float
    sharpe: float | None


def min_variance(est: Estimates, cap: float) -> Mix: ...
def max_return_at(est: Estimates, cap: float, volatility: float) -> Mix: ...
def max_sharpe(est: Estimates, cap: float, risk_free: float) -> Mix: ...
def frontier(est: Estimates, cap: float, risk_free: float, points: int = 21) -> list[Mix]: ...
def within_account_targets(
    holdings: Mapping[str, Mapping[str, float]], target: Mapping[str, float]
) -> dict[str, dict[str, float]]: ...
def trade_cost(amount_gbp: float, fee_gbp: float, rate: float) -> float: ...
```

## 6. Plan of Work

1. Config fields: `max_weight` and `trading`. Ledoit–Wolf, estimates and the priced sleeve.
2. Optimiser: minimum variance, the frontier, maximum Sharpe, the same-risk target.
3. Trades: household and within-account plans, costs, and the half-window sensitivity.
4. `sbretire portfolio frontier`: summary, caveats and the three CSVs.
5. Docs and a local run.

## 7. Validation

- **T1:** closed forms. The minimum variance of two uncorrelated assets. A cap that binds. Ledoit–Wolf on a
  hand-built sample matches a direct computation of the 2004 formula. Every frontier point is feasible and
  volatility rises along it. Max Sharpe beats every frontier point. Same-risk volatility ≤ today's and return ≥
  today's. Within-account splits and costs checked by hand.
- **T2:** the command on synthetic price files (4 series over 24 months, 2 accounts): the CSVs and the summary,
  plus exit 2 on an infeasible cap.
- **T3:** the real holdings, a `check:` run. With no price files, fewer than 2 series are priced, so it exits 2
  with that reason.

## 8. Decision Log

- 2026-10-18 — These come from the user's answers: §2 #2 (Ledoit–Wolf), #3 (cap 0.25, settable), #4 (target:
  same risk as today) and #7 (per-account `trading` costs). The rest are mine, from the epic.

## 9. Surprises

## 10. Tasks

### F-029.1 Settings, estimates and the priced sleeve
- **Status**: Verification
- **Depends on**: —

What to build:
- `SecuritiesConfig.max_weight` (0 < w ≤ 1, default 0.25).
- `AccountConfig.trading` (`fee_per_trade` ≥ 0, `0 ≤ cost_rate < 0.05`).
- `ledoit_wolf` and the estimates over the priced sleeve.

§2 #1–#3.

**Acceptance criteria**
- [x] `max_weight` and `trading` load with defaults and reject out-of-range values with their locations — `test_frontier_settings`
- [x] `ledoit_wolf` on a hand-built 3-series sample equals a direct computation of the Ledoit–Wolf (2004) intensity and target; annual estimates are 12 × the monthly mean and covariance; only series with every month in the window enter the sleeve — `test_estimates_and_sleeve`

**Notes**
2026-10-18 SecuritiesConfig.max_weight (0 < w ≤ 1, default 0.25); accounts.TradingCosts and AccountConfig.trading; accounts.validation_issues (drops pydantic's redundant 'too short' for lists whose items failed; now shared by accounts, prices and exposure); ledger/frontier.py ledoit_wolf, Estimates, estimate (priced sleeve = full-window series with a value today); tests/unit/test_frontier_estimates.py (2).

### F-029.2 Optimiser
- **Status**: In Progress
- **Depends on**: F-029.1

`min_variance`, `frontier`, `max_sharpe`, `max_return_at`. §2 #4.

**Acceptance criteria**
- [ ] Two uncorrelated assets give the closed-form minimum-variance weights; a cap of 0.6 binds when the closed form exceeds it; frontier points are feasible (sum 1, 0 ≤ w ≤ cap) with non-decreasing volatility and return; max Sharpe is at least every frontier point's Sharpe; the same-risk mix has volatility ≤ the given level and the highest return among frontier points within it; a cap with `cap × n < 1` raises — `test_optimiser_known_answers`

### F-029.3 Trades, costs and sensitivity
- **Status**: To Do
- **Depends on**: F-029.2

Household deltas, `within_account_targets`, `trade_cost`, `--min-trade`, half-window turnover. §2 #5–#8.

**Acceptance criteria**
- [ ] Household trades are target × sleeve − today per series and sum to zero; within each account the sleeve value is re-split over the series it holds in proportion to target weights; trades below the minimum are skipped; cost = fee converted to GBP + rate × |trade|; the half-window turnover is Σ|w₁ − w₂| / 2 — `test_trades_costs_and_sensitivity`

### F-029.4 `sbretire portfolio frontier`
- **Status**: To Do
- **Depends on**: F-029.3

The command, the summary with its caveats, and the three CSVs. §2 #9.

**Acceptance criteria**
- [ ] On synthetic price files (4 series over 24 months, 2 accounts with fee schedules) the command prints today's, the minimum-variance, max-Sharpe and target mixes with return, volatility and Sharpe, the trades with costs, the half-window turnover and the analysis-not-advice and wrapper caveats, and writes `frontier.csv`, `frontier_weights.csv` and `trades.csv` (UTF-8, LF, columns); an infeasible cap exits 2 — `test_cli_portfolio_frontier`

### F-029.5 Docs and a local run
- **Status**: To Do
- **Depends on**: F-029.4

What to write and run:
- README section.
- Example config fields.
- THESAURUS: Efficient Frontier, Priced Sleeve and Target Mix, sorted.
- `docs/decisions/portfolio-data.md` §21–§24.
- A local run on the real holdings.

**Acceptance criteria**
- [ ] README documents `portfolio frontier`, `max_weight`, `trading` and the caveats; THESAURUS defines the three terms in order; decisions recorded — `check: grep -n "portfolio frontier" README.md docs/decisions/portfolio-data.md`
- [ ] On the real holdings the command explains that fewer than 2 series are priced (exit 2) until price files exist (run locally; never committed) — `check: uv run sbretire portfolio frontier --usd-gbp 0.7503 --risk-free 0.04`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Settings — `test_frontier_settings`
2. Estimates — `test_estimates_and_sleeve`
3. Optimiser — `test_optimiser_known_answers`
4. Trades — `test_trades_costs_and_sensitivity`
5. CLI — `test_cli_portfolio_frontier`
6. Docs — `check: grep -n "portfolio frontier" README.md docs/decisions/portfolio-data.md`
7. Real run — `check: uv run sbretire portfolio frontier --usd-gbp 0.7503 --risk-free 0.04`
