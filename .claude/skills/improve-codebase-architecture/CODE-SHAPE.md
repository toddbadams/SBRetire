# Code Shape Priorities

When a candidate's **Solution** (Step 2) or the grilling loop (Step 3) or an [INTERFACE-DESIGN.md](INTERFACE-DESIGN.md) sub-agent sketch gets to actual code, shape it by this priority order. Highest first — when two priorities pull in opposite directions, the higher one wins.

1. **Fewer lines.** A shorter correct implementation beats a longer one. Don't pad for "clarity" a reader doesn't need.
2. **Less nesting.** Flatten conditionals and loops. Two levels of nesting is a soft ceiling — a third level is a signal to extract a guard clause or a comprehension.
3. **Fewer temporary variables.** Don't bind a value you use once. Inline it, or fold it into the expression that consumes it.
4. **Comprehensions over loops.** `for` loops that build a list/dict/set become a comprehension. Reach for a loop only when the body has a side effect (I/O, mutation of external state) that a comprehension would obscure.
5. **Built-in functions over manual logic.** `any`/`all`/`sum`/`max`/`min`/`sorted`/`itertools`/`dict.get`/`collections.Counter`/`dataclasses` over a hand-rolled equivalent. If the standard library already expresses the intent, don't re-derive it.
6. **Early returns.** Guard clauses at the top of a function over a deeply-indented single-return `if/else` chain.
7. **Function consolidation.** Merge functions that are only ever called from one place and don't earn their own name — the **deletion test** from [LANGUAGE.md](LANGUAGE.md) is the arbiter: if deleting the split reveals no real seam (only ever one caller, no independent test value), consolidate.

## The one exception: vectorised simulation math

None of the above license replacing a NumPy array operation over the path axis with a per-path Python comprehension. Simulation math (cash flows, mortality draws, inflation compounding, aggregation into percentiles) must stay vectorised over paths. If a candidate's friction is a Python loop over paths, the **Solution** is "vectorise it," not "make the loop shorter."

## Calibration

- These are Python-shape priorities, not a license for cleverness. Ruff + strict mypy still gate every change (`scripts/check.py`) — a shorter line that trips a type-ignore or turns unreadable is not a win.
- Priority 2 (less nesting) and priority 4 (comprehensions) will occasionally conflict — a comprehension nested inside another comprehension is often *less* readable than two flat statements. When they conflict, less nesting wins; don't nest comprehensions to satisfy priority 4 at the cost of priority 2.
- These priorities describe the **shape** of new/changed code. They don't override [DEEPENING.md](DEEPENING.md)'s seam discipline — a function consolidated per priority 7 must still pass the one-caller/no-test-value bar, not just "it would be fewer lines."
