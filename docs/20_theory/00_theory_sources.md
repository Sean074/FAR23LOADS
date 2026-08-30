# Theory & Equation Sources

Every load equation in `sloads/` traces back to a printed source. This file is
the map from "the number in the code" to "the page it came from". **Per the
project's documentation requirement, cite the source in the code and the test
whenever you port or change a calculation** (see `CLAUDE.md`).

## Authoritative references (in `reference/`)

| Short name | File | Role |
|------------|------|------|
| **Reference 1** | `reference/FAR23Loads_Code.pdf` (371 pp) | McMaster's theory manual — the source of truth for **equations** *and* the **regression oracle**. Appendix A (6-place GA single) p131; Appendix B (10-place twin turboprop) p251; Appendix C `.BAS` source p373. |
| **FAA User's Guide** | `reference/FAR23Loads_UserGuide.pdf` (DOT/FAA/AR-96/46) | Module data-flow reference (Table 2.2) — which module consumes which upstream quantity. |
| **Brochure** | `reference/FAR-23-Loads-Brochure-2023.pdf` | Product overview / context. |
| **Digital DATCOM** | `reference/datcom/` (added 2026-08-15 — see its `PROVENANCE.md`) | USAF Digital DATCOM, the computer implementation of the *USAF Stability and Control DATCOM* chart methods (public domain, via PDAS). Carries the chart data as `DATA` statements, so a method can be ported without the printed charts. Used for the lateral body derivatives of decision **L-7** (`sloads/lateral_body_aero.py`, shipped 2026-08-17): wing-body `Cn_β` (DATCOM 5.2.3.1, subsonic subroutine `SUBLAT`, `datcom.f:29038-29052`; chart data `X158A..Y58C` at `:28723-28756`), wing-body `Cy_β` (5.2.1.1, `:29027-29036`) and the body lift-curve slope `CL_α,B` (4.2.1.1, `BODYRT`, `:2326-2462`); the interpolators `TLINEX`/`TLIN1X`/`TBFUNX` (`:40816`/`:40501`/`:39130`) are ported with their per-call extrapolation flags because the Fortran, not the printed chart, is what the sample output reproduces. **The oracle is its printed sample output** — the *applicable* subsonic body-alone / wing-body rows of `examples/ex1, ex3, ex4, ex5` (`ex2` wing-alone, `ex1` c3–4 / `ex4` c2 supersonic, `ex3` c2–5 experimental overrides, `ex7`/`ex8` fin-inclusive totals only, `ex9`–`11` hypersonic are inapplicable — note 19 rev. 3 decision L-7.8); because `reference/` is gitignored, `tests/test_lateral_body_aero.py` carries the printed numbers and case geometry as literals with this citation, exactly as the Appendix A tests do. |
| **Factor of safety** | `reference/14CFR_factor_of_safety.md` | Limit vs. ultimate: 14 CFR 23.303 / 25.303 (FS = 1.5); 23.302 / 25.302 / Appendix K (case-dependent factor for failure conditions, future). Basis for the ULTIMATE rendered/exported output. |

## Oracle status (canonical) <a id="oracle-status"></a>

**This is the single authoritative statement of how each module is validated; the
per-module "Oracle" column below and the READMEs/`PROGRAM_SPEC.md` defer to it —
do not restate it elsewhere.**

- **Appendix A (6-place GA single, p131) is the printed oracle and is *in hand*.**
  Modules whose GA-single figures appear there are **oracle-locked** — a
  `tests/test_<module>.py` asserts `run(project)` against the printed numbers within
  the ±0.1% tolerance (Decision-3 math modernization; see `PROJECT_GUIDE.md §6`).
- **Appendix B (10-place twin turboprop, p251) is *absent* from the bundled
  `reference/FAR23Loads_Code.pdf`.** Only the Appendix A GA single is present, and
  the FAA User's Guide (Ch 22) gives partial inputs / no outputs. So **no module has
  a printed Appendix-B twin oracle.**
- **Twin-only / turboprop-only cases are therefore *closure-locked*, not
  oracle-locked** — validated by sub-formula exactness against the `.BAS` source
  plus physics/integration closure, with the printed twin oracle recorded as a
  deferred item. This covers `one_engine_out` (no printed oracle) and the
  turbopropeller engine-mount cases (`engine` `23.361(a)(3)`, formula-checked).
- **A few Appendix-A cases are only *partially* oracle-locked** where the bundled
  scan is OCR-garbled — e.g. LANDLOAD's p231–233 wheel-load table (formula-closure +
  legible-cell spot-check). Called out per-module below.

## Limit vs. ultimate loads (ALL output is ULTIMATE)

