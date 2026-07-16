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
`.BAS` oracle (`configuration`, `body_loads`). Schema **`SCHEMA_VERSION = 22`**;
362 tests pass; coverage ~92%. The FAR23 path is oracle-locked (Appendix A/B
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

**Remaining suite programs (0):** all 22 ported.

---

# Phase 1 — Make concept-loads development possible (priority)

**Goal.** An engineer can define a beyond-FAR23 configuration, run the *full*
airframe (wing + body + tail + control surfaces) through concept mode, trust the
result via physics-closure checks, and export every component to sbeam — with the
FAR23 oracle still intact. Steps are in dependency/priority order; P1-1 unblocks
the rest.

> **Invariant (unchanged):** no calc-math change to the FAR23 path — Appendix A/B
> oracles pass unmodified; concept mode reduces exactly to FAR23 on GA inputs.

### Step P1-1 — A full-airframe concept reference fixture — *airplane chosen: regional jet (D-1, 2026-07-16)*
**Objective.** Build a concept project JSON (`examples/concept_regional_jet.project.json`)
that drives **every** component path, not just the wing: `configuration`
(geometry/CG/tail-volume), tail aero/geometry (`tail_loads`/`vtail_loads`),
`fuselage_mass` + `flight_loads` (body), `aileron_loads`/`flap_loads`/`tab_loads`,
and the missing wing-chain slices (`envelope.vn` / `mass` so `wing_inertia` and
`net_loads` resolve their `nz/nx`). This is the enabler for P1-2…P1-5 and for any
real concept-loads engineering.
**Why it's first.** Today `concept_heavy.project.json` exercises the wing only
(running it through `run_all_modules` fires 7 modules and skips `net_loads`,
`body_loads`, `taildist`, `aileron`/`flap`/`tab`); tail/body/control concept loads
are untested territory. Nothing downstream can be validated without a fixture that
actually reaches those modules.
**Airplane (D-1, chosen 2026-07-16).** A **regional jet** — swept wing, high
subsonic Mach, twin (aft- or wing-mounted) turbofans, conventional or T-tail,
MTOW well above the FAR23 12,500 lb cap. Deliberately picks the configuration that
**forces the `AIRLOAD4` swept/high-Mach branch** (the least-covered path, furthest
from any FAR23 oracle) rather than staying on Schrenk. *Working starter geometry
(refine at build time): MTOW ≈ 30–35,000 lb; wing area ≈ 500–600 ft²; quarter-chord
sweep ≈ 20–25°; span ≈ 70 ft; cruise Mach ≈ 0.75; ~50 seats.* Confirm/adjust these
scalars when the fixture is built.
**Acceptance.** `run_all_modules(load('examples/concept_regional_jet.project.json'))`
runs the wing, body, tail and control-surface modules without a missing-slice
`ValueError`; `airloads` selects the AIRLOAD4 swept branch; the project round-trips
through `io.py`.

### Step P1-2 — Concept distributed-loads end-to-end + closure test suite
**Objective.** Drive `net_loads`, `body_loads`, `taildist`, `aileron`, `flap`,
`tab` through the P1-1 concept fixture and add **physics-closure assertions for
each** (today only the wing has a concept closure test in
`test_sbeam_bridge.py::test_concept_closure`): total lift = `n·W`; balancing tail
load reacts the wing-plus-inertia pitching moment about the CG; body net load
integrates to the applied inertia/airload distribution; each component's exported
nodal FORCE/MOMENT set sums to its root/total.
**Why.** Closure is concept mode's *only* validation (no printed oracle above
12,500 lb). It must actually run on a concept airframe, per component, or concept
results for tail/body/control remain unverified.
**Acceptance.** `tests/test_concept.py` (or per-module concept cases) asserts
closure for wing, body, tail and each control surface on the concept fixture; the
whole set exports cleanly through `sbeam_bridge`.

### Step P1-3 — True concept↔FAR23 identity test
**Objective.** Add a test that takes a GA project (`ga6_normal`), flips it to
`category="C"` with the equivalent explicit `chosen_n`/`chosen_nneg`, runs it
through the concept code path, and asserts the per-component loads match the FAR23
result within tolerance.
**Why.** The C-1 invariant ("concept reduces **exactly** to FAR23 on GA inputs")
is currently only *assumed* — asserted by the absence of regression on GA
fixtures, not verified through the concept branch. A direct identity test guards
the branch itself.
**Acceptance.** The GA-as-concept run reproduces the FAR23 loads (`rel_tol=1e-3`);
the test fails if any concept branch diverges on GA inputs.

### Step P1-4 — Complete the export package public API
**Objective.** Re-export the body and control-surface functions from
`farloads/export/__init__.py` (`__all__` today lists only wing + tail —
`body_span_load_csv`, `body_force_moment_cards`, `control_surface_csv`,
`control_surface_force_moment_cards`, their `write_*` variants, and
`case_index_csv`/`filter_by_selected_case_ids` are reachable only via the
submodule) and update the wing-only package docstring to describe all four
component families + the case index.
**Why.** A caller following the package API can currently export only wing + tail;
the concept deliverable is "all components to sbeam." Small change, real API gap.
**Acceptance.** `from farloads.export import body_force_moment_cards,
control_surface_force_moment_cards` works; a test imports the full surface.

### Step P1-5 — Concept engine gyroscopic rates: guard + warn — *approach chosen (D-2, 2026-07-16)*
**Objective.** `engine.py`'s `condition_25_371` uses a fixed FAR 23.371(b)
stand-in (2.5 rad/s yaw, 1 rad/s pitch) in lieu of the maneuver-derived 25.371
rates the tool does not solve. The moment is linear in body rate, so the fixed
rates are conservative *only while the concept's real rates stay at or below them*
— for an agile concept they under-predict silently, with no guard today.
**Approach (D-2, chosen 2026-07-16): guard + warn, keep the fixed stand-in.**
Keep the fixed 23.371(b) rates as the default; add a guard that emits a
`ConditionResult.note` + UI warning when the concept's inputs (or an explicit
user-supplied rate override) imply real pitch/yaw rates above 2.5 / 1 rad/s, so the
non-conservative case can never pass silently. No new envelope/rate-derivation math
(that would be the "solve for real rates" alternative, deferred). Accepts the
residual over-conservatism for slow transports (e.g. the D-1 regional jet's mount
is over-sized, not unsafe).
**Acceptance.** A concept whose implied/override rates exceed the fixed values
produces a load result carrying an explicit under-prediction warning; the GA/light
path is unchanged (no warning, oracle intact).

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
1.0); wire the recovered curve into `_vt_rudder_load` (~1% shift; needs a
re-baselined oracle check). *(Unblocked.)*

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

### 2-8 — Aero-coefficient curve plot (declined in E)
A CL–α / drag-polar / CM plot on Aerodynamic Data (with the recovered-CL closure
check) was reviewed and **not selected** (2026-07-15). Revisit if
coefficient-entry errors prove common.

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
