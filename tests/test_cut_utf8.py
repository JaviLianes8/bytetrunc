"""cut_utf8 against the UTF-8 grammar of RFC 3629 and against CPython's own decoder.

The grammar is read from tests/upstream/rfc3629.txt (fetched by scripts/fetch_upstream.py,
pinned in tests/upstream/MANIFEST.json). The decoder check needs nothing fetched: an
incremental decoder holds back exactly the bytes that may still become a character.
"""

from __future__ import annotations

import codecs
import itertools
import random
import re
from array import array

import pytest
from conftest import upstream_path

from bytetrunc import cut_utf8

# Bytes at the edges of every range in the grammar, for the longer exhaustive walks.
EDGES = bytes.fromhex("00417f808f909fa0bfc0c1c2dfe0e1ecedeeeff0f1f3f4f5ff")


def _grammar() -> list[list[range]]:
    """Every alternative of UTF8-char in RFC 3629 section 4, as a list of byte ranges."""
    text = upstream_path("rfc3629.txt").read_text(encoding="utf-8")
    block = text[text.index("UTF8-1      =") : text.index("UTF8-tail   =")]
    rules = dict(re.findall(r"(UTF8-[1-4])\s*=\s*(.*?)(?=UTF8-[1-4]\s*=|\Z)", block, re.S))
    alternatives: list[list[range]] = []
    for body in rules.values():
        for alternative in body.split("/"):
            ranges: list[range] = []
            for count, token in re.findall(
                r"(?:(\d)\(\s*)?(%x[0-9A-F]{2}(?:-[0-9A-F]{2})?|UTF8-tail)", alternative
            ):
                if token == "UTF8-tail":
                    low, high = 0x80, 0xBF
                else:
                    low_text, _, high_text = token[2:].partition("-")
                    low, high = int(low_text, 16), int(high_text or low_text, 16)
                ranges.extend([range(low, high + 1)] * int(count or 1))
            alternatives.append(ranges)
    return alternatives


def _grammar_cut(data: bytes, alternatives: list[list[range]]) -> bytes:
    for size in (1, 2, 3):
        tail = data[-size:] if len(data) >= size else b""
        if tail and any(
            len(tail) < len(alt) and all(b in r for b, r in zip(tail, alt, strict=False))
            for alt in alternatives
        ):
            return data[:-size]
    return data


def _decoder_cut(data: bytes) -> bytes:
    for size in (1, 2, 3):
        if len(data) < size:
            break
        decoder = codecs.getincrementaldecoder("utf-8")()
        try:
            held = decoder.decode(data[-size:], final=False) == "" and decoder.getstate()[0]
        except UnicodeDecodeError:
            held = b""
        if held == data[-size:]:
            if size == 2 and data[-2] == 0xED and data[-1] >= 0xA0:
                # CPython also holds back the start of an encoded surrogate, for its
                # surrogatepass handler; strict UTF-8 rejects every way to finish it.
                assert all(_strict_rejects(held + bytes([c])) for c in range(0x80, 0xC0))
                return data
            return data[:-size]
    return data


def _strict_rejects(data: bytes) -> bool:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def _inputs() -> list[bytes]:
    found = [bytes([a]) for a in range(256)]
    found += [bytes(pair) for pair in itertools.product(range(256), repeat=2)]
    # cut_utf8 never reads further back than three bytes, nor do the two references.
    found += [bytes(combo) for combo in itertools.product(EDGES, repeat=3)]
    return found


def test_the_grammar_read_from_the_rfc_has_its_nine_forms() -> None:
    sizes = sorted(len(alternative) for alternative in _grammar())
    assert sizes == [1, 2, 3, 3, 3, 3, 4, 4, 4]


def test_cut_points_follow_the_rfc_3629_grammar() -> None:
    alternatives = _grammar()
    for data in _inputs():
        assert cut_utf8(data) == _grammar_cut(data, alternatives), data.hex()
        assert cut_utf8(b"ok" + data) == b"ok" + _grammar_cut(data, alternatives), data.hex()


def test_cut_points_match_what_cpython_holds_back() -> None:
    for data in _inputs():
        assert cut_utf8(data) == _decoder_cut(data), data.hex()


def test_limits_on_valid_text_keep_every_whole_character() -> None:
    rng = random.Random(3629)
    for _ in range(3000):
        text = "".join(
            chr(rng.choice([0x41, 0xE9, 0x20AC, 0x1F600, rng.randrange(0x10FFFF)]))
            for _ in range(rng.randrange(12))
        )
        data = text.encode("utf-8", "replace")
        for limit in range(len(data) + 2):
            decoded = codecs.getincrementaldecoder("utf-8")().decode(data[:limit], final=False)
            assert cut_utf8(data, limit) == decoded.encode(), (data.hex(), limit)


def test_invalid_bytes_at_the_end_are_kept() -> None:
    for tail in ("c0", "c1", "e080", "eda0", "f08f", "f490", "f5", "ff", "80", "c3a9a9"):
        assert cut_utf8(b"ab" + bytes.fromhex(tail)) == b"ab" + bytes.fromhex(tail)
    for tail in ("c3", "e2", "e282", "f0", "f09f", "f09f98", "f48f", "ed"):
        assert cut_utf8(b"ab" + bytes.fromhex(tail)) == b"ab"


@pytest.mark.parametrize(
    "data",
    [
        bytearray("h\N{LATIN SMALL LETTER E WITH ACUTE}llo \U0001f600".encode()),
        memoryview("h\N{LATIN SMALL LETTER E WITH ACUTE}llo \U0001f600".encode()),
        memoryview(array("H", [0x68C3, 0xA96C])),
        memoryview(bytes(range(256)))[::3],
        memoryview(bytes(range(240))).cast("B", (2, 120)),
    ],
    ids=["bytearray", "memoryview", "two-byte items", "strided", "two-dimensional"],
)
def test_every_bytes_like_form_is_read_as_its_raw_bytes(data: bytearray | memoryview) -> None:
    raw = bytes(data)
    for limit in [None, *range(len(raw) + 1)]:
        assert cut_utf8(data, limit) == cut_utf8(raw, limit)
