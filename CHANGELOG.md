# Changelog

All notable changes to FAR 23 LOADS are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed

- **VC/VD speed coefficients clamp at W/S = 100 (M1-6, review T9).** The FAR
  23.335(a)/(b) minimum-speed coefficients Kc/Kd are tabulated only to a wing
  loading of 100 lb/ft² (Kc → 28.6, Kd → 1.35). `constants.cruise_speed_coefficient`
  / `dive_ratio_coefficient` kept extrapolating the W/S = 20→100 taper *below* those
  endpoints past 100, understating VC(min)/VD(min) — inert for GA (W/S ≈ 20) but
  non-conservative for the heavy-concept band this tool targets. Both coefficients
  now hold constant at 28.6 / 1.35 for W/S ≥ 100 (matching STRSPEED.BAS, which clamps
  there); the clamp is continuous (the taper reaches the endpoint exactly at 100).
  For W/S > 100 — outside 23.335's tabulated range — `structural_speeds` attaches an
  OUT-OF-BAND note to the design-speeds condition, flagging VC(min)/VD(min) as
  GA-extrapolated advisories and pointing to chosen VC/VD (warn-only, mirroring the
  P1-5 pattern). Boundary + note tests in `test_structural_speeds.py`.

- **One-engine-out 23.367(a)(2) case no longer double-factored (M1-5, review T7).**
  The VC (ultimate) condition carried the default safety factor 1.5 even though
  23.367(a)(2) loads are *defined as ultimate*, so the render/export layer multiplied
  an already-ultimate load by 1.5. The safety factor is now owned by the **load-case
  definition** — set by how the regulation *classifies* the load (LIMIT vs ULTIMATE),
  not by the speed — and each case definition also fixes the **speed range** it is
  considered over (evaluated at the critical high end). Being a *failure* case does
  not by itself reduce the factor. 23.367(a) (turbopropeller; Ref 1 Ch 11 p87;
  VMC = minimum control speed) defines two cases: **(a)(1)** fuel-flow interruption,
  **LIMIT → SF 1.5**, considered VMC→VD (a failure that keeps the full factor);
  **(a)(2)** compressor-from-turbine disconnection / turbine-blade loss,
  **ULTIMATE → SF 1.0**, considered VMC→VC ("limit treated as ultimate"). The VS
  point (VS substituted for VMC per the Ch 11 Method) is a **LIMIT → SF 1.5** design
  point. Each case declares its `load_class`/`safety_factor`, speed range and basis
  as a row in the `_load_cases` table (new `_LoadCase` NamedTuple), carried onto each
  `ConditionResult` (`safety_factor` + `note`), so the VC deliverable now renders
  `lbs-ULT` at `SF=1.0` instead of `SF=1.5`. Three tests added
  (`test_safety_factors_by_failure_mode`, `test_load_case_owns_sf_and_speed_range`,
  `test_rendered_loads_are_ultimate_with_correct_sf`). Not an oracle change (no
  printed ONENGOUT oracle exists; the factor is applied only at the render/export
  boundary).

### Changed

- **23.427(a) unsymmetrical tail: restore the full candidate set (M1-4, review T6;
  approved oracle deviation).** `select_htail_unsymmetrical` no longer filters the
  **unchecked** maneuvers out of the 23.427 search. `SELECT.BAS` lines 6070–6175
  (Ref 1 Appendix C p440–441) load the unchecked cases into the candidate array
  (`L(5)=U1CK`, `L(6)=U2CK`) and take the max over all 12 conditions; 23.427(a)
  applies the unsymmetrical distribution to "the loads prescribed in 23.421
  **through** 23.425", spanning the 23.423 unchecked case. The earlier exclusion
  (citing a "CAM 3.216" rationale) was an undocumented, non-conservative deviation.
  On the Appendix A GA6 the DN unchecked maneuver governs, so the unsymmetrical
  total moves from **−1111.8 → −1204.7** (RH −700.4, LH −504.3, 72%). The Appendix A
  sample output's −1111.8 (gust-governed) is a **stale printout from a superseded
  `SELECT.BAS` revision** — it is inconsistent with its own Appendix C listing, which
  the larger unchecked case (`U2CK` = −1397.835) would win. The listing + the CFR
  are authoritative. The governing condition carries a documented `note`;
  `CriticalCondition` gains a `note` field. `test_htail_gust_and_unsymmetrical_match_appendix_a`
  updated (manual's −1111.8 kept in a comment). Source:
  `reference/23_427_unsymmetrical_candidate_set.md`; register in `CLAUDE.md`.

- **Single-source stall from CLmax (M1-1b; closes old 2-13(b)).** Stall speeds are
  no longer hand-entered scalars. The maximum lift coefficients live once on
  `AeroCoefficientsInput` — `clmax_clean` / `clmax_clean_neg` / `clmax_flap` — and
  STRSPEED, `flap` and `one_engine_out` **derive** VS/VSF from them at the design
  weight (`constants.stall_speed_kt`: `VS = √(295·(W/S)/CLmax)`, User's Guide p7-5),
  which in turn set VA and VF. The `StructuralSpeedsInput.stall_clean_kt` /
  `stall_flap_kt` fields are removed; CLmax is entered on the **Aerodynamic Data**
  page, which now precedes **Structural Speeds** in the workflow (STRSPEED
  `requires=("aero_coeffs",)`). The FLTLOADS balance clamp `AeroCoeffSet.stall_cl`
  stays authored per config (it can differ from the stall-speed CLmax by the 0.9
  stall-margin factor — e.g. Appendix A ga6: `clmax_clean` 1.4068 from the printed
  VS vs FLTLOADS `stall_cl` 1.41); `AeroCoefficientsInput.__post_init__` fills either
  representation from the other only when one is missing, never overwriting. All
  Appendix-A oracles (STRSPEED VA/VF and the FLTLOADS/SELECT envelope) are preserved
  exactly. `SCHEMA_VERSION` → 29; example projects updated.

- **Single-source landing-gear geometry (Phase G, Step G6b).** The tricycle-gear
  geometry native to LANDLOAD — main/nose axle `(X, Z)` at the three strut states,
  rolling radius, strut type, and the main-wheel tread — is now entered **once**, on
  the Geometry page, in a new `GeometryInput.landing_gear` (`LandingGearGeometry`).
  It drives both the three-view (strut + wheels, ground line) and the ground-load
  analysis: `landing.build_landing` syncs it onto `Project.landing` before the
  reaction solve, so the LANDLOAD math is unchanged. The duplicated coarse
  `LayoutInput` gear fields (`main_gear_x`/`nose_gear_x`/`track`/`gear_height`) are
  retired — the three-view and the tip-back/overturn/prop-clearance estimate now
  **derive** the station/track/height from the native axle geometry (ground = static
  axle `Z` − rolling radius), so a stored coarse height that disagreed with the axles
  no longer diverges silently. The Landing Loads page drops its gear/tread widgets
  (reads the geometry read-only), keeping only the non-geometry LANDLOAD inputs. `io`
  migrates a pre-v28 file's top-level `landing` gear (and legacy `LayoutInput` gear
  fields) into `geometry.landing_gear`; `SCHEMA_VERSION` 27 → 28. **Appendix A gear
  reactions unchanged bit-for-bit** (`tests/test_landing_gear_geometry.py`,
  `tests/test_landing.py`).
- **Single-source empennage & control-surface geometry (Phase G, Step G6).** The
  horizontal-/vertical-tail + **elevator/rudder** geometry is now entered **once**,
  on the Geometry page, and drives both the three-view and the rational tail-load
  analysis. A new `GeometryInput.empennage` (`EmpennageInput{htail, vtail}`) is the
  single stored home; `Project.tail_loads`/`.vtail_loads` become **properties**
  proxying to it (so SELECT/TAILDIST/BALLOADS/one-engine-out read them unchanged),
  and the duplicated `LayoutInput` h-/v-tail area/span/arm fields are retired (the
  three-view and the tail-volume static-margin estimate now read the analysis-native
  values; the tail arm is derived from `xt25`/`xv25` minus the 25% wing-MAC station,
  not stored twice). The **three-view draws the elevator and rudder** as the aft
  `Saft/S` chord band, and the Geometry page gains an *Empennage & control surfaces*
  editor (the elevator/rudder geometry's first GUI home — previously JSON-only); the
  Tail Loads page becomes analysis-only (reads the geometry read-only). `io` migrates
  a pre-v27 file's top-level `tail_loads`/`vtail_loads` (and the retired `LayoutInput`
  tail fields) into `geometry.empennage`; `SCHEMA_VERSION` 26 → 27. The derived
  slices are byte-identical, so the **Appendix A SELECT tail-load oracles are
  unchanged** (`tests/test_empennage.py`, `tests/test_select.py`).

### Added

- **Trim & static-margin plots — Flight Envelope page (Phase G, Step G5).** A new
  **Trim & Stability** tab on the Flight Envelope page plots the balancing
  horizontal-tail load at 1-g trim (FLTLOADS BAL A/C/D) swept across the CG range,
  and the tail-volume static margin. A pure `flight_envelope.trim_sweep()` helper
  re-runs the existing FLTLOADS balance (subroutine 3900) at ~15 interpolated CG
  stations at a fixed weight/waterline — no new load equations, so a swept station
  that coincides with a project CG case reproduces that case's `build_envelope` BAL
  load exactly. The static-margin sweep reads the tail-volume **neutral point** from
  the Configuration module (`SM = NP − CG`, %MAC) and overlays the WTENV
  forward/aft CG limits; it is shown only when the project carries a parametric
  layout (Appendix A/B fixtures show just the trim plot). Tail loads on the tab are
  **LIMIT** (marked, with the ULTIMATE deliverables pointed to on the Critical
  Loads tab / Results Review / exports). GUI-only over existing calc — no schema
  change. (Config-building for the balance was factored into
  `flight_envelope._balance_configs`, shared by `build_envelope` and `trim_sweep`
  so both see the same G4 fuselage-augmented coefficients; behaviour unchanged.)
- **Fuselage pitching-moment estimator — Munk slender-body (Phase G, Step G4).** A
  pure, geometry-only helper (`farloads/fuselage_moment.py`) derives the fuselage's
  contribution to the airplane-less-tail moment slope `dCm/dα` from the G1 fuselage
  outline (Munk apparent-mass method, NACA TR-184 / DATCOM 4.2.1.1; see
  `reference/fuselage_pitching_moment.md`), so a concept airplane built from a
  planform no longer has to hand-fold the fuselage into the FLTLOADS input
  coefficients. Surfaced on the **Aerodynamic Data** page: the estimate (volume,
  fineness ratio, `k₂−k₁`, ΔM1) is displayed and overridable, with an enable
  checkbox. A new `AeroCoefficientsInput.fuselage_moment` field
  (`FuselageMomentInput{enabled, d_cm_dalpha}`) carries it; when enabled,
  `flight_envelope.build_envelope` adds ΔM1 to every configuration's M1 (a local
  copy — the stored raw coefficients are untouched) and the compressibility factor
  applies automatically. **Off by default → Appendix A/B oracles bit-for-bit
  unchanged** (their coefficients already include the fuselage). `SCHEMA_VERSION`
  25 → 26; older files load with no fuselage moment.

### Changed

- **Phase-1 page consolidation — Develop V-n diagram (Phase G, Step G3).** The
  *Develop V-n diagram* section collapses from ten nav pages to five, using
  `st.tabs` where a page gathers formerly-separate pages. New **Weight & Mass
  Properties** page (`app/views/weight_mass.py`) with tabs *Estimate* (WTESTIMA) ·
  *Weight, CG & Inertia* (WTONECG) · *Payload Cases* · *Weight / CG Envelope*
  (WTENV) — the single owner of all weight/mass data. **Structural Speeds** gains a
  *Design Speeds* / *Speed–Altitude Envelope* (MACHLIM) tab split; **Flight Envelope
  (V-n)** gains a *V-n diagram* / *Critical Loads (SELECT)* tab split (the FLTLOADS
  balance inputs stay on the page, shared by both tabs). Six view files are deleted
  and folded (`weight_estimate`, `weight_cg_inertia`, `payload_cases`,
  `weight_envelope`, `mach_limit`, `critical_loads`); `workflow.FOLDED_MODULES` gains
  `weight_estimate`, `weight_envelope`, `mach_limit`, `select` (each still a
  registered/tested calc module, now without its own nav step). **No calc, schema,
  or oracle change** — the folded modules and `Project` slices are untouched; only
  which page edits a slice moved. Cross-page captions/warnings updated to the new tab
  locations.
