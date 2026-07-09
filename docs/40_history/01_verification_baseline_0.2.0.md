# Verification Baseline — Release 0.2.0

Permanent regression-baseline record for the `0.2.0` release
(`RELEASE_PROCESS.md` §4.4 / backlog step R4). One table per module: the
condition checked, the printed Appendix A/B (or worked-example) figure the
manual gives, the reference-page citation, and the tolerance the test enforces.

**How to read "Computed vs. printed."** Every row below is a currently-passing
`math.isclose(computed, printed, rel_tol=...)` (or exact-equality) assertion in
`tests/test_<module>.py` — by definition the module's *computed* figure equals
the *printed* manual figure to within the stated tolerance, verified by the
`0.2.0` test run: **257 passed, 0 failed** (`pytest`, coverage ~92%,
`ruff check farloads/ cli.py` clean). This document does not duplicate the
computed number as a separate column; it records what the suite locks against
and where that figure comes from, so a future regression is traceable back to
a manual page. Tolerance follows `docs/10_standard/00_program_overview.md`
"Decision 3" (modernized math ⇒ ±0.1% regression oracle, `rel_tol=1e-3`, unless
a module states a wider tolerance for a specific noisy quantity — e.g.
FLTLOADS' AoA-balance convergence noise).

All fixtures are **Appendix A** (the 6-place GA single, `examples/ga6_normal.project.json`)
unless noted otherwise. **No Appendix B (10-place twin turboprop) printed table
is in the bundled `reference/FAR23 loads (1).pdf`** — see "Closure-locked
modules" at the end for the modules this affects (ONENGOUT, the LANDLOAD wheel
table, AIRLOAD4's swept branch) and the engine module's Appendix-B-style inline
turboprop hand-calc, which is the one exception (an inline worked example, not
a printed table).

---

## WTESTIMA — Weight estimation

Appendix A p133. Tolerance: **exact** (source BASIC prints truncated `INT(...)`
integers).

| Condition | Printed figure | Tolerance |
|---|---|---|
| Max take-off weight | 3468 | exact |
| Useful load | 1318 | exact |
| Empty weight | 2150 | exact |
| Empty/take-off ratio | 0.62 | exact |
| Options & miscellaneous | 99 | exact |
| Wing | 359 | exact |
| Fuselage | 340 | exact |
| Tail | 81 | exact |
| Nacelle | 50 | exact |
| Landing gear | 198 | exact |
| Controls | 52 | exact |
| Total structure | 1081 | exact |
| Engine installed (incl. propeller) | 490 | exact |
| Propeller (included above) | 83 | exact |
| Fuel system | 52 | exact |
| Exhaust | 72 | exact |
| Other engine details | 86 | exact |
| Total powerplant | 700 | exact |
| Instruments & nav equip | 15 | exact |
| Pneumatics | 3 | exact |
| Electrical | 83 | exact |
| Electronics | 0 | exact |
| Furnishings & equipment | 152 | exact |
| Environmental & anti-ice | 10 | exact |
| Misc other system wt | 0 | exact |
| Total systems weight | 268 | exact |

---

## WTONECG — Weight/CG/inertia, one loading

Appendix A p136 (aft gross weight loading). Tolerance `rel_tol=1e-3` unless noted.

| Condition | Printed figure | Tolerance |
|---|---|---|
| Weight | 3400 | exact |
| XBAR (fuselage station) | 84.99936 | 1e-3 |
| ZBAR (waterline) | 92.57932 | 1e-3 |
| IXX (slug-ft²) | 1201.527 | 1e-3 |
| IYY (slug-ft²) | 2058.209 | 1e-3 |
| IZZ (slug-ft²) | 3022.766 | 1e-3 |
| IXZ (slug-ft²) | 134.4063 | 1e-3 |
| IXX (lb-in²) | 5566051 | 1e-3 |
| IYY (lb-in²) | 9534613 | 1e-3 |
| IZZ (lb-in²) | 14002901 | 1e-3 |
| IXZ (lb-in²) | 622634 | 1e-3 |
| IX(P) principal | 1191.662 | 1e-3 |
| IY(P) principal | 2058.209 | 1e-3 |
| IZ(P) principal | 3032.632 | 1e-3 |
| Principal-axis angle θ (deg) | 4.198392 | 2e-3 |

---

## WTENV — Weight/CG envelope

Ch 3 p21-22 (6-place single). Tolerance `rel_tol=1e-3` unless noted.

| Condition | Printed figure | Tolerance |
|---|---|---|
| Aft gross station | 85.1 | 1e-3 |
| Forward gross station | 77.49 | 1e-3 |
| Forward regardless station | 72.64 | 1e-3 |
| Minimum flight weight | 2063 | 1e-3 |
| Minimum flight weight station | 73.09 | 1e-3 |
| Maximum loading weight | 3322 | 1e-3 |
| Maximum loading station | 84.56 | 1e-3 |
| Aft gross ballast weight | 78 | 1e-3 |
| Forward gross ballast weight | 418 | 1e-3 |
| Forward regardless ballast weight | 158 | 1e-3 |
| Forward gross ballast station | 80.27 | 1e-3 |
| Forward regardless ballast station | 70.97 | 5e-3 (hand-calc rounding) |
| Aft gross point weight (FLTLOADS CG1) | 3400 | exact |
| Forward regardless point weight (FLTLOADS CG4) | 2800 | exact |
| Minimum weight point station | 73.09 | 1e-3 |

**Approved deviation.** The aft gross ballast station is **not** matched to
the manual's printed figure — the test instead bounds it (107.0 < station <
110.0) against the exact moment-balance result (~108.5); the manual's own
hand-rounded 103.7 is explicitly rejected as the target in the test docstring
(a documented, code-side improvement over a rounding artifact in the source
BASIC, not an oracle failure).

