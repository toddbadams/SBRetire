"""Account returns from the ledger: what each account actually earned since the first export (F-031; §26–§28).

Month-end values are rebuilt backwards from today's holdings through the ledger and priced with the price
files; time-weighted returns chain Modified Dietz months, money-weighted returns solve the internal rate
of return.
"""

from __future__ import annotations

import csv
import datetime as dt
import itertools
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from scipy.optimize import brentq

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.holdings import Holding
from sbretire.ledger.merge import build_ledger
from sbretire.ledger.model import LedgerRow
from sbretire.ledger.prices import SecuritiesConfig, read_price_file
from sbretire.ledger.returns import add_months, today_values, window

_TAIL: Final = {
    "acc", "accumulation", "accumulating", "inc", "income", "dist", "distributing", "shares", "share",
    "class",
    "gbp", "usd", "fund",
}  # fmt: skip


def normalise_name(name: str) -> str:
    """Lower case, punctuation removed, trailing share-class words and single letters dropped (§26)."""
    tokens = re.sub(r"[^a-z0-9]+", " ", name.lower()).split()
    while tokens and (tokens[-1] in _TAIL or len(tokens[-1]) == 1):
        tokens.pop()
    return " ".join(tokens)


def match_securities(
    rows: Sequence[LedgerRow], holdings: Sequence[Holding], securities: SecuritiesConfig
) -> tuple[dict[tuple[str, str], str], list[tuple[str, str]]]:
    """(account, ledger security key) → series id for every security in ``rows``, and those left unmatched.

    Order (§26): a series' ``ledger_names`` (in the accounts its holdings name); the account's holding with
    the same key; the account's holding with the same normalised name. A matched holding takes the series that
    prices it.
    """
    series_of_ref = {ref: s.id for s in securities.securities for ref in s.holdings}
    overrides: dict[tuple[str, str], str] = {}
    for series in securities.securities:
        for account in {ref.split(":", 1)[0] for ref in series.holdings}:
            for name in series.ledger_names:
                overrides[(account, name)] = series.id
    by_key: dict[tuple[str, str], str] = {}
    by_name: dict[tuple[str, str], str] = {}
    for holding in holdings:
        if holding.kind != "security":
            continue
        ref = f"{holding.account}:{holding.security_key}"
        if ref in series_of_ref:
            by_key[(holding.account, holding.security_key)] = series_of_ref[ref]
            by_name.setdefault((holding.account, normalise_name(holding.security_name)), series_of_ref[ref])
            by_name.setdefault((holding.account, normalise_name(holding.security_key)), series_of_ref[ref])
    matched: dict[tuple[str, str], str] = {}
    unmatched: list[tuple[str, str]] = []
    for row in rows:
        key = (row.account, row.security_key)
        if not row.security_key or key in matched or key in unmatched:
            continue
        found = (
            overrides.get(key)
            or overrides.get((row.account, row.security_name))
            or by_key.get(key)
            or by_name.get((row.account, normalise_name(row.security_key)))
            or by_name.get((row.account, normalise_name(row.security_name)))
        )
        if found is None:
            unmatched.append(key)
        else:
            matched[key] = found
    return matched, unmatched


def month_end(month: dt.date) -> dt.date:
    """The last day of ``month`` (given as its first day)."""
    return add_months(month, 1) - dt.timedelta(days=1)


def units_at(
    rows: Sequence[LedgerRow],
    matched: Mapping[tuple[str, str], str],
    today: Mapping[str, float],
    month: dt.date,
) -> dict[str, float]:
    """Series → units at the end of ``month``: today's units less every later ``quantity_change`` (§27)."""
    end = month_end(month)
    units = dict(today)
    for row in rows:
        series = matched.get((row.account, row.security_key))
        if series is not None and row.date > end and row.quantity_change:
            units[series] = units.get(series, 0.0) - row.quantity_change
    return units


def cash_at(rows: Sequence[LedgerRow], today: float, month: dt.date) -> float:
    """Cash at the end of ``month``: today's cash less every later ``cash_change`` (§27)."""
    end = month_end(month)
    return today - sum(row.cash_change for row in rows if row.date > end)


def price_in(account_currency: str, quote: str, close: float, usd_gbp: float) -> float:
    """A month-end price in the account's currency: GBX ÷ 100; USD × GBP-per-USD into GBP, and back (§27)."""
    pounds = close / 100.0 if quote == "GBX" else close
    major = "GBP" if quote == "GBX" else quote
    if major == account_currency:
        return pounds
    if major == "USD" and account_currency == "GBP":
        return pounds * usd_gbp
    if major == "GBP" and account_currency == "USD":
        return pounds / usd_gbp
    raise ValueError(f"no conversion from {quote} to {account_currency}")


