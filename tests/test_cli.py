"""Drive the command line tool in a real child process (``python -m bytetrunc``)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

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
    done = run(
        "truncate",
        "6",
        stdin="h\N{LATIN SMALL LETTER E WITH ACUTE}llo world\r\nshort\nlast".encode(),
    )
    assert done.returncode == 0
    assert done.stdout == "h\N{LATIN SMALL LETTER E WITH ACUTE}llo\r\nshort\nlast".encode()


def test_truncate_with_suffix_grapheme_and_encoding() -> None:
    family = "\U0001f468\N{ZERO WIDTH JOINER}\U0001f469\N{ZERO WIDTH JOINER}\U0001f467"
    done = run("truncate", "12", "-s", "...", "--on", "grapheme", stdin=f"ab{family}\n".encode())
    assert done.stdout == b"ab...\n"
    done = run("truncate", "4", "-e", "utf-16-le", stdin=b"abcdef\n")
    assert done.stdout == b"ab\n"


def test_encoding_accepts_the_same_spellings_as_the_library() -> None:
    assert run("count", "-e", "UTF_16LE", stdin=b"abc\n").stdout == b"6\n"
    assert run("count", "--encoding", "utf8", stdin=b"abc\n").stdout == b"3\n"


def test_truncate_keep_extension() -> None:
    done = run("truncate", "12", "--keep-extension", stdin=b"quarterly report.pdf\n")
    assert done.stdout == b"quarterl.pdf\n"
    family = "\U0001f468\N{ZERO WIDTH JOINER}\U0001f469\N{ZERO WIDTH JOINER}\U0001f467"
    # With --keep-extension the default boundary is a grapheme cluster.
    done = run("truncate", "12", "--keep-extension", stdin=f"a{family}.png\n".encode())
    assert done.stdout == b"a.png\n"
    done = run(
        "truncate", "12", "--keep-extension", "--on", "char", stdin=f"a{family}.png\n".encode()
    )
    assert done.stdout == "a\U0001f468\N{ZERO WIDTH JOINER}.png\n".encode()


def test_chunk_and_null_separator() -> None:
    assert run("chunk", "8", stdin=b"one long SMS body\n").stdout == b"one long\n SMS bod\ny\n"
    assert run("chunk", "8", "-0", stdin=b"one long SMS").stdout == b"one long\0 SMS\0"
    # One final line ending is not part of the text; any other newline is.
    assert run("chunk", "3", "-0", stdin=b"ab\ncd\r\n").stdout == b"ab\n\0cd\0"


def test_count() -> None:
    done = run("count", stdin="h\N{LATIN SMALL LETTER E WITH ACUTE}llo\n\U0001f600\r\n\n".encode())
    assert done.stdout == b"6\n4\n0\n"
    assert run("count", "-e", "utf-16-le", stdin=b"abc\n").stdout == b"6\n"


def test_empty_input_gives_empty_output() -> None:
    for args in (("truncate", "3"), ("chunk", "3"), ("count",)):
        done = run(*args)
        assert (done.returncode, done.stdout, done.stderr) == (0, b"", b"")


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("truncate",),
        ("truncate", "abc"),
        ("truncate", "-1"),
        ("truncate", "+3"),
        ("truncate", "\N{ARABIC-INDIC DIGIT THREE}"),
        ("truncate", "9" * 5000),
        ("truncate", "2", "-e", "latin-1"),
        ("truncate", "2", "--on", "word"),
        ("chunk", "-1"),
        ("count", "5"),
        ("frobnicate",),
    ],
)
def test_a_wrong_command_line_exits_2_with_a_short_message(args: tuple[str, ...]) -> None:
    done = run(*args, stdin=b"abc\n")
    assert (done.returncode, done.stdout) == (2, b"")
    assert b"error" in done.stderr and len(done.stderr) < 2000


@pytest.mark.parametrize(
    ("args", "stdin", "message"),
    [
        (("truncate", "2", "-s", "..."), b"abcdef\n", b"line 1: suffix needs 3 bytes"),
        (("chunk", "0"), b"abc", b"max_bytes must be positive"),
        (("chunk", "2"), "\U0001f600".encode(), b"character at index 0 needs 4 bytes"),
        (("count",), b"ok\n\xff\n", b"stdin is not valid UTF-8 (byte 3 cannot be decoded)"),
        (("truncate", "1", "--keep-extension"), b"a\n.hidden\n", b"line 2: no usable file name"),
    ],
)
def test_input_that_cannot_be_handled_exits_1(
    args: tuple[str, ...], stdin: bytes, message: bytes
) -> None:
    done = run(*args, stdin=stdin)
    assert (done.returncode, done.stdout) == (1, b"")
    assert done.stderr.startswith(b"bytetrunc: error: ") and message in done.stderr


def test_huge_input_in_an_error_is_not_echoed() -> None:
    done = run("truncate", "9", "--keep-extension", stdin=b"a/" + b"x" * 100_000 + b"\n")
    assert done.returncode == 1 and b"not a single file name component" in done.stderr
    assert len(done.stderr) < 300


def test_help_has_runnable_examples_and_version() -> None:
    done = run("--help")
    assert done.returncode == 0
    assert b"examples:" in done.stdout and b"bytetrunc truncate 6" in done.stdout
    for command in ("truncate", "chunk", "count"):
        assert b"example:" in run(command, "--help").stdout
    assert run("--version").stdout.strip() == f"bytetrunc {bytetrunc.__version__}".encode()


def test_help_examples_produce_what_the_docs_say() -> None:
    assert (
        run(
            "truncate", "6", stdin="h\N{LATIN SMALL LETTER E WITH ACUTE}llo world\n".encode()
        ).stdout
        == "h\N{LATIN SMALL LETTER E WITH ACUTE}llo\n".encode()
    )
    done = run("truncate", "10", "--suffix", "...", stdin=b"a long status message\n")
    assert done.stdout == b"a long ...\n"
    assert (
        run(
            "count",
            "--encoding",
            "utf-16-le",
            stdin="h\N{LATIN SMALL LETTER E WITH ACUTE}llo\n".encode(),
        ).stdout
        == b"10\n"
    )
    done = run("truncate", "12", "--keep-extension", stdin=b"quarterly report.pdf\n")
    assert done.stdout == b"quarterl.pdf\n"


def test_keep_extension_passes_empty_lines() -> None:
    done = run("truncate", "6", "--keep-extension", stdin=b"a.txt\n\nlonger.txt\n")
    assert (done.returncode, done.stdout) == (0, b"a.txt\n\nlo.txt\n")


def test_every_option_has_help() -> None:
    for command in ("truncate", "chunk", "count"):
        text = " ".join(run(command, "--help").stdout.decode().split())
        assert "how bytes are counted" in text
    assert "byte limit per line" in run("truncate", "--help").stdout.decode()
    chunk_help = " ".join(run("chunk", "--help").stdout.decode().split())
    assert "needed when the text has newlines" in chunk_help


def test_a_reader_that_goes_away_ends_the_program_quietly() -> None:
    env = dict(os.environ, PYTHONPATH=str(SRC))
    with subprocess.Popen(
        [sys.executable, "-m", "bytetrunc", "chunk", "1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    ) as child:
        assert child.stdin is not None and child.stdout is not None and child.stderr is not None
        child.stdin.write(b"a" * 1_000_000)
        child.stdin.close()
        assert child.stdout.read(10) == b"a\n" * 5
        child.stdout.close()
        status = child.wait(timeout=60)
        assert (status, child.stderr.read()) == (1, b"")
