- **A solve that cannot close now says so, and the one that closes on nothing is
  named rather than refused (#33, tier M, 2026-08-22)** — the review ranked this
  band-C item second of everything filed because of its blast radius rather than
  its size: `_balance`'s two loops returned their last iterate on exhaustion, and
  every V-n point, SELECT pick, balanced case and exported deck consumes that
  return with nothing to distinguish an answer from a place the search gave up.
  Working it turned up the shipped instance the ranking predicted — a CG the
  airplane cannot trim at yields `NZ = 0.658` at 41 deg alpha, reported as a 1-g
  balanced point — and, in the same sweep, two more solvers with the identical
  shape: WINGINER returning the density it was passing through, FLAPLOAD
  returning its own 100,000 ft/s guard value and amplifying the flap load by its
  square. The interesting half was not the refusal but what must **not** be
  refused. Measured before deciding: the only exhaustion on any shipped fixture
  is nine of `atr42_100`'s 300 points, and they are exactly the nine decision
  **D-30** had already ruled ordinary stall-limited flight — the Mach cap pins
  the true airspeed, the dynamic-pressure iteration has no lever, and **23.333(b)**
  excludes such a point from the manoeuvring envelope rather than owing it. A
  plain converged/failed flag would have refused three weight cases of a shipped
  fixture for agreeing with the regulation, so the vocabulary has three outcomes
  and `sloads/convergence.py` owns it: **converged**, **clamped** — a fixed point
  outside the acceptance band, returned with its state attached — and **failed**,
  which raises. Clamped is detected as exact float equality on `q` rather than by
  any physics test, which is what makes exiting on it free: the remaining trips
  re-solve the identical inner problem, verified as all 600 rows bit-identical to
  the pre-#33 code and 4.3× faster on the fixture that clamps. The state has one
  owner (`EnvelopeResult.clamped_cases`, derived, never persisted, no schema hop),
  and the Aerodynamic Data page's stall-clamp margin — which finds the same corner
  from the published CL, from the outside — is pinned to name the same rows, so
  band-B #32's marker reads the solver's own answer instead of growing a second
  predicate beside it. The class is closed by an AST walk rather than by prose: a
  trip-counted loop that breaks with no `else: raise` fails the build or is
  classified with its reason, and the two classified loops are stated to be
  something else (a time march, an unbounded inflation) rather than exempted.
