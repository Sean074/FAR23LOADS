# Design note — Distributed empennage loads → sbeam FORCE/MOMENT export

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status:** assessment + step-by-step development guide; decisions T-1…T-7 taken
2026-08-08 (user), **T-8…T-11 taken 2026-08-08** in the development-plan review
(they supersede the T-3 inertia wording and the §3.1/§4 half-vs-full
bookkeeping). **PHASE 1 SHIPPED 2026-08-08** — T1–T5 complete (mission step 7).
**PHASE 2 SHIPPED 2026-08-13 — T6–T8 complete (mission step 9); the plan is
CLOSED** (see §9 for what shipped and where measurement changed the plan, §10
for the phase-2 design record; the closure trail is in the history file and the
`[Unreleased]` changelog).
Decision T-11's gate was **satisfied as of 2026-08-08** -- the plan-07 equilibrium invariant (step 1) and the sbeam
round-trip harness (step 2) have both landed, so this item is unblocked. T4 adds
its deck family to **both** gates: two rows in the plan-07 §4 invariant table and
a tail leg in `tests/test_sbeam_roundtrip.py` (whose wrapper already solves the
chordwise tail deck, and whose `groups` argument exists because the h-tail and
v-tail are separate beams -- the spanwise decks will need the same treatment). **Closure tier: L** (new physics, new
result slices, schema/contract change — full trail per the CLAUDE.md tier table).

Conventions cited throughout:
[`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md) (§1 axes/signs,
§2 units channels, §3 LIMIT→ULTIMATE contract, §4 case identity, §6 rule R10
benchmark-first, §7 single-source owners). Deck contract:
[`../10_standard/PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md) sbeam-bridge
section. Sibling design note this plan extends:
[`07_export_equilibrium_invariant_plan.md`](07_export_equilibrium_invariant_plan.md)
(the spanwise tail decks must satisfy the same §4 invariant table on day one).

---

## 1. Objective

Give the empennage the same deliverable the wing already has: per-station
distributed ULTIMATE loads on a user-defined load reference axis (LRA), exported
as `GRID` + `FORCE` + `MOMENT` bulk-data cards that close in force **and**
moment from their own card text.

Today the tail path stops short of that in every dimension:

| Capability | Wing today | Empennage today |
|---|---|---|
| Planform geometry (LE/TE lines, taper, sweep) | `SurfaceInput` polylines | none — scalar areas/spans only (`TailLoadsInput`, `VTailLoadsInput`) |
| Spanwise distribution | Schrenk / AIRLOAD4 strips (`airloads.py`) | **none** — `taildist.py` is chordwise-only, on the average chord |
| Station count | user-set `SurfaceInput.elements` | fixed 5 chordwise pressure stations |
| LRA | `SurfaceInput.ref_axis_pct`, transfer at export boundary (`net_loads.to_loads_ref_axis`) | no LRA concept |
| Surface mass / inertia relief | `WingMassInput` + `wing_inertia.py` | no tail mass slice; empennage mass implicit in aft fuselage stations |
| Deck | `GRID`+`FORCE`+`MOMENT`, root-clamped stick model | `FORCE` cards only, **no `GRID`, no `MOMENT`** (gap G3 of plan 07) |
| Control-surface load path | aileron/flap simplified distributions | areas only; no hinge line station, no actuator, no hinge-moment output |
| T-tail | — | `TailType.T_TAIL` exists but drives **only the three-view sketch** (`configuration.py`); no load-path consequence |

The chordwise TAILDIST path and the SELECT totals (`LT25`/`LT50`, v-tail side
loads) are Appendix-A oracle-locked and are **inputs to** this feature, never
modified by it.

## 2. Decisions of record (user, 2026-08-08)

