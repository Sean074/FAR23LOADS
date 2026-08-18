- **Engine thrust at the hub (issue #10, note 21 carve-out, tier M, 2026-08-17)** —
  design note 21's seven-step power-effects plan stays parked; what shipped is
  the one piece of it that needs no estimator. A user-entered `thrust_lb` per
  engine is applied as an axial `FORCE` at that engine's hub (`prop_cg`, else
  `engine_cg`, else a refusal) on flight balanced cases only, and routes to the
  LRA model's engine member so it lands on the hub node with an exactly zero
  transfer couple. The design turned on where the unbalance goes: the trim the
  case is assembled at is thrust-free, so rather than re-trimming (note 21 §4's
  parked `retrim_with_power`) the thrust and its hub-arm couple are carried in
  full by the closure's longitudinal and pitch degrees of freedom — which made
  `n_x` the quantity `balance.py` had recorded the suite as lacking a carrier
  for, and put a powered case outside the 1 % pre-closure gate alongside the
  lateral, 23.427(a) and ground families. That exemption is paid for with a
  stronger claim, not a weaker one: with no printed oracle for a number the user
  types, `tests/test_hub_thrust.py` gates closed forms — the pre-closure
  residual *equals* `−ΣT` and `Σ−T·(z_hub − z_cg)` to the last digit (G-3), a
  case whose thrust equals its own net drag closes at `n_x = 0` (G-4), and the
  transferred LRA set keeps the case's resultant with power in it (G-6). Also:
  `units.py` gained a `force` input kind (lbf → N), kept distinct from `weight`
  (lb mass → kg) because conflating the two is the units defect that table
  exists to prevent. The schema field itself had shipped the day before as
  L-7's reserved passenger (decision L-7.10), so this hop changed no schema and
  moved no shipped number — every fixture's cases were exactly zero-thrust
  before and remain so.
