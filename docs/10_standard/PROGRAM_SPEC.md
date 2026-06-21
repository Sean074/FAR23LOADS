# FAR 23 LOADS — Program Specification

Per-module specification for replicating the 22-program **FAR 23 LOADS** suite.
Read alongside [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md), which defines the shared
architecture (hybrid package + multipage UI), the single-project-JSON / per-module
-CSV data model, the modernized-math fidelity decision, and the phased roadmap.

## Source documents

Two distinct manuals describe the suite — do not conflate them. **Both are in the
repo.**

- **Reference 1** — McMaster, *"FAR23 LOADS"* (Aero Science Software, Std v3.0 /
  Pro v1.0); file `FAR23 loads (1).pdf` (371 pp). The **theoretical** development
  and the project's authoritative **equation + validation oracle**: 20 chapters,
  **Appendix A** (6-place GA loads report, p131), **Appendix B** (10-place twin
  loads report, p251), **Appendix C** `.BAS` source listings (p373). Chapter
  numbers cited below as "Ch N" refer to *this* manual (and are correct — Ch 2
  WTESTIMA … Ch 19 ENGLOADS … Ch 20 LANDLOAD).
- **User's Guide** — *DOT/FAA/AR-96/46* (UDRI / P. Miedlar, March 1997; file
  `ADA324952.pdf`). The **operational** guide for a later FAA repackaging. Its
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
  correction helper; folds into `airloads.py` as planned. Not a menu module.

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

`Project` is the single shared input model (`farloads/models.py`). "Reads … from
`Project`" means those fields were produced by an upstream module or entered
directly; a module never recomputes another module's owned quantity.

---

## Phase 1 — Mass properties

### WTESTIMA — Weight estimation
- **FAR §:** 23.23, 23.25 (weight limits); supports the loading basis for all of Subpart C.
- **Source:** Ch 2, `WTESTIMA.BAS`.
- **Reads:** primary geometry & mission inputs (gross weight target, useful-load items, fuel, occupants, baggage, component weight fractions). Pipeline head — mostly direct input.
- **Writes:** empty weight, max take-off weight, component weight breakdown & stations → `Project.weight`.
- **Validation:** Appendix A 6-place GA — empty weight / CG and component weights as printed (e.g. mid weight 2063 lb @ x=73.09; empty 1822 lb @ x=75.03).
- **Notes:** Empty/takeoff weight ratio `K = 0.62` with adjustments (UG Table 3.1: multiengine +0.01, liquid-cooled +0.01, super/turbocharged +0.01, turboprop −0.05, pressurized +0.02, one-seat −0.04); `W_TO = W_use/(1−K)`. Component weights as %-of-TO-weight (UG Table 3.2). 170 lb/seat. Engine types: 4-cycle recip, 2-cycle recip, turbocharged, turboprop, liquid-cooled. FAR 23.25(b) minimum-weight rule (crew @ 170 lb + ½ hr fuel at max-continuous; turbojets 5% fuel capacity). **Feeds WTONECG *and* WTENV — they are parallel siblings off WTESTIMA, sharing one weight database; neither feeds the other.** As a UI convenience, `estimate_to_mass_items(inp)` expands the estimate's structure/powerplant/systems components (plus options/miscellaneous) into empty-weight `MassItem` rows — skipping the group totals and the propeller already inside "Engine installed" — to seed that shared database; the Weight Estimate page's "Seed Weight, CG & Inertia" button writes them to `Project.weight.items` with stations/inertias left at zero. The page also overlays the estimate's MTOW/OEW on a reference fleet (log-log Plotly scatter) loaded from `app/data/reference_aircraft.csv` — nominal published specs for visual sanity-checking only, never read by any calc. **Concept mode (Step C0):** the `K=0.62` regression is GA-calibrated and out of band above 12,500 lb, so in concept mode (`Project.is_concept`) WTESTIMA is flagged as a sanity-only estimate and the design weight comes from the **direct-weight path** `WeightInput.direct_totals()` — MTOW/OEW/useful summed straight from the itemized `MassItem` database by kind.

