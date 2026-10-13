# bytetrunc guide

This guide explains when byte limits bite, which function to reach for, and what
exactly each one promises. Every example runs as written.

## Why byte limits are different from length limits

`len(s)` counts code points. Storage, protocols and file systems count bytes, and in
UTF-8 a code point takes 1 to 4 bytes. Slicing the encoded bytes (`data[:n]`) can stop
in the middle of a character, and slicing the string (`s[:n]`) can stop in the middle
of what a reader sees as one character: an accented letter written as `e` plus a
combining accent, a flag made of two regional indicators, or a family emoji made of
five code points joined with zero width joiners.

Real limits you will meet:

| Where | Limit | How to call bytetrunc |
| --- | --- | --- |
| MySQL InnoDB index key prefix, `DYNAMIC` row format | 3072 bytes | `truncate_bytes(s, 3072)` |
| MySQL InnoDB index key prefix, `COMPACT` row format | 767 bytes (a `utf8mb4` column needs 4 bytes per character, so only 191 are safe) | `truncate_bytes(s, 767)` |
| ext4, XFS, Btrfs file name | 255 bytes | `truncate_filename(name)` |
| NTFS file name | 255 UTF-16 code units | `truncate_filename(name, 510, encoding="utf-16-le")` |
| Apache request header field | 8190 bytes (`LimitRequestFieldSize`) | `truncate_bytes(value, 8190)` |
| nginx header buffer | 8 KiB (`large_client_header_buffers 4 8k`) | `truncate_bytes(value, 8192)` |
| SMS in UCS-2 / UTF-16 | 140 octets per message, 134 per part of a concatenated message | `chunk_bytes(body, 134, encoding="utf-16-be")` |
| Apple push notification payload | 4096 bytes | `truncate_bytes(alert, budget)` after the rest of the JSON |
| Browser `maxlength`, JavaScript `.length` | UTF-16 code units | `truncate_utf16(s, n)` |

Sources: [MySQL InnoDB limits](https://dev.mysql.com/doc/refman/8.4/en/innodb-limits.html),
[ext4 directory entries](https://www.kernel.org/doc/html/latest/filesystems/ext4/directory.html),
[Windows path limits](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation),
[Apache core](https://httpd.apache.org/docs/2.4/mod/core.html#limitrequestfieldsize),
[nginx core](https://nginx.org/en/docs/http/ngx_http_core_module.html#large_client_header_buffers),
[SMS character limits](https://www.twilio.com/docs/glossary/what-sms-character-limit),
[APNs payloads](https://developer.apple.com/documentation/usernotifications/generating-a-remote-notification).

## Choosing a boundary

`on="char"` (the default for `truncate_bytes` and `chunk_bytes`) never splits a code
point. It is the fastest mode and right for identifiers, keys and machine text.

`on="grapheme"` never splits an extended grapheme cluster as defined by
[UAX #29](https://www.unicode.org/reports/tr29/). Use it for anything a person will
read: titles, previews, notification text, file names.

```python
from bytetrunc import truncate_bytes

family = "\U0001f468\u200d\U0001f469\u200d\U0001f467"  # 18 bytes, one visible emoji
# char mode leaves a stray man and joiner behind:
truncate_bytes("hi " + family, 10)  # -> 'hi \U0001f468\u200d'
truncate_bytes("hi " + family, 10, on="grapheme")  # -> 'hi '
```

## Suffixes count against the limit

```python
truncate_bytes("an important message", 12, suffix="...")  # -> 'an import...'
```

The suffix is only added when the input was cut. If the suffix alone is larger than
the limit, `ValueError` is raised rather than silently returning something too long.

## Other encodings

`encoding=` accepts `utf-8`, `utf-16-le`, `utf-16-be`, `utf-32-le` and `utf-32-be`
(aliases such as `UTF8` work). Encodings with a byte order mark (`utf-16`, `utf-32`,
`utf-8-sig`) are rejected because the mark would silently change the count. In UTF-16
a surrogate pair is never split.

## Knowing what happened

```python
from bytetrunc import truncate_detailed

t = truncate_detailed("héllo world", 8, suffix="...")
(t.text, t.size, t.original_size, t.truncated)  # -> ('héll...', 8, 12, True)
```

## Splitting into chunks

`chunk_bytes(s, max_bytes)` fills pieces greedily and `"".join(pieces) == s` always
holds. When one character or cluster is larger than the limit on its own, it raises
`ValueError` naming the index and size instead of emitting an oversized piece.

## Raw bytes

`cut_utf8(data, max_bytes)` works on `bytes` without decoding. With no limit it only
drops an incomplete trailing sequence, which is what you want after a fixed-size read
from a socket or file. It inspects only the cut point; validate the rest with
`data.decode("utf-8")` if you need to.

## File names

`truncate_filename(name, max_bytes=255)` keeps the last extension (`.gz` of
`archive.tar.gz`) and shortens the stem on grapheme boundaries. A leading dot is part
of the name, not an extension. It does not sanitize characters a platform forbids; it
rejects only inputs that are not a single path component.

## Command line

```
printf 'héllo world\n' | bytetrunc truncate 6
printf 'quarterly report.pdf\n' | bytetrunc truncate 12 --keep-extension
printf 'one long SMS body\n' | bytetrunc chunk 8
printf 'héllo\n' | bytetrunc count --encoding utf-16-le
```

Input and output are UTF-8; `--encoding` changes only how bytes are counted.
`truncate` and `count` work line by line (with `--keep-extension`, empty lines pass
through). `chunk` treats all of stdin as one text, so pass `-0` when it holds newlines
to keep the pieces unambiguous. Errors are printed to stderr with the failing line
number, and the exit status is 1.

## Conformance

Grapheme segmentation implements every rule of UAX #29 for Unicode 18.0.0, including
GB9c for Indic conjuncts. The property tables are generated by
`scripts/gen_ucd_tables.py` from the Unicode Character Database files. Those files are not committed:
`data/ucd/MANIFEST.json` pins their URLs, Unicode version, sizes and SHA-256 sums, and
`python scripts/fetch_upstream.py` fetches them into `data/ucd/`. With them in place the
test suite runs all 853 cases of the official `GraphemeBreakTest.txt` and checks that the
committed tables match a fresh run of the generator; without them those tests skip.
