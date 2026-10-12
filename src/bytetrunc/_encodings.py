"""Supported encodings and code point safe cut positions in encoded bytes."""

from __future__ import annotations

import codecs
from typing import Literal

Encoding = Literal["utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"]
ENCODINGS: tuple[str, ...] = ("utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be")


def normalize_encoding(encoding: str) -> str:
    """Return the canonical name of a supported encoding or raise ``ValueError``.

    Aliases such as ``"UTF8"`` or ``"utf_16_le"`` are accepted. Byte order mark
    encodings (``"utf-16"``, ``"utf-32"``, ``"utf-8-sig"``) are rejected because the
    mark would change the byte count in a way callers rarely expect.
    """
    if not isinstance(encoding, str):
        raise TypeError(f"encoding must be a str, got {type(encoding).__name__}")
    try:
        name = codecs.lookup(encoding).name
    except LookupError:
        name = ""
    if name not in ENCODINGS:
        supported = ", ".join(ENCODINGS)
        raise ValueError(f"unsupported encoding {encoding!r}; use one of: {supported}")
    return name


def check_limit(value: int, name: str = "max_bytes") -> None:
    """Reject a negative or non-integer limit with a clear message."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must not be negative, got {value}")


def char_cut(data: bytes, start: int, limit: int, encoding: str) -> int:
    """Return the largest end ``<= start + limit`` that falls on a code point boundary.

    ``data`` must be the encoding of a string in ``encoding`` and ``start`` must be on a
    boundary. The result is never past ``len(data)``.
    """
    end = min(len(data), start + limit)
    if end == len(data):
        return end
    if encoding == "utf-8":
        while end > start and data[end] & 0xC0 == 0x80:
            end -= 1
        return end
    width = 2 if encoding.startswith("utf-16") else 4
    end -= (end - start) % width
    if width == 2 and end > start:
        high = data[end - 1] if encoding == "utf-16-le" else data[end - 2]
        if 0xD8 <= high <= 0xDB:
            end -= 2
    return end


def _sequence_length(lead: int) -> int:
    if lead < 0x80:
        return 1
    if lead >> 5 == 0b110:
        return 2
    if lead >> 4 == 0b1110:
        return 3
    if lead >> 3 == 0b11110:
        return 4
    return 1


def cut_utf8(data: bytes | bytearray | memoryview, max_bytes: int | None = None) -> bytes:
    """Cut raw UTF-8 ``data`` to at most ``max_bytes`` without ending mid-sequence.

    Works on bytes without decoding them, which suits network reads, fixed-size
    records and buffers that may stop in the middle of a character. With
    ``max_bytes=None`` only an incomplete trailing sequence is dropped. The result is
    always a prefix of ``data``.

    Only the cut point is inspected: when ``data`` is valid UTF-8, possibly ending in an
    incomplete sequence, the result is valid UTF-8. Invalid bytes elsewhere are kept
    as they are; decode with ``errors="strict"`` if you need to reject them.

    >>> cut_utf8("héllo".encode(), 2)
    b'h'
    >>> cut_utf8(b"abc\\xe2\\x82")
    b'abc'
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"data must be bytes-like, got {type(data).__name__}")
    if isinstance(data, memoryview):
        data = data.cast("B")
    if max_bytes is not None:
        check_limit(max_bytes)
    end = len(data) if max_bytes is None else min(len(data), max_bytes)
    lead = end - 1
    while lead >= 0 and end - lead < 4 and data[lead] & 0xC0 == 0x80:
        lead -= 1
    if lead < 0 or data[lead] & 0xC0 == 0x80:
        return bytes(data[:end])
    if lead + _sequence_length(data[lead]) > end:
        return bytes(data[:lead])
    return bytes(data[:end])