| # | Decision | Rationale |
|---|---|---|
| T-1 | **Geometry: reuse `SurfaceInput`.** `"htail"` and `"vtail"` become entries in `geometry.surfaces` — same LE/TE polylines, `elements` (the user-set load-reporting station count), `ref_axis_pct` (the LRA) as the wing | Maximum pipeline reuse: the strip integrator, LRA transfer, and §7 drift guards work unchanged; the existing scalar areas/spans become validated derived quantities |
| T-2 | **Spanwise shape: proportional to local chord** for both the `LT25` (α) and `LT50` (camber/control) parts, and for the v-tail side load | Simple, one integrator, conservative-ish inboard; no Schrenk machinery needed on the tail. Chordwise placement stays exactly TAILDIST's: `LT25` acts at 25 % chord, `LT50` at 50 % chord — so strip torsion about the LRA is closed-form (§5, step T2) |
| T-3 *(weight source revised 2026-08-10: the surface weight is **derived from the `htail`/`vtail`-tagged `weight.items`** via `mass_distribution.tail_surface_weight`, not entered — `panel_weight_lb` is an explicit override. The uniform-area-density distribution itself is unchanged.)* | **Mass: evenly distributed** — uniform area density over the defined planform, total from a new per-surface tail mass input; inertia load per case = load factor × distributed weight, opposing the air load (wing sign convention) | User requirement ("evenly distributed into the defined geometry"). Deliberately simpler than the wing's tapered-density model; upgrade path noted in §8 |
| T-4 | **Control surfaces: both options, distributed first.** Phase 1 ships option 2 (control-surface load smeared into the parent-surface distribution — no new geometry). Phase 2 ships option 1 (user defines hinge + actuator spanwise locations; control load enters the parent surface as discrete point loads at those stations). A per-project mode setting selects | Phase 1 needs zero new geometry and unblocks the deck; phase 2 is the structurally correct localization and needs the hinge/actuator schema |
| T-5 | **T-tail: concurrent balancing + inertia.** For each vertical-tail case, the horizontal-tail loads concurrent with that flight condition — the balancing tail load `LT` at that case's speed/`n` (from `flight_envelope`/`envelope.vn`) plus h-tail mass inertia — are transferred to the fin-tip station as force + moment cards | Rational pairing, one deck per VT case; the conservative superposed-critical-HT pairing is recorded in §8 as a possible later policy option |
| T-6 | **Stations:** load reporting stations = `SurfaceInput.elements` mid-strip stations (uniform strips, root→tip), exactly the wing pattern; user-set, validated ≥ 2 | User requirement; identical semantics to the wing keeps `interp_x`/tributary logic shared |
| T-7 | **Oracle lock:** `taildist.py` chordwise pressures, `select.py` totals, and every Appendix-A figure are unchanged; the spanwise path is a pure consumer of their outputs (concept-mode superset rule, plan 01 §1) | CLAUDE.md invariant |
| T-8 | **H-tail bookkeeping: full-span deck through the centreline.** The h-tail beam runs tip→tip as one member; strips cover the full planform and `LT25`/`LT50` enter as the both-sides totals SELECT already produces. The deck is supported at the **fuselage attachment stations** (not root-clamped like the wing), and the carry-through between them is modelled explicitly | Keeps SELECT/TAILDIST's full-surface, full-load bookkeeping end-to-end with no factor-of-two seam, and is the only topology that can carry the 23.427(a) left/right asymmetry (T-10) in a single deck. Cost, accepted: a beam topology the wing pipeline has no analogue for — the attachment/support nodes must be defined in T2 before T4's invariant can close |
| T-9 | **Inertia sign: always `−n·W_ht` (d'Alembert), never "opposing the air load."** The inertia direction is set by the case's load factor alone — relieving on up-load cases, **additive** on down-load cases | The governing GA6 h-tail conditions are down-load (DN UNCHECKED ≈ −1400 lb); a magnitude-opposing rule would relieve exactly those and be unconservative. Supersedes the "opposing the air load" wording in T-3 |
| T-10 | **23.427(a) UNSYMMETRICAL: per-side scaled distribution in phase 1.** Each side carries the same chord-proportional shape scaled by its own share — RH `0.5·total`, LH `pc%·RH` with `pc = min(100 − 10(n−1), 80)`, exactly `select_htail_unsymmetrical`'s split, read never recomputed | A chord-proportional *symmetric* shape cannot represent a named FAR condition; with the T-8 full-span deck this is one scale factor per side, and it is the only h-tail case that produces a net rolling/yawing input to the fuselage — worth having on day one |
| T-11 | **Sequencing: the plan-07 equilibrium invariant and the sbeam round-trip CI harness land first.** T4's acceptance is "add two rows to the plan-07 §4 invariant table", not "author the checker" | Avoids coupling two `[E]` items, and gives the tail double-count question its proper home: `body_loads` already carries the tail air load as a point station (GID 1001 band), so the export boundary — not a tail step — must declare which tail representation is authoritative in a combined-airframe sum |

**Axes note (CONVENTIONS §1, becomes a convention at closure):** the h-tail maps
exactly like the wing (span along `y`, air load `fz`, torsion `myy` about the
LRA). The **v-tail spans along `z` and its air load is the side force `fy`**;
strip math runs in a local (span, chord) frame identical to the wing's, and the
local→airplane mapping (span→`z`, normal-force→`fy`, torsion about the LRA →
`myy`… ) is owned by `export/coordinates.py` — the §7 single edit point — with a
drift-guard test, never hand-mapped per call site.

## 3. Schema additions (one `SCHEMA_VERSION` bump for the phase-1 set)

All round-trip through `io.py`; older files still load (absent slices → feature
off); `DATA_DICTIONARY.md` regenerated via its generator.

1. **`geometry.surfaces` gains `"htail"` / `"vtail"` `SurfaceInput` entries**
   (T-1). Validation: when present alongside the scalar slices, planform area
   must agree with `htail_area_sqft` / `vtail_area_sqft` and span with
   `htail_semispan_in` / `vtail_span_in` within 1 % — a loud `ValueError`, not a
   silent preference. The scalars stay authoritative for the oracle-locked
   modules; the polylines are authoritative for strips.
   **Half/full bookkeeping (T-8), stated once so the validator cannot get it
   wrong:** `SurfaceInput` polylines are defined on **one side** for a
   `symmetric=True` surface, so the h-tail comparison is
   `2 × polyline_area ↔ htail_area_sqft` and `polyline_semispan ↔
   htail_semispan_in`. The v-tail is a single-sided surface: `polyline_area ↔
   vtail_area_sqft`, `polyline_span ↔ vtail_span_in`, no factor. The full-span
   h-tail *deck* of T-8 is built by mirroring the semispan polyline about the
   centreline at strip-generation time — one geometry input, two half-planforms,
   one beam.
2. **`TailMassInput`** (one per surface, mirroring `WingMassInput`'s position in
   `Project`): `surface: str` (`"htail"`/`"vtail"`), `panel_weight_lb: float`.
   Uniform density per T-3 — no taper ratio, no concentrated list in phase 1.
3. **Control-surface attachment** (phase 2 only, T-4): per control surface
   (elevator, rudder), `hinges_span_in: List[float]` (≥ 2 hinge stations,
   measured along the surface span axis) and `actuator_span_in: float`.
4. **`control_load_mode: "smeared" | "discrete"`** (default `"smeared"`), the
   T-4 selector. `"discrete"` without attachment geometry is a `ValueError`.
   **Per surface, with a project-level default** — an elevator may have hinge
   geometry entered while the rudder does not, and a project-wide flag would
   force the whole empennage back to `"smeared"` for the missing one.
5. **New `LoadsResult` slices:** `htail_span` / `vtail_span` —
   lists of per-case spanwise results reusing the `WingStationLoad` station
   shape (`x, y, z, fx, fz, sx, sz, mxx, myy, mzz` — the fields are already
   surface-generic; the station's span coordinate is stored in `y` in the local
   frame, mapped at export per §2's axes note). Each result carries the **same
   `CaseRef` as its source SELECT condition** (§4 case identity: one ID per
   physical condition — the spanwise result is a new *view* of an existing
   `HT-xx`/`VT-xx` case, never a new case ID).

## 4. Physics, stated before code (required practice 1)

Per strip `j` at span station `y_j`, chord `c_j`, strip width `Δy`, **full
planform area `S`** (both sides for the h-tail, per T-8), for a case with
totals `LT25`, `LT50` (limit, both-sides as SELECT produces them):

```
k_side = 1                                  # symmetric cases, both sides
       = per-side share (T-10)              # 23.427(a): RH 1.0, LH pc/100
w25_j  = k_side · LT25 · (c_j·Δy)/S         # chord-proportional (T-2)
w50_j  = k_side · LT50 · (c_j·Δy)/S
fz_j   = w25_j + w50_j                                          # strip air load
myy_j  = w25_j·(x_lra_j − x_25_j) + w50_j·(x_lra_j − x_50_j)    # strip torsion about the LRA
fzin_j = −n_case · W_surf · (c_j·Δy)/S      # T-3 uniform-area mass; sign is d'Alembert (T-9),
                                            # independent of the air-load sign
```

For the symmetric cases `k_side = 1` on both halves and the two halves sum to
the SELECT total exactly; for 23.427(a) the halves sum to `RH + LH`, which is
the condition's own reported total — so the closure below holds unchanged in
both. Cumulative shear/bending/torsion integrate **tip→root on each half**
exactly as `airloads.py` does (`sz`, `mxx`, `myy` running sums), so the export
bridge's increments-of-cumulative recovery (`dFz[i] = sz[i]−sz[i+1]`)
telescopes identically; the two halves meet at the centreline station, where
the carry-through and the fuselage-attachment supports (T-8) live. The v-tail
runs the same equations in its local frame with the side load as the normal
force, single-sided and root-supported at the fuselage.

Because the distribution is chord-proportional, the targets are **closed-form**
and serve as the R10 gates (no printed oracle exists for a spanwise tail
distribution). Per half-planform, with `L_half = k_side·(LT25 + LT50)`:

- **Force closure:** Σ strip `fz` over the whole deck = `LT25 + LT50` exactly
  (telescoping sum); per half = `L_half`.
- **Bending closure:** each half's attachment-station `mxx = L_half · ȳ_A`,
  where `ȳ_A` is the area centroid of the half planform — analytic for a
  trapezoid: `ȳ_A = (b/3)·(c_r + 2c_t)/(c_r + c_t)`. An independent
  hand-derived target, not a re-run of the quadrature.
- **Centreline rolling closure (T-8 + T-10):** net moment about the centreline
  = `(L_RH − L_LH)·ȳ_A` — **identically zero for every symmetric case**, and
  the asymmetry moment for 23.427(a). This is the gate the full-span topology
  buys, and the one a per-side deck could not state.
- **Torsion closure:** `myy = (LT25+LT50)·x̄_lra − LT25·x̄_25 − LT50·x̄_50`
  with the `x̄` values area-weighted means — again closed-form for straight-line
  LE/TE.
- **Inertia closure:** Σ inertia strip loads = `−n_case · W_surf` exactly,
  **signed by `n_case` alone** (T-9); a companion test asserts the down-load
  cases come out larger in magnitude than air-load-only, which is what pins the
  sign convention against regression.
- **Reduction:** with `ref_axis_pct = 0.25` the `LT25` torsion term vanishes
  identically (LRA-transfer identity, same property the wing tests pin).

## 5. Step-by-step development guide

Each step lands green (`ruff` + `pytest` 3.9/3.11/3.12) with its gate written
**with** the feature (R10), and does not start until the previous one is merged.

### ~~T1~~ ✅ — Geometry + schema (Tier M within the phase)

`geometry.surfaces` htail/vtail entries + the 1 % consistency validator +
`TailMassInput` + the `LoadsResult` slices + `SCHEMA_VERSION` bump + `io.py`
round-trip + dictionary regen. GUI: the existing geometry page grows the two
surfaces (reuse the wing's `SurfaceInput` editor). **Gate:** round-trip test
(new → JSON → load → equal); validator fires on a deliberately inconsistent
fixture; all existing fixtures load unchanged.

### ~~T2~~ ✅ — Spanwise distribution module `sloads/modules/tail_span.py`

New concept-mode module (`run(project) -> ModuleResult`, self-registers; module
contract per CLAUDE.md). Consumes: `envelope.critical` (`HT-xx`/`VT-xx`
conditions with their `LT25`/`LT50` / side-load splits — read, never
recomputed), the T1 planforms, `TailMassInput`, and each case's load factor
(from the condition's V-n point; documented fallback `n = 1.0` where the source
condition carries none, e.g. yaw cases). Emits the §3.5 slices, LIMIT, with
`safety_factor` carried per case and the torsion axis label stamped
(`"LRA 42% chord"` — every torsion names its axis). Builds the **full-span**
h-tail station set by mirroring the semispan planform (T-8) and defines the
**fuselage-attachment support stations** the deck is reacted at — these must
exist here, not be improvised in T4, or the invariant has nothing to close
against. `select_htail_unsymmetrical`'s RH/LH split is read for `k_side`
(T-10), never recomputed. Inertia sign is `−n_case` unconditionally (T-9).
**Phase-1 scope note:** v-tail *inertia* loads are omitted (no lateral load
factor exists in the case data) — documented in-band, revisit in §8.
**Gate:** the §4 closures as `tests/test_tail_span.py` — including the
centreline rolling closure (zero for every symmetric case, the asymmetry
moment for 23.427(a)) and the down-load inertia-sign test — each with the
hand-derived number and its derivation in the test docstring.

### ~~T3~~ ✅ — UI + CSV reporting

New Streamlit view (registered in `workflow.py` — the nav SSOT, drift-guarded)
showing per-station tables/plots per case; LIMIT display allowed per the
CLAUDE.md carve-out, downloads unit-suffixed (lesson L-8i). **Gate:** workflow
drift guard passes; smoke test renders the page for both concept fixtures.

### ~~T4~~ ✅ — Export: spanwise tail decks (`GRID` + `FORCE` + `MOMENT`)

Extend `sbeam_bridge.py` with `htail_span_*` / `vtail_span_*` writers on the
wing pattern: `GRID` cards on the LRA line (v-tail grids mapped span→`z` via
`coordinates.py`, §2 axes note), `FORCE`/`MOMENT` increments of the cumulative
table, `_sf()` applied once at the boundary, SIDs =
`case_ids.subcase_id(case_id)` (same SUBCASE as the chordwise deck of the same
case — separate files, same identity), `$` subcase-map + axes/units header. New
GID bands (proposal: htail-span 4001+, vtail-span 4501+) added to the
disjointness drift guard of plan 07 step 3. The h-tail deck is SPC'd at the
T2 fuselage-attachment stations (full-span topology, T-8), not at a single
root node. **Gate:** the plan-07 §4 invariant table gains two rows — spanwise
tail decks assert `ΣF = sf·(LT25+LT50)` (or side-load total), `ΣM` about the
attachment stations `= sf·mxx` there, torsion `= sf·myy`, and `ΣM` about the
centreline `= 0` for symmetric cases — swept across all fixtures × both unit
systems in `test_export_equilibrium.py` (**which T-11 requires to already
exist**). Also state, in the deck `$` header and the plan-07 checker, that the
spanwise tail deck **supersedes** `body_loads`' point tail-load station for any
combined-airframe sum — the double-count rule, written down once.
Imperial digest regeneration, once, deliberately, with its own CHANGELOG line.

### ~~T5~~ ✅ — Control surfaces, option 2 (smeared) — completes phase 1

`control_load_mode = "smeared"`: the `LT50`/control part is already inside the
T2 distribution, so this step is mostly *labelling and proof*: the deck states
the mode in its `$` header, and the mode plumbing exists so T6 can add
`"discrete"`. **Gate:** mode stated in header; smeared results bit-identical to
T2 output.

### T6 — Control surfaces, option 1 (discrete hinge/actuator) — phase 2

Schema item §3.3/§3.4. In `"discrete"` mode the control part (`LT50` for the
elevator, the rudder share for the fin) is removed from the smeared strips and
re-enters the parent surface as point loads: air load on the control surface →
hinge reactions by tributary span between hinge stations, plus the actuator
load reacting the hinge moment (hinge moment from the TAILDIST aft-of-hinge
pressure block — the first hinge-moment output in the suite). Point loads land
on dedicated `GRID`s at the hinge/actuator span stations on the LRA. **Gates:**
ΣF identical between modes (exact); Σ hinge+actuator loads = control-surface
total; root torsion consistency between modes within a stated tolerance, with
the difference (load localization) printed in the test as the physical
explanation; smeared mode remains bit-identical (mode isolation).

### T7 — T-tail load transfer

Gated on `layout.tail_type == TailType.T_TAIL` (first load-path consumer of the
enum). For each VT case: resolve the concurrent h-tail load per T-5 (balancing
`LT` at the case's speed/`n` + h-tail inertia `−n·W_ht`), then transfer the
h-tail root reaction set to the **fin-tip station** (the last v-tail `GRID`, no
new node): `FORCE` (vertical load — axial to the fin) + `MOMENT` cards for the
lever-arm terms (fore-aft offset `x_ht_lra − x_vt_tip_lra` × vertical load →
`myy`; h-tail weight/air offsets likewise). The deck `$` header states the
pairing policy (T-5) and the transferred resultant. **Gate:** deck-derived fin
resultants (plan-07 checker) equal the VT-only resultants **plus** the stated
transferred set exactly; with `tail_type` conventional the deck is bit-identical
to T4 output (gating isolation); equilibrium invariant still passes on the
combined deck.

### T8 — Closure (Tier L)

`CHANGELOG.md`; backlog item removed; **full step format** in
`docs/40_history/00_completed_development.md`; `PROGRAM_SPEC.md` (module +
deck contract rows); `PROJECT_GUIDE.md` schema section;
**`CONVENTIONS.md`**: the v-tail span-axis mapping (§2 axes note) and the
T-tail transfer reference point — they are conventions, and conventions live
there; `theory_sources.md`: the §4 closure gates recorded as the oracle
substitute (R10); `cspell.json` for new terms.

## 6. Acceptance (whole feature)

1. All §4 closures pass in CI for both concept fixtures; Appendix A oracles and
   the chordwise TAILDIST path bit-unchanged throughout (T-7).
2. Spanwise h-tail and v-tail decks satisfy the plan-07 equilibrium invariant
   (force **and** moment, both unit systems, from their own card text),
   including the centreline rolling closure — zero for every symmetric case,
   the stated asymmetry moment for 23.427(a).
3. Control-surface mode `"discrete"` vs `"smeared"`: ΣF exact-equal, hinge set
   sums to the control total, smeared path bit-stable.
4. T-tail: transfer closure per T7's gate; conventional-tail decks unaffected.
5. GID bands disjoint across every fixture; workflow drift guard green.
6. `ruff` clean; `pytest` green 3.9/3.11/3.12; Imperial digests regenerated
   exactly once per byte-changing step.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Scalar-vs-polyline geometry drift (two representations of tail area/span) | The 1 % T1 validator is loud; scalars stay oracle-authoritative; backlog M4-3(a) (v-tail geometry provenance) is subsumed here — close or re-scope it at T1 |
| V-tail axis mapping hand-rolled at a call site | `coordinates.py` single owner + drift guard, written in T2/T4, per CONVENTIONS §7 |
| `n` for tail inertia not defined for every case | Explicit per-case source table in T2's design review; documented `1.0` fallback, printed in-band |
| T-tail concurrency assumption challenged later | T-5 pairing stated in the deck header; conservative superposed policy pre-scoped in §8 |
| Chord-proportional shape questioned vs Schrenk | Recorded as decision T-2 with rationale; upgrading the shape later changes only the `w_j` line in §4 — closures re-derive |
| **Full-span h-tail is a new beam topology** (T-8): fuselage-attachment supports have no wing analogue, and getting them wrong makes the T4 invariant unclosable | Attachment stations are defined and gated in **T2**, before any deck exists; the centreline rolling closure is the specific test that catches a mis-placed support |
| **Double-count with `body_loads`' point tail-load station** (GID 1001 band) in a combined-airframe sum | T-11: the plan-07 checker declares the authoritative tail representation; T4 restates it in the deck `$` header. Do not defer this to L-1's assembled-airframe export |
| Half/full (both-sides) bookkeeping seam between SELECT/TAILDIST totals and semispan polylines | Stated once in §3.1 and used everywhere from there; the T1 validator is the drift guard, and T-8's full-span deck removes the factor-of-two entirely from the strip math |
| **T6 hinge moment is new physics with no printed oracle** | R10 substitute: Σ(hinge + actuator) = control-surface total exactly, and cross-mode ΣF identity; the hinge moment itself is derived from the oracle-locked TAILDIST aft-of-hinge pressure block, so it inherits that provenance |

## 8. Deliberately out of scope (candidate backlog items on completion)

- Schrenk (or other rational) spanwise shape for tails — T-2 upgrade path.
- V-tail lateral inertia (needs a lateral load factor in the case data).
- Tapered/concentrated tail mass (upgrade `TailMassInput` toward
  `WingMassInput` parity).
- Conservative superposed-critical-HT T-tail pairing as a selectable policy.
- Gust-specific tail spanwise shape (pairs with the existing `[V]` gust
  spanwise-distribution decision).
- Hinge-moment deliverable as a reported load case in its own right (T6 emits
  the number; reporting it as a case is a separate step).


## 9. Phase 1 as shipped (2026-08-08) — T1–T5

Delivered: `sloads/tail_geometry.py` (planform resolution + the 1 % validator),
`sloads/modules/tail_span.py`, the `htail`/`vtail` axis map in
`export/coordinates.py`, the `tail_span_*` writers and GID bands 4001+/4501+ in
`sbeam_bridge.py`, the **Tail Span Loads** page, `Project.tail_mass` +
`LoadsResult.htail_span`/`.vtail_span` + `WingStationLoad.myy_free`
(`SCHEMA_VERSION` 42, additive, no hop), `cli.py --export-target
htail-span|vtail-span`, and three test modules (`test_tail_geometry.py`,
`test_tail_span.py`, plus new rows in `test_export_equilibrium.py` and
`test_sbeam_roundtrip.py`).

**Appendix A and the chordwise TAILDIST path are bit-unchanged** (T-7 held):
every Imperial digest change is a **new channel**, verified channel-by-channel —
no existing artifact moved.

### 9.1 Where measurement changed the plan

**1. No fixture carries a tail planform, so one is derived and marked.** §3.1
assumed `geometry.surfaces` would gain `htail`/`vtail` entries; none of the six
shipped airplanes has one, and inventing polylines for six aircraft with no
oracle would have been fabricated data. `tail_geometry` therefore **derives a
rectangular planform** from the oracle-authoritative area/span — precisely the
first-order derivation `configuration.tail_planform` already uses for the
three-view — and sets `assumed=True`, which travels into the result, the page,
the CSV and the deck header. Entered polylines still win and are still validated
to 1 %. Quantified in-band: `ybar` for the rectangle is `b/2` against `(b/3)(c_r
+ 2c_t)/(c_r + c_t)` for a taper, so a derived planform is **conservative in root
bending** but its station distribution is not the surface's own. The gates run
against a tapered *and swept* planform too, so the closures are not properties of
the rectangle.

**2. The fin's torsion is `Mzz`, not `Myy`.** §2's axes note says the v-tail's
span maps to `z` and its load to `fy`, and stops there. A surface's torsion is
about its **span** axis, so the fin's is about `z` — and the sign is the stored
value **negated**, because `r x F` with a side force reverses. Derived in
`coordinates.tail_torsion_to_airplane` with the derivation written down, because
the h-tail writer's sign copy-pasted onto the fin gives a deck that parses,
solves, and twists the fin the wrong way. The v-tail invariant row asserts
`Myy == 0` on the fin deck for exactly this reason.

**3. The determinate support was implicitly x-axis-only.** The round-trip
harness's `Support.DETERMINATE` constrained `1234` + `23`, which restrains
rotation about **x**. The h-tail spanwise deck is the first beam in the suite to
run along **y**, and it came back *exactly singular*: the model was free to spin
about its own axis. Fixed in `roundtrip._determinate_components`, which picks the
axial-rotation DOF from the beam's direction. A latent defect in step 2's
machinery, found by step 7 — and it could only be found by a beam that was not
along `x`.

**4. `WingStationLoad` gained `myy_free`.** The spanwise deck applies strip loads
directly rather than differencing a cumulative column (which is what smears a
concentrated wing mass inboard in the wing bridge), so it needs the per-strip
free torsion. The cumulative `myy` is **not** that — it carries the sweep
transfer, the same distinction plan 11 had to make for the wing, where
`balance._free_moments` reconstructs it. Populated by `tail_span`; left `0.0` by
the oracle-locked wing chain.

**5. The h-tail attachment stations fall back to the centreline pair.**
**Closed 2026-08-15 by T-8a** for the three real types, which gained published
fuselage outlines; the two synthetic fixtures still read as below. At the time:
`geometry.parametric.fuselage_width` was `None` on every fixture, so T-8's
"supported at the fuselage sides" had no data. The attachments become the
innermost strip pair, stated on the result rather than chosen silently; the
consequence (a one-strip-wide carry-through, so attachment bending is slightly
high) is the same direction as the wing's centreline-clamp limitation and is
filed alongside it.

### 9.2 Scope deliberately left for later

* **V-tail inertia** — omitted, because the suite has **no lateral load factor**
  and applying the airplane's normal `n` to a fin's mass is a fabricated load in
  the wrong direction. Stated on every v-tail result. Lands with plan 11 **B8a**,
  which is where a lateral load factor first has to exist.
* **T6** (discrete hinge/actuator) and **T7** (T-tail transfer) — shipped
  2026-08-13 as mission step 9, to §10's design record. (This bullet originally
  read "unstarted"; the phase-1 plumbing — `control_load_mode` with `"discrete"`
  raising rather than falling back — is what T6 landed on.)
* **T8** — the Tier-L closure trail: done for phase 1 in its session, and for
  phase 2 at the 2026-08-13 step-9 closure.

---

## 10. Phase 2 design note — T6 + T7 (agreed 2026-08-13, user)

Required practice 1: theory reference, `CONVENTIONS.md` citations, closure
targets with their expected numbers, and acceptance tolerances, agreed before
implementation. §5's T6/T7 sections stated *what* ships; this section states the
physics, and it supersedes them where the two differ (T-12 is such a place).

### 10.1 Decisions of record

| # | Decision | Rationale |
|---|---|---|
| T-12 | **The control-surface load is SELECT's, read never recomputed.** `select.elevator_load` (SELECT.BAS 5216-5218: `(SEFWDHL + 0.5·SEAFTHL)·LT50/(ST − SEAFTHL)` + the AoA share) and the rudder equivalent already inside `select_vtail` are the producers. They are decomposed into their **(camber, AoA) parts** by part-returning helpers in `select.py` whose sum is bit-identical to today's expression, so the two smeared parts can be de-scaled at their own chord stations. Where a condition carries no such value the load is **derived** from the TAILDIST aft-of-hinge pressure block and marked | Supersedes T6's "the control part (LT50)". `LT50` is the *camber* load and its TAILDIST trapezoid runs leading edge to trailing edge — it is not the load on the control surface, and hanging all of it on the hinges would move stabilizer load onto the elevator while ignoring the AoA share the elevator really carries. SELECT's number is oracle-locked, is the load on the surface including its aerodynamic-balance area forward of the hinge, and the module contract (`CLAUDE.md`) forbids recomputing it |
| T-13 | **The hinge moment is `HM = L_cs · c_e/3`**, `c_e = CEAFTHL` the aft-of-hinge chord — the centroid of the aft-of-hinge block, which is **always** a triangle because TAILDIST's net trailing-edge pressure is identically zero (`WATT3 = WCAM3 = 0`) | The plan's stated provenance ("hinge moment from the TAILDIST aft-of-hinge pressure block"), and the block's shape makes the arm closed-form rather than quadrature-dependent — so the suite's first hinge-moment output has a hand-checkable gate |
| T-14 | **Exact by construction, not by quadrature.** Removal from the strips is normalised so that exactly `L_cs` leaves, and exactly `L_cs` arrives at the hinges. The removal is spread chord-proportionally over the **control surface's span extent** (first to last hinge station), each part de-scaled at its own chord station (`att` off the 25 % line, `cam` off the 50 %) | Makes the ΣF cross-mode identity a property of the construction. Distributing the removal by the raw strip fractions would leave the identity resting on `Σ frac = 1`, which is exact for a derived rectangle and only 1 %-true for an entered polyline (the T1 validator's own tolerance) |
| T-15 | **The actuator carries a couple, not a force.** Hinges take `L_cs` by chord-weighted tributary span at the hinge-line chord station; the actuator station takes `−HM` | With no horn radius in the schema, a rotary actuator is the honest model. It also makes the chordwise identity exact: hinge torsion + actuator couple = `L_cs·(x_lra − x_cp)`, the control load acting at its own centre of pressure |
| T-16 | **T-tail transfer set: `Fz` and `Myy` only**, at the last v-tail `GRID`; roll and yaw transfer are zero and are stated so | The concurrent pairing (T-5) is a *balancing* condition, which is symmetric, so the h-tail's two halves cancel about the centreline. A transferred `Mxx` would be a number with no producer |
| T-17 | **Attachment geometry lives on `TailMassInput`**, beside `control_load_mode` (`hinges_span_in`, `actuator_span_in`), and **no shipped fixture gets any** | The mode and the geometry it requires belong to one per-surface slice, so "discrete without geometry raises" is a check inside one object. Inventing hinge stations for six aircraft with no oracle is the fabrication §9.1 refused for tail polylines; the discrete gates run against a project the test builds, and every shipped deck stays byte-identical in smeared mode — which *is* the mode-isolation gate |
| T-18 *(added 2026-08-15, note 24 R-2 — for the LRA beam model, step 12)* | **In the LRA model a control surface is its own `CBAR` chain on the hinge line.** The hinge `GRID`s sit at the true hinge-line position `(x_hl, y_h, z)` — `x_hl = x_le + c − c_e`, already computed for T-15 — plus the actuator node, each hinge node rigid-linked to the parent-surface LRA node at its span station. The hinge force is applied on the hinge node **without** the folded torsion `F_i·(x_lra − x_hl)` (the lever arm is now geometry the solver sees); the actuator couple `−HM` stays. The T6 representation — hinge nodes on the parent LRA with the folded torsion — remains the **per-component tail-span deck's** card set, for a consumer with no control-surface beam. **Gate:** the two representations reproduce the same parent-surface torsion, closed-form (T-14/T-15 identities). The T-17 field shape (`hinges_span_in`, `actuator_span_in`, entered never invented) is **extended to the wing control surfaces** — aileron and flap inputs gain the same fields plus inboard/outboard butt lines (backlog Pri 10) | A hinge node on the parent LRA with a folded torsion is the right *card* for a consumer who has no control-surface beam; it is the wrong *node* for a beam model that has one (target F1/F6: control-surface LRA on the hinge line). The elevator/rudder are the only surfaces that have hinge nodes today; the aileron/flap have no `GRID`s at all because they have no span station — one schema addition serves both this and the aileron-increment item |

### 10.2 Physics, stated before code

Per surface, per condition, with `k_side` as in §4 and the surface's own
`L_cs` (T-12), hinge stations `y_1 … y_m` and actuator station `y_a`:

```
c_e   = CEAFTHL = (Saft/S)·CAVE          aft-of-hinge chord      (TAILDIST)
x_hl  = x_le + (c − c_e)                 hinge line, local chord station
e     = c_e/3                            block centroid aft of the hinge  (T-13)
HM    = k_side · L_cs · e                hinge moment                     (T-13)
L_cs  = att + cam                        SELECT's parts                   (T-12)

strips:    w25_j −= att · g_j            g_j = chord-weighted, Σ g_j = 1 over
           w50_j −= cam · g_j                  the control span [y_1, y_m]
hinge i:   F_i    = k_side · L_cs · t_i  t_i = chord-weighted tributary, Σ t_i = 1
           M_i    = F_i · (x_lra − x_hl)       torsion carried to the LRA node
actuator:  M_a    = −HM
```

The T-tail transfer, for a v-tail condition naming V-n point `p`, gated on
`layout.tail_type == T_TAIL`:

```
F_air = p.lt                             the balancing h-tail load at that point
F_in  = −p.nz · W_ht                     h-tail inertia, d'Alembert (T-9)
Fz    = F_air + F_in                     applied at the last v-tail GRID
Myy   = (x_tip − x_cp)·F_air + (x_tip − x_m)·F_in
```

`x_cp` is the tail CP station `envelope.tail_balance` publishes for that point
(fallback `xt25`, marked); `x_m` is the h-tail planform's area-weighted mid-chord
line; `x_tip` is the fin-tip node's own LRA station. The moment sign is
`(x_ref − x_load)·F`, the same `r × F` form
`coordinates.tail_torsion_to_airplane` derives — the axis map keeps its single
owner (`CONVENTIONS.md` §7), which gains a `ttail_transfer_to_airplane` entry
rather than a literal at the writer.

### 10.3 Gates (R10 substitutes — no printed oracle exists for either)

1. **Cross-mode force identity, exact.** `Σ F(discrete) == Σ F(smeared)` to
   `rel_tol=1e-12` on every condition of every fixture — a property of T-14's
   construction, not of the strip quadrature.
2. **Hinge set closure, exact.** `Σ F_i == k_side · L_cs`, and
   `Σ M_i + M_a == k_side·L_cs·(x_lra − x_cp_control)` with
   `x_cp_control = x_hl + c_e/3`.
3. **The cross-mode torsion difference is closed-form, not a tolerance.** Root
   torsion moves by exactly `att·x_25 + cam·x_50 − L_cs·x_cp_control` — the
   chordwise relocation of the control load from TAILDIST's two smeared stations
   to its own centre of pressure. The test asserts the identity and *prints* the
   number as the physical explanation, which is stronger than §5's "within a
   stated tolerance".
4. **Mode isolation, byte-level.** With no attachment geometry entered, every
   shipped fixture's deck and every Imperial digest is unchanged.
5. **T-tail transfer.** The fin deck's resultant about the origin equals the
   VT-only resultant **plus** `Fz` and `Myy` above, exactly; with `tail_type`
   conventional the deck is bit-identical to T4 output; the equilibrium
   invariant still closes on the combined deck. `concept_regional_jet` is the
   only `t_tail` fixture, so it is the only Imperial digest that moves — once,
   deliberately, with its own `CHANGELOG` line.
6. **Bands.** Hinge/actuator `GRID`s take registered bands
   (`tail-control-htail` 5001-5300, `tail-control-vtail` 5301-5600); the
   registry's own disjointness guard covers them, and the emitted-GID sweep in
   `test_export_equilibrium.py` gains the two families.
