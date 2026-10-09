---
id: F-019
type: feature
parent: v1-1-enhancements
status: in-progress
complexity: 5
created: 2026-10-09
updated: 2026-10-09
---
# F-019 End-of-Life Reserve Target

## 1. Purpose

Answer the user's question: "based on mortality, how much can we spend and still be left with 12 months' income in
savings when the second of us dies?" A new option `budget.end_reserve_months` (R, default 0) adds a stricter success
test: a Path meets the **End-of-Life Reserve** target only if it is Successful under SPEC §7.2 *and* its balance at
Household End is at least R × the monthly Budget, inflated to that month. `sbretire run` then reports a second
Maximum Sustainable Budget table "leaving an R-month reserve", next to the unchanged V1 table (SPEC §11, §14).

Requested by the user on 2026-10-09; reserve definition chosen by the user (12 × monthly Budget, today's GBP,
inflated to the date of the second death). Epic `v1-1-enhancements`.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Config | `budget.end_reserve_months`: whole number ≥ 0, default 0 (off). The user's config sets 12 | Opt-in; V1 unchanged by default | user decision; epic |
| 2 | Reserve amount | Required End Balance = R × B × I_d, nominal GBP: B the Budget (today's GBP/month; during the search, the candidate budget), I_d the path's Inflation Index at its Household End month d (the first month both are dead). The full Budget, not the survivor-reduced spending | User chose "12 × monthly budget (today's £), inflated to the date of the second death" | user decision 2026-10-09 |
| 3 | Success under the target | Successful (SPEC §7.2) **and** final balance ≥ Required End Balance. A path that ends below its reserve counts as **Failed** for the reserve metrics (it missed the target); Unresolved paths stay Unresolved and never succeed | Conservative; keeps the three-way split and its rates | SPEC §7.2, §11 |
| 4 | Search | Same per-path threshold bisection as F-010 (optimization §1). Valid because a higher budget leaves a lower (never higher) final balance and needs a higher reserve, so each path still has one threshold. A test checks monotonicity on seeded inputs | Reuse; one definition of B* | optimization §1 |
| 5 | What changes in `run` | Only when R > 0: one summary line (reserve success rate at the configured budget), a second budget table, `lifestyle_reserve_results.csv` (`end_reserve_months` + the lifestyle columns) and a reserve section in the results guide. The V1 summary, tables, CSVs and annual results are identical to R = 0 | User asked for it beside the V1 table | epic scope |
| 6 | Config Hash | Options at their default value are left out of the canonical JSON, so every V1 config keeps its hash | Reproducibility records stay comparable | configuration §7 |
| 7 | Per-path index | `StochasticPriceIndex.level_at(months)` returns each path's I at its own month (vectorised) | Reserve needs I at a different month per path | CLAUDE.md constraint 3 |
| 8 | Return search | Not extended (still V1 success) | Not requested | — |
| 9 | Term | **End-of-Life Reserve** / **Required End Balance** added to `docs/THESAURUS.md` | Ubiquitous language | CLAUDE.md |

## 3. Context

- `simulate_paths` returns `final_balance` (balance when the path stopped) and `household_end_month`; a Successful
  path's final balance is its balance at Household End (F-002, F-009).
- `classify_paths` / `SuccessMetrics.from_outcomes` (F-009); `path_budget_thresholds` /
  `maximum_sustainable_budgets` (F-010); `StochasticPriceIndex.level(month)` gives one month for all paths (F-006).
- `config_sha256` dumps the whole validated Scenario (F-005).

## 4. Touch-points

**New**: `tests/unit/test_end_reserve.py`.

**Modified**: `src/sbretire/config.py`, `src/sbretire/inflation.py`, `src/sbretire/metrics.py`,
`src/sbretire/monte_carlo.py`, `src/sbretire/metadata.py`, `src/sbretire/optimization.py`,
`src/sbretire/reporting.py`, `src/sbretire/results_guide.py`, `src/sbretire/inputs_report.py`,
`src/sbretire/__main__.py`, `tests/unit/test_cli_run.py`, `tests/unit/test_results_guide.py`,
`tests/acceptance/test_v1_acceptance.py`, `README.md`, `docs/THESAURUS.md`, `docs/decisions/optimization.md` (§3),
`config/model.example.yaml` (commented key).

## 5. Interfaces

```python
# config.py
class BudgetAssumptions(_Frozen):
    ...
    end_reserve_months: Annotated[Integer, Field(ge=0)] = 0


# inflation.py
class StochasticPriceIndex:
    def level_at(self, months: NDArray[np.int64]) -> FloatArray: ...  # I at months[i] on path i


# metrics.py
def classify_paths(outcomes: PathOutcomes, required_end_balance: FloatArray | None = None) -> NDArray[np.int8]: ...
class SuccessMetrics:
    @classmethod
    def from_outcomes(cls, outcomes: PathOutcomes, required_end_balance: FloatArray | None = None) -> SuccessMetrics: ...


# monte_carlo.py
def required_end_balance(
    inputs: RandomInputs, outcomes: PathOutcomes, monthly_budget_today: float | FloatArray, end_reserve_months: int
) -> FloatArray: ...  # nominal GBP per path; 0 where the household has not ended
def run_monte_carlo(..., end_reserve_months: int = 0) -> MonteCarloResult: ...


# optimization.py
def path_budget_thresholds(scenario, inputs, end_reserve_months: int = 0) -> ThresholdSearch: ...
# ThresholdSearch gains end_reserve_months: int = 0 (used by the confirming runs)

# reporting.py
LIFESTYLE_RESERVE_COLUMNS: Final = ("end_reserve_months", *LIFESTYLE_COLUMNS)
def write_lifestyle_reserve_results_csv(results, end_reserve_months: int, path: Path) -> Path: ...
```

## 6. Plan of Work

1. Config field, `level_at`, reserve-aware classification and metrics, Config Hash defaults.
2. Reserve-aware budget search (closed form, monotonicity, R = 0 identity).
3. `run` outputs, results guide, README, THESAURUS, decision record.

## 7. Validation

- **T1**: config validation; `level_at` = `level` elementwise; classification at, just below and above the reserve;
  hand-computed Required End Balance.
- **T2**: closed-form B* = S / (d + R) (zero return and inflation, no income, both die in month d) and its
  inflation variant; seeded monotonicity; R = 0 reproduces F-010 exactly.
- **T3**: CLI run with R = 12 (table + CSV) and with the default (no new output).

## 8. Decision Log

- 2026-10-09 — §2 #1–#2 from the user's answers; #3–#9 taken by me within that decision (recorded in
  optimization §3).

