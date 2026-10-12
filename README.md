# bytetrunc

Truncate a string to a maximum number of UTF-8 bytes on a safe character or grapheme
boundary, with an optional counted suffix. Typed, zero dependencies, and conformant
with Unicode 18.0.0 grapheme clusters (UAX #29).

## Install

```
pip install bytetrunc
```

## Usage

```python
from bytetrunc import byte_len, truncate_bytes

# é is two UTF-8 bytes:
byte_len("héllo")  # -> 6

# Cut to a byte budget without ever splitting a character.
truncate_bytes("héllo world", 6)  # -> 'héllo'

# Append a suffix whose own bytes count against the budget.
truncate_bytes("héllo world", 8, suffix="...")  # -> 'héll...'

# Keep whole grapheme clusters: base plus combining marks, flags, emoji sequences.
truncate_bytes("man\u0303ana", 4, on="grapheme")  # -> 'ma'
```

More tools for the same job:

```python
from bytetrunc import (
    chunk_bytes,
    cut_utf8,
    iter_graphemes,
    truncate_detailed,
    truncate_filename,
    truncate_utf16,
)

# Count bytes in another encoding (UTF-16 never splits a surrogate pair).
truncate_bytes("abcdef", 4, encoding="utf-16-le")  # -> 'ab'

# Enforce the same limit JavaScript's .length enforces.
truncate_utf16("ab\U0001f600", 3)  # -> 'ab'

# Get the byte counts back.
truncate_detailed("héllo", 3).size  # -> 3

# Split into pieces that each fit, for SMS parts or push payloads.
chunk_bytes("héllo wörld", 5)  # -> ['héll', 'o wö', 'rld']

# Trim raw bytes that may end in the middle of a character.
cut_utf8(b"abc\xe2\x82")  # -> b'abc'

# Fit a file name to 255 bytes (ext4) and keep its extension.
truncate_filename("quarterly report.pdf", 12)  # -> 'quarterl.pdf'

# The segmentation itself.
len(list(iter_graphemes("\U0001f1ea\U0001f1f8e\u0301")))  # -> 2
```

From the shell:

```
printf 'héllo world\n' | bytetrunc truncate 6
printf 'one long SMS body\n' | bytetrunc chunk 8
printf 'héllo\n' | bytetrunc count --encoding utf-16-le
```

Every function returns the input unchanged when it already fits, and otherwise
guarantees the result stays within the limit. Bad arguments raise `ValueError` with a
message that says what to change. See [GUIDE.md](GUIDE.md) for real-world byte limits,
how to choose a boundary, and the conformance story.

## Why

Several languages ship this as a named primitive (truncating text to a byte limit on a
safe boundary): Rust has `floor_char_boundary`, Go callers lean on `utf8.RuneCount`
helpers, and JavaScript projects reach for `Buffer`-aware truncators. Python has no
clean, typed package for it. The naive `s.encode("utf-8")[:n].decode()` throws on a
split multibyte character, and ad-hoc fixes ignore grapheme clusters and the suffix
budget. Reach for this when writing to a fixed-width column, a protocol field, or a
store with a byte cap (database columns, headers, filenames). Pure standard library,
no runtime dependencies.

## License

MIT. See [LICENSE](LICENSE). The Unicode data files in `data/ucd/` are covered by the
[Unicode License v3](https://www.unicode.org/license.txt).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
