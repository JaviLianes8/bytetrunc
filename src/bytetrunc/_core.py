"""Byte-budget truncation of text on safe code point or grapheme boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ._encodings import Encoding, char_cut, check_limit, normalize_encoding
from ._graphemes import grapheme_ends

Boundary = Literal["char", "grapheme"]


def check_boundary(on: str) -> None:
    """Reject an unknown boundary mode."""
    if on not in ("char", "grapheme"):
        raise ValueError(f"on must be 'char' or 'grapheme', got {on!r}")


@dataclass(frozen=True, slots=True)
class Truncation:
    """The outcome of :func:`truncate_detailed`.

    Attributes:
        text: The result, suffix included when the input was cut.
        size: Bytes ``text`` occupies in ``encoding``; always ``<= limit``.
        original_size: Bytes the input occupied in ``encoding``.
        limit: The byte limit that was requested.
        encoding: Canonical name of the encoding used for counting.
        truncated: True when the input did not fit and was shortened.
    """

    text: str
    size: int
    original_size: int
    limit: int
    encoding: str
    truncated: bool


def byte_len(s: str, encoding: Encoding | str = "utf-8") -> int:
    """Return the number of bytes ``s`` occupies in ``encoding`` (UTF-8 by default).

    >>> byte_len("héllo")
    6
    >>> byte_len("héllo", "utf-16-le")
    10
    """
    return len(s.encode(normalize_encoding(encoding)))


def utf16_len(s: str) -> int:
    """Return the length of ``s`` in UTF-16 code units, as JavaScript's ``.length``.

    Characters outside the Basic Multilingual Plane, such as most emoji, count as two.
    Unlike JavaScript, a lone surrogate raises ``UnicodeEncodeError``.

    >>> utf16_len("a😀")
    3
    """
    return len(s.encode("utf-16-le")) // 2


def truncate_detailed(
    s: str,
    max_bytes: int,
    suffix: str = "",
    on: Boundary = "char",
    *,
    encoding: Encoding | str = "utf-8",
) -> Truncation:
    """Like :func:`truncate_bytes` but return a :class:`Truncation` with the byte counts.

    >>> t = truncate_detailed("héllo world", 8, suffix="...")
    >>> t.text, t.size, t.original_size, t.truncated
    ('héll...', 8, 12, True)
    """
    check_limit(max_bytes)
    check_boundary(on)
    enc = normalize_encoding(encoding)
    data = s.encode(enc)
    if len(data) <= max_bytes:
        return Truncation(s, len(data), len(data), max_bytes, enc, False)
    suffix_size = len(suffix.encode(enc))
    budget = max_bytes - suffix_size
    if budget < 0:
        raise ValueError(
            f"suffix needs {suffix_size} bytes in {enc}, more than max_bytes={max_bytes}"
        )
    cut = char_cut(data, 0, budget, enc)
    head = data[:cut].decode(enc)
    if on == "grapheme":
        keep = 0
        for end in grapheme_ends(s):
            if end > len(head):
                break
            keep = end
        cut -= len(head[keep:].encode(enc))
        head = head[:keep]
    return Truncation(head + suffix, cut + suffix_size, len(data), max_bytes, enc, True)


def truncate_bytes(
    s: str,
    max_bytes: int,
    suffix: str = "",
    on: Boundary = "char",
    *,
    encoding: Encoding | str = "utf-8",
) -> str:
    """Shorten ``s`` so its encoding fits within ``max_bytes``.

    The result never splits a code point, and with ``on="grapheme"`` it never splits an
    extended grapheme cluster (UAX #29) either: emoji ZWJ sequences, flags, combining
    marks and Hangul syllables stay whole. When ``s`` already fits it is returned
    unchanged, with no suffix. Otherwise the longest fitting prefix is kept and
    ``suffix`` is appended; the suffix's own bytes count against the budget, so the full
    return value stays within ``max_bytes``.

    ``encoding`` selects how bytes are counted: ``"utf-8"`` (default), ``"utf-16-le"``,
    ``"utf-16-be"``, ``"utf-32-le"`` or ``"utf-32-be"``. UTF-16 never splits a
    surrogate pair.

    Raises ``ValueError`` if ``max_bytes`` is negative, if ``on`` or ``encoding`` is not
    supported, or if ``suffix`` alone cannot fit within ``max_bytes``. A string holding
    lone surrogates raises ``UnicodeEncodeError`` (a ``ValueError``).

    >>> truncate_bytes("héllo world", 6)
    'héllo'
    >>> truncate_bytes("héllo world", 8, suffix="...")
    'héll...'
    """
    return truncate_detailed(s, max_bytes, suffix, on, encoding=encoding).text


def truncate_utf16(s: str, max_units: int, suffix: str = "", on: Boundary = "char") -> str:
    """Shorten ``s`` to at most ``max_units`` UTF-16 code units (JavaScript ``.length``).

    Use it to enforce on the server the same limit a browser ``maxlength`` or a
    JavaScript check applies. A surrogate pair is never split.

    >>> truncate_utf16("ab😀", 3)
    'ab'
    """
    check_limit(max_units, "max_units")
    return truncate_detailed(s, max_units * 2, suffix, on, encoding="utf-16-le").text
