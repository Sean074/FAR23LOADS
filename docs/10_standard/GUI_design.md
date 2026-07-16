# FAR 23 LOADS — GUI Design & Structure

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
`farloads/workflow.py`, the single source of truth for *what the suite does and in
what order*.

```
project.json ──io.load_project──▶ Project ──▶ view widgets ──▶ Project
                                     │                            │
                                     └────── registry / report ◀──┘
                                              (results, CSV, sbeam)
```

`app/Home.py` is the entry point; `app/views/<key>.py` is one page each;
`farloads/models.py` holds `Project` and its per-domain slices; `farloads/io.py`
is the only dataclass⇔JSON mapper; `farloads/units.py` owns unit conversion.

---

## 3. Navigation model

The sidebar is built by `st.navigation` in `app/Home.py` from
`farloads/workflow.py` — **not** from a `pages/` directory — so page order and
titles come from workflow metadata, not filename numbers. Work flows left-to-right
through six sections:

    1 · Start ─▶ 2 · Airplane ─▶ 3 · Envelopes & Critical Conditions ─▶
    4 · Analysis ─▶ 5 · Loads Plots ─▶ 6 · Export

Each `WorkflowStep` names its `key` (= the view file stem), `title`, `phase`, the
calc `module` behind it, and the project slices it `requires`/`produces` — the
seed of a dependency DAG that also drives the Dashboard completeness panel. A page
is exactly `app/views/<step.key>.py`. The **Airplane** section — the definition
pages this doc is chiefly about — is: Configuration & Layout, Wing / Surface
Geometry, Weight Estimate, Weight/CG/Inertia, Structural Speeds, Aerodynamic Data.

The full six-section target and its per-page mapping are in
[`../30_future/02_gui_workflow_plan.md §2`](../30_future/02_gui_workflow_plan.md).

---

## 4. Global sidebar (`Home.py`)

`Home.py` owns the two controls that appear on every page, built once above
`pg.run()`:

- **Unit-system toggle** — an Imperial/SI radio writing
  `st.session_state["unit_system"]` (a `UnitSystem` enum). It changes only how
  inputs and results are *displayed*; calc and `project.json` stay Imperial (§7).
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
→ Wing Loads / Tail Loads; STRSPEED `MC`/`MD`/shoulder altitude → Mach Limit;
existing wing surface → Configuration & Layout parametric wing fields.

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

---

## 7. Units at the boundary (the definition-page input pattern)

Imperial is the canonical internal system; SI is presentation only. Results are
converted with `convert_results` / `si_scalar_label` / `to_si_scalar`. **Input
widgets** on the definition pages follow this standard pattern (reference
implementation: `app/views/engine_mount.py`; helpers in `farloads/units.py`):

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
`SI_PER_IMPERIAL` / `UNIT_LABELS` in `farloads/units.py`.

**Aviation-standard exception:** airspeed (KEAS) and altitude (ft) stay in
aviation units in *both* systems and are never converted — do not add a unit kind
for them.

---

## 8. Airplane-definition page standards

The design bar every definition page builds to. Where a page does not yet meet a
standard, the rollout is tracked in
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) **Phase E**.

### 8.1 Explanation

Every domain input widget carries a `help=` tooltip; dense pages (Configuration &
Layout geometry, Aerodynamic Data coefficients, Weight/CG inertias) additionally
carry a collapsible **"ℹ️ Parameter guide"** expander. Jargon (MAC, XLEMAC, static
margin, shoulder altitude, area-density ratio, the aero `C0…C4` polynomials) is
defined for the user, with FAR / Reference-1 page citations. *(Target — Phase E2;
today explanation is caption-only, no per-widget `help=`.)*

### 8.2 Graphical review

Every page that takes substantial numeric input offers a plot or derived readout
that lets the user *see* whether the inputs are self-consistent:

| Page | Graphical review |
|------|------------------|
| Configuration & Layout | Three-view (CG, neutral point, gear, mass bubbles, engines) + fleet scatter |
| Wing / Surface Geometry | Planform plot; derived Area/MAC/XLEMAC/AR/span |
| Weight Estimate | MTOW-vs-OEW fleet scatter |
| Structural Speeds | **V-n envelope plot** *(target — Phase E3)* |
| Weight/CG/Inertia | **CG marker + mass-distribution plot** *(target — Phase E3)* |
| Aerodynamic Data | Echo tables only *(curve plot deferred — see backlog)* |

