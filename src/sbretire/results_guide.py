"""``results_guide.md``: a plain-English guide to one run's results (F-018).

Built from the run itself — Scenario, seed, input rows, success metrics, budget and return results — so the
formulas show this run's numbers. There is no timestamp: the same run writes a byte-identical guide. Column
descriptions live in :data:`COLUMN_GUIDE`, which a test ties to the CSV column tuples.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sbretire import __version__
from sbretire.config import HOUSEHOLD, Scenario
from sbretire.inputs_report import InputRow, display_value
from sbretire.metrics import SuccessMetrics
from sbretire.optimization import (
    BUDGET_TOLERANCE,
    RETURN_LOWER,
    RETURN_TOLERANCE,
    RETURN_UPPER,
    BudgetResult,
    ReturnResult,
)
from sbretire.randomness import ResolvedSeed
from sbretire.reporting import round_return_up
from sbretire.timeline import month_start

_SURVIVAL: Final = "share of all paths"
_NOMINAL_YEAR: Final = "GBP/year, nominal"

COLUMN_GUIDE: Final[dict[str, dict[str, tuple[str, str]]]] = {
    "inputs.csv": {
        "section": ("text", "model, portfolio, budget, inflation, mortality, people, income or derived"),
        "item": ("text", "Where the value lives in the config, e.g. budget.monthly_amount_today"),
        "label": ("text", "Plain-English name"),
        "value": ("as written", "The exact value used: numbers unrounded, dates ISO, lists separated by ;"),
        "unit": (
            "text",
            "The value's unit; for run.seed, whether the seed came from the config or was generated",
        ),
    },
    "annual_results.csv": {
        "year": ("calendar year", "The row's year; the first and last rows can be partial years"),
        "months": ("count", "Simulated months in the row"),
        "probability_both_alive": (
            _SURVIVAL,
            "Both people alive at year end (the row's last simulated month)",
        ),
        "probability_person_1_alive": (_SURVIVAL, "The first person under people alive at year end"),
        "probability_person_2_alive": (_SURVIVAL, "The second person under people alive at year end"),
        "monthly_budget_today": ("GBP/month, today's money", "Your configured budget"),
        "monthly_budget_nominal_median": (
            "GBP/month, nominal",
            "Median over all paths of budget x inflation index at year end",
        ),
        "annual_budget_nominal_median": (
            _NOMINAL_YEAR,
            "Median Required Spending in the year (survivor factor applied), over paths still running in "
            "the year",
        ),
        "annual_income_median": (_NOMINAL_YEAR, "Median income received in the year, same paths"),
        "annual_net_withdrawal_median": (
            _NOMINAL_YEAR,
            "Median of spending minus income in the year, same paths",
        ),
        "portfolio_p05": (
            "GBP, nominal",
            "5th percentile of the year-end balance over paths where someone is alive",
        ),
        "portfolio_p25": ("GBP, nominal", "25th percentile of that balance (paths that ran out count as 0)"),
        "portfolio_median": ("GBP, nominal", "Median of that balance"),
        "portfolio_p75": ("GBP, nominal", "75th percentile of that balance"),
        "portfolio_p95": ("GBP, nominal", "95th percentile of that balance"),
        "probability_not_depleted_yet": (_SURVIVAL, "The money has not run out by year end"),
        "estimated_lifetime_success_rate": (
            "share",
            "Of the paths not yet out of money at year end, the share that turn out Successful",
        ),
        "completed_paths": (
            "count",
            "Paths settled by year end: the money ran out, or both people have died",
        ),
        "unresolved_paths": ("count", "All paths minus completed_paths"),
    },
    "sustainability_results.csv": {
        "monthly_budget_today": (
            "GBP/month, today's money",
            "The configured budget behind the success columns",
        ),
        "annual_return": ("annual effective rate", "The configured fixed return behind the success columns"),
        "target_probability": ("share", "Target conservative success rate for this row"),
        "estimated_success_probability": (
            "share",
            "Completed-path success rate: successful / (successful + failed)",
        ),
        "conservative_success_probability": ("share", "Conservative success rate: successful / all paths"),
        "standard_error": (
            "share",
            "Monte Carlo standard error of the conservative rate (denominator: all paths)",
        ),
        "unresolved_fraction": ("share", "Unresolved paths / all paths"),
        "required_annual_return": (
            "annual effective rate",
            "Lowest fixed return meeting the target at this budget, rounded up to 1e-6; empty if none in "
            "range",
        ),
        "return_tolerance": ("annual rate", "Search precision (0.0001 = 0.01 percentage points)"),
        "converged": ("true/false", "Whether the return search settled inside its bounds"),
        "iterations": ("count", "Engine runs used by the return search"),
        "note": ("text", "Why a row has no solution or sits at the lower bound; otherwise empty"),
    },
    "lifestyle_results.csv": {
        "target_probability": ("share", "Target conservative success rate for this row"),
        "maximum_monthly_budget_today": (
            "GBP/month, today's money",
            "Largest budget meeting the target, rounded down to 0.01; empty if infeasible",
        ),
        "maximum_annual_budget_today": ("GBP/year, today's money", "12 x the monthly figure"),
        "estimated_success_probability": (
            "share",
            "Conservative success rate at that budget, from a confirming run",
        ),
        "standard_error": ("share", "Its Monte Carlo standard error (denominator: all paths)"),
        "unresolved_fraction": (
            "share",
            "Paths never out of money with someone alive at the horizon, at that budget",
        ),
        "budget_tolerance": ("GBP/month", "Search precision (1.00)"),
        "converged": ("true/false", "Whether the search settled below its 1,000,000 GBP/month cap"),
        "iterations": ("count", "Engine runs used by the budget search"),
        "note": ("text", "Why a row is infeasible or capped; otherwise empty"),
    },
}


COLUMN_GUIDE["lifestyle_reserve_results.csv"] = {
    "end_reserve_months": (
        "months",
        "The End-of-Life Reserve R: R x the budget, inflated, must remain at the second death",
    ),
    **{
        column: (unit, meaning.replace("Conservative success rate", "Rate meeting the reserve target"))
        for column, (unit, meaning) in COLUMN_GUIDE["lifestyle_results.csv"].items()
    },
}


@dataclass(frozen=True)
class GuideContext:
    """Everything the guide reports, all from one run on one set of random inputs."""

    config: Path
    scenario: Scenario
    seed: ResolvedSeed
    input_rows: Sequence[InputRow]
    metrics: SuccessMetrics
    """At the configured Budget and return."""
    budgets: Sequence[BudgetResult]
    returns: Sequence[ReturnResult]
    reserve_metrics: SuccessMetrics | None = None
    """At the configured Budget under the End-of-Life Reserve; None when ``end_reserve_months`` is 0."""
    reserve_budgets: Sequence[BudgetResult] = ()
    """Maximum Sustainable Budgets leaving the reserve; empty when ``end_reserve_months`` is 0."""


def _money(amount: float) -> str:
    return f"{amount:,.0f}" if float(amount).is_integer() else f"{amount:,.2f}"


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _header(context: GuideContext) -> list[str]:
    model = context.scenario.model
    return [
        "# SBRetire results guide",
        "",
        f"Run of `{context.config.as_posix()}` with sbretire {__version__}: {context.metrics.n_paths:,} "
        "simulated "
        f"futures from {model.as_of_date:%Y-%m} over a {model.horizon_years}-year horizon, seed "
        f"{context.seed.value} ({context.seed.source}). Every figure comes from the same simulated futures, "
        "and "
        "rerunning the same config, seed and data files reproduces this file exactly.",
        "",
        "Rates are simulated proportions of paths. `+/-` is one Monte Carlo standard error (simulation noise "
        "only), not a confidence interval. Nothing here is financial advice or a forecast.",
        "",
    ]


def _results(context: GuideContext) -> list[str]:
    s, m = context.scenario, context.metrics
    last = month_start(s.model.as_of_date, s.model.horizon_years * 12 - 1)
    if m.completed_success_rate is None or m.completed_standard_error is None:
        completed = "n/a (no path completed within the horizon)"
    else:
        completed = f"{m.completed_success_rate:.2%} +/- {m.completed_standard_error:.3%}"
    lines = [
        "## Your results",
        "",
        f"### At your budget of {_money(s.budget.monthly_amount_today)} GBP/month (today's money) and a "
        "fixed "
        f"return of {s.portfolio.annual_return:.2%} a year",
        "",
        f"Of {m.n_paths:,} simulated futures (seed {context.seed.value}):",
        "",
        f"- **Successful: {m.n_successful:,}.** The money paid every month's spending until both of you had "
        "died.",
        f"- **Failed: {m.n_failed:,}.** The money ran out while someone was alive.",
        f"- **Unresolved: {m.n_unresolved:,}.** The money never ran out, but someone is still alive at the "
        "end "
        f"of the horizon ({last:%Y-%m}). These never count as successes.",
        "",
        f"- **Conservative success rate: {m.conservative_success_rate:.2%} +/- "
        f"{m.conservative_standard_error:.3%}** (successful / all paths). This is the figure to plan with.",
        f"- Completed-path success rate: {completed} (successful / (successful + failed)).",
        "",
        "### Maximum sustainable budget",
        "",
        "The most you can spend each month (in today's money, rising with inflation) while at least the "
        "target "
        "share of simulated futures succeeds. Rounded **down** to whole pounds.",
        "",
        *_budget_table(context.budgets),
        *_reserve_results(context),
        "",
        "### Required return at your budget",
        "",
        "The lowest fixed annual return (nominal, after fees, every year) at which each target is still met "
        "at "
        "your budget. Rounded **up** to 0.01 %. Compare it with the return you assumed: the gap is your "
        "margin.",
        "",
        "| Target | Required return a year | Success at that return | Unresolved |",
        "|---|---|---|---|",
    ]
    for found in context.returns:
        target = f"{found.target_probability:.0%}"
        if found.required_annual_return is None:
            lines.append(f"| {target} | - | {_cell(found.note)} | {found.unresolved_fraction:.2%} |")
            continue
        success = f"{found.estimated_success_probability:.2%} +/- {found.standard_error:.3%}"
        lines.append(
            f"| {target} | {round_return_up(found.required_annual_return):.2%} | {success} | "
            f"{found.unresolved_fraction:.2%} |"
        )
    lines += [line for found in context.returns if found.note and found.required_annual_return is not None
              for line in ("", f"Note ({found.target_probability:.0%}): {found.note}")]  # fmt: skip
    lines.append("")
    return lines


def _budget_table(budgets: Sequence[BudgetResult]) -> list[str]:
    lines = [
        "| Target | Per month (GBP) | Per year (GBP) | Success at that budget | Unresolved |",
        "|---|---|---|---|---|",
    ]
    for budget in budgets:
        target = f"{budget.target_probability:.0%}"
        if budget.maximum_monthly_budget_today is None or budget.maximum_annual_budget_today is None:
            lines.append(f"| {target} | - | - | {_cell(budget.note)} | {budget.unresolved_fraction:.2%} |")
            continue
        success = f"{budget.estimated_success_probability:.2%} +/- {budget.standard_error:.3%}"
        lines.append(
            f"| {target} | {math.floor(budget.maximum_monthly_budget_today):,} | "
            f"{math.floor(budget.maximum_annual_budget_today):,} | {success} | "
            f"{budget.unresolved_fraction:.2%} |"
        )
    lines += [line for budget in budgets if budget.note and budget.maximum_monthly_budget_today
              for line in ("", f"Note ({budget.target_probability:.0%}): {budget.note}")]  # fmt: skip
    return lines


def _reserve_results(context: GuideContext) -> list[str]:
    months = context.scenario.budget.end_reserve_months
    m = context.reserve_metrics
    if months == 0 or m is None:
        return []
    return [
        "",
        f"### Maximum sustainable budget leaving a {months}-month reserve",
        "",
        f"The same question with a stricter test: when the second of you dies, at least {months} x the "
        "monthly "
        "budget (in that month's money) must still be in savings. A future that ends with less counts as "
        "failed.",
        "",
        "At your budget, the conservative success rate leaving the reserve is "
        f"{m.conservative_success_rate:.2%} "
        f"+/- {m.conservative_standard_error:.3%} ({m.n_successful:,} of {m.n_paths:,} futures).",
        "",
        *_budget_table(context.reserve_budgets),
    ]


def _survivor_factor(scenario: Scenario, index: int) -> float:
    own = scenario.people[index].survivor_budget_factor
    return scenario.budget.survivor_budget_factor if own is None else own


def _spending_floor(scenario: Scenario) -> list[str]:
    if not scenario.budget.spend_at_least_income:
        return []
    return [
        "",
        "With `budget.spend_at_least_income: true`, each month's Required Spending is max(B x I_t x F_t, "
        "Y_t), "
        "where Y_t is that month's household income: income above the budget is spent, not saved. The "
        "portfolio still pays any amount by which the budget exceeds income.",
    ]


def _income_lines(scenario: Scenario) -> list[str]:
    if not scenario.income:
        return ["No income streams are configured."]
    names = {person.id: person.name for person in scenario.people}
    lines = []
    for stream in scenario.income:
        monthly = stream.annual_amount_today / 12
        indexed = (
            "x I_t (rises with inflation)" if stream.inflation_linked else "fixed in pounds (not indexed)"
        )
        until = f" until before {stream.end_date:%Y-%m}" if stream.end_date is not None else ""
        if stream.recipient == HOUSEHOLD:
            after = f"{stream.survivor_percentage:.0%} continues while one of you survives"
        else:
            after = (
                f"paid to {names[stream.recipient]}; after their death {stream.survivor_percentage:.0%} "
                "continues while the other is alive"
            )
        lines.append(
            f"- {stream.name}: {_money(stream.annual_amount_today)} / 12 = {monthly:,.2f} GBP/month in "
            "today's "
            f"money, {indexed}, from {stream.start_date:%Y-%m}{until}; {after}."
        )
    return lines


def _calculations(context: GuideContext) -> list[str]:
    s, m = context.scenario, context.metrics
    r = s.portfolio.annual_return
    monthly = (1 + r) ** (1 / 12) - 1
    inflation, mortality = s.inflation, s.mortality
    people = s.people
    budget_runs = context.budgets[0].iterations if context.budgets else 0
    return_runs = context.returns[0].iterations if context.returns else 0
    completed = "n/a (no completed paths)"
    if m.completed_success_rate is not None:
        completed = (
            f"{m.n_successful:,} / {m.n_completed:,} = {m.completed_success_rate:.2%}, SE "
            f"{m.completed_standard_error:.3%}"
        )
    first = context.budgets[0] if context.budgets else None
    example = ""
    if first is not None:
        needed = math.ceil(first.target_probability * m.n_paths)
        example = f" (for {first.target_probability:.0%}: number {needed:,} of {m.n_paths:,}, largest first)"
    return [
        "## How the figures are calculated",
        "",
        "### Each simulated month",
        "",
        "Starting in the as-of month (month 0), every path runs month by month, in this order:",
        "",
        f"1. **Return** on the opening balance at the monthly rate (1 + {r!r})^(1/12) - 1 = {monthly:.4%} "
        f"(equivalent to {r:.2%} a year).",
        "2. **Income** due that month is added.",
        "3. **Spending** due that month is paid. If the balance after return and income is less than the "
        "spending, the money has run out (Depletion): the unmet amount is recorded as the shortfall, the "
        "balance "
        "is set to 0 and the path stops. It never goes negative.",
        "",
        "A path also stops in the first month both people are dead (Household End).",
        "",
        "### Inflation",
        "",
        "Each path draws its own yearly inflation rates pi from an AR(1) lognormal process in x = log(1 + "
        "pi):",
        "",
        f"x_y = mu + phi (x_(y-1) - mu) + sigma e_y, with mu = {inflation.log_mean!r}, phi = "
        f"{inflation.ar1_coefficient!r}, sigma = {inflation.innovation_sd!r}, and e_y a standard normal "
        "draw. "
        f"The year before the as-of date had pi = {inflation.initial_rate!r}. The median long-run rate is "
        f"e^mu - 1 = {math.expm1(inflation.log_mean):.2%} a year (calibrated to {inflation.source} "
        f"{inflation.source_period}).",
        "",
        "The Inflation Index I_t starts at I_0 = 1 and compounds monthly within each simulated year k: "
        "I_t = I_(12k) x (1 + pi_k)^((t - 12k)/12).",
        "",
        "### Spending",
        "",
        "Required Spending in month t is S_t = B x I_t x F_t, with B = "
        f"{_money(s.budget.monthly_amount_today)} "
        "GBP/month (your budget in today's money) and F_t the Survivor Budget Factor:",
        "",
        "- F = 1 while both of you are alive;",
        f"- F = {_survivor_factor(s, 0):g} while only {people[0].name} is alive;",
        f"- F = {_survivor_factor(s, 1):g} while only {people[1].name} is alive;",
        f"- F = 0 once both have died. (Household default: {s.budget.survivor_budget_factor:g}; a person's "
        "own "
        "factor overrides it.)",
        *_spending_floor(s),
        "",
        "### Income",
        "",
        *_income_lines(s),
        "",
        "### Lifetimes",
        "",
        f"Each person's month of death is drawn once per path from {mortality.source} {mortality.geography} "
        f"{mortality.projection} mortality rates for their sex and birth year (cohort rate q(x, b + x) at "
        "age x). "
        "Each year's rate is spread evenly over its months, q_m = 1 - (1 - q)^(1/12), and the death month is "
        "drawn by inverse CDF of the person's survival curve. Above age 100 the age-100 rate is held. The "
        "two "
        "lifetimes are independent.",
        "",
        "### Success rates",
        "",
        "Each path is Successful (never ran out, both died within the horizon), Failed (ran out while "
        "someone was "
        "alive) or Unresolved (never ran out, someone alive at the horizon).",
        "",
        f"- Conservative success rate = successful / all paths = {m.n_successful:,} / {m.n_paths:,} = "
        f"{m.conservative_success_rate:.2%}.",
        f"- Its standard error = sqrt(p (1 - p) / N) = {m.conservative_standard_error:.3%}.",
        f"- Completed-path success rate = successful / (successful + failed) = {completed}.",
        "",
        "### Maximum sustainable budget",
        "",
        "Every candidate budget is tested on the same simulated futures (Common Random Numbers). For each "
        "path, "
        "the largest budget at which it still succeeds is found by bisection, all paths at once: from 0 up "
        "to a "
        "bound that starts at the larger of 2 x your budget and 1,000 GBP/month and doubles until every path "
        "whose household ends within the horizon fails (capped at 1,000,000 GBP/month), to within "
        f"{BUDGET_TOLERANCE:,.0f} GBP/month. This run used {budget_runs} engine runs. A target p's budget is "
        "the "
        f"ceil(p x N)-th largest path threshold{example}. One confirming run at that budget gives the "
        "success "
        "rate shown.",
        "",
        *_reserve_calculation(s),
        "### Required return",
        "",
        "For each path, the lowest fixed annual return at which it succeeds at your budget is found by "
        "bisection "
        f"between {RETURN_LOWER:.0%} and +{RETURN_UPPER:.0%} a year, to within {RETURN_TOLERANCE * 100:.2f} "
        f"percentage points, on the same simulated futures ({return_runs} engine runs). A target p's return "
        "is "
        "the ceil(p x N)-th smallest path threshold, confirmed by one run.",
        "",
        "### Annual results",
        "",
        "Each `annual_results.csv` row is a calendar year at your budget. Survival and not-depleted figures "
        "are "
        "shares of all paths at the row's last simulated month. Spending, income and net withdrawal are "
        "medians "
        "of each path's totals for the year, over paths still running in it. Portfolio percentiles cover "
        "paths "
        "where someone is alive at year end, with paths that ran out counted as 0.",
        "",
    ]


def _reserve_calculation(scenario: Scenario) -> list[str]:
    months = scenario.budget.end_reserve_months
    if months == 0:
        return []
    budget = _money(scenario.budget.monthly_amount_today)
    return [
        "### End-of-life reserve",
        "",
        f"With `budget.end_reserve_months: {months}`, a path meets the reserve target only if it is "
        "Successful "
        f"and its balance in the month the second person dies (month d) is at least {months} x B x I_d: the "
        f"budget B in today's money (at your budget, {months} x {budget} GBP) inflated to that month by the "
        "path's own Inflation Index. The full budget is used, not the survivor's reduced spending. A path "
        "that "
        "ends below it is counted as Failed; unresolved paths stay unresolved. The reserve budget table uses "
        "the same per-path search, because a higher budget never leaves more money and needs a larger "
        "reserve.",
        "",
    ]


def _assumptions(context: GuideContext) -> list[str]:
    s = context.scenario
    return [
        "## Assumptions",
        "",
        f"- **Returns:** one fixed nominal return of {s.portfolio.annual_return:.2%} a year, after fees, "
        "earned "
        "every year. No market volatility or sequence-of-returns risk.",
        f"- **Inflation:** simulated UK CPI ({s.inflation.source} {s.inflation.source_period}, AR(1) "
        "lognormal). "
        "Spending and every inflation-linked income follow the same simulated path.",
        f"- **Mortality:** {s.mortality.source} {s.mortality.geography} {s.mortality.projection} cohort "
        "rates; "
        "the two lifetimes are independent.",
        "- **Cash-flow order** each month: return, then income, then spending. Money that runs out stays at "
        "0.",
        "- **Success** means the money paid every month's spending until both people had died. Paths that "
        "reach "
        "the horizon with someone alive are unresolved and never count as successes.",
        "- **Amounts** are entered in today's money; the model works in nominal pounds internally.",
        "",
    ]


def _limitations() -> list[str]:
    return [
        "## Limitations",
        "",
        "- **Gross figures.** Every amount is gross: nothing owed on income or withdrawals is deducted "
        "(SPEC §16).",
        "- **No market risk.** The fixed return hides crashes and sequence risk; use the required-return "
        "table to "
        "stress-test it.",
        "- **Foreign income** is converted at a fixed planning exchange rate and linked to UK CPI.",
        "- **Not covered:** housing, long-term care, fees beyond the return, one-off expenses.",
        "- **Parameter uncertainty is not modelled.** The `+/-` figures measure simulation noise only, not "
        "whether the inputs are right.",
        "",
    ]


def _columns() -> list[str]:
    lines = ["## Columns", "", "Every CSV is UTF-8 with a header row; `.` decimals; no thousands separators."]
    for file_name, guide in COLUMN_GUIDE.items():
        lines += ["", f"### `{file_name}`", "", "| Column | Unit | Meaning |", "|---|---|---|"]
        lines += [f"| `{column}` | {unit} | {_cell(meaning)} |" for column, (unit, meaning) in guide.items()]
    lines.append("")
    return lines


def _inputs(context: GuideContext) -> list[str]:
    lines = [
        "## Inputs",
        "",
        "Every setting this run used (also in `inputs.csv`).",
        "",
        "| Item | Meaning | Value | Unit |",
        "|---|---|---|---|",
    ]
    for row in context.input_rows:
        shown = display_value(row)
        value = row.value if shown == row.value else f"{shown} ({row.value})"
        lines.append(f"| `{row.item}` | {_cell(row.label)} | {_cell(value)} | {_cell(row.unit)} |")
    return lines


def results_guide_markdown(context: GuideContext) -> str:
    """The whole guide as Markdown text (LF line endings, ends with a newline)."""
    lines = [
        *_header(context),
        *_results(context),
        *_calculations(context),
        *_assumptions(context),
        *_limitations(),
        *_columns(),
        *_inputs(context),
    ]
    return "\n".join(lines) + "\n"


def write_results_guide(context: GuideContext, path: Path) -> Path:
    """Write ``results_guide.md`` (UTF-8, LF)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(results_guide_markdown(context).encode("utf-8"))
    return path
