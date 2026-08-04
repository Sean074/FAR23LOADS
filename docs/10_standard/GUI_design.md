# sloads — GUI Design & Structure

The authoritative description of how the Streamlit GUI is designed and the
standards every page — especially the airplane-**definition** pages — must meet.
Read this before adding or changing a view.

**See also:** [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) — architecture rationale and
the shared pure-calc/thin-shell split; [`00_program_overview.md`](00_program_overview.md)
— coding standards, the error-handling contract and the units convention;
[`../30_future/02_gui_workflow_plan.md`](../30_future/02_gui_workflow_plan.md) —
the Phase-D narrative (assessment, the six-section target, locked decisions
D-1…D-7, page conventions §5) this doc references rather than repeats;
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) — **Phase E**, the open
GUI usability & concept-awareness work whose target standards are set out below.

---

## 1. Purpose & scope

The GUI lets an engineer **build an airplane, review that the inputs are right,
run the FAR 23 loads workflow, and export** the results (per-module CSVs and the
sbeam `FORCE`/`MOMENT` bulk-data cards). It is a concept-aware **superset** of the
FAR 23 replication: it can describe airplanes that exceed the FAR 23 applicability
limits (higher MTOW, more occupants) while making the user aware they are outside
the certificated band — and it reduces exactly to the oracle-locked FAR 23
behaviour on GA inputs (see §9).

Every page is a thin I/O shell over the shared pure-calc package: the GUI does no
load math of its own. Calc always runs in the Imperial units of the original
programs; SI and unit presentation are applied only at the render boundary (§7).

---

## 2. Architecture at a glance

The system is a **shared pure-calc package + interchangeable thin front-ends**
(GUI, CLI, tests). The GUI carries **one reloadable `Project`** in
`st.session_state["project"]`; every page reads the slices it needs off that
`Project` and writes its own slice back. Navigation is generated from
`sloads/workflow.py`, the single source of truth for *what the suite does and in
what order*.

```
project.json ──io.load_project──▶ Project ──▶ view widgets ──▶ Project
                                     │                            │
                                     └────── registry / report ◀──┘
                                              (results, CSV, sbeam)
```

`app/Home.py` is the entry point; `app/views/<key>.py` is one page each;
`sloads/models.py` holds `Project` and its per-domain slices; `sloads/io.py`
is the only dataclass⇔JSON mapper; `sloads/units.py` owns unit conversion.

---

## 3. Navigation model

The sidebar is built by `st.navigation` in `app/Home.py` from
`sloads/workflow.py` — **not** from a `pages/` directory — so page order and
titles come from workflow metadata, not filename numbers. Since Step G2 the
sections follow the FAR 23 analysis flow — an un-numbered **Start** app-shell group
above the six numbered analysis-flow phases:

    Start ─▶ 1 · Develop V-n diagram ─▶ 2 · Flight loads ─▶ 3 · Other loads ─▶
    4 · Landing loads ─▶ 5 · Load-case plotting ─▶ 6 · Export

Each `WorkflowStep` names its `key` (= the view file stem), `title`, `phase`, the
calc `module` behind it, and the project slices it `requires`/`produces` — the
seed of a dependency DAG that also drives the Dashboard completeness panel. A page
is exactly `app/views/<step.key>.py`. Since Step G3 the **Develop V-n diagram**
section — the definition pages this doc is chiefly about — is five consolidated
pages, several using `st.tabs` to gather formerly-separate pages: **Geometry**;
**Weight & Mass Properties** (tabs: Estimate · Weight, CG & Inertia · Payload
Cases · Weight / CG Envelope); **Structural Speeds** (tabs: Design Speeds ·
Speed–Altitude Envelope); **Aerodynamic Data**; and **Flight Envelope (V-n)**
(tabs: V-n diagram · Critical Loads (SELECT) · Trim & Stability — the last, Step G5,
plots the balancing tail load swept across the CG range and the tail-volume static
margin).

