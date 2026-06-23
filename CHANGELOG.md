# Changelog

All notable changes to FAR 23 LOADS are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed

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
