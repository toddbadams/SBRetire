---
id: F-012
type: feature
parent: reporting-release
status: in-progress
complexity: 5
created: 2026-10-09
updated: 2026-10-09
---
# F-012 Annual Results CSV

## 1. Purpose

Produce `annual_results.csv` (SPEC §12, §15.1): one row per calendar year with survival probabilities, budget, income
and net-withdrawal medians, portfolio percentiles, **Probability Not Depleted Yet**, the conditional estimated lifetime
success rate, and completed/unresolved counts — for the configured Budget, from the same `RandomInputs` as the rest of
`sbretire run`. Aggregation streams year by year through the engine's observer so memory stays O(n_paths) (SPEC §10.4).

Resolves SPEC §18 "Definition of annual portfolio percentiles and funded probabilities" (simulation-conventions §8).
Makes passable SPEC §17.2 "CSV schemas and units match this specification" for the annual file.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Rows | One per calendar year from the As-Of year to the year of the last month in which anyone on any Path is alive (at most the Horizon); `months` = simulated months in the row (first/last may be partial). "Year end" = the row's last simulated month | SPEC §12 "one row per calendar year"; partial years explicit | SPEC §12; epic risk |
| 2 | Survival | `probability_both_alive`, `probability_person_1_alive`, `probability_person_2_alive`: share of **all** paths with that person (both) alive at year end; person 1/2 = `people[0]`/`people[1]` | Unconditional, simple | simulation-conventions §8 |
| 3 | Budget | `monthly_budget_today` = configured Budget; `monthly_budget_nominal_median` = median over all paths of Budget × I at year end | SPEC "or another explicitly identified statistic" | simulation-conventions §8 |
| 4 | Annual flows | Per path, sums over the months of the year in which the path was running (not depleted, someone alive): required spending (`annual_budget_nominal`), income due (`annual_income`), net withdrawal = spending − income. Medians over paths running in at least one month of the year; nominal GBP | Household cash flows actually faced | simulation-conventions §8 |
| 5 | Portfolio percentiles | p05/p25/median/p75/p95 of the year-end balance across paths **in scope** (someone alive at year end), depleted paths at 0; paths whose household has ended are excluded; nominal GBP; linear interpolation (`numpy.percentile` default) | SPEC §12 recommendation | SPEC §12 |
| 6 | Not depleted yet | `probability_not_depleted_yet` = share of all paths with no Depletion by year end (paths that ended without depletion count as not depleted) | SPEC §12 definition | SPEC §12 |
| 7 | Lifetime success | `estimated_lifetime_success_rate` = among paths not depleted by year end, the share whose lifetime outcome is Successful (Unresolved count as non-success) — "given you have got this far solvent" | Interview Q1 | Interview Q1; simulation-conventions §8 |
| 8 | Counts | `completed_paths` = cumulative paths resolved by year end (depleted, or household ended); `unresolved_paths` = N − completed (still running); the last row's unresolved = Censored paths that never depleted | Interview Q1 | Interview Q1 |
| 9 | No `probability_funded` | Omitted (SPEC §12 bans the ambiguous name) | SPEC §12 | SPEC §12 |
| 10 | CSV format | UTF-8, LF, header row, columns in the order of §5, `.` decimals, no separators/symbols; probabilities as decimals 0–1 (6 dp); money 2 dp; counts integers; empty field when a statistic has no population | SPEC §15 | SPEC §15 |
| 11 | Streaming | An observer + recording cash-flow wrapper accumulate per-path sums for the current year and emit the row at each year end; after the engine stops early, remaining years are finished from the final state | SPEC §10.4 | SPEC §10.4 |
| 12 | Placement | `sbretire/reporting.py` (collector, rows, CSV writer); `run` writes `annual_results.csv` | SPEC §3 output module | SPEC §3 |

## 3. Context

- `simulate_paths(..., observer)` calls `observer(month, balance, alive, active)` after each month's cash flows while
  any path is active; it stops early when none is (F-002). `ScenarioCashFlows` gives income/spending (F-003/F-004).
- `run_monte_carlo`, `RandomInputs`, `classify_paths` (F-009); `timeline.month_start`.
- Preview (F-015) already aggregates one path by calendar year (`_RecordingCashFlows`, `_by_calendar_year`).

## 4. Touch-points

**New**: `src/sbretire/reporting.py`, `tests/unit/test_reporting_annual.py`, `tests/unit/test_annual_csv.py`.

**Modified**: `src/sbretire/monte_carlo.py` (optional observer pass-through), `src/sbretire/__main__.py`,
`tests/unit/test_cli_run.py`, `README.md`, `docs/decisions/simulation-conventions.md` (§8, with this brief).

## 5. Interfaces