The analysis-flow phases and their per-page mapping are in
[`../30_future/03_gui_rework_plan.md §4`](../30_future/03_gui_rework_plan.md); the
superseded Phase-D six-section grouping is in
[`../30_future/02_gui_workflow_plan.md §2`](../30_future/02_gui_workflow_plan.md).

---

## 4. Global sidebar (`Home.py`)

`Home.py` owns the two controls that appear on every page, built once above
`pg.run()`:

- **Unit-system toggle** — an Imperial/SI radio writing
  `st.session_state["unit_system"]` (a `UnitSystem` enum). It changes how inputs
  and results are *displayed* **and it is the selection that every exported
  deliverable is rendered in** (report, load-case CSV, span CSVs, sbeam BDF —
  `00_program_overview.md`, *Deliverable units follow the user's selection*); the
  toggle persists into the project's unit-system field so a headless re-render
  reproduces it. Calc and the stored `project.json` values stay Imperial (§7).
- **Project-file widget** — Open a saved project (local `projects/`), New-from-
  example (`examples/*.project.json`), browser Upload, plus Save-to-disk and
  Download. An unsaved-changes guard (`_has_unsaved_changes` vs. a
  `_saved_project_snapshot`, and the `_confirm_discard` dialog) protects an edited
  session from being clobbered by a load.

---

## 5. Shared `Project` & data flow

`Project` holds one slice per domain (`configuration`, `geometry`, `weight`,
`speeds`, `aero`/`aero_coeffs`, `flight_loads`, `wing_mass`, `landing`, `engines`,
… and the result slices `mass`/`envelope`/`loads`). Two rules keep the pages
consistent:

- **Read, don't re-ask.** A page must not prompt for a quantity another slice
  already owns — it reads it. Where a page's field overlaps upstream data, it
  seeds its default from that data instead of showing a blank.
- **Merge, don't wholesale-replace** a slice shared with other pages/edits — only
  the sole owner of a slice may reconstruct it in full on Apply.

The established **seed-chain** (each seeds the next when its target is unset):
Configuration & Layout → WINGGEOM wing surface → Weight DB component stations;
Weight Estimate → Weight DB items; Configuration & Layout `dihedral` / tail spans
→ Wing Loads / Tail Loads; existing wing surface → Configuration & Layout
parametric wing fields. (STRSPEED `MC`/`MD`/shoulder altitude were formerly seeded
into the Mach Limit page; as of Step E7 the **Speed–Altitude Envelope** page instead
*reads them through* read-only from `speeds` — not an editable seed — so they are
never entered twice.)

---

## 6. Page anatomy & conventions

The contract that makes pages copy-of-the-pattern (full list in
[`02_gui_workflow_plan.md §5`](../30_future/02_gui_workflow_plan.md)):

- **Inputs live in an `st.form`** with a single **Apply/Compute** submit — the
  page does not recompute on every keystroke.
- **Apply merges** targeted fields onto the existing slice; a sole-owner page may
  fully reconstruct its own slice.
- **No airplane-shaped widget defaults** — a blank project opens with neutral
  defaults, not Appendix-A numbers baked into `value=`.
- **LIMIT vs. ULTIMATE marking** — deliverables (CSV, sbeam cards, Review/Export)
  are ULTIMATE; a per-module *analysis* page may show LIMIT values **only** when
  explicitly marked (a caption + a `LIMIT` marker per column). See
  [`00_program_overview.md`](00_program_overview.md) and `CLAUDE.md`.
  **A LIMIT download must carry the basis in-band (M4-15):** the filename ends
  `_LIMIT.csv` *and* the content states it (a `Basis` column, or LIMIT-marked
  column headers) — an on-page caption does not travel with the file. Pages may
  pair it with the ULTIMATE twin from the sbeam bridge (`*_ULT.csv`, `SF`
  column), as Wing Loads / Fuselage Loads do.
  `tests/test_ultimate_contract.py` scans every view's CSV `download_button`
  and fails on an unmarked load CSV that doesn't route through an ULTIMATE
  channel.

---

## 7. Units at the boundary (the definition-page input pattern)

Imperial is the canonical internal system; the *displayed and exported* system is
whichever the user selected. Results are
converted with `convert_results` / `si_scalar_label` / `to_si_scalar`. **Input
widgets** on the definition pages follow this standard pattern (reference
implementation: `app/views/engine_mount.py`; helpers in `sloads/units.py`):

```python
system = st.session_state.get("unit_system", UnitSystem.IMPERIAL)
U = labels_for(system)                                   # kind -> unit label
val = st.number_input(f"Wing area S ({U['area_sqft']})", # unit-suffixed label
                      value=to_display(imperial, "area_sqft", system),
                      key=f"w_area_{system.value}")       # re-seed on toggle
...
inp.wing_area_sqft = to_imperial_scalar(val, "area_sqft", system)   # on Apply
```

Key points: seed the widget from the stored Imperial value via
`to_display(value, kind, system)`; suffix the label with `U[kind]`; suffix the
widget `key` with `system.value` so switching units re-seeds the widget; convert
back with `to_imperial_scalar(v, kind, system)` before writing the (always
Imperial) `Project`. Unit **kinds** and their factors/labels live in
`SI_PER_IMPERIAL` / `UNIT_LABELS` in `sloads/units.py`.

**Aviation-standard exception:** airspeed (KEAS) and altitude (ft) stay in
aviation units in *both* systems and are never converted — do not add a unit kind
for them. Where a deliverable reports them it says so, so an SI reader does not
read an unconverted speed as an oversight.

**Exports follow the toggle too.** The toggle is not display-only: the export
bundle (report, load-case CSV, span CSVs, sbeam BDF) is rendered in the selected
system, one system per bundle, each file stating it in-band — see
[`SUMMARY_REPORT.md`](SUMMARY_REPORT.md) §3.5 for the full rule. The Export page
SHALL show which system the bundle will be written in, next to the download
control, so the choice is visible at the point of export rather than only in the
sidebar.

---

## 8. Airplane-definition page standards

The design bar every definition page builds to. Where a page does not yet meet a
standard, the rollout is tracked in
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) **Phase E**.