---

## WINGGEOM — Wing geometry

Appendix A p141 (wing), p142 (aileron). Tolerance `rel_tol=1e-3` unless noted.

| Condition | Printed figure | Tolerance |
|---|---|---|
| Area per side | 13257 | 1e-3 |
| MAC | 69.246 | 1e-3 |
| YLE(MAC) — butt line of MAC | 87.854 | 1e-3 |
| XLE(MAC) — station of MAC LE | 63.641 | 1e-3 |
| Aspect ratio | 6.095 | 1e-3 |
| Span | 402 | exact |
| Aileron-path area per side (p142) | 932 | 2e-2 |
| Aileron-path MAC (p142) | 11.645 | 2e-2 |
| Aileron-path aspect ratio (p142) | 7.036 | 2e-2 |

---

## STRSPEED — Structural design speeds

Appendix A (V-n/geometry table). Tolerance `rel_tol=1e-3` unless noted.

| Condition | Printed figure | Tolerance |
|---|---|---|
| Limit positive load factor | 3.8 | 1e-3 |
| Limit negative load factor | -1.52 | 1e-3 |
| Maneuver speed VA | 121.3 KEAS | 1e-3 |
| Cruise speed VC | 170 KEAS | 1e-3 |
| Dive speed VD | 212.5 KEAS | 1e-3 |
| Flap speed VF | 105.5 KEAS | 1e-3 |
| Minimum cruise VC(min) | 141.8 kt | 2e-3 |
| Cruise Mach MC (12000 ft shoulder) | 0.323 | 3e-3 |
| Dive Mach MD (12000 ft shoulder) | 0.403 | 3e-3 |

---

## MACHLIM — Mach-limit lines

Appendix A p160. Tolerance `rel_tol=1e-3`.

| Condition | Printed figure | Tolerance |
|---|---|---|
| Never-exceed Mach MNE | 0.3627 | 1e-3 |
| Flutter-clearance Mach MFC | 0.4836 | 1e-3 |
| V(MC) at 12000 ft (shoulder) | 170.16 | 1e-3 |
| V(MNE) at 12000 ft | 191.08 | 1e-3 |
| V(MD) at 12000 ft | 212.31 | 1e-3 |
| V(FC) at 12000 ft | 254.77 | 1e-3 |
| V(MC) at 18000 ft (max altitude) | 150.77 | 1e-3 |
| V(MD) at 18000 ft | 188.11 | 1e-3 |

---

## ENGLOADS — Engine-mount loads

Manual worked example (Continental IO-520-BB), p131. Tolerance `rel_tol=1e-3`
unless noted; integer/dimensionless quantities exact. The **23.361(a)(1)
takeoff-torque factor** and **23.361(a)(3) turboprop mean-torque factor** are
approved oracle deviations (AC 23-19A correction) — see `CLAUDE.md` "Approved
corrections to the source"; the corrected figures below are *not* the raw
manual print, which is called out per row.

| Condition | Printed figure | Tolerance | Note |
|---|---|---|---|
| Combined engine+prop weight | 579 | exact | |
| Takeoff torque (unfactored, as printed) | 554.3884 ft-lb | 1e-3 | manual p131 raw print |
| Max continuous torque | 556.7227 ft-lb | 1e-3 | |
| Torque factor (6-cyl) | 1.33 | exact | |
| Combined CG XPP | 17.91 | abs_tol=0.01 | |
| 23.361(a)(1) vertical load factor | 2.85 | exact | |
| 23.361(a)(1) vertical down load | 1650.15 lb | 1e-3 | |
| 23.361(a)(1) engine-mount torque | -737.337 ft-lb | 1e-3 | **corrected** (AC 23-19A: 1.33 × 554.3884); manual's unfactored print is 554.39 |
| 23.361(a)(2) vertical down load | 2200.2 lb | 1e-3 | |
| 23.361(a)(2) engine-mount torque | -740.4412 ft-lb | 1e-3 | |
| 23.363 side-load factor | 1.33 | exact | |
| 23.363 side load | 770.07 lb | 1e-3 | |

