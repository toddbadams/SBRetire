---
id: F-020
type: feature
parent: v1-1-enhancements
status: in-progress
complexity: 3
created: 2026-10-09
updated: 2026-10-09
---
# F-020 Spend-At-Least-Income Option

## 1. Purpose

V1 saves any month's income above the Budget-based spending: the surplus stays in the portfolio. The user wants to
model a household that always spends at least what comes in. A new option `budget.spend_at_least_income: true`
(default false) makes each month's **Required Spending** the larger of the Budget-based spending (SPEC §6) and that
month's household income (SPEC §8). Surplus income is then spent, not saved, and every result (success rates,
maximum budgets, required returns, annual results) reflects that household.

Requested by the user on 2026-10-09 ("spending is at least equivalent to income", option (a) spend all income);
epic `v1-1-enhancements`.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Config | `budget.spend_at_least_income`: boolean, default `false` | Opt-in; V1 unchanged by default | user decision (a) |
| 2 | Rule | When on, S'_t = max(B × I_t × F_t, Y_t) per path and month, with Y_t the household income due that month (all streams, survivor shares applied). After both deaths both are 0 | "Spend all income": surplus income is spent each month | user decision (a) |
| 3 | Placement | `ScenarioCashFlows.spending` applies the floor, so the Monte Carlo engine, both searches, the annual results and `preview` all see the same Required Spending | One definition of Required Spending | SPEC §6 |
| 4 | Depletion | Unchanged rule (SPEC §9). With the floor, a month whose income covers the budget-based spending costs the portfolio nothing; the portfolio still pays any excess of the budget over income | Follows from §2 #2 | SPEC §9 |
| 5 | Searches | Budget search: S' is non-decreasing in B, so success stays monotone and the per-path bisection applies (verified by a test). Return search: spending does not depend on the return, so its monotonicity is unchanged | Same argument as optimization §1–§2 | optimization §1–§2 |
| 6 | Outputs | No new columns. `annual_budget_nominal_median` is Required Spending, so it includes the top-up; `monthly_budget_nominal_median` stays B × I. `run` prints one line saying the option is on; the results guide states the rule | The column meaning is "required spending" | simulation-conventions §8 |
| 7 | Config Hash | Left out at its default (as F-019's option), so V1 configs keep their hash | configuration §7 | optimization §3 |
| 8 | Reserve (F-019) | The End-of-Life Reserve still uses R × B × I_d (the Budget, not the topped-up spending) | User's reserve definition | optimization §3 |

## 3. Context

- `ScenarioCashFlows` combines `ScenarioIncome` and `ScenarioSpending`; the engine calls `income` then `spending` for
  the same month and alive state (F-003, F-004).
- `metadata._OPTIONS_HASHED_ONLY_WHEN_SET` (F-019) lists post-V1 options left out of the hash at their default.
- The input rows (F-017) need a label for every new field.

## 4. Touch-points

**New**: `tests/unit/test_spend_at_least_income.py`.

**Modified**: `src/sbretire/config.py`, `src/sbretire/cash_flows.py`, `src/sbretire/metadata.py`,
`src/sbretire/inputs_report.py`, `src/sbretire/__main__.py`, `src/sbretire/results_guide.py`,
`tests/unit/test_cli_run.py`, `tests/unit/test_results_guide.py`, `tests/acceptance/test_v1_acceptance.py`,
`README.md`, `docs/THESAURUS.md` (Required Spending), `docs/decisions/configuration.md` (§9),
`config/model.example.yaml` (commented key).

## 5. Interfaces

```python
# config.py
class BudgetAssumptions(_Frozen):
    ...
    spend_at_least_income: Boolean = False


# cash_flows.py
class ScenarioCashFlows:
    def spending(self, month: int, alive: BoolArray) -> FloatArray:
        """B × I × F, or max(B × I × F, income) when budget.spend_at_least_income is true."""
```

## 6. Plan of Work

1. Config field, the floor in `ScenarioCashFlows.spending`, Config Hash, input label.
2. Search monotonicity and closed form with the option; `run` line, guide, README, THESAURUS, decision.

## 7. Validation

- **T1**: cash-flow unit test where income is below, equal to and above the budget-based spending; default off equals
  V1 exactly.
- **T2**: closed form — zero return and inflation, 3,000/month income in months 0–23 only, both die in month 60,
  balance 50,000: B* = (50,000 + 24 × 3,000) / 60 = 2,033.33 off and 50,000 / 36 = 1,388.89 on; seeded
  monotonicity with the option on.
- **T3**: CLI run with the option prints the line and its CSVs equal the library output.

## 8. Decision Log

- 2026-10-09 — §2 #1–#2 from the user's choice (a); #3–#8 by me (configuration §9).

## 9. Surprises

- 2026-10-09 — F-020.2: the briefed closed form (no income for 24 months, then 3,000/month) is wrong: the binding
  constraint is running out in month 23, which is the same with the option on or off (both 2,083.33). Replaced by
  income first (months 0–23) then none, where the option changes B* from 2,033.33 to 1,388.89. Brief §7 and the AC
  updated before the code.

## 10. Tasks

### F-020.1 Spend-at-least-income in the cash flows
- **Status**: Verification
- **Depends on**: —

§2 #1–#4, #7: config field, the floor in `ScenarioCashFlows.spending`, Config Hash exclusion at default, input-row
label. Tests in `tests/unit/test_spend_at_least_income.py`.

**Acceptance criteria**
- [x] `spend_at_least_income` defaults to false, accepts true and rejects "yes", 1 and null with a located message — `test_budget_spend_at_least_income_validated`
- [x] With the option on, monthly spending equals income where income exceeds B × I × F, equals B × I × F otherwise, and is 0 once both have died; with it off, spending equals `ScenarioSpending` exactly — `test_spend_at_least_income_floors_spending_at_income`
- [x] A V1 config's Config Hash is unchanged by the default; `true` changes it — `test_config_sha256_spend_option_default_excluded`

**Notes**
- 2026-10-09 `BudgetAssumptions.spend_at_least_income` (Boolean, default false); `ScenarioCashFlows.spending` returns max(budget-based spending, the same month's income) when on; added to `metadata._OPTIONS_HASHED_ONLY_WHEN_SET`; input-row label. Tests `tests/unit/test_spend_at_least_income.py` (3).

### F-020.2 Searches, run output and docs with the option
- **Status**: Verification
- **Depends on**: F-020.1

§2 #5–#6, #8: verify the searches, print the option line, guide text, README, THESAURUS, decision configuration §9,
example config comment.

**Acceptance criteria**
- [x] Closed form (§7 T2): B* within £1 below 2,033.33 with the option off and below 1,388.89 with it on — `test_spend_at_least_income_closed_form`
- [x] With the option on, on 400 seeded paths the successful set never grows as the budget rises and each path's threshold separates its successes from its failures — `test_spend_at_least_income_budget_monotone`
- [x] `run` with the option prints that spending is at least income, and its lifestyle and sustainability CSVs equal the library output on the same inputs — `test_cli_run_spend_at_least_income`
- [x] The results guide states the rule when on and not when off — `test_results_guide_spend_at_least_income`
- [x] README documents `spend_at_least_income` — `test_readme_covers_v1_sections`
- [x] THESAURUS (Required Spending) and configuration §9 record the rule — `check: grep -n "spend_at_least_income" docs/THESAURUS.md docs/decisions/configuration.md`

**Notes**
- 2026-10-09 No search code changed: the floor lives in `ScenarioCashFlows`, so both searches see it; closed form and seeded monotonicity tests confirm. `format_run_summary` prints the option line when on; results guide Spending section adds the max(B x I_t x F_t, Y_t) rule when on; README config row and budget bullet; example config comment; THESAURUS + configuration §9 committed with the brief. Tests: 2 in `test_spend_at_least_income.py`, `test_cli_run_spend_at_least_income`, `test_results_guide_spend_at_least_income`, README key guard. Full gate 398 passed.
- 2026-10-09 One gate run during the red phase hit a transient MemoryError and a failed `--version` subprocess; both passed on three reruns with ample free memory (not reproducible).

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Config validation — `test_budget_spend_at_least_income_validated`
2. Floor in cash flows — `test_spend_at_least_income_floors_spending_at_income`
3. Config Hash stable — `test_config_sha256_spend_option_default_excluded`
4. Closed form — `test_spend_at_least_income_closed_form`
5. Monotone — `test_spend_at_least_income_budget_monotone`
6. run output — `test_cli_run_spend_at_least_income`
7. Guide — `test_results_guide_spend_at_least_income`
8. README — `test_readme_covers_v1_sections`
9. THESAURUS + decision — `check: grep -n "spend_at_least_income" docs/THESAURUS.md docs/decisions/configuration.md`
