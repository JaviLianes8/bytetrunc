# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Before you open a pull request

- Keep public API in `src/bytetrunc/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Unit tests are deterministic and offline;
  `tests/test_e2e_wheel.py` builds and installs the real wheel, so it needs network
  access for the build backend.
- The Unicode tables in `src/bytetrunc/_ucd_*.py` are generated. To move to a new
  Unicode version, replace the files in `data/ucd/` (record URLs, date and checksums in
  `data/ucd/SOURCES.txt`) and run `python scripts/gen_ucd_tables.py`.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
