# docs/THESAURUS.md Format

SBRetire already has a domain glossary at `docs/THESAURUS.md`, maintained by the `/ubiquitous-language` skill. Use its entry format exactly — don't invent a parallel `CONTEXT.md` structure.

## Structure

```md
### [Term]
- **Definition**: What this concept means in the domain — one or two sentences, naming the concrete class/table/function that embodies it where useful.
- **NOT**: What this term does NOT mean (prevents confusion with similar concepts)
- **Synonyms to AVOID**: Terms that mean the same thing but must NOT be used
- **Related terms**: Other thesaurus terms this concept connects to
```

Minimal viable entry (when a full write-up isn't warranted yet):

```md
### [Term]
- **Definition**: [one sentence]
- **Synonyms to AVOID**: [list]
```

### Worked example (from the existing thesaurus)

```md
### Conservative Success Rate
- **Definition**: N_success / N_all — successful completed paths over *all* paths, treating censored paths as non-successes. The V1 optimization target (SPEC §11).
- **NOT**: *Completed-Path Success Rate* (N_success / N_completed).
- **Synonyms to AVOID**: success rate (unqualified), probability of success (unqualified)
- **Related terms**: Completed-Path Success Rate, Censored Path, Monte Carlo Standard Error
```

## Rules

- **Be opinionated.** When multiple words exist for the same concept, pick the best one and list the others under **Synonyms to AVOID**.
- **Flag conflicts explicitly.** If a term is used ambiguously in the codebase, call it out and propose a resolution.
- **Keep definitions tight.** Define what it IS, not what it does; name the concrete implementing class/table when it sharpens the definition.
- **Check the Forbidden Lexicon before naming anything new.** `docs/THESAURUS.md` carries one: `Manager`, bare `Handler` (unless subclassing a framework class), `Helper`/`Util`, `Info`/`Data` suffix, `Object`/`Obj` suffix, bare unqualified `Service`, plus the domain bans listed there (`confidence interval`, `safe withdrawal rate`, …).
- **Only include terms specific to this project's domain.** General programming concepts (arrays, RNG plumbing, CSV writing) don't belong even if the codebase uses them extensively.
- **Add `Related terms`, not a separate `## Relationships` section** — that's how the existing thesaurus links concepts; don't introduce a second linking mechanism.

## Single flat list, no bounded contexts yet

`docs/THESAURUS.md` states: "Alphabetized. Flat list — no bounded contexts yet (introduce only if polysemy in Unresolved is confirmed)." Don't propose a `CONTEXT-MAP.md`-style multi-context split unless the thesaurus's own `## Unresolved` section already flags a genuine polysemy that warrants it.

## Where to add it

Insert the new entry alphabetically into `docs/THESAURUS.md`'s `## Terms` section. If a concept can't be resolved yet, add it to `## Unresolved` with a `[WHITE-SPOT]` tag instead of forcing a name — per `/ubiquitous-language`'s workflow.
