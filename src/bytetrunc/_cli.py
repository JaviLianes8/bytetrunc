"""Command line interface: truncate, chunk and count text read from stdin."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from typing import NoReturn

from . import __version__
from ._chunk import chunk_bytes
from ._core import Boundary, byte_len, truncate_bytes
from ._encodings import ENCODINGS
from ._filename import truncate_filename

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
exit status 1.
"""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def _limit(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {text!r}") from None
    if value < 0:
        raise argparse.ArgumentTypeError(f"must not be negative: {value}")
    return value


def _example(command: str, text: str) -> str:
    return f"example:\n  printf '{text}\\n' | bytetrunc {command}\n"


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the ``bytetrunc`` command."""
    parser = _Parser(
        prog="bytetrunc",
        description="Fit text to a byte limit without splitting characters.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"bytetrunc {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    common = _Parser(add_help=False)
    common.add_argument(
        "-e",
        "--encoding",
        default="utf-8",
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
        help="cut each stdin line to N bytes",
        epilog=_example("truncate 10 --suffix ...", "a long status message"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    trunc.add_argument("max_bytes", type=_limit, metavar="N", help="byte limit per line")
    trunc.add_argument("-s", "--suffix", default="", help="appended when a line is cut")
    trunc.add_argument(
        "--keep-extension",
        action="store_true",
        help="treat each line as a file name and keep its extension",
    )
    chunk = sub.add_parser(
        "chunk",
        parents=[common, boundary],
        help="split stdin into pieces of N bytes",
        epilog=_example("chunk 8", "one long SMS body"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    chunk.add_argument("max_bytes", type=_limit, metavar="N", help="byte limit per piece")
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


def _lines(text: str) -> list[tuple[str, str]]:
    """Split ``text`` into ``(body, line ending)`` pairs on ``\\n``."""
    pairs: list[tuple[str, str]] = []
    parts = text.split("\n")
    for index, body in enumerate(parts):
        last = index == len(parts) - 1
        if last and not body:
            break
        end = "" if last else "\n"
        if body.endswith("\r"):
            body, end = body[:-1], "\r" + end
        pairs.append((body, end))
    return pairs


def _run(args: argparse.Namespace, text: str) -> str:
    on = getattr(args, "on", None)
    if args.command == "count":
        return "".join(f"{byte_len(body, args.encoding)}\n" for body, _ in _lines(text))
    if args.command == "chunk":
        body = text[:-1] if text.endswith("\n") else text
        body = body[:-1] if body.endswith("\r") else body
        pieces = chunk_bytes(body, args.max_bytes, on or "char", encoding=args.encoding)
        sep = "\0" if args.null else "\n"
        return "".join(piece + sep for piece in pieces)
    out: list[str] = []
    for number, (body, end) in enumerate(_lines(text), 1):
        try:
            out.append(_truncate_line(args, body, on) + end)
        except ValueError as exc:
            raise ValueError(f"line {number}: {exc}") from None
    return "".join(out)


def _truncate_line(args: argparse.Namespace, body: str, on: Boundary | None) -> str:
    if args.keep_extension:
        if not body:
            return body
        return truncate_filename(
            body, args.max_bytes, args.suffix, on or "grapheme", encoding=args.encoding
        )
    return truncate_bytes(body, args.max_bytes, args.suffix, on or "char", encoding=args.encoding)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line tool and return its exit status."""
    args = build_parser().parse_args(argv)
    try:
        text = sys.stdin.buffer.read().decode("utf-8")
        result = _run(args, text)
    except ValueError as exc:
        print(f"bytetrunc: error: {exc}", file=sys.stderr)
        return 1
    try:
        sys.stdout.buffer.write(result.encode("utf-8"))
        sys.stdout.buffer.flush()
    except BrokenPipeError:
        # The reader went away (for example `| head -1`); exit quietly like other filters.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    return 0
