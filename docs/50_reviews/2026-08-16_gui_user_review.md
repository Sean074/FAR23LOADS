# User GUI review

**Status (2026-08-19):** in progress, issue #29.

*Decided and recorded inline, dated:* **Sidebar** (SIDE-1/2/3), **Start** (START-1…8 plus
8a/8b/8c), **Input** (INPUT-1/2), **Geometry rows 1–8**, **ENG** (1–4, plus the full
Engine Mount page inventory), **GEAR** (1–17) and **FUEL/PAY** (1–4 / 1–5), with the **surface
sweep** of WING / VTAIL / HTAIL in its own section below — **every written section of this
review is now swept.** *Still to write:* Flight loads, Other loads, Ground, Plotting, Export
(the owner's own observations are needed; the pages can be listed against `workflow.py` to
prepare the ground). No rulings are outstanding. Findings raised out of the sweep
have full bodies in **Design-note items raised during this review** (`[D]`, note-first) and
**Defects found during this review**, and are filed as issues, with the rest of this review's
findings, when #29 closes (rule 5).

*Three rules were agreed and now govern every row here:* **placement-only** (GR-INPUT-2 — a
"MOVE" is a widget move; the field stays on its dataclass, subject to the merge-write rule);
**planform primary, analysis scalars derived, an entered scalar wins and is marked**
(GR-GEOM-3); and, from the ENG sweep, **one owner per field, detected by a field-ownership
registry with a drift-guard test** — the duplicate-owner class (five instances found here)
gets one artefact, not one patch per instance (rule 4; see the structural note under
GR-INPUT-2).

**Nothing here is promoted yet.** The GUI freeze
([`2026-08-16_scope_and_deficiency_review.md`](2026-08-16_scope_and_deficiency_review.md) §Streamlit UI)
was carried past the **0.6.0 cut of 2026-08-17** and holds pending this review, whose
findings decide what re-opens. **Schema:** 0.7.0's single additive hop is reserved for L-7's
lateral inputs, so on current ordering rules the `[I]` rows below are **0.8**, not 0.7.0 —
the earlier "one 0.7.0 input-model step" no longer holds. The placement-only rule means most
rows once tagged `[I]` need **no** schema hop at all.

**Keys.** Every actionable row carries a section-scoped key `GR-<SECTION>-<n>`
(`SIDE`, `START`, `INPUT`, `GEOM`, `WING`, `VTAIL`, `HTAIL`, `ENG`, `GEAR`, `FUEL`,
`PAY`). Keys are stable citations for issues and PRs; they are not a priority order.

**Classes.**

| Class | Meaning | Closure tier |
|---|---|---|
| **[P]** | Placement / display only — no stored field, no calc change | S |
| **[I]** | Input model — a new, moved or re-owned stored field; schema consequence | L (one hop, 0.7.0) |
| **[D]** | Decision of record — resolved in a design note, merged at AGREED **before** code | note first |

Rows marked *(guard)* are satisfied by a drift-guard test rather than by a page
change, and can be written while the GUI freeze is in force.

---

## Sidebar -

**GR-SIDE-1** [P] **Restated and agreed 2026-08-18.** The sidebar carries **only what is
global to the project**: the page list (nav), Units, the unsaved-changes indicator and
Save, and About. All page-specific input moves into its page — the parametric geometry
set (`configuration_layout.py`), the V-n tail-CP / reference-Mach form
(`flight_envelope.py`), and the engine layout + "engine being assessed" selector
(`engine_mount.py`). The test is scope, not placement: project-global stays, page-local
moves.

Proposed moves (each decided below):
1) **GR-SIDE-2** [P] Units - move to Start / Project dash board. **Reversed, decided
   2026-08-18: the units control stays in the sidebar.** The selection applies to every
   page *and to every export*, so it belongs in global chrome for the same reason Save
   does (GR-SIDE-3). Nothing moves and nothing is built. See **GR-START-4**, which must
   not add a second control on the same `project.unit_system` field.
2) **GR-SIDE-3** [P] Project file - move to Start / Project dash board. **Split, decided
   2026-08-18:** Open / New from example / Upload move to Start; the **unsaved-changes
   indicator and Save stay in the sidebar on every page**. The sidebar widget owns the
   dirty guard (`_has_unsaved_changes` / `_confirm_discard` / `_load_with_guard`,
   `app/Home.py`), and taking Save away from the analysis pages is where a lost-work
   defect lands.

## Start

### Project Dash Board

THe top to bottom page layout

**GR-START-1** [P] EXISTING Summary of sloads - Current text is good.
**GR-START-2** [P] ADD Load project files.  Load existing example, user selected load, new file
— the arriving half of GR-SIDE-3 (Open / New from example / Upload only; Save and the
dirty indicator stay global).
**GR-START-3** [P] EXISTING Project name Engineer and Date - Good.
**GR-START-4** [P] ADD Units selection — **dropped 2026-08-19.** GR-SIDE-2 keeps the one
control in the sidebar; a second widget on `project.unit_system` is the double-definition
this review exists to remove. Nothing to build.
**GR-START-5** [P] EXISTING Description Filed - Good
**GR-START-6** [P] Work flow progress — **confirmed 2026-08-19, no change**; rendered as
rows per GR-START-8.
**GR-START-7** [P] REMOVE slices/produced, steps blocked, Schema version — **amended
2026-08-19.** "Steps blocked" goes (the per-row ⛔ already says it). The **progress
fraction stays** for now (may be removed later). **Schema version is moved, not deleted** —
it is the only place a user learns their file was migrated, so it belongs on the loaded-file
identity line beside the project file, where that question is actually asked.
**GR-START-8** [P] REARRANGE into rows
    Input Data: Geometry, Weight and Mass Props, Aero Data, Structural Speed, V-n Diagram
    Flight Loads: Wing, Fuselage, Tail (Vertical), Tail (Horizontal), Balaance Cases
    Other: Aileron, Flaps, Tab, Engine Mount, Engine Out
    Ground: Landing, Ground Handling
    Plotting: Load Plots
    Export: Comparison, Report, Export

**Checked against `workflow.py`'s 22 shipped steps, 2026-08-18.** "Input Data" and "Other"
match exactly (name change only). Three asks were hiding inside this [P] row and are split
out as **GR-START-8a/8b/8c** below; what remains here is the display change — progress as
rows not per-phase columns — plus the phase renames "Develop V-n diagram" → **Input**
(GR-INPUT-1) and "Landing loads" → **Ground loads** (GR-START-8b). Tier M, because
`workflow.py` is the nav SSOT and carries a drift guard.

**GR-START-8a** [P] Tail (Vertical) / Tail (Horizontal) as listed do **not** match the
shipped split, which is by *method*: `tail_loads` is SELECT's rational loads and
`tail_span_loads` the TAILDIST distribution, each running **both** surfaces off shared
`EmpennageInput` data. Splitting the pages by surface would mean two pages calling one
module with a filter. Do it as **vertical/horizontal sub-tabs inside each page** instead;
the pages are not split.

**GR-START-8b** [P] **Decided 2026-08-19: the phase is "Ground loads"**, holding
**ground handling and landing as two analysis sets** — and, in future, jacking. **No page
and no module split.** LANDLOAD is one solve (FAR 23.473–23.499, 33 cases, 40
`ConditionResult`s) and already labels every case with its family
(`modules/landing.py::_MAIN_FAMILIES` + `_NOSE_FAMILY`, one summary condition per family),
so the two sets are a **view over `far_reference`**:

  * **Landing** — 23.479(a) level (3-wheel, 2-wheel), 23.481 tail-down, 23.483 one-wheel,
    23.485 side load *(placed here as the side load during a landing; the one ambiguous
    family)*. Cases 1–12 and 19–24.
  * **Ground handling** — 23.493 braked roll (nose down, nose clear), 23.499 supplementary
    nose wheel. Cases 13–18 and 25–33.

  The case numbers **interleave**, so the split keys on `far_reference` and never on a case
  range. The rename is an accuracy fix in itself: braked roll and nose-wheel conditions are
  not landings. **Jacking (23.507) and towing (23.509)** are already declared
  `in_suite=False` in `report/coverage.py` and the ground-case kind enum is open for them
  by design — a new module in an existing slot, tier L with a stated closure gate (no
  Appendix A oracle), filed separately when wanted, not part of this row.

**GR-START-8c** [P]/[I] **Decided 2026-08-19.** *Project JSON Editor* is **retained as its
own page** but is **not listed on the dashboard** — a utility, not a workflow step. Hide it
by metadata (a `utility` flag on `WorkflowStep`), never by a key test inside `dashboard.py`,
which would put a second authority on the nav SSOT into a view. *Results Review* **is**
listed on the dashboard, and that page gains a **user concurrence check box** — "I have
reviewed these results" (concurrence, not approval: results are not certified). **[I], not
[P]:** a bare boolean stays ticked while the inputs change underneath it, asserting
something that has stopped being true. It stores `reviewed_by` + `reviewed_date` + **the
input state it was made against**, so the dashboard reads "reviewed" while it holds and
"reviewed *date*, inputs changed since" when it does not, and it prints on the summary
report's signature block beside the existing `revision` / `checked_by` / `approved_by`.
**`reviewed_by` appears in both places (agreed 2026-08-19):** entered on *Results Review*,
where the reviewing happens, and displayed in the dashboard's Document control block with
the other signatures, where they are read. Two consequences to expect: *Results Review*
stops being a derived view — it gains a slice to produce, so it takes a ✅/🟡 status and the
progress fraction's denominator moves — and the "inputs changed since" state needs the
input digest above to be computable, not just stored. *Results Review*'s own page content is
reviewed later.

## 1 - Develop V-n diagram **RENAME** Input

