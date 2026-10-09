---
epic: simulation-engine
title: Simulation Engine
status: proposed
spec_sections: [§5, §7.2, §9, §10.1, §10.2, §10.4, §11]
depends_on: [foundations]
milestones:
  - { id: F-002, title: Deterministic Portfolio Engine (Walking Skeleton), status: proposed }
  - { id: F-009, title: Monte Carlo Path Outcomes, Censoring and Success Metrics, status: proposed }
created: 2026-10-09
updated:
  - 2026-10-09: created by /decompose-spec
---

# Simulation Engine

## Goal

The monthly, path-vectorised engine that answers the primary question (SPEC §1.1): for each **Path**, does the portfolio fund every month of **Required Spending** until both people have died? F-002 is the walking skeleton — deterministic deaths, zero inflation, fixed return — so the full month loop, **Depletion** and **Shortfall** rules are proven before any randomness is added. F-009 turns it into the full Monte Carlo with **Censored Path** handling and the success metrics.

## Scope

**In:**
- Annual effective → monthly effective return (SPEC §9).
- Documented within-month ordering: alive-state update → income/spending due → apply return to opening balance → add income → test funding → subtract spending (SPEC §5).
- Depletion when balance after return + income < Required Spending; balance floored at zero; shortfall recorded; path stops (SPEC §9).
- Path stops when both people are dead (SPEC §10.2 step 5).
- Vectorised over paths with memory-conscious state (SPEC §10.4).
- Path classification: completed / successful / failed / censored; **Conservative Success Rate**, **Completed-Path Success Rate**, unresolved fraction, **Monte Carlo Standard Error** with stated denominators (SPEC §11).

**Out:**
- Income-stream and spending rules themselves (household-cash-flows epic) — F-002 uses the simplest constant forms and F-003/F-004 replace them.
- Stochastic inputs (stochastic-inputs epic).
- CSV output (reporting-release epic).

## Decomposition — features and order

| F-NNN | Feature | SPEC §§ | §17 tests made passable | §18 decisions resolved | depends_on |
|---|---|---|---|---|---|
| F-002 | Deterministic Portfolio Engine (Walking Skeleton) | §5, §9, §10.2 | Annual→monthly return; cash-flow ordering; failure at first unfundable month; no negative compounding; zero spending never fails; no capital + no income fails | Within-month ordering and death timing | F-001 |
| F-009 | Monte Carlo Path Outcomes, Censoring and Success Metrics | §7.2 (censoring), §10.1–§10.4, §11 | Censored paths reported, never successes; large portfolio + zero spending solvent on all completed paths | Horizon-censoring policy and conservative denominator | F-006, F-008 |

## Risks and open questions

- SPEC §7.2's sentence "exclude unresolved paths from neither numerator nor denominator without explicit reporting" is garbled; F-009 must pin the meaning (recommended: conservative rate = successes ÷ all paths; completed-path rate = successes ÷ completed; unresolved count always reported).
- Whether to keep per-path monthly history at all — only what F-012's percentiles need (SPEC §10.4).
