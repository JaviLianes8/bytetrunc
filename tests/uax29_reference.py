"""A second grapheme segmenter, written by hand from the rule table of UAX #29 revision 49.

Section 3.1.1 of https://www.unicode.org/reports/tr29/tr29-49.html (fetched 2026-10-18,
pinned in tests/upstream/MANIFEST.json) lists the rules GB1 to GB999. This module applies
them literally: for every position it reads the context to the left of the break, rule by
rule, in the order of the table. It shares only the property lookup with bytetrunc, whose
state machine reads the text once from left to right instead. RULES holds each rule as the
annex writes it, so a test can compare them with the fetched text.
"""

from __future__ import annotations

import random

from bytetrunc._ucd import _CODES, _STARTS, EXT_PICT_BIT, GCB, INCB_SHIFT, prop

RULES = (
    ("GB1", "sot \N{DIVISION SIGN} Any"),
    ("GB2", "Any \N{DIVISION SIGN} eot"),
    ("GB3", "CR \N{MULTIPLICATION SIGN} LF"),
    ("GB4", "(Control | CR | LF) \N{DIVISION SIGN}"),
    ("GB5", "\N{DIVISION SIGN} (Control | CR | LF)"),
    ("GB6", "L \N{MULTIPLICATION SIGN} (L | V | LV | LVT)"),
    ("GB7", "(LV | V) \N{MULTIPLICATION SIGN} (V | T)"),
    ("GB8", "(LVT | T) \N{MULTIPLICATION SIGN} T"),
    ("GB9", "\N{MULTIPLICATION SIGN} (Extend | ZWJ)"),
    ("GB9a", "\N{MULTIPLICATION SIGN} SpacingMark"),
    ("GB9b", "Prepend \N{MULTIPLICATION SIGN}"),
    ("GB9c", "\\p{InCB=Linker} \\p{InCB=Extend}* \N{MULTIPLICATION SIGN} \\p{InCB=Consonant}"),
    (
        "GB11",
        "\\p{Extended_Pictographic} Extend* ZWJ \N{MULTIPLICATION SIGN} \\p{Extended_Pictographic}",
    ),
    ("GB12", "sot (RI RI)* RI \N{MULTIPLICATION SIGN} RI"),
    ("GB13", "[^RI] (RI RI)* RI \N{MULTIPLICATION SIGN} RI"),
    ("GB999", "Any \N{DIVISION SIGN} Any"),
)

CR, LF, CONTROL, EXTEND, ZWJ = (GCB[n] for n in ("CR", "LF", "Control", "Extend", "ZWJ"))
RI, PREPEND, SPACING = GCB["Regional_Indicator"], GCB["Prepend"], GCB["SpacingMark"]
L, V, T, LV, LVT = (GCB[n] for n in ("L", "V", "T", "LV", "LVT"))
LINKER, CONSONANT, INCB_EXTEND = 1, 2, 3


def _no_break(g: list[int], pict: list[bool], incb: list[int], i: int) -> bool:
    """True when one of GB3 to GB13 forbids a break between index i - 1 and i."""
    before, after = g[i - 1], g[i]
    if before == CR and after == LF:  # GB3
        return True
    if before in (CONTROL, CR, LF) or after in (CONTROL, CR, LF):  # GB4, GB5
        return False
    if before == L and after in (L, V, LV, LVT):  # GB6
        return True
    if before in (LV, V) and after in (V, T):  # GB7
        return True
    if before in (LVT, T) and after == T:  # GB8
        return True
    if after in (EXTEND, ZWJ, SPACING) or before == PREPEND:  # GB9, GB9a, GB9b
        return True
    if incb[i] == CONSONANT:  # GB9c: a linker, then only InCB=Extend, before the break
        j = i - 1
        while j >= 0 and incb[j] == INCB_EXTEND:
            j -= 1
        if j >= 0 and incb[j] == LINKER:
            return True
    if pict[i] and before == ZWJ:  # GB11: a pictograph, then only Extend, then the ZWJ
        j = i - 2
        while j >= 0 and g[j] == EXTEND:
            j -= 1
        if j >= 0 and pict[j]:
            return True
    if before == RI and after == RI:  # GB12, GB13: an odd run of RI before the break
        j = i - 1
        while j >= 0 and g[j] == RI:
            j -= 1
        return (i - 1 - j) % 2 == 1
    return False  # GB999


def clusters(text: str) -> list[str]:
    """Split ``text`` into extended grapheme clusters by the rule table."""
    if not text:
        return []  # GB1 and GB2 need text to put a boundary in
    props = [prop(ord(ch)) for ch in text]
    g = [p & 0x0F for p in props]
    pict = [bool(p & EXT_PICT_BIT) for p in props]
    incb = [(p >> INCB_SHIFT) & 0x03 for p in props]
    found: list[str] = []
    start = 0
    for i in range(1, len(text)):
        if not _no_break(g, pict, incb, i):
            found.append(text[start:i])
            start = i
    found.append(text[start:])
    return found


def representatives(rng: random.Random, per_code: int = 4) -> list[str]:
    """Return a few characters for every distinct property code in the embedded tables."""
    by_code: dict[int, list[int]] = {}
    ends = [*_STARTS[1:], 0x110000]
    for start, end, code in zip(_STARTS, ends, _CODES, strict=True):
        scalars = [
            cp for cp in (rng.randrange(start, end) for _ in range(4)) if not 0xD800 <= cp <= 0xDFFF
        ]
        if scalars:
            by_code.setdefault(code, []).append(scalars[0])
    chosen: list[str] = []
    for points in by_code.values():
        chosen.extend(chr(cp) for cp in rng.sample(points, min(per_code, len(points))))
    return chosen


def random_text(rng: random.Random, pool: list[str], longest: int = 12) -> str:
    """A random string of pool characters and, now and then, any scalar value."""
    parts: list[str] = []
    for _ in range(rng.randrange(longest + 1)):
        if rng.random() < 0.1:
            cp = rng.randrange(0x110000)
            parts.append(chr(cp) if not 0xD800 <= cp <= 0xDFFF else "x")
        else:
            parts.append(rng.choice(pool))
    return "".join(parts)
