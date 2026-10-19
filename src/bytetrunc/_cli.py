"""Command line interface: truncate, chunk and count text read from stdin."""

from __future__ import annotations

import argparse
import contextlib
import errno
import os
import sys
from collections.abc import Sequence

from . import __version__
from ._chunk import chunk_bytes
from ._cli_args import build_parser
from ._core import Boundary, byte_len, truncate_bytes
from ._filename import NO_ROOM_HINT, truncate_filename

CLI_HINT = "run without --keep-extension to cut it as plain text"


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


def _truncate_line(args: argparse.Namespace, body: str, on: Boundary | None) -> str:
    if args.keep_extension:
        if not body:
            return body
        return truncate_filename(
            body, args.max_bytes, suffix=args.suffix, on=on or "grapheme", encoding=args.encoding
        )
    return truncate_bytes(
        body, args.max_bytes, suffix=args.suffix, on=on or "char", encoding=args.encoding
    )


def run(args: argparse.Namespace, text: str) -> str:
    """Return the output of the parsed command for the input ``text``."""
    on = getattr(args, "on", None)
    if args.command == "count":
        return "".join(f"{byte_len(body, args.encoding)}\n" for body, _ in _lines(text))
    if args.command == "chunk":
        for ending in ("\r\n", "\n"):
            if text.endswith(ending):
                text = text[: -len(ending)]
                break
        pieces = chunk_bytes(text, args.max_bytes, on=on or "char", encoding=args.encoding)
        sep = "\0" if args.null else "\n"
        return "".join(piece + sep for piece in pieces)
    out: list[str] = []
    for number, (body, end) in enumerate(_lines(text), 1):
        try:
            out.append(_truncate_line(args, body, on) + end)
        except ValueError as exc:
            message = str(exc)
            if message.endswith(NO_ROOM_HINT):
                message = message[: -len(NO_ROOM_HINT)] + CLI_HINT
            raise ValueError(f"line {number}: {message}") from None
    return "".join(out)


def _read_stdin() -> bytes:
    stream = sys.stdin
    if stream is None:
        return b""
    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        return str(stream.read()).encode("utf-8")
    return bytes(buffer.read())


def _write_stdout(data: bytes) -> None:
    stream = sys.stdout
    if stream is None:
        raise BrokenPipeError(errno.EPIPE, "no standard output")
    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        stream.write(data.decode("utf-8"))
    else:
        buffer.write(data)
    stream.flush()


def _silence_stdout() -> None:
    # Python flushes stdout again at exit; point it at devnull so that flush cannot fail.
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except (AttributeError, OSError, ValueError):
        pass


def _fail(message: str) -> int:
    with contextlib.suppress(AttributeError, OSError, ValueError):
        print(f"bytetrunc: error: {message}", file=sys.stderr)
    return 1


def _parse(argv: Sequence[str] | None) -> argparse.Namespace | int:
    try:
        return build_parser(__version__).parse_args(argv)
    except SystemExit as stop:
        if stop.code not in (None, 0):
            return stop.code if isinstance(stop.code, int) else 2
    # --help or --version: report output that could not be delivered.
    try:
        if sys.stdout is not None:
            sys.stdout.flush()
    except (OSError, ValueError):
        _silence_stdout()
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line tool and return its exit status.

    0 on success, 1 when the input cannot be handled or the output cannot be written
    (for example when the reader of a pipe goes away), 2 for a wrong command line.
    """
    args = _parse(argv)
    if isinstance(args, int):
        return args
    try:
        text = _read_stdin().decode("utf-8")
    except UnicodeDecodeError as exc:
        return _fail(f"stdin is not valid UTF-8 (byte {exc.start} cannot be decoded)")
    except (OSError, ValueError) as exc:
        return _fail(f"cannot read stdin: {type(exc).__name__}")
    try:
        result = run(args, text)
    except ValueError as exc:
        return _fail(str(exc))
    try:
        _write_stdout(result.encode("utf-8"))
    except (OSError, ValueError) as exc:
        _silence_stdout()
        if isinstance(exc, BrokenPipeError) or getattr(exc, "errno", None) == errno.EINVAL:
            return 1
        return _fail(f"cannot write the output: {type(exc).__name__}")
    return 0
