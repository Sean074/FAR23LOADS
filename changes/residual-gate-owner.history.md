- **Residual-gate exemption predicate: one owner (CR-C-2 `[MAJOR]`, #41, tier M,
  2026-08-22)** — the review's third theme, statements about the deliverable, in
  its sharpest form: the controlling document declared the flagship balanced
  model *over* its own residual gate in every ga6/RJ bundle shipped since 0.6.0.
  Three defects sat in one rendered sentence. The maximum was taken over all
  cases, so what §6 reported as the deliverable's verdict was the 23.427(a)
  maneuver tail load (143.885 % of n·W on `ga6_normal`) — a quantity the deck's
  own `$` header, the case-table note and the theory doc each separately say the
  gate does not apply to. The cause the sentence offered had been retired months
  earlier with the `body-axial` carrier. And the Balanced Cases page reached the
  same false warning by a different route, excluding only the 23.427(a) family
  and so reporting a ground case's applied gear reaction (100.000 %) as a balance
  failure. The gate read the case objects; nothing read the claim. The fix is the
  one the repo's rule 3 asks for: `balance.residual_gate_applies` is now the
  single owner of *which cases the gate applies to*, with
  `residual_gate_exemptions` naming and counting the exempt families so a
  filtered maximum always ships with its filter visible, and both surfaces plus
  the case-table note read them. Working the predicate settled a question the
  review had left implicit: the lateral family stays **gated**, because
  23.441/23.443 exempts `Fy`/`Mz` and the two gated fractions contain neither —
  they are exactly the symmetric half that the lateral family's own gate is
  stated on, so exempting it would have deleted a live check on eight cases per
  fixture. The powered family, which no shipped fixture exercises, was added to
  the exemption on the strength of `is_powered`'s own docstring rather than left
  to be discovered from a future failure. Two further sites of the class went in
  the same change: the per-case table note, which named every exemption except
  the ground rows sitting at 100 % inside that very table, and the page's
  stale caption on unassembled conditions, deleted rather than re-worded since
  `skipped_condition_lines` already owns that wording per reason. The rendered
  §6 sentence is now pinned on a ground-assembling fixture, which is the gate the
  whole finding turned on: a claim nothing reads is a claim nothing can keep true.
  Correcting the family then exposed the rest of the same defect, and the owner
  ruled on it in the same session rather than deferring it. The sentence compared
  `max(force, pitch)` against the flat 1 %; pitch meets that everywhere with an
  order of magnitude to spare, force does not on four of the six fixtures
  (1.209–2.360 %), and the ordering tracks fixture lift-model quality rather than
  the assembly — the one fixture with a printed source behind its aero is the
  best of them. None of the six is an oracle: the balanced model is a
  mission-extension deliverable with no printed figure behind it, and the FAR23
  core stays oracle-locked independently. So the force half is now stated at the
  value `tests/test_balance.py` already enforced as its hard stop
  (`FORCE_RESIDUAL_ACCEPTANCE`, 2.5 % of `n·W`), pitch keeps `RESIDUAL_GATE`, the
  test reads the package owner instead of re-declaring the number, and the
  per-fixture ratchets stay beneath it as the regression guard. Splitting the two
  components surfaced one more layer: the pitch residual passes 1 % on exactly the
  cases whose forward non-wing axial force is clamped (D-4), which are out of trim
  by that known un-applied force and its couple and are gated per case — so
  `residual_gate_family` returns `(judged, clamped)` and both surfaces state the
  clamped standing rather than reporting a modelling decision as a failure. The
  judged family then clears both acceptances on every fixture, and what the
  controlling document says about the primary deliverable is true again.
