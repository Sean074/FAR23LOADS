- **The residual-gate exemption has one owner, and §6 no longer declares the
  primary deliverable failed on every fixture with ground cases (CR-C-2
  `[MAJOR]`, tier M, 2026-08-22).** The report's §6 maximised the pre-closure
  residual over **all** assembled cases, so `ga6_normal` rendered *"the worst
  pre-closure residual is 143.885 % of n·W against a 1 % gate — OVER the gate"*
  — that number being the 23.427(a) maneuver tail load, which the deck's own `$`
  header, the case-table note and `balanced_cases.md` §7/§8/§9.4 all say the gate
  does not apply to. The Balanced Cases page made the same claim from a different
  wrong family (it excluded only 23.427(a), leaving the ground cases in at
  100.000 % — the applied gear reaction in full). The family the gate actually
  applies to sits at **0.624 %**. The cause named in the sentence had been retired
  on 2026-08-15 when the `body-axial` carrier landed. Now
  `balance.residual_gate_applies` owns the question — exempt where the pre-closure
  `Fz`/`My` *is* an applied load in full (ground 23.471-23.499, unsymmetrical
  h-tail 23.427(a), powered) — and `residual_gate_exemptions` states the exempt
  families, counted, beside the number, since a maximum over a filtered set is
  honest only if the filter is visible. Both surfaces read it; the over-gate
  branch now names the case and whether `Fz` or `My` drives it instead of
  asserting a cause it has not measured.

  **The lateral family is deliberately *not* exempt.** What 23.441/23.443 exempts
  is the `Fy`/`Mz` pair, and neither appears in `force_residual_fraction`
  (`|Fz|/n·W`) or `moment_residual_fraction` (`|My|/(n·W·MAC)`) — those two
  measure precisely the *symmetric half* that `is_lateral`'s own docstring names
  as the gate that does apply to it. Excluding the family, as the review's
  suggested fix would have, deletes a live gate on eight cases per fixture rather
  than correcting a false one; it passes on all six (worst 0.614 %), and
  `test_the_residual_gate_family_is_the_predicates` keeps it that way.

- **Force and pitch are judged against their own acceptances, and the force one
  is stated at the value the suite already enforced (owner's decision,
  2026-08-22, tier M).** Correcting the family exposed the second half of the
  same defect: §6 compared `max(force, pitch)` against the flat 1 %, and force
  does not meet 1 % on four of the six fixtures (atr42 2.360 %, concept_heavy
  1.994 %, dhc8 1.818 %, cessna 1.209 %, against ga6 0.624 % and the RJ 0.478 %).
  Pitch does, everywhere, with an order of magnitude to spare (0.07–0.84 %). The
  ordering tracks **fixture lift-model quality**, not the assembly — `ga6_normal`,
  the one fixture whose aero and planform come from a printed source, is best —
  and none of the six is a printed oracle: the balanced full-span model is a
  mission-extension deliverable with no Appendix A/B figure behind it, and the
  FAR23 replication core stays oracle-locked independently of it. So
  `balance.FORCE_RESIDUAL_ACCEPTANCE` (2.5 % of `n·W`) now owns the force half —
  the value `tests/test_balance.py` already enforced as the hard stop no fixture
  may cross — `RESIDUAL_GATE` (1 % of `n·W·MAC`) keeps the pitch half, and the
  report judges each against the one it is actually held to instead of declaring
  a failure against a bound nothing enforced. The test's own ceiling now *reads*
  the package owner rather than re-declaring it (a second copy of a number is how
  the report and the suite came to disagree in the first place), and the
  per-fixture, per-family `_FORCE_RESIDUAL_RATCHET` is unchanged beneath it: a
  fixture drifting from 2.360 % toward the acceptance still fails loudly, well
  before it arrives.
- **A clamped case is split out rather than judged (tier M).** Reporting the two
  components separately also surfaced that the pitch residual exceeds 1 % on
  exactly the cases whose forward non-wing axial force was **not applied** (design
  note 20 D-4: the trim α outside the polar's trusted window) — atr42 `NMAA`
  1.574 %, concept_heavy `NMAA` 2.090 %. Those are out of trim by exactly the
  clamped force and its couple about the CG, which is a measured quantity gated
  per case in `_CLAMPED_BODY_AXIAL`, so judging them against a flat acceptance
  reports a modelling decision as a failure — the same defect one layer down.
  `balance.residual_gate_family` returns `(judged, clamped)` so the report and the
  page cannot draw that line differently, and both state the clamped cases'
  standing rather than dropping them. With the split, the judged family clears
  both acceptances on all six fixtures.

  Two more sites of the same class went with it: the report's per-case table note
  named the rolling and 23.427(a) exemptions but not the **ground** rows sitting
  at 100.000 % in that same table; and the Balanced Cases page's caption on
  conditions that did not assemble still called ground, fuselage and one-engine-out
  conditions *"a deliberate exclusion … covered by the per-component analyses"*,
  false in both halves since 0.6.0 — ground conditions assemble, and the
  per-component fuselage view is flight-only permanently (D-28). That caption was
  a stale restatement of the per-reason lines above it and was deleted rather
  than re-worded; `skipped_condition_lines` is the single owner of that wording.
  The rendered §6 sentence is now pinned on a ground-assembling fixture — no test
  read the claim before, only the case objects it was derived from.
