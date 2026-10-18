"""F-028.2 — look-through tables on hand-sized values (known answers)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sbretire.ledger.exposure import Factsheet, look_through
from sbretire.ledger.prices import SecuritiesConfig

SECURITIES = SecuritiesConfig.model_validate(
    {
        "securities": [
            {"id": "corp", "name": "Example Corp", "file": "c.csv", "quote": "USD", "holdings": ["x:CORP"],
             "sector": "Information Technology", "region": "North America"},
            {"id": "balanced", "name": "Balanced", "file": "b.csv", "quote": "GBP", "holdings": ["y:BAL"],
             "factsheet": "balanced.yaml"},
            {"id": "tech", "name": "Tech ETF", "file": "t.csv", "quote": "GBX", "holdings": ["y:TECH"],
             "factsheet": "tech.yaml"},
        ]
    }
)  # fmt: skip
FACTSHEETS = {
    "balanced": Factsheet(
        path=Path("balanced.yaml"), as_of=date(2026, 9, 30), source="Example",
        weights={
            "asset_class": {"equity": 0.6, "bond": 0.4},
            "sector": {"Information Technology": 0.3, "Health Care": 0.3, "Other": 0.4},
            "region": {"North America": 0.5, "UK": 0.5},
            "currency": {"USD": 0.5, "GBP": 0.5},
        },
        currency_derived=True, top_holdings={"Example Corp.": 0.05, "Big Bank": 0.02},
    ),
    "tech": Factsheet(
        path=Path("tech.yaml"), as_of=date(2026, 9, 30), source="Example",
        weights={
            "asset_class": {"equity": 1.0},
            "sector": {"Information Technology": 1.0},
            "region": {"North America": 1.0},
            "currency": {"USD": 1.0},
        },
        top_holdings={"example corp": 0.10},
    ),
}  # fmt: skip


def test_look_through_known_answers() -> None:
    values = {"x:CORP": 30.0, "y:BAL": 40.0, "y:TECH": 20.0, "z:MYSTERY": 20.0}  # MYSTERY is in no series
    exposure = look_through(values, {"GBP": 10.0}, SECURITIES, FACTSHEETS)
    assert exposure.total_gbp == pytest.approx(120.0)
    expected = {
        "asset_class": {"equity": 74.0, "bond": 16.0, "cash": 10.0, "Unclassified": 20.0},
        "sector": {"Information Technology": 62.0, "Health Care": 12.0, "Other": 16.0, "Cash": 10.0,
                   "Unclassified": 20.0},
        "region": {"North America": 70.0, "UK": 20.0, "Cash": 10.0, "Unclassified": 20.0},
        "currency": {"USD": 70.0, "GBP": 30.0, "Unclassified": 20.0},
    }  # fmt: skip
    for dimension, table in expected.items():
        assert exposure.tables[dimension] == pytest.approx(table), dimension  # type: ignore[index]
        assert sum(exposure.tables[dimension].values()) == pytest.approx(120.0)  # type: ignore[index]
    # the balanced fund's currencies came from its regions (£40) and the stock's from its region (£30)
    assert exposure.approximated_currency_gbp == pytest.approx(70.0)
    assert exposure.top_holdings[0] == ("Example Corp", pytest.approx(30.0 + 40 * 0.05 + 20 * 0.10))
    assert exposure.top_holdings[1] == ("Big Bank", pytest.approx(0.8))
