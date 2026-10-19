"""Every python block of the README and GUIDE runs on its own, and every
``expression  # -> value`` line in it holds."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BLOCK = re.compile(r"```python\n(.*?)```", re.S)


@pytest.mark.parametrize("doc", ["README.md", "GUIDE.md"])
def test_documented_results_are_true(doc: str) -> None:
    text = (ROOT / doc).read_text(encoding="utf-8")
    checked = 0
    for block in BLOCK.findall(text):
        # A fresh namespace per block: each example must carry its own imports.
        namespace: dict[str, object] = {}
        lines: list[str] = []
        for line in block.splitlines():
            if "  # -> " in line:
                exec("\n".join(lines), namespace)
                lines = []
                code, expected = line.split("  # -> ", 1)
                assert eval(code, namespace) == ast.literal_eval(expected), line
                checked += 1
            else:
                lines.append(line)
        exec("\n".join(lines), namespace)
    assert checked >= 4