def rebuild(
    rows: Sequence[LedgerRow],
    matched: Mapping[tuple[str, str], str],
    today_units: Mapping[str, float],
    today_cash: float,
    months: Sequence[dt.date],
    closes: Mapping[str, Mapping[dt.date, float]],
    quotes: Mapping[str, str],
    currency: str,
    usd_gbp: Mapping[dt.date, float],
) -> tuple[list[tuple[dt.date, float | None]], list[str]]:
    """Month-end values of one account in its own currency, and what stops any month being valued (§27).

    A ledger security with no matched series, or a held series without a price (or a needed USD rate) at a
    month-end, is listed; that month's value is ``None``.
    """
    missing: list[str] = []
    for row in rows:
        if row.security_key and (row.account, row.security_key) not in matched:
            label = f"{row.security_key} (no price series matched)"
            if label not in missing:
                missing.append(label)
    values: list[tuple[dt.date, float | None]] = []
    for month in months:
        total: float | None = cash_at(rows, today_cash, month)
        for series, units in units_at(rows, matched, today_units, month).items():
            if abs(units) < 1e-9:
                continue
            close = closes.get(series, {}).get(month)
            quote = quotes.get(series, currency)
            needs_rate = ("GBP" if quote == "GBX" else quote) != currency
            rate = usd_gbp.get(month)
            if close is None:
                missing.append(f"{series} ({month:%Y-%m})")
                total = None
            elif needs_rate and rate is None:
                missing.append(f"{series} ({month:%Y-%m}: no USD rate)")
                total = None
            elif total is not None:
                total += units * price_in(currency, quote, close, rate or 1.0)
        values.append((month, total))
    return values, missing


Flow = tuple[dt.date, float]
"""A dated external flow; positive = money into the account."""


def modified_dietz(v0: float, v1: float, flows: Sequence[Flow], start: dt.date, end: dt.date) -> float | None:
    """``(V₁ − V₀ − F) / (V₀ + Σ wᵢFᵢ)``, ``wᵢ`` the share of the period left after each flow (§28)."""
    days = (end - start).days
    total = sum(amount for _, amount in flows)
    weighted = sum(amount * (end - day).days / days for day, amount in flows) if days > 0 else 0.0
    base = v0 + weighted
    return None if abs(base) < 1e-9 else (v1 - v0 - total) / base


def xirr(v0: float, flows: Sequence[Flow], v_end: float, start: dt.date, end: dt.date) -> float | None:
    """The annual rate ``r`` solving ``−V₀ − ΣFᵢ(1+r)^(−tᵢ) + V_end(1+r)^(−T) = 0``, years = days ÷ 365 (§28).

    Solved for the log growth ``x = ln(1 + r)`` so short, steep periods (huge annual rates) still converge;
    ``None`` when there is no root for ``x`` between ln(0.01) and 50.
    """
    years = (end - start).days / 365.0
    if years <= 0:
        return None
    times = [(amount, (day - start).days / 365.0) for day, amount in flows]

    def npv(x: float) -> float:
        value = -v0 - sum(amount * math.exp(-x * t) for amount, t in times)
        return float(value + v_end * math.exp(-x * years))

    low, high = math.log(0.01), 50.0
    if npv(low) * npv(high) > 0:
        return None
    return math.expm1(float(brentq(npv, low, high, xtol=1e-14, maxiter=500)))


@dataclass(frozen=True)
class PeriodReturn:
    """Time- and money-weighted returns over valuation points (month-ends, then the valuation date)."""

    twr: float | None
    monthly: list[tuple[dt.date, float | None]]
    """Each sub-period's end date and Modified Dietz return."""
    mwr_period: float | None
    mwr_annual: float | None
    """Only when the period is at least a year."""
    net_flows: float


