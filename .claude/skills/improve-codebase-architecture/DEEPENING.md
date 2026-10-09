# Deepening

How to deepen a cluster of shallow modules safely, given its dependencies. Assumes the vocabulary in [LANGUAGE.md](LANGUAGE.md) — **module**, **interface**, **seam**, **adapter**.

## Dependency categories

When assessing a candidate for deepening, classify its dependencies. The category determines how the deepened module is tested across its seam.

### 1. In-process

Pure computation, in-memory state, no I/O. Always deepenable — merge the modules and test through the new interface directly. No adapter needed.

Most of this model lives here: inflation, mortality, income, spending and portfolio arithmetic are pure functions of arrays. Deepen freely.

### 2. Local-substitutable

Dependencies that have local test stand-ins. In this repo: the filesystem (config YAML, data CSVs, output CSVs) — the stand-in is pytest's `tmp_path` with small fixture files. Deepenable if the module accepts a path or an already-loaded table. The seam is internal; no port at the module's external interface.

### 3. Remote but owned (Ports & Adapters)

Your own services across a network boundary. SBRetire has none in V1. If one appears (e.g. a later web front-end calling the engine), define a **port** at the seam, keep the logic in one deep module and inject the transport as an **adapter**; tests use an in-memory adapter.

### 4. True external (Mock)

Things you don't control. In SBRetire the important one is **randomness**: the engine takes injected `numpy.random.Generator` Random Streams (mortality, inflation) so tests can pass deterministic fixtures (SPEC §17.2). ONS data files are versioned inputs, never fetched at run time (SPEC §2).

## Seam discipline

- **One adapter means a hypothetical seam. Two adapters means a real one.** Don't introduce a port unless at least two adapters are justified (typically production + test). A single-adapter seam is just indirection.
- **Internal seams vs external seams.** A deep module can have internal seams (private to its implementation, used by its own tests) as well as the external seam at its interface. Don't expose internal seams through the interface just because tests use them.

## Testing strategy: replace, don't layer

- Old unit tests on shallow modules become waste once tests at the deepened module's interface exist — delete them.
- Write new tests at the deepened module's interface. The **interface is the test surface**.
- Tests assert on observable outcomes through the interface, not internal state.
- Tests should survive internal refactors — they describe behaviour, not implementation. If a test has to change when the implementation changes, it's testing past the interface.
