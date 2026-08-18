- **Fixture-data pass: entered empennage planforms on the four type fixtures, the `ga6_normal` fin root pinned and its Appendix A body outline entered (issue #9, Pri 1, tier M, 2026-08-17).**
  Three fixture edits, each with its own attributable digest wave, in note 19
  §10.2's order. **(i)** `ga6_normal` enters `vtail_root_waterline_z = 78.5` —
  the value the fuselage-top fallback had been producing (wing root waterline
  + `fuselage_height 0 / 2`), now stated: zero numeric movement, only the
  `ASSUMED … fuselage-top` provenance notes on the fin cards/report become
  `entered`. **(ii)** `cessna_210`, `atr42_100`, `dhc8_dash8` and
  `concept_regional_jet` enter `htail`/`vtail` polylines — taper 0.4–0.7,
  LE sweep 6–30° (h-tail 6–28°, fins 30–35°), estimated from the type
  three-views, tied to the scalar area/span/`xt25`/`xv25` and reported with
  `elements = wing.elements // 2` (the derived rectangle's count, so the
  station set does not change shape). Every tail card, tail CSV, balance text,
  balanced deck and LRA deck on those four moves; the fin LOAD and `n_y` are
  bit-identical (see the `fixed` fragment) while `p_dot` falls 6–10 % (a
  tapered fin's load centroid sits lower, so its roll arm shrinks) and `r_dot`
  moves < 1 %. `ga6_normal` deliberately stays on the derived rectangle:
  Appendix A prints no tail chords, and an invented taper on the oracle
  fixture would be reported as entered data. Fin sweeps were capped at 30° on
  the three larger types because ≥ 35° pushes the SI (mm-frame) LRA deck over
  sbeam's dense-path 1e15 condition heuristic — the known units-artifact
  limitation the RJ's SI deck already xfails on. **(iii)** `ga6_normal` gains
  the Appendix A body outline (Ref 1 p.49 airplane data): length 26.522 ft,
  max width 3.833 ft, height 68.7 in from the printed 17.231 sq ft frontal
  area read as an ellipse (the `FuselageSection` area rule), on the suite's
  three-section pattern (max at 0.35 L; tail cone 0.10 w / 0.15 h), `z_centre`
  left unentered. It moves ga6's h-tail attachment from the innermost strip
  pair to the outline's half-width at the h-tail LRA station (±7.5 in), gives
  the wing stick deck an SOB node and the report a side-of-body table, and
  lets the LRA beam model build for the Appendix A airplane for the first
  time (`sbeam/lra_model` joins its digest set); the balance CSV and every
  Appendix A oracle are untouched. Reference: note 19 §10.2, plan 09 T-1/T-8a.
  Closes the planform and outline parts of #9; the WTENV-envelope part stays
  open with a re-stated body (see the backlog).
