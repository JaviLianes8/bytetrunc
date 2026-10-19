"""Exact wording of messages, help and printed results, pinned so a change is deliberate."""

from __future__ import annotations

import sys
import traceback

import pytest
from test_cli import run

from bytetrunc import BytetruncError, Truncation, cut_utf8, truncate_bytes, truncate_filename


@pytest.mark.parametrize(
    ("name", "shown"),
    [
        ("a\nb", "a\\nb"),
        ("q\x1b[31m", "q\\x1b[31m"),
        ("t\N{ZERO WIDTH SPACE}z", "t\\u200bz"),
    ],
    ids=["newline", "escape", "zero width space"],
)
def test_a_type_name_is_escaped_in_messages(name: str, shown: str) -> None:
    with pytest.raises(TypeError) as caught:
        truncate_bytes(type(name, (), {})(), 1)
    assert str(caught.value) == f"s must be a str, got {shown}"


NO_ROOM = "extension '.txtxt' leaves no room for the name within max_bytes=3; "


def test_the_no_room_message_of_truncate_filename_is_exact() -> None:
    with pytest.raises(BytetruncError) as caught:
        truncate_filename("a.txtxt", 3)
    assert str(caught.value) == NO_ROOM + "pass keep_extension=False to cut it as plain text"


def test_the_cli_no_room_error_line_is_exact() -> None:
    done = run("truncate", "3", "--keep-extension", stdin=b"a.txtxt\n")
    assert done.returncode == 1
    expected = (
        f"bytetrunc: error: line 1: {NO_ROOM}run without --keep-extension to cut it as plain text"
    )
    assert done.stderr.decode().splitlines() == [expected]


def test_the_top_level_help_names_the_limit_of_each_command() -> None:
    lines = [" ".join(line.split()) for line in run("--help").stdout.decode().splitlines()]
    assert "truncate cut each stdin line to MAX_BYTES bytes" in lines
    assert "chunk split stdin into pieces of MAX_BYTES bytes" in lines


def test_a_released_memoryview_error_hides_the_internal_error() -> None:
    view = memoryview(b"abc")
    view.release()
    with pytest.raises(BytetruncError) as caught:
        cut_utf8(view, 1)
    assert caught.value.__suppress_context__ is True
    shown = "".join(traceback.format_exception(BytetruncError, caught.value, None))
    assert "During handling" not in shown


@pytest.mark.skipif(sys.version_info < (3, 12), reason="__buffer__ needs Python 3.12")
def test_a_buffer_error_of_a_bytes_subclass_reaches_the_caller() -> None:
    class Failing(bytes):
        def __buffer__(self, flags: int) -> memoryview:
            raise ValueError("custom buffer failure")

    with pytest.raises(ValueError) as caught:
        cut_utf8(Failing(b"abc"), 2)
    assert type(caught.value) is ValueError
    assert str(caught.value) == "custom buffer failure"


def test_every_integer_of_a_result_prints_by_its_size_when_huge() -> None:
    huge = 10**5000
    size = f"an integer of {huge.bit_length()} bits"
    assert repr(Truncation("a", huge, huge, huge, "utf-8", True)) == (
        f"Truncation(text='a', size={size}, original_size={size}, limit={size}, "
        "encoding='utf-8', truncated=True)"
    )
