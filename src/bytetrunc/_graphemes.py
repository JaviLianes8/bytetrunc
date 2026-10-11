"""Pragmatic grapheme cluster segmentation built on the standard library."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterator

_ZWJ = "‍"
_MARK_CATEGORIES = frozenset({"Mn", "Mc", "Me"})


def _is_extend(ch: str) -> bool:
    """A combining mark or variation selector that attaches to the base before it."""
    return unicodedata.combining(ch) != 0 or unicodedata.category(ch) in _MARK_CATEGORIES


def _is_regional(ch: str) -> bool:
    """A regional indicator symbol: two of them form one flag."""
    return 0x1F1E6 <= ord(ch) <= 0x1F1FF


def iter_graphemes(s: str) -> Iterator[str]:
    """Yield user-perceived characters, keeping marks, joiners and flags attached.

    This covers the common boundaries (combining marks, variation selectors, emoji
    ZWJ sequences and regional-indicator flags) without pulling in a dependency. It is
    not a complete UAX #29 implementation, but it never splits the clusters above.
    """
    cluster: list[str] = []
    regionals = 0
    prev = ""
    for ch in s:
        if not cluster:
            cluster.append(ch)
            regionals = 1 if _is_regional(ch) else 0
            prev = ch
            continue
        if ch == _ZWJ or prev == _ZWJ or _is_extend(ch):
            cluster.append(ch)
        elif _is_regional(ch) and regionals % 2 == 1:
            cluster.append(ch)
            regionals += 1
        else:
            yield "".join(cluster)
            cluster = [ch]
            regionals = 1 if _is_regional(ch) else 0
        prev = ch
    if cluster:
        yield "".join(cluster)
