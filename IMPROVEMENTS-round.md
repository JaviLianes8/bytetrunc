# Improvements for this round

Ranked by user impact. Every item is additive: the 0.1.0 API keeps its exact behaviour,
except that grapheme mode now follows the full standard instead of a partial heuristic.

1. **Standard grapheme clusters (UAX #29, Unicode 18.0.0).** Replace the heuristic
   segmenter with the complete extended grapheme cluster rules (GB1 to GB999, including
   Hangul syllables, Prepend, SpacingMark, the Indic conjunct rule GB9c, emoji ZWJ
   sequences and regional indicator pairs). Property data comes from the official UCD
   files, committed under `data/ucd/` and turned into embedded tables by
   `scripts/gen_ucd_tables.py`. The whole official `GraphemeBreakTest.txt` runs in the
   test suite. Public `iter_graphemes()` and `UNICODE_VERSION`.
2. **Other encodings.** `encoding=` on `byte_len`, `truncate_bytes` and friends:
   `utf-8`, `utf-16-le`, `utf-16-be`, `utf-32-le`, `utf-32-be`. UTF-16 never splits a
   surrogate pair. Windows wide-string APIs and many binary protocols count UTF-16 bytes.
3. **JavaScript-compatible limits.** `utf16_len()` and `truncate_utf16()` count UTF-16
   code units, the same number `String.prototype.length` reports, so a server can enforce
   a limit that a browser form also enforces.
4. **Typed results.** `truncate_detailed()` returns a frozen `Truncation` with the text,
   the bytes it uses, the original size, the limit and whether anything was cut, so
   callers can log or meter without encoding twice.
5. **Byte-limited chunks.** `chunk_bytes()` splits text into consecutive pieces that each
   fit a byte limit and join back to the exact input, on code point or grapheme
   boundaries. For SMS segments, push payloads and streaming writes.
6. **Raw bytes that may end mid-sequence.** `cut_utf8()` trims a `bytes` buffer to a
   limit (or just drops an incomplete trailing sequence) without decoding, so network
   reads and fixed-size records never yield a broken character.
7. **Filename-safe truncation.** `truncate_filename()` fits a name to a byte limit
   (255 on ext4, NTFS counts UTF-16 units) while keeping the extension whole, and
   rejects inputs that are not a single path component.
8. **Honest errors.** Clear `ValueError` messages for negative limits, unknown modes or
   encodings, suffixes that cannot fit, and a grapheme cluster larger than a chunk limit.
   Lone surrogates surface as the standard `UnicodeEncodeError`.
9. **Command line tool.** `bytetrunc truncate N`, `bytetrunc chunk N` and
   `bytetrunc count` over stdin, with runnable examples in `--help`, errors on stderr
   and exit status 1.
10. **Docs.** Full docstrings, a GUIDE with real-world byte limits (MySQL index prefixes,
    HTTP header sizes, ext4 filenames, SMS and push payloads) and the conformance story.
11. **Proof.** Contract test over the complete promise, seeded fuzzing of every mode and
    encoding, a table regeneration check, and an end-to-end test that builds a wheel,
    installs it in a fresh virtual environment and drives the real `bytetrunc` command.
