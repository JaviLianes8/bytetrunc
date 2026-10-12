"""Fit a file name to a byte limit while keeping its extension."""

from __future__ import annotations

from ._core import Boundary, truncate_detailed
from ._encodings import Encoding, check_limit, normalize_encoding

NUL = chr(0)


def truncate_filename(
    name: str,
    max_bytes: int = 255,
    suffix: str = "",
    on: Boundary = "grapheme",
    *,
    encoding: Encoding | str = "utf-8",
    keep_extension: bool = True,
) -> str:
    """Shorten the file name ``name`` to ``max_bytes`` while keeping its extension.

    The default of 255 UTF-8 bytes is the name limit of ext4, XFS, Btrfs and APFS. For
    NTFS, which counts 255 UTF-16 code units, pass ``max_bytes=510`` and
    ``encoding="utf-16-le"``. The extension is everything from the last dot, unless the
    dot is the first character (``.bashrc`` has no extension). Only the part before the
    extension is shortened, by default on grapheme boundaries, and ``suffix`` (for
    example ``"~"``) goes between the shortened stem and the extension.

    This function measures and cuts; it does not sanitize. Names that are not a single
    path component (empty, ``.``, ``..``, or containing ``/`` or NUL) are rejected
    with ``ValueError``, as is a ``suffix`` containing ``/`` or NUL, a result that would
    be empty, ``.`` or ``..``, and an extension too long to leave room for at least one
    unit of the stem (pass ``keep_extension=False`` to cut the name as plain text). A
    backslash is not treated as a separator; reject it yourself on Windows.

    >>> truncate_filename("quarterly report.pdf", 12)
    'quarterl.pdf'
    >>> truncate_filename("quarterly report.pdf", 12, suffix="~")
    'quarter~.pdf'
    """
    check_limit(max_bytes)
    enc = normalize_encoding(encoding)
    if name in ("", ".", "..") or "/" in name or NUL in name:
        raise ValueError(f"not a single file name component: {name!r}")
    if "/" in suffix or NUL in suffix:
        raise ValueError(f"suffix must not contain '/' or NUL: {suffix!r}")
    result = _fit(name, max_bytes, suffix, on, enc, keep_extension)
    if result in ("", ".", ".."):
        raise ValueError(f"no usable file name fits within max_bytes={max_bytes}: {result!r}")
    return result


def _fit(name: str, max_bytes: int, suffix: str, on: Boundary, enc: str, keep: bool) -> str:
    dot = name.rfind(".")
    if not keep or dot <= 0:
        return truncate_detailed(name, max_bytes, suffix, on, encoding=enc).text
    stem, extension = name[:dot], name[dot:]
    if len(name.encode(enc)) <= max_bytes:
        return name
    budget = max_bytes - len(extension.encode(enc))
    if budget >= len(suffix.encode(enc)):
        result = truncate_detailed(stem, budget, suffix, on, encoding=enc)
        if result.text != suffix:
            return result.text + extension
    raise ValueError(
        f"extension {extension!r} leaves no room for the name within max_bytes={max_bytes}; "
        "pass keep_extension=False to cut it as plain text"
    )