**GR-INPUT-1** [P] **RENAME** the step from "Develop V-n diagram" to "Input". **Decided
2026-08-19: the label is "Input"** (not "Input Data" as GR-START-8 listed it) — a bare noun,
parallel to "Flight loads" / "Other loads" / "Ground loads". **Nothing catches a missed
rename:** `tests/test_workflow.py` asserts each step's phase is *in* `PHASES` and that the
grouping order matches, never the literal strings. The phrase appears in ten files —
**sweep seven** (`sloads/workflow.py`, `app/Home.py`, `app/views/dashboard.py`,
`GUI_design.md`, `GUI_USER_GUIDE.md`, `PROGRAM_SPEC.md`, `03_gui_rework_plan.md`) and
**leave three alone** (`CHANGELOG.md` and the two `40_history/` files record what shipped
under the old name; history is not rewritten to match a later rename). Add a
`test_doc_currency`-family guard asserting the phase list in `GUI_USER_GUIDE.md` matches
`wf.PHASES`, so the next rename cannot silently strand the user guide.

**GR-INPUT-2** [I] the aim is to have all the airplane specific input defined here.  I.e. all geometry, Weights, engine power.  ANy analysis specif assumptions shall be on the page for that analysis (i.e. engine stoppage time, control sufface deflection limits)

**Amended 2026-08-19.** The rule stands — airplane-specific input lives in **Input**;
analysis-specific assumptions live on the page for that analysis — and it is the same test
as GR-SIDE-1 one level down. Three corrections from checking it against the schema:

  * **Control surface deflection limits are airplane data and stay in Geometry** (decided
    2026-08-19), so this row's own example is wrong and the GEOM rows are right
    (GR-VTAIL-11 rudder range, GR-HTAIL-14 elevator range). The distinction: the physical
    **stop limits** are a design characteristic like a hinge line, while the deflection
    *used in a given condition* is the assumption. Today's fields
    (`rudder_deflection_deg`, `elevator_te_up_deg`/`elevator_te_down_deg`,
    `flap_deflection_deg`, the aileron up/down pair) are full-throw limits — airplane data.
    **Engine stoppage time (`stop_time_s`) remains the good example** of the other kind.
  * **Decided 2026-08-19 — the rule governs *editing placement*, not storage.**
    `EngineInput` straddles the line in one dataclass: airplane data (engine weight, power,
    rpm, `prop_cg`, `prop_diameter_in`, `thrust_lb`) beside analysis assumptions
    (`stop_time_s`, `limit_load_factor`, the concept-mode rate guards). If only the widget
    moves and the fields stay where they sit, this row is **[P] with no schema hop**; if the
    model is reorganised to match the rule it is **[I]/L**. The difference is days against a
    release. **This row and every "MOVE …" row in this review are therefore [P] widget
    moves with no schema hop** — including the aileron/flap geometry that tab 2 of
    GR-GEOM-6 gathers while `AileronLoadsInput`/`FlapLoadsInput` keep owning the fields.
    Two boundaries: it does **not** cover genuinely new fields (fuel tanks, payload zones,
    thrust-line toe/pitch, wheels per gear, h-tail dihedral — still [I]), and it does not
    cover the unowned duplicates in GR-GEOM-2, which are defects, not placements.
    **Hazard to design for:** a page editing a field on a slice it does not own must obey
    the **merge-write rule** (`PROGRAM_SPEC.md`, `Project.weight` merge-write, fixed at
    Step D4.7/D5) — reconstruct the dataclass passing the *other* fields through unchanged,
    never omitted, or an untouched field silently resets to its default on save. That defect
    class is what placement-only re-opens, so every moved widget needs it.
  * **ANSWERED 2026-08-19 — GR-ENG grows.** The row's own list was short; the Engine Mount
    page inventory below (ENG section) splits all 25 of its inputs three ways. Engine
    *installation geometry* joins the Geometry engine tab; engine *mass* goes to Weight (and
    is folded into the inertia design note); engine *ratings* stay on the analysis page. The
    row does not narrow.

**Structural note — PROMOTED 2026-08-19.** GR-GEOM-2 (defined once), GR-GEOM-4 (all of it in
the JSON) and this row (edited in the right place) are three questions about one missing
artefact: a **field-ownership registry** naming, per input field, its owning slice and its
editing page. Built once, all three become drift-guard tests instead of discussions — which
is what `CLAUDE.md` rule 3 asks for. Writable today: no schema hop, and no dependency on the
entered-vs-derived decision (GR-GEOM-1/3).

The ENG sweep settled it. The registry is **the** fix for the duplicate-owner class, not one
patch per instance — `CLAUDE.md` rule 4 (generalize on first find). The class now has five
members found in this review alone:

| Field | Second owner | Held equal by | Measured today |
|---|---|---|---|
| `VTailLoadsInput.gross_weight_lb` | MTOW (G-14) | nothing | equal on every fixture |
| `TailLoadsInput.airplane_length_in` | entered twice | nothing | equal; zero effect today |
| `WeightEstimationInput.engines` | `engine_layout` / `len(engines)` | nothing | **`concept_heavy` 2 vs 0** |
| `EngineInput.limit_load_factor` | FAR 23.337 limit | nothing | equal to 5 decimals |
| `EngineInput.engine_weight_lb` / `engine_cg` | the weight DB (D-25 mass SSOT) | nothing | **regional jet 300 lb, 130 in apart** |

Each fix is different — derive, delete, single-source, fold into the mass model — but the
*detection* is one registry plus one drift-guard test. Instances get filed as issues pointing
at the registry, not as five independent defects.

### Geometry

**GR-GEOM-1** [I] All the geometry data is entered in this section. Including the Loads Reference Axis (LRA) definition. Geometry parameters should be user entered adn then related derived geometry that is used in analysis calculated.  Example, wing leading and trailing edge is defined, wing area is calculated.

**Agreed 2026-08-19 — the rule and its gates are recorded once, under GR-GEOM-3 below.**
This row's example ("leading and trailing edge is defined, wing area is calculated") is the
rule stated exactly; it already holds for the wing and now extends to the empennage and to
`LayoutInput.wing_area_sqft`.

**GR-GEOM-2** [I] *(guard)* CHECK parameters are not defined multiple time, there should be one location for all definitions.

