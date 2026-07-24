# sloads — Program Specification

Per-module specification for replicating the 22-program **FAR 23 LOADS** suite.
Read alongside [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md), which defines the shared
architecture (hybrid package + multipage UI), the single-project-JSON / per-module
-CSV data model, the modernized-math fidelity decision, and the phased roadmap.

## Source documents

Two distinct manuals describe the suite — do not conflate them. **Both are in the
repo.**

- **Reference 1** — McMaster, *"FAR23 LOADS"* (Aero Science Software, Std v3.0 /
  Pro v1.0); file `FAR23Loads_Code.pdf` (371 pp). The **theoretical** development
  and the project's authoritative **equation + validation oracle**: 20 chapters,
  **Appendix A** (6-place GA loads report, p131), **Appendix B** (10-place twin
  loads report, p251), **Appendix C** `.BAS` source listings (p373). Chapter
  numbers cited below as "Ch N" refer to *this* manual (and are correct — Ch 2
  WTESTIMA … Ch 19 ENGLOADS … Ch 20 LANDLOAD). **Note — Appendix B is *absent* from
  the bundled scan**, so twin/turboprop-only cases are closure-locked, not
  oracle-locked; the canonical per-module validation status is
  [`docs/20_theory/00_theory_sources.md` § Oracle status](../20_theory/00_theory_sources.md#oracle-status).
- **User's Guide** — *DOT/FAA/AR-96/46* (UDRI / P. Miedlar, March 1997; file
  `FAR23Loads_UserGuide.pdf`). The **operational** guide for a later FAA repackaging. Its
  **Table 2.2** is the authoritative module input→output map (adopted by the
  dependency table below), it gives the **FAR regs per module** (through
  Amendment 42), and it defines the two sample airplanes. Sections cited as "UG §N".

**Two counts, both correct — know which artifact you mean.** Reference 1
**Appendix C ships 22 QBasic programs**; the FAA User's Guide exposes **20 of them
as menu modules**. The two not on the FAA menu are utilities, but they are real
and in Appendix C, so the build targets all 22:
- **`BALLOADS.BAS`** (Appendix C p497) — a **verification utility**, not a
  pipeline stage. It recomputes the rational balanced-tail-load centers of
  pressure to verify the approximate `XTC`/`XTF` that **FLTLOADS** uses, and to
  demonstrate that the elevator load is not always opposite the stabilizer load
  (Ch 8 "Assumption", Ch 9). Run after FLTLOADS. The *pipeline* balancing loads
  live in FLTLOADS (approximate CP) and are refined rationally in **SELECT**.
- **`TAU.BAS`** (Appendix C p407; `TAU.EXE` in UG Table 2.1) — lift-curve-slope
  correction helper; folded into `airloads.py` (the `_tau` helper). Not a menu module.

## Module → User's Guide section map

| Module | UG § | Module | UG § |
|--------|------|--------|------|
| WTESTIMA | §3 | WINGINER | §15 |
| WTONECG | §4 | NETLOADS | §16 |
| WTENV | §5 | ENGLOADS | §17 |
| WINGGEOM | §6 | LANDLOAD | §18 |
| STRSPEED | §7 | LGFACTOR | §19 |
| MACHLIM | §8 | TAILDIST | §20 |
| AIRLOADS | §9 | TABLOADS | §21 |
| AIRLOAD4 | §10 | ONENGOUT | §22 |
| FLTLOADS | §11 | TAU | Ref 1 Ch 7 / App C; no UG § |
| SELECT | §12 | BALLOADS | Ref 1 Ch 8–9 / App C; no UG § |
| AILERON | §13 | — | — |
| FLAPLOAD | §14 | — | — |

## How to read this document

Each module has a fixed template:

- **FAR §** — the regulation(s) it satisfies (Part 23 Subpart C unless noted).
  The User's Guide gives the regs per module (through Amendment 42).
- **Source** — reference 1 chapter ("Ch N") + the original `.BAS`; the chapter
  text and the Appendix C source listing are the authoritative equation reference.
  Exact field lists and equations are transcribed *from these* when the module is
  built — they are intentionally not re-typed (and possibly garbled) from the
  scanned PDF here. UG § (see map above) is the operational cross-reference.
- **Reads** — fields it consumes from `Project` (its upstream dependencies).
- **Writes** — the result quantities / load-case CSV it produces.
- **Validation** — the reference 1 Appendix A and/or B figure(s) the test asserts
  (within the ±0.1% tolerance set by Decision 3). The two sample airplanes are the
  User's Guide data sets: `M2002576`/`WTENV36`-series (Appendix A, 6-place GA
  single) and the `BB*` files (Appendix B, twin turboprop).
- **Notes** — modeling assumptions, sign conventions, gotchas.

`Project` is the single shared input model (`sloads/models.py`). "Reads … from
`Project`" means those fields were produced by an upstream module or entered
directly; a module never recomputes another module's owned quantity.

**Limit vs. ultimate (ALL output is ULTIMATE).** The calc emits **LIMIT** loads (the
oracle figures the manual prints), but **every load that leaves the calc is
ULTIMATE** — no rendered table, text report, load-case CSV, or sbeam card may show a
bare limit load. Ultimate = limit × the per-case factor of safety
(`ConditionResult.safety_factor`, default **1.5 per 14 CFR 23.303**; the Part 25
equivalent is 25.303; see `reference/14CFR_factor_of_safety.md`). Scaling is applied
only at the render/export boundary, to force/moment/pressure quantities — never to
geometry, weights, inertias, or (dimensionless) load factors.

The `ULT` marker is **part of the load's units string** — force `lbs-ULT` (SI
`N-ULT`), moment `ft-lb-ULT` / `lb-in-ULT` (SI `Nm-ULT`), pressure `lb/in^2-ULT`
(`psi-ULT`) — and the load-case CSV carries the factor in an `SF` column. **Every
load case states its SF.** The factor is per-case so a future 14 CFR 23.302/25.302 /
Appendix K refinement can give a failure case a probability-interpolated value
(1.0–1.5); sudden engine stoppage is held at 1.5. A value already at ultimate (or an
inherently-limit value reported as-ultimate with no amplification) is **`ULT
SF=1.0`** — still ultimate output, not a limit load. **Scope:** this applies to
every *deliverable* (the `report.py` tables/text, the load-case CSV, the sbeam
export, the Review/Export pages); a per-module *analysis* page may instead show the
calc's LIMIT values when **explicitly marked `LIMIT`** (`flap_loads`, `tab_loads`,
`one_engine_out`, `balanced_tail_verification`). **A LIMIT *download* carries the
basis in-band (M4-15):** filename `*_LIMIT.csv` plus a `Basis` column (or
LIMIT-marked column headers) — the canonical station-row shapes
(`net_loads.wing_load_rows`, `body_loads.body_load_rows`) append `Basis = LIMIT`
to every row, and the Wing/Fuselage Loads pages pair the LIMIT file with the
sbeam bridge's ULTIMATE twin (`*_ULT.csv`, `SF` column).
`tests/test_ultimate_contract.py` scans the app's CSV downloads and enforces
this.

---

## Phase 1 — Mass properties

### WTESTIMA — Weight estimation
- **FAR §:** 23.23, 23.25 (weight limits); supports the loading basis for all of Subpart C.
- **Source:** Ch 2, `WTESTIMA.BAS`.
- **Reads:** primary geometry & mission inputs (gross weight target, useful-load items, fuel, `seats`/`crew`, baggage, component weight fractions). Pipeline head — mostly direct input. **Power single-source (Step M2-6):** the combined max-continuous power `max_continuous_hp` is derived from `sum(engines[].max_cont_hp)` (`resolve_max_continuous_hp`) unless `WeightEstimationInput.override_max_continuous_hp` is set (then the stored total is used; also the fallback when no engine carries a rating) — so the Weight & Mass "total power" field can no longer silently drift from the per-engine Engine Mount ratings, while the two rating concepts (per-engine vs combined-total, takeoff vs max-continuous) stay distinct.
- **Writes:** empty weight, max take-off weight, **operating empty weight (OEW = empty + crew×170)**, component weight breakdown & stations → `Project.weight`.
- **Validation:** Appendix A 6-place GA — empty weight / CG and component weights as printed (e.g. mid weight 2063 lb @ x=73.09; empty 1822 lb @ x=75.03).
- **Notes:** Empty/takeoff weight ratio `K = 0.62` with adjustments (UG Table 3.1: multiengine +0.01, liquid-cooled +0.01, super/turbocharged +0.01, turboprop −0.05, pressurized +0.02, one-seat −0.04); `W_TO = W_use/(1−K)`. Component weights as %-of-TO-weight (UG Table 3.2). 170 lb/seat. **Crew & OEW (Step E1 follow-up):** the `crew` count (default 1, 170 lb each) is carried in a derived **operating empty weight** line `OEW = empty + crew×170`; this is reporting-only — `WTO`/`useful`/`empty` (the Appendix-A oracles) are untouched, the crew weight already sits inside `useful` (seats×170), so OEW is not re-summed with the useful load. `crew` also feeds the FAR 23 seat-limit check (`passenger seats = occupants − crew`). Engine types: 4-cycle recip, 2-cycle recip, turbocharged, turboprop, liquid-cooled. FAR 23.25(b) minimum-weight rule (crew @ 170 lb + ½ hr fuel at max-continuous; turbojets 5% fuel capacity). **Feeds WTONECG *and* WTENV — they are parallel siblings off WTESTIMA, sharing one weight database; neither feeds the other.** As a UI convenience, `estimate_to_mass_items(inp)` expands the estimate's structure/powerplant/systems components (plus options/miscellaneous) into empty-weight `MassItem` rows — skipping the group totals and the propeller already inside "Engine installed" — to seed that shared database; the Weight Estimate page's "Seed Weight, CG & Inertia" button writes them to `Project.weight.items` with stations/inertias left at zero. The reference-fleet comparison (formerly overlaid on this page and Configuration & Layout) now lives on its own dedicated **Aircraft Comparison** page in the Export phase (`app/views/aircraft_comparison.py`, Phase F Step F2); it loads `app/data/reference_aircraft.csv` — nominal published specs for visual sanity-checking only, never read by any calc. **Concept mode (Step C0):** the `K=0.62` regression is GA-calibrated and out of band above 12,500 lb, so in concept mode (`Project.is_concept`) WTESTIMA is flagged as a sanity-only estimate and the design weight comes from the **direct-weight path** `WeightInput.direct_totals()` — MTOW/OEW/useful summed straight from the itemized `MassItem` database by kind.

