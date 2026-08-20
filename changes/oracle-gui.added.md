- **The oracle GUI: a second front-end over the one analysis model (design note 32 step OG-D, tier M, 2026-08-20).**
  `streamlit run oracle_app/Oracle.py`, or the new `sloads-oracle` console
  script, opens a Streamlit app that exposes **only** what the original McMaster
  FAR 23 LOADS suite asked for: **230 input fields across 14 pages**, against the
  323 the full app carries. It is not a mode of `app/` — the two are peer
  front-ends over the same `sloads` calc package, sharing the project, the dirty
  guard, the units toggle and the unit-input boundary through `app_shell/` and
  nothing else. A project moves between them in both directions unchanged; this
  one asks for less, it stores nothing different.
  **Fourteen pages, one renderer, no page files.** `oracle_app/form.py` builds
  any page from `sloads.field_registry`: the page *is* the registry rows whose
  editing page is that step and whose path is in the oracle input set, and each
  widget's shape comes from the resolved annotation (`field_registry.field_type`,
  new), its unit from `units.field_unit` (new) through the shell's
  `unit_number_input`, and its help from the row's `basis` — so every field in
  this GUI can name the `.BAS` program that asked for it. Numbers, text,
  checkboxes, enum selects, `(X, Z)` gear points, `(X, Y, Z)` vectors, the
  five-term aero polynomials, the WINGGEOM planform polylines, spanwise curves
  and the mass-item tables are all derived rather than hand-written; the one
  hand-declared thing is the member labels for composite fields (an `XYPoint` is
  (X, Z) on a gear leg and (X, Y) on a planform, and no type can say which),
  which a guard requires for every composite in the input set.
  Navigation comes from `workflow.oracle_steps()` and the pages are callables
  rather than `views/<key>.py` files, so gate **G2** holds literally: adding a
  `bas` to a workflow step adds a page with no edit to the GUI at all. `Tail
  Loads` correctly has no input of its own and says so — TAILDIST/BALLOADS read
  entirely upstream.
