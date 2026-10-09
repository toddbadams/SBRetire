---
id: F-014
type: feature
parent: reporting-release
status: in-progress
complexity: 3
created: 2026-10-09
updated: 2026-10-09
---
# F-014 V1 Release: README, Acceptance and Reproducibility Sweep

## 1. Purpose

Prove V1 meets every SPEC §17.3 acceptance criterion with named, re-runnable evidence, guard the hard constraints
(no tax logic, no network access, injected randomness, recorded §18 decisions) with automated checks, finish the README
(§17.3 #9), and cut version 1.0.0 with a CHANGELOG and a local annotated tag `v1.0.0`.

## 2. Settled Decisions

| # | Decision | Choice | Why | Source |
|---|---|---|---|---|
| 1 | Release scope | Version 1.0.0 in `pyproject.toml` and `sbretire.__version__`; `CHANGELOG.md`; local annotated tag `v1.0.0` after the full gate passes; nothing pushed | Interview Q1 | Interview Q1 |
| 2 | Acceptance evidence | `docs/acceptance.md` maps every SPEC §17.1, §17.2 and §17.3 item to the tests/commands that evidence it; a test checks every referenced test exists so the map cannot rot | SPEC §17.3 | SPEC §17.3 |
| 3 | Constraint guards | `tests/acceptance/test_v1_acceptance.py`: no tax logic in `src/` (SPEC §16), no network modules imported in `src/` (SPEC §2), no global `np.random.*` calls (SPEC §10.3), every SPEC §18 item struck in `docs/decisions/` with a numbered entry, data provenance hashes in `data/README.md` match the files (SPEC §19), README has every §17.3 #9 section | Automated, so they stay true | CLAUDE.md hard constraints |
| 4 | README | Status updated to V1; sections: install, configuration (every key, units), running, outputs and interpretation, assumptions, limitations (no tax, fixed return, UK CPI for all linked income incl. FX, independent mortality, horizon censoring, not advice) | SPEC §17.3 #9, §2 | SPEC §17.3 |

## 3. Context

- All features F-001…F-013 and F-015 are done; 361 tests; `sbretire run` writes all outputs.
- Every SPEC §18 item is struck in `docs/decisions/*.md`.

## 4. Touch-points

**New**: `docs/acceptance.md`, `tests/acceptance/test_v1_acceptance.py`, `CHANGELOG.md`.

**Modified**: `README.md`, `pyproject.toml`, `src/sbretire/__init__.py`, `uv.lock`.

## 5. Interfaces

None (documentation, tests, version).

## 6. Plan of Work

1. Constraint guards and the acceptance map.
2. README completion.
3. Version, CHANGELOG, tag.

## 7. Validation

- **T1**: the acceptance tests; full `scripts/check.py`.
- **T2**: an end-to-end run of the example config after the version bump; metadata shows 1.0.0.

## 8. Decision Log

- 2026-10-09 — Release = 1.0.0 + CHANGELOG + local tag (Interview Q1).

## 9. Surprises

_(filled during implementation)_

## 10. Tasks

### F-014.1 Constraint guards and acceptance map
- **Status**: Verification
- **Depends on**: —

`tests/acceptance/test_v1_acceptance.py` (§2 #3) and `docs/acceptance.md` (§2 #2).

**Acceptance criteria**
- [x] No tax logic, no network imports and no global `np.random` calls in `src/` — `test_src_has_no_tax_network_or_global_randomness`
- [x] Every SPEC §18 item is struck and points at a numbered decision entry that exists — `test_all_spec_18_decisions_recorded`
- [x] `data/README.md` records the SHA-256 of every committed data file, and they match — `test_data_provenance_hashes_match`
- [x] `docs/acceptance.md` covers every §17.1, §17.2 and §17.3 item, and every test it names exists — `test_acceptance_map_complete`

**Notes**
- 2026-10-09 Added `tests/acceptance/test_v1_acceptance.py` (constraint guards over `src/`; explicit map of the ten SPEC §18 items to numbered decision entries and no unstruck SPEC items; raw data SHA-256s in data/README.md and sidecars; acceptance-map completeness parsed from SPEC §17.1–§17.3 with every named test checked to exist) and `docs/acceptance.md` (16 + 9 + 9 items → evidence). The guards passed on first run against existing code; the map test needed SPEC section parsing to stop at the next heading of any level (no ### follows §17.3).

### F-014.2 README for V1
- **Status**: Verification
- **Depends on**: F-014.1

Complete the README per §2 #4.

**Acceptance criteria**
- [x] README has install, configuration, running, outputs/interpretation, assumptions and limitations sections, documents every config key, and no longer says "scaffold" — `test_readme_covers_v1_sections`

**Notes**
- 2026-10-09 README: V1 status line (no longer 'scaffold'); Windows PowerShell quick start; '## Configuration' reference table covering every key with units/meaning; separate '## Assumptions' (returns, inflation, mortality, ordering, success definition) and '## Limitations' (no tax, no market risk, foreign income/FX, exclusions, parameter uncertainty, not advice) sections. `test_readme_covers_v1_sections` passes.

### F-014.3 Version 1.0.0, CHANGELOG and tag
- **Status**: Verification
- **Depends on**: F-014.2

Bump to 1.0.0, write `CHANGELOG.md`, run the full gate and an end-to-end example run, then tag `v1.0.0` locally.

**Acceptance criteria**
- [x] `sbretire --version` prints 1.0.0 and `run_metadata.json` records `software_version` 1.0.0; CHANGELOG has a 1.0.0 entry — `test_version_is_1_0_0`
- [x] Annotated tag `v1.0.0` exists on the release commit — `check: git tag -l v1.0.0 -n1`

**Notes**
- 2026-10-09 Version 1.0.0 in `pyproject.toml`, `src/sbretire/__init__.py` and `uv.lock`; `CHANGELOG.md` 1.0.0 entry (features F-001…F-015, fix B-011.1). Full gate 367 passed. PowerShell end-to-end run of the example: exit 0 in 94 s, four files written, `software_version` 1.0.0. Annotated tag `v1.0.0` created locally on this commit (not pushed).

## 11. Open Questions

- None.

## 12. Acceptance Criteria

1. Constraint guards — `test_src_has_no_tax_network_or_global_randomness`
2. §18 recorded — `test_all_spec_18_decisions_recorded`
3. Provenance hashes — `test_data_provenance_hashes_match`
4. Acceptance map — `test_acceptance_map_complete`
5. README — `test_readme_covers_v1_sections`
6. Version — `test_version_is_1_0_0`
7. Tag — `check: git tag -l v1.0.0 -n1`
