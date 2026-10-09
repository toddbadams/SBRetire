"""Build data/uk_cpi.csv and its provenance sidecar from the ONS CPI D7G7 download.

One-off and reproducible; never called by a model run (SPEC §2, §19). Rules: data-and-calibration §2.

- D7G7 is the CPI annual rate (all items, %) from ONS dataset MM23; annual rows are calendar-year averages.
- Each year is cross-checked against the D7BT CPI index (annual average): the two must agree within 0.15 pp
  (the index is published to one decimal place).
- Rates are written as decimals (5.2 % -> 0.052).

Usage: uv run python scripts/build_uk_cpi.py [--raw-rate ...] [--raw-index ...] [--out-dir data]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RATE = ROOT / "data" / "raw" / "ons_cpi_d7g7.csv"
DEFAULT_INDEX = ROOT / "data" / "raw" / "ons_cpi_d7bt.csv"
DEFAULT_OUT = ROOT / "data"
TOLERANCE = 0.0015

META = {
    "source": "UK_CPI",
    "series": "D7G7",
    "title": "CPI ANNUAL RATE 00: ALL ITEMS 2015=100",
    "dataset": "MM23",
    "release_date": "2026-09-16",
    "retrieved": "2026-10-09",
    "edition": "D7G7 (released 2026-09-16)",
    "source_url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7g7/mm23",
    "raw_file": "raw/ons_cpi_d7g7.csv",
    "index_series": "D7BT",
    "index_raw_file": "raw/ons_cpi_d7bt.csv",
    "units": "annual_rate_decimal",
    "columns": "year,annual_rate",
    "build": "scripts/build_uk_cpi.py",
}


def read_annual(path: Path, cdid: str) -> dict[int, Decimal]:
    """The annual ``"YYYY","value"`` rows of an ONS timeseries CSV, after checking its CDID."""
    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    header = {row[0]: row[1] for row in rows if len(row) == 2 and not re.fullmatch(r"\d{4}", row[0])}
    if header.get("CDID") != cdid:
        raise ValueError(f"{path.name}: expected CDID {cdid}, found {header.get('CDID')!r}")
    yearly = [row for row in rows if len(row) == 2 and re.fullmatch(r"\d{4}", row[0])]
    annual = {int(year): Decimal(value) for year, value in yearly}
    years = sorted(annual)
    if years != list(range(years[0], years[-1] + 1)):
        raise ValueError(f"{path.name}: annual years are not contiguous")
    return annual


def build(raw_rate: Path, raw_index: Path) -> tuple[str, str]:
    """Return (csv text, sidecar JSON text)."""
    rates = read_annual(raw_rate, "D7G7")
    index = read_annual(raw_index, "D7BT")
    for year, percent in rates.items():
        implied = float(index[year] / index[year - 1] - 1)
        if abs(float(percent) / 100 - implied) > TOLERANCE:
            raise ValueError(f"{year}: D7G7 {percent}% disagrees with D7BT index change {implied:.4%}")
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["year", "annual_rate"])
    for year in sorted(rates):
        writer.writerow([year, repr(float(rates[year] / 100))])
    meta = {
        **META,
        "raw_sha256": hashlib.sha256(raw_rate.read_bytes()).hexdigest(),
        "index_raw_sha256": hashlib.sha256(raw_index.read_bytes()).hexdigest(),
    }
    return buffer.getvalue(), json.dumps(meta, indent=2, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-rate", type=Path, default=DEFAULT_RATE)
    parser.add_argument("--raw-index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    csv_text, meta_text = build(args.raw_rate, args.raw_index)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "uk_cpi.csv").write_text(csv_text, encoding="utf-8", newline="\n")
    (args.out_dir / "uk_cpi.meta.json").write_text(meta_text, encoding="utf-8", newline="\n")
    print(f"Wrote {args.out_dir / 'uk_cpi.csv'} ({csv_text.count(chr(10)) - 1} years)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
