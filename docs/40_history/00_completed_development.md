# Completed Development

The authoritative record of what has shipped: completed modules/phases, key
decisions, and resolved defects. Items move here from
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) the moment they close,
with a matching `CHANGELOG.md` entry.

Each entry uses the step format: **Objective**, **Deliverables**, **Test /
Acceptance**, **Key decisions**.

---

## Phase 0 — Package restructure (complete)

**Objective.** Recast the standalone `engloads` program into the shared
pure-calc package + thin-shell architecture that every subsequent module will
follow, with the engine-mount module as the proof of pattern.

**Deliverables.**
- `farloads/` pure-calc package: `models.py` (`Project`, `EngineInput`/`Rotor`,
  `ConditionResult`/`LoadValue`, `ModuleResult`, `SCHEMA_VERSION`),
  `modules/engine.py` (port of `ENGLOADS.BAS`), `registry.py`, `io.py`,
  `units.py`, `report.py`, `constants.py`.
- `app/` Streamlit multi-page UI (`Home.py` + `pages/19_Engine_Mount.py`).
- `cli.py` argparse front-end.
- `tests/` suite vs the manual's Appendix A/B figures.

**Test / Acceptance.** Green build — full `pytest` suite passing, engine module
checked against Appendix A (p131) and Appendix B (p251) figures within ±0.1%.

**Key decisions.**
1. **Hybrid architecture** — one shared calc package, interchangeable GUI/CLI/test
   front-ends; calc does no I/O.
2. **Single reloadable `Project`** — one JSON bundle carries every module's input
   slice; `schema_version` from day one.
3. **Modernize the math** — `math.pi` and clean equations, *not* the BASIC's
   `3.1416`. The manual's printed figures become **tolerance-based** regression
   oracles (±0.1%), not exact oracles. Constants centralised in `constants.py` so
   this stays a one-file decision.
4. **Preserved engineering conventions** — engine-mount reaction torque reported
   negative; "clockwise from the pilot's view is positive"; selected intermediate
   quantities truncated to 3 decimals (`int(x*1000)/1000`) to mirror the BASIC.

---

## Phase 1 — Mass properties: WTESTIMA + WTONECG (complete)

**Objective.** Port the head of the mass-properties pipeline: weight estimation
(`WTESTIMA`) and one-loading weight/CG/inertia (`WTONECG`), establishing the
shared `Project.weight` slice the downstream load modules will read. `WTENV` was
**re-scoped to Phase 2** (its structural-CG-limit math needs `XLEMAC`/`MAC` from
`WINGGEOM`); see the backlog.

**Deliverables.**
- `farloads/models.py` — `Project.weight` slice (`WeightInput`) carrying mission
  `estimation` inputs (`WeightEstimationInput`) and the itemized `items` mass list
  (`MassItem`), plus `EngineWeightType` and `MassItemKind` enums.
- `farloads/modules/weight_estimate.py` (`WTESTIMA.BAS`) and
  `farloads/modules/weight_onecg.py` (`WTONECG.BAS`), self-registered as
  `weight_estimate` / `weight_onecg`. Mass-properties constants and the
  installed-engine-weight correlation centralised in `constants.py`.
- `farloads/io.py` — `weight_from_dict`/`weight_to_dict` wired into the project
  JSON round-trip; `load_cases_csv` falls back to the generic property table for
  modules that emit no structural load cases.
- `report.module_text_report` and a generalised `cli.py` text path so non-engine
  modules render to stdout.
- `app/pages/01_Weight_Estimate.py`, `app/pages/02_Weight_CG_Inertia.py` (Imperial
  units; the CG page edits the weight data base in a `st.data_editor`).