**Turboprop hand-calc (inline in `tests/test_engine.py`, manual's gyro
example — Appendix-B-style, not a page-numbered table):**

| Condition | Printed figure | Tolerance | Note |
|---|---|---|---|
| Propeller inertia | 9.174 slug-ft² | abs_tol=1e-2 | manual hand calc |
| 23.361(a)(3) torque factor | 1.25 | exact | AC 23-19A correction |
| 23.361(a)(3) malfunction factor | 1.6 | exact | |
| 23.361(a)(3) mean takeoff torque | 1970 ft-lb | exact | |
| 23.361(a)(3) engine-mount torque | -3940 ft-lb | 1e-3 | **corrected** (1.6 × 1.25 × 1970); would be -3152 uncorrected |
| 23.361(a)(3) vertical down load | 450 lb | exact | |
| Gyro (23.371(b)) max continuous thrust | 4484.7 lb | abs_tol=1.0 | manual: THRUST = 1970×230.38/101.2 |

**ENGLOADS FAR 25 optional cases (`tests/test_engine_far25.py`).**
Closure-locked, not printed-oracle: no McMaster worked example exists for
Part 25. Checks are hand-calc closures traced to
`reference/14CFR_Part25_engine_torque.md` (case-count invariants, duplicate-case
removal, and cross-formula equality against the FAR 23 figures above) — see
"Closure-locked modules" below.

---

## FLTLOADS — Flight envelope (V-n) + balancing tail loads

Appendix A p179-180, CG1 (aft gross) unless noted. The AoA balance converges
NZ only to ±0.005 (FLTLOADS.BAS line 4130), so tail-load/LZW figures carry
~0.5% convergence noise (wider tolerances below reflect that, not test
laxness). Speeds/Mach/load-factor tolerance `rel_tol=1e-3`.

| Condition | Printed figure | Tolerance |
|---|---|---|
| Corner speed VA | 121.3 | 1e-3 |
| Corner speed VC | 170.0 | 1e-3 |
| Corner speed VD | 212.5 | 1e-3 |
| Corner speed VF | 105.5 | 1e-3 |
| Cruise Mach MC | 0.323 | 2e-3 |
| Dive Mach MD | 0.403 | 2e-3 |
| Positive limit load factor | 3.8 | 1e-3 |
| Negative limit load factor | -1.52 | 1e-3 |
| CG1 STALL 1G: V / NZ / α | 61.4 / 1.00 / 13.38° | 2e-3 / abs 0.01 / abs 0.05 |
| CG1 MAN A: V / NZ / α | 121.3 / 3.80 / 12.75° | 2e-3 / abs 0.01 / abs 0.05 |
| CG1 MAN D: V / NZ / α | 212.5 / 3.80 / 1.56° | 2e-3 / abs 0.01 / abs 0.05 |
| CG1 MAN -C: V / NZ / α | 170.0 / -1.52 / -7.00° | 2e-3 / abs 0.01 / abs 0.05 |
| CG1 AC ROLL: V / NZ / α | 115.0 / 3.25 / 11.96° | 2e-3 / abs 0.01 / abs 0.05 |
| CG1 STALL 1G tail load LT | 132 | rel 5e-3, abs 3.0 |
| CG1 MAN A tail load LT | 493 | rel 5e-3, abs 3.0 |
| CG1 MAN D tail load LT | 169 | rel 5e-3, abs 3.0 |
| CG1 MAN -C tail load LT | -465 | rel 5e-3, abs 3.0 |
| CG1 GUST +C tail load LT | 352 | rel 5e-3, abs 3.0 |
| CG1 AC ROLL tail load LT | 412 | rel 5e-3, abs 3.0 |
| CG1 MAN A wing-lift-less-tail LZW | 12419 | rel 3e-3, abs 2.0 |
| CG1 GUST +C LZW | 13120 | rel 3e-3, abs 2.0 |
| CG1 AC ROLL LZW | 10637 | rel 3e-3, abs 2.0 |
| CG1 MAN A pitching moment M(W+F) | 22864 | rel 5e-3 |
| CG1 MAN -C pitching moment M(W+F) | -58797 | rel 5e-3 |
| CG2 STALL 1G speed V | 62.6 | 5e-3 |
| CG2 STALL 1G tail load LT | -16 | abs 3.0 |
| CG2 MAN A NZ | 3.80 | abs 0.01 |
| CG2 MAN A LZW | 12970 | rel 3e-3, abs 2.0 |
| CG2 MAN A tail load LT | -59 | abs 4.0 |
| GUST +C / -C NZ | 3.96 / -1.96 | abs 0.01 |
| GUST +D / -D NZ | 2.88 / -0.88 | abs 0.01 |
| Tail CP station XTC (cruise, flaps up) | 253.364 | exact |

