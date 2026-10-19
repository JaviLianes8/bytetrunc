"""Seeded fuzzing of every mode and encoding against the stated invariants."""

from __future__ import annotations

import random

import pytest

from bytetrunc import (
    ENCODINGS,
    Boundary,
    BytetruncError,
    chunk_bytes,
    cut_utf8,
    iter_graphemes,
    truncate_bytes,
    truncate_detailed,
)
from bytetrunc._graphemes import grapheme_ends

POOL = [
    "a",
    "Z",
    " ",
    "\r",
    "\n",
    "\t",
    "\x00",
    "\u00e9",
    "e\u0301",
    "\u0301",
    "\u4f60",
    "\U0001f600",
    "\U0001f468",
    "\u200d",
    "\U0001f3fd",
    "\U0001f1ea",
    "\U0001f1f8",
    "\u1100",
    "\u1161",
    "\u11a8",
    "\uac00",
    "\uac01",
    "\u0915",
    "\u094d",
    "\u0924",
    "\u093f",
    "\u0903",
    "\u0600",
    "\ufe0f",
    "\U000e0067",
    "\U0001f3f4",
    "\u2764",
    "\U0010fffd",
    "\ud7ff",
    "\ue000",
    "\u00ad",
    "\u0e33",
    "\U0001f9d1",
]
SUFFIXES = ["", "...", "\u2026", "~"]
SEED = 20261012
BOUNDARIES: tuple[Boundary, ...] = ("char", "grapheme")


def _random_text(rng: random.Random) -> str:
    parts: list[str] = []
    for _ in range(rng.randrange(0, 24)):
        if rng.random() < 0.15:
            cp = rng.randrange(0x110000)
            parts.append(chr(cp) if not 0xD800 <= cp <= 0xDFFF else "x")
        else:
            parts.append(rng.choice(POOL))
    return "".join(parts)


def _cases(count: int) -> list[tuple[str, str, Boundary, int, str]]:
    rng = random.Random(SEED)
    cases: list[tuple[str, str, Boundary, int, str]] = []
    for _ in range(count):
        text = _random_text(rng)
        enc = rng.choice(ENCODINGS)
        size = len(text.encode(enc))
        cases.append(
            (text, enc, rng.choice(BOUNDARIES), rng.randrange(size + 3), rng.choice(SUFFIXES))
        )
    return cases


CASES = _cases(3000)


def test_truncation_invariants() -> None:
    for text, enc, on, limit, suffix in CASES:
        size = len(text.encode(enc))
        if len(suffix.encode(enc)) > limit and size > limit:
            with pytest.raises(BytetruncError):
                truncate_detailed(text, limit, suffix=suffix, on=on, encoding=enc)
            continue
        result = truncate_detailed(text, limit, suffix=suffix, on=on, encoding=enc)
        encoded = result.text.encode(enc)
        assert len(encoded) == result.size <= limit
        assert result.original_size == size
        if size <= limit:
            assert (result.text, result.truncated) == (text, False)
            continue
        assert result.truncated and result.text.endswith(suffix)
        head = result.text[: len(result.text) - len(suffix)]
        assert text.startswith(head)
        assert text.encode(enc).startswith(head.encode(enc))
        units = list(text) if on == "char" else list(iter_graphemes(text))
        ends = [0]
        for unit in units:
            ends.append(ends[-1] + len(unit))
        assert len(head) in ends, "result does not end on a boundary"
        nxt = ends[ends.index(len(head)) + 1]
        budget = limit - len(suffix.encode(enc))
        assert len(text[:nxt].encode(enc)) > budget, "result is not the longest prefix"


def test_truncate_bytes_equals_detailed_text() -> None:
    for text, enc, on, limit, _ in CASES[:500]:
        assert (
            truncate_bytes(text, limit, on=on, encoding=enc)
            == truncate_detailed(text, limit, on=on, encoding=enc).text
        )


def test_chunk_invariants() -> None:
    rng = random.Random(SEED + 1)
    for text, enc, on, _, _ in CASES[:1500]:
        limit = rng.randrange(4, 40)
        try:
            pieces = chunk_bytes(text, limit, on=on, encoding=enc)
        except BytetruncError:
            units = list(text) if on == "char" else list(iter_graphemes(text))
            assert any(len(u.encode(enc)) > limit for u in units)
            continue
        assert "".join(pieces) == text
        boundaries = set(grapheme_ends(text)) if on == "grapheme" else set(range(len(text) + 1))
        position = 0
        for piece in pieces:
            assert 0 < len(piece.encode(enc)) <= limit
            position += len(piece)
            assert position in boundaries


def test_cut_utf8_matches_text_truncation() -> None:
    rng = random.Random(SEED + 2)
    for text, *_ in CASES:
        data = text.encode("utf-8")
        limit = rng.randrange(len(data) + 2)
        cut = cut_utf8(data, limit)
        assert data.startswith(cut) and len(cut) <= limit
        assert cut.decode("utf-8") == truncate_bytes(text, limit)
        assert cut_utf8(data[:limit]) == cut


def test_segmentation_concatenates_back() -> None:
    for text, *_ in CASES:
        clusters = list(iter_graphemes(text))
        assert "".join(clusters) == text
        assert all(clusters)
