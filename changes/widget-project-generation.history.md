- **Widget identity across a project replacement — the project generation
  (#51, the data-loss half of parked L-8d, tier M, 2026-08-21)** — the 0.7.0
  band's Pri 1, and a defect in shipped content rather than a UX nit: a project
  loaded into either GUI did not reach the widgets of a page that was already
  open, and those widgets then wrote their stale values back over it. The cause
  is one property of Streamlit plus one of both front-ends: widget state, once
  registered under a key, wins over the `value=` argument on every later rerun,
  and every project-editing widget was keyed by something stable across
  projects (a registry path in `oracle_app/form.py`, a hand-written name in
  `app/views/`), while `adopt()` swapped `st.session_state["project"]` and
  touched no key at all. Measured on the oracle GUI: seed project → visit
  Weight & Mass Properties → load `atr42_100` rendered zeros, and because
  `render_scalar`/`render_table` persist what they return, the render wrote
  them back — the table's row-count widget held `0`, so all 21 `weight.items`
  and all 8 `weight.cg_cases` were popped out of the loaded project, with a
  Save from that state putting the emptied project on disk. Parked L-8d rested
  its "not a data-loss bug" on `app/views/` having an Apply step; the oracle
  GUI has none, and the sweep established that the Apply step only defers the
  overwrite to the click the user believes is confirming what they were shown.
  The fix is a single stamp on the widget key: `app_shell/widget_keys.py` owns
  a *project generation* counter, `widget_key(base)` prefixes it (idempotently,
  so a view may stamp a key it also hands to the shell's
  `unit_number_input`), and the counter is bumped by the two places that mean
  "the project was replaced" — `project_state.adopt` and the JSON editor's
  Apply, which replaces without saving and therefore bumps the generation
  without touching the dirty baseline. A replaced project therefore renders
  into *different widgets*, which is the only thing that beats retained state;
  the alternative — clearing widget state on adopt — needs a key list the shell
  would have to keep in step with the field registry and 21 view modules.
  Swept across both GUIs (practice 4): the oracle form's eight key sites, the
  shell's unit boundary (which stamps for all its callers), and 78 direct
  widget calls across 13 `app/views/` modules. Guards in
  `tests/test_widget_freshness.py` (new): render → load → re-render leaves the
  session project equal to the loaded file for every oracle page on every
  shipped example (66 of these fail without the stamp), the same for three
  `app/views/` page shapes, a display-half assertion on the page the defect was
  found on, and an AST walk over `app/`, `app_shell/` and `oracle_app/` that
  fails on any input widget keyed without the stamp — so the next widget added
  is fresh by construction rather than by review. The three test modules that
  had each grown a private "find the widget for this path" lookup now share
  `helpers.widget_editing`, which matches on what the widget edits and lets the
  shell decorate the key as it likes. `GUI_design.md` §5 states the rule.
