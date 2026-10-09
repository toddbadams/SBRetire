---
id: F-002
type: feature
parent: simulation-engine
status: in-progress
complexity: 4
created: 2026-10-09
updated: 2026-10-09
---
# F-002 Deterministic Portfolio Engine (Walking Skeleton)

## 1. Purpose

The monthly portfolio accounting at the heart of the model (SPEC §9, §10.2): for every **Path** at once, step month
by month from the As-Of month, apply the fixed return to the opening balance, add income, and pay **Required
Spending** — detecting **Depletion** and recording the **Shortfall** the first month spending can't be funded, and
stopping when both people are dead (**Household End**). Everything is deterministic here: deaths are supplied as
**Death Months** and income/spending come from an injected cash-flow provider, so the engine is proven with exact
numbers before any randomness (F-005, F-006, F-008) or real income/spending rules (F-003, F-004) arrive.

Resolves the SPEC §18 item "within-month cash-flow ordering and death timing" (simulation-conventions §2).

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Within-month ordering | Alive-state update → income & spending due → return on opening balance → add income → funding test → subtract spending | SPEC's V1 default | SPEC §5; simulation-conventions §2 |
| 2 | Monthly return | r_m = (1 + r_a)^(1/12) − 1 | SPEC formula | SPEC §9 |
| 3 | Depletion | If balance after return + income < spending: path depleted that month, available funds are spent, shortfall = spending − available, balance = 0, path stops. Equality is funded. No negative balance ever compounds | SPEC's recommended shortfall rule | SPEC §9; simulation-conventions §2 |
| 4 | Death timing | `death_month[p]` = first month index person p is dead; alive for the whole of the month before; the alive update is step 1 of each month; both dead at a month start → path ends before that month's cash flows | Whole-month boundaries match monthly q_m sampling (F-008); one fact — "alive at month start" — drives everything | Interview Q1; simulation-conventions §2 |
| 5 | Cash-flow seam | `HouseholdCashFlows` protocol, `income(month, alive)` / `spending(month, alive)` → nominal GBP per path, evaluated one month at a time | Memory bounded (SPEC §10.4); engine testable with exact numbers; F-003/F-004/F-006 plug in unchanged | Interview Q2 |
| 6 | Outputs | Frozen `PathOutcomes` (per-path arrays) + optional per-month `observer` | F-009/F-012 aggregate monthly without months × paths storage | Interview Q3; SPEC §10.4 |
| 7 | Death input | `death_month: int64[2, n_paths]` supplied up front; value ≥ horizon = alive at the horizon | Bounded memory; the same deaths reused across optimization candidates (CRN, SPEC §10.3) | Brief author, confirmed |
| 8 | Time base | Month 0 = As-Of month; `horizon_months = horizon_years × 12` | Simulation-conventions §1 | simulation-conventions §1 |
| 9 | Censoring | Path flagged `censored` when at least one person is alive at the horizon (any `death_month ≥ horizon_months`); success classification is F-009's | SPEC §7.2 | SPEC §7.2, §10.2 step 10 |

## 3. Context

- Code today: `sbretire.config` (validated `Scenario`), CLI. No engine.
- Constraints (CLAUDE.md): vectorised over paths — the month loop is the only Python loop; float64 nominal GBP;
  no randomness in this feature; mypy --strict with `numpy.typing.NDArray`.
- Downstream: F-003/F-004 implement `HouseholdCashFlows` from the Scenario; F-008 produces `death_month`;
  F-009 classifies outcomes and uses the observer; F-012 aggregates via the observer.

## 4. Touch-points

**New**

| File | Purpose |
|---|---|
| `src/sbretire/portfolio.py` | `monthly_return_rate`, `apply_month`, `MonthResult` |
| `src/sbretire/simulation.py` | `HouseholdCashFlows`, `MonthObserver`, `PathOutcomes`, `simulate_paths` |
| `tests/unit/test_portfolio.py` | month-step arithmetic and ordering |
| `tests/unit/test_simulation.py` | path loop, deaths, depletion, censoring, observer |
| `tests/unit/cash_flow_doubles.py` | test doubles: constant / scripted `HouseholdCashFlows` |
| `tests/integration/test_engine_closed_form.py` | closed-form known-answer checks (T3) |

**Modified:** none (decision simulation-conventions §2 and thesaurus terms **Death Month**, **Household End**
were written with this brief).

**Deleted:** none.

## 5. Interfaces

