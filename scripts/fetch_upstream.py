"""Fetch the third-party files listed in data/ucd/MANIFEST.json and tests/upstream/MANIFEST.json.

The files are not part of the repository. data/ucd holds the Unicode Character Database
files the table generator reads; tests/upstream holds the other sources the tests compare
against. The generator and the tests that read a file skip until this script has fetched
it; each download is checked against the size and sha256 in its manifest, and a file that
is already present and matches is kept.

    python scripts/fetch_upstream.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = (ROOT / "data" / "ucd", ROOT / "tests" / "upstream")


def _matches(body: bytes, entry: dict[str, object]) -> bool:
    return len(body) == entry["size"] and hashlib.sha256(body).hexdigest() == entry["sha256"]


def main() -> int:
    failed = 0
    for folder in FOLDERS:
        manifest = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))
        for name, entry in manifest.items():
            target = folder / name
            if target.is_file() and _matches(target.read_bytes(), entry):
                print(f"{name}: ok (present)")
                continue
            with urllib.request.urlopen(entry["url"], timeout=60) as response:
                body = response.read()
            if not _matches(body, entry):
                digest = hashlib.sha256(body).hexdigest()
                print(f"{name}: got {len(body)} bytes, sha256 {digest}; manifest differs")
                failed += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            print(f"{name}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