**Deferred (closure-only, no printed figure).** Flaps-extended (LANDING
config) corner set — no real landing-config aero polynomials in the repo;
checked only for condition-set presence and that MAN 2G attains NZ=2.0 at
V=VF (a design-speed check, not an independent LT/LZW oracle). See backlog
"Deferred refinements."

---

## SELECT — Critical load selection

Appendix A "Critical Wing/Horiz Tail/Vert Tail/Fuselage Loads" summaries;
Ch 9 hand-calc case 202. Flaps-**retracted** cases only are printed-oracle
(flaps-extended is closure-only — see backlog). Tolerance per row.

**Wing (flaps retracted):**

| Condition | Printed CL | Printed V (KEAS) | Tolerance |
|---|---|---|---|
| PHAA (STALL +N) | 1.519 | 117.40 | CL rel 5e-3/abs 3e-3, V rel 2e-3 |
| PLAA (MAN D) | 0.472 | 212.40 | same |
| PMAA (GUST +C) | 0.810 | 170.00 | same |
| NMAA (GUST -C) | -0.433 | 170.00 | same |
| ACRL (AC ROLL) | 1.328 | 116.00 | same |
| TORS (ST ROL C) | 0.470 | 170.00 | same |
| PHAA load factor NZ | 3.80 | — | abs 0.01 |

**Ch 9 rational hand-calc, case 202 (STALL +N / CG1 / 18000 ft):**

| Condition | Printed figure | Tolerance |
|---|---|---|
| LT25 | 907.62 | 3e-3 |
| LT50 | -387.78 | 5e-3 |
| AT (α) | 7.747 | abs 0.05 |
| Elevator deflection δ | -5.39° | abs 0.03 |
| Total LT | 519.845 | 3e-3 |
| CP (% tail MAC) | 6.35 | abs 0.1 |

**H-tail, flaps retracted (printed):**

| Condition | Printed figure | Tolerance |
|---|---|---|
| BAL UP RETRACTED (case 202) | 519.85 | 5e-3 |
| BAL DN RETRACTED (case 165) | -613.92 | 5e-3 |
| UNCHECKED MAN DN total (case 274) | -1397.8 | 5e-3 |
| UNCHECKED MAN DN δ-increment (cp50) | -1346.5 | 3e-3 |
| UNCHECKED MAN UP total (case 34) | 1227.2 | 5e-3 |
| CHECKED MAN DN total (case 56) | -671.5 | 5e-3 |
| CHECKED MAN DN pitch inertia Iyy | 2242.8 | 2e-3 |
| CHECKED MAN UP total (case 204) | 787.8 | 5e-3 |
| GUST UP RETRACTED total | 908.6 | 5e-3 |
| GUST UP RETRACTED increment (cp25) | 1017.0 | 3e-3 |
| GUST DN RETRACTED total | -1292.8 | 5e-3 |
| UNSYMMETRICAL total | -1111.8 | 5e-3 |
| UNSYMMETRICAL RH side load | -646.4 | 5e-3 |
| UNSYMMETRICAL LH side load | -465.4 | 5e-3 |
| UNSYMMETRICAL other-side % | 72.0 | abs 0.1 |

**Large-deflection factor EF (back-solved from SELECT.BAS subr 10000):**

| Condition | Printed figure | Tolerance |
|---|---|---|
| EF(30.0°, 16.403/36.944) | 0.5419 | abs 2e-3 |
| EF(20.0°, 16.403/36.944) | 0.7011 | abs 2e-3 |
| EF(0.0°, 0.0) | 1.0 | exact |

**Fuselage (printed, "Critical Fuselage Loads"):**

| Condition | Printed figure | Tolerance |
|---|---|---|
| MAX DOWN LOAD ON WING | 13347.6 | 3e-3 |
| AFT DOWN BENDING | 12569.6 | 3e-3 |
| AFT UP BENDING | -6390.3 | 3e-3 |
| GREATEST NZ | 5.81 | 3e-3 |

**Vertical tail (printed, "Critical Vertical Tail Loads").** Carries ~1% EFV
large-deflection-chart noise (default `EFV=1.0` vs the manual's back-solved
~1.009) on rows so marked.

| Condition | Printed figure | Tolerance | Note |
|---|---|---|---|
| SUDDEN RUDDER total tail load | 591 | 1.5e-2 | EFV noise |
| SUDDEN RUDDER load on rudder | 167 | 1.5e-2 | EFV noise |
| YAW TO SIDESLIP due-to-yaw (cp25) | -684 | 3e-3 | |
| YAW TO SIDESLIP due-to-rudder (cp50) | 591 | 1.5e-2 | EFV noise |
| YAW 15 NEUTRAL total (cp25) | -526 | 3e-3 | |
| SIDE GUST total (cp25) | 604 | 3e-3 | |
| SIDE GUST yaw inertia IZZ | 4169.164 | 1e-3 | |
| SUDDEN RUDDER, EFV=1.009 explicit | 591 | 4e-3 | confirms EFV chart origin |

