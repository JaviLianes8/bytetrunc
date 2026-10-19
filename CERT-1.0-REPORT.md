# bytetrunc 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to bytetrunc. PyPI has no release
(`https://pypi.org/pypi/bytetrunc/json` answered 404 on 2026-10-18 and again on
2026-10-19), so 1.0.0 is the first published version and there is no upgrade path to
test; every change since 0.2.1, the last version in the CHANGELOG (unpublished), is
listed in the CHANGELOG all the same.

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.2.1, ef98f2d)
- [x] Baseline gates on 0.2.1
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: Unicode files and UAX #29 fetched live, reference implementations (item 7)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e, every Python (items 8, 10, 13, 14)
- [x] Gates (item 15)
- [x] PR and trace guard CLEAN
- [ ] Five QA lenses (item 19) and independent reviewer (item 16): run by the maintainer next

## Scorecard (author)

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: 15 names; `suffix` and `on` made keyword-only, `BytetruncError` added, limits take `__index__` integers; signatures pinned in `tests/test_contract.py`; every change in the CHANGELOG |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples, doctests | PASS: every public name; README and GUIDE `# ->` lines run as tests |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed` shipped, a consumer type-checks against the installed wheel |
| 5 | Typed, documented, bounded errors | PASS: `BytetruncError` (a `ValueError`), `TypeError` for wrong types, messages quote at most 32 characters |
| 6 | Contract tests of every public name | PASS: `tests/test_contract.py`, `tests/test_promises.py` |
| 7 | Real ground truth | PASS: see below; all nine sources fetched again on 2026-10-19 with matching sha256 |
| 8 | Real e2e from the wheel | PASS: wheel in a fresh venv, used from an empty folder with `-I`, CLI by subprocess; no PyPI release to upgrade from |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS: `tests/test_fuzz.py`, `tests/test_hostile.py` |
| 10 | Supported Pythons | PASS: CPython 3.10.22, 3.11.17, 3.12.15, 3.13.16, 3.14.8, 3.14.8 free-threaded |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links, comparison checked against PyPI |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-19 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 18 | Contracts bite (mutations) | PASS: 46 author mutants, 41 killed at once, 2 killed by contracts added after the round, 3 argued equivalent |

## Baseline on 0.2.1 (before any change)

On this PC, CPython 3.13.2: `ruff format --check .`, `ruff check .`, `mypy --strict src tests`,
`mypy --strict src` and `python scripts/gen_ucd_tables.py --check` exit 0. Full suite on the
laptop from a fresh clone of `release/1.0.0` at ef98f2d with the Unicode files fetched
(CPython 3.14): 952 passed (the 853 official grapheme cases included), exit 0.

## API review (items 1 to 5)

Kept: the fifteen public names of 0.2.1 with their parameter names and defaults. Changed,
all in the CHANGELOG (the GUIDE has new Errors and Stability sections): `suffix` and `on`
keyword-only; `BytetruncError` for every refusal; `TypeError` for every wrong type (an exact
`bool` for `keep_extension`, `str` subclasses read as plain text); limits accept any
`__index__` integer; encoding names matched without the codec registry, which caches
unknown names; short messages; `cut_utf8` follows the RFC 3629 ranges and reads any
`memoryview` by its raw bytes; the command exits 2 for a wrong command line. Internal:
`_errors.py`, `_rawbytes.py` and `_cli_args.py` split out to keep files under 200 lines.
`scripts/release.ps1` now refuses only a version already on PyPI, and a dirty tree.

## Ground truth (item 7)

Nothing fetched is committed or shipped: `data/ucd/MANIFEST.json` and
`tests/upstream/MANIFEST.json` record URL, revision, size, sha256 and licence, and
`scripts/fetch_upstream.py` fetches them; tests check the hash before reading and skip when
a file is absent. All nine were fetched again on 2026-10-19 and match their manifests.

- Unicode 18.0.0 `GraphemeBreakTest.txt`: all 853 official cases.
- Unicode 18.0.0 `GraphemeBreakProperty.txt`, `emoji-data.txt` and
  `DerivedCoreProperties.txt`: the embedded tables equal a fresh run of the generator.
- UAX #29 revision 49 (`tr29-49.html`): the rule table is read from the annex, and a second
  segmenter written by hand from it (`tests/uax29_reference.py`) agrees with the library on
  the official cases, on seeded random text and on long runs.
- RFC 3629: the `UTF8-char` grammar is read from the text and every cut point of `cut_utf8`
  is checked against it; the incremental UTF-8 decoder of CPython agrees.
- Unicode 17.0.0 property files: used to leave out the code points whose properties changed
  in 18.0 when comparing with segmenters that are still on 17.0.
- Reference implementations run live: the `regex` module 2026.9.29 (`\X`), and Node.js
  v24.18.0 (laptop, ICU 78.3, Unicode 17.0) and v25.5.0 (Elena's PC, Unicode 17.0):
  `Intl.Segmenter` clusters and cuts, `TextEncoder.encodeInto` whole code points and
  `String.prototype.length` UTF-16 units, thousands of seeded texts each, no difference.
- The Python codec registry: every alias of the five codecs, in many spellings, means the
  same codec to Python and to bytetrunc. On Windows, Python 3.14 reads `cp` followed by an
  integer literal such as `Cp6_5001` as code page 65001; the test now confirms that codec
  writes UTF-8 (the name comparison failed on 3.14 until 367755e).

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`: seeded random text over every property class (truncation invariants in
every encoding and boundary, chunk invariants, `cut_utf8` against text truncation,
segmentation round trip). `tests/test_hostile.py`: nine adversarial shapes (one cluster of
40,000 marks, regional indicator floods, ZWJ and Indic conjunct chains, jamo, CR LF floods,
lone CR floods, astral text, a mix) timed at n and 4n through grapheme truncation, UTF-16
truncation, segmentation and chunking (all linear), a cluster larger than a chunk,
continuation byte floods for `cut_utf8` and dot floods for `truncate_filename`; 1 MB texts
and a 5,000 digit integer in every error path give messages under 200 characters.

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

