- **LANDLOAD's `BETA` carried the wrong sign on the ground-roll and tail-down
  attitudes; the ground-roll families were levered and resolved off it (tier L,
  2026-08-29).** `BETA` is the resultant-to-FS angle, and Appendix A p234 states
  the rule in the drawing: `BETA = GAMMA − GROUND ANGLE`, with `GAMMA = 0` where
  the reaction is normal to the ground. `LANDLOAD.BAS` applies that to the level
  attitude only, writing `+GRA(2)` / `+GRA(3)` for the other two. Attitude 3
  negates it back at both its use sites and came out right; **attitude 2 negated
  it at neither**, so every braked-roll, side and supplementary-nose case took
  both its lever arms and its `PHIM`/`PHIN` from the wrong sign — and those are
  shipped ULTIMATE loads, carried into the exported ground `FORCE` cards and the
  gear reference-point loads. Corrected at the origin (`landing.py:229`), which
  is one line plus the `ap[1]` call site that read the literal `gra2`; attitude
  3's two compensating negations are removed as redundant, changing no number.
  Approved oracle deviation (design note 38 GF-1/GF-2′/GF-3″, AGREED; register
  `docs/20_theory/02_approved_corrections.md`), superseding the "considered and
  declined" decision of 2026-08-15. The evidence is the manual against itself:
  Appendix A's braked-roll construction figure **p235** prints lever arms of
  77.052 / 17.760 / 94.811 where its p230 **table** — program output — prints
  69.886 / 23.260 / 93.147, and flipping the one sign reproduces all three figure
  values exactly with `CP` untouched. The `ρ == −GRA` pin is **flipped, not
  deleted**, and now holds in every attitude against `ground_angles` directly
  (`test_rho_is_minus_the_ground_angle_in_every_attitude`), replacing a check
  that recovered its reference from the thing it checked. The p230/p231/p232/p233
  locks re-pin cell by cell with the printed values kept transcribed beside the
  corrected ones; `balanced_cases.md` §9.5 and the frozen Imperial digest move
  with them. Side-family body drag flips from +186 lb aft to −186 lb forward,
  which is what nose-up geometry demands.