### 8.1 Explanation

Every domain input widget carries a `help=` tooltip; dense and grid pages
(the unified Geometry page — parametric layout, fuselage outline and WINGGEOM
surface planforms, Step G1 — Aerodynamic Data coefficients, Weight/CG inertias,
and a short one on Structural Speeds)
additionally carry a collapsible **"ℹ️ Parameter guide"** expander. Jargon (MAC,
XLEMAC, static margin, neutral point, tip-back/overturn, shoulder altitude, KEAS,
the aero `C0…C4` polynomials, per-item inertias and the parallel-axis convention)
is defined for the user, with FAR paragraph + Reference-1 program/chapter
citations. The three `st.data_editor` grid pages (Weight/CG inertias, Wing
Geometry LE/TE points, the Aero `C0…C4` table) explain their columns in the guide
expander rather than per column. *(Implemented — Phase E2.)*

### 8.2 Graphical review

Every page that takes substantial numeric input offers a plot or derived readout
that lets the user *see* whether the inputs are self-consistent:

| Page | Graphical review |
|------|------------------|
| Geometry (Step G1: parametric + fuselage outline + WINGGEOM planforms; Step G6/G6b: single-source empennage + landing gear) | Three-view (CG, neutral point, **gear strut + wheels** from the axle geometry, fuselage outline, mass bubbles, engines, **elevator/rudder** shaded from the aft Saft/S band); per-surface planform-derived Area/MAC/XLEMAC/AR/span. The **Empennage & control surfaces** (Step G6) and **Landing gear** (Step G6b) sections are the single input homes for the h-/v-tail + elevator/rudder (`GeometryInput.empennage`) and the tricycle-gear axle geometry (`GeometryInput.landing_gear`), feeding both this three-view and the tail-/ground-load analysis |
| Flight Envelope (V-n) | Continuous LIMIT design envelope (curved stall boundary, flaps-up/down manoeuvre envelope, gust lines) overlaid on the rigorous Mach-corrected balanced corner points *(consolidated — Phase E6)* |
| Weight/CG/Inertia | CG marker + mass-distribution plot (with WTENV limits when defined) *(implemented — Phase E3)* |
| Aerodynamic Data | Echo tables only *(curve plot deferred — see backlog)*; **fuselage pitching-moment (Munk) estimate** — volume/fineness/k₂−k₁/ΔM1 from the Geometry outline, off-by-default, overridable (Step G4) |
| Aircraft Comparison (Export) | Parameter table + six fleet scatters (loading, weight, geometry) *(Phase F, Step F2)* |