- **Workflow-aligned navigation re-sequence (Phase G, Step G2).** The GUI sidebar
  is re-grouped from the historical Phase-D sections into the FAR 23 analysis flow
  (decision G-4): an un-numbered **Start** app-shell group (Project Dashboard, JSON
  Editor) above the six numbered analysis phases **1 · Develop V-n diagram → 2 ·
  Flight loads → 3 · Other loads → 4 · Landing loads → 5 · Load-case plotting → 6 ·
  Export**. The old **Airplane**/**Envelopes & Critical Conditions** split dissolves
  — geometry, all weight/CG pages, both speed pages, aero data, and V-n + SELECT now
  sit together under *Develop V-n diagram*; *Landing Loads* moves after the
  control-surface/engine *Other loads* group. `farloads/workflow.py` (`PHASES`
  renamed, `STEPS` reordered/reassigned) and `app/Home.py` (`_PHASE_LABEL`) carry the
  change; the Dashboard caption follows. **Grouping/labels only — no page bodies, no
  calc, no schema change** (the per-page consolidation into §4's 1a–1e sub-steps is
  the separate Step G3). The nav-drift guard test stays green.
- **Geometry single source of truth, incl. fuselage (Phase G, Step G1).** The two
  geometry-owning pages — Configuration & Layout (parametric `LayoutInput`) and
  Wing / Surface Geometry (WINGGEOM planforms) — are merged into **one Geometry
  page**, and their two project slices are **unified into one** (`SCHEMA_VERSION`
  **24 → 25**): the parametric layout (formerly the top-level `Project.configuration`)
  and a new **fuselage outline** move onto `GeometryInput` as `.parametric` and
  `.fuselage`, alongside the unchanged `.surfaces`. The oracle-locked `.surfaces`
  consumers (AIRLOADS, WINGINER, NETLOADS, …) are untouched. The **fuselage is now a
  real geometry entity** — a station-area table (`FuselageOutline`/`FuselageSection`,
  cross-section width/height vs. station) that drives the three-view body profile and
  seeds the future Step G4 pitching-moment estimator; older files default it from the
  `fuselage_length/width/height` scalars on load. Downstream pages (flight envelope,
  structural speeds, weight, tail/wing loads, aircraft comparison) read geometry
  **read-only** through the unified slice. `workflow.py` collapses to one **Geometry**
  step (the `wing_geometry` module is folded in via `FOLDED_MODULES`); legacy project
  files migrate on load (`io.py` folds the top-level `"configuration"` block onto
  `geometry.parametric`). **Appendix A/B oracles unchanged.** New tests:
  fuselage-outline default + round-trip (`test_configuration.py`, `test_io.py`) and
  the legacy-`configuration`→`geometry` migration (`test_io.py`).
- **Canonical display units — one unit per dimension (Phase G, Step G0).** The GUI
  now shows a single unit per physical dimension: **length → `in` (SI `mm`), area →
  `ft²` (SI `m²`)**. The geometry inputs that previously carried a different unit are
  renamed to canonical-unit field names and stored in canonical units
  (**`SCHEMA_VERSION` 23 → 24**): `TailLoadsInput.airplane_length_ft` and
  `VTailLoadsInput.{airplane_length_ft, wing_span_ft, vtail_mac_ft}` → `*_in` (×12);
  `LayoutInput.{h_tail_span_ft, v_tail_span_ft}` → `*_in` (×12);
  `TabSpec.area_sqin` → `area_sqft` (÷144). The redundant `length_ft`/`area_sqin`
  kinds are removed from `farloads/units.py` (`SI_PER_IMPERIAL`, `UNIT_LABELS`,
  `_KIND_FACTORS`); `_PROJECT_FIELD_KIND` maps the renamed keys. **Calc results are
  unchanged** — the original ft/in² math is restored internally, so the Appendix A/B
  oracles are untouched. Older project files migrate on load (`io.py`
  `_rename_legacy_units`); the bundled `examples/*.json` (older schema versions) load
  via that path. New guardrail tests: one-label-per-dimension (`test_units.py`) and
  legacy-key migration (`test_io.py`).

### Documentation

- **Phase G — detailed plan for G0/G1 + canonical-units decision.** Locked the
  G-1 canonical display units (length → `in`/`mm`, area → `ft²`/`m²`) in
  `docs/30_future/03_gui_rework_plan.md` §2, and expanded `00_backlog.md` → Phase G
  steps **G0** (units collapse: retire the redundant `length_ft`/`area_sqin` kinds
  in `units.py`, remap `_PROJECT_FIELD_KIND`, sweep the views — display-only, no
  oracle change) and **G1** (geometry single-source-of-truth: consolidate
  `configuration_layout` + `wing_geometry`, add the fuselage as a geometry entity
  with schema bump, downstream read-through) with file-level scope, guardrails and
  sequencing. Docs only — no code, calc, or schema change.

- **Phase G — workflow-aligned GUI rework plan.** Added
  `docs/30_future/03_gui_rework_plan.md` (renamed/expanded from the draft
  `fix_the_gui.md`): assessment of the redesign proposal against the shipped
  Phase D/E/F GUI, locked decisions G-1…G-4 (one-unit-per-dimension,
  single-source-of-truth geometry incl. the fuselage, re-entry vs. true-loss
  persistence, genuine analysis-flow re-sequencing), and the target six
  analysis-flow sections with their page mapping. Seeded the step-by-step plan
  into `00_backlog.md` → Phase G (Steps G0–G8) plus the split-out calc item 2-12
  (ground-case distributed fuselage loads + pressurization); indexed in
  `00_INDEX.md` and cross-linked from `GUI_design.md`. Docs only — no code, calc,
  or schema change.

### Added

- **Concept engine gyroscopic guard + warn (Phase 1, Step P1-5).** The optional
  FAR 25.371 gyroscopic concept case (`engine.condition_25_371`) uses a fixed
  FAR 23.371(b) stand-in (2.5 rad/s yaw, 1 rad/s pitch); the gyro moment is linear
  in body rate, so the stand-in under-predicts for a concept whose real rates are
  higher. `EngineInput` gains two optional advisory fields —
  `design_yaw_rate_rad_s` / `design_pitch_rate_rad_s` (**`SCHEMA_VERSION` 22 → 23**,
  additive; older files load with both unset) — and when a declared rate exceeds its
  stand-in the case's note becomes an explicit `WARNING -- gyroscopic loads
  UNDER-PREDICTED …` (naming the axis, rate and moment ratio). Per decision D-2 this
  is **warn-only**: the reported moment stays at the fixed stand-in (the declared
  rates are advisory, not a re-derivation). The engine GUI page adds the two rate
  inputs and renders `WARNING` notes as `st.warning`. The GA/oracle path is
  unchanged (no declared rates → no warning). Guarded by five new tests in
  `tests/test_engine_far25.py`.

- **Complete export package public API (Phase 1, Step P1-4).**
  `farloads/export/__init__.py` now re-exports all four component families +
  the case index: the body (`body_span_load_csv`, `body_force_moment_cards`),
  control-surface (`control_surface_csv`/`control_surface_force_moment_cards` +
  their `write_*` variants), and case-index (`case_index_csv`,
  `write_case_index_csv`, `filter_by_selected_case_ids`) functions were previously
  reachable only via the `sbeam_bridge` submodule (`__all__` advertised wing + tail
  only). The package docstring is rewritten from "wing-only" to enumerate all four
  families. Guarded by `test_sbeam_bridge.py::test_export_package_exposes_all_component_families`.
  API-surface-only (no calc-math or schema change).

- **Concept↔FAR23 identity test (Phase 1, Step P1-3).** `tests/test_concept.py`
  now guards the C-1 invariant ("concept mode reduces **exactly** to FAR23 on GA
  inputs") *directly, through the concept branch* — previously it was only assumed
  via the absence of GA-oracle regression. `test_concept_reduces_to_far23_on_ga_inputs`
  runs `ga6_normal` through `run_all_modules` twice — once as Normal (`category="N"`)
  and once flipped to concept (`category="C"`) with the FAR23-computed load factors
  (n = 3.8, nneg = −1.52 per 14 CFR 23.337, derived from the baseline) — and asserts
  full-pipeline parity (every module's every `LoadValue` matches at `rel_tol=1e-3`;
  only the appended concept `note` may differ). `test_concept_load_factors_match_far23_caps`
  pins the single numeric divergence point (`structural_speeds._maneuver_load_factors`).
  Test-only (no calc-math or schema change); FAR23 oracles unmoved.

- **Concept distributed-loads closure suite (Phase 1, Step P1-2).**
  `tests/test_concept_closure.py` (10 tests) drives `net_loads`, `body_loads`,
  `taildist`, `aileron`/`flap`/`tab` through the P1-1 concept fixture
  (`concept_regional_jet`) and asserts **physics-closure per component** — concept
  mode's only validation above the 12,500 lb FAR23 oracle band. Checks: wing lift
  closes vertically (`LZW + LT = Nz·W`); the balancing tail load reacts the pitching
  moment about the CG (`LT·(Xt−Xcg) = LZW·(Xcg−Xw) − DX·(Zcg−Zw) + M(W+F)`); the
  fuselage net distribution is free-free (terminal cumulative shear = 0); TAILDIST
  carries SELECT's `lt25`/`lt50` split verbatim; each control surface's `build_*`
  load matches its `run` analysis report; and every component family's nodal FORCE
  set (and its re-parsed cards) sums to that component's root/total at ULTIMATE —
  the whole concept airframe exports cleanly through `sbeam_bridge`. Test-only
  (no calc-math or schema change); FAR23 oracles unmoved.

- **Full-airframe concept reference fixture (Phase 1, Step P1-1).**
  `examples/concept_regional_jet.project.json` — "RJ-50 concept", a swept-wing,
  high-subsonic twin-turbofan regional jet (MTOW 33,000 lb, S 500 ft², c/4 sweep
  24°, cruise M 0.74, 50 seats; `category="C"`, Part 25 load factors, `include_far25`).
  It is the first concept example to drive **every** component path — the wing chain,
  `body_loads`, `taildist`, `aileron`/`flap`/`tab`, and the swept `AIRLOAD4` branch
  (19 modules, no missing-slice skips) — where `concept_heavy` reached the wing only.
  Carries the two slices no GA fixture had (`fuselage_mass`, `configuration`); the
  turbofan is modelled with a fan-spool `Rotor` and no propeller (25.371 gyro path).
  Guarded by `tests/test_concept_regional_jet.py`. Airplane per decision D-1, engine
  per D-2.

- **Aircraft Comparison page (Phase F, Step F2).** A dedicated
  `app/views/aircraft_comparison.py` view in the **Export** phase (before Results
  Review; GUI-only `WorkflowStep`) is now the single home for the fleet comparison.
  It carries a quantitative readout (nearest-3, W/S & W/P percentile band, outliers),
  a **parameter table** (subject + nearest-N over MTOW/OEW/power/W-S/W-P/wingspan/
  area/AR/seats), and **six scatter tabs** (W/S-vs-W/P, MTOW-vs-OEW, and wingspan /
  wing area / aspect ratio / seats vs. MTOW). `Subject` (and `FleetPoint`) gain
  presentation-only `wingspan_ft`/`aspect_ratio`/`seats` fields plus `span` /
  `aspect_ratio_effective` derivations (`span = √(AR·S)`); the nearest-N distance
  stays on MTOW / W/S / W/P, so `fleet_stats` is byte-identical (decision D-F2-a).
  Guarded by new `tests/test_aircraft_comparison.py` and extended
  `tests/test_fleet_compare.py`. No calc-math or oracle change.

- **Reference-fleet expansion for the Aircraft Comparison page (Phase F, Step
  F1).** `app/data/reference_aircraft.csv` gains an `aspect_ratio` column (span²/area)
  and six aircraft (PA-28-181 Archer, Cirrus SR22, Diamond DA40, Extra 300, PA-44
  Seminole, TBM 940 — 23 → 29) to broaden the geometric spread. `FleetPoint` carries
  optional `seats` / `wingspan_ft` / `aspect_ratio` (defaults; `fleet_stats`
  unaffected), and `_fleet_points` maps them. Data-only; no calc-math or oracle
  change. Guarded by `tests/test_reference_aircraft.py`.

- **`farloads.constants.convert_airspeed` + `eas_to_mach`/`mach_to_eas` (Phase E,
  Step E7).** Presentation-layer airspeed conversions: KEAS→KTAS (=KEAS/√σ) and
  KEAS→KCAS (standard subsonic compressible impact-pressure relation, exact at sea
  level). Backed by `tests/test_airspeed_conversions.py`.

### Changed

- **Fleet comparison moved to its own page (Phase F, Step F2).** The shared
  `app/components.render_fleet_comparison` helper (its private `_fleet_points` /
  `_fleet_readout`) and the fleet block on **Configuration & Layout** and **Weight
  Estimate** are removed; the comparison now lives only on the new Aircraft
  Comparison page. `app/components.py` retains just the FAR 23 applicability banner.

- **Mach Limit page reworked into the Speed–Altitude Envelope (Phase E, Step E7).**
  MC, MD and the shoulder altitude are now read from the Structural Speeds `speeds`
  slice instead of being re-entered — only the max operating altitude and increment
  remain as inputs. The chart is now a transport-category-style speed–altitude
  flight-limits diagram: altitude on the y-axis, a **KEAS/KCAS/KTAS** selectable
  x-axis, a constant-Mach fan, and the design-speed boundary drawn EAS-limited below
  the shoulder and Mach-limited above it (VC/MC and VD/MD kink at the shoulder). The
  workflow step is retitled "Speed–Altitude Envelope". GUI + one new pure helper; no
  calc-math or oracle change (`mach_limit_lines` untouched).

- **V-n diagram consolidated onto the Flight Envelope page (Phase E, Step E6).**
  The suite had two V-n diagrams: the continuous LIMIT textbook envelope on the
  **Structural Speeds** page (Step E3) and the rigorous, Mach-corrected balanced
  corner points on the **Flight Envelope (V-n)** page — redundant. The continuous
  LIMIT envelope (from the pure `farloads/vn_diagram.py` helper) is now drawn as a
  grey backdrop on the Flight Envelope page, behind the rigorous balanced markers,
  so the envelope visibly *bounds* them in a single figure. It is rebuilt there from
  `project.speeds` (already a required slice) via `design_speed_values` — no new
  inputs. The Structural Speeds page now shows only its numeric design-speed tables
  plus a pointer to the Flight Envelope page. GUI-only; no calc math changed
  (`vn_diagram` and its tests are untouched).

### Fixed

- **AIRLOAD4 swept-wing renormalization restored (M1-3, review T4 — `[Major]`).**
  The swept-branch span-load correction subtracted the Pope & Haney sweepback term
  but omitted AIRLOAD4.BAS's `COL20 = COL19/CLCOL19` renormalization, so a swept
  concept wing's span load integrated to **less** than the operating CL — the
  shipped `concept_regional_jet` flagship (Λ=24°) lost **9.6%** of its lift
  (`recovered_cl` 0.452 vs target 0.50; 6–13% across Λ=20–30°), non-conservative and
  flowing into the `net_loads` → sbeam FORCE/MOMENT export. `airloads._apply_sweep`
  is replaced by `_sweep_operating`, which applies the Pope subtraction **and** the
  renormalization to the **combined operating** distribution (matching AIRLOAD4.BAS
  `COL16` — twist is redistributed too, not additive-only), at `target_cl` for the
  report/closure path and per-condition at each case's CL for the deliverable path.
  Renormalization uses the physically-correct span-load integral (the literal
  chord-weighted `CLCOL19` line is OCR-garbled and closes only to ~0.3%; span-load
  form closes exactly — Decision 3). `recovered_cl` on the flagship now recovers
  0.500; the unswept GA Appendix-A additive and the Λ=0 reduction invariant are
  unchanged. Guarded by a Λ≠0 closure test, a listing-traceable COL18/COL19/COL20
  reconstruction, and a deliverable per-case CL-recovery test.

- **`BAL 1.4VSF` balances at the 1-g flaps-down stall (M1-2, review T2 — `[Critical]`).**
  In the flaps-extended envelope corner set, `flight_envelope._flap_config_points`
  captured the **STALL 2G** speed and ran the `BAL 1.4VSF` balancing point at 1.4×
  that. `FLTLOADS.BAS` (Code.pdf p300–302) saves the **STALL 1GL** (1-g flaps-down
  stall) speed for this condition; since STALL 2G ≈ √2 × STALL 1G, the balance speed
  was ~1.4× too high and the balancing tail load (∝ V²) ~2.2× too large, feeding the
  SELECT search and sbeam export. Fixed to balance at 1.4× the STALL 1GL speed. On
  Appendix A p181 (LANDING CG5, case 89 `BAL 1.4VS`) the corrected point is V 83.6 kt
  / LT −430 lb; the defect produced ~116 kt / −957 lb. The real landing-config aero
  polynomials (Appendix A p179 input listing) are now transcribed into the
  `flight_envelope` test fixture — correcting the 0.2.0 baseline note that the repo
  lacked them — and the new `test_bal_1p4vsf_balances_at_one_g_flaps_down_stall`
  asserts both the exact fix invariant and the p181 oracle. The shipped
  `examples/ga6_normal.project.json` is unchanged (it carries no `flaps_down` set),
  so no existing envelope/SELECT/export result moved; activating the full
  flaps-extended SELECT→TAILDIST pipeline in the example stays with L-2.

- **VD floor now enforces `K_d·VCmin` (M1-1, review T1 — `[Critical]`).**
  `structural_speeds.py` computed the K_d dive-speed term as `K_d·VC` and reported
  it only as a "recommended" advisory, so on the **no-chosen-speeds** path VD fell
  to the `1.25·VC` floor. FAR 23.335(b) and `STRSPEED.BAS` (`V2DMIN=K2·V1CMIN`,
  lines 380/390) require **both** minimums with the K_d term on the *minimum* cruise
  speed: `VD ≥ max(K_d·VCmin, 1.25·VC)`. On the Appendix A Cat-N no-chosen-speeds
  case (p155) the corrected VD is **198.53 kt**; the prior code returned 177.26 —
  10.7% non-conservative, propagating into MD/MACHLIM and every case at VD. The
  chosen-speeds worked example (p156, VD 212.5) clears both floors and is unchanged.
  Concept mode (Cat C) keeps only the absolute 1.25·VC floor and reports K_d·VCmin
  as advisory (behavior unchanged). Reported `LoadValue` renamed
  "Recommended dive VD (gust, K*VC)" → **"Minimum dive VD(min)"** (the enforced
  floor). New oracle `test_vd_floor_no_chosen_speeds` (p155).

- **FAR-citation labels corrected (found via the FAA User's Guide review).**
  `WTONECG` (`weight_onecg.py`) cited `23.21/23.23` (proof-of-compliance + load
  distribution); changed to **`23.23/23.29`** — load-distribution limits and empty
  weight & corresponding CG, the quantities the module actually computes (User's
  Guide §4.3). `FLTLOADS` (`flight_envelope.py`) `_FAR` omitted **23.345**
  (high-lift devices) despite building the oracle-tested flaps-down envelope; now
  `23.333/23.337/23.341/23.345/23.421`. Labels only — no load value changes. (The
  SELECT v-tail side-gust `23.443(b)` was reviewed and deliberately kept: the
  McMaster `SELECT.BAS` grounds the gust-load formula in (b).)

- **TAILDIST mis-cited every chordwise tail condition as `23.421` (found via the
  FAA User's Guide review).** `taildist.run` hardcoded `far_reference="23.421"`
  (balancing loads) on every emitted `ConditionResult`, so the v-tail distributions
  (23.441/23.443) and the h-tail maneuver/gust/unsymmetrical rows (23.423/425/427)
  were all reported as "23.421 Balancing Loads." The correct citation was already on
  the source SELECT `CriticalCondition.far_reference` but was discarded because
  `TailChordResult` did not carry it. `TailChordResult` gains a `far_reference` field
  (populated verbatim from the governing condition, serialized by `io`), and
  `taildist.run` now cites `r.far_reference or "23.421"`. Load magnitudes are
  unchanged (citation-only). Regression: `test_far_reference_propagates_from_select`
  in `tests/test_taildist.py`. Additive field, defaulted `""`; older projects load
  unchanged. Source: FAA User's Guide §20.2.2/20.2.3 (DOT/FAA/AR-96/46).

- **Swept-wing aero fields dropped by the JSON round-trip (found via Step P1-1).**
  `AeroSurfaceInput.sweep_deg` / `design_mach` (the fields that auto-select the
  swept/high-Mach `AIRLOAD4` branch, added in Step C7) were never serialized by
  `io._aero_surface_from_dict` / `aero_to_dict`, so a swept wing loaded from disk
  silently reverted to the low-speed Schrenk path. No GA fixture set these fields,
  so the gap was invisible until the swept `concept_regional_jet` fixture. Both
  directions now carry them; additive and defaulted (0.0), so every existing project
  loads unchanged. Regression: `tests/test_concept_regional_jet.py`.

- **Weight Estimate page crashed on beyond-GA projects.** The Mission-inputs form
  hard-capped its widgets at GA-tier limits (`max_value = 3000 hp`, 12 seats, 6
  engines, 10 hr) while seeding each widget from the loaded project, so opening a
  project whose value exceeded a cap raised `StreamlitValueAboveMaxError` before
  the page could render (e.g. `examples/dhc8_dash8.project.json` at 4000 hp / 39
  seats). The hard `max_value` caps are removed (keeping `min_value` for physical
  sanity), consistent with the concept-aware superset that must accept airplanes
  beyond the GA band (`GUI_design.md §9` — warn, don't block). Regression:
  `tests/test_views_smoke.py::test_weight_estimate_accepts_beyond_ga_power` loads
  the DHC-8 into the page and asserts no exception.

### Changed

- **Load-path robustness (Phase E, Step E5).** The three sidebar load actions
  (Open saved, Load example, Upload) now fail **gracefully**: a malformed or
  wrong-shape file shows an `st.error` ("Couldn't load …: …") instead of an
  uncaught traceback, matching the JSON Editor's behavior. Both the sidebar and the
  Project JSON Editor now run a **soft `SCHEMA_VERSION` check**: a file from a
  *newer* app version warns and still loads (unrecognized fields ignored); an
  *older* file is migrated in place (its field-presence migration already ran in
  `io.py`; the version stamp is bumped to the current `SCHEMA_VERSION`), surfaced as
  a brief toast in the sidebar / an info line in the editor. The classification is
  the new pure, unit-tested `farloads.io.schema_status(version) -> (status,
  message)` (no Streamlit). GUI-only: no schema change (`SCHEMA_VERSION` stays
  **22**) and no calc-math change — the Appendix A/B oracles are untouched (347
  tests pass, +4). Implements `GUI_design.md §10`.

### Added

- **Quantitative fleet comparison (Phase E, Step E4).** The visual, duplicated
  fleet scatters on **Configuration & Layout** and **Weight Estimate** are unified
  behind one shared helper that adds a **quantitative readout** above the scatters:
  the **nearest-3** similar reference aircraft (by a normalized distance over
  log-MTOW plus W/S and W/P where known), the **W/S and W/P percentile band**, and
  **outlier flags** (outside the fleet p10–p90). The numeric core is the new pure,
  unit-tested `farloads/fleet.py` (`fleet_stats(subject, fleet) -> FleetStats`; no
  pandas / file access / Streamlit); the CSV load and rendering are the single
  `app/components.render_fleet_comparison`, reused by both pages. Jets (`max_hp = 0`)
  are excluded from the W/P comparison only, never from the comparator pool.
  GUI-only: no schema change (`SCHEMA_VERSION` stays **22**) and no calc-math change
  — the Appendix A/B oracles are untouched (343 tests pass, +10). Implements
  `GUI_design.md §8.4`.
- **Graphical review + input-consistency validation (Phase E, Step E3).** Two new
  pure, unit-tested helpers and their GUI surfacing. `farloads/vn_diagram.py` builds
  a proper **V-n diagram** — the curved stall boundary `n = (V/VS)²`, the flaps-up
  and flaps-down (n ≤ 2.0, 14 CFR 23.337(b)) manoeuvre envelopes and the gust lines
  at VC/VD (textbook Pratt form, 14 CFR 23.341) — now shown on the **Structural
  Speeds** page (Flaps up/down/both + gust toggle, LIMIT-marked; the rigorous
  Mach-corrected gust V-n stays on the Flight Envelope page, unchanged).
  `farloads/validation.py` adds `consistency_warnings(project)` — taper > 1,
  non-positive area, LE/TE ordering, Configuration-vs-WINGGEOM wing-area mismatch,
  and CG outside the WTENV structural envelope — surfaced as `st.warning` on the
  relevant definition pages. The **Weight/CG/Inertia** page gains a CG-marker +
  mass-distribution plot (with the WTENV limits when defined). GUI-only in effect:
  no schema change (`SCHEMA_VERSION` stays **22**) and no calc-math change — the
  Appendix A/B oracles are untouched (333 tests pass, +18). Implements
  `GUI_design.md §8.2/§8.3`.
- **Parameter explanation — tooltips + guides (Phase E, Step E2).** Every domain
  input widget across the six Airplane-definition pages (Configuration & Layout,
  Wing / Surface Geometry, Weight Estimate, Weight/CG/Inertia, Structural Speeds,
  Aerodynamic Data) now carries a `help=` hover tooltip citing the relevant FAR
  paragraph and Reference-1 program/chapter; the three grid (`st.data_editor`)
  pages and the dense pages additionally carry a collapsible **"ℹ️ Parameter
  guide"** expander defining the jargon (MAC, XLEMAC, static margin, neutral
  point, tip-back/overturn, shoulder altitude, KEAS, the aero `C0…C4`
  polynomials, per-item inertias and the parallel-axis convention). GUI-only:
  no schema change (`SCHEMA_VERSION` stays **22**) and no calc-math change — the
  Appendix A/B oracles are untouched (314 tests pass). Implements
  `GUI_design.md §8.1`.
- **FAR 23 applicability detection + occupants/crew fields (Phase E, Step E1).** The
  GUI now surfaces — never blocks — when an airplane exceeds the FAR 23 applicability
  band. New pure, unit-tested `farloads.far23_applicability(project)` returns the
  structured exceedances (field / value / limit / label) against the non-commuter
  FAR 23 tier (12,500 lb / 9 passenger seats, the required flight crew excluded);
  the limits live once in `farloads/constants.py` (`FAR23_MAX_WEIGHT_LB` etc.,
  `DEFAULT_FLIGHT_CREW = 1`, with the 19,000 lb / 19-seat commuter tier encoded but
  dormant until a distinct Commuter category exists). Two additive schema fields
  (`SCHEMA_VERSION` **20 → 22**, older files load with defaults): a
  `StructuralSpeedsInput.occupants` field (total souls; falls back to the Weight
  Estimate seat count) entered on **Structural Speeds** and echoed read-only on
  **Configuration & Layout**; and a `WeightEstimationInput.crew` field (flight crew,
  default 1) entered on **Weight Estimate**, subtracted from occupants for the seat
  check (`passenger seats = occupants − crew`) and carried in a new derived
  **operating empty weight** line WTESTIMA reports (`OEW = empty + crew×170`, a
  reporting-only figure — `MTOW`/`useful`/`empty` and their Appendix-A oracles are
  untouched). A shared `app/components.render_applicability_banner` renders a
  non-blocking banner on the **Dashboard** and the definition pages with a one-click
  **"Switch to Concept"** action that flips `speeds.category = "C"` and seeds
  `chosen_n`/`chosen_nneg` from the computed FAR 23.337 factors so the switch is
  continuous. No calc-math change — the Appendix A/B oracles pass unmodified and
  concept mode still reduces exactly to FAR 23 on GA inputs. Tests:
  `tests/test_applicability.py` (GA → no exceedances; 20,000 lb / 12-occupant Normal
  → weight + seat exceedances; crew reduces the seat count), the OEW line in
  `tests/test_weight_estimate.py`, and occupants/crew io round-trip / old-file
  defaults in `tests/test_io.py`.

- **Definition pages seed defaults from upstream project data.** Pages no longer
  re-ask for a quantity another slice already owns. New
  `farloads.modules.configuration.wing_layout_from_surface()` (the inverse of
  `wing_polylines`) lets **Configuration & Layout** seed its parametric wing
  fields (area / aspect ratio / taper / LE sweep / LE station) from an existing
  WINGGEOM `wing` surface; **Flight Envelope** seeds MAC / wing area / 25%-MAC
  station from that surface (and waterline from `configuration`) instead of
  hardcoded Appendix-A literals; **Mach Limit** seeds `MC`/`MD`/shoulder
  altitude from STRSPEED's `design_speed_values`; **Tail Loads** seeds the
  h/v-tail spans from `configuration.h_tail_span_ft`/`v_tail_span_ft`; **Wing
  Loads** seeds dihedral from `configuration.dihedral_deg`. Each seed fires only
  when the page's own field is still unset, so an explicit value is never
  overwritten. No calc-math change, no new `Project` slice, `SCHEMA_VERSION`
  unchanged at 20.

- **Airplane-phase GUI usability pass: tail geometry, wing planform plot,
  aero-data naming.** `LayoutInput` gains `tail_type` (`TailType`:
  `CONVENTIONAL`/`T_TAIL`/`V_TAIL`/`CRUCIFORM`, additive, default
  `CONVENTIONAL`) plus `h_tail_span_ft`/`h_tail_z`/`v_tail_span_ft` (all
  default `0.0`, backward-compatible — an older project with these unset draws
  no tail, exactly as before). New `farloads.modules.configuration.
  tail_planform()` sketches the tail panel(s) for the Configuration & Layout
  three-view, which now draws them in Top/Side/Front alongside the existing
  wing/fuselage/gear overlays. The Wing/Surface Geometry page gains a top-view
  planform plot (new shared `farloads.modules.wing_geometry.
  surface_top_outline()` helper, also used by the three-view's wing outline).
  The `aero_coefficients` Airplane-phase step is retitled "Aerodynamic Data"
  (key unchanged) with a cross-link caption to the Wing Loads page, where the
  per-surface spanwise (Schrenk) aero input stays, with a matching caption
  pointing back. `SCHEMA_VERSION` bumped 19 → 20 (additive fields only).

- **Session-wide Imperial/SI display toggle + Project JSON Editor page.** A
  single sidebar control (`app/Home.py`, `st.session_state["unit_system"]`)
  now drives Imperial/SI display consistently across every GUI page (all 24
  views), replacing the handful of pages that previously had their own local,
  uncoordinated toggle. New `farloads.units` scalar helpers (`to_si_scalar`,
  `si_scalar_label`) convert per-station/per-case dataclass values (wing/
  fuselage/tail/landing-gear results) that aren't `ConditionResult`/`LoadValue`
  based; every conversion is display-only — the objects feeding sbeam BDF
  export, project persistence and CSV downloads stay canonical Imperial.
  Airspeed (KEAS) and altitude (ft) are never converted (aviation-standard
  units in both systems). New `app/views/project_editor.py` (Start section):
  the whole project shown/hand-editable as JSON in the selected units, backed
  by new `farloads.units.project_dict_to_display`/`project_dict_to_imperial`
  (a field-name-driven whole-project converter, distinct from mass-vs-force
  `_lb` fields); Apply converts back to Imperial before updating the session.
  `project.json` on disk is unchanged — still Imperial-only, no unit tag ever
  written, no new `Project` slice, `SCHEMA_VERSION` unchanged at 19.

- **Export & report upgrades** (Phase D Step D8 — closes Phase D). Export page
  gains a "📊 Download workbook (.xlsx)" button (new `farloads/export
  /workbook.py::build_workbook`, `openpyxl` dependency): one workbook tab per
  module/component (Project info, per-module load-case CSVs, the case-index
  table, and the tabular sbeam span-load CSVs), a sibling alternative to the
  `.zip` bundle. Export page also gains an "Export scope" toggle (Full set /
  Governing set) that filters the fuselage/tail sbeam artifacts and the case
  index to the D5 Critical Loads page's selection (new pure helper
  `sbeam_bridge.filter_by_selected_case_ids`); wing and control-surface
  exports always include the full set since their case ids don't overlap
  `envelope.critical`'s (a known, documented gap — see the backlog). No
  calc-math change, no new `Project` slice, `SCHEMA_VERSION` unchanged at 19.

- **Loads Plots page** (Phase D Step D7). New `app/views/loads_plots.py`, the
  sixth workflow section: a read-only, consolidated viewer over the
  distributed-load results already persisted on `Project.loads` by the
  Analysis pages — a component picker (wing / fuselage / horizontal tail /
  vertical tail / aileron / flap / tab), overlay plots by case ID with a
  max-|value| envelope trace, a combined wing+fuselage "total loads" snapshot,
  and an external-comparison CSV importer reusing
  `farloads.export.sbeam_bridge.span_load_csv`/`body_span_load_csv`'s exact
  column schema. `farloads/workflow.py` gains the `loads_plots` step
  (`module=None`, like `dashboard`/`results_review`/`export_report`), which
  makes "5 · Loads Plots" appear in `Home.py`'s sidebar automatically. Pure
  GUI addition — no calc-math change, no new `Project` slice,
  `SCHEMA_VERSION` unchanged at 19. The graphics audit (confirm every plot the
  original suite rendered has a Streamlit equivalent) found no gaps.

- **Analysis merged into nine component pages** (Phase D Step D6). The 11
  per-BAS-program Analysis pages are now 9: **Wing Loads**
  (`app/views/wing_loads.py`) merges AIRLOADS (Schrenk) + WINGINER + NETLOADS
  behind one form; **Tail Loads** (`app/views/tail_loads.py`) merges TAILDIST +
  BALLOADS. `farloads/workflow.py`'s `wing_loads`/`tail_loads` steps are the
  shared nav step for each pair (`"airloads"`/`"balloads"` added to
  `FOLDED_MODULES`, reusing the existing `wing_inertia` precedent). The other 7
  pages (Engine Out, Fuselage Loads, Aileron, Flap, Tab, Engine Mount, Landing
  Gear) converted to the Phase-D page conventions: inputs moved into
  `st.form` + an explicit Apply button; Wing Loads' `Project.aero.surfaces`
  write-back changed from a wholesale replace to an upsert-by-name; Fuselage
  Loads' hardcoded 5-row station table and Engine Mount's baked-in Continental
  IO-520-BB `default_engine()` replaced with blank defaults; Aileron/Fuselage/
  Landing Gear/Engine Mount gained the LIMIT caption+marker they were missing.
  Engine Mount additionally retired its separate `st.session_state
  ["engine_inputs"]` store and ad hoc local `Project`, now reading/writing
  `Project.engines`/`Project.engine_layout`/`Project.include_far25` directly
  like every other page. No calc-math change; Appendix A/B oracles pass
  unmodified; `SCHEMA_VERSION` unchanged at 19 (pure GUI reorg).

- **Envelopes & Critical Conditions section** (Phase D Step D5,
  `SCHEMA_VERSION` 18 → 19). New **Weight/CG Grid & Payload Cases** page
  (`app/views/payload_cases.py`) owns a shared `WeightInput.cg_cases` list of
  named loading scenarios; the Weight/CG Envelope page's chart overlays them
  read-only against the forward-loading-envelope boundary, and the Flight
  Envelope page reads them read-only and merges them into the calc-facing
  `FlightLoadsInput.cg_cases` (unchanged for SELECT/WINGINER/NETLOADS/
  BALLOADS), so the two views can no longer diverge. Old project files migrate
  automatically (`io._legacy_cg_cases_from_flight_loads`). The Mach Limit
  page's chart now overlays the VA/VC/VD/VF design speeds as reference lines
  over the Mach-limit boundary. The Flight Envelope page exposes
  `FlightLoadsInput.altitudes_ft` as a real, fully-editable list (multi-altitude
  V-n), with a CG-case selector, an altitude selector and an "overlay all
  altitudes" toggle on the V-n chart. The Critical Loads page adds a per-
  condition opt-out checkbox persisted as `CriticalLoadSet.selected_case_ids`
  (empty = unfiltered); Results Review's governing-loads summary honors it —
  the structural calc modules and the sbeam export bridge are unaffected. No
  calc-math change; Appendix A/B oracles pass unmodified.

- **Form+Apply conversion, Airplane section** (Phase D Step D4.7, closing
  Phase D Step D4). `configuration_layout.py`, `wing_geometry.py`,
  `weight_estimate.py`, `weight_cg_inertia.py` and `structural_speeds.py`
  converted to `st.form`+explicit-Apply (matching `aero_coefficients.py`);
  every remaining Appendix-A-shaped literal default in these pages (GA6
  geometry, WTESTIMA mission figures, STRSPEED speeds/load-factor figures, the
  WINGGEOM Appendix-A wing polyline) replaced with 0/blank/derived defaults.

- **Engine write-back + mass-item overlay on the three-view** (Phase D Step
  D4.6). The Configuration & Layout page's three-view now overlays a marker
  per `Project.weight.items` `MassItem` (colored by `MassItemKind`, sized by
  `weight_lb`) and a diamond marker per `Project.engines[]` entry at its
  `engine_cg`, in all three views. A new "Engine positions (engine_cg)"
  expander lets you numerically override each engine's X/Y/Z station
  (defaulted to the current `engine_cg`); Apply writes back into
  `Project.engines` and re-renders the marker. Page-only change — no
  calc-math, no schema change.

- **True CG from `Project.mass`** (Phase D Step D4.5). New
  `farloads/modules/configuration.cg_estimate(project, layout, geom)` returns
  the weight-averaged CG station from `Project.mass.cases[0]` (WTONECG's
  itemized loading) when present, else the pre-existing `xlemac + 0.25*mac` /
  wing-reference-waterline first cut, plus a `source` label
  ("Weight DB" / "25% MAC estimate"). The landing-gear tip-back/overturn
  `ConditionResult` and the Configuration & Layout page's three-view CG marker
  (top and side views) both switch to it automatically once a mass slice
  exists, with the source named in the `ConditionResult` label and the
  three-view legend. Prop ground clearance is CG-independent and unaffected.
  No schema change.

- **Design-weight read-through, Structural Speeds / Weight Envelope** (Phase D
  Step D4.4). `app/views/structural_speeds.py` reads the design weight from
  `Project.weight.direct_totals()[0]` (the Weight DB total) when items exist,
  read-only with an "Override design weight" checkbox, instead of asking for
  it a second time; when no Weight DB is present it shows an info message
  pointing at the Weight, CG & Inertia page instead of falling back to a
  `3400.0`-shaped literal default (same treatment for its wing-area fallback,
  now `0.0` with its own info message; the pre-existing wing-area
  read-through from `Project.geometry` is unchanged). `app/views/weight_envelope.py`
  (WTENV) gets the same weight read-through + override checkbox for its
  `gross` weight. No calc-math or schema change; the GA6 example is
  unaffected since its stored `speeds.weight_lb` already equals its Weight DB
  total.

- **Component-station derivation + Weight DB seeding** (Phase D Step D4.3).
  `farloads/modules/configuration.py` gained two pure functions:
  `component_stations(layout)` derives approximate `(x, y, z)` stations for
  named airframe components (wing, fuselage, h-tail, v-tail, a lumped "tail"
  average, main/nose gear, a lumped "landing_gear" average) from
  `LayoutInput`'s existing coarse scalars — no schema change; and
  `match_component_station(name, stations)` maps a `MassItem.name` to one of
  those keys by case-insensitive substring alias, most-specific first. The
  Configuration & Layout page gained a "Seed component stations into Weight
  DB" button (mirroring the existing "Seed wing geometry" button) that fills
  a weight item's station only when it is still `(0, 0, 0)`, never
  overwriting a hand-entered value — closing the gap `estimate_to_mass_items`
  (WTESTIMA) leaves (component weights with no station). No calc-math or
  schema change.

- **Aero Coefficients page** (Phase D Step D4.2). New `app/views/aero_coefficients.py`
  is now the single owner of the `Project.aero_coeffs` slice (Step D4.1):
  a form+Apply page (page conventions §5) editing the cruise coefficient set
  plus an optional flaps-down (landing) set behind a checkbox, with no
  Appendix-A-shaped widget defaults (0/blank). Apply wholesale-replaces
  `project.aero_coeffs` — correct for this page since it is the slice's sole
  owner. `app/views/flight_envelope.py` drops the cruise-coefficient editor it
  carried since Step D4.1, gains a "no aero coefficients — define them on the
  Aero Coefficients page" guard alongside its existing missing-speeds guard,
  and shows the coefficients it reads as a read-only caption. No calc-math or
  schema change (reuses the D4.1 `Project.aero_coeffs` slice).

- **`Project.aero_coeffs` slice — single-owner airplane-less-tail aero
  coefficients** (Phase D Step D4.1). New `AeroCoefficientsInput` (`cruise`,
  `flaps_down`, both `Optional[AeroCoeffSet]`) replaces
  `FlightLoadsInput.configurations` (a list of `AeroCoeffSet` keyed by
  `flaps_down`), which is dropped from the schema. `flight_envelope`
  (FLTLOADS) now reads `Project.aero_coeffs` instead of owning the coefficient
  list; `select` and `balloads` read it too (via `select._flaps_by_config_name`)
  for the flaps-retracted/extended split. A new **Aero Coefficients** workflow
  step (`aero_coefficients`, Airplane section, `produces="aero_coeffs"`) and
  placeholder page (`app/views/aero_coefficients.py`, read-only) land in the
  nav; `flight_envelope`'s step now also `requires=("aero_coeffs",)`. The
  cruise-coefficient editor stays on the **Flight Envelope** page for now,
  writing into `Project.aero_coeffs.cruise` while preserving any existing
  `.flaps_down` set — it moves to the new page, plus a flaps-down editor, in
  Step D4.2. `SCHEMA_VERSION` 17 → 18; older project files (with
  `flight_loads.configurations`) migrate automatically
  (`io._legacy_aero_coeffs_from_flight_loads`) so they still load unchanged.
  No calc-math change (Appendix A/B oracles pass unmodified).

- **Local-disk project persistence + Engineer/Date metadata** (Phase D Step D3,
  decision D-3). `app/Home.py` now owns a global **Project file** sidebar
  widget (visible on every page): Open (from a local `projects/` directory,
  newest-first), New from example (`examples/*.project.json`), Save to disk
  (overwrites `<name>.project.json`), the existing browser upload/download, and
  an unsaved-changes indicator; Open/New-from-example confirm via a dialog
  before discarding unsaved edits. `farloads/io.py` gains
  `default_projects_dir()` (repo-relative, not cwd-relative) and
  `list_saved_projects()`. `Project.engineer`/`Project.date` (freeform text,
  blank by default) are new optional metadata, shown on the dashboard and as a
  header line in the Export & Report page's text report / zip bundle.
  `SCHEMA_VERSION` 16 → 17 (additive; omitted from the JSON when blank, so
  existing files round-trip unchanged). `projects/` is git-ignored. No
  calc-math change.

### Fixed

- **GUI input widgets ignored the Imperial/SI toggle.** The global unit toggle
  (`app/Home.py`, `st.session_state["unit_system"]`) governed *results*
  everywhere but not *inputs* — every sidebar form and `data_editor` accepted
  and displayed Imperial regardless of the setting, so an SI user's entries were
  stored as Imperial. All remaining pages with domain inputs now follow the
  `engine_mount.py` pattern: seed via `farloads.units.to_display`, unit-suffixed
  labels, widget `key`s suffixed with `system.value` (re-seed on toggle), and
  `to_imperial_scalar` back to canonical Imperial on Apply (`configuration_
  layout`, `structural_speeds`, `wing_geometry`, `weight_cg_inertia`,
  `aileron_loads`, `flap_loads`, `flight_envelope`, `fuselage_loads`,
  `landing_loads`, `mach_limit`, `payload_cases`, `tab_loads`, `tail_loads`,
  `weight_envelope`, `weight_estimate`, `wing_loads`). `loads_plots.py`, which
  never referenced the toggle, gained display-only conversion of its plotted
  values and axis labels. `farloads/units.py`'s scalar kind tables gained
  `area_sqft`/`length_ft`/`inertia_lbin2`/`area_sqin`. Airspeed (KEAS) and
  altitude (ft) stay aviation-standard in both systems. Display/boundary only —
  `project.json` and the calc core stay Imperial, `SCHEMA_VERSION` unchanged at
  20; 303 tests pass.

- **`project.weight` merge-write dropped `envelope`.** `configuration_layout.
  py`'s station-seed button and both `project.weight` writes in
  `weight_estimate.py`/`weight_cg_inertia.py` rebuilt `WeightInput` without
  carrying forward `.envelope`, silently discarding the Weight Envelope
  page's inputs on the next save from any of those three pages. Found while
  verifying the Phase D Step D4 regression DoD item; all three now pass
  `envelope=project.weight.envelope` through.

### Changed

- **Six-section GUI navigation restructure** (Phase D Step D2, regroup only).
  `farloads/workflow.py`'s four phases (Define/Analyze/Review/Export) are
  replaced with the six Phase-D sections: Start, Airplane, Envelopes &
  Critical Conditions, Analysis, Loads Plots, Export. `airloads` moves from
  Define into Analysis; `balanced_tail_verification` and `critical_loads` move
  alongside their related pages (Analysis and Envelopes & Critical Conditions
  respectively); `results_review` moves into Export (pre-export summary,
  alongside `export_report`). The dashboard is now a real `WorkflowStep`
  (`"dashboard"`, phase Start) instead of a Home.py special case, so
  `app/Home.py` builds every sidebar group — including Start — uniformly from
  `wf.by_phase()`; a section with no steps yet (`Loads Plots`, pending Step D7)
  is omitted from the sidebar rather than shown empty. No page merges, no
  calc-math or schema change — `requires`/`produces` on every step are
  unchanged; this is metadata + display only.

### Added

- **Structured load-case IDs** (Phase D Step D1, decision D-1). Every
  delivered load case now carries a stable, traceable `case_id`
  (`"<component>-<seq>"`, e.g. `W-01`, `HT-03`, `VT-02`, `F-04`, `EM-01`,
  `LG-05`) that replaces `report.py`'s old render-time, per-module, unstable
  `LC{idx}`. New `CaseRef` dataclass (`farloads/models.py`) and
  `farloads/case_ids.py` (the six-prefix taxonomy + a per-call-site
  `CaseIdAllocator`, no shared/global state). Minted once by the module that
  first names a physical condition (`select.py`, `engine.py`, `landing.py`,
  `aileron.py`, `flap.py`, `tab.py`, `one_engine_out.py`,
  `wing_inertia.py`/`net_loads.py`) and copied downstream by consumers
  (`taildist.py`, `body_loads.py`) rather than re-minted. `report.py`'s
  load-case tables gain `Component`/`Condition`/`CG`/`Speed`/`Altitude`
  columns; `export/sbeam_bridge.py` stamps the case id into every sbeam
  `FORCE`/`MOMENT` card comment and adds a new case-index CSV
  (`case_index_csv_from`/`case_index_rows`), surfaced on the Export page.
  `SCHEMA_VERSION` 15 → 16 (additive; older files load with `case_ref = None`,
  back-filled on the next compute). No calc-math change — the Appendix A/B
  oracles pass unmodified. **Accepted, not closed:** `select_wing`'s own wing
  `CriticalCondition` list and `WingMassInput.cases` (which drives
  WINGINER/NETLOADS) remain two independent case lists sharing the `W` prefix
  in disjoint numeric bands (not the same case object); same gap between
  `one_engine_out` and `select_vtail`'s vertical-tail sequence — tracked as a
  deferred refinement. See `docs/30_future/00_backlog.md` → history for the
  full design and the banding-collision bug caught during implementation.

## [0.2.0] — 2026-07-08

### Added

- **`scripts/smoke_test.sh`** (release step R2, `RELEASE_PROCESS.md` §3.5): a
  permanent, repeatable GUI/CLI smoke test. Starts `app/Home.py` headless,
  waits for `/_stcore/health`, checks the root page returns HTTP 200 with no
  traceback in the server log, then runs `farloads engine
  examples/ga6_normal.project.json -o out.csv` and checks the CSV header/row
  count. `RELEASE_PROCESS.md` §3.5 now points at the script instead of manual
  steps. No calc or schema change.

### Fixed

- **Flight Envelope page no longer destroys unedited `flight_loads` data**
  (Phase D Step D0, release step R1). The page previously rebuilt
  `FlightLoadsInput` wholesale (`configurations=[cruise]`,
  `altitudes_ft=[altitude]`) on every rerun, so merely opening it deleted any
  flaps-down configuration or extra altitudes a loaded project carried.
  `FlightLoadsInput` gains a pure `merged()` method (`farloads/models.py`) that
  merges one page-edit into the existing slice — the edited altitude replaces
  `altitudes_ft[0]`, the edited configuration replaces its same-`flaps_down`
  peer (appended if none), and everything else is preserved — and
  `app/views/flight_envelope.py` persists through it. This is the first
  application of the Phase-D "Apply merges into the project slice" page
  convention (`docs/30_future/02_gui_workflow_plan.md §5`). Regression tests in
  `tests/test_flight_envelope.py` load a slice with a flaps-down configuration
  and two altitudes through the persist path and assert both survive. No calc
  or schema change.

### Added

- **`docs/40_history/01_verification_baseline_0.2.0.md`** (release step R4,
  `RELEASE_PROCESS.md` §4.4): the permanent regression-baseline record — one
  table per module (all 22 ported programs + `configuration`/`body_loads`)
  mapping each printed Appendix A/B figure the test suite locks against to
  its reference-page citation and tolerance, plus a dedicated section for the
  closure-locked modules (ONENGOUT, the LANDLOAD wheel table, swept AIRLOAD4,
  FAR 25 optional engine cases, `body_loads`, `configuration`, concept-mode
  closure) that have no printed oracle. Docs-only.

### Changed

- **`PROGRAM_SPEC.md` docs-drift fix** (release step R3, `RELEASE_PROCESS.md`
  §3.1): `body_loads` (shipped in Step C6) now has its own module-spec entry
  (it was previously only mentioned inside SELECT's write-up) and the
  cross-module field-ownership table gained the `fuselage_mass` row it reads.
  Docs-only; no code/schema change.
- **Per-module analysis pages now mark their on-screen LIMIT loads.** The
  `flap_loads`, `tab_loads`, `one_engine_out` and `balanced_tail_verification`
  Streamlit pages display the calc's LIMIT values (the oracle-traceable numbers);
  each now carries a caption stating the on-screen loads are LIMIT and that the
  CSV/FORCE-card downloads and Review/Export pages are ULTIMATE (= limit × 1.5), and
  a `LIMIT` marker on every load column/metric. The mandate was scoped accordingly
  (`CLAUDE.md`, `docs/10_standard/00_program_overview.md`): **all deliverable load
  output is ULTIMATE**; a per-module analysis page may show explicitly-marked LIMIT
  oracle values as the sole exception.
- **The `ULT` marker is now part of the load's units string.** All rendered load
  output (the load-case CSV headers, the `results_to_rows` `Units` column, and the
  text reports) carries the marker inline — force `lbs-ULT`/`N-ULT`, moment
  `ft-lb-ULT`/`lb-in-ULT`/`Nm-ULT`, pressure `lb/in^2-ULT` — replacing the previous
  separate `ULT` suffix on the column header. `report.py` gains `_ult_units()`
  (keyed off the existing load-unit detection), so non-load quantities (weights,
  locations, inertias, dimensionless load factors) keep their plain units. The `SF`
  column is unchanged; a case held at ultimate is `SF=1.0`. Render tests
  (`test_report.py`) updated to the `-ULT` unit forms.
- **Documented the ULTIMATE-output convention as a mandatory standard.** Codified in
  `CLAUDE.md`, `docs/10_standard/00_program_overview.md`,
  `docs/10_standard/PROGRAM_SPEC.md`, `docs/10_standard/PROJECT_GUIDE.md §5`,
  `docs/20_theory/00_theory_sources.md` and `docs/30_future/01_concept_loads_plan.md`:
  **all load output SHALL be ultimate**, the `ULT` marker is **part of the load's
  units string** (`lbs-ULT`/`N-ULT`, `ft-lb-ULT`/`lb-in-ULT`/`Nm-ULT`,
  `lb/in^2-ULT`), **every load case states its safety factor** (default 1.5 per 14
  CFR 23.303; Part 25 equivalent 25.303), and a value already at ultimate is
  **`ULT SF=1.0`**.
- **Rendered/exported loads are now ULTIMATE (= limit × factor of safety).** The
  calc still emits LIMIT loads (oracle-locked to the manual), but `report.py` and
  `export/sbeam_bridge.py` now multiply the load quantities (forces/moments/
  pressures — never geometry, weights, inertias, or dimensionless load factors) by a
  per-case factor of safety to report ultimate = limit × 1.5 (14 CFR 25.303). New
  `constants.ULTIMATE_FACTOR = 1.5` and `ConditionResult.safety_factor` (default
  1.5); the field is per-case so a future 14 CFR 25.302 / Appendix K probability-
  based factor (1.0–1.5) can be assigned to a failure case — sudden engine stoppage
  is held at the conservative 1.5 for now. The load-case CSV gains an `SF` column and
  marks the force/moment headers `ULT`; the sbeam FORCE/MOMENT cards, span-load CSVs
  and closure comments are ultimate (the set still sums to 1.5 × the root/total).
  Reference: `reference/14CFR_factor_of_safety.md`. Calc oracle tests unchanged;
  render/export tests (`test_report.py`, `test_io.py`, `test_sbeam_bridge.py`) updated
  to ultimate.


- **GUI restructured into the four-phase workflow (Define → Analyze → Review →
  Export).** `app/Home.py` is now an `st.navigation` entry point that builds the
  phase-grouped sidebar from the new `farloads/workflow.py` — the ordered,
  dependency-aware step graph (each step names its calc `module` and the slices it
  `requires`/`produces`). The 20 page files moved `app/pages/NN_*.py` →
  `app/views/<workflow-key>.py` (clean names, no numeric prefixes; the duplicate
  `06_` index is gone), and each page's `set_page_config` was removed (called once,
  in `Home.py`, as `st.navigation` requires). The old Phase-0 Home page (which only
  inspected four of the ~20 project slices) is replaced by `views/dashboard.py`: an
  Overview that loads/saves the project and shows per-step completeness.

### Added (GUI)

- **Results Review & Export pages.** `views/results_review.py` consolidates the
  governing (critical) loads on every component plus all module results by phase;
  `views/export_report.py` gathers every output in one place — project JSON,
  per-module load CSVs + a combined text report, sbeam wing/fuselage/tail/
  control-surface BDF cards, and a single **Download all `.zip`** bundle. Both
  recompute from the project inputs, so exports are never stale. *(Closes the
  "Combined workbook export" backlog item.)*
- **GUI regression tests.** `tests/test_workflow.py` (step-graph well-formedness;
  every registered module has a workflow step) and `tests/test_views_smoke.py`
  (headless `AppTest` runs the entry point + all 20 views with the example project,
  asserting no uncaught exception). +24 tests.
- **Multi-engine engine-mount page.** `app/views/engine_mount.py` now exposes the
  first-class multi-engine `Project`: a sidebar **layout** selector (1 nose / 2 or
  4 wing-mounted engines) drives the engine count, and an **engine selector** picks
  which engine is being assessed. Each engine's inputs (type, CG, weights, rotors)
  are held canonically in Imperial in `st.session_state["engine_inputs"]` — keyed
  per engine and unit system — so switching engine or unit system preserves every
  engine's data. Results default to the selected engine with a **"Show all engines"**
  toggle for the full `engine.run(project)` (each condition prefixed with the engine
  designation); the JSON/CSV/text exports cover every engine. A single engine
  reduces exactly to the previous behaviour (no prefixes, identical to `run_all`).

### Fixed

- **Engine-mount page crash.** `app/views/engine_mount.py` still built its
  save-project payload with the removed single-engine `Project(engine=...)` keyword;
  now uses `engines=[...]` + `EngineLayout.SINGLE_NOSE`. Caught by the new view
  smoke test.

### Changed

- **Corrected FAR 23.361(a)(1) takeoff torque (AC 23-19A).** The takeoff-case engine
  mount torque is now `factor × mean takeoff torque` (the same cylinder/turboprop
  factor as (a)(2)), where the original program and McMaster's manual left it
  **unfactored**. Per **AC 23-19A**, the unfactored form is the **Amendment 23-26**
  drafting error (non-conservative, lower loads), corrected by **Amendment 23-45**:
  23.361(c) applies the factor to all of paragraph (a). For the IO-520-BB the
  takeoff mount torque changes 554.39 → **737.34 ft-lb**; for a turbopropeller it
  becomes 1.25× mean takeoff, identical to 25.361(a)(1)(i). This is a **user-approved,
  documented deviation from the Appendix A oracle** (CLAUDE.md "Approved corrections
  to the source"); `test_361_a1` asserts the corrected value and retains 554.39 as
  the mean-torque figure. Source text: `reference/AC_23-19A_engine_torque.md`.
- **Corrected FAR 23.361(a)(3) turboprop-malfunction torque (AC 23-19A).** The
  propeller-control-malfunction mount torque is now `1.6 × 1.25 × mean takeoff
  torque` (= 2.0× mean), where the original program (`TTP=1.6*ENGTORQ`) and
  McMaster's manual applied only the 1.6 factor. The (a)(3) base limit takeoff
  torque is the same quantity as (a)(1), so 23.361(c)'s 1.25 turbopropeller
  mean-torque factor applies before the 1.6 — the same **Amendment 23-26** omission
  / **Amendment 23-45** restoration as the (a)(1) correction above. A **user-approved,
  documented deviation** (CLAUDE.md "Approved corrections to the source"); no printed
  Appendix B engine-mount oracle exists, so it is formula-checked in
  `test_361_a3_applies_mean_torque_factor`. Source: `reference/AC_23-19A_engine_torque.md`.

### Added

- **Optional supplemental FAR 25 engine cases (concept superset).**
  `Project.include_far25` (default off) appends only the **non-duplicative**
  **14 CFR 25.361 / 25.371** engine-mount cases on top of the oracle-locked FAR 23
  set, for **turbopropeller** engines: (a)(3)(i) stoppage `@ 1g`, (a)(3)(ii)
  max-accel torque `@ 1g` (no FAR 23 analog), and 25.371 gyroscopic on the A2 limit
  load factor. The FAR 25 torque cases 25.361(a)(1)(i)/(ii)/(iii) are **omitted** —
  with the AC 23-19A correction factoring the FAR 23 takeoff case, they are
  bit-for-bit duplicates of the corrected 23.361(a)(1)/(a)(2)/(a)(3) for a
  turbopropeller. 25.371 reuses the fixed FAR 23.371(b) rates (2.5/1.0 rad/s) as a
  conservative concept stand-in for the maneuver-derived rates. New optional input
  `EngineInput.max_accel_torque` (blank → `max_engine_torque`); recip/jet engines get
  no FAR 25 cases. The engine-mount GUI gains an **"Add supplemental FAR 25 cases"**
  checkbox. Kept opt-in (not folded into the FAR 23 path) so the Appendix A/B oracle
  — 6 turboprop conditions, 2.5g gyro vertical — is byte-identical when off. Source
  text in `reference/14CFR_Part25_engine_torque.md`; formula-closure tested
  (`tests/test_engine_far25.py`). No oracle exists for Part 25.
- **Balanced-tail-load verification — BALLOADS (Step C11).** New
  `modules/balloads.py` (registers `"balloads"`): the off-pipeline cross-check of
  `BALLOADS.BAS` (Reference 1 Ch 8–9). For every flaps-retracted V-n condition it
  recomputes the rational balancing horizontal-tail load — AoA load at 25% tail MAC
  (`LT25`) + camber/elevator load at 50% (`LT50`), elevator deflection and elevator
  load — **reusing SELECT's oracle-locked `htail_balance`/`_elevator_load`** (no
  re-derivation), converts the rational CP (% tail MAC) to a fuselage station and
  reports it against FLTLOADS' *approximate* `XTC`/`XTF`. Verification report only —
  no schema change, no pipeline output. New `app/pages/16_Balanced_Tail_Verification.py`.
  Oracle-locked against the Ch 9 case-202 hand-calc (`LT = 519.845 lb`, LT25 +907.62,
  LT50 −387.78, δ −5.39°, CP 6.35% tail MAC); the rational up/down loads equal
  SELECT's `BAL UP/DN RETRACTED` exactly. 4 new tests (211 total). **This completes
  all 22 of Reference 1's Appendix-C programs.**
- **Landing / ground loads — LGFACTOR + LANDLOAD (Step C10).** New
  `modules/landing.py` (registers `"landing"`): the FAR Part 23 Subpart C
  ground-load conditions (Reference 1 Ch 20). **LGFACTOR** estimates the landing
  load factor from the FAR 23.473 drop-test work-energy balance (descent velocity
  `V = 4.4·(W/S)^0.25` clamped 7–10 fps, tyre/strut energy efficiencies → airplane
  load factor `N`, gear factor `NLG = N − L`). **LANDLOAD** computes the tricycle-gear
  reaction loads (24 main-wheel + 33 nose-wheel cases) for the level, tail-down,
  one-wheel, braked-roll, side and supplementary-nose-wheel conditions
  (FAR 23.473–23.499) — the drag factor `K`, ground angles, `BETA`, the `AP/BP/DP/CP`
  lever arms, per-wheel ground-line and airplane-datum reactions and the unbalanced
  moments. New `LandingInput`/`LandingGearInput` input slice (`Project.landing`,
  carrying the gear strut geometry that has no home in the aerodynamic
  `Project.geometry`) and `GearReactionCase` result record; `SCHEMA_VERSION` 14 → 15
  (additive). New `app/pages/15_Landing_Loads.py`. LGFACTOR is oracle-locked against
  Appendix A p236 (V 9.0048 / N 3.0951 / NLG 2.4281); LANDLOAD's gear-geometry
  intermediates are oracle-locked against p230, with the OCR-garbled printed
  wheel-load table closure- + legible-cell-validated (the ONENGOUT precedent). 9 new
  tests; **all 22 Reference 1 Appendix-C suite programs except the optional BALLOADS
  utility are now ported.**
- **One-engine-out vertical-tail loads — ONENGOUT (Step C9).** New
  `modules/one_engine_out.py` (registers `"one_engine_out"`): a time-marching yaw
  simulation of the FAR 23.367 critical-engine failure (Reference 1 Ch 11). The
  failed engine's thrust/windmill-drag asymmetry yaws the airplane about its
  vertical axis (`IZZ`) until the pilot — at peak yaw rate but ≥2 s after failure
  (23.367(b)) — applies full rudder and recovers; `run()` reports the maximum
  vertical-tail load per speed (VC ultimate / VD limit / VS) with engine thrust,
  windmill drag, max yaw rate, the 25%/50% MAC loads at peak and time to recovery,
  and `time_history()` returns the full transient on demand (below VMC the run is
  time-bounded and flagged non-recovered). New shared `modules/_vtail.py` (the v-tail
  lift slope AVT, rudder effectiveness EFFECTV and the large-deflection EF chart),
  with SELECT's private `_avt`/`_effectv`/`_ef` refactored to delegate to it. New
  `app/pages/20_One_Engine_Out.py` (per-speed summary + on-demand time-history
  charts/CSV). First module to exercise the first-class multi-engine `Project`.
  **Validation:** the printed Appendix B twin oracle is unavailable (Appendix B is
  absent from the bundled references), so C9 is locked by sub-formula exactness vs
  `ONENGOUT.BAS` + integration/physics closure + refactor-parity with SELECT (11 new
  tests; 198 pass).

- **Schema v14 (Step C9).** `Project.one_engine_out` (`OneEngineOutInput`) input
  slice and `VTailLoadsInput.xv50` (FS of 50% v-tail MAC) — additive; older files
  load unchanged.

- **Control-surface simplified distributions — AILERON / FLAPLOAD / TABLOADS (Step
  C8).** New `modules/aileron.py`, `modules/flap.py`, `modules/tab.py` (register
  `"aileron"` / `"flap"` / `"tab"`): the FAR-style simplified pressure
  distributions. **Aileron** (Ch 16, FAR 23.455 / CAM 3.222) — deflected up/down
  rolling loads over the VA/VC/VD schedule, constant LE→hinge then taper to 0 at
  the TE. **Flap** (Ch 17, FAR 23.345 / 23.457) — the four-condition flaps-extended
  envelope (Abbott & von Doenhoff Fig 98) with the momentum-theory propeller
  slipstream and the head-on 25 fps gust amplifications, taper LE→half at TE.
  **Tab** (Ch 18, FAR 23.409 / CAM 3.224) — full deflection at VC, trapezoidal
  (LE = 2× TE). New input slices `AileronLoadsInput` / `FlapLoadsInput` /
  `TabLoadsInput`(+`TabSpec`), the `ControlSurfaceLoadResult` slice on
  `LoadsResult.control_surface`, the `sbeam_bridge` control-surface export
  (`control_surface_csv` / `control_surface_force_moment_cards`, FORCE set scaled to
  the critical load), and `app/pages/12_Aileron_Loads.py` /
  `13_Flap_Loads.py` / `14_Tab_Loads.py`. `structural_speeds.design_speed_values()`
  exposes the scalar design speeds the modules read. Oracle-locked against the
  Appendix A reports (p200/p201/p202) within ±0.1%.

- **Schema v13 (Step C8).** `Project.aileron_loads` / `flap_loads` / `tab_loads`
  input slices and `LoadsResult.control_surface` — all additive; older files load
  unchanged.

- **Chordwise tail-load distribution — TAILDIST (Step C7).** New `modules/taildist.py`
  (registers `"taildist"`): the five-station chordwise net pressure profile on the
  average tail chord — the additive (angle-of-attack, 25% chord) plus camber (50%
  chord) distributions (TAILDIST.BAS subroutine 3000, Reference 1 Ch 10) — for each
  critical horizontal/vertical-tail condition from SELECT. SELECT now attaches the
  rational `lt25`/`lt50` split to every tail `CriticalCondition`. New
  `app/pages/11_Tail_Distribution.py`, the `sbeam_bridge` tail export
  (`tail_chordwise_csv` / `tail_force_moment_cards`) and the `cli.py`
  `--export-target tail` option. Oracle-locked against the Appendix A "Chordwise
  Distribution of Tail Loads" tables (13 horizontal p237 + 4 vertical p245) within
  ±0.1%.

- **Swept / high-Mach airloads — AIRLOAD4 (Step C7).** `modules/airloads.py` gains
  the AIRLOAD4 branch (Ref 1 Ch 12): the Pope & Haney sweepback redistribution of
  the additive Schrenk span load, auto-selected (`use_airload4`) when the 25%-chord
  sweep exceeds 15° or the design Mach exceeds 0.4, reducing exactly to AIRLOADS at
  zero sweep / low Mach. New `AeroSurfaceInput.sweep_deg` / `design_mach` triggers.

- **Schema v12 (Step C7).** `TailLoadsInput.htail_semispan_in`,
  `VTailLoadsInput.vtail_span_in`, `CriticalCondition.lt25`/`lt50`, the
  `TailChordResult` slice on `LoadsResult.tail_chordwise`, and the
  `AeroSurfaceInput` sweep fields — all additive; older files load unchanged.

- **Critical Loads + Fuselage Loads UI pages (Step C6, R9).** New Streamlit pages
  `app/pages/09_Critical_Loads.py` (the SELECT critical wing / h-tail / v-tail /
  fuselage conditions, grouped per component with their loads and FAR cites; persists
  `envelope.critical`) and `app/pages/10_Fuselage_Loads.py` (the Ch 15 fuselage net
  shear/bending per critical condition, editable fuselage mass distribution, closure
  metric, plots and CSV download). Both flag concept-mode results as unverified
  extrapolation.

- **Flaps-extended tail loads + flapped V-n envelope (Step C6, R3/R4).**
  `flight_envelope` gains the flaps-extended (LANDING) V-n corner set at the flap
  speed VF (FLTLOADS.BAS subroutine 3000: stall at 2/3 g / 1 g / 2 g, the n=2 / n=0
  maneuver points at VF, ± gusts at VF, and the VF / 1.4 Vs balancing points,
  n-limited to 2 per FAR 23.345 and investigated at sea level). SELECT extends the
  balancing search to the flaps-extended points (FAR 23.421) and adds the
  flaps-extended gust (FAR 23.425(a)(2), 25 fps at VF). The real landing-config aero
  polynomials are not in the repo fixtures, so R3/R4 are validated by **closure**
  (the flapped points achieve their target NZ; the rational balancing tail load
  zeroes the flapped pitching moment) rather than the printed flaps-extended oracle
  (Appendix A cases 81/106/88/108). `tests/test_flight_envelope.py` /
  `tests/test_select.py` extended.

- **Net fuselage loads + sbeam body export (Step C6, R6/R8).** New `body_loads`
  module (Ref 1 Ch 15) computes the fuselage longitudinal net distribution for each
  critical fuselage condition: each station's inertia (`-NZ·w`), the balancing tail
  air load at the tail station, and the wing reaction at 25% wing MAC, integrated
  nose→tail to running shear `Sz` and bending `Myy` → `Project.loads.body_net`
  (`BodyLoadResult`/`BodyStationLoad`) + a per-station CSV (`body_load_rows`). Ch 15
  ships no program/oracle, so it is validated by **equilibrium closure** (applied
  `ΣFz=0`, shear returns to 0 aft of the wing). The sbeam bridge gains
  `body_span_load_csv` / `body_force_moment_cards` (FORCE Fz per station, the set
  summing to ~0). New `tests/test_body_loads.py`.

- **WTONECG — persisted mass slice (Step C6, R7).** `weight_onecg.build_mass`
  emits the long-deferred `Project.mass` slice (`MassResult`): weight, CG and the
  airplane moments/product of inertia (lb-in²) about the CG for the itemized
  loading. Validated against Appendix A p136 and the io round-trip. SELECT's oracle
  searches keep their documented Ch 9 inertia approximations (so the slice is
  available for reporting/future per-CG work without changing the locked results).

- **SELECT — critical fuselage conditions (Step C6).** Adds the Ch 9 fuselage
  condition search (SELECT.BAS subroutine 4000): the maximum fuselage load reacted
  at the wing (`LZW − NZ·WW`, FAR 23.301), the aft-fuselage down/up bending (the
  largest signed product of that load and the tail load, 23.331), and the greatest
  vertical inertia factor for concentrated-weight installations (23.301). `WW`
  (wing weight) is a new `SelectInput` field (default `0.09·MTOW`). These are
  condition *selections* (scalar criticals) distinct from the Ch 15 fuselage net
  *distribution* (R6). Oracle-locked against Appendix A "Critical Fuselage Loads":
  max down load on wing 13347.6 (GUST +C), aft down bending 12569.6, aft up bending
  −6390.3 (GUST −C), greatest NZ 5.81. `tests/test_select.py` extended.

- **SELECT — horizontal-tail maneuver / gust / unsymmetrical loads (Step C6).**
  Extends the `select` module with the remaining flaps-retracted h-tail conditions:
  unchecked maneuver up/down (FAR 23.423(a) — full elevator deflection at the 1g VA
  points), checked maneuver up/down (23.423(b) — a pitch-acceleration increment
  `Iyy·θ̈/arm` with the approximate `Iyy=0.44·W·LF²/384` and `θ̈=39·n(n−1.5)/V` at
  VC/VD), up/down gust (23.425(a)(1) — the balancing load plus the rational gust
  increment `KG·Ude·V·ST·AHT·(1−36aw/ARW)/498`), and the unsymmetrical load
  (23.427(a) — 100% one side / `100−10(n−1)`% the other, excluding the locally
  carried unchecked-maneuver loads per FAA CAM 3.216). The large-deflection
  effectiveness factor `EF(δ, Se/St)` is reconstructed exactly from SELECT.BAS
  subroutine 10000. `TailLoadsInput` extended with the elevator geometry, airplane
  length and wing lift slope (`SCHEMA_VERSION` 10 → 11, additive). Oracle-locked
  against Appendix A "Critical Horizontal Tail Loads": unchecked −1397.8 / +1227.2,
  checked −671.5 / +787.8, gust +908.6 / −1292.8, unsymmetrical −1111.8 (RH −646.4,
  LH −465.4). `tests/test_select.py` extended.

- **SELECT — rational vertical-tail loads (Step C6).** Extends the `select` module
  with the four critical vertical-tail loads (Ch 9 / SELECT.BAS subroutine 8300),
  searched over the V-n `BAL A` (VA) and `BAL C` (VC) points: sudden full rudder
  deflection (FAR 23.441(a)(1)), yaw to a 19.5° sideslip with the rudder held
  (23.441(a)(2)), a 15° yaw with the rudder neutral (23.441(a)(3)), and the lateral
  gust at VC (23.443(b)). Side loads use the tail lift slope `AVT=2π/(1+2/ARVT)`,
  the rudder effectiveness `EFFECTV=cubic(SR/SV)`, and the gust mass-ratio /
  alleviation `UGT`/`KGT` with a default yaw inertia `IZZ`. New `VTailLoadsInput`
  slice (`Project.vtail_loads`); `SCHEMA_VERSION` 9 → 10 (additive) with the `io.py`
  round-trip. Oracle-locked against Appendix A "Critical Vertical Tail Loads" —
  yaw-15 −526, side gust +604 (IZZ 4169.2) and the angle-of-attack components are
  exact; the rudder-deflection loads (sudden rudder +591, rudder load 167) carry an
  `EFV≈1.009` large-deflection chart factor that is illegible in the scanned source
  (a `VTailLoadsInput` field, default 1.0). `tests/test_select.py` extended.
  Vertical-tail `CriticalCondition`s land alongside the wing and htail sets in
  `Project.envelope.critical`.

- **SELECT — rational horizontal-tail balancing loads (Step C6).** Extends the
  `select` module with the Ch 9 / BALLOADS rational balancing method: for every
  balanced V-n point it resolves the total balanced tail load into the
  angle-of-attack load at 25% tail MAC (`LT25=(AT·AHT/57.3)·Q·ST`, tail AoA
  `AT=αwl+IT−E`, downwash `E=114.6·CL/(π·ARW)`, slope `AHT=2π/(1+2/ARHT)`) and the
  camber/elevator load at 50% MAC (`LT50` from balancing the pitching moment about
  the CG for the elevator deflection), then selects the largest up and largest down
  balancing load with flaps retracted (FAR 23.421) into `Project.envelope.critical`
  as `htail` `CriticalCondition`s. New `TailLoadsInput` slice (`Project.tail_loads`:
  tail incidence, wing/tail aspect ratios, tail area, elevator effectiveness, 25%/50%
  tail-MAC stations, wing zero-lift angles); `SCHEMA_VERSION` 8 → 9 (additive) with
  the `io.py` round-trip. Oracle-locked against the Ch 9 case-202 hand-calc
  (LT25 +907.62, LT50 −387.78, δ −5.39°, **LT 519.845**, CP 6.35%) and Appendix A
  "Critical Horizontal Tail Loads" (UP STALL +N CG1 18000 +519.85, DOWN MAN D CG3
  12000 −613.92). The H-tail maneuver/gust/unsymmetrical, the flaps-extended
  balancing (needs the flapped V-n envelope), the vertical tail and the fuselage net
  are still later C6 increments. `tests/test_select.py` extended.

- **SELECT — critical wing loads (Step C6).** New registered `select` module
  (`farloads/modules/select.py`) porting SELECT.BAS's wing critical-load search
  (Ref 1 Ch 9, SELECT.BAS ~2990-3540): it scans the balanced FLTLOADS V-n matrix
  for the governing wing condition of each design point — **PHAA**/**PLAA**
  (largest resultant `√(LZW²+DX²)`), **PMAA** (largest LZW), **NMAA** (largest
  negative resultant), **ACRL** (accelerated roll), and **TORS** (steady-roll
  aileron torsion `(cm−0.01·δ)·G·V²`, deflection per CAM 3.222) — and writes them
  as wing `CriticalCondition`s into `Project.envelope.critical`. New `SelectInput`
  slice (`Project.select_input`: full-down aileron deflection + basic-airfoil cm
  for the steady-roll search); `SCHEMA_VERSION` bumped 7 → 8 (additive) with the
  `io.py` round-trip. Oracle-locked against Appendix A "Critical Wing Loads" (PHAA
  STALL +N CL +1.519/V 117.40, PLAA MAN D +0.472/212.40, PMAA GUST +C +0.810/170,
  NMAA GUST −C −0.433/170, ACRL AC ROLL +1.328/116, TORS ST ROL C +0.470/170);
  `tests/test_select.py`. The rational horizontal/vertical-tail and fuselage
  critical loads (rest of Ch 9) and the fuselage net distribution are a later C6
  increment; `select` joins the `run_all_modules` set.

