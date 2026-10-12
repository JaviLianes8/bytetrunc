"""Drive the command line tool in a real child process (``python -m bytetrunc``)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import bytetrunc

SRC = Path(__file__).resolve().parent.parent / "src"


def run(*args: str, stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ, PYTHONPATH=str(SRC))
    return subprocess.run(
        [sys.executable, "-m", "bytetrunc", *args],
        input=stdin,
        capture_output=True,
        env=env,
        timeout=60,
        check=False,
    )


def test_truncate_lines_keeps_line_endings() -> None:
    done = run("truncate", "6", stdin="h\u00e9llo world\r\nshort\nlast".encode())
    assert done.returncode == 0
    assert done.stdout == "h\u00e9llo\r\nshort\nlast".encode()


def test_truncate_with_suffix_grapheme_and_encoding() -> None:
    family = "\U0001f468\u200d\U0001f469\u200d\U0001f467"
    done = run("truncate", "12", "-s", "...", "--on", "grapheme", stdin=f"ab{family}\n".encode())
    assert done.stdout == b"ab...\n"
    done = run("truncate", "4", "-e", "utf-16-le", stdin=b"abcdef\n")
    assert done.stdout == b"ab\n"


def test_truncate_keep_extension() -> None:
    done = run("truncate", "12", "--keep-extension", stdin=b"quarterly report.pdf\n")
    assert done.stdout == b"quarterl.pdf\n"


def test_chunk_and_null_separator() -> None:
    assert run("chunk", "8", stdin=b"one long SMS body\n").stdout == b"one long\n SMS bod\ny\n"
    assert run("chunk", "8", "-0", stdin=b"one long SMS").stdout == b"one long\0 SMS\0"


def test_count() -> None:
    done = run("count", stdin="h\u00e9llo\n\U0001f600\n".encode())
    assert done.stdout == b"6\n4\n"
    assert run("count", "-e", "utf-16-le", stdin=b"abc\n").stdout == b"6\n"


def test_empty_input_gives_empty_output() -> None:
    for args in (("truncate", "3"), ("chunk", "3"), ("count",)):
        done = run(*args)
        assert (done.returncode, done.stdout) == (0, b"")


def test_errors_go_to_stderr_with_status_1() -> None:
    cases = [
        (("truncate", "abc"), b""),
        (("truncate", "-1"), b""),
        (("truncate", "2", "-s", "..."), b"abcdef\n"),
        (("chunk", "0"), b"abc"),
        (("chunk", "2"), "\U0001f600".encode()),
        (("count",), b"\xff\n"),
        (("truncate", "2", "-e", "latin-1"), b"abc"),
        ((), b""),
    ]
    for args, stdin in cases:
        done = run(*args, stdin=stdin)
        assert done.returncode == 1, args
        assert done.stdout == b"", args
        assert b"error" in done.stderr, args


def test_help_has_runnable_examples_and_version() -> None:
    done = run("--help")
    assert done.returncode == 0
    assert b"examples:" in done.stdout and b"bytetrunc truncate 6" in done.stdout
    for command in ("truncate", "chunk", "count"):
        assert b"example:" in run(command, "--help").stdout
    assert run("--version").stdout.strip() == f"bytetrunc {bytetrunc.__version__}".encode()


def test_help_examples_produce_what_the_docs_say() -> None:
    assert (
        run("truncate", "6", stdin="h\u00e9llo world\n".encode()).stdout == "h\u00e9llo\n".encode()
    )
    done = run("truncate", "10", "--suffix", "...", stdin=b"a long status message\n")
    assert done.stdout == b"a long ...\n"
    assert run("count", "--encoding", "utf-16-le", stdin="h\u00e9llo\n".encode()).stdout == b"10\n"