**Answered 2026-08-19 by scanning `models/inputs.py`: 267 fields, 25 names shared by more
than one dataclass.** Most are legitimate namesakes (`name`, `x`, `y`, `z`, `weight_lb`,
`surface` on different objects). Nine are genuinely one physical quantity in two places, and
they split:

  * **Owned, with a documented derived copy — no action.** `wing_area_sqft` (owner
    `LayoutInput`; `FlightLoadsInput`/`LandingInput` marked "derived (M2-6); not persisted"
    and synced by `derived_geometry.sync_geometry_derived`), `mac` (same, with
    `WeightEnvelopeInput.mac` an `Optional` override), `dihedral_deg` (synced onto
    `WingMassInput`), and `main_gear`/`nose_gear`/`tread_in` (`LandingGearGeometry` owns;
    `LandingInput`'s copy resolved onto an effective input at run time, G6b).
  * **Unowned — no single source, no sync, nothing stopping them disagreeing:**
    `izz_slugft2` and `airplane_length_in` (**promoted to defect rows, below**),
    `taper_ratio` (`LayoutInput` entry vs `AeroSurfaceInput` "for TAU"),
    `shoulder_altitude_ft` (`MachLimitInput` vs `StructuralSpeedsInput`), and the
    `wing_surface` name pointer (`WeightEnvelopeInput` vs `StructuralSpeedsInput`).

The guard this row asks for is the **field-ownership registry** (see GR-INPUT-2): per input
field, its owning slice, its editing page, and whether it is a derived copy.

**GR-GEOM-3** [D] **DISCUSSION** Which geometry parameters should be user input and which should be calculated. The ORACLE named parameters should be preferred as user input.

### AGREED 2026-08-19 — the entered-vs-derived rule (with GR-GEOM-1)

**Rule.** Primary is what the airplane physically **is** — the planform. The analysis
scalars (`S`, `MAC`, `XLEMAC`, `XW`, `ST`, `ARHT`, `xt25`/`xt50`, `SV`, `ARVT`, `VMAC`,
`xv25`/`xv50`, and **`LayoutInput.wing_area_sqft`**) are **derived** from it. An entered
scalar stays legal, **wins**, and is **marked `entered`** wherever it is shown. Neither
representation is ever silently preferred.

**Why not one global direction.** The oracle *input* differs by surface, and both current
behaviours are already right: AIRLOADS / WINGINER / NETLOADS consume the wing **polyline**,
so the wing's oracle input is the planform (already derived — `derived_geometry
.wing_reference` + `sync_geometry_derived`); SELECT / BALLOADS consume `ST`/`ARHT`/`VMAC`/
`xt25`, so the tail's oracle input is the **scalars** (`tail_geometry._scalars` — "the
oracle-authoritative scalar slice"). A blanket rule either way breaks one of the two. This
row's original premise — "the ORACLE named parameters should be preferred as user input" —
therefore holds for the tail and is already inverted, correctly, for the wing.

**No new concept.** `ref_axis_pct`, `sob_y_in` and `vtail_root_waterline_z` already do
exactly this ("None → derived, marked assumed"). This generalises a pattern the codebase
converged on three times.

**Measured starting point (2026-08-19, all shipped fixtures).** The two descriptions already
agree, because #9's fixture-data pass made them agree:

| | area | span | 25 % MAC station |
|---|---|---|---|
| H-tail (4 fixtures with planforms) | ≤ 0.07 % | 0.00 % | ≤ 0.02 in |
| V-tail (same 4) | ≤ 0.05 % | 0.00 % | ≤ 0.06 in |
| Wing area, parametric vs planform | 0.00 % on five fixtures; **0.45 %** on `concept_regional_jet` (entered as a round 500.0 against a 497.75 planform) | | |

**No number moves anywhere on adoption** — every fixture keeps its entered scalars as
overrides, `concept_regional_jet` included, so the derived value is displayed beside the
entered one and never replaces it.

**Acceptance gates.**
1. **No oracle input changes.** Fixtures keep entered scalars as overrides; derivation is
   what a project *without* an entered scalar gets. This is what makes the 0.07 % margin
   against the ±0.1 % oracle tolerance irrelevant rather than something to lean on.
2. **Agreement asserted, not hoped for** — a test pins derived-vs-entered on every fixture
   at the values above.
3. **`tail_geometry.validate_tail_planform` stays a hard raise**, not a warning: it is the
   existing enforcement, and softening it would let the tail path describe two airplanes.
4. **Provenance always visible** — every scalar states derived or entered, on the page and
   in the export header.

**Tolerance (decided).** Reuse **`tail_geometry.PLANFORM_TOLERANCE` (1 %)** as the single
disagreement tolerance rather than inventing a third number. **Consequence to handle in the
same change (rule 3):** `validation._AREA_MISMATCH_TOL` (5 %) is a second tolerance for the
same question and must be retired onto the one constant, or this decision creates the very
duplication it exists to remove. `concept_regional_jet`'s 0.45 % passes either way.

**Out of scope of this decision.** No entered scalar leaves the schema; no calc changes; no
oracle is touched.

**GR-GEOM-4** [D] *(guard)* **DISCUSSION** Are ALL user defined parameters recorded in the project.JSON?

**Answered 2026-08-19.** Settle it permanently with a round-trip test: build a `Project`
with every field non-default, save through `io`, load, compare. `io.py` is the only
dataclass↔JSON mapping and `DATA_DICTIONARY.md` is already generated by something that walks
the model, so the enumeration half exists. **One catch before it is written:** the fields
marked `# not persisted` (the derived copies above) would legitimately *fail* a naive
round-trip, so the test must know which fields are exempt — the same **field-ownership
registry** GR-GEOM-2 and GR-INPUT-2 need. Three rows, one artefact.

**GR-GEOM-5** [D] **DISCUSSION** Is it required that the user "seed down stream pages"? Is this needed? Is the geometry only needed if the user wishes ot use the estimated component weight?

**Answered and decided 2026-08-19.** The section does **two unrelated things**, and neither
is what its caption claims:

  1. **Seed wing geometry (WINGGEOM)** — *generates* the wing planform polylines from the
     parametric layout, carrying a user-set LRA, spar fractions and side-of-body across. A
     generator, not a sync; it is the parametric→polyline direction of GR-GEOM-1/3 wearing
     a button.
  2. **Seed component stations into Weight DB** — fills `weight.items` x/y/z for items still
     at `(0,0,0)`, never overwriting a hand-entered station. The only place the Geometry
     page writes into the mass SSOT.

Neither is redundant: `sync_geometry_derived` covers something else — the read-only derived
copies (MAC/S/XW/ZW, wing-mass dihedral, fuselage summary) — and it runs automatically at
the top of every consuming module and after every load. **The caption is the actual defect**:
it implies the Weight-Envelope and Structural-Speeds pages need the button pressed before
they see MAC and wing area. They do not; that propagation is automatic.

**Decided: keep both actions, drop the "Seed downstream pages" framing, and re-site them** —
the planform generator into the **Wing** tab where the planform lives, the station seeder
onto **Weight & Mass Properties**, the page that owns the slice being written (GR-INPUT-2's
rule and D-25b's mass SSOT agreeing).

**Second question — no.** Geometry is not only needed for estimated component weight:
MAC/S/XW/ZW drive the FLTLOADS balance, the planform drives AIRLOADS/WINGINER/NETLOADS, the
gear geometry drives LANDLOAD, and the LRA drives the beam-model export. Only the *station
seeding* is a convenience.

**GR-GEOM-6** [P] This page shall have sub pages. **Closed 2026-08-19: `st.tabs` inside the
one page, not workflow steps.** `WorkflowStep.produces` is a *single* dotted path, so eight
steps all producing `geometry` cannot be expressed and the dashboard's completeness model
would break; tabs also keep the whole geometry slice under one owner (Step G1). The
952-line `configuration_layout.py` is the largest view in the app and this is the split it
needs. Two additions to the list below: the **main page is "Overview"** (assessment +
three-view, GR-GEOM-7/8), and the **fuselage outline gets its own tab** — the body sections
are edited on this page today and the list omits them.
1) main page — **Overview**
    * **GR-GEOM-7** [P] Assessment (Wing planform parameters, Vertical tail parameters, Horizontal tail parameters, longitudinal stability and landing gear geometry)

      **Closed 2026-08-19.** Every value on the Overview tab is **derived and read-only** —
      nothing is typed here, so no assessment figure can disagree with the tab that owns it
      (GR-GEOM-2 enforced by layout). Groups: wing, horizontal tail, vertical tail,
      landing gear, fuselage. Additions worth having: **tail volume coefficients V̄h/V̄v**
      (not computed today, trivial to derive, and the conventional first sanity check on an
      empennage) and **`assumed` markers** on values that came from a fallback — the fin
      root waterline (`tail_geometry.fin_root_waterline`) and the side-of-body
      (`derived_geometry.sob_station`) both announce themselves only in the exported deck
      header today, which is too late to be actionable.

      **One call made for you, reversible in a word: longitudinal stability splits.** The
      **neutral point** stays here — it is geometry. The **CG limits and static margin move
      to Weight & CG**, with tip-back and turnover (GR-GEAR-16/17), because they read the
      WTENV envelope from a *later* step: on a fresh project they would render blank, and on
      an edited one they can be stale against a CG envelope the user has since changed.
      Everything weight-dependent then lives on the page that owns the weight.

    * **GR-GEOM-8** [P] 3 view plot of the vehicle lift surface geometry, fuselage outline, LRAs, landing gear location both fully extended and compressed.

      **Closed 2026-08-19: read-only verification plot, extended — not an input surface.**
      A plotly three-view already ships (`configuration_layout.py:325`) with the CG, gear and
      control-surface bands, so this is an increment on shipped code, not new work. Add: the
      **LRAs** (wing, tail, fuselage centreline) as dashed lines, and a **front view**, which
      is the only one showing dihedral, track and fin height together and is the cheapest of
      the three to draw. **Gear: draw all three strut states, not two** — `LandingGearInput`
      carries compressed / static / extended, and *static* is the load-bearing one (the
      ground line derives from static axle `Z` − rolling radius). Static solid, compressed
      and extended ghosted. Labelled "verification only" on the page so it cannot be
      mistaken for an editable view.
*(Rows 2–4 below were swept against the agreed rules on 2026-08-19 — outcomes, and the two
`[D]` answers, are recorded once in **Surface sweep** after this list rather than repeated
per row.)*

2) Wing and Aileron And Flap
    * **GR-WING-1** [I] Symmetric flag
    * **GR-WING-2** [I] Leading edge definition (in wing reference plan)
    * **GR-WING-3** [I] Trailing Edge Definition (in wing reference plan)
    * **GR-WING-4** [I] twist definition root to tip
    * **GR-WING-5** [I] Dihedral of wing reference plane
    * **GR-WING-6** [I] LRA definition (% chord or two gird points in the wing reference plane)
3) Vertical Stabilizer And Rudder
    * **GR-VTAIL-1** [I] V-tail span
    * **GR-VTAIL-2** [I] V-tail tip chord
    * **GR-VTAIL-3** [I] V-tail root chord
    * **GR-VTAIL-4** [I] V-tail z root location (were the vtail intersect the fuselage)
    * **GR-VTAIL-5** [I] V-tail x root location (where the LE of the V-tail is)
    * **GR-VTAIL-6** [I] V-tail sweep
    * **GR-VTAIL-7** [I] V-tail LRA (default 25% chord)
    * **GR-VTAIL-8** [I] Rudder % chord at tip and % v-tail span (default 1.0)
    * **GR-VTAIL-9** [I] Rudder % chord at root and % v-tail span (default 0.0)
    * **GR-VTAIL-10** [I] Rudder hinge location (assume 90% rudder chord)
    * **GR-VTAIL-11** [I] Rudder deflection range
    * **GR-VTAIL-12** [P] MOVE Large deflection factor EFV (ADD explanation) to the tail loads analysis page.
    * **GR-VTAIL-13** [P] MOVE yaw inertia, gross weight to mass properties
    * **GR-VTAIL-14** [D] DISCUSSION Airplane Length LF, is this parameter pure geometric 25% WING MAC to 25% V-tail MAC, or the distance from the CG to the V-tail 25% MAC? If geometric defined/calculated here, else it should be calculated in the v-tail analysis for each weight and cg.
4) Horizontal Stabilizer and Elevator
    * **GR-HTAIL-1** [I] ADD type: T tail, conventional
    * **GR-HTAIL-2** [I] H-tail semi-span (tip to centerline)
    * **GR-HTAIL-3** [I] H-tail tip chord
    * **GR-HTAIL-4** [I] H-tail root chord (at centerline)
    * **GR-HTAIL-5** [I] H-tail z root location (were the h-tail intersect the fuselage conventional or v-tail for T tail)
    * **GR-HTAIL-6** [I] H-tail x root location (where the LE of the h-tail is at the centerline)
    * **GR-HTAIL-7** [I] H-tail sweep
    * **GR-HTAIL-8** [I] H-tail dihedral
    * **GR-HTAIL-9** [I] H-tail LRA (default 25% chord)
    * **GR-HTAIL-10** [I] H-tail incidence angle (assume fixed stab, may need to make this variable later or perform analysis at different setting angles, thus later development may require, max up and max down)
    * **GR-HTAIL-11** [I] Elevator % chord at tip and % v-tail span (default 1.0)
    * **GR-HTAIL-12** [I] Elevator % chord at root and % v-tail span (default 0.0)
    * **GR-HTAIL-13** [I] Elevator hinge location (assume 90% rudder chord)
    * **GR-HTAIL-14** [I] Elevator deflection range (trailing edge up and trailing edge down limits)
    * **GR-HTAIL-15** [P] MOVE Elevator effectiveness (ADD explanation) to the tail loads analysis page.
    * **GR-HTAIL-16** [P] MOVE Wing aero data (wing zer-life cruise, Wing zero-lift, Wing zero-lift, landing, wing lift slope AW)
    * **GR-HTAIL-17** [D] DISCUSSION Airplane Length LF, is this parameter pure geometric 25% WING MAC to 25% H-tail MAC, or the distance from the CG to the H-tail 25% MAC? If geometric defined/calculated here, else it should be calculated in the h-tail analysis for each weight and cg.
5) Engine
    * **GR-ENG-1** [I] Number of
    * **GR-ENG-2** [I] Location of prop (x, y, z)
    * **GR-ENG-3** [I] Thrust line (tow, pitch)
    * **GR-ENG-4** [I] propeller diameter

#### ENG swept — AGREED 2026-08-19

**The four rows.** Three are already stored and reclassify to `[P]`; one is genuinely new.

