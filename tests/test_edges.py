"""Edge cases found by review: huge limits in results, unusual buffers, sizes in messages."""

from __future__ import annotations

from array import array

import pytest

from bytetrunc import BytetruncError, chunk_bytes, cut_utf8, truncate_detailed


@pytest.mark.parametrize("limit", [10**4300, 10**10000], ids=["4301 digits", "10001 digits"])
def test_a_result_with_a_huge_limit_can_be_printed(limit: int) -> None:
    result = truncate_detailed("abc", limit)
    assert result.limit == limit
    for shown in (repr(result), str(result), f"{result}"):
        assert shown.startswith("Truncation(text='abc', size=3, original_size=3, limit=")
        assert shown.endswith(", encoding='utf-8', truncated=False)")
        assert f"an integer of {limit.bit_length()} bits" in shown
        assert len(shown) < 200


def test_a_result_with_a_wide_limit_still_prints_its_digits() -> None:
    assert "limit=1" + "0" * 30 + "," in repr(truncate_detailed("abc", 10**30))


def test_a_released_memoryview_is_refused_as_a_value() -> None:
    view = memoryview(b"abc")
    view.release()
    with pytest.raises(BytetruncError, match="released memoryview"):
        cut_utf8(view, 2)


def test_a_strided_view_of_wide_items_is_cut_by_its_raw_bytes() -> None:
    words = array("H", [0x6261, 0x6463, 0x6665])
    for view in (memoryview(words)[::2], memoryview(words)[::-1]):
        raw = view.tobytes()
        assert cut_utf8(view, 3) == raw[:3]
        assert cut_utf8(view) == raw


def test_a_fortran_order_view_of_wide_items_is_cut_by_its_raw_bytes() -> None:
    testbuffer = pytest.importorskip("_testbuffer")
    items = list(range(0x61, 0x61 + 6))
    grid = testbuffer.ndarray(items, shape=[2, 3], format="H", flags=testbuffer.ND_FORTRAN)
    view = memoryview(grid)
    assert view.f_contiguous and not view.c_contiguous
    raw = view.tobytes()
    assert cut_utf8(view, 5) == raw[:5]
    assert cut_utf8(view) == raw


E_ACUTE = "\N{LATIN SMALL LETTER E WITH ACUTE}"
GRIN = "\U0001f600"


@pytest.mark.parametrize(
    ("text", "limit", "encoding", "on", "message"),
    [
        (E_ACUTE, 3, "utf-32-le", "char", "character at index 0 needs 4 bytes"),
        ("a", 3, "utf-32-be", "grapheme", "grapheme cluster at index 0 needs 4 bytes"),
        ("a" + GRIN, 2, "utf-16-le", "char", "character at index 1 needs 4 bytes"),
        ("ab" + GRIN, 3, "utf-16-be", "grapheme", "grapheme cluster at index 2 needs 4 bytes"),
    ],
)
def test_the_size_of_an_oversized_character_is_counted_in_the_encoding(
    text: str, limit: int, encoding: str, on: str, message: str
) -> None:
    with pytest.raises(BytetruncError) as caught:
        chunk_bytes(text, limit, on=on, encoding=encoding)  # type: ignore[arg-type]
    assert str(caught.value) == f"{message}, more than max_bytes={limit}"
