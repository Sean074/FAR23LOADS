# Phase D — GUI Workflow Restructure (development plan)

The GUI today is a faithful *per-BAS-program port*: one page per McMaster
program, each with its own inputs, defaults and downloads, grouped into the four
generic phases Define → Analyze → Review → Export. That was the right Phase-A/B
strategy, but it forces the user to know the 22-program suite to navigate an
airplane analysis. Phase D reorganizes the GUI around the **airplane and the
loads-release workflow** — without touching the oracle-locked calc.

This document is the Phase-D narrative (assessment, target structure, locked
decisions, invariants). The **step-by-step plan lives in
[`00_backlog.md`](00_backlog.md)** (steps D0–D8); the Phase-C narrative it
follows is [`01_concept_loads_plan.md`](01_concept_loads_plan.md).

---

## 1. Assessment — why the current GUI feels clunky

Findings from the 2026-07-08 GUI review (all against the shipped app):

1. **Flat navigation.** "1 · Define" is a wall of nine sidebar pages mixing two
   different ideas: *describing the airplane* and *deriving the load
   environment*. The Flight Envelope page is simultaneously an aero-coefficient
   input page, a weight/CG-case input page, and a V-n results page.
2. **No enforced single source of truth for shared inputs.** Wing area is asked
   on Structural Speeds, again on Flight Envelope, and defined again in
   Configuration & Layout; MAC and design weight likewise.
   `configuration_layout` is documented as the geometry source of truth but
   downstream pages don't read from it.
3. **The Appendix-A airplane is baked in as widget defaults.** A new user can
   click through every page and get a complete, plausible loads report for
   McMaster's 6-place single without ever entering their own airplane. Defaults
   belong in the loadable example project, not in `st.number_input(value=...)`.
4. **Pages write to the project on every widget tick, some destructively.**
   `flight_envelope.py` rebuilt `FlightLoadsInput` wholesale with
   `configurations=[cruise]` and `altitudes_ft=[altitude]` — opening the page
   deleted any flaps-down configuration or extra altitudes a loaded project
   carried. **Fixed in Step D0** (2026-07-08, release step R1):
   `FlightLoadsInput.merged()` merge-write + regression tests. The wider
   write-on-every-tick pattern remains for D6's form+Apply rework.
5. **Thin project management.** The loader is a `file_uploader` in the
   dashboard sidebar only; state lives solely in `st.session_state` (a browser
   refresh loses unsaved work); "save" is a download button.
6. **Single-altitude envelope, no speed–altitude chart, cruise aero only.**
7. **No consolidated loads-plots page.** Shear/moment plots are scattered
   per-module; no case overlays, no envelope curves, no comparison import, no
   total-loads view.
8. **No load-case naming.** The only ID in the system is `report.py`'s
   render-time `LC{idx}` — per-module, unstable under reordering, not unique
   across modules, and not traceable from a V-n point through SELECT to a
   component load case and its sbeam card. A loads release needs a stable case
   ID on every delivered case.

## 2. Target GUI structure (six sections)

Navigation stays driven from `farloads/workflow.py` (the single source of
truth), regrouped from four phases into six sections:

| # | Section | Pages (existing → target) | New work |
|---|---------|---------------------------|----------|
| 1 | **Start** (landing) | `dashboard` | Open/save against a local projects directory, recent-projects list, new-from-example, Engineer & Date metadata, whole-flow status board |
| 2 | **Airplane** | `configuration_layout`, `wing_geometry`, `weight_estimate`, `weight_cg_inertia`, `structural_speeds` | New **Aero Coefficients** page (extracted from `flight_envelope`); 3-view with mass items overlaid |
| 3 | **Envelopes & Critical Conditions** | `weight_envelope`, `flight_envelope`, `mach_limit`, `critical_loads` | Weight/CG grid + payload-cases page; speed–altitude chart with design speeds; V-n at multiple altitudes; critical-case selection by case ID |
| 4 | **Analysis** | 9 component pages: Wing Loads (= `airloads` + `net_wing_loads`), Tail Loads (= `tail_distribution` + `balanced_tail_verification`), Engine Out (`one_engine_out`), Fuselage Loads, Aileron, Flap, Tab, Engine Mount, Landing Gear | Merge per-program pages into component pages (locked decision) |
| 5 | **Loads Plots** | — (new) | Overlaid shear/moment/torsion by case ID, spanwise envelope curves, external-CSV comparison, total loads |
| 6 | **Export** | `export_report` | Case-index table in the bundle; `.xlsx` workbook |