- `examples/ga6_normal.project.json` extended with the Appendix A weight slice;
  `tests/test_weight_estimate.py` and `tests/test_weight_onecg.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing with the coverage floor held (≥80%). `WTESTIMA` reproduces
Appendix A p133 exactly (integer-truncated figures); `WTONECG` matches Appendix A
p136 within ±0.1% (weight and lb-in² accumulators are g-independent and exact).

**Key decisions.**
1. **One input slice, pure-calc outputs.** `Project.weight` is the shared input
   "weight database"; modules stay pure (`run → ModuleResult`). No persisted
   `Project.mass` slice yet — it is added when a consumer (FLTLOADS/LANDLOAD)
   exists.
2. **Property table, not load cases.** Mass-properties results render via
   `results_to_rows`/`module_text_report`, not the engine-specific
   `load_cases_to_rows`.
3. **Force vs mass units.** A weight is pounds-*mass* and must convert to kg, but
   a load in `lb` is pounds-*force* and converts to N — the same `"lb"` label.
   `LoadValue` gained an optional `quantity` hint; a weight sets `quantity="mass"`
   so `units.py` routes it to kg, while loads (blank hint) convert by unit string
   to N. Inertia (slug-ft²/lb-in²) → kg·m². The mass-properties pages expose an SI
   output toggle on this basis; inputs stay Imperial.
4. **Preserved BASIC quirks** — `INT(...)` truncation on `WTESTIMA` outputs, and
   the single-engine "misc other system wt = 0" (the program prints an unset
   variable there).

---

## Phase 2 — Geometry: WINGGEOM + first-class multi-engine (complete)

**Objective.** Port aerodynamic-surface geometry (`WINGGEOM`) — the wing's
`MAC`/`XLEMAC` seed `WTENV` and `STRSPEED` — and, alongside it, promote the engine
slice to first-class multi-engine support (resolving PROJECT_GUIDE open decision
#2) so geometry/weight/speeds can reference the engine layout now and `ONENGOUT`
can exercise it fully later.

**Deliverables.**
- **Multi-engine schema** — `EngineLayout` enum (`SINGLE_NOSE`/`TWIN_WING`/
  `QUAD_WING`, symmetric); `Project.engines: List[EngineInput]` + `engine_layout`
  with `__post_init__` count validation and a read-only `Project.engine` compat
  property. `io.py` reads the new `engines`/`engine_layout` JSON or the legacy
  single `engine` key; `modules/engine.py` `run()` loops over every engine
  (single-engine output byte-identical, multi-engine prefixed by designation).
- `farloads/models.py` — `Project.geometry` slice (`GeometryInput` →
  `SurfaceInput` per surface: LE/TE point polylines, `symmetric`, `elements`).
- `farloads/modules/wing_geometry.py` (`WINGGEOM.BAS`), self-registered as
  `wing_geometry`: strip-sum area/MAC/YBAR/XLEMAC/AR/span per surface, plus
  wing-mounted engine spanwise stations driven by `engine_layout`.
- `farloads/io.py` — `geometry_from_dict`/`geometry_to_dict`; `units.py` gained
  area (`in²`→m²) and airspeed (`knot`→m/s) SI output conversions.
- `app/pages/03_Wing_Geometry.py` (per-surface point editors, SI output toggle);
  `examples/ga6_normal.project.json` extended with wing + aileron surfaces and the
  multi-engine layout form; `tests/test_wing_geometry.py` and new multi-engine
  assertions in `tests/test_engine.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). The **wing** reproduces
Appendix A p141 within ±0.1% (AREA/SIDE 13257, MAC 69.246, YLE(MAC) 87.854,
XLE(MAC) 63.641, AR 6.095) at the manual's 20-element strip count; the aileron
exercises the unsymmetric path (checked loosely, since Appendix A does not
tabulate its element count).

**Key decisions.**
1. **Strip count is an input, oracle is H-specific.** The manual's printed figures
   *are* the `H`-element midpoint strip sum, so `elements` must match the manual's
   value (20 for the wing) to reproduce them — kept as a per-surface field.
