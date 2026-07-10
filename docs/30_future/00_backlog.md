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

**Shipped:** Phases 0–2, Phase-C Steps **C0–C11**, and Phase-D **Step D0–D3**
(GUI defect fix; structured load-case IDs; six-section navigation restructure;
Start-page local-disk persistence). **All 22** of Reference 1's
Appendix-C programs are ported (ENGLOADS, WTESTIMA, WTONECG, WTENV,
WINGGEOM, STRSPEED, MACHLIM, TAU, AIRLOADS, AIRLOAD4, FLTLOADS, SELECT, WINGINER,
NETLOADS, TAILDIST, AILERON, FLAPLOAD, TABLOADS, ONENGOUT, LGFACTOR, LANDLOAD,
BALLOADS), plus **2 modern modules** with no `.BAS` oracle (`configuration`,
`body_loads`).
Schema is at **`SCHEMA_VERSION = 17`**; 266 tests pass; coverage ~92%. The wing
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
Step D1 (structured load-case IDs) shipped 2026-07-08 — see
`40_history/00_completed_development.md` → "Phase D — Step D1". Step D2
(six-section navigation restructure) shipped 2026-07-08 — see
`40_history/00_completed_development.md` → "Phase D — Step D2". Step D3
(Start-page local-disk persistence) shipped 2026-07-09 — see
`40_history/00_completed_development.md` → "Phase D — Step D3". **Step D4
(below) is now the active step.** Invariant throughout: no calc-math
change — the Appendix A/B oracles pass unmodified at every step.

