"""F-022.2 / F-022.3 — the common CSS theme and the results viewer page (docs/decisions/viewer.md §1-§2).

Static checks on src/sbretire/web: every decided token is defined for light and dark, text colours meet WCAG
AA (contrast computed from the oklch values), and the page uses only theme tokens and no network.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "src" / "sbretire" / "web"
THEME = WEB / "theme.css"
VIEWER = WEB / "viewer"
DECISION = ROOT / "docs" / "decisions" / "viewer.md"


def _block(css: str, selector: str, after: str = "") -> dict[str, str]:
    """Custom properties declared in the first ``selector { … }`` block found after ``after``."""
    start = css.index(selector, css.index(after) if after else 0)
    body = css[css.index("{", start) + 1 : css.index("}", start)]
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", body))


def _themes() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    css = THEME.read_text(encoding="utf-8")
    light = _block(css, ":root {")
    system_dark = _block(css, ':root:not([data-theme="light"])', "prefers-color-scheme: dark")
    forced_dark = _block(css, ':root[data-theme="dark"]', "@media screen {")
    return light, system_dark, forced_dark


def test_theme_css_defines_decided_tokens() -> None:
    light, system_dark, forced_dark = _themes()
    section = DECISION.read_text(encoding="utf-8").split("## 2.")[0]
    named = set(re.findall(r"`(--[a-z0-9-]+)`", section))
    assert len(named) >= 30
    assert named <= set(light), sorted(named - set(light))
    colours = {token for token in light if token.startswith(("--color-", "--chart-"))}
    assert len(colours) >= 30
    assert colours <= set(system_dark), sorted(colours - set(system_dark))
    assert colours <= set(forced_dark), sorted(colours - set(forced_dark))
    assert system_dark == forced_dark  # the forced dark mode is the same theme as the system one
    text = THEME.read_text(encoding="utf-8")
    assert "@import" not in text and "url(" not in text  # nothing downloaded


def _luminance(oklch: str) -> float:
    """Relative luminance (WCAG) of an opaque ``oklch(L C H)`` colour, via OKLab and linear sRGB."""
    match = re.fullmatch(r"oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)", oklch.strip())
    assert match, oklch
    lightness, chroma, hue = (float(part) for part in match.groups())
    a, b = chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    red = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    green = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    blue = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    red, green, blue = (min(max(channel, 0.0), 1.0) for channel in (red, green, blue))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(first: str, second: str) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


TEXT_PAIRS = [
    (text, ground, 4.5)
    for text in ("--color-text", "--color-text-muted", "--chart-axis-text")
    for ground in ("--color-bg", "--color-surface", "--color-surface-sunken")
] + [
    ("--color-on-accent", "--color-accent", 4.5),
    ("--color-tooltip-text", "--color-tooltip-bg", 4.5),
]
MARK_PAIRS = [
    (mark, "--color-bg", 3.0)
    for mark in (
        "--color-accent",
        "--color-success",
        "--color-warning",
        "--color-failure",
        "--color-focus",
        "--chart-run-a",
        "--chart-run-b",
        "--chart-person-1",
        "--chart-person-2",
        "--chart-both",
        "--chart-fan-median",
    )
]


def test_theme_contrast_meets_aa() -> None:
    light, dark, _ = _themes()
    failures = []
    for mode, tokens in (("light", light), ("dark", dark)):
        for foreground, background, minimum in TEXT_PAIRS + MARK_PAIRS:
            ratio = _contrast(tokens[foreground], tokens[background])
            if ratio < minimum:
                failures.append(f"{mode}: {foreground} on {background} = {ratio:.2f} < {minimum}")
    assert failures == []


COLOUR_LITERAL = re.compile(
    r"#[0-9a-fA-F]{3,8}\b(?![-\w])|\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb|color)\(", re.IGNORECASE
)
NAMED_COLOUR = re.compile(
    r":\s*(?:white|black|red|green|blue|gray|grey|silver|orange|yellow|purple|navy|teal)\b", re.IGNORECASE
)
NETWORK = re.compile(r"fetch\(|XMLHttpRequest|WebSocket|sendBeacon|https?://|//cdn|@import|import\(")


def _page_files() -> dict[str, str]:
    names = ("index.html", "viewer.css", "viewer.js")
    return {name: (VIEWER / name).read_text(encoding="utf-8") for name in names}


def test_viewer_uses_only_theme_tokens() -> None:
    files = _page_files()
    for name, text in files.items():
        assert not COLOUR_LITERAL.findall(text), (name, COLOUR_LITERAL.findall(text)[:5])
        assert not NETWORK.findall(text), (name, NETWORK.findall(text)[:5])
        for leftover in ("theme-instrument", "data-direction", "review-direction", "Design review"):
            assert leftover not in text, (name, leftover)
    assert not NAMED_COLOUR.findall(files["viewer.css"])
    assert 'href="theme.css"' in files["index.html"] and '<script src="runs/runs.js">' in files["index.html"]
    used = set(re.findall(r"var\((--[a-z0-9-]+)", "".join(files.values())))
    light, _, _ = _themes()
    assert used <= set(light), sorted(used - set(light))  # every token the page uses exists in the theme


def test_viewer_reads_budget_tolerance() -> None:
    script = _page_files()["viewer.js"]
    assert "budget_tolerance" in script
    assert "£1 a month" not in script and "£1 tolerance" not in script


def test_viewer_escapes_run_data() -> None:
    """Regression for the F-022.3 security review: data-derived strings found unescaped in the prototype."""
    script = _page_files()["viewer.js"]
    assert "esc(INFLATION_SOURCES[src] || src.replace(/_/g, ' '))" in script
    assert "return isNaN(d) ? esc(iso) :" in script  # F.date fallback
    assert "if (isNaN(d)) return esc(iso) || DASH;" in script  # F.dateTime fallback
    assert "var sex = p.sex ? esc(" in script
    # no unescaped copy of the inflation-source expression is left anywhere
    assert script.count("INFLATION_SOURCES[src] ||") == script.count("esc(INFLATION_SOURCES[src] ||")


def test_viewer_labels_short_income_streams() -> None:
    """B-022.1: a one-month stream is a one-time payment of annual / 12, not a yearly figure."""
    script = _page_files()["viewer.js"]
    assert "function monthsPaid(" in script
    assert "one-time payment" in script and "in total over " in script and " a year" in script
    assert '<th scope="col" class="num">Amount</th>' in script
    assert '<th scope="col" class="num">Per year</th>' not in script


def _print_tokens() -> dict[str, str]:
    css = THEME.read_text(encoding="utf-8")
    return _block(css, ":root, :root[data-theme]", "@media print {")


NEUTRAL = re.compile(r"oklch\(\s*[\d.]+\s+0(?:\.0+)?\s+[\d.]+\s*(?:/\s*[\d.]+\s*)?\)")


def test_print_tokens_are_neutral() -> None:
    """F-023.1: every colour and chart token has a grey (chroma 0) value in print."""
    light, _, _ = _themes()
    printed = _print_tokens()
    colours = {token for token in light if token.startswith(("--color-", "--chart-"))}
    assert colours <= set(printed), sorted(colours - set(printed))
    coloured = {token: value for token, value in printed.items() if not NEUTRAL.fullmatch(value.strip())}
    assert coloured == {}


def test_print_contrast_meets_aa() -> None:
    printed = _print_tokens()
    failures = [
        f"{foreground} on {background} = {ratio:.2f} < {minimum}"
        for foreground, background, minimum in TEXT_PAIRS + MARK_PAIRS
        if (ratio := _contrast(printed[foreground], printed[background])) < minimum
    ]
    assert failures == []


def _print_section(css: str) -> str:
    return css[css.index("@media print {") :]


def test_print_css_layout_rules() -> None:
    """F-023.2: A4 with header/footer, nothing split, screen-only items hidden, print-only items shown."""
    css = _page_files()["viewer.css"]
    assert re.search(r"@page\s*\{\s*size:\s*A4", css)
    assert "@bottom-right" in css and "counter(page)" in css and "counter(pages)" in css
    screen, printed = css[: css.index("@media print {")], _print_section(css)
    assert re.search(r"\.print-only\s*\{\s*display:\s*none", screen)
    assert re.search(r"\.print-keep[^{]*\{[^}]*break-inside:\s*avoid", printed)
    assert re.search(r"\.card[^{]*\{[^}]*break-inside:\s*avoid", printed)
    for hidden in (
        "#pdf-button",
        "#theme-toggle",
        "#pickers",
        ".info",
        ".screen-only",
        ".year-box",
        ".fold > summary",
    ):
        assert hidden in printed, hidden
    assert re.search(r"\.print-only\s*\{\s*display:\s*block", printed)


def test_print_keep_together_script() -> None:
    script = _page_files()["viewer.js"]
    for needed in (
        "function wrapForPrint(",
        "function unwrapAfterPrint(",
        "addEventListener('beforeprint', wrapForPrint)",
        "addEventListener('afterprint', unwrapAfterPrint)",
        "'print-keep'",
        "d.open = true",
        "@top-right",  # the page header with the run names, injected before printing
    ):
        assert needed in script, needed
    html = _page_files()["index.html"]
    assert 'id="print-runs"' in html and "print-only" in html
    assert 'class="screen-only"' in script  # the hover/keyboard help is screen-only


def test_print_year_tables_cover_all_columns() -> None:
    from sbretire.reporting import ANNUAL_COLUMNS

    script = _page_files()["viewer.js"]
    match = re.search(r"var PRINT_YEAR_COLUMNS = (\[\[.*?\]\]);", script, re.S)
    assert match is not None
    groups = json.loads(match.group(1).replace("'", '"'))
    assert len(groups) == 2 and all(group[0] == "year" for group in groups)
    rest = [column for group in groups for column in group[1:]]
    assert sorted(rest) == sorted(set(ANNUAL_COLUMNS) - {"year"}) and len(rest) == len(set(rest))
    assert 'class="print-only year-print"' in script


def test_pdf_button_sets_title_and_prints() -> None:
    """F-023.3: the button names the PDF after the runs, opens the print dialog and restores the title."""
    files = _page_files()
    assert re.search(r'<button id="pdf-button"[^>]*>Save as PDF</button>', files["index.html"])
    script = files["viewer.js"]
    for needed in (
        "function printPdf(",
        "$('#pdf-button').addEventListener('click', printPdf)",
        "document.title = pdfTitle()",
        "window.print()",
        "document.title = savedTitle",
    ):
        assert needed in script, needed
    assert "#pdf-button" in _print_section(files["viewer.css"])
