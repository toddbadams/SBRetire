from __future__ import annotations

from pathlib import Path

import pytest

import backlog_check

ROADMAP = """# Roadmap

| # | Feature | Epic | depends_on | Status |
|---|---|---|---|---|
| F-001 | Config | [foundations](foundations.md) | — | {s1} |
| F-002 | Engine | [engine](engine.md) | F-001 | proposed |
"""

EPIC = """---
epic: foundations
milestones:
  - {{ id: F-001, title: Config, status: {status} }}
---
# Foundations
"""

BRIEF = """---
id: F-001
type: feature
status: {brief_status}
---
# Config

## 10. Tasks

### F-001.1 Models
- **Status**: {t1}
- **Depends on**: —

Build models.

**Acceptance criteria**
- [{ac1}] Missing keys reported — `test_missing_keys`
- [{ac1}] README updated — `check: grep validate README.md`

### F-001.2 CLI
- **Status**: To Do
- **Depends on**: {dep}

**Acceptance criteria**
- [ ] Exits 2 on invalid — `test_cli_invalid`

## 11. Open Questions
"""


def make_repo(
    tmp_path: Path,
    *,
    roadmap_status: str = "briefed",
    epic_status: str = "briefed",
    brief_status: str = "planned",
    t1: str = "To Do",
    ac1: str = " ",
    dep: str = "F-001.1",
    brief: str | None = None,
) -> Path:
    epics, backlog = tmp_path / "docs" / "epics", tmp_path / "docs" / "backlog"
    epics.mkdir(parents=True)
    backlog.mkdir(parents=True)
    (epics / "roadmap.md").write_text(ROADMAP.format(s1=roadmap_status), encoding="utf-8")
    (epics / "foundations.md").write_text(EPIC.format(status=epic_status), encoding="utf-8")
    text = brief or BRIEF.format(brief_status=brief_status, t1=t1, ac1=ac1, dep=dep)
    (backlog / "feature-config-design-brief.md").write_text(text, encoding="utf-8")
    return tmp_path


def problems(root: Path, capsys: pytest.CaptureFixture[str]) -> str:
    assert backlog_check.run(root, show_next=False) == 1
    return capsys.readouterr().err


def test_valid_backlog_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert backlog_check.run(make_repo(tmp_path), show_next=False) == 0
    assert "2 features, 1 briefs, 2 tasks" in capsys.readouterr().out


def test_parse_brief_reads_status_deps_and_acs(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    issues: list[str] = []
    brief = backlog_check.parse_brief(root / "docs/backlog/feature-config-design-brief.md", root, issues)
    assert brief is not None and not issues
    first, second = brief.tasks
    assert (first.id, first.status, first.depends_on, len(first.acs)) == ("F-001.1", "To Do", (), 2)
    assert second.depends_on == ("F-001.1",)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"t1": "Doing"}, "status 'Doing' not in"),
        ({"dep": "F-001.9"}, "depends on unknown task F-001.9"),
        ({"t1": "Done"}, "status Done but not every AC is ticked"),
        ({"t1": "Done", "ac1": "x", "brief_status": "done"}, "brief is done but has tasks not Done"),
        ({"roadmap_status": "proposed", "epic_status": "proposed"}, "status must be past 'proposed'"),
        ({"epic_status": "proposed"}, "F-001 status 'proposed' != roadmap 'briefed'"),
        ({"roadmap_status": "in progress", "epic_status": "in progress"}, "not in ('proposed'"),
    ],
)
def test_inconsistencies_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], kwargs: dict[str, str], expected: str
) -> None:
    assert expected in problems(make_repo(tmp_path, **kwargs), capsys)


def test_ac_without_named_evidence_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    brief = BRIEF.format(brief_status="planned", t1="To Do", ac1=" ", dep="—").replace(
        " — `test_cli_invalid`", ""
    )
    assert "AC lacks named evidence" in problems(make_repo(tmp_path, brief=brief), capsys)


def test_task_id_must_belong_to_brief(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    brief = BRIEF.format(brief_status="planned", t1="To Do", ac1=" ", dep="—").replace("F-001.2", "F-002.1")
    assert "F-002.1: id does not belong to brief F-001" in problems(make_repo(tmp_path, brief=brief), capsys)


def test_bug_tasks_allowed_in_parent_feature_brief(tmp_path: Path) -> None:
    brief = BRIEF.format(brief_status="planned", t1="To Do", ac1=" ", dep="—").replace("F-001.2", "B-001.1")
    assert backlog_check.run(make_repo(tmp_path, brief=brief), show_next=False) == 0


def test_next_view_orders_ready_then_blocked(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert backlog_check.run(make_repo(tmp_path), show_next=True) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("READY") and "F-001.1" in lines[0]
    assert lines[1].startswith("BLOCKED") and "(waits on F-001.1)" in lines[1]
    assert lines[2].startswith("NEXT FEATURE") and "F-001" in lines[2]


def test_repository_backlog_is_valid() -> None:
    assert backlog_check.run(backlog_check.ROOT, show_next=False) == 0
