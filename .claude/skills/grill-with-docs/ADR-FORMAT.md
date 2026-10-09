# Decision Record Format (backlog/docs/decisions/)

SBRetire doesn't use standalone `docs/adr/NNNN-slug.md` files. Decisions live as numbered sections inside **topic-grouped** files under `backlog/docs/decisions/`, authored via the **Backlog.md MCP** (`mcp__backlog__document_update` to append to an existing topic file, `mcp__backlog__document_create` only when no topic file fits). Never hand-edit these files directly — same discipline as `backlog/tasks/` (CLAUDE.md: "Backlog.md MCP... Single source of truth").

## Existing topic files — pick one, don't create a new one unless none fit

| File | Covers |
|---|---|
| `doc-001 - Simulation-Conventions-Decisions.md` | Month ordering, death timing, failure/shortfall rule, censoring policy, Random Streams, CRN |
| `doc-002 - Data-and-Calibration-Decisions.md` | ONS mortality file/table/mapping, inflation process and calibration data, provenance |
| `doc-003 - Configuration-Decisions.md` | YAML schema, validation strictness, survivor-factor precedence, income-stream survivor rules |
| `doc-004 - Optimization-Decisions.md` | Budget and return search bounds, tolerances, convergence, MC standard error |
| `doc-005 - Tooling-and-Process-Decisions.md` | Python/uv/ruff/mypy/pytest, SDLC, Backlog.md conventions |

## Template

Each file starts with Backlog.md document frontmatter, then a `# {Title}` and numbered `## N. {Decision title}` sections:

```md
---
id: doc-NNN
type: other
created_date: 'YYYY-MM-DD HH:MM'
title: {Topic} Decisions
description: {One sentence describing the scope of this decision file.}
source: SPEC §N; other originating doc
---

# {Topic} Decisions

## N. {Short title of the decision}

{1-3 sentences: what was decided.}

**Why**: {The reasoning — often the part a future reader actually needs.}

---
```

That's the whole shape — a decision can be one paragraph plus a **Why** line. The value is recording *that* a decision was made and *why*, not filling out sections. Only add a table, a "Considered Options" list, or "Enforced by" line when it adds genuine value (see `architecture.md` for worked examples of all three).

## Numbering

Within a topic file, scan for the highest existing `## N.` and increment by one. `id: doc-NNN` frontmatter is assigned by the Backlog.md MCP on `document_create` — don't hand-pick it.

## When to offer a decision record

All three of these must be true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will look at the code and wonder "why on earth did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If a decision is easy to reverse, skip it. If it's not surprising, nobody will wonder why. If there was no real alternative, there's nothing to record beyond "we did the obvious thing."

### What qualifies (SBRetire-flavored)

- **SPEC §18 items.** Every "implementation decision to finalize before release" gets a numbered entry: exact ONS file and age/period mapping, valuation date and first month, inflation process and calibration set, within-month ordering and death timing, income behaviour after recipient death, censoring policy, optimization bounds/tolerances, percentile and funded-probability definitions.
- **Deliberate deviations from SPEC suggestions.** e.g. a package layout other than SPEC §3's, or a truncated-normal inflation process instead of lognormal.
- **Constraints not visible in the code.** e.g. "the mortality and inflation Random Streams are spawned from one SeedSequence so adding a component never perturbs existing draws".
- **Rejected alternatives when the rejection is non-obvious.** e.g. why failure is assessed before spending rather than on a negative closing balance.