**Deferred (closure-only, no printed figure).** Flaps-extended H-tail
balancing/gust — condition-set presence + internal closure (Total = LT25 +
LT50) only; no landing-config aero polynomials in the repo, so the printed
Appendix A cases 81/106/88/108 are not checked. See backlog.

---

## BALLOADS — Rational balanced-tail-load verification (utility)

Ch 9 case-202 hand-calc (same case as SELECT above); BALLOADS.BAS Appendix C
p497.

| Condition | Printed figure | Tolerance |
|---|---|---|
| Case 202 up balancing LT (max-LT row) | 519.845 | 3e-3 |
| Case 202 LT25 | 907.62 | 3e-3 |
| Case 202 LT50 | -387.78 | 5e-3 |
| Case 202 elevator deflection δ | -5.39° | abs 0.03 |
| Case 202 CP (% tail MAC) | 6.35 | abs 0.1 |

**Cross-check (not a printed figure).** BALLOADS' max/min-LT rows are also
asserted equal to SELECT's own "BAL UP/DN RETRACTED" output (`rel_tol=1e-9`)
— a module-to-module consistency check, listed here for completeness.

---

## AIRLOADS — Air-load (Schrenk) distribution

Ref 1 Ch 7 p46-47; worked example Appendix A p161-162 (additive) / p162
(basic). Tolerance `rel_tol=1e-3` unless noted.

| Condition | Printed figure | Tolerance |
|---|---|---|
| Additive CC(LA1), station 1 | 91.05576 | 1e-3 |
| Additive CC(LA1), station 10 | 69.44847 | 1e-3 |
| Additive CC(LA1), station 20 | 31.82978 | 1e-3 |
| Additive C(LA1), station 1 (section cl) | 0.9275981 | 1e-3 |
| Recovered CL (additive distribution) | 1.00061 | 1e-3 |
| AWO (basic-distribution constant) | 3.988146 | 1e-3 |
| Basic CC(lb), station 1 | 5.09762 | 1e-3 |
| Basic Clb, station 1 | 0.05193 | 1e-3 |
| Mo (constant section moment) | 0.1075 | 1e-3 |
| TAU(0.0, 0.0) curve fit | 0.206209 | 1e-3 |

---

## WINGINER — Wing inertia loads

WINGINER.BAS Appendix C p455-458; Appendix A p217 (mass density), p220
(unit-load cases), p221 (combined torsion case 138).

| Condition | Printed figure | Tolerance |
|---|---|---|
| Root panel density (lb/ft²) | 2.213 | abs 0.002 |
| Tip panel density (lb/ft²) | 2.102 | abs 0.002 |
| Unit vertical (case 1001): root SZ | -167 | rel 2e-3, abs 2.0 |
| Unit vertical: root MXX | -16158 | rel 2e-3, abs 2.0 |
| Unit vertical: root MYY | 4482 | rel 2e-3, abs 2.0 |
| Unit drag (case 1002): root SX | 167 | rel 2e-3, abs 2.0 |
| Unit drag: root MZZ | 16158 | rel 2e-3, abs 2.0 |
| Unit drag: root MYY | 1698 | rel 2e-3, abs 2.0 |
| Unit roll (case 1003): tip FZ | -30 | rel 2e-3, abs 1.5 |
| Unit roll: tip SZ | -30 | rel 2e-3, abs 1.5 |
| Unit roll: tip MYY | 337 | rel 2e-3, abs 2.0 |
| Case 138 TORS: root SZ | -423 | rel 2e-3, abs 2.0 |
| Case 138: root SX | -22 | rel 2e-3, abs 2.0 |
| Case 138: root MXX | -41041 | rel 2e-3, abs 2.0 |
| Case 138: root MYY | 11161 | rel 2e-3, abs 2.0 |
| Case 138: root MZZ | -2130 | rel 2e-3, abs 2.0 |

---

## NETLOADS — Net (air − inertia) wing loads

Appendix A p206 (air-load distribution, Case 22 PHAA), p222 (net loads, Case
22 PHAA).

