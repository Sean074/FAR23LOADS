## Step 153 — Entered polylines are the geometry source of record (tier L, 2026-08-30)

**Objective.** Where a user enters a surface's leading- and trailing-edge definition, derive
its area, aspect ratio, MAC and quarter-MAC station from that definition; and give the GA6
example the planforms Appendix A actually prints for it.

**The finding that prompted it.** `sloads/tail_geometry.py` justified deriving a rectangular
tail planform on the grounds that "no shipped fixture carries tail polylines, and requiring
them would mean hand-entering planform data for six airplanes with no oracle to check it
against", and `tests/test_tail_geometry.py` pinned the consequence: "`ga6_normal` stays
derived on purpose: **Appendix A prints no tail chords**." Appendix A prints them. Its
contents list nine WINGGEOM runs beyond the wing and aileron already in the fixture —
vertical tail p147, vertical stabilizer p148, rudder p149, horizontal tail p151, horizontal
stabilizer p152, elevator p153, elevator fwd/aft of hinge p155/p156, elevator tab p157 —
each with its entered coordinate table and its computed properties. The fixture had kept the
outputs and dropped the inputs, while four *other* fixtures were given taper estimated from
published three-views. The one airplane with printed oracle geometry was the only one
running on an assumed rectangle.

**Deliverables.**
- `wing_geometry.planform_boundary` — the closed planform, one owner. Leading edge, tip
  chord, trailing edge, root chord; where the two edges span the same stations the closing
  chords are degenerate and it reduces to `chord = X_TE − X_LE`.
- `wing_geometry.surface_properties` — closed-form integrals in place of the strip sum.
- `examples/ga6_normal.project.json` — h-tail, v-tail, elevator, rudder and flap polylines.
- `tail_geometry._polyline_area_and_span` / `_polyline_mac_and_x25` / `TailPlanform.chord`
  — all now ask the shared owner.

**Test.** New oracle coverage on every transcribed surface against its printed AREA/SIDE,
MAC, YLE(MAC), XLE(MAC) and AR; worst 0.084 %. The v-tail, whose own table is on a leaf
missing from the bundled scan, is gated by closure against the fixture's scalars instead and
reproduces area to 0.014 % with span and aspect ratio exact.

**Key decisions.**
- **The polylines are the input; the manual's derived values are its output** (owner, in
  session). WINGGEOM's `H` is an unprinted convergence parameter, so its printed figures
  carry whichever discretisation each run used — demonstrated by the manual's own three
  elevator figures failing to sum (1181 − 1065 = 116, printed 118).
- **Span is measured across both edges**, root to tip, so a fin whose trailing edge reaches
  below its leading edge measures its full height. Every surface entered before this change
  has matching edge ranges, for which the value is unchanged.
- **The oracle chain moved and was re-pinned** rather than preserved. For the wing the
  manual used `H = 20`, and the 20-strip sum reproduces its printed MAC to 0.0006 % where
  the exact integral is 0.042 % away — so this trades fidelity to the manual's arithmetic
  for fidelity to the planform it drew. Six printed Appendix A figures move, the largest by
  0.51 %; all are registered in `02_approved_corrections.md` with the owner's approval and
  the full trail.
- **Two findings filed, not fixed** (frozen code, OR-14): **#153**, the per-row delete on
  the Geometry page removes the last row rather than the one it names — invisible until a
  fixture carried more than two surfaces, and pinned meanwhile by a strict `xfail` asserting
  the correct contract; and **#155**, the configuration module's note still says MAC/XLEMAC/AR
  come "via the WINGGEOM strip integrator", which is now the method this step removed and is
  reproduced verbatim in §2.1 of the report.

**Authority.** `sloads/modules/wing_geometry.py` is hash-frozen for milestone 0.8.2 by
design note 44 OR-13; the owner admitted this change under OR-15 in session on 2026-08-30,
and the manifest hash is updated in the same commit.