```python
# sbretire/reporting.py
ANNUAL_COLUMNS: Final = (
    "year", "months",
    "probability_both_alive", "probability_person_1_alive", "probability_person_2_alive",
    "monthly_budget_today", "monthly_budget_nominal_median", "annual_budget_nominal_median",
    "annual_income_median", "annual_net_withdrawal_median",
    "portfolio_p05", "portfolio_p25", "portfolio_median", "portfolio_p75", "portfolio_p95",
    "probability_not_depleted_yet", "estimated_lifetime_success_rate", "completed_paths", "unresolved_paths",
)  # fmt: skip


@dataclass(frozen=True)
class AnnualRow:  # one field per column; float | None where a population can be empty
    ...


def annual_results(scenario: Scenario, inputs: RandomInputs) -> list[AnnualRow]: ...
def write_annual_results_csv(rows: Sequence[AnnualRow], path: Path) -> Path: ...
```

## 6. Plan of Work

1. Streaming collector and `annual_results` with hand-checked fixtures.
2. CSV writer, `run` integration, README, decision.

## 7. Validation

- **T1**: unit tests on deterministic fixtures (step mortality, zero inflation) with hand-computed rows; ruff; mypy.
- **T2**: seeded run — independent recomputation of selected rows from full per-month arrays on a small run.
- **T3**: CSV schema test.

## 8. Decision Log

- 2026-10-09 — Annual definitions per §2 #1–#8 (Interview Q1 for #7–#8; simulation-conventions §8).

## 9. Surprises

- 2026-10-09 — F-012.1: the engine stops once no path is running (here after month 25), so year rows whose last month was never observed must be closed from the run's final balances — handled by `_AnnualCollector.finish`.

## 10. Tasks

### F-012.1 Streaming annual aggregation
- **Status**: Verification
- **Depends on**: —

`AnnualRow`, the collector (observer + recording cash flows), `annual_results` in `src/sbretire/reporting.py`
(§2 #1–#9, #11); `run_monte_carlo` gains an optional `observer`. Tests in `tests/unit/test_reporting_annual.py`.

**Acceptance criteria**
- [x] Deterministic 2-path fixture (step mortality, zero inflation, zero return): every row's survival probabilities, annual spending/income/net-withdrawal medians, portfolio percentiles, not-depleted, lifetime success and counts equal hand-computed values, including a partial first year and a path that depletes — `test_annual_results_hand_computed_fixture`
- [x] On a seeded 300-path run, every row equals an independent recomputation from full month × path arrays (recorded separately in the test) — `test_annual_results_match_full_history_recomputation`
- [x] Rows run from the As-Of year to the last year anyone is alive (≤ horizon), `months` sums to the simulated months, and years after the engine's early stop are still produced — `test_annual_results_row_span`
- [x] The collector holds only per-path (n_paths,) state — no month × path arrays — `check: grep -nE "horizon_months\s*,\s*n_paths|\(n_years, n_paths\)" src/sbretire/reporting.py returns nothing`

**Notes**
- 2026-10-09 Added `src/sbretire/reporting.py`: `AnnualRow`, `_RecordingCashFlows`, `_AnnualCollector` (engine observer; per-path current-year sums only; closes each year at its last month; `finish` closes years after the engine's early stop from final balances), `annual_results`. Calls `simulate_paths` directly with the recording wrapper on the same inputs instead of adding an observer to `run_monte_carlo` (brief §4 listed that change; not needed). Tests `tests/unit/test_reporting_annual.py` (3: hand fixture incl. depletion and early stop; 300-path recomputation from full month × path history kept only in the test; row span).

### F-012.2 annual_results.csv and run integration
- **Status**: To Do
- **Depends on**: F-012.1

`write_annual_results_csv`; `sbretire run` writes `output/annual_results.csv`; README output section (columns, units,
definitions); decision §8 recorded with the brief.

**Acceptance criteria**
- [ ] CSV: header exactly `ANNUAL_COLUMNS`; UTF-8, LF; `.` decimals, no thousands separators or currency symbols; probabilities in [0, 1]; counts integers; empty fields only where a population is empty; values round-trip to the rows — `test_annual_results_csv_format`
- [ ] `sbretire run` writes `annual_results.csv` beside `run_metadata.json` and says so — `test_cli_run_writes_annual_results`
- [ ] README documents every annual column with its unit and definition — `check: grep -n "probability_not_depleted_yet" README.md`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Hand-computed fixture — `test_annual_results_hand_computed_fixture`
2. Matches full-history recomputation — `test_annual_results_match_full_history_recomputation`
3. Row span — `test_annual_results_row_span`
4. O(n_paths) memory — `check: grep for month × path arrays in reporting.py`
5. CSV format — `test_annual_results_csv_format`
6. run writes the file — `test_cli_run_writes_annual_results`
7. README — `check: grep -n "probability_not_depleted_yet" README.md`
