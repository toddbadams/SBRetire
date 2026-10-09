---
id: doc-003
title: Configuration Decisions
type: other
created_date: '2026-10-09 09:26'
updated_date: '2026-10-09 09:30'
---
# Configuration Decisions

Scope: YAML schema, validation and unknown-key strictness, survivor budget factor precedence, income-stream recipient and survivor rules, household-level streams.

SPEC §18 items open in this topic (resolve each as a numbered `## N.` entry with a **Why** line):
- Behaviour of each income stream after recipient death (SPEC §8).
- Treatment of household-level income and survivor benefits (SPEC §4.2, §8).
- Survivor budget factor precedence: per-person override vs household default (SPEC §4.2, §6).
- Unknown-key strictness setting (SPEC §4.3).
