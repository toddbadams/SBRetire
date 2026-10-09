---
id: F-001
type: feature
parent: foundations
status: in-progress
complexity: 3
created: 2026-10-09
updated: 2026-10-09
---
# F-001 Scenario Config Loading and Validation

## 1. Purpose

Load a **Scenario** YAML into typed, immutable objects and refuse anything invalid before a single **Path** is simulated. Every field required by SPEC §4.2 is validated; every problem is reported at once with its YAML location and an actionable message (SPEC §4.3). Resolves two decisions: the **As-Of Date** / first simulated month (SPEC §5, §18) and the unknown-key strictness setting (SPEC §4.3).

Ships a user-visible slice: `sbretire validate --config <file>`.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Validation mechanism | pydantic v2 models (frozen, `strict` scalar types) | YAML-path error locations and collect-all errors for free; mypy plugin | Interview Q1; tooling-and-process |
| 2 | As-Of Date | `model.as_of_date` required, must be the 1st of a month; first simulated month = that month | No partial months; fail fast rather than round | Interview Q2; SPEC §5; simulation-conventions §1 |
| 3 | Unknown keys | `model.unknown_keys: error \| warn`, default `error`, applies at every depth | Catches typos that would silently fall back to defaults; reproducible from the file alone | Interview Q3; SPEC §4.3; configuration §1 |
| 4 | Relative paths | Resolved against the config file's directory | Independent of working directory | Interview Q4; configuration §2 |
| 5 | Schema scope | Exactly the SPEC §4.1 example fields + optional `income[].end_date`; `inflation.model` free string (F-006 narrows); `recipient` must be a person id (F-003 extends); per-person `survivor_budget_factor` stored, precedence in F-004 | Later features own their §18 decisions | Interview Q5 |
| 6 | Date rules | Income `start_date`/`end_date` on the 1st of a month; `end_date` exclusive and > `start_date`; `end_date` ≤ as-of rejected; `start_date` < as-of allowed; DOB < as-of; exactly 2 people | Consistent with #2; SPEC §2 two people | Interview Q6; configuration §3 |
| 7 | Interface + CLI | `sbretire.config.load_scenario` → `LoadedScenario`; `ScenarioError` with `ScenarioIssue`s; CLI subcommands `validate` and `run` | Usable now on real configs | Interview Q7 |
| 8 | SPEC-fixed values | `currency == "GBP"`, `frequency == "monthly"`, ranges per SPEC §4.2 (see §5) | Stated by SPEC | SPEC §4.2 |
| 9 | Duplicate YAML keys | Rejected (custom SafeLoader) | PyYAML otherwise keeps the last silently — same typo class as #3 | Brief author; SPEC §4.3 spirit |
| 10 | Sex categories | `male` \| `female` enum; F-007 verifies against the dataset's definitions | No silent mapping (SPEC §4.2) | SPEC §4.2 |

## 3. Context

- Code today: `src/sbretire/__main__.py` (argparse placeholder with `--config`, `--output-dir`), `tests/unit/test_cli.py`. No config module.
- Constraints (CLAUDE.md): nothing personal hard-coded; fail fast with actionable errors; mypy --strict; names from `docs/THESAURUS.md` (Scenario, As-Of Date, Budget, Income Stream, Recipient, Survivor Percentage, Survivor Budget Factor, Horizon).
- `config/model.yaml` is git-ignored; `config/model.example.yaml` is committed and must validate.

## 4. Touch-points

**New**

| File | Purpose |
|---|---|
| `src/sbretire/config.py` | pydantic models, `load_scenario`, `parse_scenario`, `ScenarioError`, `ScenarioIssue`, `LoadedScenario` |
| `src/sbretire/_yaml.py` | SafeLoader subclass rejecting duplicate keys |
| `tests/unit/test_config_fields.py` | field-level validation |
| `tests/unit/test_config_consistency.py` | cross-field / date rules |
| `tests/unit/test_config_loading.py` | file loading, duplicates, unknown keys, paths, example file |
| `tests/fixtures/scenarios/valid_minimal.yaml` | known-good fixture (no personal data) |

**Modified**

| File | Change |
|---|---|
| `pyproject.toml` | add `pydantic>=2.9`; mypy `plugins = ["pydantic.mypy"]` |
| `src/sbretire/__main__.py` | subcommands `validate`, `run` |
| `tests/unit/test_cli.py` | subcommand tests |
| `config/model.example.yaml` | `unknown_keys: error`; `data_file: ../data/ons_mortality.csv` |
| `README.md`, `CLAUDE.md` | `sbretire validate` / `sbretire run` usage; config path rule |

**Deleted:** none.

## 5. Interfaces