### WTENV — Weight vs CG envelope
> **Status: deferred to Phase 2.** WTENV's structural-CG limits need `XLEMAC`/`MAC`,
> which `WINGGEOM` owns, so it is ported alongside `WINGGEOM` (reading them from
> `Project.geometry`) rather than via an interim direct input. Its Streamlit page
> renders the envelope as a chart + tables.
- **FAR §:** 23.23 (load distribution), 23.25.
- **Source:** Ch 3, `WTENV.BAS`.
- **Reads:** `Project.weight` (component weights & stations), structural CG limits (fwd/aft gross, fwd-regardless), wing geometry (XLEMAC, MAC).
- **Writes:** weight/CG envelope of all possible loadings; structural-limit envelope; ballast weight & station to meet each limit → `Project.weight.envelope`.
- **Validation:** Appendix A — structural-limit stations (X_aft=85.1, X_fwd=77.49, X_fwd-regardless=72.64 from XLEMAC=63.641, MAC=69.246) and ballast (e.g. aft-gross ballast 78 lb @ x≈103.7).
- **Notes:** `X(limit) = XLEMAC + (percent/100)·MAC`. Shares the WTONECG weight database; computes the minimum flight weight and the envelope of all discretionary loadings (UG §5). Output (envelope of useful loads + CG) **feeds FLTLOADS only** (UG Table 2.2). Supports multi-category certification (e.g. normal n=3.8 @ 3400 lb ≡ acrobatic n=6 @ 2153 lb). Has a graphics output (envelope diagram) — render as a Streamlit chart.

### WTONECG — Weight & inertia for one configuration
- **FAR §:** 23.21/23.23; provides masses & inertias for dynamic/gyroscopic conditions.
- **Source:** Ch 4, `WTONECG.BAS`.
- **Reads:** `Project.weight` items (component weights + x,y,z locations). Computed at the **4 CG locations** of the structural-limits diagram (aft gross, fwd gross, most-fwd reduced, minimum weight) — ×2 (gear up/down) for retractable gear, so up to 8 loadings, not one.
- **Writes:** total weight, CG (x,y,z), and mass moments of inertia (Ixx, Iyy, Izz, products), output in **both slug-ft² and lb-in²**. *(Conceptually `→ Project.mass`; see Phase 1 note.)*
- **Validation:** Appendix A/B — CG and inertia for the example loadings.
- **Notes:** Per UG Table 2.2 / §4.5 the outputs split: **weight & CG → FLTLOADS, LANDLOAD**; **inertia → SELECT, ONENGOUT** (maneuver/gust balancing and unbalanced landing). Component inertia = transfer (parallel-axis) of each item about the airplane CG. Conceptually the same machinery as the engine/rotor inertia in `engloads`, at airplane scale — but ENGLOADS does **not** read `Project.mass` (it is standalone, UG Table 2.2).
- **Phase 1 implementation notes:** modules stay pure (`run → ModuleResult`); there is **no persisted `Project.mass` slice yet** — it is introduced when a consumer (FLTLOADS/LANDLOAD) lands. `WTESTIMA`/`WTONECG` results are a **property table**, so they render via `report.results_to_rows` / `module_text_report` (not the engine-specific `load_cases_to_rows`). The UI offers an SI **output** toggle: a weight is pounds-*mass* and converts to kg, distinguished from a pounds-*force* load (→ N) by `LoadValue.quantity="mass"`; inertia (slug-ft²/lb-in²) → kg·m², CG positions in→mm, angle (deg) unchanged. Inputs are entered in Imperial. See `units.py`.

---

## Phase 2 — Geometry & speeds

### WINGGEOM — Aerodynamic & surface geometry
- **FAR §:** geometry basis for 23.301+ airloads.
- **Source:** Ch 5, `WINGGEOM.BAS`. Largest module — runs once per surface.
- **Reads:** planform inputs per surface (root/tip chord, span, sweep, dihedral, incidence, station offsets) for: wing, horizontal & vertical tail, aileron, flap, elevator, rudder, tabs (the original keeps a `*GEOM.INP/.OUT` per surface).
- **Writes:** derived geometry per surface — MAC, XLEMAC, area, aspect ratio, spanwise station table, control-surface hinge geometry → `Project.geometry.<surface>`.
- **Validation:** Appendix A/B — MAC=69.246, XLEMAC=63.641 (wing) and the per-surface area/MAC tables.
- **Notes:** Many downstream modules read `geometry`. Model surfaces as a dict/list keyed by surface name so one calc serves all. Has graphics (planform plots).

