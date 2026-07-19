# Phase G — Workflow-aligned GUI rework (design & specification)

> **Status:** design/spec complete; the §6 feature scope is **closed** and the
> step-by-step plan lives in [`00_backlog.md`](00_backlog.md) → **Phase G**. This
> document is the narrative, the assessment vs. the current code, and the locked
> decisions. (To avoid confusion: the six **analysis-flow phases** in §4 are the
> GUI's *workflow sections*; "Phase G" is the *development phase* that builds them.)
>
> **Related:** [`02_gui_workflow_plan.md`](02_gui_workflow_plan.md) (Phase D — the
> six-section restructure this reworks), [`../10_standard/GUI_design.md`](../10_standard/GUI_design.md)
> (the GUI design standard this must keep satisfying), [`01_concept_loads_plan.md`](01_concept_loads_plan.md)
> (Phase C — concept mode).

---

## 1. Why this rework (the problem)

The current GUI is too hard to use. The concrete pain, in the user's words:

1. **Geometry is all over the place.** The same geometry is entered or derived on
   several pages (Configuration & Layout, Wing/Surface Geometry, Flight Envelope),
   so there is no single place that owns it.
2. **The workflow does not follow a sensible order.** Page order does not follow
   how the analysis is actually done, so navigating an airplane analysis requires
   knowing the 22-program suite.
3. **Data feels un-stored.** Because geometry/inputs are re-asked in multiple
   places, work feels lost on return even though the project JSON does persist.
   (Verified: `io.py` round-trips every slice — see §3, Claim 3. The fix is the
   single-source-of-truth restructure, not a persistence bug — but a real reload
   bug, if one is found, is fixed first.)
4. **Units are inconsistent.** The same page mixes `in`, `ft`, `ft²`, so a user
   cannot read the inputs as one coherent set.

The aim: a structure **aligned with the FAR 23 analysis workflow**, with geometry
owned in one place, one unit per dimension app-wide, and persistent data — while
keeping the oracle-locked calc untouched and reusing the mature parts of the
existing GUI (do not throw the baby out with the bathwater).

---

## 2. Locked decisions (this session, 2026-07-16)

| # | Decision | Resolution |
|---|----------|------------|
| **G-1** | **Units policy** | **One unit per dimension, app-wide.** Each quantity type has exactly one display unit per system. No page shows the same dimension two ways. The Imperial/SI toggle still switches the whole app. (Calc stays canonical Imperial internally per `GUI_design.md §7`.) **Canonical display units locked 2026-07-18:** length → **`in`** (SI **`mm`**), area → **`ft²`** (SI **`m²`**). This retires the redundant feet-length and square-inch area kinds in `units.py:UNIT_LABELS`. **Shipped 2026-07-18 (Step G0):** the offending stored fields (`*_ft` spans/lengths, the tab's square-inch area key) were *renamed* to canonical-unit names and stored in canonical units (`SCHEMA_VERSION` 23 → 24, older files migrate) rather than relabelled display-only — the display-only path would have mislabelled a stored feet value as inches. Calc results are held identical (ft/in² restored internally); see `docs/40_history/00_completed_development.md`. |
| **G-2** | **Geometry ownership** | **One geometry page = the single source of truth.** Fuselage, wing, empennage, control surfaces, gear and engine locations are defined there once; every downstream page reads geometry read-only and never re-asks it. This also closes the doc's original *"Is geometry before weight?"* open decision — **geometry is defined first** (the weight DB and the aero both need it). **Shipped 2026-07-18 (Step G1):** the two geometry pages (Configuration & Layout + Wing / Surface Geometry) are merged into one **Geometry** page, and their two slices are **unified** onto `GeometryInput` (`.parametric` + `.surfaces` + a new `.fuselage` station-area outline); `SCHEMA_VERSION` 24 → 25, older files migrate. Downstream pages read the slice read-only; the fuselage is now a real geometry entity feeding the G4 estimator. Oracles unchanged. See `docs/40_history/00_completed_development.md`. |
| **G-3** | **Persistence** | The perceived data loss is **re-entry, not true loss** — fixed by G-2's single-source-of-truth. Any genuine reload bug found during the work is fixed before restructuring. No autosave in scope. |
| **G-4** | **Restructure depth** | **Genuinely re-sequence** `farloads/workflow.py` into the analysis-flow phases of §4 (not merely relabel). Pages are consolidated/reordered so the sequence matches how the analysis is really performed. **Shipped 2026-07-18 (Step G2 — the re-sequence):** `PHASES`/`STEPS` re-grouped into an un-numbered **Start** app-shell section + the six analysis-flow phases (**Develop V-n diagram → Flight loads → Other loads → Landing loads → Load-case plotting → Export**); the old Airplane/Envelopes/Analysis split dissolved (weight+speed pages interleave into their V-n sub-groups; Landing moved after Other loads). Grouping/labels only — no page bodies changed (that consolidation is Step G3). Nav-drift guard green; oracles untouched. See `docs/40_history/00_completed_development.md`. |

Invariants carried from Phase C/D (unchanged): calc math untouched (Appendix A/B
±0.1% oracles pass throughout); ultimate-load output rules apply; pure calc / thin
shells; `workflow.py` stays the single source of navigation truth.

---

## 3. Assessment against the current implementation

The GUI has already shipped **Phase D** (six-section restructure), **Phase E**
(usability: tooltips, plots, applicability banner, hardened persistence) and
**Phase F** (fleet comparison). Several items this document originally treated as
missing already exist. The claims were checked against the code:

| Original claim | Verdict | Reality in the code |
|---|---|---|
| Data not stored → reload needs re-entry | **Stale** | Every `Project` slice (inputs *and* results) round-trips through `io.py`. Perceived loss = re-entry (Claim/§1.3). |
| 3-view drawing missing | **Incorrect** | Full top/side/front three-view exists — `configuration_layout.py:265` (`_three_view`): fuselage outline, wing, empennage, gear, engines. |
| Mass-distribution plot missing | **Incorrect** | Exists twice — overlaid on the three-view, and a station-stem plot on Weight/CG (`weight_cg_inertia.py:159`). Phase E3. |
| "% chord of elevator" missing | **Partial** | Not a *direct* input, but the hinge-line chord fraction is derived from `elevator_aft_hinge_sqft / htail_area` (`taildist.py:80`). A direct field is an *addition*, not a fix. |
| Fuselage pitching moment not in tail balance | **Partial / misleading** | The FLTLOADS balance *does* carry wing+fuselage moment "M(W+F)" via the airplane-less-tail `CM` polynomial (`flight_envelope.py:162,428`). What is missing is a fuselage-moment *estimator from geometry* — today the user folds it into the input coefficients. |
| Fuselage as a geometry/aero surface | **Confirmed missing** | Fuselage is only scalars on `LayoutInput` (length/width/height); not a `SurfaceInput`. Drawn as a plain rectangle. |
| Longitudinal stability / trim plots | **Shipped (Step G5)** | The Flight Envelope page's **Trim & Stability** tab plots the balancing tail load (BAL A/C/D) swept across the CG range (`flight_envelope.trim_sweep`, re-running the balance) and a static-margin sweep from the Configuration tail-volume neutral point. |
| Ground-case distributed fuselage loads | **Confirmed missing** | `body_loads` distributes over **flight** V-n conditions only; landing produces gear reactions only; the pressurized no-down-select rule is not modeled. |

**Takeaway.** This rework is ~90% a *re-sequencing + consolidation* of pages that
already exist (reusing Phase D/E/F work), plus **four genuinely new capabilities**
(§5). It is **not** a from-scratch rebuild.

---

## 4. Target structure — the analysis-flow phases

Navigation is re-sequenced (G-4) into the six analysis phases below. Each phase
lists the existing pages/modules it consolidates so the plan can reuse them.

### Phase 1 — Develop V-n diagram (define the airplane & load environment)

> **Shipped 2026-07-19 (Step G3).** The phase-1 pages are consolidated into the
> five sub-steps 1a–1e below, using `st.tabs` where a sub-step gathers several
> formerly-separate pages (1b Weight & Mass Properties = Estimate · Weight, CG &
> Inertia · Payload Cases · Weight / CG Envelope; 1c Structural Speeds = Design
> Speeds · Speed–Altitude Envelope; 1e Flight Envelope (V-n) = V-n diagram ·
> Critical Loads (SELECT)). The FLTLOADS balance-geometry/CG inputs stay on 1e (the
> page that runs them). No calc change; oracles unchanged. See
> `docs/40_history/00_completed_development.md` → Phase G, Step G3.

The primary user input: geometry, mass distribution, aerodynamic data, and the
mass + speed/altitude envelopes. Output = the set of load cases to assess
(mass/CG cases × speed/altitude points).

Ordered sub-steps (geometry first, per G-2):

- **1a. Aerodynamic surface geometry — the single geometry page (G-2).**
  WINGGEOM for all surfaces (wing, aileron, aileron tab, flap, h-tail/stab,
  elevator + tab, v-tail/stab, rudder + tab) **plus the fuselage** (new — for the
  three-view and for fuselage pitching moment, §5). Adds landing-gear and engine
  locations. Produces the three-view and a geometry summary (S, AR, span, taper,
  MAC, XLEMAC per surface). *Consolidates:* `configuration_layout`, `wing_geometry`.
- **1b. Weight & mass properties.** Owns *all* weight/mass data — nothing weight
  is asked downstream. Design weights (MTOW/MLW/ZFW/OEW, CG limits); optional
  WTESTIMA estimate (seeds from geometry); the itemized weight database (empty /
  payload / etc.) incl. distributed wing & fuselage mass; WTENV CG-grid envelope;
  WTONECG mass cases (the loading scenarios for loads analysis — heavy/light ×
  fwd/aft CG, landing high/low waterline). *Consolidates:* `weight_estimate`,
  `weight_cg_inertia`, `weight_envelope`, `payload_cases`.
- **1c. Structural design speeds.** STRSPEED minimums (user may edit/define) +
  MACHLIM shoulder-altitude Mach limits → the speed/altitude envelope.
  *Consolidates:* `structural_speeds`, `mach_limit`.
- **1d. Aerodynamic coefficients.** Wing spanwise (AIRLOADS/Schrenk) + airplane-
  less-tail `C0…C4`/`D…`/`M…` sets (incl. the wing+fuselage pitching moment),
  summarized/plotted for comparison against other data. *Consolidates:*
  `aero_coefficients`, the aero half of `flight_envelope`.
- **1e. V-n diagram.** Plot the V-n diagrams; summarize the weight/CG and
  speed/altitude conditions that flight loads will assess. *Consolidates:*
  `flight_envelope` (V-n results), `critical_loads` (SELECT).

**Understanding plots for phase 1** (some already exist — reuse): (1) three-view
with surfaces/control-surfaces/gear ✔ exists; (2) mass distribution over geometry
✔ exists; (3) weight-&-CG grid with corner CG cases ✔ exists (WTENV); (4)
speed/altitude chart ✔ exists (Mach Limit); (5) V-n per payload/altitude ✔ exists.

### Phase 2 — Flight loads

FLTLOADS loads for every airspeed/load-factor (and mass/CG) on/within the
envelopes; SELECT reads the balanced symmetrical conditions. Output = distributed
wing, empennage and fuselage loads. **New:** standard longitudinal-stability /
trim plots to check trim and balancing tail loads (§5). *Consolidates:*
`wing_loads`, `fuselage_loads`, `tail_loads`.

### Phase 3 — Other loads

Aileron, flap, tab, engine-mount, one-engine-out — control-surface chordwise
distributed loads and reaction loads. *Consolidates:* `aileron_loads`,
`flap_loads`, `tab_loads`, `engine_mount`, `one_engine_out`.

### Phase 4 — Landing loads

Loads on the landing gear (LGFACTOR + LANDLOAD). **Extension (new, §5):**
distributed fuselage (and wing) loads from the ground/landing cases — noting that
for **pressurized** airplanes ground cases **cannot** be down-selected against
flight, because the pressurization load must be assessed for flight, not ground.
*Consolidates:* `landing_loads`.

### Phase 5 — Load-case plotting

VMT plots for wing and fuselage: envelope plots of max shear (V), bending/torsion
(Mx, My, Mz). **Future extension:** load a prior analysis to compare.
*Consolidates:* `loads_plots` (already supports case overlays, envelope curves,
external-CSV comparison).

### Phase 6 — Export

sbeam/NASTRAN BDF for distributed wing/fuselage loads; load tables for other
components; plus a **summary report**: (1) input-data summary; (2) envelope plots
(V-n, weight/CG, speed/altitude); (3) loads-analysis conditions + FAR coverage;
(4) results summary — VMT wing/fuselage, control-surface/flap, landing gear,
engine loads. *Consolidates:* `aircraft_comparison`, `results_review`,
`export_report`.

---

## 5. Genuinely new work (not yet built)

These are the real capability gaps (everything else in §4 is reuse/reorder):

1. **Fuselage as a geometry entity + pitching-moment estimator.** Add the fuselage
   to the geometry page (outline for the three-view) and derive its pitching-moment
   contribution so the balancing tail load no longer relies on the user hand-folding
   it into the `CM` coefficients. *(Calc + GUI.)* **Shipped:** the outline is a
   geometry entity (Step G1) and the **Munk slender-body `dCm/dα` estimator**
   (`farloads/fuselage_moment.py`) landed as **Step G4 (2026-07-19)** — surfaced on
   the Aero page, off by default, added to M1 when enabled; Appendix A/B oracles
   unchanged. See `docs/40_history/00_completed_development.md`.
2. **Longitudinal-stability / trim plots** in Phase 2 (CG-vs-balanced-tail-load,
   static-margin sweep). *(GUI over existing calc.)* **Shipped as Step G5
   (2026-07-19)** — the Flight Envelope **Trim & Stability** tab; `trim_sweep()`
   re-runs the balance across the CG range, static margin from the Configuration
   neutral point. See `docs/40_history/00_completed_development.md`.
3. **Ground-case distributed fuselage (and wing) loads** in Phase 4, incl. the
   pressurized no-down-select rule. **Substantial calc work** (new distribution
   path + pressurization load cases), not just GUI.
4. **Single-source empennage & control-surface geometry.** *(GUI + model.)*
   **Shipped as Step G6 (2026-07-19)**, expanded from the original narrow "direct
   elevator %-chord input": the h-/v-tail + elevator/rudder geometry is entered once
   on the Geometry page (`GeometryInput.empennage`; `tail_loads`/`vtail_loads` become
   properties over it), the three-view draws the elevator/rudder, and the duplicated
   `LayoutInput` tail fields are retired (schema 26 → 27, oracles bit-for-bit). See
   `docs/40_history/00_completed_development.md`. The landing-gear and wing/fuselage
   single-source follow-ons are backlog Steps G6b/G6c.

---

## 6. Feature scope — closed (2026-07-16)

**In scope for this rework:** §5 items (1) fuselage aero + pitching-moment
estimator (GUI + light calc), (2) longitudinal-stability / trim plots (GUI), and
(4) single-source empennage & control-surface geometry (GUI + model; the elevator
%-chord ask grew into the full single-source empennage step G6).

**Split out** to its own **calc-side backlog item:** §5 item (3) ground-case
distributed fuselage (and wing) loads + the pressurized no-down-select rule — the
heaviest piece, orthogonal to the usability restructure. Tracked as a separate
backlog step (see [`00_backlog.md`](00_backlog.md) → "Ground-case distributed
fuselage loads").

---

## 7. Design principles (apply to every reworked page)

Carried from `GUI_design.md §6` and this document's decisions:

- **One unit per dimension (G-1).** Suffix every label; never mix units for one
  dimension on a page.
- **Read, don't re-ask (G-2).** A page reads geometry/weight/speed from the owning
  slice read-only; only the sole owner edits it. Geometry lives on one page.
- **Form + Apply, merge not replace.** Inputs in `st.form` with an explicit Apply;
  Apply merges targeted fields (never wholesale-replaces a shared slice — the D0
  defect class).
- **No airplane-shaped widget defaults** — blank/neutral defaults; Appendix-A
  numbers live in the loadable example project.
- **LIMIT vs. ULTIMATE marking** — deliverables are ULTIMATE (`-ULT`, per-case
  `SF`); per-module analysis views may show LIMIT only when explicitly marked.
- **Persistent by construction** — every entered value lives on a `Project` slice
  that `io.py` round-trips; nothing input-bearing lives only in `st.session_state`.