2. **Multi-engine first-class now.** Engine list + layout modelled this phase;
   the engine module loops over engines, but one-engine-out *loads* remain at
   `ONENGOUT`. Backward-compatible: legacy single-`engine` JSON still loads.
3. **Wing is the authoritative oracle.** `XLEMAC`/`MAC` (the figures the whole
   pipeline cites) are matched tightly; secondary surfaces use the same calc.

---

## Phase 1 (deferred item) — WTENV weight/CG envelope (complete)

**Objective.** Complete the mass-properties phase by porting `WTENV` — the
discretionary-loading envelope, structural CG limits and ballast — which was
re-scoped to land after `WINGGEOM` because its limit stations need the wing
`XLEMAC`/`MAC`.

**Deliverables.**
- `farloads/models.py` — `WeightEnvelopeInput` under `Project.weight.envelope`
  (gross weight, the three %-MAC CG limits, the forward-regardless reduced weight,
  and an optional XLEMAC/MAC override).
- `farloads/modules/weight_envelope.py` (`WTENV.BAS`), self-registered as
  `weight_envelope`: empty / minimum-flight / maximum loadings; structural-limit
  stations `X = XLEMAC + pct·MAC` (reading the wing geometry through WINGGEOM's
  `surface_properties`, not re-deriving it); the forward loading envelope; and the
  ballast per limit by moment balance.
- `farloads/io.py` — envelope (de)serialization on the weight slice;
  `app/pages/04_Weight_Envelope.py`; envelope inputs in the example;
  `tests/test_weight_envelope.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). Reproduces Chapter 3 p21-22:
stations 85.1 / 77.49 / 72.64, minimum flight weight 2063 @ 73.09, maximum loading
3322 @ 84.56, and ballast weights 78 / 418 / 158 lb (forward-gross/forward-
regardless ballast *stations* also match: 80.27 / 70.97).

**Key decisions.**
1. **Read geometry, don't re-derive.** WTENV obtains XLEMAC/MAC by calling
   WINGGEOM's pure `surface_properties` on the wing surface — honouring "read
   shared, write own".
2. **Ballast is the exact moment balance.** Per Decision 3 the aft-gross ballast
   station is reported as the precise balance (~108.5 in); the original manual's
   hand calc rounded the limit station to 85.0 (giving the 103.7 its own WTONECG
   data base then carried). The ballast *weights* match exactly.
3. **Documented reference-point selection.** The ballast reference loadings are
   chosen as in the worked example (full load for aft gross; the forward-boundary
   knee for forward gross; the heaviest forward point ≤ reduced weight for forward
   regardless), reproducing all three manual ballast weights.

---

## Phase 2 — Structural design speeds: STRSPEED (complete)

**Objective.** Port the design-airspeed and limit-maneuver-load-factor module
(`STRSPEED`), which seeds the flight-envelope and control-surface load modules
(FLTLOADS, AILERON, FLAPLOAD) and shares its standard-atmosphere/Mach machinery
with `MACHLIM`.

**Deliverables.**
- `farloads/models.py` — `StructuralSpeedsInput` and the `Project.speeds` slice
  (category, design weight, stall speeds, VH, shoulder altitude, chosen speeds and
  load factors).
- `farloads/modules/structural_speeds.py` (`STRSPEED.BAS`), self-registered as
  `structural_speeds`: FAR 23.337 maneuver load factors, FAR 23.335 design speeds
  (VA/VC/VD/VF) with their minimums, and cruise/dive Mach at the shoulder altitude.
- `farloads/constants.py` — shared `standard_atmosphere(altitude)` (a, sigma, with
  the tropopause branch) plus `cruise_speed_coefficient`/`dive_ratio_coefficient`,
  reused by MACHLIM next.
- `farloads/io.py` — speeds (de)serialization; `app/pages/05_Structural_Speeds.py`;
  speeds slice in the example; `tests/test_structural_speeds.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). Reproduces the Appendix A V-n
