"""bytetrunc against independent implementations, run live when they are installed.

- The ``regex`` module (``\\X``): 2026.9.29 and later state Unicode 18.0.0 support.
- Node.js: ``Intl.Segmenter`` (ICU), ``TextEncoder.encodeInto`` (WHATWG Encoding, which
  writes only whole code points) and ``String.prototype.length`` (UTF-16 code units).

Both segmenters still apply the GB9c rule of Unicode 17, which UAX #29 revision 49 changed,
so texts with an InCB=Linker character are left out of the segmentation comparisons; that
rule is checked against the official test file instead. For an implementation on Unicode
17.0 the code points whose properties changed in 18.0 are left out as well, computed from
the 17.0.0 files pinned in tests/upstream/MANIFEST.json.
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess
from functools import cache
from typing import Any

import pytest
from conftest import UCD, generator, ucd_fetched, upstream_path
from uax29_reference import random_text, representatives

from bytetrunc import byte_len, iter_graphemes, truncate_bytes, truncate_utf16, utf16_len
from bytetrunc._ucd import INCB_SHIFT, prop

NODE = shutil.which("node")
SEED = 20261018


@cache
def changed_since_17() -> frozenset[int]:
    if not ucd_fetched():
        pytest.skip("Unicode data not fetched; run python scripts/fetch_upstream.py")
    folder = upstream_path("ucd-17.0.0/GraphemeBreakProperty.txt").parent
    for name in ("emoji-data.txt", "DerivedCoreProperties.txt"):
        upstream_path(f"ucd-17.0.0/{name}")
    gen = generator()
    new, old = gen.property_codes(UCD), gen.property_codes(folder)
    return frozenset(cp for cp in range(0x110000) if new[cp] != old[cp])


def _texts(count: int, excluded: frozenset[int]) -> list[str]:
    rng = random.Random(SEED)
    pool = [ch for ch in representatives(rng) if ord(ch) not in excluded]
    texts: list[str] = []
    while len(texts) < count:
        text = random_text(rng, pool, 16)
        if all(ord(ch) not in excluded and (prop(ord(ch)) >> INCB_SHIFT) & 3 != 1 for ch in text):
            texts.append(text)
    return texts


def test_regex_module_finds_the_same_clusters() -> None:
    regex = pytest.importorskip("regex")
    on_18 = regex.match(r"\p{Grapheme_Cluster_Break=Extend}", "\U000005c8") is not None
    excluded = frozenset() if on_18 else changed_since_17()
    cluster = regex.compile(r"\X")
    for text in _texts(20000, excluded):
        assert cluster.findall(text) == list(iter_graphemes(text)), ascii(text)


def _node(program: str, payload: object) -> list[Any]:
    if NODE is None:
        pytest.skip("Node.js is not installed")
    done = subprocess.run(
        [NODE, "-e", program],
        input=json.dumps(payload).encode(),
        capture_output=True,
        timeout=300,
        check=True,
    )
    result: list[Any] = json.loads(done.stdout.decode("utf-8"))
    return result


READ = "const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
WRITE = "process.stdout.write(JSON.stringify(out));"


def test_node_text_encoder_writes_the_same_whole_code_points() -> None:
    rng = random.Random(SEED + 1)
    cases = [(text, rng.randrange(byte_len(text) + 2)) for text in _texts(4000, frozenset())]
    program = f"""{READ}
const enc = new TextEncoder();
const out = input.map(([s, n]) => {{ const r = enc.encodeInto(s, new Uint8Array(n));
  return [r.read, r.written]; }}); {WRITE}"""
    for (text, limit), (read, written) in zip(cases, _node(program, cases), strict=True):
        cut = truncate_bytes(text, limit)
        assert (utf16_len(cut), byte_len(cut)) == (read, written), ascii(text)


def test_node_string_length_is_utf16_len() -> None:
    texts = _texts(4000, frozenset())
    out = _node(f"{READ} const out = input.map((s) => s.length); {WRITE}", texts)
    assert out == [utf16_len(text) for text in texts]


def test_node_truncates_utf16_units_the_same_way() -> None:
    rng = random.Random(SEED + 2)
    cases = [(text, rng.randrange(utf16_len(text) + 2)) for text in _texts(4000, frozenset())]
    program = f"""{READ}
const out = input.map(([s, n]) => {{ let r = ''; for (const c of s) {{
  if (r.length + c.length > n) break; r += c; }} return r; }}); {WRITE}"""
    assert _node(program, cases) == [truncate_utf16(text, n) for text, n in cases]


def test_node_intl_segmenter_finds_the_same_clusters_and_cuts() -> None:
    if NODE is None:
        pytest.skip("Node.js is not installed")
    version = subprocess.run(
        [NODE, "-p", "process.versions.unicode"], capture_output=True, text=True, check=True
    ).stdout.strip()
    if version not in ("17.0", "18.0"):
        pytest.skip(f"Node.js reports Unicode {version}; this comparison knows 17.0 and 18.0")
    excluded = frozenset() if version == "18.0" else changed_since_17()
    rng = random.Random(SEED + 3)
    cases = [(text, rng.randrange(byte_len(text) + 2)) for text in _texts(6000, excluded)]
    program = f"""{READ}
const seg = new Intl.Segmenter('en', {{ granularity: 'grapheme' }});
const enc = new TextEncoder();
const out = input.map(([s, n]) => {{ const parts = Array.from(seg.segment(s), (x) => x.segment);
  let cut = '', size = 0; for (const p of parts) {{ const b = enc.encode(p).length;
    if (size + b > n) break; cut += p; size += b; }}
  return [parts, cut]; }}); {WRITE}"""
    for (text, limit), (parts, cut) in zip(cases, _node(program, cases), strict=True):
        assert parts == list(iter_graphemes(text)), ascii(text)
        assert cut == truncate_bytes(text, limit, on="grapheme"), ascii(text)
