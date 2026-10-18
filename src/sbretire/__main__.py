"""Command-line entry point: ``python -m sbretire`` / ``sbretire``.

Subcommands:
    validate  check a scenario YAML and print a one-line summary (exit 0), every issue (exit 2),
              or an unreadable-file error (exit 1)
    preview   deterministic year-by-year illustration with chosen death ages (F-015)
    run       Monte Carlo: success metrics for the configured Budget + run_metadata.json (F-009)
    portfolio import
              read the monthly account exports into one ledger, output/portfolio/ledger.csv (F-024)
    portfolio value
              value the newest month's holdings in GBP: the starting_balance line and holdings.csv (F-025)
    portfolio returns
              monthly GBP total returns from data/prices and their coverage of the holdings (F-026)
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Sequence
from pathlib import Path

from sbretire import __version__
from sbretire.config import LoadedScenario, Scenario, ScenarioError, ScenarioIssue, load_scenario
from sbretire.inflation import inflation_coverage_issues, inflation_data_file_record
from sbretire.inputs_report import format_inputs, scenario_input_rows, write_inputs_csv
from sbretire.ledger.accounts import AccountConfig, load_accounts
from sbretire.ledger.holdings import HoldingsError
from sbretire.ledger.merge import merge_exports, read_exports
from sbretire.ledger.model import UnknownTransaction
from sbretire.ledger.prices import PriceFileError
from sbretire.ledger.report import format_account_summary, reconciliation_problems, write_ledger_csv
from sbretire.ledger.returns import build_returns, format_returns, write_returns_csv, write_returns_metadata
from sbretire.ledger.valuation import (
    ValuationError,
    format_valuation,
    read_holdings,
    value_holdings,
    write_holdings_csv,
)
from sbretire.metadata import build_run_metadata, write_run_metadata
from sbretire.metrics import SuccessMetrics
from sbretire.monte_carlo import draw_random_inputs, run_monte_carlo
from sbretire.mortality import MortalityTableError, coverage_issues, load_mortality_table
from sbretire.optimization import (
    BUDGET_TOLERANCE,
    RETURN_LOWER,
    RETURN_TOLERANCE,
    RETURN_UPPER,
    BudgetResult,
    ReturnResult,
    maximum_sustainable_budgets,
    path_budget_thresholds,
    path_return_thresholds,
    required_returns,
)
from sbretire.preview import format_preview_table, run_preview, write_preview_csv
from sbretire.randomness import ResolvedSeed, resolve_seed
from sbretire.reporting import (
    annual_results,
    round_return_up,
    write_annual_results_csv,
    write_lifestyle_reserve_results_csv,
    write_lifestyle_results_csv,
    write_sustainability_results_csv,
)
from sbretire.results_guide import GuideContext, write_results_guide
from sbretire.results_json import (
    RUN_NAME_HELP,
    RUN_OUTPUT_FILES,
    build_results,
    check_run_name,
    copy_viewer,
    refresh_runs_index,
    write_results_json,
)

EXIT_OK, EXIT_FAILURE, EXIT_INVALID = 0, 1, 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sbretire",
        description="Retirement Sustainability Model (Monte Carlo). See docs/SPEC.md.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    validate = commands.add_parser("validate", help="check a scenario file without running the model")
    validate.add_argument("--config", type=Path, required=True, help="scenario YAML file")
    validate.add_argument(
        "--require-data-files", action="store_true", help="also fail if referenced data files are missing"
    )

    preview = commands.add_parser(
        "preview", help="year-by-year illustration for chosen death ages (not a sustainability result)"
    )
    preview.add_argument("--config", type=Path, required=True, help="scenario YAML file")
    preview.add_argument(
        "--death-ages",
        type=_death_ages,
        required=True,
        metavar="A,B",
        help="age at death for each person, in the config's people order (e.g. 88,92)",
    )
    preview.add_argument(
        "--output-dir", type=Path, default=Path("output"), help="where preview.csv is written"
    )

    run = commands.add_parser("run", help="run the Monte Carlo model for the configured budget")
    run.add_argument("--config", type=Path, required=True, help="scenario YAML file")
    run.add_argument(
        "--output-dir", type=Path, default=Path("output"), help="where the CSVs, guide and JSON files go"
    )
    run.add_argument(
        "--name",
        help="name this run: its files go to <output-dir>/runs/<name>/ and the runs index is refreshed "
        f"({RUN_NAME_HELP})",
    )
    run.add_argument("--overwrite", action="store_true", help="replace an existing run of the same --name")

    portfolio = commands.add_parser("portfolio", help="account exports and portfolio analysis")
    portfolio_commands = portfolio.add_subparsers(dest="portfolio_command", required=True, metavar="COMMAND")
    imports = portfolio_commands.add_parser(
        "import", help="read every month folder's transaction exports into output/portfolio/ledger.csv"
    )
    value = portfolio_commands.add_parser(
        "value", help="value the newest month folder's holdings: the household starting_balance"
    )
    returns = portfolio_commands.add_parser(
        "returns", help="monthly GBP total returns from data/prices and their coverage of the holdings"
    )
    for sub, written in ((imports, "ledger.csv"), (value, "holdings.csv"), (returns, "returns.csv")):
        sub.add_argument(
            "--root", type=Path, default=Path("data/transactions"), help="folder of <mon>-<yy> folders"
        )
        sub.add_argument(
            "--accounts", type=Path, default=Path("config/accounts.yaml"), help="accounts YAML file"
        )
        sub.add_argument(
            "--output-dir", type=Path, default=Path("output"), help=f"{written} goes to <dir>/portfolio/"
        )
    value.add_argument(
        "--usd-gbp",
        type=_positive_rate,
        metavar="RATE",
        help="GBP per USD for USD accounts (e.g. 0.7450); required when any account is in USD",
    )
    returns.add_argument(
        "--prices", type=Path, default=Path("data/prices"), help="folder with securities.yaml and price files"
    )
    returns.add_argument(
        "--months", type=_positive_months, default=60, help="monthly returns ending last month (default 60)"
    )
    returns.add_argument(
        "--usd-gbp",
        type=_positive_rate,
        metavar="RATE",
        help="GBP per USD for value shares (default: the FX price file's latest month-end)",
    )
    return parser


def _positive_months(text: str) -> int:
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError(f"expected a whole number of months, at least 1 (got {text!r})")
    return int(text)


def _positive_rate(text: str) -> float:
    try:
        rate = float(text)
    except ValueError:
        rate = math.nan
    if not math.isfinite(rate) or rate <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive number of GBP per USD (got {text!r})")
    return rate


def _death_ages(text: str) -> tuple[int, int]:
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise argparse.ArgumentTypeError(f"expected two whole-number ages like 88,92 (got {text!r})")
    return int(parts[0]), int(parts[1])


def _preview(args: argparse.Namespace, loaded: LoadedScenario) -> int:
    try:
        result = run_preview(loaded.scenario, args.death_ages)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INVALID
    print(format_preview_table(result, loaded.scenario, args.death_ages))
    csv_path = args.output_dir / "preview.csv"
    write_preview_csv(result, csv_path)
    print()
    print(f"Wrote {csv_path}")
    return EXIT_OK


def _load(config: Path, *, require_data_files: bool) -> LoadedScenario | int:
    """Load and validate, reporting problems on stderr; return an exit code on failure."""
    try:
        loaded = load_scenario(config, require_data_files=require_data_files)
    except OSError as exc:
        print(f"error: cannot read {config}: {exc.strerror or exc}", file=sys.stderr)
        return EXIT_FAILURE
    except ScenarioError as exc:
        return _report(config, exc.issues)
    for warning in loaded.warnings:
        print(f"warning: {warning.location}: {warning.message}", file=sys.stderr)
    if require_data_files:
        failed = _check_data_files(config, loaded)
        if failed is not None:
            return failed
    return loaded


def _portfolio_import(args: argparse.Namespace) -> int:
    """``sbretire portfolio import``: exit 0 clean, 1 unreadable or not reconciled, 2 invalid."""
    accounts = _load_accounts(args.accounts)
    if isinstance(accounts, int):
        return accounts
    try:
        exports = read_exports(args.root, accounts)
    except OSError as exc:
        print(f"error: cannot read {args.root}: {exc.strerror or exc}", file=sys.stderr)
        return EXIT_FAILURE
    except UnknownTransaction as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INVALID
    rows = merge_exports(exports)
    for account in accounts:
        own = [row for row in rows if row.account == account.id]
        print(format_account_summary(account, own, [e for e in exports if e.account.id == account.id]))
    ledger = args.output_dir / "portfolio" / "ledger.csv"
    write_ledger_csv(rows, ledger)
    print(f"ledger: {ledger} ({len(rows)} rows)")
    return EXIT_FAILURE if reconciliation_problems(exports) else EXIT_OK


def _portfolio_value(args: argparse.Namespace) -> int:
    """``sbretire portfolio value``: exit 0 valued, 1 unreadable, 2 invalid (export, rate or totals)."""
    accounts = _load_accounts(args.accounts)
    if isinstance(accounts, int):
        return accounts
    try:
        folder, exports = read_holdings(args.root, accounts)
        valuation = value_holdings(folder, exports, args.usd_gbp)
    except OSError as exc:
        print(f"error: cannot read {args.root}: {exc.strerror or exc}", file=sys.stderr)
        return EXIT_FAILURE
    except (HoldingsError, UnknownTransaction, ValuationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INVALID
    print(format_valuation(valuation, accounts))
    holdings = args.output_dir / "portfolio" / "holdings.csv"
    write_holdings_csv(valuation, holdings)
    print(f"holdings: {holdings} ({len(valuation.holdings)} rows)")
    return EXIT_OK


def _portfolio_returns(args: argparse.Namespace) -> int:
    """``sbretire portfolio returns``: exit 0 written (gaps reported), 1 unreadable, 2 invalid."""
    accounts = _load_accounts(args.accounts)
    if isinstance(accounts, int):
        return accounts
    securities = args.prices / "securities.yaml"
    try:
        report = build_returns(args.root, accounts, args.prices, args.months, args.usd_gbp)
    except OSError as exc:
        print(f"error: cannot read {exc.filename or args.prices}: {exc.strerror or exc}", file=sys.stderr)
        return EXIT_FAILURE
    except ScenarioError as exc:
        return _report(securities, exc.issues)
    except (HoldingsError, PriceFileError, UnknownTransaction, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INVALID
    print(format_returns(report))
    folder = args.output_dir / "portfolio"
    write_returns_csv(report, folder / "returns.csv")
    write_returns_metadata(report, folder / "returns_metadata.json")
    print(f"returns: {folder / 'returns.csv'} ({len(report.returns)} rows); metadata: returns_metadata.json")
    return EXIT_OK


def _load_accounts(path: Path) -> list[AccountConfig] | int:
    try:
        return load_accounts(path)
    except OSError as exc:
        print(f"error: cannot read {path}: {exc.strerror or exc}", file=sys.stderr)
        return EXIT_FAILURE
    except ScenarioError as exc:
        return _report(path, exc.issues)


def _report(config: Path, issues: Sequence[ScenarioIssue]) -> int:
    print(f"{config}: {len(issues)} problem(s)", file=sys.stderr)
    for issue in issues:
        print(f"  {issue.location}: {issue.message}", file=sys.stderr)
    return EXIT_INVALID


def _check_data_files(config: Path, loaded: LoadedScenario) -> int | None:
    """Load the data files and check their coverage (F-006 CPI, F-007 mortality); an exit code on failure."""
    issues = inflation_coverage_issues(loaded.scenario.inflation)
    mortality = loaded.scenario.mortality
    try:
        table = load_mortality_table(mortality.data_file, mortality)
    except MortalityTableError as exc:
        issues.extend(exc.issues)
    else:
        issues.extend(coverage_issues(table, loaded.scenario))
    return _report(config, issues) if issues else None


def _summary(config: Path, loaded: LoadedScenario) -> str:
    s = loaded.scenario
    return (
        f"OK {config} - {len(s.people)} people, {len(s.income)} income streams, "
        f"as-of {s.model.as_of_date.isoformat()}, {s.model.simulation_count} paths, "
        f"horizon {s.model.horizon_years} y"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "portfolio":
        handlers = {"import": _portfolio_import, "value": _portfolio_value, "returns": _portfolio_returns}
        return handlers[args.portfolio_command](args)
    require_data_files = args.command == "run" or getattr(args, "require_data_files", False)
    loaded = _load(args.config, require_data_files=require_data_files)
    if isinstance(loaded, int):
        return loaded
    if args.command == "validate":
        print(_summary(args.config, loaded))
        return EXIT_OK
    if args.command == "preview":
        return _preview(args, loaded)
    return _run(args, loaded)


def _run(args: argparse.Namespace, loaded: LoadedScenario) -> int:
    """The full model: inputs, summary and tables on stdout; the CSVs and run_metadata.json in --output-dir.

    Every figure comes from one set of random inputs (Common Random Numbers). The output directory is checked
    before the (long) computation so an unwritable path fails fast with exit 1.
    """
    name: str | None = args.name
    output_dir: Path = args.output_dir
    if name is not None:
        problem = check_run_name(name)
        if problem:
            print(f"error: {problem}", file=sys.stderr)
            return EXIT_INVALID
        output_dir = args.output_dir / "runs" / name
        if output_dir.exists() and not args.overwrite:
            print(
                f"error: run '{name}' already exists in {output_dir}; "
                "choose another --name or add --overwrite",
                file=sys.stderr,
            )
            return EXIT_INVALID
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot write to output directory {output_dir}: {exc.strerror or exc}", file=sys.stderr)
        return EXIT_FAILURE
    scenario = loaded.scenario
    targets = scenario.model.confidence_levels
    table = load_mortality_table(scenario.mortality.data_file, scenario.mortality)
    seed = resolve_seed(scenario.model.random_seed)
    input_rows = scenario_input_rows(scenario, seed)
    print(format_inputs(args.config, input_rows))
    print()
    inputs = draw_random_inputs(scenario, table, seed)
    result = run_monte_carlo(scenario, inputs)
    budgets = maximum_sustainable_budgets(path_budget_thresholds(scenario, inputs), targets)
    returns = required_returns(path_return_thresholds(scenario, inputs), targets)
    reserve_months = scenario.budget.end_reserve_months
    reserve_metrics, reserve_budgets = None, []
    if reserve_months > 0:
        reserve_metrics = run_monte_carlo(scenario, inputs, end_reserve_months=reserve_months).metrics
        reserve_search = path_budget_thresholds(scenario, inputs, end_reserve_months=reserve_months)
        reserve_budgets = maximum_sustainable_budgets(reserve_search, targets)
    annual = annual_results(scenario, inputs)
    records = [table.data_file_record(), inflation_data_file_record(scenario.inflation)]
    try:
        if name is not None:  # --overwrite: drop the old run's files only now the new results exist
            for file_name in RUN_OUTPUT_FILES:
                (output_dir / file_name).unlink(missing_ok=True)
        written = [
            write_inputs_csv(input_rows, output_dir / "inputs.csv"),
            write_annual_results_csv(annual, output_dir / "annual_results.csv"),
            write_sustainability_results_csv(
                result.metrics,
                scenario.portfolio.annual_return,
                returns,
                output_dir / "sustainability_results.csv",
            ),
            write_lifestyle_results_csv(budgets, output_dir / "lifestyle_results.csv"),
        ]
        if reserve_months > 0:
            written.append(
                write_lifestyle_reserve_results_csv(
                    reserve_budgets, reserve_months, output_dir / "lifestyle_reserve_results.csv"
                )
            )
        context = GuideContext(
            args.config,
            scenario,
            seed,
            input_rows,
            result.metrics,
            budgets,
            returns,
            reserve_metrics=reserve_metrics,
            reserve_budgets=reserve_budgets,
        )
        metadata = build_run_metadata(loaded, seed, records)
        results = build_results(
            context,
            annual,
            name=name,
            config_sha256=metadata.config_sha256,
            created_at=metadata.created_at,
        )
        written += [
            write_run_metadata(metadata, output_dir),
            write_results_guide(context, output_dir / "results_guide.md"),
            write_results_json(results, output_dir / "results.json"),
        ]
        if name is not None:
            written += refresh_runs_index(output_dir.parent)
            written += copy_viewer(output_dir.parent.parent)
    except OSError as exc:
        print(f"error: cannot write to output directory {output_dir}: {exc.strerror or exc}", file=sys.stderr)
        return EXIT_FAILURE
    print(format_run_summary(args.config, scenario, seed, result.metrics))
    if reserve_metrics is not None:
        print(format_reserve_line(reserve_metrics, reserve_months))
    print()
    print(format_budget_table(budgets))
    print()
    if reserve_months > 0:
        print(format_budget_table(reserve_budgets, reserve_months))
        print()
    print(format_return_table(returns))
    print()
    for path in written:
        print(f"Wrote {path}")
    return EXIT_OK


def format_return_table(results: Sequence[ReturnResult]) -> str:
    """Plain-ASCII table of required annual returns at the configured Budget (SPEC §13)."""
    budget = results[0].monthly_budget_today if results else 0.0
    runs = results[0].iterations if results else 0
    lines = [
        f"Required return for a budget of {budget:,.0f} GBP/month (fixed annual effective return; "
        f"search {RETURN_LOWER:.0%} to +{RETURN_UPPER:.0%}, "
        f"tolerance {RETURN_TOLERANCE * 100:.2f} percentage points; {runs} engine runs, same random paths):",
        f"{'target':>6}  {'return/yr':>10}  {'success +/- SE':>22}  {'unresolved':>10}  converged",
    ]
    for result in results:
        target = f"{result.target_probability:.0%}"
        if result.required_annual_return is None:
            lines.append(f"{target:>6}  {result.note}")
            continue
        assert result.estimated_success_probability is not None and result.standard_error is not None
        success = f"{result.estimated_success_probability:.2%} +/- {result.standard_error:.3%}"
        lines.append(
            f"{target:>6}  {round_return_up(result.required_annual_return):>10.2%}  {success:>22}  "
            f"{result.unresolved_fraction:>10.2%}  {'yes' if result.converged else 'no'}"
        )
        if result.note:
            lines.append(f"{'':>6}  note: {result.note}")
    lines.append("Required returns are model outputs under a fixed-return assumption, not forecasts.")
    return "\n".join(lines)


def format_reserve_line(metrics: SuccessMetrics, end_reserve_months: int) -> str:
    """Conservative Success Rate at the configured Budget under the End-of-Life Reserve (optimization §3)."""
    return (
        f"Conservative success rate leaving a {end_reserve_months}-month reserve "
        f"{metrics.conservative_success_rate:.2%} +/- {metrics.conservative_standard_error:.3%} "
        f"(also needs {end_reserve_months} x the budget, inflated, left at the second death)"
    )


def format_budget_table(results: Sequence[BudgetResult], end_reserve_months: int = 0) -> str:
    """Plain-ASCII table of Maximum Sustainable Budgets, one row per confidence level (SPEC §14).

    With ``end_reserve_months`` > 0 the table is the one leaving the End-of-Life Reserve (optimization §3).
    """
    runs = results[0].iterations if results else 0
    reserve = f" leaving a {end_reserve_months}-month reserve" if end_reserve_months else ""
    lines = [
        f"Maximum sustainable budget{reserve} (today's GBP; tolerance {BUDGET_TOLERANCE:,.0f} GBP/month; "
        f"{runs} engine runs, same random paths for every budget):",
        f"{'target':>6}  {'per month':>11}  {'per year':>12}  {'success +/- SE':>22}  "
        f"{'unresolved':>10}  converged",
    ]
    for result in results:
        target = f"{result.target_probability:.0%}"
        if result.maximum_monthly_budget_today is None:
            lines.append(f"{target:>6}  {result.note}")
            continue
        assert result.maximum_annual_budget_today is not None
        assert result.estimated_success_probability is not None and result.standard_error is not None
        success = f"{result.estimated_success_probability:.2%} +/- {result.standard_error:.3%}"
        lines.append(
            f"{target:>6}  {math.floor(result.maximum_monthly_budget_today):>11,}  "
            f"{math.floor(result.maximum_annual_budget_today):>12,}  "
            f"{success:>22}  {result.unresolved_fraction:>10.2%}  {'yes' if result.converged else 'no'}"
        )
        if result.note:
            lines.append(f"{'':>6}  note: {result.note}")
    lines.append(
        "A target's budget is the most you can spend per month (rising with inflation) while that share of "
        "simulated paths never runs out"
        + (
            f" and still holds {end_reserve_months} x that budget (inflated) when the second person dies."
            if end_reserve_months
            else "."
        )
    )
    return "\n".join(lines)


def format_run_summary(config: Path, scenario: Scenario, seed: ResolvedSeed, metrics: SuccessMetrics) -> str:
    """Plain-ASCII summary of one run (SPEC §11): counts, both rates with SE and denominator."""
    model = scenario.model
    lines = [
        f"SBRetire Monte Carlo - {config}",
        f"As-of {model.as_of_date:%Y-%m}; {metrics.n_paths:,} paths; horizon {model.horizon_years} years; "
        f"seed {seed.value} ({seed.source}).",
        f"Budget {scenario.budget.monthly_amount_today:,.0f} GBP/month in today's money "
        "(rises with inflation).",
        *(
            [
                "Spending is at least each month's income (budget.spend_at_least_income): "
                "surplus income is spent."
            ]
            if scenario.budget.spend_at_least_income
            else []
        ),
        "",
        f"Paths: {metrics.n_paths:,} = successful {metrics.n_successful:,} + failed {metrics.n_failed:,} "
        f"+ unresolved {metrics.n_unresolved:,}",
        f"Conservative success rate     {metrics.conservative_success_rate:.2%} "
        f"+/- {metrics.conservative_standard_error:.3%} (denominator: all {metrics.n_paths:,} paths)",
    ]
    if metrics.completed_success_rate is None or metrics.completed_standard_error is None:
        lines.append("Completed-path success rate   n/a (no path completed within the horizon)")
    else:
        lines.append(
            f"Completed-path success rate   {metrics.completed_success_rate:.2%} "
            f"+/- {metrics.completed_standard_error:.3%} "
            f"(denominator: {metrics.n_completed:,} completed paths)"
        )
    lines += [
        f"Unresolved (someone alive at the horizon, never ran out): {metrics.unresolved_share:.2%}",
        "",
        "Rates are simulated proportions of paths; +/- is one Monte Carlo standard error, "
        "not a confidence interval.",
        "Failed = money ran out while someone was alive. Unresolved paths never count as successes.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