def returns_for(points: Sequence[tuple[dt.date, float]], flows: Sequence[Flow]) -> PeriodReturn:
    """Chain Modified Dietz sub-periods between ``points`` and solve the MWR over the whole span (§28).

    Flows dated after the first point and up to the last belong to the sub-period they fall in.
    """
    start, end = points[0][0], points[-1][0]
    inside = [(day, amount) for day, amount in flows if start < day <= end]
    monthly: list[tuple[dt.date, float | None]] = []
    growth: float | None = 1.0
    for (d0, v0), (d1, v1) in itertools.pairwise(points):
        r = modified_dietz(v0, v1, [(d, a) for d, a in inside if d0 < d <= d1], d0, d1)
        monthly.append((d1, r))
        growth = None if r is None or growth is None else growth * (1.0 + r)
    rate = xirr(points[0][1], inside, points[-1][1], start, end)
    years = (end - start).days / 365.0
    return PeriodReturn(
        twr=None if growth is None else growth - 1.0,
        monthly=monthly,
        mwr_period=None if rate is None else (1.0 + rate) ** years - 1.0,
        mwr_annual=rate if rate is not None and years >= 1.0 else None,
        net_flows=sum(amount for _, amount in inside),
    )


def to_gbp(
    points: Sequence[tuple[dt.date, float]],
    flows: Sequence[Flow],
    currency: str,
    usd_gbp: Mapping[dt.date, float],
) -> tuple[list[tuple[dt.date, float]], list[Flow]]:
    """Points and flows in GBP: USD amounts at the GBP-per-USD rate of their month (§28)."""
    if currency == "GBP":
        return list(points), list(flows)

    def rate(day: dt.date) -> float:
        found = usd_gbp.get(day.replace(day=1))
        if found is None:
            raise ValueError(f"no USD rate for {day:%Y-%m}")
        return found

    return [(d, v * rate(d)) for d, v in points], [(d, a * rate(d)) for d, a in flows]


@dataclass(frozen=True)
class AccountReturn:
    """One account's (or the household's) actual returns, or why they cannot be measured yet."""

    account: str
    currency: str
    available: bool
    reason: str | None
    start: dt.date | None
    end: dt.date | None
    start_value: float | None
    end_value: float | None
    net_flows: float | None
    twr: float | None
    mwr_period: float | None
    mwr_annual: float | None
    points: list[tuple[dt.date, float | None, float, float | None]]
    """Valuation date, value, external flow in the sub-period ending there, sub-period return."""


@dataclass(frozen=True)
class AccountReturnsReport:
    folder: str
    accounts: list[AccountReturn]
    household: AccountReturn
    unmatched: list[tuple[str, str]]


def _unavailable(account: str, currency: str, reason: str) -> AccountReturn:
    return AccountReturn(account, currency, False, reason, None, None, None, None, None, None, None, None, [])


def _measured(
    account: str, currency: str, points: Sequence[tuple[dt.date, float]], flows: Sequence[Flow]
) -> AccountReturn:
    result = returns_for(points, flows)
    sub = dict(result.monthly)
    flow_in = {
        d1: sum(a for d, a in flows if d0 < d <= d1) for (d0, _), (d1, _) in itertools.pairwise(points)
    }
    rows = [(d, v, flow_in.get(d, 0.0), sub.get(d)) for d, v in points]
    return AccountReturn(
        account, currency, True, None, points[0][0], points[-1][0], points[0][1], points[-1][1],
        result.net_flows, result.twr, result.mwr_period, result.mwr_annual, list(rows),
    )  # fmt: skip


