- **A load and a point and a named frame: the half of LANDLOAD's printout the
  replication had never shipped (tier L, 2026-08-29)** —

  **Objective.** Close design note 38's second deliverable (GF-6/GF-7, issue
  #134): make the landing output what a stress model can consume. LANDLOAD
  prints its whole 33-case matrix **twice** — once with respect to the ground
  line, once with respect to the airplane datum, each under its own banner — and
  `run()` shipped the first set only, with no application point, no attitude and
  no frame label, while the export deck consumed the other frame. A reader
  moving between the Oracle's table and the deck had no stated bridge, and the
  two differ by a rotation of the ground angle. The item waited on two ordering
  conditions and outlived both in the same session: the `BETA` sign (#133) and
  the application point (#139), each of which would otherwise have shipped a
  number this item then had to move.

  **What was missing.** Five things, all of them printed in 1990: the
  fuselage-axis angle per case (p231's own column); the airplane-datum table
  (p232 — `vm/dm/vn/dn` were computed and never reached `ModuleResult`); the
  NR/NV/ND datum load factors (not computed at all); the frame labels (the main
  GUI said "(ground line)" in prose, the Oracle said nothing); and the point of
  application, which lived only in the gear free-body report and the deck.

  **Deliverables.** New `sloads/frames.py` — the two frames, the manual's own
  caption words (`LANDLOAD.BAS` lines 5140/5230), the report-vs-deliver rule
  (`is_report_only`) and the rotation between the frames (`rotation_deg`,
  `to_airplane_datum`, `to_ground_line`, moved down from `gear_loads` so
  `landing` can reach them). `LoadValue` gains `frame` — **schema v57 → v58**
  with an identity hop, because `LoadValue` is persisted inside
  `critical.conditions[].loads`. `gear_loads` gains `DeliveredLeg` and
  `delivered_legs` / `delivered_gear_legs`: the three wheels of a case, in report
  order, built *from* `applied_wheels` rather than beside it, with the wheels it
  drops emitted at zero and their point and node still stated. `landing.run()`
  emits, per case: the three wheels' `Fx, Fy, Fz` and `x, y, z` and node, the
  fuselage-axis angle, NR/NV/ND, and p233's datum unbalanced moments — with the
  strut state and Appendix A's point-of-load column in the condition note. The
  critical-reaction summaries render through the same builder, so a family's
  summary cannot state its case differently from the matrix row it points at.
  Both GUIs gain the datum table and caption every reactions table from
  `frames.caption`. The main GUI's landing page and the Oracle's landing block
  both say which frame each row is in, in the manual's words.

  **Two more sign errors, and the reason they could not be typed.** The datum
  drag load factor's lift term is written `+LF*SIN(GRA)` in the `.BAS` and the
  datum moment transform rotates by `+GRA` — the third and fourth instances of
  the class #133 adjudicated, in the two quantities that entry could not reach
  because neither existed in sloads. Neither is written longhand here: the lift
  is `to_airplane_datum(LF, 0, ρ)` and the moments are
  `to_airplane_datum(YAWP, ROLLP, ρ)`, rotated through the case's own **measured**
  `ρ`. The corrected value is what a rotation gives; there is no second place a
  `+` could be typed for a `−`. Approved deviation registered under #134.

  **Test.** New `tests/test_landing_deliverable.py` (18 gates, G-GF-6/G-GF-7):
  three legs on every case of every bundled example and the *right* wheels
  unloaded per family; the point is the printed column and is the axle or the
  patch and nothing between, checked against the geometry rather than against
  `gear_loads`' own construction; the three legs **sum to p232's own force
  cells** and the datum factors are that sum through the printed loops — derived
  from the page, never from the module under test; case 1 and case 16 lock at the
  ruled numbers; the datum moments preserve their magnitude and leave pitch
  invariant; the CSV/text split guarded **both ways**; the frame split owned by
  one predicate; neither GUI writing the frame words itself. Plus 72 new
  Appendix A cells in `test_landing.py::test_landload_p232_airplane_datum_load_factors`.

  **Key decisions.** *(1)* The primed set leaves the CSV, so the datum moments
  had to be built — otherwise the deliverable would carry no moment at all. That
  answers design note 38 §5.4's one open disposition, in the item that needed it.
  *(2)* Three legs always, zeros included: which gears a family lifts is a fact
  about the case, and omitting them makes the reader reconstruct the rule from
  the case number. *(3)* The deliverable is built from the deck's own wheels, not
  beside them — #139 had just shown what two constructions of the same statement
  cost. *(4)* The LANDLOAD case families moved to `modules/landing.py`, which
  draws those lines already, and `attitude_of` with them; the 23.485 pairing that
  `NS` and the deck each derived separately became one `side_partner`.

  **What the numbers said back.** Three invariants the correction did not aim at:
  the tail-down family reproduces **all three** printed p232 cells exactly, because
  the `.BAS` already carries the corrected sign there — the manual is internally
  inconsistent, and one of its attitudes is right; `NV` does not move on cases
  1–12, because a cosine is even; and `NR` stays printed to the digit on the
  wheels-only families 16–24 (1.703, 1.330), because a rotation preserves a
  resultant. A correction that broke any of the three would have been the wrong
  correction.
