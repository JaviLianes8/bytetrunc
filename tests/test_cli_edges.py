"""Command line edges: trailing line endings of chunk, capped usage errors, CLI wording."""

from __future__ import annotations

import pytest
from test_cli import run


@pytest.mark.parametrize(
    ("stdin", "expected"),
    [
        (b"a\n\r\n", b"a\n\x00"),
        (b"a\n\n", b"a\n\x00"),
        (b"a\r\n\n", b"a\r\n\x00"),
        (b"a\r\n", b"a\x00"),
        (b"a\n", b"a\x00"),
        (b"a", b"a\x00"),
    ],
)
def test_chunk_strips_exactly_one_trailing_line_ending(stdin: bytes, expected: bytes) -> None:
    done = run("chunk", "10", "-0", stdin=stdin)
    assert done.returncode == 0
    assert done.stdout == expected


def test_a_huge_invalid_argument_gives_a_short_usage_error() -> None:
    done = run("truncate", "5", "--on", "x" * 20_000, stdin=b"a\n")
    assert done.returncode == 2
    assert b"invalid choice" in done.stderr
    assert len(done.stderr) < 1000


def test_cli_errors_name_options_of_the_command() -> None:
    done = run("truncate", "3", "--keep-extension", stdin=b"a.txt\n")
    assert done.returncode == 1
    message = done.stderr.decode()
    assert "keep_extension=False" not in message
    assert "without --keep-extension" in message
    assert message.startswith("bytetrunc: error: line 1: extension '.txt' leaves no room")


@pytest.mark.parametrize("command", ["truncate", "chunk"])
def test_the_limit_has_the_name_its_messages_use(command: str) -> None:
    assert b"MAX_BYTES" in run(command, "--help").stdout
    done = run(command, "x")
    assert done.returncode == 2
    assert b"argument MAX_BYTES: not a non-negative integer" in done.stderr
    assert b"max_bytes must be positive" in run("chunk", "0", stdin=b"a\n").stderr
