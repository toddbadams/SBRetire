---
name: backlog-next
description: Read-only. Show what to work on next from the markdown backlog — tasks in progress, awaiting verification, ready and blocked, plus the next feature on the roadmap — and offer exactly one handoff (/verify, /implement, /design-brief or /decompose-spec). Use when the user asks "what's next", "what should I work on", "show open bugs", or "backlog status".
metadata:
  version: "2.0.0"
---

# Backlog Next

Read-only. Never edits files.

1. Run `uv run python scripts/backlog_check.py --next`.
   - If it reports problems, show them and offer to fix (that is the first piece of work).
   - Otherwise it prints `IN PROGRESS`, `VERIFICATION`, `READY` (bugs first, then roadmap order), `BLOCKED (waits on …)`
     and `NEXT FEATURE` lines.
2. Show that view. For the top READY task add its brief path and one-line purpose.
3. Offer exactly one handoff, in this precedence:
   1. An `IN PROGRESS` task → resume it with `/implement <task id>`.
   2. `VERIFICATION` tasks → `/verify <feature>`.
   3. A `READY` task → `/implement <feature>`.
   4. `NEXT FEATURE` is `proposed` → `/design-brief F-NNN`.
   5. No roadmap rows at all → `/decompose-spec`.
