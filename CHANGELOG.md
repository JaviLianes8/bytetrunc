# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-19

The first stable release. The fifteen names in `bytetrunc.__all__`, their signatures,
defaults, return types and error types are now stable and follow Semantic Versioning:
`truncate_bytes`, `truncate_detailed`, `truncate_utf16`, `truncate_filename`,
`chunk_bytes`, `cut_utf8`, `byte_len`, `utf16_len`, `iter_graphemes`, `Truncation`,
`BytetruncError`, `Boundary`, `Encoding`, `ENCODINGS` and `UNICODE_VERSION`, plus the
`bytetrunc` command (`truncate`, `chunk`, `count`) and its exit statuses. The grapheme
cluster rules and data follow Unicode 18.0.0; a later Unicode version will come in a
minor release and change `UNICODE_VERSION`.

### Added

- `BytetruncError`, a subclass of `ValueError`, raised for every value bytetrunc refuses.
  `except ValueError` keeps working.
- Docstring examples on every public name, run as doctests, and the errors each public
  function raises.

### Changed

- `suffix` and `on` are keyword-only in `truncate_bytes`, `truncate_detailed`,
  `truncate_utf16` and `truncate_filename` (as `encoding` and `keep_extension` already
  were). Write `truncate_bytes(s, 10, suffix="...")`, not `truncate_bytes(s, 10, "...")`.
- `on` is keyword-only in `chunk_bytes`: write `chunk_bytes(s, 10, on="grapheme")`, not
  `chunk_bytes(s, 10, "grapheme")`, which now raises `TypeError`.
- Limits accept any integer type with `__index__` (for example NumPy integers) and are
  stored as a plain `int` in `Truncation.limit`. `bool` is still refused.
- Arguments of the wrong type raise `TypeError` in every function: the text, the suffix,
  `on`, `encoding`, the file name and `keep_extension` (which must be a real `bool`).
  `iter_graphemes` raises it at the call, not at the first item. A `str` subclass is
  read as plain text and the result is always a plain `str`.
- Encoding names are matched without the codec registry: ASCII case, hyphens,
  underscores and spaces are ignored, and Python's own aliases of the five codecs (such
  as `u8`, `cp65001` or `UnicodeLittleUnmarked`) still work. Unknown names no longer add
  entries to Python's codec cache. Other spellings the codec registry used to accept,
  such as names with dots (`utf.16le`), tabs or newlines, or a non-ASCII hyphen, now
  raise `BytetruncError`. Some names the codec registry refused are now accepted, such
  as `utf16le`, `UTF16-BE` or `utf32be`, since only the separators differ from a
  supported name. `ENCODINGS` and `Truncation.encoding` are typed with
  the `Encoding` literal.
- Error messages quote at most 32 characters of any text and print very wide integers
  by their size, so they stay short whatever the input. The suffix error of
  `truncate_utf16` counts UTF-16 units.
- `cut_utf8` drops a trailing sequence only when it is the unfinished start of a
  well-formed UTF-8 character (RFC 3629 ranges); every other byte is kept, valid or not,
  for a strict decode to reject. A `memoryview` of any format or layout is cut by its
  raw bytes. A released `memoryview` raises `BytetruncError`, not a bare `ValueError`;
  an error raised by the buffer export of a `bytes` or `bytearray` subclass reaches the
  caller unchanged.
- The `repr` of a `Truncation` prints a size, original size or limit too wide for
  Python's integer printing limit (4300 digits) by its size, so printing or logging any result works.
- Type names in `TypeError` messages are cut to 40 characters after escaping, so a
  class name made of non-printable characters stays short too.
- The command exits with 2 for a wrong command line (it was 1) and `--encoding` accepts
  the same names as the library. The limit argument is called `MAX_BYTES` in the help and
  in usage errors (it was `N`), matching the error messages, and an extension too long
  for `--keep-extension` suggests running without that option.

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
