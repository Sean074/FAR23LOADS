# TAILDIST states the aero state of each case it distributes

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6)*

**Status: SHIPPED 2026-08-27 (#100, C210-32, tier L;
`changes/taildist-aero-state.*`). Agreed 2026-08-26 (owner, in session —
`CLAUDE.md` rule 1's working-alone path); implemented as drafted, gates
G-AS-1…G-AS-5 in `tests/test_taildist_aero_state.py`. Milestone: 0.8.0; rolls
to `40_history/` at the cut.** Agreed with one scope ruling: the
equivalent-gust-Δα extension offered under AS-2 is **parked**
([`02_parked.md`](02_parked.md), "Equivalent gust Δα on the h-tail gust
conditions") — the gust cases state their trim state plus the existing load
increment, nothing more.

**Scope.** Owner directive (C210-32, build review 2026-08-23): *"it would be
useful in TAILDIST to record the alpha, beta and rudder or elevator
deflections for each case"* — with the slope/effectiveness intermediates
(AVT, EFFECTV) printed once per component. Today TAILDIST prints only
LT25/LT50 and the five net pressures; the aero state that produced each case
is invisible on the page that distributes it, and for several conditions it
is computed upstream and discarded. This note settles the contract change
(which fields, on what), which conditions can supply each quantity, what a
condition that cannot supply one emits, and the closure gates.

Sources reviewed: `sloads/modules/select.py`, `sloads/modules/_vtail.py`,
`sloads/modules/taildist.py`, `sloads/models/results.py`
(`CriticalCondition`, `TailChordResult`), `sloads/io.py`,
`docs/10_standard/CONVENTIONS.md` §1.1 (SC-1/SC-2, the AT chain) and §3
(angles are never SF-scaled), `docs/20_theory/00_theory_sources.md`
(`select`, `taildist` rows), `tests/test_l7_lateral_balance.py`,
`tests/test_schema_guards.py`. Theory: Ref 1 Ch 9 (SELECT) / Ch 10
(TAILDIST); `SELECT.BAS` htail balancing + subr 8300.

---

## 1. What exists today (verified inventory, 2026-08-26)

| Condition family | tail/fin AoA | elevator/rudder δ | β | q |
|---|---|---|---|---|
| htail BAL UP/DN RET/EXT (×4) | computed **and published** as loose `LoadValue` "Tail angle of attack AT" (`select.py:430`) | computed and published "Elevator deflection (TE dn +)" (`:431`) | — | computed (`:370`), unpublished |
| htail UNCHECKED MAN UP/DN (×2) | computed (`bal(p).at`), **discarded** | published "Elevator deflection" = signed full throw (`:535`) | — | computed inline, unpublished |
| htail CHECKED MAN UP/DN (×2) | computed (trim `b.at`), discarded | **never computed** — the 23.423(b) increment is the `Iyy·θ̈/arm` inertia term, no δ in the method | — | computed inside balance, unpublished |
| htail GUST UP/DN RET/EXT (×4) | computed (trim, `bal_full`), discarded | computed (trim `b.delta`), discarded | — | unpublished |
| htail UNSYMMETRICAL | copies the governing case's `lt25`/`lt50` only | — | — | — |
| vtail SUDDEN RUDDER | fin AoA is 0, never a variable | the input `rudder_deflection_deg`, unpublished | `beta_deg=0.0` (structured, L-7.6) | computed in `_vt_rudder_load`, unpublished |
| vtail YAW TO SIDESLIP | the literal `-19.5` (`:859`) | full rudder (input), unpublished | `beta_deg=19.5` | unpublished |
| vtail YAW 15 NEUTRAL | literal `-15.0` | rudder neutral, unstated | `beta_deg=15.0` | unpublished |
| vtail SIDE GUST | effective gust β (`_vt_side_gust_terms`) | rudder neutral, unstated | `beta_deg=gust β` | N/A — 23.443(b) is linear in V, no q term |

AVT (`_vtail.vtail_lift_slope`) and EFFECTV (`_vtail.rudder_effectiveness`)
never escape the module in any form; the htail slope AHT
(`2π/(1+2/AR_HT)` — the *same formula* as AVT) is re-spelled inline at three
sites in `select.py`. TAILDIST reads only
`component/lt25/lt50/label/case_ref/far_reference/safety_factor`.

---

## 2. Decisions (AS-1 … AS-8)

| # | Decision | Rationale |
|---|---|---|
| **AS-1** | `CriticalCondition` gains three optional **result** fields, `None` default: `alpha_tail_deg` (htail AT / fin AoA, deg), `delta_deg` (elevator for htail, rudder for vtail, deg), `q_psf` (dynamic pressure at the governing point, lb/ft²). `beta_deg` already exists (L-7.6) and is unchanged. Tail-scoped like `lt25`/`lt50`: `None` on wing/fuselage conditions by contract. | The structured field is what TAILDIST can read without parsing `LoadValue` labels; L-7.6 is the precedent ("publish the state that made the load; the consumer never re-derives it"). |
| **AS-2** | **The published state is the state the method actually used.** Balancing: the balance AT and moment-balance δ. Unchecked: trim AT + the signed full throw. Checked and gust: the **trim** AT and **trim** δ at the governing point — the increment (already a labelled `LoadValue`) is what separates trim from total, and the display says so. Unsymmetrical: fields **copied from the governing source condition**. No new physics is computed; a quantity the method never defines is `None` with a stated reason (AS-4). *(Owner ruling at agreement, 2026-08-26: the equivalent-gust-Δα form is parked, `02_parked.md`.)* | Inventing a "total effective α" for a gust, or a δ for the checked inertia increment, would be new physics outside C210-32's display-only scope and unverifiable against any oracle. |
| **AS-3** | Signs and senses are the existing conventions, cited not restated: AT per CONVENTIONS §1.1 (`AT = α_wl + IT − E`, +AT ⇒ up tail load); elevator δ TE-down positive (the existing `:431` label); rudder δ per **SC-2** (+δr = TE port); β per **SC-1**. Fin AoA for the yaw cases is the value the method feeds `_vt_aoa_load` (−19.5/−15: opposite sign to `beta_deg`, which is the SC-1 restatement). Angles and q are never SF-scaled (§3: loads only). | One owner per convention; the report's sign section already states all of these. |
| **AS-4** | **A condition that cannot supply a quantity states why.** The reason strings are fixed by this note: checked maneuver δ → "not defined by the method — the 23.423(b) increment is the pitching-acceleration inertia term"; side-gust q → "23.443(b) is linear in V — no q term"; a persisted critical set predating the fields → "aero state not recorded — critical set predates these fields; re-run SELECT" (the `test_l7_lateral_balance.py:310-325` stale-set pattern), never a guess. | The done-condition is "every TAILDIST condition either stating its aero state or saying why it has none". |
| **AS-5** | **AHT and AVT get one owner.** `_vtail.vtail_lift_slope` generalizes to the shared finite-surface slope `2π/(1+2/AR)`; the three inline `aht = 2π/(1+2/AR_HT)` spellings in `select.py` are **replaced by calls**, not duplicated (consolidation over decoration). TAILDIST prints AHT / AVT / EFFECTV **once per component** by calling the same owners on the same inputs — the `surface_geom` precedent ("one hinge line in the suite instead of two"): calling the single-source function is not recomputing another module's quantity. Not persisted. | Rule 3 (make it structural): the intermediate printed beside the loads must be arithmetically the one inside them, and a shared pure function guarantees it without schema weight. |
| **AS-6** | **Display:** `TailChordResult` carries the four fields across; TAILDIST's per-condition block (`taildist.py:166-174`) prints them as deg / lb/ft² values ahead of the stations, each `None` replaced by its AS-4 reason; the per-component header prints AHT (htail) or AVT + EFFECTV (vtail) once. SELECT's existing loose `LoadValue`s stay (its own page is unchanged); the balancing pair at `:430-431` is **populated from the same locals** as the new fields, so screen and structure cannot disagree. | C210-32 is aimed at the TAILDIST page; SELECT display churn is #95/#94 territory. |
| **AS-7** | **Schema: additive result fields, no migration hop and no version bump** — the `body_axial_clamped` precedent (`test_schema_guards.py:245-250`) and the `beta_deg` ledger entry ("all additive with `None` defaults, so no migration hop"). Writing is automatic (`asdict`); `io.py:_critical_condition_from_dict` gains three `d.get(...)` lines beside `beta_deg`'s; the schema-guard ledger records the addition. | `SCHEMA_VERSION` guards input migrations; a result field that loads as `None` from every older file is exactly what the ledger's additive class is for. |
| **AS-8** | **No load number changes anywhere.** This is fields + display only; every Appendix A oracle and twin closure passes untouched, and the FAR23-reduction invariant is part of the gate. | The backlog's standing invariant; C210-32 is class c (display). |

---

## 3. Closure gates (G-AS-1 … G-AS-5)

Benchmark-first (rule 2). Oracle tolerance ±0.1 % where a number is printed;
pass-through identities exact (`rel_tol=1e-9`).

| Gate | Statement | Expected numbers |
|---|---|---|
| **G-AS-1** (oracle) | On ga6, UP BAL RETRACTED's structured `alpha_tail_deg`/`delta_deg` equal the loose `LoadValue`s already oracle-checked, and `delta_deg` matches Appendix A "Critical Horiz Tail Loads" **δ = −5.39°** (±0.1 %; Ch 9 case 202, the row that prints LT25 +907.62 / LT50 −387.78 / CP 6.35 %). | δ −5.39°; AT equal to the published "Tail angle of attack AT" value bit-for-bit (same local). |
| **G-AS-2** (closure identity, CI) | On every shipped fixture, the published state reconstructs the stamped split, per family: balancing `lt25 = (AT·AHT/57.3)·q·ST`; unchecked `lt50 = δ·eff·EF·AHT/57.3·q·ST` and `lt25` from trim AT; checked/gust `lt25 − (stated increment) = (AT·AHT/57.3)·q·ST`; vtail yaw/rudder loads from (fin AoA, δr, q, AVT, EFFECTV) per the Ch 9 formulas. | rel 1e-9 — these are the method's own equations evaluated on the published values. |
| **G-AS-3** (statement guard) | Every TAILDIST htail/vtail condition row states each of AoA / β / δ / q **or** its AS-4 reason string; iterated over ga6 and the twin fixture. | No silent blank. |
| **G-AS-4** (stale set) | A persisted critical set built with the fields `None` renders the AS-4 "predates — re-run SELECT" statement, never a value. | Pattern of `test_l7_lateral_balance.py:310-325`. |
| **G-AS-5** (drift guard) | Per-label expected values on ga6: vtail fin AoA `0 / −19.5 / −15 / gust β`, δr `(input, input, 0, 0)`, htail checked δ = the AS-4 reason — extending the `test_l7_lateral_balance.py:296-307` per-label pattern; plus the FAR23-reduction check that the full oracle suite is untouched. | Literals per §1's table. |

**Closure tier:** L — this note at AGREED first, then implementation with the
`theory_sources.md` citation (the `select`/`taildist` rows grow the
published-state sentence), the schema-ledger entry, a full-format history
fragment, and `PROGRAM_SPEC.md`'s TAILDIST section updated.
