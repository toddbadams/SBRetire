---
name: grill-with-docs
description: Grilling session that challenges your plan against SBRetire's existing domain model and docs/SPEC.md, sharpens terminology, and updates project docs (docs/THESAURUS.md, docs/decisions/) inline as decisions crystallise. Use when user wants to stress-test a plan against the project's language and documented decisions.
disable-model-invocation: true
metadata:
  version: "1.0.0"
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing.

If a question can be answered by exploring the codebase, explore the codebase instead.

## Domain awareness

During codebase exploration, also read the project's existing documentation:

### File structure (SBRetire)

Single context, project-wide:

```
/
├── docs/
│   ├── SPEC.md               ← authoritative specification (cite as SPEC §N)
│   ├── THESAURUS.md          ← domain glossary, maintained by /ubiquitous-language
│   ├── epics/                ← epics + roadmap.md (the feature index)
│   ├── backlog/              ← design briefs, tasks inline
│   └── decisions/            ← decision records, one file per topic
│       ├── simulation-conventions.md
│       ├── data-and-calibration.md
│       ├── configuration.md
│       ├── optimization.md
│       └── tooling-and-process.md
```

There is no `CONTEXT.md`/`CONTEXT-MAP.md` and no `docs/adr/` in this repo — `docs/THESAURUS.md` and `docs/decisions/*.md` are the equivalents, and they already exist. Read them; don't invent parallel files.

## During the session

### Challenge against the thesaurus

When the user uses a term that conflicts with `docs/THESAURUS.md`, call it out immediately, quoting the entry. E.g. "The thesaurus defines **Conservative Success Rate** as successes over *all* paths, but you seem to mean successes over completed paths — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose the precise canonical term from the thesaurus, or flag a Forbidden Lexicon violation (`Manager`, bare `Handler`, `Helper`/`Util`, `Info`/`Data` suffix, bare `Service`). E.g. "You're saying 'scenario' — do you mean one **Path** or the whole **Scenario** YAML? The thesaurus lists 'scenario' as a synonym to avoid for Path."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios grounded in this model (the first death in the same month an Income Stream starts, a Path depleting in the month of the second death, a Censored Path at the Horizon, a negative inflation draw). Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. Check docs/SPEC.md too. If you find a contradiction, surface it: "SPEC §9 says failure is assessed before spending, but `portfolio.py` checks the closing balance — which is right?"

### Update the thesaurus inline

When a term is resolved, update `docs/THESAURUS.md` right there — don't batch these up. Use the entry format the `/ubiquitous-language` skill already defines (`### [Term]` / **Definition** / **NOT** / **Synonyms to AVOID** / **Related terms**), and follow its reuse → compose → qualify → ask order before minting anything new. Don't couple thesaurus entries to implementation details — only terms meaningful to a domain expert (retirement planner, actuary, the household) belong there.

### Offer decision records sparingly

Only offer to record a decision when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip it. When offered, record it under `docs/decisions/` — append a numbered entry to the topic file it belongs with (`simulation-conventions`, `data-and-calibration`, `configuration`, `optimization`, `tooling-and-process`; start a new topic file only if none fits) — edit the file directly, appending (never rewriting) entries. Match the existing entries' shape: `## N. {Title}` heading, 1–3 sentence decision + rationale, an explicit **Why** line when the reasoning isn't obvious from the decision itself.