| Row | Where it lives today | Class |
|---|---|---|
| **GR-ENG-1** number of | stored **three** times: `Project.engine_layout` (`1N`/`2W`/`4W`), `len(Project.engines)` — tied to the layout by `Project.__post_init__` — and `WeightEstimationInput.engines` (NOENGS, Weight page), tied to nothing | `[P]` + duplicate-owner instance |
| **GR-ENG-2** prop location | `EngineInput.prop_cg` (XPROP/YPROP/ZPROP) | `[P]` widget move |
| **GR-ENG-3** thrust line (toe, pitch) | **absent** | `[I]`, 0.8 |
| **GR-ENG-4** prop diameter | `EngineInput.prop_diameter_in` | `[P]` widget move |

**GR-ENG-3 is the only input-model row, and the code wrote its own ticket.** Shipped
`balance.hub_thrust_set` (#10, 2026-08-17) says in-band: the P-6 incidence/toe angles
(`i_T`, `tau`) "have no fields and no estimator, and inventing them would put a lateral and a
vertical component into every case on an assumed geometry", so entered thrust is a pure `-x`
force *by declaration, not by geometry*. Two fields — `thrust_incidence_deg`,
`thrust_toe_deg`, both defaulting to `0.0` — make the existing consumer honest. **Gate:**
`0.0` reproduces today's `fx = -T` bit-for-bit, so the regression test is written with the
feature and every shipped fixture is unchanged (the same G-1 shape `test_hub_thrust.py` uses).
Design note 21 keeps the rest of the wake plan parked.

**The Engine Mount page inventory** (the reason GR-INPUT-2 does not narrow). All 25 inputs,
split by the GR-INPUT-2 rule:

* **→ Geometry (engine tab):** `engine_cg` x/y/z, `prop_cg` x/y/z, `prop_diameter_in`,
  `prop_blades`, `mounted_on` (fuselage/wing, BM-4), count/layout, and the two new
  thrust-line angles. All `[P]` except ENG-3.
* **→ Weight & Mass Properties:** `engine_weight_lb`, `prop_weight_lb`, `hub_weight_lb`,
  `prop_inertia`. **Not a plain widget move** — see the inertia design note, which these
  fold into.
* **Stays on the analysis page** (engine ratings and case inputs): `takeoff_rpm`,
  `max_cont_rpm`, `takeoff_hp`, `max_cont_hp`, `cylinders`, `max_engine_torque`,
  `cruise_torque`, `max_accel_torque`, `stop_time_s`, the rotor list,
  `design_yaw_rate_rad_s` / `design_pitch_rate_rad_s`, `thrust_lb`, and the two designations.
* **Neither — `include_far25` is project-level.** `Project.include_far25` is set from one
  analysis page's "Certification basis" block. By the GR-SIDE-1 logic it is project-global
  configuration and belongs with the project identity on **Start**. **DECIDED 2026-08-19: it
  moves to Start, together with `speeds.category`, and the boolean is reframed as a
  certification-basis selection** — see *Certification basis and the case manifest* under
  Design-note items.

**GR-ENG-1's fix has a precedent in its own dataclass.** M2-6 already single-sourced
`WeightEstimationInput.max_continuous_hp` from `sum(engines[].max_cont_hp)` with an explicit
`override_max_continuous_hp` flag. `engines` gets the same treatment — derive from
`engine_layout.expected_count` / `len(engines)`, keep the stored value as the older-file
fallback. Measured: agrees on four fixtures, **`concept_heavy` stores 2 against an empty
engine list** — benign there (no engine list, so the mount module cannot run) but it proves
nothing holds them equal.

**DECIDED — `limit_load_factor` (LIMNZ) is derived, not entered.** It is neither a geometry
input nor an engine-mount input: it is the FAR 23.337 limit manoeuvring load factor, already
owned by `structural_speeds.maneuver_load_factors(category, weight, chosen_n, chosen_nneg)`
and already read by `flight_envelope` (`flight_envelope.py:266`) and `app/components.py`. The
engine module reads that owner at the design gross weight; the user's entry point stays
`SpeedsInput.chosen_n`, where the 23.337 floor and the concept-mode bypass already live.

*Measured, and the reason this is zero-risk:* the derived value equals the entered value
**exactly** on all five fixtures — `ga6` and `cessna_210` 3.80000 vs 3.8, the three
concept-category fixtures 2.50000 vs 2.5, delta `+0.000 %` on every one. No oracle moves, so
this needs no approved-deviation trail; the gate is the equality itself.

| Item | Effort | Error risk |
|---|---|---|
| ENG-2/4 + prop_blades/mounted_on widget moves | S | Low — merge-write rule is the only hazard |
| ENG-1 single-source `estimation.engines` | S | Low — copy the M2-6 `override_` pattern |
| ENG-3 thrust-line angles | M | Low — `0.0` default is bit-identical |
| `include_far25` → Start | S | Low |
| LIMNZ derived from 23.337 owner | M | Low — measured `+0.000 %` on every fixture |
| engine mass → weight DB | **L, note first** | **High if rushed** — changes which weight sizes the mount |
6) Landing Gear
    * **GR-GEAR-1** [D] assume tricycle gear.
    * **GR-GEAR-2** [I] Nose gear axle location compressed: x, y, z (y assumed 0)
    * **GR-GEAR-3** [D] Nose gear axle location static: x, y, z. **DISCUSSION** is this calculated or user provided? Is it calculated for each weight and cg?
    * **GR-GEAR-4** [I] Nose gear axle location extended: x, y, z
    * **GR-GEAR-5** [I] Main gear axle location compressed: x, y, z
    * **GR-GEAR-6** [D] Main gear axle location static: x, y, z. **DISCUSSION** is this calculated or user provided? Is it calculated for each weight and cg?
    * **GR-GEAR-7** [I] Main gear axle location extended: x, y, z
    * **GR-GEAR-8** [I] Nose gear strut type
    * **GR-GEAR-9** [I] Main gear strut type
    * **GR-GEAR-10** [I] Nose gear rolling radius
    * **GR-GEAR-11** [I] Main gear rolling radius
    * **GR-GEAR-12** [I] Wheels per node gear
    * **GR-GEAR-13** [I] Wheels per main gear
    * MOVE to geometry main page assessment:
        * **GR-GEAR-14** [P] tread between mains calculated
        * **GR-GEAR-15** [P] track calculated
        * **GR-GEAR-16** [D] MOVE tip back angle calculated fully compressed and extended, to weight and cg page.  Need to be performed at a given weight and cg.
        * **GR-GEAR-17** [D] MOVE turn over angle static, to weight and cg page.  Need to be performed at a given weight and cg.

#### GEAR swept — AGREED 2026-08-19

**Eleven of the seventeen rows are already stored.** `GeometryInput.landing_gear`
(`LandingGearGeometry`, Step G6b) is the single source, holding both legs plus the tread:

| Rows | Field today |
|---|---|
| GEAR-2/4/5/7 compressed & extended, nose & main | `axle_compressed`, `axle_extended` — `(X, Z)` per leg |
| GEAR-3/6 static | `axle_static` — **also stored**; the `[D]`'s question already has an answer in code: *user provided* |
| GEAR-8/9 strut type | `strut` (`"O"` oleo / `"S"` spring) |
| GEAR-10/11 rolling radius | `rolling_radius_in` |
| GEAR-1 tricycle | already the documented restriction of the slice |

**The `y` the rows ask for needs no field.** Axles are `(X, Z)`; the butt line follows from
`tread_in`, which is LANDLOAD's own oracle input TREAD. Under GR-GEOM-3 tread stays primary
and axle `y = ±tread/2` is a derived display value (`gear_loads._leg_load` already computes
exactly that for the contact patch). **Caveat carried from `LandingGearInput`'s own docstring:
that is the *wheel* butt line and must never be confused with the trunnion butt line, which
is `attach.y` — a separately entered field (G-2).**

**DECIDED — GEAR-3/6, the static axle stays a GUI input.** Deriving it per weight and CG
needs a strut load-deflection curve the tool does not carry, and `axle_static` is LANDLOAD's
own oracle input — deriving it would move an oracle input to buy a fidelity the model cannot
supply. What the row's concern earns instead is a **check**: static must lie between
compressed and extended on both `X` and `Z`, warned by the validator, not silently accepted.

**DECIDED — GEAR-12/13, wheels per gear becomes an entered field.** Recorded with its
consumer state stated plainly: **nothing consumes it today.** LANDLOAD works per *leg*
(`VMP`/`VNP`, and `gear_loads` reports one patch per leg with the main's twin as a mirror),
never per tyre. It is therefore an input that is declared and displayed but does not reach a
delivered load, and that is the intended state — its consumer is a future **per-wheel
reaction split**, which is its own L-sized feature (a dual-wheel main currently puts the whole
leg reaction at one node). Filed this way so the field exists for the configuration record
without implying a per-tyre capability the suite does not have.

**GEAR-14/15 are nearly free.** Track is *already* derived — `configuration.gear_stations`
returns `track = tread_in`, G6b having retired the coarse `LayoutInput.track`. Tread itself
cannot be derived without an entered axle `y`, which would invert the primary. So **GEAR-15
is already implemented** and **GEAR-14 is a no-change row**; both are display lines on the
Overview assessment panel (GR-GEOM-7).

**GEAR-16/17 ride the inertia design note.** Tip-back and overturn already ship
(`configuration.py:547` and `:561`). They read **one** CG through `cg_estimate`, which takes
`project.mass.cases[0]` — and that function's own docstring records the deferral: *"once that
lands this should pick the representative case rather than always the first."* The move to
Weight & CG was decided under GR-GEOM-7; the *per weight-and-CG* half is blocked by the same
missing build step as Izz. **Listed as consumers of the per-payload-case inertia note, not as
separate design work** — that note now has three independent consumers (fin/ONENGOUT inertia,
engine mass, gear angles), which is what carries it.

**One managed duplicate — not a defect.** `LandingInput` carries its own
`main_gear`/`nose_gear`/`tread_in`. `landing._effective_gear_input` resolves the geometry copy
over them on every run (M2R-4, onto a local effective copy, no write-back), and measured on
all five fixtures they are **zero and never persisted to JSON**. That is an *owned* duplicate
— a field-ownership registry entry reading "vestigial, resolved from
`geometry.landing_gear`", not another instance of the unowned class. The one hazard is a
directly-constructed test `Project` that sets them and gets different behaviour from a GUI
project: a guard-test target.

| Item | Effort | Error risk |
|---|---|---|
| GEAR-14/15 display rows | S | Low — already derived |
| Axle `y` shown as ±tread/2 | S | Low |
| GEAR-3/6 between-states check | S | Low |
| GEAR-12/13 wheels per gear (no consumer) | S | Low — display only by construction |
| GEAR-16/17 per case | — | rides the inertia note |
| `carrier` + `attach` (gear reference point) widgets | **M** | Low to build, **high value**; tier M because the export's failure mode changes — see the defect body |
| `weight_lb` | — | moves to Weight & Mass Properties, on the inertia note |

7) Fuel volume
    * **GR-FUEL-1** [I] Number of tanks
    * **GR-FUEL-2** [I] For each tank: the four corners
    * **GR-FUEL-3** [I] For each tank: trapped fuel
    * **GR-FUEL-4** [I] For each tank: full fuel
