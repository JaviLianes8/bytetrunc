"""Build the real wheel, install it into a throwaway venv and drive the installed script.

Nothing is mocked: this needs network access for pip to fetch the build backend.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import bytetrunc

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run(cmd, input=stdin, capture_output=True, env=env, timeout=600, check=False)


def test_wheel_installs_and_the_script_works(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(dist), str(ROOT)]
    )
    assert built.returncode == 0, built.stderr.decode(errors="replace")
    wheels = list(dist.glob("bytetrunc-*.whl"))
    assert [w.name for w in wheels] == [f"bytetrunc-{bytetrunc.__version__}-py3-none-any.whl"]
    names = zipfile.ZipFile(wheels[0]).namelist()
    assert "bytetrunc/py.typed" in names and "bytetrunc/_ucd_part1.py" in names
    assert not [n for n in names if n.startswith(("data/", "tests/", "scripts/"))]

    env_dir = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
    bindir = env_dir / ("Scripts" if os.name == "nt" else "bin")
    python = bindir / ("python.exe" if os.name == "nt" else "python")
    script = bindir / ("bytetrunc.exe" if os.name == "nt" else "bytetrunc")
    installed = _run([str(python), "-m", "pip", "install", "-q", "--no-index", str(wheels[0])])
    assert installed.returncode == 0, installed.stderr.decode(errors="replace")
    assert script.is_file()

    done = _run([str(script), "truncate", "6"], "h\u00e9llo world\n".encode())
    assert (done.returncode, done.stdout) == (0, "h\u00e9llo\n".encode())
    family = "\U0001f468\u200d\U0001f469\u200d\U0001f467"
    done = _run([str(script), "chunk", "20", "--on", "grapheme"], f"ab{family}cd".encode())
    assert done.stdout == f"ab{family}\ncd\n".encode()
    done = _run([str(script), "count"], b"abc\n")
    assert done.stdout == b"3\n"
    failed = _run([str(script), "chunk", "0"], b"abc")
    assert failed.returncode == 1 and b"error" in failed.stderr and failed.stdout == b""
    version = _run([str(script), "--version"])
    assert version.stdout.strip() == f"bytetrunc {bytetrunc.__version__}".encode()

    probe = "import bytetrunc; print(bytetrunc.UNICODE_VERSION, bytetrunc.__file__)"
    shown = _run([str(python), "-c", probe]).stdout.decode()
    assert shown.startswith("18.0.0 ") and str(env_dir) in shown