- **C6 schema foundation (SELECT + fuselage/body loads).** First step of Step C6:
  the `Project` schema additions the SELECT module and fuselage net distribution
  build on, all additive (`SCHEMA_VERSION` bumped 6 → 7; older files load
  unchanged). New `Project.mass` slice (`MassResult`/`MassCase`: persisted WTONECG
  weight/CG/inertia per loading) — the long-deferred persisted mass slice, landed
  now that SELECT needs the inertia. New `Project.fuselage_mass` input slice
  (`FuselageMassInput`/`FuselageStation`: the fuselage longitudinal mass
  distribution for the body net loads). New SELECT critical-load set
  (`CriticalLoadSet`/`CriticalCondition`) on `EnvelopeResult.critical` (previously
  reserved). New fuselage net distribution (`BodyLoadResult`/`BodyStationLoad`) on
  `LoadsResult.body_net`, the body analogue of `wing_net`. Full `io.py` JSON
  round-trip for every new slice; the new types are re-exported from `farloads`.
  Validated by `tests/test_io.py::test_c6_slices_round_trip`.

- **Configuration & Layout page + fleet assessment (Step C5).** New
  `Project.configuration` slice (`LayoutInput`: fuselage, parametric wing, tail
  areas/arms, landing gear) and a registered `configuration` calc module that
  derives the wing planform (MAC/XLEMAC/Y_MAC/AR/span via the WINGGEOM strip
  integrator on generated polylines), a tail-volume neutral point + static margin,
  tip-back / overturn angles and prop ground clearance. New Streamlit page
  `app/pages/00_Configuration_Layout.py` (Plotly three-view with CG/NP markers,
  assessment panel, a WINGGEOM seed button, and W/S-vs-W/P + MTOW-vs-OEW fleet
  plots). `app/data/reference_aircraft.csv` extended with a heavier/concept tier
  (twin pistons, commuters, a bizjet, light transports). Modern addition — no
  `.BAS` and **no regression oracle**; figures are first-order estimates flagged in
  concept mode. `SCHEMA_VERSION` bumped 5 → 6 (additive). Validated by
  analytic-vs-WINGGEOM-strip MAC consistency (±0.1%) and Appendix A trapezoid
  plausibility (±10%).