8) Payload
    * **GR-PAY-1** [I] crew (part of OEW)
    * passengers
        * **GR-PAY-2** [I] number
        * **GR-PAY-3** [I] fuse station range for passengers
    * cargo
        * **GR-PAY-4** [I] number of cargo areas
        * **GR-PAY-5** [I] for each the fuse range for each cargo area

#### FUEL and PAY swept — AGREED 2026-08-19

**What this information is for.** Asked by the owner: *"is it to identify the area where these
are so that payload and fuel can be placed in the correct location in the weights page?"* Yes
— and it does four distinct jobs, which is what decides how much geometry to buy.

1. **Generating mass rows at a usable granularity.** Payload is hand-written lumps today: the
   ATR-42's 48 passengers are **two** rows (`Passengers, fwd cabin (24)` 4,080 lb @ x=350.1 and
   `Passengers, aft cabin (24)` 4,080 lb @ x=480.0), so the finest loading expressible is half a
   cabin — "12 forward, 36 aft" cannot be said. A station range plus seat pitch (GR-PAY-3)
   generates a row per seat row; cargo ranges (GR-PAY-5) do the same for holds.
2. **Making the CG envelope corners reachable — the real payoff.** D-25 records that on **5 of
   6 fixtures no combination of the item database reaches the entered CG corner** within a
   credible ballast fraction, which is why the loading became an explicit input. Coarse lumps
   are a direct cause: a handful of reachable CG points, with the corners falling between them.
   Finer granularity closes that gap, and under D-25a the loading is authoritative, so this
   feeds the weight/CG envelope rather than decorating it.
3. **Fuel CG that moves as fuel burns — today it does not.** `LoadingDefinition.fractions`
   scales a consumable row and its docstring is explicit that *"the station and inertias are
   unchanged"*: a half-full tank sits at the **full** tank's CG. Acceptable for a small
   centreline tank, increasingly wrong for a long wing tank. **This is the only job that needs
   the tank's *shape* rather than its location.**
4. **The wing/body fuel split becomes derived instead of hand arithmetic.** Fuel is one lumped
   row at `y = 0` and `MassItem.wing_fraction` (WF-2) splits it onto the wing beam. Measured,
   every fixture that uses it:

   | Fixture | fuel row × `wing_fraction` | 2 × concentrated "wing fuel" |
   |---|---|---|
   | `atr42_100` | 9,174 × 0.414214083 = **3,800.0** | 1,900 ×2 = **3,800** |
   | `dhc8_dash8` | 4,660 × 0.858369099 = **4,000.0** | 2,000 ×2 = **4,000** |
   | `concept_heavy` | 5,500 × 0.218181818 = **1,200.0** | 600 ×2 = **1,200** |

   Those nine-decimal fractions are hand-computed to reproduce the wing concentrated weight:
   **two owners of one split, held equal by arithmetic done by hand** — the sixth instance of
   the duplicate-owner class, and the only one with an obvious derivation waiting (tank extent
   against the side of body computes it).

   Related gap, worth knowing when this is scheduled: **`cessna_210`, `ga6_normal` and
   `concept_regional_jet` carry `wing_fraction = 0` and no wing fuel concentrated weight**, so
   all their fuel rides the fuselage beam and their wings receive **zero fuel bending relief**
   — on airplanes with wing tanks. Conservative rather than unsafe, but a fidelity gap that
   tank location closes.

**Already stored.** GR-FUEL-3 (trapped) and GR-FUEL-4 (full) largely exist as rows in every
fixture — `Unusable fuel`, `Reserve fuel`, `Fuel to gross`. What is missing is **per-tank
attribution**, not the quantities.

**DECIDED — the light version.** A tank is a **station and spanwise extent plus capacity**, not
a shape. It delivers jobs 1, 2 and 4, retires the hand-computed `wing_fraction`, and gives the
three zero-relief fixtures their wing fuel — with no volume-versus-level model. **Job 3
(fill-level CG) is explicitly out of scope**, and GR-FUEL-2's "four corners" is not taken:
corners buy only job 3, and the volume model they need is the cost. Recorded so that if a
long-tank concept later makes fill-level CG matter, the reason it was deferred is on file
rather than re-argued.

