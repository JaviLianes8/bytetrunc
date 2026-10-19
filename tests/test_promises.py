"""The complete promise of every public function, one test per clause, on one rich sample."""

from __future__ import annotations

import pytest

from bytetrunc import (
    ENCODINGS,
    Boundary,
    BytetruncError,
    Encoding,
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

SAMPLE = (
    "Na\N{LATIN SMALL LETTER I WITH DIAERESIS}ve caf\N{LATIN SMALL LETTER E WITH ACUTE} "
    "\U0001f469\N{ZERO WIDTH JOINER}\U0001f4bb "  # woman technologist, one cluster
    "\U0001f1ef\U0001f1f5 "  # the flag of Japan, two regional indicators
    "\N{HANGUL SYLLABLE HAN}\N{HANGUL SYLLABLE GEUL} e\N{COMBINING ACUTE ACCENT} "
    "\N{DEVANAGARI LETTER KA}\N{DEVANAGARI SIGN VIRAMA}\N{DEVANAGARI LETTER SSA} "  # a conjunct
    "\r\n!"
)
BOUNDARIES: tuple[Boundary, ...] = ("char", "grapheme")


def _units(text: str, on: Boundary) -> list[str]:
    return list(text) if on == "char" else list(iter_graphemes(text))


def _ends(text: str, on: Boundary) -> list[int]:
    ends = [0]
    for unit in _units(text, on):
        ends.append(ends[-1] + len(unit))
    return ends


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_byte_len_is_the_size_of_the_encoding(encoding: Encoding) -> None:
    for end in range(len(SAMPLE) + 1):
        assert byte_len(SAMPLE[:end], encoding) == len(SAMPLE[:end].encode(encoding))
    assert byte_len(SAMPLE) == len(SAMPLE.encode("utf-8"))


@pytest.mark.parametrize("encoding", ENCODINGS)
@pytest.mark.parametrize("on", BOUNDARIES)
def test_truncate_keeps_the_longest_prefix_that_fits(encoding: Encoding, on: Boundary) -> None:
    total = byte_len(SAMPLE, encoding)
    ends = _ends(SAMPLE, on)
    for limit in range(total + 3):
        for suffix in ("", "...", "\N{HORIZONTAL ELLIPSIS}"):
            options = {"suffix": suffix, "on": on, "encoding": encoding}
            if limit < total and byte_len(suffix, encoding) > limit:
                with pytest.raises(BytetruncError, match="suffix needs"):
                    truncate_bytes(SAMPLE, limit, **options)  # type: ignore[arg-type]
                continue
            result = truncate_detailed(SAMPLE, limit, **options)  # type: ignore[arg-type]
            size = byte_len(result.text, encoding)
            assert result == Truncation(result.text, size, total, limit, encoding, total > limit)
            assert result.size <= limit
            assert truncate_bytes(SAMPLE, limit, **options) == result.text  # type: ignore[arg-type]
            if not result.truncated:
                assert result.text == SAMPLE  # fits: unchanged, no suffix
                continue
            head = result.text[: len(result.text) - len(suffix)]
            assert result.text == head + suffix and SAMPLE.startswith(head)
            assert len(head) in ends
            following = ends[ends.index(len(head)) + 1]
            budget = limit - byte_len(suffix, encoding)
            assert byte_len(SAMPLE[:following], encoding) > budget  # nothing longer fits


@pytest.mark.parametrize("on", BOUNDARIES)
def test_utf16_units_are_counted_like_javascript(on: Boundary) -> None:
    assert utf16_len(SAMPLE) == byte_len(SAMPLE, "utf-16-le") // 2
    assert utf16_len("\U0001f600") == 2 and utf16_len("") == 0
    for units in range(utf16_len(SAMPLE) + 2):
        for suffix in ("", "~"):
            if utf16_len(suffix) > units and utf16_len(SAMPLE) > units:
                with pytest.raises(BytetruncError):
                    truncate_utf16(SAMPLE, units, suffix=suffix, on=on)
                continue
            got = truncate_utf16(SAMPLE, units, suffix=suffix, on=on)
            same = truncate_bytes(SAMPLE, units * 2, suffix=suffix, on=on, encoding="utf-16-le")
            assert got == same and utf16_len(got) <= units


@pytest.mark.parametrize("encoding", ENCODINGS)
@pytest.mark.parametrize("on", BOUNDARIES)
def test_chunks_are_greedy_whole_and_fit(encoding: Encoding, on: Boundary) -> None:
    biggest = max(byte_len(unit, encoding) for unit in _units(SAMPLE, on))
    ends = set(_ends(SAMPLE, on))
    for limit in range(1, byte_len(SAMPLE, encoding) + 2):
        if limit < biggest:
            with pytest.raises(BytetruncError, match="needs"):
                chunk_bytes(SAMPLE, limit, on=on, encoding=encoding)
            continue
        pieces = chunk_bytes(SAMPLE, limit, on=on, encoding=encoding)
        assert "".join(pieces) == SAMPLE
        position = 0
        for number, piece in enumerate(pieces):
            assert 0 < byte_len(piece, encoding) <= limit
            position += len(piece)
            assert position in ends  # pieces end on a code point or cluster boundary
            if number < len(pieces) - 1:
                after = _units(SAMPLE[position:], on)[0]
                assert byte_len(piece + after, encoding) > limit  # greedy: the next unit spills
    assert chunk_bytes("", 1) == []
    with pytest.raises(BytetruncError, match="positive"):
        chunk_bytes("abc", 0)


def test_cut_utf8_cuts_raw_bytes_like_text() -> None:
    data = SAMPLE.encode()
    for limit in range(len(data) + 2):
        cut = cut_utf8(data, limit)
        assert data.startswith(cut) and len(cut) <= limit
        assert cut.decode() == truncate_bytes(SAMPLE, limit)
        assert cut_utf8(data[:limit]) == cut
    assert cut_utf8(data) == data and cut_utf8(b"") == b""
    assert cut_utf8(b"ab\xff\xc3") == b"ab\xff"  # an unfinished character goes, junk stays
    with pytest.raises(BytetruncError):
        cut_utf8(data, -1)


def test_filename_keeps_its_extension_and_fits() -> None:
    name = SAMPLE.replace(" ", "_").replace("\r\n", "") + ".json"
    for limit in range(6, byte_len(name) + 2):
        cut = truncate_filename(name, limit)
        assert byte_len(cut) <= limit and cut.endswith(".json")
        stem = cut[: -len(".json")]
        assert stem == truncate_bytes(name[: -len(".json")], limit - 5, on="grapheme")
    assert truncate_filename(name) == name  # 255 bytes by default, and it fits
    with pytest.raises(BytetruncError, match="leaves no room"):
        truncate_filename(name, 5)


def test_graphemes_concatenate_back_and_are_never_empty() -> None:
    clusters = list(iter_graphemes(SAMPLE))
    assert "".join(clusters) == SAMPLE and all(clusters)
    expected = [
        "\U0001f469\N{ZERO WIDTH JOINER}\U0001f4bb",
        "\U0001f1ef\U0001f1f5",
        "e\N{COMBINING ACUTE ACCENT}",
        "\r\n",
        "\N{DEVANAGARI LETTER KA}\N{DEVANAGARI SIGN VIRAMA}\N{DEVANAGARI LETTER SSA}",  # GB9c
    ]
    assert [cluster for cluster in expected if cluster not in clusters] == []
    assert list(iter_graphemes("")) == []
