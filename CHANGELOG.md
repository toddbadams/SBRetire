# Changelog

All notable changes to SBRetire. Dates are ISO (YYYY-MM-DD).

## [Unreleased]

V1.1 enhancements (epic `v1-1-enhancements`). Both new model options are off by default, so V1 results and config
hashes are unchanged unless you switch them on.

### Added

- **VS Code test setup:** shared workspace settings, debug configurations and recommended extensions (F-016).
- **Inputs display:** `run` first prints every setting it will use, and writes them to `inputs.csv` (F-017).
- **Results guide:** every run writes `results_guide.md`. It covers your results, how each figure was calculated
  (with your numbers), the assumptions and limitations, every column of every file, and the inputs (F-018).
- **End-of-life reserve:** `budget.end_reserve_months` (e.g. `12`) adds a success rate and a second maximum-budget
  table for leaving R × the monthly budget, inflated, in savings at the second death. Also adds
  `lifestyle_reserve_results.csv` (F-019).
- **Spend at least income:** `budget.spend_at_least_income: true` makes each month's spending at least that month's
  income, so surplus income is spent rather than saved (F-020).
- **Named runs and results.json:** every run writes `results.json` (validated by `schemas/results.schema.json`).
  `--name` keeps each run in `output/runs/<name>/` (refused if it exists, unless `--overwrite`), and
  `output/runs/index.json` plus `runs.js` collect every named run for an offline web page (F-021).

## [1.0.0] - 2026-10-09

First complete release of the Retirement Sustainability Model (V1). It meets every SPEC §17 test and acceptance
criterion; see `docs/acceptance.md` for the evidence.

### Added

- **Scenario configuration** (`config/*.yaml`): validated with actionable, located errors, strict types, an
  unknown-key policy, data paths relative to the config file, and `sbretire validate` (F-001).
- **Engine:** monthly, vectorised over paths. Each month applies the return, then income, then spending. Money
  running out (depletion) records the shortfall and never lets a negative balance compound. Paths with someone
  alive at the horizon are tracked as censored (F-002).
- **Household cash flows:** income streams with start and end dates, CPI linking, survivor percentages and
  household-owned income; spending with the survivor's own budget factor (F-003, F-004).
- **Reproducibility:** separate seeded random streams for mortality and inflation, a canonical config hash, and
  `run_metadata.json` with versions and data-file hashes (F-005).
- **Inflation:** an AR(1) lognormal process calibrated to ONS CPI D7G7 for 1989–2025, compounding monthly
  (F-006).
- **Mortality:**
  - ONS 2024-based UK cohort rates (principal projection) built from the official workbook, with an age-100 tail
    (F-007).
  - Monthly death sampling by inverse CDF (F-008).
- **Monte Carlo** via `sbretire run`: Successful, Failed and Unresolved paths; conservative and completed-path
  success rates with Monte Carlo standard errors (F-009).
- **Searches,** both using common random numbers:
  - The maximum sustainable budget per confidence level, by per-path threshold bisection with a £1 tolerance
    (F-010).
  - The required fixed return per confidence level, with monotonicity verified (F-011).
- **Output files:**
  - `annual_results.csv`, aggregated by calendar year as the engine runs (F-012).
  - `sustainability_results.csv` and `lifestyle_results.csv`, with all outputs written by one run (F-013).
- **Preview:** `sbretire preview`, a deterministic year-by-year illustration with chosen death ages (F-015).
- **Release checks:** automated V1 acceptance guards (no tax logic, no network access, no global randomness,
  every SPEC §18 decision recorded, data provenance), the SPEC §17 acceptance map, and a full README (F-014).

### Fixed

- Displayed and written budgets now round down and required returns round up, so every reported figure meets its
  target (B-011.1).
