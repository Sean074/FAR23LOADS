**Step OG-B — the app-layer shell gets one owner (`app_shell/`) (design note 32, tier L, 2026-08-19)**

**Objective.** Design note 32 adds a second Streamlit front-end over the same
analysis model. Its decision OG-4 names the prerequisite: the app-layer code both
front-ends need — project state, the unsaved-changes guard, the units toggle, the
project-file widget, the page scaffold, the unit-input boundary and the LIMIT CSV
builders — must have a single owner *before* the second GUI exists, because
skipping it is not "some duplication" but the dual-path failure the project
rejects in the calc layer, relocated to the shell.

The blocker was concrete rather than stylistic. `app/components.py` and
`app/limit_csv.py` were bare top-level modules importable only because Streamlit
puts the entry point's directory on `sys.path`, and the seven project-lifecycle
helpers were private functions of `app/Home.py` — a *script*, which calls
`st.set_page_config` at line 45, builds the sidebar at 150 and `pg.run()` at 258.
Importing it to reach `_has_unsaved_changes` would have booted the existing app.
A second GUI could therefore only have copied the dirty guard, and two answers to
"are there unsaved changes?" is exactly what `CLAUDE.md` rule 3 exists to prevent.

**Deliverables.**

- **`app_shell/`**, a new package: `components.py` (page scaffold, unit boundary,
  workflow page links, applicability banner — moved unchanged), `limit_csv.py`
  (moved unchanged), `project_state.py` (`ensure_project`, `mark_saved`,
  `has_unsaved_changes`, `adopt`, `confirm_discard`, `apply_schema_check`,
  `safe_load`, `load_with_guard` — lifted out of `Home.py`, de-underscored, with
  the module-global `project` they closed over replaced by `active_project()`),
  and `sidebar.py` (`render_shell_sidebar`, the units + project-file + About
  block, previously an inline `with st.sidebar:` in the script).
- **`app/Home.py` reduced to what is specific to this front-end**: 258 lines to
  81 — its phase labels, its `_page`/`st.navigation` construction, and one
  `st.set_page_config`. Navigation is deliberately *not* shell: this GUI shows
  every workflow step and the oracle GUI will show only the steps backed by a
  `.BAS` program (OG-2), so the two derive their page sets from the same
  `workflow.py` by different rules and a shared builder would fit neither.
- **Gate G8**, `tests/test_app_shell.py` — three assertions: no GUI package
  redefines a public shell name; the shell never imports a GUI package back
  (without which "single owner" is nominal and the second GUI inherits the
  first's pages); and the GUI set is non-empty, guarding the guard.
- **Call-site sweep**: 21 view modules and 3 test modules re-pointed from
  `from components import …` to `from app_shell.components import …`;
  `pyproject.toml` gained `app_shell*` to `packages.find`; `PROJECT_GUIDE.md` §4
  gained the package in the tree and lost the two prose claims the move
  invalidated; the lint gate gained `app_shell/` in all nine places it is
  written down.
- **Generalised on first find (rule 4)**: `conftest.py` and eight test modules
  carried `sys.path.insert(…, "app")` with comments explaining it as necessary
  "or the view fails on `import components`". That reason no longer exists, so
  the whole class went with the change rather than being left as nine copies of
  a stale rationale.

**Test.** `tests/test_app_shell.py` is the new gate; the existing suite is the
no-behaviour-change evidence — 2,167 passed, including `test_views_smoke`'s
entry-point and per-view AppTest runs, `test_app_components` (the unit-boundary
round-trip, now importing through the package), `test_dirty_flag`,
`test_limit_csv` and `test_page_links`. The entry point was additionally booted
in a fresh interpreter from an unrelated working directory, confirming the
sidebar renders both headers, the units radio, all three buttons and the dirty
flag through the extracted helpers — the check an AppTest run from inside the
repo cannot give.

**Key decisions.**

1. **`app_shell/` at the repo root, not `app/shell/`.** A subpackage would make
   the existing GUI the structural parent of its sibling, which is the asymmetry
   OG-4 exists to remove. `sloads/` was never a candidate: the pure-calc rule and
   OG-1 both forbid Streamlit imports there.
2. **A real installed package, not a directory on the implicit path.** This is
   what lets a second entry point import the shell without inheriting the first
   one's `sys.path`, and it is why the test-side path hacks could be deleted
   rather than duplicated for the new GUI. It costs one one-time
   `pip install -e '.[dev]'` for an existing checkout, and a restart of any
   already-running dev server; CI installs fresh and is unaffected.
3. **G8 derives its GUI set instead of listing it.** A hardcoded `app/` vs
   `oracle_app/` comparison would pass vacuously today and would have to be
   remembered later, at the exact moment the guard matters. Discovering
   directories by their `st.set_page_config` entry point means the second GUI
   activates the gate by existing — the same derive-don't-list rule the
   navigation guard follows.
4. **Behaviour frozen deliberately.** Widget keys, ordering and help text are
   byte-identical, so the smoke and dirty-flag suites are a real regression
   check on the move. Two improvements were noticed and *not* taken here:
   `use_container_width` is deprecated in current Streamlit, and the lint-gate
   invocation is written out in nine places. Both are their own items; folding
   either in would have made this diff unreviewable as a move.