The continuous LIMIT design envelope is built by the pure `sloads/vn_diagram.py`
helper from the STRSPEED design speeds + limit load factors; its gust lines are the
textbook Pratt form (14 CFR 23.341) and are explicitly captioned as approximate.
It is drawn as a grey backdrop on the **Flight Envelope (V-n)** page (FLTLOADS)
behind the rigorous, Mach-corrected balanced corner points, so the envelope visibly
bounds them — a single consolidated V-n. (Originally a separate diagram on
Structural Speeds in Phase E3; merged onto Flight Envelope in Phase E6 to remove the
redundancy. The Structural Speeds page now shows only the numeric design-speed
tables and points to the Flight Envelope page.)

### 8.3 Input-consistency validation

Pages surface explicit `st.warning`s on inconsistent input — taper ratio > 1,
non-positive area, leading-/trailing-edge point ordering, a wing-area mismatch
between Configuration & Layout and Wing/Surface Geometry, a CG outside the
weight-CG envelope, or a per-case `safety_factor` outside the legal [1.0, 1.5]
band (M4-14; rendered on the Export page, where the consequence lives). The
checks are pure predicates in `sloads/validation.py`
(`consistency_warnings(project)`), each tagged with the page that renders it; the
CG-envelope check compares the WTONECG CG against the WTENV structural envelope and
is silently skipped when that envelope (or the wing geometry it needs) is absent.
The Project JSON Editor additionally scans the **raw** edited dict at Apply for
invalid `safety_factor` values (via the public `validation.safety_factor_valid`)
and warns that they were reset — `io.py`'s readers coerce any invalid persisted
factor to the conservative 1.5 default on load, so the built project cannot show
what was typed. *(Implemented — Phase E3; safety-factor check M4-14.)*

### 8.4 Fleet comparison — the Aircraft Comparison page

The airplane is placed against the reference fleet in
`app/data/reference_aircraft.csv` (29 aircraft spanning GA singles to ~41,000-lb /
50-seat regional turboprops, so a concept airplane has real comparators) on **one
dedicated page** — **Aircraft Comparison**, in the Export phase before Results
Review (`app/views/aircraft_comparison.py`, GUI-only `WorkflowStep`). The two input
pages (Configuration & Layout, Weight Estimate) **no longer** carry a fleet block —
the comparison lives in exactly one place (Phase F, Step F2). The page carries a
quantitative readout (nearest-3 similar aircraft, W/S & W/P percentile band, outlier
flags), a **parameter table** (subject row on top, then the nearest-N over MTOW,
OEW, power, W/S, W/P, wingspan, wing area, aspect ratio, seats), and **six scatter
tabs**: W/S-vs-W/P, MTOW-vs-OEW, and four geometric scatters (wingspan / wing area /
aspect ratio / seats vs. MTOW).

The numeric core is the pure, unit-tested `sloads/fleet.py`
(`fleet_stats(subject, fleet)` → `FleetStats`; no pandas / file access / Streamlit);
the CSV load and rendering are owned by the page itself. Locked decisions
(Step E4, 2026-07-15): **D-E4-1** pure core in `sloads/fleet.py`; **D-E4-2**
nearest-N uses a normalized-Euclidean distance over whichever metrics the subject
supplies (always log-MTOW; add W/S and W/P when known), and the outlier flag is the
fleet **p10–p90** band; **D-E4-3** the readout lists the **nearest 3** from the
whole fleet, with jets (`max_hp = 0`, no shaft power) excluded from W/P distance and
the W/P percentile only, never from the comparator pool. Step F2 decisions
(2026-07-16): **D-F2-a** the nearest-N distance stays on MTOW / W/S / W/P — the
geometry (span / area / AR / seats) is **presentation-only** (table columns and plot
axes), never a distance term; **D-F2-b** six tabs, one plot each; **D-F2-c** no
category coloring (two-series `Reference fleet` vs `This airplane`). *(Implemented —
Phase F, Step F2; the shared `render_fleet_comparison` wrapper on the two input
pages, its Phase-E4 home, was removed.)*

