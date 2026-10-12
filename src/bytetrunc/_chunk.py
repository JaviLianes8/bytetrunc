"""Split text into consecutive pieces that each fit a byte limit."""

from __future__ import annotations

from ._core import Boundary, check_boundary
from ._encodings import Encoding, char_cut, check_limit, normalize_encoding
from ._graphemes import grapheme_ends


def chunk_bytes(
    s: str,
    max_bytes: int,
    on: Boundary = "char",
    *,
    encoding: Encoding | str = "utf-8",
) -> list[str]:
    """Split ``s`` into pieces whose encodings each fit within ``max_bytes``.

    Pieces are filled greedily, never split a code point (nor a grapheme cluster with
    ``on="grapheme"``) and ``"".join(pieces) == s`` always holds. Use it for SMS
    segments, push payloads, log lines or any transport with a per-message byte cap.
    The empty string gives an empty list.

    Raises ``ValueError`` if ``max_bytes`` is not positive, if ``on`` or ``encoding`` is
    not supported, or if a single character (or grapheme cluster) is larger than
    ``max_bytes`` on its own; the message names its index and size.

    >>> chunk_bytes("héllo wörld", 5)
    ['héll', 'o wö', 'rld']
    """
    check_limit(max_bytes)
    check_boundary(on)
    enc = normalize_encoding(encoding)
    if max_bytes == 0:
        raise ValueError("max_bytes must be positive to split text into chunks")
    if on == "grapheme":
        return _grapheme_chunks(s, max_bytes, enc)
    data = s.encode(enc)
    pieces: list[str] = []
    start = 0
    chars = 0
    while start < len(data):
        end = char_cut(data, start, max_bytes, enc)
        if end == start:
            size = len(s[chars].encode(enc))
            raise ValueError(
                f"character at index {chars} needs {size} bytes, more than max_bytes={max_bytes}"
            )
        piece = data[start:end].decode(enc)
        pieces.append(piece)
        chars += len(piece)
        start = end
    return pieces


def _grapheme_chunks(s: str, max_bytes: int, enc: str) -> list[str]:
    pieces: list[str] = []
    piece_start = 0
    cluster_start = 0
    used = 0
    for end in grapheme_ends(s):
        size = len(s[cluster_start:end].encode(enc))
        if size > max_bytes:
            raise ValueError(
                f"grapheme cluster at index {cluster_start} needs {size} bytes, "
                f"more than max_bytes={max_bytes}"
            )
        if used + size > max_bytes:
            pieces.append(s[piece_start:cluster_start])
            piece_start = cluster_start
            used = 0
        used += size
        cluster_start = end
    if piece_start < len(s):
        pieces.append(s[piece_start:])
    return pieces