```python
FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


# sbretire.portfolio
def monthly_return_rate(annual_return: float) -> float: ...  # requires annual_return > -1


class MonthResult(NamedTuple):
    balance: FloatArray  # closing balance, >= 0
    depleted: BoolArray  # True where spending could not be funded this month
    shortfall: FloatArray  # unmet spending (0 where funded)


def apply_month(
    balance: FloatArray, rate: float, income: FloatArray, spending: FloatArray
) -> MonthResult: ...


# sbretire.simulation
class HouseholdCashFlows(Protocol):
    def income(
        self, month: int, alive: BoolArray
    ) -> FloatArray: ...  # alive: (2, n_paths); returns (n_paths,)
    def spending(self, month: int, alive: BoolArray) -> FloatArray: ...  # nominal GBP for this month


class MonthObserver(Protocol):
    def __call__(self, month: int, balance: FloatArray, alive: BoolArray, active: BoolArray) -> None: ...

    # called after month `month`'s cash flows; balance = closing; active = paths running at the month's start


@dataclass(frozen=True)
class PathOutcomes:
    depletion_month: IntArray  # month of Depletion, -1 if never
    shortfall: FloatArray  # unmet spending in that month, 0 if never depleted
    household_end_month: IntArray  # first month both are dead, -1 if not within the horizon
    censored: BoolArray  # at least one person alive at the horizon
    final_balance: FloatArray  # balance when the path stopped (0 if depleted)


def simulate_paths(
    *,
    starting_balance: float,
    annual_return: float,
    death_month: IntArray,
    horizon_months: int,
    cash_flows: HouseholdCashFlows,
    observer: MonthObserver | None = None,
) -> PathOutcomes: ...
```

Month loop (t = 0 … horizon_months − 1): `alive = t < death_month`; `active` = not yet depleted and not both dead;
stop early once no path is active. Cash-flow providers are evaluated for all paths; only active paths change.

## 6. Plan of Work

1. `portfolio.py`: return conversion and the single-month step with the depletion/shortfall rule.
2. `simulation.py`: protocol, outcomes, the month loop with alive masks, household end, censoring, observer.
3. Closed-form known-answer tests.

## 7. Validation

- **T1** — `tests/unit/test_portfolio.py`, `tests/unit/test_simulation.py`; ruff, mypy --strict.
- **T2** — n/a until a scenario drives the engine (F-003/F-004 wire cash flows; F-013 the CLI).
- **T3** — `tests/integration/test_engine_closed_form.py`: annuity depletion month and interest-only perpetuity.

No randomness: nothing to pin.

## 8. Decision Log

- 2026-10-09 — Interview Q1–Q3 settled decisions 4–6; decisions 1–3 and 8–9 taken from SPEC / existing decisions; decision 7 proposed by brief author and confirmed. Decisions 1, 3, 4 recorded as simulation-conventions §2; thesaurus gains Death Month and Household End.

## 9. Surprises

- 2026-10-09 — Timing at SPEC scale (100k paths × 1,200 months, constant cash flows): 1.65 s per run on the dev box. A budget bisection of ~20 iterations × 3 confidence levels is ~100 s — acceptable for V1, but F-010 should reuse precomputed draws and may cache cash-flow arrays per month.
- 2026-10-09 — F-002.3 is pure verification of F-002.1/.2 behaviour: written test-first is impossible for known-answer checks of existing code, so it was committed as a single `test(F-002.3)` commit with a documented sensitivity check.

## 10. Tasks

Task format and statuses: `docs/project-sdlc.md` §2. Definition of done: `docs/project-sdlc.md` §4.

### F-002.1 Monthly portfolio step
- **Status**: Done
- **Depends on**: —

