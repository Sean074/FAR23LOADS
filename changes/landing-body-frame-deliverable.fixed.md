- **LANDLOAD's airplane-datum lift term and moment transform carry the same wrong sign as `BETA` did (approved deviation, issue #134, tier L, 2026-08-29).**
  The third and fourth instances of the #133 sign class, in the two quantities
  that entry could not reach because neither was in sloads until now.
  `LANDLOAD.BAS` writes the datum drag load factor's lift term as
  `+LF*SIN(GRA)` and the datum moment transform as a rotation of `+GRA`, where
  the physics — and `ρ = −GRA`, and the deck's own ground lift (G-7a) — give the
  other sign. Neither is written longhand in the port: both rotate through the
  case's own **measured** `ρ`, so the corrected value is what a rotation gives
  rather than a sign somebody typed. Case 1's factors move from the printed
  3.287 / 3.216 / 0.679 to **3.269 / 3.216 / 0.585**. Registered in
  `docs/20_theory/02_approved_corrections.md`; no printed cell was unlocked and
  the locked count rose by 72.

- **The LANDLOAD case families and the frame rotation had drifted from the code that draws them (rule 4 sweep, 2026-08-29).**
  `GROUND_LIFT_CASES` / `GROUND_ONE_WHEEL_CASES` / `GROUND_SIDE_CASES` /
  `BALANCED_GROUND_CASES` lived in `modules/balance.py`, beside the deck that
  consumes them and away from `modules/landing.py`, which *is* the case
  numbering; `attitude_of` lived in `gear_loads`. All are now owned by
  `landing`, and the 23.485 pairing that `NS` and the deck each derived
  separately is one `side_partner`. `to_airplane_datum` / `to_ground_line` /
  the `ρ` measurement moved to `sloads/frames.py`, the module that names the two
  frames they rotate between.
