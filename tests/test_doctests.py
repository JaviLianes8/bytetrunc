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
