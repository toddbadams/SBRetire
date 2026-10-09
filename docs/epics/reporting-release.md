---
epic: reporting-release
title: Reporting and Release
status: active
spec_sections: [§1.2, §2, §12, §15, §16, §17.3, §19]
depends_on: [simulation-engine, analysis-optimization, foundations, household-cash-flows]
milestones:
  - { id: F-012, title: Annual Results CSV, status: in-progress }
  - { id: F-013, title: Sustainability and Lifestyle CSVs and End-to-End CLI, status: briefed }
  - { id: F-014, title: "V1 Release: README, Acceptance and Reproducibility Sweep", status: proposed }
  - { id: F-015, title: Deterministic Preview Run, status: done }
created: 2026-10-09
updated:
  - 2026-10-09: created by /decompose-spec
  - 2026-10-09: added F-015 Deterministic Preview Run
  - 2026-10-09: F-015 briefed
  - 2026-10-09: F-015 done
---

# Reporting and Release

## Goal

Turn engine and optimizer results into the three required CSVs plus run metadata, run end to end from `sbretire --config … --output-dir …`, and prove V1 meets every SPEC §17.3 acceptance criterion.

## Scope

**In:**
- `annual_results.csv`: one row per calendar year with survival probabilities, budget/income/net-withdrawal medians, portfolio percentiles, **Probability Not Depleted Yet**, estimated lifetime success rate, completed/unresolved counts (SPEC §12, §15.1).
- `sustainability_results.csv` and `lifestyle_results.csv` (SPEC §15.2, §15.3).
- CSV conventions: UTF-8, header, `.` decimals, ISO dates, no currency symbols/thousands separators, units in names or README (SPEC §15).
- `run_metadata.json` written with every run (SPEC §10.3, §15).
- README: installation, configuration, running, output interpretation, assumptions, limitations (SPEC §17.3 #9).
- Acceptance sweep: every §17.3 criterion evidenced; constraint checks (no tax logic, no network, CRN, reproducibility) (SPEC §2, §16, §17.3).

**Out:**
- Charts/visualisation (not in SPEC).
- Tax module (SPEC §16 — later, separate).

## Decomposition — features and order

| F-NNN | Feature | SPEC §§ | §17 tests made passable | §18 decisions resolved | depends_on |
|---|---|---|---|---|---|
| F-012 | Annual Results CSV | §12, §15.1, §15, §1.2 | CSV schema and units match spec (annual) | Definition of annual portfolio percentiles and funded probabilities | F-009 |
| F-013 | Sustainability and Lifestyle CSVs and End-to-End CLI | §15.2, §15.3, §15 metadata | CSV schemas and units match spec (sustainability, lifestyle) | — | F-010, F-011, F-012 |
| F-014 | V1 Release: README, Acceptance and Reproducibility Sweep | §17.3, §2, §16, §19 | §17.3 acceptance criteria 1–9 | Confirms all §18 items are recorded | F-013 |
| F-015 | Deterministic Preview Run — `sbretire preview`: one Path with chosen death ages and constant inflation at `inflation.annual_mean`, year-by-year table + `preview.csv` | §1.1 (sanity view), §12 groundwork | — (not a SPEC requirement) | — | F-003, F-004 |

## Risks and open questions

- F-015 is built early (after F-004) for visibility; it must be labelled as a deterministic illustration, never as a sustainability result (SPEC §14 "avoid presenting illustrative example numbers as calculated results").

- SPEC §12 lists `probability_funded` but then requires two unambiguous columns instead. Recommendation: omit `probability_funded`, publish `probability_not_depleted_yet` and `estimated_lifetime_success_rate` (F-012).
- Calendar-year rows vs a mid-year as-of date: the first and last rows are partial years — F-012 must define how partial years are aggregated.