- **sbeam export bridge (Step C4).** New `farloads/export/` subpackage turns the
  NETLOADS net wing load (`Project.loads.wing_net`) into sbeam-consumable
  artifacts: a **span-load CSV**, **FORCE/MOMENT** bulk-data cards (comma
  free-field unit-scale form matching `sbeam/results/load_export.py`, one load set
  per case), and an optional minimal **CBAR stick-model BDF** (GRID + CBAR chain +
  PBAR/MAT1 placeholder + root SPC1 + a SOL 101 subcase per case). The applied
  nodal load at each station is the *increment of the cumulative* NETLOADS column,
  so the FORCE set sums to the root shear and the MOMENT(My) set to the root
  torsion exactly (and the FORCE moments reproduce the root bending). Coordinate
  map (`export/coordinates.py`) is FAR23LOADS station/butt/waterline inches →
  sbeam global CID 0 (identity, single edit-point). New CLI flag
  `--export-sbeam <prefix> [--stick-model]`. The bridge is a pure renderer, not a
  registered calc module. Validated by force/moment closure + a self-contained
  free-field round-trip; the stick deck parses **and solves SOL 101** in the real
  sbeam (manual verification).

- **Net wing loads — WINGINER + NETLOADS (Step C3).** New `wing_inertia` and
  `net_loads` modules compute the spanwise wing **shear, bending moment and
  torsion** along the 25% chord as the algebraic sum of the air loads and the
  inertia loads — the headline structural deliverable (root values size the wing).
  `AIRLOADS` is extended with an air-load distribution (`air_load_distribution`):
  it scales the C1 Schrenk lift to the operating CL, builds per-strip
  lift/drag/pitching-moment forces, rotates them into the airplane reference and
  integrates to the cumulative shears/moments/torsion (drag = computed induced +
  input profile). `WINGINER` models the wing-panel mass as a linearly-tapered area
  density (root density iterated to the panel weight) plus concentrated weights,
  forming 1g-vertical / 1g-drag / unit-roll cases combined per condition.
  `NETLOADS` sums air + inertia per station. Adds a `Project.wing_mass` input slice
  (`WingMassInput`/`ConcentratedWeight`/`WingLoadCase`) and a `Project.loads`
  result slice (`LoadsResult`/`WingLoadResult`/`WingStationLoad`), with section
  `profile_drag`/`section_cm` added to `AeroSurfaceInput`; schema bumped to **v5**
  (additive). New Streamlit page `app/pages/08_Net_Wing_Loads.py` (air/inertia/net
  shear-BM-torsion plots + CSV). FAR23 oracle-locked against the Appendix A air-load
  (p206), wing-inertia (p217-221) and net-load (p222) tables; the critical
  conditions come from the FLTLOADS V-n matrix (the C3-before-SELECT bridge).

