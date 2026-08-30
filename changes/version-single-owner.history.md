- **The sloads version got a single owner (`RELEASE_PROCESS.md`, tier M,
  2026-08-30)** — Found by reading a generated report: it stated sloads 0.8.0
  while `pyproject.toml` said 0.8.1, which is the basis of the branch that built
  it. Not a display bug. `tool_version()` asked `importlib.metadata`, which reads
  `PKG-INFO` — a snapshot written at install time. The 0.8.1 bump edited
  `pyproject.toml`, nobody re-ran `pip install -e .`, and every report since had
  been stamping the previous version into its analysis basis and its
  `build.json`. A provenance field that is wrong but plausible is worse than one
  that is absent, and this one appears on a page a reader trusts.

  Fixed structurally rather than by reinstalling (CLAUDE.md rule 3: one owner
  plus a drift guard, never a prose rule). `sloads/_version.py` holds the
  literal and imports nothing; `pyproject.toml` declares `dynamic = ["version"]`
  and points `[tool.setuptools.dynamic]` at the attribute; `tool_version()`
  reads the same attribute, so it tracks an edit with no install step. The
  version lives in its own module rather than in `sloads/__init__.py` because
  setuptools falls back to *importing* the module when it cannot read the
  attribute statically, and `__init__.py` pulls in the whole package, whose
  dependencies a build environment does not have.

  Four guards in `tests/test_version_owner.py`: packaging declares the version
  dynamic and names the owner, `[project]` carries no literal of its own, the
  report stamp does not import `importlib`, and the literal stays a plain
  module-level string setuptools can parse without importing anything. The third
  is scanned as an *import* via AST rather than as text — the function's own
  docstring explains why `importlib.metadata` is not used, and a substring
  search failed on the very comment documenting the fix.
