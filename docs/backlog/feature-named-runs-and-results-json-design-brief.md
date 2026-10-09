---
id: F-021
type: feature
parent: results-viewer
status: in-progress
complexity: 5
created: 2026-10-09
updated: 2026-10-09
---
# F-021 Named Runs and results.json

## 1. Purpose

Prepare everything an HTML results page needs before it is designed in Claude Design. Every `sbretire run` writes
one `results.json` holding all its results. `--name` keeps each run in its own folder, and a browser-loadable
`runs.js` collects every named run, so a static page can list runs, show one, or compare two. The page works
offline from disk (SPEC §11–§15 results; the CSVs stay the specified outputs). A committed sample from the example
config and a design prompt in `docs/design/` are the hand-off to Claude Design.

Requested by the user on 2026-10-09; epic `results-viewer`.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | One JSON per run | `results.json` beside the CSVs on every run (named or not), built from the same result objects as the CSVs and the guide | One source of truth; cannot disagree with the CSVs | user request |
| 2 | Schema | `schema_version: "1.0"`; sections `run`, `people`, `inputs`, `summary`, `reserve_summary`, `budgets`, `reserve_budgets`, `returns`, `annual`, `columns` (§5). Raw numbers, `null` for missing; budgets floored to 0.01 and required returns ceiled to 1e-6, exactly as the CSVs (B-011.1). A JSON Schema (draft 2020-12) in `schemas/results.schema.json`; tests validate every written file against it | A contract the page and the model share | user request; B-011.1 |
| 3 | Run name | `--name`: 1–64 characters `[A-Za-z0-9_-]`, starting with a letter or digit; anything else → exit 2 with the rule | Always a safe folder name on Windows | this brief |
| 4 | Where | Named run → `<output-dir>/runs/<name>/` (all files). Unnamed → `<output-dir>/` as before, plus `results.json`, and no index update | User: unnamed runs unchanged | user decision |
| 5 | Existing name | Exit 2 before any computation ("run '<name>' already exists … use --overwrite"); with `--overwrite`, the run's own output files (only the known file names) are removed, then rewritten | User: refuse unless --overwrite | user decision |
| 6 | Page data | After a named run, rebuild `<output-dir>/runs/index.json` and `<output-dir>/runs/runs.js` from every `runs/*/results.json` on disk (so deleted runs disappear). `runs.js` = `window.SBRETIRE_RUNS = {schema_version, index, runs: {name: results}};` | User: embedded data, works from `file://` | user decision |
| 7 | Index entry | name, created_at, config file name, paths, monthly budget, return, conservative success rate and SE, the first target's maximum budget; newest first, then by name | What a run picker shows | this brief |
| 8 | Privacy | `config_file` is the file name only; `results.json` still holds names, dates of birth and amounts, so `output/` stays git-ignored and only the example sample is committed | Personal data | epic risk |
| 9 | Hand-off | `scripts/build_design_sample.py` runs two named runs of `config/model.example.yaml` (base, and 4 % return + 12-month reserve) into `docs/design/sample/`; `docs/design/claude-design-prompt.md` describes the page | User: prepare the hand-off | user decision |
| 10 | Dev dependency | `jsonschema` (+ `types-jsonschema`) as dev-only dependencies for the schema tests; never imported by `src/` | Standard validator; runs stay offline | CLAUDE.md constraint 2 |

## 3. Context

- `__main__._run` already builds every result object (inputs, metrics, budget and return results, reserve results,
  annual rows) and a `GuideContext`; outputs are written in one `try` block.
- `reporting._money_down` / `_return_up` implement the CSV rounding as text; JSON needs the numeric versions.
- `results_guide.COLUMN_GUIDE` holds every column's unit and meaning.

## 4. Touch-points

**New**: `src/sbretire/results_json.py`, `schemas/results.schema.json`, `tests/unit/test_results_json.py`,
`tests/unit/test_named_runs.py`, `scripts/build_design_sample.py`, `docs/design/claude-design-prompt.md`,
`docs/design/sample/` (generated).

**Modified**: `src/sbretire/__main__.py`, `src/sbretire/reporting.py` (numeric rounding helpers), `pyproject.toml`
(dev dependencies, known-local-folder), `uv.lock`, `README.md`, `CHANGELOG.md`.

## 5. Interfaces

```python
# sbretire/results_json.py
SCHEMA_VERSION: Final = "1.0"
RUN_NAME_RULE: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


def check_run_name(name: str) -> str | None: ...  # None when valid, else the problem
def build_results(
    context: GuideContext,
    annual: Sequence[AnnualRow],
    *,
    name: str | None,
    config_sha256: str,
    created_at: str,
) -> dict[str, Any]: ...
def write_results_json(results: dict[str, Any], path: Path) -> Path: ...
def refresh_runs_index(runs_dir: Path) -> tuple[Path, Path]: ...  # index.json, runs.js
```

`results.json` (abridged):

