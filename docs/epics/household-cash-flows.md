---
epic: household-cash-flows
title: Household Cash Flows
status: delivered
spec_sections: [§4.2, §6, §8]
depends_on: [simulation-engine]
milestones:
  - { id: F-003, title: Income Streams, status: done }
  - { id: F-004, title: Spending with Survivor Budget Factor, status: done }
created: 2026-10-09
updated:
  - 2026-10-09: created by /decompose-spec
  - 2026-10-09: F-003 briefed
  - 2026-10-09: F-003 done
  - 2026-10-09: F-004 briefed
  - 2026-10-09: F-004 done (epic delivered)
---

# Household Cash Flows

## Goal

Model what the household receives and spends each month, given who is alive: each **Income Stream** with its start/end dates, inflation linking and **Survivor Percentage**, and **Required Spending** S_t = B_m × I_t × F_t with the **Survivor Budget Factor** after the first death.

## Scope

**In:**
- Income streams: inactive before `start_date` / after optional `end_date`; annual ÷ 12; inflation-linked streams scale with the **Inflation Index**, non-linked stay nominal (SPEC §8, §6).
- Recipient/survivor rules: survivor percentage applies only when the recipient has died and the other person is alive; explicitly configured household-level streams (SPEC §4.2, §8).
- Spending: base **Budget** in today's GBP × index × survivor factor; per-person override precedence (SPEC §4.2, §6).
- Pure, vectorised functions of (month, alive-state arrays, inflation index) consumed by the engine.

**Out:**
- Legal eligibility rules for pensions/benefits (SPEC §2 excluded; config represents user assumptions).
- Tax (SPEC §16).
- The inflation process that produces the index (F-006). These features take the index as an input and are tested with fixed indices.

## Decomposition — features and order

| F-NNN | Feature | SPEC §§ | §17 tests made passable | §18 decisions resolved | depends_on |
|---|---|---|---|---|---|
| F-003 | Income Streams | §8, §4.2 income | Inflation-linked income tracks the index; non-linked constant; start/end dates; survivor % only on recipient-death condition | Behaviour of each stream after recipient death; household-level income and survivor benefits | F-002 |
| F-004 | Spending with Survivor Budget Factor | §6, §4.2 budget | Spending changes after first death per configured factor | Survivor budget factor precedence | F-002 |

## Risks and open questions

- **Whose per-person survivor factor applies** — the survivor's or the deceased's (SPEC §4.2/§6 ambiguous)? Resolve in F-004 via `/grill-with-docs`.
- **Inflation-linked income before start** — confirm the first payment is `annual_amount_today × I(start)` (indexed from the as-of date), not `annual_amount_today` at start (F-003).