- **Flight envelope + balancing tail loads — FLTLOADS (Step C2).** New
  `flight_envelope` module (`farloads/modules/flight_envelope.py`) builds the
  FAR 23.333 maneuver + gust **V-n diagram** and the **balancing horizontal-tail
  load** at every cruise corner — a faithful port of FLTLOADS.BAS subroutine 3900
  (iterate angle of attack to the required load factor, then dynamic pressure to
  the Mach-adjusted stall line; Glauert compressibility; CLmax-vs-Mach curve) and
  4864 (gust load factor, FAR 23.341). Reads the design speeds and limit load
  factors from STRSPEED. Adds a `Project.flight_loads` input slice
  (`FlightLoadsInput`/`AeroCoeffSet`/`CgCase`: geometry scalars, airplane-less-tail
  aero-coefficient polynomials, weight-CG cases) and a `Project.envelope` result
  slice (`EnvelopeResult`/`VnPoint`/`TailBalanceLoad`) with `io.py` round-trip;
  schema bumped to **v4** (additive — older files load unchanged). New Streamlit
  page `app/pages/07_Flight_Envelope.py` (V-n chart + balanced-condition table).
  The GA and concept example fixtures gain a `flight_loads` slice. FAR23
  oracle-locked against the Appendix A "V-n Data" cruise matrix (p179-180); concept
  mode validated by physics closure (attains the user load factor; LZ+LT = NZ·W).

