#!/usr/bin/env python
"""Check the markdown backlog and print what to work on next.

The backlog is plain markdown (docs/project-sdlc.md §2):

* ``docs/epics/roadmap.md`` — one table row per feature: ``| F-NNN | Title | Epic | depends_on | status |``.
* ``docs/epics/<slug>.md`` — epic frontmatter ``milestones: [{id, title, status}]``.
* ``docs/backlog/*-design-brief.md`` — brief frontmatter (``id``, ``status``) and, under
  ``## 10. Tasks``, one ``### <ID> <title>`` block per task::

      ### F-001.1 Scenario field models
      - **Status**: To Do
      - **Depends on**: —            (or: F-001.1, F-002.3)

      **Acceptance criteria**
      - [ ] Missing key reports its location — `test_missing_required_field_reports_location`
      - [x] Docs updated — `check: grep -n "sbretire validate" README.md`

Usage:
    python scripts/backlog_check.py          # validate; exit 1 listing every problem
    python scripts/backlog_check.py --next   # validate, then print the next-work view
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

TASK_STATUSES = ("To Do", "In Progress", "Verification", "Done")
FEATURE_STATUSES = ("proposed", "briefed", "in-progress", "done", "superseded")
BRIEF_STATUSES = ("planned", "in-progress", "done")

_TASK_HEADING = re.compile(r"^### ((?:F|O|B)-\d{3}\.\d+) (.+?)\s*$")
_FIELD = re.compile(r"^- \*\*(Status|Depends on)\*\*: (.+?)\s*$")
_AC = re.compile(r"^- \[([ x])\] (.+?)\s*$")
_EVIDENCE = re.compile(r"`(test_\w+|check: [^`]+)`")
_ROADMAP_ROW = re.compile(r"^\| ((?:F|O)-\d{3}) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|\s*$")
_FEATURE_ID = re.compile(r"^(?:F|O)-\d{3}$")


@dataclass
class Task:
    id: str
    title: str
    brief: Path
    status: str = ""
    depends_on: tuple[str, ...] = ()
    acs: list[tuple[bool, str]] = field(default_factory=list)


@dataclass
class Brief:
    path: Path
    id: str
    status: str
    tasks: list[Task]


@dataclass
class RoadmapRow:
    id: str
    title: str
    depends_on: tuple[str, ...]
    status: str


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _frontmatter(text: str) -> dict[str, object]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    loaded = yaml.safe_load(match.group(1))
    return loaded if isinstance(loaded, dict) else {}


def _split_ids(raw: str) -> tuple[str, ...]:
    raw = raw.strip()
    if raw in ("—", "-", ""):
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _tasks_section(lines: list[str]) -> list[str]:
    start = next((i for i, line in enumerate(lines) if re.match(r"^## 10\. Tasks\b", line)), None)
    if start is None:
        return []
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start + 1 : end]


def parse_brief(path: Path, root: Path, problems: list[str]) -> Brief | None:
    text = path.read_text(encoding="utf-8")
    meta = _frontmatter(text)
    where = _rel(path, root)
    brief_id, status = str(meta.get("id", "")), str(meta.get("status", ""))
    if not brief_id:
        problems.append(f"{where}: frontmatter has no id")
        return None
    if status not in BRIEF_STATUSES:
        problems.append(f"{where}: brief status {status!r} not in {BRIEF_STATUSES}")

    tasks: list[Task] = []
    in_acs = False
    for line in _tasks_section(text.splitlines()):
        if heading := _TASK_HEADING.match(line):
            tasks.append(Task(heading.group(1), heading.group(2), path))
            in_acs = False
        elif not tasks:
            continue
        elif fld := _FIELD.match(line):
            if fld.group(1) == "Status":
                tasks[-1].status = fld.group(2)
            else:
                tasks[-1].depends_on = _split_ids(fld.group(2))
        elif line.strip() == "**Acceptance criteria**":
            in_acs = True
        elif line.startswith("**"):
            in_acs = False
        elif in_acs and (ac := _AC.match(line)):
            tasks[-1].acs.append((ac.group(1) == "x", ac.group(2)))
    return Brief(path, brief_id, status, tasks)


def parse_roadmap(path: Path) -> list[RoadmapRow]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if match := _ROADMAP_ROW.match(line):
            fid, title, _epic, deps, status = match.groups()
            rows.append(RoadmapRow(fid, title, _split_ids(deps), status))
    return rows


def _feature_of(task_id: str) -> str:
    """Roadmap row a task belongs to: F-001.2 → F-001; B-001.3 → F-001; O-002.1 → O-002."""
    prefix = task_id.split(".")[0]
    return "F" + prefix[1:] if prefix.startswith("B") else prefix


def _belongs(task_id: str, brief_id: str) -> bool:
    """F briefs hold F- and B- tasks, O briefs O- tasks, bug briefs B- tasks — same NNN."""
    allowed = {"F": "FB", "O": "O", "B": "B"}[brief_id[0]]
    return task_id[0] in allowed and task_id[2:5] == brief_id[2:5]


def check_briefs(briefs: list[Brief], root: Path, problems: list[str]) -> dict[str, Task]:
    all_tasks: dict[str, Task] = {}
    for brief in briefs:
        where = _rel(brief.path, root)
        for task in brief.tasks:
            loc = f"{where} {task.id}"
            if not _belongs(task.id, brief.id):
                problems.append(f"{loc}: id does not belong to brief {brief.id}")
            if task.id in all_tasks:
                problems.append(f"{loc}: duplicate task id (also in {_rel(all_tasks[task.id].brief, root)})")
            all_tasks[task.id] = task
            if task.status not in TASK_STATUSES:
                problems.append(f"{loc}: status {task.status!r} not in {TASK_STATUSES}")
            if not task.acs:
                problems.append(f"{loc}: no acceptance criteria")
            for _, text in task.acs:
                if not _EVIDENCE.search(text):
                    problems.append(f"{loc}: AC lacks named evidence (`test_…` or `check: …`): {text[:60]}")
            if task.status in ("Verification", "Done") and not all(done for done, _ in task.acs):
                problems.append(f"{loc}: status {task.status} but not every AC is ticked")
        statuses = {t.status for t in brief.tasks}
        if brief.status == "done" and statuses - {"Done"}:
            problems.append(f"{where}: brief is done but has tasks not Done")
    for task in all_tasks.values():
        for dep in task.depends_on:
            if dep not in all_tasks:
                problems.append(f"{_rel(task.brief, root)} {task.id}: depends on unknown task {dep}")
    return all_tasks


def check_roadmap(
    rows: list[RoadmapRow], briefs: list[Brief], epics: Iterable[Path], root: Path, problems: list[str]
) -> None:
    by_id = {row.id: row for row in rows}
    if len(by_id) != len(rows):
        problems.append("docs/epics/roadmap.md: duplicate feature rows")
    for row in rows:
        if row.status not in FEATURE_STATUSES:
            problems.append(f"roadmap {row.id}: status {row.status!r} not in {FEATURE_STATUSES}")
        for dep in row.depends_on:
            if dep not in by_id:
                problems.append(f"roadmap {row.id}: depends on unknown feature {dep}")
    for brief in briefs:
        if not _FEATURE_ID.match(brief.id):
            continue  # bug briefs live under their parent's roadmap row
        brief_row = by_id.get(brief.id)
        if brief_row is None:
            problems.append(f"{_rel(brief.path, root)}: {brief.id} has no roadmap row")
        elif brief_row.status == "proposed":
            problems.append(f"roadmap {brief.id}: brief exists, so status must be past 'proposed'")
        elif (brief.status == "done") != (brief_row.status == "done"):
            problems.append(
                f"roadmap {brief.id}: status {brief_row.status!r} != brief status {brief.status!r}"
            )
    for epic in epics:
        meta = _frontmatter(epic.read_text(encoding="utf-8"))
        milestones = meta.get("milestones")
        for item in milestones if isinstance(milestones, list) else []:
            fid, status = str(item.get("id", "")), str(item.get("status", ""))
            epic_row = by_id.get(fid)
            if epic_row is None:
                problems.append(f"{_rel(epic, root)}: {fid} not in roadmap")
            elif epic_row.status != status:
                problems.append(f"{_rel(epic, root)}: {fid} status {status!r} != roadmap {epic_row.status!r}")


def next_view(rows: list[RoadmapRow], tasks: dict[str, Task]) -> str:
    def ready(task: Task) -> bool:
        return all(tasks[d].status == "Done" for d in task.depends_on if d in tasks)

    order = {row.id: i for i, row in enumerate(rows)}

    def key(task: Task) -> tuple[int, int, str]:
        bug_first = 0 if task.id.startswith("B") else 1
        return (bug_first, order.get(_feature_of(task.id), 999), task.id)

    open_tasks = sorted((t for t in tasks.values() if t.status != "Done"), key=key)
    groups = {
        "IN PROGRESS": [t for t in open_tasks if t.status == "In Progress"],
        "VERIFICATION": [t for t in open_tasks if t.status == "Verification"],
        "READY": [t for t in open_tasks if t.status == "To Do" and ready(t)],
        "BLOCKED": [t for t in open_tasks if t.status == "To Do" and not ready(t)],
    }
    lines = []
    for name, items in groups.items():
        for task in items:
            waits = [d for d in task.depends_on if d in tasks and tasks[d].status != "Done"]
            suffix = f" (waits on {', '.join(waits)})" if name == "BLOCKED" else ""
            lines.append(f"{name:<13}{task.id} {task.title}{suffix}")
    done = {row.id: row.status for row in rows}
    candidates = [
        row
        for row in rows
        if row.status in ("proposed", "briefed") and all(done.get(d) == "done" for d in row.depends_on)
    ]
    if candidates:
        nxt = candidates[0]
        lines.append(f"{'NEXT FEATURE':<13}{nxt.id} {nxt.title} ({nxt.status})")
    return "\n".join(lines) if lines else "Nothing open."


def run(root: Path, show_next: bool) -> int:
    problems: list[str] = []
    briefs = [
        b
        for p in sorted((root / "docs" / "backlog").glob("*-design-brief.md"))
        if (b := parse_brief(p, root, problems))
    ]
    tasks = check_briefs(briefs, root, problems)
    roadmap = root / "docs" / "epics" / "roadmap.md"
    rows = parse_roadmap(roadmap) if roadmap.exists() else []
    epic_dir = root / "docs" / "epics"
    epics = [p for p in sorted(epic_dir.glob("*.md")) if p.name not in ("roadmap.md", "_TEMPLATE.md")]
    check_roadmap(rows, briefs, epics, root, problems)
    if problems:
        print("Backlog problems:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    if show_next:
        print(next_view(rows, tasks))
    else:
        print(f"Backlog OK: {len(rows)} features, {len(briefs)} briefs, {len(tasks)} tasks.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--next", action="store_true", help="print the next-work view")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    return run(args.root.resolve(), args.next)


if __name__ == "__main__":
    raise SystemExit(main())
