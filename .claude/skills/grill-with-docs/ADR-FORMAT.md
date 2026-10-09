# Decision Record Format (docs/decisions/)

SBRetire doesn't use standalone `docs/adr/NNNN-slug.md` files. Decisions live as numbered sections inside **topic-grouped** plain-markdown files under `docs/decisions/`. Edit them directly; append, never rewrite an existing entry (supersede it with a new numbered entry that says what it replaces).

## Existing topic files — pick one, don't create a new one unless none fit

| File | Covers |
|---|---|
| `simulation-conventions.md` | Month ordering, death timing, failure/shortfall rule, censoring policy, Random Streams, CRN |
| `data-and-calibration.md` | ONS mortality file/table/mapping, inflation process and calibration data, provenance |
| `configuration.md` | YAML schema, validation strictness, survivor-factor precedence, income-stream survivor rules |
| `optimization.md` | Budget and return search bounds, tolerances, convergence, MC standard error |
| `tooling-and-process.md` | Python/uv/ruff/mypy/pytest, SDLC, backlog format |

## Template

Each file is a `# {Topic} Decisions` title, a one-paragraph scope, the list of SPEC §18 items still open in this topic, then numbered `## N. {Decision title}` sections:

```md
# {Topic} Decisions

## N. {Short title of the decision}

{1-3 sentences: what was decided.}

**Why**: {The reasoning — often the part a future reader actually needs.}

---
```

That's the whole shape — a decision can be one paragraph plus a **Why** line. The value is recording *that* a decision was made and *why*, not filling out sections. Only add a table, a "Considered Options" list, or "Enforced by" line when it adds genuine value (see `architecture.md` for worked examples of all three).

## Numbering

Within a topic file, scan for the highest existing `## N.` and increment by one. When an entry resolves an open SPEC §18 item, strike it through in the open list and point to the entry (`~~item~~ → §N`).

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
