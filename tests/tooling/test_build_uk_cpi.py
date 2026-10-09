"""F-006.1 — ONS CPI D7G7 → data/uk_cpi.csv + sidecar (F-006 brief §2 #1; data-and-calibration §2)."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import build_uk_cpi

ROOT = Path(__file__).resolve().parents[2]
RAW_RATE = ROOT / "data" / "raw" / "ons_cpi_d7g7.csv"
RAW_INDEX = ROOT / "data" / "raw" / "ons_cpi_d7bt.csv"
CSV_PATH = ROOT / "data" / "uk_cpi.csv"
META_PATH = ROOT / "data" / "uk_cpi.meta.json"


def _committed() -> dict[int, float]:
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        return {int(row["year"]): float(row["annual_rate"]) for row in csv.DictReader(handle)}


def _raw_annual(path: Path) -> dict[int, float]:
    """Independent read of an ONS timeseries CSV: the annual rows look like "1989","5.2"."""
    out: dict[int, float] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) == 2 and re.fullmatch(r"\d{4}", row[0]):
                out[int(row[0])] = float(row[1])
    return out


def test_build_uk_cpi_reproduces_committed_files(tmp_path: Path) -> None:
    build_uk_cpi.main(
        ["--raw-rate", str(RAW_RATE), "--raw-index", str(RAW_INDEX), "--out-dir", str(tmp_path)]
    )
    assert (tmp_path / "uk_cpi.csv").read_bytes() == CSV_PATH.read_bytes()
    assert (tmp_path / "uk_cpi.meta.json").read_bytes() == META_PATH.read_bytes()


def test_uk_cpi_known_values() -> None:
    text = CSV_PATH.read_bytes()
    assert text.startswith(b"year,annual_rate\n")
    assert b"\r" not in text
    rates = _committed()
    assert list(rates) == list(range(1989, 2026))
    assert rates[1989] == 0.052
    assert rates[2015] == 0.0
    assert rates[2022] == 0.091
    assert rates[2025] == 0.034
    raw = _raw_annual(RAW_RATE)
    assert all(rates[year] == round(raw[year] / 100, 6) for year in rates)


def test_uk_cpi_agrees_with_index() -> None:
    rates = _committed()
    index = _raw_annual(RAW_INDEX)
    for year, rate in rates.items():
        assert abs(rate - (index[year] / index[year - 1] - 1)) <= 0.0015, year


def test_uk_cpi_meta_records_provenance() -> None:
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    assert meta["source"] == "UK_CPI"
    assert meta["series"] == "D7G7"
    assert meta["dataset"] == "MM23"
    assert meta["release_date"] == "2026-09-16"
    assert meta["retrieved"] == "2026-10-09"
    assert meta["raw_file"] == "raw/ons_cpi_d7g7.csv"
    assert meta["raw_sha256"] == "ff87e9f1cc2412d1688a35b21c67243be6902b463ccbd9df19387109978fdcae"
    assert meta["index_raw_sha256"] == "27a2473f818423a499fce4be23a2816d6670b1ae93b8eaaa11687c2237322865"
    assert meta["units"] == "annual_rate_decimal"
    assert meta["edition"] == "D7G7 (released 2026-09-16)"
    assert meta["source_url"].startswith("https://www.ons.gov.uk/")
