- **Where the load acts: the printed column the OCR lost, and a gate that was
  correcting the code instead of testing it (tier L, 2026-08-29)** —

  **Objective.** Give the landing deliverable a point of application that is the
  manual's, opening issue #134 (design note 38 GF-6, "a load and its point are
  one statement"). The first check made before emitting anything was whether the
  point about to be emitted was the point the deck already transferred from. It
  was not, on twelve of the 33 cases, and the item stopped there: a defect with
  first-order effect on shipped content outranks the fidelity item that exposes
  it (`CLAUDE.md` rule 6), so #139 was filed, design note 39 written and agreed,
  and #134 re-ordered behind it — the same sequence #133 forced a day earlier,
  for the same reason.

  **What was wrong.** `gear_loads` transferred every case from the tyre contact
  patch. Appendix A applies cases 1–12 at the **axle** ("CENTER OF EACH WHEEL")
  and 13–24 at the **ground contact point**, with 25/26, 28/29, 31/32 at "CL
  AXLE" and 27, 30, 33 at "GROUND" — a column in the p231/p232/p233 headers that
  had been unreadable in the scan since 2026-08-15 and was recovered at 200 dpi
  on 2026-08-29. The consequence is a spurious `r × F` pitching moment on every
  balanced landing case, absorbed into the solved `q̈` and shipped in the deck's
  `MOMENT` cards. The split is not editorial: level-landing drag is a **spin-up**
  load, whose reaction reaches the leg through the bearing at the axle, while
  braking torque is internal to the wheel/leg free body and leaves the patch
  force where it acts.

  **The evidence, and why it counts.** LANDLOAD prints its own unbalanced
  pitching moment `PITCHP`; the assembled case reports a pre-closure residual;
  the two are the same quantity up to G-7a's distributed lift, which the manual
  nets at the CG. Nothing in `residual My − G-7a lift == PITCHP` is derived from
  the application point, so it adjudicates it — and it reproduces the printed
  column on all six fixtures with gear, closing to ≤62 lb-in at the column's
  point against 20,964–665,862 lb-in at the other one, splitting exactly at the
  column's own family boundary. On ga6's LG-01/02/03 `PITCHP` is exactly zero, so
  the entire patch residual was invented; at the axle what remains is the lift
  moment the suite knowingly adds, to 0.1 / −1.8 / −0.5 lb-in.

  **Deliverables.** `application_point` / `application_point_of` (`AXLE` /
  `GROUND_CONTACT`) own the point; `GearLegLoad.point` and `AppliedWheel.point`
  carry it beside `patch`, which stays reported because a gear analysis starts
  there (AP-3); `transfer_couple` takes it. No reaction changes — the forces are
  LANDLOAD's own — so every Appendix A oracle and printed-cell lock passes
  unmodified, which is itself the acceptance criterion G-AP-5 states. `LG-04`'s
  pre-closure `My` moves −179,232 → −158,271 lb-in, `q̈` −1.925e-2 → −1.701e-2;
  the frozen Imperial digest, `balanced_cases.md` §9.5, `CONVENTIONS.md` §1/§7,
  `PROGRAM_SPEC.md` and `theory_sources.md` move with them. The sbeam roundtrip
  stayed green, as note 39's OQ-A2 predicted and did not assume.

  **Test.** **G-AP-1** — the identity on every balanced ground case of every
  bundled fixture at `1e-4 · n·W·MAC` (worst measured 2.65e-5, baron_58 LG-17).
  **G-AP-2** — the point against a case-by-case *transcription* of the printed
  column, never against the rule the code applies, since two copies of one rule
  cannot disagree. **G-AP-3** — a structural guard that the package builds an
  application point in exactly one place. The two existing negative controls were
  re-anchored to `point`: one of them, the static-axle control, had read `patch`
  and would have silently lost the ability to fire.

  **Key decisions.** AP-1 the printed column, as physics and not as a label; AP-2
  one owner for the point; AP-3 the patch stays reported; AP-4 no reaction moves,
  which keeps the whole oracle surface outside the change; AP-5 ship the gate
  that found it rather than a widened tolerance; AP-6 tier L, ahead of #134.

  **The lesson, which is about a test and not about the code.** The rotational
  gate had been moving the applied load from the tyre to the axle *inside the
  test* since 2026-08-15, on exactly cases 1–12, with a comment recording that
  getting it wrong "is not subtle: the level family misses by 12 % (21,000 lb-in
  on ga6_normal case 4)". The number was right, measured, and written down; it
  was read as bookkeeping between two conventions rather than as a defect,
  because the point the code used had no independent statement to be wrong
  against until the column was recovered. A gate that corrects the code before
  comparing is not testing the code — it is agreeing with it. The correction now
  lives at the origin and the gate makes none of its own, which also let the
  braked-roll pitch line drop the 5 % slack it had carried for #133: **every
  family closes on one bound.** Design note 38 §1.7 had audited this chain
  end-to-end and passed it, checking that the transfer was consistent — which is
  precisely what a wrong point preserves. Its verdict is overturned in place.

  **A duplicate removed on the way through** (rule 4): `transfer_couple` was
  implemented twice, identically, in `gear_loads` and in `export/coordinates`,
  each docstring claiming to be note 24 R-11's single owner. Consolidated onto
  the calc layer, since the export side can import it and not the reverse, with
  the name re-exported so no export call site moved.