| Condition | Printed figure | Tolerance |
|---|---|---|
| Air load, root FZ | 466 | rel 2e-3, abs 2.0 |
| Air load, root FX | -68 | rel 2e-3, abs 2.0 |
| Air load, root SZ | 6470 | rel 2e-3, abs 2.0 |
| Air load, root SX | -1126 | rel 2e-3, abs 2.0 |
| Air load, root MXX | 516955 | rel 2e-3, abs 2.0 |
| Air load, root MYY | -79003 | rel 2e-3, abs 2.0 |
| Air load, root MZZ | -91283 | rel 2e-3, abs 2.0 |
| Air load, root X | 71.628 | rel 2e-3, abs 2.0 |
| Air load, root Z | 79.028 | rel 2e-3, abs 2.0 |
| Air load, tip FZ | 143 | rel 2e-3, abs 2.0 |
| Air load, tip MYY | -198 | rel 2e-3, abs 2.0 |
| Air load, mid-station SZ | 2509 | rel 2e-3, abs 2.0 |
| Air load, mid-station MXX | 97044 | rel 2e-3, abs 2.0 |
| Net load, root FX | -68 | rel 2e-3, abs 2.0 |
| Net load, root FZ | 466 | rel 2e-3, abs 2.0 |
| Net load, root SX | -1025 | rel 2e-3, abs 2.0 |
| Net load, root SZ | 5837 | rel 2e-3, abs 2.0 |
| Net load, root MXX | 455555 | rel 2e-3, abs 2.0 |
| Net load, root MYY | -60940 | rel 2e-3, abs 2.0 |
| Net load, root MZZ | -81483 | rel 2e-3, abs 2.0 |
| Net load, tip FX | -12 | rel 2e-3, abs 2.0 |
| Net load, tip FZ | 118 | rel 2e-3, abs 2.0 |
| Net load, tip MYY | 85 | rel 2e-3, abs 3.0 |

---

## TAILDIST — Chordwise tail-load distribution

TAILDIST.BAS Appendix C subr 3000; Appendix A p237 (13 horizontal conditions,
flaps retracted), p245 (4 vertical conditions). Tolerance `rel_tol=1e-3,
abs_tol=1e-3` throughout; PSI reported at chord stations X1/X2/X3/X4/X5 (X3 =
trailing edge, always 0.000 by construction).

**Horizontal tail (p237), 13 rows — LT25/LT50 input → PSI[X1,X2,X4,X5] oracle:**

| # | LT25 | LT50 | PSI(X1) | PSI(X2) | PSI(X4) | PSI(X5) |
|---|---|---|---|---|---|---|
| 1 | 907.62 | -387.77 | 0.682 | 0.095 | 0.015 | -0.030 |
| 2 | 217.58 | -831.50 | 0.164 | -0.122 | -0.228 | -0.239 |
| 3 | -34.76 | -62.09 | -0.026 | -0.019 | -0.025 | -0.023 |
| 4 | -532.85 | -496.12 | -0.401 | -0.197 | -0.236 | -0.209 |
| 5 | -51.60 | -1227.79 | -0.039 | -0.250 | -0.393 | -0.390 |
| 6 | 65.04 | 1072.70 | 0.049 | 0.222 | 0.346 | 0.343 |
| 7 | -458.46 | -218.34 | -0.345 | -0.129 | -0.137 | -0.114 |
| 8 | 700.30 | 87.48 | 0.527 | 0.149 | 0.133 | 0.098 |
| 9 | 843.46 | 65.04 | 0.634 | 0.171 | 0.147 | 0.105 |
| 10 | -1186.70 | -106.00 | -0.892 | -0.244 | -0.212 | -0.152 |
| 11 | -478.67 | 3.52 | -0.360 | -0.089 | -0.071 | -0.047 |
| 12 | -1087.52 | -161.30 | -0.818 | -0.236 | -0.214 | -0.160 |
| 13 | -1186.81 | -106.00 | -0.892 | -0.244 | -0.212 | -0.152 |

**Vertical tail (p245), 4 rows:**

| # | LT25 | LT50 | PSI(X1) | PSI(X2) | PSI(X4) | PSI(X5) |
|---|---|---|---|---|---|---|
| 1 | 0.00 | 679.00 | 0.000 | 0.370 | 0.462 | 0.462 |
| 2 | -1076.00 | 679.00 | -2.014 | -0.134 | 0.000 | 0.252 |
| 3 | -827.00 | 0.00 | -1.548 | -0.387 | -0.355 | -0.161 |
| 4 | 950.00 | 0.00 | 1.778 | 0.445 | 0.408 | *(not checked)* |

