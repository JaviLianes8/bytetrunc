"""Fit a file name to a byte limit while keeping its extension."""

from __future__ import annotations

from typing import SupportsIndex

from ._core import Boundary, _cut, check_boundary
from ._encodings import Encoding, normalize_encoding
from ._errors import BytetruncError, check_flag, check_limit, check_text, preview

NUL = chr(0)
NO_ROOM_HINT = "pass keep_extension=False to cut it as plain text"


def truncate_filename(
    name: str,
    max_bytes: SupportsIndex = 255,
    *,
    suffix: str = "",
    on: Boundary = "grapheme",
    encoding: Encoding | str = "utf-8",
    keep_extension: bool = True,
) -> str:
    """Shorten the file name ``name`` to ``max_bytes`` while keeping its extension.

    The default of 255 UTF-8 bytes is the file name limit of ext4. For NTFS, which
    counts 255 UTF-16 code units, pass ``max_bytes=510`` and ``encoding="utf-16-le"``.
    The extension is everything from the last dot, unless that dot is the first
    character (``.bashrc`` has no extension). Only the part before the extension is
    shortened, by default on grapheme boundaries, and ``suffix`` (for example ``"~"``)
    goes between the shortened stem and the extension. A name that fits is returned
    unchanged.

    This function measures and cuts; it does not sanitize. Names that are not a single
    path component (empty, ``.``, ``..``, or containing ``/`` or NUL) are refused with
    :class:`~bytetrunc.BytetruncError`, as is a ``suffix`` containing ``/`` or NUL, a
    result that would be empty, ``.`` or ``..``, and an extension too long to leave room
    for at least one character of the stem (pass ``keep_extension=False`` to cut the
    name as plain text). A backslash is not treated as a separator; refuse it yourself
    on Windows. It also raises :class:`~bytetrunc.BytetruncError` for a negative
    ``max_bytes`` or an unsupported ``on`` or ``encoding``, :class:`TypeError` for
    arguments of the wrong type and :class:`UnicodeEncodeError` if ``name`` or
    ``suffix`` holds a lone surrogate.

    >>> from bytetrunc import truncate_filename
    >>> truncate_filename("quarterly report.pdf", 12)
    'quarterl.pdf'
    >>> truncate_filename("quarterly report.pdf", 12, suffix="~")
    'quarter~.pdf'
    """
    text = check_text(name, "name")
    limit = check_limit(max_bytes, "max_bytes")
    tail = check_text(suffix, "suffix")
    mode = check_boundary(on)
    enc = normalize_encoding(encoding)
    keep = check_flag(keep_extension, "keep_extension")
    if text in ("", ".", "..") or "/" in text or NUL in text:
        raise BytetruncError(f"not a single file name component: {preview(text)}")
    if "/" in tail or NUL in tail:
        raise BytetruncError(f"suffix must not contain '/' or NUL: {preview(tail)}")
    result = _fit(text, limit, tail, mode, enc, keep)
    if result in ("", ".", ".."):
        raise BytetruncError(f"no usable file name fits within max_bytes={limit}: {result!r}")
    return result


def _fit(name: str, limit: int, suffix: str, on: Boundary, enc: Encoding, keep: bool) -> str:
    dot = name.rfind(".")
    if not keep or dot <= 0:
        return _cut(name, limit, suffix, on, enc, 1).text
    stem, extension = name[:dot], name[dot:]
    suffix_size = len(suffix.encode(enc))
    if len(name.encode(enc)) <= limit:
        return name
    budget = limit - len(extension.encode(enc))
    if budget >= suffix_size:
        result = _cut(stem, budget, suffix, on, enc, 1)
        if result.text != suffix:
            return result.text + extension
    raise BytetruncError(
        f"extension {preview(extension)} leaves no room for the name within "
        f"max_bytes={limit}; {NO_ROOM_HINT}"
    )