Definition of done per step (in addition to the file-top DoD where it applies):
pages follow the Phase-D page conventions (`02_gui_workflow_plan.md §5` —
form+Apply, merge-writes, read-don't-re-ask, no airplane-shaped defaults), and
the workflow-step ↔ registered-module test stays green.

### Step D4 — Authoritative shared inputs + Aero Coefficients page

Applies the page conventions to the Airplane section. Subsumes the C5
"Configuration seeding follow-ups" (its tasks are folded into D4.3–D4.6).
Design decisions locked 2026-07-09 (see `02_gui_workflow_plan.md` §3 D-5)
before starting; sub-steps below are ordered — D4.1/D4.2 must land before
D4.4 (which reads what D4.1 produces), D4.3 before D4.5/D4.6 (station data),
D4.7 last (reworks pages the earlier sub-steps already touched).

1. **D4.1 — Schema: new `Project.aero_coeffs` slice.** *(shipped 2026-07-09.)*
   `models.py`: new
   `AeroCoefficientsInput` holding `cruise: Optional[AeroCoeffSet]` and
   `flaps_down: Optional[AeroCoeffSet]`. `FlightLoadsInput` keeps only balance geometry (`mac`,
   `wing_area_sqft`, `xw`, `zw`, `xtc`, `xtf`, CG cases) and drops
   `configurations`. `SCHEMA_VERSION` bump + `io.py` round-trip (older files
   load with an empty/default `aero_coeffs`; a legacy `configurations` list
   migrates via `io._legacy_aero_coeffs_from_flight_loads`). `workflow.py`: new
   `aero_coefficients` step in the Airplane section (after
   `structural_speeds`), `module=None`, `produces="aero_coeffs"`, no
   `requires` (mirrors the other GUI-only steps — there is no calc behind pure
   data entry); add `"aero_coeffs"` to the `flight_envelope` step's
   `requires`. `select`/`balloads` (which paired V-n points to their flaps
   state via `fl.configurations`) now read `Project.aero_coeffs` through a
   shared `select._flaps_by_config_name` helper. A placeholder
   `app/views/aero_coefficients.py` (read-only) fills the new nav slot so
   `st.Page` has a file to resolve; `app/views/flight_envelope.py` keeps its
   cruise-coefficient editor in the interim, now writing into
   `project.aero_coeffs.cruise` (preserving any existing `.flaps_down`) — D4.2
   moves that editor to the new page and adds the flaps-down table.
2. **D4.2 — New Aero Coefficients page.** *(shipped 2026-07-09.)*
   `app/views/aero_coefficients.py` (replacing the D4.1 read-only placeholder)
   owns the whole `Project.aero_coeffs` slice as a single `st.form` + Apply:
   a cruise coefficient table/stall-CL pair (defaults 0/blank, no Appendix-A
   literals) plus an "include a flaps-down configuration" checkbox gating a
   parallel flaps-down table; Apply wholesale-replaces `project.aero_coeffs`
   with a fresh `AeroCoefficientsInput` (correct here — unlike a shared slice,
   this page is the sole owner of the whole thing). `flight_envelope.py`
   dropped the cruise-editor block entirely, added a guard ("no aero
   coefficients found... enter them on the Aero Coefficients page first") next
   to the existing `speeds`-missing guard, and now only shows a read-only
   caption naming the cruise/flaps-down configuration in use; kept the
   balance-geometry block and CG-cases block (CG cases stay deferred to D5).
   Verified end-to-end with `streamlit.testing.v1.AppTest` (both pages render
   without exceptions on the GA6 example; Apply round-trips the cruise set
   unchanged; the flight_envelope guard fires when `aero_coeffs` is absent) —
   no automated UI test suite exists yet, so this was a manual/scripted check,
   not a pytest addition. No calc-math change; no schema change beyond D4.1.
3. **D4.3 — Station derivation + Weight DB seeding.** *(shipped 2026-07-09.)*
   `farloads/modules/configuration.py` gained `component_stations(layout) ->
   Dict[str, Vec3]` (`wing`, `fuselage`, `h_tail`, `v_tail`, `tail` — area-
   weighted h/v average for WTESTIMA's single lumped "Tail" item —
   `main_gear`, `nose_gear`, `landing_gear` — weight-weighted ~3:1 main:nose
   average; keys present depend on which layout scalars are set, no
   fabricated zeros) and `match_component_station(name, stations)` (alias
   substring matching, most-specific key first, e.g. "Horizontal tail" before
   the lumped "tail" catch-all). Both pure, no schema change — engine(s) were
   dropped from scope here since `EngineInput.engine_cg` already owns engine
   position (Step D4.6 wires that up, not D4.3). `configuration_layout.py`
   gained a "Seed component stations into Weight DB" button (same pattern as
   "Seed wing geometry") that only fills a `MassItem.x/y/z` still at
   `(0, 0, 0)` — never overwrites a hand-entered station — so it fills the
   zeros `estimate_to_mass_items` leaves. Verified with
   `streamlit.testing.v1.AppTest`: a zero-station item gets seeded, a
   nonzero-station item is left untouched, an unmatched item name is left at
   zero. `tests/test_configuration.py` covers the pure functions directly.
4. **D4.4 — `XLEMAC`/`MAC`/weight read-through to WTENV/STRSPEED.** Ownership
   stays `LayoutInput → wing_surface() → Project.geometry → WTENV/STRSPEED`
   (per `PROGRAM_SPEC.md` — no direct `LayoutInput → WeightEnvelopeInput`
   write; the existing "Seed wing geometry" button already produces this
   path). `structural_speeds.py`: extend the existing `has_wing` gating
   (today only hides wing area) to also read `weight_lb` from
   `project.weight`'s direct totals, read-only with an override checkbox.
   `weight_envelope.py`: same dedup for its `gross` weight entry. Both pages:
   "define in Airplane section" message instead of a literal default when
   upstream data is missing. This is the item that kills the duplicate
   wing-area/MAC/weight entry on Structural Speeds / Flight Envelope.
5. **D4.5 — True CG from `Project.mass`.** Once `Project.mass` is populated,
   `configuration.py`'s `configuration_properties()` (or `_three_view()`
   directly) computes CG as the weight-averaged station across
   `project.mass`'s items instead of `xlemac + 0.25*mac`; falls back to the
   25%-MAC estimate when `project.mass` is absent, with a caption noting which
   source is in use. Tail/prop ground-clearance checks recomputed using the
   D4.3 station data where applicable.
6. **D4.6 — Engine write-back + mass-item overlay on the three-view.**
   `_three_view()` gains a `project.weight`/`project.mass` argument and draws
   a marker per `MassItem` (sized/colored by weight or kind) in all three
   views. Per-engine numeric x/y/z override inputs (not drag-and-drop) default
   to `EngineInput.engine_cg`; Apply writes back into `engine_cg` and
   re-renders the marker. Subsumes "3-view with mass items overlaid" and the
   engine-write-back clause.
7. **D4.7 — Form+Apply conversion, Airplane section.** Applied last:
   convert `configuration_layout.py`, `wing_geometry.py`, `weight_estimate.py`,
   `weight_cg_inertia.py`, `structural_speeds.py`, and the new
   `aero_coefficients.py` to the page conventions (§5): inputs in `st.form` +
   explicit Apply, merge-write, remove remaining Appendix-A-shaped literals
   from these six files down to 0/blank/derived defaults. Scope note: the
   Appendix-A defaults on `flight_envelope`/`weight_envelope`/`mach_limit`/
   `airloads` are **out of D4 scope** — they clean up under D5/D6 when those
   pages get their own form+Apply rework.

**Definition of done (D4-specific, in addition to the file-top DoD and the
per-step DoD above):** `aero_coefficients` step registered and the nav-drift
test green; `SCHEMA_VERSION` bumped with an old-project-file load test; no
calc-math changes (D4 is schema/UI plumbing only) — Appendix A/B oracle tests
pass unmodified; a regression test that loading
`examples/ga6_normal.project.json` and running the D4.3 seed button produces
the same downstream STRSPEED/WTENV/FLTLOADS results as entering the values by
hand today.

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

1. ~~Case-index table included in the export bundle and shown on the Export
   page~~ — done as part of D1 (`sbeam_bridge.case_index_csv_from`, the Export
   page's "Case index" section).
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
