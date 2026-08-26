- **The shell's unit radio beat a loaded project's own unit system, and the
  disabled wing-area copy showed a number the analysis does not use**
  (PB-16, PB-17, issue #70, tier M, 2026-08-25). `unit_system` is a field of
  `Project`, so the sidebar radio is a project-seeded widget; it was exempted
  from the project-generation stamp as "the user's choice", and its retained
  state therefore beat `index=` — opening an SI-saved file in an Imperial
  session put `imperial` back on the file and reported it *unsaved* before the
  user had touched anything. It now carries the stamp like every other widget
  seeded from the project, and the exemption list has a behavioural guard
  beneath it: loading any shipped example through the shell must leave it clean.
  Separately, `speeds.wing_area_sqft` was registered as a display-only copy of
  `geometry.parametric.wing_area_sqft` while STRSPEED integrates the
  `speeds.wing_surface` **planform** — so the disabled widget stated 500.0 where
  the answer used 497.75 on `concept_regional_jet`, and two unrelated numbers on
  a hand-typed project. The row now names the planform as its owner and the
  widget shows the resolved area, from the same function the calc calls; where
  no such surface exists the field is what STRSPEED actually reads, so it goes
  live instead of being disabled against its own error message's advice.
- **The wing planform integral had four implementations and the wing-area
  mismatch warning printed twice on one page and never on the other**
  (#70, tier M, 2026-08-25). `structural_speeds`, `landing`, `validation` and
  `derived_geometry` each performed the strip integral; the guard that was
  supposed to prevent this scanned `sloads/modules/` only and allowlisted two of
  them, so `validation.py` grew a third copy outside its view. There is now one
  owner, `derived_geometry.planform_area_sqft` — the callers keep their own
  policy for an absent planform (LGFACTOR refuses, STRSPEED falls back) and none
  of them keeps the arithmetic — and the guard covers all of `sloads/`.
  `_check_area_mismatch` returned its warning tagged for Configuration & Layout
  twice, so that page printed the same sentence twice and Design Speeds, where
  the disagreement decides which number is integrated, printed it not at all.
- **A caption quoting an owner's value quoted it in Imperial on an SI page**
  (#70, tier S, 2026-08-25). The copy marks state the governing number beside a
  widget that converts, so an SI reader was shown kilograms in the box and
  pounds in the caption. `oracle_app.form._shown` converts and labels it.