```python
# sbretire.config
class ScenarioIssue(NamedTuple):
    location: str  # e.g. "income[2].survivor_percentage", "model" for whole-section issues
    message: str  # actionable, includes the offending value where safe


class ScenarioError(ValueError):
    issues: tuple[ScenarioIssue, ...]  # str(err) = one issue per line, sorted by location


@dataclass(frozen=True)
class LoadedScenario:
    scenario: Scenario
    source_path: Path  # resolved config path
    warnings: tuple[ScenarioIssue, ...]  # unknown keys under `warn`


def load_scenario(path: Path | str, *, require_data_files: bool = False) -> LoadedScenario: ...
def parse_scenario(
    raw: Mapping[str, object], *, base_dir: Path, require_data_files: bool = False
) -> LoadedScenario: ...
```

Models (all `frozen=True`; `extra` driven by `unknown_keys`):

| Model | Fields (type, rule) |
|---|---|
| `Scenario` | `model: ModelSettings`, `portfolio: PortfolioAssumptions`, `budget: BudgetAssumptions`, `inflation: InflationAssumptions`, `mortality: MortalityAssumptions`, `people: tuple[Person, Person]`, `income: tuple[IncomeStream, ...]` (may be empty) |
| `ModelSettings` | `currency: Literal["GBP"]`; `as_of_date: date` (day == 1); `simulation_count: int > 0`; `confidence_levels: tuple[float, ...]` non-empty, each 0 < p < 1, unique; `frequency: Literal["monthly"]`; `horizon_years: int > 0`; `random_seed: int ≥ 0 \| None`; `unknown_keys: Literal["error","warn"] = "error"` |
| `PortfolioAssumptions` | `starting_balance: float ≥ 0`; `annual_return: float > -1` |
| `BudgetAssumptions` | `monthly_amount_today: float ≥ 0`; `survivor_budget_factor: float ≥ 0` |
| `InflationAssumptions` | `source: str`; `source_period: str`; `annual_mean: float`; `annual_standard_deviation: float ≥ 0`; `model: str`; `parameter_units: str` |
| `MortalityAssumptions` | `source, geography, projection: str`; `data_file: Path` (resolved against config dir; must exist iff `require_data_files`) |
| `Person` | `id: str` (non-empty, unique); `name: str`; `date_of_birth: date` (< as_of); `sex: Literal["male","female"]`; `survivor_budget_factor: float ≥ 0 \| None = None` |
| `IncomeStream` | `id: str` (unique among streams); `name: str`; `start_date: date` (day 1); `end_date: date \| None` (day 1, > start, > as_of); `annual_amount_today: float ≥ 0`; `inflation_linked: bool`; `survivor_percentage: float in [0, 1]`; `recipient: str` (a person id) |

Scalars are strict: `"0.05"` is not a float, `"yes"` is not a bool, `1` is not a bool. Ints are accepted where floats are expected. Dates accept YAML dates or ISO `YYYY-MM-DD` strings only.

CLI:

```
sbretire validate --config PATH [--require-data-files]   # exit 0: summary; exit 2: issues (stderr); exit 1: unreadable file
sbretire run --config PATH --output-dir DIR              # validates, then "engine not implemented" (exit 1) until F-013
```

Validate summary (stdout), e.g.: `OK config/model.yaml — 2 people, 3 income streams, as-of 2026-10-01, 100000 paths, horizon 100 y`, plus any warnings.

## 6. Plan of Work

1. Add pydantic + mypy plugin; build the field models and `parse_scenario` with issue aggregation (pydantic errors → `ScenarioIssue` with dotted/indexed locations).
2. Add cross-field validators (dates, uniqueness, recipient refs, two people) reporting into the same issue list.
3. Add the file layer: duplicate-key-rejecting YAML loader, `unknown_keys` handling (error vs warn), path resolution, `require_data_files`; update the example config and prove it validates.
4. CLI subcommands, docs.

## 7. Validation

- **T1** — unit tests per AC (named in §12); `scripts/check.py` green (ruff, format, mypy --strict with pydantic plugin).
- **T2** — `sbretire validate --config config/model.example.yaml` exits 0 (`test_cli_validate_example_config_exits_zero`).
- **T3** — n/a (no randomness).

## 8. Decision Log

- 2026-10-09 — Interview Q1–Q7 settled decisions 1–7 in §2. Decisions 2, 3, 4, 6 recorded in `docs/decisions/` (simulation-conventions §1, configuration §§1–3).
- 2026-10-09 — Duplicate YAML keys rejected (decision 9), added by brief author as a §4.3 corollary.
- 2026-10-09 — Backlog.md dropped (tooling-and-process §4): TASK-001…004 became F-001.1…F-001.4 in §10; decisions moved to `docs/decisions/`.

## 9. Surprises

