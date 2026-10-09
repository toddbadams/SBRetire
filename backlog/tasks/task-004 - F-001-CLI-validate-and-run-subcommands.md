---
id: TASK-004
title: 'F-001: CLI validate and run subcommands'
status: To Do
assignee: []
created_date: '2026-10-09 09:52'
labels:
  - feature
  - config
milestone: m-0
dependencies:
  - TASK-003
references:
  - docs/backlog/feature-scenario-config-loading-and-validation-design-brief.md
  - src/sbretire/__main__.py
  - tests/unit/test_cli.py
  - README.md
  - CLAUDE.md
priority: medium
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Expose validation to the user.

Brief: docs/backlog/feature-scenario-config-loading-and-validation-design-brief.md — §2 decision 7; §5 CLI; §6 step 4.

- `sbretire validate --config PATH [--require-data-files]`: exit 0 + one-line summary (and warnings) on success; exit 2 + one issue per line on stderr when invalid; exit 1 when the file is unreadable.
- `sbretire run --config PATH --output-dir DIR`: validates, then exits 1 with "engine not implemented" until F-013.
- Update `tests/unit/test_cli.py`, README.md (Run section) and CLAUDE.md (Commands).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 validate on the example config exits 0 and prints a summary — test_cli_validate_example_config_exits_zero
- [ ] #2 validate on an invalid config exits 2 and prints one line per issue — test_cli_validate_invalid_exits_two_lists_issues
- [ ] #3 validate on a missing file exits 1 — test_cli_validate_missing_file_exits_one
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
