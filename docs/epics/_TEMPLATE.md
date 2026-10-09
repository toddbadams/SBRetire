---
epic: <kebab-slug-matching-filename>
title: <Epic title>
status: proposed        # proposed | active | delivered | superseded
spec_sections: [§N, §N.M]
depends_on: []          # other epic slugs
milestones:
  - { id: F-NNN, title: <feature title>, status: proposed }   # proposed | briefed | in-progress | delivered | superseded
created: YYYY-MM-DD
updated:
  - YYYY-MM-DD: created by /decompose-spec
---

# <Epic title>

## Goal

<One paragraph: the capability this epic delivers and why it matters to the primary question in SPEC §1.1.>

## Scope

**In:** <bullets, citing SPEC §§>

**Out:** <bullets — what a reader might expect here but belongs elsewhere or is excluded by SPEC §2>

## Decomposition — features and order

| F-NNN | Feature | SPEC §§ | §17 tests made passable | §18 decisions resolved | depends_on |
|---|---|---|---|---|---|

## Risks and open questions

- <SPEC ambiguity, data-availability risk, etc. — resolve via /grill-with-docs>
