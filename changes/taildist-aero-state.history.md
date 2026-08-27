## Step — TAILDIST states the aero state of each case it distributes (#100, note 35, tier L, 2026-08-27)

**Objective.** Close C210-32 (owner directive: "record the alpha, beta and
rudder or elevator deflections for each case" in TAILDIST, with the
slope/effectiveness intermediates once per component): the aero state that
produced each distributed tail case was computed upstream and discarded — for
several conditions not even computed loose — and the page that distributes a
case could not say what state made it.

**Deliverables.**
- `CriticalCondition.alpha_tail_deg` / `delta_deg` / `q_psf` (AS-1): additive
  `None`-default **result** fields beside L-7's `beta_deg`; `io.py` reads
  them with the same `d.get` pattern, no migration hop, `SCHEMA_VERSION`
  unchanged (AS-7, the `beta_deg`/`body_axial_clamped` ledger class).
- Every SELECT tail emitter publishes the state its method actually used
  (AS-2): balancing the balance AT and moment-balance δ (the same locals as
  the loose oracle-checked `LoadValue`s, AS-6), unchecked the trim AT plus
  the signed full throw, checked and gust the trim state (the labelled
  increment is what separates trim from total), the unsymmetrical case a copy
  of its governing source; v-tail fin AoA 0 / −19.5 / −15 / −gust-β with the
  rudder throw, and q stamped centrally in `_htail_condition` from the
  governing point itself.
- `TailChordResult` carries the four fields across; TAILDIST renders them
  ahead of the stations (`taildist.aero_state_values`) with the AS-4 fixed
  reasons where a method defines no value (checked δ, side-gust q, h-tail β)
  and the "re-run SELECT" statement on a stale persisted set; angles and q
  are non-load units, never SF-scaled (CONVENTIONS §3).
- `taildist.component_constants`: AHT (h-tail) / AVT + EFFECTV (v-tail)
  printed once per component by calling the same owners inside the loads.
  The finite-surface slope `2π/(1+2/AR)` consolidated to
  `_vtail.lift_curve_slope` (AS-5) — the three inline `select.py` spellings
  replaced by calls, ONENGOUT renamed onto the shared owner.
- Docs: `theory_sources.md` `select`/`taildist` rows grew the published-state
  sentences; `PROGRAM_SPEC.md` TAILDIST section; the schema-guard ledger
  entry.

**Test.** `tests/test_taildist_aero_state.py` — G-AS-1: on the Appendix A
GA6, `BAL UP RETRACTED`'s structured fields equal the loose `LoadValue`s
bit-for-bit and δ matches Appendix A's −5.39° (Ch 9 case 202). G-AS-2: on
every shipped fixture the published state reconstructs the stamped
`LT25`/`LT50` through the method's own equations (rel 1e-9, per family).
G-AS-3: every TAILDIST condition states each of AoA/β/δ/q or its AS-4
reason. G-AS-4: a stale persisted set renders the "re-run SELECT" statement,
never a value. G-AS-5: the §1 per-label literals plus the one-spelling slope
drift guard. AS-8 (no load number moves) is the rest of the suite: only the
`csv/taildist` / `txt/taildist` digests changed.

**Key decisions.** The published state is the state the method used, never a
derived "total effective" one — the equivalent-gust-Δα extension is parked
with the owner's ruling (`02_parked.md`). Disclosure reasons are fixed
strings owned by `taildist` (AS-4), so "cannot supply" is a statement, not a
blank. Reading the slope/effectiveness owners from TAILDIST is not
recomputing another module's quantity (the `surface_geom` precedent); making
the slope single-source is what guarantees the printed intermediate is
arithmetically the one inside the loads (rule 3).
