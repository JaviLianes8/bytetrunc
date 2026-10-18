"""The first promise of bytetrunc: UTF-8 byte budgets, suffixes and the two boundaries."""

from __future__ import annotations

import pytest

from bytetrunc import byte_len, truncate_bytes


def test_byte_len_counts_utf8_bytes() -> None:
    assert byte_len("") == 0
    assert byte_len("abc") == 3
    assert byte_len("é") == 2
    assert byte_len("你") == 3
    assert byte_len("😀") == 4


def test_text_that_already_fits_is_returned_unchanged() -> None:
    assert truncate_bytes("hello", 5) == "hello"
    assert truncate_bytes("hello", 99, suffix="...") == "hello"


def test_short_budget_does_not_split_a_multibyte_character() -> None:
    # "aé" is a(1) + é(2) = 3 bytes; a budget of 2 cannot hold é.
    result = truncate_bytes("aé", 2)
    assert result == "a"
    assert byte_len(result) <= 2


def test_result_always_stays_within_the_budget() -> None:
    text = "héllo wörld 你好 😀"
    for limit in range(0, byte_len(text) + 2):
        assert byte_len(truncate_bytes(text, limit)) <= limit


def test_suffix_is_counted_against_the_budget() -> None:
    result = truncate_bytes("hello world", 8, suffix="...")
    assert result == "hello..."
    assert byte_len(result) == 8


def test_suffix_can_consume_the_whole_budget() -> None:
    result = truncate_bytes("abcdef", 3, suffix="...")
    assert result == "..."
    assert byte_len(result) == 3


def test_char_mode_may_split_a_grapheme_cluster() -> None:
    # "aé" is a(1) + e(1) + combining acute(2) = 4 bytes.
    assert truncate_bytes("aé", 2, on="char") == "ae"


def test_grapheme_mode_keeps_combining_marks_with_their_base() -> None:
    # The acute-e cluster is 3 bytes and does not fit a budget of 2.
    assert truncate_bytes("aé", 2, on="grapheme") == "a"


def test_grapheme_mode_keeps_a_flag_whole() -> None:
    flag = "\U0001f1ea\U0001f1f8"  # one regional-indicator flag, 8 bytes
    assert truncate_bytes(flag, 4, on="grapheme") == ""
    assert truncate_bytes(flag, 8, on="grapheme") == flag


def test_empty_string_returns_empty() -> None:
    assert truncate_bytes("", 5) == ""
    assert truncate_bytes("", 0) == ""


def test_zero_budget_without_suffix_returns_empty() -> None:
    assert truncate_bytes("hello", 0) == ""


def test_negative_max_bytes_is_rejected() -> None:
    with pytest.raises(ValueError):
        truncate_bytes("hello", -1)


def test_unknown_boundary_is_rejected() -> None:
    with pytest.raises(ValueError):
        truncate_bytes("hello", 3, on="word")  # type: ignore[arg-type]


def test_suffix_larger_than_budget_is_rejected() -> None:
    with pytest.raises(ValueError):
        truncate_bytes("hello", 2, suffix="...")