**M2-5 (2026-07-20).** The comparison **subject** now resolves its wing geometry from
the WINGGEOM planform when no parametric layout is present:
`_subject_from_project` reads wing **area** `parametric → geometry.by_name("wing")
surface (Total area ÷ 144) → speeds.wing_area_sqft`, wing **AR** and **span**
`parametric → surface` (span set directly from the surface Span ÷ 12, not
back-derived from √(AR·area)). Most shipped examples carry `geometry.surfaces` rather
than a parametric layout, so this is what fills W/S / area / span / AR for them (e.g.
GA-6 recovers AR 6.095 / span 33.5 ft). The page **stays in the Export phase** (the
single navigation-truth order in `workflow.py` is unchanged); a workflow-derived
`page_link` on the **Weight & Mass Properties** page makes the fleet check reachable
at definition time.

---

## 9. FAR 23 applicability & concept-awareness (warn-but-allow)

The tool must let a user describe an airplane **beyond** FAR 23 while making clear
it is outside the certificated band — never blocking. The design:

- **Limits encoded once** in `sloads/constants.py`
  (`FAR23_MAX_WEIGHT_LB = 12500`, `FAR23_MAX_PASSENGER_SEATS = 9`, and the encoded-
  but-dormant commuter tier `FAR23_COMMUTER_MAX_WEIGHT_LB = 19000` /
  `FAR23_COMMUTER_MAX_PASSENGER_SEATS = 19`; `DEFAULT_FLIGHT_CREW = 1`, the crew
  assumed when no weight-estimation slice is present). The commuter tier is dormant
  until a distinct Commuter category exists (backlog).
- **A pure `far23_applicability(project)` helper** (`sloads/applicability.py`)
  returns the structured exceedances (`Exceedance(field, value, limit, label)`); no
  Streamlit, unit-testable, and yields *no* exceedances on Appendix-A GA inputs.
  The MTOW check reads `speeds.weight_lb`, falling back to the Weight DB total; the
  seat check compares `passenger seats = effective_occupants − effective_crew`
  against 9, where the crew is the user-set `WeightEstimationInput.crew`.
- **A non-blocking banner** (`app/components.render_applicability_banner`) on the
  Dashboard and the definition pages when a non-concept airplane exceeds a limit —
  "exceeds FAR 23 applicability; results are concept-mode extrapolation" — with a
  one-click **"Switch to Concept"** action that also seeds the concept load factors
  from the computed FAR 23.337 values so the flip never breaks the downstream calc.
- **`occupants` is a first-class field** (`StructuralSpeedsInput.occupants`,
  co-located with `category` + `weight_lb`; seeds its default from the Weight
  Estimate seat count; echoed read-only on Configuration & Layout), driving the
  seat-count check. **`crew` is a user-set field** (`WeightEstimationInput.crew`,
  co-located with `seats`; default 1) that is subtracted from occupants for the
  seat check and carried in the **operating empty weight** (WTESTIMA reports a
  derived `OEW = empty + crew×170` line; the manufacturer's-empty oracle is
  unchanged).
- **Concept mode** (`speeds.category == "C"`, surfaced by `Project.is_concept`)
  lets the user set their own limit load factors and, on GA inputs, reduces
  exactly to the FAR 23 result.

*(Implemented — Phase E1, `SCHEMA_VERSION = 22`.)*

---

## 10. JSON persistence