### WTENV — Weight vs CG envelope
WTENV's structural-CG limits need `XLEMAC`/`MAC`, which `WINGGEOM` owns, so it
reads them from `Project.geometry`. Its Streamlit page renders the envelope as a
chart + tables.
- **FAR §:** 23.23 (load distribution), 23.25.
- **Source:** Ch 3, `WTENV.BAS`.
- **Reads:** `Project.weight` (component weights & stations), structural CG limits (fwd/aft gross, fwd-regardless), wing geometry (XLEMAC, MAC), fuselage station extent (optional `envelope.fuselage_nose_x`/`fuselage_tail_x` override, else the Step G1 fuselage outline).
- **Writes:** weight/CG envelope of all possible loadings; structural-limit envelope; ballast weight & station to meet each limit → `Project.weight.envelope`.
- **Validation:** Appendix A — structural-limit stations (X_aft=85.1, X_fwd=77.49, X_fwd-regardless=72.64 from XLEMAC=63.641, MAC=69.246) and ballast (e.g. aft-gross ballast 78 lb @ x≈103.7).
- **Notes:** `X(limit) = XLEMAC + (percent/100)·MAC`. Shares the WTONECG weight database; computes the minimum flight weight and the envelope of all discretionary loadings (UG §5). Output (envelope of useful loads + CG) **feeds FLTLOADS only** (UG Table 2.2). Supports multi-category certification (e.g. normal n=3.8 @ 3400 lb ≡ acrobatic n=6 @ 2153 lb). Has a graphics output (envelope diagram) — render as a Streamlit chart. **Step D5:** the chart additionally overlays `Project.weight.cg_cases` (the shared named loading scenarios the Weight/CG Grid & Payload Cases page owns) as read-only markers — `weight_envelope.envelope()`'s own math is unchanged; `loading_envelope_points()` exposes the forward-boundary vertices the chart plots. **Ballast reference selection (M1-7/M1-11):** each of the three ballast references is the heaviest forward-loading vertex still within that point's weight/station limit (aft-gross = heaviest loading ≤ gross; fwd-gross = heaviest at/forward of the fwd-gross station; fwd-regardless = heaviest ≤ the regardless weight). When no vertex qualifies, the reference already meets the target weight, the reference already sits at/aft of the aft-gross limit, or the moment-balance station falls **outside the fuselage extent** (e.g. forward of the nose datum on synthetic over-gross concept databases whose loadings all sit aft of the forward limit), the ballast row emits an explicit `"(none — <reason>)"` marker (0 lb) instead of vanishing or printing a nonphysical station.