**Folded into the mass-model design note** (owner's call). FUEL/PAY do not get their own note:
a tank and a seat block are further **named installation items whose database rows must be
findable**, which is the same row-attribution mechanism the note already owes engine mass and
gear mass. Both groups are `[I]` with a schema hop, and both argue with the mass SSOT (D-25b),
so neither ships ahead of the note.

---

## Surface sweep — WING / VTAIL / HTAIL (2026-08-19)

Swept against the two agreed rules: **placement-only** (GR-INPUT-2 — the widget moves, the
field stays on its dataclass) and **planform primary, scalars derived, entered wins and is
marked** (GR-GEOM-3).

### Both LF rows answered — GR-VTAIL-14 and GR-HTAIL-17

`airplane_length_in` equals the **fuselage length exactly** on every fixture that sets it —
ga6 318.3 / 318.3, cessna 338.4 / 338.4, atr42 892.8 / 892.8, dash8 876.0 / 876.0, RJ
1056.0 / 1056.0 — against tail arms (`xv25 − xw`) of roughly half that. So LF is **neither**
option in the question: it is the airplane's longitudinal extent, used **only** in the
approximate inertia estimates, where `Iyy`/`Izz` treat the non-wing mass as a uniform rod of
length LF. **The tail arm is already a separate per-CG derived quantity** (`xt25 − XCG`;
`LXVT = (XV25 − XCG)/12`), computed per weight-and-CG case exactly as the rows ask. Nothing
is owed beyond deriving LF from the fuselage outline instead of entering it twice — the
defect row below.

### Already stored, entered here today — no change

`symmetric`, `leading_edge`, `trailing_edge` (WING-1/2/3); `dihedral_deg` (WING-5);
`vtail_root_waterline_z` (VTAIL-4, `0` → derived and marked assumed); `ref_axis_pct` with
`DEFAULT_REF_AXIS_PCT = 0.25` (WING-6, VTAIL-7, HTAIL-9 — the rows' "default 25 % chord"
exactly); `tail_type` (HTAIL-1); `htail_semispan_in` (HTAIL-2); `tail_incidence_deg`
(HTAIL-10); `elevator_te_up_deg`/`elevator_te_down_deg` (HTAIL-14 — already the pair).

### Decided by the entered-vs-derived rule — no new fields

VTAIL-1/2/3/5/6 and HTAIL-3/4/5/6/7 (span, root and tip chord, x and z root, sweep). The
entered planform gives them; `vtail_span_in`, `htail_semispan_in`, `xv25`/`xt25` and the
areas remain as marked overrides.

### Widget moves — [P], no schema hop

WING-4 wing twist (`AeroSurfaceInput.twist`, the (Y, zero-lift angle) polyline) onto the
Wing tab; VTAIL-12 `rudder_large_deflection_factor` (EFV) and HTAIL-15
`elevator_effectiveness` onto the tail-loads page; **VTAIL-13** `izz_slugft2` and
`gross_weight_lb` onto Weight & Mass Properties — **split 2026-08-19: this is the small
`[P]` half and ships independently.** Neither field is geometry, and both are on the
Geometry page only because Step G6 made the whole `VTailLoadsInput` slice editable there.
The substantive half — inertia becoming a **per-payload-case** derived output of the mass
model — is the `[D]` note above, and the widget move must not wait for it. HTAIL-16 the wing aero set onto
Aerodynamic Data. **HTAIL-16 is a genuine mis-homing** — `wing_zero_lift_cruise_deg` /
`_enroute_deg` / `_landing_deg`, `wing_lift_slope_per_rad` and `aspect_ratio_wing` are
*wing* aero living on the tail slice; **ARW additionally becomes derived** from the wing
planform under GR-GEOM-3. Every one of these obeys the merge-write rule.

### Genuinely new

* **HTAIL-8 h-tail dihedral** — no field exists. [I].
* **VTAIL-8/9/10 and HTAIL-11/12/13, control-surface %-chord and hinge.** Today a control
  surface is `rudder_area_sqft` / `elevator_area_sqft` plus `*_fwd_hinge_sqft` /
  `*_aft_hinge_sqft`, i.e. **the hinge line is implied by the areas**. **Decided
  2026-08-19: the %-chord description lands *alongside* the areas, with the areas
  derived from it and the entered area winning as a marked override** — the same shape as
  GR-GEOM-3, chosen because replacing the areas would change SELECT's own oracle inputs.
* **VTAIL-11 rudder deflection range — decided 2026-08-19: symmetric.** `rudder_deflection_deg`
  stays a single full-throw value applied ±; no asymmetric pair, no new field. (The elevator
  keeps its existing up/down pair, which is a real asymmetry.)

### Deferred with its reason on record

**GR-WING-6, the "two grid points" LRA — decided 2026-08-19: %-chord only for now.** Recording
why it will come back: on a tapered or swept wing a **constant-%-chord line is not straight**,
and the LRA is the elastic axis the exported beam model is built on, so `ref_axis_pct` cannot
express a straight spar for most real wings. The consumer that will force the issue is the LRA
beam exporter (note 24 R-7c / BM-3), which already refuses a `None` axis rather than assuming
one. [I]/L with its own gate when it is taken up.

---

## Design-note items raised during this review

`[D]`, note-first: agreed at AGREED before any code (`CLAUDE.md` rule 1).

### The mass-model note — the database owns mass and inertia, and each analysis reads its own case's

*Opened 2026-08-19 as "per-payload-case inertia"; grown by the ENG, GEAR and FUEL/PAY sweeps
into one note with a single central deliverable and five consumers. Scope, in the order the
review found them: (1) per-payload-case Ixx/Iyy/Izz, (2) engine mass, (3) gear leg mass,
(4) fuel and payload row generation, (5) the tip-back / overturn angles. All five need the same
missing mechanism — **a way to attribute a weight-database row to a named installation item** —
which is what the note actually designs; the consumers follow from it.*

#### Per-payload-case inertia — the item that opened the note

Raised by the user 2026-08-19: *"There should be only one Izz for each payload case… calculated
in the weight tab. Thus the analysis will use multiple Izz, Ixx, Iyy all dependent on the
payload and fuel."* Correct, and further from today's code than GR-VTAIL-13 implied.

**What is there now:**

| Inertia | Source | Per payload case? |
|---|---|---|
| `Iyy` (h-tail checked manoeuvre, 23.423) | slender-rod estimate `W_case·LF²/12/g × 0.44`, `modules/select.py:496` | Only through the case's **weight**; the mass distribution never enters |
| `Izz` (v-tail gust, 23.443) | `_default_izz(vt, gw)` — statistical, from MTOW, span and LF, computed **once outside** the case loop (`select.py:796`) | **No** — one value for every case |
| `Izz` (one engine out) | `_heaviest_case(project).izz`, from the mass model (`one_engine_out.py:404`) | **No** — the heaviest case only |
| `Ixx` | not consumed anywhere | — |

`MassCase` already carries `ixx`/`iyy`/`izz`/`ixz`, but **`mass.cases` holds exactly one
entry** ("itemized loading") against **7–8 `weight.cg_cases`** on every fixture:
`build_mass` does not loop over the cases. `VTailLoadsInput`'s own docstring records the
deferral in as many words — *"The per-CG IZZ override is a later refinement."*

**Why it sits on the Geometry page at all** — an accident, not a design. Step G6 made
`GeometryInput.empennage` the single source for tail inputs, and `VTailLoadsInput` mixes real
geometry (`SV`, `ARVT`, `VMAC`, `xv25`) with non-geometry (`izz_slugft2`, `gross_weight_lb`,
EFV), so editing the slice on that page dragged the inertia along.

**Enabling fact.** Since **D-25** every `CgCase` carries an explicit `LoadingDefinition` —
items aboard, fuel fractions, ballast — and every case of every fixture now states one. The
input a per-case inertia needs **already exists**; only the build step is missing.

**Shape.** `build_mass` emits one `MassCase` per `CgCase`; SELECT reads the inertia of
`cg_map[p.cg]`; ONENGOUT reads its own case's instead of the heaviest; the statistical
formulas survive as fallbacks for a project with no mass model; `izz_slugft2` (both copies)
stays an entered override.

**Payoff and risk, measured.** The **fin gust load barely responds** — 0.04–0.10 % for a
27–80 % Izz change, because `KGT` is saturated (see the Izz entry under Defects). The payoff
is **ONENGOUT**, where Izz enters **linearly** (`theta_2dot = moment / izz`), and any dynamic
work added later. The risk sits in the same place: moving ONENGOUT off the heaviest case will
move its numbers, so every oracle it touches is checked first and anything that moves needs
the approved-deviation trail (`docs/20_theory/02_approved_corrections.md`).

**Tier L** — new physics ownership plus a schema consequence on `Project.mass`. Design note
first. **This supersedes the Izz defect body below**, which is the symptom: the resolution is
not choosing between two airplane-level estimates but making the mass model the owner, per
case.

#### Folded in 2026-08-19 — engine mass belongs to the weight database (from the ENG sweep)

The Engine Mount page's `engine_weight_lb`, `prop_weight_lb`, `hub_weight_lb` and
`prop_inertia` are the same question as the inertia one — mass entered outside the mass SSOT
— so they are settled here rather than as a separate note. **D-25 makes the weight database
the mass SSOT**; these are a second, unowned copy of a mass row, and `engine_cg` is a second
copy of its station:

| Fixture | Engine Mount | weight-DB row | |
|---|---|---|---|
| `atr42_100` | 890 lb ×2 @ x=370 | `Engines (2)` 1,780 @ 370 | agree |
| `dhc8_dash8` | 1,050 ×2 @ 365 | `Engines (2)` 2,100 @ 365 | agree |
| `ga6_normal` | 505 @ 22 | `Engine install` 505 @ 22 | agree |
| `cessna_210` | prop @ x=**−12** | `Propeller` @ x=**0** | **12 in apart** |
| `concept_regional_jet` | 1,550 ×2 = 3,100 @ x=**980** | `Engines installed (2)` **3,400** @ x=**850** | **300 lb, 130 in apart** |

Four agree because they were typed twice, correctly. Nothing holds them. The mount is sized
by the Engine Mount figure while the airplane balances on the weight-DB figure, so on the
regional jet **the mount is currently designed for an engine the airplane does not have** —
first-order on a delivered load, which under `CLAUDE.md` rule 6 outranks every fidelity item
regardless of mission trace.

**Why it is not a widget move.** The weight DB lumps `Engines (2)` as one row, so per-engine
extraction needs a `component` tag plus a count convention before `EngineInput` can read its
mass from the database. That partition is the design work; the widget is incidental.

#### Folded in 2026-08-19 — gear leg weight, the same missing mechanism (from the GEAR sweep)

`LandingGearInput.weight_lb` (the whole leg, trunnion down, G-12a) moves to Weight & Mass
Properties by the owner's call, and lands here rather than in the GUI batch because it hits
the identical obstacle. `MassComponent` has **no GEAR member** (`WING`, `FUSELAGE`, `HTAIL`,
`VTAIL`), so a database row cannot be identified as gear — and `gear_loads` must find the
leg's mass to form its inertia term `weight × NVP`.

Adding `GEAR` to that enum is the wrong fix: `component` answers *"which beam reacts this
mass"*, which for gear is already answered by `carrier` (BODY → fuselage beam, WING → wing
beam), so a `GEAR` tag would leave `dhc8_dash8`'s wing-carried main gear unable to say its
mass rides the wing beam.

**So this note owns one mechanism serving three callers:** per-engine mass, per-leg gear
mass, and the per-case inertia build itself all need *a way to attribute a weight-database
row to a named installation item*. `MassComponent`'s docstring already rejected geometric
inference for this exact reason — every mass item in every fixture sits at `y = 0`, so
inference tags the whole database `FUSELAGE`. Designing that attribution once is the note's
central deliverable; the three consumers follow from it.

The current fallbacks stay honest in the meantime: `weight_lb` of `0.0` means **not stated**,
and the gear report prints the inertia term blank and says why rather than closing the free
body with a guess.

#### Folded in 2026-08-19 — fuel tanks and payload areas, light version (from the FUEL/PAY sweep)

The fourth consumer, and the one that supplies the note's *inputs* rather than reading its
outputs. Full reasoning under **FUEL and PAY swept**; what the note owes:

* **Tanks and payload areas are named installation items** — a tank, a seat block, a cargo
  hold — whose database rows must be findable. Identical to the engine and gear cases, so the
  attribution mechanism is designed once for all four.
* **Row generation, not row duplication.** A payload area (station range + pitch) and a tank
  (station + spanwise extent + capacity) *generate* `MassItem` rows; the database stays the
  mass SSOT and nothing here holds a second copy of a weight. This is the constraint that
  keeps the light version from becoming a parallel mass model.
* **`MassItem.wing_fraction` becomes derived.** Measured, all three fixtures that set it carry
  a hand-computed nine-decimal fraction reproducing the wing concentrated fuel weight exactly
  (`atr42` 9,174 × 0.414214083 = 3,800.0 = 2 × 1,900, and likewise `dhc8`, `concept_heavy`).
  Tank spanwise extent against the side of body computes it, retiring the sixth instance of
  the duplicate-owner class.
* **Granularity is the point.** D-25's finding — 5 of 6 fixtures cannot reach their entered CG
  corner from the item database — is caused in part by lumps like the ATR-42's two 24-passenger
  rows. Finer generated rows are what make the corners reachable, so this consumer is what
  makes the *loading* side of D-25a work, not merely tidier.

**Out of scope, with the number that parks it:** fill-level CG. `fractions` preserves station
by design, so a part-full tank sits at the full tank's CG; fixing that needs tank *shape* plus
a volume-versus-level model, and GR-FUEL-2's four corners are not taken. Deferred with the
reason on file so it is not re-argued — and flagged as the thing to revisit if a long-tank
concept makes the station shift material.

**Fidelity gap this closes on the way past:** `cessna_210`, `ga6_normal` and
`concept_regional_jet` put **all** their fuel on the fuselage beam (`wing_fraction = 0`, no
wing concentrated fuel), so their wings take zero fuel bending relief despite carrying wing
tanks. Conservative rather than unsafe — but the acceptance gate should state which fixtures
move and by how much, because these three will.

#### Prerequisite the note must clear — the mass database has no lateral arms

**Every mass row of every fixture sits at `y = 0`**: 21 rows / 37,781 lb on the ATR-42,
22 / 34,500 on the Dash-8 — 0.0 % of mass off the centreline, while the engines themselves
are entered at ±161 in and ±168 in. The `y` column exists and is editable in the weight
table, so this is **authoring, not schema**. But it decides whether a computed Izz is usable:

| Fixture | Izz in use (SELECT statistical) | engines at their true butt line would add |
|---|---|---|
| `atr42_100` | 335,513 slug-ft² | +16,784 (**+5.0 %**) |
| `dhc8_dash8` | 310,485 | +21,322 (**+6.9 %**) |

