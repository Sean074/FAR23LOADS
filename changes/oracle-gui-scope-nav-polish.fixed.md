- **The oracle GUI no longer offers a switch to concept mode, and the shared nav
  link stops swallowing real failures (review 2026-08-20 CR-A-4, CR-A-5/CR-D-10,
  CR-A-9; tier S, 2026-08-22).**
  An airplane above the FAR 23 applicability band got a **"Switch to Concept"**
  button on the oracle front-end, which carries no concept page and no concept
  field (note 32, OG-1): one click wrote `speeds.category="C"` and seeded
  `chosen_n`/`chosen_nneg` into a project only `app/` could then show. The
  applicability *warning* stays — the numbers are still an extrapolation and must
  say so — via a new `switch_action=` flag on
  `app_shell.components.render_applicability_banner` (and on `page_header`/`page`),
  which the oracle renderer passes as `False`. Pinned two ways in
  `tests/test_oracle_gui.py`: an out-of-band project renders the warning with no
  such button, and no shared-header call in `oracle_app/` may inherit the shell
  default. `tests/test_app_components.py` pins the `app/` default from the other
  side, so the flag cannot be flipped for everyone by a fix aimed at one GUI.
  Also: `workflow_page_link` narrows its `except Exception: pass` to
  `StreamlitAPIException` — the unregistered-step fallback is the `page is None`
  branch, so the broad catch only hid genuine `st.page_link` failures as silent
  text degradation, shipping a broken nav green; and `oracle_app/Oracle.py`
  resolves `oracle_steps()[0]` once for the page set instead of once per page.
