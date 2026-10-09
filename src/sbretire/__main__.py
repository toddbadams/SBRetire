"""Command-line entry point: ``python -m sbretire`` / ``sbretire``."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from sbretire import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sbretire",
        description="Retirement Sustainability Model (Monte Carlo). See docs/SPEC.md.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config",
        default="config/model.yaml",
        help="Path to the scenario YAML (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for CSV and run-metadata outputs (default: %(default)s)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    raise SystemExit("Simulation engine not implemented yet — see backlog/ for the build plan.")


if __name__ == "__main__":
    raise SystemExit(main())
