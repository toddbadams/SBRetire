"""F-014 — V1 acceptance guards: constraints, §18 decisions, provenance, acceptance map, README, version."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import sbretire

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "sbretire"
SPEC = (ROOT / "docs" / "SPEC.md").read_text(encoding="utf-8")


def _src_text() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in SRC.glob("*.py")}


def test_src_has_no_tax_network_or_global_randomness() -> None:
    forbidden = {
        "tax logic (SPEC §16)": re.compile(r"\btax\w*|\bhmrc\b|personal_allowance|national_insurance", re.I),
        "network access (SPEC §2)": re.compile(
            r"^\s*(import|from)\s+(requests|urllib|http|socket|ftplib|httpx|aiohttp)\b", re.M
        ),
        "global randomness (SPEC §10.3)": re.compile(
            r"np\.random\.(rand|randn|random|seed|normal|uniform|choice|randint|shuffle|permutation)\("
            r"|^\s*import random\b",
            re.M,
        ),
    }
    hits = [
        f"{name}: {rule}"
        for name, text in _src_text().items()
        for rule, pattern in forbidden.items()
        if pattern.search(text)
    ]
    assert hits == []


# SPEC §18 item (distinctive phrase) -> (decision file, numbered entry)
SPEC_18 = {
    "Exact ONS file/table and age/period mapping": ("data-and-calibration.md", 1),
    "Valuation date and first simulated month": ("simulation-conventions.md", 1),
    "Exact inflation stochastic process and calibration dataset": ("data-and-calibration.md", 2),
    "Within-month cash-flow ordering and death timing": ("simulation-conventions.md", 2),
    "Behavior of each income stream after recipient death": ("configuration.md", 4),
    "Treatment of household-level income and survivor benefits": ("configuration.md", 5),
    "Whether any income is indexed to a measure other than CPI": ("data-and-calibration.md", 3),
    "Horizon-censoring policy and conservative sustainability denominator": ("simulation-conventions.md", 7),
    "Budget and return optimization bounds and tolerances": ("optimization.md", 2),
    "Definition of annual portfolio percentiles and funded probabilities": ("simulation-conventions.md", 8),
}


def test_all_spec_18_decisions_recorded() -> None:
    section = SPEC[SPEC.index("## 18.") : SPEC.index("## 19.")]
    items = [line[2:].strip() for line in section.splitlines() if line.startswith("- ")]
    assert len(items) == len(SPEC_18) == 10
    for phrase, (file_name, entry) in SPEC_18.items():
        assert any(phrase in item for item in items), phrase
        text = (ROOT / "docs" / "decisions" / file_name).read_text(encoding="utf-8")
        assert re.search(rf"^## {entry}\. ", text, re.M), (file_name, entry)
        assert "**Why**" in text
    for path in (ROOT / "docs" / "decisions").glob("*.md"):
        open_items = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("- ") and "SPEC §" in line and "~~" not in line
        ]
        assert open_items == [], (path.name, open_items)


def test_data_provenance_hashes_match() -> None:
    readme = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    raw_files = sorted((ROOT / "data" / "raw").iterdir())
    assert len(raw_files) == 3
    for path in raw_files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest in readme, path.name
    for sidecar in ("ons_mortality.meta.json", "uk_cpi.meta.json"):
        meta = json.loads((ROOT / "data" / sidecar).read_text(encoding="utf-8"))
        raw = ROOT / "data" / meta["raw_file"]
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == meta["raw_sha256"], sidecar
        assert meta.get("retrieved") and (meta.get("publication_date") or meta.get("release_date")), sidecar


def _collected_test_names() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "tests").rglob("test_*.py"):
        names.update(re.findall(r"^def (test_\w+)\(", path.read_text(encoding="utf-8"), re.M))
    return names


def test_acceptance_map_complete() -> None:
    acceptance = (ROOT / "docs" / "acceptance.md").read_text(encoding="utf-8")
    for heading, count in (("### 17.1", 16), ("### 17.2", 9), ("### 17.3", 9)):
        start = SPEC.index(heading)
        following = re.search(r"^#{2,3} ", SPEC[start + 4 :], re.M)
        assert following is not None
        block = SPEC[start : start + 4 + following.start()]
        spec_items = [
            re.sub(r"^(- |\d+\. )", "", line).strip()
            for line in block.splitlines()
            if line.startswith("- ") or re.match(r"\d+\. ", line)
        ]
        assert len(spec_items) == count, heading
        for item in spec_items:
            assert item in acceptance, (heading, item)
    named = set(re.findall(r"`(test_\w+)`", acceptance))
    missing = named - _collected_test_names()
    assert missing == set()
    assert len(named) >= 40


def test_readme_covers_v1_sections() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for heading in ("## Install", "## Configuration", "## Running the model", "## Outputs", "## Assumptions",
                    "## Limitations"):  # fmt: skip
        assert re.search(rf"^{re.escape(heading)}", readme, re.M), heading
    assert "scaffold" not in readme.lower()
    config_keys = (
        "currency", "as_of_date", "simulation_count", "confidence_levels", "frequency", "horizon_years",
        "random_seed", "unknown_keys", "starting_balance", "annual_return", "monthly_amount_today",
        "survivor_budget_factor", "source_period", "data_file", "log_mean", "ar1_coefficient",
        "innovation_sd", "initial_rate", "geography", "projection", "date_of_birth", "sex", "start_date",
        "end_date",
        "annual_amount_today", "inflation_linked", "survivor_percentage", "recipient",
    )  # fmt: skip
    for key in config_keys:
        assert f"`{key}`" in readme, key
    for column_file in ("annual_results.csv", "sustainability_results.csv", "lifestyle_results.csv"):
        assert f"### `{column_file}`" in readme


def test_version_is_1_0_0() -> None:
    assert sbretire.__version__ == "1.0.0"
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'^version = "1\.0\.0"$', pyproject, re.M)
    version = subprocess.run(
        [sys.executable, "-m", "sbretire", "--version"], capture_output=True, text=True, check=True
    ).stdout
    assert "1.0.0" in version
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"^## \[1\.0\.0\] - \d{4}-\d{2}-\d{2}", changelog, re.M)


PROBE_VIOLATIONS = (
    "income_tax = 0.2",
    "def apply_tax(x): ...",
    "rates = np.random.lognormal(0, 1, 5)",
    "draws = np.random.exponential(1.0)",
    "n = np.random.binomial(10, 0.5)",
    "x = numpy.random.normal()",
    "import numpy.random as npr",
    "from random import random",
    "import urllib3",
    "import os, socket",
)


def test_constraint_guard_catches_probe_patterns() -> None:
    for probe in PROBE_VIOLATIONS:
        assert _constraint_violations(probe), probe
    for name, text in _src_text().items():
        assert _constraint_violations(text) == [], name


def _readme_table(readme: str, file_name: str) -> str:
    start = readme.index(f"### `{file_name}`")
    following = re.search(r"^#{2,3} ", readme[start + 4 :], re.M)
    return readme[start : start + 4 + following.start()] if following else readme[start:]


def test_readme_documents_every_output_column() -> None:
    from sbretire.reporting import ANNUAL_COLUMNS, LIFESTYLE_COLUMNS, SUSTAINABILITY_COLUMNS

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for file_name, columns in (
        ("annual_results.csv", ANNUAL_COLUMNS),
        ("sustainability_results.csv", SUSTAINABILITY_COLUMNS),
        ("lifestyle_results.csv", LIFESTYLE_COLUMNS),
    ):
        table = _readme_table(readme, file_name)
        missing = [column for column in columns if f"`{column}`" not in table]
        assert missing == [], (file_name, missing)
