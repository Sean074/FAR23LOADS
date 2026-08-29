- **The set that carries no airplane (#144, tier M, 2026-08-29)** — Found
  diagnosing a GA6 V-n failure that named nothing: a coefficient set had reached
  the balance with every lift coefficient zero, and the only evidence the user
  got was "did not converge in 400 iterations … reached NZ=0 at alpha=41.3861
  deg". The refusal is stated where the value is consumed, for every writer,
  because more than one can produce it (#143 is the writer this one came from,
  and it is fixed separately) — the same ruling the #81 stall-CL, weightless-CG
  and tail-CP-at-datum guards on that function already carry.
  The line is drawn at *no alpha lever*, `C1..C4` all zero, rather than at the
  identically-zero polynomial the report showed. A constant-CL set (`C0`
  non-zero, no slope) hangs the inner loop the same way and for the same reason:
  NZ cannot move, so the iteration has nothing to iterate. That is unsolvable,
  not merely implausible, which is what separates it from the neighbouring
  `aero_lift_slope_sign` warning — a negative or over-large slope still
  balances, and stays a `ConsistencyWarning` rather than becoming a run failure.
  The other two polynomials are ruled on explicitly in the guard's docstring and
  executed in the test: an all-zero drag or moment polynomial must still run,
  because `CD = 0` and `CM = 0` are values a set may honestly carry, while an
  all-zero lift polynomial is a statement that there is no airplane to balance.
  The test drives both entry points that share `balance_configs`, and builds its
  phantom set the way the GUI does — blank coefficients with `stall_cl` filled
  from `clmax_flap` — asserting that fill first, so the case cannot quietly stop
  proving anything by starting to trip the #81 guard instead.
