---
name: backlog-next
description: Read-only. Show what to work on next — open bugs and ready tasks ranked READY / BLOCKED, plus the next feature on the roadmap — and offer exactly one handoff (/design-brief, /implement or /verify). Use when the user asks "what's next", "what should I work on", "show open bugs", or "backlog status".
metadata:
  version: "1.0.0"
---

# Backlog Next

Read-only. Never edits tasks.

## Step 1 — Load

1. Read all `backlog/tasks/*.md` frontmatter (id, title, status, milestone, labels, priority, dependencies). `dependencies:` may be inline or a block list. A dependency id may live in `backlog/completed/` or `backlog/archive/` — treat those as satisfied.
2. Read `docs/epics/roadmap.md` (feature order and status) and `backlog/milestones/*.md` (m-id → F-NNN title).

## Step 2 — Classify open work (status To Do / In Progress)

- **READY** — all dependencies Done.
- **BLOCKED** — a dependency not Done (name it).
- **Bugs first**: label `bug` or `B-NNN.M` in the title rank above features at equal priority.
- Rank: In Progress first → bugs → priority (high > medium > low) → roadmap order of the milestone → id.

Also count tasks in **Verification** (waiting for `/verify`).

## Step 3 — Report

```
IN PROGRESS   TASK-… title (F-NNN)
READY         TASK-… title (F-NNN, priority)     ← top 5
BLOCKED       TASK-… title — waits on TASK-…
VERIFICATION  n tasks across F-…
NEXT FEATURE  F-NNN <title> — roadmap status (proposed / briefed)
```

## Step 4 — One handoff

Offer exactly one, in this precedence:
1. Verification tasks exist → `/verify <milestone>`.
2. A READY task on a briefed milestone → `/implement <milestone>`.
3. A bug without a brief → `/design-brief` (Bug, parent F-NNN).
4. Next roadmap feature not yet briefed → `/design-brief F-NNN`.
5. No roadmap yet → `/decompose-spec`.