- 2026-10-09 — pydantic's built-in `strict=True` rejects YAML lists for tuple fields and ISO strings for dates, so strictness is implemented per scalar type with BeforeValidators instead of model-wide strict mode. `income` is optional (defaults to no streams); `random_seed` is required but may be null.
- 2026-10-09 — Relational rules (ids, people count, DOB, recipient, end-date ordering) run only after every field is valid, so a scenario with field errors gets a second round of relational issues once those are fixed. Day-of-month rules are field-level and always reported in the first round.

## 10. Tasks

Task format and statuses: `docs/project-sdlc.md` §2. Definition of done: `docs/project-sdlc.md` §4.

### F-001.1 Scenario field models and issue aggregation
- **Status**: Verification
- **Depends on**: —

Build the typed Scenario models and parse_scenario with collect-all error reporting.

- Add `pydantic>=2.9` to dependencies and `plugins = ["pydantic.mypy"]` to [tool.mypy].
- New `src/sbretire/config.py`: frozen models ModelSettings, PortfolioAssumptions, BudgetAssumptions, InflationAssumptions, MortalityAssumptions, Person, IncomeStream, Scenario with SPEC §4.2 field rules; strict scalars (no str→number/bool, no int→bool).
- `parse_scenario(raw, *, base_dir, require_data_files=False) -> LoadedScenario` converting pydantic errors to ScenarioIssue(location, message) with dotted/indexed locations (e.g. `income[2].survivor_percentage`), raised as one ScenarioError sorted by location.
- Fixture `tests/fixtures/scenarios/valid_minimal.yaml` (no personal data). Tests in `tests/unit/test_config_fields.py`.

**Acceptance criteria**
- [x] Missing required key in any section yields an issue at that key's location — `test_missing_required_field_reports_location` (parametrised over every required key)
- [x] Wrong types are rejected without coercion (string number, string/int bool, non-ISO date) — `test_strict_scalars_reject_coercion`
- [x] Out-of-range values rejected: negative amounts, annual_return <= -1, survivor_percentage outside [0,1], negative factors, confidence level not in (0,1), duplicate confidence levels, simulation_count/horizon_years <= 0, currency != GBP, frequency != monthly — `test_out_of_range_values_rejected` (parametrised)
- [x] Three independent errors yield exactly three issues sorted by location in one ScenarioError — `test_all_issues_reported_together`

**Notes**
- 2026-10-09: `src/sbretire/config.py` — frozen pydantic models (`_Frozen`: frozen, extra=forbid) for every §4.2 section; strict scalars via BeforeValidator types (`Number`, `Integer`, `Boolean`, `Text`, `IsoDate`); `parse_scenario` maps pydantic errors to `ScenarioIssue` (natural-sorted, "must be …" wording, offending value echoed). Added `pydantic>=2.9` + mypy plugin. Tests: `tests/unit/test_config_fields.py` (79 cases), helpers `tests/unit/scenario_helpers.py`, fixture `tests/fixtures/scenarios/valid_minimal.yaml`.

### F-001.2 Cross-field and date consistency rules
- **Status**: Verification
- **Depends on**: F-001.1

Add cross-field validators to the Scenario models, reporting into the same issue list.

- model.as_of_date must be the 1st of a month.
- Income start_date/end_date on the 1st; end_date exclusive, > start_date, > as_of_date; start_date before as_of_date allowed.
- Each date_of_birth < as_of_date; exactly two people; unique person ids; unique income ids; income.recipient must be a person id.
- Tests in `tests/unit/test_config_consistency.py`.

**Acceptance criteria**
- [x] Duplicate person ids and duplicate income ids are rejected — `test_duplicate_ids_rejected`
- [x] Date rules enforced: as-of not on the 1st, income dates not on the 1st, end_date <= start_date, end_date <= as_of_date, DOB >= as_of — `test_date_rules_rejected` (parametrised)
- [x] Income start_date before as_of_date is accepted — `test_income_start_before_as_of_accepted`
- [x] People count != 2 and a recipient that is not a person id are rejected — `test_people_count_and_recipient_reference`

**Notes**
- 2026-10-09: `src/sbretire/config.py` — `MonthStart` date type (1st-of-month, with a suggested correction) for `as_of_date`, `start_date`, `end_date`; `_consistency_issues` for duplicate ids, exactly two people, DOB < as-of, recipient ∈ people ids, `end_date` > start and > as-of. Tests: `tests/unit/test_config_consistency.py`.

### F-001.3 YAML file loading, unknown keys and path resolution
- **Status**: To Do
- **Depends on**: F-001.2

Add the file layer: load_scenario(path, *, require_data_files=False) -> LoadedScenario.

