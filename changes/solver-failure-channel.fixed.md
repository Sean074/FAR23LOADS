- **The balance had no way to say it had failed, and one shipped path took it up
  on that (#33, tier M, 2026-08-22).** `_balance`'s two iterations — angle of
  attack to the required load factor, then dynamic pressure to the Mach-adjusted
  stall line — both ended the same way whether they succeeded or ran out of
  trips: fall out of the loop, return the last iterate. Every V-n point, SELECT
  pick, balanced case and exported deck downstream consumed the result with no
  way to tell the two apart (review 2026-08-20 §6 rank 2). Measured on a real
  path: a CG the airplane cannot trim at produced `NZ = 0.658` reported as a 1-g
  balanced point, angle of attack 41 deg, and carried it onward. The
  angle-of-attack iteration now **refuses** (`SolverFailure`, a `ValueError` per
  the error contract, so `run_all_modules` cannot swallow it), quoting the
  condition, the CG, the target and what it actually reached.

- **The one non-converged state that is not a failure is named, not refused.**
  Nine of `atr42_100`'s 300 points — `MAN A` / `MAN C` / `AC ROLL` at 25,000 ft
  on all three gross-weight cases — exhaust the dynamic-pressure loop, and
  decision **D-30** already ruled that state ordinary stall-limited flight:
  **23.333(b)** applies the manoeuvring envelope "except where limited by maximum
  (static) lift coefficients", and the Mach cap producing it is 23.335 a.(4)'s
  own provision. A two-state converged/failed flag would have refused three
  shipped weight cases of a shipped fixture on the strength of the regulation
  agreeing with them. So there are three outcomes: **converged**, **clamped**
  (the iterate reached a fixed point outside its band — no lever left) and
  **failed** (trips exhausted with the iterate still moving), the last raised
  rather than returned.

- **Clamped is detected as the fixed point it is, and exiting on it is free.**
  The Mach cap pins the true airspeed, so `q` returns to the same value every
  trip and each remaining trip re-solves the identical inner problem; the test is
  exact float equality on `q`, with no physics in it. Verified against the
  pre-#33 code on the fixture that clamps: all 300 V-n rows and all 300 tail rows
  **bit-identical**, and `build_envelope` 4.3× faster (39.6 ms → 9.2 ms) for not
  spinning 199 dead trips × 400 inner steps × 9 points. Every oracle, SELECT pin
  and the frozen digest are unmoved.

- **One owner for the predicate, so #32 has something to read.**
  `EnvelopeResult.clamped_cases` / `is_clamped` carry the state — derived and
  **never persisted** (`io.envelope_to_dict` names its keys, so no schema field
  and no hop; a loaded project carries it empty until FLTLOADS runs). The
  Aerodynamic Data page's stall-clamp margin finds the same corner from the
  outside, by recovering each published point's CL; the two are now pinned to
  name the **same rows**, so band-B #32's published marker reads the state the
  solver reached instead of deriving a second predicate that can drift from it.

- **Swept with it (rule 4), and closed structurally (rule 3).** The same shape
  was live in two more solvers: WINGINER's root-density iteration returned
  whatever density it was passing through when 100,000 trips ran out, and
  FLAPLOAD's slipstream search returned its own guard value — a 100,000 ft/s
  slipstream — and amplified the flap load by its square. Both refuse now. The
  gate is an **AST walk** over `sloads/`
  (`tests/test_convergence.py::test_no_bounded_search_in_the_package_falls_out_in_silence`):
  a trip-counted loop that `break`s and has no `else: raise` fails the build, or
  is classified with the reason it is not the class. Two are — ONENGOUT's time
  march (running out of steps is the end of the simulation, and `recovered`
  already states what happened) and WTESTIMA's 1 % inflation (no trip bound to
  exhaust). A loop over a collection is deliberately outside the sweep: falling
  off the end of a list means "not there", which is a fact, not an unconverged
  answer.
