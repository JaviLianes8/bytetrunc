"""Truncate text to a byte limit without breaking characters or grapheme clusters."""

from __future__ import annotations

from ._chunk import chunk_bytes
from ._core import (
    Boundary,
    Truncation,
    byte_len,
    truncate_bytes,
    truncate_detailed,
    truncate_utf16,
    utf16_len,
)
from ._encodings import ENCODINGS, Encoding, cut_utf8
from ._filename import truncate_filename
from ._graphemes import iter_graphemes
from ._ucd import UNICODE_VERSION

__version__ = "0.2.0"

__all__ = [
    "ENCODINGS",
    "UNICODE_VERSION",
    "Boundary",
    "Encoding",
    "Truncation",
    "byte_len",
    "chunk_bytes",
    "cut_utf8",
    "iter_graphemes",
    "truncate_bytes",
    "truncate_detailed",
    "truncate_filename",
    "truncate_utf16",
    "utf16_len",
]
