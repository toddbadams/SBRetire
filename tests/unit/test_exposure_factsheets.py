"""F-028.1 — fixed sector/region names, series fields and fund factsheets (synthetic)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sbretire.config import ScenarioError
from sbretire.ledger.exposure import load_factsheet
from sbretire.ledger.prices import load_securities
from sbretire.ledger.taxonomy import canonical

PERCENT = """\
as_of: 2026-09-30
source: Example Fund factsheet, September 2026
asset_classes: {Equity: 60, Fixed Income: 40}
sectors: {Technology: 15, Healthcare: 9, Financials: 12, Industrials: 8, Other: 16, Bonds: 40}
regions: {United States: 36, United Kingdom: 12, Europe ex-UK: 6, Japan: 3, Other: 43}
top_holdings: {Example Corp: 2.5, "Example Treasury 4% 2030": 1.5}
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _locations(path: Path) -> list[str]:
    with pytest.raises(ScenarioError) as caught:
        load_factsheet(path)
    return [issue.location for issue in caught.value.issues]


def test_taxonomy_and_series_fields(tmp_path: Path) -> None:
    assert canonical("sector", "technology") == "Information Technology"
    assert canonical("sector", "Health Care") == "Health Care"
    assert canonical("sector", "healthcare") == "Health Care"
    assert canonical("region", "United States") == "North America"
    assert canonical("region", "europe ex-uk") == "Europe ex UK"
    assert canonical("asset_class", "Fixed Income") == "bond"
    assert canonical("currency", "usd") == "USD"
    assert canonical("sector", "Crypto") is None

    head = "securities:\n  - {id: a, name: A, file: a.csv, quote: USD, holdings: ['x:A']"
    path = _write(tmp_path, "securities.yaml", head + ", sector: technology, region: United States}\n")
    series = load_securities(path).securities[0]
    assert (series.sector, series.region, series.asset_class, series.factsheet) == (
        "Information Technology", "North America", None, None,
    )  # fmt: skip
    for field, bad in (("sector", "Crypto"), ("region", "Atlantis")):
        _write(tmp_path, "securities.yaml", head + f", {field}: {bad}}}\n")
        with pytest.raises(ScenarioError) as caught:
            load_securities(path)
        assert [issue.location for issue in caught.value.issues] == [f"securities[0].{field}"]


FRACTION_SECTORS = "Technology: 0.15, Healthcare: 0.09, Financials: 0.12, Industrials: 0.08, Other: 0.56"
FRACTION_REGIONS = "United States: 0.36, United Kingdom: 0.12, Europe ex-UK: 0.06, Japan: 0.03, Other: 0.43"


def test_load_factsheet(tmp_path: Path) -> None:
    percent = load_factsheet(_write(tmp_path, "pct.yaml", PERCENT))
    fractions = (
        PERCENT.replace("Equity: 60, Fixed Income: 40", "Equity: 0.6, Fixed Income: 0.4")
        .replace(
            "Technology: 15, Healthcare: 9, Financials: 12, Industrials: 8, Other: 16, Bonds: 40",
            FRACTION_SECTORS,
        )
        .replace(
            "United States: 36, United Kingdom: 12, Europe ex-UK: 6, Japan: 3, Other: 43", FRACTION_REGIONS
        )
    )
    fraction = load_factsheet(_write(tmp_path, "frac.yaml", fractions))
    for sheet in (percent, fraction):
        assert sheet.as_of == date(2026, 9, 30)
        assert sheet.weights["asset_class"] == pytest.approx({"equity": 0.6, "bond": 0.4})
        assert sheet.weights["sector"]["Information Technology"] == pytest.approx(0.15)
        assert sheet.weights["sector"]["Other"] == pytest.approx(
            0.56
        )  # "Bonds" is no sector: it counts as Other
        assert sheet.weights["region"]["North America"] == pytest.approx(0.36)
        assert sum(sheet.weights["region"].values()) == pytest.approx(1.0)
    assert percent.top_holdings == pytest.approx({"Example Corp": 0.025, "Example Treasury 4% 2030": 0.015})

    # currencies omitted: derived from regions and flagged
    assert percent.currency_derived
    expected = {"USD": 0.36, "GBP": 0.12, "EUR": 0.06, "JPY": 0.03, "Other": 0.43}
    assert percent.weights["currency"] == pytest.approx(expected)

    off = PERCENT.replace("Equity: 60, Fixed Income: 40", "Equity: 59, Fixed Income: 40")
    rescaled = load_factsheet(_write(tmp_path, "r.yaml", off))
    assert rescaled.weights["asset_class"]["equity"] == pytest.approx(59 / 99)

    unknown = _write(tmp_path, "u.yaml", PERCENT.replace("Japan: 3", "Atlantis: 3"))
    assert _locations(unknown) == ["regions.Atlantis"]
    assert _locations(_write(tmp_path, "s.yaml", PERCENT.replace("Other: 16", "Other: 6"))) == ["sectors"]
    assert _locations(_write(tmp_path, "d.yaml", PERCENT.replace("as_of: 2026-09-30\n", ""))) == ["as_of"]
