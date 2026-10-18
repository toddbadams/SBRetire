"""Build the SYNTHETIC portfolio sample for the Portfolio page and design work (F-030).

Usage:
    uv run python scripts/build_portfolio_design_sample.py

Runs the real ``sbretire portfolio report`` analysis on synthetic inputs only: the invented account exports in
tests/fixtures/accounts, seeded synthetic monthly prices, synthetic factsheets and a 4 % risk-free rate (the
same set-up the tests use). Writes docs/design/sample/portfolio/portfolio.json and portfolio.js
(window.SBRETIRE_PORTFOLIO), schema 1.0, marked "synthetic": true. No personal data is read.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "design" / "sample" / "portfolio"
GENERATED = "2026-10-18T00:00:00+00:00"  # fixed, so regenerating the sample gives the same files


def main() -> None:
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests" / "unit")]
    from test_portfolio_document import full_setup  # the tests' synthetic fixtures and seeded prices

    from sbretire.ledger.accounts import load_accounts
    from sbretire.ledger.document import ReportOptions, build_portfolio_document, write_portfolio_files

    with tempfile.TemporaryDirectory() as work:
        root, prices, accounts, factsheets = full_setup(Path(work) / "inputs")
        options = ReportOptions(
            root=root, prices=prices, factsheets=factsheets, months=24, min_trade=1.0, synthetic=True
        )
        document = build_portfolio_document(options, load_accounts(accounts))
        document["generated"] = GENERATED
        document["warnings"] = [w.replace(str(Path(work)), "<sample>") for w in document["warnings"]]  # type: ignore[attr-defined]
        written = Path(work) / "out"
        write_portfolio_files(document, written)
        OUT.mkdir(parents=True, exist_ok=True)
        for name in ("portfolio.json", "portfolio.js"):
            shutil.copyfile(written / "portfolio" / name, OUT / name)
    print(f"wrote {OUT / 'portfolio.json'} and portfolio.js (synthetic, schema 1.0)")


if __name__ == "__main__":
    main()
