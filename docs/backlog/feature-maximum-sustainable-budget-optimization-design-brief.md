---
id: F-010
type: feature
parent: analysis-optimization
status: in-progress
complexity: 5
created: 2026-10-09
updated: 2026-10-09
---
# F-010 Maximum Sustainable Budget Optimization

## 1. Purpose

Answer the headline question (SPEC §1.1, §14): for each target probability p* in `model.confidence_levels`, the
**Maximum Sustainable Budget** B* — the largest monthly Budget in today's GBP whose **Conservative Success Rate** is at
least p* — with **Common Random Numbers** (one `RandomInputs` for every candidate, SPEC §10.3), explicit bounds,
a currency tolerance, convergence status, iteration count and the Monte Carlo standard error at B*. `sbretire run`
prints the result.

Resolves the budget half of SPEC §18 "Budget and return optimization bounds and tolerances" (optimization §1; the
return half is F-011). Makes passable SPEC §17.2 "Budget optimization returns a feasible budget within configured
tolerance on a small deterministic fixture" and completes §17.1 "Common random numbers are reused across candidate
budgets".

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Algorithm | **Per-path threshold bisection**: each Path i has a threshold budget T_i = the largest budget at which it is Successful (success is monotone non-increasing in the budget per path under CRN — verified in F-009). All paths are bisected at once by giving each path its own candidate budget in one vectorised engine run. Then rate(B) = #{T_i ≥ B} / N exactly, so B* for every target comes from the one search | One search (~20 engine runs) serves all targets; equals SPEC §14's bisection on the rate to within the tolerance | Interview Q1; optimization §1 |
| 2 | Who can succeed | Paths with someone alive at the Horizon are never Successful at any budget (Death Months do not depend on the budget) → no threshold (T = −∞). Completed-by-death paths have T ∈ [0, cap]; at budget 0 they never fail (F-009 zero-spending result) | simulation-conventions §7 | simulation-conventions §7 |
| 3 | Bounds | Lower bound £0/month. Upper bound starts at 2 × `budget.monthly_amount_today` (£1,000 if that is 0) and doubles until every completed-by-death path fails, capped at £1,000,000/month; paths still Successful at the cap get T = cap and are flagged | SPEC §14: explicit bounds, verified lower-feasible / upper-infeasible, documented expansion | Interview Q2; optimization §1 |
| 4 | Tolerance | £1/month: bisect until hi_i − lo_i ≤ 1 for every path; T_i = lo_i (the feasible end) | SPEC §14 example; reported result is always feasible | Interview Q2 |
| 5 | Selecting B* | k = ⌈p* · N⌉; B* = the k-th largest T_i (so #{T ≥ B*} ≥ k ⇒ rate(B*) ≥ p*). If fewer than k paths have a threshold (too many Unresolved), the target is **infeasible**: B* = None, converged = False, reason recorded | Conservative; never overstates sustainability | SPEC §11, §14 |
| 6 | Reported per target | `target_probability`, `maximum_monthly_budget_today`, `maximum_annual_budget_today` (= 12 ×), `estimated_success_probability` (= #{T ≥ B*}/N), its SE √(p(1−p)/N) (denominator all N paths), `unresolved_fraction`, `budget_tolerance`, `converged`, `iterations` (doublings + bisection rounds), `note` | SPEC §14 suggested columns + SE | SPEC §14 |
| 7 | Per-path budget plumbing | `ScenarioSpending` / `ScenarioCashFlows` / `run_monte_carlo` take optional `monthly_budget_today: float | FloatArray` (shape (n_paths,)); default = the Scenario's Budget | Minimal engine change; scalar path unchanged | Brief author |
| 8 | Constants | Tolerance and cap are module constants (documented, echoed in output), not YAML | Interview Q2 | Interview Q2 |
| 9 | Placement | `sbretire/optimization.py` | SPEC §3 | SPEC §3 |

## 3. Context

- `run_monte_carlo(scenario, inputs) -> MonteCarloResult(outcomes, metrics)`; `RandomInputs` read-only death months
  and a `StochasticPriceIndex` (F-009). `classify_paths` (F-009.1).
- `ScenarioSpending(scenario, price_index).spending(month, alive)` = B × I_t × F_t with the survivor's own factor
  (F-004); `ScenarioCashFlows` composes it with income.
- Engine cost: ~3.4 s per 100k-path run including load (F-009); a full search ≈ 20–25 runs.
- `format_run_summary` in `__main__.py` (F-009.3).

## 4. Touch-points

**New**: `src/sbretire/optimization.py`, `tests/unit/test_spending_per_path.py`, `tests/integration/test_optimization.py`.

**Modified**: `src/sbretire/spending.py`, `src/sbretire/cash_flows.py`, `src/sbretire/monte_carlo.py`,
`src/sbretire/__main__.py`, `tests/unit/test_cli_run.py`, `README.md`, `docs/decisions/optimization.md` (§1, with
this brief).

## 5. Interfaces

```python
# sbretire/optimization.py
BUDGET_TOLERANCE: Final = 1.0  # GBP / month, today's money
BUDGET_CAP: Final = 1_000_000.0  # GBP / month


@dataclass(frozen=True)
class ThresholdSearch:
    thresholds: NDArray[np.float64]  # (n_paths,) today's GBP/month; -inf where the path can never succeed
    capped: NDArray[np.bool_]  # still Successful at BUDGET_CAP
    iterations: int  # doublings + bisection rounds (engine runs after the first)
    upper_bound: float  # final upper bound used


def path_budget_thresholds(scenario: Scenario, inputs: RandomInputs) -> ThresholdSearch: ...


@dataclass(frozen=True)
class BudgetResult:
    target_probability: float
    maximum_monthly_budget_today: float | None
    maximum_annual_budget_today: float | None
    estimated_success_probability: float | None
    standard_error: float | None  # denominator: all paths
    unresolved_fraction: float
    budget_tolerance: float
    converged: bool
    iterations: int
    note: str  # "" | "infeasible: ..." | "reached cap ..."


def maximum_sustainable_budgets(search: ThresholdSearch, targets: Sequence[float]) -> list[BudgetResult]: ...
```

## 6. Plan of Work

1. Per-path budget through spending / cash flows / `run_monte_carlo`.
2. Threshold search + B* selection; fixtures and equivalence checks.
3. CLI table, README, timing.

## 7. Validation

- **T1**: unit tests for per-path spending; ruff; mypy.
- **T2**: deterministic closed-form fixture (§17.2); equivalence with a literal scalar bisection on the rate;
  confirmation run at B*.
- **T3**: timing of the example (100k paths) recorded.

## 8. Decision Log

- 2026-10-09 — Per-path threshold bisection, one search for all targets (Interview Q1; optimization §1).
- 2026-10-09 — Bounds £0 → doubling from 2 × Budget to a £1M cap; £1/month tolerance; infeasible targets reported
  (Interview Q2; optimization §1).

## 9. Surprises

_(filled during implementation)_

## 10. Tasks

### F-010.1 Per-path budget in the cash flows
- **Status**: In Progress
- **Depends on**: —

Optional `monthly_budget_today` (scalar or (n_paths,)) through `ScenarioSpending`, `ScenarioCashFlows`,
`run_monte_carlo` (§2 #7). Tests in `tests/unit/test_spending_per_path.py`.

**Acceptance criteria**
- [ ] With a per-path budget array, spending for path i = B_i × I_t × F_t (both alive and survivor cases) — `test_spending_per_path_budget`
- [ ] Omitting the argument or passing the Scenario's Budget as a scalar gives results identical to before (fixture run equal to F-009's) — `test_spending_default_budget_unchanged`
- [ ] A budget array of the wrong shape, or any negative or non-finite entry, raises `ValueError` — `test_spending_rejects_bad_budget`

### F-010.2 Thresholds and the maximum sustainable budget
- **Status**: To Do
- **Depends on**: F-010.1

`ThresholdSearch`, `path_budget_thresholds`, `BudgetResult`, `maximum_sustainable_budgets` in
`src/sbretire/optimization.py` (§2 #1–#6, #8). Tests in `tests/integration/test_optimization.py`.

**Acceptance criteria**
- [ ] Deterministic fixture (step mortality table, σ = 0 zero inflation, zero return, no income, 1 path): B* is within £1 below the closed form balance ÷ (m_both + f · m_one) and feasible (§17.2) — `test_optimization_deterministic_fixture_closed_form`
- [ ] On the fixture scenario (seed pinned, 400 paths, three targets) B* equals a literal scalar bisection on the Conservative Success Rate to within £1 — `test_optimization_matches_scalar_bisection`
- [ ] A confirming `run_monte_carlo` at B* (scalar) gives conservative rate ≥ p* and equal to `estimated_success_probability`; at B* + £2 the rate is < p* unless thresholds tie — `test_optimization_confirming_run`
- [ ] A target above the share of completed-by-death paths returns B* None, converged False, note "infeasible" — `test_optimization_infeasible_target`
- [ ] A scenario whose income exceeds any budget up to the cap flags `capped` paths and marks affected targets not converged with a "cap" note — `test_optimization_reports_cap`
- [ ] B* is non-increasing as the target rises; iterations and tolerance are reported; the `RandomInputs` are unchanged after the search (CRN) — `test_optimization_monotone_and_crn`

### F-010.3 `sbretire run` shows the maximum sustainable budgets
- **Status**: To Do
- **Depends on**: F-010.2

`run` adds a table (one row per confidence level) after the F-009 summary; README; timing.

**Acceptance criteria**
- [ ] `run` prints, per confidence level: target, B* per month and per year (today's GBP), estimated success ± SE, unresolved share, converged, iterations; infeasible targets say so; ASCII — `test_cli_run_prints_maximum_budgets`
- [ ] Example config (100,000 paths) completes with the optimisation in under 300 s; elapsed recorded in Notes — `check: time uv run sbretire run --config config/model.example.yaml --output-dir <tmp>`
- [ ] README documents the Maximum Sustainable Budget, the tolerance, infeasible targets and that it is not advice — `check: grep -n "Maximum sustainable budget" README.md`

## 11. Open Questions

- Writing these rows to `lifestyle_results.csv` is F-013.

## 12. Acceptance Criteria

1. Per-path spending — `test_spending_per_path_budget`
2. Default unchanged — `test_spending_default_budget_unchanged`
3. Bad budget rejected — `test_spending_rejects_bad_budget`
4. Closed-form fixture — `test_optimization_deterministic_fixture_closed_form`
5. Matches scalar bisection — `test_optimization_matches_scalar_bisection`
6. Confirming run — `test_optimization_confirming_run`
7. Infeasible target — `test_optimization_infeasible_target`
8. Cap reported — `test_optimization_reports_cap`
9. Monotone + CRN — `test_optimization_monotone_and_crn`
10. CLI table — `test_cli_run_prints_maximum_budgets`
11. Timing — `check: time sbretire run on the example`
12. README — `check: grep -n "Maximum sustainable budget" README.md`
