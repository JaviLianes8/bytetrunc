"""Byte-budget truncation of text on safe code point or grapheme boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, SupportsIndex

from ._encodings import Encoding, char_cut, normalize_encoding
from ._errors import BytetruncError, check_limit, check_text, preview, type_name
from ._graphemes import grapheme_ends

Boundary = Literal["char", "grapheme"]


def check_boundary(on: object) -> Boundary:
    """Return ``on`` as one of the two boundary names or raise."""
    if not issubclass(type(on), str):
        raise TypeError(f"on must be a str, got {type_name(on)}")
    name = str.__str__(on)
    if name not in ("char", "grapheme"):
        raise BytetruncError(f"on must be 'char' or 'grapheme', got {preview(name)}")
    return name  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class Truncation:
    """The outcome of :func:`truncate_detailed`, with the byte counts.

    Attributes:
        text: The result, suffix included when the input was cut.
        size: Bytes ``text`` occupies in ``encoding``; never more than ``limit``.
        original_size: Bytes the input occupied in ``encoding``.
        limit: The byte limit that was requested, as an ``int``.
        encoding: Canonical name of the encoding used for counting.
        truncated: True when the input did not fit and was shortened.

    >>> from bytetrunc import truncate_detailed
    >>> truncate_detailed("héllo world", 8, suffix="...")
    Truncation(text='héll...', size=8, original_size=12, limit=8, encoding='utf-8', truncated=True)
    """

    text: str
    size: int
    original_size: int
    limit: int
    encoding: Encoding
    truncated: bool


Truncation.__module__ = "bytetrunc"


def byte_len(s: str, encoding: Encoding | str = "utf-8") -> int:
    """Return the number of bytes ``s`` occupies in ``encoding`` (UTF-8 by default).

    >>> from bytetrunc import byte_len
    >>> byte_len("héllo")
    6
    >>> byte_len("héllo", "utf-16-le")
    10
    """
    text = check_text(s, "s")
    return len(text.encode(normalize_encoding(encoding)))


def utf16_len(s: str) -> int:
    """Return the length of ``s`` in UTF-16 code units, the number JavaScript's
    ``.length`` reports.

    Characters outside the Basic Multilingual Plane, such as most emoji, count as two.
    Unlike JavaScript, a lone surrogate raises :class:`UnicodeEncodeError`.

    >>> from bytetrunc import utf16_len
    >>> utf16_len("a😀")
    3
    """
    return len(check_text(s, "s").encode("utf-16-le")) // 2


def _cut(text: str, limit: int, suffix: str, on: Boundary, enc: Encoding, unit: int) -> Truncation:
    data = text.encode(enc)
    suffix_size = len(suffix.encode(enc))
    if len(data) <= limit:
        return Truncation(text, len(data), len(data), limit, enc, False)
    budget = limit - suffix_size
    if budget < 0:
        need = f"{suffix_size} bytes in {enc}" if unit == 1 else f"{suffix_size // 2} UTF-16 units"
        name = "max_bytes" if unit == 1 else "max_units"
        raise BytetruncError(f"suffix needs {need}, more than {name}={limit // unit}")
    cut = char_cut(data, 0, budget, enc)
    head = data[:cut].decode(enc)
    if on == "grapheme":
        keep = 0
        for end in grapheme_ends(text):
            if end > len(head):
                break
            keep = end
        cut -= len(head[keep:].encode(enc))
        head = head[:keep]
    return Truncation(head + suffix, cut + suffix_size, len(data), limit, enc, True)


def truncate_detailed(
    s: str,
    max_bytes: SupportsIndex,
    *,
    suffix: str = "",
    on: Boundary = "char",
    encoding: Encoding | str = "utf-8",
) -> Truncation:
    """Like :func:`truncate_bytes`, but return a :class:`Truncation` with the byte counts.

    >>> from bytetrunc import truncate_detailed
    >>> t = truncate_detailed("héllo world", 8, suffix="...")
    >>> t.text, t.size, t.original_size, t.truncated
    ('héll...', 8, 12, True)
    """
    text = check_text(s, "s")
    limit = check_limit(max_bytes, "max_bytes")
    tail = check_text(suffix, "suffix")
    return _cut(text, limit, tail, check_boundary(on), normalize_encoding(encoding), 1)


def truncate_bytes(
    s: str,
    max_bytes: SupportsIndex,
    *,
    suffix: str = "",
    on: Boundary = "char",
    encoding: Encoding | str = "utf-8",
) -> str:
    """Shorten ``s`` so its encoding fits within ``max_bytes``.

    The result never splits a code point, and with ``on="grapheme"`` it never splits an
    extended grapheme cluster (UAX #29) either: emoji ZWJ sequences, flags, combining
    marks and Hangul syllables stay whole. When ``s`` already fits it is returned as it
    is, with no suffix. Otherwise the longest prefix that fits is kept and ``suffix`` is
    appended; the suffix's own bytes count against the budget, so the whole result stays
    within ``max_bytes``. The result is always a plain ``str``.

    ``encoding`` selects how bytes are counted: ``"utf-8"`` (default), ``"utf-16-le"``,
    ``"utf-16-be"``, ``"utf-32-le"`` or ``"utf-32-be"``. UTF-16 never splits a
    surrogate pair. ``max_bytes`` may be any integer type with ``__index__``.

    Raises :class:`~bytetrunc.BytetruncError` if ``max_bytes`` is negative, if ``on``
    or ``encoding`` is not supported, or if ``s`` does not fit and ``suffix`` alone is
    larger than ``max_bytes``; :class:`TypeError` for arguments of the wrong type; and
    :class:`UnicodeEncodeError` if ``s`` or ``suffix`` holds a lone surrogate.

    >>> from bytetrunc import truncate_bytes
    >>> truncate_bytes("héllo world", 6)
    'héllo'
    >>> truncate_bytes("héllo world", 8, suffix="...")
    'héll...'
    >>> truncate_bytes("man\\u0303ana", 4, on="grapheme")
    'ma'
    """
    return truncate_detailed(s, max_bytes, suffix=suffix, on=on, encoding=encoding).text


def truncate_utf16(
    s: str, max_units: SupportsIndex, *, suffix: str = "", on: Boundary = "char"
) -> str:
    """Shorten ``s`` to at most ``max_units`` UTF-16 code units (JavaScript ``.length``).

    Use it to enforce on the server the same limit a browser ``maxlength`` or a
    JavaScript check applies. A surrogate pair is never split, and ``suffix`` counts
    against the limit as in :func:`truncate_bytes`.

    >>> from bytetrunc import truncate_utf16
    >>> truncate_utf16("ab😀", 3)
    'ab'
    """
    text = check_text(s, "s")
    units = check_limit(max_units, "max_units")
    tail = check_text(suffix, "suffix")
    return _cut(text, units * 2, tail, check_boundary(on), "utf-16-le", 2).text
