---
id: F-004
type: feature
parent: household-cash-flows
status: in-progress
complexity: 3
created: 2026-10-09
updated: 2026-10-09
---
# F-004 Spending with Survivor Budget Factor

## 1. Purpose

Turn the **Budget** into the engine's monthly **Required Spending** for every **Path** (SPEC §6):
S_t = B_m × I_t × F_t, with F_t = 1 while both people are alive and the **Survivor Budget Factor** once exactly
one is. Combine it with F-003's income into the single `HouseholdCashFlows` the engine expects, so a validated
Scenario can drive `simulate_paths` directly — the last piece before the F-015 preview.

Resolves the SPEC §18-adjacent item "survivor budget factor precedence: per-person override vs household default"
(configuration §6).

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Spending formula | S_t = `budget.monthly_amount_today` × I_t × F_t, nominal GBP | SPEC formula | SPEC §6 |
| 2 | Index | Same `PriceIndex` as income | SPEC §6: income "uses the same CPI path" | SPEC §6; F-003 brief #7 |
| 3 | F_t | 1 while both alive; survivor factor while exactly one alive; 0 once both dead (path has ended) | SPEC §6 | SPEC §6 |
| 4 | Precedence | The **survivor's own** `people[].survivor_budget_factor`; if unset, `budget.survivor_budget_factor` | A person's factor = "my share of the joint budget when I'm the one left"; lets the factor differ by who survives | Interview Q1; configuration §6 |
| 5 | Composition | `ScenarioCashFlows(scenario, price_index, n_paths)` = `ScenarioIncome` + `ScenarioSpending`; validates `price_index.level(0).shape == (n_paths,)` once at construction | Single entry point for the engine; F-003 surprise (index shape checked only in paying months) | F-003 brief §9 |
| 6 | Budget variation for optimization | Not here — F-010 builds candidates from a copied Scenario | YAGNI; keeps F-004 small | Brief author, confirmed |
| 7 | Placement | `sbretire/spending.py`, `sbretire/cash_flows.py` | SPEC §3 module responsibilities | SPEC §3 |

## 3. Context

- `ScenarioIncome(scenario, price_index)` (F-003) provides `income(month, alive)`; `PriceIndex` / `FlatPriceIndex`
  in `sbretire.inflation`; engine `simulate_paths` takes a `HouseholdCashFlows`.
- Person rows in `alive` follow `scenario.people` order.
- No age-varying spending in V1 (not in SPEC).

## 4. Touch-points

**New**

| File | Purpose |
|---|---|
| `src/sbretire/spending.py` | `ScenarioSpending` |
| `src/sbretire/cash_flows.py` | `ScenarioCashFlows` |
| `tests/unit/test_spending.py`, `tests/unit/test_cash_flows.py` | unit tests |
| `tests/integration/test_cash_flows_end_to_end.py` | engine + scenario cash flows (T2) |

**Modified:** `README.md` (budget rules). Decision configuration §6 and the thesaurus update are written with this
brief.

**Deleted:** none.

## 5. Interfaces

```python
# sbretire.spending
class ScenarioSpending:
    def __init__(self, scenario: Scenario, price_index: PriceIndex) -> None: ...
    def spending(self, month: int, alive: BoolArray) -> FloatArray: ...  # nominal GBP, (n_paths,)


# sbretire.cash_flows
class ScenarioCashFlows:  # implements sbretire.simulation.HouseholdCashFlows
    def __init__(self, scenario: Scenario, price_index: PriceIndex, n_paths: int) -> None: ...
    def income(self, month: int, alive: BoolArray) -> FloatArray: ...
    def spending(self, month: int, alive: BoolArray) -> FloatArray: ...
```

Spending per path: `B_m × I_t × where(both alive, 1, where(only p alive, factor_p, 0))`, with
`factor_p = people[p].survivor_budget_factor if set else budget.survivor_budget_factor`.

## 6. Plan of Work

1. `ScenarioSpending` with the precedence rule.
2. `ScenarioCashFlows` composition and construction-time index check; end-to-end test; README budget rules.

## 7. Validation

- **T1** — unit tests per AC; ruff; mypy --strict.
- **T2** — `tests/integration/test_cash_flows_end_to_end.py`: fixture scenario, `FlatPriceIndex`, zero return,
  fixed Death Months → final balance = start + hand-computed income − hand-computed spending.
