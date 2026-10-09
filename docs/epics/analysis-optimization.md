---
epic: analysis-optimization
title: Analysis and Optimization
status: delivered
spec_sections: [§1.2, §10.3, §11, §13, §14]
depends_on: [simulation-engine]
milestones:
  - { id: F-010, title: Maximum Sustainable Budget Optimization, status: done }
  - { id: F-011, title: Return Search, status: done }
created: 2026-10-09
updated:
  - 2026-10-09: created by /decompose-spec
---

# Analysis and Optimization

## Goal

Answer the headline questions: the **Maximum Sustainable Budget** at each **Confidence Level** (SPEC §14) and the minimum fixed return needed for a given **Budget** (**Return Search**, SPEC §13) — both with **Common Random Numbers**, explicit bounds and tolerances, and reported convergence and Monte Carlo uncertainty.

## Scope

**In:**
- Bisection over the budget targeting the **Conservative Success Rate**; feasibility check of bounds and a documented expansion strategy; currency tolerance; convergence status and iteration count; MC standard error at the selected budget (SPEC §14).
- Bracketed root-find over annual effective return; bounds, tolerance, no-solution behaviour; empirical monotonicity check for the chosen cash-flow convention (SPEC §13).
- One set of mortality/inflation draws reused across every candidate (SPEC §10.3).

**Out:**
- Writing the result CSVs (F-013).
- Optimizing anything other than budget and return (e.g. survivor factor) — not in SPEC.

## Decomposition — features and order

| F-NNN | Feature | SPEC §§ | §17 tests made passable | §18 decisions resolved | depends_on |
|---|---|---|---|---|---|
| F-010 | Maximum Sustainable Budget Optimization | §14, §10.3 | CRN reused across candidate budgets; budget optimization returns a feasible budget within tolerance on a small deterministic fixture | Budget bounds, expansion strategy, tolerance | F-009 |
| F-011 | Return Search | §13 | CRN reused across candidate returns; return search converges to a bracketed result or clearly reports no solution | Return bounds and tolerance | F-010 |

## Risks and open questions

- With CRN the success rate is a step function of the budget; bisection must terminate on the currency tolerance, not on equality of the rate.
- Cost: each candidate re-runs the engine over N paths. F-010 should measure and, if needed, cache the stochastic draws rather than regenerate them.
