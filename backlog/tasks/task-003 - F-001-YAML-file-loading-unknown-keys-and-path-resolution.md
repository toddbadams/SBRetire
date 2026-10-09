---
id: TASK-003
title: 'F-001: YAML file loading, unknown keys and path resolution'
status: To Do
assignee: []
created_date: '2026-10-09 09:52'
labels:
  - feature
  - config
milestone: m-0
dependencies:
  - TASK-002
references:
  - docs/backlog/feature-scenario-config-loading-and-validation-design-brief.md
  - src/sbretire/_yaml.py
  - src/sbretire/config.py
  - config/model.example.yaml
priority: medium
type: feature
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add the file layer: load_scenario(path, *, require_data_files=False) -> LoadedScenario.

Brief: docs/backlog/feature-scenario-config-loading-and-validation-design-brief.md — §2 decisions 3, 4, 9; §5 Interfaces; §6 step 3. Decisions: doc-003 §1, §2.

- New `src/sbretire/_yaml.py`: SafeLoader subclass that rejects duplicate mapping keys with their location.
- `model.unknown_keys: error|warn` (default error) applied at every depth; warn mode returns LoadedScenario.warnings.
- mortality.data_file resolved against the config file's directory; existence checked only when require_data_files=True.
- Update `config/model.example.yaml`: add `unknown_keys: error`, change data_file to `../data/ons_mortality.csv`.
- Tests in `tests/unit/test_config_loading.py` (use tmp_path; never depend on CWD).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The committed example config loads into a Scenario with every SPEC §4.2 field typed — test_load_example_config_returns_typed_scenario
- [ ] #2 Unknown keys at top level and nested are errors by default — test_unknown_keys_error_by_default
- [ ] #3 With unknown_keys: warn, unknown keys are returned as warnings and loading succeeds — test_unknown_keys_warn_mode_returns_warnings
- [ ] #4 Duplicate YAML keys in any mapping are rejected with their location — test_duplicate_yaml_keys_rejected
- [ ] #5 mortality.data_file resolves relative to the config file's directory regardless of CWD — test_data_file_resolved_relative_to_config
- [ ] #6 A missing data file is an issue only with require_data_files=True — test_missing_data_file_only_when_required
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 uv run python scripts/check.py passes (ruff, ruff format, mypy --strict, pytest)
- [ ] #2 Unit tests written or updated for all changed production code; SPEC §17 tests covered where the task touches them
- [ ] #3 Every acceptance criterion checked off and traceable to a SPEC section
- [ ] #4 No tax logic, hard-coded personal assumptions, or live data downloads in src/ (SPEC §2, §4, §16)
- [ ] #5 Implementation decisions recorded in backlog/docs/decisions/ when the task resolves a SPEC §18 item
- [ ] #6 README / docs/THESAURUS.md / data/README.md updated where behaviour, terms, or data provenance changed
<!-- DOD:END -->
