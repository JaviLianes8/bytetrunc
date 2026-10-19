"""Supported encodings, their accepted names, and code point safe cut positions."""

from __future__ import annotations

from typing import Literal

from ._errors import BytetruncError, preview, type_name

Encoding = Literal["utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"]
ENCODINGS: tuple[Encoding, ...] = ("utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be")

# Every spelling is matched after removing hyphens, underscores and spaces and folding
# ASCII case. Besides the plain names this accepts Python's own aliases of these codecs.
_NAMES: dict[str, Encoding] = {
    "utf8": "utf-8",
    "u8": "utf-8",
    "utf": "utf-8",
    "cp65001": "utf-8",
    "utf8ucs2": "utf-8",
    "utf8ucs4": "utf-8",
    "utf16le": "utf-16-le",
    "unicodelittleunmarked": "utf-16-le",
    "utf16be": "utf-16-be",
    "unicodebigunmarked": "utf-16-be",
    "utf32le": "utf-32-le",
    "utf32be": "utf-32-be",
}
_FOLD = {ord(c): ord(c) + 32 for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"} | dict.fromkeys(b"-_ ")


def normalize_encoding(encoding: object) -> Encoding:
    """Return the canonical name of a supported encoding.

    The name is matched without regard to ASCII case, hyphens, underscores and spaces,
    so ``"UTF8"``, ``"utf_16_le"`` and ``"UTF-16LE"`` work. The lookup never consults
    the codec registry, which caches every unknown name it is asked for. Encodings that
    write a byte order mark (``"utf-16"``, ``"utf-32"``, ``"utf-8-sig"``) are refused:
    the mark would change every count.
    """
    if not issubclass(type(encoding), str):
        raise TypeError(f"encoding must be a str, got {type_name(encoding)}")
    name = str.__str__(encoding)
    if name in ENCODINGS:
        return name
    found = _NAMES.get(name.translate(_FOLD)) if name.isascii() else None
    if found is None:
        supported = ", ".join(ENCODINGS)
        raise BytetruncError(
            f"unsupported encoding {preview(name)}; use one of {supported} (no byte order mark)"
        )
    return found


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
