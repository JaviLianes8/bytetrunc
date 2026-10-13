# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1]

### Changed

- The Unicode Character Database files are no longer committed. `data/ucd/MANIFEST.json`
  pins them to Unicode 18.0.0 (URL, size, sha256, licence) and `scripts/fetch_upstream.py`
  fetches them; the generator check and the conformance tests skip until then. The
  generated tables stay in the package and the Unicode licence notice ships in the wheel.
- The sdist ships only the sources, tests, scripts and docs.

## [0.2.0]

### Added

- Full extended grapheme cluster segmentation per UAX #29 for Unicode 18.0.0, built
  from embedded tables generated out of the official Unicode Character Database
  (`scripts/gen_ucd_tables.py`, data in `data/ucd/`). Public `iter_graphemes()` and
  `UNICODE_VERSION`.
- `encoding=` on `byte_len`, `truncate_bytes` and the new functions: `utf-8`,
  `utf-16-le`, `utf-16-be`, `utf-32-le`, `utf-32-be`.
- `utf16_len()` and `truncate_utf16()` for JavaScript-compatible UTF-16 unit limits.
- `truncate_detailed()` returning a frozen `Truncation` with byte counts.
- `chunk_bytes()` to split text into byte-limited pieces.
- `cut_utf8()` to trim raw UTF-8 bytes without ending mid-sequence.
- `truncate_filename()` to fit a file name to a byte limit while keeping its extension.
- `bytetrunc` command line tool with `truncate`, `chunk` and `count`.
- `GUIDE.md` with real-world byte limits and conformance notes.

### Changed

- `on="grapheme"` now follows the complete standard (Hangul syllables, Prepend,
  SpacingMark, Indic conjuncts, emoji modifier and ZWJ sequences) instead of a partial
  heuristic, so some clusters are kept whole where 0.1.0 split them.
- A non-integer limit now raises `TypeError`, and error messages state the sizes.

## [0.1.0]

- First release: `truncate_bytes` with character and grapheme boundaries and a counted
  suffix, plus the `byte_len` helper.