A Izz computed from the database as it stands comes out **systematically low on any twin**.
At 5–7 % this sits inside the base-method band (`theory_sources.md` §Base-method uncertainty,
5–10 %), so under rule 6 it does not rank as a fidelity item on its own — it ranks as an
**acceptance gate on this note**: the note cannot compute lateral inertia from a database
with no lateral arms. Butt lines on at least the off-centreline rows are a precondition, and
the fixtures need the data before the gate can pass.

---

## Defects found during this review

Raised 2026-08-19 out of GR-GEOM-2's duplicate scan and filed with bodies in the same
session (`CLAUDE.md` rule 5). Descriptive names, no new ID series; promoted to GitHub Issues
with the rest of this review's findings when #29 closes.

### One airplane, two yaw inertias — `izz_slugft2` has two owners and two different fallbacks

`VTailLoadsInput.izz_slugft2` (`models/inputs.py:1107`) documents `0 -> compute the default
IZZ` — SELECT's statistical estimate
`IZZ = (Wwing/g)·B²/12 + ((0.62·GW − Wwing)/g)·LF²/12` with `Wwing = 0.09·GW`.
`OneEngineOutInput.izz_slugft2` (`:1356`) documents `0 -> from Project.mass (heaviest case)`
— the assembled mass model. Both default to `0`, **no shipped fixture enters either**, so
every fixture runs the two analyses on two different inertias for the same airplane:

| Fixture | Izz, SELECT statistical | Izz, mass model | Ratio |
|---|---|---|---|
| `ga6_normal` | 4,173 | 3,022 | 1.38× |
| `cessna_210` | 5,350 | 2,626 | 2.04× |
| `atr42_100` | 335,513 | 66,597 | 5.04× |
| `dhc8_dash8` | 310,485 | 84,902 | 3.66× |
| `concept_regional_jet` | 384,316 | 209,382 | 1.84× |

slug-ft², mass-model values converted with `constants.LBIN2_PER_SLUGFT2`.

**What this is not.** Not "the vertical tail is wrong": SELECT's statistical formula is
**oracle-locked** — McMaster's own, reproducing Appendix A — so a fix that makes the v-tail
read `Project.mass` moves a locked number and is out of bounds without the full approved-
deviation trail. The defect is that one airplane carries two Izz values, differing by up to
5×, with **no statement of which is authoritative and no check that they agree**.

**Superseded 2026-08-19** by *Per-payload-case inertia* under **Design-note items** above:
the resolution is not choosing between two airplane-level estimates but making the **mass
model the owner, per payload case**, with both fields surviving as entered overrides. This
entry stays as the symptom and as the band evidence below.

**Interim, if the note is not taken up soon.** Report the mass-model value beside SELECT's,
with a `consistency_warnings` finding when the two disagree beyond a stated tolerance — the
`area_mismatch` shape, which already does exactly this for wing area. Reporting only; the
SELECT default stays bit-for-bit and no schema field is added.

**Band (rule 6) — measured 2026-08-19: parked with the number.** Running `select` twice per
fixture, once on each Izz, an input change of **−27 % to −80 %** moves the **delivered** fin
side-gust load by **+0.04 % to +0.10 %**:

| Fixture | Izz change | Total tail load, side gust (cp 25 %) |
|---|---|---|
| `ga6_normal` | −27.6 % | 603.99 → 604.20 lb (+0.04 %) |
| `cessna_210` | −50.9 % | 555.79 → 556.02 (+0.04 %) |
| `atr42_100` | −80.2 % | 4139.69 → 4143.99 (+0.10 %) |
| `dhc8_dash8` | −72.7 % | 4527.13 → 4531.86 (+0.10 %) |
| `concept_regional_jet` | −45.5 % | 7082.53 → 7089.96 (+0.10 %) |

The cause is saturation: `KGT = .88·UGT/(5.3+UGT)` sits near its 0.88 asymptote on these
airplanes, so the alleviation factor barely responds to the radius of gyration. Against the
base method's own 5–10 % band this is **far below the bar** — hygiene, not a sizing defect,
and it does not outrank anything.

**What the measurement rules out.** Do **not** reconcile by changing the calc. Pointing
SELECT at the mass-model Izz moves the Appendix A fin gust load 0.04 % — inside ±0.1 %, but
spending 40 % of the oracle tolerance budget on a cosmetic consistency change is the wrong
trade, and it would need the approved-deviation trail. The reverse is worse: ONENGOUT uses
Izz **linearly** (`theta_2dot = moment / izz`), so pointing *it* at the statistical value
would move its yaw acceleration by up to 5×. Report both, warn on disagreement, leave both
defaults alone.

### One airplane, three gross weights — `VTailLoadsInput.gross_weight_lb` restates MTOW

Raised 2026-08-19 from the GR-VTAIL-13 sweep. `VTailLoadsInput.gross_weight_lb`
(`models/inputs.py:1106`) is documented `GW (IZZ default; 0 -> use the heaviest CG case)`,
but decision **G-14** made **MTOW a single input on `WeightInput`** (`max_takeoff_weight_lb`),
read through `sloads.cg_cases`. The v-tail slice is a third independent statement of the same
weight.

**Effect on shipped output today: zero, and entered.** Every fixture sets it, equal to MTOW
exactly — ga6 3400, cessna 3800, atr42 36817, dash8 34500, RJ 33000. **The hazard is the
blank case:** left at `0` the field falls back to *the heaviest CG case*, which is not what
MTOW names — the same class of latent defect G-4 removed from `LandingInput`, where a
`gross_weight_lb` fallback picked MLW instead of MTOW and understated cases 13–24 by ~5 %.

**What ships.** The field becomes a derived copy of `WeightInput.max_takeoff_weight_lb`
refreshed by `sync_geometry_derived`'s pattern, with an entered value surviving as a marked
override and an equality guard test; the widget moves to **Weight & Mass Properties**
(decided 2026-08-19, GR-VTAIL-13), which is the page that owns the weight. Tier S — no
number moves on any shipped fixture.

### One airplane, two lengths — `airplane_length_in` is entered twice

`TailLoadsInput.airplane_length_in` (`:1056`, feeds the approximate `Iyy` for the 23.423 /
23.425 horizontal-tail searches) and `VTailLoadsInput.airplane_length_in` (`:1103`, feeds
`IZZ`) are the same physical airplane length, entered independently.

**Effect on shipped output today: zero.** Every fixture that sets it writes the value twice,
identically — `ga6_normal` 318.264 / 318.264, `cessna_210` 338.4 / 338.4, `atr42_100`
892.8 / 892.8, `dhc8_dash8` 876.0 / 876.0, `concept_regional_jet` 1056.0 / 1056.0. The
defect is that **nothing holds them equal**: a user editing one page gives the airplane one
length in pitch and another in yaw, silently.

**What ships.** One owner (the geometry slice, derivable from the fuselage outline), the two
slice fields becoming derived copies refreshed by `sync_geometry_derived` — the pattern
`wing_area_sqft` and `mac` already use — with an equality guard test. Tier S; no number
moves on any shipped fixture, which is exactly why it is cheap to do now and awkward later.

### Three gear fields the GUI cannot reach — `carrier`, `attach`, `weight_lb`

Found 2026-08-19 in the GEAR sweep. `LandingGearInput.carrier` (G-2),
`.attach` (the trunnion / G-12 gear reference point) and `.weight_lb` (the whole leg,
trunnion down, G-12a) are populated in **every shipped fixture by hand in the JSON**, and are
editable on **no page** — `GearCarrier` does not appear anywhere under `app/`.

**What they do.** LANDLOAD computes where the *ground* pushes; these three say where that load
goes. Worked example, `ga6_normal` case 1 (3-wheel level landing, 23.479(a)), main leg:

| | |
|---|---|
| contact patch (ground pushes here) | `(96.9, 57.2, 47.9)` |
| `attach` — trunnion node | `(96.2, 6.0, 66.0)` |
| `carrier` | `BODY` |
| ground-line reaction (V, D, S) | `(3144, 1020, 0)` lb |
| transfer couple, patch → node | `(164430, -16514, -40753)` lb-in |
| `weight_lb` | 77.5 lb |
| leg inertia term, `weight × NVP` | 245.4 lb |

* **`attach`** — 23.485(d) puts the reaction at the tyre patch, but the airframe feels it at
  the attachment, so the export carries it up the leg (`gear_loads.transfer_couple`). Here
  that is 51 in of butt line and 18 in of waterline — a 164,000 lb-in couple that does not
  exist if the point is not entered.
* **`carrier`** — BODY or WING: which beam the leg ties into, and where WING, the attach point
  is additionally resolved onto the wing loads reference axis so a gear torsion is stated
  about the same axis as every other wing torsion. Four fixtures BODY; `dhc8_dash8`'s main
  gear WING. This is the one of the three that *can* be inferred — from the attach butt line
  against the side of body — and is marked ASSUMED when it is (BM-4).
* **`weight_lb`** — closes the free body: 3,144 lb up at the patch minus `weight × NVP` is
  what arrives at the trunnion. `0.0` means **not stated**, distinct from weightless — the
  report prints the inertia term blank and says why rather than closing the free body with a
  guess.

**Measured cost of the gap.** Blanking the three on `ga6_normal`, as a GUI-built project has
them:

| | gear nodes in the exported LRA model |
|---|---|
| fixture as shipped | **3** |
| GUI-only equivalent | **0** |

— with two `assumed_notes` lines the only warning. A project built entirely through the GUI
exports a ground model with **nowhere to attach the gear reactions**. First-order on a
delivered deck, so under `CLAUDE.md` rule 6 it outranks every fidelity item here.

Note the shape of the failure: `attach` blank **omits the node silently** (a note, not a
refusal), while a blank `carrier` is inferred and marked. All three exist precisely because
the suite refuses to guess them — and then the GUI never asks.

It also answers GR-GEOM-4 concretely: reachability is not "is it in the JSON" but "can the
GUI write it".

#### What ships — AGREED 2026-08-19, after the owner's statement of purpose

The owner's framing settles the shape: *"the beam model will connect the reference point to
the CARRIER with an element. The export bdf function would move the gear loads from the
contact patch to the reference point … so that the model does not have multiple load
application points for the landing gear applied load. Thus the user needs to define the
reference point."*

