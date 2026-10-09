# Data and Calibration Decisions

Scope: ONS mortality dataset selection and mapping, inflation stochastic process and calibration data, data provenance and hashing.

SPEC §18 items open in this topic (resolve each as a numbered `## N.` entry with a **Why** line):
- ~~Exact ONS file/table and age/period mapping used for cohort mortality (SPEC §7.1).~~ → §1
- ~~Exact inflation stochastic process and calibration dataset (SPEC §4.1, §6).~~ → §2
- ~~Whether any income is indexed to a measure other than CPI (SPEC §6, §8).~~ → §3

## 1. Mortality: ONS 2024-based UK principal qx (`ukppp24qx.xlsx`), read as cohort q(x, b + x), age-100 rate held above 100

The mortality input is ONS "Mortality rates (qx), principal projection, UK", 2024-based (published 2026-05-15, file `ukppp24qx.xlsx`, kept unmodified in `data/raw/`). `scripts/build_ons_mortality.py` converts it to `data/ons_mortality.csv` (`sex,birth_year,age,qx`, qx as a probability) plus `data/ons_mortality.meta.json` (provenance). Construction: period sheets give q at age x in calendar year y for 1981–2074, ages 0–100; for y > 2074 the cohort sheets (ONS's projection, indexed by birth year 1981–2074) are used; the cells neither covers (ages 95–100 in 2075–2080) are interpolated log-linearly in q between (x, 2074) and (x, 1981 + x). A person aged x (completed years from their birth month) uses q(x, b + x) for that whole year of age, b = birth year. Above 100, q stays at q(100, b + 100). Sheets `males`/`females` map to `male`/`female` only. (F-007)

**Why**: SPEC §7.1 asks for the ONS 2024-based UK cohort rates, principal projection. The cohort sheets start at birth year 1981, so they omit anyone retiring now; on inspection, cohort qx(b, x) equals period qx(b + x, x) exactly on every overlapping cell, so reading the period sheets along the cohort diagonal gives ONS's cohort rates for every birth year, and the cohort sheets supply ONS's own improvement after 2074 instead of an invented one. q(x, b + x) is ONS's definition of cohort qx (aged exactly x in year b + x); looking up by the calendar year of each month was rejected because it mixes two years' rates within one year of age. Holding the age-100 rate (≈0.33–0.43) never shortens lives below ONS's last published rate, so it errs towards longevity — conservative for sustainability — and sits close to the ≈0.5 late-life plateau; q = 1 at 101 was rejected as anti-conservative, and Gompertz extrapolation with a cap as an extra unsourced parameter. Ages to 125 are available from ONS on request; a later refinement may use them.

## 2. Inflation: AR(1) lognormal in log(1 + π), calibrated to ONS CPI D7G7 1989–2025

Each Path draws one annual rate per simulated year from x_y = μ + φ (x_{y−1} − μ) + σ ε_y, x = log(1 + π), ε ~ N(0, 1), starting from x_{−1} = log(1 + `initial_rate`). Parameters are log-space (`parameter_units: log_annual`): `log_mean` μ, `ar1_coefficient` φ (−1 < φ < 1), `innovation_sd` σ ≥ 0, explicit in the YAML. Calibration data: ONS MM23 series D7G7 (CPI annual rate, all items), annual values 1989–2025, built into `data/uk_cpi.csv` by `scripts/build_uk_cpi.py` and cross-checked against the D7BT index. Estimator: μ = mean of x; φ = Σ(x_{t−1}−μ)(x_t−μ)/Σ(x_{t−1}−μ)²; σ = residual SD with n − 2 degrees of freedom → μ 0.027742, φ 0.617897, σ 0.015365 (median rate 2.81 %, stationary log SD 0.0195). `scripts/calibrate_inflation.py` prints the block; the example config carries it to 4 dp and `initial_rate` = the last observed year. (F-006)

**Why**: SPEC §6 requires a precisely defined process guaranteeing 1 + π > 0 with explicit parameter meaning; working in log(1 + π) guarantees positivity and the parameters are stated in log space, so no arithmetic-moment conversion is implied. UK inflation is persistent (φ ≈ 0.6): with a fixed nominal portfolio return, runs of high inflation (1990–91, 2022–23) are the material risk, and iid draws would roughly halve the 30-year dispersion of the price level. Rejected: iid lognormal (no persistence), iid bootstrap of 37 years (no persistence, 0 % floor), block bootstrap (few distinct blocks, block-length sensitivity). Starting from the latest observation uses current conditions; parameters live in YAML so they can be stress-tested, with a test pinning the example to the calibration.

## 3. No income is indexed to a measure other than UK CPI in V1

Every `inflation_linked: true` Income Stream follows the single simulated UK CPI path; there is no per-stream escalation rule. Income actually indexed to another measure (e.g. US Social Security's COLA, received in USD) is approximated by UK CPI at a fixed planning exchange rate, and this is documented in the README. (F-006)

**Why**: one index keeps the model and its tests simple, and a foreign COLA without exchange-rate risk would add precision that isn't real. SPEC §4.2 lists `escalation_rule` only as an optional future field; it remains a candidate later feature.
