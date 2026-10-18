"""The embedded tables must equal a fresh run of the generator over the fetched UCD files."""

from __future__ import annotations

import hashlib

from conftest import MANIFEST, ROOT, UCD, generator, needs_ucd

PACKAGE = ROOT / "src" / "bytetrunc"


@needs_ucd
def test_committed_tables_equal_generator_output() -> None:
    files = generator().render(UCD)
    assert files, "generator produced nothing"
    for name, text in files.items():
        assert (PACKAGE / name).read_text(encoding="utf-8") == text, f"{name} is stale"


@needs_ucd
def test_no_stray_generated_parts() -> None:
    expected = set(generator().render(UCD))
    present = {p.name for p in PACKAGE.glob("_ucd_part*.py")} | {"_ucd_data.py"}
    assert present == expected


@needs_ucd
def test_generated_modules_stay_short() -> None:
    for name in generator().render(UCD):
        assert len((PACKAGE / name).read_text(encoding="utf-8").splitlines()) <= 200


@needs_ucd
def test_snapshot_files_match_the_manifest() -> None:
    assert {p.name for p in UCD.glob("*.txt")} == set(MANIFEST)
    for name, entry in MANIFEST.items():
        data = (UCD / name).read_bytes()
        assert (len(data), hashlib.sha256(data).hexdigest()) == (entry["size"], entry["sha256"])


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
