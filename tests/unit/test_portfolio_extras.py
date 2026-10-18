"""F-030.1 — drawdown episodes, calendar, correlation, risk contribution and income by month."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from sbretire.ledger.extras import (
    calendar,
    correlation,
    drawdown_episodes,
    income_by_month,
    risk_contribution,
)
from sbretire.ledger.model import LedgerRow, TransactionType


def _row(day: date, kind: TransactionType, cash: float, currency: str = "GBP") -> LedgerRow:
    return LedgerRow(
        account="a", owner="p", wrapper="isa", date=day, settle_date=None, type=kind, flow="none",
        security_key="", security_name="", quantity_change=0.0, price=None, cash_change=cash, fees=0.0,
        currency=currency, reference="", source_file="f.csv", source_row=2, sequence=1,
    )  # fmt: skip


def test_portfolio_extras_known_answers() -> None:
    months = [date(2026, m, 1) for m in range(1, 7)]
    episodes = drawdown_episodes(months, [0.10, -0.10, 0.05, 0.10, -0.20, 0.05])
    # wealth 1.10, 0.99, 1.0395, 1.14345, 0.91476, 0.96050
    assert [e["depth"] for e in episodes] == [pytest.approx(0.2), pytest.approx(0.1)]
    assert episodes[0] == {
        "peak": "2026-04", "trough": "2026-05", "recovery": None, "depth": pytest.approx(0.2),
        "months_to_trough": 1, "months_to_recover": None,
    }  # fmt: skip
    assert episodes[1] == {
        "peak": "2026-01", "trough": "2026-02", "recovery": "2026-04", "depth": pytest.approx(0.1),
        "months_to_trough": 1, "months_to_recover": 2,
    }  # fmt: skip
    assert drawdown_episodes(months[:2], [0.01, 0.02]) == []

    years = calendar([date(2025, 11, 1), date(2025, 12, 1), date(2026, 1, 1), date(2026, 2, 1)],
                     [0.01, 0.02, -0.01, 0.03])  # fmt: skip
    assert [y["year"] for y in years] == [2025, 2026]
    assert years[0]["months"] == [None] * 10 + [0.01, 0.02]
    assert years[0]["total"] == pytest.approx(1.01 * 1.02 - 1)
    assert years[1]["months"] == [-0.01, 0.03] + [None] * 10
    assert years[1]["total"] == pytest.approx(0.99 * 1.03 - 1)

    np.testing.assert_allclose(correlation(np.array([[4.0, 2.0], [2.0, 9.0]])), [[1.0, 1 / 3], [1 / 3, 1.0]])
    np.testing.assert_allclose(risk_contribution(np.array([0.5, 0.5]), np.diag([0.04, 0.04])), [0.5, 0.5])
    shares = risk_contribution(np.array([0.7, 0.3]), np.array([[0.04, 0.01], [0.01, 0.09]]))
    assert shares.sum() == pytest.approx(1.0)
    w, cov = np.array([0.7, 0.3]), np.array([[0.04, 0.01], [0.01, 0.09]])
    np.testing.assert_allclose(shares, w * (cov @ w) / (w @ cov @ w))

    rows = [
        _row(date(2026, 1, 10), "dividend", 12.0),
        _row(date(2026, 1, 20), "dividend", 10.0, "USD"),
        _row(date(2026, 1, 20), "tax_withheld", -1.5, "USD"),
        _row(date(2026, 2, 1), "interest", 0.5),
        _row(date(2026, 2, 28), "fee", -20.0),
        _row(date(2026, 3, 1), "buy", -1000.0),  # not income
        _row(date(2025, 12, 31), "dividend", 99.0),  # before the window
    ]
    income = income_by_month(rows, date(2026, 1, 1), date(2026, 3, 1), usd_gbp=0.8)
    assert [m["month"] for m in income] == ["2026-01", "2026-02", "2026-03"]
    assert income[0] == {"month": "2026-01", "dividends_gbp": pytest.approx(12.0 + 8.0), "interest_gbp": 0.0,
                         "fees_gbp": 0.0, "tax_withheld_gbp": pytest.approx(-1.2)}  # fmt: skip
    assert income[1] == {"month": "2026-02", "dividends_gbp": 0.0, "interest_gbp": pytest.approx(0.5),
                         "fees_gbp": pytest.approx(-20.0), "tax_withheld_gbp": 0.0}  # fmt: skip
    assert income[2]["dividends_gbp"] == 0.0 and income[2]["fees_gbp"] == 0.0
