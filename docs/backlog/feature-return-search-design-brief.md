---
id: F-011
type: feature
parent: analysis-optimization
status: in-progress
complexity: 4
created: 2026-10-09
updated: 2026-10-09
---
# F-011 Return Search

## 1. Purpose

For a fixed Budget (the configured `budget.monthly_amount_today`), find the minimum fixed annual effective return at
which the **Conservative Success Rate** reaches each target in `model.confidence_levels` (SPEC §13), with **Common
Random Numbers** across candidate returns (SPEC §10.3), explicit bounds and tolerance, a documented no-solution
behaviour, convergence and iteration reporting, and an explicit check that success is monotone in the return for the
chosen cash-flow convention. `sbretire run` prints the result.

Resolves the return half of SPEC §18 "Budget and return optimization bounds and tolerances" (optimization §2). Makes
passable SPEC §17.1 "Common random numbers are reused across candidate … returns" and §17.2 "Return optimization either
converges to a valid bracketed result or clearly reports no solution".

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Monotonicity | The balance never goes negative and the return applies to the opening balance (simulation-conventions §2), so per path the balance in every month is non-decreasing in the return; success is therefore monotone non-decreasing in the return. **Verified empirically** on a grid of returns (SPEC §13 requires it) | SPEC §13 | SPEC §13 |
| 2 | Algorithm | **Per-path threshold bisection** (mirrors optimization §1): each completed-by-death Path i has a minimum return R_i at which it is Successful; all paths bisected together with a per-path return array; rate(r) = #{R_i ≤ r}/N; required return for p* = the ⌈p*·N⌉-th smallest R_i; one confirming run per target gives the exact rate, SE and unresolved share | One search for all targets; consistent with F-010 | Interview Q1; optimization §2 |
| 3 | Bounds and tolerance | Fixed bounds −50 % … +50 % a year; tolerance 0.0001 (0.01 percentage points); R_i = the feasible (upper) end of its final bracket | Wide enough that strong-income plans don't sit on a bound; ~14 rounds | Interview Q2; optimization §2 |
| 4 | Edge cases | Path failing even at +50 % → R = +∞ (no solution in range); path Successful even at −50 % → R = −50 % (flagged `at_lower_bound`); paths with someone alive at the Horizon → R = +∞ (never Successful). Per target: fewer than ⌈p*·N⌉ finite R → **no solution within bounds** (r* None, converged False); r* at −50 % → reported as "≤ −50 %", converged False | SPEC §13 "behaviour when no solution exists" | Interview Q2 |
| 5 | Reported per target | `monthly_budget_today`, `target_probability`, `required_annual_return`, `estimated_success_probability` (confirming run), `standard_error` (denominator all paths), `unresolved_fraction`, `return_tolerance`, `converged`, `iterations`, `note` | SPEC §13 columns + SE | SPEC §13 |
| 6 | Per-path return plumbing | `simulate_paths(annual_return: float | FloatArray)` and `run_monte_carlo(annual_return=...)`; the monthly rate (1 + r)^(1/12) − 1 per path | Minimal engine change; scalar path unchanged | Brief author |
| 7 | Placement | `sbretire/optimization.py` (alongside the budget search) | One module for both searches | Brief author |

## 3. Context

- `simulate_paths(starting_balance, annual_return: float, …)`; `monthly_return_rate(annual)` rejects ≤ −1;
  `apply_month(balance, rate, income, spending)` is already elementwise.
- `run_monte_carlo(scenario, inputs, monthly_budget_today=None)` (F-010); `ThresholdSearch`,
  `maximum_sustainable_budgets` pattern (F-010).
- `sbretire run` prints the F-009 summary and the F-010 budget table (≈ 45 s for 100k paths).

## 4. Touch-points

**New**: `tests/unit/test_simulation_per_path_return.py`, `tests/integration/test_return_search.py`.

**Modified**: `src/sbretire/portfolio.py`, `src/sbretire/simulation.py`, `src/sbretire/monte_carlo.py`,
`src/sbretire/optimization.py`, `src/sbretire/__main__.py`, `tests/unit/test_cli_run.py`, `README.md`,
`docs/decisions/optimization.md` (§2, with this brief).

## 5. Interfaces

```python
# sbretire/optimization.py
RETURN_LOWER: Final = -0.5
RETURN_UPPER: Final = 0.5
RETURN_TOLERANCE: Final = 0.0001


@dataclass(frozen=True)
class ReturnSearch:
    thresholds: FloatArray  # (n_paths,) minimum annual return found Successful; +inf if none in range
    at_lower_bound: BoolArray  # Successful even at RETURN_LOWER
    iterations: int
    monthly_budget_today: float
    scenario: Scenario
    inputs: RandomInputs


def path_return_thresholds(
    scenario: Scenario, inputs: RandomInputs, monthly_budget_today: float | None = None
) -> ReturnSearch: ...


@dataclass(frozen=True)
class ReturnResult:
    monthly_budget_today: float
    target_probability: float
    required_annual_return: float | None
    estimated_success_probability: float | None
    standard_error: float | None
    unresolved_fraction: float
    return_tolerance: float
    converged: bool
    iterations: int
    note: str


def required_returns(search: ReturnSearch, targets: Sequence[float]) -> list[ReturnResult]: ...
```

## 6. Plan of Work

