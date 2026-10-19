"""Adversarial input shapes: linear time, short messages, no crash.

Each shape is timed at n and 4n characters; linear code takes about four times as long,
quadratic code sixteen. The best of three runs is compared to keep scheduler noise out.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import pytest

from bytetrunc import (
    BytetruncError,
    chunk_bytes,
    cut_utf8,
    iter_graphemes,
    truncate_bytes,
    truncate_detailed,
    truncate_filename,
    truncate_utf16,
)

N = 40_000
MARK = "\N{COMBINING ACUTE ACCENT}"
ZWJ = "\N{ZERO WIDTH JOINER}"
VIRAMA = "\N{DEVANAGARI SIGN VIRAMA}"
KA = "\N{DEVANAGARI LETTER KA}"
FLAG = "\U0001f1ea"

SHAPES: dict[str, Callable[[int], str]] = {
    "one cluster of marks": lambda n: "e" + MARK * n,
    "regional indicators": lambda n: FLAG * n,
    "emoji zwj chain": lambda n: ("\U0001f468" + ZWJ) * (n // 2),
    "indic conjunct chain": lambda n: (KA + VIRAMA) * (n // 2),
    "hangul jamo": lambda n: "ᄀ" * n,
    "cr lf flood": lambda n: "\r\n" * (n // 2),
    "lone cr flood": lambda n: "\r" * n,
    "astral text": lambda n: "\U0001f600" * n,
    "mixed": lambda n: ("a" + MARK + FLAG + "가" + ZWJ) * (n // 6),
}


def _best(action: Callable[[], object]) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        action()
        best = min(best, time.perf_counter() - start)
    return best


def _scales_linearly(make: Callable[[int], str], use: Callable[[str], object]) -> None:
    small, large = make(N), make(4 * N)
    use(small)  # warm caches before timing
    ratio = _best(lambda: use(large)) / max(_best(lambda: use(small)), 1e-4)
    assert ratio < 10, ratio


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_grapheme_truncation_is_linear(shape: str) -> None:
    make = SHAPES[shape]
    _scales_linearly(make, lambda s: truncate_bytes(s, len(s), suffix="~", on="grapheme"))
    _scales_linearly(make, lambda s: truncate_utf16(s, len(s) // 2, on="grapheme"))


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_segmentation_and_chunks_are_linear(shape: str) -> None:
    make = SHAPES[shape]
    _scales_linearly(make, lambda s: sum(1 for _ in iter_graphemes(s)))
    _scales_linearly(make, lambda s: chunk_bytes(s, 64, encoding="utf-16-le"))


def test_a_cluster_larger_than_a_chunk_is_refused_quickly() -> None:
    def use(s: str) -> object:
        with pytest.raises(BytetruncError, match="grapheme cluster at index 0"):
            chunk_bytes(s, 64, on="grapheme")
        return None

    _scales_linearly(SHAPES["one cluster of marks"], use)


def test_raw_bytes_and_file_names_are_linear() -> None:
    _scales_linearly(lambda n: "\x80" * n, lambda s: cut_utf8(s.encode("latin-1"), len(s) - 1))
    _scales_linearly(lambda n: "." * n + "x", lambda s: truncate_filename("a" + s, 255))
    _scales_linearly(lambda n: "a." * n, lambda s: truncate_filename(s, 255))


def test_messages_stay_short_for_huge_inputs() -> None:
    huge = "x" * 1_000_000
    calls: list[Callable[[], object]] = [
        lambda: truncate_bytes(huge, 1, suffix=huge),
        lambda: truncate_bytes("a", 1, on=huge),  # type: ignore[arg-type]
        lambda: truncate_bytes("a", 1, encoding=huge),
        lambda: truncate_filename(huge + "/", 10),
        lambda: truncate_filename("a" + "." + huge, 10),
        lambda: truncate_detailed("a", -(10**5000)),
        lambda: chunk_bytes(huge + "\U0001f600", 3),
    ]
    for call in calls:
        with pytest.raises(BytetruncError) as caught:
            call()
        assert len(str(caught.value)) < 200


def test_wrong_types_never_echo_their_value() -> None:
    class Loud:
        def __repr__(self) -> str:
            return "x" * 1_000_000

    with pytest.raises(TypeError) as caught:
        truncate_bytes(Loud(), 1)  # type: ignore[arg-type]
    assert len(str(caught.value)) < 100
