# Changelog

All notable changes to FAR 23 LOADS are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

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