The calc reproduces McMaster's **LIMIT** loads (the printed oracle figures), but
**all load output is ULTIMATE** — every force/moment/pressure that leaves the calc
(rendered table, text report, load-case CSV, sbeam export) is `ultimate = limit ×
SF`, never a bare limit load. The factor is the per-case factor of safety
(`ConditionResult.safety_factor`, default `constants.ULTIMATE_FACTOR = 1.5`,
**14 CFR 23.303**; Part 25 equivalent 25.303). It is applied only at the
render/export boundary and only to force/moment/pressure quantities, so the
regression oracles below (asserted on the calc's limit results) are unaffected.

The `ULT` marker is treated as **part of the units string** — force `lbs-ULT`
(SI `N-ULT`), moment `ft-lb-ULT` / `lb-in-ULT` (SI `Nm-ULT`), pressure
`lb/in^2-ULT` (`psi-ULT`) — and **every load case states its SF**. The per-case
field anticipates a 14 CFR 23.302/25.302 / Appendix K probability-based factor
(1.0–1.5) for failure conditions; sudden engine stoppage is currently held at 1.5.
A value already at ultimate (or an inherently-limit value reported as-ultimate with
no amplification) is `ULT SF=1.0`. See `reference/14CFR_factor_of_safety.md`.

### The governing safety-factor table (M4-8 / decision G-11, 2026-08-14)

The factor is no longer decided at the case. `sloads/safety_factors.py` holds one
row per **condition family**, and the family boundaries are **14 CFR Subpart C's own
section groupings** — this is why the table's granularity needs no separate
justification:

| family | sections | class | SF | citation |
|---|---|---|---|---|
| General structural loads | 23.301–23.307 | LIMIT | 1.5 | "Strength requirements are specified in terms of limit and ultimate loads" — **23.301(a)** |
| Flight loads (manoeuvre, gust, engine torque, gyroscopic) | 23.321–23.371 | LIMIT | 1.5 | flight load factors are prescribed as limit values — **23.321(a)** |
| Sudden engine stoppage | 23.367(a)(2) | ULTIMATE | 1.0 | the case is prescribed as an **ultimate** load — **23.367(a)(2)** |
| Control surface and system loads | 23.391–23.459 | LIMIT | 1.5 | **23.391**ff |
| Ground and landing loads | 23.471–23.511 | LIMIT | 1.5 | "The **limit** ground loads specified in this subpart…" — **23.471**; every embedded multiplier (1.33/0.83 **23.485**, 0.8 **23.493**, 2.25 **23.499**) is a limit quantity |
| Water loads | 23.521–23.537 | LIMIT | 1.5 | **23.521** |
| Emergency landing conditions | 23.561–23.562 | ULTIMATE | 1.0 | **ultimate** inertia load factors — **23.561(b)** |
| Weight/CG and configuration reference conditions | 23.21–23.29 | — | inert | not load cases; the factor is never applied to them |

Parts 23 and 25 number Subpart C in parallel, so one range table serves both. The
regulation text quoted above is in `reference/ug.txt` (verbatim CFR) and
`reference/14CFR_factor_of_safety.md` (§ 25.303).

**Why this is a closure gate rather than an oracle.** There is no printed figure to
match — the table's correctness claim is *reproduction*:
`tests/test_safety_factors.py` asserts, case by case on all six shipped fixtures,
that the table resolves exactly the factor the producing module mints, and that no
case falls through unclassified. Those two together are what make it an authority
rather than a second opinion.

### The two design weights and consumable fuel (step 10 piece 2, 2026-08-14)

Decisions **G-4**, **G-14** and **G-5**. Three rules whose authority is the
regulation, not the manual, so they are cited here rather than page-matched:

| rule | citation | what it fixes |
|---|---|---|
| The reduced landing weight is a design limit distinct from the take-off weight; LANDLOAD's level / tail-down / one-wheel cases use it and the side / braked-roll / nose-supplementary cases use MTOW via `WR = MTOW/MLW` | **14 CFR 23.473(b)/(c)** (and the manual's Ch 20 p126-130) | `landing.gross_weight_lb` fell back to `max(landing cg_cases)` — which is **MLW**, so `WR = 1.0` and cases 13-24 came out ~5 % light. `WeightInput` now owns both weights and there is no fallback. |
| A design landing weight is **fuel burned off**, not payload left behind, so a `GROUND` loading burns its `consumable` rows down — continuously and proportionally — before any discretionary subset is dropped | **14 CFR 23.473(b)/(c)** | Measured on ga6: the ballast-minimising subset search dropped the 6th person (x = 150) and kept all 409 lb of fuel (x = 70) — the right weight with the mass 80 in out of place, and on a wing-fuel airplane worse than misplaced, because burning fuel removes wing inertia relief and dropping a passenger does not. Burn-down reaches the case by burning **317 lb**, landing **0.12 in** from its target CG. |
| The gear reaction is computed at the **ground contact point** and any transfer to an airframe node is the tool's, not the regulation's | **14 CFR 23.485(d)**: "The side loads … are assumed to be applied at the ground contact point and the drag loads may be assumed to be zero." | It is why `LandingGearInput.attach` is an input with a resultant-preserving transfer rather than a place to compute the reaction. |
| The wing lift factor `L` is a certification-basis choice, not a physical cap: FAR 23 assumes wing lift **not exceeding two-thirds of the weight** through impact, FAR 25 permits **lift equal to the weight** | **14 CFR 23.473(g)** ("wing lift not exceeding two-thirds of the weight of the airplane … may be assumed"); **14 CFR 25.473(a)(2)** ("a wing lift not exceeding the airplane weight may be assumed to exist throughout the landing impact") | Note 37 (LF-4, #123): the former hard `L ≤ 0.667` refusal could not serve a FAR 25-basis concept; `L` is now a free input, both GUIs caption the two bases as guidance, and the honest bound is the 23.473(g) floors (`N ≥ 2.67`, `NLG ≥ 2.0` — refused in a FAR 23 category, warned in concept; `landing.far23_473g_floor_violations`, floors in `constants.py`). |

**Stated assumption (G-14):** MTOW is a **single scalar, constant between the
forward and aft CG limits**. On some airplanes it varies with CG (the 777 among
them) — a weight-dependent *upper* boundary of the weight-CG envelope, in
machinery that already expresses a weight-dependent boundary in the other
direction (`fwd_regardless_weight`). Recorded here rather than left implicit.

**Why these are closure gates rather than oracles.** No printed figure covers
them: the migration is claimed *output-neutral*, so the gate is that every
Appendix-A oracle and every fixture digest is unchanged, and that the
`FLIGHT`-tagged case set after migration equals the pre-hop `flight_loads.cg_cases`
exactly, per fixture (`tests/test_cg_cases.py`).

## How to cite

- **In test code:** keep the manual's printed figure *and* a page citation next
  to each assertion, so drift is traceable. The math is modernised (`math.pi`,
  clean equations, not the BASIC's `3.1416`), so the printed figures are
  **tolerance-based** oracles — `math.isclose(..., rel_tol=1e-3)` (±0.1%), exact
  equality only for integer/dimensionless quantities. See `PROJECT_GUIDE.md §6`.
- **In module code:** when a constant or formula is non-obvious, comment it with
  the FAR section (e.g. `23.361(a)(1)`) and/or the Reference 1 page.

## Per-module equation citations

Add a row here as each module is ported, pointing to the Reference 1 chapter/page
its equations come from and the Appendix A/B figures its test checks against.

| Module | `.BAS` source | Reference 1 location | Oracle (appendix figures) |
|--------|---------------|----------------------|---------------------------|
| `engine` (ENGLOADS) | `ENGLOADS.BAS` | Engine-mount loads chapter; theory walk-through + worked IO-520-BB example in [`engine_loads.md`](engine_loads.md) | Appendix A p131 / Appendix B p251. **Approved corrections (both per AC 23-19A, `reference/AC_23-19A_engine_torque.md`):** 23.361(c)'s mean-torque factor applies to *all* of paragraph (a), but the manual/`.BAS` leave the two takeoff-derived cases unfactored (Amdt 23-26 error, restored by Amdt 23-45). **(a)(1)** takeoff torque → `factor × mean takeoff` (manual 554.39 unfactored → IO-520-BB 737.34; manual figure kept as "mean takeoff torque" in `test_361_a1`). **(a)(3)** malfunction torque → `1.6 × 1.25 × mean takeoff` (manual/`.BAS` `TTP=1.6*ENGTORQ` apply 1.6 × mean only); no printed Appendix B engine-mount output exists in the bundled PDF, so it is formula-checked in `test_361_a3_applies_mean_torque_factor`. See the register of record `docs/20_theory/02_approved_corrections.md` (policy in CLAUDE.md).  **23.361(b)(1) sudden stoppage** has no printed engine-mount figure in the bundled Appendix B either, so it is closure-locked on `I·ω/Δt` summed over prop + rotors (`test_361_b1_closes_on_the_angular_momentum_formula`), with the reported whole-integer torque floored per ENGLOADS.BAS line 944's `INT(-TORQSUDSTOP)` (`reference/FAR23Loads_Code.pdf` p466) — CR-B-3. **LIMNZ/mass derive (note 36 OV-7, #97):** a blank `limit_load_factor` falsy-derives from the FAR 23.337 limit the design speeds own (`design_speed_values(project).n`), and with an `engine_mass_item`/`prop_mass_item` selector set the engine/prop weight and CG falsy-derive from the named weight-database row (decision D-25 mass SSOT); a typed value overrides (`engine_mass_row_mismatch` warns on disagreement) and a selector naming no row is refused by name. |
| `engine` — supplemental FAR 25 cases | n/a (not in ENGLOADS) | `reference/14CFR_Part25_engine_torque.md` (verbatim 14 CFR 25.361 decel/accel + 25.371 gyroscopic) | **No oracle** — formula-closure tested (`tests/test_engine_far25.py`). Reduced to the non-duplicative cases: (a)(3)(i) stoppage `@1g`; (a)(3)(ii) max-accel torque `@1g` (no FAR 23 analog); 25.371 fixed-rate gyro on A2 load factor. The torque cases (a)(1)(i)/(ii)/(iii) were removed as exact duplicates of the corrected 23.361(a)(1)/(a)(2)/(a)(3) (post AC 23-19A). Turbopropeller only; enabled by `Project.include_far25`. **25.371 under-prediction guard (P1-5):** optional advisory rates `EngineInput.design_yaw_rate_rad_s`/`design_pitch_rate_rad_s` flag the fixed 2.5/1.0 rad/s stand-in as non-conservative (`WARNING … UNDER-PREDICTED` note) when a declared rate exceeds it — warn-only (D-2), the moment is unchanged. |
| `weight_estimate` (WTESTIMA) | `WTESTIMA.BAS` | Ch 2; Appendix C p374-376 (`K`, fuel/component/engine-weight correlations; UG Tables 3.1/3.2) | Appendix A p133 (MTOW 3468, empty 2150, component breakdown) |
| `weight_onecg` (WTONECG) | `WTONECG.BAS` | Ch 4; Appendix C p377-381 (CG `S2/S1`; parallel-axis inertias ÷144·g; principal-axis rotation) | Appendix A p136 (aft gross: weight 3400, XBAR 84.999, ZBAR 92.579, IXX/IYY/IZZ 1201.5/2058.2/3022.8 slug-ft²)  **M4-17a:** no equation change — the persisted `Project.mass` slice is now produced by the GUI (the Weight & Mass **Apply weight items** handler calls `build_mass`) and by every bundled example, so its ZBAR is a real waterline source for the Landing Loads CG seed. |
| `wing_geometry` (WINGGEOM) | `WINGGEOM.BAS` | Ch 5; Appendix C geometry subroutine p409-410 (strip sum `A=ΣC·dy`, `MAC=ΣC²·dy/A`, `XLEMAC=XBAR−MAC/2`, `AR=(2·Ytip)²/2A`) | Appendix A p141 (wing: AREA/SIDE 13257, MAC 69.246, YLE(MAC) 87.854, XLE(MAC) 63.641, AR 6.095) |
| `weight_envelope` (WTENV) | `WTENV.BAS` | Ch 3 (`X(limit)=XLEMAC+pct·MAC/100`; ballast `WB=WL−WA`, `XB=(WL·XL−WA·XA)/WB`) | Ch 3 p21-22 (stations 85.1/77.49/72.64; min flight 2063@73.09; max load 3322@84.56; ballast wts 78/418/158). Aft-gross ballast station is the exact moment balance (~108.5); the manual hand-rounded to 103.7 (limit station 85.0 vs 85.107). **Ballast reference selection (M1-7, review T8):** each reference is the heaviest forward-loading vertex within the point's limit — the aft-gross reference is the heaviest loading **not exceeding gross** (mirroring forward-regardless), equal to the full loading on the GA6 (3322 → 78 lb, oracle unchanged) but correctly below gross on databases whose full loading exceeds gross (prior code used the full loading unconditionally → 0 ballast). Degenerate references (empty candidate set; loading already at/above the target weight; heaviest ≤-gross loading already at/aft of the aft-CG limit) emit an explicit `"(none — …)"` marker row rather than a dropped row or a nonphysical station (`test_aft_gross_uses_heaviest_loading_below_gross`, `test_aft_gross_degenerate_reference_reports_marker`, `test_ballast_marker_rows_not_dropped`). **Nonphysical ballast station (M1-11):** the forward-regardless reference is selected by weight only, so on synthetic over-gross concept databases whose loadings all sit aft of the forward limit the moment balance can land a ballast station outside the fuselage (e.g. dhc8_dash8 → −112 in, forward of the nose datum). A physical fore/aft station extent — explicit `envelope.fuselage_nose_x`/`fuselage_tail_x` override, else the Step G1 fuselage outline, else the station-0 datum with an unbounded tail — gates every computed ballast station; one outside it emits the same `"(none — …)"` marker (`test_fwd_regardless_station_outside_extent_marks_none`, `test_fwd_regardless_negative_station_marks_none_via_datum`, `test_fwd_regardless_station_inside_extent_kept`, `test_fwd_regardless_extent_from_geometry_outline_kept`). GA6 oracle (158 @ 71.08) unchanged — its stations are physical. **Limit-point flight cases (D-27, 2026-08-17):** the four structural-limit points FLTLOADS.BAS prompts for (Ch 3 p21: aft gross, fwd gross, fwd regardless, minimum weight) are seeded from this module's stations by `cg_cases.seed_flight_cases` (+ one `mid gross` case); on the GA6 the seed reproduces CG1..CG4 (3400 @ 85.1 / 77.49, 2800 @ 72.64, 2063 @ 73.09) to the printed rounding (`test_the_seed_reproduces_appendix_a_s_four_points_on_ga6`). |
| `structural_speeds` (STRSPEED) | `STRSPEED.BAS` | Theory walk-through in [`design_airspeeds.md`](design_airspeeds.md). Ch 6 (`n=2.1+24000/(W+10000)`; `VC_min=Kc·√(W/S)`; `VD=max(Kd·VCmin, 1.25·VC)` — the K_d term uses the *minimum* cruise VCmin, per STRSPEED.BAS `V2DMIN=K2·V1CMIN` lines 380/390 and FAR 23.335(b)(2); `VA=VS·√n`; `VF=max(1.4VS, 1.8VSF)` with **VS/VSF derived from CLmax** — `VS=√(295·(W/S)/CLmax_clean)`, `VSF=√(295·(W/S)/CLmax_flap)` at the design weight (M1-1b, User's Guide p7-5; CLmax is `aero_coeffs.clmax_clean`/`clmax_flap`, the single stall-speed source — distinct from the FLTLOADS balance clamp `AeroCoeffSet.stall_cl`, which carries the 0.9 stall-margin factor and may differ by ~0.1%); atmosphere `a=29.02436√(T+459.4)`) | Appendix A V-n table (VA 121.3, VC 170, VD 212.5, VF 105.5; n +3.8/−1.52; MC 0.323, MD 0.403 @ 12000 ft; S = 2·13257/144 = 184.1 ft²). Chosen-speeds case (p156): chosen VD 212.5 clears both floors, so the 1.25·VC floor shows. **No-chosen-speeds case (p155, Cat N): VD(min)=Kd·VCmin=1.40·141.8=198.53 kt governs** — the M1-1 fix (`test_vd_floor_no_chosen_speeds`); prior code reported Kd·VCmin only as an advisory and returned the 1.25·VCmin floor (177.26, 10.7% non-conservative). Concept mode (Cat C) treats the GA-calibrated Kd term as advisory only. **Dive-speed basis (F25-2, 14 CFR 25.335(b) / 23.335(b)(4); `reference/14CFR_25_335_design_airspeeds.md`, `reference/14CFR_MC_MD_speed_margin.md`):** the regulation offers two routes *disjunctively* — the speed ratio `VC/MC ≤ 0.8·VD/MD` (algebraically `VD ≥ 1.25·VC`, i.e. what the suite always implemented) **or** a minimum Mach margin `MD ≥ MC + margin`. `speeds.vd_basis` selects; on the margin route the 1.25·VC floor is NOT also applied (that would re-impose what the "or" relieves) and the value it would have imposed is reported as `vd_ratio_floor`. Margin policy is owned solely by `resolve_mach_margin`: default **0.07 M** (Amdt 25-91, eff. 1997-08-28; AC 25.335-1A "sufficient without further investigation"), **0.05–0.07 M only with a written rational-analysis basis** (25.335(b)(2), automatic systems credited) and flagged, **below 0.05 M refused** (absolute floor). A chosen VD short of the required margin is *raised* to meet it. **Concept category "C" only** (decision D-1) so the Appendix A oracles stay locked. **No oracle exists** — the gates are stated invariants: the reduction invariant (speed-ratio route reproduces the pre-F25-2 VD/VC/VA/VF for all six shipped examples at 1e-6) and the margin-route vectors on the RJ fixture (VD 350 → MD 0.85112, margin +0.09728; VD 320 → raised to 338.79). **Incomplete by construction:** 25.335(b) requires the *greater of* the Mach margin and the (b)(1) upset-criterion speed increase; the upset term is not implemented and every margin-route output says so. **Kc/Kd clamp (M1-6, review T9):** the 23.335(a)/(b) coefficient schedule is tabulated only to W/S = 100 (Kc → 28.6, Kd → 1.35); `constants.py` now holds Kc/Kd at those endpoints for W/S ≥ 100 (STRSPEED.BAS clamps there) instead of extrapolating the taper below them (non-conservative for the heavy-concept band). Inert on GA (W/S ≈ 20); for W/S > 100 the design-speeds condition carries an OUT-OF-BAND note flagging VC(min)/VD(min) as GA-extrapolated advisories (`test_speed_coefficients_clamp_at_wing_loading_100`, `test_out_of_band_note_above_wing_loading_100`). **Operating-limitation implications (M2-10, advisory — no oracle):** `operational_placards`/`operational_implications` derive the preliminary Subpart-G placards from the design speeds — VNE=0.9·VD, VNO=min(VC, 0.89·VNE), MNE=0.9·MD (recip yellow-arc; **14 CFR 23.1505(a)/(b)**), VMO=VC/MMO=MC (turbine/no-yellow-arc; **Ref 1 p47**), VFE=VF (**23.1511**). Optional operational **targets** invert the ladder into required design minima (VNE⇒VD≥VNE/0.9; VNO⇒VC≥VNO and VD≥VNO/0.89/0.9; VMO⇒VC≥VMO; MMO⇒MD≥MMO+the **resolved Mach margin** (F25-2: `resolve_mach_margin`, default 0.07 per **25.335(b)(2)**/**23.335(b)(4)(iii)**, floor 0.05 per **23.335(b)(4)(ii)** — it was a hardcoded 0.05); VFE⇒VF≥VFE) and warn-only on infeasibility (`operational_target_checks`; dashboard via `validation._check_operational_targets`). Regulation text: `reference/14CFR_operating_limitations.md` (web-verified 2011 CFR ed. + Ref 1 p47). GA6 placards checked in `test_operational_placards_ga6` (VNE 191.25, VNO 170, MNE 0.363, VMO 170, MMO 0.3226, VFE 105.5); display/validation only — no load-math change, oracles unaffected. |
| `mach_limit` (MACHLIM) | `MACHLIM.BAS` (Appendix C p393-394) | Theory walk-through in [`design_airspeeds.md`](design_airspeeds.md). Ch 6 (`MNE=0.9·MD`; `V(M,EAS)=M·a·√σ`; shared `standard_atmosphere`). **`MFC=1.2·MD` and its `V(FC)` are withdrawn from scope** (#79, 2026-08-26): flutter substantiation is 23.629, not a design load, and the symbol is read as §25.253's VFC/MFC — registered in [`02_approved_corrections.md`](02_approved_corrections.md) §Withdrawn from scope, which is *not* a correction: the printed figure stands. **MC/MD are arguments, not inputs (F25-2):** `design_speed_values` is the sole producer; they were previously stored on `MachLimitInput` *and* recomputed by the GUI, so the CLI and the GUI reported different MNE for one project (RJ: 0.738 vs 0.848). Drift-guarded by `test_mc_md_come_from_strspeed_on_every_front_end`. **The shoulder altitude is an argument too (v55, #52):** `speeds.shoulder_altitude_ft` is its one home, so the table's first row and the Mach numbers on it are at the same altitude by construction; no equation moved (note 33 §8, gates DG-6/DG-7). | Appendix A p160 (MC 0.323, MD 0.403, shoulder 12000 → 18000 ft: MNE 0.3627; V(MC) 170.16→150.77, V(MD) 212.31→188.11; the page's MFC 0.4836 and V(FC) are out of scope, above). Program used a=29.02 vs the shared helper's 29.02436 (~0.01%). |
| airspeed conversions (Step E7) | — (presentation layer for the Speed–Altitude Envelope chart) | KTAS = KEAS/√σ; KCAS via the standard subsonic compressible impact-pressure relation `qc/P0 = δ·((1+0.2·M²)^3.5 − 1)`, `δ = σ·(a/a0)²`, `KCAS = a0·√(5·((qc/P0+1)^(2/7) − 1))` (`constants.convert_airspeed`; a0 = `SEA_LEVEL_SOUND_KT`) | No manual oracle (a display transform over MACHLIM). Checked by identity/ordering in `tests/test_airspeed_conversions.py`: KEAS==KCAS==KTAS at sea level; EAS < CAS < TAS at altitude. Standard airspeed relations (NASA RP-1046). |
| `airloads` (AIRLOADS + TAU) | `AIRLOADS.BAS` / `TAU.BAS` | Ch 7 p46-47 (Schrenk: additive `c·cl=½(mo·c/Mo+4S/πB·√(1−(2y/B)²))` for CL=1; basic `Awo=Σmo·c·ac·dy/Σmo·c·dy`, `c·cl_b=(mo/2)(ac−Awo)c`; combine `c·cl=c·cl_a·CL+c·cl_b`; wing slope `M=mo/(1+mo/πAR·(1+τ))` Peery 9.59); TAU quartic curve-fit p407 (ANC(1) 1938) | Appendix A p161-162 (additive `CC(LA1)` elem 1/10/20 = 91.05576 / 69.44847 / 31.82978, `C(LA1)` elem 1 = 0.9275981, additive ∫ → CL 1.00061; basic `Awo` = 3.988146, `CC(lb)` elem 1 = +5.09762, `Clb` elem 1 = 0.05193). Modernized π vs the BASIC's 3.1416 → ±0.1% drift. **Twist sign (decision SC-4, 2026-08-10):** the twist-table entries `ac` are the WL-to-section-zero-lift angle, nose-up-positive in the same sense as α — verified in the basic-lift formula `c·cl_b=(mo/2)(ac−Awo)c` (a more positive entry lifts more; washout enters negative at the tip) and the induced-angle use `ai=(α−Awo+refang)−kcl/mo`. Label only; no computed number depends on the statement. **Derive-by-default (note 36 OV-2/OV-4, #97):** a blank `taper_ratio` falsy-derives as the polyline tip/centreline chord ratio and a blank `tip_ratio` as `tip_cap_width_in`/semi-span before the TAU fit runs (`derived_geometry.taper_ratio_from_planform`/`tip_ratio_from_planform`, resolved once in `airloads.resolved_tau`); an entered ratio or `tau` overrides, so every printed oracle is untouched — the pre-fix blank landed on the fit's pointed-wing knot (τ = 0.206209) silently. |
| `flight_envelope` (FLTLOADS) | `FLTLOADS.BAS` (Appendix C p421-428) | Ch 8 (balance subr 3900: `CL=C0+ΣCi·αⁱ·G/Gmn`, `CD=ΣDi·CLⁱ`, `CM=M0+ΣMi·αⁱ·G/Gmn`; `L=CL·Q·S`, `Q=V²/295`; rotate `LZ=L·cosα+D·sinα`, `DX=D·cosα−L·sinα`; balance `LT=[M(W+F)+LZ(Xcg−Xw)−DX(Zcg−Zw)]/(XT−Xcg)`, `NZ=(LZ+LT)/W`; iterate α to NZ then Q to Mach-adjusted stall; Glauert `G=1/√(1−M²)`; CLmax-vs-Mach 5th-order fit; gust subr 4864 FAR 23.341: `μ=2(W/S)/(ρ·c̄·a·g)`, `Kg=.88μ/(5.3+μ)`, `NZ=1+NG·Kg·Ude·V·a/(498·W/S)`, `Ude` 50 fps @ VC / 25 @ VD) | Appendix A "V-n Data" p179-180 (cruise CG1: STALL 1G V 61.4 / LZW 3266 / LT 132; MAN A V 121.3 / NZ +3.80 / LZW 12419 / LT 493; GUST +C NZ +3.96; AC ROLL LT 412; CG2 MAN A LZW 12970 / LT −59). AoA converges to ±0.005 NZ → ~0.5% noise on low-load points; LT + corner speeds/factors match tightly. The program's private speed of sound (518.688 vs the shared 518.4) was retired 2026-08-17 — measured to pin no printed oracle; `a` is read from `constants.standard_atmosphere` (issue #26 C-7, register). **Step G5** adds `trim_sweep()` — the same balance re-run at interpolated CG stations for the BAL A/C/D 1-g trim loads (the Flight Envelope "Trim & Stability" plot); adds no equations, so a station coinciding with a CG case reproduces `build_envelope`'s BAL load exactly (`tests/test_trim_sweep.py`). **Flaps-extended (LANDING) corner set** (subr 3000, n≤2 per FAR 23.345, sea level only): the `BAL 1.4VSF` point balances at **1.4× the 1-g flaps-down stall (`STALL 1GL`)** speed — `FLTLOADS.BAS` p300–302 saves the STALL 1GL speed for this condition — matching Appendix A p181 (LANDING CG5, case 89 `BAL 1.4VS`: V 83.6 kt / LT −430 lb; landing-config aero polynomials printed in the p179 input listing). Earlier code captured `STALL 2G` (≈√2× higher), giving a balance speed ~1.4× too high and LT ~2.2× too large — review finding T2, fixed in M1-2 (`test_bal_1p4vsf_balances_at_one_g_flaps_down_stall`). |
| `fuselage_moment` (Munk fuselage pitching-moment estimator — **Step G4**, no `.BAS`) | — (modern concept-mode helper; McMaster's Ch 7 aero program takes the combined wing+fuselage moment as input) | Munk slender-body apparent-mass moment: for a body of revolution at small α the free (destabilizing) moment magnitude is `M_fus = (k2−k1)·q·Vol·α`, so non-dimensionalized on the wing reference `dCm/dα (per rad) = (k2−k1)·Vol/(S·mac)`; section area = ellipse `π/4·w·h`, `Vol` = trapezoidal integral over the G1 outline, fineness `l/d` = length ÷ max equiv. diameter `√(w·h)`, `(k2−k1)` from the Munk prolate-spheroid table. Reference-point independent (volume-based). Sources: Munk NACA TR-184; USAF DATCOM 4.2.1.1; Perkins & Hage — see `reference/fuselage_pitching_moment.md`. | **No printed oracle** (modern add-on; the manual's coefficients already include the fuselage). Closure (`tests/test_fuselage_moment.py`): matches the closed form on a known cylinder (Vol, l/d, k2−k1, ΔM1) + table endpoints; **off by default → Appendix A V-n matrix bit-for-bit unchanged** (disabled or zero increment); an enabled positive ΔM1 shifts the balancing tail load (wiring reaches the balance). |
| `lateral_body_aero` (wing-body `Cy_β`/`Cn_β` in sideslip — **L-7**, no `.BAS`) + `atmosphere` (viscosity/Reynolds) | — (modern concept-mode term; McMaster's suite carries fin-only lateral aero) | USAF DATCOM **5.2.1.1**: `Cy_β,WB = −K_i·CL_α,B − 0.0001·\|Γ°\|` per deg, `K_i` = fig. 5.2.1.1-7 closed form (`1+0.49·2z_w/d` low wing / `1−0.85·2z_w/d` high), `CL_α,B` per **4.2.1.1** (`BODYRT`: `2(k2−k1)·S_0/S_ref`, `S_0` at `x_0 = 0.378·l_B + 0.527·x_1`, `x_1` the steepest-area-decrease station else `l_B`, `(k2−k1)` from fig. 4.2.1.1-20 on `l_B/d_eq(S_max)`); **5.2.3.1**: `Cn_β,WB = −K_N·K_Rl·S_BS·l_B/(S·b)` per deg, `K_N` through the three chained charts of fig. 5.2.3.1-8 on `l_B²/S_BS`, `x_ref/l_B`, `√(h_¼/h_¾)`, `h_max/w_max`, `K_Rl = 1 + ln(Re_l·10⁻⁶)/4.86` (fig. 5.2.3.1-9 closed form; `Re_l` on TAS and Sutherland viscosity, `atmosphere.reynolds_per_ft`); DATCOM's `+Cn` (nose starboard) negated into the suite's `+mz` (nose port). Applied by `balance` as one `body-aero` load: side force at the body side-area centroid, free couple closing `Cn_β` about `xw`; transfer to a case CG `Cn(x) = Cn(xw) − Cy·(x−xw)/b`. Cross-check: Munk's isolated-body couple `(k2−k1)·Vol/(S·b)` (`fuselage_moment.munk_yaw_slope_per_deg`) must sit **below** it. | **Printed oracle** (`tests/test_lateral_body_aero.py`, ±0.1 %): `ex1` c1 body-alone `CLA = 3.433E-03`; `ex3` c1 wing-body `CYB = −1.610E-03`, `CNB = −1.845E-03` (M 0.6) and `CNB = −1.941E-03` (M 0.8, the `K_Rl` Re-dependence); `ex5` `CYB = −1.612E-03` (area from the round half-width); `ex4` `CYB = −3.660E-04`, `CNB = −6.036E-04` (19-station body, `Re_l = 1.86E8`, top-of-chart `K_Rl = 2.075`). `K_i` and the dihedral term have **no printed case** (every sample has `z_w = 0`, `Γ = 0`) and are checked against their closed forms only. Balance gates G2–G12 in `tests/test_l7_lateral_balance.py` (zero at `β = 0`, static stability restoring on both fixtures and flagged when not, `\|n_y\|` up / `\|ψ̈\|` down, exact closed-form pair about `xw`, Munk below DATCOM, off-by-default bit-for-bit, six-DOF closure in memory and from the deck cards in both unit systems, symmetric half closes with fin and body removed, twins mirror). |
| `airloads` (load distribution) | `AIRLOADS.BAS` subr 4500 (Appendix C, lines 4600-5060) | Ch 12 (operating section lift `kcl=cl_basic+CL·cl_add`; induced angle `ai=(α−Awo+refang)−kcl/mo`, induced drag `cdi=kcl·ai/57.3`, `cd=cdi+CDO`; strip `L=kcl·c·dy·Q/144`, `D=cd·c·dy·Q/144`, `ML=CM·c²·dy·Q/144`, `Q=V²/295`; rotate by `α_rw2wl=CL/M−Awo`; integrate tip→root `Sz,Mxx=ΣSz·dy,Tyy=−ΣSz·Δx25`, `Sx,Mzz=ΣSx·dy,Tvyy=ΣSx·Δz`, `Trq=ΣML`; `Myy=Tyy+Tvyy+Trq`) | Appendix A "Airloads for Case 22 PHAA" p206 (CL 1.52, V 117.4: root FZ +466, SZ +6470, MXX +516955, MYY −79003, MZZ −91283; tip MYY −198) — exact with `tau=0.05` (the manual's printed wing TAU). |
| `select` (SELECT — **wing + htail balancing + vtail, Step C6**) | `SELECT.BAS` (Appendix C, wing search ~2990-3540; htail balancing / BALLOADS; vtail subr 8300) | Ch 9. **Search scope (made explicit 2026-08-23, review C210-26):** the candidate pool for *every* selection — wing, h-tail, v-tail and fuselage alike — is the **entire balanced V-n matrix** (one `VnPoint` per condition × loading/CG × altitude, FLTLOADS' full output), filtered only by condition label (`select._pick`); `extreme()` then returns **one governing case per category**, and that single case is what proceeds to the distributed-loads pass (AIRLOADS/WINGINER/TAILDIST). 23.333(b)'s "each combination" requirement is discharged by FLTLOADS balancing the full matrix; SELECT's job is the reduction to design conditions — envelope everywhere, detail only where the envelope governs. Known limit of the method (as in SELECT.BAS): the wing criteria are airload-side scalars, so wing inertia relief is not in the criterion — NETLOADS applies the *selected* case's loading afterward. Wing criteria: search the matrix for the critical wing condition — **PHAA**/**PLAA** largest resultant `√(LZW²+DX²)` among STALL +N·MAN A / MAN D·GUST D; **PMAA** largest `LZW` among MAN C·GUST +C; **NMAA** largest resultant among the negative maneuver/gust points; **ACRL** largest `LZW` among the AC ROLL points; **TORS** most-negative aileron torsion proxy `(cm−0.01·δ)·G·V²` among ST ROL A/C/D with δ per CAM 3.222 `DA, DC=(VA/VC)DA, DD=½(VA/VD)DA`. **Horizontal-tail balancing (rational):** resolve the balanced load into AoA load at 25% MAC and camber/elevator load at 50% — `AT=αwl+IT−E`, `E=114.6·CL/(π·ARW)`, `AHT=2π/(1+2/ARHT)`, `LT25=(AT·AHT/57.3)·Q·ST`, elevator `δ` from balancing M about the CG → `LT50`, `LT=LT25+LT50`, `CP%=(25·LT25+50·LT50)/LT`; largest up/down flaps retracted, FAR 23.421. **Vertical tail** (subr 8300, search BAL A/BAL C): `AVT=2π/(1+2/ARVT)`, rudder effectiveness `EFFECTV=cubic(SR/SV)`; sudden rudder `LV=RD·EFV·EFFECTV·AVT/57.3·V²/295·SV` (FAR 23.441(a)(1)), yaw-to-sideslip `LV−19.5·AVT/57.3·V²/295·SV` (a)(2), yaw 15° neutral `−15·AVT/57.3·…` (a)(3), side gust `KGT·UDE·V·AVT·SV/498`, `UGT=2W/(ρ·VMAC·g·AVT·SV·(K/LXVT)²)`, FAR 23.443(b); rudder load `(SRfwd+½SRaft)·LV/(SV−SRaft)`; default `IZZ=(Wwing/g)B²/12+((.62GW−Wwing)/g)LF²/12`. **Published aero state (note 35, #100):** every h-tail/v-tail `CriticalCondition` publishes the state its method actually used — `alpha_tail_deg` (h-tail AT / fin AoA, the yaw cases' −19.5/−15 opposite in sign to the SC-1 `beta_deg`; the side gust's is the load's own `Kgt·Ude/V`), `delta_deg` (balancing's moment-balance δ, the unchecked full throw, the trim δ on the gust cases; `None` on the checked maneuver — the 23.423(b) increment is an inertia term with no δ) and `q_psf` (`None` on the side gust — 23.443(b) is linear in V); the unsymmetrical case copies its governing source's. The finite-surface slope `2π/(1+2/AR)` has **one owner**, `_vtail.lift_curve_slope` (AHT and AVT are the same chart, AS-5); **LF is one stored length** since v55 (#52) — `geometry.empennage.airplane_length_in`, read by both the pitch-inertia `Iyy=W·LF²/g/12·0.44` and the default IZZ through `derived_geometry.airplane_length_in`; the per-tail copies it replaces agreed on every shipped fixture, so no oracle moved) | Appendix A "Critical Wing Loads": PHAA STALL +N (+1.519, 117.40), PLAA MAN D (+0.472, 212.40), PMAA GUST +C (+0.810, 170), NMAA GUST −C (−0.433, 170, CG3), ACRL AC ROLL (+1.328, 116), TORS ST ROL C (+0.470, 170). "Critical Horiz Tail Loads"/Ch 9 case 202: UP BAL retracted **LT +519.845** (LT25 +907.62, LT50 −387.78, δ −5.39°, CP 6.35%); DOWN BAL retracted MAN D **LT −613.92**. "Critical Vertical Tail Loads": sudden rudder **+591** (rudder 167), sideslip 19.5° total −92 (yaw −684, rudder 591), yaw 15° **−526**, side gust VC **+604** (IZZ 4169.2). Selected loads inherit FLTLOADS' ±0.005-NZ noise (~0.5%); the rudder-deflection loads also carry the `EFV≈1.009` large-deflection chart factor (default 1.0, illegible in the scan) — AoA/gust loads exact; renumbered case indices. **Approved oracle deviation (M1-4, 2026-07-20):** the 23.427(a) unsymmetrical h-tail search **includes the unchecked maneuvers**, per `SELECT.BAS` lines 6070–6175 (`L(5)=U1CK`/`L(6)=U2CK`, `FOR I=1 TO 12`) and 23.427(a)'s scope ("the loads prescribed in 23.421 **through** 23.425", spanning 23.423). The Appendix A sample output prints the unsymmetrical governed by the down gust (total −1111.8) — inconsistent with its own Appendix C listing, which the larger unchecked case (`U2CK` = −1397.835, ref case 274) would win; that printout is from a superseded revision that excluded the unchecked cases. The GA6 unsymmetrical is thus −1204.7 (RH −700.4, LH −504.3, 72%, DN unchecked governing); tested in `test_htail_gust_and_unsymmetrical_match_appendix_a` with −1111.8 kept in a comment. Source: `reference/23_427_unsymmetrical_candidate_set.md`; in the approved-corrections register [`02_approved_corrections.md`](02_approved_corrections.md). |
| `balloads` (BALLOADS — **Step C11**, off-pipeline verification) | `BALLOADS.BAS` (Appendix C p497) | Ch 8–9 (rational balanced-tail-load cross-check of FLTLOADS' *approximate* CP). For each flaps-retracted V-n point recompute the rational balance — `LT25=(AT·AHT/57.3)·Q·ST` at 25% MAC, elevator `δ`-balanced `LT50` at 50%, `LT=LT25+LT50`, `CP%=(25·LT25+50·LT50)/LT` — **by reusing `select.htail_balance`** (no re-derivation; it returns the `HtailBalance` NamedTuple `lt25/lt50/at/delta/lt/cp` — the Ch 9 symbols are in its docstring), convert `CP%` to a fuselage station `XT=XT25+(CP−25)·(XT50−XT25)/25` and compare to FLTLOADS' assumed `XTC`/`XTF`. Reports the elevator load (`select.elevator_load`), demonstrating it is not always opposite the stabilizer load. No schema/pipeline output. | Ch 9 case-202 hand-calc: up balancing **LT 519.845** (LT25 +907.62, LT50 −387.78, δ −5.39°, CP 6.35% tail MAC), within FLTLOADS' ±0.5% V-n noise; rational up/down equal SELECT's `BAL UP/DN RETRACTED` exactly (shared routine). |
| `wing_inertia` (WINGINER) | `WINGINER.BAS` (Appendix C p455-458) | Ch 13 (panel area density tapered root→tip, root density iterated to panel weight; 1g vertical `Fz=W, Sz=ΣW, Mxx=ΣSz·dy, Tyy=−ΣSz·Δx25−ΣW·(x50−x25)`; 1g drag `Mzz=ΣSx·dy, Tvyy=ΣSx·Δz`; unit roll `Iwxx=2ΣW·Y²`, `Fz=W·Y·1e5/Iwxx`; combine `Fz=Nz·W+UNB/1e5·Fz_roll`, `Myy=Nz·Tyy+Nx·Tvyy+UNB/1e5·Tuyy`; concentrated weights add inboard steps) | Appendix A "Wing Inertia Loads" p217-221 (panel 165 lb, ratio 0.95, rib BL 23 → root 2.213 / tip 2.102 lb/ft²; unit-vert root Mxx −16158; case 138 Nz −2.54 Nx −0.1318 root Mxx −41041, Myy +11161, Mzz −2130). |
| `net_loads` (NETLOADS; LRA transfer **M4-18**) | `NETLOADS.BAS` (Appendix C p461-463) | Ch 14 (net = air + inertia per station, `A(I)=A_air(I)+A_inertia(I)`; inertia entered with signs opposing the air load). The suite computes torsion about the **25% chord** (AIRLOADS 4500-5060 / WINGINER conventions, oracle-locked). **Modern boundary addition (M4-18, no `.BAS` counterpart):** `to_loads_ref_axis` transfers the cumulative torsion to the surface's loads reference axis (LRA, `SurfaceInput.ref_axis_pct`, the beam-model elastic axis) at render/export only — `Myy_lra = Myy_25 + Sz·(x_lra − x_25)`, the statics of moving the moment-reference point of the outboard load set (WINGINER's `−W·(x_load − x_axis)` sign convention); shears/bending unchanged; 0.25 is a bitwise no-op. | Appendix A "Net Loads, Case 22 PHAA" p222 (root Sz +5837, Mxx +455555, Myy −60940, Mzz −81483 = air p206 + inertia case 22 Nz −3.8 Nx +0.6065). LRA transfer: per-station formula identity + 25%-no-op in `test_net_loads.py::test_loads_ref_axis_transfer` (no printed oracle — the manual has no LRA concept). |
| `taildist` (TAILDIST — **Step C7**) | `TAILDIST.BAS` (Appendix C subroutine 3000) | Ch 10 (chordwise net pressure on the average tail chord = additive (angle-of-attack) + camber distributions). Stations `X1=0, X2=.25·CT, X3=CT, X4=CEAFTHL=(Saft/S)·CT, X5=CT−X4` with `CT=CAVE=S/span`. Additive `WATT=LT25/S` → `WATT1=4·WATT, WATT2=WATT, WATT3=0`, `WATT4/WATT5` linear LE→¼c→TE; camber `WCAM=LT50/(S−Saft)` → `WCAM1=WCAM3=0, WCAM4=WCAM5=WCAM, WCAM2=(X2/X4)·WCAM if X4>X2`; `PSI(Xi)=WATTi+WCAMi`. The BASIC halves the both-sides `LT25/LT50` over the half tail area; working in the suite's full both-sides areas folds the two factors of two into the `LT/S` form above. `LT25`/`LT50` per condition come from SELECT (the rational 25%/50% split on each `CriticalCondition`). **Note 35 (#100):** each distribution also carries and prints the source condition's published aero state (AoA/β/δ/q — or its fixed AS-4 reason where the method defines none), and AHT / AVT + EFFECTV print once per component from the same owners inside the loads; the closure identities (the published state reconstructs the stamped `LT25`/`LT50` through the Ch 9 equations, rel 1e-9, every fixture) are gate G-AS-2 in `tests/test_taildist_aero_state.py`. | Appendix A "Chordwise Distribution of Tail Loads": **13 horizontal** p237 (cond 1 UP-BAL-RET LT25 +907.62 / LT50 −387.77 → PSI 0.682 / 0.095 / 0 / 0.015 / −0.030; cond 5 / 6 / 9 …) and **4 vertical** p245 (S 2137, Saft 667, span 57; cond 1 LT50 679 → PSI 0 / 0.370 / 0 / 0.462 / 0.462; cond 2 LT25 −1076 → PSI −2.014 / −0.134 / 0 / 0 / 0.252) within ±0.1%. The landing-config aero polynomials are now in the repo (M1-2 transcribed the p179 input listing into the `flight_envelope` test fixture, oracle-matching the `BAL 1.4VSF` balancing point at p181); wiring the 4 flaps-extended horizontal chordwise rows (Appendix A cases 81/106/88/108) through SELECT→TAILDIST with the CG5–7 loadings remains L-2. |
| `aileron` (AILERON — **Step C8**) | `AILERON.BAS` (Appendix C p450) | Ch 16 (deflected-aileron rolling loads, FAR 23.455 / CAM 3.222(c)): `LAIL=0.04·DEFL·SA·V²/295`, `SA=SAFWD+SAAFT`; deflection schedule full at VA, `(VA/VC)·DEFL` at VC, `0.5·(VA/VD)·DEFL` at VD (CAM 3.222(b)(3)); largest up/down loads selected. Chordwise pressure constant LE→hinge then taper to 0 at TE: `W=LAIL/(SAFWD+0.5·SAAFT)`, `psi=W/144`. VA/VC/VD from STRSPEED. | Appendix A "Critical Aileron Loads" p200 (VA/VC/VD 121/170/213; down 15° / up −10°; SAFWD 1.3 / SAAFT 5.188 → **down 271.44 lb / up −180.96 lb @170 kt**; pressure +0.484 / −0.323 lb/in²) within ±0.1% (the oracle uses the manual's rounded VA=121; the pipeline's computed VA≈121.3 shifts the load ~0.3%). |
| `flap` (FLAPLOAD — **Step C8**) | `FLAPLOAD.BAS` (Appendix C p452-454) | Ch 17 (critical flaps-extended load, FAR 23.345 / 23.457): Abbott & von Doenhoff Fig 98 `D1=−2.6E+2.6`, `D2=0.59E+0.08`, `CLf=D1·δ_rad+D2·CLw`, `CLw=n·W/(Q·SW)`; four conditions (1G stall V=VSF, 2G stall V=√2·VSF, 2G at VF, NG-gust at VF), `LF=CLf·Q·SF`, largest taken. Chordwise taper LE→half at TE: `LE psi=LF/0.75/SF/144`. **Slipstream** (23.457(b)) momentum sub 500: iterate `U1` until `area·ρ·(U1−Vf)(U1+Vf)²/(4·550)=0.85·MAXHP`, contract `A1=Aprop·U/U1` (`U=(Vf+U1)/2`), band `BL±RTOT`, `RTOT=√(4(A1+AF)/π)/2`, factor `(Vss/VF)²`. **Applied since #85 (2026-08-24)**, not merely printed: the delivered slipstream case is `factor × max(LF 2G-at-VF, LF gust-at-VF)` — the factor is a ratio of dynamic pressures *at VF* and so may only scale a VF-based condition — enveloped with the head-on-gust case rather than multiplied by it (independent worst cases; owner ruling). No printed oracle exists for the applied load, so the gate is that stated closure (rule 2), not ±0.1%. **Head-on 25 fps gust** (23.345(c)(1)): factor `((Vf_fps+25)/Vf_fps)²`. VS/VSF/VF/W from STRSPEED, SW from geometry, MAXHP/PDIA from the engine (MAXHP is **takeoff power** per 23.457(b): `takeoff_hp` preferred, `max_cont_hp` fallback). | Appendix A "Critical Flap Loads" p201 (VS 62.2, VSF 58.6, VF 105.48, W 3400, NG 1.9, SF 10.7, SW 184.125, δ 40°, E 0.27, MAXHP 250, BLPROP 68, AF 8.2, PDIA 85 → CLf 1.7046/1.7046/1.5593/1.5476; LF 212/424/**629**/624; LE 0.545 psi; slipstream ×1.407, BL 22.828…113.172, Vss 125.1; gust ×1.301; **combined 819 lb**) within ±0.1%. **NG derive (note 36 OV-6, #97):** a blank `gust_load_factor` falsy-derives from the flight envelope's own GUST VF corner factor (`flight_envelope.gust_at_vf` — the same 23.341/23.345 gust chain, bit-for-bit the envelope's number, gate G-OV-2); a typed NG overrides, and the result states which it used. |
| `tab` (TABLOADS — **Step C8**) | `TABLOADS.BAS` (Appendix C p490-491) | Ch 18 (control-surface tab loads, FAR 23.409 / CAM 3.224): full deflection at VC, `E=MACTAB/CAIRFOIL`, slope `M=0.0446·(1−E)` per deg (NACA TN 353 + Fig 98), `LTAB=M·δ·Q·STAB/144` (STAB sq in, `Q=VC²/295`). Trapezoidal chordwise (CAM 3.224-1(b), LE = 2× TE): `W=LTAB/1.5/STAB`, `LE=2W`, `TE=W`. Host-surface CL lift on the tab neglected (chord ratio ~0.12). VC from STRSPEED. | Appendix A "Tab Loads" p202 (h-tail tab: VC 170, MACTAB 7.478, STAB 226, CAIRFOIL 42.166, δ 15° → **E 0.17735, LTAB 84.62 lb, LE 0.4992 / TE 0.2496 lb/in²**) within ±0.1%. |
| `airloads` (AIRLOAD4 swept branch — **Step C7**; renormalization **M1-3**) | `AIRLOAD4.BAS` (Appendix C) | Ch 12 (sweepback redistribution of the Schrenk span load, Pope & Haney JAS Aug 1949 p505 Eq. 12.38 / Pope *Basic Wing & Airfoil Theory* 1951): AIRLOAD4.BAS applies it to the **combined operating** distribution — `COL16 = c·kcl/(MAC·CL)`, `COL18 = (1−2y/b)·2(1−cosΛ)`, `COL19 = COL16 − COL18`, then **renormalizes** `COL20 = COL19 / CLCOL19` so the swept span load re-integrates to the operating `CL` (the final step; `Λ` = 25%-chord sweep, negative = sweptforward). Wing twist is redistributed too (not additive-only). Auto-selected when `|Λ|>15°` or design Mach `>0.4`; compressibility is carried upstream by FLTLOADS' Glauert `CL`, so high Mach alone leaves the shape unchanged. **Mach-threshold source (M1-8, verified 2026-07-20):** Ref 1 (Ch 12 aileron-torsion air-loads section) states the trigger as *"Mach >.4 or sweepback > 15 degrees"*; the FAA User's Guide §9.1/§10.1 instead says *"greater than 0.5"*. No `.BAS` oracle pins it — AIRLOAD4 selection was a human-operator choice, not a hardcoded `IF MN > …` (the listing carries no Mach comparison). We keep Ref 1's **0.4** as the higher-authority source and the conservative gate (swept branch triggers earlier); given the Glauert-upstream note it is nearly moot for output regardless. The 15° sweep trigger matches across both sources. The port renormalizes on the physically-correct span-load integral (Decision 3 "modernize the math"; the literal chord-weighted `COL16`/`CLCOL19` line is OCR-garbled and closes only to ~0.3%). | **Reduction invariant** (Λ=0 / low Mach ≡ AIRLOADS exactly; additive/basic split stays unswept) + **swept-CL closure** (`recovered_cl ≈ target_cl` for Λ≠0 — the renormalization; `test_swept_closure_recovers_target_cl`, deliverable `test_swept_deliverable_recovers_case_cl`) + **listing-traceable** COL18/COL19/COL20 reconstruction (`test_sweep_operating_matches_basic_listing`) + swept-redistribution direction (sweepback reduces inboard loading, tip ~unchanged). The printed Appendix B swept spanwise oracle is **deferred** (no legible swept fixture). |
| `body_loads` (NET FUSELAGE LOADS — **no `.BAS`, Step C6**) | — (Ref 1 Ch 15 ships a *suggested procedure*, not a program) | Ch 15 p103, **two passes**. Pass 1: per-station inertia `fz=−NZ·w` plus the balancing tail air load at the tail station, integrated nose→tail to shear `Sz=Σfz` and bending `Myy=Σ(area under Sz)`; *its* terminal moment is the **unbalanced moment** `M_ub` (“the moment at the aft end is the unbalanced moment”). Pass 2: `M_ub` and the vertical residual `R_total=NZ·W_fus−LT` are reacted **at the wing front and rear spar attachments** (“the unbalanced moment is reacted by the wing at the front and rear spar attachments … recalculate the loads, shear and moments”) — `R_r=(M_ub+R_total·(x_ref−x_f))/(x_r−x_f)`, `R_f=R_total−R_r`, about the integrator's aft-most station `x_ref`; spar stations from the G1 planform × `SurfaceInput.front_spar_pct`/`rear_spar_pct` (defaults 0.15/0.65, flagged `assumed`). **Documented refinement of the manual (ours, M4-1):** the two point reactions are applied as the statically equivalent **linear line load** over `[x_f, x_r]` — identical resultant and first moment, but without the `±M_ub/d` shear spike two point loads put across a short carry-through, and continuous onto the manual's two-point solve as `d→0`. Each segment is lumped by its exact static equivalent, so closure does not depend on the node count. `R_f`/`R_r` are reported as fitting loads, never re-applied on top | **No printed oracle** (Ch 15 ships no program and no printed station table). Equilibrium closure in **both** degrees of freedom: applied `ΣFz=0`, the running shear returns to ~0 at the aft end, **and the terminal `Myy` returns to ~0** (M4-1, closed 2026-08-03 — previously 7.3e4–5.5e5 lb-in of unreacted couple); the exported FORCE set re-sums to ~0. Also locked: `R_f+R_r=R_total` and the pair's moment about `x_ref` recovering `−M_ub`; node-count independence (2/3/5/9/33); the `d→0` collapse onto the manual's two-point solve. Where the spar stations are underivable a whole-body correction closes the beam with **no physical source** — flagged `closure_artifact` and stamped on that path only via `body_loads.CLOSURE_ARTIFACT_CAVEAT`. Open, split out: **M4-21** (pitching load factor; `θ̈=0` on the balanced trim cases, so it does not affect this closure) and **M4-19** (distributed body aero moment). |
| `export/sbeam_bridge` (C4 export bridge — **no `.BAS` oracle**; LRA-axis export **M4-18**: the `Project` path transfers wing torsion to the loads reference axis via `net_loads.loads_ref_axis_results`, and the axis label travels in-band — span-CSV `MyyAxis` column, BDF `$` comments, stick-model beam-axis note) | — (renderer; card style from `sbeam/results/load_export.py`) | Ref 1 Ch 14 (the net wing load being exported); NASTRAN bulk data: `FORCE`/`MOMENT` (`F·(N1,N2,N3)`, comma free-field, unit scale), `GRID`/`CBAR`/`PBAR`/`MAT1`/`SPC1`, `SOL 101`. Nodal load = increment of the cumulative NETLOADS column (`dFz[i]=sz[i]−sz[i+1]`), so `ΣdFz=sz_root` exactly. **Concentrated-mass offset couples (plan 14, 2026-08-09):** a point mass does not sit on a station, so differencing alone loses its lever arm and `ΣdFz·(y−y₀)≠mxx_root`. The loss is exactly the per-station defect `δ[k]=mxx[k]−mxx[k+1]−sz[k+1]·dy`, which is identically zero under the lumped-at-nodes recursion (`airloads` and the panel part of `WINGINER` both build the column with it) and equals `w·(y_c−y[j])` at the bracketing station — WINGINER.BAS 1180-1270's `mxx[i] += w·(cw.y−ye[i])`. Restored as an applied couple `Mx=δ[j]` (`Mz` likewise for `mzz`), the rigid-offset static equivalent, so the exported set reproduces `sz[k]` **and** `mxx[k]` at every node. Sign map owned by `coordinates.bending_moment_vector` (`Mxx→+x`, `Mzz→−z`). | **No printed oracle.** Closure: re-summed FORCE/MOMENT = NETLOADS root totals (exact); a self-contained free-field reader round-trips the cards; the stick deck parses **and solves SOL 101** in the real sbeam — a standing CI gate since step 2 (`tests/test_sbeam_roundtrip.py`), not a manual step. |
| `export/lra_model` + `export/lra_import` (step 12 LRA beam model — **no `.BAS` oracle**; modern deliverable) | — (renderer over the assembled balanced cases; NASTRAN `GRID`/`CBAR`/`RBE2`/`PBAR`/`MAT1`/`SPC1`/`FORCE`/`MOMENT`, `SOL 101`) | No new load physics: the load sets are the plan-11 balanced cases unchanged, and the only operation is the statics transfer `(F, M)@p → (F, M + (p − n) × F)@n` — the exact rigid static equivalent, single owner `export/coordinates.transfer_couple` (note 24 R-11 / note 25 LM-1). Topology per the agreed design notes 24/25: wing beams start at the side of body (R-3), split-fuselage cantilevers onto the front/rear-spar posts (BM-2, statically determinate under rigid ties), fin root / h-tail attachment / gear / engine ties per R-5/R-6/R-8/R-9. | **No printed oracle** (nothing in Ref 1 assembles a beam model). Benchmark-first gates, stated with the feature: the transferred set's card resultant equals the balanced deck's per case, all six components (the plan-07 invariant, exact by construction, gated at card-format tolerance); the solver's support reaction equals minus the applied resultant ≈ 0 (free-free proof through real structure); and the SOB / front-post internal loads equal the cut-side card sums through the element frame (round-trip CI, both unit systems; one pinned sbeam conditioning limitation on the largest airframe's mm deck). |
| `applicability` (FAR 23 applicability check — **Step E1, no `.BAS`**) | — (modern addition) | 14 CFR 23.1 (pre-Amdt 23-64 applicability): Normal/Utility/Acrobatic ≤ 12,500 lb & ≤ 9 passenger seats; Commuter ≤ 19,000 lb & ≤ 19 passenger seats. The required flight crew are excluded from the passenger-seat count (`passenger seats = occupants − crew`, `crew` = user-set `WeightEstimationInput.crew`, default 1, carried in OEW). Limits encoded in `sloads/constants.py` (`FAR23_MAX_WEIGHT_LB` etc.; `DEFAULT_FLIGHT_CREW = 1`; commuter tier dormant). | **No oracle** (regulatory threshold, not a load calc). Closure: yields no exceedances on the Appendix-A GA single (~3,468 lb, 6 occupants − 1 crew = 5 passenger seats) and flags weight + seat exceedances on a 20,000 lb / 12-occupant Normal input (`tests/test_applicability.py`). |
| `vn_diagram` (V-n diagram geometry — **Step E3, no `.BAS`**) | — (modern GUI helper) | 14 CFR 23.333 (flight envelope), 23.335 (design speeds), 23.337 (limit manoeuvre load factors: flaps-down capped at n = 2.0), 23.341 (gust loads). Curved stall boundary `n = (V/VS)²` sampled VS→VA; closed positive/negative manoeuvre envelope; flaps-down envelope off VSF/VF capped at 2.0; gust lines the textbook Pratt form `Δn = Kg·Ude·Ve·a/(498·W/S)`, `Kg = 0.88μ/(5.3+μ)`, `μ = 2(W/S)/(ρ·c̄·a·g)`, `Ude` 50 fps @ VC / 25 @ VD (same taper as FLTLOADS `_gust_ude`). Reads the STRSPEED design speeds/load factors; the gust slope/MAC come from the aero/geometry slices when present, else textbook defaults (flagged approximate). | **No oracle** (presentation geometry, not an oracle-locked load). Closure (`tests/test_vn_diagram.py`): stall parabola through (VS, 1) and the manoeuvre corner; flaps-down capped at 2.0; gust line linear through (0, 1) and symmetric about n = 1; Kg → 1 when MAC unknown. The rigorous Mach-corrected gust V-n stays on the Flight Envelope page (FLTLOADS), unchanged. |
| `validation` (input-consistency predicates — **Step E3, no `.BAS`**) | — (modern GUI helper) | Pure predicates over a `Project`: taper ratio > 1 (WINGGEOM/TAU), non-positive reference area (14 CFR 23.335), leading-/trailing-edge ordering (LE fuselage station forward of TE; edge points inboard→outboard), Configuration-vs-WINGGEOM wing-area agreement (5% tol), and CG vs the WTENV structural CG envelope (14 CFR 23.23; skipped when the envelope/geometry is absent); a fuselage-carried weight item outside the fuselage outline's fore/aft extent (`mass_item_outside_body`, D-27). | **No oracle** (consistency checks). Closure (`tests/test_validation.py`): each predicate fires on crafted bad input and is silent on the Appendix-A GA fixture; the CG check flags a far-aft ballast loading and is skipped without a WTENV envelope. |
| `configuration` (Step C5 — **no `.BAS` oracle**) | — (modern addition) | Ref 1 Ch 5 (trapezoidal wing: `b=√(AR·S)`, `c_root=2S/(b(1+λ))`, `MAC=⅔c_root(1+λ+λ²)/(1+λ)`, `Y_MAC=(b/6)(1+2λ)/(1+λ)`; MAC/XLEMAC obtained via the WINGGEOM strip integrator, not re-derived); Ch 8 (tail-volume neutral point `V_H=S_t·l_t/(S_w·MAC)`, `h_n=h_acw+V_H·(a_t/a_w)·(1−dε/dα)`, defaults `h_acw=0.25`, `a_t/a_w=1`, `1−dε/dα=0.6`); landing-gear tip-back `atan((x_main−x_cg)/h_cg)` and overturn `atan(h_cg/d)` (standard gear geometry; no FAR oracle). | **No printed oracle.** Sanity: analytic-vs-WINGGEOM-strip MAC ±0.1%; Appendix A trapezoid plausibility — MAC 69.246 / MAC butt line 87.854 within ±10% (the real wing has an inboard strake). |
| `landing` (LGFACTOR + LANDLOAD — **Step C10**) | `LGFACTOR.BAS` (Appendix C p483), `LANDLOAD.BAS` (Appendix C p468) | Ch 20 pp. 126–130 (FAR 23.473–23.499 ground loads, tricycle gear). **LGFACTOR** (drop-test work-energy, FAR 23.473(d)–(g)): limit descent `V = 4.4·(W/S)^0.25` clamped 7–10 fps; flat-tyre deflection `(OD−hub)/6`; airplane load factor `N = [W·V²/(2g) + W·(1−L)·(stroke+δ_tyre)/12] / [W·(η_tyre·δ_tyre + η_strut·stroke)/12]`, `η_tyre 0.3`, `η_strut 0.5 spring / 0.75 oleo`; gear factor `NLG = N − L`. **Governing pair (note 37, #123):** the reactions run at the entered `N` when filled (`NLG = N − L`, derived — `landing.governing_load_factors`), else at the energy values; **FAR 23.473(g) floor (LF-6, superseding M2-8's concept-only warning):** the regulation requires `N ≥ 2.67` and `NLG ≥ 2.0` on the governing pair — refused in a FAR 23 category, warn-only in concept; the computed energy `N`/`NLG` are left unchanged (Appendix-A 3.0951 / 2.4281 sit above the floors, oracle unaffected). **LANDLOAD** (needs three *distinct* CG loadings — aft/fwd max landing + fwd light, UG fig 18.2 — supplied explicitly, not auto-derived, M2-8): drag factor `K = (NLG+L)/NLG · K0` (Appendix C 23.1 `K0` interpolated 0.25→0.33 over 3000–6000 lb — the lift-correction restores drag as if no lift), `GAMMA = atan(K)`; per-attitude ground angle = axle-line slope − wheel-contact-line slope, `BETA = GAMMA − GRA` (level) / `GRA` (roll, tail-down); lever arms `AP/BP/DP/CP` of Fig C23.1 (truncated to 3 dp as the BASIC prints); per-wheel reactions per FAR section — level `VMP = ½·NLG·W·AP/DP, DMP = K·VMP`; braked `½·1.33·W·AP/(.8CP+DP), DMP = .8VMP, VNP = 1.33W−2VMP` (23.493); **the per-case weight `WL` and the gross-weight ratio `WR = GW/MLW`** (`LANDLOAD.BAS` 820–900) — cases 1–12 at each loading's own weight, and the braked-roll/side/supplementary-nose families at `WCG(i)·WR` for the two *max landing* loadings but at `WCG(3)` **bare** for the light one, which is already below the landing weight: `WL(15) = WL(18) = WL(23) = WL(24) = WCG(3)`, and `2.25·WCG(3)` for cases 31–33; side `½·1.33·W, SMP = ∓.5W/.33W` (23.485); supplementary nose `VNP = 2.25·static·BP/DP, DNP = .8/−.4·VNP, SNP = .7·VNP` (23.499); resultants `√(V²+D²)`; airplane-datum loads rotate the resultants through `PHIM/PHIN`. **`BETA` is the resultant-to-FS angle, `BETA = GAMMA − GROUND ANGLE`** — the rule Appendix A p234 states in the drawing, with `GAMMA = 0` for the ground-roll and tail-down attitudes (their reaction is normal to the ground; the braked drag rides the separate `.8·CP` term), and positive ground angle **nose up**. `LANDLOAD.BAS` applies that rule to the level attitude only and writes `+GRA(2)`/`+GRA(3)` for the other two; attitude 3 negates it back at both use sites and comes out right, attitude 2 at neither. **Corrected 2026-08-29** (approved deviation, `02_approved_corrections.md`, #133) on the evidence of Appendix A's braked-roll construction figure **p235**, which prints AP 77.052 / BP 17.760 / DP 94.811 where the p230 *table* prints 69.886 / 23.260 / 93.147 — the manual contradicting its own program. The correction is witnessed by a quantity it does not touch: case 13's pre-closure residual pitching moment against LANDLOAD's own unbalanced moments falls from −757.1 to −0.7 lb-in. **Unbalanced moments about the CG, ground line** (LANDLOAD.BAS 1910–2090): `PITCHP = −2·RMP·BP` for the 2-wheel level (4–6) and tail-down (7–9) cases, `−1·RMP·BP` for the one-wheel cases (10–12), `−2(VMP·BP + DMP·CP)` for braked roll nose-clear (16–18) and `−2·VMP·BP` for the side cases (19–24); `ROLLP = VMP·TREAD/2` and `YAWP = −DMP·TREAD/2` (one wheel), `ROLLP = ±0.83·W·CP` and `YAWP = ±0.83·W·BP` (side, signed by drift direction). **Ground-line inertia factors**: `NVP = (2·VMP + VNP + L·W)/W` (cases 1–9, wing lift carried), `(VMP + L·W)/W` (10–12, one wheel), `(2·VMP + VNP)/W` (13–24, no lift term); `NDP` likewise on the drag reactions; `NS = (SMP − SMP_partner)/W` for the side pairs. These are **dimensionless load factors** and are never scaled to ultimate. **Airplane-datum load factors** (p232's NR/NV/ND columns, built 2026-08-29 — note 38 GF-6, #134): `NV = (VN + n·VM)/W`, `ND = (DN + n·DM)/W` with `n = 1` on the one-wheel family and `n = 2` elsewhere, plus — on the lift-carrying families 1–12 only — the wing lift rotated into body axes; `NR = √(NV² + ND²)`. `NS` is **not** repeated in this frame: the side axis is normal to the rotation, so there is one side factor and not two. The 23.499 family (25–33) carries no airplane in equilibrium and therefore no datum factors, exactly as it carries no `NVP`/`NDP`. **Airplane-datum unbalanced moments** (p233's second table): `PITCH = PITCHP` — the rotation is about the pitch axis, so that component is invariant — and `(YAW, ROLL)` is the ground-line pair rotated through the same `ρ`, because a moment vector rotates exactly as a force vector does under one change of frame. **Both carry an approved deviation** (`02_approved_corrections.md`, #134): the `.BAS` writes the lift term as `+LF·SIN(GRA)` and the moment transform as a rotation of `+GRA`, where the physics — and `ρ = −GRA`, and the deck's own ground lift — give the other sign. Neither is written longhand here: both are `frames.to_airplane_datum` applied through the case's own measured `ρ`, so the corrected value is what a rotation gives rather than a sign somebody typed. **Critical-case ranking (M4-17e):** the per-family critical case is picked on the full `√(V²+D²+S²)` magnitude, not the printed two-component `RMP`/`RESULT`, which excludes the side load; the picks are unchanged on every bundled example. **Forward CG limit at the landing weight (M4-17c):** WTENV's forward limit is linear in weight between the forward-regardless and forward-gross anchors, and the manual reads it *at* the landing weight — Appendix A p230 pairs 3230 lb with **76.12 in**, between 72.643 in @ 2800 lb and 77.490 in @ 3400 lb (`validation.wtenv_fwd_cg_limit_at_weight`, clamped outside the anchors). No equation or oracle band changes: all of the above were already computed by the port; M4-17 delivers, cites and tests them. | **LGFACTOR fully oracle-locked**: Appendix A "Landing Load Factor" p236 (V 9.0048 / N 3.0951 / NLG 2.4281) — N within +0.07% (Decision-3 `G=32.174` vs the program's `32.2`). **LANDLOAD fully oracle-locked (2026-08-29)**, with the p230 ground-roll arm row and the p231/p232/p233 cells that derive from it re-pinned to the **p235 figure** under the approved deviation (#133) — the printed values stay transcribed beside the corrected ones, and no lock was removed. The p230 gear-geometry intermediates (K 0.324, GAMMA 17.978, ground angles 4.057/4.724/15, BETA 13.921/4.724/15, AP/BP/DP/CP table) and **every printed cell of p231 (ground line), p232 (airplane datum, force columns) and p233 (limit unbalanced moments, ground-line columns)** for all 33 cases — reactions, resultants, side loads, the NVP/NDP/NS inertia factors and the pitch/roll/yaw moments — match at the page's own print resolution (±0.5 in an integer column, ±0.0005 in a three-decimal one, or ±0.1 %, whichever is looser): `test_landload_p231_ground_line_table`, `..._p232_airplane_datum_table`, `..._p233_unbalanced_moments_table`. **The pages are OCR-garbled but not illegible**: rendered at 200 dpi they read cleanly, and every cell locked here is a **transcription**, not an OCR extraction — a distinction this citation states, because treating an OCR failure as an illegible page is what held cases 13–33 on internal identities alone (formula closure + legible-cell spot checks, the ONENGOUT/C9 precedent). Two defects lived in that gap — LANDLOAD's `WL` gross-weight ratio applied to the light loading (#135), and a fixture light-landing weight of 2803 lb back-solved from a mis-OCR'd p231 cell (#137), which had also made an input a function of the output it was used to check. p233 additionally prints a **second ground-to-datum rotation** — `RMOM = RMOMP·cos(GA) + YMOMP·sin(GA)`, `YMOM = YMOMP·cos(GA) − RMOMP·sin(GA)` — applied with the *same* sign on every attitude, where PHIM/PHIN switch sign between attitudes; it was the independent reference for design note 38's GF-1 question, and since #134 it is **ported and corrected** — the third instance of the same sign class, registered with the ND lift term in `02_approved_corrections.md`. **The NR/NV/ND columns are locked too** (72 cells, `_P232_FACTORS`, `test_landload_p232_airplane_datum_load_factors`): the tail-down family reproduces all three printed cells exactly, `NV` is untouched on 1–12 because a cosine is even, and `NR` stays printed on the wheels-only families 16–24 because a rotation preserves a resultant — three invariants the correction did not aim at. The p232 force columns are a **port-fidelity lock, not a frame adjudication** — `LANDLOAD.BAS` computes them from the printed PHIM on the same line, so they cannot test the sign of the rotation that produced them (note 38 §1.12). The manual's LANDLOAD runs at the **rounded design NLG 2.5** (NAP = 3.167), distinct from LGFACTOR's 2.428 — entered since note 37 as the governing `N = 3.167` on `ga6_normal` (LF-9), from which NLG derives. |
| `gear_loads` + `balance`'s ground families (**step 10 piece 3**, no `.BAS`) | — (the manual computes the reactions in `LANDLOAD.BAS`; nothing in the suite assembled them) | **FAR 23.471**: *"The limit ground loads … are the external loads and inertia forces that act upon an airplane structure. In each specified ground load condition, the external reactions must be placed **in equilibrium with the linear and angular inertia forces** in a rational or conservative manner."* That sentence **is** the six-DOF rigid-body closure over the itemized mass model (decision G-6), so the assembled ground case has a regulatory basis and not merely a convenient reuse of the flight machinery. **FAR 23.473(a)**: the ground requirements are met at the design maximum weight *"except that FARs 23.479, 23.481, and 23.483 may be complied with at a design landing weight"* — which is one split doing three jobs, since 23.479/481/483 are exactly the families LANDLOAD carries wing lift on and scales to MLW, and 23.485/23.493 are the gross-weight, lift-free ones (decision G-7). **FAR 23.485(d)**: the side loads *"are assumed to be applied at the ground contact point"*, so that is where the 23.485 reaction is computed and the transfer to the trunnion is ours (decision G-2). **The point is per family, and Appendix A prints it** (design note 39 AP-1, #139): the p231 and p233 tables head cases 1–12 "CENTER OF EACH WHEEL" and 13–24 "GROUND CONTACT POINT", and p232 heads 25/26, 28/29, 31/32 "CL AXLE" and 27, 30, 33 "GROUND" — the column the OCR lost, transcribed from the 200 dpi render 2026-08-29 and locked in `test_the_application_point_is_the_manuals_printed_column`. The split is physical rather than editorial: the level-landing drag is a **spin-up** load, whose reaction reaches the leg through the bearing at the axle, while braking torque is internal to the wheel/leg free body and leaves the patch force where it acts. Applying every case at the patch instead invents a pitching moment of up to 524,302 lb-in (atr42_100), and the identity `residual My − the G-7a lift moment == PITCHP` reproduces the printed column on all six fixtures from arithmetic that never read it. **FAR 23.485(c)**: 0.5 W inboard on one wheel and 0.33 W outboard on the other — two statements that act the same way globally and sum to the 0.83 W `NS` states, which is why the assembler reads the partner case for the second wheel rather than re-deriving the percentages (G-8). Lift acts along the **ground line** rather than the airplane datum (G-7a): lift is perpendicular to the flight path, and at touchdown the flight path is the runway to within the descent angle. | **No printed oracle** — Appendix A prints LANDLOAD's reactions, not an airplane in equilibrium. The gate is a **stated closed-form invariant with two independent producers**, which is what `CLAUDE.md` asks for in an oracle's absence and is stronger than the usual form of it: the solved rigid-body field, rotated back to the ground line through the case's own `ρ = atan2(dm, vm) − atan2(DMP, VMP)`, reproduces LANDLOAD's `NVP`, `NDP` **and** `NS` on every case of both fixtures at `rel_tol 1e-9` (`NS` signed per hand, R6-T2). The agreement carries content because LANDLOAD reaches those factors by lever arms and FAR percentages with no mass matrix anywhere in it, while this reaches them by solving one on the assembled item database. **The rotational half of the same gate** (R6-T1, 2026-08-15; **G-AP-1** since 2026-08-29): the solved `[I]{ω̇}` — transferred from the mass centroid to the CG, less the G-7a lift term rebuilt in closed form, and taken about **the point the case applies its reactions at** (design note 39 AP-1: Appendix A's printed column, axle on 1–12, ground contact on 13–24) — reproduces `PITCHP`/`ROLLP`/`YAWP`: an identity at `rel_tol 1e-9` for the one-wheel family's tread arms, and within `1e-4·W·MAC` elsewhere on **every** family, the residue being the BASIC's 3-decimal truncation of its printed arms (worst measured 2.65e-5·n·W·MAC, baron_58 LG-17). **The gate makes no arm correction of its own** — a gate that moves the load before comparing agrees with the code rather than testing it, which is what a version of it that shifted cases 1–12 and 19–24 from the tyre to the axle *inside the test* did, booking the 12 % it was worth as a difference between two conventions. It was a defect in the deck's lever arm — the deck applied every case at the patch while the manual applies the landing attitudes at the axle (#139) — and the move now lives in `gear_loads.application_point`. The roll and yaw lines still read the other point, because `ROLLP = ±0.83 W·CP` is built on a contact-line arm and `YAWP = ±0.83 W·BP` on an axle one; that is LANDLOAD's own choice per line and is stated rather than averaged. **The frame caveat this half used to expose is gone, and both halves of it were defects.** `LANDLOAD.BAS` resolved the ground-roll attitude at `PHIM = +BETA(2)` where the level and tail-down attitudes use `GAMMA − BETA(1)` / `−BETA(3)`, which put the braked-roll pitch line 2·GRA(2) — 9.45° on `ga6_normal` — from the rest and forced a **5 %** bound with the cause stated. That was corrected at its origin on 2026-08-29 (#133, note 38 GF-1/GF-2′), and the arm move above with it (#139), so every family now closes on the one `1e-4` bound. The 2026-08-15 decision of record to keep the manual's convention was superseded the same day — [`02_approved_corrections.md`](02_approved_corrections.md) carries both the declined entry and the ruling that superseded it. Supporting invariants: the contact-patch→trunnion transfer preserves the resultant about an arbitrary reference at 3.4e-16 (G-2's third guard, exact by construction); reflecting the odd member of a 23.485 pair reproduces LANDLOAD's **own** even-member `NS`/`ROLLP`/`YAWP` sign-flipped (G-8 — the only *external* check the reflection operator has); and the reaction sbeam recovers at each gear GID equals the gear report's reference-point reaction, in both unit systems. Three negative controls (a dropped offset couple; a level case computed at the **static axle** instead of the compressed one; the arm point and the lift term measured at 12.5 % and 5.8 % of `PITCHP`) show the gates have teeth. The second and third are anchored to `GearLegLoad.point` since 2026-08-29: they read `patch`, and when the patch stopped being the transfer point on cases 1–12 the static-axle control silently lost the ability to fire — a negative control that survives the thing it controls moving is not one. |
| `one_engine_out` (ONENGOUT — **Step C9**) | `ONENGOUT.BAS` (Appendix C pp. 492–494) | Ch 11 pp. 87–88 (FAR 23.367 one-engine-out yaw transient): unbalanced moment `MOM = thrust/windmill schedule − LT25·(XT25−XCG) − LT50·(XT50−XCG)`, `THETA2DOT = MOM/12/IZZ·57.3`, Euler-integrate `THETADOT`, `THETA` at step `DT` until recovery (`THETA<0`); `THRUST = MAXHP·550·.85/VTFPS`, windmill `DRAG = .85·.232·ρ·VTFPS²·DIA²` (Glauert), `VTFPS = (V/√σ)·1.15·88/60`; tail loads `LT25 = (THETA+damp)·AVT/57.3·Q·SVT/144`, `LT50 = EF·EFFECTV·AVT/57.3·RUD·Q·SVT/144`, `Q = V²/295`; pilot rudder initiated at peak yaw rate but ≥2 s after failure (23.367(b)). Shares `_vtail` AVT/EFFECTV/EF with SELECT. **Safety factor is a case-definition attribute (M1-5, review T7):** the SF is set by how the regulation *classifies* each load case (LIMIT vs ULTIMATE), not by the speed, and the same case definition also fixes the speed range it is considered over (evaluated at the critical high end). Being a failure case does not by itself reduce the factor. 23.367(a) (turbopropeller; Ref 1 Ch 11 p87) defines two cases — **(a)(1)** fuel-flow interruption, **limit** SF 1.5, considered VMC→VD; **(a)(2)** compressor-from-turbine disconnection / turbine-blade loss, **ultimate** SF 1.0, considered VMC→VC (limit treated as ultimate, previously double-factored at 1.5). The VMC-floor point (VS substituted for VMC = minimum control speed, per the Ch 11 Method) is a **limit** design point (SF 1.5). Declared per row in the `_LoadCase` table (`load_class`/`safety_factor`/speed range). | **No printed oracle** (Appendix B twin is absent from the bundled `reference/FAR23Loads_Code.pdf` — only the Appendix A GA single is present; FAA User's Guide Ch 22 gives partial inputs/no outputs). Locked by **sub-formula exactness** vs `ONENGOUT.BAS` + integration/physics closure (recovery, yaw-rate peak, `DT`-halving convergence) + refactor-parity with SELECT's v-tail helpers. Printed twin oracle + `examples/twin_turboprop.project.json` fixture are deferred. |

## Summary-report provenance (Step G8)

The report computes nothing, so it has no equations of its own to cite; what it
does have is **provenance for the two statements it makes about the analysis**,
and both are quoted rather than paraphrased:

- **The FAR 23 Subpart C coverage matrix** (`sloads/report/coverage.py`) — the
  static regulation list is `PROGRAM_SPEC.md`'s per-module FAR conditions
  cross-read with the **FAA User's Guide Table 2.2** module/condition map
  (`reference/FAR23Loads_UserGuide.pdf`). Each row is then classified against the
  `far_reference` values a given run actually produced.
- **The verification statement** in `sloads/report/methods.py` quotes the
  [Oracle-status](#oracle-status) wording above verbatim — oracle-locked to
  Appendix A within ±0.1%, twin/turbopropeller cases closure-locked because
  Appendix B is not bundled. It is deliberately not softened into a blanket claim
  of validation, and `SUMMARY_REPORT.md` §4.6(3) forbids doing so.

Every figure the report prints comes from the modules cited in the table above,
through the same pure builders the GUI uses; the limit→ultimate boundary is
`report/render.py`'s, unchanged.

## Base-method uncertainty (the effect-vs-error-bar datum) <a id="base-method-uncertainty"></a>

The suite's own fidelity ceiling, stated once so that scope decisions can be
measured against it (`CLAUDE.md` rule 6; 2026-08-16 scope review). The base
method is a **rigid airplane** balanced at discrete V-n points, wing airloads by
the **Schrenk** approximation (Ch 7 — no lifting-line, no aeroelastic
redistribution), the empennage as a **lumped balancing load** split 25/50 % chord
(Ch 9/10), and lumped-mass inertia (Ch 15). Against a panel method or a flexible
model that basis is good to **order 5–10 % on a distributed load** (spanwise
shear/bending at a station; body beam moment) and better than that on the
integrated totals the oracles pin (root shear, `n·W`, balancing tail load — those
close to ±0.1 % by construction). A fidelity item whose stated effect on a
delivered load is below that band buys nothing a consumer can see; one above it
is real. The number is an order of magnitude, not a tolerance — it ranks work, it
does not gate a test.

**Worked application (D-31, 2026-08-18).** The gust cases reuse the manoeuvre
**spanwise** shape rather than a gust-specific one, and that is a recorded
decision, not deferred work: Schrenk *is* this method's approximation of the
spanwise shape, so a gust-vs-manoeuvre shape difference is inside the ±5–10 %
band above **by construction** and cannot buy a consumer anything the method can
resolve. It re-opens only if the wing airload basis itself moves off Schrenk.

## Concept-mode closure validation (Step P1-2)

Concept mode (`category="C"`) has **no printed oracle** above the 12,500 lb FAR23
calibration band (Phase-C invariant 2), so its per-component distributed loads are
validated by **physics closure**, evaluated through the concept code path on the
full-airframe fixture `examples/concept_regional_jet.project.json`. The identities
and their sources (`tests/test_concept_closure.py`):

| Component | Closure identity | Source |
|-----------|------------------|--------|
| Wing (airload) | `LZW + LT = Nz·W` — total lift closes vertically | Ch 7/8; FLTLOADS `_balance` (`nz = (lz+lt)/W`) |
| Tail (balancing) | `LT·(Xt − Xcg) = LZW·(Xcg − Xw) − DX·(Zcg − Zw) + M(W+F)` — the balancing tail load reacts the wing-plus-inertia pitching moment about the CG | Ch 8/9; FLTLOADS balancing formula |
| Body (fuselage) | terminal cumulative shear `Sz = 0` **and** terminal `Myy = 0` — the net distribution (inertia + tail air load + the front/rear spar carry-through reaction) is built free-free in both ΣFz and ΣM (M4-1, closed 2026-08-03). The flagged `closure_artifact` fallback closes the same two residuals with a whole-body correction that has no physical source. | Ch 15 p103 (fuselage beam) |
| Tail (chordwise) | TAILDIST's `lt25`/`lt50` equal SELECT's stamped split verbatim, so the chordwise pressure profile sums back to the SELECT-critical tail load | Ch 10; SELECT→TAILDIST |
| Control surfaces | each `build_*` critical load matches its `run` analysis report (`lb`-unit `LoadValue`) | AILERON/FLAPLOAD/TABLOADS build↔run |
| All (export) | every component's nodal FORCE set — and its re-parsed cards — sums to that component's root/total at ULTIMATE (`limit × that case's safety_factor`, default 1.5; the factor is uniform within a case, so closure is scale-invariant — defect M4-7) | `export/sbeam_bridge` increment construction + `_sf()` |

### The balanced free-free case as a closure gate (step B2–B6, 2026-08-08)

Theory walk-through with worked examples (wing symmetric/antisymmetric, the
low-tail / T-tail lateral empennage cases, the 23.427(a) unsymmetrical
horizontal tail, and the ground/landing families — §9, where the load factor is
solved rather than given and the gate is LANDLOAD's own closed form) in
[`balanced_cases.md`](balanced_cases.md).

The FAR 23 core validates against Appendix A; the *assembled airplane* has no
printed oracle at all, so its gate is equilibrium itself. Plan 11's acceptance,
now in CI (`tests/test_balance.py`):

| Identity | Gate | Achieved |
|---|---|---|
| `\|ΣFz\|/(n·W)` before closure | < 1 % | 0.05–0.70 % |
| `\|ΣMy_cg\|/(n·W·MAC)` before closure | < 1 % | 0.12–1.04 % |
| `\|Δn\|/n` (relief applied) | < 1 % | 0.05–0.70 % |
| all six components after closure (B8a-2) | ~ 0 | ≤ 2e-16 of n·W |
| the same, re-derived from the deck's own card text | ~ 0 | ~1e-7 (card format) |
| the same, re-derived by **sbeam** from the deck's own `GRID` cards | ~ 0 | export tolerance, both unit systems |
| the symmetric half of a **lateral** case, fin load removed (B8a-3) | unchanged | exact — a fin set carries `fy`/`mz` only |
| the **trim half** of the 23.427(a) case, lumped `vn.lt` restored (D-R8) | < 1 % force, per-fixture pitch | 0.187 / −0.246 % force, 0.301 / 0.694 % pitch |
| the 23.427(a) applied halves against SELECT's own RH/LH (D-R8) | exact | 6.7e-16 relative |
| the 23.427(a) applied roll against `(RH − LH)·ȳ` (D-R8) | exact | ratio 1.000000000, both fixtures |

The pre-closure force and pitch rows are read **per family**: the lateral cases
sit at V-n points the symmetric families never visit, and their pitch residual is
larger there (ga6 `SUDDEN RUDDER` 0.341 %, RJ `SIDE GUST` 1.586 %). Ceilings are
stated per fixture *and* per family rather than merged, so the symmetric bounds
keep their bite. `residual_mx` on a rolling case and `residual_fy`/`residual_mz`
on a lateral one are **applied loads, not errors**, and are outside this table by
construction (`CONVENTIONS.md` §1). The 23.427(a) case's `Fz`/`My` are outside it
for the same reason and the strongest instance of it: its applied tail load is a
*maneuver* load replacing the trim tail load, so the residual is that mismatch in
full (−49.8 % of `n·W` on the ga6) and the closure is the pitching maneuver
itself — what is gated there is the trim half, in the rows above (D-R8, decision
of record; FAR 23.427(a) via `select_htail_unsymmetrical`, SELECT.BAS 6030-6180,
Ref 1 Appendix C p440-441, with the approved M1-4 deviation). A **powered**
case's `Fx`/`My` are outside it on the same construction and with the strongest
gate of the set: the V-n point it is assembled at is thrust-free, so the entered
hub thrust and its arm `−T·(z_hub − z_cg)` *are* the pre-closure residual in
closed form, carried by `n_x = (D − ΣT)/W` and `q̇` — asserted as an identity,
not a bound, by `tests/test_hub_thrust.py` G-3/G-4 (`balance.hub_thrust_set`,
#10; `balanced_cases.md` §2.1).

The measurement is deliberately taken **before** the closure: the gate is on what
the physics achieves, not on what the correction hides. The remaining ~0.3 %
**force** floor is the strip-versus-closed-form lift difference plan 11 R3
predicted (ga6 PHAA: the spanwise integral gives 12,940 lb against the trim's
12,969) — a model difference rather than a quadrature error, since it converges
to −42.3 lb / 0.327 % as `elements` → ∞. The **pitch** residual had a different
cause and no `elements` dependence at all — the couple left by the airplane's
non-wing drag, which nothing in the assembled model carried (measured 2026-08-15;
backlog Pri 5). Carrying it as the `body-axial` load brings pitch to the same
lift-model floor: **0.014–0.086 % on every fixture and family**, and the
per-fixture ceiling the RJ's low-CL cases needed is retired.

**The non-wing drag** (`balance.body_axial_set`) is the airplane-less-tail
polar's body-axis `x` force less what the wing strips carry — `drag_cd(config,
cl)` against `airloads`' section profile plus lifting-line induced drag, resolved
through the same `α`. That it is parasite drag rather than a lift-model
disagreement is measured: decomposing into wind axes gives `ΔL/L` ≤ 0.6 % while
`ΔC_D` is a near-constant −0.018 across all seven ga6 cases. Outside the polar's
one-sided trusted-`α` window `constants.POLAR_TRUSTED_ALPHA_DEG` = (−10°, +15°)
it inverts sign (above: the RJ's strip induced drag overshoots the polar; below:
the crude-polar fixtures' `NMAA` at −12.9…−14.3°, the fit read 13° under zero
lift) and a forward value there is **not applied** — `ΔC_D` still reported
unclamped, `body_axial_clamped` set (note 20 D-4 as revised 2026-08-17).
**Gate:** the applied axial resultant equals the trim's `dx` and `delta_nx`
equals `dx/W`, both to 1e-9, except on the recorded clamped cases where both are
the strips' own `fx`; the `ΔC_D` band is pinned per fixture and asserted
negative inside the window; the clamped set is pinned both ways with per-case
residual ceilings. Its waterline is the single owner
`derived_geometry.body_drag_waterline` — the only free parameter of the load, and
stated rather than derived because the suite has no body-centreline datum (design
note `../40_history/24_body_drag_carrier_note.md` §8.1).

One term still has no distributed carrier and is stated as lumped rather than
omitted: the fuselage's share of the airplane-less-tail `Cm` (the Munk moment,
until M4-19 distributes it — a sign-changing slope term, −6.6 to +4.9 % of
n·W·MAC on ga6 and −8.5 to +5.8 % on the RJ).

#### The relief field itself, and its two producers (step B8a-2, 2026-08-09)

**Equation.** The closure relief is the rigid-body d'Alembert field, the standard
result for a free body accelerating under an unbalanced load — **no suite source,
because no suite program assembles an airplane**:

    f_i = −m_i (a_cg + ω̇ × r_i)        moment about the CG:  −[I]{ω̇}

with `[I]` the full inertia tensor of the assembled mass set (`Ixx`…`Ixz`) plus,
per plan 13 decision L-3, the entered self-inertia of every item the assembly
carries as a *point*. So `{ω̇} = [I]⁻¹{M}` — one coupled 3×3 solve, because `Ixz`
is 8.4 % of the ga6's pitch inertia. Owner: `sloads/rigid_body.py`; conventions in
`CONVENTIONS.md` §1 and §7. Angular accelerations are carried in weight-space
`1/in` (g per inch of arm), the same convention that makes the translational DOF
come out as load factors.

Having no printed oracle, the field is gated by **identities against independent
producers**, one per rotational degree of freedom — which is what makes this a
substitute rather than a self-check:

| DOF | Independent producer | Status |
|---|---|---|
| **yaw** | `ONENGOUT.BAS` 282-286 — `THETA2DOT = MOM/12/IZZ·57.3`, Ref 1 Ch 11 p87-88 (FAR 23.367). **Oracle-locked FAR 23 code**, checked step by step against its own time history | exact, `rel_tol = 1e-12` |
| **roll** | `WINGINER`'s `fz_r`/`iwxx` unit-roll recurrence (Appendix A-locked). Reproduces the **shape** strip for strip; the **magnitude** ratio is the wing span's share of the roll moment — 0.795230 ga6 / 0.769455 RJ — because WINGINER's wing-only model has no term for mass off the roll axis | shape exact; ratio pinned |
| **pitch** | none — `Iyy` has no second producer in the suite. Carried by the closure identity `Σ r × f = −[I]{ω̇}` and by the six-DOF closure itself | identity only |
| **the tensor** | `WTONECG` (Appendix A p136 oracle) via `Izz(closure) = Izz(WTONECG) − wing self-Izz + Σw·y²(WINGINER spread)` | 0.0 % ga6, +0.40 % RJ |

**A caution recorded with the yaw row:** the two producers meet on no shipped
fixture — the two airplanes that assemble a balanced case enter no
`one_engine_out` slice, and the two that enter one carry no engine horsepower, so
ONENGOUT cannot execute on any fixture as shipped (filed on the backlog). The
gate supplies that single input and reads everything else from the fixture.

#### The lateral (±β) cases (step B8a-3, 2026-08-09)

**Equations.** No new aerodynamics: the fin load is SELECT's, `LV` per FAR
23.441(a)(1)–(a)(3) and 23.443(b) (cited in the `select` row above, Ref 1 Ch 9,
`SELECT.BAS` subr 8300), distributed along the span by `tail_span`'s
chord-proportional shape and mapped to airplane axes by `export/coordinates.py`.
What is new is the **lateral balance**, which is the same rigid-body statement as
the symmetric one, read in the other three DOF:

    ΣFy = 0  →  n_y = L_v / W
    ΣMz = 0  →  ψ̈ from the coupled {ω̇} = [I]⁻¹{M} solve above
    ΣMx = 0  →  ṗ, coupled to ψ̈ through Ixz; the fin's own roll moment is
                −L_v·(z_fin − z_cg), which is why the fin root waterline is a
                load quantity (B8a-1, `CONVENTIONS.md` §7.2)

**Why the 1 % residual gate does not apply here.** `residual_fy` and
`residual_mz` before closure *are* the fin load, by construction — nothing in an
airplane balances a rudder kick. The gate that does apply is that the case's
**symmetric half** still closes (`CONVENTIONS.md` §1); it does exactly, since a
fin set carries `fy` and `mz` only. Same standing as `ACRL`'s roll residual.

Having no printed oracle, the cases are pinned by measurement in both directions
(`tests/test_balance.py::test_the_lateral_cases_are_pinned`, `rel_tol = 1e-4`),
with `n_y` additionally asserted **structurally** as `L_v/W` rather than only
pinned:

| Condition | ga6: `L_v` lb / `n_y` g / `ψ̈` / `ṗ` deg/s² | RJ: `L_v` lb / `n_y` g / `ψ̈` / `ṗ` deg/s² |
|---|---|---|
| `SUDDEN RUDDER` | +585.7 / +0.17227 / +178.05 / −12.04 | +6907.3 / +0.20931 / +51.57 / −57.75 |
| `YAW TO SIDESLIP` | −97.8 / −0.02875 / −19.44 / +3.24 | −3548.2 / −0.10752 / −20.84 / +31.13 |
| `YAW 15 NEUTRAL` | −525.7 / −0.15463 / −151.91 / +11.75 | −8042.7 / −0.24372 / −55.70 / +68.37 |
| `SIDE GUST` | +604.0 / +0.17764 / +185.51 / −20.16 | +7080.4 / +0.21456 / +42.93 / −77.88 |

The fin loads reconcile with Appendix A's printed vertical-tail totals (+591 /
−92 / −526 / +604 — see the `select` row): they are the same numbers, since the
balance consumes SELECT and never recomputes it.

**The wing-body sideslip term** (decision L-7, shipped 2026-08-17 — see the
`lateral_body_aero` row above): the wing-body side force and yawing moment in
sideslip are computed per case and applied beside the fin's load when
`aero_coeffs.lateral_body_aero.enabled`; **off by default**, because the term
raises `|n_y|` (the side force adds to the fin's at `+β`) and lowers `|ψ̈|` (the
body's couple is destabilizing and opposes the fin's) — with it off `ψ̈` is
over-stated (conservative) and `n_y` **under**-stated (not conservative), by the
amount every lateral case now states. Measured on the shipped fixtures, term on
vs off: `concept_regional_jet` `|n_y|` +11 % / +11 % / +33 % and `|ψ̈|` −73 % /
−71 % / reversed on `YAW 15 NEUTRAL` / `SIDE GUST` / `YAW TO SIDESLIP`;
`ga6_normal` `|n_y|` +27 % / +27 % / ×2.9 and `|ψ̈|` −41 % / −40 % / reversed.
The 23.441(a)(2) reversal is the regulation's overswing past equilibrium under
full rudder, not a failure (note 19 §4); the valid gate is static directional
stability, `Cn_β,fin + Cn_β,body < 0` about `xw` — RJ −0.00154/deg (fin −0.00486,
body +0.00332), ga6 −0.00107/deg (fin −0.00176, body +0.00069). The fin's own
design load (SELECT's) is untouched. The distributed per-station body load is
still paired with M4-19; the lumped term is carried in-band on every lateral case
rather than living only here.

### The spanwise empennage closures as the oracle substitute (step T1–T5, 2026-08-08)

Appendix A gives the tail's **totals** (SELECT) and its **chordwise** profile
(TAILDIST) and stops. There is no printed oracle for a spanwise tail
distribution, so the gate is `CLAUDE.md` practice 2's substitute — and the
chord-proportional shape (decision T-2) makes it an unusually strong one, because
every target is **analytic** rather than a re-run of the quadrature.
`sloads/modules/tail_span.py`; gates in `tests/test_tail_span.py`.

**Where that beam is supported has no oracle either (T-8a, 2026-08-15).** The
attachment stations are a *geometry* statement, not a load one, so no Appendix A
figure moves with them and none can validate them. The gate is therefore
structural rather than numeric: `tail_span.htail_attachment` is the single owner
and returns the stations **with their provenance**, `tests/test_tail_span.py`
pins one test per branch (T-tail fin tip / body outline interpolated at the
h-tail LRA station / the stated `±ds/2` pair), and the outline test asserts the
interpolated width is under a quarter of the maximum section — the guard against
silently reverting to `derived_geometry.fuselage_summary`, whose maximum is five
times too wide at `atr42_100`'s h-tail. The branch a consumer may build
structure on is named by `attachment_basis`, never inferred.

Per strip `j` of the **whole** planform area `S`, with `LT25`/`LT50` read from
SELECT and never recomputed (T-7):

    w25 = k_side·LT25·(c_j·dy)/S      w50 = k_side·LT50·(c_j·dy)/S
    fz  = w25 + w50                  tor = w25·(x_lra − x_25) + w50·(x_lra − x_50)
    fi  = −n_n·W_surf·(c_j·dy)/S     (d'Alembert, T-9; n_n = the surface's own normal-axis factor)
    fa  = −n_a·W_surf·(c_j·dy)/S     (axial along the span — the fin only)

`W_surf` is derived from the `htail`/`vtail`-tagged `weight.items` since
2026-08-10, not entered: see "The fin's two inertia axes" below.

| Closure | Analytic target | Why it is not a tautology |
|---|---|---|
| **Force** | Σ air = `LT25 + LT50` exactly | The target is SELECT's own total; a factor-of-two in the half/full bookkeeping lands here |
| **Bending** | root = `L_half · ȳ`, with `ȳ = (b/3)(c_r + 2c_t)/(c_r + c_t)` | The centroid is computed from the planform, not from the load table |
| **Centreline rolling** | `(L_RH − L_LH)·ȳ` — **identically zero for every symmetric case** | The gate the full-span topology buys; a per-side deck cannot state it, and a mirrored-wrong half or mis-signed side scale is invisible to a force sum |
| **Torsion** | `(LT25+LT50)·x̄_lra − LT25·x̄_25 − LT50·x̄_50`, area-weighted | Assembled from area-weighted chordwise means, a different computation from the per-strip sum |
| **Inertia** | Σ = `−n·W_surf`, **signed by `n` alone** | Companion test asserts a *down*-load case comes out **larger** in magnitude than air alone |
| **Reduction** | LRA at 25 % chord ⇒ the `LT25` torsion term vanishes identically | Same property the wing's LRA transfer is pinned by |

**The inertia-sign gate is the one worth naming.** The intuitive rule — inertia
opposes the air load — is wrong for a tail, and wrong in the unconservative
direction: the GA6 conditions that size the horizontal tail are down-load
(`UNCHECKED MAN DN`, ≈ −1400 lb), so a magnitude-opposing rule would relieve
exactly them. Decision T-9 makes the sign `−n` unconditionally, and the test
asserts the *increase*.

All six closures are additionally checked against a **tapered and swept**
planform, because every shipped fixture takes the derived rectangle — without
that, the torsion transfer term (identically zero on an unswept surface) would
never be exercised.

**Deck-side, the same conditions are gated twice more:** the plan-07 invariant
sweep gains a spanwise h-tail row (force, and the centreline rolling moment: zero
symmetric, non-zero for 23.427(a)) and a v-tail row (the load is `Fy` and the
torsion `Mzz` — a force-only check in the wrong component would still "close"),
and plan 10's harness solves both decks in the real sbeam.

### The discrete control-surface path and the first hinge moment (step T6, 2026-08-13)

Also without a printed oracle, and gated the same way. The control-surface load
itself is **not** new physics — it is `select.elevator_load` (SELECT.BAS
5216-5218) and its rudder counterpart, Appendix-A-locked and here only *read*,
decomposed into the two parts it is the sum of so each can leave the spanwise
distribution from the chord station TAILDIST placed it at. What is new is where
that load enters the structure, and the moment it makes about the hinge line.

    c_e   = CEAFTHL = (Saft/S)·CAVE       aft-of-hinge chord              (TAILDIST)
    e     = c_e/3                         centroid of the aft-of-hinge block
    HM    = L_cs·e                        the hinge moment
    hinge i: F_i = k_side·L_cs·t_i        chord-weighted tributary, Σ t_i = 1
             M_i = F_i·(x_lra − x_hl)
    actuator: M_a = −HM

**The third is exact, not a rule of thumb.** TAILDIST's net trailing-edge
pressure is identically zero (`WATT3 = WCAM3 = 0`), so the pressure block aft of
the hinge line is *always* a triangle running from its hinge-line value to
nothing — whatever the condition, whatever the deflection — and a triangle's
centroid is a third of its base. That is what lets the suite's first hinge-moment
output be gated by a closed form instead of a quadrature.

| Closure | Analytic target | Why it is not a tautology |
|---|---|---|
| **Cross-mode force** | `ΣF(discrete) == ΣF(smeared)`, `rel_tol 1e-12` | The identity is a property of the *construction* (exactly `L_cs` removed, exactly `L_cs` applied), not of the strip quadrature — which would be exact for a derived rectangle and only 1 %-true for an entered polyline |
| **Hinge set** | `Σ F_hinge == L_cs`; the actuator carries no force at all | The load arrives from SELECT and is shared by a tributary rule the test derives independently (25 / 50 / 25 % for hinges at 10 / 40 / 70 in) |
| **Chordwise identity** | hinge torsion + actuator couple = `L_cs·(x_lra − x_cp)`, `x_cp = x_hl + c_e/3` | Reverse the actuator's sign and the sum lands on the hinge *line* — a 4.86 in chordwise error on ga6 with nothing else in the deck to notice it |
| **Cross-mode torsion** | moves by exactly `att·x_25 + cam·x_50 − L_cs·x_cp` | Stated as an identity rather than "within a tolerance", so the difference is *explained* (one chordwise relocation) rather than merely bounded |
| **Mode isolation** | no attachment geometry ⇒ every shipped deck and Imperial digest unchanged | The default path is pinned byte-for-byte, so a discrete-mode defect cannot leak into the mode nobody selected |

Where a condition publishes no control-surface load of its own — the balancing,
checked, gust and unsymmetrical h-tail conditions, and the rudder-neutral fin
ones — the load is **derived** by integrating the aft-of-hinge block
(`0.5·c_e·ψ(x_hl)·span`) and marked as derived on the result, the page, the CSV
and the deck header. Derive-and-mark, the same contract the tail planform is
under.

### The T-tail transfer (step T7, 2026-08-13)

A rational-pairing decision (T-5) rather than a closure: for each v-tail case,
the **balancing** horizontal-tail load at that case's own V-n point plus that
point's h-tail inertia, carried at the fin's last node. Its gate is a free-body
statement read from the deck's own card text — the fin deck's resultant about the
origin equals the v-tail-only resultant plus the transferred set at its stated
node — plus byte-level gating isolation: flip `tail_type` back to conventional
and the deck returns exactly. `concept_regional_jet` is the suite's only T-tail
fixture, so it is the only Imperial digest the step moves.

### The fin's two inertia axes, and its exact-ratio closure (2026-08-10)

A surface's inertia is built on the acceleration along **its own normal axis**,
and that is where the two empennage surfaces stop being alike. The h-tail's
normal axis is the airplane's vertical, so `n_n = n_z` and there is no axial
term. The **fin spans in `z`**, so the same vertical acceleration runs *along*
its beam: it takes `n_n = n_y` for bending and `n_a = n_z` for an axial column
that compresses the surface and produces no bending at all.

`n_y` has no producer in a single-condition view — a lateral load factor is a
property of a balanced case — so it is derived the one self-consistent way
available, from the only lateral aerodynamic load the suite models, which is the
fin's own:

    n_y = (LT25 + LT50) / W_case          W_case = the condition's V-n CG case weight

That makes the fin's closure **exact and case-independent**, which is why it is
the gate:

| Closure | Analytic target | Why it is not a tautology |
|---|---|---|
| **Fin lateral inertia** | `Σ inertia / Σ air ≡ −W_vt/W_case` | The left side comes out of the strip quadrature; the right is two scalars it never touches. `n_y ∝ Fy` cancels the air load out of the ratio, so the identity holds on a rudder kick and a side gust alike — and fails immediately if the *vertical* factor is reached for where the lateral one belongs |
| **Fin axial column** | `Σ f_span = −n_z·W_vt`, and root bending unchanged by it | An axial load has no moment about its own line of action; asserting both at once catches it leaking into the bending channel |

**Two limitations, both stated in-band on every fin result rather than only
here.** First, the term **relieves**: the surface total comes out at exactly
`(1 − W_vt/W_case)` of the air load — 0.68 % on `ga6_normal`, 1.84 % on the
regional jet — which is the *unconservative* direction, and small only because a
fin is light. Second, it inherits decision **L-7**: with the wing-body sideslip
term off (the shipped default) the real airplane's `n_y` is *larger* than this
one (the missing side force adds to the fin's), so the relief above is a lower
bound on itself; with the term on the balanced case carries the larger `n_y`
and the relief follows it.
A condition naming no V-n point has no `W_case` and therefore gets **no** lateral
term, reported rather than filled with a gross-weight stand-in.

This supersedes plan 13 decision **L-8** for the per-condition view (user
decision, 2026-08-10). The assembled balanced case still accounts for the fin's
mass in its closure field, so the applied aerodynamic set it reads from
`tail_span` is taken as `fz − f_inertia`: each mass enters exactly one field.

### The rolling case's roll closure as a closure gate (step B7, 2026-08-08)

The balanced-case gate above is a *smallness* gate: the residual before closure
must be under 1 %. An **antisymmetric** case cannot be gated that way, because
what it is out of balance in is not an error. On an accelerated-roll condition
(FAR 23.349) the applied aileron couple is 6.71 % of `n·W·b/2` on `ga6_normal`
and 2.00 % on `concept_regional_jet`, and the airplane is *supposed* not to
balance it — it rolls. The couple is reacted by roll acceleration, exactly as
drag is reacted by `nx`: nothing else in a free-free model can.

So the gate here is an **identity against an independent producer** instead.
Closing the roll residual with mass-proportional relief `k·w_i·y_i` (physically
`−m_i·ṗ·y_i`) must reproduce **WINGINER's own unit-roll inertia distribution** —
`fz_r[i] = w_i·y_i·10⁵/Iwxx`, WINGINER.BAS's accelerated-roll case, which is
oracle-locked FAR 23 code that this step did not touch and that knows nothing
about the balance layer:

| | ga6_normal ACRL | concept_regional_jet ACRL |
|---|---|---|
| UNB (in-lb) | −149,043 | −600,000 |
| per-strip closure ÷ `ur·fz_r` | **1.000000** | **1.000000** |
| net force added by the roll term | 6.4e-14 lb | 2.3e-13 lb |
| `residual_mx` vs `−UNB` | exact | exact |
| all six DOF after relief | machine precision | machine precision |

The wing-item/WINGINER-panel scale (0.9903 and 1.0100) **cancels identically**,
because the closure normalises on the same masses the assembled model carries —
which is why the agreement is exact rather than approximate, and why it is a
gate rather than a coincidence. Both twins then solve in the real sbeam with
determinate-support reactions ≈ 0 (plan 10's assembled leg).

Sign, recovered rather than assumed: WINGINER's unit-roll set produces a rolling
moment of exactly `+UNB` (its normalisation makes `Σ y·fz_r = 100,000` for a unit
case, verified), and NETLOADS enters inertia opposing the air load — so the *aero*
couple is `−UNB`. The strip-for-strip identity is what confirms that sign is
right rather than merely self-consistent.

**Scope limit, stated in-band wherever the case is rendered:** the aileron's own
lift increment has no spanwise carrier (`AileronLoadsInput` has areas, no butt
lines), so the couple is lumped at the wing aerodynamic centre. This reduces
*exactly* to the oracle-locked model — WINGINER also carries only the inertia
reaction — but it means `ACRL` wing bending omits the differential lift itself.
Filed on the backlog.

### The CONM2 mass model as an *external* check (step C1–C5, 2026-08-08)

Every closure gate above is internal: sloads checking sloads. The distributed
**inertia** load has no printed oracle and, until this step, no external check
either — the same code computed it and wrote it out, so no artifact could
disagree. The `CONM2` export supplies one: sbeam parses the mass model
independently, and its own grid-point-weight generator recovers weight, CG and
inertia from it.

Verified by hand 2026-08-08 (sbeam is not a dependency, so CI cannot run it):
`sbeam.gpwg.compute_gpwg` reproduces sloads' mass, CG-x and CG-z for all four
`ga6_normal` payload cases exactly. The `GRAV`-driven nodal-inertia comparison
(plan 12 C6) needs the round-trip harness and is filed.

Two scope limits, stated rather than discovered: `GRAV` is a uniform
*translational* field and sbeam has no `RFORCE`, so rotational-acceleration
inertia (pitch/yaw) is not recoverable from a `CONM2` set and stays checked by
sloads-side closure; and a payload case is only exported when the weight database
can produce it as a loading — 7 of the 18 shipped cases, all four of ga6's among
them.

### The mass model as a closure gate (step B1, 2026-08-08)

The Ch 15 fuselage beam has no printed oracle (Ref 1 ships no program for it), and
its *input* — the longitudinal mass distribution — had none either: it was a
hand-entered lump table that nothing checked. Step B1 makes
`weight.items` the single source and gates the beam on reconciliation identities
instead (`sloads/mass_distribution.py`, `tests/test_mass_distribution.py`):

| Identity | What it locks |
|---|---|
| `Σ(wing items) + Σ(beam stations) == Σ(all items) == W` | The partition is complete: no item lost between the two distributions, none counted twice |
| `Σ(items tagged wing) == 2 × (panel_weight_lb + Σ concentrated)` | The itemized wing and WINGINER's spanwise model describe one wing. Both WINGINER terms are per **side**, so the airplane carries twice their sum. **Holds on every shipped fixture since design note 29 (2026-08-17):** the wing-tank share of a fuel row is stated as `MassItem.wing_fraction` (derived from WINGINER's own `concentrated` entry — 3,800 / 4,000 / 1,200 lb on the three fuel-in-wing fixtures, no number invented) and read through `reacted_parts`; before it those pounds rode both beams — 7–15 % of the body beam, above the base-method band — and were pinned open. The tie is the invariant gate for that step (no printed oracle covers a fuel split), and it is a validator (`wing_mass_tie_open`) as well as a test |
| entered `fuselage_mass.stations` vs the derived table | Reported, never silently taken — the two disagreed by 10–100 % of the beam on every shipped fixture |

The beam carries the empennage (it hangs off the aft fuselage) and excludes the
wing (which enters as the Ch 15 p103 carry-through reaction — applying it as mass
too would double it). The free-free closure the beam already satisfied
(`ΣFz = 0`, terminal `Myy = 0`) is unchanged by all of this: it held on the light
beam and holds on the correct one, which is precisely why it could not have caught
the missing mass.

### The entered loading, and what checks it (D-25, 2026-08-15)

There is **no printed oracle for a loading**: Appendix A prints weights, CGs and
inertias, never the item set behind a CG case, and WTONECG/WTENV take the loading
hierarchy as data. The suite's answer had been to *derive* one — search the
discretionary subsets of `weight.items` for a set that reproduces the case's
weight and CG with a solved ballast row inside the fuselage — which is a search,
not a source. D-25 makes the loading an input (`CgCase.loading`), following the
same `MassItemKind` partition WTONECG's database uses (empty → minimum flight
weight → discretionary useful load, Ref 1 Ch 4), with fuel treated as continuously
burnable per 23.473(b)/(c) as decision G-5 already established for the derived
route.

What replaces the missing oracle is a **checked echo** (D-25a) plus a reduction
identity, both in CI:

| Gate | What it locks |
|---|---|
| `Σw`, `Σwx/Σw`, `Σwz/Σw` of the entered loading vs the case's `weight_lb`/`xcg`/`zcg`, within `max(0.5 lb, 0.1 %)` and `0.5 in` | The stated loading really is the case it claims to be. The loading is authoritative, so this is *reported*, never absorbed by adjusting the loading |
| entering the loading the search finds reproduces the searched result item-for-item (`rel=1e-12`) | The entered route is a superset of the derived one, not a second answer — the same reduction rule concept mode obeys against FAR 23 |

The credibility gate (10 % ballast) stays on **solved** ballast only (D-25d): a
number the tool invented has to be plausible, whereas a number an engineer states
is data — and stress/flight-test ballast on a real airplane is not bounded by what
a search finds comfortable. The fraction is stated everywhere the case appears
rather than being silently accepted.

### The export-boundary closure gate (step 1, 2026-08-08)

The identities above are evaluated on in-memory results. Because concept mode has
no printed oracle, the **deliverable itself** needs a stated closure gate too
(`CLAUDE.md` required practice 2) — the deck a solver actually reads, not the
objects it was rendered from. `sloads/export/equilibrium.py` re-derives Σ`FORCE`
and Σ`MOMENT` **from the emitted card text**, about the per-component reference
of `CONVENTIONS.md` §1, and `tests/test_export_equilibrium.py` sweeps every
shipped example × {Imperial, SI} × every deck family:

| Deck | Force closure | Moment closure | Basis |
|---|---|---|---|
| Wing | Σ`FORCE`.Fz/Fx = SF × root `Sz`/`Sx` | Σ`MOMENT`.My = SF × root `Myy`; Σ`FORCE` moment about the root station = SF × root `Mxx` | Ch 14 (net loads); WINGINER quadrature |
| Body | Σ`FORCE`.Fz = 0 | Σ`FORCE` moment about the aft-most `GRID` = 0 | **Ch 15 p103** — the fuselage beam is assembled free-free (inertia + tail air load + wing carry-through), so its equilibrium statement is `Σ = 0` |
| Tail | Σ`FORCE` = SF × (`LT25`+`LT50`) on the surface's normal axis (h-tail `Fz`, fin `Fy`) | chordwise first moment = the profile's own (deck ↔ CSV cannot disagree), about `My` / `Mz` respectively | Ch 10 |
| Control | Σ`FORCE`.Fz = SF × critical load | — (no geometry; chord-fraction profile) | AILERON/FLAPLOAD/TABLOADS |

Two findings recorded because they are the kind that get re-proposed:

1. **The invariant is not `Σ FORCE = n·W`.** That form (as originally worded) is
   unrealizable per-component: the body deck already closes to *zero*, the decks'
   case ids are disjoint by construction so no case pairs a wing, body and tail
   block, and the wing deck is a root-clamped half-span whose root shear is not
   `n·W/2` (fuselage-carried lift plus inertia relief; and doubling is wrong for
   the antisymmetric cases outright). The assembled-airframe `n·W` closure is a
   separate item, pairing with the assembled stick model.
2. **A beam torsion is not a rigid-body moment** — see `CONVENTIONS.md` §1. The
   wing torsion claim is on the applied `MOMENT` cards; only bending integrates
   the `FORCE` lever arms.

Tolerances have one owner (`equilibrium.REL_TOL` / `ZERO_REL_TOL`): `1e-4`
relative against a non-zero target, and against a **zero** target
`1e-6 × Σ|term| + 1e-3` in deck units — summed, not maxed, because the error
being bounded is accumulated `%.6E` card truncation (~5e-7 per card).

### The solver round-trip as a closure gate (step 2, 2026-08-08)

The gate above reads the deck's own card text; this one hands the deck to
**another program**. Where no printed oracle exists, an independent *consumer*
reproducing the numbers is the strongest substitute available (`CLAUDE.md`
required practice 2), and it is the only form that covers whether the deliverable
is solvable at all. `sloads/export/roundtrip.py` parses and solves each deck
through sbeam's own `parse_bdf` / `run_sol101`, and
`tests/test_sbeam_roundtrip.py` sweeps `ga6_normal` + `concept_regional_jet` ×
{Imperial, SI} over four deck families. Design note:
`docs/40_history/17_sbeam_roundtrip_ci_harness_plan.md`.

| Deck | What the solver must reproduce | Independent of the cards? |
|---|---|---|
| Wing (stick, as exported) | reaction = −Σ applied (force and moment, about the deck's own clamped node); reaction `T3` and element-1 end-B `SHEAR-1`/`BENDING-2`/`BENDING-1` = SF × root `Sz`/`Mxx`/`−Mzz` | **Yes** for the last two — the target is the NETLOADS quadrature (`r.stations[0]`), while the cards come from `wing_nodal_loads` |
| Body (test-only wrapper, determinate support) | the deck **solves**; Σ reactions = 0; and every element's `SHEAR-1`/`BENDING-2 B` = −SF × cumulative `Sz` / +SF × cumulative `Myy`, station by station | **Yes** — sbeam reassembles the whole Ch 15 p103 cumulative table from the `FORCE` cards and `GRID` coordinates alone |
| Tail (test-only wrapper, clamped at the LE station) | the deck solves; reaction `T3` = −SF × (`LT25`+`LT50`); reaction moment about the LE station = the chordwise first moment | Partly — the total is Ch 10's, the moment is the deck's own profile |
| Assembled full-span (as exported) | the deck solves and **all six** reaction components are zero at its determinate support | **Yes** — the target is the constant 0 |

Three points of substance, none of them re-derivable from the card-sum gate:

1. **Never a root-node moment comparison** (decision S-6). The wing stick model's
   clamped node sits half a strip inboard of station 0 and, on a swept wing,
   offset in `x`, so its reaction moment is *not* station-0 `Mxx`/`Myy` — on
   `ga6_normal` PHAA, −1.847E5 against a −91,410 lb-in root torsion. Element 1 is
   the exception the identities rest on: `_root_node` copies station 0's `x` and
   `z`, so that element lies exactly along `y` and its local frame is a fixed
   permutation of the airplane axes.
2. **"Reactions ≈ 0" is the free-free proof, not a modelling convenience.** SOL
   101 has no inertia relief (sbeam's `SUPORT` is SOL 144 only), so the free-free
   decks carry a **statically determinate** support, which by construction
   carries exactly the residual the applied set fails to balance — computed from
   the lever arms *sbeam* derives from the deck's `GRID` cards, not the ones
   sloads used. A deck that closes on paper but reacts non-zero here has a
   geometry error no card sum can see; the third negative test below demonstrates
   exactly that.
3. **The gate is shown to bite.** Three mutation tests assert it *fails*: a wing
   `FORCE` card scaled by 1.01, two `SUBCASE`s' `LOAD` ids swapped, and one body
   `GRID` displaced by 1 % — the last of which leaves every force sum in the deck
   closing exactly, so only the solve can catch it.

Tolerances are the export-boundary gate's own (`equilibrium.closes`), deliberately:
the two gates must never disagree about what "equal" means.

**Recorded solver finding (2026-08-08).** sbeam's `recover_reactions` subtracts
the *unreduced* applied vector at the constrained DOFs, so a load that a rigid
element transfers onto a constrained node is never subtracted and reappears as
reaction. Found here: `concept_regional_jet`'s fuselage carries the tail air load
at exactly a mass lump's station, and the support at that node reported 1738.13 lb
against an applied set closing to 0.007 lb — to the pound, the tied node's own
load. The harness supports elsewhere (`roundtrip._supportable`), which costs
nothing since determinacy needs two distinct positions and not two particular
ones. This is a finding *about sbeam*, filed for that repository, not a sloads
defect.

These hold to machine precision on the concept fixture (wing/tail rel ≈ 1e-16, body
terminal shear ≈ 1e-12 lb). The wing-`Nz·W` and tail-moment identities deliberately
re-use the FLTLOADS equilibrium formulas — their purpose is to prove the **concept
branch stays balanced** (no silent NaN / unbalanced result), not to re-derive the
aero. The FAR23 identity (concept reduces exactly to FAR23 on GA inputs) is a
separate guard, Step P1-3.