## 9. Surprises

- 2026-10-09 — F-019.1: the hand fixture's censored path (alex alive at the horizon) runs out of money in month 25,
  so it is Failed, not Unresolved; the test's assumption "one Unresolved path" was wrong and now asserts the path is
  censored and that both tests give the same Unresolved count.

## 10. Tasks

### F-019.1 Reserve config, per-path index and reserve-aware metrics
- **Status**: Verification
- **Depends on**: —

§2 #1–#3, #6, #7: `budget.end_reserve_months`; `level_at`; `classify_paths` / `SuccessMetrics.from_outcomes` with
`required_end_balance`; `required_end_balance` and `run_monte_carlo(..., end_reserve_months)`; Config Hash leaves
default-valued options out; input-row label. Tests in `tests/unit/test_end_reserve.py`.

**Acceptance criteria**
- [x] `end_reserve_months` defaults to 0, accepts 12 and rejects -1, 1.5 and "12" with a located message — `test_budget_end_reserve_months_validated`
- [x] `level_at(months)` equals `level(m)[i]` for every path i and month m in 0 … 12·n_years — `test_price_index_level_at_matches_level`
- [x] A Successful path whose final balance is just below its Required End Balance is Failed; at or above it, Successful; Failed and Unresolved paths are unchanged; no requirement gives the V1 classes — `test_classify_paths_end_reserve`
- [x] On the hand fixture (zero return, 3 % inflation), the Required End Balance equals R × B × 1.03^(d/12) at each path's Household End month and 0 for a censored path, and the reserve metrics count accordingly — `test_required_end_balance_hand_computed`
- [x] A V1 config's Config Hash is unchanged by the new default; setting `end_reserve_months: 12` changes it — `test_config_sha256_default_options_excluded`

