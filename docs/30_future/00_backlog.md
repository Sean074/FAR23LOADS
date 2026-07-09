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

**Shipped:** Phases 0–2 and Phase-C Steps **C0–C11**. **All 22** of Reference 1's
Appendix-C programs are ported (ENGLOADS, WTESTIMA, WTONECG, WTENV,
WINGGEOM, STRSPEED, MACHLIM, TAU, AIRLOADS, AIRLOAD4, FLTLOADS, SELECT, WINGINER,
NETLOADS, TAILDIST, AILERON, FLAPLOAD, TABLOADS, ONENGOUT, LGFACTOR, LANDLOAD,
BALLOADS), plus **2 modern modules** with no `.BAS` oracle (`configuration`,
`body_loads`).
Schema is at **`SCHEMA_VERSION = 15`**; 242 tests pass; coverage ~92%. The wing
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

## Release 0.2.0 — priority work (ships first; gates Phase D)

Cut the first post-0.1.0 release: `pyproject.toml` is still at `version = 0.1.0`
while the entire Phase 1–2 + C0–C11 body of work sits in `CHANGELOG.md`
`[Unreleased]` (~617 lines, ready to be dated). No git tag exists yet. Process:
[`../10_standard/RELEASE_PROCESS.md`](../10_standard/RELEASE_PROCESS.md).
Pragmatically cut **one `0.2.0`** for the whole body (MINOR-per-module would be
many bumps).

**Gate status (verified 2026-07-08):** `ruff check farloads/ cli.py` clean;
`pytest` 255 passed / 0 failed, coverage ~92%; Appendix A/B ±0.1% oracle tests
all pass; no `skip`/`xfail` needing a backlog note; `[Unreleased]` complete.

Remaining work, in priority order:

### R1 — Step D0 defect fix (the only code work) ✅ **done 2026-07-08**

Shipped: `FlightLoadsInput.merged()` (pure, `farloads/models.py`) +
`app/views/flight_envelope.py` persists through it; regression tests in
`tests/test_flight_envelope.py` (flaps-down config + two altitudes survive the
persist path); `CHANGELOG.md` `Fixed` entry; D0 moved to
`40_history/00_completed_development.md`. Suite 257 passed, ruff clean —
§3.2's no-open-critical-findings gate is met.

### R2 — GUI / CLI smoke test (§3.5)

`streamlit run app/Home.py` starts headless without error and renders a
representative project; `farloads engine examples/ga6_normal.project.json -o
out.csv` writes the expected load-case CSV.

### R3 — Docs-drift check (§3.1)

Review pass confirming `PROGRAM_SPEC.md`, `PROJECT_GUIDE.md` and
`20_theory/00_theory_sources.md` match the released code (they have been
maintained per-step; this is verification, not writing).

### R4 — Archive verification baseline (§4.4 — largest documentation task)

No permanent regression-baseline artifact exists yet. Create
`docs/40_history/01_verification_baseline_0.2.0.md`: one table per module —
condition → computed figure → Appendix A/B printed figure → reference page
citation — extracted from the test assertions (the data already lives in
`tests/test_*.py`). Note the closure-locked modules (ONENGOUT, LANDLOAD wheel
table, swept AIRLOAD4) as such rather than inventing printed figures.

### R5 — Version bump + changelog dating (§4.1–4.2)

Bump `pyproject.toml` to `0.2.0`; rename `[Unreleased]` →
`## [0.2.0] — YYYY-MM-DD` and open a fresh empty `[Unreleased]`.

### R6 — Tag & GitHub release (§4.3 — user-run)

`git tag -a v0.2.0 -m "Release v0.2.0"`, push the tag, create the GitHub
Release with the changelog entry as the body. *(All git actions are the user's
to run; prepare exact commands.)*

### R7 — Post-release (§5)

Remove this section from the backlog (→ history + changelog note of the
tag/date in `00_completed_development.md`); Phase D Step D1 becomes the active
step.

