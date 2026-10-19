"""Build the wheel and sdist, install the wheel in a throwaway venv and use it from outside.

Nothing is mocked. It needs network access for the build backend and for pytest in the
new venv, so it runs only with BYTETRUNC_E2E=1.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

import bytetrunc

ROOT = Path(__file__).resolve().parent.parent
VERSION = bytetrunc.__version__
INFO = f"bytetrunc-{VERSION}.dist-info/"

pytestmark = pytest.mark.skipif(
    os.environ.get("BYTETRUNC_E2E") != "1", reason="set BYTETRUNC_E2E=1 to build and install"
)

PROGRAM = r"""
import importlib.metadata, importlib.resources, pickle, sys
import bytetrunc
from bytetrunc import *

assert "site-packages" in bytetrunc.__file__, bytetrunc.__file__
assert bytetrunc.__version__ == importlib.metadata.version("bytetrunc") == sys.argv[1]
assert importlib.resources.files("bytetrunc").joinpath("py.typed").is_file()
assert sorted(bytetrunc.__all__) == sorted(n for n in dir(bytetrunc) if not n.startswith("_"))
assert UNICODE_VERSION == "18.0.0" and ENCODINGS[0] == "utf-8"
assert truncate_bytes("h\xe9llo world", 8, suffix="...") == "h\xe9ll..."
conjunct = "\N{DEVANAGARI SIGN VIRAMA}\N{DEVANAGARI LETTER KA}"
assert truncate_bytes(conjunct + "!", 6, on="grapheme") == conjunct
result = truncate_detailed("abcdef", 4, encoding="UTF-16LE")
assert result == Truncation("ab", 4, 12, 4, "utf-16-le", True), result
assert pickle.loads(pickle.dumps(result)) == result
assert truncate_utf16("ab\U0001f600", 3) == "ab" and utf16_len("\U0001f600") == 2
assert chunk_bytes("h\xe9llo w\xf6rld", 5) == ["h\xe9ll", "o w\xf6", "rld"]
assert cut_utf8(b"abc\xe2\x82") == b"abc" and byte_len("h\xe9llo") == 6
assert truncate_filename("quarterly report.pdf", 12) == "quarterl.pdf"
assert [len(g) for g in iter_graphemes("e\N{COMBINING ACUTE ACCENT}\U0001f1ea\U0001f1f8")] == [2, 2]
try:
    truncate_bytes("abc", 2, suffix="...")
except BytetruncError as error:
    assert isinstance(error, ValueError) and type(error).__module__ == "bytetrunc"
    assert pickle.loads(pickle.dumps(error)).args == error.args
else:
    raise AssertionError("an oversized suffix was accepted")
print("e2e ok")
"""
CONSUMER = """
from collections.abc import Iterator
from bytetrunc import (
    Boundary, Encoding, Truncation, byte_len, chunk_bytes, cut_utf8, iter_graphemes,
    truncate_bytes, truncate_detailed, truncate_filename, truncate_utf16, utf16_len,
)

