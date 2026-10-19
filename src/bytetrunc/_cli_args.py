"""Argument parsing of the ``bytetrunc`` command."""

from __future__ import annotations

import argparse
import contextlib
import sys
from typing import TYPE_CHECKING, NoReturn

from ._encodings import ENCODINGS, normalize_encoding
from ._errors import BytetruncError, preview

if TYPE_CHECKING:
    from _typeshed import SupportsWrite

_MESSAGE = 300
EPILOG = """\
examples:
  printf 'h\\xc3\\xa9llo world\\n' | bytetrunc truncate 6
  printf 'quarterly report.pdf\\n' | bytetrunc truncate 12 --keep-extension
  printf 'a long status message\\n' | bytetrunc truncate 10 --suffix '...'
  printf 'one long SMS body\\n' | bytetrunc chunk 8
  printf 'h\\xc3\\xa9llo\\n' | bytetrunc count --encoding utf-16-le

Input is read from stdin as UTF-8 and output is written as UTF-8. --encoding only
changes how bytes are counted. truncate and count work line by line; chunk treats
all of stdin as one text, so use -0 when it holds newlines. Errors go to stderr with
exit status 2 for a wrong command line and 1 for input that cannot be handled.
"""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        if len(message) > _MESSAGE:
            message = message[:_MESSAGE] + "..."
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")

    def _print_message(self, message: str, file: SupportsWrite[str] | None = None) -> None:
        # Python 3.13 and later skip a stream that cannot be written; do the same on 3.10.
        if message:
            with contextlib.suppress(AttributeError, OSError):
                (file or sys.stderr).write(message)


def _limit(text: str) -> int:
    if not (text.isascii() and text.isdigit()):
        raise argparse.ArgumentTypeError(f"not a non-negative integer: {preview(text)}")
    digits = text.lstrip("0") or "0"
    if len(digits) > 4000:
        raise argparse.ArgumentTypeError(f"too large: an integer of {len(digits)} digits")
    return int(digits)


def _encoding(text: str) -> str:
    # The library's spellings work here too; argparse reports any other name with the choices.
    try:
        return normalize_encoding(text)
    except BytetruncError:
        return text


def _suffix(text: str) -> str:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        raise argparse.ArgumentTypeError("the suffix is not valid text") from None
    return text


def _example(command: str, text: str) -> str:
    return f"example:\n  printf '{text}\\n' | bytetrunc {command}\n"


def build_parser(version: str) -> argparse.ArgumentParser:
    """Return the argument parser for the ``bytetrunc`` command."""
    parser = _Parser(
        prog="bytetrunc",
        description="Fit text to a byte limit without splitting characters.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"bytetrunc {version}")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    common = _Parser(add_help=False)
    common.add_argument(
        "-e",
        "--encoding",
        default="utf-8",
        type=_encoding,
        choices=ENCODINGS,
        help="how bytes are counted (default utf-8); input and output stay UTF-8",
    )
    boundary = _Parser(add_help=False)
    boundary.add_argument(
        "--on",
        choices=("char", "grapheme"),
        default=None,
        help="cut on code points or whole grapheme clusters "
        "(default: char, or grapheme with --keep-extension)",
    )
    trunc = sub.add_parser(
        "truncate",
        parents=[common, boundary],
        help="cut each stdin line to MAX_BYTES bytes",
        epilog=_example("truncate 10 --suffix ...", "a long status message"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    trunc.add_argument("max_bytes", type=_limit, metavar="MAX_BYTES", help="byte limit per line")
    trunc.add_argument(
        "-s", "--suffix", type=_suffix, default="", help="appended when a line is cut"
    )
    trunc.add_argument(
        "--keep-extension",
        action="store_true",
        help="treat each line as a file name and keep its extension",
    )
    chunk = sub.add_parser(
        "chunk",
        parents=[common, boundary],
        help="split stdin into pieces of MAX_BYTES bytes",
        epilog=_example("chunk 8", "one long SMS body"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    chunk.add_argument("max_bytes", type=_limit, metavar="MAX_BYTES", help="byte limit per piece")
    chunk.add_argument(
        "-0",
        "--null",
        action="store_true",
        help="end each piece with NUL, not newline (needed when the text has newlines)",
    )
    sub.add_parser(
        "count",
        parents=[common],
        help="print the byte length of each line",
        epilog=_example("count --encoding utf-16-le", "hello"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    return parser
