---
id: doc-005
title: Tooling and Process Decisions
type: other
created_date: '2026-10-09 09:26'
updated_date: '2026-10-09 09:30'
---
# Tooling and Process Decisions

Scope: language/toolchain, repository layout, quality gate, task tracking and SDLC conventions.

## 1. Python 3.12 + uv, src-layout package `sbretire`

The model is a single package `src/sbretire/` managed with uv (`pyproject.toml` + `uv.lock`), exposing a `sbretire` console script instead of SPEC §3's suggested top-level `run.py` + `requirements.txt`. Module responsibilities follow SPEC §3 (config, inflation, mortality, income, spending, portfolio, simulation, optimization, output).

**Why**: SPEC §3 permits a different layout if module responsibilities stay clear; a src-layout package with a lockfile gives reproducible environments (SPEC §10.3 requires identical results in the supported environment) and prevents tests importing from the working directory by accident.

## 2. One quality gate: `scripts/check.py`

ruff lint, ruff format check, `mypy --strict`, pytest — the same script runs locally, in the Backlog definition of done, and in GitHub Actions CI. A Claude Code PostToolUse hook ruff-checks each edited Python file.

**Why**: a single command removes drift between what agents run, what the DoD claims, and what CI enforces.

## 3. SDLC and tracking adapted from SBFoundation

Backlog.md (MCP) tracks milestones/tasks/decisions; SPEC → epics → F-milestones → briefs → tasks via the `/decompose-spec`, `/design-brief`, `/implement`, `/verify` skills. See `docs/project-sdlc.md`.

**Why**: reuses a workflow the owner already operates in SBFoundation, slimmed of its production-pipeline coupling.