- **T3** — n/a.

## 8. Decision Log

- 2026-10-09 — Interview Q1 settled decision 4 (survivor's own factor, else household default); decisions 1–3 from SPEC §6; 5–7 proposed by brief author and confirmed. Recorded configuration §6; thesaurus Survivor Budget Factor updated.

## 9. Surprises

- 2026-10-09 — No behavioural surprises. Recurring friction: module docstrings and explanatory test comments often exceed the 110-character line limit; each caught by the edit hook and wrapped by hand.

## 10. Tasks

Task format and statuses: `docs/project-sdlc.md` §2. Definition of done: `docs/project-sdlc.md` §4.

### F-004.1 ScenarioSpending
- **Status**: Verification
- **Depends on**: —

`src/sbretire/spending.py`: `ScenarioSpending(scenario, price_index).spending(month, alive)` per brief §2 #1–#4,
§5. Tests in `tests/unit/test_spending.py` (fixture budget 3000/month, household factor 0.7; alex has no override,
sam has 0.65).

**Acceptance criteria**
- [x] While both are alive, spending is the budget × I_t per path — `test_spending_tracks_price_index_while_both_alive`
- [x] After the first death spending changes to budget × I_t × the survivor's factor — `test_spending_changes_after_first_death_by_survivor_factor`
- [x] The survivor's own factor wins; a survivor without one falls back to the household default — `test_survivor_factor_precedence_uses_survivor_then_default`
- [x] Spending is 0 once both have died, with mixed alive states evaluated together — `test_spending_zero_when_both_dead`

**Notes**
- 2026-10-09: `src/sbretire/spending.py` — `ScenarioSpending` resolves each person's factor-as-survivor once (own override else household default); `spending()` picks the survivor's factor with `np.where(alive[0], …)` and is fully vectorised. Tests: `tests/unit/test_spending.py` (4).

### F-004.2 ScenarioCashFlows and end-to-end check
- **Status**: Verification
- **Depends on**: F-004.1

`src/sbretire/cash_flows.py`: `ScenarioCashFlows` composing income and spending, validating the price index's path
count at construction (brief §2 #5, §5). Tests in `tests/unit/test_cash_flows.py` and
`tests/integration/test_cash_flows_end_to_end.py`; README budget rules.

**Acceptance criteria**
- [x] `ScenarioCashFlows` returns exactly `ScenarioIncome` income and `ScenarioSpending` spending and is accepted by `simulate_paths` — `test_scenario_cash_flows_delegates_income_and_spending`
- [x] A price index whose path count differs from `n_paths` is rejected at construction — `test_scenario_cash_flows_rejects_mismatched_price_index`
- [x] With zero return, the engine's final balance equals start + hand-computed income − hand-computed spending over fixed Death Months — `test_cash_flows_end_to_end_matches_hand_total`
- [x] README documents the survivor budget factor precedence — `check: grep -n "survivor's own" README.md`

**Notes**
- 2026-10-09: `src/sbretire/cash_flows.py` — `ScenarioCashFlows` validates `price_index.level(0).shape == (n_paths,)` at construction, then delegates to `ScenarioIncome` and `ScenarioSpending`. End-to-end test covers two completed paths (final 129 800 and 17 000) and one depleting path that is funded exactly at month 288 and depletes at month 289 with a 2000 shortfall. README gains a "Budget" section. Tests: `tests/unit/test_cash_flows.py` (2), `tests/integration/test_cash_flows_end_to_end.py` (1).


## 11. Open Questions

- Age-varying spending (e.g. lower spending in later life) is outside SPEC V1; would be a new budget field.

## 12. Acceptance Criteria

1. Index-tracking spending while both alive — `test_spending_tracks_price_index_while_both_alive`
2. Spending changes after first death — `test_spending_changes_after_first_death_by_survivor_factor`
3. Precedence survivor → household default — `test_survivor_factor_precedence_uses_survivor_then_default`
4. Zero when both dead — `test_spending_zero_when_both_dead`
5. Composition delegates and fits the engine — `test_scenario_cash_flows_delegates_income_and_spending`
6. Mismatched index rejected at construction — `test_scenario_cash_flows_rejects_mismatched_price_index`
7. Engine end-to-end hand total — `test_cash_flows_end_to_end_matches_hand_total`
8. README precedence — `check: grep -n "survivor's own" README.md`
