"""Access to the third-party files that scripts/fetch_upstream.py fetches.

Nothing fetched is committed. data/ucd/MANIFEST.json pins the Unicode 18.0.0 files the
table generator reads; tests/upstream/MANIFEST.json pins the other sources the tests
compare against (UAX #29, RFC 3629 and the Unicode 17.0.0 property files). Every entry
records its URL, fetch date, size and sha256. Tests that read a file skip while it is
absent and fail if it differs from its manifest entry.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
UCD = ROOT / "data" / "ucd"
UPSTREAM = ROOT / "tests" / "upstream"
MANIFEST: dict[str, dict[str, Any]] = json.loads(
    (UCD / "MANIFEST.json").read_text(encoding="utf-8")
)
UPSTREAM_MANIFEST: dict[str, dict[str, Any]] = json.loads(
    (UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8")
)


def ucd_fetched() -> bool:
    """True when every Unicode 18.0.0 file of data/ucd/MANIFEST.json is present."""
    return all((UCD / name).is_file() for name in MANIFEST)


needs_ucd = pytest.mark.skipif(
    not ucd_fetched(), reason="Unicode data not fetched; run python scripts/fetch_upstream.py"
)


def upstream_path(name: str) -> Path:
    """Return a fetched file of tests/upstream, checked against its manifest entry."""
    path = UPSTREAM / name
    if not path.is_file():
        pytest.skip(f"{name} is not fetched; run python scripts/fetch_upstream.py")
    entry = UPSTREAM_MANIFEST[name]
    body = path.read_bytes()
    assert (len(body), hashlib.sha256(body).hexdigest()) == (entry["size"], entry["sha256"])
    return path


def generator() -> ModuleType:
    """Load scripts/gen_ucd_tables.py, the generator of the embedded tables."""
    spec = importlib.util.spec_from_file_location(
        "gen_ucd_tables", ROOT / "scripts" / "gen_ucd_tables.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@cache
def official_cases() -> tuple[tuple[int, tuple[str, ...]], ...]:
    """Every case of the official GraphemeBreakTest.txt as (line, clusters)."""
    cases: list[tuple[int, tuple[str, ...]]] = []
    text = (UCD / "GraphemeBreakTest.txt").read_text(encoding="utf-8")
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        clusters: list[str] = []
        current = ""
        for token in line.split()[1:]:
            if token == "\N{DIVISION SIGN}":
                clusters.append(current)
                current = ""
            elif token != "\N{MULTIPLICATION SIGN}":
                current += chr(int(token, 16))
        cases.append((number, tuple(clusters)))
    return tuple(cases)
