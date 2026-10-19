# bytetrunc 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to bytetrunc. PyPI has no release
(`https://pypi.org/pypi/bytetrunc/json` answered 404 on 2026-10-18), so 1.0.0 is the
first published version; every change since 0.2.1, the last version in the CHANGELOG
(unpublished), is listed in the CHANGELOG all the same.

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.2.1, ef98f2d)
- [x] Baseline gates on 0.2.1
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: Unicode files and UAX #29 fetched live, reference implementations (item 7)
- [ ] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e, every Python (items 8, 10, 13, 14)
- [ ] Gates (item 15)
- [ ] PR and trace guard CLEAN
- [ ] Five QA lenses (item 19) and independent reviewer (item 16): run by the maintainer next

## Baseline on 0.2.1 (before any change)

On this PC, CPython 3.13.2: `ruff format --check .`, `ruff check .`, `mypy --strict src tests`,
`mypy --strict src` and `python scripts/gen_ucd_tables.py --check` exit 0. Full suite on the
laptop from a fresh clone of `release/1.0.0` at ef98f2d with the Unicode files fetched
(CPython 3.14): 952 passed (the 853 official grapheme cases included), exit 0.

The four Unicode 18.0.0 files pinned in `data/ucd/MANIFEST.json` were fetched again on
2026-10-18 by `scripts/fetch_upstream.py`: sizes and SHA-256 match the manifest.
