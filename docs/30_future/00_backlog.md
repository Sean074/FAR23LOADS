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

## Phase D — GUI workflow restructure (the active plan)

Reorganize the GUI from per-BAS-program pages into the six-section
loads-release workflow (Start → Airplane → Envelopes & Critical → Analysis →
Loads Plots → Export). Narrative, assessment findings, locked decisions D-1…D-4
and the page conventions are in
[`02_gui_workflow_plan.md`](02_gui_workflow_plan.md). **Gate met:** the `0.2.0`
release shipped 2026-07-08 (tag `v0.2.0` on `50e2c9c`, GitHub Release
published — release steps R1–R7, see `40_history/00_completed_development.md`);
Step D0 was a defect fix shipped **inside** that release (= release step R1).
**Step D1 (below) is now the active step.** Invariant throughout: no calc-math
change — the Appendix A/B oracles pass unmodified at every step.

Definition of done per step (in addition to the file-top DoD where it applies):
pages follow the Phase-D page conventions (`02_gui_workflow_plan.md §5` —
form+Apply, merge-writes, read-don't-re-ask, no airplane-shaped defaults), and
the workflow-step ↔ registered-module test stays green.

### Step D1 — Structured load-case IDs (data model) — active

Decision D-1. The current `report.py` `LC{idx}` is render-time, per-module and
unstable — a loads release needs stable, traceable case IDs. **Sub-decisions
locked 2026-07-08** (user-approved, superseding the loose wording above):

- **Storage: a `CaseRef` dataclass**, not inline fields scattered across eight
  result types.
- **Propagation: assign once, carry downstream.** The module that first names a
  physical condition mints the `CaseRef`; every downstream stage copies that
  same object/id rather than re-minting.
- **Component taxonomy: fold into the host structural component.** Exactly six
  prefixes — `W` (wing, incl. aileron/flap/wing-tab), `HT` (horizontal tail,
  incl. htail-tab), `VT` (vertical tail, incl. vtail-tab, incl.
  one-engine-out), `F` (fuselage), `EM` (engine mount), `LG` (landing gear). No
  separate `AIL`/`FLP`/`TAB` prefixes; the control-surface identity lives in
  the `CaseRef.condition` label.
- **Stability: fixed enumeration order, not a persisted registry.** IDs are
  recomputed every run from each module's existing deterministic emission
  order (a pure function of the project's own data — no run-order coupling, no
  extra persisted state). This closes the "Case-ID sequence stability" open
  item in `02_gui_workflow_plan.md §8`.

#### 1. `CaseRef` + schema (`models.py`, `SCHEMA_VERSION` 15 → 16)

```python
@dataclass
class CaseRef:
    case_id: str            # "<component>-<seq>", e.g. "W-01", "HT-03"
    component: str          # "wing" | "htail" | "vtail" | "fuselage" | "engine_mount" | "landing_gear"
    condition: str          # human label, e.g. "PHAA", "down aileron", "sudden rudder"
    cg: str = ""
    speed_kt: Optional[float] = None
    altitude_ft: Optional[float] = None
    far_reference: str = ""
```

Add `case_ref: Optional[CaseRef] = None` to `ConditionResult`, `VnPoint`,
`CriticalCondition`, `WingLoadResult`, `BodyLoadResult`, `TailChordResult`,
`ControlSurfaceLoadResult`, `GearReactionCase`. All additive — older project
JSON loads with `case_ref = None`, back-filled the next time the project is
recomputed (no migration of stored results; only inputs persist across a
reload).

#### 2. `farloads/case_ids.py` (new, small, pure)

- `COMPONENT_PREFIX` — the six-entry map above.
- A tiny `CaseIdAllocator` (a per-call-site counter dict + `next_id(component)
  -> str`, formatting `f"{prefix}-{n:02d}"`). Each minting module creates its
  own allocator instance at the top of its build function — no shared/global
  state, so determinism comes from each module's own fixed iteration order,
  matching the "fixed enumeration order" decision.
- Numeric **banding** where one prefix has more than one minting module (only
  `W`, since aileron/flap/wing-tab fold into it per the taxonomy decision but
  run as separate modules from WINGINER/NETLOADS with no shared runtime
  state): reserve `W-01..W-49` for the WINGINER/NETLOADS structural cases,
  `W-50..W-59` for AILERON, `W-60..W-69` for FLAPLOAD, `W-70+` for a wing-hosted
  tab. Documented once here and in `case_ids.py`'s module docstring; bands are
  wide enough that no realistic case count collides. `HT`/`VT` need no
  banding — TABLOADS entries for those hosts are minted by SELECT/TAILDIST's
  own htail/vtail sequence (see below), not a separate module.

#### 3. Minting sites (in existing emission order — no loop reshuffling)

- **`select.py`** (`build_critical`): stamp a `CaseRef` on each
  `CriticalCondition` as `select_wing`/`select_htail`/`select_vtail`/
  `select_fuselage` append it, using one allocator per component scoped to the
  `build_critical` call. This covers `htail`, `vtail`, `fuselage` end-to-end —
  `taildist.py` and `body_loads.py` already iterate
  `_critical_set(project).conditions` directly, so they **copy**
  `cond.case_ref` onto the `TailChordResult`/`BodyLoadResult` they produce
  (pure propagation, no new IDs).
- **Known wing gap — flag, don't silently paper over.** `select_wing` mints its
  own `CriticalCondition` list (feeds the critical-loads summary table and the
  steady-roll torsion condition) but WINGINER/NETLOADS drive off
  `WingMassInput.cases` (`WingLoadCase`, still user/GUI-supplied per the
  pre-SELECT "C3 bridge" note in `models.py`) — **two independent wing case
  lists today, not one.** For D1: mint the `W-` ids on the WINGINER/NETLOADS
  path (the actual exported structural deliverable — `wing_net` +
  `export/sbeam_bridge.py`), in `wing_inertia.py`'s case-resolution helper
  (`_resolve_case`), keyed by the case's position in `wm.cases`; `net_loads.py`
  reuses the identical `WingLoadCase` object so `wing_air`/`wing_inertia`/
  `wing_net` for the same case agree without cross-module state.
  `select_wing`'s own `CriticalCondition` list gets its `W-` ids from a
  *separate* allocator inside `build_critical` (bounded by the `W-01..W-49`
  band together with WINGINER, so no collision, but no object-identity link
  either) — the two sequences can diverge in practice until the wing pipeline
  is unified. **Do not close this quietly**: add an explicit note to
  `PROGRAM_SPEC.md` and a code comment flagging it, and open a follow-on
  backlog item ("unify `select_wing` into `WingMassInput.cases`") rather than
  pretending the ID makes them the same case. `wing_air`'s single-`target_cl`
  path (no per-condition loop today) stays out of scope — it is an
  intermediate distribution, not itself a delivered case.
- **`engine.py`**: mint `EM-` ids in the existing per-condition loop
  (23.361(a)(1)/(2)/(3), 23.363, the 23.371(b) gyro block). The gyro condition
  expands into 4 sign-combination rows in `report.py`'s `_gyro_subcases` — mint
  4 distinct `EM-` ids there too (one per sub-case), since each is a distinct
  delivered load case.
- **`landing.py`** (LANDLOAD): mint `LG-` ids per `GearReactionCase` in the
  existing generation loop (24 main + 33 nose cases × CG cases). Keep the
  manual's own 1-based `case` number as-is for oracle/manual traceability
  (unrelated to the new `case_id`); the `CaseRef.condition` label carries
  `description`/`cg_name`.
- **`aileron.py` / `flap.py`**: mint `W-` ids from their own band
  (`W-50..W-59` / `W-60..W-69`) in their existing emission order (aileron:
  down/up; flap: the up-to-4 flaps-extended conditions).
- **`tab.py`**: mint from the host component's band per `TabSpec.surface`
  (`W-70+` for a wing tab; otherwise fold into the `HT`/`VT` sequence via its
  own allocator scoped to `build_tab_loads`, since tabs aren't SELECT-critical
  conditions).
- **`one_engine_out.py`**: mint its own `VT-` id (own allocator scoped to that
  module) continuing conceptually after SELECT's vtail sequence — same
  divergence caveat as wing applies here too (`select_vtail`'s ids and
  `one_engine_out`'s id are never numerically adjacent by construction, only
  by convention); note this in the same follow-on-backlog item as the wing gap.

#### 4. Retire `LC{idx}` (`report.py`)

- `load_cases_to_rows` / `results_to_rows` emit the `ID` column from
  `case_ref.case_id` when present (fall back to the current `LC{idx}` only for
  results with no `case_ref` yet, so nothing renders blank mid-rollout); add
  `Component`/`Condition`/`CG`/`Speed`/`Altitude`/`FAR` traceability columns
  sourced from `CaseRef`. CSVs, Review tables and the text report pick this up
  unchanged (they already iterate the same row dicts).

#### 5. sbeam export (`export/sbeam_bridge.py`)

- Stamp `case_ref.case_id` into the `$`-comment header of every
  `FORCE`/`MOMENT` card block (`_case_card_block` and the fuselage equivalent),
  next to the existing `SID`/`Nz`/`Nx` comment line.

#### 6. New export: case-index table

- A CSV (ID → component, condition, CG, speed, altitude, FAR reference),
  built from every `case_ref` on the current run's results, included in the
  export bundle and shown on the Export page (this is also D8 item 1 —
  implement it once here, D8 just surfaces it in the upgraded export page).

#### 7. Tests

- ID uniqueness across a full `run_all_modules` run (no two results share a
  `case_id`).
- Stability: two identical runs of the same project produce byte-identical
  `case_id` sets (guards the "fixed enumeration order" decision).
- Oracle values unchanged: existing Appendix A/B tests pass unmodified
  (`case_ref` is a new field, not a value change).
- The wing-gap divergence is itself asserted/documented in a test (e.g. a
  regression test that fails loudly, not silently, if someone later makes
  `select_wing` and `WingMassInput.cases` agree without updating this note).

#### 8. Docs sync (mandatory, same session per `CLAUDE.md`)

- `PROGRAM_SPEC.md` — the `CaseRef` result contract, the six-prefix taxonomy,
  the wing/one-engine-out numbering-divergence caveat.
- `PROJECT_GUIDE.md` — the case-ID convention (banding scheme, allocator
  pattern) for future modules.
- `02_gui_workflow_plan.md §8` — close the "Case-ID sequence stability" open
  item with the fixed-enumeration-order decision.
- This backlog: move Step D1 to `40_history/00_completed_development.md` and
  add the follow-on item "Unify `select_wing` into `WingMassInput.cases` /
  align `one_engine_out`'s VT sequence" to "Deferred refinements" when D1
  ships — the divergence is accepted for D1 but is not closed by it.
- `CHANGELOG.md` `[Unreleased]` entry; `SCHEMA_VERSION` bump note in
  `models.py`'s version-history comment.

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