- **Spanwise wing airloads — AIRLOADS + TAU (Step C1).** New `airloads` module
  (`farloads/modules/airloads.py`) computes the wing spanwise lift distribution by
  **Schrenk's method** (Reference 1 Ch 7): the additive distribution (untwisted
  wing at CL=1), the twist-driven basic distribution, and their combination at a
  target CL — the `c·cl` span load every downstream wing-load module consumes. Folds
  in the **TAU** lift-curve-slope planform correction (`TAU.BAS` curve-fit, p407).
  Adds a `Project.aero` slice (`AeroInput`/`AeroSurfaceInput`: section lift-curve
  slope, taper/tip ratio, twist table, target CL) with `io.py` round-trip; schema
  bumped to v3 (additive — older files load unchanged). New Streamlit page
  `app/pages/06_Airloads.py` with a span-load plot (additive / basic / total) and
  the integrated-CL closure check. The GA and concept example fixtures gain an
  `aero` wing slice. FAR23 oracle-locked: the additive (`CC(LA1)`/`C(LA1)`) and
  basic (`Awo`/`CC(lb)`/`Clb`) distributions match Appendix A p161-162 within ±0.1%;
  concept mode is validated by physics closure (integrated `∫c·cl dy` recovers the
  target CL; basic distribution carries zero net wing lift). Known limitation: the
  cosine fairing of the basic distribution across a flap/aileron discontinuity is
  not yet modelled (arises only with deflected flaps).