- New `src/sbretire/_yaml.py`: SafeLoader subclass that rejects duplicate mapping keys with their location.
- `model.unknown_keys: error|warn` (default error) applied at every depth; warn mode returns LoadedScenario.warnings.
- mortality.data_file resolved against the config file's directory; existence checked only when require_data_files=True.
- Update `config/model.example.yaml`: add `unknown_keys: error`, change data_file to `../data/ons_mortality.csv`.
- Tests in `tests/unit/test_config_loading.py` (use tmp_path; never depend on CWD).

**Acceptance criteria**
- [ ] The committed example config loads into a Scenario with every SPEC §4.2 field typed — `test_load_example_config_returns_typed_scenario`
- [ ] Unknown keys at top level and nested are errors by default — `test_unknown_keys_error_by_default`
- [ ] With unknown_keys: warn, unknown keys are returned as warnings and loading succeeds — `test_unknown_keys_warn_mode_returns_warnings`
- [ ] Duplicate YAML keys in any mapping are rejected with their location — `test_duplicate_yaml_keys_rejected`
- [ ] mortality.data_file resolves relative to the config file's directory regardless of CWD — `test_data_file_resolved_relative_to_config`
- [ ] A missing data file is an issue only with require_data_files=True — `test_missing_data_file_only_when_required`

### F-001.4 CLI validate and run subcommands
- **Status**: To Do
- **Depends on**: F-001.3

Expose validation to the user.

- `sbretire validate --config PATH [--require-data-files]`: exit 0 + one-line summary (and warnings) on success; exit 2 + one issue per line on stderr when invalid; exit 1 when the file is unreadable.
- `sbretire run --config PATH --output-dir DIR`: validates, then exits 1 with "engine not implemented" until F-013.
- Update `tests/unit/test_cli.py`, README.md (Run section) and CLAUDE.md (Commands).

**Acceptance criteria**
- [ ] validate on the example config exits 0 and prints a summary — `test_cli_validate_example_config_exits_zero`
- [ ] validate on an invalid config exits 2 and prints one line per issue — `test_cli_validate_invalid_exits_two_lists_issues`
- [ ] validate on a missing file exits 1 — `test_cli_validate_missing_file_exits_one`

## 11. Open Questions

- Should `simulation_count` have an upper bound or a memory estimate warning? Deferred to F-009 (memory is engine-specific).
- Upper bound on `survivor_budget_factor` (> 1 allowed by SPEC)? Not restricted in F-001.

## 12. Acceptance Criteria

1. The committed example config loads into a `Scenario` with every SPEC §4.2 field typed — `test_load_example_config_returns_typed_scenario`.
2. A missing required key in any section produces an issue at that key's location — `test_missing_required_field_reports_location` (parametrised over every required key).
3. Wrong types are rejected without coercion (string number, string/int bool, non-ISO date) — `test_strict_scalars_reject_coercion`.
4. Out-of-range values are rejected: negative amounts, `annual_return ≤ -1`, survivor percentage outside [0,1], negative factors, confidence level ∉ (0,1), duplicate confidence levels, `simulation_count`/`horizon_years` ≤ 0, `currency ≠ GBP`, `frequency ≠ monthly` — `test_out_of_range_values_rejected` (parametrised).
5. Duplicate person ids and duplicate income ids are rejected — `test_duplicate_ids_rejected`.
6. Date rules (§2 #2, #6) are enforced: as-of not on the 1st, income dates not on the 1st, `end_date ≤ start_date`, `end_date ≤ as_of_date`, DOB ≥ as-of — `test_date_rules_rejected` (parametrised); `start_date` before as-of is accepted — `test_income_start_before_as_of_accepted`.
7. People count ≠ 2 and a `recipient` that is not a person id are rejected — `test_people_count_and_recipient_reference`.
8. All issues are reported together: a config with three independent errors yields exactly three issues, sorted by location, in one `ScenarioError` — `test_all_issues_reported_together`.
9. Unknown keys at top level and nested (`income[0].foo`) are errors by default and warnings with `unknown_keys: warn` — `test_unknown_keys_error_by_default`, `test_unknown_keys_warn_mode_returns_warnings`.
10. Duplicate YAML keys in any mapping are rejected with their location — `test_duplicate_yaml_keys_rejected`.
11. `mortality.data_file` resolves relative to the config file's directory regardless of CWD; a missing file is an issue only with `require_data_files=True` — `test_data_file_resolved_relative_to_config`, `test_missing_data_file_only_when_required`.
12. `sbretire validate` exits 0 with a summary on a valid file, 2 with one line per issue on an invalid file, 1 on an unreadable file — `test_cli_validate_example_config_exits_zero`, `test_cli_validate_invalid_exits_two_lists_issues`, `test_cli_validate_missing_file_exits_one`.
