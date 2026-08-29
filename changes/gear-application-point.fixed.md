- **The ground reaction is applied where Appendix A applies it, not at the tyre
  on every case (tier L, 2026-08-29).** `gear_loads.transfer_couple(patch, …)`
  was one call site for all 33 LANDLOAD cases, while the manual's own printed
  column applies cases 1–12 at the **axle** and 13–24 at the **ground contact
  point** — so the twelve landing cases carried a spurious `r × F` pitching
  moment into every balanced ground case, absorbed silently into the solved `q̈`.
  Found by an identity that never reads the point: `residual My − the G-7a lift
  moment == PITCHP`, LANDLOAD's own unbalanced moment. It closes to ≤62 lb-in at
  the printed column's point and misses by 20,964–665,862 lb-in at the other one,
  on all six bundled fixtures, splitting **exactly** where the column splits;
  clearest on ga6's LG-01/02/03, where `PITCHP` is exactly zero and the whole
  patch residual (−9,840.6 / −28,553.5 / −31,182.9 lb-in) was invented. The split
  is physical: level-landing drag is a spin-up load reacted through the bearing,
  braking torque is internal to the wheel/leg free body. `application_point` is
  the one owner (design note 39 AP-2), read by the transfer, the gear free-body
  report and the emitted location; `GearLegLoad`/`AppliedWheel` carry `point`
  beside `patch`, which stays reported as the gear-side geometry it always was.
  No reaction changes and no oracle moved: the forces are LANDLOAD's own, so
  every Appendix A lock passes unmodified. `LG-04`'s pre-closure `My` moves
  −179,232 → −158,271 lb-in and its `q̈` −1.925e-2 → −1.701e-2; the frozen
  Imperial digest and `balanced_cases.md` §9.5 move with them. New gate
  **G-AP-1** asserts the identity on every balanced ground case of every fixture
  at `1e-4 · n·W·MAC` (worst measured 2.65e-5), replacing both an arm correction
  the *test* used to make on cases 1–12/19–24 and the 5 % slack the braked-roll
  pitch line carried for the #133 sign error — every family now closes on one
  bound. **G-AP-2** locks the point against a transcription of the printed
  column; **G-AP-3** asserts the package builds an application point in exactly
  one place. Design note 39 (AP-1…AP-6, G-AP-1…G-AP-5), AGREED 2026-08-29.
