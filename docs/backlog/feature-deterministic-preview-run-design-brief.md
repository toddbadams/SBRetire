---
id: F-015
type: feature
parent: reporting-release
status: in-progress
complexity: 4
created: 2026-10-09
updated: 2026-10-09
---
# F-015 Deterministic Preview Run

## 1. Purpose

Give a year-by-year view of one household future as soon as income and spending exist (F-003, F-004), long before
the Monte Carlo outputs (F-009, F-012, F-013). `sbretire preview` runs **one Path** with Death Months derived from
death ages the user chooses, constant inflation at `inflation.annual_mean`, and the configured fixed return, then
prints a calendar-year table and writes `preview.csv`.

It is a **deterministic illustration**, not a sustainability result (SPEC §14: "avoid presenting illustrative
example numbers as calculated results"); every output says so. It also sanity-checks F-002–F-004 on real inputs and
prepares the calendar-year aggregation that F-012 will generalise (SPEC §12).

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Death input | Required `--death-ages A,B` in `people` order; person p is dead from the start of the month of their A-th birthday; an age reaching beyond the horizon = alive at the horizon; an age ≤ current age is rejected | Explicit every run (no hidden default that reads as a forecast); matches the Death Month convention | Interview Q1; simulation-conventions §2 |
| 2 | Inflation in the preview | `AnnualStepPriceIndex`: I_t = (1 + `inflation.annual_mean`)^floor(t / 12) — one annual rate held for twelve months, years counted from the As-Of month | SPEC §6 "one annual rate … applied to each of the twelve monthly steps"; provisional until F-006 | Interview Q2; simulation-conventions §3 (provisional) |
| 3 | Rows | One per calendar year (first/last partial), until the path stops (Depletion, Household End or horizon) | SPEC §12 rows are calendar years; matches the future annual CSV | Interview Q3; SPEC §12 |
| 4 | Columns | `year, months, age_person_1, age_person_2, income, spending, investment_return, net_withdrawal, balance_end, balance_end_today, price_index` — money nominal GBP except `balance_end_today` (= `balance_end / I` at the year's last simulated month); ages at 31 Dec, blank once dead | Today's-GBP balance beside nominal so inflation can't flatter the numbers | Interview Q3 |
| 5 | Summary | Depletion month index and date (or `never`), Shortfall, Household End date (or `alive at horizon`), final balance nominal and today's GBP | The questions a user asks first | Interview Q3 |
| 6 | Capture | A recording wrapper around `ScenarioCashFlows` plus the engine `observer`; investment return per month = opening balance × r_m (what the engine applies) | No engine change | Brief author, confirmed |
| 7 | Labelling | Banner `DETERMINISTIC ILLUSTRATION — not a sustainability estimate` printed above the table and summary on stdout; `preview.csv` stays pure data (header row first, SPEC §15) and its name marks it as a preview | SPEC §14, §15 | SPEC §14; reporting-release epic |
| 8 | CLI | `sbretire preview --config PATH --death-ages A,B [--output-dir DIR]` (default `output`), overwrites `preview.csv`; exit 0 ok, 1 unreadable config, 2 invalid config or arguments | Consistent with `validate` / `run` | F-001 CLI |
| 9 | CSV format | UTF-8, header row, `.` decimals, no thousands separators or currency symbols, 2-dp money, 6-dp index | SPEC §15 conventions | SPEC §15 |
| 10 | Placement | `AnnualStepPriceIndex` in `sbretire/inflation.py`; `death_months_from_ages`, `run_preview`, `PreviewResult`, `format_preview_table`, `write_preview_csv` in `sbretire/preview.py`; subcommand in `__main__.py` | Module per responsibility | SPEC §3 |

## 3. Context

- Available: `ScenarioCashFlows` (F-004), `PriceIndex` / `FlatPriceIndex` (F-003), `simulate_paths` with observer
  (F-002), `month_index` (F-003), `load_scenario` + CLI (F-001).
- The engine observer reports `(month, balance, alive, active)` after each month; income/spending are not passed to
  it, hence the recording wrapper (decision 6).

## 4. Touch-points

**New**

| File | Purpose |
|---|---|
| `src/sbretire/preview.py` | preview run, aggregation, formatting, CSV |
| `tests/unit/test_preview.py` | death-age mapping, aggregation, summary |
| `tests/unit/test_cli_preview.py` | CLI behaviour, CSV format |

**Modified**

| File | Change |
|---|---|
| `src/sbretire/inflation.py` | `AnnualStepPriceIndex` |
| `tests/unit/test_inflation.py` | annual-step tests |
| `src/sbretire/__main__.py` | `preview` subcommand |
| `README.md`, `CLAUDE.md` | preview usage |

**Deleted:** none.

## 5. Interfaces

```python
# sbretire.inflation
class AnnualStepPriceIndex:
    def __init__(self, n_paths: int, annual_rate: float) -> None: ...  # annual_rate > -1
    def level(self, month: int) -> FloatArray: ...  # (1 + annual_rate) ** (month // 12)


# sbretire.preview
def death_months_from_ages(scenario: Scenario, ages: tuple[int, int]) -> IntArray: ...  # (2, 1); ValueError


@dataclass(frozen=True)
class PreviewYear:
    year: int
    months: int
    age_person_1: int | None
    age_person_2: int | None
    income: float
    spending: float
    investment_return: float
    net_withdrawal: float
    balance_end: float
    balance_end_today: float
    price_index: float


@dataclass(frozen=True)
class PreviewResult:
    rows: tuple[PreviewYear, ...]
    depletion_month: int | None
    depletion_date: date | None
    shortfall: float
    household_end_date: date | None  # None = someone alive at the horizon
    final_balance: float
    final_balance_today: float


def run_preview(scenario: Scenario, death_ages: tuple[int, int]) -> PreviewResult: ...
def format_preview_table(result: PreviewResult, scenario: Scenario) -> str: ...
def write_preview_csv(result: PreviewResult, path: Path) -> None: ...
```

CSV header: `year,months,age_person_1,age_person_2,income,spending,investment_return,net_withdrawal,balance_end,balance_end_today,price_index`.

## 6. Plan of Work

1. `AnnualStepPriceIndex`; `death_months_from_ages`.
2. `run_preview`: recording wrapper + observer → monthly records → calendar-year rows and summary.
3. Formatting, CSV writer, `preview` subcommand, docs.

## 7. Validation

- **T1** — unit tests per AC; ruff; mypy --strict.
- **T2** — `test_cli_preview.py` runs the real subcommand on the fixture and parses the CSV.
- **T3** — hand numbers: fixture with `annual_mean` 0 and `annual_return` 0 reproduces F-004's known path
  (2026 row: 3 months, income 1 500, spending 9 000, balance 492 500; Depletion month 289 = 2050-11, shortfall 2 000).
  Dates are pinned by the fixture's As-Of date; no randomness.

## 8. Decision Log

- 2026-10-09 — Interview Q1–Q3 settled decisions 1–5; 6–10 proposed by brief author and confirmed. Decision 2 recorded as simulation-conventions §3 (provisional, F-006 to confirm or replace).

## 9. Surprises

- 2026-10-09 — In a Depletion month the `spending` column shows the full Required Spending, not the amount actually paid; the unpaid part is the summary's Shortfall. Kept deliberately so rows show what the household needed; documented in the README preview section.
- 2026-10-09 — Needed `timeline.month_start` (month index → date) for dates in the summary and calendar grouping; added with round-trip tests rather than an ad-hoc helper in preview.py.

## 10. Tasks

Task format and statuses: `docs/project-sdlc.md` §2. Definition of done: `docs/project-sdlc.md` §4.

### F-015.1 Annual-step index and death months from ages
- **Status**: Verification
- **Depends on**: —

`AnnualStepPriceIndex` in `src/sbretire/inflation.py` (brief §2 #2) and `death_months_from_ages` in
`src/sbretire/preview.py` (§2 #1). Tests in `tests/unit/test_inflation.py` and `tests/unit/test_preview.py`.

**Acceptance criteria**
- [x] The index is 1 for months 0–11, (1+π) for 12–23, (1+π)^k for months 12k…12k+11 — `test_annual_step_index_steps_on_anniversaries`
- [x] A zero rate gives a constant index of 1 — `test_annual_step_index_zero_rate_is_flat`
- [x] A death age maps to the month index of that birthday's month (fixture: alex b. 1958-03 at age 90 → 2048-03 = month 257) — `test_death_months_from_ages_uses_birthday_month`
- [x] Ages at or below a person's current age are rejected; ages beyond the horizon give a Death Month ≥ the horizon — `test_death_months_from_ages_validates_range`

**Notes**
- 2026-10-09: `src/sbretire/inflation.py` — `AnnualStepPriceIndex` (rejects rate ≤ −1). `src/sbretire/preview.py` — `death_months_from_ages` (birthday month via `month_index`; rejects ages ≤ 0 or Death Month ≤ 0 with "must be greater than their current age"). Tests: 2 added to `tests/unit/test_inflation.py`, 2 in `tests/unit/test_preview.py`.

### F-015.2 Preview run and calendar-year aggregation
- **Status**: Verification
- **Depends on**: F-015.1

`run_preview`, `PreviewYear`, `PreviewResult` in `src/sbretire/preview.py` (brief §2 #3–#6, §5). Tests in
`tests/unit/test_preview.py` using the fixture with `annual_mean` and `annual_return` overridden.

**Acceptance criteria**
- [x] Calendar-year rows aggregate months correctly: with zero inflation and return the 2026 row has 3 months, income 1 500, spending 9 000, net withdrawal 7 500, balance 492 500 — `test_run_preview_aggregates_calendar_years`
- [x] The summary reports Depletion month 289 on 2050-11-01 with shortfall 2 000, and rows stop at 2050 — `test_run_preview_reports_depletion`
- [x] With 2% inflation, `balance_end_today` = `balance_end` / `price_index` and the index steps on As-Of anniversaries — `test_run_preview_deflates_with_price_index`
- [x] `investment_return` sums opening balance × r_m: the first full year with no cash flows matches B(1+r_a)^… closed form — `test_run_preview_investment_return_matches_closed_form`
- [x] Household End before the horizon is reported as a date; rows stop there; ages are blank after a death — `test_run_preview_household_end_and_ages`

**Notes**
- 2026-10-09: `src/sbretire/preview.py` — `run_preview` wraps `ScenarioCashFlows` in `_RecordingCashFlows` and records each simulated month via the engine observer (income, spending, opening × r_m, closing balance, alive, index), then groups by calendar year (`_by_calendar_year`, `_year_row`). `src/sbretire/timeline.py` gains `month_start` (inverse of `month_index`, with round-trip tests). Tests: 5 in `tests/unit/test_preview.py`, 2 in `tests/unit/test_timeline.py`.

### F-015.3 Preview command, table and CSV
- **Status**: In Progress
- **Depends on**: F-015.2

`format_preview_table`, `write_preview_csv` in `src/sbretire/preview.py`; `preview` subcommand in
`src/sbretire/__main__.py` (brief §2 #7–#9); README and CLAUDE.md. Tests in `tests/unit/test_cli_preview.py`.

**Acceptance criteria**
- [ ] `sbretire preview` prints the illustration banner, the table and the summary, writes `preview.csv`, exits 0 — `test_cli_preview_prints_table_and_writes_csv`
- [ ] The CSV has the exact header, one row per year, `.` decimals and no thousands separators or currency symbols — `test_preview_csv_format`
- [ ] Wrong `--death-ages` (count, non-integer, at or below current age) exits 2 with a message; an invalid config exits 2; a missing config exits 1 — `test_cli_preview_rejects_bad_arguments`
- [ ] README documents the preview and its illustration-only status — `check: grep -n "sbretire preview" README.md`

## 11. Open Questions

- F-006 decides the stochastic year boundary; if it differs from As-Of anniversaries, `AnnualStepPriceIndex` and the preview follow it (simulation-conventions §3 is provisional).
- Later (after F-006/F-008) the preview could add `--median-path`; out of scope here.

## 12. Acceptance Criteria

1. Annual-step index — `test_annual_step_index_steps_on_anniversaries`
2. Zero-rate flat — `test_annual_step_index_zero_rate_is_flat`
3. Death age → birthday month — `test_death_months_from_ages_uses_birthday_month`
4. Death-age range validation — `test_death_months_from_ages_validates_range`
5. Calendar-year aggregation — `test_run_preview_aggregates_calendar_years`
6. Depletion summary — `test_run_preview_reports_depletion`
7. Deflation by index — `test_run_preview_deflates_with_price_index`
8. Investment return closed form — `test_run_preview_investment_return_matches_closed_form`
9. Household End and ages — `test_run_preview_household_end_and_ages`
10. CLI table + CSV — `test_cli_preview_prints_table_and_writes_csv`
11. CSV format — `test_preview_csv_format`
12. Bad arguments — `test_cli_preview_rejects_bad_arguments`
13. README — `check: grep -n "sbretire preview" README.md`