Notes:

- `airloads` (Schrenk) moves from Define to the Wing Loads page — it is a wing
  analysis input, not airplane definition. The workflow-step `requires`/
  `produces` metadata is unchanged; only the grouping moves.
- The dashboard remains the default landing page; its per-step status logic
  (`requirements_met` / `is_produced`) is reused, re-grouped by the six sections.

## 3. Locked decisions (user-approved 2026-07-08)

- **D-1: Structured case IDs.** Every delivered load case carries a stable
  `case_id` of the form `<component>-<seq>` (`W-01`, `HT-03`, `VT-02`, `F-04`,
  `EM-01`, `LG-05`, …) assigned by the **calc** module (not the renderer), with
  traceability carried as separate fields (condition label, CG case, speed,
  altitude, FAR reference) — shown as columns in every table/CSV and as a
  comment on every sbeam card. A case-index table (ID → full definition) is a
  first-class export. `report.py`'s render-time `LC{idx}` is retired.
  **Sub-decisions locked 2026-07-08** (see `00_backlog.md` Step D1 for the full
  design): traceability lives in a new `CaseRef` dataclass (not inline fields);
  IDs are assigned once by the module that first names a physical condition and
  copied downstream, never re-minted; exactly six component prefixes, with
  control surfaces folding into their host (`W`/`HT`/`VT`/`F`/`EM`/`LG`, no
  separate `AIL`/`FLP`/`TAB`); stability comes from each module's existing
  fixed emission order (a pure function of project data), not a persisted
  registry. **Known accepted gap:** `select_wing`'s wing `CriticalCondition`
  list and `WingMassInput.cases` (which actually drives WINGINER/NETLOADS) are
  two independent case lists today: D1 mints `W-` ids on the WINGINER/NETLOADS
  path (the exported structural deliverable) and a separate `W-` sequence for
  `select_wing`'s own list, banded so they don't collide numerically but not
  unified as the same case object. Same caveat for `one_engine_out`'s `VT-` id
  vs. `select_vtail`'s. A follow-on backlog item unifies these; D1 does not.
- **D-2: Merge to nine Analysis component pages** (not merely regroup): Wing,
  Tail, Engine Out, Fuselage, Aileron, Flap, Tab, Engine Mount, Landing Gear.
- **D-3: Local-disk project persistence.** The app runs locally, so the landing
  page gains save/open against a projects directory (recent list, explicit Save
  to disk) while keeping browser upload/download. No autosave in this phase.
- **D-4: Release 0.2.0 first.** The GUI phase starts only after the pending
  `0.2.0` release is cut (with the D0 defect fix included), so the shipped
  Phase 1–2 + C0–C11 body of work is tagged before GUI churn begins. Deferred
  calc refinements stay open and land opportunistically.
- **D-5: Step D4 design decisions** *(locked 2026-07-09)*:
  - **Default-scrub scope.** D4's "remove Appendix-A widget defaults"
    (convention §5.4) applies only to the five Airplane-section pages plus the
    new Aero Coefficients page. `flight_envelope`/`weight_envelope`/
    `mach_limit`/`airloads` keep their Appendix-A-shaped literals for now —
    they clean up under D5/D6 when those pages get their own form+Apply
    rework, not as an early sweep.
  - **Aero-coefficient ownership.** Cruise/flaps-down `AeroCoeffSet`s move to
    a new `Project.aero_coeffs` slice owned by the new `aero_coefficients`
    module (Airplane section), not left nested inside `FlightLoadsInput`.
    `flight_envelope` (Envelopes section) reads it read-only — single owner
    per slice, even though the writer and the reader sit in different
    sections. `FlightLoadsInput` keeps only balance geometry and CG cases.
  - **Component-station mapping.** No new per-component station sub-model on
    `LayoutInput`. Stations for the Weight-DB seed (and, later, the three-view
    mass overlay) are **derived** by a pure function from `LayoutInput`'s
    existing coarse scalars (`le_root_x`, `h_tail_arm`, `v_tail_arm`, gear
    positions, …) — approximate but zero new required inputs; a user can
    still override any seeded `MassItem.x/z` by hand afterward.
  - **Engine three-view write-back.** In scope for D4 (not deferred), per the
    ownership rule already documented at `EngineInput.engine_cg` — implemented
    as numeric x/y/z override fields per engine rather than drag-and-drop
    markers.