def build_account_returns(
    root: Path, accounts: Sequence[AccountConfig], prices_dir: Path, usd_gbp: float | None = None
) -> AccountReturnsReport:
    """Rebuild every account's month-end values and measure its TWR and MWR, and the household's (§26–§28).

    The span starts at the month-end before the earliest ledger row (or before the export month) and ends at
    the newest valuation. An account that cannot be fully valued is unavailable with its reason; the household
    then is too.
    """
    today = today_values(root, accounts, prices_dir, usd_gbp)
    valuation = today.valuation
    rows = build_ledger(root, accounts)
    matched, unmatched = match_securities(rows, valuation.holdings, today.config)
    series_of_ref = {ref: s.id for s in today.config.securities for ref in s.holdings}
    closes: dict[str, dict[dt.date, float]] = {}
    quotes: dict[str, str] = {}
    for series in today.config.securities:
        path = prices_dir / series.file
        if path.exists():
            closes[series.id] = {m.month: m.close for m in read_price_file(path).months}
            quotes[series.id] = series.quote
    fx = {m.month: m.close for m in today.fx.months} if today.fx is not None else {}

    dates = [on for on, _ in valuation.dates().values()]
    valued_on = max(dates)
    first, last = window(today.folder, 1)
    begin = min([row.date.replace(day=1) for row in rows], default=first)
    months: list[dt.date] = []
    month = add_months(begin, -1)
    while month <= last:
        months.append(month)
        month = add_months(month, 1)

    results: list[AccountReturn] = []
    gbp: list[tuple[list[tuple[dt.date, float]], list[Flow]]] = []
    rates = dict(fx)
    if today.usd_gbp is not None:
        rates.setdefault(valued_on.replace(day=1), today.usd_gbp)
    for account in accounts:
        own = [h for h in valuation.holdings if h.account == account.id]
        account_rows = [row for row in rows if row.account == account.id]
        today_units: dict[str, float] = {}
        problems: list[str] = []
        for holding in own:
            if holding.kind != "security":
                continue
            series_id = series_of_ref.get(f"{holding.account}:{holding.security_key}")
            if series_id is None:
                problems.append(f"{holding.security_key} (no price series)")
            else:
                today_units[series_id] = today_units.get(series_id, 0.0) + holding.quantity
        today_cash = sum(h.value for h in own if h.kind == "cash")
        values, missing = rebuild(account_rows, matched, today_units, today_cash, months, closes, quotes,
                                  account.currency, fx)  # fmt: skip
        named = {problem.split(" (", 1)[0] for problem in problems}
        problems += [m for m in missing if m.split(" (", 1)[0] not in named]  # one line per security
        if problems:
            shown = ", ".join(problems[:5]) + (f" and {len(problems) - 5} more" if len(problems) > 5 else "")
            results.append(_unavailable(account.id, account.currency, f"cannot value: {shown}"))
            continue
        points = [(month_end(m), float(v)) for m, v in values if v is not None]
        points.append((valued_on, sum(h.value for h in own)))
        flows = [(row.date, row.cash_change) for row in account_rows if row.flow == "external"]
        results.append(_measured(account.id, account.currency, points, flows))
        try:
            gbp.append(to_gbp(points, flows, account.currency, rates))
        except ValueError as exc:
            gbp.append(([], []))
            problems.append(str(exc))

    if any(not r.available for r in results) or any(not p for p, _ in gbp):
        why = "every account must be fully valued (and USD needs the GBP=X file) to combine the household"
        household = _unavailable("household", "GBP", why)
    else:
        totals: dict[dt.date, float] = {}
        for points, _ in gbp:
            for day, value in points:
                totals[day] = totals.get(day, 0.0) + value
        household = _measured("household", "GBP", sorted(totals.items()), [f for _, fl in gbp for f in fl])
    return AccountReturnsReport(today.folder, results, household, unmatched)


def write_account_returns_csv(report: AccountReturnsReport, path: Path) -> None:
    """UTF-8, LF: ``account``, ``date``, ``value``, ``external_flow``, ``return`` per point (§28)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("account", "date", "value", "external_flow", "return"))
        for item in [*report.accounts, report.household]:
            for day, value, flow, ret in item.points:
                writer.writerow((item.account, day.isoformat(), "" if value is None else round(value, 2),
                                 round(flow, 2), "" if ret is None else ret))  # fmt: skip


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2%}"


def format_account_returns(report: AccountReturnsReport) -> str:
    """The table of accounts and household, the reasons for anything unavailable and unmatched securities."""
    measured = [r for r in [*report.accounts, report.household] if r.available]
    span = next((r for r in measured), None)
    head = (
        f"Account returns from {span.start:%d %b %Y} to {span.end:%d %b %Y} (exports {report.folder})"
        if span is not None and span.start and span.end else f"Account returns (exports {report.folder})"
    )  # fmt: skip
    lines = [
        head,
        "  time-weighted = the investments' own return; money-weighted = the result incl. timing of money",
        "  {:<18} {:<4} {:>14} {:>14} {:>12} {:>14} {:>14}".format(
            "account", "ccy", "start value", "end value", "net flows", "time-weighted", "money-weighted"
        ),
    ]
    for item in [*report.accounts, report.household]:
        if not item.available:
            continue
        mwr = _pct(item.mwr_period) + ("" if item.mwr_annual is None else f" ({item.mwr_annual:.2%} a year)")
        lines.append(
            f"  {item.account[:18]:<18} {item.currency:<4} {item.start_value or 0:>14,.2f} "
            f"{item.end_value or 0:>14,.2f} "
            f"{item.net_flows or 0:>12,.2f} {_pct(item.twr):>14} {mwr:>14}"
        )
    for item in [*report.accounts, report.household]:
        if not item.available:
            lines.append(f"unavailable {item.account}: {item.reason}")
    if report.unmatched:
        names = ", ".join(f"{a}: {k}" for a, k in report.unmatched[:8])
        lines.append(f"unmatched transaction securities (add ledger_names to their series): {names}")
    return "\n".join(lines)
