# bytetrunc

Truncate a string to a maximum number of UTF-8 bytes on a safe character or grapheme boundary, with an optional counted suffix

## Install

```
pip install bytetrunc
```

## Usage

```python
from bytetrunc import byte_len, truncate_bytes

byte_len("héllo")  # 6: é is two UTF-8 bytes

# Cut to a byte budget without ever splitting a character.
truncate_bytes("héllo world", 6)  # 'héllo'

# Append a suffix whose own bytes count against the budget.
truncate_bytes("héllo world", 8, suffix="...")  # 'héll...'

# Keep whole grapheme clusters (base plus combining marks, flags, emoji).
truncate_bytes("mañana", 3, on="grapheme")  # 'ma'
```

`truncate_bytes` returns the input unchanged when it already fits, and otherwise
guarantees the result stays within `max_bytes`. It raises `ValueError` for a negative
budget, an unknown boundary, or a suffix that cannot fit on its own.

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

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