### STRSPEED — Design speeds & maneuver load factors
- **FAR §:** 23.335 (design airspeeds), 23.337 (limit maneuver load factors), 23.333.
- **Source:** Ch 6, `STRSPEED.BAS`.
- **Reads:** `Project.weight` (W, W/S), `Project.geometry` (wing area), CL_max, category (normal/utility/acrobatic, or **concept `"C"`** — see Notes), chosen speeds.
- **Writes:** minimum-required & chosen V_A, V_C, V_D, V_S, gust speeds; limit maneuver load factors n1/n2 (pos/neg) → `Project.speeds`.
- **Validation:** Appendix A/B printed design-speed table and load factors (normal n=+3.8).
- **Notes:** Category drives the maneuver load-factor formula (23.337: n=2.1+24000/(W+10000), capped 3.8/utility 4.4/acrobatic 6.0; negative −0.4× positive for normal/utility, −0.5× for acrobatic — UG Table 7.1). **Concept mode (`category="C"`, Step C0)** bypasses the GA-only 23.337 formula and cap entirely: it requires explicit `chosen_n`/`chosen_nneg` and uses them verbatim (no FAR floor), so >12,500 lb concepts are not forced to a meaningless GA limit; the VC(min)/VD(min) coefficients become out-of-band advisories. `Project.is_concept` is the single concept read-point. STRSPEED also computes Mach limits at altitude (`T = 59 − 0.003566·h`; `a = 29.02·(T+459.4)^0.5`), so it overlaps MACHLIM — keep the shared atmosphere/Mach helper in one place. Feeds MACHLIM, FLTLOADS, AILERON, FLAPLOAD (UG Table 2.2).

### MACHLIM — Mach limit lines
- **FAR §:** 23.335(b) high-speed limit; compressibility.
- **Source:** Ch 6, `MACHLIM.BAS`.
- **Reads:** `Project.speeds`, altitude range, limiting Mach.
- **Writes:** Mach-limited speed vs altitude (the V-M limit line) → `Project.speeds.mach_limit`.
- **Validation:** Appendix B (high-altitude twin) Mach-limit table.
- **Notes:** Only material for high-performance/high-altitude airplanes (Appendix B). Graphics: V vs altitude limit line.

---

## Phase 3 — Aero coefficients & flight envelope

### TAU — Lift-curve-slope correction (built, folded into `airloads.py`)
- **FAR §:** supports 23.301 airload distribution.
- **Source:** Ch 7, `TAU.BAS` (curve-fit p407).
- **Reads:** wing aspect ratio (from the planform) + `AeroSurfaceInput.taper_ratio`/`tip_ratio`.
- **Writes:** τ correction factor for the wing lift-curve slope (the `_tau` helper in `airloads.py`; the per-surface value is also overridable via `AeroSurfaceInput.tau`).
- **Notes:** Not a separate module — implemented as the `_tau` quartic curve-fit (in taper ratio, interpolated by tip ratio per ANC(1) 1938) inside `airloads.py`, exactly as the original folds `TAU.EXE` into AIRLOADS.

### AIRLOADS — Spanwise lift distribution (built; AIRLOAD4 swept deferred to C7)
- **FAR §:** 23.301 (loads), 23.321+ (flight loads), 23.347+ asymmetric.
- **Source:** Ch 7, `AIRLOADS.BAS` (low speed). `AIRLOAD4.BAS` (sweepback, high Mach) is scheduled in Step C7.
- **Module:** `modules/airloads.py` (registers `"airloads"`).
- **Reads:** `Project.geometry` (wing planform polylines & strip count) + `Project.aero` (`AeroSurfaceInput`: section slope `mo`, taper/tip ratio for TAU, spanwise `twist` table, `target_cl`).
- **Writes:** the spanwise additive + basic + combined `c·cl` distribution (the `SpanwiseTable`) returned as a `ModuleResult`. The persisted `Project.aero.spanwise` result field is added when a consumer (FLTLOADS, C2) needs it.
- **Validation:** Appendix A spanwise tables (additive `CC(LA1)`/`C(LA1)`, basic `Awo`/`CC(lb)`/`Clb`, p161-162) within ±0.1%; concept closure (integrated `∫c·cl dy` recovers the target CL).
- **Notes:** Schrenk additional-lift method (average of planform-chord and elliptic distributions). Per UG Table 2.2 AIRLOADS↔SELECT is **iterative** (SELECT names the critical conditions, AIRLOADS computes airloads at them); the shared model must allow a module to both read and write the critical-load set — wired when SELECT lands (C6). The basic-distribution cosine fairing across a flap/aileron discontinuity (p47) is deferred (deflected-flap case only).