table within ±0.1%: VA 121.3, VC 170, VD 212.5, VF 105.5 kt (EAS); n = +3.8 /
−1.52; MC 0.323 / MD 0.403 at the 12000 ft shoulder altitude; VC(min) 141.8 kt;
wing area 184.1 ft².

**Key decisions.**
1. **Wing area from geometry.** S is read from the WINGGEOM wing surface
   (total area in² → ft²), not re-entered — "read shared, write own".
2. **VD floor is 1.25·VC.** The worked example's governing dive-speed bound is the
   absolute FAR 23.335(b) floor 1.25·VC (212.5 kt); the gust-based K_d·VC (238 kt)
   is reported as the recommended value but not enforced, matching the manual.
3. **Shared atmosphere helper.** `standard_atmosphere` lives once in
   `constants.py` so STRSPEED and MACHLIM cannot drift; the shoulder altitude
   (12000 ft for the example) is an input.

---

## Phase 2 — Mach-limit lines: MACHLIM (complete)

**Objective.** Port the Mach-limit-line module (`MACHLIM`) — the V-vs-altitude
limit lines for the flight-limits diagram — completing Phase 2.

**Deliverables.**
- `farloads/models.py` — `MachLimitInput` on `Project.speeds.mach_limit` (MC, MD,
  shoulder/max altitudes, increment).
- `farloads/modules/mach_limit.py` (`MACHLIM.BAS`), self-registered as
  `mach_limit`: `MNE = 0.9·MD`, `MFC = 1.2·MD`, and the per-altitude
  Mach-limited equivalent airspeeds `V(M) = M·a·√σ` (reusing
  `constants.standard_atmosphere`, including its tropopause branch).
- `farloads/io.py` — nested `mach_limit` (de)serialization on the speeds slice;
  `app/pages/06_Mach_Limit.py` (with a V-vs-altitude line chart);
  mach_limit inputs in the example; `tests/test_mach_limit.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). Reproduces Appendix A p160
within ±0.1%: MNE 0.3627, MFC 0.4836, and the EAS table from V(MC) 170.16 /
V(MD) 212.31 at 12000 ft down to V(MC) 150.77 / V(MD) 188.11 at 18000 ft.

**Key decisions.**
1. **Reuses the shared atmosphere.** No second copy of the atmosphere law; the
   program's `a = 29.02` vs the helper's `29.02436` is a ~0.01% difference
   absorbed by the ±0.1% tolerance (Decision 3).
2. **Per-altitude condition rows.** Each altitude is its own `ConditionResult`, so
   the CSV/text/GUI render the limit-line table directly and the GUI can chart it.

---

## Phase C — Step C0: concept-mode foundation & mission reframe (complete)

**Objective.** Remove the two GA-only assumptions that block >12,500 lb /
greater-than-GA-seat configurations — the FAR 23.337 maneuver-load-factor
formula/cap and WTESTIMA's statistical estimate — without disturbing the
oracle-locked FAR23 path. (Prerequisite for the Phase-C concept loads tool;
narrative in [`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md).)

**Deliverables.**
- `models.py` — `StructuralSpeedsInput.category` gains `"C"` (concept), documented
  as requiring explicit `chosen_n`/`chosen_nneg`; `WeightInput.direct_totals()`
  (the direct-weight path: MTOW/OEW/useful summed from the itemized `items` by
  `MassItemKind`); `Project.is_concept` (single concept read-point); `SCHEMA_VERSION`
  bumped 1 → 2 (additive — v1 files load unchanged via the `from_dict` defaults).
- `modules/structural_speeds.py` — `_maneuver_load_factors` branches on concept,
  using the user's load factors verbatim with no FAR floor/cap; the load-factor
  result note flags the unverified extrapolation. The GA-calibrated VC(min)/VD(min)
  coefficients remain as out-of-band advisories (concept supplies chosen speeds).
