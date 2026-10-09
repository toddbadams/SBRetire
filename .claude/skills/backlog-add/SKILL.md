---
name: backlog-add
description: Quickly capture a single bug, chore or small task into the markdown backlog — appends a task block to the right design brief with the next free id. Use when the user says "add a task", "log a bug", "note this for later", or finds an out-of-scope issue mid-work. For anything needing design, use /design-brief instead.
metadata:
  version: "2.0.0"
---

# Backlog Add

Capture, don't design. One task per invocation. Format: `docs/project-sdlc.md` §2.

1. **Type** — bug / chore / task. A new *feature* → `/decompose-spec` or `/design-brief`, not here.
2. **Home brief** — the feature it belongs to. Bugs go in their parent feature's brief (or its bugfix brief). If that
   feature has no brief yet, stop: say it should be captured during `/design-brief F-NNN`, and add a bullet to the
   brief-less feature's epic `## Risks and open questions` instead.
3. **Id** — bug: `B-<parent NNN>.<N>` with N = highest existing `B-<NNN>.*` across `docs/backlog/` + 1; otherwise the
   brief's next `F-NNN.N`. Never reuse an id.
4. **Title** — imperative, thesaurus terms (`docs/THESAURUS.md`).
5. **Description** — what and why; for bugs the symptom, reproduction command and observed output.
6. **Acceptance criteria** — at least one, each with named evidence; bugs include
   "regression test `test_…` fails before the fix and passes after".
7. **Depends on** — `—` or task ids.

Ask only for what you can't infer from the conversation. Show the draft block; on confirmation append it to the end of
the brief's `## 10. Tasks` with `- **Status**: To Do`. If the brief's feature was `done`, set brief `status:
in-progress` and roadmap/epic status `in-progress`. Run `uv run python scripts/backlog_check.py`. Don't commit unless
asked.
