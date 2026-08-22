- **23.361(b)(1) stoppage torque: formula closure + truncation basis (CR-B-3
  `[MAJOR]`, #40, tier M, 2026-08-22)** — the review's second guard blind spot.
  The sudden-stoppage engine-mount torque was computed but never asserted: the
  only numbers any test held for it were the propeller inertia and the FAR 25
  case's equality with it, so the rotor loop, a rotor's sign and the Δt division
  were all unguarded. Because the condition is turboprop-only and the bundled
  Appendix B has no engine-mount page, the policy gate is closure rather than an
  oracle (CONVENTIONS §6), and it is now stated as such: the angular-momentum
  formula `I·ω/Δt` summed over the propeller and every rotor, re-derived in the
  test from the fixture's own rotor list, with a counter-rotating rotor present
  so the signed summation is what passes. Working the truncation half turned up
  the substantive defect: ENGLOADS.BAS prints `INT(-TORQSUDSTOP)`, and GW-BASIC's
  `INT()` floors while Python's `int()` truncates toward zero. They agree
  wherever the argument is non-negative — which is why the port survived this
  long — but the reported reaction torque is negative by convention, so the suite
  had been reporting 1 ft-lb less torque than the source program, on the
  non-conservative side (ATR-42: −24472 → −24473 ft-lb limit; no Appendix A
  figure moves, and the frozen Imperial baseline was regenerated for that one
  change). The class fix (rules 3 and 4) is a single owner for the BASIC numeric
  semantics, `sloads/basic.py`, holding both `basic_int` and the 3-decimal
  `basic_trunc3`; all seven previously open-coded truncations across `engine.py`,
  `landing.py`, `wing_inertia.py` and `weight_estimate.py` now read it, four of
  them carrying the same latent negative-argument exposure (a left-hand engine's
  Y c.g., a LANDLOAD lever arm forward of the datum) that no shipped fixture had
  yet triggered. `tests/test_basic_semantics.py` is the drift guard: it pins
  floor-vs-truncate directly and greps the calc layer so a new `int()` there has
  to be classified rather than defaulted to Python's semantics.