**That machinery is already built.** `balance.py:2292` emits, in-band, "gear reactions are
transferred from the tyre contact patch to each leg's own reference point … with the
lever-arm couple, so the load at the node has the identical resultant it had at the patch".
The transfer, the couple and the one-node-per-leg rule all ship. **The only missing piece is
the GUI to define the point** — which raises the value of the fix rather than lowering it:
the machinery is idle for want of a number field.

1. **`attach` becomes a required field, and the export refuses without it.** If the element
   from reference point to carrier cannot exist without the point, a blank `attach` is not a
   degraded model — there is **no load path at all**. Omitting the node with a note is the
   wrong failure mode; the refusal rule the exporter already applies to its other missing
   datums applies here. **This is what makes the batch tier M rather than S: export
   behaviour changes, not just placement.**
2. **`carrier` keeps its three states — inference stays.** G-2/BM-4 already decided
   inferred-and-marked, and the data supports it: measured across all five fixtures the
   butt-line-against-side-of-body rule reproduces the entered carrier on **10 legs out of
   10**, including `dhc8_dash8`'s WING main gear (attach `y` = 75.0 against sob `y` = 52.95).
   No ground for forcing entry. The GUI shows the inferred value live beside the field so
   accepting it is a conscious act, and since the user is already at the trunnion fields,
   stating it is one selectbox away.
3. **`weight_lb` moves to Weight & Mass Properties** (owner's call, and the right one under
   D-25) — **on the inertia design note, not ahead of it.** The obstacle is named below.
4. **Layout: two labelled groups per leg** — *where the wheel is* (three axle states, rolling
   radius, tread) and *where the leg attaches* (`attach` x/y/z, `carrier`). The owner's
   framing makes these visibly two different structural objects: a contact patch, and a node
   an element runs from. On `ga6_normal` they are 51 in of butt line apart, so in one
   undifferentiated column of numbers an axle station will eventually be typed into the
   trunnion. The three-view draws both.
5. **Acceptance gate (rule 2):** the gear free body — contact-patch load minus
   `weight × NVP` against the reaction delivered at the reference point, per leg per case.
   It needs no new physics and it is the check that would have caught the zero-node export.

**The obstacle to moving `weight_lb`, and why it belongs on the inertia note.**
`MassComponent` has **no GEAR member** — `WING`, `FUSELAGE`, `HTAIL`, `VTAIL` only — so a
weight-database row cannot be identified as gear, and `gear_loads` must find the leg's mass
to form the inertia term. The obvious fix is a trap: `component` answers *"which beam reacts
this mass"*, and for gear that is exactly what `carrier` already says (BODY → fuselage beam,
WING → wing beam), so adding `GEAR` to that enum conflates two questions and leaves the
Dash-8's wing gear unable to say its mass rides the wing beam.

What is actually missing is **a way to attribute a database row to a named installation
item** — and that is the *same* mechanism the engine-mass fold-in needs, which must find "the
rows belonging to engine 2" against fixtures storing `Engines (2)` as one lumped centreline
row. `MassComponent`'s own docstring records why geometric inference was rejected for exactly
this reason: every mass item in every shipped fixture sits at `y = 0`, so inference tags the
whole database `FUSELAGE`. **Gear weight and engine mass are one problem, and the
per-payload-case inertia note is the home for both.**

**Doc fix riding along (tier S).** `LandingGearInput.weight_lb`'s docstring illustrates the
free body with *"ga6's 155 lb main leg is 491 lb at NVP 3.167"*, but the field is **per leg**
and `ga6_normal` stores 77.5, giving 245 lb. The example quotes the pair while the field and
the computation are per leg — an ambiguity that matters in a field whose whole job is closing
a free body.

### Certification basis and the case manifest

`[D]`, tier L. Raised 2026-08-19 out of the ENG page inventory and decided in the same
session. Owner's ruling: *"collect both on Start, the use FAR25 button toggle should really be
add additional or modify base FAR 23 cases to FAR 25. Future development will add more FAR 25
cases. This selection should go in start. And we should have a program definition of what
cases are baseline and what the FAR25 case selection changes and adds."*

**Three parts, in dependency order.**

**1. Both declarations collect on Start.** Today a user answering *"what am I certifying this
to?"* must visit two analysis pages. `Project.include_far25` is a checkbox inside the Engine
Mount page's per-engine form — a project-wide flag rendered inside per-engine data, whose help
text has to disclaim its own surroundings (*"Applies to all engines in the project"*).
`SpeedsInput.category` — Normal / Utility / Acrobatic / Commuter / **Concept**, with 14
consumers across the codebase — sits on Structural Speeds, where it bypasses the 23.337 cap,
switches the dive-speed basis (D-1) and changes the weight estimate's calibration. The report
already treats the pair as configuration: `report/content.py:467` prints *"FAR 25 optional
cases | included | Engine Mount"* in the **Configuration** section.

Both move to Start as a project-setup block. `category` is **not** a free move — Structural
Speeds owns the field and it feeds an oracle-locked module — so this is the standard
widget-moves / field-stays `[P]` treatment with the merge-write hazard that comes with it.

**2. The toggle becomes a basis selection, not a boolean.** "Add supplemental FAR 25 cases"
describes what the flag happens to do today; the concept is *which rules this airplane is
being designed to*, and future work adds FAR 25 cases that **modify** base FAR 23 cases as well
as append to them. A boolean cannot express that, and renaming it later is worse than shaping
it now.

**3. The program definition — a case manifest with a declared delta per basis.**

*What exists:* `report/coverage.py::FAR23_SUBPART_C`, 52 rows, a static declaration of every
regulation the suite can cover, cross-checked against a run's actual `far_reference` values and
classified `covered` / `not_applicable` / `not_analysed` / `out_of_scope`. That is already the
baseline half of what is being asked for.

*What is missing, measured:* **the table has zero FAR 25 rows.** With the flag on, `atr42_100`
produces `25.361(a)(3)(i)`, `25.361(a)(3)(ii)` and `25.371` — three conditions the coverage
matrix cannot see. The report section whose whole job is *"what was analysed and what was
not"* is blind to the cases the flag adds.

*Shape:* follow `safety_factors.py` (M4-8 / G-11) — the governing table lives in code, one row
per condition family, each row carrying its basis; project data holds only deviations. The
manifest is structurally the same object: baseline rows, plus a declared delta per basis
stating **added** or **modified** for each case. `CLAUDE.md` rule 3 requires precisely this —
a single-source code owner plus a drift-guard test, not a prose rule.

**The oracle constraint, stated correctly.** `engine.py`'s standing comment argues that making
the FAR 25 cases *unconditional* would break oracle-lock ("would alter the Appendix B
turboprop case count and gyro vertical"). That is an argument against unconditional
application, **not** against modification. Behind an opt-in basis that every oracle fixture
leaves at FAR 23, modifying a base case is legitimate. **Acceptance gate:** with the basis set
to FAR 23, every shipped fixture's output is byte-identical to today — the same G-1 shape used
for `hub_thrust_set` and the M4-8 safety-factor table. That gate is what makes future
modify-type FAR 25 cases safe to add.

**Design consequence to settle before the second FAR 25 case, not after.** Today the delta is
purely additive, so case identities never collide. Once a basis *modifies* a base case, two
runs of the same airplane produce different numbers under the same `far_reference` and case
id, distinguished only by a project-level flag printed once in the report header. Certification
basis then has to become part of **case identity** — or at minimum be stated on every case —
which is `CONVENTIONS.md` §case-identity territory and is far cheaper to design now than to
retrofit.

**Tier L** (new cross-cutting single-source owner plus a schema consequence: the boolean
becomes a basis selection). Design note first. The Start move (part 1) is `[P]` and can ship
in the placement batch ahead of the note, since it changes no behaviour.

### A widget with no effect — `speeds.wing_area_sqft` is entered but never read

Found 2026-08-19 opening the Structural Speeds page. `structural_speeds._wing_area_sqft`
takes the wing area from the **geometry surface unconditionally**; the slice field is a
fallback reached only when the project has no wing surface at all:

```python
def _wing_area_sqft(project, inp):
    if project.geometry is not None:
        surf = project.geometry.by_name(inp.wing_surface)
        if surf is not None:
            ...
            return total_in2 / IN2_PER_FT2      # geometry always wins
    if inp.wing_area_sqft:                      # fallback only
        return inp.wing_area_sqft
```

The Structural Speeds page nevertheless renders it as an editable number input
(`app/views/structural_speeds.py:214`). **A user types a wing area, watches it save, and the
analysis ignores it.**

**Measured on `atr42_100`:** the slice stores **586.6 ft²** (the real airplane's book figure);
the analysis uses **480.639 ft²** (the modelled wing — WINGGEOM total area 69,212 in², which
`parametric.wing_area_sqft` and `landing.wing_area_sqft` both agree with). An **18 %**
divergence, silent.

**Nothing is computed wrongly.** The modelled wing is self-consistent — aspect ratio 13.54
against S = 480.64 and an 80.7 ft span — and every consumer reads the same geometry. The
defect is what the user is led to believe: wing loading is reported as **76.6 psf**, while the
entered number would give 62.8, and W/S drives every √(W/S) minimum design speed in 23.335 —
roughly **10 %** on VC(min), VA(min) and VF(min). A stale or hopeful number in that box looks
authoritative and does nothing.

**Class.** Not a duplicate owner — ownership here is clear and correct (geometry wins, by
design, the same shape as `landing.wing_area_sqft` and `FlightLoadsInput.wing_area_sqft`,
both refreshed by `sync_geometry_derived`). It is the **display half**: a derived value
rendered as an input. The registry catches it as soon as it records *editing page* alongside
*owning slice*, because the pair "owned by geometry / edited on Structural Speeds" is exactly
what it flags.

**What ships.** Render it as a **derived read-only value with its source named**, matching
GR-GEOM-7's treatment of the other derived scalars, and keep the field as the documented
no-wing-surface fallback — visible as an input only when there is no wing surface to derive
from. Tier S, display-only, no calc change. **Generalise on first find (rule 4):** sweep for
the same shape — `landing.wing_area_sqft` and `FlightLoadsInput.wing_area_sqft` are the two
known siblings, both already synced, and any page rendering them as inputs has the same
defect.