At e622459 on Elena's PC from a fresh clone: `python -m build`, then `twine check --strict`
PASSED for both files. The wheel holds the 14 modules, `py.typed`, `LICENSE` and
`LICENSE-UNICODE` and nothing else; the sdist holds the sources, the tests, the two
manifests (no fetched file), the two scripts, the docs and both licences, and no scratch
file or this report. `tests/test_e2e_wheel.py` (with `BYTETRUNC_E2E=1`) builds both,
inspects them, installs the wheel in a fresh venv, runs a consumer program from an empty
folder with `-I`, drives `bytetrunc` and `python -m bytetrunc` by subprocess (exit statuses
0, 1 and 2), type-checks a strict consumer against the wheel and runs the sdist suite with
`src` removed. Metadata: 1.0.0, `Development Status :: 5 - Production/Stable`, Python 3.10
to 3.14 classifiers, `License-Expression: MIT`, Homepage, Source, Issues and Changelog URLs,
no runtime dependency.

Every CPython available here from `requires-python` up, each with the built wheel in a fresh
venv and the suite run against it (src removed, fetched sources and `regex` present):
3.10.22, 3.11.17, 3.12.15, 3.13.16, 3.14.8 and 3.14.8 free-threaded, 1094 passed and 5
skipped each (the e2e tests, which need the source tree and ran in the gate run). 3.8 and
3.9 are below `requires-python`.

## Gates (item 15)

At e622459 on Elena's PC from a fresh clone, each command on its own, with the fetched
sources, `regex`, Node.js and `BYTETRUNC_E2E=1`: `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests`, `python scripts/gen_ucd_tables.py --check`
and `pytest` (1099 passed, no skips) all exit 0.

