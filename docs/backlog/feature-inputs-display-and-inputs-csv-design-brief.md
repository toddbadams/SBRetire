---
id: F-017
type: feature
parent: v1-1-enhancements
status: done
complexity: 3
created: 2026-10-09
updated: 2026-10-09
---
# F-017 Inputs Display and inputs.csv

## 1. Purpose

Show exactly which inputs produced a run. `sbretire run` prints an **Inputs** block before the results and writes
`inputs.csv` beside the other outputs, so every result file can be traced back to the validated Scenario (SPEC §4,
§15) without opening the YAML. Every Scenario field appears, including the ones left at their defaults, plus a few
derived values a reader needs (the seed actually used, each person's age at the As-Of Date, the horizon's last month).

Requested by the user on 2026-10-09 ("display the inputs"); epic `v1-1-enhancements`.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Granularity | One row per **leaf field of the validated Scenario** — never a hand-picked subset. A test walks the pydantic models and fails if any field has no row, so new config keys (F-019, F-020) cannot be missed | No drift between config and display | user request; this brief |
| 2 | Item key | The config path: `budget.monthly_amount_today`, `people[person_1].date_of_birth`, `income[nhs_pension].survivor_percentage` (list entries by `id`) | Readers can find the key in their YAML | this brief |
| 3 | Values | The validated value, exactly: numbers as Python `repr` of the float (`0.0277`, `1500000.0`) or the integer, dates ISO, booleans `true`/`false`, lists `;`-separated, unset optional fields empty. Data files by **file name only** (the full path is machine-specific and already excluded from the Config Hash) | Exact and reproducible; no personal paths | configuration §7 |
| 4 | Derived rows | Section `derived`: `run.seed` (value used, unit says `config` or `generated`), `people[<id>].age_at_as_of` (completed years), `model.last_month` (the Horizon's last simulated month, YYYY-MM) | What a reader otherwise has to work out | SPEC §5, configuration §8 |
| 5 | CSV | `inputs.csv`: columns `section,item,label,value,unit`; same format as the other CSVs (UTF-8, LF, header) | SPEC §15 conventions | SPEC §15 |
| 6 | Console | An `Inputs (<config>)` block printed **first** by `run`, grouped by section, `label: value unit`; money shown with thousands separators; plain ASCII apart from user-entered names | Seen before the results it explains | user request |
| 7 | Placement | New module `sbretire/inputs_report.py` (rows, CSV writer, console formatter); `run` only (not `validate`/`preview`) | Keeps reporting.py focused on results | this brief |

## 3. Context

- `Scenario` and its sections are frozen pydantic models (`config.py`); optional fields: `model.random_seed`,
  `model.unknown_keys` (default `error`), `people[].survivor_budget_factor`, `income[].end_date`.
- `resolve_seed` gives the `ResolvedSeed` actually used (`randomness.py`); `timeline.month_start` maps month indices
  to dates.
- `_run` in `__main__.py` writes four files and prints the summary and tables.

## 4. Touch-points

**New**: `src/sbretire/inputs_report.py`, `tests/unit/test_inputs_report.py`.

**Modified**: `src/sbretire/__main__.py`, `tests/unit/test_cli_run.py`, `README.md` (Outputs: `inputs.csv`),
`tests/acceptance/test_v1_acceptance.py` (README column guard covers `inputs.csv`).

## 5. Interfaces

```python
# sbretire/inputs_report.py
INPUT_COLUMNS: Final = ("section", "item", "label", "value", "unit")


@dataclass(frozen=True)
class InputRow:
    section: str  # model | portfolio | budget | inflation | mortality | people | income | derived
    item: str  # config path, e.g. "people[person_1].date_of_birth"
    label: str  # plain-English name
    value: str  # exact validated value as text ("" when unset)
    unit: str


def scenario_input_rows(scenario: Scenario, seed: ResolvedSeed) -> list[InputRow]: ...
def write_inputs_csv(rows: Sequence[InputRow], path: Path) -> Path: ...
def format_inputs(config: Path, rows: Sequence[InputRow]) -> str: ...
```

## 6. Plan of Work

1. `inputs_report.py`: rows from the Scenario, the coverage test, exact values, CSV writer, console formatter.
2. `run` prints the block first and writes `inputs.csv`; README.

## 7. Validation

- **T1**: field-coverage test over the pydantic models; exact-value round trip on the example config; CSV format.
- **T2**: CLI run on the fixture prints the block before the summary and writes `inputs.csv` byte-equal to the
  library output.

## 8. Decision Log

- 2026-10-09 — §2 #1–#7 taken without further interview: the user asked for the inputs to be displayed and left the
  format to my recommendation (inputs block + `inputs.csv`).

## 9. Surprises

## 10. Tasks

### F-017.1 Input rows, inputs.csv writer and console block
- **Status**: Done
- **Depends on**: —

`src/sbretire/inputs_report.py` per §2 #1–#7 and §5. Tests in `tests/unit/test_inputs_report.py`.

**Acceptance criteria**
- [x] Every leaf field of the validated Scenario (every section, every person, every income stream) has exactly one row whose `item` is its config path — `test_scenario_input_rows_cover_every_field`
- [x] Values are exact: numeric rows parse back to the validated value, dates are ISO, unset optional fields are empty, data files are file names only — `test_scenario_input_rows_values_exact`
- [x] Derived rows give the seed used and its source, each person's completed age at the As-Of Date and the Horizon's last month — `test_scenario_input_rows_derived`
- [x] `inputs.csv`: header `INPUT_COLUMNS`, UTF-8, LF, one line per row, round-trips — `test_inputs_csv_format`
- [x] The console block lists every row's label and value under its section — `test_format_inputs_lists_every_row`

**Notes**
- 2026-10-09 Added `src/sbretire/inputs_report.py`: `InputRow`, `INPUT_COLUMNS`, `scenario_input_rows` (one row per validated field via the pydantic models; a label table keyed section.field raises KeyError for an unlabelled new field), derived rows (seed used, ages, last month), `write_inputs_csv`, `display_value`, `format_inputs` (date/file/month units left off the console only). Tests `tests/unit/test_inputs_report.py` (5).
- 2026-10-09 /verify PASS:
  - 5 tests pass; the coverage test derives fields independently from the pydantic models
  - own recursive walk: example config 59 leaves / 63 rows, fixture 51 / 55, items unique and set-equal; floats round-trip exactly; ages 66/57 and 68/64; last months 2126-09 and 2086-09; data files by name only
  - inputs.csv LF only, header exact, csv round-trip; no network/tax/randomness/hard-coded values; ruff + mypy clean

### F-017.2 run prints the inputs and writes inputs.csv
- **Status**: Done
- **Depends on**: F-017.1

`_run` prints `format_inputs` before the summary and writes `inputs.csv`; README Outputs documents the file and its
columns; the README column guard includes it.

**Acceptance criteria**
- [x] `sbretire run` prints the Inputs block before the Monte Carlo summary and writes `inputs.csv` byte-equal to `write_inputs_csv` on the same Scenario and seed — `test_cli_run_prints_inputs_and_writes_csv`
- [x] README documents `inputs.csv` and every one of its columns — `test_readme_documents_every_output_column`

**Notes**
- 2026-10-09 `_run` builds the input rows right after resolving the seed, prints `format_inputs` before the (long) computation and writes `inputs.csv` first among the outputs. README: Running the model mentions the block; Outputs table + an `inputs.csv` column table. Tests: `test_cli_run_prints_inputs_and_writes_csv`; `inputs.csv` added to `OUTPUT_FILES` (all-outputs and reproducibility tests) and to the README column guard.
- 2026-10-09 /verify PASS:
  - CLI and acceptance tests: 20 passed
  - fixture run twice: stdout starts with the Inputs block (line 1) before the summary (line 66); inputs.csv LF only, header exact, byte-identical across runs; Wrote line printed
  - reporting/optimization/monte_carlo unchanged since 190012a; README Outputs row + inputs.csv column table; ruff + mypy clean

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Field coverage — `test_scenario_input_rows_cover_every_field`
2. Exact values — `test_scenario_input_rows_values_exact`
3. Derived rows — `test_scenario_input_rows_derived`
4. CSV format — `test_inputs_csv_format`
5. Console block — `test_format_inputs_lists_every_row`
6. run integration — `test_cli_run_prints_inputs_and_writes_csv`
7. README — `test_readme_documents_every_output_column`