on: Boundary = "grapheme"
encoding: Encoding = "utf-16-le"
text: str = truncate_bytes("abc", 2, suffix="", on=on, encoding=encoding)
detail: Truncation = truncate_detailed("abc", 2)
counts: tuple[int, int, bool] = (detail.size, detail.limit, detail.truncated)
used: Encoding = detail.encoding
pieces: list[str] = chunk_bytes("abc", 2, on="char")
raw: bytes = cut_utf8(memoryview(b"abc"), None)
clusters: Iterator[str] = iter_graphemes("abc")
sizes: list[int] = [byte_len("a", "utf-8"), utf16_len("a")]
names: list[str] = [truncate_filename("a.txt", keep_extension=False), truncate_utf16("a", 1)]
"""
FAMILY = "\U0001f468\N{ZERO WIDTH JOINER}\U0001f469\N{ZERO WIDTH JOINER}\U0001f467"


def _run(
    *cmd: object, cwd: Path | None = None, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "BYTETRUNC_E2E")}
    args = [str(c) for c in cmd]
    return subprocess.run(args, cwd=cwd, input=stdin, capture_output=True, env=env, timeout=900)


@pytest.fixture(scope="module")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("dist")
    built = _run(sys.executable, "-m", "build", "--outdir", out, ROOT)
    assert built.returncode == 0, built.stderr.decode(errors="replace")
    return out


@pytest.fixture(scope="module")
def installed(dist: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    folder = tmp_path_factory.mktemp("venv")
    venv.EnvBuilder(with_pip=True, clear=True).create(folder)
    python = folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    (wheel,) = dist.glob("bytetrunc-*.whl")
    done = _run(python, "-m", "pip", "install", "-q", wheel, "pytest", "pytest-timeout")
    assert done.returncode == 0, done.stderr.decode(errors="replace")
    return python


def test_wheel_and_sdist_hold_exactly_what_they_should(dist: Path) -> None:
    (wheel,) = dist.glob("bytetrunc-*.whl")
    assert wheel.name == f"bytetrunc-{VERSION}-py3-none-any.whl"
    names = zipfile.ZipFile(wheel).namelist()
    sources = (ROOT / "src" / "bytetrunc").iterdir()
    expected = sorted(f"bytetrunc/{p.name}" for p in sources if p.suffix in (".py", ".typed"))
    assert sorted(n for n in names if not n.startswith(INFO)) == expected
    assert {f"{INFO}licenses/LICENSE", f"{INFO}licenses/LICENSE-UNICODE"} <= set(names)
    metadata = zipfile.ZipFile(wheel).read(f"{INFO}METADATA").decode()
    assert "Classifier: Development Status :: 5 - Production/Stable" in metadata
    requires = [line for line in metadata.splitlines() if line.startswith("Requires-Dist:")]
    assert requires and all(line.replace('"', "'").endswith("extra == 'dev'") for line in requires)
    (sdist,) = dist.glob("bytetrunc-*.tar.gz")
    with tarfile.open(sdist) as archive:
        listed = [n.split("/", 1)[1] for n in archive.getnames() if "/" in n]
    present = ["README.md", "LICENSE", "LICENSE-UNICODE", "GUIDE.md", "CHANGELOG.md"]
    present += ["tests/upstream/MANIFEST.json", "data/ucd/MANIFEST.json", "src/bytetrunc/py.typed"]
    assert [name for name in present if name not in listed] == []
    junk = [n for n in listed if "__pycache__" in n or n.endswith((".txt", ".html", ".pyc"))]
    assert junk == []
    absent = ["CERT-1.0-REPORT.md", "IMPROVEMENTS-round.md", ".github", "requirements-dev.txt"]
    assert [name for name in absent if any(n.startswith(name) for n in listed)] == []


def test_installed_package_works_from_an_empty_folder(installed: Path, tmp_path: Path) -> None:
    done = _run(installed, "-I", "-c", PROGRAM, VERSION, cwd=tmp_path)
    assert done.returncode == 0, done.stderr.decode(errors="replace")
    assert done.stdout.decode().strip() == "e2e ok"


def test_installed_command_and_module_drive_the_cli(installed: Path, tmp_path: Path) -> None:
    script = installed.parent / ("bytetrunc.exe" if os.name == "nt" else "bytetrunc")
    for program in ([script], [installed, "-I", "-m", "bytetrunc"]):
        hello = "h\N{LATIN SMALL LETTER E WITH ACUTE}llo"
        done = _run(*program, "truncate", "6", cwd=tmp_path, stdin=f"{hello} world\n".encode())
        assert (done.returncode, done.stdout) == (0, f"{hello}\n".encode())
        text = f"ab{FAMILY}cd".encode()
        done = _run(*program, "chunk", "20", "--on", "grapheme", cwd=tmp_path, stdin=text)
        assert done.stdout == f"ab{FAMILY}\ncd\n".encode()
        assert _run(*program, "count", "-e", "utf8", cwd=tmp_path, stdin=b"abc\n").stdout == b"3\n"
        failed = _run(*program, "chunk", "0", cwd=tmp_path, stdin=b"abc")
        assert (failed.returncode, failed.stdout) == (1, b"") and b"positive" in failed.stderr
        usage = _run(*program, "truncate", "x", cwd=tmp_path)
        assert (usage.returncode, usage.stdout) == (2, b"")
        version = _run(*program, "--version", cwd=tmp_path)
        assert version.stdout.strip() == f"bytetrunc {VERSION}".encode()


def test_a_strict_consumer_type_checks_against_the_wheel(installed: Path, tmp_path: Path) -> None:
    pytest.importorskip("mypy")
    (tmp_path / "consumer.py").write_text(CONSUMER, encoding="utf-8")
    positional = 'from bytetrunc import truncate_bytes\ntruncate_bytes("abc", 2, "...")\n'
    (tmp_path / "positional.py").write_text(positional, encoding="utf-8")
    mypy = [sys.executable, "-m", "mypy", "--strict", "--no-incremental", "--python-executable"]
    done = _run(*mypy, installed, "consumer.py", cwd=tmp_path)
    assert done.returncode == 0, done.stdout.decode(errors="replace")
    done = _run(*mypy, installed, "positional.py", cwd=tmp_path)
    assert done.returncode == 1 and b"Too many positional arguments" in done.stdout


def test_the_sdist_suite_passes_against_the_installed_wheel(
    dist: Path, installed: Path, tmp_path: Path
) -> None:
    (sdist,) = dist.glob("bytetrunc-*.tar.gz")
    with tarfile.open(sdist) as archive:
        archive.extractall(tmp_path, filter="data")
    tree = tmp_path / f"bytetrunc-{VERSION}"
    shutil.rmtree(tree / "src")  # the tests must import the installed wheel
    done = _run(
        installed, "-m", "pytest", "-p", "no:cacheprovider", "--basetemp", tmp_path / "t", cwd=tree
    )
    assert done.returncode == 0, done.stdout.decode(errors="replace")[-3000:]
