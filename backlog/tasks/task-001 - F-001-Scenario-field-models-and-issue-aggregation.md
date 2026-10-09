---
id: TASK-001
title: 'F-001: Scenario field models and issue aggregation'
status: To Do
assignee: []
created_date: '2026-10-09 09:52'
labels:
  - feature
  - config
milestone: m-0
dependencies: []
references:
  - docs/backlog/feature-scenario-config-loading-and-validation-design-brief.md
  - docs/SPEC.md
  - pyproject.toml
  - src/sbretire/config.py
priority: high
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the typed Scenario models and parse_scenario with collect-all error reporting.

Brief: docs/backlog/feature-scenario-config-loading-and-validation-design-brief.md — §2 decisions 1, 5, 8, 10; §5 Interfaces (models table, ScenarioIssue/ScenarioError); §6 step 1.

- Add `pydantic>=2.9` to dependencies and `plugins = ["pydantic.mypy"]` to [tool.mypy].
- New `src/sbretire/config.py`: frozen models ModelSettings, PortfolioAssumptions, BudgetAssumptions, InflationAssumptions, MortalityAssumptions, Person, IncomeStream, Scenario with SPEC §4.2 field rules; strict scalars (no str→number/bool, no int→bool).
- `parse_scenario(raw, *, base_dir, require_data_files=False) -> LoadedScenario` converting pydantic errors to ScenarioIssue(location, message) with dotted/indexed locations (e.g. `income[2].survivor_percentage`), raised as one ScenarioError sorted by location.
- Fixture `tests/fixtures/scenarios/valid_minimal.yaml` (no personal data). Tests in `tests/unit/test_config_fields.py`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Missing required key in any section yields an issue at that key's location — test_missing_required_field_reports_location (parametrised over every required key)
- [ ] #2 Wrong types are rejected without coercion (string number, string/int bool, non-ISO date) — test_strict_scalars_reject_coercion
- [ ] #3 Out-of-range values rejected: negative amounts, annual_return <= -1, survivor_percentage outside [0,1], negative factors, confidence level not in (0,1), duplicate confidence levels, simulation_count/horizon_years <= 0, currency != GBP, frequency != monthly — test_out_of_range_values_rejected (parametrised)
- [ ] #4 Three independent errors yield exactly three issues sorted by location in one ScenarioError — test_all_issues_reported_together
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
