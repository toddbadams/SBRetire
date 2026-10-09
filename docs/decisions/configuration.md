# Configuration Decisions

Scope: YAML schema, validation and unknown-key strictness, survivor budget factor precedence, income-stream recipient and survivor rules, household-level streams.

SPEC §18 items open in this topic (resolve each as a numbered `## N.` entry with a **Why** line):
- ~~Behaviour of each income stream after recipient death (SPEC §8).~~ → §4
- ~~Treatment of household-level income and survivor benefits (SPEC §4.2, §8).~~ → §5
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

## 4. Income after the recipient's death; inflation linking from the As-Of month

A person-level Income Stream pays in full while its Recipient is alive (whoever else has died), × `survivor_percentage` while the Recipient is dead and the other person alive, and nothing once both are dead. A Recipient who dies before the stream's `start_date` leaves the survivor × `survivor_percentage` from `start_date`, nothing earlier. Inflation-linked streams pay `annual_amount_today × I_t / 12` with the index measured from the As-Of month — so a stream starting in a later year begins at its inflated amount; non-linked streams pay `annual_amount_today / 12` nominal for their whole life. (F-003)

**Why**: SPEC §8 applies the survivor percentage to "the otherwise applicable amount" and defines linked income as the today's-GBP amount times the cumulative index. One rule covers streams that die with their owner (`survivor_percentage: 0`, e.g. UK State Pension) and spouse pensions (> 0). Rejected: lapsing a stream whose recipient dies before it starts (wrong for DB spouse pensions), and starting a survivor pension at the death month (wrong for State-Pension-like streams unless % = 0; would need a new per-stream field). These are user-supplied assumptions, not legal eligibility rules (SPEC §2, §8).

## 5. Household Streams: `recipient: household`

An Income Stream with `recipient: household` belongs to the household rather than one person: full while both people are alive, × `survivor_percentage` while exactly one is alive. `household` is reserved — no person may use it as an `id`. (F-003)

**Why**: SPEC §4.2 asks for explicitly configured household-level income with defined survivor behaviour. Reusing `recipient` and `survivor_percentage` keeps one meaning ("what continues after a death") — 1.0 for rent, less for a reducing joint annuity. Omitting `recipient` was rejected because a forgotten field would silently become household income instead of a validation error.
