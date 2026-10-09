# SBRetire — Claude Code guide

Monte Carlo **Retirement Sustainability Model**: the maximum sustainable household budget (today's GBP)
for two people's joint lifetimes at a target success probability.
**`docs/SPEC.md` is authoritative** — cite it as `SPEC §N`. If code and SPEC disagree, stop and ask.

## Commands

```bash
uv sync                                   # install / update env (.venv)
uv run python scripts/check.py            # full gate: ruff, ruff format --check, mypy --strict, pytest
uv run python scripts/check.py --fast     # skip @pytest.mark.slow
uv run python scripts/check.py --fix      # ruff --fix + format, then gate
uv run pytest tests/unit/test_x.py::test_y -q
uv run sbretire --config config/model.yaml --output-dir output
backlog board                             # Backlog.md kanban (or the backlog MCP tools)
```

On this Windows box `.venv/Scripts/python.exe` works in place of `uv run python`.

## Layout

```
src/sbretire/        package (config, inflation, mortality, income, spending, portfolio,
                     simulation, optimization, output — created feature by feature)
tests/unit/          fast, pure tests      tests/integration/  seeded end-to-end runs
config/              model.example.yaml (committed); model.yaml is personal and git-ignored
data/                ONS mortality + CPI inputs; provenance in data/README.md
docs/SPEC.md         specification         docs/THESAURUS.md   domain glossary
docs/epics/          epics + roadmap       docs/backlog/       design briefs
backlog/             Backlog.md tasks, milestones, decisions (backlog/docs/decisions/)
scripts/check.py     the quality gate (also CI: .github/workflows/ci.yml)
```

## Hard constraints

1. **No tax logic** in the core model (SPEC §16). No hard-coded personal assumptions — everything scenario-specific comes from YAML (SPEC §4).
2. **No network access** during a run; data files are local, versioned, hashed into run metadata (SPEC §2, §10.3).
3. **Vectorised over paths.** Simulation math is NumPy array operations over the path axis; the month loop is the only sanctioned Python loop. Memory-conscious — don't store every month × path unless reporting needs it (SPEC §10.4).
4. **Randomness is injected.** Separate `numpy.random.Generator` streams for mortality and inflation, spawned from one `SeedSequence`; common random numbers across optimization candidates (SPEC §10.3). Never call `np.random.*` global functions.
5. **Units are explicit.** Internally nominal GBP; `*_today` names mean today's GBP. Monthly vs annual is in the name or docstring.
6. **Failure semantics** per SPEC §9: depletion when balance after return + income < required spending; balance floors at zero, shortfall recorded, no negative compounding.
7. **Censored paths never count as successes**; optimization targets the conservative rate (SPEC §7.2, §11).
8. **Fail fast** on invalid config with actionable messages (SPEC §4.3).
9. **SPEC §18 decisions are recorded**, not left implicit — in `backlog/docs/decisions/` via the Backlog.md MCP.

## Code style

- Python 3.12, `from __future__ import annotations`, full type hints; `mypy --strict` clean. Use `numpy.typing.NDArray[np.float64]` for arrays.
- Frozen `dataclass`es for validated config and results; pure functions for model math.
- Names come from `docs/THESAURUS.md`; respect its Forbidden Lexicon. New domain term → `/ubiquitous-language` first.
- Tests: `test_<unit>_<scenario>_<expected>`; known-answer/closed-form cases preferred; pin seeds; `hypothesis` for invariants (e.g. dead stays dead, price index > 0).

## Workflow (see docs/project-sdlc.md)

`/decompose-spec` → `/design-brief F-NNN` → `/implement F-NNN` → `/verify F-NNN`. `/backlog-next` says what's next.
TDD per task: commit failing tests, then code + task file. Never weaken a test to go green.
Backlog tasks/milestones/decision docs are written via the Backlog.md MCP/CLI only. Use absolute dates (YYYY-MM-DD).
Stage named paths — never `git add .`. Push only when asked.

## Domain Language

See `docs/THESAURUS.md`. Key distinctions: **Path** vs **Scenario**; **Budget** (today's GBP) vs **Required Spending** (nominal);
**Conservative Success Rate** (÷ all paths) vs **Completed-Path Success Rate**; **Probability Not Depleted Yet** vs lifetime success;
"confidence level" is a simulated proportion, never a confidence interval.