**Chord-station geometry (row 1's LT25/LT50), same p237 worked example:**

| Condition | Printed figure | Tolerance |
|---|---|---|
| X3 (= CT) | 36.38851 | 1e-3 |
| X2 (= 0.25·CT) | 9.097128 | 1e-3 |
| X4 (= CEAFTHL) | 14.56908 | 1e-3 |
| X5 (= CT − X4) | 21.81942 | 1e-3 |

**Deferred (not covered).** The 4 flaps-extended horizontal rows of the p237
13-row table are not exercised by the SELECT→TAILDIST integration test
(deferred with the FLTLOADS/SELECT flaps-extended aero — see backlog).

---

## AILERON — Simplified aileron loads

AILERON.BAS Appendix C p450; Appendix A p200 ("Critical Aileron Loads").

| Condition | Printed figure | Tolerance |
|---|---|---|
| Down aileron load @ VC=170kt | 271.44 lb | 1e-3 |
| Up aileron load | -180.96 lb | 1e-3 |
| Critical-speed selection (both @ 170 kt) | — | exact |
| Down hinge pressure | 0.484 psi | 2e-3 |
| Up hinge pressure | -0.323 psi | 2e-3 |
| Pipeline down load (via computed VA=121.3 vs. manual's rounded 121) | 271.44 lb | 4e-3 (widened for VA rounding) |

---

## FLAPLOAD — Simplified flap loads

FLAPLOAD.BAS Appendix C p452; Appendix A p201 ("Critical Flap Loads").

| Condition | Printed figure | Tolerance |
|---|---|---|
| CLf[0..3] (1G/2G stall, 2G@VF, gust@VF) | 1.704565 / 1.704565 / 1.559282 / 1.547566 | 1e-3 |
| Critical flap load | 629.0 lb | 2e-3 |
| Leading-edge pressure | 0.545 psi | 2e-3 |
| Four flap loads (manual INT-truncated) | 212 / 424 / 629 / 624 lb | abs diff ≤1.5 lb |
| Slipstream factor | 1.407 | 2e-3 |
| Slipstream velocity | 125.1 kt | 2e-3 |
| Slipstream BL inboard | 22.828 | 2e-3 |
| Slipstream BL outboard | 113.172 | 2e-3 |
| Gust factor | 1.301 | 2e-3 |
| Combined gust load | 819.0 lb | 2e-3 |

---

## TABLOADS — Simplified tab loads

TABLOADS.BAS Appendix C p490; Appendix A p202 ("Tab Loads").

| Condition | Printed figure | Tolerance |
|---|---|---|
| Chord ratio E | 0.17735 | 1e-3 |
| Tab load LTAB | 84.618 lb | 1e-3 |
| Leading-edge pressure | 0.49922 psi | 1e-3 |
| Trailing-edge pressure | 0.24961 psi | 1e-3 |

---

## LGFACTOR — Landing load factor

LGFACTOR.BAS Appendix C p483; Appendix A p236.

| Condition | Printed figure | Tolerance |
|---|---|---|
| Sink rate V | 9.004822 fps | 1e-3 |
| Airplane load factor N | 3.095102 | 1e-3 |
| Gear load factor NLG (= N − L) | 2.428102 | 1e-3 |
| Velocity clamp bounds (23.473(d), not a printed figure) | 7.0 / 10.0 fps | exact |

The N figure carries a documented ~+0.07% drift from `g=32.174` (modernized
`constants.py`) vs. the source BASIC's `32.2` — inside the ±0.1% tolerance.

---

## LANDLOAD — Landing loads

LANDLOAD.BAS Appendix C p468; Appendix A p230 (ground-line geometry, fully
oracle-locked), p231-233 (wheel-load table, **OCR-garbled in the bundled
PDF** — closure + legible-cell spot-check only, the ONENGOUT precedent).

**Geometry (oracle-locked, p230):**

| Condition | Printed figure | Tolerance |
|---|---|---|
| Drag factor K | 0.324 | 3e-3 |
| GAMMA = arctan(K) | 17.978° | 3e-3 |
| Ground angle GRA[0] (3-wheel level) | 4.057° | 3e-3 |
| Ground angle GRA[1] (2-wheel level) | 4.724° | 3e-3 |
| Ground angle GRA[2] (tail down) | 15.0° | exact |
| BETA[0] | 13.921° | 3e-3 |
| BETA[1] | 4.724° | 3e-3 |
| BP level, 3 CG cases | 19.796 / 28.512 / 31.649 | 2e-3 |
| Ground-roll AP[1][0] | 78.836 | 2e-3 |
| Ground-roll BP[1][0] | 14.311 | 2e-3 |
| Ground-roll DP[1][0] | 93.147 | 2e-3 |
| Ground-roll CP[1][1] | 42.981 | 2e-3 |
| Tail-down BP[2][2] | 13.511 | 2e-3 |

**Wheel loads — legible-cell spot-checks (p231; the full 24-main/33-nose
matrix beyond these cells is unreadable in the bundled PDF):**

| Condition | Printed figure | Tolerance |
|---|---|---|
| Case 1 (3-wheel level, aft max landing) VMP | 3144 lb | 3e-3 |
| Case 1 VNP | 1787 lb | 3e-3 |
| Case 1 nose resultant | 1879 lb | 3e-3 |
| Case 19 (side-load, LT drift) VMP | 2261 lb | 3e-3 |
| Case 19 SMP | -1700 lb | 3e-3 |
| Case 20 (RT drift) SMP | 1122 lb | 3e-3 |

---

## Closure-locked modules (no printed oracle — physics-closure / sub-formula validated)

These modules have **no legible printed Appendix A/B figure** to lock
against, for the reason stated. Each is validated instead by the specific
closure or sub-formula check listed — recorded here so the baseline is
complete, per the backlog's instruction not to invent printed figures for
them.

### AIRLOAD4 (swept/high-Mach branch of AIRLOADS)
No printed Appendix B swept spanwise table exists in the bundled PDF.
Validated by:
- **Reduction invariant** — at zero sweep / low Mach, `ccl_additive` is
  byte-identical to the un-swept AIRLOADS baseline (exact equality).
- **Redistribution-direction closure** — with 25° sweep, root `ccl_additive`
  is strictly less than the un-swept root value, and tip deviation is
  strictly smaller in magnitude than root deviation (qualitative, no numeric
  target).

### ONENGOUT — One-engine-out transient
No printed Appendix B one-engine-out table exists in the bundled PDF (the FAA
User's Guide gives partial inputs only, no outputs). Validated by:
- **Sub-formula exactness** — thrust/windmill-drag, `AVT = 2π/(1+2/ARVT)`, and
  the rudder-effectiveness cubic `0.014844 + 2.7358r − 4.4679r² + 3.0306r³`
  are checked against ONENGOUT.BAS's own formula text (lines 205-208 for
  thrust/drag), `rel_tol=1e-12` — algebraic identity, not a manual figure.
- **Refactor-parity** — SELECT's private `_avt`/`_effectv`/`_ef` helpers equal
  the shared `_vtail` module versions (`rel_tol=1e-12`).
- **Physics/integration closure** — the transient recovers (θ swings back
  through zero), peak yaw rate occurs mid-simulation, halving the Euler time
  step changes the max tail load by <5%, and below-VMC behavior is bounded/
  flagged rather than unstable.

### LANDLOAD wheel-load table (beyond the legible p231 cells)
See the LANDLOAD table above — the printed p231-233 matrix is OCR-garbled
past the spot-checked cells. The remaining rows are validated by pure
algebraic closure against the module's own formulas (e.g.
`rx[1].vmp == 0.5*nlg*w1*ap/dp`, `rx[13].dmp == 0.8*rx[13].vmp`) — internal
consistency, not a second oracle.

### ENGLOADS FAR 25 optional cases (concept superset)
No McMaster worked example exists for 14 CFR Part 25. Validated by hand-calc
closures traced to `reference/14CFR_Part25_engine_torque.md`: case-count
invariants (6 conditions by default, 9 with the opt-in flag, 0 added for
reciprocating engines), duplicate-case removal, and cross-formula equality
against the FAR 23 figures in the ENGLOADS table above (e.g. 25.361(a)(3)(i)
torque equals the FAR23 23.361(b)(1) torque).

### body_loads — Fuselage net-load distribution (modern addition)
Ch 15 ships no program and no printed station table. Validated by
**equilibrium closure**: the sum of per-station vertical force ≈ 0
(`abs_tol=1e-6`), shear returns to ≈0 aft of the wing reaction
(`abs_tol=1e-6`), and the exported FORCE-card Fz re-sums to ≈0
(`abs_tol=1e-3`).

### configuration — General configuration & layout (modern addition)
No manual regression oracle. Validated by (1) **closed-form consistency** —
the module's MAC/Y_MAC/XLEMAC/span/AR match analytic trapezoidal-wing
formulas (`rel_tol=1e-3`), and (2) an **Appendix A plausibility band**
(not oracle-exact) against p141: MAC and the MAC butt-line station within
±10% of the manual's 69.246 / 87.854 (the real wing has an inboard strake a
pure trapezoid can't reproduce — XLEMAC's absolute station is intentionally
not asserted).

### AIRLOADS / NETLOADS concept-mode closure
Concept mode (category `"C"`, no FAR23 weight/seat cap) has no printed
oracle by design. AIRLOADS checks the integrated distribution recovers
`aero.target_cl` (`rel_tol=2e-3`) and that basic lift sums to zero
(`abs_tol=1e-6`); NETLOADS checks `net.nz` matches the V-n chosen load factor
(`abs_tol=0.01`) and the air+inertia=net identity (`abs_tol=1e-6`).

---

## Cross-module identities (not printed figures, recorded for completeness)

A handful of assertions check algebraic identities rather than manual
figures — listed here so they aren't mistaken for missing oracle coverage:
NETLOADS' `net == air + inertia` (`abs_tol=1e-6`); WINGINER's inboard-strip
zero-panel-mass rule and concentrated-weight delta-shear identity; SELECT's
`Total tail load == LT25 + LT50` closure for the flaps-extended path; and
BALLOADS' cross-check against SELECT's own `BAL UP/DN RETRACTED` output
(`rel_tol=1e-9`).
