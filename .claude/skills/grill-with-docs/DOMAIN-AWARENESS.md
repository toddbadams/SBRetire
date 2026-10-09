# Domain Awareness

Consumer rules for any skill that explores the SBRetire codebase. Producer rules (updating `docs/THESAURUS.md`, offering decision records) live in [SKILL.md](./SKILL.md).

## Before exploring, read these

- **`docs/THESAURUS.md`** at the repo root — the domain glossary, maintained by `/ubiquitous-language`. Includes a **Forbidden Lexicon** (`Manager`, bare `Handler`, `Helper`/`Util`, `Info`/`Data` suffix, `Object`/`Obj` suffix, bare `Service`) that new names must not violate.
- **`docs/SPEC.md`** — the authoritative specification. Cite it as `SPEC §N`.
- **`docs/decisions/*.md`** — topic-grouped decision records (`simulation-conventions`, `data-and-calibration`, `configuration`, `optimization`, `tooling-and-process`). Read the ones that touch the area you're about to work in.
- **`CLAUDE.md`** at the repo root — architecture, hard constraints, and module roster; often answers a question faster than exploring code.

This repo has no `CONTEXT.md`/`CONTEXT-MAP.md` and no `docs/adr/` — don't create them. `docs/THESAURUS.md` and `docs/decisions/` are the established equivalents and already exist; use them.

## File structure

```
/
├── CLAUDE.md
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

## Use the thesaurus's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `docs/THESAURUS.md` — e.g. **Path**, **Budget**, **Income Stream**, **Depletion**, **Censored Path**, **Conservative Success Rate**, not ad-hoc synonyms. Don't drift to terms the thesaurus's "Synonyms to AVOID" lists explicitly reject.

If the concept you need isn't in the thesaurus yet, that's a signal — either you're inventing language the project doesn't use (reconsider), or there's a real gap (note it for `/grill-with-docs` or `/ubiquitous-language` to resolve).

## Flag decision-record conflicts

If your output contradicts an existing entry in `docs/decisions/`, surface it explicitly rather than silently overriding:

> _Contradicts `simulation-conventions.md` §2 (failure assessed before spending) — but worth reopening because…_
