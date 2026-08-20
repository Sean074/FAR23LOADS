- **The lint gate covers every GUI, and every statement of it must agree (design note 32 step OG-D, tier M, 2026-08-20).**
  `oracle_app/` and `oracle.py` join the ruff target list — which is written out
  in **eleven** places (CI, the pre-commit hook, `solo_close.sh`, four standard
  docs, the PR template, `CLAUDE.md`, `README.md` and the script test that pins
  it). Adding `app_shell/` meant editing nine of them by hand; this is the
  second sweep, which is where `CLAUDE.md` rule 3 says a convention stops being
  a prose rule. Two guards in `tests/test_app_shell.py` now close it:
  every **derived** GUI directory (a repo-root directory holding a
  `set_page_config` entry point — the same discovery gate G8 uses) must appear
  in CI's lint command, and every file that repeats that command must repeat it
  **exactly**, with CI as the authority. A GUI outside the lint gate is unlinted
  code behind a green badge; a document stating a different gate is a developer
  running a different one from the PR that will fail.
  Also here, because the oracle GUI's generic renderer is what needed it:
  `units` gains a `moment` input kind (lb-in → N·m, distinct from the engine
  channel's `torque` in ft-lb) for the entered unbalanced wing moment, and
  `field_registry.field_at` is split so `field_type` can resolve a path's real
  annotation rather than the string `Field.type` holds under
  `from __future__ import annotations`.
  **`oracle_app` is an installed package**, so `pip install -e '.[dev]'` must be
  re-run once after this change or the entry point cannot import its own
  renderer.
