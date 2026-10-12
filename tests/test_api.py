"""Hand-written examples for encodings, UTF-16 units, detailed results and graphemes."""

from __future__ import annotations

import pytest

from bytetrunc import (
    Truncation,
    byte_len,
    iter_graphemes,
    truncate_bytes,
    truncate_detailed,
    truncate_utf16,
    utf16_len,
)

FAMILY = "\U0001f468\u200d\U0001f469\u200d\U0001f467"  # man ZWJ woman ZWJ girl, 18 bytes
THUMB = "\U0001f44d\U0001f3fd"  # thumbs up with a medium skin tone, 8 bytes
FLAG = "\U0001f1ea\U0001f1f8"  # regional indicators E and S, 8 bytes
HANGUL = "\u1112\u1161\u11ab"  # conjoining jamo for one syllable, 9 bytes


def test_byte_len_in_each_encoding() -> None:
    assert byte_len("a\u00e9\U0001f600") == 1 + 2 + 4
    assert byte_len("a\u00e9\U0001f600", "utf-16-le") == 2 + 2 + 4
    assert byte_len("a\u00e9\U0001f600", "utf-16-be") == 8
    assert byte_len("a\u00e9\U0001f600", "utf-32-le") == 12
    assert byte_len("abc", "UTF8") == 3  # aliases are accepted


def test_byte_order_mark_encodings_are_rejected() -> None:
    for name in ("utf-16", "utf-32", "utf-8-sig", "latin-1", "no-such-codec"):
        with pytest.raises(ValueError, match="unsupported encoding"):
            byte_len("a", name)


def test_utf16_never_splits_a_surrogate_pair() -> None:
    text = "ab\U0001f600cd"  # 2 + 2 + 4 + 2 + 2 bytes in UTF-16
    assert truncate_bytes(text, 6, encoding="utf-16-le") == "ab"
    assert truncate_bytes(text, 7, encoding="utf-16-be") == "ab"
    assert truncate_bytes(text, 8, encoding="utf-16-le") == "ab\U0001f600"
    assert truncate_bytes(text, 5, encoding="utf-16-le") == "ab"  # odd limit rounds down


def test_utf32_counts_four_bytes_per_code_point() -> None:
    assert truncate_bytes("abcdef", 10, encoding="utf-32-le") == "ab"


def test_utf16_units_match_javascript_length() -> None:
    assert utf16_len("") == 0
    assert utf16_len("abc") == 3
    assert utf16_len("\U0001f600") == 2
    assert utf16_len(FAMILY) == 8
    assert truncate_utf16("ab\U0001f600", 3) == "ab"
    assert truncate_utf16("ab\U0001f600", 4) == "ab\U0001f600"
    assert truncate_utf16("hello world", 8, suffix="...") == "hello..."
    with pytest.raises(ValueError, match="max_units"):
        truncate_utf16("abc", -1)


def test_detailed_result_reports_sizes() -> None:
    fits = truncate_detailed("abc", 5)
    assert fits == Truncation("abc", 3, 3, 5, "utf-8", False)
    cut = truncate_detailed("h\u00e9llo world", 8, suffix="...")
    assert cut == Truncation("h\u00e9ll...", 8, 12, 8, "utf-8", True)
    wide = truncate_detailed("abcdef", 7, encoding="utf_16_le")
    assert (wide.text, wide.size, wide.encoding) == ("abc", 6, "utf-16-le")


def test_truncation_is_immutable() -> None:
    result = truncate_detailed("abc", 1)
    with pytest.raises(AttributeError):
        result.text = "x"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("cluster", "size"), [(FAMILY, 18), (THUMB, 8), (FLAG, 8), (HANGUL, 9), ("e\u0301", 3)]
)
def test_grapheme_mode_keeps_each_cluster_whole(cluster: str, size: int) -> None:
    text = "ab" + cluster + "cd"
    assert list(iter_graphemes(text)) == ["a", "b", cluster, "c", "d"]
    for limit in range(2, 2 + size):
        assert truncate_bytes(text, limit, on="grapheme") == "ab"
    assert truncate_bytes(text, 2 + size, on="grapheme") == "ab" + cluster


def test_char_mode_may_split_a_cluster_but_never_a_code_point() -> None:
    text = "ab" + FAMILY
    assert truncate_bytes(text, 7) == "ab\U0001f468\u200d"[:3]
    assert truncate_bytes(text, 9) == "ab\U0001f468\u200d"


def test_grapheme_mode_with_suffix_and_utf16() -> None:
    text = "ok " + FLAG + FLAG
    assert truncate_bytes(text, 16, "~", "grapheme", encoding="utf-16-le") == "ok " + FLAG + "~"


def test_crlf_is_one_cluster() -> None:
    assert truncate_bytes("ab\r\ncd", 3, on="grapheme") == "ab"
    assert truncate_bytes("ab\r\ncd", 3, on="char") == "ab\r"


def test_lone_surrogates_raise_unicode_encode_error() -> None:
    with pytest.raises(UnicodeEncodeError):
        truncate_bytes("a\ud800b", 1)


def test_limit_type_is_checked() -> None:
    with pytest.raises(TypeError):
        truncate_bytes("abc", 2.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        truncate_bytes("abc", True)
