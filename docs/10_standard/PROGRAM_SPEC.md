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
- **Notes:** Empty/takeoff weight ratio `K = 0.62` with adjustments (UG Table 3.1: multiengine +0.01, liquid-cooled +0.01, super/turbocharged +0.01, turboprop −0.05, pressurized +0.02, one-seat −0.04); `W_TO = W_use/(1−K)`. Component weights as %-of-TO-weight (UG Table 3.2). 170 lb/seat. **Crew & OEW (Step E1 follow-up):** the `crew` count (default 1, 170 lb each) is carried in a derived **operating empty weight** line `OEW = empty + crew×170`; this is reporting-only — `WTO`/`useful`/`empty` (the Appendix-A oracles) are untouched, the crew weight already sits inside `useful` (seats×170), so OEW is not re-summed with the useful load. `crew` also feeds the FAR 23 seat-limit check (`passenger seats = occupants − crew`). Engine types: 4-cycle recip, 2-cycle recip, turbocharged, turboprop, liquid-cooled. FAR 23.25(b) minimum-weight rule (crew @ 170 lb + ½ hr fuel at max-continuous; turbojets 5% fuel capacity). **Feeds WTONECG *and* WTENV — they are parallel siblings off WTESTIMA, sharing one weight database; neither feeds the other.** As a UI convenience, `estimate_to_mass_items(inp)` expands the estimate's structure/powerplant/systems components (plus options/miscellaneous) into empty-weight `MassItem` rows — skipping the group totals and the propeller already inside "Engine installed" — to seed that shared database; the Weight Estimate page's "Seed Weight, CG & Inertia" button writes them to `Project.weight.items` with stations/inertias left at zero. The reference-fleet comparison (formerly overlaid on this page and Configuration & Layout) now lives on its own dedicated **Aircraft Comparison** page in the Export phase (`app/views/aircraft_comparison.py`, Phase F Step F2); it loads `app/data/reference_aircraft.csv` — nominal published specs for visual sanity-checking only, never read by any calc. **Concept mode (Step C0):** the `K=0.62` regression is GA-calibrated and out of band above 12,500 lb, so in concept mode (`Project.is_concept`) WTESTIMA is flagged as a sanity-only estimate and the design weight comes from the **direct-weight path** `WeightInput.database_totals()` (named `direct_totals()` until 2026-08-15) — database total/OEW/useful summed straight from the itemized `MassItem` database by kind. Its first element is the **ceiling** of `OEW ≤ MLW ≤ MTOW ≤ Σ items`, not the design take-off weight: a database can hold full fuel *and* full payload at once. MTOW has one owner, `cg_cases.max_takeoff_weight` off `weight.max_takeoff_weight_lb` (decision G-14).

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
- **Writes:** `Project.weight.cg_cases` — named `CgCase` rows (weight, xcg, zcg, the `analyses` the case is run for, and a landing `role` where it is one of LANDLOAD's three) entered once.
- **Notes:** exists to stop the CG-envelope chart (WTENV) and the flight-envelope balance (FLTLOADS) from carrying two independently-edited copies of the same loading scenarios (the Phase-D GUI assessment's finding #2, "no enforced single source of truth for shared inputs"). Decision **G-3** finished the job: `FlightLoadsInput.cg_cases` (a derived copy kept in step by a *page* rather than by the model) and `LandingInput.cg_cases` (the one list that never joined the SSOT) are **removed**, each case states the `analyses` it is run for, and every consumer reads `sloads.cg_cases` rather than filtering for itself. Pre-v19 files carried the scenarios only under `flight_loads.cg_cases` (`migrations._v19_cg_cases`); the v46 hop tags those `FLIGHT` and folds `landing.cg_cases` in as `GROUND` with roles from the canonical names, merging onto an existing case where name **and** `(weight_lb, xcg, zcg)` match.

### WTONECG — Weight & inertia for one configuration
- **FAR §:** 23.23 (load-distribution limits) / 23.29 (empty weight & corresponding CG); provides masses & inertias for dynamic/gyroscopic conditions. (User's Guide §4.3 also ties the module to 23.25.)
- **Source:** Ch 4, `WTONECG.BAS`.
- **Reads:** `Project.weight` items (component weights + x,y,z locations). Computed at the **4 CG locations** of the structural-limits diagram (aft gross, fwd gross, most-fwd reduced, minimum weight) — ×2 (gear up/down) for retractable gear, so up to 8 loadings, not one.
- **Writes:** total weight, CG (x,y,z), and mass moments of inertia (Ixx, Iyy, Izz, products), output in **both slug-ft² and lb-in²** → `Project.mass`.
- **Validation:** Appendix A/B — CG and inertia for the example loadings.
- **Notes:** **`Project.mass` is produced by the GUI (M4-17a).** `weight_onecg.build_mass` had **zero callers** — no page, no CLI path and no example produced the slice — so the `weight_mass` step's `produces="mass"` never turned ✅, the dashboard blocked Landing Loads on every shipped example, and the One Engine Out gate was unsatisfiable. The **Weight, CG & Inertia** tab's `Apply weight items` handler now persists `project.mass = build_mass(project)`, and every bundled example carries a regenerated `mass` block. Consequence to expect: `configuration.cg_estimate` flips from the 25%-MAC fallback to its `"Weight DB"` branch, sharpening the tip-back / overturn / static-margin figures on the Geometry page and in the example outputs. Per UG Table 2.2 / §4.5 the outputs split: **weight & CG → FLTLOADS** (LANDLOAD reads the three roled `GROUND` weight/CG cases, **not** `mass` — M2-8/M4-17a/G-3; `cg_cases.seed_landing_cases` uses `mass.cases[0].cg_z` only to seed the waterline); **inertia → SELECT, ONENGOUT** (maneuver/gust balancing and unbalanced landing). Component inertia = transfer (parallel-axis) of each item about the airplane CG. Conceptually the same machinery as the engine/rotor inertia in `engloads`, at airplane scale — but ENGLOADS does **not** read `Project.mass` (it is standalone, UG Table 2.2).
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
- **Notes:** Category drives the maneuver load-factor formula (23.337: n=2.1+24000/(W+10000), capped 3.8/utility 4.4/acrobatic 6.0; negative −0.4× positive for normal/utility, −0.5× for acrobatic — UG Table 7.1). **Dive speed VD (23.335(b), M1-1):** enforced as `VD ≥ max(K_d·VCmin, 1.25·VC)` — **both** minimums, with the K_d term applied to the *minimum* cruise VCmin (STRSPEED.BAS `V2DMIN=K2·V1CMIN`). On the no-chosen-speeds path K_d·VCmin governs (Appendix A p155, Cat N: 198.53 kt; `test_vd_floor_no_chosen_speeds`); the worked chosen-speeds case (p156, VD 212.5) clears both floors. Concept mode (Cat C) keeps only the absolute 1.25·VC floor and reports K_d·VCmin as advisory. **Dive-speed basis (F25-2):** 14 CFR 25.335(b) offers two routes *disjunctively* — the speed ratio `VC/MC ≤ 0.8·VD/MD` (= `VD ≥ 1.25·VC`) **or** a minimum Mach margin `MD ≥ MC + margin`; 23.335(b)(4) has the same structure. `speeds.vd_basis` (`VdBasis.SPEED_RATIO`, the default, or `MACH_MARGIN`) selects. The margin route is **concept category "C" only** (decision D-1) and requires a non-zero shoulder altitude and a `chosen_vd`; on it the 1.25·VC floor does not apply, and the value it would have imposed is reported so the two routes stay comparable. Margin policy has one owner, `resolve_mach_margin`: default 0.07 M, 0.05–0.07 M only with `speeds.mach_margin_basis` (a written rational analysis crediting automatic systems, 25.335(b)(2)) and flagged everywhere it appears, below 0.05 M refused. A chosen VD short of the margin is raised to meet it. Every margin-route output states that only the (b)(2) Mach term is evaluated — the (b)(1) upset criterion is not implemented, so the check is not a sufficiency demonstration. **`speeds.vb_kt`** (rough-air speed, 25.335(d)) is accepted and checked for 25.335(a) ordering against VC only; the full `VC ≥ VB + 1.32·U_ref` margin needs the 25.341 reference-gust schedule and is deferred to F25-1. Regulation text: `reference/14CFR_25_335_design_airspeeds.md`, `reference/14CFR_MC_MD_speed_margin.md`. **Concept mode (`category="C"`, Step C0)** bypasses the GA-only 23.337 formula and cap entirely: it requires explicit `chosen_n`/`chosen_nneg` and uses them verbatim (no FAR floor), so >12,500 lb concepts are not forced to a meaningless GA limit; the VC(min)/VD(min) coefficients become out-of-band advisories. `Project.is_concept` is the single concept read-point. **FAR 23 applicability (Step E1):** the pure `sloads.far23_applicability(project)` helper (`sloads/applicability.py`) compares the design gross weight (the MTOW SSOT via `cg_cases.max_takeoff_weight` — decision **G-14**; it read the Weight DB *total* on the `speeds.weight_lb`-unset branch until 2026-08-15, an upper bound standing up to 1,800 lb above MTOW) and passenger-seat count (`occupants − crew`, where `occupants` seeds from the Weight Estimate seat count when unset and `crew` is the user-set `WeightEstimationInput.crew`, default 1) against the non-commuter FAR 23 tier (12,500 lb / 9 seats; limits in `constants.py`, commuter tier dormant) and returns structured `Exceedance`s — none on GA inputs. `app/components.render_applicability_banner` surfaces them on the Dashboard + definition pages with a non-blocking "Switch to Concept" action that seeds `chosen_n`/`chosen_nneg` from the computed 23.337 factors. STRSPEED also computes Mach limits at altitude (`T = 59 − 0.003566·h`; `a = 29.02·(T+459.4)^0.5`), so it overlaps MACHLIM — keep the shared atmosphere/Mach helper in one place. Feeds MACHLIM, FLTLOADS, AILERON, FLAPLOAD (UG Table 2.2). **Operating-limitation implications (Step M2-10, advisory):** the design speeds bound the eventual Subpart-G operating limitations; `operational_implications`/`operational_placards` derive the preliminary placards — **both families** shown (recip yellow-arc: VNE=0.9·VD, VNO=min(VC, 0.89·VNE), MNE=0.9·MD; turbine/no-yellow-arc: VMO=VC, MMO=MC; common VFE=VF) per 14 CFR 23.1505/23.1511 and Ref 1 p47 (`reference/14CFR_operating_limitations.md`). Optional operational **targets** invert the ladder into required design minima (`operational_target_checks`: VNE⇒VD≥VNE/0.9; VNO⇒VC≥VNO and VD≥VNO/0.89/0.9; VMO⇒VC≥VMO; MMO⇒MD≥MMO+the resolved Mach margin (F25-2 — `resolve_mach_margin`, default 0.07; formerly a hardcoded 0.05); VFE⇒VF≥VFE) and **warn-only** on infeasibility — never mutating a design speed or load. Infeasible targets also surface on the dashboard via `validation._check_operational_targets` (`operational_target_infeasible`, page `structural_speeds`). Display/validation only; the FAR23 loads path is unchanged. **GUI read-through (Step D4.4):** `app/views/structural_speeds.py` reads the design weight from `Project.weight.max_takeoff_weight_lb` (the MTOW SSOT; the Weight DB *total* until 2026-08-15) when it is entered, read-only with an "Override design weight" checkbox, instead of asking for it a second time; likewise wing area from `Project.geometry`'s wing surface (pre-existing `has_wing` gating). When neither upstream slice is populated the page shows an info message pointing at the Airplane-section page that owns it, rather than falling back to an Appendix-A-shaped literal default. `app/views/weight_envelope.py` (WTENV) does the same read-through for its `gross` weight (it already requires a Weight DB to render at all, so the total is always available; only the override path differs).

### MACHLIM — Mach limit lines
- **FAR §:** 23.335(b) high-speed limit; compressibility.
- **Source:** Ch 6, `MACHLIM.BAS`.
- **Reads:** `Project.speeds` (the design speeds, from which MC/MD are derived — F25-2), altitude range.
- **Writes:** Mach-limited speed vs altitude (the V-M limit line) → `Project.speeds.mach_limit`.
- **Validation:** Appendix B (high-altitude twin) Mach-limit table.
- **Notes:** Only material for high-performance/high-altitude airplanes (Appendix B). Graphics: V vs altitude limit line. **Step E7 (Speed–Altitude Envelope consolidation):** the page is retitled **Speed–Altitude Envelope**. MC, MD and the shoulder altitude are now READ from `Project.speeds` (via `structural_speeds.design_speed_values`) instead of re-entered — only the max operating altitude and the increment remain as page inputs (removing the Step D5 duplicate MC/MD/shoulder entry). The chart becomes a transport-category-style speed–altitude flight-limits diagram: **altitude on y**, a **KEAS/KCAS/KTAS** selectable x-axis (via the new `constants.convert_airspeed`), a thin constant-Mach fan, and the design-speed boundary drawn EAS-limited (constant) below the shoulder and Mach-limited (V=M·a·√σ) above it, so VC/MC and VD/MD kink at the shoulder like a placard chart. All chart speeds are design *limit* speeds (a speed boundary, not a load deliverable — the ULT rule does not apply). Display-only + one new pure helper; no change to `mach_limit_lines`' calc. **F25-2 (schema v40): MC/MD are no longer stored.** `MachLimitInput` carries only the shoulder/max altitude and the increment; `mach_limit_lines(inp, mc, md)` takes MC/MD explicitly and `structural_speeds.design_speed_values` is their sole producer on every front-end. They used to be persisted here *and* recomputed by the Streamlit page (which ignored the stored pair) while the registry/CLI path honoured them, so one project reported two different MNE/MFC depending on how it was run. Migration hop `_v39_mach_limit_mc_md` drops the dead keys; `test_mc_md_come_from_strspeed_on_every_front_end` is the drift guard.

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
- **Reads:** `Project.speeds` (STRSPEED — VA/VC/VD/VF, MC/MD and the limit load factors via the shared `maneuver_load_factors`); **`Project.flight_loads`** (`FlightLoadsInput`) for the balance geometry scalars `mac`/`wing_area_sqft`/`xw`/`zw`/`xtc`/`xtf`, the reference Mach `mn`, the altitude list and the four weight-CG cases (`CgCase`) — **`mac`/`wing_area_sqft`/`xw`/`zw` are derived from `Project.geometry` (Step M2-6), not stored**: MAC/S/XW from the WINGGEOM wing surface (`XW = XLEMAC + 0.25·MAC`), ZW from the parametric wing (`root_waterline_z + Y_MAC·tan(dihedral)`), filled by `sloads.derived_geometry.sync_geometry_derived` at calc entry (`build_envelope`), GUI read-only; `xtc`/`xtf`/`mn`/altitudes stay this page's own input; and **`Project.aero_coeffs`** (`AeroCoefficientsInput`, Step D4.1) for the airplane-*less-tail* aero-coefficient polynomials (`AeroCoeffSet`: CL(α), CD(CL), CM(α) + stall CLs) — `.cruise` (flaps up, balanced at every altitude) and, when present, `.flaps_down` (balanced at sea level only, FLTLOADS.BAS line 3000). `Project.aero_coeffs` is the single owner of these coefficient sets; the Airplane-section **Aerodynamic Data** page (workflow key `aero_coefficients`,
retitled in the Airplane-phase GUI usability pass — the per-surface spanwise
Schrenk aero, `Project.aero`, stays on the Wing Loads page next to the load
distribution it drives, cross-linked from both pages) writes it (`flight_envelope` only reads it) — before Step D4.1 they were carried inline as `FlightLoadsInput.configurations`, a list of `AeroCoeffSet` keyed by `flaps_down`; older project files migrate automatically (`io._legacy_aero_coeffs_from_flight_loads`). **As built (C2):** the aero polynomials come from the Ch 7 aero-coefficients program and are entered as input (AIRLOADS/C1 does not yet emit them); the CG cases are entered explicitly (seeding them from `Project.weight.envelope`/WTENV is a later refinement), so the original data-flow's `Project.mass` read is not needed for the balance. **Step D5:** the four weight-CG cases are no longer edited on this page — they are the shared `Project.weight.cg_cases` the **Weight/CG Grid & Payload Cases** page owns. **Decision G-3b** removed the derived copy that kept them in step: `FlightLoadsInput.cg_cases` is gone, and `build_envelope`/SELECT/WINGINER/NETLOADS/BALLOADS read the `FLIGHT`-tagged set through `sloads.cg_cases` — a plumbing change, pinned per fixture to reproduce the pre-hop list exactly. The altitude list, previously a single-altitude widget touching only `altitudes_ft[0]`, is now a fully-editable list on this page (multi-altitude V-n); the calc loop (`for alt in fl.altitudes_ft`) already supported more than one entry since Step C2. **Step G4:** when `aero_coeffs.fuselage_moment` is enabled, `build_envelope` adds its Munk `dCm/dα` increment (ΔM1) to each config's M1 on a local copy (stored coefficients untouched, Glauert factor applies automatically); off by default so the GA/twin oracles are bit-for-bit unchanged. The estimate is produced by `sloads.fuselage_moment.estimate` from `Project.geometry.fuselage` + this page's wing S/MAC and shown/overridden on the Aerodynamic Data page. **M4-5 (decision D-10):** the coefficient polynomials are now **evaluated in one place** — `sloads/aero_curves.py` (`lift_cl`/`drag_cd`/`moment_cm`/`clmax_curve`), which `_balance` calls, so the Aerodynamic Data page's plotted curve and the balance that produces the loads cannot drift apart (the Glauert factor is passed as `(g, gmn)` rather than a pre-divided ratio, keeping the FLTLOADS arithmetic order bit-for-bit). The same module builds the page's CL–α / drag-polar / CM–α curves with the balanced V-n points overlaid — recovered from each point's *dimensional* output (`L = LZW·cosα − DX·sinα`, `CL = L/(Q·S)`; likewise CD and CM from `M(W+F)`) rather than re-evaluated — plus two closure metrics: **recovered CL** (that recovery vs the polynomial; algebraically identical within a converged point, so a **drift guard** at 1e-9, not a numerical result) and the **stall-clamp margin** (no balanced point may sit above its Mach-adjusted stall CL by more than the balance's own 0.005 band — this one has content: it fails when the dynamic-pressure iteration never reaches the stall line, e.g. because the Mach cap binds first). The coefficient-*entry* checks (`aero_clmax_unreachable`, `aero_lift_slope_sign`, `aero_drag_negative`, `aero_drag_polar_shape`, `aero_clmax_neg_sign`) are `sloads.validation` warnings tagged `aero_coefficients`; there is deliberately **no moment-slope check** — a positive M1 is the normal airplane-less-tail state (the tail is what makes the airplane stable) and every shipped fixture including the Appendix A oracle carries one.
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
- **Notes:** Central junction. Reads V-n data from FLTLOADS + geometry (WINGGEOM) + inertia (WTONECG). Per UG Table 2.2 it feeds **AIRLOADS, AIRLOAD4 (iterative — see AIRLOADS), WINGINER, TAILDIST**. NETLOADS/component modules consume `critical` indirectly via those. **Step D5:** `CriticalLoadSet.selected_case_ids` is an **opt-out GUI selection** — the Critical Loads page persists which computed conditions the engineer keeps for the deliverable (empty = no filter, every condition kept, the default and the whole behavior for older projects); `CriticalLoadSet.selected()` applies it. Only the **Results Review** page's display reads `.selected()` — every structural calc module (WINGINER/NETLOADS, `body_loads`, the sbeam export bridge) deliberately keeps reading `.conditions` unfiltered, so the selection can never silently drop load cases from a deliverable's structural sizing, only from the GUI summary. (D8.3 is expected to wire the export bundle to this same selection — not yet done.) **M2-4:** the governing-loads tables on **both** the **Results Review** headline and the Flight Envelope **Critical Loads** tab render through one shared `report.governing_loads_table(conditions, system, sf)` — load columns are ULTIMATE (scaled by SF, `-ULT` marker + `SF` column), dimensionless/speed columns (n, CL, V) unscaled and unmarked, absent cells `"—"`. **Review F-R1 (M4-8 Layer-1 report-side slice):** the factor is **per case** — each row scales by its own `CriticalCondition.safety_factor` (14 CFR 23.303 → 1.5 by default, 1.0 for a case already at ultimate) and its `SF` cell states that row's factor, matching the export side (`sbeam_bridge._sf`); the helper takes no caller-supplied `sf` override, so a report figure and its bulk-data card cannot state different factors for one case. **M4-8 / G-11 (2026-08-14):** that per-case factor is now itself a derived view — `sloads/safety_factors.py`'s governing table classifies each case by its FAR reference and writes the carrier at `registry.run_all_modules`, `report.content.component_loads` and `balanced_run`, so a project-level override reaches the report column and the bulk-data cards together or not at all.

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
- **Notes:** The panel mass is a linearly-tapered area density iterated to the entered panel weight; strips inboard of the rib carry no panel mass; concentrated weights add spanwise steps to the shears/moments. Subtracted from the air load in NETLOADS. **A non-positive panel weight short-circuits to an empty panel** (review F-C5, 2026-08-10): the BASIC iteration's ±1% acceptance band is empty at zero, so it walked the density down *through* zero and returned negative strip masses — a sign-flipped wing, not a lighter one (−0.108 lb integrated on `ga6_normal` with the weight cleared).

### NETLOADS — Net wing loads
- **FAR §:** 23.301(b) (net = air + inertia in equilibrium).
- **Source:** Ch 14, `NETLOADS.BAS`.
- **Reads:** `Project.wing_mass`, `Project.geometry.<surface>`, `Project.aero.<surface>` (and `Project.envelope.vn` for the per-case CL/V/Nz/Nx). Combines the AIRLOADS air-load distribution and the WINGINER inertia distribution.
- **Writes:** the net spanwise shear, bending moment and torsion along the 25% chord → **`Project.loads.wing_net`** (+ the air/inertia distributions in `Project.loads`) + a one-row-per-station CSV (`net_loads.wing_load_rows`, with the in-band `MyyAxis` torsion-axis column and `Basis` LIMIT marker). Pure entry `net_loads.build_net_loads(project)`.
- **Validation:** Appendix A "Net Loads, Case 22 PHAA" p222 (root Sz +5837, Mxx +455555, Myy -60940, Mzz -81483) — exact algebraic sum of the air (p206) and inertia distributions.
- **Notes:** A primary structural deliverable (root shear/BM/torsion), wing only, full fidelity (all of Fx/Fz/Sx/Sz/Mxx/Myy/Mzz). SELECT selects the governing cases; NETLOADS also accepts them supplied directly as `WingLoadCase`s referencing the V-n matrix.
- **Torsion reference axis (M4-18).** The calc accumulates torsion about the local **25% chord** (AIRLOADS/WINGINER convention, oracle-locked). The deliverables state it about the surface's **loads reference axis** (LRA, `SurfaceInput.ref_axis_pct` — the beam-model elastic axis, typically 40–50 % chord; default 0.25 = the original reporting): `net_loads.to_loads_ref_axis` applies the pure boundary transform `Myy_lra(y) = Myy_25(y) + Sz(y)·(x_lra(y) − x_25(y))` (shears/bending unchanged), stamps `WingLoadResult.torsion_axis`, and is invoked by the Loads-Plots page and the sbeam bridge (`loads_ref_axis_results`) — exactly the limit→ultimate boundary pattern. Every rendered/exported torsion **names its axis** (metric/plot labels, `MyyAxis` CSV column, BDF `$` comments); the Wing Loads analysis page stays at the labelled 25 % chord for manual cross-checks, and `net_loads.run` reports the root torsion at both axes (labelled) when the LRA differs.

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
- **Validation:** **sub-formula exactness** vs `ONENGOUT.BAS` (thrust, windmill drag, AVT, EFFECTV, EF, density ratio) + integration/physics closure (recovery, yaw-rate peak, time-step convergence) + refactor-parity with SELECT. The printed **Appendix B twin oracle is unavailable** — Appendix B is absent from the bundled `reference/FAR23Loads_Code.pdf` (only the Appendix A GA single is present) and the FAA User's Guide Ch 22 gives partial inputs/no outputs; recorded as a deferred item. **Fixture coverage (2026-08-13):** the module was registered but **unrunnable on every shipped fixture** — `atr42_100`/`dhc8_dash8` entered the `one_engine_out` slice with no engine horsepower, the other four entered no slice, so the whole simulation path was exercised only on constructed inputs (same class as the `tail_mass` gap). Both turboprops now enter **take-off and max-continuous shaft power** — PW120 2000/1700 shp, PW121 2150/1950 shp, converted from the certificated kW in **EASA TCDS IM.E.041 issue 07 (20 Dec 2023) §5** — and `tests/test_one_engine_out.py::test_the_shipped_turboprops_execute_onengout` is the standing gate. Both fields are entered deliberately rather than left to `_engine_power`'s one-sided fallback: `use_takeoff_power` is the user's choice of rating and a fallback would make it silently. Their **VS cases do not recover** (full asymmetric power at the clean stall speed is below VMC) and say so in band.
- **Limitation — propeller installations only.** Both terms of the yawing moment are propeller relations from `ONENGOUT.BAS`: thrust `= HP·550·0.85/V` and Glauert windmilling `∝ DIA²`. A turbofan/turbojet multi is **not covered** — the thrust term becomes a shaft-power surrogate and the windmill term collapses to zero with the propeller diameter, understating the asymmetry — which is why `concept_regional_jet` enters **no** `one_engine_out` slice rather than a plausible-looking one. Single-owner wording: `one_engine_out.PROPELLER_ONLY_NOTE`, carried as the `engine-failure-propeller-only` standing limitation in every methods-and-limitations stamp. Refusing to *run* on a non-turboprop is the separate `is_turboprop` gate (backlog M4-3(b)).
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
- **Reads:** the **landing-gear geometry** (main/nose axle `(X, Z)` at 3 deflection states, rolling radii, tread, strut type) from the single-source **`Project.geometry.landing_gear`** (`LandingGearGeometry`, Step G6b) — `build_landing` resolves it onto a local **effective** input copy before the reaction solve (`_effective_gear_input`, M2R-4: no write-back to `Project.landing`), so the LANDLOAD math is unchanged; the **non-geometry** LANDLOAD inputs (strut stroke, tyre OD/hub, lift factor, tail-down angle, gear-load-factor override) and the LGFACTOR result stay on `Project.landing` (**`wing_area_sqft` is derived from the geometry wing, Step M2-6, via `landing._wing_area` — not stored**); **both design weights from `Project.weight`** — `max_landing_weight_lb` (MLW, decision **G-4**) and `max_takeoff_weight_lb` (MTOW, decision **G-14**), read through `sloads.cg_cases` and passed to `landing_reactions` explicitly; and the per-CG weight & CG as the **three roled `GROUND` cases** of the one shared `weight.cg_cases` list (decision **G-3**) — **three explicit, distinct loadings are required** (aft max landing, fwd max landing, fwd light; UG fig 18.2), resolved by `cg_cases.landing_role_cases`. *(Before G6b the gear geometry was carried on `Project.landing` and duplicated by the coarse `LayoutInput` gear fields — now retired.)*
- **Writes:** **40 `ConditionResult`s** (M4-17e) → `ModuleResult` / CSV: the LGFACTOR condition, one critical-reaction summary per FAR ground family (6), and the **full 33-case matrix**, one condition per case. Each matrix row carries VMP/DMP/SMP/RMP + VNP/DNP/SNP/RESULT (`lb` → `lbs-ULT`), the unbalanced pitch/roll/yaw moments (`lb-in` → `lb-in-ULT`) and the **dimensionless** ground-line inertia factors NVP/NDP/NS (units `""` — load *factors*, so no `-ULT` marker, never scaled, blank `SF` column). Cases 25–33 (23.499 supplementary nose) are nose-only. Summary and matrix rows for the same case share a `CaseRef.case_id` — they are the same physical case. The airplane-datum reactions (`vm/dm/vn/dn`) are **surfaced from step 10 piece 3** (decision **G-12**): they are what the assembled ground cases apply at each gear reference point, and what the gear load report states as the airframe end of the leg. Each row also carries `weight_lb`, the design weight the case is computed at — **not** the named loading's own weight on cases 13–22, which 23.473(a) lets LANDLOAD scale to the take-off weight via `WR`. The loading a case is computed at is owned by `landing._loading_index`, which is *not* a plain 3-cycle: cases 19–24 are three loadings × **two drift directions** (23.485's inboard/outboard pair), which the `WL` table and both unbalanced-moment tables already say and which the per-case record mislabelled until 2026-08-15. Landing is a property-style table, so it routes through `report.results_to_rows`; `report._LOAD_CASE_LABELS` is deliberately **not** extended — `load_cases_to_rows`' single-point-load schema (one location, one vertical/side/thrust triple) cannot hold a *pair* of reactions at two stations plus three unbalanced moments without losing the nose reaction or fabricating locations.
- **Validation:** Appendix A `LANDLOAD.OUT` p230 — the **gear-geometry intermediates oracle-locked** (K 0.324, GAMMA 17.978, ground angles, BETA, the AP/BP/DP/CP lever-arm table) ±0.1%; the printed p231–233 **wheel-load table is OCR-garbled** in the bundled PDF, so the full matrix is **closure + legible-cell spot-checked** (case 1 VMP 3144 / VNP 1787 / resultant 1879; side cases VMP 2261, SMP −1700/1122) — the ONENGOUT (C9) precedent.
- **Notes:** **Tricycle gear only** (UG Table 2.1). LANDLOAD takes the gear load factor as a rounded design input (2.5 on p230), distinct from LGFACTOR's computed 2.428. **`cg_cases` are required, not auto-derived (M2-8):** the earlier fallback took *both* max-landing corners from the single heaviest `Project.mass` case, so the fwd/aft pair was degenerate and the nose-gear/braked-roll lever arms (`AP/BP/CP` about `xcg`) — hence those reactions — were under-predicted; `landing._cg_cases` raises when no roled `GROUND` case exists (WTENV's structural fwd/aft CG limits, `validation.wtenv_cg_limits`, are the intended source). **M2R-5:** the three loadings gained a real editor, seeded from those WTENV limits (fwd/aft stations + gross/fwd-regardless weights) — previously project-JSON only. **Step 10 piece 2 (G-3) re-homed both:** the editor is the Weight & Mass Properties page's **Payload Cases** tab, which is now the sole editor of every weight/CG case and carries the `analyses` / `role` columns; the seed is the pure calc helper `cg_cases.seed_landing_cases`, offered on that tab as a button and never written by a render; and the Landing Loads page's CG table is a **read-only** view of the three roled cases. **M4-17c — seed hardening:** the seed never emits a zero cell. The waterline comes from `Project.mass.cases[0].cg_z` (WTONECG) and is left **blank** when no mass slice exists — the former `0.0` fallback put the CG on the ground line and produced nonphysical negative nose reactions (−233…−2887 lb on GA-6) and braked-roll main loads ~2.6× the p230 oracle, silently; the forward station now comes from the new **`validation.wtenv_fwd_cg_limit_at_weight(project, weight_lb)`**, the WTENV forward limit interpolated (clamped, never extrapolated) *at* each row's weight — Appendix A p230 reads 76.12 in at the 3230 lb landing weight, where the weight-agnostic `wtenv_cg_limits` hull gives 72.64 in; and the max-landing rows are blank rather than seeded at full MTOW when the max landing weight is unset. The page blocks the reaction compute until every row has a positive weight, station **and waterline**. **M4-17d — hierarchy & sanity validation:** `validation._check_landing_hierarchy` (input-side: `gross_ge_max_landing`, `landing_light_le_max`, `landing_cg_ordering`, `landing_cg_below_axle`, `landing_cg_names`) and `validation.landing_reaction_warnings` (post-compute: `landing_negative_vertical`, `landing_zero_nose`, kept out of `consistency_warnings` so no definition page pays for a gear solve). Warn-only, silent on the Appendix-A GA fixture. The three loadings are consumed **positionally**, and that order is now an explicit `CgCase.role` (**G-3a**) rather than a name match: `cg_cases.landing_role_cases` returns exactly one case per role, in role order, and **raises** rather than reordering or padding. `gross_ge_max_landing` and `landing_cg_names` left with the fields they policed — `GW` is no longer an overridable copy but the MTOW SSOT, and the canonical-name check was the workaround for the contract the role replaced; `landing_case_weight_is_mlw` took their place, since a roled max-landing case that disagrees with MLW is an error and not a preference (**G-4**). **M4-17e — critical-case ranking:** `_critical` ranks on the full `√(V²+D²+S²)` rather than the printed two-component `RMP`/`RESULT`, which excluded the side load and made the 23.485 pick a tie-break accident; numerically inert on every bundled example. **Concept-mode 23.473(g) floor (M2-8):** in concept mode the LGFACTOR condition appends a warn-only note when `N < 2.67` or `NLG < 2.0` (the regulation's floors); the computed `N`/`NLG` are left untouched, so the Appendix-A oracle (3.0951 / 2.4281, both above the floors) is unaffected.

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
  the D-5 decision in `docs/40_history/05_phase_d_gui_workflow_plan.md`). Keys: `wing`
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
  station), `Project.fuselage_mass` (`FuselageMassInput` — the per-station
  lumped fuselage weight distribution, which should exclude wing mass per Ch 15)
  and the wing carry-through resolved from `Project.geometry` by
  `derived_geometry.carry_through` (planform root chord × `SurfaceInput`
  `front_spar_pct`/`rear_spar_pct`; **M4-1**).
