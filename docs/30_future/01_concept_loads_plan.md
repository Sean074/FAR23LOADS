# Phase C — Initial-Concept Loads Tool (development plan)

The active development plan that grows FAR23LOADS from a faithful ≤12,500 lb
**FAR Part 23 Subpart C** replication into an **initial-concept distributed-loads
tool**: one that can exceed the FAR23 weight and seat limits, assesses a candidate
configuration against similar airplanes, and emits per-component distributed loads
(wing / body / tail, plus *standard simplified* control-surface distributions),
with a clean hand-off to **sbeam** for structural sizing.

This document is the Phase-C narrative (companion to
[`PROJECT_GUIDE.md`](../10_standard/PROJECT_GUIDE.md) §7, which still describes the
original phase-by-phase suite roadmap). The authoritative open-item list is
[`00_backlog.md`](00_backlog.md); per-module equation/IO detail is in
[`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md). When a Phase-C step closes,
follow the lifecycle rule: remove it from the backlog, add it to
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md),
and add a `CHANGELOG.md` `[Unreleased]` entry — same session.

---

## 1. Why this is a superset, not a rewrite

The user requirements map almost one-for-one onto modules the suite **already
plans to port** — the work is sequencing and concept-mode generalization, not new
physics:

| Requirement | Realized by |
|-------------|-------------|
| Distributed loads — **wing** | AIRLOADS (Schrenk) → WINGINER → **NETLOADS** (span shear / BM / torsion) |
| Distributed loads — **body / fuselage** | SELECT (fuselage net loads, Ref 1 Ch 9 / Ch 15) |
| Distributed loads — **tail** | FLTLOADS (balancing) → **TAILDIST** (chordwise H/V-tail) |
| **Control surfaces — standard simplified distributions** | AILERON / FLAPLOAD / TABLOADS (FAR-style simplified pressure distributions) |
| **Assess vs similar airplanes** | existing fleet plot + the planned Configuration & Layout page |
| Leverage FAR23 LOADS methods / core | the ported FAR23 modules (22 of 22, through C11) are the foundation |
| Leverage sbeam | code/doc style (already mirrored) **plus** a real FORCE/MOMENT BDF export bridge |

### The one genuine conflict: exceeding the FAR23 limits

Two things in the suite are calibrated to small GA and do **not** extrapolate past
12,500 lb; the rest of the physics is weight-agnostic:

1. **Maneuver-load-factor formula** — `n = 2.1 + 24000/(W+10000)`, capped
   3.8 / 4.4 / 6.0 (FAR 23.337). Meaningless for a heavy concept.
2. **Statistical weight estimate** — WTESTIMA's empty/TO ratio (`K ≈ 0.62`) and
   component %-of-TOW are regression-fit to light GA.

Everything else — Schrenk spanwise lift, balancing tail loads, inertia relief, net
span loads, simplified control-surface distributions — is geometric/physical and
generalizes. So the task is to **parametrize the regulatory caps**, not rewrite the
methods.

---

## 2. Two invariants the plan preserves

1. **The FAR23 path stays oracle-locked.** Every module with an Appendix A/B
   worked example keeps its ±0.1% regression test *in FAR23 mode*. Concept mode is
   a superset that must reduce **exactly** to the FAR23 result when given GA inputs
   (an identity test guards this).
2. **Concept mode has no printed oracle**, so it is validated by physics-closure
   checks (total lift = `n·W`; tail balances the pitching moment; net load
   integrates to the applied distribution), fleet-comparison plausibility, and an
   optional sbeam-VLM cross-check of the Schrenk distribution. This is documented,
   accepted, and surfaced in the UI (concept results are flagged "unverified
   extrapolation").

---

## 3. Locked decisions (basis of this plan)

| # | Decision | Choice | Consequence |
|---|----------|--------|-------------|
| C-1 | **Exceeding FAR23 limits** | **Concept mode — generalize the caps in place.** | New `category = "C"`; load-factor / weight / seat limits become configurable or overridable; physics unchanged; FAR23 oracle intact. |
| C-2 | **Aero engine for distributed loads** | **McMaster analytical (Schrenk AIRLOADS → NETLOADS).** | Self-contained, validated, fast, matches "standard simplified distributions"; no sbeam runtime dependency. sbeam VLM is an optional future cross-check only. |
| C-3 | **sbeam integration** | **Export bridge.** | Distributed component loads emit as sbeam-consumable `FORCE`/`MOMENT` BDF cards + span-load CSV (and an optional CBAR stick model), matching sbeam's card style. Includes continuing to mirror sbeam's code/doc discipline. |
| C-4 | **Build order** | **Vertical slice first.** | Wing distributed loads work end-to-end (geometry → speeds → envelope → airloads → inertia → net) and export to sbeam before widening to tail/body/control surfaces. |

---

## 4. Schema additions

New `Project` slices (`farloads/models.py`; bump `SCHEMA_VERSION`, extend the
`io.py` round-trip), mirroring the ownership table in `PROGRAM_SPEC.md`:

| Slice | Owned by | Notes |
|-------|----------|-------|
| `Project.mass` | WTONECG | persisted weight/CG/inertia (introduced when FLTLOADS consumes it) |
| `Project.aero` | TAU, AIRLOADS | `tau`, `spanwise` (cl·c vs span) |
| `Project.envelope` | FLTLOADS, SELECT | `vn`, `tail_balance`, `critical` |
| `Project.loads` | component modules | `wing_inertia`, `wing_net`, per-component distributed results |
| `Project.configuration` | Configuration & Layout | `LayoutInput` (fuselage/wing/tail/gear/engine geometry) |

Concept-mode fields: `StructuralSpeedsInput.category` gains `"C"`;
`WeightInput` gains a direct-weight path so MTOW/OEW/components come from the
itemized `MassItem` list rather than the GA regression.

---

## 5. The steps (dependency-ordered, vertical-slice first)

Each step ends with: module(s) merged, a `tests/test_<module>.py` passing
(Appendix A/B where an oracle exists), a Streamlit page, the `Project` schema
extended, and docs synced.

### Step C0 — Concept-mode foundation & mission reframe *(prerequisite)*
**Objective.** Remove the GA-only assumptions that block >12,500 lb / >GA-seat
configurations, without disturbing the FAR23 path.
**Deliverables.**
- `models.py`: add `category="C"` (concept) to `StructuralSpeedsInput`; concept
  requires explicit `chosen_n`/`chosen_nneg` (override fields already exist) so the
  23.337 cap is bypassed, not applied. Add a direct-weight path to `WeightInput`.
- `structural_speeds.py` / `weight_estimate.py`: gate the GA-calibrated formulas
  behind `category != "C"`; in concept mode emit WTESTIMA only as a flagged "GA
  sanity estimate." Confirm no hard 12,500 lb / seat assertion is load-bearing.
- Docs: reframe `CLAUDE.md`, `README.md`, `PROJECT_GUIDE.md` scope to
  "initial-concept loads tool (FAR23 replication core + concept extrapolation)."
**Test/Acceptance.** All existing tests pass unchanged (FAR23 identity). A new
concept fixture (MTOW > 12,500 lb, user n) runs end-to-end without tripping a GA cap.
**Risk.** WTESTIMA invalid above its calibration band — mitigated by the
itemized/direct-weight path and a UI label.

### Step C1 — AIRLOADS (Schrenk spanwise lift) + TAU helper
**Objective.** Spanwise additional + basic lift distribution (`cl·c` vs span)
normalized to a target `CL`, for any planform/weight.
**Deliverables.** `modules/airloads.py` (registers `"airloads"`; folds in the TAU
lift-curve-slope correction). Reads `Project.geometry` wing strips (reuse the
WINGGEOM strip integrator); writes `Project.aero.spanwise`. Span-load Streamlit
plot. Schrenk = average of actual-chord and elliptic distributions (Ref 1 Ch 7).
**Test/Acceptance.** Appendix A spanwise table ±0.1% (FAR23). Concept: integrated
`∫cl·c dy` recovers the target `CL`; an elliptic wing returns an elliptic
distribution.
**Note.** Swept / high-Mach concepts need AIRLOAD4 — scheduled in C7; flagged here
as a known limitation for swept concept wings.

### Step C2 — FLTLOADS (V-n envelope + balancing tail loads)
**Objective.** Maneuver+gust V-n envelope and the balancing horizontal-tail load at
each corner.
**Deliverables.** `modules/flight_envelope.py`. Reads `Project.mass`,
`weight.envelope`, `geometry`, `speeds`, `aero`; writes `Project.envelope.vn` +
`tail_balance`. Concept mode uses user n / user envelope. V-n Streamlit chart.
Approximate tail CP (XTC ≈ 5%, XTF ≈ 25% tail MAC; Ref 1 Ch 8).
**Test/Acceptance.** Appendix A/B corner-point speeds, load factors and balancing
tail loads ±0.1%. Concept closure: tail load balances the wing-plus-inertia
pitching moment about the CG.

### Step C3 — WINGINER + NETLOADS (wing distributed loads — headline output)
**Objective.** Net spanwise **shear, bending moment, torsion** for the wing
(airload − inertia) at the critical V-n conditions.
**Deliverables.**
- `models.py`: add a spanwise **wing mass distribution** input (structure + fuel)
  — *new field, no current home* — required for inertia relief; documented default
  (per-strip lumped structure %-of-span + fuel).
- `modules/wing_inertia.py` (`Project.loads.wing_inertia`) and
  `modules/net_loads.py` (`Project.loads.wing_net`: station, shear, BM, torsion) +
  CSV + Streamlit shear/BM/torsion plots.
**Test/Acceptance.** Appendix A/B `PHAABB36` / `TORBB36` net-load tables ±0.1%.
Concept closure: net shear integrates to `n·W_wing`; root BM matches a hand
trapezoidal integration of the Schrenk distribution.

### Step C4 — sbeam export bridge (wing slice end-to-end)
**Objective.** Turn the wing distributed load into an sbeam-consumable structural
load set, proving the integration on the vertical slice.
**Deliverables.** `farloads/export/sbeam_bridge.py`:
- span-load CSV in sbeam's format;
- `FORCE`/`MOMENT` bulk-data cards at wing stations, matching sbeam's comma
  free-field card style (`sbeam/results/load_export.py`);
- optional minimal CBAR stick-model BDF (GRID + CBAR + PBAR + load cards + a SOL
  101 case) so the load runs directly in sbeam;
- a documented coordinate/units map (FAR23LOADS station-X / butt-Y / waterline-Z,
  inches → sbeam global CID 0).
**Test/Acceptance.** Exported cards sum to the same total Fz/My as NETLOADS
(force/moment closure); the stick-model BDF parses and solves in sbeam without
error; round-trip Fz matches within tolerance.
**Open sub-decision (resolve at build time).** Emit *only* load cards to splice
into a user's existing sbeam model, *or* also auto-generate the stick model.
Working assumption: do both, stick model behind a flag.

### Step C5 — Configuration & Layout page + fleet assessment *(shipped)*
**Objective.** Satisfy "assess the configuration against similar airplanes" — the
planned Configuration & Layout page plus an extended fleet set. (Supersedes the
"Configuration & Layout page" modern-addition backlog item.)
**Deliverables.** `Project.configuration` (`LayoutInput`) + `modules/configuration.py`
(MAC/XLEMAC, static margin via tail-volume neutral point, tip-back / overturn,
clearances); `app/pages/00_Configuration_Layout.py` (three-view, CG/NP markers,
W/S-vs-W/P and MTOW-vs-OEW **fleet comparison**); extend
`app/data/reference_aircraft.csv` with a heavier/concept tier (commuters, bizjets,
light transports) so concept designs have meaningful peers.
**Test/Acceptance.** Derived MAC/XLEMAC match WINGGEOM on Appendix A (sanity); the
fleet plot places the concept aircraft against peers.

### Step C6 — SELECT (critical loads) + body/fuselage distributed loads *(shipped)*
**Objective.** Critical-load selection per component and the **fuselage** net
distribution.
**Deliverables (shipped, R1–R10).** `modules/select.py` → `Project.envelope.critical`
(wing PHAA/PMAA/PLAA/NMAA + accelerated/steady roll; H-tail balancing + unchecked/
checked maneuver + gust + unsymmetrical, flaps retracted & extended; V-tail
23.441/23.443; fuselage 23.301/23.331); `modules/body_loads.py` for the Ch 15
fuselage longitudinal net distribution + CSV; `flight_envelope.py` flapped V-n
corner set; `weight_onecg.build_mass` persisting `Project.mass`; the sbeam bridge
body export; and the Critical Loads / Fuselage Loads Streamlit pages. Full schema
in `models.py` (`SCHEMA_VERSION` 6 → 11).
**Test/Acceptance (met).** Appendix A `SEL*LDS` / "Critical … Tail Loads" /
"Critical Fuselage Loads" critical points within ±0.1% + FLTLOADS' ~0.5% V-n noise;
fuselage net satisfies inertia/balancing closure. **Deferred (recorded in the
backlog):** the *printed* flaps-extended oracle (needs landing-config aero + CG5–7
fixtures; R3/R4 are closure-validated), per-CG precise inertia in SELECT, and the
v-tail `EFV` chart. See
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).

### Step C7 — TAILDIST + AIRLOAD4 (tail distributed loads; swept-wing concepts) *(shipped)*
**Objective.** Chordwise H/V-tail load distribution; high-Mach/swept spanwise
airloads for concept jets.
**Deliverables.** `modules/taildist.py` (chordwise = α-load @25% + camber @50%, Ref
1 Ch 10) → tail distributed loads + sbeam bridge; AIRLOAD4 branch in `airloads.py`
(sweep/Mach), auto-selected by sweep/Mach.
**Test/Acceptance.** Appendix A/B tail-distribution and Appendix B swept spanwise
tables ±0.1%.

### Step C8 — Control-surface simplified distributions *(shipped)*
**Objective.** The explicit requirement: control surfaces use **standard simplified
distributions**.
**Deliverables.** `modules/aileron.py`, `flap.py`, `tab.py` — FAR-style simplified
pressure distributions (uniform/triangular per 23.349 / 23.345 / 23.459), hinge
moments + distributed loads + CSV + sbeam bridge.
**Test/Acceptance.** Appendix A/B `AILERON` / `FLAPLOAD` / tab tables ±0.1%.

*(ONENGOUT [C9], LGFACTOR + LANDLOAD [C10], and the off-pipeline BALLOADS
verification utility [C11] have since shipped — all 22 Appendix-C programs are now
ported. See [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).)*

---

## 6. Cross-cutting risks (accepted)

- **Concept-mode validation gap** — no oracle above 12,500 lb. Mitigation: FAR23
  identity tests + physics-closure checks + fleet plausibility + optional sbeam-VLM
  cross-check. UI flags concept results as unverified extrapolation.
- **WTESTIMA out of band** above GA weights → concept relies on itemized/direct
  weights; the estimate is shown only as a labelled sanity figure.
- **Spanwise wing mass distribution (C3)** has no manual precedent — documented
  default, user-overridable.
- **Schrenk accuracy for swept/high-AR concept wings** — addressed by AIRLOAD4 in
  C7; default-Schrenk results warn when sweep/Mach exceeds the method's band.
- **Export coordinate/units mapping** — FAR23LOADS is Imperial inches (station /
  butt / waterline); sbeam runs in global CID 0, user-consistent units. The bridge
  documents and tests the transform explicitly.

## 7. Open user decisions (non-blocking)

- **Naming.** "FAR23LOADS" undersells the concept scope. Keep the name, or adopt a
  "Concept Loads" sub-brand? *(Deferred; non-blocking.)*
- **sbeam VLM cross-check.** Build the optional sbeam-VLM backend as a validation
  aid for concept Schrenk distributions, or leave it out of scope? *(Default: out
  of Phase C; revisit after C8.)*
- **Export granularity (C4).** Load-cards-only vs auto-stick-model. *(Working
  assumption: both, stick model behind a flag.)*