- `modules/weight_estimate.py` — `run()` flags the WTESTIMA summary as a GA
  sanity estimate in concept mode; `estimate()` is unchanged so the Appendix-A
  oracle still holds.
- UI — Structural Speeds page adds the Concept (C) category with `n`/`n_neg`
  inputs and an unverified-extrapolation warning; the Weight Estimate page shows a
  concept sanity banner.
- `examples/concept_heavy.project.json` — an 18,000 lb concept commuter twin.

**Test / Acceptance.** All pre-existing tests pass unchanged (FAR23 identity
invariant). New `tests/test_concept.py` (`direct_totals` by kind; end-to-end
fixture run; IO round-trip) and concept cases in `tests/test_structural_speeds.py`
(cap bypassed; missing load factors raise). The fixture (MTOW > 12,500, user n)
runs STRSPEED and WTESTIMA end-to-end with the chosen factors (4.0 / -2.0) honoured
verbatim. **Confirmed** no hard ≤12,500 lb / seat-count assertion was load-bearing
(STRSPEED only checks `w > 0`; WTESTIMA only `engines >= 1` / `seats >= 1`; WTENV
none).

**Key decisions.**
1. **Concept is a strict superset** — `category == "C"` switches off the GA caps;
   the physics is unchanged and reduces exactly to FAR23 on GA inputs.
2. **Direct-weight = sum the itemized data base by kind** — one source of truth (no
   parallel direct-MTOW field that could disagree with the items list).
3. **Docs scope reframe landed with the plan** — CLAUDE.md / README.md /
   PROJECT_GUIDE.md were reframed when the Phase-C plan was adopted; C0 is the code.

---

## Phase C — Step C1: AIRLOADS (Schrenk spanwise lift) + TAU (complete)

