"""Command-line entry point: ``python -m sbretire`` / ``sbretire``.

Subcommands:
    validate  check a scenario YAML and print a one-line summary (exit 0), every issue (exit 2),
              or an unreadable-file error (exit 1)
    preview   deterministic year-by-year illustration with chosen death ages (F-015)
    run       validate, then run the model (engine arrives with F-013)
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from sbretire import __version__
from sbretire.config import LoadedScenario, ScenarioError, ScenarioIssue, load_scenario
from sbretire.inflation import inflation_coverage_issues
from sbretire.mortality import MortalityTableError, coverage_issues, load_mortality_table
from sbretire.preview import format_preview_table, run_preview, write_preview_csv

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

    run = commands.add_parser("run", help="validate a scenario and run the model")
    run.add_argument("--config", type=Path, required=True, help="scenario YAML file")
    run.add_argument("--output-dir", type=Path, default=Path("output"), help="CSV output directory")
    return parser


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
    loaded = _load(args.config, require_data_files=getattr(args, "require_data_files", False))
    if isinstance(loaded, int):
        return loaded
    if args.command == "validate":
        print(_summary(args.config, loaded))
        return EXIT_OK
    if args.command == "preview":
        return _preview(args, loaded)
    print(
        "error: simulation engine not implemented yet; see docs/epics/roadmap.md for the build plan.",
        file=sys.stderr,
    )
    return EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
