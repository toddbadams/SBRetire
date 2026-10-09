---
name: improve-codebase-architecture
description: Find deepening opportunities in the SBRetire codebase, informed by the domain language in docs/THESAURUS.md and the decisions in backlog/docs/decisions/. Use when the user wants to improve architecture, find refactoring opportunities, consolidate tightly-coupled modules, or make a codebase more testable and AI-navigable.
metadata:
  version: "1.0.0"
---

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability.

## Glossary

Use these terms exactly in every suggestion. Consistent language is the point — don't drift into "component," "service," "API," or "boundary." Full definitions in [LANGUAGE.md](LANGUAGE.md).

- **Module** — anything with an interface and an implementation (function, class, package, slice).
- **Interface** — everything a caller must know to use the module: types, invariants, error modes, ordering, config. Not just the type signature.
- **Implementation** — the code inside.
- **Depth** — leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation.
- **Seam** — where an interface lives; a place behaviour can be altered without editing in place. (Use this, not "boundary.")
- **Adapter** — a concrete thing satisfying an interface at a seam.
- **Leverage** — what callers get from depth.
- **Locality** — what maintainers get from depth: change, bugs, knowledge concentrated in one place.

Key principles (see [LANGUAGE.md](LANGUAGE.md) for the full list):

- **Deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **The interface is the test surface.**
- **One adapter = hypothetical seam. Two adapters = real seam.**

This skill is _informed_ by the project's domain model. The domain language gives names to good seams; decision records (`backlog/docs/decisions/`) record decisions the skill should not re-litigate.

## Project conventions (SBRetire)

- **Domain glossary** = `docs/THESAURUS.md`, maintained by `/ubiquitous-language` — not a generic `CONTEXT.md`. Read it before naming anything; it also carries the **Forbidden Lexicon** (`Manager`, bare `Handler`, `Helper`/`Util`, `Info`/`Data` suffix, `Object`/`Obj` suffix, bare unqualified `Service`) — a deepened module's name must not violate it.
- **Decision records** = `backlog/docs/decisions/*.md` (topic-grouped: `Simulation-Conventions-Decisions`, `Data-and-Calibration-Decisions`, `Configuration-Decisions`, `Optimization-Decisions`, `Tooling-and-Process-Decisions`), authored via the Backlog.md MCP — not standalone numbered ADRs.
- **Simulation math stays vectorised in NumPy over the path axis** (CLAUDE.md, Hard constraints). A per-path Python loop doing what an array operation should do is not a deepening candidate to make terser — the Solution is "vectorise it over paths". The month loop itself is the one sanctioned Python loop.
- **Code-shape priorities** for any proposed implementation (Step 2 solutions, Step 3 grilling loop, interface sketches) — see [CODE-SHAPE.md](CODE-SHAPE.md).

## Process

### 1. Explore

Before exploring, follow [../grill-with-docs/DOMAIN-AWARENESS.md](../grill-with-docs/DOMAIN-AWARENESS.md) — read `docs/THESAURUS.md` and relevant `backlog/docs/decisions/*.md` entries first.

Then use the Agent tool with `subagent_type=Explore` to walk the codebase. Don't follow rigid heuristics — explore organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow: would deleting it concentrate complexity, or just move it? A "yes, concentrates" is the signal you want.

### 2. Present candidates

Present a numbered list of deepening opportunities. For each candidate:

- **Files** — which files/modules are involved
- **Problem** — why the current architecture is causing friction
- **Solution** — plain English description of what would change, shaped by [CODE-SHAPE.md](CODE-SHAPE.md)'s priorities (fewer lines, less nesting, fewer temporaries, comprehensions/built-ins over manual logic, early returns, function consolidation) — unless the friction is a per-path Python loop, which should be vectorised over paths, not made terser
- **Benefits** — explained in terms of locality and leverage, and also in how tests would improve

**Use `docs/THESAURUS.md` vocabulary for the domain, and [LANGUAGE.md](LANGUAGE.md) vocabulary for the architecture.** If the thesaurus defines **Income Stream**, talk about "the Income Stream module" — not "the pension calculator," and not "the income service." Propose solution names that pass the Forbidden Lexicon check up front — don't propose `SimulationManager` or `MortalityHelper` and expect the grilling loop to fix it later.

**Decision-record conflicts**: if a candidate contradicts an entry in `backlog/docs/decisions/`, only surface it when the friction is real enough to warrant revisiting the decision. Mark it clearly (e.g. _"contradicts `Simulation-Conventions-Decisions` §2 (failure assessed before spending) — but worth reopening because…"_). Don't list every theoretical refactor a decision record forbids.

Do NOT propose interfaces yet. Ask the user: "Which of these would you like to explore?"

### 3. Grilling loop

Once the user picks a candidate, drop into a grilling conversation. Walk the design tree with them — constraints, dependencies, the shape of the deepened module, what sits behind the seam, what tests survive.

Side effects happen inline as decisions crystallize:

- **Naming a deepened module after a concept not in `docs/THESAURUS.md`?** Run it past the Forbidden Lexicon first, then add the term — same discipline as `/grill-with-docs` (see [CONTEXT-FORMAT.md](../grill-with-docs/CONTEXT-FORMAT.md), which documents the thesaurus's actual entry format). Insert alphabetically into the `## Terms` section; it already exists, don't create a parallel file.
- **Sharpening a fuzzy term during the conversation?** Update `docs/THESAURUS.md` right there.
- **User rejects the candidate with a load-bearing reason?** Offer a decision record, framed as: _"Want me to record this in `backlog/docs/decisions/` so future architecture reviews don't re-suggest it?"_ Only offer when the reason would actually be needed by a future explorer to avoid re-suggesting the same thing — skip ephemeral reasons ("not worth it right now") and self-evident ones. See [ADR-FORMAT.md](../grill-with-docs/ADR-FORMAT.md) for which topic file it belongs in and how to append via the Backlog.md MCP.
- **Want to explore alternative interfaces for the deepened module?** See [INTERFACE-DESIGN.md](INTERFACE-DESIGN.md) — each candidate interface should also be checked against [CODE-SHAPE.md](CODE-SHAPE.md).