### FLTLOADS — Flight envelope (V-n) **+ balancing tail loads**
- **FAR §:** 23.333 (flight envelope), 23.337, 23.341 (gust), 23.345 (flaps), 23.421+ (balancing/horizontal tail loads), 23.423.
- **Source:** Ch 8, `FLTLOADS.BAS`. UG Table 2.1: *"Balancing calculations for flight envelope."*
- **Reads:** `Project.speeds` (STRSPEED — VA/VC/VD/VF, MC/MD and the limit load factors via the shared `_maneuver_load_factors`) and a new **`Project.flight_loads`** input slice (`FlightLoadsInput`): the geometry scalars `mac`/`wing_area_sqft`/`xw`/`zw`/`xtc`/`xtf`, the reference Mach `mn`, the altitude list, the airplane-*less-tail* aero-coefficient polynomials per configuration (`AeroCoeffSet`: CL(α), CD(CL), CM(α) + stall CLs) and the four weight-CG cases (`CgCase`). **As built (C2):** the aero polynomials come from the Ch 7 aero-coefficients program and are entered as input (AIRLOADS/C1 does not yet emit them); the CG cases are entered explicitly (seeding them from `Project.weight.envelope`/WTENV is a later refinement), so the original data-flow's `Project.mass` read is not needed for the balance.
- **Writes:** the full balanced V-n matrix (one `VnPoint` per condition × CG × altitude: V, NZ, α, G, CL, M(W+F), LZW, **LT**, DX) and the balancing tail load per point → **`Project.envelope`** (`EnvelopeResult.vn` + `.tail_balance`). The pure entry point is `flight_envelope.build_envelope(project) → EnvelopeResult`; `run(project)` returns the per-point `ModuleResult`. Persisting the result into `Project.envelope` is wired when a consumer lands (SELECT, C6 — mirrors the `aero.spanwise` precedent).
- **Validation:** Appendix A "V-n Data" p179-180 — the cruise balanced matrix per CG case. The AoA balance converges NZ only to ±0.005 (FLTLOADS.BAS line 4130), so low-load-factor quantities carry ~0.5% noise; LT and the corner speeds/load factors match tightly.
- **Notes:** Graphics: the V-n diagram. Faithful port of FLTLOADS.BAS subroutine **3900** (iterate AoA to the required load factor, then dynamic pressure to the Mach-adjusted stall line; Glauert compressibility `G/Gmn`; CLmax-vs-Mach curve) and **4864** (gust load factor, FAR 23.341). Balancing tail load `LT = [M(W+F) + LZ·(Xcg−Xw) − DX·(Zcg−Zw)]/(XT−Xcg)` with *approximate* tail CP (`XTC`≈5% tail MAC flaps-up, `XTF`≈25% flaps-down; Ch 8 "Assumption"). **Scope (C2):** the **cruise** maneuver+gust corner set (20 conditions, lines 1000-1594); the flapped LANDING/ENROUTE envelopes share the balance engine and drop in later. SELECT (C6) refines the CP rationally; `BALLOADS.BAS` independently verifies it. Produces the candidate conditions SELECT then prunes; feeds SELECT and WINGINER (UG Table 2.2). FLTLOADS uses its own speed-of-sound constant (518.688 vs the shared `standard_atmosphere`'s 518.4), replicated locally for oracle fidelity.

### SELECT — Critical load selection
> **Status: built (Step C6)** (`modules/select.py`, registers `"select"`).
> Oracle-locked against the Appendix A loads report (±0.1% + FLTLOADS' ~0.5% V-n
> noise): (1) the **wing** search (PHAA/PLAA/PMAA/NMAA + accelerated-roll + steady-
> roll TORS), (2) the **horizontal-tail** loads — balancing (23.421), unchecked/
> checked maneuver (23.423), gust (23.425(a)(1)/(2)) and unsymmetrical (23.427(a)),
> flaps retracted **and extended** (the exact SELECT.BAS subr-10000 large-deflection
> factor `EF(δ,Se/St)`), (3) the **vertical-tail** loads (23.441(a)(1)/(2)/(3),
> 23.443(b)), and (4) the **fuselage** critical conditions (23.301/23.331). The
> fuselage *net distribution* (Ch 15) lives in `modules/body_loads.py`. Inputs come
> from `Project.tail_loads`/`vtail_loads`/`select_input`/`fuselage_mass`. **Known
> limits** (recorded in the backlog): the flaps-extended path is closure-validated
> (the landing-config aero + CG5–7 fixtures needed for the *printed* oracle are not
> in the repo); the v-tail rudder `EFV≈1.0` is an input (illegible chart); SELECT's
> checked-maneuver `Iyy` / v-tail `IZZ` use the Ch 9 approximations (which match the
> oracle) rather than the now-persisted `Project.mass`.
- **FAR §:** 23.301 critical-load determination across the envelope.
- **Source:** Ch 9, `SELECT.BAS`.
- **Reads:** `Project.mass` (WTONECG inertia), `Project.geometry` (WINGGEOM), `Project.envelope.vn` (FLTLOADS); plus AIRLOADS/AIRLOAD4 spanwise airloads. Run once per component (wing, fuselage, htail, vtail).
- **Writes:** the governing (critical) flight-load set per surface → `Project.envelope.critical`. Per Ch 9 this is **much more than selection** — SELECT *computes* the rational critical loads: wing loads (PHAA/PMAA/PLAA/NMAA, accelerated & steady roll), rational + balancing + maneuvering + up/down-gust + unsymmetrical **horizontal** tail loads, **vertical** tail loads (23.441/23.443), and **fuselage** loads (23.301/23.331/23.351/23.471; Ch 9 + Ch 15 net fuselage).
- **Validation:** Appendix A/B — the selected critical points (`SELWGLDS/SELHTLDS/SELVTLDS/SELFSLDS`).
- **Notes:** Central junction. Reads V-n data from FLTLOADS + geometry (WINGGEOM) + inertia (WTONECG). Per UG Table 2.2 it feeds **AIRLOADS, AIRLOAD4 (iterative — see AIRLOADS), WINGINER, TAILDIST**. NETLOADS/component modules consume `critical` indirectly via those.

### BALLOADS — Rational balanced-tail-load verification (utility)
- **FAR §:** 23.421 (balancing loads); supports the 23.331 rational-balancing requirement.
- **Source:** Ch 8–9 (method), `BALLOADS.BAS` (Appendix C p497). **Not a FAA menu module.**
- **Reads:** the same V-n / geometry / mass inputs as FLTLOADS' balancing subroutine (run after FLTLOADS).
- **Writes:** rational balanced horizontal-tail load per balanced condition — load due to angle-of-attack at 25% chord (`LT25`), load due to camber at 50% chord (`LT50`), elevator deflection & elevator load. Worked hand-calc: 6-place case 202 → `LT = 519.845 lb`.
- **Validation:** Appendix A/B balanced-tail-load values (must match SELECT's rationally-recalculated `XTC`/`XTF`).
- **Notes:** Optional verification/teaching tool, not in the main pipeline; demonstrates the elevator load is **not** always opposite the stabilizer load. Implement as a standalone calc that cross-checks FLTLOADS/SELECT, or defer.

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
- **Reads:** a new **`Project.wing_mass`** input slice (`WingMassInput`): outboard panel weight, tip/root area-density ratio, inboard rib butt line, wing-reference-plane waterline + dihedral, concentrated wing masses, and the critical `WingLoadCase` list. The per-case `Nz`/`Nx` come straight from the FLTLOADS `envelope.vn` point (the C3-before-SELECT bridge — `Nz = −NZ`, `Nx = −DX/W`) when not given explicitly; plus `Project.geometry.<surface>`. (The original `envelope.critical`/`Project.mass` reads are deferred to SELECT, C6.)
- **Writes:** the spanwise wing inertia distribution per case → **`Project.loads.wing_inertia`** (one `WingLoadResult` of `WingStationLoad` each). Pure entry `wing_inertia.build_wing_inertia(project)`.
- **Validation:** Appendix A "Wing Inertia Loads" p217-221 — root/tip density 2.213/2.102 lb/ft²; unit vertical/drag/roll and the combined case 138 (Nz −2.54 Nx −0.1318: root Mxx −41041, Myy +11161).
- **Notes:** The panel mass is a linearly-tapered area density iterated to the entered panel weight; strips inboard of the rib carry no panel mass; concentrated weights add spanwise steps to the shears/moments. Subtracted from the air load in NETLOADS.

### NETLOADS — Net wing loads
- **FAR §:** 23.301(b) (net = air + inertia in equilibrium).
- **Source:** Ch 14, `NETLOADS.BAS`.
- **Reads:** `Project.wing_mass`, `Project.geometry.<surface>`, `Project.aero.<surface>` (and `Project.envelope.vn` for the per-case CL/V/Nz/Nx). Combines the AIRLOADS air-load distribution and the WINGINER inertia distribution.
- **Writes:** the net spanwise shear, bending moment and torsion along the 25% chord → **`Project.loads.wing_net`** (+ the air/inertia distributions in `Project.loads`) + a one-row-per-station CSV (`net_loads.wing_load_rows`). Pure entry `net_loads.build_net_loads(project)`.
- **Validation:** Appendix A "Net Loads, Case 22 PHAA" p222 (root Sz +5837, Mxx +455555, Myy -60940, Mzz -81483) — exact algebraic sum of the air (p206) and inertia distributions.
- **Notes:** A primary structural deliverable (root shear/BM/torsion). **Scope (C3):** the wing; full fidelity (all of Fx/Fz/Sx/Sz/Mxx/Myy/Mzz). SELECT (C6) will select the governing cases automatically; here they are supplied as `WingLoadCase`s referencing the V-n matrix.

### AILERON — Aileron loads
- **FAR §:** 23.349 (rolling), 23.455 (aileron).
- **Source:** Ch 16, `AILERON.BAS`.
- **Reads:** `Project.speeds` (STRSPEED — the design speeds/load factors, the only module input per UG Table 2.2), `Project.geometry.aileron`.
- **Writes:** aileron hinge moments & loads → CSV.
- **Validation:** Appendix A/B `AILERON.OUT`.

### FLAPLOAD — Flap loads
- **FAR §:** 23.345 (flaps), 23.457 (flap hinge).
- **Source:** Ch 17, `FLAPLOAD.BAS`.
- **Reads:** `Project.speeds` (STRSPEED — V_F etc., the module input per UG Table 2.2), `Project.geometry.flap`, `Project.aero`.
- **Writes:** flap loads & hinge moments → CSV.
- **Validation:** Appendix A/B `FLAPLOAD.OUT`.

### TABLOADS — Tab loads
- **FAR §:** 23.459 / control-tab loads.
- **Source:** Ch 18, `TABLOADS.BAS`.
- **Reads:** `Project.geometry.<tab>`, `Project.speeds`.
- **Writes:** tab loads & hinge moments → CSV.
- **Validation:** Appendix A/B tab-load tables.

### TAILDIST — Chordwise tail load distribution
- **FAR §:** 23.421+ tail loads, chordwise distribution.
- **Source:** Ch 10, `TAILDIST.BAS`.
- **Reads:** `Project.envelope.critical` (SELECT — the only module input per UG Table 2.2), `Project.geometry` (h-tail, v-tail). Handles 13 critical horizontal + 4 critical vertical load cases (UG §20).
- **Writes:** chordwise (rational) pressure/load distribution for htail & vtail (`TAILHLDS/TAILVLDS`, stalled `TLHSTALD/TLVSTALD`) → CSV; plots to `*.TLD`.
- **Validation:** Appendix A/B tail distribution tables.
- **Notes:** Produces the chordwise (rational) tail-load distribution (UG Table 2.1/2.3) for SELECT's critical horizontal & vertical tail loads. Net chordwise load = additive (angle-of-attack, 25% chord) + camber (50% chord) distributions (Ch 10). Replaces the arbitrary FAR Appendix B figures (pre-Amendment 42).

### ENGLOADS — Engine mount loads ✅ DONE
- **FAR §:** 23.361(a)(1)/(a)(2)/(a)(3), 23.361(b)(1), 23.363, 23.371(b).
- **Source:** Ch 19, `ENGLOADS.BAS`. Implemented in `engloads/` (becomes `farloads/modules/engine.py`).
- **Reads:** `Project.engine` (engine/prop weight, CG, diameter, RPM, HP/torque, rotor list, optional measured polar inertia), `Project.weight` load factor.
- **Writes:** the 3 (recip) / 6 (turboprop) FAR conditions; load-case CSV (one row per case, gyro 23.371(b) expands to 4 sign-combination cases).
- **Validation:** Appendix A (Continental IO-520-BB) and Appendix B (turboprop gyro). Currently exact; **relax to ±0.1% and switch to `math.pi` during Phase 0** per Decision 3.
- **Notes:** **Standalone** — no module inputs/outputs (UG Table 2.2); all data is direct input. Already supports measured-vs-approximated rotating inertia and SI/Imperial. Serves as the reference template for every other module's calc/units/report/CSV pattern.

### ONENGOUT — One-engine-out loads
- **FAR §:** 23.367 (unsymmetrical loads due to engine failure), multi-engine.
- **Source:** Ch 11, `ONENGOUT.BAS`.
- **Reads:** `Project.geometry` (WINGGEOM) and `Project.mass` (WTONECG) — the two module inputs per UG Table 2.2; plus `Project.engine[]` (multi-engine), `Project.speeds`.
- **Writes:** asymmetric **vertical-tail** loads from engine failure (UG Table 2.1: "One engine out vertical tail loads") → CSV.
- **Validation:** Appendix B (twin turboprop) one-engine-out tables.
- **Notes:** Needs the multi-engine project field (see Guide §8 open decision 2).

### LGFACTOR — Landing load factor
- **FAR §:** 23.473 (ground load conditions), 23.725 (drop test).
- **Source:** `LGFACTOR.BAS`.
- **Reads:** `Project.weight`, gear/tire/strut data, descent velocity.
- **Writes:** estimated landing load factor n → `Project.landing.n`.
- **Validation:** Appendix A/B `LGFACTOR.OUT`.
- **Notes:** Feeds LANDLOAD.

### LANDLOAD — Landing loads
- **FAR §:** 23.473–23.511 (ground loads: level, tail-down, one-wheel, side, braked).
- **Source:** Ch 20, `LANDLOAD.BAS`.
- **Reads:** `Project.landing.n` (LGFACTOR) and `Project.mass` (WTONECG weight/CG) — the two module inputs per UG Table 2.2; plus `Project.geometry` (gear geometry).
- **Writes:** landing-gear reaction loads for each ground condition → CSV.
- **Validation:** Appendix A/B `LANDLOAD.OUT`.
- **Notes:** **Tricycle gear only** (UG Table 2.1: "Landing loads for tricycle gear").

---

## Modern additions (no `.BAS` oracle)

These are registered calc modules with no original program and **no manual
regression oracle**; Appendix A/B geometry is used only as a *sanity* fixture.

### configuration — General configuration & layout (Step C5)
- **FAR §:** none (modern addition; geometric source of truth, not a FAR condition).
- **Source:** `farloads/modules/configuration.py`; method refs Reference 1 Ch 5
  (trapezoidal MAC) and Ch 8 (tail-volume neutral point).
- **Reads:** `Project.configuration` (`LayoutInput`: fuselage / parametric wing /
  tail areas+arms / gear); `Project.weight.envelope` (aft-gross %MAC for the static
  margin, optional); `Project.engine` (prop geometry for clearance, optional).
- **Writes:** derived MAC / XLEMAC / Y_MAC / AR / span (obtained by running the
  generated wing polylines through the WINGGEOM strip integrator — WINGGEOM stays
  the owner), horizontal tail volume, neutral-point %MAC + station, static margin,
  tip-back / overturn angles, prop ground clearance → `ConditionResult`s. The page
  also *seeds* `Project.geometry` with the generated wing `SurfaceInput`.
- **Validation:** **no oracle.** `tests/test_configuration.py` — analytic-vs-strip
  MAC consistency ±0.1%; Appendix A trapezoid plausibility (MAC 69.246 / MAC butt
  line 87.854, ±10%, since the real wing has an inboard strake).
- **Notes:** all stability/gear figures are first-order estimates (CG at 25% MAC
  when no mass slice is present; tail-volume NP with `h_acw=0.25`, `a_t/a_w=1`,
  `1−dε/dα=0.6`). In concept mode the results are flagged unverified extrapolation.

---

## Export bridges

These are **output renderers**, not registered calc modules: they read a results
slice and emit a file for an external tool. They live in `farloads/export/`,
return strings (with thin `write_*` file wrappers), and do no physics.

### sbeam export bridge — net wing load → sbeam (Step C4)
- **Source:** `farloads/export/sbeam_bridge.py`; card style mirrors
  `sbeam/results/load_export.py`.
- **Reads:** `Project.loads.wing_net` (NETLOADS) — accepts a `Project`, a list of
  `WingLoadResult`, or one result.
- **Writes:** (1) a **span-load CSV** (one row per wing station per case: applied
  nodal `Fx/Fz/My` + cumulative `Sx/Sz/Mxx/Myy/Mzz`); (2) **FORCE/MOMENT**
  bulk-data cards, comma free-field unit-scale form (`FORCE, SID, GID, 0, 1.0,
  Fx, Fy, Fz`, components `%.6E`), one load set (SID) per case; (3) an optional
  minimal **CBAR stick-model BDF** (GRID + CBAR chain + PBAR/MAT1 placeholder +
  root SPC1 + the load cards + a SOL 101 subcase per case).
- **Nodal loads:** the applied nodal force/torsion at each station is the
  *increment of the cumulative* NETLOADS column to the next station outboard, so
  the FORCE set sums to the root shear and the MOMENT(My) set to the root torsion
  **exactly**; under the WINGINER quadrature (`y[i]-y[0] = i·dy`) the FORCE
  moments about the root reproduce the root bending exactly.
- **Coordinates:** `farloads/export/coordinates.py` — FAR23LOADS station-X /
  butt-Y / waterline-Z inches → sbeam global CID 0, **identity** (single
  edit-point for any future sign/axis/unit change).
- **Validation:** force/moment closure (cards re-summed = NETLOADS root totals);
  a self-contained free-field reader round-trips the cards in tests; the stick
  deck parses **and solves SOL 101** in the real sbeam (manual verification step).
- **CLI:** `python cli.py --export-sbeam <prefix> <project.json> [--stick-model]`.

---

## Cross-module field ownership (the shared schema at a glance)

Derived from **User's Guide Table 2.2** (the authoritative input→output map):

| `Project` slice | Owned by | Read by |
|-----------------|----------|---------|
| `weight` (components, empty/MTOW) | WTESTIMA | WTONECG, WTENV |
| `weight.envelope` (useful-load envelope) | WTENV | FLTLOADS |
| `mass` (weight/CG + inertias) | WTONECG | FLTLOADS, LANDLOAD (weight/CG); SELECT, ONENGOUT (inertia) |
| `geometry.<surface>` | WINGGEOM | STRSPEED, AIRLOADS, AIRLOAD4, FLTLOADS, SELECT, ONENGOUT |
| `speeds` (V_A/C/D, n, mach) | STRSPEED, MACHLIM | FLTLOADS, AILERON, FLAPLOAD |
| `aero` (tau, spanwise) | TAU, AIRLOADS/AIRLOAD4 | SELECT, NETLOADS (and AIRLOADS↔SELECT iterate) |
| `envelope.vn / tail_balance` | FLTLOADS | SELECT, WINGINER |
| `envelope.critical` | SELECT | AIRLOADS, AIRLOAD4, WINGINER, TAILDIST |
| `loads.wing_inertia` | WINGINER | NETLOADS |
| `landing.n` | LGFACTOR | LANDLOAD |
| `engine[]` | direct input | ENGLOADS, ONENGOUT |
| `configuration` (`LayoutInput`: fuselage/wing/tail/gear) | configuration (modern; no `.BAS`) | seeds WINGGEOM (`geometry.wing`); reads `weight.envelope`, `engine` |
| `loads.wing_net` (net wing load) | NETLOADS | report/CSV export; **sbeam export bridge** (FORCE/MOMENT + stick model) |
| `loads.*` (per-module results) | each component module | report/CSV export only |
| *(verification only)* | BALLOADS | reads FLTLOADS data; no pipeline output |

This table is the build order in disguise: a module is ready to implement once
everything in its "Read by"/owner chain exists. Note the non-DAG / off-pipeline
edges: **AIRLOADS↔SELECT** iterate (aero ⇄ critical); **ENGLOADS / TABLOADS** are
standalone; **BALLOADS** is a post-FLTLOADS verification utility (no output that
other modules consume).

---

## Status summary

| Phase | Modules | Done | Remaining |
|-------|---------|------|-----------|
| 0 Restructure | engine → package | ✅ done (engloads → farloads, Project model, io/registry, app/) | 0 |
| 1 Mass | WTESTIMA, WTONECG, WTENV | 3 (WTESTIMA, WTONECG, WTENV) | 0 |
| 2 Geometry/Speeds | WINGGEOM, STRSPEED, MACHLIM | 3 (WINGGEOM, STRSPEED, MACHLIM) | 0 |
| 3 Aero/Envelope | TAU\*, AIRLOADS, AIRLOAD4, FLTLOADS, SELECT, BALLOADS† | 4 (TAU, AIRLOADS, FLTLOADS, SELECT) | 2 (AIRLOAD4, BALLOADS†) |
| 4 Component loads | WINGINER, NETLOADS, AILERON, FLAPLOAD, TABLOADS, TAILDIST, ENGLOADS, ONENGOUT, LGFACTOR, LANDLOAD | 3 (ENGLOADS, WINGINER, NETLOADS) | 7 |
| **Total** | **22** | **13** | **9** |

Counts reference 1's 22 Appendix-C programs only; the **configuration** module
(Step C5) is a modern addition with no `.BAS` and is not counted above. The FAA
User's Guide exposes **20**
of these as menu modules — the two it omits are:
\* **TAU** (`TAU.EXE`/`TAU.BAS`), the lift-curve-slope helper folded into
`airloads.py`; and
† **BALLOADS** (`BALLOADS.BAS`), the post-FLTLOADS balanced-tail-load verification
utility (off-pipeline; may be deferred). The pipeline balancing calc lives in
FLTLOADS and is refined rationally in SELECT.
