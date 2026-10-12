"""Lookup of the embedded Unicode properties used by grapheme segmentation."""

from __future__ import annotations

from bisect import bisect_right

from ._ucd_data import EXT_PICT_BIT, GCB_NAMES, INCB_SHIFT, RUNS, UNICODE_VERSION

__all__ = ["EXT_PICT_BIT", "GCB", "INCB_SHIFT", "UNICODE_VERSION", "prop"]

GCB = {name: index for index, name in enumerate(GCB_NAMES)}


def _decode(runs: str) -> tuple[list[int], bytes]:
    """Expand the run tokens into parallel lists of run starts and property codes."""
    starts: list[int] = []
    codes = bytearray()
    position = 0
    for token in runs.split():
        starts.append(position)
        codes.append(int(token[:2], 36))
        position += int(token[2:], 36)
    if position != 0x110000:
        raise RuntimeError("embedded Unicode tables do not cover the code space")
    return starts, bytes(codes)


_STARTS, _CODES = _decode(RUNS)
_ASCII = bytes(_CODES[bisect_right(_STARTS, cp) - 1] for cp in range(128))


def prop(cp: int) -> int:
    """Return the packed property code of code point ``cp``.

    Bits 0-3 hold the Grapheme_Cluster_Break value (an index into ``GCB_NAMES``),
    bit 4 is Extended_Pictographic and bits 5-6 hold Indic_Conjunct_Break.
    """
    if cp < 128:
        return _ASCII[cp]
    return _CODES[bisect_right(_STARTS, cp) - 1]
