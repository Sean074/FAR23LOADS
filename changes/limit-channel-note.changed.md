- **Design note 48 records the LIMIT-channel contract, agreed (tier S, 2026-09-04).**
  Reviewing **#154** — a `ConditionResult` holding no load still carrying
  `safety_factor = 1.5`, so a geometry table prints an ULTIMATE banner — found
  the factor applied on far more surfaces than the contract's purpose requires;
  the `engine` CLI report scales a mean takeoff torque 554.4 → 831.6 ft-lb.
  `docs/30_future/48_limit_channel_note.md` states the rulings that follow
  (**OR-76 … OR-86**, gates **G-OR-44 … G-OR-48**): module analysis becomes a
  LIMIT channel while the oracle GUI, the technical report and the export deck
  stay ULTIMATE through 0.8.2; the factor is **stated, never applied** as the
  endpoint, with the last multiply removed in 0.8.3's own boundary note; LIMIT
  becomes the global default with no per-artifact marker, retiring M4-15 in
  0.8.3; and the factorless test gets one owner,
  `safety_factors.prescribes_factor` — *no load-unit value and no `case_ref`* —
  leaving the governing family table untouched. Measured, that rule is a stable
  38 conditions on both GA6 and Baron 58, with `select`'s 6 critical wing cases
  protected by the `case_ref` clause. Decisions only: no code, no schema hop, no
  frozen file touched; #154 stays open and implements inside the note.
