# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
python scripts/fetch_upstream.py
```

The fetch step is optional: it downloads the Unicode data files listed in
`data/ucd/MANIFEST.json` (checked against their sha256) into `data/ucd/`, which
git ignores. The generator check and the tests that need them skip until they are there.

## Before you open a pull request

- Keep public API in `src/bytetrunc/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Unit tests are deterministic and offline;
  `tests/test_e2e_wheel.py` builds and installs the real wheel, so it needs network
  access for the build backend.
- The Unicode tables in `src/bytetrunc/_ucd_*.py` are generated. To move to a new
  Unicode version, update the URLs, sizes and checksums in `data/ucd/MANIFEST.json`, run
  `python scripts/fetch_upstream.py` and then `python scripts/gen_ucd_tables.py`.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