```json
{
  "schema_version": "1.0",
  "run": {"name": "base", "created_at": "2026-10-09T17:00:00+00:00", "sbretire_version": "1.0.0",
          "config_file": "model.example.yaml", "config_sha256": "…", "seed": {"value": 42, "source": "config"},
          "as_of_date": "2026-10-01", "horizon_years": 100, "last_month": "2126-09", "paths": 100000,
          "monthly_budget_today": 6667.0, "annual_return": 0.05,
          "options": {"end_reserve_months": 0, "spend_at_least_income": false}},
  "people": [{"id": "person_1", "name": "Person 1"}, {"id": "person_2", "name": "Person 2"}],
  "inputs": [{"section": "model", "item": "model.currency", "label": "Currency", "value": "GBP", "unit": ""}],
  "summary": {"n_paths": 100000, "n_successful": 0, "n_failed": 0, "n_unresolved": 0, "n_completed": 0,
              "conservative_success_rate": 0.0, "conservative_standard_error": 0.0,
              "completed_success_rate": null, "completed_standard_error": null, "unresolved_share": 0.0},
  "reserve_summary": null,
  "budgets": [{"target_probability": 0.9, "maximum_monthly_budget_today": 0.0, "...": "lifestyle columns"}],
  "reserve_budgets": [],
  "returns": [{"target_probability": 0.9, "required_annual_return": 0.0, "...": "sustainability return columns"}],
  "annual": [{"year": 2026, "months": 3, "...": "annual_results columns"}],
  "columns": {"annual_results.csv": {"year": {"unit": "calendar year", "meaning": "…"}}}
}
```

## 6. Plan of Work

1. `results.json` builder, JSON Schema, schema-validation tests; write it on every run.
2. `--name` / `--overwrite`, run folders, `index.json` and `runs.js` rebuilt from disk.
3. Design hand-off: sample generator, committed sample, design prompt; README and CHANGELOG.

## 7. Validation

- **T1**: builder output validates against the schema; values equal the CSVs and guide figures; rounding as CSVs;
  name rule; index ordering and content.
- **T2**: CLI named runs (new, duplicate refused before computing, `--overwrite`, unnamed unchanged), `runs.js`
  parses back to the same data.
- **T3**: the committed sample validates against the schema and contains no personal config data.

## 8. Decision Log

- 2026-10-09 — #4–#6, #9 from the user's answers (embedded runs.js; refuse unless --overwrite; unnamed unchanged;
  prepare the hand-off); the rest by me.

## 9. Surprises

- 2026-10-09 — /verify of F-021.1 found `returns[]` reusing three sustainability CSV column names for different
  figures (success at the required return); renamed `*_at_required_return` so equal names always mean equal things.
- 2026-10-09 — The user moved the Claude Design hand-off document to F-022 (with a common CSS theme requirement);
  F-021.3 keeps the sample and docs.

- 2026-10-09 — F-021.1: `run.seed.value` is a decimal **string**, not a number: a generated seed is 128-bit and
  JavaScript cannot hold it exactly. The test was changed to expect `"21"` before the code went green.

## 10. Tasks

### F-021.1 results.json and its schema
- **Status**: Verification
- **Depends on**: —

`src/sbretire/results_json.py` (`build_results`, `write_results_json`, `SCHEMA_VERSION`), numeric rounding helpers
in `reporting.py`, `schemas/results.schema.json`, `jsonschema` dev dependency; `run` writes `results.json`.

**Acceptance criteria**
- [x] On a seeded 300-path run (with and without a 12-month reserve) the built results validate against `schemas/results.schema.json`, and the schema rejects a document missing a section or with a wrong type — `test_results_json_validates_against_schema`
- [x] Summary, budgets, reserve budgets, returns and annual values equal the run's result objects, with budgets floored to 0.01 and returns ceiled to 1e-6 exactly as the CSVs; a `returns` key that shares a name with a `sustainability_results.csv` column has the same meaning (success at the required return is `*_at_required_return`); `columns` equals `COLUMN_GUIDE`; `inputs` equals the input rows — `test_results_json_matches_run_objects`
- [x] `sbretire run` (unnamed) writes `results.json` beside the CSVs; it validates against the schema, is strict JSON with no NaN, and is identical across two runs apart from `run.created_at` — `test_cli_run_writes_results_json`

