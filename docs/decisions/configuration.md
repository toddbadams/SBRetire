# Configuration Decisions

Scope: YAML schema, validation and unknown-key strictness, survivor budget factor precedence, income-stream recipient and survivor rules, household-level streams.

SPEC §18 items open in this topic (resolve each as a numbered `## N.` entry with a **Why** line):
- ~~Behaviour of each income stream after recipient death (SPEC §8).~~ → §4
- ~~Treatment of household-level income and survivor benefits (SPEC §4.2, §8).~~ → §5
- ~~Survivor budget factor precedence: per-person override vs household default (SPEC §4.2, §6).~~ → §6
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

## 6. Survivor Budget Factor precedence: the survivor's own factor, else the household default

While exactly one person is alive, Required Spending is the Budget × I_t × the factor of the person still alive: their `people[].survivor_budget_factor` if set, otherwise `budget.survivor_budget_factor`. While both are alive the factor is 1. (F-004)

**Why**: spending after a death is the survivor's lifestyle, so the person living on owns the number — "my share of the joint budget when I'm the one left". It allows different factors depending on who survives. Using the deceased's factor was rejected as describing someone else's spending; ignoring per-person factors was rejected because SPEC §4.2 lists them.

## 7. Config Hash: SHA-256 of the canonical validated Scenario, without the data-file path

`config_sha256` is the SHA-256 of the validated `Scenario` serialised as canonical JSON (`model_dump(mode="json")`, sorted keys, no whitespace) with the data-file paths (`mortality.data_file`, and `inflation.data_file` from F-006) removed. Data files are hashed separately by content and recorded in Run Metadata. (F-005)

**Why**: the hash should change exactly when the model's inputs change. Comments, key order and YAML formatting don't change results, so they must not change the hash; the resolved `data_file` is an absolute, machine-specific path, so including it would make the same config hash differently on two machines. Hashing raw YAML bytes was rejected (a comment edit looks like a new config); recording both hashes was rejected as two numbers to explain for no extra protection.

## 8. `random_seed: null` generates a 128-bit seed and records it

When `model.random_seed` is `null`, the run seeds from `numpy.random.SeedSequence().entropy` (128 bits of OS entropy) and records it in Run Metadata with `seed_source: "generated"`; pasting that number into `random_seed` reproduces the run. (F-005)

**Why**: SPEC §4.2 allows `null` but requires the generated seed to be recorded. NumPy's own entropy makes collisions between runs practically impossible, and YAML/pydantic accept integers of any size. A shorter 63-bit seed was considered for readability; forbidding `null` was rejected as contradicting SPEC §4.2.

## 9. `budget.spend_at_least_income`: optional floor of Required Spending at the month's income, default off

With `budget.spend_at_least_income: true`, each month's Required Spending is max(B × I_t × F_t, Y_t), where Y_t is that month's household income on the Path (every stream, survivor shares applied); both are 0 once both people have died. The floor is applied in `ScenarioCashFlows.spending`, so the Monte Carlo run, both searches, the annual results and `preview` use the same Required Spending. The budget search stays valid (Required Spending is non-decreasing in the Budget) and the return search is unaffected (spending does not depend on the return); a test verifies budget monotonicity with the option on. `annual_budget_nominal_median` includes the top-up; the End-of-Life Reserve (optimization §3) still uses the Budget. Default `false` keeps V1 behaviour, and the option is left out of the Config Hash at its default (§7). (F-020)

**Why**: the user asked to model a household that spends at least its income — option (a), "spend all income" — instead of V1's implicit saving of surplus income. A per-month floor is the direct reading, needs no new state, and keeps one definition of Required Spending everywhere.
