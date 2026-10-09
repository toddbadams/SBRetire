---
name: backlog-add
description: Quickly capture a single bug, chore or small task into Backlog.md via the MCP — asks for the minimum fields, attaches it to the right milestone, never invents ids. Use when the user says "add a task", "log a bug", "note this for later", or finds an out-of-scope issue mid-work. For anything needing design, use /design-brief instead.
metadata:
  version: "1.0.0"
---

# Backlog Add

Capture, don't design. One task per invocation.

1. **Type** — bug / chore / task. (A new *feature* → `/decompose-spec` or `/design-brief`, not here.)
2. **Title** — imperative, thesaurus terms (`docs/THESAURUS.md`). Bugs: prefix `B-<parent F>.<M>:` — find the next M by reading existing titles for that parent.
3. **Milestone** — bugs **must** go on their parent feature's milestone. Others: the milestone they belong to, or none. Resolve the m-id from `backlog/milestones/`.
4. **Description** — what and why; for bugs the symptom + reproduction command + observed output.
5. **Acceptance criteria** — at least one objectively checkable line; bugs include "regression test `test_…` fails before the fix and passes after".
6. **Priority** (default medium), labels (`bug`/`chore` + area: `engine`, `config`, `data`, `output`, `optimization`, `tooling`, `docs`), dependencies, references (files).

Ask only for what you can't infer from the conversation. Show the draft, confirm, then `mcp__backlog__task_create`. Report the id the tool returned — never invent one. Don't commit; the Stop hook reminds to commit governance docs.