**Notes**
- 2026-10-09 `config.BudgetAssumptions.end_reserve_months` (Integer ≥ 0, default 0); `StochasticPriceIndex.level_at` (vectorised per-path month); `classify_paths` / `SuccessMetrics.from_outcomes` take an optional `required_end_balance` (short of it → Failed; censored untouched); `monte_carlo.required_end_balance` and `run_monte_carlo(..., end_reserve_months)`; `metadata._OPTIONS_HASHED_ONLY_WHEN_SET` keeps V1 hashes (fixture hash pinned); input-row label. Tests `tests/unit/test_end_reserve.py` (5).

### F-019.2 Maximum sustainable budget leaving a reserve
- **Status**: In Progress
- **Depends on**: F-019.1

§2 #4: `path_budget_thresholds(..., end_reserve_months)` and the confirming runs in `maximum_sustainable_budgets`.

**Acceptance criteria**
- [ ] Zero return, zero inflation, no income, both die in month d = 88, balance 100,000: B* lies in (999, 1000] for R = 12 (closed form S / (d + R) = 1,000) and in (1,135.36, 1,136.36] for R = 0; with 3 % inflation, B* matches the closed form S / (Σ_{t<d} I_t + R·I_d) within £1 — `test_reserve_budget_closed_form`
- [ ] On 400 seeded paths, the set of paths meeting a 12-month reserve shrinks (never grows) as the budget rises over a grid, and each path's threshold separates its successes from its failures — `test_reserve_success_monotone_in_budget`
- [ ] With R = 0 the thresholds and budget results equal F-010's exactly; with R = 12 every target's budget is at most the V1 budget — `test_reserve_zero_matches_v1_budgets`

### F-019.3 Reserve outputs in run, guide and docs
- **Status**: To Do
- **Depends on**: F-019.2

§2 #5, #9: summary line, second table and `lifestyle_reserve_results.csv` when R > 0; results guide reserve section and
column guide; README (config key, output file, columns); THESAURUS; decision optimization §3; example config comment.

**Acceptance criteria**
- [ ] With `end_reserve_months: 12`, `run` prints the reserve success rate and a second budget table titled with the 12-month reserve and writes `lifestyle_reserve_results.csv` byte-equal to the library output; the V1 files are byte-identical to a run without the option — `test_cli_run_reserve_table_and_csv`
- [ ] With the default, no reserve line, table or file appears — `test_cli_run_no_reserve_outputs_by_default`
- [ ] The results guide has a reserve subsection (figures and formula with R, B and the reserve rule) when R > 0 and none when 0; `COLUMN_GUIDE` covers `lifestyle_reserve_results.csv` — `test_results_guide_reserve_section`
- [ ] README documents `end_reserve_months` and every `lifestyle_reserve_results.csv` column — `test_readme_documents_every_output_column`
- [ ] THESAURUS defines End-of-Life Reserve and optimization §3 records the rule — `check: grep -n "End-of-Life Reserve" docs/THESAURUS.md docs/decisions/optimization.md`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Config validation — `test_budget_end_reserve_months_validated`
2. Per-path index — `test_price_index_level_at_matches_level`
3. Classification — `test_classify_paths_end_reserve`
4. Required End Balance — `test_required_end_balance_hand_computed`
5. Config Hash stable — `test_config_sha256_default_options_excluded`
6. Closed-form budget — `test_reserve_budget_closed_form`
7. Monotone — `test_reserve_success_monotone_in_budget`
8. R = 0 identity — `test_reserve_zero_matches_v1_budgets`
9. run with reserve — `test_cli_run_reserve_table_and_csv`
10. run by default — `test_cli_run_no_reserve_outputs_by_default`
11. Guide — `test_results_guide_reserve_section`
12. README — `test_readme_documents_every_output_column`
13. THESAURUS + decision — `check: grep -n "End-of-Life Reserve" docs/THESAURUS.md docs/decisions/optimization.md`
