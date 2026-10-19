# bytetrunc

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

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

The `truncate_*` functions return the input unchanged when it already fits, and
otherwise guarantee the result stays within the limit. A value bytetrunc refuses (a
negative limit, an unknown encoding, a suffix larger than the limit) raises
`BytetruncError`, a subclass of `ValueError`, with a short message that says what to
change; an argument of the wrong type raises `TypeError`. The command exits with 1 for
input it cannot handle and 2 for a wrong command line. See the
[guide](https://github.com/JaviLianes8/bytetrunc/blob/main/GUIDE.md) for real-world byte
limits, how to choose a boundary and the conformance story, and the
[changelog](https://github.com/JaviLianes8/bytetrunc/blob/main/CHANGELOG.md) for what
changed in each version.

## Why

Databases, file systems, HTTP headers, SMS and push payloads cap the bytes of a text,
not its length. The usual one-liner, `s.encode()[:n].decode("utf-8", "ignore")`, keeps
whole code points, but it splits what a reader sees as one character (with `n=4` it
turns `"man\u0303ana"` into `"man"`, an `n` without its tilde), it leaves the room for a
`"..."` suffix to you, and with the default `errors="strict"` it raises instead.

Grapheme clusters are covered on PyPI by the `regex` module (`\X`) and by `uniseg`,
which find the clusters and leave the byte budget to you, and by `grapheme` 0.6.0
(Unicode 13.0.0, last released in March 2020), whose helpers count and slice clusters,
not bytes. bytetrunc does the byte budget itself: the suffix counted in the limit,
UTF-8, UTF-16 and UTF-32 counts, JavaScript `.length` limits, chunking, file names and
raw byte buffers, on Unicode 18.0.0 clusters checked against the official test file.
It is typed, has no runtime dependencies and runs on CPython 3.10 to 3.14.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/bytetrunc/blob/main/LICENSE). The
property tables in `src/bytetrunc/_ucd_*.py` are generated from the Unicode Character
Database and are covered by the
[Unicode License v3](https://github.com/JaviLianes8/bytetrunc/blob/main/LICENSE-UNICODE),
fetched from https://www.unicode.org/license.txt.

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