### payload_cases — Weight/CG Grid & Payload Cases (Step D5; modern, no `.BAS`)
- **FAR §:** none (a shared-input page, not a FAR condition).
- **Source:** none — a GUI-only page (`module=None` in `sloads/workflow.py`, same treatment as `aero_coefficients`).
- **Reads:** `Project.weight.items` (must be non-empty).
- **Writes:** `Project.weight.cg_cases` — named `CgCase` rows (weight, xcg, zcg) entered once.
- **Notes:** exists to stop the CG-envelope chart (WTENV) and the flight-envelope balance (FLTLOADS) from carrying two independently-edited copies of the same loading scenarios (the Phase-D GUI assessment's finding #2, "no enforced single source of truth for shared inputs"). The Flight Envelope page reads this slice read-only and merges it into the calc-facing `FlightLoadsInput.cg_cases` (which SELECT/WINGINER/NETLOADS/BALLOADS keep reading unchanged — no calc module was touched by this move). Pre-Step-D5 project files carried the scenarios only under `flight_loads.cg_cases`; `io._legacy_cg_cases_from_flight_loads` migrates them into `weight.cg_cases` on load.

### WTONECG — Weight & inertia for one configuration
- **FAR §:** 23.23 (load-distribution limits) / 23.29 (empty weight & corresponding CG); provides masses & inertias for dynamic/gyroscopic conditions. (User's Guide §4.3 also ties the module to 23.25.)
- **Source:** Ch 4, `WTONECG.BAS`.
- **Reads:** `Project.weight` items (component weights + x,y,z locations). Computed at the **4 CG locations** of the structural-limits diagram (aft gross, fwd gross, most-fwd reduced, minimum weight) — ×2 (gear up/down) for retractable gear, so up to 8 loadings, not one.
- **Writes:** total weight, CG (x,y,z), and mass moments of inertia (Ixx, Iyy, Izz, products), output in **both slug-ft² and lb-in²** → `Project.mass`.
- **Validation:** Appendix A/B — CG and inertia for the example loadings.
- **Notes:** Per UG Table 2.2 / §4.5 the outputs split: **weight & CG → FLTLOADS, LANDLOAD**; **inertia → SELECT, ONENGOUT** (maneuver/gust balancing and unbalanced landing). Component inertia = transfer (parallel-axis) of each item about the airplane CG. Conceptually the same machinery as the engine/rotor inertia in `engloads`, at airplane scale — but ENGLOADS does **not** read `Project.mass` (it is standalone, UG Table 2.2).
- **Implementation notes:** modules stay pure (`run → ModuleResult`); the persisted `Project.mass` slice (added at Step C6 with SELECT/LANDLOAD) holds the weight/CG/inertia results. `WTESTIMA`/`WTONECG` results are a **property table**, so they render via `report.results_to_rows` / `module_text_report` (not the engine-specific `load_cases_to_rows`). The UI offers an SI **output** toggle: a weight is pounds-*mass* and converts to kg, distinguished from a pounds-*force* load (→ N) by `LoadValue.quantity="mass"`; inertia (slug-ft²/lb-in²) → kg·m², CG positions in→mm, angle (deg) unchanged. Inputs are entered in Imperial. See `units.py`. **`Project.weight` merge-write rule (fixed Step D4.7; extended Step D5):** `WeightInput` bundles `estimation`/`items`/`envelope`/`cg_cases`; every page that owns only one of the four (Weight Estimate → `estimation`, Weight/CG/Inertia → `items`, `configuration_layout`'s station-seed button → `items`, Weight/CG Grid & Payload Cases → `cg_cases`) must reconstruct `WeightInput` with the *other three* read from the current `project.weight` and passed through unchanged, never omitted — an omitted field silently resets to its dataclass default (`None`/`[]`) on save. Only `weight_envelope.py` (the `envelope` owner) sets all four explicitly by design.

---

## Phase 2 — Geometry & speeds

### WINGGEOM — Aerodynamic & surface geometry
- **FAR §:** geometry basis for 23.301+ airloads.
- **Source:** Ch 5, `WINGGEOM.BAS`. Largest module — runs once per surface.
- **Reads:** planform inputs per surface (root/tip chord, span, sweep, dihedral, incidence, station offsets) for: wing, horizontal & vertical tail, aileron, flap, elevator, rudder, tabs (the original keeps a `*GEOM.INP/.OUT` per surface).
- **Writes:** derived geometry per surface — MAC, XLEMAC, area, aspect ratio, spanwise station table, control-surface hinge geometry → `Project.geometry.surfaces[<surface>]`.
- **Validation:** Appendix A/B — MAC=69.246, XLEMAC=63.641 (wing) and the per-surface area/MAC tables.
- **Notes:** Many downstream modules read `geometry.surfaces`. Model surfaces as a list keyed by surface name so one calc serves all. **Step G1:** WINGGEOM (the `wing_geometry` module) no longer has its own page — it is folded onto the single **Geometry** page (`configuration_layout.py`, `FOLDED_MODULES`), whose "Lifting-surface planforms" section is the surface polyline editor. Has graphics: the top-view planform outline per surface (`sloads.modules.wing_geometry.surface_top_outline`, a presentation-only helper — no new `ConditionResult`), reused by the Geometry page's three-view for the wing outline.

### STRSPEED — Design speeds & maneuver load factors
- **FAR §:** 23.335 (design airspeeds), 23.337 (limit maneuver load factors), 23.333.
- **Source:** Ch 6, `STRSPEED.BAS`.
- **Reads:** `Project.weight` (W, W/S), `Project.geometry` (wing area), **`Project.aero_coeffs.clmax_clean`/`clmax_flap`** (the maximum lift coefficients — the single stall-speed source; VS/VSF = `√(295·(W/S)/CLmax)` at the design weight, M1-1b, User's Guide p7-5, so STRSPEED `requires` aero_coeffs), category (normal/utility/acrobatic, or **concept `"C"`** — see Notes), chosen speeds, **`occupants`** (Step E1; total souls on board — not used by the load calc, drives the FAR 23 applicability check), and the **operational-limitation targets** (Step M2-10: `no_yellow_arc`, `target_vne`/`vno`/`vmo`/`mmo`/`vfe` — advisory only, see Notes).
- **Writes:** minimum-required & chosen V_A, V_C, V_D, V_S, gust speeds; limit maneuver load factors n1/n2 (pos/neg) → `Project.speeds`. **Advisory (no persisted result):** the preliminary Subpart-G operating-limitation placards (VNE/VNO/MNE + VMO/MMO + VFE) and any operational-target feasibility (Step M2-10) — a read-only advisory rendered on the Design Speeds page, never a load deliverable.
- **Validation:** Appendix A/B printed design-speed table and load factors (normal n=+3.8).
- **Notes:** Category drives the maneuver load-factor formula (23.337: n=2.1+24000/(W+10000), capped 3.8/utility 4.4/acrobatic 6.0; negative −0.4× positive for normal/utility, −0.5× for acrobatic — UG Table 7.1). **Dive speed VD (23.335(b), M1-1):** enforced as `VD ≥ max(K_d·VCmin, 1.25·VC)` — **both** minimums, with the K_d term applied to the *minimum* cruise VCmin (STRSPEED.BAS `V2DMIN=K2·V1CMIN`). On the no-chosen-speeds path K_d·VCmin governs (Appendix A p155, Cat N: 198.53 kt; `test_vd_floor_no_chosen_speeds`); the worked chosen-speeds case (p156, VD 212.5) clears both floors. Concept mode (Cat C) keeps only the absolute 1.25·VC floor and reports K_d·VCmin as advisory. **Concept mode (`category="C"`, Step C0)** bypasses the GA-only 23.337 formula and cap entirely: it requires explicit `chosen_n`/`chosen_nneg` and uses them verbatim (no FAR floor), so >12,500 lb concepts are not forced to a meaningless GA limit; the VC(min)/VD(min) coefficients become out-of-band advisories. `Project.is_concept` is the single concept read-point. **FAR 23 applicability (Step E1):** the pure `sloads.far23_applicability(project)` helper (`sloads/applicability.py`) compares the design gross weight (`speeds.weight_lb`, else the Weight DB total) and passenger-seat count (`occupants − crew`, where `occupants` seeds from the Weight Estimate seat count when unset and `crew` is the user-set `WeightEstimationInput.crew`, default 1) against the non-commuter FAR 23 tier (12,500 lb / 9 seats; limits in `constants.py`, commuter tier dormant) and returns structured `Exceedance`s — none on GA inputs. `app/components.render_applicability_banner` surfaces them on the Dashboard + definition pages with a non-blocking "Switch to Concept" action that seeds `chosen_n`/`chosen_nneg` from the computed 23.337 factors. STRSPEED also computes Mach limits at altitude (`T = 59 − 0.003566·h`; `a = 29.02·(T+459.4)^0.5`), so it overlaps MACHLIM — keep the shared atmosphere/Mach helper in one place. Feeds MACHLIM, FLTLOADS, AILERON, FLAPLOAD (UG Table 2.2). **Operating-limitation implications (Step M2-10, advisory):** the design speeds bound the eventual Subpart-G operating limitations; `operational_implications`/`operational_placards` derive the preliminary placards — **both families** shown (recip yellow-arc: VNE=0.9·VD, VNO=min(VC, 0.89·VNE), MNE=0.9·MD; turbine/no-yellow-arc: VMO=VC, MMO=MC; common VFE=VF) per 14 CFR 23.1505/23.1511 and Ref 1 p47 (`reference/14CFR_operating_limitations.md`). Optional operational **targets** invert the ladder into required design minima (`operational_target_checks`: VNE⇒VD≥VNE/0.9; VNO⇒VC≥VNO and VD≥VNO/0.89/0.9; VMO⇒VC≥VMO; MMO⇒MD≥MMO+0.05 per 23.335(b)(4)(ii); VFE⇒VF≥VFE) and **warn-only** on infeasibility — never mutating a design speed or load. Infeasible targets also surface on the dashboard via `validation._check_operational_targets` (`operational_target_infeasible`, page `structural_speeds`). Display/validation only; the FAR23 loads path is unchanged. **GUI read-through (Step D4.4):** `app/views/structural_speeds.py` reads the design weight from `Project.weight.direct_totals()[0]` (the Weight DB total) when items are present, read-only with an "Override design weight" checkbox, instead of asking for it a second time; likewise wing area from `Project.geometry`'s wing surface (pre-existing `has_wing` gating). When neither upstream slice is populated the page shows an info message pointing at the Airplane-section page that owns it, rather than falling back to an Appendix-A-shaped literal default. `app/views/weight_envelope.py` (WTENV) does the same read-through for its `gross` weight (it already requires a Weight DB to render at all, so the total is always available; only the override path differs).

### MACHLIM — Mach limit lines
- **FAR §:** 23.335(b) high-speed limit; compressibility.
- **Source:** Ch 6, `MACHLIM.BAS`.
- **Reads:** `Project.speeds`, altitude range, limiting Mach.
- **Writes:** Mach-limited speed vs altitude (the V-M limit line) → `Project.speeds.mach_limit`.
- **Validation:** Appendix B (high-altitude twin) Mach-limit table.
- **Notes:** Only material for high-performance/high-altitude airplanes (Appendix B). Graphics: V vs altitude limit line. **Step E7 (Speed–Altitude Envelope consolidation):** the page is retitled **Speed–Altitude Envelope**. MC, MD and the shoulder altitude are now READ from `Project.speeds` (via `structural_speeds.design_speed_values`) instead of re-entered — only the max operating altitude and the increment remain as page inputs (removing the Step D5 duplicate MC/MD/shoulder entry). The chart becomes a transport-category-style speed–altitude flight-limits diagram: **altitude on y**, a **KEAS/KCAS/KTAS** selectable x-axis (via the new `constants.convert_airspeed`), a thin constant-Mach fan, and the design-speed boundary drawn EAS-limited (constant) below the shoulder and Mach-limited (V=M·a·√σ) above it, so VC/MC and VD/MD kink at the shoulder like a placard chart. All chart speeds are design *limit* speeds (a speed boundary, not a load deliverable — the ULT rule does not apply). Display-only + one new pure helper; no change to `mach_limit_lines`' calc.

---

## Phase 3 — Aero coefficients & flight envelope

### TAU — Lift-curve-slope correction (built, folded into `airloads.py`)
- **FAR §:** supports 23.301 airload distribution.
- **Source:** Ch 7, `TAU.BAS` (curve-fit p407).
- **Reads:** wing aspect ratio (from the planform) + `AeroSurfaceInput.taper_ratio`/`tip_ratio`.
- **Writes:** τ correction factor for the wing lift-curve slope (the `_tau` helper in `airloads.py`; the per-surface value is also overridable via `AeroSurfaceInput.tau`).
- **Notes:** Not a separate module — implemented as the `_tau` quartic curve-fit (in taper ratio, interpolated by tip ratio per ANC(1) 1938) inside `airloads.py`, exactly as the original folds `TAU.EXE` into AIRLOADS.

### AIRLOADS — Spanwise lift distribution (built; AIRLOAD4 swept branch built in C7)
- **FAR §:** 23.301 (loads), 23.321+ (flight loads), 23.347+ asymmetric.
- **Source:** Ch 7, `AIRLOADS.BAS` (low speed); Ch 12, `AIRLOAD4.BAS` (sweepback, high Mach) — both in `modules/airloads.py`, the swept branch auto-selected by `use_airload4` when 25%-chord sweep > 15° or design Mach > 0.4. **Mach threshold (M1-8):** Ref 1 (Ch 12) says *"Mach >.4"*, the User's Guide §9.1/§10.1 says *"0.5"*; we keep Ref 1's conservative **0.4** (no `.BAS` oracle exists — selection was an operator choice). See `docs/20_theory/00_theory_sources.md` (AIRLOAD4 row).
- **Module:** `modules/airloads.py` (registers `"airloads"`).
- **Reads:** `Project.geometry` (wing planform polylines & strip count) + `Project.aero` (`AeroSurfaceInput`: section slope `mo`, taper/tip ratio for TAU, spanwise `twist` table, `target_cl`, and the C7 `sweep_deg` / `design_mach` AIRLOAD4 triggers).
- **Writes:** the spanwise additive + basic + combined `c·cl` distribution (the `SpanwiseTable`) returned as a `ModuleResult`, carried on the persisted `Project.aero.spanwise` field.
- **Validation:** Appendix A spanwise tables (additive `CC(LA1)`/`C(LA1)`, basic `Awo`/`CC(lb)`/`Clb`, p161-162) within ±0.1%; concept closure (integrated `∫c·cl dy` recovers the target CL). AIRLOAD4: reduction invariant (sweep 0 / low Mach ≡ AIRLOADS exactly) + swept-CL closure `recovered_cl ≈ target_cl` for Λ≠0 (**M1-3**: the `COL20 = COL19/CLCOL19` renormalization applied to the *combined operating* distribution — sweeps twist too — so no lift is lost; deliverable path re-applies it per condition at that condition's CL) + a **listing-traceable** COL18/COL19/COL20 per-station reconstruction; the printed Appendix B swept spanwise oracle is deferred to a mini-step (no legible swept fixture).
- **Notes:** Schrenk additional-lift method (average of planform-chord and elliptic distributions). Per UG Table 2.2 AIRLOADS↔SELECT is **iterative** (SELECT names the critical conditions, AIRLOADS computes airloads at them); the shared model lets a module both read and write the critical-load set (wired with SELECT). The basic-distribution cosine fairing across a flap/aileron discontinuity (p47) is deferred (deflected-flap case only).

### FLTLOADS — Flight envelope (V-n) **+ balancing tail loads**
- **FAR §:** 23.333 (flight envelope), 23.337, 23.341 (gust), 23.345 (flaps), 23.421+ (balancing/horizontal tail loads), 23.423.
- **Source:** Ch 8, `FLTLOADS.BAS`. UG Table 2.1: *"Balancing calculations for flight envelope."*
- **Reads:** `Project.speeds` (STRSPEED — VA/VC/VD/VF, MC/MD and the limit load factors via the shared `_maneuver_load_factors`); **`Project.flight_loads`** (`FlightLoadsInput`) for the balance geometry scalars `mac`/`wing_area_sqft`/`xw`/`zw`/`xtc`/`xtf`, the reference Mach `mn`, the altitude list and the four weight-CG cases (`CgCase`) — **`mac`/`wing_area_sqft`/`xw`/`zw` are derived from `Project.geometry` (Step M2-6), not stored**: MAC/S/XW from the WINGGEOM wing surface (`XW = XLEMAC + 0.25·MAC`), ZW from the parametric wing (`root_waterline_z + Y_MAC·tan(dihedral)`), filled by `sloads.derived_geometry.sync_geometry_derived` at calc entry (`build_envelope`), GUI read-only; `xtc`/`xtf`/`mn`/altitudes stay this page's own input; and **`Project.aero_coeffs`** (`AeroCoefficientsInput`, Step D4.1) for the airplane-*less-tail* aero-coefficient polynomials (`AeroCoeffSet`: CL(α), CD(CL), CM(α) + stall CLs) — `.cruise` (flaps up, balanced at every altitude) and, when present, `.flaps_down` (balanced at sea level only, FLTLOADS.BAS line 3000). `Project.aero_coeffs` is the single owner of these coefficient sets; the Airplane-section **Aerodynamic Data** page (workflow key `aero_coefficients`,
retitled in the Airplane-phase GUI usability pass — the per-surface spanwise
Schrenk aero, `Project.aero`, stays on the Wing Loads page next to the load
distribution it drives, cross-linked from both pages) writes it (`flight_envelope` only reads it) — before Step D4.1 they were carried inline as `FlightLoadsInput.configurations`, a list of `AeroCoeffSet` keyed by `flaps_down`; older project files migrate automatically (`io._legacy_aero_coeffs_from_flight_loads`). **As built (C2):** the aero polynomials come from the Ch 7 aero-coefficients program and are entered as input (AIRLOADS/C1 does not yet emit them); the CG cases are entered explicitly (seeding them from `Project.weight.envelope`/WTENV is a later refinement), so the original data-flow's `Project.mass` read is not needed for the balance. **Step D5:** the four weight-CG cases are no longer edited on this page — they are the shared `Project.weight.cg_cases` the **Weight/CG Grid & Payload Cases** page owns; the Flight Envelope page reads that slice read-only and merges it (unchanged) into `FlightLoadsInput.cg_cases`, which `build_envelope`/SELECT/WINGINER/NETLOADS/BALLOADS keep reading exactly as before (no calc module changed). The altitude list, previously a single-altitude widget touching only `altitudes_ft[0]`, is now a fully-editable list on this page (multi-altitude V-n); the calc loop (`for alt in fl.altitudes_ft`) already supported more than one entry since Step C2. **Step G4:** when `aero_coeffs.fuselage_moment` is enabled, `build_envelope` adds its Munk `dCm/dα` increment (ΔM1) to each config's M1 on a local copy (stored coefficients untouched, Glauert factor applies automatically); off by default so the GA/twin oracles are bit-for-bit unchanged. The estimate is produced by `sloads.fuselage_moment.estimate` from `Project.geometry.fuselage` + this page's wing S/MAC and shown/overridden on the Aerodynamic Data page.
- **Writes:** the full balanced V-n matrix (one `VnPoint` per condition × CG × altitude: V, NZ, α, G, CL, M(W+F), LZW, **LT**, DX) and the balancing tail load per point → **`Project.envelope`** (`EnvelopeResult.vn` + `.tail_balance`), consumed by SELECT. The pure entry point is `flight_envelope.build_envelope(project) → EnvelopeResult`; `run(project)` returns the per-point `ModuleResult`.
- **Validation:** Appendix A "V-n Data" p179-180 — the cruise balanced matrix per CG case. The AoA balance converges NZ only to ±0.005 (FLTLOADS.BAS line 4130), so low-load-factor quantities carry ~0.5% noise; LT and the corner speeds/load factors match tightly.
- **Notes:** Graphics: the V-n diagram, plus (Step G5) a **Trim & Stability** tab — `flight_envelope.trim_sweep()` re-runs the balance at ~15 interpolated CG stations for the BAL A/C/D 1-g trim loads (balancing tail load vs CG), and a static-margin sweep (`SM = NP − CG`, %MAC) from the Configuration tail-volume neutral point. It adds no load equations (a swept station coinciding with a CG case reproduces `build_envelope`'s BAL load exactly), and its tail loads are shown **LIMIT** (marked; the ULTIMATE deliverables are the SELECT/Results-Review/export loads). Faithful port of FLTLOADS.BAS subroutine **3900** (iterate AoA to the required load factor, then dynamic pressure to the Mach-adjusted stall line; Glauert compressibility `G/Gmn`; CLmax-vs-Mach curve) and **4864** (gust load factor, FAR 23.341). Balancing tail load `LT = [M(W+F) + LZ·(Xcg−Xw) − DX·(Zcg−Zw)]/(XT−Xcg)` with *approximate* tail CP (`XTC`≈5% tail MAC flaps-up, `XTF`≈25% flaps-down; Ch 8 "Assumption"). Covers the **cruise** maneuver+gust corner set (20 conditions, lines 1000-1594) plus the flapped LANDING/ENROUTE corner set (subr 3000; added with SELECT, C6); both share the balance engine. In the flapped set the `BAL 1.4VSF` point balances at **1.4× the 1-g flaps-down stall (`STALL 1GL`) speed** — FLTLOADS.BAS p300–302 saves the STALL 1GL speed — reproducing Appendix A p181 LANDING CG5 case 89 (V 83.6 kt / LT −430 lb; M1-2). Earlier code balanced at 1.4× `STALL 2G`, ~2.2× too large a tail load (review T2). SELECT refines the CP rationally; `BALLOADS.BAS` independently verifies it. Produces the candidate conditions SELECT then prunes; feeds SELECT and WINGINER (UG Table 2.2). FLTLOADS uses its own speed-of-sound constant (518.688 vs the shared `standard_atmosphere`'s 518.4), replicated locally for oracle fidelity.

### SELECT — Critical load selection
`modules/select.py` (registers `"select"`). Oracle-locked against the Appendix A
loads report (±0.1% + FLTLOADS' ~0.5% V-n noise): (1) the **wing** search
(PHAA/PLAA/PMAA/NMAA + accelerated-roll + steady-roll TORS), (2) the
**horizontal-tail** loads — balancing (23.421), unchecked/checked maneuver
(23.423), gust (23.425(a)(1)/(2)) and unsymmetrical (23.427(a)), flaps retracted
**and extended** (the exact SELECT.BAS subr-10000 large-deflection factor
`EF(δ,Se/St)`), (3) the **vertical-tail** loads (23.441(a)(1)/(2)/(3), 23.443(b)),
and (4) the **fuselage** critical conditions (23.301/23.331). The fuselage *net
distribution* (Ch 15) lives in `modules/body_loads.py`. Inputs come from
`Project.tail_loads`/`vtail_loads`/`select_input`/`fuselage_mass`. **M2R-5:** the
`select_input` search fields — `full_down_aileron_deg` / `basic_airfoil_cm` (the
23.349(b) steady-roll wing-torsion drivers) and `wing_weight_lb` (the critical
fuselage's reacted wing weight, 0 → 0.09·MTOW) — are editable on the Critical Loads
tab (previously project-JSON only, defaulting silently). **Known limits**
(see backlog): the flaps-extended SELECT→TAILDIST path is closure-validated (the
landing-config aero polynomials are now in the `flight_envelope` test fixture and
oracle-match FLTLOADS' `BAL 1.4VSF` at Appendix A p181 — M1-2; wiring the printed
chordwise cases 81/106/88/108 through SELECT with the CG5–7 loadings remains L-2); the
v-tail rudder `EFV≈1.0` is an input (illegible chart); SELECT's checked-maneuver
`Iyy` / v-tail `IZZ` use the Ch 9 approximations (which match the oracle) rather
than the persisted `Project.mass`. **Approved oracle deviation (M1-4, 2026-07-20):**
the 23.427(a) unsymmetrical search includes the **unchecked** maneuvers, per
`SELECT.BAS` lines 6070–6175 and 23.427(a)'s "23.421 **through** 23.425" scope; the
Appendix A sample-output value (−1111.8, gust-governed) is a stale printout from a
superseded revision that excluded them, so the GA6 unsymmetrical is −1204.7 (DN
unchecked governs). See `reference/23_427_unsymmetrical_candidate_set.md` and the
approved-corrections register [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md).
- **FAR §:** 23.301 critical-load determination across the envelope.
- **Source:** Ch 9, `SELECT.BAS`.
- **Reads:** `Project.mass` (WTONECG inertia), `Project.geometry` (WINGGEOM), `Project.envelope.vn` (FLTLOADS); plus AIRLOADS/AIRLOAD4 spanwise airloads. Run once per component (wing, fuselage, htail, vtail).
- **Writes:** the governing (critical) flight-load set per surface → `Project.envelope.critical`. Per Ch 9 this is **much more than selection** — SELECT *computes* the rational critical loads: wing loads (PHAA/PMAA/PLAA/NMAA, accelerated & steady roll), rational + balancing + maneuvering + up/down-gust + unsymmetrical **horizontal** tail loads, **vertical** tail loads (23.441/23.443), and **fuselage** loads (23.301/23.331/23.351/23.471; Ch 9 + Ch 15 net fuselage).
- **Validation:** Appendix A/B — the selected critical points (`SELWGLDS/SELHTLDS/SELVTLDS/SELFSLDS`).
- **Notes:** Central junction. Reads V-n data from FLTLOADS + geometry (WINGGEOM) + inertia (WTONECG). Per UG Table 2.2 it feeds **AIRLOADS, AIRLOAD4 (iterative — see AIRLOADS), WINGINER, TAILDIST**. NETLOADS/component modules consume `critical` indirectly via those. **Step D5:** `CriticalLoadSet.selected_case_ids` is an **opt-out GUI selection** — the Critical Loads page persists which computed conditions the engineer keeps for the deliverable (empty = no filter, every condition kept, the default and the whole behavior for older projects); `CriticalLoadSet.selected()` applies it. Only the **Results Review** page's display reads `.selected()` — every structural calc module (WINGINER/NETLOADS, `body_loads`, the sbeam export bridge) deliberately keeps reading `.conditions` unfiltered, so the selection can never silently drop load cases from a deliverable's structural sizing, only from the GUI summary. (D8.3 is expected to wire the export bundle to this same selection — not yet done.) **M2-4:** the governing-loads tables on **both** the **Results Review** headline and the Flight Envelope **Critical Loads** tab render through one shared `report.governing_loads_table(conditions, system, sf)` — load columns are ULTIMATE (scaled by SF, `-ULT` marker + `SF` column), dimensionless/speed columns (n, CL, V) unscaled and unmarked, absent cells `"—"`; the flat SF 1.5 (14 CFR 23.303) is applied at the render boundary since `CriticalCondition` has no per-case factor yet (deferred to M4-8).

### BALLOADS — Rational balanced-tail-load verification (utility) — Step C11
- **FAR §:** 23.421 (balancing loads); supports the 23.331 rational-balancing requirement.
- **Source:** Ch 8–9 (method), `BALLOADS.BAS` (Appendix C p497). **Not a FAA menu module.** Module `sloads/modules/balloads.py`, registered `"balloads"`.
- **Reads:** `Project.flight_loads` (FLTLOADS V-n / geometry, incl. the approximate `xtc`/`xtf`) and `Project.tail_loads` (h-tail geometry/aero); run after FLTLOADS/SELECT.
- **Writes:** a verification **report only** (no schema/pipeline output). Per flaps-retracted V-n condition: rational `LT25` (cp 25%), `LT50` (cp 50%), elevator deflection & elevator load, total `LT`, rational CP (% tail MAC) and its fuselage station `XT`, compared to FLTLOADS' approximate `XTC`. Worked hand-calc: 6-place case 202 → `LT = 519.845 lb`.
- **Validation:** Ch 9 case-202 hand-calc (`LT 519.845`, LT25 +907.62, LT50 −387.78, δ −5.39°, CP 6.35%); rational up/down loads equal SELECT's `BAL UP/DN RETRACTED` exactly (BALLOADS **reuses** `select.htail_balance`).
- **Notes:** Optional verification/teaching tool, off the main pipeline; demonstrates the elevator load is **not** always opposite the stabilizer load. Reuses SELECT's oracle-locked balance routine (no re-derivation) and adds the rational-vs-approximate CP cross-check.

---

## Phase 4 — Component loads

### AIRLOADS — air-load distribution (load option, Step C3 extension)
- **Source:** Ch 12, `AIRLOADS.BAS` subroutine 4500 (lines 4600-5060).
- **Reads:** the C1 Schrenk section-lift distribution (`schrenk_distribution`), the operating wing `CL` and speed for a condition, and the section **profile-drag** (`AeroSurfaceInput.profile_drag`, CDO) and **pitching-moment** (`section_cm`, CM) tables added in C3.
- **Writes:** the air-load shear/bending/torsion station table along the 25% chord (a `WingLoadResult`), consumed by NETLOADS. Exposed as `airloads.air_load_distribution(geom, aero, cl, v, wrp, dihedral)`.
- **Validation:** Appendix A "Airloads for Case 22 PHAA" p206 (CL 1.52, V 117.4: root SZ +6470, MXX +516955, MYY -79003, MZZ -91283) — matches to ±0.1% (the `tau=0.05` override reproduces the manual wing slope; drag is induced `cl·ai/57.3` + profile CDO).

### WINGINER — Wing inertia loads
- **FAR §:** 23.301(b)/(d) inertia relief.
- **Source:** Ch 13, `WINGINER.BAS`.
- **Reads:** the **`Project.wing_mass`** input slice (`WingMassInput`): outboard panel weight, tip/root area-density ratio, inboard rib butt line, wing-reference-plane waterline + dihedral (**`wrp_waterline`/`dihedral_deg` are derived from the parametric wing on `Project.geometry`, Step M2-6 — not stored, GUI read-only**), concentrated wing masses, and the critical `WingLoadCase` list. The per-case `Nz`/`Nx` come straight from the FLTLOADS `envelope.vn` point (`Nz = −NZ`, `Nx = −DX/W`) when not given explicitly; plus `Project.geometry.<surface>`.
- **Writes:** the spanwise wing inertia distribution per case → **`Project.loads.wing_inertia`** (one `WingLoadResult` of `WingStationLoad` each). Pure entry `wing_inertia.build_wing_inertia(project)`.
- **Validation:** Appendix A "Wing Inertia Loads" p217-221 — root/tip density 2.213/2.102 lb/ft²; unit vertical/drag/roll and the combined case 138 (Nz −2.54 Nx −0.1318: root Mxx −41041, Myy +11161).
- **Notes:** The panel mass is a linearly-tapered area density iterated to the entered panel weight; strips inboard of the rib carry no panel mass; concentrated weights add spanwise steps to the shears/moments. Subtracted from the air load in NETLOADS.

### NETLOADS — Net wing loads
- **FAR §:** 23.301(b) (net = air + inertia in equilibrium).
- **Source:** Ch 14, `NETLOADS.BAS`.
- **Reads:** `Project.wing_mass`, `Project.geometry.<surface>`, `Project.aero.<surface>` (and `Project.envelope.vn` for the per-case CL/V/Nz/Nx). Combines the AIRLOADS air-load distribution and the WINGINER inertia distribution.
- **Writes:** the net spanwise shear, bending moment and torsion along the 25% chord → **`Project.loads.wing_net`** (+ the air/inertia distributions in `Project.loads`) + a one-row-per-station CSV (`net_loads.wing_load_rows`). Pure entry `net_loads.build_net_loads(project)`.
- **Validation:** Appendix A "Net Loads, Case 22 PHAA" p222 (root Sz +5837, Mxx +455555, Myy -60940, Mzz -81483) — exact algebraic sum of the air (p206) and inertia distributions.
- **Notes:** A primary structural deliverable (root shear/BM/torsion), wing only, full fidelity (all of Fx/Fz/Sx/Sz/Mxx/Myy/Mzz). SELECT selects the governing cases; NETLOADS also accepts them supplied directly as `WingLoadCase`s referencing the V-n matrix.

### AILERON — Aileron loads (built, Step C8)
- **FAR §:** 23.349 (rolling), 23.455 (aileron), CAM 3.222.
- **Source:** Ch 16, `AILERON.BAS`.
- **Reads:** `Project.speeds` (STRSPEED VA/VC/VD via `design_speed_values`, the only upstream input per UG Table 2.2), `Project.aileron_loads` (`AileronLoadsInput`: up/down deflection, area fwd/aft of hinge).
- **Writes:** critical up/down aileron loads + forward-of-hinge pressures → `ConditionResult`; `ControlSurfaceLoadResult` (simplified chordwise profile) for `Project.loads.control_surface` + the sbeam control-surface bridge.
- **Validation:** Appendix A "Critical Aileron Loads" p200 (down 271.44 / up −180.96 lb @170 kt; psi +0.484 / −0.323) within ±0.1% — `tests/test_aileron.py`.
- **Notes:** Deflected (unsymmetrical) conditions only; symmetrical undeflected is never critical (Ref 1 Ch 16). The pure-function oracle uses the manual's entered VA=121; the pipeline's computed VA≈121.3 shifts the load ~0.3% (tested at 0.4%).

### FLAPLOAD — Flap loads (built, Step C8)
- **FAR §:** 23.345 (flaps), 23.457 (flap hinge / slipstream).
- **Source:** Ch 17, `FLAPLOAD.BAS`.
- **Reads:** `Project.speeds` (STRSPEED VS/VSF/VF + design weight), `Project.geometry` wing area, `Project.engines[0]` (MAXHP/prop diameter for the slipstream — MAXHP is **takeoff power** per FAR 23.457(b): `takeoff_hp`, falling back to `max_cont_hp` only when unset), `Project.flap_loads` (`FlapLoadsInput`: gust factor, flap area, deflection, chord ratio, nacelle frontal area, engine butt line).
- **Writes:** the four-condition flap-CL/load envelope, critical load, LE pressure, slipstream band/factor, head-on-gust combined load → `ConditionResult`; `ControlSurfaceLoadResult` (gust-combined envelope) for the loads slice + sbeam bridge.
- **Validation:** Appendix A "Critical Flap Loads" p201 (CLf 1.7046/1.7046/1.5593/1.5476; critical 629 lb; LE 0.545 psi; slipstream ×1.407, BL 22.828…113.172; gust ×1.301; combined 819 lb) within ±0.1% — `tests/test_flap.py`.
- **Notes:** Slipstream is the momentum-theory sub 500 (iterate `U1` to absorb 0.85·MAXHP); computed only when engine power is present. Knots→ft/s uses the suite's `1.15·88/60` factor (`constants.KT_TO_FPS_SUITE`) to reproduce the slipstream geometry.

### TABLOADS — Tab loads (built, Step C8)
- **FAR §:** 23.409 / CAM 3.224 (control-surface tabs).
- **Source:** Ch 18, `TABLOADS.BAS`.
- **Reads:** `Project.speeds` (VC), `Project.tab_loads` (`TabLoadsInput.tabs`, each a `TabSpec`: host surface, tab MAC, area sq ft, station, host-airfoil chord at the tab MAC, deflection).
- **Writes:** per-tab chord ratio E, tab load, LE/TE pressures → one `ConditionResult` per tab; `ControlSurfaceLoadResult` (trapezoid LE = 2× TE) for the loads slice + sbeam bridge.
- **Validation:** Appendix A "Tab Loads" p202 (h-tail tab: E 0.17735, LTAB 84.62 lb, LE 0.4992 / TE 0.2496) within ±0.1% — `tests/test_tab.py`.
- **Notes:** Full deflection at VC (the shoulder point); host-surface CL lift on the tab neglected (chord ratio ~0.12). `TabSpec.area_sqft` is the tab area in **square feet** (canonical display unit since Phase G0, schema v24; older files with the legacy `area_sqin` key migrate `/144`). The calc restores the original program's square inches internally (`STAB = area_sqft × 144`) so `LTAB = M·δ·Q·STAB/144` is unchanged.

### TAILDIST — Chordwise tail load distribution (built, Step C7)
- **FAR §:** 23.421+ tail loads, chordwise distribution.
- **Source:** Ch 10, `TAILDIST.BAS` (subroutine 3000).
- **Module:** `modules/taildist.py` (registers `"taildist"`).
- **Reads:** `Project.envelope.critical` (SELECT — each h-tail/v-tail `CriticalCondition` now carries the rational `lt25`/`lt50` split), plus the chordwise geometry on `Project.tail_loads` (`htail_semispan_in` + the elevator areas) and `Project.vtail_loads` (`vtail_span_in` + the rudder areas).
- **Writes:** the five-station chordwise net pressure profile per critical h-tail / v-tail condition (`TailChordResult` on `Project.loads.tail_chordwise`) → text report + CSV + sbeam FORCE export (`sbeam_bridge.tail_*`).
- **Validation:** Appendix A "Chordwise Distribution of Tail Loads" — 13 horizontal (p237) + 4 vertical (p245) conditions' `PSI(X1..X5)` within ±0.1%. The four flaps-extended horizontal rows depend on the deferred flapped V-n landing aero (the pure-`chordwise_pressures` oracle test covers all 13 directly).
- **Notes:** Net chordwise load = additive (angle-of-attack, 4×avg at LE → avg at 25% chord → 0 at TE) + camber (trapezoid symmetric about 50% chord). Working in the suite's full both-sides areas folds the program's half-area / both-sides-load factors of two into the unified `LT/S` form. Replaces the arbitrary FAR Appendix B figures (pre-Amendment 42). Each distribution **carries the governing condition's citation** — `TailChordResult.far_reference` is copied verbatim from the source SELECT `CriticalCondition` (23.421 balancing, 23.423 maneuver, 23.425 gust, 23.427 unsymmetrical h-tail; 23.441/23.443 v-tail) rather than a single hardcoded `23.421`.

### ENGLOADS — Engine mount loads ✅ DONE
- **FAR §:** 23.361(a)(1)/(a)(2)/(a)(3), 23.361(b)(1), 23.363, 23.371(b).
- **Source:** Ch 19, `ENGLOADS.BAS`. Implemented in `sloads/modules/engine.py` (the original `engloads/` port).
- **Reads:** `Project.engine` (engine/prop weight, CG, diameter, RPM, HP/torque, rotor list, optional measured polar inertia), `Project.weight` load factor.
- **Writes:** the 3 (recip) / 6 (turboprop) FAR conditions; load-case CSV (one row per case, gyro 23.371(b) expands to 4 sign-combination cases).
- **Validation:** Appendix A (Continental IO-520-BB) and Appendix B (turboprop gyro), ±0.1% per Decision 3 — **except** the (a)(1) takeoff torque, see the approved correction below.
- **Approved correction — 23.361(a)(1) takeoff-torque factor (AC 23-19A):** the manual leaves the takeoff-case engine torque **unfactored** (Appendix A prints 554.39 ft-lb), encoding the **Amendment 23-26** drafting error. AC 23-19A states this is non-conservative and was corrected by **Amendment 23-45**: 23.361(c) applies the mean-torque factor to *all* of paragraph (a). `condition_361_a1` now applies `factor × mean takeoff torque` (IO-520-BB → **737.34 ft-lb**; turbopropeller → 1.25× mean, identical to 25.361(a)(1)(i)). User-approved, documented deviation from the oracle (register: `docs/20_theory/02_approved_corrections.md`; policy in CLAUDE.md); cited to `reference/AC_23-19A_engine_torque.md`. `test_361_a1` asserts the corrected value and keeps 554.39 as the mean-torque figure for traceability.
- **Approved correction — 23.361(a)(3) turboprop-malfunction mean-torque factor (AC 23-19A):** the manual / `ENGLOADS.BAS` (`TTP=1.6*ENGTORQ`) apply only the 1.6 propeller-control-malfunction factor, encoding the same **Amendment 23-26** omission. The (a)(3) base "limit engine torque corresponding to takeoff power and propeller speed" is the same quantity as (a)(1), so by the same authority 23.361(c)'s **1.25** turbopropeller mean-torque factor applies before the 1.6 factor. `condition_361_a3` now reports `1.6 × 1.25 × mean takeoff torque` (= **2.0× mean**). User-approved, documented deviation; cited to `reference/AC_23-19A_engine_torque.md`. No printed Appendix B engine-mount oracle exists in the bundled PDF, so it is formula-checked in `test_361_a3_applies_mean_torque_factor`.
- **Notes:** **Standalone** — no module inputs/outputs (UG Table 2.2); all data is direct input. Already supports measured-vs-approximated rotating inertia and SI/Imperial. Serves as the reference template for every other module's calc/units/report/CSV pattern. **GUI is multi-engine:** the engine-mount page (`app/views/engine_mount.py`) exposes the first-class multi-engine `Project` — a sidebar layout selector (`SINGLE_NOSE`/`TWIN_WING`/`QUAD_WING`) sets the engine count and an engine selector picks which engine is edited; per-engine inputs live in `st.session_state["engine_inputs"]` (canonical Imperial, keyed by engine + unit system). Results default to the selected engine with a "Show all engines" toggle over `engine.run(project)`; exports cover every engine. A single engine reduces exactly to `run_all`.
- **Optional supplemental FAR 25 cases (concept superset):** `Project.include_far25` (default off → FAR 23 output byte-identical) appends the **non-duplicative 14 CFR 25.361/25.371** engine cases for **turbopropeller** engines. Because the AC 23-19A correction now factors the FAR 23 takeoff case too, for a turbopropeller the FAR 25 torque cases 25.361(a)(1)(i)/(ii)/(iii) became **bit-for-bit duplicates** of the corrected 23.361(a)(1)/(a)(2)/(a)(3) and were **removed**. Only the three genuinely additive cases remain: (a)(3)(i) `stoppage torque @ 1g` (23.361(b)(1) reports the torque alone), (a)(3)(ii) `max-accel torque @ 1g` (no FAR 23 analog), and 25.371 gyroscopic on the **A2 limit load factor** (23.371(b) fixes the vertical at 2.5g). 25.371 uses the **fixed FAR 23.371(b) rates (2.5/1.0 rad/s)** as a conservative concept stand-in for the maneuver-derived rates (the tool does not solve 25.331/341/…). These stay opt-in — *not* folded into the FAR 23 path — so the Appendix A/B oracle (locked to **6** turboprop conditions and a **2.5g** gyro vertical) is unchanged; making them unconditional would break oracle-lock. New optional input `EngineInput.max_accel_torque` (blank → `max_engine_torque`). Reciprocating/jet engines are out of scope (25.361(a)(2) defines no recip factor; the math is prop-centric) → no FAR 25 cases. Sourced from `reference/14CFR_Part25_engine_torque.md`; **formula-closure tested** (no McMaster Part-25 oracle). GUI: an "Add supplemental FAR 25 cases" checkbox in the engine-mount sidebar.
- **25.371 gyro under-prediction guard (P1-5, D-2).** The fixed 2.5/1.0 rad/s stand-in is conservative only while the concept's real rates stay at or below it; the gyro moment is linear in body rate, so an agile concept would be under-predicted silently. Two optional advisory inputs, `EngineInput.design_yaw_rate_rad_s` / `design_pitch_rate_rad_s` (blank → no guard; **`SCHEMA_VERSION` 22 → 23**, additive), let the engineer declare the concept's real 25.371 rates. When a declared rate **exceeds** its stand-in, `condition_25_371`'s note becomes an explicit `WARNING -- gyroscopic loads UNDER-PREDICTED …` (naming axis, rate and moment ratio) and the GUI renders it as `st.warning`. **Warn-only** by decision D-2: the declared rates are *advisory* — the reported Myy/Mzz stay at the fixed stand-in (no re-derivation; solving the real maneuver-rates is deferred). The GA/oracle path (no declared rates) is unchanged.

### ONENGOUT — One-engine-out loads ✅ DONE (C9)
- **FAR §:** 23.367 (unsymmetrical loads due to engine failure), multi-engine.
- **Source:** Ch 11, `ONENGOUT.BAS`. Implemented in `sloads/modules/one_engine_out.py` (registers `"one_engine_out"`).
- **Reads:** `Project.one_engine_out` (`OneEngineOutInput` — the failure-transient timing: thrust-decay / windmill-drag / rudder-travel times, Euler step, failed-engine index); the failed `Project.engines[i]` (HP, prop diameter, butt line); `Project.vtail_loads` (ARVT, areas, rudder deflection, `xv25`/`xv50`); `Project.mass` (WTONECG — `IZZ`, CG, heaviest case); `Project.speeds` (VC/VD/VS, shoulder altitude). The 25%/50% MAC v-tail stations are the `xv25`/`xv50` of `VTailLoadsInput` (`xv50` added in C9).
- **Writes:** the maximum asymmetric **vertical-tail** load per speed (VC ultimate / VD limit / VS) — a `ModuleResult` with one `ConditionResult` each (engine thrust, windmill drag, max yaw rate, **max tail load**, 25%/50% MAC loads at peak, time to recovery). Non-recovery (below VMC) is flagged. The full time history is available on demand (`time_history`) for the Streamlit re-run; it is not persisted.
- **Safety factor is a case-definition attribute (M1-5, review T7).** The SF is owned by the **load-case definition**, not the speed: how the governing regulation *classifies* the load (LIMIT vs ULTIMATE) sets the factor, and the same case definition also fixes the **speed range** it is considered over (evaluated at the range's critical high end). Being a *failure* case does not by itself reduce the factor. 23.367(a) (turbopropeller; Ref 1 Ch 11 p87; VMC = minimum control speed, Method allows VS/VSF substituted for VMC) defines two cases: **(a)(1)** power failure from **fuel-flow interruption** — **LIMIT → SF 1.5**, considered VMC→VD (a failure case that keeps the full factor); **(a)(2)** **compressor-from-turbine disconnection / turbine-blade loss** — **ULTIMATE → SF 1.0**, considered VMC→VC (a "limit treated as ultimate" value; the previous default 1.5 double-factored it). The **VS** point (VS substituted for VMC, the shared floor) is reported as a **LIMIT** design point (**SF 1.5**, decided 2026-07-20). Each case declares its `load_class`/`safety_factor`, speed range and basis as a row in the `_load_cases` table (`_LoadCase`), carried onto the `ConditionResult` (`safety_factor` + `note`), so the deliverable renders `lbs-ULT` with the correct `SF`. (23.367(a) is turbopropeller-specific — the `is_turboprop` gate and the VSF alternative VMC substitute are backlog M4-3.)
- **Method:** a **time-marching yaw simulation** (Euler), reusing the shared v-tail aero helpers (`sloads/modules/_vtail.py`: AVT lift slope, EFFECTV, the EF large-deflection chart) that SELECT also uses.
- **Validation:** **sub-formula exactness** vs `ONENGOUT.BAS` (thrust, windmill drag, AVT, EFFECTV, EF, density ratio) + integration/physics closure (recovery, yaw-rate peak, time-step convergence) + refactor-parity with SELECT. The printed **Appendix B twin oracle is unavailable** — Appendix B is absent from the bundled `reference/FAR23Loads_Code.pdf` (only the Appendix A GA single is present) and the FAA User's Guide Ch 22 gives partial inputs/no outputs; recorded as a deferred item.
- **Notes:** First module to exercise the first-class multi-engine `Project`. The recovered EF chart (ONENGOUT.BAS subr 10000) is now in `_vtail.large_deflection_factor`; wiring it into SELECT's static v-tail loads (replacing `rudder_large_deflection_factor=1.0`) is a deferred mini-step.

### LGFACTOR — Landing load factor ✅ (Step C10)
- **FAR §:** 23.473 (ground load conditions), 23.725 (drop test).
- **Source:** `LGFACTOR.BAS` (Appendix C p483). Module `modules/landing.py`.
- **Reads:** `Project.landing` (wing area / landing weight / strut stroke / tyre OD & hub / lift factor / strut type); wing area falls back to the `Project.geometry` wing.
- **Writes:** nothing to `Project` (M2R-4: `build_landing`/`run` are pure). The estimated landing load factor N (gear factor NLG = N − L) is **returned** on `LoadFactorResult.airplane_load_factor`/`.gear_load_factor` — the former write-back `Project.landing.n` field was removed (v32), since rendering the page must not mutate the project.
- **Validation:** Appendix A `LGFACTOR.OUT` p236 (V 9.0048 / N 3.0951 / NLG 2.4281) within ±0.1%.
- **Notes:** Feeds LANDLOAD. `V = 4.4·(W/S)^0.25` clamped 7–10 fps; energy efficiencies 0.3 tyre / 0.5 spring / 0.75 oleo.

### LANDLOAD — Landing loads ✅ (Step C10)
- **FAR §:** 23.473–23.499 (ground loads: level, tail-down, one-wheel, side, braked, supplementary nose wheel).
- **Source:** Ch 20, `LANDLOAD.BAS` (Appendix C p468). Module `modules/landing.py`.
- **Reads:** the **landing-gear geometry** (main/nose axle `(X, Z)` at 3 deflection states, rolling radii, tread, strut type) from the single-source **`Project.geometry.landing_gear`** (`LandingGearGeometry`, Step G6b) — `build_landing` resolves it onto a local **effective** input copy before the reaction solve (`_effective_gear_input`, M2R-4: no write-back to `Project.landing`), so the LANDLOAD math is unchanged; the **non-geometry** LANDLOAD inputs (max-landing/gross weights, strut stroke, tyre OD/hub, lift factor, tail-down angle, gear-load-factor override) and the LGFACTOR result stay on `Project.landing` (**`wing_area_sqft` is derived from the geometry wing, Step M2-6, via `landing._wing_area` — not stored**); the per-CG weight & CG from `Project.landing.cg_cases` — **three explicit, distinct loadings are required** (aft max landing, fwd max landing, fwd light; UG fig 18.2). *(Before G6b the gear geometry was carried on `Project.landing` and duplicated by the coarse `LayoutInput` gear fields — now retired.)*
- **Writes:** the 24 main-wheel + 33 nose-wheel reaction loads for each ground condition (ground-line and airplane-datum) → `ModuleResult` / CSV.
- **Validation:** Appendix A `LANDLOAD.OUT` p230 — the **gear-geometry intermediates oracle-locked** (K 0.324, GAMMA 17.978, ground angles, BETA, the AP/BP/DP/CP lever-arm table) ±0.1%; the printed p231–233 **wheel-load table is OCR-garbled** in the bundled PDF, so the full matrix is **closure + legible-cell spot-checked** (case 1 VMP 3144 / VNP 1787 / resultant 1879; side cases VMP 2261, SMP −1700/1122) — the ONENGOUT (C9) precedent.
- **Notes:** **Tricycle gear only** (UG Table 2.1). LANDLOAD takes the gear load factor as a rounded design input (2.5 on p230), distinct from LGFACTOR's computed 2.428. **`cg_cases` are required, not auto-derived (M2-8):** the earlier fallback took *both* max-landing corners from the single heaviest `Project.mass` case, so the fwd/aft pair was degenerate and the nose-gear/braked-roll lever arms (`AP/BP/CP` about `xcg`) — hence those reactions — were under-predicted; `landing._cg_cases` now raises when `cg_cases` is empty (WTENV's structural fwd/aft CG limits, `validation.wtenv_cg_limits`, are the intended source). **M2R-5:** the Landing Loads page now carries a fixed 3-row `st.data_editor` for `cg_cases`, seeded from those WTENV limits (fwd/aft stations + gross/fwd-regardless weights) — previously project-JSON only. **Concept-mode 23.473(g) floor (M2-8):** in concept mode the LGFACTOR condition appends a warn-only note when `N < 2.67` or `NLG < 2.0` (the regulation's floors); the computed `N`/`NLG` are left untouched, so the Appendix-A oracle (3.0951 / 2.4281, both above the floors) is unaffected.

---

## Modern additions (no `.BAS` oracle)

These are registered calc modules with no original program and **no manual
regression oracle**; Appendix A/B geometry is used only as a *sanity* fixture.

### configuration — General configuration & layout (Step C5)
- **FAR §:** none (modern addition; geometric source of truth, not a FAR condition).
- **Source:** `sloads/modules/configuration.py`; method refs Reference 1 Ch 5
  (trapezoidal MAC) and Ch 8 (tail-volume neutral point).
- **Unified geometry slice (Step G1):** the parametric layout is `Project.geometry.parametric`
  (`LayoutInput`) — formerly the separate top-level `Project.configuration` slice, now
  folded onto `GeometryInput` alongside `.surfaces` (WINGGEOM planforms) and a new
  `.fuselage` outline (`FuselageOutline`: `FuselageSection` width/height vs. station,
  the station-area table for the three-view body profile and the Step G4 pitching-
  moment estimator). **Step M2-6: the `.fuselage` outline is the sole editable shape
  source; the `LayoutInput.fuselage_length`/`_width`/`_height` scalars are a derived
  read-only summary of it (length = station span, width/height = max section), not
  persisted** (`fuselage_summary`); `default_fuselage_outline` remains the *migration*
  path that seeds an outline from the scalars for a pre-outline file. One **Geometry**
  page owns and edits the whole slice; `SCHEMA_VERSION` **25** (**26** after Step G4's
  `fuselage_moment`, **27** after Step G6's `empennage`, **28** after Step G6b's
  `landing_gear`, **29** after Step M1-1b's single-source CLmax stall, **30** after
  Step M2-6's wing/fuselage single-source, **31** after Step M2-10's operational
  placards, **32** after Step M2R-2 removed the `LandingInput.n` write-back);
  legacy files migrate on load.
- **Single-source landing gear (Step G6b):** the tricycle-gear geometry (main/nose
  axle `(X, Z)` at compressed/static/extended, rolling radius, strut type, tread)
  lives in `Project.geometry.landing_gear` (`LandingGearGeometry`); LANDLOAD reads it
  (synced onto `Project.landing`), and the retired coarse `LayoutInput`
  `main_gear_x`/`nose_gear_x`/`track`/`gear_height` are **derived** by
  `gear_stations(layout, landing_gear)` (ground = static axle `Z` − rolling radius) for
  the three-view and the tip-back/overturn/clearance estimate. `io` migrates a pre-v28
  file's top-level `landing` gear into `geometry.landing_gear`.
- **Single-source empennage (Step G6):** the horizontal-/vertical-tail + elevator/
  rudder geometry lives in `Project.geometry.empennage` (`EmpennageInput{htail, vtail}`,
  the analysis-native `TailLoadsInput`/`VTailLoadsInput`). `Project.tail_loads` /
  `.vtail_loads` are **properties** proxying to it (so SELECT/TAILDIST/BALLOADS/ONENGOUT
  read them unchanged), and the duplicated `LayoutInput` `h_tail_area`/`h_tail_arm`/
  `h_tail_span_in`/`v_tail_area`/`v_tail_arm`/`v_tail_span_in` fields are **retired** —
  the three-view and the tail-volume static margin read the analysis-native values
  (area/span; arm derived from `xt25`/`xv25` minus the 25% wing-MAC station). `io`
  migrates a pre-v27 file's top-level `tail_loads`/`vtail_loads` into `geometry.empennage`.
- **Reads:** `Project.geometry.parametric` (`LayoutInput`: fuselage / parametric wing /
  tail-arrangement (`tail_type`, `h_tail_z`)); `Project.geometry.empennage`
  (tail + elevator/rudder); `Project.geometry.landing_gear` (gear axles/tread);
  `Project.weight.envelope` (aft-gross %MAC for the static
  margin, optional); `Project.engine` (prop geometry for clearance, optional);
  `Project.mass` (the WTONECG itemized loading, optional — Step D4.5, see
  `cg_estimate` below). The page (not the calc) also reads `Project.weight.items`
  and `Project.engines` to overlay markers on the three-view (Step D4.6, no calc
  input).
- **Tail sketch (Step G6):** `tail_planform(layout, empennage) -> Dict[str, Dict[str,
  List[(x, y)]]]` returns per-panel `top`/`side`/`front` outline polylines from the
  single-source `empennage` (h-tail area/span `2·htail_semispan_in`, v-tail area/span,
  the 25%-MAC stations `xt25`/`xv25`), a first-order rectangular sketch (constant chord
  = area / span; no taper/sweep data for the tail). It also draws the **elevator** and
  **rudder** as the aft `Saft/S` chord band (`_hinge_fraction(aft_hinge_area, area)`;
  the `elevator`/`rudder` panels). `LayoutInput.tail_type` (`CONVENTIONAL`/`T_TAIL`/
  `V_TAIL`/`CRUCIFORM`) and `h_tail_z` still drive placement: `T_TAIL`/`CRUCIFORM`
  default `h_tail_z` (when `0`) to the top/mid-height of the fin; `V_TAIL` derives two
  mirrored diagonal panels at a fixed 40° dihedral (`_V_TAIL_DIHEDRAL_DEG`). Returns
  `{}` (nothing drawn) when there is no empennage geometry.
- **Writes:** derived MAC / XLEMAC / Y_MAC / AR / span (obtained by running the
  generated wing polylines through the WINGGEOM strip integrator — WINGGEOM stays
  the owner), horizontal tail volume, neutral-point %MAC + station, static margin,
  tip-back / overturn angles, prop ground clearance → `ConditionResult`s. The page
  also *seeds* `Project.geometry` with the generated wing `SurfaceInput`, and (Step
  D4.3) approximate component stations into the Weight DB (WTONECG) via
  `component_stations(layout) -> Dict[str, Vec3]` + `match_component_station` —
  pure functions, no new schema (no per-component station sub-model was added; see
  the D-5 decision in `docs/30_future/02_gui_workflow_plan.md`). Keys: `wing`
  (25% MAC), `fuselage` (length midpoint), `h_tail`/`v_tail` (wing 25% MAC + tail
  arm), `tail` (area-weighted h/v average, for WTESTIMA's single lumped "Tail"
  structure-group item), `main_gear`/`nose_gear` (gear station, strut mid-height)
  and `landing_gear` (weight-weighted ~3:1 main:nose average). The seed button
  (`configuration_layout.py`) matches each `MassItem.name` to a key by
  case-insensitive substring alias, most-specific first, and only fills an item
  still at `(0, 0, 0)` — a hand-entered station is never overwritten. The gear
  tip-back/overturn CG (Step D4.5, `cg_estimate(project, layout, geom) ->
  (x_cg, z_cg, source)`) is the true weight-averaged station from
  `Project.mass.cases[0]` (WTONECG's itemized loading — currently always a
  single case; `weight_onecg.build_mass`'s per-CG-case/gear-up-down set is a
  later refinement, at which point this should pick the representative case
  rather than always the first) when present, else the 25%-MAC / wing-
  reference-waterline first cut; the `source` string ("Weight DB" / "25% MAC
  estimate") is surfaced as part of the `ConditionResult` label and the
  three-view CG-marker legend so the UI always states which one is in play.
  Prop ground clearance does not depend on the CG, so it is unaffected by
  which source is active. (Step D4.6) `configuration_layout.py`'s three-view
  overlays a marker per `Project.weight.items` `MassItem` in all three views —
  grouped by `MassItemKind` (color) and sized by `weight_lb` — and a diamond
  marker per `Project.engines[]` entry at its `engine_cg`; this is a
  page-only, calc-free overlay (no new `ConditionResult`s). The page also
  gains a per-engine numeric X/Y/Z override (not drag-and-drop), defaulted to
  the current `EngineInput.engine_cg`, with an Apply button that writes back
  into `Project.engines[i].engine_cg` and re-renders the marker.
- **Validation:** **no oracle.** `tests/test_configuration.py` — analytic-vs-strip
  MAC consistency ±0.1%; Appendix A trapezoid plausibility (MAC 69.246 / MAC butt
  line 87.854, ±10%, since the real wing has an inboard strake); `component_stations`/
  `match_component_station` are checked directly (arm/weighting arithmetic, alias
  precedence, and that ungiven components are omitted rather than defaulted to 0);
  `cg_estimate` is checked directly for both the mass-present and fallback paths,
  and that the gear `ConditionResult`'s CG-station label reflects the active source;
  `tail_planform` is checked for each `TailType` branch (h-tail height per type,
  V-tail's mirrored panels) and for the empty-when-unset backward-compat case.
- **Notes:** all stability/gear figures are first-order estimates (CG at 25% MAC
  when no mass slice is present, true weight-averaged CG once one exists — Step
  D4.5; tail-volume NP with `h_acw=0.25`, `a_t/a_w=1`, `1−dε/dα=0.6`). In concept
  mode the results are flagged unverified extrapolation.

### body_loads — Fuselage net-load distribution (Step C6)
- **FAR §:** none directly (modern addition); the fuselage design conditions it
  distributes are 23.301/23.331, selected by SELECT.
- **Source:** `sloads/modules/body_loads.py`; method refs Reference 1 Ch 15
  (fuselage net-load distribution along the body).
- **Reads:** SELECT's fuselage critical conditions via `select.select_fuselage(project)`
  (not a persisted `Project.envelope.critical` read — it calls SELECT's fuselage
  selection directly), `Project.tail_loads` (h-tail balancing load + `xt25` tail
  station) and `Project.fuselage_mass` (`FuselageMassInput` — the per-station
  lumped fuselage weight distribution, which should exclude wing mass per Ch 15).
- **Writes:** the longitudinal net shear/bending-moment/torsion distribution
  along the fuselage stations → `ConditionResult`s / CSV; feeds the sbeam
  export bridge's body target.
- **Validation:** **no printed oracle** (a modern addition); closure-checked —
  the net distribution balances the applied tail load and fuselage inertia
  relief (physics-closure, not a manual figure). **Vertical (ΣFz) closure only:**
  a single wing reaction is applied, so **ΣM is not balanced** — the terminal
  `Myy` is non-zero and the bending distribution carries a net pitching couple.
  The Ch 15 front/rear-spar two-reaction solve (Ref 1 p103, incl. the pitching
  load factor) is open work — backlog **M4-1**. Until it lands, the limitation is
  single-sourced as `body_loads.CLOSURE_CAVEAT` and stamped onto every
  deliverable: `$ CAVEAT:` comment lines in `fuselage_loads.bdf`, a warning on
  the **Net Fuselage Loads** page, and a caption on the **Export** page's
  Fuselage row.
- **Notes:** off the FLTLOADS→SELECT→component-module main span-load pipeline
  in the sense that it distributes a fuselage station-load rather than a wing
  spanwise one; still driven by SELECT's critical selection.

---

## Export bridges

These are **output renderers**, not registered calc modules: they read a results
slice and emit a file for an external tool. They live in `sloads/export/`,
return strings (with thin `write_*` file wrappers), and do no physics.

### sbeam export bridge — net wing load → sbeam (Step C4)
- **Source:** `sloads/export/sbeam_bridge.py`; card style mirrors
  `sbeam/results/load_export.py`.
- **Reads:** `Project.loads.wing_net` (NETLOADS) — accepts a `Project`, a list of
  `WingLoadResult`, or one result.
- **Writes:** (1) a **span-load CSV** (one row per wing station per case: applied
  nodal `Fx/Fz/My` + cumulative `Sx/Sz/Mxx/Myy/Mzz` + `SF`); (2) **FORCE/MOMENT**
  bulk-data cards, comma free-field unit-scale form (`FORCE, SID, GID, 0, 1.0,
  Fx, Fy, Fz`, components `%.6E`), one load set (SID) per case; (3) an optional
  minimal **CBAR stick-model BDF** (GRID + CBAR chain + PBAR/MAT1 placeholder +
  root SPC1 + the load cards + a SOL 101 subcase per case).
- **Nodal loads:** the applied nodal force/torsion at each station is the
  *increment of the cumulative* NETLOADS column to the next station outboard, so
  the FORCE set sums to the root shear and the MOMENT(My) set to the root torsion
  **exactly**; under the WINGINER quadrature (`y[i]-y[0] = i·dy`) the FORCE
  moments about the root reproduce the root bending exactly.
- **Coordinates:** `sloads/export/coordinates.py` — SLOADS station-X /
  butt-Y / waterline-Z inches → sbeam global CID 0, **identity** (single
  edit-point for any future sign/axis/unit change).
- **Limit → ultimate (defect M4-7):** every exported force/moment/pressure is the
  calc's LIMIT value × **that case's** `safety_factor` (default
  `constants.ULTIMATE_FACTOR` = 1.5 per 14 CFR 23.303; `1.0` for a case already at
  ultimate), resolved per result by `sbeam_bridge._sf()` — never a flat suite-wide
  constant. Geometry (coordinates, chord fractions) is not scaled. The factor is
  uniform *within* a case, which is what the closure guarantee requires. Every CSV
  carries it in the last column (`SF`) and every card block states it in its `$`
  header. The same applies to the fuselage, tail-chordwise and control-surface
  exports below.
- **Factor mint sites (defect M4-13):** every distributed-load result carries a
  factor minted **once** by its producer: `taildist`/`body_loads` copy the
  governing `CriticalCondition.safety_factor`; `net_loads` (whose wing cases have
  no upstream `CriticalCondition` — their case ids are on a disjoint band) mints
  `ULTIMATE_FACTOR` once per case in `build_net_loads` and sets it on the air,
  inertia **and** net families; `aileron`/`flap`/`tab` mint once in their
  `build_*`. In all of them `run()`'s rendered `ConditionResult` copies the
  factor **from the built result** — never re-defaults it — so the report and
  the exported cards cannot disagree, even for a future non-1.5 case (M4-8).
- **Read-side validation (defect M4-14):** the persisted `safety_factor` is
  hand-editable (Project JSON Editor / the file itself), so the five `io.py`
  readers coerce it through one helper (`io._safety_factor`): anything
  non-numeric (null, string, bool, NaN/inf) **or outside the legal
  `[1.0, ULTIMATE_FACTOR]` band** falls back to the conservative default
  `ULTIMATE_FACTOR` — a low value would silently under-scale cards still
  labelled ULTIMATE, including on the headless CLI export path. The band is
  owned by the load-case definition (14 CFR 23.303; a case already at ultimate
  is 1.0, an agreed 23.302/25.302 failure-case factor lies between). The shared
  predicate is the public `validation.safety_factor_valid`; the advisory
  `safety_factor_out_of_range` consistency warning (Export page) covers
  in-session values, and the JSON editor warns on the raw dict at Apply
  (post-coercion the built project can no longer show what was typed).
- **Validation:** force/moment closure (cards re-summed = NETLOADS root totals);
  a self-contained free-field reader round-trips the cards in tests; the stick
  deck parses **and solves SOL 101** in the real sbeam (manual verification step).
- **CLI:** `python cli.py --export-sbeam <prefix> <project.json> [--stick-model]`.

### Export-scope filter (Step D8.3)
- **Source:** `sloads/export/sbeam_bridge.py::filter_by_selected_case_ids`.
- Filters any case-carrying result list to `envelope.critical.selected_case_ids`
  (the D5 Critical Loads page's opt-out selection); a result with no `case_ref`
  is kept, and `selected_ids is None` returns the input unchanged (no filter).
- **Used by** the Export page's "Export scope" toggle, and only for fuselage
  (`body_net`) and tail (`tail_chordwise`) results, whose `case_ref.case_id` is
  copied verbatim from `envelope.critical.conditions` (`body_loads.py`,
  `taildist.py`). Wing (`wing_net`) and control-surface (aileron/flap/tab)
  results mint independent case ids on disjoint bands that never overlap
  `envelope.critical`'s (see the backlog's "Unify select_wing/one_engine_out
  case identity" gap), so they always export the full set.

### Workbook export bridge — multi-sheet `.xlsx` (Step D8.2)
- **Source:** `sloads/export/workbook.py::build_workbook`; `openpyxl` dependency.
- Pure renderer: re-shapes strings/rows the Export page has already computed
  for the CSV/`.zip` channel (project fields, per-module load-case CSVs, the
  case-index table, and the tabular sbeam span-load CSVs) into one workbook —
  no new calculation. BDF card text is excluded (not tabular data).
- **Sheets:** `Project`; one per module with results (sheet name = the
  workflow-step title, truncated to Excel's 31-char limit); `Case Index`; and
  the tabular sbeam artifacts (`Wing Span Loads`, `Fuselage Span Loads`,
  `Tail Chordwise`, `Control Surface Loads`) when their inputs are present.
- **Used by** the Export page's "📊 Download workbook (.xlsx)" button, a
  sibling alternative to the `.zip` bundle (not nested inside it).

---

## Cross-module field ownership (the shared schema at a glance)

Derived from **User's Guide Table 2.2** (the authoritative input→output map):

| `Project` slice | Owned by | Read by |
|-----------------|----------|---------|
| `weight` (components, empty/MTOW) | WTESTIMA | WTONECG, WTENV |
| `weight.cg_cases` (named loading scenarios) | Weight & Mass Properties page, Payload Cases tab (Step G3; Step D5, modern, no `.BAS`) | weight_envelope (chart overlay, read-only); Flight Envelope page merges it into `FlightLoadsInput.cg_cases` |
| `weight.envelope` (useful-load envelope) | WTENV | FLTLOADS |
| `mass` (weight/CG + inertias) | WTONECG | FLTLOADS, LANDLOAD (weight/CG); SELECT, ONENGOUT (inertia) |
| `geometry.surfaces[<surface>]` | WINGGEOM | STRSPEED, AIRLOADS, AIRLOAD4, FLTLOADS, SELECT, ONENGOUT |
| `geometry.parametric` (`LayoutInput`: fuselage/wing/tail/gear) + `geometry.fuselage` (`FuselageOutline` station-area table, Step G1) | configuration (modern; no `.BAS`) — the one **Geometry** page | seeds WINGGEOM (`geometry.surfaces[wing]`); reads `weight.envelope`, `engine`; `fuselage` → Step G4 estimator |
| `speeds` (V_A/C/D, n, mach) | STRSPEED, MACHLIM | FLTLOADS, AILERON, FLAPLOAD |
| `aero_coeffs` (airplane-less-tail CL/CD/CM, cruise + flaps-down; **`clmax_clean`/`clmax_clean_neg`/`clmax_flap`** stall-speed source, M1-1b; + `fuselage_moment` Munk ΔM1, Step G4) | Aerodynamic Data page (`aero_coefficients` key, Step D4.1; formerly `FlightLoadsInput.configurations`) | FLTLOADS (polynomials + per-config `stall_cl` clamp); **STRSPEED / FLAPLOAD / ONENGOUT (CLmax → VS/VSF)** |
| `aero` (tau, spanwise) | TAU, AIRLOADS/AIRLOAD4 | SELECT, NETLOADS (and AIRLOADS↔SELECT iterate) |
| `envelope.vn / tail_balance` | FLTLOADS | SELECT, WINGINER |
| `envelope.critical` | SELECT | AIRLOADS, AIRLOAD4, WINGINER, TAILDIST |
| `envelope.critical.selected_case_ids` (opt-out GUI selection, Step D5) | Flight Envelope (V-n) page, Critical Loads tab (Step G3) | Results Review page (display filter only); Export page (fuselage/tail sbeam artifacts + case index only, Step D8.3 — structural calc modules keep reading `envelope.critical.conditions` unfiltered) |
| `loads.wing_inertia` | WINGINER | NETLOADS |
| `landing` (gear geometry + load factor) | LGFACTOR (N returned on `LoadFactorResult`, not stored — M2R-4), direct gear-geometry input | LANDLOAD; reads `landing.cg_cases` (required, weight/CG), `geometry.wing` (area) |
| `engine[]` | direct input | ENGLOADS, ONENGOUT |
| `loads.wing_net` (net wing load) | NETLOADS | report/CSV export; **sbeam export bridge** (FORCE/MOMENT + stick model) |
| `fuselage_mass` (per-station fuselage weight) | direct input | body_loads |
| `loads.*` (per-module results, incl. body_loads' net fuselage shear/BM) | each component module | report/CSV export only |
| *(verification only)* | BALLOADS | reads FLTLOADS data; no pipeline output |

This table is the build order in disguise: a module is ready to implement once
everything in its "Read by"/owner chain exists. Note the non-DAG / off-pipeline
edges: **AIRLOADS↔SELECT** iterate (aero ⇄ critical); **ENGLOADS / TABLOADS** are
standalone; **BALLOADS** is a post-FLTLOADS verification utility (no output that
other modules consume).

**GUI page consolidation (Step G3).** The calc modules and slices above are
unchanged, but the *Develop V-n diagram* nav section now hosts several of them on
merged, tabbed pages (the `.BAS`→module map and slice ownership hold; only the page
that edits a slice moved):

| Merged page (nav step) | `st.tabs` | Folded calc modules (still registered/tested) |
|---|---|---|
| **Weight & Mass Properties** (`weight_mass`) | Estimate · Weight, CG & Inertia · Payload Cases · Weight / CG Envelope | `weight_estimate`, `weight_envelope` folded; `weight_onecg` is the step's named module |
| **Structural Speeds** (`structural_speeds`) | Design Speeds · Speed–Altitude Envelope | `mach_limit` folded |
| **Flight Envelope (V-n)** (`flight_envelope`) | V-n diagram · Critical Loads (SELECT) | `select` folded |

Folded modules are listed in `workflow.FOLDED_MODULES` (the wing_inertia precedent),
so the nav-drift guard stays green without a dedicated step each. See
`docs/40_history/00_completed_development.md` → Phase G, Step G3.

---

## Structured load-case IDs (Step D1)

Every delivered load case carries a stable `CaseRef` (`sloads/models.py`):
`case_id` (`"<component>-<seq>"`), `component`, `condition`, `cg`, `speed_kt`,
`altitude_ft`, `far_reference`. It replaces `report.py`'s old render-time,
per-module, unstable `LC{idx}`. Full design in `docs/30_future/
00_backlog.md` Step D1 (moved to `40_history/00_completed_development.md` once
shipped); summary for anyone adding a new module:

- **Six component prefixes, no more.** `wing` → `W`, `htail` → `HT`,
  `vtail` → `VT`, `fuselage` → `F`, `engine_mount` → `EM`,
  `landing_gear` → `LG` (`sloads/case_ids.py::COMPONENT_PREFIX`).
  Control surfaces fold into their host structural component (aileron/flap/
  wing-tab → `W`; htail/vtail-tab → `HT`/`VT`); the surface identity lives in
  `CaseRef.condition`, not a separate prefix.
- **Assign once, in the minting module's own fixed emission order**, using a
  fresh `case_ids.CaseIdAllocator()` per build call — never a shared/global
  counter. Downstream modules that consume an already-identified result (e.g.
  TAILDIST/body_loads reading SELECT's `CriticalCondition`s) **copy** the
  `case_ref`, they never re-mint.
- **Band disjoint allocators that share a prefix.** Two independent counters
  over the *same* numeric range collide outright (verified in a smoke run:
  `select_wing`'s own `W-02` and WINGINER's `W-02` briefly meant two different
  cases before this was caught) — not just the weaker "divergent sequence"
  gap below. `case_ids.py` reserves: `W-01..39` WINGINER/NETLOADS structural,
  `W-40..49` `select_wing`'s own list, `W-50..59` AILERON, `W-60..69`
  FLAPLOAD, `W-70+` a wing-hosted tab; `HT-50+`/`VT-50+` for TABLOADS' htail/
  vtail-hosted tabs (disjoint from SELECT's own htail/vtail sequence). A new
  module minting into an existing prefix must claim its own band here.
- **Known accepted gap — not closed by D1.** `select_wing`'s own
  `CriticalCondition` list and `WingMassInput.cases` (which actually drives
  WINGINER/NETLOADS) are two independent wing case lists (the pre-SELECT "C3
  bridge" in `models.py`); banding prevents an ID collision but does not make
  them the same case object, so the same numeric range can label two
  different physical cases depending which list you're looking at. Same gap
  between `one_engine_out`'s own `VT-` id and `select_vtail`'s. See "Unify
  `select_wing`/`one_engine_out` case identity..." in `docs/30_future/
  00_backlog.md` → Deferred refinements.
- **A `ConditionResult` carries at most one `CaseRef`.** Where a module packs
  several sub-cases into one result (23.371(b)'s four gyro sign combinations),
  the base id is minted once in calc and the sub-case ids are *derived*
  (`report.py`'s `_gyro_subcase_id`, an a/b/c/d suffix) at render time — this
  is the one place ID text is built outside a calc module, and only because
  the model has no way to carry four `CaseRef`s on one result.
- **Not persisted for transient results.** `ConditionResult`/`GearReactionCase`
  are never written to `project.json` (they're recomputed every run), so their
  `case_ref` has no `io.py` round-trip; only the *persisted* result slices
  (`EnvelopeResult.vn`/`.critical`, `LoadsResult.*`) serialize it.

---

## Status summary

| Phase | Modules | Done | Remaining |
|-------|---------|------|-----------|
| 0 Restructure | engine → package | ✅ done (engloads → sloads, Project model, io/registry, app/) | 0 |
| 1 Mass | WTESTIMA, WTONECG, WTENV | 3 (WTESTIMA, WTONECG, WTENV) | 0 |
| 2 Geometry/Speeds | WINGGEOM, STRSPEED, MACHLIM | 3 (WINGGEOM, STRSPEED, MACHLIM) | 0 |
| 3 Aero/Envelope | TAU\*, AIRLOADS, AIRLOAD4, FLTLOADS, SELECT, BALLOADS† | 6 (all) | 0 |
| 4 Component loads | WINGINER, NETLOADS, AILERON, FLAPLOAD, TABLOADS, TAILDIST, ENGLOADS, ONENGOUT, LGFACTOR, LANDLOAD | 10 (all) | 0 |
| **Total** | **22** | **22** | **0** |

Counts reference 1's 22 Appendix-C programs only; the **configuration** module
(Step C5) is a modern addition with no `.BAS` and is not counted above. The FAA
User's Guide exposes **20**
of these as menu modules — the two it omits are:
\* **TAU** (`TAU.EXE`/`TAU.BAS`), the lift-curve-slope helper folded into
`airloads.py`; and
† **BALLOADS** (`BALLOADS.BAS`), the post-FLTLOADS balanced-tail-load verification
utility (off-pipeline; ported in Step C11, reusing SELECT's balance routine). The
pipeline balancing calc lives in FLTLOADS and is refined rationally in SELECT.