`sloads/io.py` is the **only** dataclass⇔JSON mapper. `project.json` **values** are
always canonical Imperial (`io.py` never converts units); the project's
unit-system field records the user's *display/export preference* only and never
changes how a stored value is interpreted. The load path carries no unit
assumption, so loading an Imperial file under an SI toggle converts exactly once,
at each page's render boundary. `Project` carries a `schema_version`
(`models.py`, `SCHEMA_VERSION`); older on-disk shapes are migrated leniently by
field-presence heuristics so old files still load.

Every load path is hardened (Phase E5): the three sidebar actions (Open saved,
Load example, Upload) and the Project JSON Editor's **Apply**
(`app/views/project_editor.py`, which round-trips the whole project as JSON in the
selected units via `project_dict_to_display` / `project_dict_to_imperial`) all show
a graceful `st.error` on a malformed / wrong-shape file instead of a traceback, and
run a soft `SCHEMA_VERSION` check via the pure `io.schema_status(version)`: a newer
file warns and still loads (unrecognized fields ignored); an older file is migrated
in place (its field-presence migration ran in `io.py`; the stamp is bumped to the
current version). The sidebar surfaces the schema notice as a toast (its adopt path
reruns); the editor surfaces it inline.

---

## 11. Status & open work

**Implemented today:** the workflow-aligned navigation (Start + six analysis-flow
phases since Step G2; the Phase-D six-section grouping it re-sequenced), the global unit toggle and
project-file widget, the shared-`Project` data flow and seed-chain, the
form+Apply/merge page conventions, the unit-boundary input pattern across all
definition pages (§7), the Configuration & Layout three-view, the
FAR 23 applicability banner + `occupants`/`crew` fields and OEW line (§9,
Phase E1), the per-widget `help=` tooltips + parameter-guide expanders across
the six Airplane pages (§8.1, Phase E2), and the V-n diagram +
Weight/CG mass-distribution plot + input-consistency warnings (§8.2/§8.3,
Phase E3; the V-n later consolidated onto the Flight Envelope page in Phase E6),
and the dedicated **Aircraft Comparison** page — parameter table + six fleet
scatters + nearest-3 / percentile band / outlier flags via the pure
`sloads/fleet.py` (§8.4, Phase E4 core; consolidated onto its own Export-phase
page in Phase F, Step F2), and the graceful, schema-aware load path across the
sidebar and the JSON Editor (§10, Phase E5).

**Phase E is complete** — all steps E1–E5 have shipped.

The schema field list is **single-sourced in
[`DATA_DICTIONARY.md`](DATA_DICTIONARY.md)** (generated; currently
`SCHEMA_VERSION = 35`); the per-step migration history is recorded in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
(recent steps: v29 single-source CLmax
stall; v30 M2-6 wing/fuselage derived geometry; v31 M2-10 operational placards;
v32 M2R-2 `LandingInput.n` write-back removed; v33 M4-7 per-case
`safety_factor` on `CriticalCondition` + the four distributed-load results;
v34 M4-18 `SurfaceInput.ref_axis_pct` (the loads reference axis, LRA) +
`WingLoadResult.torsion_axis`; v35 M4-1 `SurfaceInput.front_spar_pct`/
`.rear_spar_pct` (the wing carry-through the Ch 15 fuselage moment closure
reacts over; `None` = not entered → assumed default)).
This paragraph's version number is guarded by
`tests/test_data_dictionary.py::test_gui_design_schema_line_current` — update
it (and this list) with every `SCHEMA_VERSION` bump.
Phases D–F (the six-section GUI restructure, the
usability/concept-awareness work, and fleet comparison) are all complete, and Phase G
is under way (G0–G6 + G6b shipped). The **open GUI plan is now
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) → Phase G** — the
workflow-aligned rework (one-unit-per-dimension, single-source-of-truth geometry,
re-sequenced analysis-flow navigation, fuselage-moment/trim-plot/empennage
features); its narrative and locked decisions G-1…G-4 are in
[`../30_future/03_gui_rework_plan.md`](../30_future/03_gui_rework_plan.md). The
Phase-D narrative is in
[`../30_future/02_gui_workflow_plan.md`](../30_future/02_gui_workflow_plan.md).
