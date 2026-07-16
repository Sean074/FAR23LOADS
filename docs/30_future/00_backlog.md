# Backlog — Open Work & Development Plan

The authoritative list of **open** items: suite programs not yet ported, modern
additions, deferred refinements, open design decisions, and known defects — in
dependency order, as a step-by-step plan. The architectural rationale lives in
[`../10_standard/PROJECT_GUIDE.md §7`](../10_standard/PROJECT_GUIDE.md); the
per-module spec is [`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md); the
Phase-C narrative (locked decisions, schema, concept-mode invariants) is
[`01_concept_loads_plan.md`](01_concept_loads_plan.md); the Phase-D narrative
(GUI assessment, target six-section structure, locked decisions, page
conventions) is [`02_gui_workflow_plan.md`](02_gui_workflow_plan.md).

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

**Shipped:** Phases 0–2, Phase-C Steps **C0–C11**, and Phase-D **Step D0–D8**
(GUI defect fix; structured load-case IDs; six-section navigation restructure;
Start-page local-disk persistence; authoritative shared inputs + Aero
Coefficients page; Envelopes & Critical Conditions section; Analysis merged
into nine component pages; Loads Plots page; Export & report upgrades) and
Phase-E **Steps E1–E2** (FAR 23 applicability detection + `occupants`/`crew`
fields + OEW line; per-widget `help=` tooltips + parameter guides; shared
quantitative fleet comparison). Phase D (the six-section GUI restructure) is
complete; **Phase E** (GUI usability & concept-awareness) is underway — E1–E4
shipped, E5 queued below. **All 22** of Reference 1's
Appendix-C programs are ported (ENGLOADS, WTESTIMA, WTONECG, WTENV,
WINGGEOM, STRSPEED, MACHLIM, TAU, AIRLOADS, AIRLOAD4, FLTLOADS, SELECT, WINGINER,
NETLOADS, TAILDIST, AILERON, FLAPLOAD, TABLOADS, ONENGOUT, LGFACTOR, LANDLOAD,
BALLOADS), plus **2 modern modules** with no `.BAS` oracle (`configuration`,
`body_loads`).
Schema is at **`SCHEMA_VERSION = 22`**; 343 tests pass; coverage ~92%. The wing
distributed-loads vertical slice (geometry → speeds → envelope → airloads → inertia
→ net → sbeam export), the critical-load selection (wing / h-tail / v-tail /
fuselage), the chordwise tail distribution, the simplified control-surface
distributions (aileron / flap / tab), the one-engine-out vertical-tail transient
and the tricycle-gear landing/ground loads are complete (FAR23 path oracle-locked;
ONENGOUT and the LANDLOAD wheel-load table closure-locked — no legible printed
oracle exists for those).

**Remaining suite programs (0):** all 22 Appendix-C programs are ported (BALLOADS
shipped in Step C11). The FAR23 path stays oracle-locked (Appendix A/B ±0.1%);
concept mode is a superset that reduces exactly to it on GA inputs.

---

## Phase D — GUI workflow restructure (the active plan)

Reorganize the GUI from per-BAS-program pages into the six-section
loads-release workflow (Start → Airplane → Envelopes & Critical → Analysis →
Loads Plots → Export). Narrative, assessment findings, locked decisions D-1…D-7
and the page conventions are in
[`02_gui_workflow_plan.md`](02_gui_workflow_plan.md). **Gate met:** the `0.2.0`
release shipped 2026-07-08 (tag `v0.2.0` on `50e2c9c`, GitHub Release
published — release steps R1–R7, see `40_history/00_completed_development.md`);
Step D0 was a defect fix shipped **inside** that release (= release step R1).
Step D1 (structured load-case IDs) shipped 2026-07-08 — see
`40_history/00_completed_development.md` → "Phase D — Step D1". Step D2
(six-section navigation restructure) shipped 2026-07-08 — see
`40_history/00_completed_development.md` → "Phase D — Step D2". Step D3
(Start-page local-disk persistence) shipped 2026-07-09 — see
`40_history/00_completed_development.md` → "Phase D — Step D3". Step D4
(authoritative shared inputs + Aero Coefficients page) shipped 2026-07-09 —
see `40_history/00_completed_development.md` → "Phase D — Step D4". Step D5
(Envelopes & Critical Conditions section) shipped 2026-07-09 — see
`40_history/00_completed_development.md` → "Phase D — Step D5". Step D6
(Analysis merged into nine component pages) shipped 2026-07-09 — see
`40_history/00_completed_development.md` → "Phase D — Step D6". Step D7
(Loads Plots page) shipped 2026-07-09 — see
`40_history/00_completed_development.md` → "Phase D — Step D7". Step D8
(Export & report upgrades) shipped 2026-07-09 — see
`40_history/00_completed_development.md` → "Phase D — Step D8". **Phase D
(the six-section GUI restructure) is now complete** — no further Phase-D steps
are queued; remaining work is the deferred calc refinements and open design
decisions below. Invariant throughout Phase D: no calc-math change — the
Appendix A/B oracles pass unmodified at every step.

---

## Phase E — GUI usability & concept-awareness (the active plan)

Close the gaps a critical review of the airplane-definition GUI found (2026-07-15):
FAR 23 applicability is never detected or surfaced (a beyond-FAR23 airplane runs
GA-calibrated math silently); domain inputs carry no `help=` and there are no
parameter guides; graphical input-review and input-consistency validation are
concentrated on one page; the fleet comparison is visual-only and duplicated. The
target design and the standards these steps build to are in
[`../10_standard/GUI_design.md`](../10_standard/GUI_design.md); the Phase-D
structure/decisions they extend are in
[`02_gui_workflow_plan.md`](02_gui_workflow_plan.md). **Invariant:** no
calc-math change — the Appendix A/B oracles pass unmodified at every step;
concept mode reduces exactly to FAR 23 on GA inputs. User-approved directions
(locked 2026-07-15): warn-banner (non-blocking) for exceedance with a "switch to
Concept" action; `occupants` as a first-class field; `help=` tooltips + per-page
parameter guides; and the E3 graphical set (V-n + input-consistency + CG/mass).

### Step E5 — Load-path robustness (P2)
**Objective.** Make the sidebar project load fail gracefully and be schema-aware.
No schema change.
**Deliverables.** Wrap the sidebar `load_project` in `app/Home.py` with the same
graceful `st.error` the JSON editor uses; a soft `SCHEMA_VERSION` check (warn on a
newer file, migrate an older one) instead of a silent passthrough.
**Test/Acceptance.** Manual: a malformed / newer-schema file shows a message, not
a traceback; a valid older file still loads; full suite + `ruff` clean.

### Deferred / declined (Phase E)
- **Aero-coefficient curve plot** — a CL–α / drag-polar / CM plot on Aerodynamic
  Data (with the recovered-CL closure check) was reviewed and **not selected**
  (2026-07-15). Revisit if coefficient-entry errors prove common.
- **Distinct Commuter category** — splitting a Commuter (19,000 lb / 19-seat)
  category out of the merged "Normal / commuter" is non-blocking; revisit when a
  concept airplane needs the intermediate certificated tier represented cleanly.

---

## Deferred refinements (carried from shipped steps)

These do not block the plan above; close each under its own mini-step (history +
changelog entry) when done.

- **AIRLOAD4 swept spanwise printed oracle (from C7).** The swept branch is
  validated by the reduction invariant (Λ=0 / low Mach ≡ AIRLOADS exactly) and
  redistribution closure; matching a *printed* Appendix B swept spanwise table
  needs a legible swept fixture (the missing `examples/twin_turboprop.project.json`
  — see "Open design decisions"). Close as a mini-step when the fixture lands.
- **Flaps-extended chordwise tail rows (from C7).** TAILDIST reproduces all 13
  horizontal + 4 vertical Appendix A chordwise rows via `chordwise_pressures`, but
  the SELECT→TAILDIST pipeline emits only the 9 flaps-retracted horizontal
  conditions until the flapped V-n landing aero (the C6 deferral below) is added.
- **Flaps-extended tail-load printed oracle (from C6).** R3/R4 (flapped V-n
  envelope + flaps-extended balancing / gust) are **closure-validated**. Matching
  the printed Appendix A flaps-extended cases (81 / 106 / 88 / 108) needs the real
  landing-config aero polynomials and the CG5–7 loadings added to the fixtures.
- **Per-CG precise inertia in SELECT (from C6).** `Project.mass` is now persisted
  (WTONECG), but SELECT's checked-maneuver `Iyy` and v-tail `IZZ` still use the
  Ch 9 approximations (which match the oracle). Wire the persisted per-CG inertia.
- **V-tail large-deflection factor `EFV` → SELECT backfill (from C6/C9).** The legible
  large-deflection chart (Dommasch fig 12:3) now lives in
  `farloads/modules/_vtail.large_deflection_factor` (recovered for ONENGOUT, C9). SELECT's
  static v-tail rudder load still uses the `VTailLoadsInput.rudder_large_deflection_factor`
  input (default 1.0); wire the recovered curve into SELECT's `_vt_rudder_load` as a
  mini-step (it shifts the rudder-deflection load ~1%; needs a re-baselined oracle check).
- **ONENGOUT printed twin oracle (from C9).** C9 is closure- + sub-formula-locked because
  the printed Appendix B one-engine-out tables are **absent** from the bundled references
  (Appendix B is not in `reference/FAR23 loads (1).pdf`; FAA User's Guide Ch 22 gives
  partial inputs / no outputs). Add the printed ±0.1% oracle if a legible Appendix B (or an
  `ONENGOUT.OUT`) surfaces, alongside the `examples/twin_turboprop.project.json` fixture below.
- **LANDLOAD printed wheel-load oracle (from C10).** LGFACTOR and the LANDLOAD
  gear-geometry intermediates (K / GAMMA / ground angles / BETA / AP-BP-DP-CP) are
  oracle-locked, but the printed Appendix A wheel-load table (p231–233) is
  **OCR-garbled** in the bundled `reference/FAR23 loads (1).pdf`, so the 24-main /
  33-nose reaction matrix is closure- + legible-cell-locked (the ONENGOUT precedent).
  Add the printed ±0.1% oracle if a legible Appendix A/B or a `LANDLOAD.OUT`
  surfaces. The airplane-datum loads and unbalanced moments (PITCHP/ROLLP/YAWP) are
  computed but only closure-checked for the same reason.
- **Unify `select_wing`/`one_engine_out` case identity into their SELECT
  counterparts (from D1).** D1 mints wing `W-` ids on two independent,
  unlinked lists — `select_wing`'s `CriticalCondition`s and the
  `WingMassInput.cases` that actually drive WINGINER/NETLOADS — banded apart
  so they don't collide numerically but are not the same case object; same gap
  between `one_engine_out`'s own `VT-` id and `select_vtail`'s sequence. Closing
  this means wiring `WingMassInput.cases` to derive from `envelope.critical`'s
  wing conditions when not explicitly given (mirroring the fuselage/tail
  pattern) and linking `one_engine_out`'s result to `select_vtail`'s
  `CriticalCondition` list, so each component has exactly one case-ID
  authority end-to-end. Out of scope for D1 (flagged there as an accepted
  gap, not silently closed); needs its own oracle re-check since it touches
  which case list WINGINER/NETLOADS iterate.
- **Configuration seeding follow-ups (from C5)** → *subsumed by Phase D Step D4*
  (see above); the tasks are carried there verbatim, not duplicated here.

> The former "Modern UI niceties" section is absorbed into Phase D: Engineer &
> Date fields → D3, per-module graphics audit → D7, `.xlsx` workbook export → D8.

---

## Open design decisions

- [ ] **Test fixtures — Appendix B twin.** The swept tables (C7) and the ONENGOUT
  printed oracle (C9) want the 10-place twin turboprop (Appendix B) as a fixture. Today
  only `examples/ga6_normal.project.json` (Appendix A) and
  `examples/concept_heavy.project.json` (concept) exist; the engine module's Appendix-B
  turboprop case is encoded **inline** in `tests/test_engine.py`, not as a project file.
  **Blocked:** Appendix B is **not in the bundled `reference/FAR23 loads (1).pdf`** (it
  holds only the Appendix A GA single, physical pp. 128–247; Appendix C source from 248),
  so the twin geometry/loads can't be transcribed from the reference. *Needs a legible
  Appendix B (or the original `.INP`/`.OUT` files) before `examples/twin_turboprop.project.json`
  can be built.*
- [ ] **Standalone vs project-only inputs.** Maintain per-module example JSONs in
  addition to the full-airplane projects? *Default: full projects are canonical;
  per-module slices are derived for tests.*
- [ ] **sbeam VLM cross-check.** Build the optional sbeam-VLM backend to validate
  concept Schrenk distributions? *Default: out of Phase C; revisit after C8.*
- [ ] **Naming.** "FAR23LOADS" undersells the concept scope. Keep the name, or
  adopt a "Concept Loads" sub-brand? *(Non-blocking.)*

---

## Known defects

- _(none open — the flight-envelope destructive slice overwrite was fixed in
  Step D0 / release step R1, 2026-07-08; see
  `40_history/00_completed_development.md` → Resolved defects.)_
