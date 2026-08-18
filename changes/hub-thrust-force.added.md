- **Engine thrust at the hub — the assembled model's first forward force** (issue
  #10, carved out of design note 21, tier M, 2026-08-17). One user-entered
  `EngineInput.thrust_lb` per engine becomes an axial `FORCE` at that engine's
  hub in every assembled **flight** balanced case, and on the LRA beam model's
  engine hub node — the node the skeleton has carried since R-9 and, until now,
  never had a load on. `fx = −T` at `prop_cg` (falling back to `engine_cg`, and
  a refusal naming the datum when neither exists); the thrust line is taken
  axial, so the P-6 incidence/toe angles, the propeller normal force, the
  slipstream band and every DATCOM power derivative stay parked with note 21.
  **Nothing balances it, by design:** the V-n point the case is assembled at is
  thrust-free, so the applied thrust and its couple `−T·(z_hub − z_cg)` are the
  pre-closure `Fx` and `My` in full and are reacted by the closure —
  `n_x = (D − ΣT)/W`, the longitudinal carrier the assembled model has always
  lacked, and `q̇`. A powered case therefore joins the lateral, 23.427(a) and
  ground families in standing outside the 1 % pre-closure gate, with a stronger
  gate of its own: the residual *is* the thrust, in closed form. Ground cases
  state the entered value and do not apply it (rating thrust per case family is
  note 21's parked power-policy table), and an **asymmetric** entry is stated
  rather than handled — it yaws the airplane, mints no twin of its own (an axial
  force off the centreline makes neither the lateral force nor the roll that
  `is_handed` measures), and a twin got from another source mirrors the
  installation with everything else, which is note 21 §4.4's parked decision. New `tests/test_hub_thrust.py` gates
  G-1…G-11, including `ΣT = D ⇒ n_x = 0`, the hub node's exactly-zero transfer
  couple, and the six-DOF closure read back from the deck's own cards. Single
  owner `balance.hub_thrust_set` (`CONVENTIONS.md` §7); behaviour of record
  `docs/20_theory/balanced_cases.md` §2.1. The Engine Mount page gains the input,
  and `units.py` gains a `force` input kind (lbf → N — deliberately not the
  `weight` kind). **Off unless entered:** the schema field shipped with v54 and
  no fixture uses it, so every shipped number is bit-for-bit unchanged. Plan
  11's double-count authority table, `PROGRAM_SPEC`'s LRA-deck node list, note
  21's decision **P-6a**, the index and the parked entry all carried "the hub
  thrust `FORCE` is absent until power effects ship" and are corrected to what
  now ships: the hub `FORCE` is applied and **axial**, the mount node's
  ENGLOADS torque/gyro `MOMENT`s are still absent.