**Objective.** Compute the wing spanwise lift distribution (`c·cl` span load) —
the first real distributed-load deliverable and the input every downstream
wing-load module (FLTLOADS balancing, WINGINER, NETLOADS, the sbeam export)
consumes. Method: **Schrenk's** (Reference 1 Ch 7, p46-47; CAA-accepted per CAM 04
App V) — average the planform-chord and elliptic lift distributions. (Narrative in
[`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md) §C1.)

**Equations (Ref 1 Ch 7).** Per strip (mid-station `ye`, chord `c`, width `dy`),
reusing the WINGGEOM strip integrator so stations align with the geometry table:
- additive (CL=1): `c·cl = 0.5·( mo·c/Mo + 4S/(π·B)·√(1−(2ye/B)²) )`, with
  `Mo = Σ(mo·c·dy)/(S/2)`, `S = 2·Σ(c·dy)`, `B = 2·ytip`;
- basic (twist): `Awo = Σ(mo·c·ac·dy)/Σ(mo·c·dy)`, `aa = ac − Awo`,
  `c·cl_basic = (mo/2)·aa·c`;
- combine at target CL: `c·cl = c·cl_additive·CL + c·cl_basic` (basic integrates to
  zero net wing lift);
- TAU planform correction from the `TAU.BAS` quartic curve-fit in taper ratio,
  interpolated by tip ratio (p407); wing slope `M = mo_rad/(1 + mo_rad/(π·AR)·(1+τ))`.

**Deliverables.**
- `models.py` — `AeroSurfaceInput` (section slope `mo`, taper/tip ratio, optional
  `tau` override, spanwise `twist` table, `target_cl`) + `AeroInput`; `Project.aero`;
  `SCHEMA_VERSION` 2 → 3 (additive — older files load unchanged).
- `modules/airloads.py` — registers `"airloads"`; `_tau` curve-fit helper;
  `schrenk_distribution()` returns the per-strip `SpanwiseTable` (additive/basic/
  total `c·cl` and `cl`, plus `Mo`/`M`/`τ`/`Awo`/area/span and the integrated-CL
  closure); `spanwise_distribution()` wraps it as a reportable `ConditionResult`;
  `run(project)` flags concept mode as an unverified extrapolation. Reuses
  `wing_geometry._interp_x` for chord and twist interpolation.
- `io.py` — `aero_from_dict`/`aero_to_dict` round-trip; wired into the project
  load/save. `modules/__init__.py` imports `airloads` for self-registration.
- UI — `app/pages/06_Airloads.py`: aero inputs + editable twist table, a span-load
  plot (additive / basic / total), and the recovered-CL closure metric.
- Fixtures — the GA (`ga6_normal`) and concept (`concept_heavy`) projects gain an
  `aero` wing slice (concept also gains a wing planform).

**Test / Acceptance.** New `tests/test_airloads.py` (10 tests). FAR23 oracle
(±0.1%, `math.isclose(rel_tol=1e-3)`) vs Appendix A p161-162: additive `CC(LA1)`
elem 1/10/20 = 91.05576 / 69.44847 / 31.82978, `C(LA1)` elem 1 = 0.9275981, additive
integral CL = 1.00061; basic `Awo` = 3.988146, `CC(lb)` elem 1 = +5.09762, `Clb`
elem 1 = 0.05193; area/span/AR match WINGGEOM (26513.4 / 402 / 6.095). TAU curve-fit
(square-tip `τ(λ=0)` = 0.206209; `τ = 0` at tip ratio 1). Concept closure: the
`concept_heavy` integral recovers `target_cl` and the basic distribution carries
zero net lift. IO round-trip + missing-slice `ValueError`. All pre-existing tests
pass unchanged (FAR23 identity) — 93 passing.

**Key decisions.**
1. **Full Schrenk (additive + basic + combine)** — needed to reproduce the Appendix A
   wing, which has washout (root 5° → tip 1.9°).
2. **Aero slice carries inputs; the distribution flows out as a `ModuleResult`** —
   no persisted result-in-project field until a consumer (C2) needs one (avoids
   speculative state); matches the existing module pattern.
3. **Basic-distribution fairing deferred** — the cosine fairing across a flap/aileron
   lift discontinuity (Ref 1 p47) only arises with deflected flaps and is absent from
   the Appendix A wing; left as a documented limitation for a later step.

---

## Phase C — Step C2: FLTLOADS (V-n envelope + balancing tail loads) (complete)

**Objective.** Port the FAR 23.333 maneuver + gust flight envelope and the
balancing horizontal-tail load at every corner — the candidate-condition matrix
SELECT later prunes and WINGINER/NETLOADS consume.

**Deliverables.**
- `farloads/models.py` — new **`Project.flight_loads`** input slice
  (`FlightLoadsInput`: `mac`/`wing_area_sqft`/`xw`/`zw`/`xtc`/`xtf`, reference Mach
  `mn`, altitude list, per-configuration `AeroCoeffSet` aero-coefficient polynomials
  CL(α)/CD(CL)/CM(α) + stall CLs, weight-CG `CgCase` list) and the new
  **`Project.envelope`** result slice (`EnvelopeResult.vn` / `.tail_balance`:
  `VnPoint` + `TailBalanceLoad`). `SCHEMA_VERSION` bumped to **4** (additive — older
  files load unchanged); `io.py` round-trip extended for both slices.
- `farloads/modules/flight_envelope.py` — faithful port of FLTLOADS.BAS subroutine
  **3900** (iterate AoA to the required load factor, then dynamic pressure to the
  Mach-adjusted stall line; Glauert `G/Gmn`; CLmax-vs-Mach 5th-order fit) and **4864**
  (gust load factor, FAR 23.341). Balancing
  `LT = [M(W+F) + LZ·(Xcg−Xw) − DX·(Zcg−Zw)]/(XT−Xcg)` with approximate tail CP
  (XTC≈5% / XTF≈25% tail MAC). Reads VA/VC/VD/VF, MC/MD and the limit load factors
  from STRSPEED (`design_speeds` + `_maneuver_load_factors`, the single owner).
  Registered `"flight_envelope"`; pure entry `build_envelope(project) → EnvelopeResult`.
- New Streamlit page `app/pages/07_Flight_Envelope.py` (V-n diagram + balanced-
  condition table + editable aero coeffs / CG cases). Example fixtures gain a
  `flight_loads` slice.

**Test / Acceptance.** `tests/test_flight_envelope.py` oracle-locks the Appendix A
"V-n Data" cruise matrix (p179-180) for CG1/CG2: corner speeds, load factors, α, G,
and the balancing tail load LT (e.g. STALL 1G LT 132, MAN A LT 493 / LZW 12419,
GUST +C NZ +3.96, AC ROLL LT 412, CG2 MAN A LZW 12970 / LT −59). The AoA balance
converges NZ to ±0.005 (FLTLOADS.BAS line 4130), so LT and corner speeds/factors
use tight tolerances while low-load-factor quantities use the ~0.5% convergence
floor. Concept mode checked by physics closure (the balance attains the user load
factor with no GA cap; LZ+LT = NZ·W). Full suite green (106 tests), ruff clean.

**Key decisions.**
1. **Aero coefficients are inputs** — the airplane-less-tail CL/CD/CM polynomials
   come from the Ch 7 aero-coefficients program and are entered via `AeroCoeffSet`
   (AIRLOADS/C1 does not yet emit them), faithful to the BAS prompts.
2. **Explicit CG cases, no `Project.mass`** — the balance uses the four weight-CG
   envelope cases entered directly (matching the BAS), so the original data-flow's
   `Project.mass`/WTONECG read is unnecessary for C2; seeding the CG cases from
   WTENV is a later refinement. The planned WTONECG `MassProperties` refactor was
   dropped from C2 as unneeded.
3. **Cruise scope** — the cruise maneuver+gust corner set (20 conditions); the
   flapped LANDING/ENROUTE envelopes share the balance engine and drop in later.
4. **Local atmosphere constant** — FLTLOADS' own speed-of-sound constant (518.688
   vs the shared `standard_atmosphere`'s 518.4) is replicated locally for oracle
   fidelity near the Mach cap; documented in the module.

---

## Phase C — Step C3: WINGINER + NETLOADS (wing net span loads) (complete)

**Objective.** The headline structural deliverable: net spanwise wing **shear,
bending moment and torsion** (air load + inertia) along the 25% chord at the
critical conditions.

**Deliverables.**
- `farloads/models.py` — new **`Project.wing_mass`** input slice (`WingMassInput`:
  panel weight, tip/root area-density ratio, inboard rib, wing-reference-plane
  waterline + dihedral, `ConcentratedWeight` list, `WingLoadCase` list) and the
  **`Project.loads`** result slice (`LoadsResult` = `wing_air`/`wing_inertia`/
  `wing_net`, each `WingLoadResult` of `WingStationLoad`). `AeroSurfaceInput`
  gains the section `profile_drag` (CDO) and `section_cm` (CM) tables.
  `SCHEMA_VERSION` 4→5 (additive); `io.py` round-trip extended.
- `farloads/modules/airloads.py` — `air_load_distribution()` (AIRLOADS load option,
  subr 4500/4600-5060): scales the C1 Schrenk section lift to the operating CL,
  builds per-strip lift/drag/moment at `Q=V²/295`, rotates by `α=CL/M−Awo`, and
  integrates tip→root to Sz/Mxx/Myy and Sx/Mzz; drag = induced `cl·ai/57.3` +
  profile CDO.
- `farloads/modules/wing_inertia.py` (`register("wing_inertia")`) — tapered
  panel-mass distribution (root density iterated to panel weight), 1g-vertical /
  1g-drag / unit-roll unit cases combined per `(Nz, Nx, UNB)`; concentrated
  weights as spanwise steps.
- `farloads/modules/net_loads.py` (`register("net_loads")`) — net = air + inertia
  per station; per-station CSV (`wing_load_rows`). The C3-before-SELECT bridge:
  `Nz=−NZ`, `Nx=−DX/W`, CL/V read from the FLTLOADS `envelope.vn` point.
- New Streamlit page `app/pages/08_Net_Wing_Loads.py` (air/inertia/net shear, BM,
  torsion plots + station table + CSV). Example fixtures gain a `wing_mass` slice
  (and the GA wing aero gains `tau=0.05`, profile drag and section CM).

**Test / Acceptance.** `tests/test_wing_inertia.py` + `tests/test_net_loads.py`
oracle-lock the Appendix A worked example to ±0.1%: the air-load Case 22 PHAA
table (p206 — root Sz +6470, Mxx +516955, Myy −79003, Mzz −91283), the WINGINER
density (2.213/2.102 lb/ft²) and unit/combined inertia tables (p217-221), and the
Net Loads Case 22 table (p222 — root Sz +5837, Mxx +455555, Myy −60940). Concept
mode checked by the net = air + inertia identity and a trapezoidal-Schrenk root-BM
closure. Full suite green (123 tests), ruff clean.

**Key decisions.**
1. **Air-load shear/BM/torsion lives in AIRLOADS** (its "load distribution" option),
   not NETLOADS — faithful to the original; NETLOADS is the algebraic sum.
2. **TAU = 0.05 override** on the GA wing aero reproduces the manual's printed wing
   lift-curve slope exactly (C1's computed 0.0397 differs), making the full
   distribution oracle-exact; C1's oracle is independent of TAU.
3. **Full fidelity** — all of Fx/Fz/Sx/Sz/Mxx/Myy/Mzz (added the section profile-drag
   and pitching-moment inputs the drag/torsion components need), per the locked C3
   scope decision.
4. **Explicit load cases / no `Project.mass`** — the critical conditions come from
   the V-n matrix (C2) as `WingLoadCase`s (SELECT, C6, will pick them automatically);
   `Nz`/`Nx` default from the V-n point. Concentrated wing masses are supported.

---

## Tooling & documentation standard (complete)

**Objective.** Bring the project's tooling and documentation standard in line
with the sibling `sbeam` project before the module-porting work scales up.

**Deliverables.**
- `pyproject.toml` — editable install (`pip install -e '.[dev]'`), so `farloads`
  and `cli` import from any cwd; the `sys.path` shims were removed from `app/`.
  `ruff` (select `E`/`F`/`W`, ignore `E741`) and `pytest`/coverage config.
- `cspell.json` domain wordlist.
- `.github/workflows/ci.yml` — `ruff` + `pytest` on Python 3.9 / 3.11 / 3.12.
- `docs/` reorganised by type (`10_standard` / `20_theory` / `30_future` /
  `40_history`) with `docs/00_INDEX.md`.
- `docs/10_standard/CODE_REVIEW_PROCESS.md` and `RELEASE_PROCESS.md`;
  `CHANGELOG.md` (Keep a Changelog).
- `CLAUDE.md` mandate strengthened: consult `reference/`, keep `docs/` in sync,
  and the backlog→history→changelog move-on-completion rule.

**Test / Acceptance.** `ruff check farloads/ cli.py` clean; full `pytest` suite
passing after the `sys.path` shims were removed.

**Key decisions.**
- CI lints `farloads/` and `cli.py` (the pure calc + CLI). Streamlit pages in
  `app/` are not lint-gated: their long widget-label lines and the deliberate
  late `from farloads.modules import engine` import are acceptable there.
- `requires-python = ">=3.9"` to match `sbeam` (the code uses
  `from __future__ import annotations`, so 3.9 is safe).

---

## Resolved defects

- _(none recorded)_