- **Writes:** the longitudinal net shear/bending-moment/torsion distribution
  along the fuselage stations → `ConditionResult`s / CSV; feeds the sbeam
  export bridge's body target. Per condition it also writes the moment-closure
  fields on `BodyLoadResult` — `m_unbalanced` and the front/rear spar **fitting
  loads** `r_front`/`r_rear` at `x_front`/`x_rear`, with the `spars_assumed` /
  `closure_artifact` provenance flags.
- **Validation:** **no printed oracle** (a modern addition); closure-checked in
  **both** degrees of freedom (physics-closure, not a manual figure) — the
  applied `ΣFz = 0`, the running shear returns to ~0 at the aft end, and the
  terminal `Myy` returns to ~0. **Moment closure (M4-1, closed 2026-08-03)**
  follows the two passes of Ref 1 p103: the terminal moment of the
  inertia + tail-load set is the unbalanced moment `M_ub`, reacted with the
  vertical residual `R_total = NZ·W_fus − LT` at the wing front/rear spar
  attachments (`R_r = (M_ub + R_total·(x_ref − x_f))/(x_r − x_f)`,
  `R_f = R_total − R_r`, `x_ref` = the integrator's aft-most station). The two
  reactions are applied as the statically **equivalent linear line load** over
  `[x_f, x_r]` — a documented refinement of p103, which prescribes two point
  loads: same resultant and first moment, no `±M_ub/d` shear spike across a
  short carry-through, and it collapses onto the manual's two-point solve as
  `d → 0`. The fitting loads `R_f`/`R_r` are **reported, not re-applied** (the
  distribution already carries them). When the spar stations are underivable a
  whole-body correction closes the beam instead; it has no physical source, so
  the result is flagged `closure_artifact` and single-sources the limitation as
  `body_loads.CLOSURE_ARTIFACT_CAVEAT`, stamped as `$ CAVEAT:` lines in
  `fuselage_loads.bdf`, a warning on the **Net Fuselage Loads** page and a
  caption on the **Export** page's Fuselage row — **only on that fallback path**.
  Still open and split out: the pitching load factor (**M4-21**; `θ̈ = 0` on the
  balanced trim cases, so it does not affect this closure) and the distributed
  body aero moment (**M4-19**).
- **Notes:** off the FLTLOADS→SELECT→component-module main span-load pipeline
  in the sense that it distributes a fuselage station-load rather than a wing
  spanwise one; still driven by SELECT's critical selection.

---

### tail_span — Spanwise empennage loads (plan 09 step T2)
- **FAR §:** none of its own — it distributes the tail conditions SELECT has
  already selected: 23.421 (balancing), 23.423 (checked/unchecked maneuver) and
  23.425 (gust) on the horizontal tail, 23.441/23.443 on the fin. The one
  condition with a hand is **23.427(a)**, the unsymmetrical horizontal tail,
  carried as the per-side scales `rh_scale`/`lh_scale`; a `ConditionResult` cites
  23.427(a) when the two sides differ and 23.421 otherwise.
- **Source:** `sloads/modules/tail_span.py`; planform resolution and the
  half/full bookkeeping in `sloads/tail_geometry.py`. Design note:
  [`../30_future/09_distributed_empennage_loads_plan.md`](../30_future/09_distributed_empennage_loads_plan.md)
  (decisions T-2/T-3/T-4/T-6/T-8/T-9/T-10/T-13/T-15/T-16), with plan 13's L-1/L-7
  for the fin. **It computes no total of its own** — `LT25`/`LT50` and the v-tail
  side loads are read from SELECT, never recomputed (T-7), so no Appendix A
  figure moves. Frame and sign conventions:
  [`CONVENTIONS.md`](CONVENTIONS.md).
- **Reads:** SELECT's h-tail/v-tail critical conditions through their owner
  (`select.default_critical`: the `LT25`/`LT50` split, the per-side scales, the
  control-surface load) and the V-n points behind them (`select.vn_points`: the
  case load factor, and the case weight the fin's `n_y` is formed on);
  `Project.geometry.empennage` for the planform (entered polylines, else the
  authoritative area/span as a rectangle); the surface weight from the
  `htail`/`vtail`-tagged rows of `Project.weight.items` via
  `mass_distribution.tail_surface_weight` (an entered
  `TailMassInput.panel_weight_lb` survives as an explicit override); and
  TAILDIST's aft-of-hinge pressure block in discrete mode.
- **Writes:** one `TailSpanResult` per condition per surface — a station table
  of `WingStationLoad` (**LIMIT**) that is **full span, tip to tip** for the
  h-tail and root-supported for the fin, `attachment_y` (the fuselage
  attachment stations the beam is reacted at, defined here in the physics),
  `control_loads` (`ControlPointLoad`: hinge reactions by tributary span plus
  the actuator couple) with `hinge_moment_lbin` — **the suite's first
  hinge-moment output** — in `"discrete"` mode, and `tip_transfer` on a T-tail
  fin. `ConditionResult`s report the air and inertia totals, root
  `Sz`/`Mxx`/`Myy` with its stated torsion axis, and the hinge/transfer values.
  Feeds the empennage decks and, through `balance`, the assembled airplane.
- **Validation:** **no printed oracle.** Chordwise placement is TAILDIST's
  unchanged (`LT25` at 25 %, `LT50` at 50 %), which makes every target
  closed-form, and those closed forms **are** the gate (`CLAUDE.md` practice 2)
  — `tests/test_tail_span.py`: the strips sum to SELECT's total plus the
  inertia; root bending is the half load × the area centroid; the torsion is the
  area-weighted closed form and vanishes for the `LT25` term at a quarter-chord
  axis; the fin's lateral inertia relieves the surface total by exactly
  `W_vt/W_case`; the two control-load modes apply identical total force; the
  hinge moment is the aft-of-hinge chord's third; and the spanwise and chordwise
  views cover the same conditions.
- **Notes:** the inertia sign is **d'Alembert** (`−n·W_surf`), set by the case's
  load factor alone and never "opposing the air load" — the governing GA6 h-tail
  conditions are down-load cases, which a magnitude-opposing rule would relieve.
  The fin carries **two** inertia terms because its normal axis is lateral
  (`−n_y·W_vt` bending, `−n_z·W_vt` axial); its local→airplane mapping belongs to
  `export/coordinates.py` alone. `control_load_mode` defaults to `"smeared"` and
  is stated on the result and in the deck, because the two modes describe
  different load paths. `n_y` inherits plan 13 decision **L-7**'s fin-only
  over-statement caveat. A planform derived from area/span travels as
  `planform_assumed` into every rendering and deck header (backlog: real
  empennage polylines).

---

### gear_loads — the landing gear as a free body (Step 10 piece 3)
- **FAR §:** none of its own — it re-presents 23.473–23.499 (LANDLOAD's own
  conditions). 23.485(d) is what puts the reaction at the contact patch.
- **Source:** `sloads/gear_loads.py`. Decision **G-12** of
  [`../30_future/18_step10_ground_cases_plan.md`](../30_future/18_step10_ground_cases_plan.md).
  **No physics of its own:** every reaction is `modules/landing.py`'s, unchanged
  and oracle-locked. What this module adds is *where* the load acts, *in which
  frame*, and *how it reaches the airframe*.
- **Reads:** `Project.geometry.landing_gear` (axle states, rolling radius, tread,
  and per leg the `carrier`/`attach`/`weight_lb` of G-2 and G-12a),
  `Project.landing` (the strut stroke and tail-down angle) and `build_landing`'s
  reaction table.
- **Writes:** `GearCaseLoads` / `GearLegLoad` — per case and per leg: the contact
  patch, the ground-line and airplane-datum component triples, the strut state,
  ground angle and stroke, the reference point, the transfer couple, and the leg's
  own inertia. Plus `AppliedWheel` (`applied_wheels`), the per-wheel form an
  assembled ground case applies. The companion CSV channel
  (`export/sbeam_bridge.gear_report_csv`, the bundle's `gear_report`) meets the
  load-output contract (R6-C2, 2026-08-15): every dimensional column header
  states its unit from the resolved unit set — `-ULT` on load columns, the
  plain force unit on the two weights, which are inputs and never factored —
  `SF` is stated per row as the last column, and a `Wheel` column says which
  wheel a `main` row describes (the starboard one of the pair; the port twin is
  the mirror — R6-C4). The row dicts keep bare, system-independent keys; only
  the file header carries units.
- **The two frames are each artifact's own and neither is re-derived.** The
  ground-line set is what the manual prints and a gear engineer reads; the
  airplane-datum set (`vm`/`dm`/`vn`/`dn`, LANDLOAD's own `PHIM`/`PHIN`
  resolution) is what a beam model applies. `ground_rotation_deg` measures the
  angle between them **from the case's own two resolutions of one reaction**
  rather than from `GRA` — which is why this module never has to adjudicate the
  sign inconsistency in LANDLOAD.BAS's `beta` (`gamma − GRA(1)` level, `+GRA(2)`
  ground roll). That rotation appears in the *checks* and in G-7a's lift axis;
  never in the load path. `SMP` passes through unrotated, being normal to the
  pitch rotation — asserted, not assumed.
- **The transfer is exact, not approximate.** `transfer_couple` is
  `M = (patch − node) × F`, so force-plus-couple at the reference point has the
  identical resultant about **every** reference as the force at the patch. Gated
  at `rel_tol 1e-12` about a deliberately arbitrary point (about the CG a dropped
  couple could cancel), with a negative control that drops the couple.
- **Validation:** `tests/test_gear_report.py`. Reproduces the design note's own
  measurements: ga6's contact patches differ by 0.49 in in `x` and 3.71 in in `z`
  between the landing and handling attitudes; the main leg sits at 24 % of its
  7-in stroke in the landing families and 77 % in the handling ones; case 1 drag
  is 1,020 lb ground-line against 795 lb airplane-datum.
- **Notes:** `weight_lb` is **per leg** (consistent with `attach`, likewise one
  leg's node with its twin got by reflection) and `0.0` means *not stated*, which
  the report shows as an open free body rather than closing against a guess. The
  inertia term is the leg at the **airplane** load factor: unsprung-mass
  amplification, which is what actually sizes an axle, is **not modelled** and
  `UNSPRUNG_NOTE` says so on every surface that renders it. **The module states a
  gear *interface* load definition and must not be read as a gear design load
  set** — sloads has no gear kinematic model, so no drag-brace, side-brace,
  trunnion or axle-bending load is claimed.

---

### balance — Balanced free-free airplane cases (plan 11 step B2)
- **FAR §:** none of its own — every case is an assembly of a condition another
  module already selected, and each row cites **that condition's** regulation:
  23.321 (the symmetric balancing conditions), 23.349 (`ACRL`'s unbalanced
  rolling moment), **23.427(a)** (the unsymmetrical horizontal tail), 23.441–
  23.443 (the four rational v-tail conditions), and 23.479–23.493 for the ground
  families, with 23.471 as the family's general-sentence fallback (R6-C1).
- **Source:** `sloads/modules/balance.py`. Theory of record:
  [`../20_theory/balanced_cases.md`](../20_theory/balanced_cases.md). Design
  notes: plan 11
  ([`../30_future/11_balanced_airframe_cases_plan.md`](../30_future/11_balanced_airframe_cases_plan.md),
  decisions B-1…B-8 — the method), plan 13
  ([`../30_future/13_b8a_lateral_closure_plan.md`](../30_future/13_b8a_lateral_closure_plan.md),
  L-1…L-8 — the lateral families), decision **D-R8** (23.427(a)), and plan 18
  ([`../30_future/18_step10_ground_cases_plan.md`](../30_future/18_step10_ground_cases_plan.md),
  G-1/G-6/G-7/G-7a/G-8 — the ground families). Axes, signs and case identity:
  [`CONVENTIONS.md`](CONVENTIONS.md).
- **Reads:** the whole upstream, recomputing nothing another module owns — the
  critical set and the V-n envelope through their owners
  (`select.default_critical` / `default_envelope`); the wing air distribution
  **recomputed at the V-n point's own** `cl`/`v`/`nz` through AIRLOADS'
  `air_load_distribution` (the entered
  `wing_mass.cases` distributions are untouched and remain the FAR 23
  deliverables); WINGINER's spanwise shape for the wing inertia; the per-case
  loadings from the mass SSOT (`mass_distribution.derive_case_loadings`, decision
  B-2) and their CG cases (`cg_cases.flight_cases` / `ground_cases`);
  `tail_span`'s fin and h-tail distributions; and, for the ground families,
  `gear_loads.gear_case_loads` / `applied_wheels`, whose reactions are LANDLOAD's
  own, unchanged.
- **Writes:** one `BalancedCaseResult` per assembled condition — **two** where
  the condition has a hand, the port twin got by reflection rather than
  recomputation (B-6/B-7) — carrying the full-span applied set of
  `BalancedLoad` (**LIMIT**; each with its own node, force, **free** moment,
  `source` band and `side`), the six pre-closure residuals, the closure relief
  (`delta_n`/`delta_nx`/`delta_ny`, `p_dot`/`q_dot`/`r_dot` from one coupled 3×3
  solve, and the `closure_inertia` it was solved on), the applied aileron couple
  and the lumped fuselage `Cm`. The **last** `ConditionResult` is always the
  skipped-conditions record (review F-C7): every condition SELECT or LANDLOAD
  named and what became of it, so a consumer can always state what the assembled
  deliverable does *not* cover. This is the mission's primary deliverable — the
  full-span balanced free-free deck (aero + inertia, `CONM2` mass cards, handed
  pairs) that the sbeam bridge exports.
- **Validation:** **no printed oracle** — stated physics-closure gates in CI
  (`CLAUDE.md` practice 2), in `tests/test_balance.py` and
  `tests/test_gear_report.py`. `RESIDUAL_GATE` = **1 %** of `n·W` / `n·W·MAC`,
  applied to the residual **before** closure (the physics, not the correction);
  the roll degree of freedom reproduces WINGINER's unit-roll distribution strip
  for strip (ratio 1.000000); the yaw degree of freedom reproduces ONENGOUT;
  23.427(a)'s applied set is SELECT's own `RH`/`LH` with the closed-form
  `(RH − LH)·ȳ` rolling moment; the ground families reproduce LANDLOAD's
  reactions and its unbalanced moments and close in all six DOF; and every
  exported deck balances from its own cards.
- **Where the gate does not apply, and why:** the lateral, 23.427(a) and ground
  families have no residual of the symmetric kind to gate — nothing balances a
  rudder kick or an abrupt elevator input, and the pre-closure `Fy`/`Mz`,
  `Fz`/`My` **are** the applied load, by construction. Each is gated instead on
  the case's symmetric (or trim) half, with the defining set removed, still
  closing inside 1 %. Stated in full in
  [`../20_theory/balanced_cases.md`](../20_theory/balanced_cases.md) (§3, and §9
  for the ground families).
- **Notes:** the **seam rule** (plan 11 §4): a load that a free-body cut
  introduces is never applied in the assembled model — the wing carry-through
  reaction is excluded and `carry_sources_absent` guards it. Only `ACRL` is
  antisymmetric, and that is measured from `UNB`, not assumed. The fuselage's
  Munk moment is applied as a **single labelled free moment** (a sign-changing
  slope term: −6.6 to +4.9 % of `n·W·MAC` on `ga6_normal`, −8.5 to +5.8 % on
  `concept_regional_jet`) until backlog item M4-19 distributes it, and the
  aileron's own spanwise lift increment is likewise lumped as a free couple at
  the wing aerodynamic centre — both stated wherever the case is rendered, since
  omitting them would leave a real aero load disguised as a closure correction.
  The airplane's **non-wing drag** — the airplane-less-tail polar's body-axis `x`
  force less what the wing strips carry — is applied as a `body-axial` load
  (`balance.body_axial_set`), spread over the body outline where there is one.
  Its waterline is the single owner `derived_geometry.body_drag_waterline`, and
  it is the *only* free parameter of that load: its magnitude is fixed by
  definition and its fuselage station contributes no pitching moment. Absent an
  entered `body_drag_waterline_z` it is the wing reference plane, marked
  `assumed`. The `ΔC_D` it represents is reported per case, because carrying the
  load makes the applied axial resultant equal the trim's `dx` by construction.
  A condition whose CG the weight database cannot produce is **recorded, not
  invented**. The ground families' own method — the `n_z = 0` solve, the applied
  gear/lift set and the LANDLOAD identity — is
  [`balanced_cases.md`](../20_theory/balanced_cases.md) §9; the gear free body
  itself is `gear_loads` above.

---

## Export bridges

These are **output renderers**, not registered calc modules: they read a results
slice and emit a file for an external tool. They live in `sloads/export/`,
return strings (with thin `write_*` file wrappers), and do no physics.

### sbeam export bridge — net wing load → sbeam (Step C4)
- **Source:** `sloads/export/sbeam_bridge.py`; card style mirrors
  `sbeam/results/load_export.py`.
- **Reads:** `Project.loads.wing_net` (NETLOADS) — accepts a `Project`, a list of
  `WingLoadResult`, or one result. The `Project` path first transfers the wing
  results to the surface's **loads reference axis** (LRA,
  `net_loads.loads_ref_axis_results`, Step M4-18) so the exported torsion is
  about the beam-model axis; bare-result callers transfer beforehand.
- **Writes:** (1) a **span-load CSV** (one row per wing station per case: applied
  nodal `Fx/Fz/My` + the `Mx/Mz` offset couples + cumulative `Sx/Sz/Mxx/Myy/Mzz`
  + the in-band `MyyAxis`
  torsion-axis column + `SF`); (2) **FORCE/MOMENT**
  bulk-data cards, comma free-field unit-scale form (`FORCE, SID, GID, 0, 1.0,
  Fx, Fy, Fz`, components `%.6E`), one load set (SID) per case; (3) an optional
  minimal **CBAR stick-model BDF** (GRID + CBAR chain + PBAR/MAT1 placeholder +
  root SPC1 + the load cards + a SOL 101 subcase per case). The stick deck states
  its **centerline clamp** in-band beside the `SPC1` (plan 10 §1.1, shipped
  2026-08-10): the clamped node is BL 0, not the side of body, so its reaction is
  the **half-span total applied load**, not a wing root design load — the
  side-of-body quantity is an internal CBAR load and needs a node the deck does
  not have (the side-of-body reporting-node item).
- **Deck `$` comment width.** Every generated `$` sentence in the wing, body,
  tail and control decks is emitted through `sbeam_bridge._comment`, which wraps
  at the **72-column free-field card width** (`$ ` + 70) — a property of the
  emitter, not of each hand-fitted sentence, because the same sentence is wider
  in SI. Swept in both unit systems by
  `test_deck_comments_fit_the_free_field_card_width`. A consumer parsing the
  header should read comment *runs*, not single lines; the unit statement
  (`$ Lengths in <unit>.`) is kept short enough to stand on its own line.
- **Nodal loads:** the applied nodal force/torsion at each station is the
  *increment of the cumulative* NETLOADS column to the next station outboard, so
  the FORCE set sums to the root shear and the MOMENT(My) set to the root torsion
  **exactly**; under the WINGINER quadrature (`y[i]-y[0] = i·dy`) the FORCE
  moments about the root reproduce the root bending exactly.
- **Concentrated-mass offset couples (plan 14, 2026-08-09).** A concentrated wing
  mass does not sit on a station, so differencing alone picks it up whole at the
  node inboard of it and loses its lever arm (bending ran 0.4–1.9 % high;
  in-plane `Mzz` 0.3–1.1 % high; shear was never affected). The lost first moment
  is the per-station defect `δ[k] = mxx[k] − mxx[k+1] − sz[k+1]·dy` — zero
  wherever the lumped-at-nodes recursion built the column, `w·(y_c − y[j])` at the
  bracketing station — and is restored as an applied **couple on that node's
  MOMENT card** (`Mx`, and `Mz` for the in-plane channel), the rigid-offset
  static equivalent. The exported set therefore reproduces the cumulative shear
  **and** bending at **every** node, not just the root, and the `FORCE` cards are
  unchanged. The couples are exactly zero on a wing with no concentrated mass.
  **Consumers must apply the `MOMENT` set**: taking the `FORCE` cards alone
  restores the smeared (high) bending — stated in the deck `$` header. Sign map
  (`Mxx → +x`, `Mzz → −z`) is owned by `coordinates.bending_moment_vector`.
- **Balanced cases and the assembled deck (step B2–B7, 2026-08-08).**
  `modules/balance.py` assembles one full-span free-free case per wing condition
  (`PHAA`/`PLAA`/`PMAA`/`NMAA`/`TORS`, plus `ACRL`) that has both a V-n point and
  a derivable payload loading: wing air + inertia **both sides** (recomputed at the
  V-n point's own condition), the balancing tail load, the fuselage/empennage
  inertia from the mass SSOT, and the fuselage's lumped share of the trim
  pitching moment. `export/balanced_deck.py` writes it — GID bands: right wing
  `6001+`, left wing `6201+`, centreline `6401+`; one determinate six-DOF
  support whose reaction *is* the residual; SUBCASE/SID minted per hand (`5101+`
  symmetric, `7101+` starboard, `8101+` port — see "Deck case identity" below).
  **No free-body cut reaction appears** (the seam rule). The residual before closure and the
  relief applied are stated on the result, in the UI and in the deck header.
  **Surfaces (0.5.0 row 1, D-R2):** the Balanced Cases page (stamped download),
  `cli.py --export-target balanced`, the Export page's own download row **and
  its bundle `.zip`**, with report §6 and the manifest as the controlling
  document's account of it — the deck was page-only, unstamped and unnamed by
  the report until then (review F-D2).
  **The B-2 partition has an edge-case gate** (review F-C5, 2026-08-10): WING-tagged
  items are kept out of the fuselage inertia set precisely because the wing set
  spreads them, so a loading carrying WING item mass against a wing that
  integrates **no** panel raises rather than scaling the wing inertia to zero and
  letting the closure absorb the missing weight in silence. A loading with no WING
  item mass scales legitimately to zero and says so in its case notes.
  **Every condition that does not assemble is recorded** (review F-C7,
  2026-08-10). `build_balanced_cases(project, skipped)` extends the caller's list
  with one `SkippedCondition` (component, condition, V-n point, reason code and
  reader-facing reason) per dropped condition, and the record is stated on three
  surfaces: the `ModuleResult` (a final "Assembly record — conditions not
  assembled" condition carrying the count and the grouped reasons), the deck's
  own `$ CONDITIONS NOT ASSEMBLED` block, and report §4 (beside the assembled
  half of the same statement, report §6). Reason codes:
  `out-of-family` (fuselage, ground and ONENGOUT conditions — the deliberate
  exclusion), `htail-symmetric` (an h-tail condition already carried by every
  case as its trim tail load; only 23.427(a) assembles — D-R8),
  `no-htail-loads`, `no-fin-loads`, `no-vn-point`, `no-cg-case`,
  `loading-not-derivable`. The record is emitted whether or not anything was
  skipped: "every condition assembled" is the completeness statement, and a
  record that appears only on a lossy run cannot be told from one that was never
  produced. Gate: assembled ∪ recorded is exactly SELECT's condition set, and the
  two are disjoint, on every fixture
  (`test_every_condition_is_either_assembled_or_recorded`) — the property, in
  place of the shipped fixtures' pinned drop set that was the only guard before.
- **Antisymmetric (rolling) cases and handedness (step B7, 2026-08-08).** A wing
  condition carrying an unbalanced rolling moment (`WingLoadCase.unbal_moment`,
  FAR 23.349 — `ACRL` only; `TORS` enters zero on every fixture because a steady
  roll has none) is assembled with that couple applied as a **lumped free moment**
  at the wing aerodynamic centre and reacted by a **fourth closure degree of
  freedom**, roll acceleration, distributed over every mass. That relief
  reproduces WINGINER's own unit-roll inertia distribution strip for strip, which
  is the step's closure gate. `residual_mx` on such a case is the *applied*
  couple, not an out-of-balance, and is reported rather than gated. Each rolling
  condition is emitted as a **handed pair** — the computed starboard case and its
  reflection — with `L`/`R` suffixed case ids; see `CONVENTIONS.md` §7.1 for the
  reflection convention and its owner. **Limitation:** the aileron's own spanwise
  lift increment is not distributed (no aileron butt lines in the schema), stated
  in the deck header, the case notes and the UI, and filed on the backlog.
- **Lateral (±β) balanced cases (step B8a-3/B8a-4, 2026-08-09).** The four
  vertical-tail conditions SELECT names — `SUDDEN RUDDER` (FAR 23.441(a)(1)),
  `YAW TO SIDESLIP` ((a)(2)), `YAW 15 NEUTRAL` ((a)(3)) and `SIDE GUST`
  (23.443(b)) — assemble as full-span free-free cases, each as a **handed pair**
  (`VT-01R`/`VT-01L` … `VT-04R`/`VT-04L`). The fin's load set is SELECT's,
  strip for strip, read through `tail_span` and mapped to airplane axes by
  `export/coordinates.py` alone: span → `z` from the fin root waterline, normal
  force → `fy`, torsion → `mz` **negated**. Fin **inertia** is not in this set —
  it rides in the closure field at the case's own `n_y`/`ω̇` through the
  `VTAIL`-tagged mass items (`CONVENTIONS.md` §1, decision L-8). Since 2026-08-10
  the per-condition fin deck carries inertia of its own, so the applied set is
  taken as `fz - f_inertia`: each mass enters exactly one field, and reading the
  net here would relieve the applied side load with a mass the closure field is
  also carrying. Reported per
  case in the result, the UI and the deck header: the applied fin side load, the
  lateral load factor `n_y = L_v/W`, and the yaw and roll accelerations it
  drives. `residual_fy`/`residual_mz` before closure **are** that load and are
  reported, never gated — the gated statement is that the case's symmetric half
  is unchanged (`CONVENTIONS.md` §1). Whether a case is handed is decided by
  `balance.is_handed` on the applied distribution, and whether it is lateral by
  `balance.is_lateral` (§7 owners). **Limitation, stated in-band:** the fin is
  the only lateral aero the suite computes, and the two lateral DOF err in
  **opposite** directions (corrected 2026-08-15) — the yaw acceleration is
  over-stated and its inertia conservative, while `n_y` is **under**-stated
  (the missing body/wing side force adds to the fin's) and its inertia is **not**
  conservative — both by an unknown amount; the fin's own design load is
  unchanged. Filed on the backlog with M4-19.
- **Unsymmetrical horizontal-tail balanced case (FAR 23.427(a), D-R8,
  2026-08-10).** The one h-tail condition with a hand assembles as a **handed
  pair** (`HT-09R`/`HT-09L`, SUBCASE `7209`/`8209`). SELECT's own RH/LH split is
  **distributed** over the full-span `tail_span` table (`balance.htail_sets`,
  `source="htail-air"`, air only — the surface mass rides the closure field with
  the rest) and **replaces** the lumped trim tail load `vn.lt`, which would
  otherwise carry the balancing part twice. Because 23.427(a)'s load is a
  *maneuver* load on a V-n point at `n_z ≈ 1`, the airplane is genuinely out of
  trim: the pre-closure `Fz`/`My` are that mismatch in full (−49.8 % of `n·W`,
  144 % of `n·W·MAC` on `ga6_normal`) and the vertical and pitch closure is the
  motion it causes (Δn −0.496 g, q̇ +637 deg/s²). Reported, never gated — the
  gated statement is that the case's **trim half**, with the lumped load
  restored, still closes inside 1 % (0.301 % on the ga6). Two closed forms check
  the applied set: each half sums to SELECT's own RH/LH exactly, and the applied
  rolling moment is `(RH − LH)·ȳ` with `ȳ` the chord-weighted half-planform
  centroid. Handedness is decided by the **net applied rolling moment** in
  `balance.is_handed` (this case carries no side force and no free `mx`); the
  family is read off the `htail-air` tag by `balance.is_unsymmetrical_htail`.
  Every other h-tail condition is symmetric and stays in the assembly record as
  `htail-symmetric`. **Closure reference:** the relief field is solved about the
  mass set's own centroid rather than the entered CG — they differ by
  0.002–0.005 in on `ga6_normal`'s `CG4`, which at this case's ω̇ is 0.31 lb of
  unclosed `Fx`.
- **Spanwise empennage loads and decks (step T1–T5, 2026-08-08).**
  `sloads/modules/tail_span.py` distributes each critical h-tail/v-tail condition
  **along the span** in proportion to local chord (SELECT's `LT25`/`LT50` read,
  never recomputed), on the surface's load reference axis, with uniform-area-
  density surface inertia at `−n·W` (d'Alembert — the sign follows the load
  factor alone, so a down-load case is *increased*). The h-tail table is **full
  span**, tip to tip through the centreline, reacted at fuselage attachment
  stations; the v-tail is single-sided and root-supported. FAR 23.427(a) scales the
  two halves by SELECT's own RH/LH split. The planform comes from an optional
  `htail`/`vtail` entry in `geometry.surfaces` (validated against the
  oracle-authoritative area/span to 1 %) or is **derived as a rectangle and
  marked assumed** — `sloads/tail_geometry.py` owns both. Decks:
  `tail_span_force_moment_cards`, GID bands `4001+` (h-tail) / `4501+` (v-tail),
  `GRID` on the LRA at real airplane positions, strip loads applied **directly**
  (not differenced from a cumulative column), and a `$` header stating the
  control-load mode and that the deck **supersedes** the fuselage deck's point
  tail-load station for any combined-airframe sum. Surfaces: the **Tail Span
  Loads** page, the Export page, `cli.py --export-target htail-span|vtail-span`.
  The chordwise TAILDIST path and every Appendix A figure are unchanged.
- **Empennage mass and the fin's two axes (2026-08-10).** The surface weight is
  **derived from `weight.items`** — the `htail`/`vtail`-tagged rows, through
  `mass_distribution.tail_surface_weight` — with `TailMassInput.panel_weight_lb`
  as an explicit override (`weight_is_override`) and the gap always reported
  (`tail_reconciliation`); a surface with no tagged item is named as a data gap,
  not reported as weightless. Until this step no fixture entered a `tail_mass` at
  all and *every h-tail deck was air-only*. Each surface's inertia is built on
  the acceleration along **its own normal axis**: `−n_z·W_ht` for the h-tail;
  for the fin, `−n_y·W_vt` bending with `n_y = (LT25+LT50)/W_case` **plus**
  `−n_z·W_vt` **axial** along the span (`f_span`/`s_span`, mapped by
  `coordinates.tail_axial_to_airplane`, emitted in the same `FORCE` cards). The
  lateral term relieves the surface total by exactly `W_vt/W_case` and inherits
  decision L-7's lateral-aero caveat (which is an **under**-statement on `n_y`,
  so the relief itself is under-stated) — both stated in-band. A condition naming
  no V-n point gets no lateral term. Load factors are resolved through
  `select.vn_points`, the single owner's tolerant read; reading
  `project.envelope` directly made every *exported* deck take the `n = 1.0`
  fallback (see the envelope-owner rule below).
  Mass is entered **only** on the Weights page's `component` column — the Tail
  Span Loads page shows the derived weight read-only and owns no mass input.
- **Discrete control surfaces and the first hinge moment (step T6, 2026-08-13).**
  `TailMassInput.control_load_mode = "discrete"` (per surface, with
  `hinges_span_in` + `actuator_span_in`) takes the control surface's own load
  **out** of the smeared strips — over the span its hinges hold, normalised so
  exactly that load leaves — and applies it at dedicated hinge `GRID`s on the LRA
  by chord-weighted tributary span, with the hinge-moment couple at the actuator
  node. GID bands `5001+` (elevator) / `5301+` (rudder). The control load is
  **SELECT's own** (`elevator_load` / `load_on_rudder`, oracle-locked, split into
  its camber and angle-of-attack parts so each leaves the distribution at the
  chord station TAILDIST put it at) where the condition publishes one, and is
  **derived from TAILDIST's aft-of-hinge pressure block and marked** where it
  does not. The **hinge moment** — the suite's first — is that load on a third of
  the aft-of-hinge chord, the centroid of a block that is always a triangle
  because the net trailing-edge pressure is identically zero; it is reported as a
  `LoadValue`, shown on the page and stated in the deck `$` header. Selecting the
  mode without attachment geometry raises. `"smeared"` remains the default and is
  unchanged to the byte.
- **T-tail transfer (step T7, 2026-08-13).** Gated on
  `layout.tail_type == T_TAIL` — the enum's first load-path consumer. Each
  v-tail case's deck carries the horizontal tail's concurrent set at the fin's
  **last** `GRID` (no new node): the balancing tail load at that case's own V-n
  point plus the h-tail's inertia there (`−n·W_ht`), as a vertical `FORCE` and
  the `MOMENT` its two lever arms make — the balancing load at the tail CP
  `envelope.tail_balance` publishes, the mass at the planform's own centroid.
  Roll and yaw transfer are zero (the pairing is a balancing condition, so the
  halves cancel). Mapped by `coordinates.ttail_transfer_to_airplane`, the one
  load in a fin deck that is not in the fin's local frame. Conventional layouts
  are bit-identical to the T4 deck.
- **CONM2 mass export (step C1–C5, 2026-08-08).** `sloads/export/mass_cards.py`
  writes the itemized mass model as `CONM2` cards with one `MASSSET` per
  *derivable* payload case, in three artifacts: a pasteable fragment, a
  self-contained runnable mass-check deck (`MASSSET` + `GRAV`, massless beam,
  **no load cards**), and sloads' inertia-only set for comparison. EID bands:
  baseline `9001+`, discretionary overlay `9101+`, per-case ballast `9201+`,
  `MASSSET` SIDs `9301+`, `GRAV` SIDs `9401+` — disjoint from every GID band.
  A payload case is exported only when the weight database can produce it as a
  loading within the ballast-credibility gate; the rest are reported with the
  number and the reason. Surfaces: `cli.py --export-conm2` /
  `--export-target mass`, the Weights page's **Mass Export** tab, and — since
  0.5.0 row 1 (**D-R2**) — the Export page's bundle `.zip` and its own download
  row, all three files stamped like every other deck.
  **Mass-case identity has one mint (0.5.0 row 1).** `massset_identity(loading,
  index) -> (SID, LABEL)` is the sole source of a payload case's identity in the
  exported model; the `MASSSET` card, the report's mass-case table and the
  bundle manifest all read it, and `mass_case_rows(project)` is the row form
  (every case, exported or not, with the loading's own weight/CG and its ballast
  fraction).
  **`GRAV` magnitude (2026-08-10, review finding C1).** The acceleration a deck
  carries is one standard gravity **in that deck's own length unit** —
  386.0886 in/s² Imperial, 9806.65 mm/s² SI — owned by
  `units.DeliverableUnits.gravity` (`force.factor / mass.factor`) and by nothing
  else. It is *not* the mass channel's dimensional identity
  `force/(mass × length)`, which is 386.0886 in **both** systems by
  construction; using that as the card value shipped an SI deck 25.4× low.
  **Inertia-only artifact (2026-08-10).** `inertia_only_cards` writes the gross
  Ch 15 beam table by default (unchanged), and *that payload case's* mass — wing
  items included, on the node their `CONM2` hangs on — when given a `loading`.
  The per-case form is what the CONM2 round-trip leg compares sbeam's recovery
  against card for card; the gross form cannot be equal to it, because the
  `MASSSET` model is per case and carries the wing.
  **Solver gate (plan 12 C6, 2026-08-10).** The mass-check deck is the round-trip
  harness's fourth deck family, solved in **both** unit systems: sbeam
  accelerates the `CONM2` set and must reproduce the per-case inertia at every
  node. Known sbeam limitation, pinned in `tests/test_sbeam_roundtrip.py`: SOL
  101 builds its `GRAV` load vector from the **baseline** mass and never reaches
  the `MASSSET` resolver, so the leg folds each case into a baseline deck
  (`export/roundtrip.flatten_mass_case`, test-only) to get the case's own mass
  accelerated.
- **Fuselage beam mass (step B1, 2026-08-08).** `body_loads` integrates the station
  table from `mass_distribution.fuselage_beam_stations`, **derived** from the
  component-tagged `weight.items` database — not `fuselage_mass.stations`, which is
  now an explicit override (`stations_are_override`). The beam carries every item
  not tagged `wing`, the empennage included; the wing enters as the carry-through
  reaction. A project therefore needs no hand-entered station table to have
  fuselage loads at all. See `CONVENTIONS.md` §1 and
  `docs/20_theory/00_theory_sources.md`.
- **`GRID` cards and the stated closure (step 1, 2026-08-08).** Every deck states
  the closure it satisfies in its `$` header and carries the geometry to verify
  it:

  | Deck | `GRID` cards | Stated closure, re-derivable from the deck's own text |
  |---|---|---|
  | Wing cards | no (geometry is in the stick deck beside it) | Σ`FORCE`.Fz/Fx = SF × root `Sz`/`Sx`; Σ`MOMENT`.My = SF × root `Myy` |
  | Wing stick | yes (root node + one per station) | the above, plus Σ`FORCE` moment **+ applied `MOMENT` Mx/Mz** about *any* station = SF × that station's `Mxx`/`Mzz` (the offset couples make this hold at every node, not only the root) |
  | Body | **yes** (one per station, `y = z = 0`) | Σ`FORCE`.Fz = 0 **and** its moment about the aft-most `GRID` = 0 (free-free, Ch 15 p103). The other four components are gated at zero too (2026-08-10, review F-G1's sweep) — zero *by construction* on a planar flight-only deck, so a non-zero one is a card in a DOF this deck does not carry; the ground cases will restate the claim |
  | Tail | **yes** (one per chord station, `y = z = 0`; **separate GID block per component**) | Σ`FORCE` = SF × (`LT25`+`LT50`) **on the surface's own normal axis** — `Fz` for the h-tail, `Fy` for the fin, via `coordinates.tail_force_to_airplane` as the spanwise family does (2026-08-10, review F-C3 / D-R4); the chordwise first moment (`My`/`Mz` respectively) matches the profile. Each case block names its axis in-band |
  | Control surface | **no, by design** | Σ`FORCE`.Fz = SF × the critical surface load. `ControlSurfaceStation.x` is a *fraction of chord* and the result carries no chord length, so the deck can carry no geometry; it says so in-band |

  **Id bands are owned by `sloads/export/bands.py`** (2026-08-10, review
  F-C1/F-G3) — the single registry of every GID, EID and SID run in the suite,
  with the whole map in its module docstring. Every allocator goes through
  `Band.allocate`, which raises on overflow rather than walking into the next
  family. GID blocks: wing `1–1000`, body mass `1001–1500`, body
  carry-through/correction `1501–2000`, chordwise h-tail `2001–2100`, chordwise
  v-tail `2101–2200`, control surface `3001–4000`, spanwise h-tail `4001–4500`,
  spanwise v-tail `4501–5000`, balanced deck `6001–7000`. The h-tail and v-tail
  chordwise split (step 1) is required because the two components have different
  average chords, so their chord stations are different points. Disjointness is
  proved over the **whole registry** by `tests/test_bands.py`, which also
  requires every id-base constant in `sloads/export` to be a registered band —
  the previous hand-enumerated guards were blind to the balanced deck, which
  collided with the spanwise tail bands from step B5 until 2026-08-10.
- **The closure gate** is `sloads/export/equilibrium.py` — the single owner of
  "parse a deck, re-derive Σ`FORCE`/Σ`MOMENT` from its card text about a stated
  reference point, and compare at the export-boundary tolerance"
  (`parse_cards`, `card_totals`, `resultant`, `deck_resultants`, `closes`). Every
  deck-closure check in the suite goes through it; `tests/test_export_equilibrium.py`
  sweeps every example × {Imperial, SI} × every deck family.
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
  the exported cards cannot disagree, even for a future non-1.5 case (M4-8 — since
  2026-08-14 the factor both sides read is written by the governing safety-factor
  table, `sloads/safety_factors.py`).
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
  a self-contained free-field reader round-trips the cards in tests; and the
  decks are **solved in the real sbeam by a standing CI gate** (step 2,
  `tests/test_sbeam_roundtrip.py`, job `sbeam-roundtrip`) — no longer a manual
  verification step. The gate covers `ga6_normal` + `concept_regional_jet` ×
  {Imperial, SI} and asserts, per case: the wing stick deck's reaction and its
  element-1 end-B internal loads against the NETLOADS root quadrature; the
  fuselage deck's whole Ch 15 cumulative shear/bending table, recovered by the
  solver from the cards and `GRID`s alone, on a determinate support whose
  reactions must be zero; the tail deck's total and chordwise first moment; and
  the assembled full-span deck's six reaction components, all zero. Body and tail
  are solved through a **test-only** stick wrapper (`sloads/export/roundtrip.py`)
  that supplies elements from the deck's own `GRID` cards and is never written by
  the CLI or the GUI; control-surface decks are permanently out of scope (their
  chordwise `x` is a fraction of chord, so there is no geometry to solve). The
  solver enters as a pinned optional extra, `pip install -e '.[solver]'`.
- **CLI — the whole deliverable menu is headless (0.5.0 row 1, review F-D1).**
  `python cli.py --export-sbeam <prefix> <project.json> --export-target <t>
  [--stick-model]`, where `<t>` is one of `wing` (default), `body`, `tail`,
  `htail-span`, `vtail-span`, `control`, `balanced` (the assembled full-span
  free-free deck — the mission's primary deliverable, previously writable only
  from the Balanced Cases page) or `mass` (the CONM2/MASSSET model; the same
  owner and the same file names as `--export-conm2`, which is kept because it
  shipped first). `cli.EXPORT_TARGETS` is the single list, handed to argparse
  and pinned against the CLI docstring by
  `tests/test_cli.py::test_the_export_menu_is_the_deliverable_menu`.
- **CLI wing decks are stated about the loads reference axis** (decision **D-R5**,
  review F-C2). The headless route transfers through
  `net_loads.loads_ref_axis_results` exactly as the GUI/report route does, so the
  two front-ends emit the same deck and the module contract ("an export built
  from a `Project` first transfers to the LRA") holds on the route the sizing
  loop scripts. The axis travels in-band (span-CSV `MyyAxis`, deck `$` header) and
  is pinned by `test_the_cli_wing_deck_is_stated_about_the_loads_reference_axis`
  on a project whose LRA is *not* the quarter chord — on every shipped fixture
  `ref_axis_pct` is 0.25, so the transfer is a no-op and exported bytes are
  unchanged.
- **Every headless CSV/BDF carries the Step G8.3 methods & limitations stamp**
  (L-8g / review F-D3), including `-o` module CSVs and the `--export-conm2`
  artifacts: one stamp per run, built from the resolved unit system and handed to
  every writer, so the files of one export cannot disagree about their basis or
  their units. Scope is always the full case set (the Critical Loads opt-out is
  GUI session state). No timestamp unless `--generated` supplies one, so two
  headless runs of one project are byte-identical and diffable.
- **One CLI error contract** (review m2): an absent or invalid input is
  `error: <message>` on stderr with exit status 1 — never a traceback, never a
  partial artifact set, on every route (module run, sbeam export, mass export).
  The single exception is the `control` target, where an **absent**
  control-surface slice (`MissingInputError`) skips that surface because the
  three are independent inputs, while an **invalid** one (plain `ValueError`)
  fails the run; a target where every surface is absent fails too. This is the
  `00_program_overview.md` error-handling contract applied at the CLI boundary.
- **Deck case identity — `SUBCASE`/`SID` numbering (M4-2).** Every deck's
  `SUBCASE` and its load-set `SID` are the **same integer**, and that integer is
  the case's own id through `case_ids.subcase_id`: a per-component block of 100
  plus the sequence number (`W-03` → 103, `HT-02` → 202, `VT-31` → 331,
  `F-04` → 404, `EM` → 5nn, `LG` → 6nn). Consequences, all of them the point:
  a filtered export cannot renumber the cases that survive; wing/tail/body/gear
  sets stay disjoint in an assembled multi-component deck (L-1); and
  `LOAD = 103` inside `SUBCASE 103` reads as one thing. Each deck opens with a
  `$` **subcase-map block** (`sbeam_bridge.subcase_map_block`) — one
  `$ SUBCASE 103 = W-03 -- PHAA -- FAR 23.333(b)` line per exported case — the
  assembled deck's own map block leads with the case id the same way — so a deck
  consumer can trace a solver result back to its governing condition from the
  deck alone. `sid_base + index` survives **only** as the fallback for a result
  carrying no `CaseRef` at all (a bare result list built in a test).
- **The linkage in the deliverables (design note 17, 2026-08-13).** The case id
  is also the deck's `LABEL`, so id, `LABEL` and `LOAD`/`SUBCASE` are one
  identity in three notations. Because there are two minters, a case can hold
  **two** deck numbers, and every document therefore states **both, qualified by
  deck family**: the case index (report table and CSV) carries
  `LOAD/SUBCASE (component)` and `LOAD/SUBCASE (assembled)`, each filled only
  where the case is actually in that deck — a handed id fills the assembled
  column alone, a symmetric case that also assembles fills both. The number's
  single owner is `case_ids.deck_load_id`, its display formatter (every GUI case
  label) `case_ids.case_label`; a case with no number in the family being quoted
  shows an em dash and **never** the positional fallback. Gates:
  `tests/test_case_ids.py::test_the_index_quotes_the_decks_own_numbers` (checked
  against the decks' own text), `::test_a_case_in_the_index_always_carries_at_least_one_deck_number`,
  `::test_a_handed_case_is_numbered_in_the_assembled_deck_only`,
  `::test_the_report_case_index_states_the_same_pairs_as_the_csv`.
  The **assembled full-span deck** (`export/balanced_deck.case_sids`) mints the
  same way, through `case_ids.balanced_subcase_id`: a per-**hand** block plus the
  case's own `subcase_id` — symmetric `5000`, starboard `7000`, port `8000`
  (`W-05R` → `7105`, `W-05L` → `8105`, `VT-01R` → `7301`). It is the only family
  carrying handed twins, and an integer `SUBCASE` has nowhere to put the `L`/`R`
  suffix; `6000` is skipped because that is this deck's own GID range. Positional
  numbering here was decision **D-R7**'s subject (review **m1**) and is retired
  except as the same no-`CaseRef` fallback, banded at `5001-5100` so it cannot
  land on a minted id. Two cases minting one id (the same `CaseRef` and hand
  assembled twice) is refused, not merged.

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
  `envelope.critical`'s, so they always export the full set. Since M4-2 the
  filter cannot renumber what survives: a deck's `SUBCASE`/`SID` is derived from
  the case id, not from its position in the exported list (below).

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

### Summary report — the bundle's controlling document (Step G8)
- **Source:** `sloads/report/content.py` (`build_report`, `component_loads`),
  `latex.py` (`render_report`/`render_document`), `plots_tex.py` (the three
  figures), and `sloads/export/pdf.py` (`compile_pdf`, the only impure piece).
- **Content standard:** [`SUMMARY_REPORT.md`](SUMMARY_REPORT.md) — required
  sections, marking rules and the excluded-content list. That file is normative;
  this entry is the data-flow summary.
- **Reads:** a `Project`, `registry.run_all_modules(project)`, and the four
  distributed-load families through `component_loads()` (which recomputes
  `build_net_loads`+`loads_ref_axis_results`, `build_body_loads`,
  `build_tail_chordwise`, aileron/flap/tab, and `build_critical`). Figures come
  from `vn_diagram.build_vn_diagram`, `weight_envelope.loading_envelope_points`
  and `mach_limit.mach_limit_lines`. **Nothing is recomputed here** — the
  governing tables are `report.governing_loads_table`'s own rows.
- **§6 Balanced free-free airframe cases (0.5.0 row 1, decision D-R2, review
  F-D2).** The assembled model is the primary deliverable and now has its own
  section: per-case `Nz`, pre-closure residuals, roll couple and closure relief
  from `export.balanced_deck.balanced_case_rows` (the *same* rows the deck and
  the Balanced Cases page render), the handed twin-pair statement, and the
  mass-case identity table — which payload case is which `MASSSET`, from
  `export.mass_cards.massset_identity`/`mass_case_rows`, with non-derivable
  cases marked NOT EXPORTED and their reason. `content.balanced_run(project)`
  assembles **once** per document and is shared with §4's skipped-conditions
  table (F-C7), so the two cannot describe different runs. A project that
  assembles nothing keeps the section and states the absence (§3.4). The
  manifest lists `balanced_airframe.bdf` and the three mass-model files, and
  lists them only when the bundle will actually contain them.
- **Section numbering has one owner (review F-R2, 2026-08-10).**
  `content.SECTIONS` is the ordered `(key, title)` list; headings come from
  `section_heading(key)` and **every** cross-reference — rendered prose and the
  manifest's "Summarised in" column alike — from `section_ref(key[, subsection])`.
  A `"§4"` written as a literal is a defect: the §2 sign-conventions insertion
  left three manifest rows pointing one section short and the §6 balanced
  insertion moved methods to §7 without them, because each number was typed in
  two places. Guarded in `tests/test_report_content.py` by the numbering-owner
  agreement test, the per-file `SUMMARISED_IN` pin (exhaustive on the GA
  fixture), the reference-resolves test (a suffix must name a real subsection —
  "§5 Tails" named none) and a document-wide sweep for out-of-range references.
- **Writes:** `.tex` (always) and, when a TeX engine is available, `.pdf`. Both
  ship in the Export page's `.zip` beside the CSV/BDF files they describe.
  All loads ULTIMATE with a per-case `SF`; the whole document renders in the
  selected unit system (`deliverable_units(system, Channel.HUMAN)`), and its
  manifest names the sbeam decks' consistent solver set beside it (D-19).
- **Used by** the Export page's **Summary report** section and
  `cli.py --report out.tex|out.pdf [--units …] [--generated …]`.
- **Absence is content:** a section whose inputs are missing renders its reason,
  never an empty table or axis — so the report doubles as the gap list.

---

## Cross-module field ownership (the shared schema at a glance)

Derived from **User's Guide Table 2.2** (the authoritative input→output map):

| `Project` slice | Owned by | Read by |
|-----------------|----------|---------|
| `weight` (components, empty/MTOW) | WTESTIMA | WTONECG, WTENV |
| `weight.cg_cases` (named loading scenarios, each tagged with the `analyses` it is run for) | Weight & Mass Properties page, Payload Cases tab — the **sole** editor (Step G3; Step D5; decision **G-3**) | **everything, through `sloads.cg_cases`**: FLTLOADS/SELECT/WINGINER/NETLOADS/BALLOADS take the `FLIGHT` set, LANDLOAD the three roled `GROUND` cases, weight_envelope the chart overlay |
| `weight.max_landing_weight_lb` / `.max_takeoff_weight_lb` (MLW / MTOW) | Weight & Mass Properties page, Weight / CG Envelope tab (decisions **G-4** / **G-14**) | LGFACTOR + LANDLOAD (`WR = MTOW/MLW`, `K0` from MLW); `select` (fin design weight, fuselage wing weight); the FAR 23 applicability gate |
| `weight.envelope` (useful-load envelope) | WTENV | FLTLOADS |
| `mass` (weight/CG + inertias) | WTONECG `build_mass`, via the Weight & Mass **Apply weight items** handler (M4-17a) | FLTLOADS (weight/CG); SELECT, ONENGOUT (inertia); `configuration.cg_estimate` ("Weight DB" branch); the Payload Cases tab's landing seed — waterline only (**LANDLOAD itself reads the roled `GROUND` cases, not `mass`**) |
| `geometry.surfaces[<surface>]` | WINGGEOM | STRSPEED, AIRLOADS, AIRLOAD4, FLTLOADS, SELECT, ONENGOUT |
| `geometry.parametric` (`LayoutInput`: fuselage/wing/tail/gear) + `geometry.fuselage` (`FuselageOutline` station-area table, Step G1) | configuration (modern; no `.BAS`) — the one **Geometry** page | seeds WINGGEOM (`geometry.surfaces[wing]`); reads `weight.envelope`, `engine`; `fuselage` → Step G4 estimator |
| `speeds` (V_A/C/D, n, mach) | STRSPEED, MACHLIM | FLTLOADS, AILERON, FLAPLOAD |
| `aero_coeffs` (airplane-less-tail CL/CD/CM, cruise + flaps-down; **`clmax_clean`/`clmax_clean_neg`/`clmax_flap`** stall-speed source, M1-1b; + `fuselage_moment` Munk ΔM1, Step G4) | Aerodynamic Data page (`aero_coefficients` key, Step D4.1; formerly `FlightLoadsInput.configurations`) | FLTLOADS (polynomials + per-config `stall_cl` clamp); **STRSPEED / FLAPLOAD / ONENGOUT (CLmax → VS/VSF)** |
| `aero` (tau, spanwise) | TAU, AIRLOADS/AIRLOAD4 | SELECT, NETLOADS (and AIRLOADS↔SELECT iterate) |
| `envelope.vn / tail_balance` | FLTLOADS | SELECT, WINGINER |
| `envelope.critical` | SELECT | AIRLOADS, AIRLOAD4, WINGINER, TAILDIST |
| `envelope.critical.selected_case_ids` (opt-out GUI selection, Step D5) | Flight Envelope (V-n) page, Critical Loads tab (Step G3) | Results Review page (display filter only); Export page (fuselage/tail sbeam artifacts + case index only, Step D8.3 — structural calc modules keep reading `envelope.critical.conditions` unfiltered) |
| `loads.wing_inertia` | WINGINER | NETLOADS |
| `landing` (LGFACTOR strut/tyre scalars + the gear-load-factor override) | LGFACTOR (N returned on `LoadFactorResult`, not stored — M2R-4) | LANDLOAD; reads the roled `GROUND` cases and both design weights from `weight` (G-3/G-4/G-14), `geometry.landing_gear` (gear), `geometry.wing` (area) |
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
- **One ID per physical condition (M4-2).** Where two modules deliver the same
  case — SELECT names the governing wing point, WINGINER/NETLOADS distribute it
  spanwise — they carry the *same* `case_id`: `wing_inertia.wing_case_ref`
  returns SELECT's ref when the condition matches by name, and the case index's
  dedupe-by-`case_id` collapses the two deliverables to one row. **The flight
  condition stated is the case's own** (user decision 2026-08-13): where
  `WingLoadCase` states a `v_eas_kt`, that is the speed the loads were computed
  at (`net_loads._air_cl_v`), so it is the speed the `CaseRef` — and therefore
  the case-index row — states, even where SELECT named the same condition at a
  different V-n point (`atr42_100` enters `PHAA` at 170 kt against SELECT's
  185.85 kt). Only the speed moves: `case_id`, CG, altitude and the FAR
  reference stay SELECT's, since the case states none of them and they are
  properties of the physical condition the shared id names. Guarded by
  `tests/test_wing_case_derivation.py::
  test_every_wing_case_row_names_the_speed_its_loads_were_computed_at`. The wing `seq`
  is a property of the **condition**, from `case_ids.WING_SLOTS`
  (PHAA 1, PLAA 2, PMAA 3, NMAA 4, ACRL 5, TORS 6), not of its position in any
  list — so a missing pick leaves a gap instead of renumbering its neighbours,
  and the strings that `selected_case_ids` and already-exported decks reference
  do not float.
- **Band disjoint allocators that share a prefix.** Two independent counters
  over the *same* numeric range collide outright (verified in a smoke run:
  `select_wing`'s own `W-02` and WINGINER's `W-02` briefly meant two different
  cases before this was caught). `case_ids.py` reserves: `W-01..19` the fixed
  `WING_SLOTS` conditions (SELECT **and** the WINGINER/NETLOADS results derived
  from them — the same case, the same id), `W-20..39` a hand-authored wing case
  outside `WING_SLOTS`, `W-50..59` AILERON, `W-60..69` FLAPLOAD, `W-70+` a
  wing-hosted tab; `VT-30..49` ONENGOUT (23.367 — a different case from
  SELECT's v-tail picks, so its own band rather than SELECT's counter);
  `HT-50+`/`VT-50+` for TABLOADS' htail/vtail-hosted tabs. A new module minting
  into an existing prefix must claim its own band here, and
  `tests/test_case_ids.py` is the drift guard.
- **`WingMassInput.cases` derives from SELECT when empty (M4-2).**
  `wing_inertia.resolve_wing_cases` returns the hand-authored list untouched when
  there is one (explicit always wins, so every shipped example and every
  Appendix A oracle takes the path it always did) and otherwise builds one case
  per `envelope.critical` wing condition. The Wing Loads page's **Pull cases from
  SELECT** button materialises the same list into the editable table. Known
  limitation: a derived ACRL case carries no unbalanced rolling moment, and its
  air-load CL/V differ from the worked example's — see the open defect in
  `docs/30_future/00_backlog.md`.
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

Counts reference 1's 22 Appendix-C programs only; the modern additions with no
`.BAS` — **configuration**, **body_loads**, **tail_span** and **balance**, each
sectioned above — are not counted here. The FAA
User's Guide exposes **20**
of these as menu modules — the two it omits are:
\* **TAU** (`TAU.EXE`/`TAU.BAS`), the lift-curve-slope helper folded into
`airloads.py`; and
† **BALLOADS** (`BALLOADS.BAS`), the post-FLTLOADS balanced-tail-load verification
utility (off-pipeline; ported in Step C11, reusing SELECT's balance routine). The
pipeline balancing calc lives in FLTLOADS and is refined rationally in SELECT.
