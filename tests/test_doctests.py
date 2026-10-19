"""Run the examples written in the docstrings of the package and of every public name."""

from __future__ import annotations

import doctest
import importlib

import pytest

import bytetrunc

MODULES = [
    "bytetrunc",
    "bytetrunc._core",
    "bytetrunc._chunk",
    "bytetrunc._filename",
    "bytetrunc._graphemes",
    "bytetrunc._rawbytes",
]
# Values and Literal aliases cannot carry their own docstring; the package docstring
# documents each of them with an example instead.
DATA = {"ENCODINGS", "UNICODE_VERSION", "Boundary", "Encoding"}


@pytest.mark.parametrize("name", MODULES)
def test_docstring_examples(name: str) -> None:
    result = doctest.testmod(importlib.import_module(name), optionflags=doctest.ELLIPSIS)
    assert result.attempted > 0
    assert result.failed == 0


@pytest.mark.parametrize("name", sorted(set(bytetrunc.__all__) - DATA))
def test_every_public_function_and_class_has_a_passing_example(name: str) -> None:
    runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
    finder = doctest.DocTestFinder(recurse=False)
    for test in finder.find(getattr(bytetrunc, name), name, module=False, globs={}):
        runner.run(test)
    assert runner.tries > 0, name
    assert runner.failures == 0, name


@pytest.mark.parametrize("name", sorted(DATA))
def test_every_public_value_has_an_example_in_the_package_docstring(name: str) -> None:
    doc = bytetrunc.__doc__ or ""
    assert f">>> bytetrunc.{name}" in doc or f"get_args(bytetrunc.{name})" in doc, name


# Each public function with the errors it raises (the calls are checked by
# tests/test_arguments.py and tests/test_contract.py); its docstring must name each one.
RAISES = {
    "byte_len": ("BytetruncError", "TypeError", "UnicodeEncodeError"),
    "utf16_len": ("TypeError", "UnicodeEncodeError"),
    "truncate_bytes": ("BytetruncError", "TypeError", "UnicodeEncodeError"),
    "truncate_utf16": ("BytetruncError", "TypeError", "UnicodeEncodeError"),
    "truncate_filename": ("BytetruncError", "TypeError", "UnicodeEncodeError"),
    "chunk_bytes": ("BytetruncError", "TypeError", "UnicodeEncodeError"),
    "cut_utf8": ("BytetruncError", "TypeError"),
    "iter_graphemes": ("TypeError",),
}


@pytest.mark.parametrize("name", sorted(RAISES))
def test_every_public_function_documents_its_errors(name: str) -> None:
    doc = getattr(bytetrunc, name).__doc__ or ""
    for error in RAISES[name]:
        assert f"{error}`" in doc, (name, error)


def test_truncate_detailed_documents_its_errors_by_reference() -> None:
    doc = bytetrunc.truncate_detailed.__doc__ or ""
    assert "the same errors as :func:`truncate_bytes`" in doc


@pytest.mark.parametrize(
    ("name", "args", "error"),
    [
        ("byte_len", ("x", "latin-1"), bytetrunc.BytetruncError),
        ("byte_len", (b"x",), TypeError),
        ("byte_len", ("\ud800",), UnicodeEncodeError),
        ("utf16_len", (b"x",), TypeError),
        ("utf16_len", ("\ud800",), UnicodeEncodeError),
        ("truncate_utf16", ("abc", -1), bytetrunc.BytetruncError),
        ("truncate_utf16", (b"x", 1), TypeError),
        ("truncate_utf16", ("\ud800x", 1), UnicodeEncodeError),
        ("truncate_filename", ("a.txt", -1), bytetrunc.BytetruncError),
        ("truncate_filename", (b"a.txt",), TypeError),
        ("truncate_filename", ("\ud800.txt", 3), UnicodeEncodeError),
    ],
)
def test_the_documented_errors_are_the_ones_raised(
    name: str, args: tuple[object, ...], error: type[Exception]
) -> None:
    with pytest.raises(error):
        getattr(bytetrunc, name)(*args)
