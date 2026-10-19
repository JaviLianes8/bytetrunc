"""Cut raw UTF-8 bytes without ending in the middle of a character."""

from __future__ import annotations

from typing import SupportsIndex

from ._errors import BytetruncError, check_limit, type_name

# Second-byte ranges that differ from 80..BF in well-formed UTF-8 (RFC 3629, section 4):
# they exclude overlong forms, surrogates and code points above U+10FFFF.
_SECOND = {0xE0: (0xA0, 0xBF), 0xED: (0x80, 0x9F), 0xF0: (0x90, 0xBF), 0xF4: (0x80, 0x8F)}


def _length(lead: int) -> int:
    """Bytes in the well-formed sequence that ``lead`` starts, or 0 if it starts none."""
    if 0xC2 <= lead <= 0xDF:
        return 2
    if 0xE0 <= lead <= 0xEF:
        return 3
    if 0xF0 <= lead <= 0xF4:
        return 4
    return 0


def _complete_end(data: memoryview, end: int) -> int:
    """Return ``end``, or where an unfinished well-formed sequence before it starts."""
    start = end - 1
    while start >= 0 and end - start <= 3 and 0x80 <= data[start] <= 0xBF:
        start -= 1
    if start < 0 or end - start > 3:
        return end
    lead = data[start]
    if _length(lead) <= end - start:
        return end
    if end - start >= 2:
        low, high = _SECOND.get(lead, (0x80, 0xBF))
        if not low <= data[start + 1] <= high:
            return end
    return start


def _bytes_view(data: object) -> memoryview:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"data must be bytes, bytearray or memoryview, got {type_name(data)}")
    try:
        view = memoryview(data)
    except ValueError:
        raise BytetruncError("data is a released memoryview") from None
    if not view.c_contiguous:
        view = memoryview(view.tobytes())
    return view.cast("B") if view.format != "B" or view.ndim != 1 else view


def cut_utf8(data: bytes | bytearray | memoryview, max_bytes: SupportsIndex | None = None) -> bytes:
    """Cut raw UTF-8 ``data`` to at most ``max_bytes`` without ending mid-character.

    Works on bytes without decoding them, which suits network reads, fixed-size records
    and buffers that may stop inside a character. The result is always a prefix of
    ``data`` (of its raw bytes, for a ``memoryview`` of any format). With
    ``max_bytes=None`` only the end of ``data`` is examined.

    Only the cut point is inspected. If the bytes just before it are the start of a
    well-formed UTF-8 sequence that the cut leaves unfinished, they are dropped; every
    other byte is kept, valid or not. So valid UTF-8 (possibly ending in an incomplete
    character) gives valid UTF-8, and invalid bytes stay for a strict decode to reject.

    Raises :class:`TypeError` for text or other types and
    :class:`~bytetrunc.BytetruncError` for a negative ``max_bytes`` or a ``memoryview``
    that has been released.

    >>> from bytetrunc import cut_utf8
    >>> cut_utf8("héllo".encode(), 2)
    b'h'
    >>> cut_utf8(b"abc\\xe2\\x82")
    b'abc'
    >>> cut_utf8(b"abc\\xc0")
    b'abc\\xc0'
    """
    view = _bytes_view(data)
    end = len(view)
    if max_bytes is not None:
        end = min(end, check_limit(max_bytes, "max_bytes"))
    return bytes(view[: _complete_end(view, end)])
