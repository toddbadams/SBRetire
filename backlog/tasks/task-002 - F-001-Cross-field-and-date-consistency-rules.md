---
id: TASK-002
title: 'F-001: Cross-field and date consistency rules'
status: To Do
assignee: []
created_date: '2026-10-09 09:52'
labels:
  - feature
  - config
milestone: m-0
dependencies:
  - TASK-001
references:
  - docs/backlog/feature-scenario-config-loading-and-validation-design-brief.md
  - src/sbretire/config.py
priority: medium
type: feature
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add cross-field validators to the Scenario models, reporting into the same issue list.

Brief: docs/backlog/feature-scenario-config-loading-and-validation-design-brief.md — §2 decisions 2 and 6; §5 models table (date and reference rules); §6 step 2. Decisions: doc-001 §1, doc-003 §3.

- model.as_of_date must be the 1st of a month.
- Income start_date/end_date on the 1st; end_date exclusive, > start_date, > as_of_date; start_date before as_of_date allowed.
- Each date_of_birth < as_of_date; exactly two people; unique person ids; unique income ids; income.recipient must be a person id.
- Tests in `tests/unit/test_config_consistency.py`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Duplicate person ids and duplicate income ids are rejected — test_duplicate_ids_rejected
- [ ] #2 Date rules enforced: as-of not on the 1st, income dates not on the 1st, end_date <= start_date, end_date <= as_of_date, DOB >= as_of — test_date_rules_rejected (parametrised)
- [ ] #3 Income start_date before as_of_date is accepted — test_income_start_before_as_of_accepted
- [ ] #4 People count != 2 and a recipient that is not a person id are rejected — test_people_count_and_recipient_reference
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
