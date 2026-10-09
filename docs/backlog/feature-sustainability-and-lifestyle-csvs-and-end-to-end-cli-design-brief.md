---
id: F-013
type: feature
parent: reporting-release
status: in-progress
complexity: 3
created: 2026-10-09
updated: 2026-10-09
---
# F-013 Sustainability and Lifestyle CSVs and End-to-End CLI

## 1. Purpose

Write the remaining required outputs (SPEC §15): `sustainability_results.csv` (§15.2, §13) and
`lifestyle_results.csv` (§15.3, §14), so one `sbretire run --config … --output-dir …` produces all three CSVs plus
`run_metadata.json` from a single set of random inputs. Makes passable SPEC §17.2 "CSV schemas and units match this
specification" for these two files, and §17.3 #3 / #5 at the CLI level (identical files for a fixed seed; all three
CSVs generated with documented schemas).

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Sustainability rows | One row per target at the configured Budget (SPEC "or per target for a configured budget") | Interview Q1 | Interview Q1 |
| 2 | Sustainability columns | `monthly_budget_today`, `annual_return` (configured, used for the success figures), `target_probability`, `estimated_success_probability` (= Completed-Path Success Rate at the configured Budget and return), `conservative_success_probability` (= Conservative Success Rate), `standard_error` (of the conservative rate, denominator all paths), `unresolved_fraction`, `required_annual_return`, `return_tolerance`, `converged`, `iterations`, `note` — the last five from the Return Search for that target | SPEC §15.2 + SE + units explicit | SPEC §11, §13, §15.2 |
| 3 | Lifestyle columns | `target_probability`, `maximum_monthly_budget_today`, `maximum_annual_budget_today`, `estimated_success_probability` (conservative, from the confirming run), `standard_error`, `unresolved_fraction`, `budget_tolerance`, `converged`, `iterations`, `note` | SPEC §14 / §15.3 + SE | SPEC §14, §15.3 |
| 4 | Conservative rounding in files | Budgets floored to 0.01 GBP; required returns ceiled to 1e-6; probabilities 6 dp; tolerances as configured constants; booleans `true`/`false`; empty cell for None; notes quoted by the csv module when needed | B-011.1 principle: a printed figure always meets its target | B-011.1 |
| 5 | Format | As annual: UTF-8, LF, header, `.` decimals, no separators/symbols | SPEC §15 | SPEC §15 |
| 6 | CLI | `run` writes `annual_results.csv`, `sustainability_results.csv`, `lifestyle_results.csv`, `run_metadata.json` to `--output-dir` and lists them; an output directory that cannot be created/written → exit 1 with an error; nothing partial is reported as success | SPEC §15; fail clearly | SPEC §15 |
| 7 | Placement | Writers in `sbretire/reporting.py` | One output module | SPEC §3 |

## 3. Context

- `BudgetResult` (F-010), `ReturnResult` (F-011), `SuccessMetrics` (F-009); `run` already computes all of them from one
  `RandomInputs` and writes `annual_results.csv` (F-012) and `run_metadata.json` (F-005/F-009).
- Display rounding helpers in `__main__.py` (B-011.1).

## 4. Touch-points

**New**: `tests/unit/test_result_csvs.py`.

**Modified**: `src/sbretire/reporting.py`, `src/sbretire/__main__.py`, `tests/unit/test_cli_run.py`, `README.md`.

## 5. Interfaces

```python
SUSTAINABILITY_COLUMNS: Final = ...  # §2 #2 order
LIFESTYLE_COLUMNS: Final = ...  # §2 #3 order


def write_lifestyle_results_csv(results: Sequence[BudgetResult], path: Path) -> Path: ...
def write_sustainability_results_csv(
    metrics: SuccessMetrics, annual_return: float, returns: Sequence[ReturnResult], path: Path
) -> Path: ...
```

## 6. Plan of Work

1. The two writers with format tests.
2. `run` writes everything; reproducibility and failure handling; README.

## 7. Validation

- **T1**: writer tests on constructed results; ruff; mypy.
- **T2**: CLI run on the fixture twice with a fixed seed → identical CSV bytes.

## 8. Decision Log

- 2026-10-09 — Sustainability rows at the configured Budget only (Interview Q1).

## 9. Surprises

_(filled during implementation)_

## 10. Tasks

### F-013.1 Sustainability and lifestyle CSV writers
- **Status**: Verification
- **Depends on**: —

`SUSTAINABILITY_COLUMNS`, `LIFESTYLE_COLUMNS`, both writers in `src/sbretire/reporting.py` (§2 #2–#5). Tests in
`tests/unit/test_result_csvs.py`.

**Acceptance criteria**
- [x] `lifestyle_results.csv`: header exactly `LIFESTYLE_COLUMNS`; one row per result; budgets floored to 0.01 (≤ B*), annual = floored 12·B*; infeasible rows have empty numbers and the note; booleans `true`/`false`; format per SPEC §15 — `test_lifestyle_results_csv`
- [x] `sustainability_results.csv`: header exactly `SUSTAINABILITY_COLUMNS`; one row per target; success columns from the run metrics; required return ceiled to 1e-6 (≥ r*); no-solution rows empty with note; format per SPEC §15 — `test_sustainability_results_csv`

**Notes**
- 2026-10-09 Added `LIFESTYLE_COLUMNS`, `SUSTAINABILITY_COLUMNS`, `write_lifestyle_results_csv`, `write_sustainability_results_csv` and helpers (`_money_down` floor 0.01, `_return_up` ceil 1e-6, `_share` 6 dp, `_flag` true/false, `_write_rows`) to `src/sbretire/reporting.py`. Tests `tests/unit/test_result_csvs.py` (2).

### F-013.2 End-to-end `run` outputs
- **Status**: To Do
- **Depends on**: F-013.1

`run` writes all four files and lists them; unwritable output → exit 1; README output sections for the two files.

**Acceptance criteria**
- [ ] `run` writes `annual_results.csv`, `sustainability_results.csv`, `lifestyle_results.csv` and `run_metadata.json`, and their contents match the library results for the same seed — `test_cli_run_writes_all_outputs`
- [ ] Two runs of the same config and seed produce byte-identical CSVs (§17.3 #3) — `test_cli_run_csvs_reproducible`
- [ ] An output path that cannot be created exits 1 with an error naming it — `test_cli_run_unwritable_output_dir`
- [ ] README documents every column of both files with units — `check: grep -n "conservative_success_probability" README.md`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Lifestyle CSV — `test_lifestyle_results_csv`
2. Sustainability CSV — `test_sustainability_results_csv`
3. run writes all outputs — `test_cli_run_writes_all_outputs`
4. Reproducible CSVs — `test_cli_run_csvs_reproducible`
5. Unwritable output — `test_cli_run_unwritable_output_dir`
6. README — `check: grep -n "conservative_success_probability" README.md`
