# Backlog — Open Work & Development Plan

The authoritative list of **open** items, restructured (2026-07-16) into **two
priority phases**:

- **Phase 1 — Make concept-loads development possible.** The minimum work that
  turns concept mode from *wired-in-but-unproven* into a tool an engineer can
  actually use to develop distributed loads for a beyond-FAR23 configuration.
- **Phase 2 — Refinements & nice-to-haves.** Everything else, in priority order:
  calc refinements, FAR23 printed-oracle backfills, export/tooling polish, fleet
  and UI niceties.

The architectural rationale lives in
[`../10_standard/PROJECT_GUIDE.md §7`](../10_standard/PROJECT_GUIDE.md); the
per-module spec is [`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md); the
Phase-C narrative (locked decisions, schema, concept-mode invariants) is
[`01_concept_loads_plan.md`](01_concept_loads_plan.md); the Phase-D narrative
(GUI restructure, locked decisions, page conventions) is
[`02_gui_workflow_plan.md`](02_gui_workflow_plan.md).

> **Lifecycle rule (hard requirement, per `CLAUDE.md`).** When an item here is
> finished, in the **same session**: (1) **remove** it from this file, (2) **add**
> it to [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
> with its full step record, and (3) add a `CHANGELOG.md` `[Unreleased]` entry.
> The backlog holds **open** items only — never leave a "✅ done" entry here.

**Definition of done** (every step closes against all of these):
the module is merged and self-registered; a `tests/test_<module>.py` passes
(Appendix A/B figures within ±0.1% where an oracle exists, else physics-closure);
a Streamlit page exists; the `Project` JSON schema is extended and round-trips in
`io.py` (`SCHEMA_VERSION` bumped, older files still load); and the four docs are
synced (`PROGRAM_SPEC.md`, `20_theory/00_theory_sources.md`, this backlog →
history, `CHANGELOG.md`).

---

## Current state (snapshot)

**Shipped:** Phases 0–2, Phase-C **C0–C11**, Phase-D **D0–D8**, Phase-E **E1–E7**,
and Phase-F **F1–F2** (2026-07-16). **All 22** Appendix-C programs are ported
(ENGLOADS, WTESTIMA, WTONECG, WTENV, WINGGEOM, STRSPEED, MACHLIM, TAU, AIRLOADS,
AIRLOAD4, FLTLOADS, SELECT, WINGINER, NETLOADS, TAILDIST, AILERON, FLAPLOAD,
TABLOADS, ONENGOUT, LGFACTOR, LANDLOAD, BALLOADS) plus **2 modern modules** with no
`.BAS` oracle (`configuration`, `body_loads`). Schema **`SCHEMA_VERSION = 23`**;
385 tests pass; coverage ~92%. The FAR23 path is oracle-locked (Appendix A/B
±0.1%); ONENGOUT and the LANDLOAD wheel table are closure-locked (no legible
printed oracle). The GUI is the six-section loads-release workflow (Start →
Airplane → Envelopes & Critical → Analysis → Loads Plots → Export).

**Concept-mode reality (the reason Phase 1 exists).** Concept mode is broadly
plumbed — `Project.is_concept` drives a concept branch in every load module, the
UI flags concept results as "unverified extrapolation" everywhere, and the sbeam
bridge implements wing/body/tail/control exports — but its **headline deliverable
(per-component distributed loads for a beyond-FAR23 airframe) is only proven for
the wing**. The one concept fixture (`examples/concept_heavy.project.json`,
18,000 lb) defines a wing surface only; running it through `run_all_modules`
fires 7 modules and **skips `net_loads`, `body_loads`, `taildist`,
`aileron`/`flap`/`tab`, and all sbeam exports** for lack of tail/body/control /
`configuration` inputs. Concept closure is tested for the wing only; there is **no
true concept↔FAR23 identity test** (it is assumed via the GA oracle tests, not
verified through the concept code path). Phase 1 closes exactly this gap.
**Steps P1-1 and P1-2 shipped 2026-07-16** — a full-airframe concept fixture
(`examples/concept_regional_jet.project.json`) now drives all 19 applicable modules
including body/tail/control + the swept AIRLOAD4 branch, and
`tests/test_concept_closure.py` (10 tests, 376 total now pass) asserts
physics-closure per component (wing lift = n·W, tail balances the pitching moment,
body free-free equilibrium, TAILDIST↔SELECT split, control build↔run, and clean
sbeam export). **Steps P1-3 (identity test), P1-4 (export API) and P1-5 (gyro
guard + warn) shipped 2026-07-16 — Phase 1 is now complete.**

**Remaining suite programs (0):** all 22 ported.

---

# Phase 1 — Make concept-loads development possible (priority)

**Goal.** An engineer can define a beyond-FAR23 configuration, run the *full*
airframe (wing + body + tail + control surfaces) through concept mode, trust the
result via physics-closure checks, and export every component to sbeam — with the
FAR23 oracle still intact. Steps are in dependency/priority order.

> **Invariant (unchanged):** no calc-math change to the FAR23 path — Appendix A/B
> oracles pass unmodified; concept mode reduces exactly to FAR23 on GA inputs.

### Step P1-1 — A full-airframe concept reference fixture — **shipped 2026-07-16**
Added `examples/concept_regional_jet.project.json` (RJ-50 concept — swept-wing,
high-subsonic twin-turbofan regional jet, MTOW 33,000 lb, `category="C"` / Part 25).
It drives **all 19** applicable modules — the first fixture to reach `body_loads`,
`taildist`, `aileron`/`flap`/`tab`, and the swept `AIRLOAD4` branch. Building it
surfaced and fixed a real `io` gap (`sweep_deg`/`design_mach` were never
serialized). Guarded by `tests/test_concept_regional_jet.py` (4 tests). See
`40_history/00_completed_development.md` → "Phase 1 — Step P1-1". *Follow-ons kept
open: closure validation is P1-2; the aft-fuselage engine layout is modelled as
`2W` (the suite has no aft-fuselage `EngineLayout` — sketch limitation, noted).*

**Phase 1 is complete** — Steps P1-3 (concept↔FAR23 identity test), P1-4 (export
package public API) and P1-5 (concept engine gyroscopic guard + warn) all shipped
2026-07-16; see `40_history/00_completed_development.md`. The remaining suite work
is the Phase 2 refinements below and the Phase G GUI rework.

---

# Phase 2 — Refinements & nice-to-haves (priority order)

Not blocking Phase 1. Listed most-valuable/least-blocked first; each closes under
its own mini-step (history + changelog entry). Items marked ⛔ are **blocked on
external reference material** and are lowest actionable priority.

### 2-1 — Unify `select_wing`/`one_engine_out` case identity (from D1)
D1 mints wing `W-` ids on two independent, unlinked lists — `select_wing`'s
`CriticalCondition`s and the `WingMassInput.cases` that actually drive
WINGINER/NETLOADS — banded apart so they don't collide but are not the same case
object; same gap between `one_engine_out`'s `VT-` id and `select_vtail`'s. Close by
deriving `WingMassInput.cases` from `envelope.critical`'s wing conditions when not
given (mirroring the fuselage/tail pattern) and linking `one_engine_out` to
`select_vtail`'s `CriticalCondition` list, so each component has one case-ID
authority end-to-end. Touches which case list WINGINER/NETLOADS iterate → needs an
oracle re-check. *(Traceability integrity; unblocked.)*

### 2-2 — Per-CG precise inertia in SELECT (from C6)
`Project.mass` is persisted (WTONECG), but SELECT's checked-maneuver `Iyy` and
v-tail `IZZ` still use the Ch 9 approximations (which match the oracle). Wire the
persisted per-CG inertia. *(Unblocked calc refinement.)*

### 2-3 — V-tail large-deflection factor `EFV` → SELECT backfill (from C6/C9)
The legible large-deflection chart (Dommasch fig 12:3) lives in
`_vtail.large_deflection_factor` (recovered for ONENGOUT). SELECT's static v-tail
rudder load still uses `VTailLoadsInput.rudder_large_deflection_factor` (default
1.0); wiring the recovered curve into `_vt_rudder_load` was proposed as a ~1% shift.
**⚠️ Not a simple wire-in — the naive fix breaks the oracle (investigated
2026-07-16).** `large_deflection_factor(defl=30°, SR/SV=5.236/14.84=0.353) = 0.53`,
*not* ~1.009 — applying it the way the elevator applies `_ef` would drop the printed
SUDDEN RUDDER load from ~586 lb to ~312 lb (−47%), shattering the Appendix A **591 lb**
oracle (`test_critical_vtail_loads_match_appendix_a`). The elevator chart *does*
reduce its load (EF≈0.84 at 10°) and matches its oracle, so the manual clearly does
**not** apply the same large-deflection alleviation to the 23.441 sudden-full-rudder
limit case — the manual's rudder factor is ~1.0. **Reopen only after** re-reading
`SELECT.BAS` subroutines 8300/10000 to establish exactly what quantity the rudder
`EFV` multiplies (and on which deflection variable); the current default-1.0
pass-through lands within the oracle's 1.5% band and should stay until that is
pinned down. *(Unblocked but needs source re-read, not a code change.)*

### 2-4 — sbeam stick model: real stiffness + assembled airframe (from C4)
The stick model uses **nominal placeholder** structural properties
(`_MAT1_E = 1.0e7`, aluminum-ish; fine for a determinate reaction check, not a
real sizing) and exports each component as a **disjoint GID block** (wing 1+,
body 1001+, tail 2001+, control 3001+) — there is no assembled airframe model.
Add real/parametric section properties and an assembled combined-airframe export.
**Granularity (D-7, decided 2026-07-16): both — load-cards-only stays the default
(splice into a user's existing sbeam model); the assembled-airframe stick model is
opt-in behind an explicit flag.** *(Concept-adjacent tooling; unblocked.)*

### 2-5 — sbeam VLM cross-check — *out of scope (D-3, 2026-07-16)*
Building the optional sbeam-VLM backend to independently validate concept Schrenk
distributions is **out of scope** (decided 2026-07-16). Concept aero stays
validated by physics-closure checks + fleet plausibility (per invariant C-2 / the
Phase-C validation strategy), not an independent VLM. Revisit only if closure
proves insufficient in practice.

### 2-6 — Flaps-extended tail loads: aero + printed oracle (from C6/C7)
R3/R4 (flapped V-n envelope + flaps-extended balancing/gust) and TAILDIST's 13
horizontal / 4 vertical chordwise rows are **closure-validated**, but the
SELECT→TAILDIST pipeline emits only the 9 flaps-retracted horizontal conditions.
Matching the printed Appendix A flaps-extended cases (81/106/88/108) needs the real
landing-config aero polynomials and the CG5–7 loadings added to the fixtures.
*(Partially blocked: needs landing-config aero data.)*

### 2-7 — Distinct Commuter category (from E)
The commuter tier (19,000 lb / 19-seat) is encoded in `constants.py` but not fully
landed as a category split out of the merged "Normal / commuter". Non-blocking;
revisit when a concept needs the intermediate certificated tier represented
cleanly.

### 2-8 — Aero-coefficient curve plot (declined in E, decision revised include)
A CL–α / drag-polar / CM plot on Aerodynamic Data (with the recovered-CL closure
check) was reviewed and **not selected** (2026-07-15). Revisit if
coefficient-entry errors prove common. Revisit not do.

### 2-9 — Fleet-data curation — *deferred, fleet is fine as-is (D-4, 2026-07-16)*
The current fleet (F1 set: 29 aircraft + `aspect_ratio`) is **sufficient for now**
(decided 2026-07-16). No further comparator additions, extra columns
(`cruise_kt`/`range_nm`/`service_ceiling`/`category` tag), or in-UI user-supplied
rows are planned. Revisit if a concept design needs peers the current set doesn't
cover (e.g. when the D-1 regional-jet fixture wants transport-class comparators).

### 2-10 — FAR23 printed-oracle backfills ⛔ *blocked on reference material*
Lowest actionable priority — all blocked on a legible source that is **not in the
bundled `reference/FAR23 loads (1).pdf`**. Close each as a mini-step if a legible
Appendix B / `.OUT` file surfaces:
- **AIRLOAD4 swept spanwise printed oracle (C7)** — swept branch is
  reduction-/closure-validated; a printed Appendix B swept spanwise table needs
  the twin fixture (D-5).
- **ONENGOUT printed twin oracle (C9)** — closure-/sub-formula-locked; Appendix B
  one-engine-out tables are absent from the bundled PDF.
- **LANDLOAD printed wheel-load oracle (C10)** — LGFACTOR + gear intermediates are
  oracle-locked, but the printed Appendix A wheel-load table (p231–233) is
  OCR-garbled; the 24-main/33-nose reaction matrix and datum loads
  (PITCHP/ROLLP/YAWP) are closure-/legible-cell-locked.
- **Appendix B twin fixture** (D-5) — the shared blocker for the swept and ONENGOUT
  oracles; the engine module's Appendix-B turboprop case is encoded inline in
  `tests/test_engine.py`, not as a project file.

### 2-11 — Naming decision — *keep "FAR23LOADS" for now (D-6, 2026-07-16)*
Resolved 2026-07-16: **keep the "FAR23LOADS" name** for now. No rename or
concept-loads sub-brand. Revisit if/when the concept scope becomes the primary
identity of the tool.

### 2-12 — Ground-case distributed fuselage (and wing) loads *(calc-side; split from Phase G, 2026-07-16)*
**Objective.** Extend the fuselage (and wing) net-load distribution so it runs for
**ground/landing** conditions, not just flight conditions, and add the pressurized
no-down-select rule.
**Why.** `body_loads` today distributes over **flight** V-n conditions only
(`select_fuselage` scores `VnPoint`s); the landing path (LGFACTOR + LANDLOAD)
produces **gear reaction loads** only — there is no distributed fuselage shear/
bending from ground cases. For **pressurized** airplanes the pressurization load
must be assessed for flight and **cannot** be down-selected by a ground case, so the
two families must be carried separately.
**Scope.** New: a ground-case fuselage inertia/reaction distribution (gear reactions
as applied external loads on the body axis at the landing load factor from
LGFACTOR); optionally the wing distribution under the ground reaction; a
pressurization load case that is never down-selected against flight. **Substantial
calc work** — the heaviest piece of the GUI rework, deliberately split out so it
does not gate the usability restructure.
**Acceptance.** A ground condition produces a distributed fuselage shear/bending run
(free-free equilibrium closes); the pressurized case is retained independent of the
governing flight case; FAR23 flight oracles unchanged. **Priority:** after Phase G's
usability work (G0–G8) unless raised.
Source narrative: `03_gui_rework_plan.md` §5 item (3).

---

## User's Guide fidelity review findings (2026-07-16)

A full pass of the **FAA User's Guide** (DOT/FAA/AR-96/46) against the ported
modules. Load *magnitudes* are all oracle-locked and correct; these are citation,
data-flow-provenance, and optional-capability gaps. **Reference 1 / the `.BAS`
source is the primary oracle** — the "verify vs `.BAS`" items must be checked
against it before any code change (the User's Guide is the secondary operational
reference). Already-tracked overlaps: v-tail EFV → **2-3**; flaps-extended tail →
**2-6**; commuter category / VB gust → **2-7**; per-CG inertia / WTONECG 4-point
loading set → **2-2**; case identity → **2-1**. Shipped from this review: the
TAILDIST per-condition citation fix (CHANGELOG `[Unreleased] → Fixed`, 2026-07-16).

### 2-13 — STRSPEED: VD floor basis + optional CLmax→stall-speed path
Two items in `structural_speeds.py`. (a) **VD floor** is computed as
`K_d·(chosen VC)` (`:147-149`); 23.335(b)(2) reads `K_d·VCmin`. For the GA6 case
(chosen VC 170 vs VCmin ≈142) the code is conservative (~238 vs ~198) but not the
reg text, and `vd_recommended` is untested — *verify vs STRSPEED.BAS*, then either
switch to `vc_min` or document the deviation. (b) **No CLmax→VS path** — the guide
(p7-5) lets the user enter CL-w/CL-f and computes stalling speed; the port only
accepts stall speeds directly (`StructuralSpeedsInput.stall_*_kt`). Add the optional
CLmax stall-speed calc or record it as intentionally out of scope.
*(Citation-verify + optional capability; unblocked.)*

### 2-14 — AIRLOAD4 auto-select Mach threshold (0.4 vs User's Guide 0.5)
`airloads.py:73` triggers the swept/high-Mach branch at `design_mach > 0.4`; the
User's Guide states **0.5** (§9.1 and §10.1, both). *Verify vs Reference 1 Ch 12 /
AIRLOAD4.BAS* — if 0.4 is not sourced there, change `_AIRLOAD4_MACH` to 0.5, else
document the conservatism. The 15° sweep trigger matches. *(Threshold-verify;
unblocked.)*

### 2-15 — FLAPLOAD slipstream power: takeoff vs max-continuous HP
`flap.py:163` (`_engine_power`) uses `max_cont_hp or takeoff_hp` (prefers
max-continuous); FAR 23.457(b) specifies the slipstream at **takeoff power**.
*Verify vs FLAPLOAD.BAS* (the input label "Max HP of One Engine" is ambiguous, the
reg is not); prefer `takeoff_hp` if the source agrees. *(Citation-verify;
unblocked.)*

### 2-16 — FAR citation cleanups (labels only, no load change)
- ~~**WTONECG** cites `23.21/23.23`~~ — **done 2026-07-16**: changed to
  **`23.23/23.29`** (load-distribution limits + empty weight & corresponding CG, the
  quantities WTONECG computes).
- ~~**FLTLOADS** `_FAR` omits **23.345**~~ — **done 2026-07-16**: added, now
  `23.333/23.337/23.341/23.345/23.421`. 23.373 still excluded until the enroute
  config exists (see 2-19).
- **SELECT** v-tail SIDE GUST labelled `23.443(b)` — **reviewed 2026-07-16, keep as
  is.** The primary oracle grounds it: `00_theory_sources.md` and `SELECT.BAS` subr
  8300 attribute the Kgt/Ude gust-load *formula* the code implements to **23.443(b)**;
  the User's Guide's 23.443(a) is the looser general-requirement reference. Changing
  it would contradict the manual and break `test_select.py`/`test_taildist.py`.
  *(Resolved — no change.)*

### 2-17 — ONENGOUT data-flow + scope
(a) **V-tail geometry provenance:** Table 2.2 sources ONENGOUT's v-tail area / AR /
rudder area from **WINGGEOM**, but `one_engine_out.py:275-300` reads a separate
`Project.vtail_loads` slice and never `Project.geometry`. Either derive `vtail_loads`
from geometry or document the slice as the intended source (same class of GUI-
mediated feed as FLTLOADS←WTONECG). (b) **Turbopropeller scope (23.367):** `run`
gates only on slice/engine presence, not `is_turboprop` — it will run for a
reciprocating multi. Add a gate or a caption. *(Data-flow + guard; unblocked.)*

### 2-18 — AIRLOADS: airplane-less-tail coefficient generation (User's Guide windows 4/6/8)
The guide's AIRLOADS also computes the airplane-less-tail CL/CD/CM polynomials —
fuselage/nacelle pitching-moment (window 6), landing-gear aero (window 8), and
per-station stall CL (window 4). None of these inputs exist in `AeroSurfaceInput`;
the coefficients are entered by hand as `AeroCoeffSet` (documented in
`flight_envelope.py`/`airloads.py`). *Documented scope gap* — implement the
coefficient generator or keep as a tracked future step. *(Medium; unblocked but
large.)*

### 2-19 — FLTLOADS enroute / speed-control config (FAR 23.373)
The guide's FLTLOADS models a third config — **enroute** (partial flaps / dive
brakes / spoilers, window 2 + windows 7-8) with a dedicated **VPF** speed
(§11.2.3, 23.373). The port builds only cruise + flaps-down. Add an enroute
`AeroCoeffSet` + VPF, or document the omission (and only then add 23.373 to the
citation string per 2-16). *(Medium; unblocked.)*

### 2-20 — WINGINER Table 15.1 output completeness
Table 15.1 lists `THETADOT` (pitch-velocity rate) and a separate incremental
torsion `DMYY`; `wing_inertia.py` emits neither (only vertical/drag/roll unit cases
and cumulative `myy`). *Confirm vs WINGINER.BAS* whether a pitch-acceleration case
is expected; surface `DMYY` if a per-strip incremental column is wanted.
*(Low; reporting completeness.)*

### 2-21 — Minor UX / reporting parity with the User's Guide
Batch of low-severity items: **ENGLOADS** captures `prop_blades` (NOBLADES, a
required guide input) but never uses it — wire into the blade-inertia approximation
or mark descriptive-only; **AILERON** silently coerces a positive up-deflection
(`aileron.py:73`) where the guide errors — document the coercion; **WTONECG** omits
YBAR (=0 for a symmetric airplane) from the CG output; **TAILDIST** implements only
the average-chord distribution, not the guide's "distributed on N station chords"
analyses (Figs 20.7-20.10). *(Low; unblocked.)*

---

# Phase G — Workflow-aligned GUI rework (usability)

**Goal.** Turn the mature-but-clunky six-section GUI into a **workflow-aligned**
tool: geometry owned in one place, one unit per dimension app-wide, persistent
(no re-entry), navigation re-sequenced to the FAR 23 analysis flow — reusing the
shipped Phase D/E/F pages rather than rebuilding them. Narrative, assessment vs.
the current code, and locked decisions **G-1…G-4** are in
[`03_gui_rework_plan.md`](03_gui_rework_plan.md); the six analysis-flow **workflow
sections** it targets are that doc's §4.

> **Invariant (unchanged):** no calc-math change to the FAR23 path — Appendix A/B
> oracles pass unmodified throughout; ultimate-load output rules hold; pure calc /
> thin shells; `workflow.py` stays the single source of navigation truth.

Steps are in dependency order. G1 (foundational) comes before the
re-sequencing (G2–G3); the new features (G4–G6) and the report (G8) follow.
**G0, G1, G2 and G3 shipped 2026-07-18/19** (see `docs/40_history/00_completed_development.md`).

### Step G4 — Fuselage pitching-moment estimator (new; GUI + light calc)
**Objective.** Derive the fuselage pitching-moment contribution from the G1 fuselage
geometry and feed it into the airplane-less-tail `CM` used by the FLTLOADS balance,
so the user no longer hand-folds it into the input coefficients.
**Scope.** A pure helper (fuselage moment from geometry — e.g. Munk/slender-body or a
documented simplified method, cited to `reference/`) that augments the `M(W+F)`
coefficient set; surfaced on the 1d Aero page with the estimate shown and
overridable. **FAR23 GA oracle inputs must reduce exactly** (estimator contributes 0
or matches the manual's assumed value on Appendix-A inputs, or is off by default so
oracles are untouched).
**Acceptance.** The estimate is displayed and overridable; Appendix A/B oracles pass
unchanged (estimator additive/optional); the balanced tail load reflects the fuselage
moment when enabled. Cite the method + page in the test.

### Step G5 — Longitudinal-stability / trim plots (new; GUI)
**Objective.** Add standard longitudinal-stability plots to the flight-loads section
to check trim and balancing tail loads (CG-vs-balanced-tail-load; static-margin
sweep).
**Scope.** GUI plots over existing calc (the FLTLOADS balance already yields tail
load per CG; `configuration` already computes neutral point / static margin). No new
calc.
**Acceptance.** The flight-loads section shows a trim plot (balanced tail load vs CG)
and a static-margin readout across the CG range; values trace to the existing calc.

### Step G6 — Direct elevator %-chord input (new; GUI + small model field)
**Objective.** Expose the elevator chord ratio as a direct input instead of only
deriving it from the hinge-area/tail-area ratio.
**Scope.** Add an elevator chord-ratio field to `TailLoadsInput` (mirroring
`TabSpec`'s `E = MACTAB/CAIRFOIL`), serialized in `io.py`, editable on the tail page;
keep the area-derived value as the default so existing projects are unchanged.
**Acceptance.** The field round-trips; when unset, results match today's area-derived
behaviour (regression); when set, it drives the chordwise station. Schema bump,
older files migrate.

### Step G7 — Persistence verification (G-3)
**Objective.** Confirm the rework eliminated re-entry and hunt any genuine reload
bug.
**Scope.** Verify every input-bearing value lives on a `Project` slice `io.py`
round-trips (no input-only `st.session_state`); drive save→reload on each example
project and diff. Fix any real loss found **before** shipping the restructure.
**Acceptance.** A save→reload of every example project is a no-op (no field resets);
no input page holds input data outside `st.session_state["project"]`.

### Step G8 — Summary report (Export phase)
**Objective.** Add the summary report described in `03_gui_rework_plan.md` §4 Phase 6:
(1) input-data summary; (2) envelope plots (V-n, weight/CG, speed/altitude); (3)
loads-analysis conditions + FAR coverage; (4) results summary (VMT wing/fuselage,
control-surface/flap, landing gear, engine loads).
**Scope.** Assemble from existing per-module results/plots + the case-index table;
reuse `report.py`/`export_report`. All load figures ULTIMATE per the output rules.
**Acceptance.** The Export phase produces a single consolidated report with the four
sections; every load figure is `-ULT` with its `SF`.

---

## Open design decisions requiring user input

The decisions that gate or shape the work above. **D-1 and D-2 gate Phase 1**; the
rest shape Phase 2.

- [x] **D-1 — The concept reference airplane (gates P1-1) — RESOLVED 2026-07-16:
  regional jet.** A swept-wing, high-subsonic-Mach twin turbofan (MTOW well above
  12,500 lb), chosen specifically to force the `AIRLOAD4` swept branch — the
  least-covered concept path, furthest from any FAR23 oracle. Working starter
  geometry recorded in Step P1-1; the exact scalars (MTOW, area, sweep, span, Mach,
  seats) are confirmed/adjusted at build time. Phase 1 can now start.
- [x] **D-2 — Concept engine gyroscopic rates (gates P1-5) — RESOLVED 2026-07-16:
  guard + warn.** Keep the fixed FAR 23.371(b) rates (2.5 / 1 rad/s) as the default
  stand-in, but add a guard that emits a note + UI warning when the concept's
  implied or user-override rates exceed them, so the non-conservative case cannot
  pass silently. Solving for real maneuver-derived rates (the fully-correct 25.371
  path) is deferred — not built in P1-5. See Step P1-5.
- [x] **D-3 — sbeam VLM cross-check (shapes 2-5) — RESOLVED 2026-07-16: out of
  scope.** No sbeam-VLM validation backend. Concept aero relies on physics-closure
  + fleet plausibility (invariant C-2). Revisit only if closure proves insufficient.
- [x] **D-4 — Fleet-comparison curation (shapes 2-9) — RESOLVED 2026-07-16: fine
  as-is.** The current 29-aircraft fleet is sufficient for now; no further
  comparators, columns, or user-supplied rows planned. Revisit if a concept design
  (e.g. the D-1 regional jet) needs transport-class peers the set lacks.
- [ ] **D-5 — Appendix B twin fixture (blocks 2-10).** The swept (C7) and ONENGOUT
  (C9) printed oracles want the 10-place twin turboprop as a fixture, but Appendix
  B is **not in the bundled PDF**. *Can the user supply a legible Appendix B or the
  original `.INP`/`.OUT` files?* Until then `examples/twin_turboprop.project.json`
  can't be built and these oracles stay blocked.
- [x] **D-6 — Naming (shapes 2-11) — RESOLVED 2026-07-16: keep "FAR23LOADS".** No
  rename or sub-brand for now; revisit if concept scope becomes the tool's primary
  identity.
- [x] **D-7 — sbeam export granularity (shapes 2-4) — RESOLVED 2026-07-16: both,
  assembled behind a flag.** Emit load-cards-only by default (splice into a user's
  existing sbeam model); the auto-generated assembled-airframe stick model is opt-in
  behind an explicit flag. See Step 2-4.
- [x] **D-8 — Standalone vs project-only inputs — RESOLVED 2026-07-16: full
  projects canonical.** Full-airplane project JSONs are the canonical input form;
  per-module input slices are **derived** from them for tests, not maintained as
  standalone example files.

---

## Known defects

- _(none open — the flight-envelope destructive slice overwrite was fixed in
  Step D0 / release step R1, 2026-07-08; see
  `40_history/00_completed_development.md` → Resolved defects.)_
</content>
</invoke>
