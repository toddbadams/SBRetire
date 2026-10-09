# Configuration Decisions

Scope: YAML schema, validation and unknown-key strictness, survivor budget factor precedence, income-stream recipient and survivor rules, household-level streams.

SPEC §18 items open in this topic (resolve each as a numbered `## N.` entry with a **Why** line):
- Behaviour of each income stream after recipient death (SPEC §8).
- Treatment of household-level income and survivor benefits (SPEC §4.2, §8).
- Survivor budget factor precedence: per-person override vs household default (SPEC §4.2, §6).
- ~~Unknown-key strictness setting (SPEC §4.3).~~ → §1

## 1. Unknown keys: `model.unknown_keys: error | warn`, default `error`

Unknown keys at any depth are rejected (reported with all other issues) unless the scenario sets `model.unknown_keys: warn`, in which case they are returned as warnings and later recorded in run metadata. (F-001)

**Why**: a typo such as `survivor_percentge` would otherwise silently fall back to a default. The setting lives in the YAML, not a CLI flag, so a scenario's behaviour is reproducible from the file alone.

## 2. Relative paths resolve against the config file's directory

Paths in the scenario (e.g. `mortality.data_file`) are resolved relative to the directory containing the YAML file, not the working directory. (F-001)

**Why**: the same scenario must load identically however the command is invoked.

## 3. Income and person date rules; exactly two people

Income `start_date` and optional `end_date` must be the 1st of a month; `end_date` is exclusive (paid through the preceding month), must be after `start_date`, and must be after `as_of_date`. A `start_date` before `as_of_date` is allowed (stream already in payment). Each date of birth must precede `as_of_date`. Exactly two people are required. (F-001)

**Why**: consistent with whole-month simulation (Simulation Conventions §1); a stream ending before the as-of date can never pay and signals an error; SPEC §2 scopes V1 to two people.