`src/sbretire/portfolio.py`: `monthly_return_rate` and `apply_month` / `MonthResult` (brief §2 #1–#3, §5). Pure
array functions, float64, no loops. Tests in `tests/unit/test_portfolio.py`.

**Acceptance criteria**
- [x] Annual→monthly conversion matches (1+r_a)^(1/12)−1 and twelve monthly steps compound back to r_a (including negative and zero returns) — `test_monthly_return_rate_compounds_to_annual`
- [x] Return applies to the opening balance only, then income is added, then spending is paid (exact numbers on a hand-worked case) — `test_apply_month_orders_return_income_then_spending`
- [x] When balance after return + income < spending the path is depleted, shortfall = spending − available and the closing balance is 0; equality is funded — `test_apply_month_depletion_records_shortfall`
- [x] No closing balance is ever negative across mixed paths (property test) — `test_apply_month_never_negative`

**Notes**
- 2026-10-09: `src/sbretire/portfolio.py` — `monthly_return_rate` (rejects r_a ≤ −1), `apply_month` returning `MonthResult(balance, depleted, shortfall)`; three vectorised `np.where` lines, no loops. Tests: `tests/unit/test_portfolio.py` (11 incl. a hypothesis property test and a negative-return depletion case).
- 2026-10-09 /verify PASS:
  - test_portfolio.py: 11 passed; hand-worked case 860 distinguishes income-first (860.5) and spend-first (858)
  - code matches simulation-conventions §2 steps 3–6; vectorised, no loops, rejects r_a <= -1
  - probe: available 150 vs spending 150 funded; vs 150.000001 depleted, shortfall ~1e-6
  - ruff + mypy clean; no network/tax/loops in portfolio.py

### F-002.2 Path loop with deaths, depletion, censoring and observer
- **Status**: Done
- **Depends on**: F-002.1

`src/sbretire/simulation.py`: `HouseholdCashFlows`, `MonthObserver`, `PathOutcomes`, `simulate_paths` (brief §2
#4–#9, §5). Test doubles in `tests/unit/cash_flow_doubles.py`; tests in `tests/unit/test_simulation.py`.

**Acceptance criteria**
- [x] A path records Depletion at the first month it cannot fund spending, with that month's shortfall — `test_simulate_paths_records_first_depletion_month`
- [x] After Depletion the balance stays 0 and the path receives no further cash flows or returns — `test_simulate_paths_no_compounding_after_depletion`
- [x] Zero spending never depletes, whatever the balance and income — `test_simulate_paths_zero_spending_never_depletes`
- [x] No starting capital and no income depletes in month 0 when positive spending is due — `test_simulate_paths_no_capital_no_income_depletes_immediately`
- [x] A person is alive in month d−1 and dead from month d; when both are dead the path ends before that month's cash flows and `household_end_month` is recorded — `test_simulate_paths_deaths_take_effect_at_month_start`
- [x] Paths with someone alive at the horizon are `censored`; others are not — `test_simulate_paths_flags_censored_paths`
- [x] The observer is called once per simulated month with closing balance, alive and active masks — `test_simulate_paths_calls_observer_each_month`
- [x] Simulating many heterogeneous paths together gives exactly the same outcomes as simulating each alone — `test_simulate_paths_vectorised_matches_single_paths`

**Notes**
- 2026-10-09: `src/sbretire/simulation.py` — `HouseholdCashFlows` / `MonthObserver` protocols, frozen `PathOutcomes`, `simulate_paths` (input validation; `alive = month < death_month`; only active paths change; loop stops when none active). Test doubles `tests/unit/cash_flow_doubles.py`; tests `tests/unit/test_simulation.py` (14, incl. early stop and input validation).
- 2026-10-09 /verify PASS:
  - test_simulation.py: 14 passed; AC8 compares all five fields over 40 seeded paths
  - code matches simulation-conventions §2 and brief §2 #4–#9; only the month loop is a Python loop
  - probe: both dead at month 0 -> no cash flows, household_end 0, balance unchanged, observer never called
  - probe: death_month == horizon -> censored, household_end -1; thesaurus definitions match the code
  - ruff + mypy clean

### F-002.3 Closed-form known-answer checks
- **Status**: Done
- **Depends on**: F-002.2

`tests/integration/test_engine_closed_form.py` (T3): the engine reproduces closed-form annuity and perpetuity
results, so the month loop is checked against mathematics rather than against itself.

**Acceptance criteria**
- [x] With constant spending and no income, the depletion month equals the closed-form annuity month for several (balance, rate, spending) cases — `test_engine_depletion_month_matches_annuity_formula`
- [x] Spending equal to the monthly interest on the starting balance never depletes and keeps the balance constant — `test_engine_interest_only_spending_is_perpetual`

**Notes**
- 2026-10-09: `tests/integration/test_engine_closed_form.py` — annuity depletion month (5 cases incl. negative and zero return) and interest-only perpetuity (3 cases). Known-answer tests against existing code, so there was no red phase; sensitivity checked instead: under a spend-before-return ordering two of the five annuity cases change month (175→174, 254→250), so the test would catch an ordering regression.
- 2026-10-09 /verify PASS:
  - test_engine_closed_form.py: 8 passed
  - closed form re-derived independently, incl. negative r and r = 0
  - plain-loop cross-check equals formula and engine for all 5 annuity cases
  - spend-before-return ordering changes 2 cases (175->174, 254->250): the test can fail on an ordering bug
  - ruff + mypy clean

## 11. Open Questions

- Should the engine expose the monthly net withdrawal to the observer (SPEC §12 `annual_net_withdrawal_median`)? Defer to F-012; the observer signature may gain arguments then.

## 12. Acceptance Criteria

1. Monthly return conversion — `test_monthly_return_rate_compounds_to_annual`
2. Ordering return → income → spending — `test_apply_month_orders_return_income_then_spending`
3. Depletion + shortfall + zero floor — `test_apply_month_depletion_records_shortfall`
4. Never negative — `test_apply_month_never_negative`
5. First depletion month recorded — `test_simulate_paths_records_first_depletion_month`
6. No compounding after depletion — `test_simulate_paths_no_compounding_after_depletion`
7. Zero spending never depletes — `test_simulate_paths_zero_spending_never_depletes`
8. No capital, no income depletes immediately — `test_simulate_paths_no_capital_no_income_depletes_immediately`
9. Deaths at month start; household end — `test_simulate_paths_deaths_take_effect_at_month_start`
10. Censoring flag — `test_simulate_paths_flags_censored_paths`
11. Observer per month — `test_simulate_paths_calls_observer_each_month`
12. Vectorised equals single — `test_simulate_paths_vectorised_matches_single_paths`
13. Annuity closed form — `test_engine_depletion_month_matches_annuity_formula`
14. Perpetuity — `test_engine_interest_only_spending_is_perpetual`
