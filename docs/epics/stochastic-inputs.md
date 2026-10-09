---
epic: stochastic-inputs
title: Stochastic Inputs
status: proposed
spec_sections: [§4.1, §4.2, §4.3, §6, §7.1, §7.2, §19]
depends_on: [foundations, household-cash-flows]
milestones:
  - { id: F-006, title: Stochastic Inflation Process and CPI Calibration, status: proposed }
  - { id: F-007, title: ONS Mortality Data Ingest and Mapping, status: proposed }
  - { id: F-008, title: Monthly Mortality Sampling, status: proposed }
created: 2026-10-09
updated:
  - 2026-10-09: created by /decompose-spec
---

# Stochastic Inputs

## Goal

The two sources of uncertainty in V1: an inflation path per **Path** (one annual draw held for twelve months, cumulative **Inflation Index**) calibrated to documented UK CPI data, and a death time per person sampled from ONS 2024-based cohort mortality — each drawn from its own **Random Stream**, with source data local, versioned and hashed.

## Scope

**In:**
- Choice and documentation of one precise inflation process guaranteeing 1+π > 0, with explicit parameter interpretation (arithmetic moments vs log-space vs empirical resampling) (SPEC §4.1, §6).
- CPI calibration file in `data/`, provenance in `data/README.md` (SPEC §19).
- ONS cohort mortality download, verification, transformation script, provenance; loader mapping (age, sex, calendar year) → q(x,y); coverage and value validation (SPEC §4.2, §4.3, §7.1).
- Monthly conversion q_m = 1 − (1 − q)^(1/12); independent per-person sampling; dead stays dead (SPEC §7.2).

**Out:**
- Mortality dependence between the two people (SPEC §7.2: independent in V1).
- Stochastic investment returns (SPEC §2 excluded).
- Live downloads during a run (SPEC §2) — acquisition is a one-off script, never called by the engine.

## Decomposition — features and order

| F-NNN | Feature | SPEC §§ | §17 tests made passable | §18 decisions resolved | depends_on |
|---|---|---|---|---|---|
| F-006 | Stochastic Inflation Process and CPI Calibration | §6, §4.1, §4.2 inflation | Zero inflation keeps index constant; deterministic inflation fixture → expected nominal spending | Exact inflation process and calibration dataset; whether any income is indexed to a non-CPI measure | F-003, F-004, F-005 |
| F-007 | ONS Mortality Data Ingest and Mapping | §7.1, §4.2 mortality, §4.3, §19 | Mortality data not covering required ages/years, or with invalid values, rejected | Exact ONS file/table and age/period mapping | F-001 |
| F-008 | Monthly Mortality Sampling | §7.2 | Monthly conversion reproduces annual probability; dead person never alive again; deterministic mortality fixture → expected household state transitions | — (death timing decided in F-002) | F-002, F-005, F-007 |

## Risks and open questions

- **Mortality coverage vs horizon.** A 100-year horizon takes person_2 to ~age 157; ONS tables end far earlier. F-007 must choose a tail rule (e.g. q = 1 at a terminal age, or extrapolation) or an age-based horizon cap — and record it.
- **Inflation "year" boundary.** Draws are annual; reporting is by calendar year. F-006 decides whether simulation years run from the as-of month or align to calendar years.
- **Data availability.** The exact ONS 2024-based cohort tables must be verified before F-007 can finish (SPEC §7.1, §19). Treat as the earliest-risk item; F-007 has no dependency beyond F-001 so it can start early.
