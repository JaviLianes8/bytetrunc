"""Grapheme segmentation against the official Unicode test file and the UAX #29 rule table.

data/ucd/GraphemeBreakTest.txt (Unicode 18.0.0) and tests/upstream/tr29-49.html (UAX #29
revision 49) are fetched by `python scripts/fetch_upstream.py` as pinned in their
manifests; the tests that read them skip until then. tests/uax29_reference.py is a second
segmenter written by hand from the rule table of that annex.
"""

from __future__ import annotations

import html
import random
import re

import pytest
from conftest import UCD, needs_ucd, official_cases, ucd_fetched, upstream_path
from uax29_reference import RULES, clusters, random_text, representatives

from bytetrunc import UNICODE_VERSION, iter_graphemes, truncate_bytes

CASES = official_cases() if ucd_fetched() else ()


def _annex_text() -> str:
    page = upstream_path("tr29-49.html").read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))


@needs_ucd
def test_fixture_matches_the_embedded_unicode_version() -> None:
    header = (UCD / "GraphemeBreakTest.txt").read_text(encoding="utf-8").splitlines()[0]
    match = re.search(r"GraphemeBreakTest-(\d+\.\d+\.\d+)\.txt", header)
    assert match is not None and match.group(1) == UNICODE_VERSION


@needs_ucd
def test_fixture_is_complete() -> None:
    # Unicode 18.0.0 ships 853 cases; a truncated fixture would silently test less.
    assert len(CASES) == 853


@pytest.mark.parametrize(("line", "expected"), CASES, ids=[f"line{n}" for n, _ in CASES])
def test_official_case(line: int, expected: tuple[str, ...]) -> None:
    text = "".join(expected)
    assert tuple(iter_graphemes(text)) == expected, f"GraphemeBreakTest.txt line {line}"
    for size, cluster in enumerate(expected):
        # Grapheme truncation keeps exactly the whole clusters that fit.
        head = "".join(expected[:size])
        budget = len(head.encode()) + len(cluster.encode()) - 1
        assert truncate_bytes(text, budget, on="grapheme") == head


@needs_ucd
def test_the_reference_rules_pass_every_official_case() -> None:
    failures = [line for line, expected in CASES if tuple(clusters("".join(expected))) != expected]
    assert failures == []


def test_the_state_machine_agrees_with_the_rule_table_on_random_text() -> None:
    rng = random.Random(29)
    pool = representatives(rng)
    for _ in range(30000):
        text = random_text(rng, pool)
        assert list(iter_graphemes(text)) == clusters(text), ascii(text)


def test_long_runs_agree_with_the_rule_table() -> None:
    linker, consonant, extend = (
        "\N{DEVANAGARI SIGN VIRAMA}",
        "\N{DEVANAGARI LETTER KA}",
        "\N{COMBINING GRAVE ACCENT}",
    )
    for text in [
        "\U0001f1e6" * 9 + "a" + "\U0001f1e6" * 4,
        consonant + (extend + linker) * 20 + consonant,
        linker * 30 + consonant,
        ("\U0001f468\N{ZERO WIDTH JOINER}" * 15) + "\U0001f469",
        "\N{HANGUL CHOSEONG KIYEOK}" * 10
        + "\N{HANGUL JUNGSEONG A}" * 5
        + "\N{HANGUL JONGSEONG KIYEOK}" * 5
        + "\N{HANGUL SYLLABLE GA}\N{HANGUL JONGSEONG KIYEOK}",
        "\N{ARABIC NUMBER SIGN}" * 6 + "a\N{DEVANAGARI SIGN VISARGA}\N{DEVANAGARI SIGN VISARGA}",
    ]:
        assert list(iter_graphemes(text)) == clusters(text), ascii(text)


def test_the_rule_table_is_the_one_of_the_fetched_annex() -> None:
    text = _annex_text()
    assert "Revision 49" in text and "Unicode 18.0.0" in text
    start = text.index("GB1 sot", text.index("3.1.1 Grapheme Cluster Boundary Rules The same"))
    table = text[start : text.index("Notes:", start)]
    assert set(re.findall(r"\bGB\d+[a-c]?\b", table)) == {rule for rule, _ in RULES}
    # Every formula appears as written, in the order of the table.
    positions = [table.find(f"{rule} {formula}") for rule, formula in RULES]
    assert -1 not in positions and positions == sorted(positions)


def test_the_annex_records_the_new_conjunct_rule() -> None:
    text = _annex_text()
    assert f"Change Rule GB9c in UAX #29 to {dict(RULES)['GB9c']}." in text
