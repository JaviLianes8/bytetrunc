"""Encoding names: the documented rule, checked against Python's own codec registry."""

from __future__ import annotations

import codecs
import contextlib
import encodings
import encodings.aliases
import random

import pytest

from bytetrunc import ENCODINGS, BytetruncError, byte_len, truncate_bytes
from bytetrunc._encodings import normalize_encoding

MODULES = {"utf_8", "utf_16_le", "utf_16_be", "utf_32_le", "utf_32_be"}


def _python_names() -> list[str]:
    """The module names and every alias Python's registry maps to the five codecs."""
    aliases = [alias for alias, module in encodings.aliases.aliases.items() if module in MODULES]
    return sorted(MODULES) + aliases


def _python_codec(spelling: str) -> str:
    """The canonical name Python's registry gives ``spelling`` (LookupError if none).

    On Windows, Python 3.14 also reads ``cp`` followed by an integer literal (``Cp6_5001``)
    as a Windows code page and returns a codec named ``cp65001``. Code page 65001 is UTF-8,
    which the codec's own output confirms here.
    """
    info = codecs.lookup(spelling)
    if info.name == "cp65001":
        sample = "aé€😀"
        assert info.encode(sample)[0] == sample.encode("utf-8")
        return "utf-8"
    return info.name


def _variants(name: str, rng: random.Random) -> list[str]:
    """Spellings of ``name`` that differ only in ASCII case and in -, _ and spaces."""
    found = [name, name.upper(), name.replace("_", "-"), name.replace("_", " ")]
    for _ in range(20):
        chars = [ch.upper() if rng.random() < 0.5 else ch for ch in name if ch != "_"]
        for _ in range(rng.randrange(4)):
            chars.insert(rng.randrange(len(chars) + 1), rng.choice("-_ "))
        found.append("".join(chars))
    return found


def test_canonical_names_are_returned_as_they_are() -> None:
    for name in ENCODINGS:
        assert normalize_encoding(name) == name


def test_every_python_alias_of_the_five_codecs_is_accepted_like_python_does() -> None:
    rng = random.Random(1)
    for name in _python_names():
        for spelling in _variants(name, rng):
            ours = normalize_encoding(spelling)
            try:
                theirs = _python_codec(spelling)
            except LookupError:
                continue  # Python needs its own separators in some aliases; we do not
            assert ours == theirs, spelling


def test_an_accepted_name_never_means_another_codec_to_python() -> None:
    rng = random.Random(2)
    spellings = [s for name in _python_names() for s in _variants(name, rng)]
    spellings += ["utf16le", "UTF32BE", "utf 8", "Utf8_Ucs4"]
    for spelling in spellings:
        with contextlib.suppress(LookupError):
            assert _python_codec(spelling) == normalize_encoding(spelling), spelling


@pytest.mark.parametrize(
    "name",
    [
        "utf-16",
        "utf-32",
        "utf-8-sig",
        "UTF-16",
        "utf_32",
        "latin-1",
        "ascii",
        "cp1252",
        "",
        "utf-8\x00",
        "\ud800",
        "utf\N{LATIN SMALL LETTER E WITH ACUTE}8",
        "unicodelittleunmar\N{KELVIN SIGN}ed",
        "utf.8",
        "utf+8",
        "utf8 ",
        "x" * 10_000,
    ],
)
def test_other_names_are_refused_with_a_short_message(name: str) -> None:
    if name == "utf8 ":
        assert normalize_encoding(name) == "utf-8"  # trailing space is a separator
        return
    with pytest.raises(BytetruncError, match="unsupported encoding") as caught:
        byte_len("a", name)
    assert len(str(caught.value)) < 200


def test_non_str_names_raise_type_error() -> None:
    for name in (None, b"utf-8", 8, ["utf-8"]):
        with pytest.raises(TypeError, match="encoding must be a str"):
            truncate_bytes("abc", 2, encoding=name)  # type: ignore[arg-type]


def test_a_str_subclass_name_is_read_as_plain_text() -> None:
    class Lying(str):
        def translate(self, table: object) -> str:
            return "utf8"

        def __eq__(self, other: object) -> bool:
            return True

        __hash__ = str.__hash__

    assert normalize_encoding(Lying("UTF-16LE")) == "utf-16-le"
    with pytest.raises(BytetruncError):
        normalize_encoding(Lying("latin-1"))


def test_unknown_names_do_not_grow_the_codec_registry_cache() -> None:
    cache = encodings._cache
    before = len(cache)
    for number in range(2000):
        with pytest.raises(BytetruncError):
            byte_len("a", f"no-such-codec-{number}")
    assert len(cache) == before
