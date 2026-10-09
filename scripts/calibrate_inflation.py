"""Print the calibrated AR(1) lognormal inflation block for a scenario's CPI file and source period.

Usage: uv run python scripts/calibrate_inflation.py --config config/model.example.yaml
Paste the printed block over the ``inflation:`` section (rules: docs/decisions/data-and-calibration.md §2).
"""

from __future__ import annotations

import argparse
import math
import os
from collections.abc import Sequence
from pathlib import Path

from sbretire.config import load_scenario
from sbretire.inflation import calibrate_inflation


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    inflation = load_scenario(args.config).scenario.inflation
    fitted = calibrate_inflation(inflation)
    stationary = fitted.innovation_sd / math.sqrt(1 - fitted.ar1_coefficient**2)
    print(f"# AR(1) lognormal fitted to {inflation.data_file.name}, {inflation.source_period}")
    print(
        f"# median annual rate {math.expm1(fitted.log_mean):.2%}; stationary SD of log(1+pi) {stationary:.4f}"
    )
    print("inflation:")
    print(f"  source: {inflation.source}")
    print(f'  source_period: "{inflation.source_period}"')
    data_file = Path(os.path.relpath(inflation.data_file, args.config.resolve().parent)).as_posix()
    print(f"  data_file: {data_file}")
    print("  model: ar1_lognormal")
    print("  parameter_units: log_annual")
    print(f"  log_mean: {round(fitted.log_mean, 4)}")
    print(f"  ar1_coefficient: {round(fitted.ar1_coefficient, 4)}")
    print(f"  innovation_sd: {round(fitted.innovation_sd, 4)}")
    print(f"  initial_rate: {round(fitted.initial_rate, 4)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
