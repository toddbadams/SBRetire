"""Monthly GBP total returns from price series (F-026; portfolio-data §12–§13).

A month's return is ``(P_t + D_t) × X_t / (P_{t-1} × X_{t-1}) − 1``: ``P`` the month-end price in pounds
or dollars (GBX ÷ 100), ``D`` the dividends paid in the month, ``X`` GBP per unit of the quote currency at
month-end.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal, get_args

from sbretire.ledger.accounts import AccountConfig
from sbretire.ledger.prices import PriceFile, SecuritiesConfig, SeriesConfig, load_securities, read_price_file
from sbretire.ledger.valuation import Valuation, read_holdings, value_holdings

_MONTHS: Final = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")


@dataclass(frozen=True)
class MonthlyReturn:
    """One series' month in GBP: value per unit, dividends and total return (``None`` when unknown)."""

    month: dt.date
    series: str
    value_gbp: float | None
    dividend_gbp: float
    return_gbp: float | None
    basis: str


def add_months(month: dt.date, count: int) -> dt.date:
    """The first day of the month ``count`` months after ``month`` (negative goes back)."""
    index = month.year * 12 + month.month - 1 + count
    return dt.date(index // 12, index % 12 + 1, 1)


def window(folder: str, months: int) -> tuple[dt.date, dt.date]:
    """(first, last) return month: ``months`` months ending the month before the folder's ``<mon>-<yy>``."""
    name, _, year = folder.partition("-")
    if name not in _MONTHS or not year.isdigit() or months < 1:
        raise ValueError(
            f"expected a <mon>-<yy> folder and a positive month count (got {folder!r}, {months})"
        )
    last = add_months(dt.date(2000 + int(year), _MONTHS.index(name) + 1, 1), -1)
    return add_months(last, -(months - 1)), last


def gbp_returns(
    series: SeriesConfig, prices: PriceFile, fx: PriceFile | None, first: dt.date, last: dt.date
) -> list[MonthlyReturn]:
    """One row per month from ``first`` to ``last``; months without a price (or rate) have no value or return.

    Raises ``ValueError`` when a USD series has no FX file.
    """
    if series.quote == "USD" and fx is None:
        raise ValueError(f"series {series.id!r} is quoted in USD but no FX file gives GBP per USD")
    unit = 0.01 if series.quote == "GBX" else 1.0
    closes = {m.month: m for m in prices.months}
    rates = {m.month: m.close for m in fx.months} if series.quote == "USD" and fx is not None else None

    def rate(month: dt.date) -> float | None:
        return 1.0 if rates is None else rates.get(month)

    def value(month: dt.date) -> float | None:
        found, x = closes.get(month), rate(month)
        return None if found is None or x is None else found.close * unit * x

    rows = []
    month = first
    while month <= last:
        found, x = closes.get(month), rate(month)
        dividend = 0.0 if found is None or x is None else found.dividend * unit * x
        now, before = value(month), value(add_months(month, -1))
        total = None if now is None or before is None else (now + dividend) / before - 1
        rows.append(MonthlyReturn(month, series.id, now, dividend, total, prices.basis))
        month = add_months(month, 1)
    return rows


CoverageStatus = Literal["full", "short", "gaps", "missing"]


@dataclass(frozen=True)
class CoverageRow:
    """How well one price series (or one holding in no series) covers the window."""

    series: str | None
    """``None`` for a holding that no series prices."""
    holdings: tuple[str, ...]
    """``<account id>:<security key>`` references."""
    status: CoverageStatus
    months: int
    """Months in the window with a return."""
    first: dt.date | None
    """First month with a return."""
    basis: str | None
    share: float
    """Share of the invested (non-cash) GBP value of the newest holdings."""
    detail: str


@dataclass(frozen=True)
class ReturnsReport:
    """Everything ``sbretire portfolio returns`` prints and writes."""

    folder: str
    first: dt.date
    last: dt.date
    usd_gbp: float | None
    rate_source: str
    returns: list[MonthlyReturn]
    coverage: list[CoverageRow]
    files: list[tuple[str, PriceFile]]
    """(series id, or ``fx:USD``, and its file) for every price file read."""
    warnings: list[str]
    series_values: dict[str, float]
    """Today's GBP value of the holdings each series prices (series with a price file only)."""
    series_names: dict[str, str]
    cash_gbp: float
    """Today's cash in GBP across every account."""
    total_gbp: float
    """Today's household value in GBP, cash and unpriced holdings included."""
    risk_free_rate: float | None
    """From ``securities.yaml``; ``None`` when it sets none."""
    max_weight: float = 0.25
    """From ``securities.yaml`` (F-029)."""
    holding_values: dict[str, float] = field(default_factory=dict)
    """``<account>:<security key>`` → today's GBP value of each security."""
    series_holdings: dict[str, tuple[str, ...]] = field(default_factory=dict)
    """Series id → the holdings (``<account>:<security key>``) it prices."""


def _classify(series: SeriesConfig, rows: Sequence[MonthlyReturn], basis: str, share: float) -> CoverageRow:
    present = [row for row in rows if row.return_gbp is not None]
    if not present:
        return CoverageRow(
            series.id, series.holdings, "missing", 0, None, basis, share, "no prices in the window"
        )
    start = present[0].month
    holes = [row.month for row in rows if row.month > start and row.return_gbp is None]
    if holes:
        status: CoverageStatus = "gaps"
        detail = "no return for " + ", ".join(f"{month:%Y-%m}" for month in holes)
    elif len(present) < len(rows):
        status, detail = "short", f"history starts {start:%Y-%m}"
    else:
        status, detail = "full", ""
    return CoverageRow(series.id, series.holdings, status, len(present), start, basis, share, detail)


@dataclass(frozen=True)
class TodayValues:
    """The securities map and the newest folder's holdings valued in GBP, shared by the portfolio commands."""

    config: SecuritiesConfig
    folder: str
    valuation: Valuation
    values: dict[str, float]
    """``<account>:<security key>`` → today's GBP value of the securities (cash excluded)."""
    cash: dict[str, float]
    """Account currency → today's cash in GBP."""
    fx: PriceFile | None
    usd_gbp: float | None
    rate_source: str
    notes: list[str]


def today_values(
    root: Path, accounts: Sequence[AccountConfig], prices_dir: Path, usd_gbp: float | None
) -> TodayValues:
    """Load ``securities.yaml`` (empty if absent, noted) and value the newest holdings (portfolio-data §14).

    USD converts at ``usd_gbp`` or else the FX price file's latest month-end.
    """
    map_path = prices_dir / "securities.yaml"
    notes = []
    if map_path.exists():
        config = load_securities(map_path)
    else:  # nothing priced yet
        config = SecuritiesConfig.model_construct(fx={}, securities=(), risk_free_rate=None, max_weight=0.25)
        notes.append(f"no {map_path}; copy config/securities.example.yaml there and list the price files")
    folder, exports = read_holdings(root, accounts)
    fx_name = config.fx.get("USD")
    fx = read_price_file(prices_dir / fx_name) if fx_name and (prices_dir / fx_name).exists() else None
    rate, source = usd_gbp, "--usd-gbp"
    if rate is None and fx is not None:
        latest = fx.months[-1]
        rate, source = latest.close, f"{fx.path.name}, {latest.month:%Y-%m}"
    valuation = value_holdings(folder, exports, rate)
    values: dict[str, float] = defaultdict(float)
    cash: dict[str, float] = defaultdict(float)
    for holding in valuation.holdings:
        if holding.kind == "security":
            values[f"{holding.account}:{holding.security_key}"] += valuation.value_gbp(holding)
        else:
            cash[holding.currency] += valuation.value_gbp(holding)
    return TodayValues(config, folder, valuation, dict(values), dict(cash), fx, rate, source, notes)


def build_returns(
    root: Path,
    accounts: Sequence[AccountConfig],
    prices_dir: Path,
    months: int = 60,
    usd_gbp: float | None = None,
) -> ReturnsReport:
    """Monthly GBP returns for every series in ``<prices_dir>/securities.yaml`` and their coverage.

    The newest month folder's holdings give each holding's share (portfolio-data §14); USD converts at
    ``usd_gbp`` or else the FX file's latest month-end. A series or holding without prices is reported, never
    an error. Raises ``ScenarioError`` (invalid map), ``PriceFileError``, ``HoldingsError`` or
    ``ValuationError``.
    """
    today = today_values(root, accounts, prices_dir, usd_gbp)
    config, folder, valuation, values, fx = (
        today.config,
        today.folder,
        today.valuation,
        today.values,
        today.fx,
    )
    rate, source, notes = today.usd_gbp, today.rate_source, today.notes
    fx_name = config.fx.get("USD")
    first, last = window(folder, months)
    files: list[tuple[str, PriceFile]] = []
    if fx is not None:
        files.append(("fx:USD", fx))
    invested = sum(values.values())
    shares = {ref: value / invested if invested else 0.0 for ref, value in values.items()}

    returns: list[MonthlyReturn] = []
    coverage: list[CoverageRow] = []
    warnings = notes + list(valuation.warnings)
    mapped: set[str] = set()
    for series in config.securities:
        mapped.update(series.holdings)
        share = sum(shares.get(ref, 0.0) for ref in series.holdings)
        warnings += [f"series {series.id}: {ref} is not in the {folder} holdings" for ref in series.holdings
                     if ref not in values]  # fmt: skip
        path = prices_dir / series.file
        if not path.exists():
            detail = f"no price file {series.file}"
            coverage.append(CoverageRow(series.id, series.holdings, "missing", 0, None, None, share, detail))
            continue
        prices = read_price_file(path)
        files.append((series.id, prices))
        if series.quote == "USD" and fx is None:
            detail = f"quoted in USD but there is no FX file {fx_name or '(fx: USD not set)'}"
            coverage.append(
                CoverageRow(series.id, series.holdings, "missing", 0, None, prices.basis, share, detail)
            )
            continue
        rows = gbp_returns(series, prices, fx, first, last)
        returns += rows
        coverage.append(_classify(series, rows, prices.basis, share))
    for ref, share in shares.items():
        if ref not in mapped:
            coverage.append(
                CoverageRow(None, (ref,), "missing", 0, None, None, share, "not in securities.yaml")
            )
    priced = {series_id for series_id, _ in files if series_id != "fx:USD"}
    series_values = {
        s.id: sum(values.get(ref, 0.0) for ref in s.holdings) for s in config.securities if s.id in priced
    }
    cash = sum(valuation.value_gbp(h) for h in valuation.holdings if h.kind == "cash")
    return ReturnsReport(
        folder, first, last, rate, source, returns, coverage, files, warnings,
        series_values=series_values,
        series_names={s.id: s.name for s in config.securities},
        cash_gbp=round(cash, 2),
        total_gbp=valuation.total_gbp(),
        risk_free_rate=config.risk_free_rate,
        max_weight=config.max_weight,
        holding_values=dict(values),
        series_holdings={s.id: s.holdings for s in config.securities},
    )  # fmt: skip


RETURNS_COLUMNS: Final = ("month", "series", "value_gbp", "dividend_gbp", "return_gbp", "basis")


def write_returns_csv(report: ReturnsReport, path: Path) -> None:
    """UTF-8, LF; one row per series and month; unknown values written empty."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(RETURNS_COLUMNS)
        for row in report.returns:
            writer.writerow(
                (
                    f"{row.month:%Y-%m}",
                    row.series,
                    "" if row.value_gbp is None else row.value_gbp,
                    row.dividend_gbp,
                    "" if row.return_gbp is None else row.return_gbp,
                    row.basis,
                )
            )


def write_returns_metadata(report: ReturnsReport, path: Path) -> None:
    """The window, the USD rate used for shares, and every price file's SHA-256 and date range."""
    document = {
        "schema_version": "1.0",
        "folder": report.folder,
        "window": {"first": f"{report.first:%Y-%m}", "last": f"{report.last:%Y-%m}",
                   "months": _span(report.first, report.last)},
        "usd_gbp": report.usd_gbp,
        "usd_gbp_source": report.rate_source if report.usd_gbp is not None else None,
        "files": [
            {"series": series, "file": prices.path.name, "sha256": prices.sha256,
             "first": prices.first.isoformat(), "last": prices.last.isoformat(), "rows": prices.rows,
             "basis": prices.basis}
            for series, prices in report.files
        ],
    }  # fmt: skip
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")


def _span(first: dt.date, last: dt.date) -> int:
    return (last.year - first.year) * 12 + last.month - first.month + 1


def format_returns(report: ReturnsReport) -> str:
    """The coverage table, the shares by status and any warnings."""
    rate = (
        "" if report.usd_gbp is None else f"; USD at {report.usd_gbp:.4f} GBP per USD ({report.rate_source})"
    )
    lines = [
        f"Monthly returns {report.first:%Y-%m} to {report.last:%Y-%m} "
        f"({_span(report.first, report.last)} months) for the {report.folder} holdings{rate}",
        "  {:<28} {:<8} {:>6}  {:<8} {:<9} {:>6}  {}".format(
            "series / holding", "status", "months", "first", "basis", "share", "detail"
        ),
    ]
    for row in report.coverage:
        name = row.series or row.holdings[0]
        first = "-" if row.first is None else f"{row.first:%Y-%m}"
        lines.append(
            f"  {name[:28]:<28} {row.status:<8} {row.months:>6}  {first:<8} {row.basis or '-':<9} "
            f"{row.share:>6.1%}  {row.detail}".rstrip()
        )
    totals = {
        status: sum(r.share for r in report.coverage if r.status == status)
        for status in get_args(CoverageStatus)
    }
    lines.append(
        "Share of invested value: " + ", ".join(f"{status} {share:.1%}" for status, share in totals.items())
    )
    lines += [f"warning: {warning}" for warning in report.warnings]
    return "\n".join(lines)
