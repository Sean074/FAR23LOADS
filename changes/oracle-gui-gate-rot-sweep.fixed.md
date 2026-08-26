- **Four oracle-GUI acceptance gates were asserting less than they read as
  (PB-10 … PB-13, issue #67, tier S, 2026-08-25).** G2 checked that the
  navigation *expression* mentions `oracle_steps()` by walking the source, which
  stays true of a page set that has been filtered or re-ordered; it now runs the
  entry point and asserts the page set actually registered
  (`app_shell.nav.PAGES`) is `oracle_steps()`, in order, with one default, the
  source scan kept as a drift hint. G8/OG-10, the lint gate and the shell
  back-import test all scoped themselves to "directories holding a module-level
  `set_page_config`", so wrapping `Oracle.py`'s call in a helper would have
  removed `oracle_app/` from all four at once with CI green — discovery is now
  by directory, pinned against a literal `{app, oracle_app}`. The Imperial→SI
  factor scan was two hand-typed literal lists (eight numbers in
  `test_oracle_gui.py`, five others in `test_units.py`, neither reading
  `app_shell/` or `oracle_app/`), replaced by one scan derived from `units.py`'s
  own constants and matched numerically against the float literals of all four
  packages; `test_constants.py`'s package list was swept the same way (rule 4).
  G7 ran on one airplane in one unit system, where `one_engine_out` is blocked
  and `body_loads` has no conditions — two pages asserted over an empty artifact
  list, and the SI conversion never applied; it now runs over a single **and** a
  twin, one unit system each, with a guard that every page running a program
  offers a file on at least one of them. Each strengthened gate was
  mutation-tested. Also corrected: G7's text half claimed byte equality with
  `cli.py` for every module, which is untrue of `engine` (the CLI prints
  `text_report` — the same body under an engine/propeller identification
  header); the gate pins the shared body of the two owners instead.
