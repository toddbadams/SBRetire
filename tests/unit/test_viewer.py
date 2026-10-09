"""F-022.2 / F-022.3 — the common CSS theme and the results viewer page (docs/decisions/viewer.md §1-§2).

Static checks on src/sbretire/web: every decided token is defined for light and dark, text colours meet WCAG
AA (contrast computed from the oklch values), and the page uses only theme tokens and no network.
"""

from __future__ import annotations

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
