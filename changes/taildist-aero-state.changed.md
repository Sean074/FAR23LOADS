- **TAILDIST states the aero state of each case it distributes (note 35, #100,
  tier L, 2026-08-27; C210-32).** Every h-tail/v-tail `CriticalCondition` now
  publishes the state its method actually used — `alpha_tail_deg` (AT / fin
  AoA), `delta_deg` (elevator TE-dn + / rudder SC-2 TE-port +) and `q_psf` —
  as additive `None`-default result fields beside L-7's `beta_deg` (AS-1/AS-2;
  no migration hop, `SCHEMA_VERSION` unchanged), and TAILDIST prints them
  ahead of each condition's stations with the carried-across fields on
  `TailChordResult`. A quantity the method never defines states its fixed
  reason instead of a guess (AS-4): the checked-maneuver δ (the 23.423(b)
  increment is the pitching-acceleration inertia term), the side-gust q
  (23.443(b) is linear in V), any h-tail β; a persisted critical set that
  predates the fields says "re-run SELECT". The AHT / AVT + EFFECTV
  intermediates print **once per component** from the same single-source
  owners inside the loads — the finite-surface slope `2π/(1+2/AR)` is
  consolidated to `_vtail.lift_curve_slope` (AS-5), replacing three inline
  spellings in `select.py`, with a one-spelling drift guard. Closure gates
  G-AS-1..G-AS-5 in `tests/test_taildist_aero_state.py`: the Appendix A
  case-202 δ −5.39° oracle, the rel-1e-9 identities reconstructing every
  fixture's stamped `LT25`/`LT50` from the published state, the
  no-silent-blank statement guard, the stale-set statement and the §1
  per-label literals. **No load number moves** (AS-8): only the
  `csv/taildist` and `txt/taildist` digests changed.