1. Per-path return in the engine.
2. Return thresholds, required returns, monotonicity verification.
3. CLI table, README, decision, timing.

## 7. Validation

- **T1**: unit tests for the per-path return; ruff; mypy.
- **T2**: closed-form fixture (independent brentq root); scalar-bisection agreement; confirming runs; monotonicity grid.
- **T3**: timing of `sbretire run` on the example.

## 8. Decision Log

- 2026-10-09 — Per-path threshold bisection for the return (Interview Q1; optimization §2).
- 2026-10-09 — Fixed bounds −50 % … +50 %, tolerance 0.01 pp; no-solution and lower-bound reporting (Interview Q2;
  optimization §2).

## 9. Surprises

_(filled during implementation)_

## 10. Tasks

### F-011.1 Per-path return in the engine
- **Status**: Verification
- **Depends on**: —

`annual_return` as scalar or (n_paths,) through `simulate_paths` and `run_monte_carlo` (§2 #6). Tests in
`tests/unit/test_simulation_per_path_return.py`.

**Acceptance criteria**
- [x] With a per-path return array, each path's outcomes equal a scalar run of that path alone at its own return — `test_simulate_paths_per_path_return_matches_scalar_runs`
- [x] A scalar return gives results identical to before (fixture run equal across scalar and full array) — `test_simulate_paths_scalar_return_unchanged`
- [x] A return ≤ −1 (scalar or any entry) or an array of the wrong shape raises `ValueError` — `test_simulate_paths_rejects_bad_return`

**Notes**
- 2026-10-09 Added `monthly_return_rates` (scalar → `monthly_return_rate`; (n_paths,) array validated finite, > −1, right shape) in `src/sbretire/portfolio.py`; `apply_month` takes a scalar or per-path rate; `simulate_paths` and `run_monte_carlo(annual_return=...)` accept a per-path return. Tests `tests/unit/test_simulation_per_path_return.py` (7).

### F-011.2 Return thresholds and the required return
- **Status**: To Do
- **Depends on**: F-011.1

`ReturnSearch`, `path_return_thresholds`, `ReturnResult`, `required_returns` in `src/sbretire/optimization.py`
(§2 #1–#5). Tests in `tests/integration/test_return_search.py`.

**Acceptance criteria**
- [ ] Monotonicity verified (SPEC §13): on the fixture (seed pinned, 300 paths), over returns −10 % … +15 % in 1 % steps, no path that is Successful at r is not Successful at any higher r, and the conservative rate is non-decreasing — `test_success_is_monotone_in_return`
- [ ] Deterministic fixture (step mortality, zero inflation, no income, 1 path, budget 6,000): the required return is within 0.0001 of the independent brentq root of B₀ = Σ S_t (1 + m)^−(t+1) converted to annual — `test_return_search_deterministic_closed_form`
- [ ] Agrees with a literal scalar bisection on the conservative rate within 0.0001 for three targets (seed pinned, 400 paths) — `test_return_search_matches_scalar_bisection`
- [ ] Confirming run at r* gives rate ≥ p* and equals `estimated_success_probability`; at r* − 0.0002 the rate is < p* — `test_return_search_confirming_run`
- [ ] Targets needing more paths than can succeed at +50 % report no solution (r* None, converged False, note "no solution"); a plan Successful at −50 % reports "≤ -50%" not converged — `test_return_search_reports_bounds`
- [ ] r* is non-decreasing as the target rises; iterations and tolerance reported; `RandomInputs` unchanged (CRN) — `test_return_search_monotone_targets_and_crn`

### F-011.3 `sbretire run` shows the required returns
- **Status**: To Do
- **Depends on**: F-011.2

`run` adds a required-return table after the budget table (reusing the same `RandomInputs`); README; decision §2
recorded with the brief.

**Acceptance criteria**
- [ ] `run` prints, per confidence level at the configured budget: target, required annual return (%), estimated success ± SE, unresolved share, converged, iterations; no-solution and lower-bound rows say so; ASCII — `test_cli_run_prints_required_returns`
- [ ] The example config completes in under 300 s with both searches; elapsed recorded in Notes — `check: time uv run sbretire run --config config/model.example.yaml --output-dir <tmp>`
- [ ] README documents the required return, its bounds/tolerance, no-solution behaviour and that it is not a forecast — `check: grep -n "Required return" README.md`

## 11. Open Questions

- Testing several budgets for `sustainability_results.csv` ("one row per tested budget/target pair") — F-013.

## 12. Acceptance Criteria

1. Per-path return matches scalar runs — `test_simulate_paths_per_path_return_matches_scalar_runs`
2. Scalar unchanged — `test_simulate_paths_scalar_return_unchanged`
3. Bad return rejected — `test_simulate_paths_rejects_bad_return`
4. Monotonicity verified — `test_success_is_monotone_in_return`
5. Closed form — `test_return_search_deterministic_closed_form`
6. Scalar bisection agreement — `test_return_search_matches_scalar_bisection`
7. Confirming run — `test_return_search_confirming_run`
8. Bounds reporting — `test_return_search_reports_bounds`
9. Monotone targets + CRN — `test_return_search_monotone_targets_and_crn`
10. CLI table — `test_cli_run_prints_required_returns`
11. Timing — `check: time sbretire run on the example`
12. README — `check: grep -n "Required return" README.md`