- **D-6: Step D5 design decisions** *(locked 2026-07-09)*:
  - **Loading-scenario shape.** Manual weight/CG rows — the new Weight/CG Grid
    & Payload Cases page edits the same `CgCase` shape (name, weight, xcg, zcg)
    FLTLOADS already asked for, rather than deriving weight/CG automatically
    from toggled `weight.items`. Lowest risk, zero new derivation logic.
  - **Schema home for the shared CG cases.** `WeightInput.cg_cases` — kept
    alongside `weight.items`/`weight.envelope`. The calc-facing
    `FlightLoadsInput.cg_cases` field is **not removed**: SELECT, WINGINER,
    NETLOADS and BALLOADS all read it directly (a wider blast radius than the
    D4.1 `aero_coeffs` precedent, which had exactly one calc consumer), so
    those modules are untouched. The Flight Envelope page instead reads
    `weight.cg_cases` read-only and merges it into `FlightLoadsInput.cg_cases`
    on every Apply — one editable list, two places it flows to that "cannot
    diverge" because only one of them is ever edited.
  - **Speed–altitude chart placement.** Extends the existing Mach Limit page
    (VA/VC/VD/VF as `plotly` reference lines over the V(MC)/V(MNE)/V(MD)/V(FC)
    boundary already plotted there) rather than a new page.
  - **Critical-case selection scope.** Opt-out, default = full set. SELECT's
    per-(component, FAR label) governing condition is still fully automatic;
    the Critical Loads page adds per-condition checkboxes (default checked) so
    an engineer can drop a condition from the **Results Review** page's
    governing-loads summary. `CriticalLoadSet.selected_case_ids` is empty
    unless something has actually been deselected, so every existing project
    (and any project that never visits the page) behaves exactly as before.
    Deliberately scoped to the GUI summary only — WINGINER/NETLOADS,
    `body_loads` and the sbeam export bridge all keep reading
    `CriticalLoadSet.conditions` unfiltered, so a deselected condition can
    never silently drop out of a structural deliverable.
  - **Multi-altitude V-n display** *(engineering call, not asked)*: two
    selectors (CG case, altitude) plus an "overlay all altitudes" checkbox that
    plots one V-n trace per altitude, rather than a tab per altitude — reuses
    the existing single-chart pattern with the least new UI surface.
