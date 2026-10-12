"""The embedded tables must equal a fresh run of the generator over the UCD snapshot."""

from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent
UCD = ROOT / "data" / "ucd"
PACKAGE = ROOT / "src" / "bytetrunc"


def _generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "gen_ucd_tables", ROOT / "scripts" / "gen_ucd_tables.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_tables_equal_generator_output() -> None:
    files = _generator().render(UCD)
    assert files, "generator produced nothing"
    for name, text in files.items():
        assert (PACKAGE / name).read_text(encoding="utf-8") == text, f"{name} is stale"


def test_no_stray_generated_parts() -> None:
    expected = set(_generator().render(UCD))
    present = {p.name for p in PACKAGE.glob("_ucd_part*.py")} | {"_ucd_data.py"}
    assert present == expected


def test_generated_modules_stay_short() -> None:
    for name in _generator().render(UCD):
        assert len((PACKAGE / name).read_text(encoding="utf-8").splitlines()) <= 200


def test_snapshot_checksums_match_sources_record() -> None:
    record = (UCD / "SOURCES.txt").read_text(encoding="utf-8")
    listed = dict(
        (name, digest) for digest, name in re.findall(r"^\s+([0-9a-f]{64})\s+(\S+)$", record, re.M)
    )
    assert set(listed) == {
        "GraphemeBreakTest.txt",
        "GraphemeBreakProperty.txt",
        "emoji-data.txt",
        "DerivedCoreProperties.txt",
    }
    for name, digest in listed.items():
        data = (UCD / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest, name


def test_spot_properties_from_the_tables() -> None:
    from bytetrunc._ucd import EXT_PICT_BIT, GCB, prop

    assert prop(0x0D) & 0x0F == GCB["CR"]
    assert prop(0x0301) & 0x0F == GCB["Extend"]
    assert prop(0x200D) & 0x0F == GCB["ZWJ"]
    assert prop(0x1F1E6) & 0x0F == GCB["Regional_Indicator"]
    assert prop(0xAC00) & 0x0F == GCB["LV"]
    assert prop(0xAC01) & 0x0F == GCB["LVT"]
    assert prop(0x1F600) & EXT_PICT_BIT
    assert prop(0x0915) >> 5 == 2  # DEVANAGARI LETTER KA is InCB=Consonant
    assert prop(0x094D) >> 5 == 1  # DEVANAGARI SIGN VIRAMA is InCB=Linker
    assert prop(0x10FFFF) & 0x0F == GCB["Other"]
