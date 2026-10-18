"""Truncate text to a byte limit without breaking characters or grapheme clusters.

Every public name is importable from ``bytetrunc``:

- :func:`truncate_bytes`, :func:`truncate_detailed` and :func:`truncate_utf16` cut text
  to a byte (or UTF-16 unit) limit, :func:`chunk_bytes` splits it into pieces that fit,
  :func:`truncate_filename` keeps a file extension and :func:`cut_utf8` trims raw bytes.
- :func:`byte_len`, :func:`utf16_len` and :func:`iter_graphemes` measure and segment.
- :class:`Truncation` is the detailed result and :class:`BytetruncError` the error type.
- ``ENCODINGS`` lists the supported encodings, ``Encoding`` and ``Boundary`` are the
  ``Literal`` types of the ``encoding`` and ``on`` arguments, and ``UNICODE_VERSION``
  names the Unicode version of the grapheme cluster rules and data.

>>> import bytetrunc
>>> bytetrunc.ENCODINGS
('utf-8', 'utf-16-le', 'utf-16-be', 'utf-32-le', 'utf-32-be')
>>> bytetrunc.UNICODE_VERSION
'18.0.0'
>>> from typing import get_args
>>> get_args(bytetrunc.Encoding) == bytetrunc.ENCODINGS
True
>>> get_args(bytetrunc.Boundary)
('char', 'grapheme')
"""

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
from ._encodings import ENCODINGS, Encoding
from ._errors import BytetruncError
from ._filename import truncate_filename
from ._graphemes import iter_graphemes
from ._rawbytes import cut_utf8
from ._ucd import UNICODE_VERSION

__version__ = "1.0.0"

__all__ = [
    "ENCODINGS",
    "UNICODE_VERSION",
    "Boundary",
    "BytetruncError",
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
