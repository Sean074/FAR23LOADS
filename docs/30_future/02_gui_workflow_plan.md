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
   `flight_envelope.py` rebuilds `FlightLoadsInput` wholesale with
   `configurations=[cruise]` and `altitudes_ft=[altitude]` — opening the page
   deletes any flaps-down configuration or extra altitudes a loaded project
   carried. Recorded as a **known defect** (backlog) and fixed in Step D0.
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
- **D-2: Merge to nine Analysis component pages** (not merely regroup): Wing,
  Tail, Engine Out, Fuselage, Aileron, Flap, Tab, Engine Mount, Landing Gear.
- **D-3: Local-disk project persistence.** The app runs locally, so the landing
  page gains save/open against a projects directory (recent list, explicit Save
  to disk) while keeping browser upload/download. No autosave in this phase.
- **D-4: Release 0.2.0 first.** The GUI phase starts only after the pending
  `0.2.0` release is cut (with the D0 defect fix included), so the shipped
  Phase 1–2 + C0–C11 body of work is tagged before GUI churn begins. Deferred
  calc refinements stay open and land opportunistically.

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
- Payload/loading-scenario cases shared by the CG envelope and the flight
  envelope — Step D5.

## 7. Interactions with existing open work

- **Absorbs** the backlog's former "Modern UI niceties": Engineer & Date fields
  → D3; per-module graphics audit → D7; `.xlsx` workbook → D8.
- **Subsumes** the "Configuration seeding follow-ups (from C5)" deferred item —
  its tasks (stations → Weight DB, `XLEMAC`/`MAC` → WTENV/STRSPEED, engine
  write-back, true-CG refinement) become Step D4 tasks.
- **Prerequisite synergy:** the dedicated Aero Coefficients page (D4) provisions
  the flaps-down coefficient-set input that the deferred *flaps-extended
  tail-load / chordwise rows* refinements (from C6/C7) have been waiting on. It
  does not close them (they also need the CG5–7 fixtures / oracle work), but it
  removes their GUI blocker.
- **Multi-altitude V-n (D5)** is a GUI exposure of `FlightLoadsInput.altitudes_ft`,
  which is already a list in the schema; verify the calc loop handles >1 entry
  and add a regression test — no equation change expected.
- **No conflict** with the remaining deferred calc refinements (Appendix-B
  fixtures, swept oracle, per-CG inertia, EFV backfill, printed-oracle backfills)
  — they are calc-side and orthogonal; land them opportunistically per D-4.

## 8. Open items (non-blocking, decide during the phase)

- **Projects-directory location** for disk persistence (D3): a `projects/`
  folder beside the app vs a user-chosen path stored in app config. *Default:
  `projects/` in the repo working directory, git-ignored.*
- **Case-ID sequence stability across reruns** (D1): sequence numbers are
  assigned in a fixed, documented enumeration order (component, then the
  module's canonical condition order) so the same project always yields the
  same IDs; renumbering only occurs when the case set itself changes. Confirm
  this is acceptable vs. a persisted ID registry if it proves too volatile.
- **Comparison-import format** for the Loads Plots page (D7): start with the
  suite's own span-loads CSV schema; extend to a generic station/value CSV
  mapping later if needed.