---

## Phase D — GUI workflow restructure (the active plan)

Reorganize the GUI from per-BAS-program pages into the six-section
loads-release workflow (Start → Airplane → Envelopes & Critical → Analysis →
Loads Plots → Export). Narrative, assessment findings, locked decisions D-1…D-4
and the page conventions are in
[`02_gui_workflow_plan.md`](02_gui_workflow_plan.md). **Gate:** Phase D starts
after the `0.2.0` release is cut (decision D-4; the plan is the **Release
0.2.0** section above); Step D0 was a defect fix shipped **inside** that
release (= release step R1, done 2026-07-08 — see
`40_history/00_completed_development.md`). Invariant throughout: no calc-math
change — the Appendix A/B oracles pass unmodified at every step.

Definition of done per step (in addition to the file-top DoD where it applies):
pages follow the Phase-D page conventions (`02_gui_workflow_plan.md §5` —
form+Apply, merge-writes, read-don't-re-ask, no airplane-shaped defaults), and
the workflow-step ↔ registered-module test stays green.

### Step D1 — Structured load-case IDs (data model)

Decision D-1. The current `report.py` `LC{idx}` is render-time, per-module and
unstable — a loads release needs stable, traceable case IDs.

1. Add `case_id: str` plus traceability fields (component, condition label,
   CG case, speed, altitude) to `ConditionResult` — or a small `CaseRef`
   dataclass it carries — and to the V-n points and the SELECT critical output.
   `SCHEMA_VERSION` bump; older files load with IDs back-filled on next compute.
2. Assign IDs in the **calc** modules as `<component>-<seq>` (`W-01`, `HT-03`,
   `VT-02`, `F-04`, `EM-01`, `LG-05`, …) in a fixed, documented enumeration
   order so the same project always yields the same IDs.
3. Retire `LC{idx}`: `load_cases_to_rows` / `results_to_rows` emit the `ID` +
   traceability columns from the data model; CSVs, Review tables and the text
   report pick them up unchanged.
4. Stamp the case ID as a comment on every sbeam `FORCE`/`MOMENT` card
   (`export/sbeam_bridge.py`).
5. New export: the **case-index table** (ID → full definition) as CSV, included
   in the bundle.
6. Tests: ID uniqueness across a full run, stability across two identical runs,
   oracle values byte-identical (fields added, values untouched). Docs:
   `PROGRAM_SPEC.md` (result contract), `PROJECT_GUIDE.md` (convention).

### Step D2 — Six-section navigation restructure (regroup only)

1. Rework `farloads/workflow.py`: replace the four phases with the six sections
   (Start, Airplane, Envelopes & Critical Conditions, Analysis, Loads Plots,
   Export); move `airloads` from Define to the Analysis group (metadata move
   only — `requires`/`produces` unchanged).
2. `app/Home.py` sidebar grouping + numbering follows automatically; update the
   dashboard's per-section status board.
3. No page merges yet (they land in D6); every existing page keeps working
   under its new section. Nav-drift test updated.

### Step D3 — Start (landing) page & local-disk persistence

Decision D-3. Absorbs the former "Home page — Engineer & Date fields" nicety.

1. Projects directory (default `projects/`, git-ignored; location noted in
   `02_gui_workflow_plan.md §8`): explicit **Save** writes
   `<name>.project.json` to disk; recent-projects list + **Open** on the
   landing page; **New from example** (`examples/*.project.json`); keep browser
   upload/download.
2. Global project load/save widget in the `Home.py` sidebar (every page), with
   an unsaved-changes indicator.
3. Project metadata: optional `engineer` and `date`, carried in the JSON
   (`SCHEMA_VERSION` bump) and shown on the text report and exports.
4. Disk I/O lives in `io.py` / the view layer only (never calc).

### Step D4 — Authoritative shared inputs + Aero Coefficients page

Applies the page conventions to the Airplane section. Subsumes the C5
"Configuration seeding follow-ups" (its tasks are items 3–4 here).

1. Downstream pages **read** wing area, MAC, design weights, CG from the
   authoritative slices (read-only display + explicit override where the
   original program allowed one) — kill the duplicate wing-area/MAC/weight
   entry on Structural Speeds / Flight Envelope.
2. Remove Appendix-A widget defaults from all pages (convention §5.4); the
   example project is the way to get the Appendix-A airplane.
3. Configuration → downstream seeding: push component stations into the Weight
   DB (WTONECG); set `XLEMAC`/`MAC` into WTENV/STRSPEED; `MassItem.x/z` station
   assignment (filling the zeros `estimate_to_mass_items` leaves) and engine
   write-back from the three-view.
4. Tail/prop ground-clearance refinement; true CG (rather than the 25%-MAC
   first cut) once a mass slice is present.
5. New **Aero Coefficients** page (Airplane section): owns the
   airplane-less-tail coefficient sets — cruise **and flaps-down** — extracted
   from `flight_envelope.py`. (Provisions the input the deferred flaps-extended
   refinements from C6/C7 have been waiting on; does not close them.)
6. 3-view with mass items overlaid (`configuration_layout`'s `_three_view()` +
   the weight DB).
7. Convert the Airplane-section pages to form+Apply with merge-writes.

### Step D5 — Envelopes & Critical Conditions section

1. **Weight/CG grid & payload cases** page: loading scenarios defined once,
   feeding both the CG envelope (WTENV) and the flight-envelope CG cases so
   they cannot diverge (`SCHEMA_VERSION` bump for the shared payload cases).
2. **Speed–altitude chart** with VA/VC/VD/VF and the Mach-limit boundary (data
   already in `speeds` + `speeds.mach_limit`).
3. **Multi-altitude V-n**: expose `FlightLoadsInput.altitudes_ft` as a real
   list; plot V-n per altitude (overlay or tabs); verify the calc loop handles
   >1 entry (regression test; no equation change expected).
4. **Critical-case selection by case ID**: the SELECT page persists the chosen
   governing set as case IDs on `envelope.critical`; Review/Export consume the
   selection.

### Step D6 — Merge Analysis into nine component pages

Decision D-2. Apply the page conventions as each page is merged; per-page LIMIT
displays keep the caption + `LIMIT`-marker convention.

1. **Wing Loads** = `airloads` (Schrenk) + `net_wing_loads` (air − inertia,
   shear/BM/torsion) on one page.
2. **Tail Loads** = `tail_distribution` + `balanced_tail_verification`.
3. **Engine Out** (`one_engine_out`), **Fuselage Loads**, **Aileron**, **Flap**,
   **Tab**, **Engine Mount**, **Landing Gear** — 1:1 conversions to the
   conventions.
4. `workflow.py` steps/keys updated (merged pages get merged steps); nav-drift
   test and the dashboard status board follow.

### Step D7 — Loads Plots page (new)

Absorbs the former "per-module graphics audit" nicety.

1. New consolidated page: pick a component → overlay shear/moment/torsion for
   selected **case IDs**; show the enveloped spanwise curve; total-loads view.
2. External-comparison import: start with the suite's own span-loads CSV
   schema (generic mapping later — `02_gui_workflow_plan.md §8`).
3. Graphics audit: confirm every plot the original program rendered (weight
   envelope, V-n, spanwise/shear-BM-torsion, Mach lines, three-view) has a
   Streamlit equivalent; close any gaps found.

### Step D8 — Export & report upgrades

Absorbs the former "`.xlsx` workbook export" nicety.

1. Case-index table (from D1) included in the export bundle and shown on the
   Export page.
2. Single multi-sheet `.xlsx` workbook (one tab per module/component) as an
   alternative to the `.zip`.
3. Exports honor the D5 critical-case selection (full set vs governing set).

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
