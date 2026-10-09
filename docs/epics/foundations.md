---
epic: foundations
title: Foundations
status: active
spec_sections: [§4, §4.2, §4.3, §5, §10.3]
depends_on: []
milestones:
  - { id: F-001, title: Scenario Config Loading and Validation, status: done }
  - { id: F-005, title: Random Streams and Run Metadata, status: briefed }
created: 2026-10-09
updated:
  - 2026-10-09: created by /decompose-spec
  - 2026-10-09: F-001 briefed
  - 2026-10-09: F-001 done
---

# Foundations

## Goal

Every run starts from a validated **Scenario** and a reproducible random state. This epic delivers the typed, fail-fast YAML config (including the **As-Of Date**) and the **Random Stream** plumbing plus run metadata that make a fixed seed reproduce identical results (SPEC §10.3, §17.3 criterion 3).

## Scope

**In:**
- YAML loading into frozen, typed config objects; every required field of SPEC §4.2; fail-fast validation with actionable errors (SPEC §4.3).
- `model.as_of_date` → valuation date and first simulated month (SPEC §5).
- Unknown-key strictness setting (SPEC §4.3).
- One `SeedSequence` spawning independent mortality and inflation streams; `random_seed: null` generates and records a seed (SPEC §4.2, §10.3).
- Run metadata: seed, software version, config hash, data-file versions/hashes (SPEC §10.3).

**Out:**
- Data-file content validation for mortality/inflation (F-006, F-007 — they own their schemas).
- Writing metadata alongside CSVs at the end of a run (F-013 wires it into the CLI).

## Decomposition — features and order

| F-NNN | Feature | SPEC §§ | §17 tests made passable | §18 decisions resolved | depends_on |
|---|---|---|---|---|---|
| F-001 | Scenario Config Loading and Validation | §4, §4.2, §4.3, §5 | YAML loads and validates; missing fields, duplicate IDs, invalid dates, invalid percentages rejected | Valuation date and first simulated month; unknown-key strictness | — |
| F-005 | Random Streams and Run Metadata | §10.3, §4.2 `random_seed` | Fixed seed reproduces outputs | — | F-001 |

## Risks and open questions

- ~~Config hash must be stable across YAML formatting changes? Decide whether to hash raw bytes or a canonicalised form (F-005).~~ → canonical validated Scenario (configuration §7).