### 8.3 Input-consistency validation

Pages surface explicit `st.warning`s on inconsistent input — taper ratio > 1,
non-positive area, leading-/trailing-edge point ordering, a wing-area mismatch
between Configuration & Layout and Wing/Surface Geometry, or a CG outside the
weight-CG envelope. *(Target — Phase E3; today the plots are the only implicit
check.)*

### 8.4 Fleet comparison

The airplane is placed against the reference fleet in
`app/data/reference_aircraft.csv` (23 aircraft spanning GA singles to ~41,000-lb /
50-seat regional turboprops, so a concept airplane has real comparators). Beyond
the W/S-vs-W/P and MTOW-vs-OEW scatters, a quantitative nearest-match / percentile
/ outlier readout is the target, via one shared helper reused by Configuration &
Layout and Weight Estimate. *(Target — Phase E4; today the comparison is visual
and duplicated across the two pages.)*

---

## 9. FAR 23 applicability & concept-awareness (warn-but-allow)

The tool must let a user describe an airplane **beyond** FAR 23 while making clear
it is outside the certificated band — never blocking. The design:

- **Limits encoded once** in `farloads/constants.py` (max takeoff weight 12,500 lb
  / commuter 19,000 lb; occupants 9 / 19) — today these figures live only in prose
  and warning strings.
- **A pure `far23_applicability(project)` helper** returns the structured
  exceedances (field, value, limit, label); no Streamlit, unit-testable, and
  yields *no* exceedances on Appendix-A GA inputs.
- **A non-blocking banner** on the Dashboard and the relevant definition pages
  when a GA-category airplane exceeds a limit — "exceeds FAR 23 applicability;
  results are concept-mode extrapolation" — with a one-click **"switch to
  Concept"** action.
- **`occupants` is a first-class field** (design home: `StructuralSpeedsInput`,
  co-located with `category` + `weight_lb`; echoed read-only on Configuration &
  Layout), driving the seat-count check.
- **Concept mode** (`speeds.category == "C"`, surfaced by `Project.is_concept`)
  lets the user set their own limit load factors and, on GA inputs, reduces
  exactly to the FAR 23 result.

*(Target — Phase E1; today only the manual Concept category exists and merely
decorates output with "unverified extrapolation" captions, with no applicability
detection or occupants field.)*

---

## 10. JSON persistence

`farloads/io.py` is the **only** dataclass⇔JSON mapper. `project.json` is always
canonical Imperial (`io.py` never converts units). The load path carries no unit
assumption, so loading an Imperial file under an SI toggle converts exactly once,
at each page's render boundary. `Project` carries a `schema_version`
(`models.py`, `SCHEMA_VERSION`); older on-disk shapes are migrated leniently by
field-presence heuristics so old files still load.

The Project JSON Editor page (`app/views/project_editor.py`) round-trips the whole
project as JSON in the selected units (`project_dict_to_display` /
`project_dict_to_imperial`) and is the one load path with graceful error handling;
hardening the sidebar load path and adding a schema-version check are Phase E5.

---

## 11. Status & open work

**Implemented today:** the six-section navigation, the global unit toggle and
project-file widget, the shared-`Project` data flow and seed-chain, the
form+Apply/merge page conventions, the unit-boundary input pattern across all
definition pages (§7), and the Configuration & Layout three-view + fleet scatters.

**Adopted standards pending rollout (backlog Phase E):** FAR 23 applicability
detection + occupants field (E1), per-widget `help=` + parameter guides (E2), the
Structural Speeds V-n and Weight/CG mass plots + input-consistency warnings (E3),
the quantitative fleet comparison (E4), and load-path robustness (E5).

Schema is at **`SCHEMA_VERSION = 20`**; Phase D (the six-section GUI restructure)
is complete. The open GUI plan is
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) → **Phase E**; the
Phase-D narrative and locked decisions are in
[`../30_future/02_gui_workflow_plan.md`](../30_future/02_gui_workflow_plan.md).
