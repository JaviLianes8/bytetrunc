"""The complete public promise of bytetrunc, one test per clause."""

from __future__ import annotations

import importlib.resources
import re
from pathlib import Path

import pytest

import bytetrunc
from bytetrunc import (
    ENCODINGS,
    UNICODE_VERSION,
    Truncation,
    byte_len,
    chunk_bytes,
    cut_utf8,
    iter_graphemes,
    truncate_bytes,
    truncate_detailed,
    truncate_filename,
    truncate_utf16,
    utf16_len,
)

ROOT = Path(__file__).resolve().parent.parent

# The public API. This list is the contract; the test below fails if they disagree.
PUBLIC_API: list[str] = [
    "ENCODINGS",
    "UNICODE_VERSION",
    "Boundary",
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
SAMPLE = (
    "Na\u00efve caf\u00e9 \U0001f469\u200d\U0001f4bb \U0001f1ef\U0001f1f5 \ud55c\uae00 e\u0301!"
)


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(bytetrunc.__all__) == sorted(PUBLIC_API)
    for name in bytetrunc.__all__:
        assert hasattr(bytetrunc, name)


def test_version_matches_pyproject_and_is_three_part() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', pyproject, re.M)
    assert match is not None and match.group(1) == bytetrunc.__version__
    assert all(part.isdigit() for part in bytetrunc.__version__.split("."))
    assert len(bytetrunc.__version__.split(".")) == 3


def test_the_package_ships_type_information_and_a_script() -> None:
    assert importlib.resources.files("bytetrunc").joinpath("py.typed").is_file()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'bytetrunc = "bytetrunc._cli:main"' in pyproject
    assert re.search(r"^dependencies = \[\]$", pyproject, re.M)


def test_unicode_version_and_encodings_are_declared() -> None:
    assert UNICODE_VERSION == "18.0.0"
    assert ENCODINGS == ("utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be")


@pytest.mark.parametrize("encoding", ENCODINGS)
@pytest.mark.parametrize("on", ["char", "grapheme"])
def test_truncate_promise_for_every_limit(encoding: str, on: str) -> None:
    total = byte_len(SAMPLE, encoding)
    clusters = list(iter_graphemes(SAMPLE))
    boundaries = {sum(len(c) for c in clusters[:i]) for i in range(len(clusters) + 1)}
    for limit in range(total + 3):
        for suffix in ("", "..."):
            if limit < total and byte_len(suffix, encoding) > limit:
                with pytest.raises(ValueError, match="suffix"):
                    truncate_bytes(SAMPLE, limit, suffix, on, encoding=encoding)  # type: ignore[arg-type]
                continue
            result = truncate_detailed(SAMPLE, limit, suffix, on, encoding=encoding)  # type: ignore[arg-type]
            assert result.size == byte_len(result.text, encoding) <= limit
            assert result.truncated == (total > limit)
            if not result.truncated:
                assert result.text == SAMPLE  # fits: unchanged, no suffix
                continue
            head = result.text[: len(result.text) - len(suffix)]
            assert result.text == head + suffix and SAMPLE.startswith(head)
            if on == "grapheme":
                assert len(head) in boundaries


def test_errors_are_honest() -> None:
    with pytest.raises(ValueError, match="negative"):
        truncate_bytes("abc", -1)
    with pytest.raises(ValueError, match="on must be"):
        truncate_bytes("abc", 1, on="word")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unsupported encoding"):
        truncate_bytes("abc", 1, encoding="utf-16")
    with pytest.raises(ValueError, match="suffix needs 3 bytes"):
        truncate_bytes("abcdef", 2, "...")
    with pytest.raises(UnicodeEncodeError):
        byte_len("\udc00")


def test_detailed_result_is_a_frozen_record() -> None:
    result = truncate_detailed("h\u00e9llo", 3)
    assert isinstance(result, Truncation)
    assert (result.text, result.size, result.original_size) == ("h\u00e9", 3, 6)
    assert (result.limit, result.encoding, result.truncated) == (3, "utf-8", True)


def test_utf16_unit_promise() -> None:
    assert utf16_len(SAMPLE) == byte_len(SAMPLE, "utf-16-le") // 2
    for units in range(utf16_len(SAMPLE) + 1):
        assert utf16_len(truncate_utf16(SAMPLE, units)) <= units


def test_chunk_promise() -> None:
    for limit in range(4, 30):
        for on in ("char", "grapheme"):
            try:
                pieces = chunk_bytes(SAMPLE, limit, on)
            except ValueError as exc:
                assert "needs" in str(exc)
                continue
            assert "".join(pieces) == SAMPLE
            assert all(0 < byte_len(p) <= limit for p in pieces)


def test_cut_utf8_promise() -> None:
    data = SAMPLE.encode()
    for limit in range(len(data) + 1):
        cut = cut_utf8(data, limit)
        assert data.startswith(cut) and len(cut) <= limit
        assert cut.decode() == truncate_bytes(SAMPLE, limit)
        assert cut_utf8(data[:limit]) == cut


def test_filename_promise() -> None:
    name = SAMPLE.replace(" ", "_") + ".json"
    for limit in range(6, byte_len(name) + 1):
        cut = truncate_filename(name, limit)
        assert byte_len(cut) <= limit and cut.endswith(".json")
        assert name.startswith(cut[: -len(".json")])


def test_graphemes_promise() -> None:
    clusters = list(iter_graphemes(SAMPLE))
    assert "".join(clusters) == SAMPLE
    assert "\U0001f469\u200d\U0001f4bb" in clusters
    assert "\U0001f1ef\U0001f1f5" in clusters
    assert "e\u0301" in clusters
    assert list(iter_graphemes("")) == []
