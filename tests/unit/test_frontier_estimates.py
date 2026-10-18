"""F-029.1 — frontier settings, Ledoit-Wolf shrinkage and the priced sleeve (known answers)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest

from sbretire.config import ScenarioError
from sbretire.ledger.accounts import load_accounts
from sbretire.ledger.frontier import estimate, ledoit_wolf
from sbretire.ledger.prices import load_securities
from sbretire.ledger.returns import MonthlyReturn, add_months

SERIES = "securities:\n  - {id: a, name: A, file: a.csv, quote: GBP, holdings: ['x:A']}\n"
ACCOUNT = (
    "accounts:\n  - {id: x, name: X, provider: hl, owner: p, wrapper: isa, currency: GBP,\n"
    "     transactions: [t.csv], holdings: [h.csv]TRADING}\n"
)


def _locations(path: Path, loader: object) -> list[str]:
    with pytest.raises(ScenarioError) as caught:
        loader(path)  # type: ignore[operator]
    return [issue.location for issue in caught.value.issues]


def test_frontier_settings(tmp_path: Path) -> None:
    path = tmp_path / "securities.yaml"
    path.write_text(SERIES, encoding="utf-8")
    assert load_securities(path).max_weight == 0.25
    for bad in ("0", "1.5"):
        path.write_text(f"max_weight: {bad}\n" + SERIES, encoding="utf-8")
        assert _locations(path, load_securities) == ["max_weight"]
    path.write_text("max_weight: 1\n" + SERIES, encoding="utf-8")
    assert load_securities(path).max_weight == 1.0

    accounts = tmp_path / "accounts.yaml"
    accounts.write_text(ACCOUNT.replace("TRADING", ""), encoding="utf-8")
    assert load_accounts(accounts)[0].trading is None
    accounts.write_text(
        ACCOUNT.replace("TRADING", ", trading: {fee_per_trade: 11.95, cost_rate: 0.002}"), "utf-8"
    )
    trading = load_accounts(accounts)[0].trading
    assert trading is not None and (trading.fee_per_trade, trading.cost_rate) == (11.95, 0.002)
    for field, bad in (("cost_rate", "0.05"), ("fee_per_trade", "-1")):
        other = "fee_per_trade: 1" if field == "cost_rate" else "cost_rate: 0.001"
        accounts.write_text(ACCOUNT.replace("TRADING", f", trading: {{{field}: {bad}, {other}}}"), "utf-8")
        assert _locations(accounts, load_accounts) == [f"accounts[0].trading.{field}"]


def _textbook_ledoit_wolf(x: np.ndarray) -> tuple[np.ndarray, float]:
    """Ledoit & Wolf (2004), 'Honey, I shrunk the sample covariance matrix', written out term by term."""
    t, n = x.shape
    xc = x - x.mean(axis=0)
    s = xc.T @ xc / t
    m = np.trace(s) / n
    d2 = np.sum((s - m * np.eye(n)) ** 2) / n
    b_bar2 = sum(np.sum((np.outer(row, row) - s) ** 2) / n for row in xc) / t**2
    b2 = min(b_bar2, d2)
    shrink = b2 / d2
    return shrink * m * np.eye(n) + (1 - shrink) * s, shrink


def test_estimates_and_sleeve() -> None:
    x = np.array(
        [[0.02, 0.01, -0.01], [-0.01, 0.03, 0.00], [0.03, -0.02, 0.02], [0.00, 0.01, 0.01],
         [0.01, 0.00, -0.02], [-0.02, 0.02, 0.03], [0.04, -0.01, 0.00], [0.01, 0.02, 0.01]]
    )  # fmt: skip
    cov, shrink = ledoit_wolf(x)
    expected_cov, expected_shrink = _textbook_ledoit_wolf(x)
    assert shrink == pytest.approx(expected_shrink)
    assert 0 < shrink < 1
    np.testing.assert_allclose(cov, expected_cov)

    first = date(2026, 1, 1)
    months = [add_months(first, i) for i in range(len(x))]
    rows = [
        MonthlyReturn(month, name, 1.0, 0.0, float(x[i, j]), "adjusted")
        for j, name in enumerate(("a", "b", "c"))
        for i, month in enumerate(months)
    ]
    gappy = [
        MonthlyReturn(m, "d", 1.0, 0.0, None if i == 3 else 0.01, "adjusted") for i, m in enumerate(months)
    ]
    values = {"a": 100.0, "b": 50.0, "c": 50.0, "d": 25.0, "e": 10.0}  # d has a gap, e has no returns
    shrunk = estimate(rows + gappy, values, first, months[-1], "shrunk")
    assert shrunk.series == ["a", "b", "c"]
    np.testing.assert_allclose(shrunk.mean, 12 * x.mean(axis=0))
    np.testing.assert_allclose(shrunk.cov, 12 * expected_cov)
    assert shrunk.shrinkage == pytest.approx(expected_shrink)
    np.testing.assert_allclose(shrunk.today, [0.5, 0.25, 0.25])
    sample = estimate(rows + gappy, values, first, months[-1], "sample")
    np.testing.assert_allclose(sample.cov, 12 * np.cov(x, rowvar=False, ddof=1))
    assert sample.shrinkage is None