- **Concept mode (Step C0) — foundation for >12,500 lb configurations.** Adds a
  `"C"` (concept) certification category to `StructuralSpeedsInput`: STRSPEED
  bypasses the GA-only FAR 23.337 maneuver-load-factor formula and cap, instead
  using the user's `chosen_n`/`chosen_nneg` verbatim (both now required in concept
  mode). Adds a **direct-weight path** (`WeightInput.direct_totals()`) that derives
  MTOW/OEW/useful by summing the itemized `MassItem` data base by kind, replacing
  WTESTIMA's GA regression for a heavy concept; WTESTIMA still runs but flags itself
  as a sanity-only estimate (`Project.is_concept` is the single concept read-point).
  Schema bumped to v2 (additive — v1 files load unchanged). The Structural Speeds
  page gains the Concept category with `n`/`n_neg` inputs and an unverified-
  extrapolation warning; the Weight Estimate page shows a concept sanity banner.
  Example fixture `examples/concept_heavy.project.json` (MTOW 18,000 lb). The FAR23
  path stays oracle-locked: all Appendix-A/B tests pass unchanged, and concept mode
  reduces exactly to FAR23 on GA inputs. Confirmed no hard ≤12,500 lb / seat-count
  assertion was load-bearing.

- **Phase C — initial-concept loads tool plan** — adopted a development plan that
  grows the suite from a ≤12,500 lb FAR Part 23 replication into an
  initial-concept distributed-loads tool: a `concept` mode that generalizes the
  FAR23 weight/seat/load-factor caps, configuration assessment against similar
  airplanes, per-component distributed loads (wing / body / tail + standard
  simplified control-surface distributions), and a `FORCE`/`MOMENT` bulk-data
  export bridge to **sbeam**. Locked decisions: concept-mode generalization,
  Schrenk analytical aero, sbeam export bridge, vertical-slice-first build order.
  Steps C0–C8 are tracked in `docs/30_future/00_backlog.md`; the full narrative,
  schema additions and per-step detail are in
  `docs/30_future/01_concept_loads_plan.md`. Reframed the project scope in
  `README.md` and `CLAUDE.md` accordingly (FAR23 replication core *being grown
  into* a concept loads tool). The FAR23 replication core stays oracle-locked
  (Appendix A/B ±0.1%) and concept mode reduces exactly to it on GA inputs.
  *(Planning docs only — no analytical code changed yet.)*
