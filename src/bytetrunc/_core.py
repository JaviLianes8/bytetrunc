"""Byte-budget truncation of text on safe character or grapheme boundaries."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from ._graphemes import iter_graphemes

Boundary = Literal["char", "grapheme"]


def byte_len(s: str) -> int:
    """Return the number of bytes ``s`` occupies when encoded as UTF-8."""
    return len(s.encode("utf-8"))


def truncate_bytes(
    s: str,
    max_bytes: int,
    suffix: str = "",
    on: Boundary = "char",
) -> str:
    """Shorten ``s`` so its UTF-8 encoding fits within ``max_bytes``.

    The result never splits a multi-byte character, and with ``on="grapheme"`` it never
    splits a grapheme cluster either. When ``s`` already fits it is returned unchanged,
    with no suffix. Otherwise ``suffix`` is appended and its own bytes count against the
    budget, so the full return value stays within ``max_bytes``.

    Raises ``ValueError`` if ``max_bytes`` is negative, if ``on`` is not a known boundary,
    or if ``suffix`` alone cannot fit within ``max_bytes``.
    """
    if max_bytes < 0:
        raise ValueError("max_bytes must not be negative")
    if on not in ("char", "grapheme"):
        raise ValueError(f"on must be 'char' or 'grapheme', got {on!r}")
    if byte_len(s) <= max_bytes:
        return s

    budget = max_bytes - byte_len(suffix)
    if budget < 0:
        raise ValueError("suffix does not fit within max_bytes")

    units: Iterable[str] = s if on == "char" else iter_graphemes(s)
    kept: list[str] = []
    used = 0
    for unit in units:
        size = byte_len(unit)
        if used + size > budget:
            break
        kept.append(unit)
        used += size
    return "".join(kept) + suffix
