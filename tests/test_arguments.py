"""Every argument of every public function: its type check, its result type, its message."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

import bytetrunc
from bytetrunc import BytetruncError

TEXT = "abcdef"

# (function, argument, wrong value, type named in the message) for every argument.
WRONG: list[tuple[str, str, object, str]] = [
    *[(f, "s", b"abcdef", "bytes") for f in ("truncate_bytes", "truncate_detailed")],
    *[(f, "s", b"abcdef", "bytes") for f in ("truncate_utf16", "chunk_bytes")],
    *[(f, "s", b"abcdef", "bytes") for f in ("byte_len", "utf16_len", "iter_graphemes")],
    ("truncate_filename", "name", b"abc.txt", "bytes"),
    ("cut_utf8", "data", TEXT, "str"),
    *[(f, "max_bytes", 1.5, "float") for f in ("truncate_bytes", "truncate_detailed")],
    *[(f, "max_bytes", 1.5, "float") for f in ("truncate_filename", "chunk_bytes")],
    ("cut_utf8", "max_bytes", 1.5, "float"),
    ("truncate_utf16", "max_units", 1.5, "float"),
    *[(f, "suffix", b".", "bytes") for f in ("truncate_bytes", "truncate_detailed")],
    *[(f, "suffix", b".", "bytes") for f in ("truncate_utf16", "truncate_filename")],
    *[(f, "on", b"char", "bytes") for f in ("truncate_bytes", "truncate_detailed")],
    *[(f, "on", b"char", "bytes") for f in ("truncate_utf16", "truncate_filename")],
    ("chunk_bytes", "on", b"char", "bytes"),
    *[(f, "encoding", b"utf-8", "bytes") for f in ("truncate_bytes", "truncate_detailed")],
    *[(f, "encoding", b"utf-8", "bytes") for f in ("truncate_filename", "chunk_bytes")],
    ("byte_len", "encoding", b"utf-8", "bytes"),
    ("truncate_filename", "keep_extension", "yes", "str"),
]
FIRST = {"cut_utf8": b"abcdef", "truncate_filename": "abcdef.txt"}
LIMITED = {"utf16_len", "byte_len", "iter_graphemes"}


def _call(function: str, **overrides: object) -> object:
    first = "data" if function == "cut_utf8" else "name" if function == "truncate_filename" else "s"
    kwargs: dict[str, object] = {first: FIRST.get(function, TEXT)}
    if function not in LIMITED:
        kwargs["max_units" if function == "truncate_utf16" else "max_bytes"] = 3
    kwargs.update(overrides)
    return getattr(bytetrunc, function)(**kwargs)


@pytest.mark.parametrize(("function", "argument", "value", "kind"), WRONG)
def test_every_argument_refuses_a_wrong_type(
    function: str, argument: str, value: object, kind: str
) -> None:
    with pytest.raises(TypeError) as caught:
        _call(function, **{argument: value})
    assert str(caught.value).startswith(f"{argument} must be ")
    assert str(caught.value).endswith(f", got {kind}")


class MyStr(str):
    pass


TEXT_RESULTS: list[tuple[str, Callable[[str], Sequence[object]]]] = [
    ("truncate_bytes", lambda s: [bytetrunc.truncate_bytes(s, n) for n in (99, 3)]),
    ("truncate_bytes suffix", lambda s: [bytetrunc.truncate_bytes(s, 4, suffix=MyStr("~"))]),
    ("truncate_detailed", lambda s: [bytetrunc.truncate_detailed(s, n).text for n in (99, 3)]),
    ("truncate_utf16", lambda s: [bytetrunc.truncate_utf16(s, n, on="grapheme") for n in (99, 3)]),
    ("truncate_filename", lambda s: [bytetrunc.truncate_filename(s + ".txt", n) for n in (99, 8)]),
    (
        "truncate_filename plain",
        lambda s: [bytetrunc.truncate_filename(s, n, keep_extension=False) for n in (99, 3)],
    ),
    ("chunk_bytes", lambda s: [*bytetrunc.chunk_bytes(s, 99), *bytetrunc.chunk_bytes(s, 4)]),
    ("chunk_bytes grapheme", lambda s: bytetrunc.chunk_bytes(s, 4, on="grapheme")),
    ("iter_graphemes", lambda s: list(bytetrunc.iter_graphemes(s))),
]


@pytest.mark.parametrize(("label", "produce"), TEXT_RESULTS)
def test_a_str_subclass_gives_plain_str_results(
    label: str, produce: Callable[[str], Sequence[object]]
) -> None:
    results = produce(MyStr(TEXT))
    assert results
    assert all(type(result) is str for result in results), label


def test_type_names_in_messages_are_cut_to_40_characters() -> None:
    long_name = type("N" * 5000, (), {})()
    hidden = type("\U000e0001" * 50, (), {})()
    for value in (long_name, hidden):
        for argument in ("s", "suffix", "on", "encoding", "max_bytes"):
            with pytest.raises(TypeError) as caught:
                _call("truncate_bytes", **{argument: value})
            name = str(caught.value).split(", got ", 1)[1]
            assert 0 < len(name) <= 40, (argument, len(name))
    with pytest.raises(TypeError) as caught:
        bytetrunc.cut_utf8(long_name)
    assert len(str(caught.value).split(", got ", 1)[1]) == 40


def test_previews_add_an_ellipsis_only_when_text_was_cut() -> None:
    for size, shown in ((31, "x" * 31), (32, "x" * 32), (33, "x" * 32)):
        with pytest.raises(BytetruncError) as caught:
            bytetrunc.byte_len("a", "x" * size)
        message = str(caught.value)
        tail = "...;" if size > 32 else ";"
        assert f"unsupported encoding {shown!r}{tail}" in message, message
