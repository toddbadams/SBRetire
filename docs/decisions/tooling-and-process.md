# Tooling and Process Decisions

Scope: language/toolchain, repository layout, quality gate, task tracking and SDLC conventions.

## 1. Python 3.12 + uv, src-layout package `sbretire`

The model is a single package `src/sbretire/` managed with uv (`pyproject.toml` + `uv.lock`), exposing a `sbretire` console script instead of SPEC §3's suggested top-level `run.py` + `requirements.txt`. Module responsibilities follow SPEC §3 (config, inflation, mortality, income, spending, portfolio, simulation, optimization, output).

**Why**: SPEC §3 permits a different layout if module responsibilities stay clear; a src-layout package with a lockfile gives reproducible environments (SPEC §10.3 requires identical results in the supported environment) and prevents tests importing from the working directory by accident.

## 2. One quality gate: `scripts/check.py`

ruff lint, ruff format check, `mypy --strict`, pytest — the same script runs locally, in the Backlog definition of done, and in GitHub Actions CI. A Claude Code PostToolUse hook ruff-checks each edited Python file.

**Why**: a single command removes drift between what agents run, what the DoD claims, and what CI enforces.

## 3. SDLC and tracking adapted from SBFoundation

_Superseded by §4 for the tracking tool (2026-10-09); the skill flow stands._

Backlog.md (MCP) tracks milestones/tasks/decisions; SPEC → epics → F-milestones → briefs → tasks via the `/decompose-spec`, `/design-brief`, `/implement`, `/verify` skills. See `docs/project-sdlc.md`.

**Why**: reuses a workflow the owner already operates in SBFoundation, slimmed of its production-pipeline coupling.

## 4. Markdown-only backlog; Backlog.md dropped

Work is tracked in plain markdown: `docs/epics/roadmap.md` indexes features, each feature's design brief (`docs/backlog/*-design-brief.md`) holds its tasks inline under `## 10. Tasks` with ids `F-NNN.N` (bugs `B-NNN.N`), and decisions live in `docs/decisions/`. `scripts/backlog_check.py` (run by `scripts/check.py`) enforces the format and prints the next-work view. (2026-10-09)

**Why**: at ~14 features and one developer, Backlog.md's CLI/MCP added cost without benefit — two id schemes per feature (`F-001` vs `m-0`), an MCP server that resolved to another repository's backlog, and CLI writes truncated by the Windows shell. Feature-scoped ids need no global counter, and one file per feature keeps a task next to its design.

## 5. Shared VS Code workspace settings; test helpers are modules, never imported test files

`.vscode/settings.json`, `extensions.json` and `launch.json` are committed (the rest of `.vscode/` stays ignored). They select the project interpreter `.venv\Scripts\python.exe`, enable pytest with the `pyproject.toml` configuration from the workspace root, add `src`, `scripts` and `tests/unit` to the editor's import paths, use ruff for formatting (line length from `pyproject.toml`) and provide debug configurations for tests and `sbretire run`. Fixtures shared between test files live in helper modules (`scenario_helpers`, `mortality_fixtures`, `annual_fixtures`, `cash_flow_doubles`); a test file never imports another test file. (F-016 chore, 2026-10-09)

**Why**: the suite passed from the command line but VS Code had no interpreter or test configuration, and one test file imported another, which IDE discovery handles poorly. Committing the workspace settings makes the Testing panel work on a fresh clone without per-machine setup; personal preferences remain in user settings.
