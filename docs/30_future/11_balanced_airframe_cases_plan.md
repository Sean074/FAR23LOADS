# Design note — Balanced full-airframe load cases (free-free)

**Raised:** 2026-08-08 (user). **Status:** design agreed at the decision level
(B-1…B-4 answered by the user, 2026-08-08); steps not yet implemented.
**Closure tier:** L — new physics concept (`BalancedCase`), a schema change, a
new module, and a change to what the mass model means.

**Goal, in the user's words:** *a full airplane balanced case — wing tip to wing
tip, nose to tail — with no need for a constraint, because the loads balance.
A wing case has its corresponding tail load and the resulting inertia loads.
Residual inertia may be used, but the change in inertia load should be small.*

Conventions: [`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md).
Related, and deliberately not duplicated here:
[`07_export_equilibrium_invariant_plan.md`](07_export_equilibrium_invariant_plan.md)
(per-deck resultant check; §9 there is the item this plan supersedes),
[`10_sbeam_roundtrip_ci_harness_plan.md`](10_sbeam_roundtrip_ci_harness_plan.md)
(the solver gate this rides on),
[`09_distributed_empennage_loads_plan.md`](09_distributed_empennage_loads_plan.md)
(decision T-11's double-count question, answered here in §4).

---

## 1. Measured baseline (2026-08-08, before any change)

Every number below was computed from `examples/ga6_normal.project.json` on the
current `main`. They are the reason the plan takes the shape it does.

### 1.1 The airplane already balances at trim level

V-n point **case 22** (PHAA, `nz` = 3.8017, W = 3400 lb):

```
lzw = 12969.2    lt = -43.4    lzw + lt = 12925.8 == nz*W = 12925.8   ✓ exact
```

`flight_envelope._balance` closes rigid-body vertical equilibrium exactly, and
`test_concept_closure.py` already asserts it. **The balance is not missing — it
is missing *downstream*, in the distributed loads.**

### 1.2 The distributed loads do not inherit it

| Term | lb |
|---|---|
| Wing net root shear, both sides (2 × 5836.9) | +11,674 |
| Wing reaction the fuselage assumes (`body_loads` `carry` source) | +10,479 |
| **Seam mismatch** | **1,195 = 9.2 % of n·W** |

`body_loads` closes to zero *by construction* — `carry` = `mass` + `tail`
identically — but it closes on a reaction it computes for itself, not on what
the wing delivers. Wing and body currently disagree about the seam load by 9 %.

### 1.3 There are two independent mass models, and they do not reconcile

| Source | Content | Total |
|---|---|---|
| `weight.items` | 24 itemized masses, each with x/y/z and inertias | **3400.0 lb at cg_x 85.00** — matches `mass.cases[0]` exactly |
| `fuselage_mass.stations` | 5 hand-entered lumps, feeding the Ch 15 beam | **2578 lb** |

`weight.items` less the wing panel (330), h-tail (42) and v-tail (23) leaves
**3005 lb** that belongs to the fuselage beam, against the **2578 lb** entered —
a **427 lb** discrepancy with nothing anywhere reconciling it. The itemized
model is the good one: it closes to W and to the CG by construction.

### 1.4 With the item model and correct pairing, the airplane balances to 0.32 %

Assembling case 22 properly — wing strips both sides, tail at its trim value,
inertia from all 24 items at that point's `nz`:

```
wing air (from strips, 2 sides)  +12928.3      [= 2 x net root 11673.7 + nz x 330 wing inertia]
tail air (trim lt)                   -43.4
inertia (all 24 items x nz)      -12925.8
                                 ---------
residual                            -41.0 lb  =  0.317 % of n*W
                                                 dn = -0.0120 g  (0.317 % of n)
```

**The 1 % gate is achievable today, with margin.** And the residual has a single
identified source: the AIRLOADS strip quadrature integrates to 12928.3 lb
against the FLTLOADS closed-form `lzw` of 12969.2 — a −41.0 lb (−0.32 %)
discretization difference. Nothing else contributes, because the item mass model
closes to W exactly and the CG-referred inertia moment is identically zero by
the definition of the CG.

This is the finding that makes the work worth doing: **the physics is already
consistent to 0.3 %; what is missing is the assembly.**

## 2. Agreed decisions

| # | Decision | Rationale |
|---|---|---|
| B-1 | **The balanced case is owned by the flight condition.** One `BalancedCase` per distinct V-n point referenced by any component's critical condition; today's `W-xx` / `F-xx` / `HT-xx` picks become **views** (a down-select) over that set | Fixes case pairing at its root. The key already exists: `CriticalCondition.case` is the V-n point index (PHAA → case 22), and `CaseRef` carries cg / speed / altitude. Nothing new has to be invented to pair them |
| B-2 | **`weight.items` is the mass SSOT**, with an item→station mapping. `fuselage_mass.stations` becomes derived from it (or validated against it), guarded by `Σw = W` and `Σw·x = W·x_cg` | §1.3. The itemized model already closes exactly; the beam distribution does not derive from it, which is where the 427 lb goes missing |
| B-3 | **Residual closed as 2-DOF mass-proportional inertia relief** — `Δn` on every mass plus `−mᵢ·Δθ̈·(xᵢ−x_cg)` — gated at **\|Δn\|/n < 1 %** and residual moment < 1 % of `n·W·MAC`; over the gate the case **fails** rather than silently absorbing the error | §1.4 says 0.32 % today, so the gate bites on regressions, not on the physics. The pitch term is self-equilibrating in force by construction (`Σmᵢ(xᵢ−x_cg) ≡ 0`), so the two DOF do not fight each other |
| B-4 | **New assembled deck per balanced case**, alongside today's per-component decks; solved in sbeam on a **statically determinate support** with the reactions gated to ≈ 0 | sbeam's SOL 101 has no inertia relief (`SUPORT` is honoured by the SOL 144 trim partition only — verified 2026-08-08). A determinate support carries exactly the residual, so "reactions ≈ 0" *is* the free-free equilibrium proof, through the solver's own assembly |

**Phasing (user, 2026-08-08):** start with the **wing** cases; empennage and
landing/ground cases follow. Phase 1 is therefore **symmetric flight cases**
(PHAA, PLAA, PMAA, NMAA…). The antisymmetric wing cases (`ACRL`, `TORS`) need
distinct left/right loading and a 6-DOF residual, and land in phase 2 with the
empennage.

## 3. What changes, by area

### 3.1 New — `sloads/mass_distribution.py` (the SSOT, B-2)

The single owner that turns `weight.items` into per-component station inertia.

- **Component assignment.** Each item is tagged to a component — `wing`,
  `fuselage`, `htail`, `vtail`, `gear`, `engine` — by an explicit optional
  `component` field on the item, defaulting to inference from `(x, y, z)`
  against the geometry. Explicit beats inferred; inference exists so the five
  existing fixtures need no hand editing to load.
- **Distribution within a component.** Wing items spread over the WINGINER
  spanwise mass distribution (which already tapers root→tip); fuselage items
  lump at their own `x` as beam stations; tail items feed plan 09's
  `TailMassInput` when that lands, and lump at `xt25` until then.
- **Drift guards** (`CLAUDE.md` practice 3 — a structural owner plus a test):
  `Σw = mass_case.weight_lb`; `Σw·x = W·cg_x`; `Σw·z = W·cg_z`; and
  `wing item weight == 2 × wing_mass.panel_weight_lb` — which ga6 already
  satisfies exactly (330 = 2 × 165), so the tie is real and worth locking.
- **`fuselage_mass.stations` becomes derived.** Keep the input for backward
  compatibility, but validate it against the derived distribution and surface
  the difference. **ga6 will fail this validator by 427 lb on day one** — that
  is the intended outcome, not a surprise; it is the fixture that is wrong.

### 3.2 New — `sloads/modules/balance.py` and the `BalancedCase` result (B-1)

For each distinct V-n point referenced by any component's `CriticalCondition`:

1. **Assemble the applied aero set** — wing strips (both sides; mirrored for
   symmetric cases), the tail load at `xt25`/`xt50`, control-surface increments
   where the case names them.
2. **Assemble the inertia set** from §3.1 at that point's `nz` (plus `θ̈` once
   M4-21 lands; `θ̈ = 0` on balanced trim points, so phase 1 is unaffected).
3. **Compute the residual** `(ΣFz, ΣFx, ΣMy about the CG)`.
4. **Close it** with `Δn` and `Δθ̈` (B-3), and record both the pre-closure
   residual and the closure magnitudes on the result — the numbers are the
   deliverable's own honesty statement, not internal scratch.

`BalancedCaseResult` carries the case identity (reusing `CaseRef`), the V-n
point, the per-component load sets, the pre-closure residual and the applied
`Δn`/`Δθ̈`.

### 3.3 Changed — the seam rule, which is also plan 09's T-11 answer (§4)

### 3.4 Changed — `body_loads`

`BodyLoadResult` gains `nz` (plan 07 §9 names its absence as a blocker) and a
link to its V-n point. Its own free-free closure is unchanged and stays
oracle-neutral; what changes is that the assembled case does **not** consume its
`carry` reaction (§4).

### 3.5 New — the assembled export

One deck per balanced case: GRIDs for both wings, the fuselage and the
empennage; `FORCE`/`MOMENT` for every applied load; a determinate support; and
a `$` header stating the case's condition, its residual and its `Δn`. Needs a
**left/right wing GID band** — today's wing band (2…N) is a single half-span —
folded into plan 07 step 3's disjointness guard.

## 4. The double-count authority table (answers plan 09 decision T-11)

In an assembled free-free model every load is either **external** (applied) or
**internal** (recovered by the solver). Today's per-component decks each take a
free-body cut and carry the cut reaction as an applied load; those reactions
must **not** appear in the assembled deck. Stated once, as the rule:

| Physical load | Per-component deck | Assembled deck |
|---|---|---|
| Wing air load | wing strips, centerline→tip, one side | wing strips, **both sides** — authoritative |
| Wing inertia | inside the wing net | from `weight.items` wing item, spread by WINGINER — authoritative |
| Wing carry-through reaction | `body_loads` `carry` source — applied | **excluded** — it is internal (the solver recovers it) |
| Fuselage inertia | `fuselage_mass.stations` × `nz` | from `weight.items`, per §3.1 — authoritative |
| Tail air load | `body_loads` `tail` point load **and** TAILDIST chordwise | the **distributed empennage** representation once plan 09 lands; the `body_loads` point load is **excluded**. Until then, the point load is authoritative and the chordwise deck is a per-component view |
| Gear reactions | — | applied external loads on ground cases (M4-6) |

The rule in one sentence, for `CONVENTIONS.md`: **a load that a free-body cut
introduces is never applied in the assembled model.**

## 5. Steps

| Step | Scope | Tier | Effort |
|---|---|---|---|
| **B1** | `mass_distribution.py` + item `component` tagging + the four drift guards + `fuselage_mass` reconciliation validator. Fixture mass models corrected (ga6's 427 lb). Schema bump + migration. | L | M (~1 session) |
| **B2** | `BalancedCase` model, `balance.py`, the per-condition assembly and the 2-DOF residual closure. **Symmetric wing cases only.** | L | M–L (~1.5) |
| **B3** | The §4 seam rule made structural: an authority function the assembled path consumes, plus a guard test that the `carry` source never reaches an assembled deck. | M | S (~0.5) |
| **B4** | CI gates: residual < 1 %, `Δn`/n < 1 %, per-component decks and Appendix A **bit-unchanged**. | M | S (~0.5) |
| **B5** | Assembled deck export + left/right GID bands + determinate support; solves in sbeam with reactions ≈ 0 (rides on plan 10's harness). | L | M (~1) |
| **B6** | Streamlit view: the balanced case list with its residual and `Δn` columns — the number an engineer needs to trust the case. | M | S–M (~0.5) |
| **B7** | Antisymmetric cases (`ACRL`, `TORS`): distinct left/right loading, 6-DOF residual. **Phase 2.** | L | M–L (~1.5) |
| **B8** | Empennage cases (needs plan 09) and landing/ground cases (needs M4-6: gear reactions as applied loads — the gear items are already in `weight.items` at x = 97 and x = 1). **Phase 3.** | L | L |
| **B9** | Tier-L closure trail: `CONVENTIONS.md` (§4 rule + the balanced-case concept), `PROGRAM_SPEC.md`, `theory_sources.md` (the closure gate as oracle substitute), `PROJECT_GUIDE.md`, `DATA_DICTIONARY.md` regen, CHANGELOG, history. | S | S (~0.5) |

Phase 1 = B1–B6.

## 6. Acceptance

1. Every balanced case satisfies `|ΣF|/(n·W) < 1 %` and `|ΣM_cg|/(n·W·MAC) < 1 %`
   **before** residual closure, on all fixtures — the gate is on the physics,
   not on the correction.
2. `|Δn|/n < 1 %` after closure; the value is recorded on the result and shown
   in the UI and the deck header.
3. The mass drift guards hold on every fixture: `Σw = W`, `Σw·x = W·x_cg`,
   `Σw·z = W·z_cg`, wing item = 2 × panel weight.
4. The assembled deck solves in sbeam with determinate-support reactions ≈ 0 at
   the plan 07 §4.1 zero-target tolerance.
5. **Appendix A oracles bit-unchanged, and every per-component deck
   byte-unchanged.** This work is additive; if a digest moves, something leaked.
6. No `carry`-source load appears in any assembled deck (B3's guard).
7. `ruff` clean, `pytest` green on 3.9 / 3.11 / 3.12.

## 7. Risks and open technical questions

| # | Item | Notes |
|---|---|---|
| R1 | **Where does `m_wf` go?** The trim solve carries a wing+fuselage aero pitching moment (26,355 lb-in at case 22). The wing's own section `Cm` is already in the strip torsion (`Trq = ΣML`); the *fuselage* Munk term has no distributed carrier until **M4-19**. Applying it twice, or not at all, lands directly in the moment residual | **The one genuine unknown in this plan.** §1.4 measured the force residual (0.32 %); the moment residual cannot be quoted until this is decided. Resolve it in B2 before writing the gate, and expect M4-19 to pair |
| R2 | ga6's `fuselage_mass` fails the new validator by 427 lb | Intended. The fixture is corrected in B1; the FAR23 oracles do not read `fuselage_mass`, so Appendix A is unaffected — **verify that claim explicitly in B1**, do not assume it |
| R3 | Strip-quadrature vs closed-form lift (−41 lb) sets a floor on achievable residual | 0.32 % against a 1 % gate is comfortable, but a fixture with coarser `elements` will do worse. Consider scaling the gate with element count, or state the floor per fixture |
| R4 | Antisymmetric cases need both wings loaded differently and a 6-DOF residual | Deferred to B7 by the phasing decision; B2's data structures should not assume symmetry even though phase 1 only exercises it |
| R5 | Scope creep into L-1 (real stiffness) | The assembled deck here uses the same placeholder properties as today's stick model. Reactions on a determinate support are stiffness-independent, so the gate is valid without real sections; L-1 improves the deck, not the check |
| R6 | `BalancedCase` becoming a second, competing case-identity system | It reuses `CaseRef` and `case_ids.py` — no new ID series (`CLAUDE.md` naming rule). Component cases become views over balanced cases, not parallel objects |

## 8. Effort

**L, phased.** Phase 1 (B1–B6) ≈ 4–5 sessions. Phase 2 (B7) ≈ 1.5. Phase 3 (B8)
depends on plan 09 and M4-6 landing first. Recommended on a feature branch with
a merge at each phase boundary, for the same reasons plan 09 gives.

## 9. What this supersedes

Plan 07 §9 ("Assembled-airframe n·W closure for symmetric cases") recommended
filing exactly this as its own `[E]` item. **This plan is that item** — filed
with the decisions answered and the baseline measured, so it should be entered
in `00_backlog.md` under that name pointing here, rather than as a second entry.