**Notes**
- 2026-10-09 `src/sbretire/results_json.py` (`build_results` from GuideContext + annual rows, `write_results_json` strict JSON, UTF-8, LF); `reporting.money_down`/`return_up` numeric rounding shared with the CSV text helpers; `schemas/results.schema.json` (draft 2020-12, additionalProperties false everywhere, generated once then maintained by hand); `run` writes `results.json` using run_metadata's hash and timestamp. Tests `tests/unit/test_results_json.py` (2) and `test_cli_run_writes_results_json`; `results.json` added to OUTPUT_FILES.
- 2026-10-09 /verify FAIL (snapshot 28fc3e6):
  - results.json `returns[]` reuses the CSV names estimated_success_probability / standard_error / unresolved_fraction for the success at the solved required return, while sustainability_results.csv (and the JSON's own `columns` guide) use them for the configured-return figures: e.g. JSON 0.901 vs CSV 0.809 — contradicts §2 #1
  - no test validates a CLI-written results.json against the schema
  - otherwise: schema strict and valid, all lifestyle/annual/inputs values match the CSVs, ruff/mypy clean
- 2026-10-09 Fix after /verify: `returns[]` keys renamed `success_probability_at_required_return`, `standard_error_at_required_return`, `unresolved_fraction_at_required_return` (code + schema descriptions); the test now forbids any returns key that shares a sustainability CSV column name without the same meaning, and the CLI test validates the written file against the schema.

### F-021.2 Named runs, index.json and runs.js
- **Status**: Done
- **Depends on**: F-021.1

`--name`, `--overwrite`, `check_run_name`, run folders, `refresh_runs_index` (§2 #3–#7).

**Acceptance criteria**
- [x] Names follow the rule: `base-4pct`, `A_1` accepted; empty, `-x`, `a b`, `../x`, `a/b`, 65 characters rejected with exit 2 and the rule in the message — `test_run_name_rule`
- [x] `--name base` writes every output (CSVs, guide, metadata, `results.json`) to `<output-dir>/runs/base/` and nothing to `<output-dir>/` itself except `runs/` — `test_cli_named_run_writes_run_folder`
- [x] Re-running an existing name exits 2 before computing and leaves the folder untouched; with `--overwrite` it is replaced and a stale `lifestyle_reserve_results.csv` from an earlier reserve run is removed — `test_cli_named_run_refuses_existing_unless_overwrite`
- [x] After two named runs, `index.json` lists both (newest first, with the §2 #7 fields) and `runs.js` is `window.SBRETIRE_RUNS = …;` whose JSON payload equals the index plus each run's `results.json`; deleting a run folder and running again drops it — `test_runs_index_and_runs_js`

**Notes**
- 2026-10-09 `results_json`: `RUN_NAME_RULE`/`RUN_NAME_HELP`/`check_run_name`, `RUN_OUTPUT_FILES`, `refresh_runs_index` (rebuilds index.json + runs.js from disk; folder name is the run name; unreadable results skipped with a warning). `run`: `--name`, `--overwrite`; name and existence checked before loading data or printing anything (exit 2); `--overwrite` removes only known output files; named runs write to `<output-dir>/runs/<name>/` and refresh the index. Tests `tests/unit/test_named_runs.py` (4).
- 2026-10-09 /verify PASS (snapshot 28fc3e6):
  - 4 tests pass and can fail; full suite 405
  - own runs: folder layout, index newest-first with the 10 fields, runs.js loads in Bun with both runs, refusal exits 2 in ~0.5 s with nothing on stdout, --overwrite removes only known files
  - notes (fixed in B-021.1): Windows reserved names (CON, COM1 accepted; nul refused as "already exists"); --overwrite deletes old outputs before computing

### F-021.3 Design sample and docs
- **Status**: In Progress
- **Depends on**: F-021.2

`scripts/build_design_sample.py`, `docs/design/sample/runs/` (two runs of the example config), README (named runs,
results.json, viewer data), CHANGELOG. The Claude Design hand-off document moved to F-022.1 (user, 2026-10-09).

**Acceptance criteria**
- [ ] The committed sample has two runs whose `results.json` validate against the schema, `runs.js` matches them, and every input value comes from `config/model.example.yaml` (no other config) — `test_design_sample_is_valid_example_data`
- [ ] README documents `--name`, `--overwrite`, `results.json`, `index.json` and `runs.js` — `check: grep -n "\-\-overwrite" README.md`

### B-021.1 Reserved Windows run names and overwrite timing
- **Status**: In Progress
- **Depends on**: F-021.2

From the F-021.2 verify notes: reject Windows reserved device names (CON, PRN, AUX, NUL, COM1–COM9, LPT1–LPT9, any
case) in `check_run_name`; with `--overwrite`, remove the old run's files only after the computation succeeds, just
before writing, so a failed rerun keeps the previous run.

**Acceptance criteria**
- [ ] `CON`, `nul`, `Com1`, `lpt9` are rejected with a message naming the reserved-name rule; `console`, `com10` are accepted — `test_run_name_rejects_windows_reserved_names`
- [ ] If the computation fails during an `--overwrite` rerun, the previous run's files are all still there — `test_cli_overwrite_keeps_old_run_when_computation_fails`

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Schema validation — `test_results_json_validates_against_schema`
2. Values equal the run — `test_results_json_matches_run_objects`
3. Unnamed run writes it — `test_cli_run_writes_results_json`
4. Name rule — `test_run_name_rule`
5. Run folder — `test_cli_named_run_writes_run_folder`
6. Existing name — `test_cli_named_run_refuses_existing_unless_overwrite`
7. Index and runs.js — `test_runs_index_and_runs_js`
8. Sample — `test_design_sample_is_valid_example_data`
9. (moved to F-022.1) Design hand-off document
10. README — `check: grep -n "\-\-overwrite" README.md`
