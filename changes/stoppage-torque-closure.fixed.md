- **23.361(b)(1) sudden-stoppage torque is closure-gated, and its whole-integer
  truncation now floors as the `.BAS` did (CR-B-3 `[MAJOR]`, tier M,
  2026-08-22).** The condition had no numeric assertion anywhere: the engine
  tests pinned only `_prop_inertia`, and the FAR 25 test asserted only that
  25.361(a)(3)(i) *equals* it — self-consistency, not a value — so a regression
  in the rotor summation or in the Δt division would have passed the suite. It
  is twin-only and the bundled Appendix B carries no engine-mount output, so the
  gate is the formula rather than a printed figure (CONVENTIONS §6):
  `torque = I_prop·ω_prop/Δt + Σᵢ I_rotor(i)·ω_rotor(i)/Δt`, re-derived in
  `test_361_b1_closes_on_the_angular_momentum_formula` from the fixture's rotor
  list rather than from the module's own summation, and with a counter-rotating
  rotor in that fixture so the **signed** sum is pinned and not its magnitude.
- **GW-BASIC `INT()` semantics have one owner, `sloads/basic.py` (tier M,
  2026-08-22).** ENGLOADS.BAS line 944 prints `INT(-TORQSUDSTOP)` and BASIC
  `INT()` **floors**, where Python's `int()` truncates toward zero. The two agree
  on non-negative arguments and differ by exactly one unit on every negative one
  — and the stoppage argument is negative by construction, since reaction torque
  is reported negative (CONVENTIONS §5). The port therefore reported 1 ft-lb
  *less* torque than the source program, in the non-conservative direction: the
  ATR-42 fixture moves −24472 → **−24473 ft-lb** limit, at both call sites
  (23.361(b)(1) and the FAR 25 case that shares the torque). No Appendix A figure
  moves — the case is turboprop-only — and the frozen Imperial baseline was
  regenerated for that one deliberate change. Swept in the same change (rule 4):
  every `.BAS` `INT()` port now reads the owner (`basic_int` / `basic_trunc3`)
  instead of open-coding it — `engine.py` ×3, `landing.py`'s printed lever arms,
  `wing_inertia.py`'s densities, `weight_estimate.py`'s weight rows. Four of
  those had the same latent exposure and were simply not yet negative in a
  shipped fixture: a left-hand engine's Y c.g., and any LANDLOAD lever arm
  forward of the datum. Guard (rule 3):
  `tests/test_basic_semantics.py` pins the floor-vs-truncate semantics and greps
  the calc layer for a re-opened copy, with a reasoned allowlist for the one
  `int()` in `sloads/modules/` that is a step count rather than a truncation.
