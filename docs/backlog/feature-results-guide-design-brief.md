---
id: F-018
type: feature
parent: v1-1-enhancements
status: planned
complexity: 4
created: 2026-10-09
updated: 2026-10-09
---
# F-018 Results Guide

## 1. Purpose

Every `sbretire run` writes `output/results_guide.md`: a plain-English guide to **this run's** results that sits
next to the CSVs. It covers what each column means, how each figure was calculated (formulas filled in with this
run's numbers), the assumptions and limitations behind them, and the inputs used (from F-017). A reader of the output
folder should not need the README or the code to understand a number (SPEC §11–§15).

Requested by the user on 2026-10-09 (explain the columns, the calculations and the assumptions); epic
`v1-1-enhancements`.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Format | Markdown (`results_guide.md`), UTF-8, LF; readable as plain text, rendered by VS Code/GitHub | User chose my recommendation (Markdown, not HTML) | epic scope |
| 2 | Generated, not static | Built from the run's Scenario, seed, input rows, success metrics, budget and return results; **no timestamp**, so the same run gives a byte-identical guide | Matches the CSVs' reproducibility | SPEC §10.3 |
| 3 | Column descriptions | One table per output file from `COLUMN_GUIDE` (unit, meaning) — a test fails if it differs from any file's column tuple, in either direction or in order | Cannot drift from the code | user request |
| 4 | Sections, in order | `## Your results` · `## How the figures are calculated` · `## Assumptions` · `## Limitations` · `## Columns` · `## Inputs` | Answer first, then why, then reference | this brief |
| 5 | Figures | Shown with the console's rounding: budgets **down** to whole £, required returns **up** to 0.01 %, rates 2 dp with SE 3 dp — the guide never shows a number the console contradicts | B-011.1 | B-011.1 |
| 6 | Calculations | Formulas with this run's values substituted: monthly return rate from the annual return; Required Spending S = B × I × F with the survivor factors; income with linking and survivor shares; the AR(1) inflation step with μ, φ, σ and the initial rate; mortality sampling; path classes; both success rates with their counts and SEs; the budget and return searches with their bounds, tolerances and engine runs | "explain the calculations" with the user's own numbers | user request |
| 7 | Rounding helper | `round_return_up` moves from `__main__` to `reporting.py` (public) so the console and the guide share it | One definition | B-011.1 |
| 8 | Placement | New module `sbretire/results_guide.py`; `run` writes it after the CSVs | reporting.py stays CSV-only | this brief |

## 3. Context

- F-017 gives `scenario_input_rows` / `InputRow`; `__main__._run` already holds the metrics, budget and return
  results and the seed.
- `reporting.py` holds `ANNUAL_COLUMNS`, `SUSTAINABILITY_COLUMNS`, `LIFESTYLE_COLUMNS`; `inputs_report.py` holds
  `INPUT_COLUMNS`. README has hand-written column tables (kept; guarded by the acceptance test).
- Definitions to explain: simulation-conventions §2, §5–§8; optimization §1–§2; configuration §4–§6.

## 4. Touch-points

**New**: `src/sbretire/results_guide.py`, `tests/unit/test_results_guide.py`.

**Modified**: `src/sbretire/reporting.py` (`round_return_up`), `src/sbretire/__main__.py`,
`tests/unit/test_cli_run.py`, `README.md`.

## 5. Interfaces

```python
# sbretire/results_guide.py
COLUMN_GUIDE: Final[dict[str, dict[str, tuple[str, str]]]]  # file name -> column -> (unit, meaning)


@dataclass(frozen=True)
class GuideContext:
    config: Path
    scenario: Scenario
    seed: ResolvedSeed
    input_rows: Sequence[InputRow]
    metrics: SuccessMetrics  # at the configured Budget and return
    budgets: Sequence[BudgetResult]
    returns: Sequence[ReturnResult]


def results_guide_markdown(context: GuideContext) -> str: ...
def write_results_guide(context: GuideContext, path: Path) -> Path: ...


# sbretire/reporting.py
def round_return_up(annual_return: float) -> float: ...  # next 0.01 % up (B-011.1)
```

## 6. Plan of Work

1. `results_guide.py`: `COLUMN_GUIDE`, the six sections, figures and formulas from the context.
2. `run` writes the guide; README.

## 7. Validation

- **T1**: column-guide equality; the guide holds every run figure (with display rounding), every input, and formulas
  with this scenario's values; section order.
- **T2**: CLI run on the fixture writes a guide byte-equal to the library output, identical on a second run.

## 8. Decision Log

- 2026-10-09 — §2 #1–#8 per the user's choice of my recommendation for items 3–5 (generated Markdown guide).

## 9. Surprises

## 10. Tasks

### F-018.1 Results guide content
- **Status**: To Do
- **Depends on**: F-017.2

`src/sbretire/results_guide.py` per §2 #1–#7 and §5; `round_return_up` moved to `reporting.py`. Tests in
`tests/unit/test_results_guide.py`.

**Acceptance criteria**
- [ ] `COLUMN_GUIDE` has exactly the columns of `inputs.csv`, `annual_results.csv`, `sustainability_results.csv` and `lifestyle_results.csv`, in order, each with a non-empty unit and meaning — `test_column_guide_matches_csv_columns`
- [ ] The guide states the run's paths, seed, outcome counts, both success rates with SEs, every budget row (floored to whole £) and every required return (ceiled to 0.01 %) exactly as the console shows them, including infeasible / no-solution notes — `test_results_guide_reports_run_figures`
- [ ] The calculations section substitutes this scenario's values: the monthly return rate computed from `annual_return`, the Budget and survivor factors, the inflation μ, φ, σ and initial rate, and the success-rate counts and SEs — `test_results_guide_calculations_use_scenario_values`
- [ ] Sections appear in the §2 #4 order; every column of every file appears in its file's table; every input row's item and value appears — `test_results_guide_sections_columns_and_inputs`

### F-018.2 run writes results_guide.md
- **Status**: To Do
- **Depends on**: F-018.1

`_run` writes `output/results_guide.md` after the CSVs and prints its path; README Outputs lists it.

**Acceptance criteria**
- [ ] `sbretire run` writes `results_guide.md` byte-equal to `write_results_guide` for the same inputs, and a second run writes an identical file — `test_cli_run_writes_results_guide`
- [ ] README's Outputs section lists `results_guide.md` — `check: grep -n "results_guide.md" README.md`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Column guide equals the code's columns — `test_column_guide_matches_csv_columns`
2. Run figures with display rounding — `test_results_guide_reports_run_figures`
3. Calculations with scenario values — `test_results_guide_calculations_use_scenario_values`
4. Sections, columns and inputs — `test_results_guide_sections_columns_and_inputs`
5. run writes a reproducible guide — `test_cli_run_writes_results_guide`
6. README — `check: grep -n "results_guide.md" README.md`