- **MTOW-vs-OEW reference plot on the Weight Estimate page** — the page now plots
  the estimated max take-off and empty weights against a bundled reference fleet
  (Cessna 150/172/182/206/210, Van's RV-7/8/10/14, Bonanza A36, PA-46, King Air
  200, ATR 42-500, Dash 8-100) as a log-log Plotly scatter, with the analysis
  airplane highlighted. Reference figures live in `app/data/reference_aircraft.csv`
  (nominal published specs, UI reference only — never used in a FAR computation) and
  are guarded by `tests/test_reference_aircraft.py`. Adds `plotly>=5.0` as a runtime
  dependency.
- **Seed the weight data base from the estimate** — new pure-calc helper
  `weight_estimate.estimate_to_mass_items(inp)` expands WTESTIMA's structure,
  powerplant and systems component weights (plus options/miscellaneous) into
  empty-weight `MassItem` rows, skipping the group totals and the propeller line
  already inside "Engine installed". `app/pages/01_Weight_Estimate.py` gains a
  "Seed Weight, CG & Inertia from this estimate" button that writes those rows
  into `Project.weight.items`, so the Weight, CG & Inertia page opens pre-filled
  (stations/inertias left at zero for the user). Covered by
  `tests/test_weight_estimate.py::test_seed_mass_items_from_estimate`.
- **MACHLIM Mach-limit lines** — `mach_limit` (MACHLIM) ported against Appendix A
  p160: never-exceed and flutter-clearance Mach (`MNE = 0.9·MD`, `MFC = 1.2·MD`)
  and the per-altitude Mach-limited equivalent airspeeds `V(M) = M·a·√σ` from the
  shoulder altitude to the max operating altitude. Reproduces MNE 0.3627, MFC
  0.4836 and V(MC) 170.16→150.77 (12000→18000 ft). New `MachLimitInput` on
  `Project.speeds.mach_limit`, reusing `constants.standard_atmosphere`;
  `app/pages/06_Mach_Limit.py` (with a V-vs-altitude chart), inputs in the example,
  and `tests/test_mach_limit.py`. **Completes Phase 2.**
- **STRSPEED structural design speeds** — `structural_speeds` (STRSPEED) ported
  against the Appendix A V-n table: limit maneuver load factors (FAR 23.337,
  `n = 2.1 + 24000/(W+10000)` capped by category, negative −0.4n/−0.5n) and design
  airspeeds VA/VC/VD/VF (FAR 23.335) with their minimums, plus cruise/dive Mach at
  the shoulder altitude. Reproduces VA 121.3, VC 170, VD 212.5, VF 105.5, n
  +3.8/−1.52, MC 0.323/MD 0.403 @ 12000 ft. New `StructuralSpeedsInput` /
  `Project.speeds` slice, a shared `constants.standard_atmosphere` helper (also for
  MACHLIM) plus `cruise_speed_coefficient`/`dive_ratio_coefficient`, wing area read
  from the WINGGEOM geometry slice (2·13257/144 = 184.1 ft²),
  `app/pages/05_Structural_Speeds.py`, speeds slice in the example, and
  `tests/test_structural_speeds.py`. VD uses the 1.25·VC floor (the worked
  example's governing bound); K_d·VC is reported as the recommended gust value.
- **WTENV weight/CG envelope** — `weight_envelope` (WTENV) ported against the
  Chapter 3 worked example: structural CG-limit stations (`X = XLEMAC + pct·MAC`,
  reading wing XLEMAC/MAC from the geometry slice via WINGGEOM), minimum/maximum
  loadings, the forward discretionary-loading envelope, and the ballast to reach
  each structural limit (`WB = WL−WA`, moment-balance station). Reproduces the
  manual's stations (85.1/77.49/72.64), min flight 2063@73.09, max load 3322@84.56
  and ballast weights 78/418/158. New `WeightEnvelopeInput` under `Project.weight`,
  `app/pages/04_Weight_Envelope.py`, envelope inputs in the example, and
  `tests/test_weight_envelope.py`. The aft-gross ballast station is the exact
  moment balance (~108.5 in); the manual's hand calc rounded it to 103.7 (limit
  station 85.0 vs the precise 85.107) — documented in the module.
- **Phase 2 geometry** — `wing_geometry` (WINGGEOM) ported against Appendix A
  p141: spanwise strip-sum of area, MAC, YLE(MAC), XLEMAC, aspect ratio and span
  per aerodynamic surface (the wing reproduces MAC 69.246 / XLEMAC 63.641 / AR
  6.095 within ±0.1% at the manual's 20-element count). New `Project.geometry`
  slice (`GeometryInput` → `SurfaceInput` with LE/TE point polylines, `symmetric`,
  `elements`), `geometry_from_dict`/`geometry_to_dict`, wing+aileron surfaces in
  the example, `app/pages/03_Wing_Geometry.py`, and `tests/test_wing_geometry.py`.
  `units.py` gained area (in²→m²) and airspeed (knot→m/s) SI output. Wing-mounted
  engine spanwise stations are derived from `engine_layout`.
- **First-class multi-engine layout** — the `Project` engine slice is now a list
  (`engines: List[EngineInput]`) plus an `EngineLayout` enum constrained to the
  modelled layouts (`SINGLE_NOSE` = 1 nose, `TWIN_WING` = 2 wing, `QUAD_WING` =
  4 wing, symmetric). `Project.__post_init__` validates the engine count against
  the layout; a read-only `Project.engine` property returns the first engine so
  single-engine call sites are unchanged. `io.py` reads either the new
  `"engines"`/`"engine_layout"` JSON or the legacy single `"engine"` key, and the
  engine module's `run(project)` loops over every engine (single-engine output is
  byte-identical; multi-engine prefixes each condition with the engine
  designation). Resolves PROJECT_GUIDE open decision #2 ("model the field now").
  Full one-engine-out *loads* still land at `ONENGOUT`.
- **Phase 1 mass properties** — two modules ported against Appendix A:
  `weight_estimate` (WTESTIMA, statistical weight estimate; reproduces the p133
  figures exactly) and `weight_onecg` (WTONECG, one-loading weight/CG/inertia;
  matches the p136 figures within ±0.1%). New `Project.weight` slice
  (`WeightInput` = mission `estimation` + itemized `items` mass list), with
  `EngineWeightType`/`MassItemKind` enums and the installed-engine-weight
  correlation centralised in `constants.py`. New Streamlit pages
  `01_Weight_Estimate.py` and `02_Weight_CG_Inertia.py`, example weight slice in
  `examples/ga6_normal.project.json`, and `tests/test_weight_estimate.py` /
  `tests/test_weight_onecg.py`. The pages offer an SI **output** toggle (weight →
  kg, inertia → kg·m², CG → mm). `WTENV` re-scoped to Phase 2 (needs `WINGGEOM`'s
  `XLEMAC`/`MAC`).
- `report.module_text_report` — module-agnostic text output, used by the
  generalised `cli.py` stdout path so non-engine modules render correctly.
- **Packaging & tooling** — `pyproject.toml` (editable install via
  `pip install -e '.[dev]'`; `ruff` and `pytest`/coverage config), `cspell.json`
  domain wordlist, and a GitHub Actions CI workflow running `ruff` + `pytest` on
  Python 3.9 / 3.11 / 3.12.
- **Documentation structure** — `docs/` reorganised by type
  (`10_standard` / `20_theory` / `30_future` / `40_history`) with an index
  (`docs/00_INDEX.md`). Added `docs/20_theory/00_theory_sources.md`,
  `docs/30_future/00_backlog.md`, and `docs/40_history/00_completed_development.md`.
- **Process guides** — `docs/10_standard/CODE_REVIEW_PROCESS.md` and
  `RELEASE_PROCESS.md`, specialised for the module-porting workflow.
- **`LICENSE`** (MIT) backing the `pyproject.toml` license declaration, plus
  README License and Disclaimer sections (results are not certified for design).
- **`docs/10_standard/00_program_overview.md`** — consolidated program code
  standard & developer guide (coding standards, an error-handling contract,
  units, entry points, testing/coverage), with `docs/00_INDEX.md` and `CLAUDE.md`
  pointing to it as the authoritative standard.
- **CI coverage floor** — the pytest step now runs with `--cov-fail-under=80` so
  coverage cannot silently regress (a ratchet, to be raised toward 85%).

### Changed

- **Documentation critical review & consistency pass.** Brought the docs in line
  with the as-built code (Phases 0–2 + Phase-C C0–C6; 13 of 22 suite programs +
  `configuration`/`body_loads`; `SCHEMA_VERSION` 11). Rewrote
  `docs/30_future/00_backlog.md` as a dependency-ordered step-by-step plan
  (Steps C7–C11 + deferred refinements + open decisions + a release/versioning
  item). Corrected stale status in `docs/10_standard/00_program_overview.md`
  (structure tree + "Phase 0 complete"), `README.md` ("7 of 22" → 13 of 22; layout
  tree), `CLAUDE.md` (`Project` "currently just engine"; the contradictory
  `sys.path`-shim line), `PROJECT_GUIDE.md` ("exactly one is ported", §2 inventory
  status, §7 roadmap, examples list), `PROGRAM_SPEC.md` (status-summary Phase 0
  row), and `docs/00_INDEX.md`. Removed the superseded `Phase1_2_review.md`
  GUI-review notes (its one live item — Home Engineer/Date fields — moved to the
  backlog). No analytical code changed.
- **SI mass vs Imperial force units.** `LoadValue` gained an optional `quantity`
  hint so the SI converter can tell a pounds-*mass* weight (→ kg) from a
  pounds-*force* load (→ N) — both labelled `lb`. Added `lb-in² → kg·m²` to the
  result converter; weights set `quantity="mass"`. Engine load output is
  unchanged.
- `cli.py` text output is now module-agnostic (was engine-specific), and
  `io.load_cases_csv` falls back to the generic property table for modules that
  emit no structural load cases, so the mass-properties modules export usable CSV.
- `farloads` and `cli` are now an editable install, so they import from any cwd;
  removed the `sys.path` shims from `app/Home.py` and `app/pages/19_Engine_Mount.py`.
- Renamed the ambiguous local helper `l` to `ln` in `farloads/units.py` (lint).
- Fixed stale `calc.py` references (the module is `farloads/modules/engine.py`) in
  `farloads/models.py` and `farloads/report.py` comments/docstrings.
- `CLAUDE.md` mandate strengthened: consult the `reference/` PDFs when generating
  analysis code, keep `docs/` in sync with every code change, and follow the
  backlog → history → changelog move-on-completion rule.
- `docs/PROGRAM_SPEC.md` and `docs/PROJECT_GUIDE.md` moved to `docs/10_standard/`;
  cross-references in `README.md` and `CLAUDE.md` updated.

---

## [0.1.0]

Phase 0 baseline — the package restructure with the engine-mount module ported.
See `docs/40_history/00_completed_development.md` for the full record.

### Added

- `farloads/` pure-calc package (`models`, `modules/engine`, `registry`, `io`,
  `units`, `report`, `constants`), the `app/` Streamlit multi-page UI, and
  `cli.py`. Engine-mount module (`ENGLOADS`) validated against Appendix A/B.
