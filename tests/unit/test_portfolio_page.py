"""F-030.3 — static checks on the Portfolio page (src/sbretire/web/portfolio), as for the results viewer."""

from __future__ import annotations

import re
from pathlib import Path

from test_viewer import COLOUR_LITERAL, NAMED_COLOUR, NETWORK, _themes

PAGE = Path(__file__).resolve().parents[2] / "src" / "sbretire" / "web" / "portfolio"
SECTIONS = (
    "headline",
    "allocation",
    "frontier",
    "rebalance",
    "performance",
    "risk",
    "income",
    "holdings",
    "returns",
    "caveats",
)
BANNED = ("you should", "we recommend", "guaranteed", "beat the market")


def _files() -> dict[str, str]:
    return {name: (PAGE / name).read_text(encoding="utf-8")
            for name in ("portfolio.html", "portfolio-view.css", "portfolio-view.js")}  # fmt: skip


def test_portfolio_page_static() -> None:
    files = _files()
    html, css, script = files["portfolio.html"], files["portfolio-view.css"], files["portfolio-view.js"]
    for name, text in files.items():
        assert not COLOUR_LITERAL.findall(text), (name, COLOUR_LITERAL.findall(text)[:5])
        assert not NETWORK.findall(text), (name, NETWORK.findall(text)[:5])
        lowered = text.lower()
        for phrase in BANNED:
            assert phrase not in lowered, (name, phrase)
    assert not NAMED_COLOUR.findall(css)
    used = set(re.findall(r"var\((--[a-z0-9-]+)", "".join(files.values())))
    light, _, _ = _themes()
    assert used <= set(light), sorted(used - set(light))

    for sheet in ("theme.css", "viewer.css", "portfolio-view.css"):
        assert f'href="{sheet}"' in html, sheet
    assert (
        '<script src="portfolio/portfolio.js"></script>' in html
        and '<script src="portfolio-view.js"></script>' in html
    )
    assert 'href="index.html"' in html  # back to the results page
    for section in SECTIONS:
        assert f'id="{section}"' in html, section
        assert f"#{section}" in html, section  # in the section jump list

    # data handling: one escaping helper, every section copes with "available": false
    assert "function esc(" in script and "window.SBRETIRE_PORTFOLIO" in script
    assert "function unavailable(" in script and script.count("unavailable(") >= 6
    assert "schema_version" in script

    # caveats and definitions the hand-off requires
    text = (html + script).lower()
    for needed in ("analysis, not advice", "cannot be made", "no tax", "volatility", "sharpe ratio"):
        assert needed in text, needed

    # theme and print, as on the results page
    for needed in ('id="theme-toggle"', 'id="pdf-button"', "print-only"):
        assert needed in html, needed
    for needed in ("'sbretire-theme'", "function printPdf(", "window.print()", "function wrapForPrint(",
                   "function unwrapAfterPrint(", "addEventListener('beforeprint', wrapForPrint)",
                   "addEventListener('afterprint', unwrapAfterPrint)", "navigator.clipboard"):  # fmt: skip
        assert needed in script, needed
    assert re.search(r"@page\s*\{[^}]*@top-left\s*\{\s*content:\s*\"SBRetire portfolio\"", css, re.S)
    assert "@media print" in css
