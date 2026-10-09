# Data and Calibration Decisions

Scope: ONS mortality dataset selection and mapping, inflation stochastic process and calibration data, data provenance and hashing.

SPEC §18 items open in this topic (resolve each as a numbered `## N.` entry with a **Why** line):
- ~~Exact ONS file/table and age/period mapping used for cohort mortality (SPEC §7.1).~~ → §1
- Exact inflation stochastic process and calibration dataset (SPEC §4.1, §6).
- Whether any income is indexed to a measure other than CPI (SPEC §6, §8).

## 1. Mortality: ONS 2024-based UK principal qx (`ukppp24qx.xlsx`), read as cohort q(x, b + x), age-100 rate held above 100

The mortality input is ONS "Mortality rates (qx), principal projection, UK", 2024-based (published 2026-05-15, file `ukppp24qx.xlsx`, kept unmodified in `data/raw/`). `scripts/build_ons_mortality.py` converts it to `data/ons_mortality.csv` (`sex,birth_year,age,qx`, qx as a probability) plus `data/ons_mortality.meta.json` (provenance). Construction: period sheets give q at age x in calendar year y for 1981–2074, ages 0–100; for y > 2074 the cohort sheets (ONS's projection, indexed by birth year 1981–2074) are used; the cells neither covers (ages 95–100 in 2075–2080) are interpolated log-linearly in q between (x, 2074) and (x, 1981 + x). A person aged x (completed years from their birth month) uses q(x, b + x) for that whole year of age, b = birth year. Above 100, q stays at q(100, b + 100). Sheets `males`/`females` map to `male`/`female` only. (F-007)

**Why**: SPEC §7.1 asks for the ONS 2024-based UK cohort rates, principal projection. The cohort sheets start at birth year 1981, so they omit anyone retiring now; on inspection, cohort qx(b, x) equals period qx(b + x, x) exactly on every overlapping cell, so reading the period sheets along the cohort diagonal gives ONS's cohort rates for every birth year, and the cohort sheets supply ONS's own improvement after 2074 instead of an invented one. q(x, b + x) is ONS's definition of cohort qx (aged exactly x in year b + x); looking up by the calendar year of each month was rejected because it mixes two years' rates within one year of age. Holding the age-100 rate (≈0.33–0.43) never shortens lives below ONS's last published rate, so it errs towards longevity — conservative for sustainability — and sits close to the ≈0.5 late-life plateau; q = 1 at 101 was rejected as anti-conservative, and Gompertz extrapolation with a cap as an extra unsourced parameter. Ages to 125 are available from ONS on request; a later refinement may use them.
