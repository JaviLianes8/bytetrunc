"""Hand-written examples for chunk_bytes, truncate_filename and cut_utf8.

The byte limits used here are real-world ones described in GUIDE.md: ext4 file names
(255 bytes), NTFS file names (255 UTF-16 units), a UCS-2 SMS segment (140 octets, 134
when concatenated), and APNs / FCM payloads (4096 bytes).
"""

from __future__ import annotations

import pytest

from bytetrunc import BytetruncError, byte_len, chunk_bytes, cut_utf8, truncate_filename

FAMILY = "\U0001f468\u200d\U0001f469\u200d\U0001f467"


def test_chunks_join_back_and_fit() -> None:
    text = "h\u00e9llo w\u00f6rld " * 20
    pieces = chunk_bytes(text, 7)
    assert "".join(pieces) == text
    assert all(0 < byte_len(p) <= 7 for p in pieces)


def test_chunk_of_empty_text_is_empty() -> None:
    assert chunk_bytes("", 10) == []


def test_concatenated_ucs2_sms_segments() -> None:
    body = "\u00a1Hola! " * 30  # 210 characters, all in the BMP
    segments = chunk_bytes(body, 134, encoding="utf-16-be")
    assert [len(s) for s in segments] == [67, 67, 67, 9]


def test_grapheme_chunks_keep_emoji_sequences_whole() -> None:
    text = "ab" + FAMILY + "cd"
    assert chunk_bytes(text, 18, on="grapheme") == ["ab", FAMILY, "cd"]
    assert chunk_bytes(text, 20, on="grapheme") == ["ab" + FAMILY, "cd"]


def test_cluster_larger_than_limit_is_an_honest_error() -> None:
    with pytest.raises(BytetruncError, match="grapheme cluster at index 2 needs 18 bytes"):
        chunk_bytes("ab" + FAMILY, 10, on="grapheme")
    with pytest.raises(BytetruncError, match="character at index 1 needs 4 bytes"):
        chunk_bytes("a\U0001f600", 3)
    with pytest.raises(BytetruncError, match="positive"):
        chunk_bytes("abc", 0)


def test_push_payload_chunks() -> None:
    text = "\u4f60\u597d" * 3000  # 18000 bytes of CJK text
    pieces = chunk_bytes(text, 4096)
    assert [byte_len(p) for p in pieces] == [4095, 4095, 4095, 4095, 1620]


def test_filename_keeps_extension_on_ext4() -> None:
    name = "\u00e9" * 200 + ".tar.gz"
    cut = truncate_filename(name)
    # Only the last extension is kept; ".tar" belongs to the stem and is cut first.
    assert cut == "\u00e9" * 126 + ".gz"
    assert byte_len(cut) == 255


def test_filename_examples() -> None:
    assert truncate_filename("report.pdf", 255) == "report.pdf"
    assert truncate_filename("quarterly report.pdf", 12) == "quarterl.pdf"
    assert truncate_filename("quarterly report.pdf", 12, suffix="~") == "quarter~.pdf"
    assert truncate_filename(".bashrc_extra_long", 7) == ".bashrc"
    assert truncate_filename("noext", 3) == "noe"
    assert truncate_filename("a" + FAMILY + ".png", 20) == "a.png"


def test_filename_for_ntfs_counts_utf16_units() -> None:
    name = "\U0001f600" * 200 + ".txt"  # 400 UTF-16 units of emoji plus 4
    cut = truncate_filename(name, 510, encoding="utf-16-le")
    assert cut == "\U0001f600" * 125 + ".txt"


def test_filename_rejections() -> None:
    for bad in ("", ".", "..", "a/b.txt", "a\0b"):
        with pytest.raises(BytetruncError, match="single file name"):
            truncate_filename(bad, 10)
    with pytest.raises(BytetruncError, match="keep_extension=False"):
        truncate_filename("a.verylongextension", 8)
    assert truncate_filename("a.verylongextension", 8, keep_extension=False) == "a.verylo"


def test_cut_utf8_drops_an_incomplete_tail() -> None:
    euro = "\u20ac".encode()  # e2 82 ac
    assert cut_utf8(b"abc" + euro[:1]) == b"abc"
    assert cut_utf8(b"abc" + euro[:2]) == b"abc"
    assert cut_utf8(b"abc" + euro) == b"abc" + euro
    assert cut_utf8(b"") == b""


def test_cut_utf8_with_a_limit() -> None:
    data = "h\u00e9llo \U0001f600".encode()
    assert cut_utf8(data, 2) == b"h"
    assert cut_utf8(data, 3) == "h\u00e9".encode()
    assert cut_utf8(data, 9) == "h\u00e9llo ".encode()
    assert cut_utf8(data, 10) == "h\u00e9llo ".encode()
    assert cut_utf8(data, 99) == data
    assert cut_utf8(data, 0) == b""
    with pytest.raises(BytetruncError):
        cut_utf8(data, -1)


def test_cut_utf8_leaves_invalid_bytes_alone() -> None:
    assert cut_utf8(b"ab\xff") == b"ab\xff"
    assert cut_utf8(b"\x80\x80\x80\x80\x80") == b"\x80\x80\x80\x80\x80"


def test_filename_never_returns_dot_or_dot_dot() -> None:
    for name, limit, kwargs in [
        ("...", 2, {}),
        (".hidden", 1, {}),
        (".hidden", 3, {"encoding": "utf-16-le"}),
        ("..hidden", 2, {"keep_extension": False}),
    ]:
        with pytest.raises(BytetruncError, match="no usable file name"):
            truncate_filename(name, limit, **kwargs)  # type: ignore[arg-type]


def test_filename_suffix_must_stay_one_component() -> None:
    for suffix in ("/", "a\0"):
        with pytest.raises(BytetruncError, match="suffix"):
            truncate_filename("abcdef.txt", 8, suffix=suffix)


def test_cut_utf8_accepts_bytes_like_and_rejects_text() -> None:
    assert cut_utf8(bytearray(b"ab\xc3"), None) == b"ab"
    assert cut_utf8(memoryview(b"ab\xc3\xa9"), 3) == b"ab"
    with pytest.raises(TypeError, match="data must be bytes, bytearray or memoryview, got str"):
        cut_utf8("abc", 2)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="encoding must be a str"):
        byte_len("a", 5)  # type: ignore[arg-type]
