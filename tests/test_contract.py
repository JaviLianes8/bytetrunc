"""The public surface of bytetrunc: names, signatures, the result record and the error type.

The behaviour each public name promises is pinned in tests/test_promises.py.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.resources
import inspect
import pickle
import re
from pathlib import Path
from typing import get_args

import pytest

import bytetrunc
from bytetrunc import (
    ENCODINGS,
    UNICODE_VERSION,
    Boundary,
    BytetruncError,
    Encoding,
    Truncation,
    byte_len,
    truncate_bytes,
    truncate_detailed,
    truncate_utf16,
)

ROOT = Path(__file__).resolve().parent.parent

# The public API. This list is the contract; the test below fails if they disagree.
PUBLIC_API: list[str] = [
    "ENCODINGS",
    "UNICODE_VERSION",
    "Boundary",
    "BytetruncError",
    "Encoding",
    "Truncation",
    "byte_len",
    "chunk_bytes",
    "cut_utf8",
    "iter_graphemes",
    "truncate_bytes",
    "truncate_detailed",
    "truncate_filename",
    "truncate_utf16",
    "utf16_len",
]
OPTIONS = "*, suffix: 'str' = '', on: 'Boundary' = 'char', encoding: 'Encoding | str' = 'utf-8'"
SIGNATURES = {
    "byte_len": "(s: 'str', encoding: 'Encoding | str' = 'utf-8') -> 'int'",
    "chunk_bytes": "(s: 'str', max_bytes: 'SupportsIndex', *, on: 'Boundary' = 'char', "
    "encoding: 'Encoding | str' = 'utf-8') -> 'list[str]'",
    "cut_utf8": "(data: 'bytes | bytearray | memoryview', "
    "max_bytes: 'SupportsIndex | None' = None) -> 'bytes'",
    "iter_graphemes": "(s: 'str') -> 'Iterator[str]'",
    "truncate_bytes": f"(s: 'str', max_bytes: 'SupportsIndex', {OPTIONS}) -> 'str'",
    "truncate_detailed": f"(s: 'str', max_bytes: 'SupportsIndex', {OPTIONS}) -> 'Truncation'",
    "truncate_filename": "(name: 'str', max_bytes: 'SupportsIndex' = 255, *, suffix: 'str' = '', "
    "on: 'Boundary' = 'grapheme', encoding: 'Encoding | str' = 'utf-8', "
    "keep_extension: 'bool' = True) -> 'str'",
    "truncate_utf16": "(s: 'str', max_units: 'SupportsIndex', *, suffix: 'str' = '', "
    "on: 'Boundary' = 'char') -> 'str'",
    "utf16_len": "(s: 'str') -> 'int'",
}


def test_all_lists_exactly_the_public_api() -> None:
    assert bytetrunc.__all__ == PUBLIC_API
    public = sorted(name for name in dir(bytetrunc) if not name.startswith("_"))
    assert public == sorted(PUBLIC_API)


def test_version_matches_pyproject_and_is_three_part() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', pyproject, re.M)
    assert match is not None and match.group(1) == bytetrunc.__version__
    assert re.fullmatch(r"\d+\.\d+\.\d+", bytetrunc.__version__)


def test_the_package_ships_type_information_and_a_script() -> None:
    assert importlib.resources.files("bytetrunc").joinpath("py.typed").is_file()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'bytetrunc = "bytetrunc._cli:main"' in pyproject
    assert re.search(r"^dependencies = \[\]$", pyproject, re.M)


def test_unicode_version_encodings_and_literal_types_are_declared() -> None:
    assert UNICODE_VERSION == "18.0.0"
    assert ENCODINGS == ("utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be")
    assert get_args(Encoding) == ENCODINGS
    assert get_args(Boundary) == ("char", "grapheme")


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_function_signatures_are_pinned(name: str) -> None:
    assert str(inspect.signature(getattr(bytetrunc, name))) == SIGNATURES[name]


def test_truncation_is_a_frozen_record_with_pinned_fields() -> None:
    fields = [(field.name, field.type) for field in dataclasses.fields(Truncation)]
    assert fields == [
        ("text", "str"),
        ("size", "int"),
        ("original_size", "int"),
        ("limit", "int"),
        ("encoding", "Encoding"),
        ("truncated", "bool"),
    ]
    result = truncate_detailed("h\N{LATIN SMALL LETTER E WITH ACUTE}llo", 3)
    assert result == Truncation("h\N{LATIN SMALL LETTER E WITH ACUTE}", 3, 6, 3, "utf-8", True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.text = "x"  # type: ignore[misc]
    assert not hasattr(result, "__dict__")  # slots: no stray attributes
    for twin in (pickle.loads(pickle.dumps(result)), copy.copy(result), copy.deepcopy(result)):
        assert twin == result and hash(twin) == hash(result)
    assert dataclasses.replace(result, size=4) == Truncation("h\xe9", 4, 6, 3, "utf-8", True)
    assert Truncation.__module__ == "bytetrunc"
    assert repr(result) == (
        "Truncation(text='h\xe9', size=3, original_size=6, limit=3, encoding='utf-8', "
        "truncated=True)"
    )


def test_bytetrunc_error_is_a_value_error_that_pickles() -> None:
    assert issubclass(BytetruncError, ValueError) and BytetruncError.__module__ == "bytetrunc"
    error = BytetruncError("bad")
    again = pickle.loads(pickle.dumps(error))
    assert (type(again), str(again)) == (BytetruncError, "bad")


def test_refusals_are_bytetrunc_errors_with_the_reason() -> None:
    with pytest.raises(BytetruncError, match="max_bytes must not be negative, got -1"):
        truncate_bytes("abc", -1)
    with pytest.raises(BytetruncError, match="on must be 'char' or 'grapheme', got 'word'"):
        truncate_bytes("abc", 1, on="word")  # type: ignore[arg-type]
    with pytest.raises(BytetruncError, match="unsupported encoding 'utf-16'"):
        truncate_bytes("abc", 1, encoding="utf-16")
    with pytest.raises(
        BytetruncError, match="suffix needs 3 bytes in utf-8, more than max_bytes=2"
    ):
        truncate_bytes("abcdef", 2, suffix="...")
    with pytest.raises(BytetruncError, match="suffix needs 3 UTF-16 units, more than max_units=2"):
        truncate_utf16("abcdef", 2, suffix="...")
    with pytest.raises(UnicodeEncodeError):
        byte_len("\udc00")
    assert truncate_bytes("ab", 2, suffix="...") == "ab"  # a suffix too big is fine when it fits


@pytest.mark.parametrize(
    "call",
    [
        lambda: truncate_bytes(b"abc", 2),  # type: ignore[arg-type]
        lambda: truncate_bytes("abc", "2"),  # type: ignore[arg-type]
        lambda: truncate_bytes("abc", 2.0),  # type: ignore[arg-type]
        lambda: truncate_bytes("abc", True),
        lambda: truncate_bytes("abc", None),  # type: ignore[arg-type]
        lambda: truncate_bytes("abc", 2, suffix=None),  # type: ignore[arg-type]
        lambda: truncate_bytes("abc", 2, on=None),  # type: ignore[arg-type]
        lambda: truncate_bytes("abc", 2, encoding=b"utf-8"),  # type: ignore[arg-type]
        lambda: byte_len(None),  # type: ignore[arg-type]
        lambda: truncate_utf16(["a"], 1),  # type: ignore[arg-type]
        lambda: bytetrunc.utf16_len(b"a"),  # type: ignore[arg-type]
        lambda: bytetrunc.chunk_bytes("abc", 1.5),  # type: ignore[arg-type]
        lambda: bytetrunc.cut_utf8("abc"),  # type: ignore[arg-type]
        lambda: bytetrunc.cut_utf8(b"abc", 1.0),  # type: ignore[arg-type]
        lambda: bytetrunc.iter_graphemes(b"abc"),  # type: ignore[arg-type]
        lambda: bytetrunc.truncate_filename(b"a.txt"),  # type: ignore[arg-type]
        lambda: bytetrunc.truncate_filename("a.txt", keep_extension=1),  # type: ignore[arg-type]
    ],
)
def test_wrong_argument_types_raise_type_error(call: object) -> None:
    with pytest.raises(TypeError):
        call()  # type: ignore[operator]