## Author mutation round (item 18)

46 mutants over every module, each applied alone to a fresh clone of the pushed branch at
aed8cc0 on Elena's PC, the full suite (fetched sources, `regex` and Node.js present) run with
`-x` and a 300 s per-test limit. 41 were killed at once. Of the five survivors, two showed
missing contracts, added in e622459 and checked to kill them; three are equivalent, as
argued in the table.

| Mutant | Module | Bug injected | Result | Caught by |
| --- | --- | --- | --- | --- |
| C1 | `_core` | exact fit treated as too long | killed | `tests/test_contract.py::test_refusals_are_bytetrunc_errors_with_the_reason` |
| C2 | `_core` | suffix not counted in the budget | killed | `tests/test_api.py::test_utf16_units_match_javascript_length` |
| C3 | `_core` | suffix one byte too large accepted | killed | `tests/test_cli.py::test_input_that_cannot_be_handled_exits_1` |
| C4 | `_core` | last whole cluster dropped | killed | `tests/test_api.py::test_grapheme_mode_keeps_each_cluster_whole` |
| C5 | `_core` | size counted in code points | killed | `tests/test_fuzz.py::test_truncation_invariants` |
| C6 | `_core` | UTF-16 limit off by one byte | survived | equivalent: UTF-16 byte counts are even, so a limit of 2n+1 bytes cuts, fits and reports exactly like 2n (the reported limit is divided back by 2) |
| C7 | `_core` | truncated flag wrong when it fits | killed | `tests/test_api.py::test_detailed_result_reports_sizes` |
| C8 | `_core` | default boundary of truncate_bytes changed | killed | `tests/test_api.py::test_char_mode_may_split_a_cluster_but_never_a_code_point` |
| E1 | `_encodings` | UTF-8 continuation test wrong | killed | `tests/test_api.py::test_grapheme_mode_keeps_each_cluster_whole` |
| E2 | `_encodings` | low surrogate taken for a high one | killed | `tests/test_api.py::test_grapheme_mode_keeps_each_cluster_whole` |
| E3 | `_encodings` | wrong endianness of the high byte | killed | `tests/test_api.py::test_utf16_never_splits_a_surrogate_pair` |
| E4 | `_encodings` | UTF-16 and UTF-32 widths swapped | killed | `tests/test_api.py::test_utf16_never_splits_a_surrogate_pair` |
| E5 | `_encodings` | alias mapped to another codec | killed | `tests/test_encodings.py::test_every_python_alias_of_the_five_codecs_is_accepted_like_python_does` |
| E6 | `_encodings` | hyphen no longer ignored in names | killed | `tests/test_encodings.py::test_every_python_alias_of_the_five_codecs_is_accepted_like_python_does` |
| R1 | `_errors` | bool accepted as a limit | killed | `tests/test_api.py::test_limit_type_is_checked` |
| R2 | `_errors` | limit -1 accepted | killed | `tests/test_chunk_filename_bytes.py::test_cut_utf8_with_a_limit` |
| R3 | `_errors` | messages quote huge text | killed | `tests/test_cli.py::test_huge_input_in_an_error_is_not_echoed` |
| R4 | `_errors` | wrong error base type | killed | `tests/test_cli.py::test_input_that_cannot_be_handled_exits_1` |
| R5 | `_errors` | huge integers printed in full | killed | `tests/test_hostile.py::test_messages_stay_short_for_huge_inputs` |
| B1 | `_rawbytes` | overlong E0 start dropped | killed | `tests/test_cut_utf8.py::test_cut_points_follow_the_rfc_3629_grammar` |
| B2 | `_rawbytes` | F4 beyond U+10FFFF dropped | killed | `tests/test_cut_utf8.py::test_cut_points_follow_the_rfc_3629_grammar` |
| B3 | `_rawbytes` | C0 and C1 leads treated as valid | killed | `tests/test_cut_utf8.py::test_cut_points_follow_the_rfc_3629_grammar` |
| B4 | `_rawbytes` | F5 to F7 leads treated as valid | killed | `tests/test_cut_utf8.py::test_cut_points_follow_the_rfc_3629_grammar` |
| B5 | `_rawbytes` | three continuation bytes not walked | survived | equivalent: three continuation bytes before the cut always keep the cut, whether the walk stops at the third one (no lead found) or reaches a byte past it |
| B6 | `_rawbytes` | lead byte kept on a cut | killed | `tests/test_chunk_filename_bytes.py::test_cut_utf8_drops_an_incomplete_tail` |
| K1 | `_chunk` | zero chunk limit not refused up front | killed | `tests/test_chunk_filename_bytes.py::test_cluster_larger_than_limit_is_an_honest_error` |
| K2 | `_chunk` | chunks one cluster short | killed | `tests/test_chunk_filename_bytes.py::test_grapheme_chunks_keep_emoji_sequences_whole` |
| K3 | `_chunk` | chunk budget not reset | killed | `tests/test_chunk_filename_bytes.py::test_grapheme_chunks_keep_emoji_sequences_whole` |
| K4 | `_chunk` | error index counted in bytes | survived | killed after the fix by `test_cluster_larger_than_limit_is_an_honest_error` (index after several multibyte pieces, added in e622459) |
| F1 | `_filename` | first dot taken as the extension | killed | `tests/test_chunk_filename_bytes.py::test_filename_keeps_extension_on_ext4` |
| F2 | `_filename` | leading dot taken as an extension | killed | `tests/test_chunk_filename_bytes.py::test_filename_keeps_extension_on_ext4` |
| F3 | `_filename` | empty stem accepted | killed | `tests/test_promises.py::test_filename_keeps_its_extension_and_fits` |
| F4 | `_filename` | NUL in a name accepted | killed | `tests/test_chunk_filename_bytes.py::test_filename_rejections` |
| F5 | `_filename` | extension counted in code points | killed | `tests/test_chunk_filename_bytes.py::test_filename_for_ntfs_counts_utf16_units` |
| G1 | `_graphemes` | GB3 reversed | killed | `tests/test_api.py::test_crlf_is_one_cluster` |
| G2 | `_graphemes` | regional indicator pairing off by one | killed | `tests/test_api.py::test_crlf_is_one_cluster` |
| G3 | `_graphemes` | GB9c without a linker | killed | `tests/test_grapheme_conformance.py::test_official_case` |
| G4 | `_graphemes` | GB11 without a pictograph | survived | equivalent: the pictograph state is 1 only after a pictograph or Extend, never right after a ZWJ, so `emoji >= 1` and `emoji == 2` agree when the previous character is ZWJ |
| G5 | `_graphemes` | GB9c extend run dropped | killed | `tests/test_grapheme_conformance.py::test_official_case` |
| G6 | `_graphemes` | GB6 misses LVT | killed | `tests/test_grapheme_conformance.py::test_official_case` |
| U1 | `_ucd` | property lookup off by one at run starts | killed | `tests/test_api.py::test_grapheme_mode_keeps_each_cluster_whole` |
| L1 | `_cli` | CRLF lines cut with the CR | killed | `tests/test_cli.py::test_truncate_lines_keeps_line_endings` |
| L2 | `_cli` | error exit status 0 | killed | `tests/test_cli.py::test_input_that_cannot_be_handled_exits_1` |
| L3 | `_cli` | chunk separators swapped | killed | `tests/test_cli.py::test_chunk_and_null_separator` |
| L4 | `_cli_args` | huge limits reach int() | survived | killed after the fix by `test_limits_past_4000_digits_are_refused_and_leading_zeros_are_not_digits` (added in e622459) |
| L5 | `_cli` | empty lines sent to truncate_filename | killed | `tests/test_cli.py::test_keep_extension_passes_empty_lines` |