- **D-7: Step D6 design decisions** *(locked 2026-07-09)*:
  - **Merged-page nav-step representation.** Wing Loads (AIRLOADS+WINGINER+
    NETLOADS) and Tail Loads (TAILDIST+BALLOADS) each reuse the existing
    `FOLDED_MODULES` precedent (the same mechanism that already folds
    WINGINER's inertia loads into the Wing Loads page) rather than adding a
    `modules: Tuple[str, ...]` field to `WorkflowStep`. `"airloads"` and
    `"balloads"` stay independently registered calc modules with their own
    tests; they just have no dedicated nav step. Zero dataclass/test-shape
    churn; `dashboard.py`/`Home.py` needed no change since both already derive
    their content purely from `wf.STEPS`/`wf.by_phase()`.
  - **Engine Mount state-management normalization.** The page's separate
    `st.session_state["engine_inputs"]` store and its ad hoc local
    `Project(...)` (built only for compute/export, never merged back) are
    retired in this same step rather than deferred to a follow-on mini-step.
    It now reads/writes `Project.engines`/`Project.engine_layout`/
    `Project.include_far25` directly through `st.session_state["project"]`,
    matching every other page. An unapplied per-engine edit is discarded on
    engine/unit switch — this is the Phase-D form+Apply convention working as
    intended, not a regression; the old separate store existed specifically to
    paper over the lack of an Apply gate.

## 4. Invariants (unchanged from Phase C)

- **Calc math untouched.** Phase D adds identity/metadata fields and moves GUI
  code; no load equation changes. Appendix A/B oracles (±0.1%) must pass
  unmodified throughout (case-ID plumbing adds fields only, never values).
- **Ultimate-load output rules** (`CLAUDE.md`) apply unchanged: deliverables are
  ULTIMATE with `-ULT` units and per-case `SF`; per-module analysis pages may
  show LIMIT when explicitly marked.
- **Pure calc / thin shells.** Case-ID assignment lives in `farloads/` (pure);
  disk persistence lives in `io.py`/the view layer, never in calc.
- **`workflow.py` stays the single source of navigation truth**; the
  registered-module ↔ workflow-step test keeps guarding nav drift.

## 5. Page conventions (applied as each page is reworked)

1. **Inputs in the main body inside `st.form`** with an explicit
   **Compute / Apply** button; the sidebar is reserved for navigation plus the
   global project load/save widget.
2. **Apply merges into the project slice** — never wholesale-replace a slice
   that can carry more than the page edits (the D0 defect class).
3. **Shared quantities are read, not re-asked.** Wing area, MAC, weights, CG
   come from the authoritative slice (`configuration` / `geometry` / `weight` /
   `mass`), displayed read-only with an explicit per-page override when the
   original program allowed one. A page with missing upstream data says
   "define in section 2" instead of fabricating a default.
4. **No airplane-shaped widget defaults.** Numeric defaults are 0/blank or
   derived from the project; the Appendix-A values move to
   `examples/ga6_normal.project.json` (already exists) surfaced via
   "new from example" on the landing page.
5. **LIMIT-marked analysis views** keep the existing caption + `LIMIT` column
   marker convention and link to the ultimate deliverables.

## 6. Schema impact

Expected `SCHEMA_VERSION` bumps (older files must still load):

- `case_id` + traceability fields on `ConditionResult` (and the V-n /
  SELECT-critical records) — Step D1.
- Project metadata: `engineer`, `date` — Step D3.
- New `Project.aero_coeffs` slice (`cruise`/`flaps_down` `AeroCoeffSet`s moved
  out of `FlightLoadsInput`) — Step D4 (D4.1, shipped 2026-07-09,
  `SCHEMA_VERSION` 17 → 18).
- Payload/loading-scenario cases shared by the CG envelope and the flight
  envelope — Step D5, shipped 2026-07-09 (`SCHEMA_VERSION` 18 → 19):
  `WeightInput.cg_cases` (new field; older files migrate from
  `flight_loads.cg_cases` via `io._legacy_cg_cases_from_flight_loads`) and
  `CriticalLoadSet.selected_case_ids` (new field, additive, empty = unfiltered).

## 7. Interactions with existing open work

- **Absorbs** the backlog's former "Modern UI niceties": Engineer & Date fields
  → D3; per-module graphics audit → D7; `.xlsx` workbook → D8.
- **Subsumes** the "Configuration seeding follow-ups (from C5)" deferred item —
  its tasks (stations → Weight DB, `XLEMAC`/`MAC` → WTENV/STRSPEED, engine
  write-back, true-CG refinement) become Step D4.3–D4.6.
- **Prerequisite synergy:** the dedicated Aero Coefficients page (D4.2)
  provisions the flaps-down coefficient-set input that the deferred
  *flaps-extended tail-load / chordwise rows* refinements (from C6/C7) have
  been waiting on. It does not close them (they also need the CG5–7 fixtures /
  oracle work), but it removes their GUI blocker.
- **Multi-altitude V-n (D5, shipped 2026-07-09)** was a pure GUI exposure of
  `FlightLoadsInput.altitudes_ft`, already a list in the schema and already
  looped by `build_envelope` since Step C2 — confirmed by regression test
  (`test_multi_altitude_vn_regression`); no equation change.
- **No conflict** with the remaining deferred calc refinements (Appendix-B
  fixtures, swept oracle, per-CG inertia, EFV backfill, printed-oracle backfills)
  — they are calc-side and orthogonal; land them opportunistically per D-4.

## 8. Open items (non-blocking, decide during the phase)

- ~~**Projects-directory location** for disk persistence (D3)~~ — **closed
  2026-07-09**: `projects/` resolved from `farloads/io.py`'s own file location
  (repo root / `projects`), not the process cwd, so it's stable regardless of
  where `streamlit run app/Home.py` is invoked from. Git-ignored; created lazily
  on first Save. See `00_backlog.md` Step D3.
- ~~**Case-ID sequence stability across reruns** (D1)~~ — **closed 2026-07-08**:
  fixed, documented enumeration order (component, then each minting module's
  own canonical condition order), no persisted registry. See `00_backlog.md`
  Step D1 and the D-1 sub-decisions above.
- ~~**Comparison-import format** for the Loads Plots page (D7)~~ — **closed
  2026-07-09**: implemented against the suite's own span-loads CSV schema
  (`sbeam_bridge.span_load_csv`/`body_span_load_csv`), auto-detected by column
  set; a generic station/value CSV mapping remains a possible future
  extension, not needed for D7. See `00_backlog.md` → history, "Phase D —
  Step D7".
- **`xtc`/`xtf` (tail CP stations) page placement.** These stay on
  `flight_envelope.py` per the D-5 aero-ownership decision, even though they
  conceptually depend on flaps state (which now lives on the Aero
  Coefficients page). Not moved in D4; revisit if D5/D6 makes the split feel
  wrong in practice.
