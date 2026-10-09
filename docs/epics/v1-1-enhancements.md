---
epic: v1-1-enhancements
title: V1.1 Enhancements
status: active
spec_sections: [§1.2, §11, §12, §14, §15]
depends_on: [reporting-release]
milestones:
  - { id: F-016, title: VS Code Test Setup, status: done }
  - { id: F-017, title: Inputs Display and inputs.csv, status: done }
  - { id: F-018, title: Results Guide (columns, calculations, assumptions), status: done }
  - { id: F-019, title: End-of-Life Reserve Target, status: in-progress }
  - { id: F-020, title: Spend-At-Least-Income Option, status: in-progress }
created: 2026-10-09
updated:
  - 2026-10-09: created from the user's post-V1 requests and decisions
---

# V1.1 Enhancements

## Goal

Make results easier to trust and use after V1: run tests from VS Code, show exactly which inputs produced a run,
explain every output column, calculation and assumption next to the results, and answer two planning questions the
V1 model doesn't: "how much can we spend and still leave a reserve?" and "what if we always spend at least our income?"

## Scope

**In** (user decisions, 2026-10-09):
- F-016 VS Code test setup — done as a tooling chore (tooling-and-process §5).
- F-017 Print an inputs block at the top of `sbretire run` and write `inputs.csv`.
- F-018 Write `output/results_guide.md` each run: every column, how each figure is calculated, the assumptions,
  with the run's own numbers; generated from the code's column tuples so it cannot drift (Markdown, not HTML).
- F-019 End-of-life reserve: a Path succeeds only if, when the second person dies, the balance is at least
  12 × the monthly Budget in today's GBP inflated to that date (`budget.end_reserve_months`, default 0); a second
  maximum-budget table "leaving a 12-month reserve" beside the V1 one. Per-path threshold search still applies
  (more budget never leaves more money).
- F-020 Optional `budget.spend_at_least_income: true` (default false): each month's Required Spending is the larger
  of the Budget-based spending and that month's income, so surplus income is spent rather than saved.

**Out:**
- Changing V1 defaults: both model options are off by default, so V1 results are unchanged unless switched on.

## Decomposition — features and order

| F-NNN | Feature | SPEC §§ | Changes results? | depends_on |
|---|---|---|---|---|
| F-016 | VS Code Test Setup | — | no | F-014 |
| F-017 | Inputs Display and inputs.csv | §15 | no | F-013 |
| F-018 | Results Guide | §12–§15 | no | F-017 |
| F-019 | End-of-Life Reserve Target | §11, §14 | yes (new table; opt-in) | F-013 |
| F-020 | Spend-At-Least-Income Option | §6 | yes (opt-in) | F-013 |

## Risks and open questions

- F-020 interacts with F-010's per-path search: with spending floored at income, a higher Budget still never
  increases savings, so monotonicity should hold — the brief must verify it as F-011 did for returns.
- F-019's reserve uses the inflation index at the Household End month; an Unresolved Path (someone alive at the
  Horizon) still never counts as a success.
