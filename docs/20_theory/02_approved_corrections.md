# Approved corrections to the source (oracle deviations) — register of record

This is the **authoritative register** of deliberate deviations from McMaster's
manual / `.BAS` source. `CLAUDE.md` states the policy and links here; this file
holds the individual entries.

## Policy

The FAR23 replication core is oracle-locked to McMaster's manual, **but the manual
and its `.BAS` source may themselves contain errors** (e.g. encoding a regulation
that was later found defective). A deliberate deviation from the oracle is allowed
**only when it is (1) approved by the user and (2) documented** — in the calc
docstring + a `note` on the affected `ConditionResult`, in the test (assert the
corrected value, keep the manual's original figure in a comment for traceability),
in `PROGRAM_SPEC.md` / [`00_theory_sources.md`](00_theory_sources.md), in
`CHANGELOG.md`, and cited to an authoritative reference in `reference/`. Until both
conditions are met, replicate the manual exactly (warts and all). Record each
correction below.

## Register

### 23.361(a)(1) takeoff-torque factor *(approved 2026-06-22)*

The manual leaves the takeoff-case engine torque **unfactored** (Appendix A prints
554.39 ft-lb for the IO-520-BB), encoding the **Amendment 23-26** drafting error.
**AC 23-19A** states that error was non-conservative (lower loads) and corrected by
**Amendment 23-45**: 23.361(c) applies the mean-torque factor to *all* of paragraph
(a), takeoff case included. `condition_361_a1` now applies `factor x mean takeoff
torque` (IO-520-BB → 737.34 ft-lb; turbopropeller → 1.25× mean, identical to
25.361(a)(1)(i)). Sources: `reference/AC_23-19A_engine_torque.md`; corroborated by
the FAA User's Guide **§17.2.1** (which prints the post-1994 CFR text of 23.361(c)).

### 23.361(a)(3) turboprop-malfunction mean-torque factor *(approved 2026-06-23)*

The manual / `ENGLOADS.BAS` (`TTP=1.6*ENGTORQ`) apply only the 1.6 propeller-
control-malfunction factor, encoding the same **Amdt 23-26** omission. The (a)(3)
base "limit engine torque corresponding to takeoff power and propeller speed" is the
same quantity as (a)(1), so by the same **AC 23-19A** / 23.361(c) / **Amdt 23-45**
authority the 1.25 turbopropeller mean-torque factor applies before the 1.6 factor.
`condition_361_a3` now reports `1.6 x 1.25 x mean takeoff torque` (= 2.0× mean). No
printed Appendix B engine-mount oracle exists in the bundled PDF, so it is
formula-checked (`test_361_a3_applies_mean_torque_factor`). Sources:
`reference/AC_23-19A_engine_torque.md`; FAA User's Guide **§17.2.1** (post-1994 CFR
text).

### 23.427(a) unsymmetrical-tail candidate set *(approved 2026-07-20)*

The Appendix A **sample output** prints the unsymmetrical h-tail load governed by the
down gust (total −1111.8), i.e. it **excludes** the unchecked maneuvers. That
printout is inconsistent with its own **Appendix C listing**: `SELECT.BAS` lines
6070–6175 load the unchecked maneuvers into the 23.427 candidate array
(`L(5)=U1CK`, `L(6)=U2CK`) and take the max over all 12 conditions. 23.427(a)
applies the unsymmetrical distribution to "the loads prescribed in 23.421
**through** 23.425" — spanning the 23.423 unchecked case. The stale sample output
was produced by a superseded `SELECT.BAS` revision; the listing + the CFR are
authoritative. `select_htail_unsymmetrical` now searches the full candidate set
(an earlier revision excluded the unchecked cases citing "CAM 3.216"); on the GA6
the DN unchecked maneuver governs and the unsymmetrical total moves to −1204.7
(RH −700.4, LH −504.3, 72%). Regression-tested in
`test_htail_gust_and_unsymmetrical_match_appendix_a` (manual's −1111.8 kept in a
comment). Source: `reference/23_427_unsymmetrical_candidate_set.md`.

### Truncated `.BAS` constants go exact; the surviving `*_SUITE` twin *(approved 2026-08-17, issue #26)*

The programs wrote several shared constants truncated — `57.3` (and `114.6`) for
deg/rad, `32.2` beside `32.174` for g, `V²/295` for dynamic pressure, `1.15·88/60`
for kt→ft/s, and FLTLOADS' private `518.688 °R` / `575 kt` speed of sound. Per the
2026-08-17 constants-and-conversions review (`docs/50_reviews/`), every one now
reads its exact owner in `sloads/constants.py`: `DEG_PER_RAD = 180/π`, `G = 32.174`,
`DYNAMIC_PRESSURE_DIVISOR = 1/(½·ρ₀·KT_TO_FPS²) = 295.237` (−0.08 % in q,
uniformly), `KT_TO_FPS = 1852 m/0.3048/3600 = 1.68781`, and the shared
`standard_atmosphere` for `a`. **Each move was measured against the whole suite
before it was made, singly and all together:** no page-cited oracle moves —
Appendix A ±0.1 % holds throughout (e.g. `ga6_normal` VA 121.35 vs printed 121.3, VF
105.54 vs 105.5); what moved were self-pins only — the frozen Imperial digest
(`tests/fixtures_imperial/digests.json`), the SELECT unsymmetrical split
(`test_balance._UNSYMMETRICAL_SPLIT`, ≤ 0.08 % per value: GA6 RH −700.42 vs
−700.38), two `_DELTA_CD_BAND` lower edges by 0.0001, and the F25-2 VA/VF
"today's numbers" pin — all re-pinned with this entry cited. **One survivor:**
`KT_TO_FPS_SUITE = 1.68667` for `VSF` only, because the ENGLOADS gyro-thrust
oracle prints `THRUST = T·ω/101.2` (`test_gyro_thrust_matches_manual`, `abs_tol`
1 lb, which the exact factor exceeds by 3 lb); FLAPLOAD's p201 slipstream oracle
and ONENGOUT hold at exact and were switched. The FAR 23.341(c) numbers (498, 0.88,
5.3) are regulatory and were **not** changed — only given one owner. Rule of
record: `CONVENTIONS.md` §7 (owners + demarcation + guards).

---

### LANDLOAD's `BETA` carries the wrong sign on attitudes 2 and 3 *(approved 2026-08-29, issue #133)*

**Supersedes the "Considered and declined" decision of 2026-08-15** on the same
question (moved below, kept verbatim). That decision named legible printed output
as the condition on which it would resume; Appendix A supplies it — not in a
table, but in the manual's own **construction figures**.

`LANDLOAD.BAS` defines `BETA` as the resultant-to-FS angle, and Appendix A
**p234** ("3 WHEEL LEVEL LANDING") states the rule in the drawing:

```
GAMMA = ARCTAN K = 17.978
BETA  = GAMMA - GRD ANGLE = 17.978 - 4.057 = 13.921
```

with the lever arms drawn **axle to axle, normal to the RESULTANT**. The BASIC
writes `BETA = (GAMMA-GRA(1), +GRA(2), +GRA(3))`, applying that rule to the level
attitude only. Attitudes 2 and 3 take `+GRA` where the rule gives `−GRA` (their
reaction is normal to the ground, so `GAMMA = 0` there — the braked drag rides
the separate `.8·CP` term). Attitude 3 negates it back at **both** its use sites
(`BP` written longhand, `PHIM(7–9) = −BETA(3)`) and so comes out right; attitude 2
negates it at neither, so its lever arms *and* its `PHIM`/`PHIN` both carry it.

**The manual contradicts itself, and that is what makes this an adjudicable
deviation rather than a judgement against a printed oracle.** Appendix A **p235**
("BRAKED ROLL", CG 6) prints the ground-roll lever arms:

| | p230 table (program output) | **p235 figure** | corrected code |
|---|---|---|---|
| AP | 78.836 / 69.886 / 66.501 | **77.052** (CG 6) | 86.002 / 77.052 / 73.502 |
| BP | 14.311 / 23.260 / 26.646 | **17.760** | 8.810 / 17.759 / 21.310 |
| DP | 93.147 | **94.811** | 94.811 |
| CP | 42.981 | 42.981 | 42.981 — unchanged |

Flipping the one sign reproduces all three figure values exactly. `CP` is
untouched (it enters through `cos`, and is even), which is itself a check that
only the sign moved. The figure's `4522 lb` is `1.33 × 3400`, confirming the
weight the braked family runs at.

**Deviated-from values and corrected expectations.** The printed cells stay
transcribed in `tests/test_landing.py` (`_P231`/`_P232`/`_P233`); the corrected
ones sit beside them in `_CORRECTED`, each derived from Appendix A's own printed
formulas with the single substitution `BETA(2) = −GRA(2)` — never from the module
under test. Surface:

- **p230** — the ground-roll `AP`/`BP`/`DP` row (above). `CP` unchanged.
- **p231** — cases 13–15 (`VMP` +7.7/+8.8/+9.1 %, `VNP` −12.6/−10.7/−10.0 %) and
  25–33 (`VNP` −39.5/−25.0/−21.4 %). Cases 1–12 and 16–24 unchanged: their
  reactions are arm-independent.
- **p232** — cases 13–33, most of the table. The braked families rotate +14.2 %
  vertical / −18.7 % drag; the side families keep their vertical magnitude and
  their body drag **flips sign**, aft → forward.
- **p233** — cases 16–24 `PITCHP`, and 19–24 `YAWP`. `ROLLP` unchanged (`CP`).
- **p236** LGFACTOR and the level and tail-down families are untouched throughout.

**The independent witness.** The correction is confirmed by a quantity it does
not touch: the pre-closure residual pitching moment of the assembled ground case,
measured against LANDLOAD's *own* printed unbalanced moments. On `ga6_normal`
case 13 it falls from **−757.1 to −0.7 lb-in**, and `q̈` from −8.0e-5 to −7.4e-8.
A correct lever arm closes the case; the wrong-signed one was what the residual
had been reading. (`balanced_cases.md` §9.5.)

**Physical claim, stated so it can be checked by eye.** In the 23.485 side
family the ground-line load is purely normal, so the entire body-frame drag
component *is* the rotation: it read **+186 lb aft** and now reads **−186 lb
forward**, which is what nose-up geometry demands. Positive `GRD ANGLE` is
**nose up** — the reading that reproduces both figures, and the one the entered
tail-down `+15` states plainly.

**Pins moved, none deleted.** `test_the_ground_roll_attitude_is_resolved_against_the_other_sign`
is **flipped** and renamed `test_rho_is_minus_the_ground_angle_in_every_attitude`
— `ρ == −GRA` in every attitude, exact, against `ground_angles` directly rather
than recovered from the case (the recovered form is self-consistent by
construction and structurally cannot see a sign error). The p230 arm oracle
re-pins to the p235 figure; the p231/p232/p233 page locks re-pin cell by cell via
`_CORRECTED`; `balanced_cases.md` §9.5's worked example and the frozen Imperial
digest are re-generated with this entry cited. Assumption recorded on the gate:
the nose-up sense of `GRA` is derived on **tricycle** geometry, the only
arrangement the suite models.

Design note: [38](../40_history/42_ground_frame_note.md) §1.15 (AGREED
2026-08-29), GF-1 / GF-2′ / GF-3″ / GF-4.

### LANDLOAD's airplane-datum lift term and moment transform carry the same wrong sign *(approved 2026-08-29, issue #134)*

**The same error, in the two places the #133 entry could not reach**, because
neither quantity was in sloads until GF-6 built it. Both are the *airplane-datum*
half of the printout, and both write the ground angle out longhand where the
physics wants a rotation:

```basic
FOR L=1 TO 6:   ND(L) = LF*SIN(GRA(1)/57.3) + (DN(L)+2*DM(L))/WL(L)
FOR L=10 TO 12: ND(L) = LF*SIN(GRA(1)/57.3) + DM(L)/WL(L)
RMOM = RMOMP*COS(GA) + YMOMP*SIN(GA)
YMOM = YMOMP*COS(GA) - RMOMP*SIN(GA)
```

**What is wrong.** The wing lift in a landing attitude is perpendicular to the
flight path: it is a **ground-line vertical**, and it enters the airplane's own
axes tilted by the same `ρ` every gear reaction is tilted by. With `ρ = −GRA`
(the #133 entry above, approved the same day) its body drag component points
**forward**, as sloads' own assembled deck has always applied it
(`balance.py`, G-7a). `+LF·SIN(GRA)` puts it aft. The `RMOM`/`YMOM` transform is
the same statement about a moment vector: a clean rotation of **+GRA**, on every
attitude, where the force rows rotate by −GRA. A moment vector and a force vector
rotate identically under one change of frame, so the two cannot both be right.

**What sloads does instead.** Neither quantity restates a sign. `NV`/`ND` take
the lift as `frames.to_airplane_datum(LF, 0, ρ)` and the datum moments as
`frames.to_airplane_datum(YAWP, ROLLP, ρ)` — the rotation applied through the
case's own measured `ρ` (`frames.rotation_deg`, taken from the case's two
resolutions of one reaction). The corrected value is what a rotation gives; there
is no second place where a `+` could be typed for a `−`.

**Why it is believed, beyond the #133 argument it inherits.** Three checks the
correction did not aim at, and passes:

* **The tail-down family is unaffected — and the `.BAS` already agrees there.**
  Its line reads `−LF*SIN(GRA(3))`, which is exactly what the rotation gives, so
  cases 7–9 reproduce **all three printed cells exactly** (3.167 / 3.059 /
  −0.820). The manual is internally inconsistent, and one of its attitudes is
  right.
* **`NV` does not move on cases 1–12.** The vertical term is a cosine, which is
  even: a sign correction in the drag term cannot touch it, and it does not
  (printed 3.216, sloads 3.216).
* **`NR` is frame-invariant on the wheels-only families and stays printed.**
  Cases 16–18 keep 1.703 and 19–24 keep 1.330 to the printed digit while `NV`/`ND`
  move (1.238/1.170 → 1.413/0.951) — a rotation preserves a resultant, so a
  correction that broke this would be the wrong correction. The datum moments
  carry the same invariance: `|(ROLL, YAW)|` is preserved and `PITCH` does not
  move at all, which is the manual's own `PMOM = PMOMP`.

**Cells deviated from.** p232's NR/ND on cases 1–6 and 10–12 (the lift term
alone: 3.287/0.679 → 3.269/0.585 on case 1) and NR/NV/ND on 13–24 (those follow
their own force cells, already deviated under #133). p233's `RMOM`/`YMOM` on
every case with a rolling or yawing moment — 10–12 and 19–24. **No printed cell
is unlocked and the count does not fall**: the 72 factor cells join the page
locks in `test_landing.py` (`_P232_FACTORS`, deviations in
`_CORRECTED["p232_factors"]`, each derived from *this page's own force cells* by
the printed loops with the one substitution, never from the module under test).

Gates: `tests/test_landing.py::test_landload_p232_airplane_datum_load_factors`;
`tests/test_landing_deliverable.py` —
`test_the_datum_load_factors_are_the_printed_formula_on_the_printed_page`,
`test_case_1_and_case_16_lock_at_the_ruled_numbers`,
`test_the_datum_moments_are_a_rotation_of_the_printed_ground_line_ones`.

Design note: [38](../40_history/42_ground_frame_note.md) §1.6 (OQ-1) and §1.13,
GF-6; the disposition §5.4 recommended — registered with the item that built it.

---

### WINGGEOM's strip sum goes closed-form *(approved 2026-08-30, in session)*

WINGGEOM divides a surface's span into `H` strips and sums `A = Σ C·DY`,
`MAC = Σ C²·DY / A` and the two first moments at strip mid-stations. `H` is an
input the manual **never prints**, so the printed figures carry whichever
discretisation each run used. Both edges are piecewise linear, so every one of
those integrals has an exact closed form on each interval between the edges'
breakpoints; `sloads.modules.wing_geometry.surface_properties` now evaluates
those instead of sampling.

**Why it was needed.** The GA6's Appendix A empennage went into the fixture on the
same day (h-tail p151, elevator p153, rudder p149, flap p145, tab p157, each with
its printed LE/TE coordinate table). At the fixture's `elements = 20` those
planforms read **0.2–1.0 %** off their own printed AREA/SIDE and MAC — the tail's
trailing edge has ten points with kinks 0.001 in apart, invisible to 3.66 in
strips. Closed-form integration puts **every** Appendix A surface within
**0.084 %**: wing 0.051, aileron 0.037, h-tail 0.044, stabilizer 0.014, elevator
0.084, elevator-aft 0.090, tab 0.015, rudder 0.067, flap 0.034. `elements` reverts
to what plan 09 T-1 calls it — the spanwise **load-station** count — and no longer
drives this calculation.

**What it costs, and it is not nothing.** For the *wing* the manual used `H = 20`,
and the 20-strip sum reproduces its printed figures far more closely than the
exact integral does: MAC 69.2464 against a printed 69.246 (0.0006 %) versus
69.2756 (0.042 %); area 13256.72 against 13257 (0.002 %) versus 13259.29
(0.017 %). We are therefore **further from the printed wing** and **closer to the
planform the manual drew**. The owner's ruling (in session, 2026-08-30) is that
the entered leading- and trailing-edge polylines are the input, and the printed
derived values are WINGGEOM's own output carrying its own error.

**Appendix A figures that moved.** The wing MAC's 0.042 % reaches the balance, and
five printed figures move with it. All are within the base method's own
uncertainty; the two stated in pounds are near-zero balancing loads where a
percentage misleads.

| Printed figure | Page | Printed | Now | Moved by |
|---|---|---|---|---|
| SELECT h-tail CHECKED MAN UP, total tail load | Critical H-tail Loads | 787.8 lb | 791.84 | +0.51 % |
| Case 202 rational balancing tail load | Ch 9 hand calc | 519.845 lb | 521.62 | +0.34 % |
| Case 202 centre of pressure | Ch 9 hand calc | 6.35 %MAC | 6.50 | +0.15 points |
| CG1 case 5 (MAN D) angle of attack | p179 | 1.56° | 1.5493 | **0.011°** |
| CG2 case 21 (STALL 1G) balancing tail load | p179 | −16 lb | −15.294 | **0.71 lb** |
| CG2 case 23 (MAN A) balancing tail load | p179 | −59 lb | −57.34 | **1.66 lb** |

The three p179 entries are gated in their own units rather than by percentage:
0.71 lb on a printed −16 reads as 4.4 % while being 0.02 % of the 3400 lb
airplane. `test_flight_envelope._PLANFORM_LT_ALLOW_LB` (1.8 lb) and
`_PLANFORM_ALPHA_ALLOW_DEG` (0.005°) carry them, each naming this entry.

**Self-pins re-pinned with this entry cited**, none page-cited: the frozen Imperial
digests (`tests/fixtures_imperial/digests.json`, all six examples — every channel
moves, since every deck carries a wing); `test_balance._UNSYMMETRICAL_SPLIT`
(≤ 0.019 %; the ATR42 and RJ do not move at all); `test_balance._LATERAL_CASE_NUMBERS`
(fin loads ≤ 0.012 %, but ga6 `p_dot` −26 % — that one is the *entered fin planform*,
not the integral: its load centroid sits 2.11 in below the derived rectangle's
half-span, so the roll arm fell 14.00 → 11.89 in); the closure `Izz` and roll
fraction for the RJ; ga6 VA 121.352521 → 121.340758 and VF 105.544396 → 105.534165;
the WTENV ballast stations and the aft-gross corner 85.11 → 85.09; the gear
report's §9.4 lift moment −2.383 → −2.3819; and `test_tail_geometry._FIN_ROOT` for
the three "fuselage-top" fixtures (≤ 0.0015 %).

**Authority:** `sloads/modules/wing_geometry.py` is hash-frozen for milestone
0.8.2 by design note 44 OR-13. The owner admitted this change under **OR-15** in
session on 2026-08-30, and the manifest hash in `tests/test_frozen_set.py` is
updated in the same commit.

---

## Withdrawn from scope

**A third category, and not a deviation.** The entries above say *the manual's
number is wrong and here is the right one*. These say *the manual's number is
right and this tool does not produce it* — the replication's scope is narrowed,
deliberately and on the owner's directive, and the printed figure stands
uncontradicted. They are registered here because the effect on a reader is the
same: an Appendix A output that no test reproduces, which without a record looks
like a regression or an oversight. Each entry names the printed value it is
declining to compute, so that number can never be mistaken for one this project
found fault with.

### MACHLIM flutter-clearance MFC / V(FC) *(withdrawn 2026-08-26, issue #79)*

`MACHLIM.BAS` computes `MFC = 1.2·MD` and its per-altitude `V(FC) = MFC·a·√σ`,
and this port reproduced both — Appendix A p160 prints **MFC 0.4836** for the
worked example, which the oracle test asserted to ±0.1 % until this date.
**Both are removed from the tool.**

Flutter substantiation is **14 CFR 23.629**, not a design load: nothing in this
suite sizes structure to MFC, and a flutter clearance speed presented among
design speeds invites the reading that it is one. The symbol makes that worse
rather than better — a Part 25 audience reads `VFC`/`MFC` as **§25.253's**
maximum-speed-for-stability-characteristics pair, a different quantity under a
different definition, so the same three letters name two things and the tool
printed the one it was not about. Removed on the owner's directive (C210-19,
escalated to full removal at the 2026-08-23 Cessna 210 build review) from the
calc, the report series and workbook column, the Speed–Altitude chart and the
theory document.

**Unaffected and still oracle-locked:** MNE = 0.9·MD (never-exceed, printed
0.3627) and the V(MC)/V(MNE)/V(MD) lines. **Not a VF finding:** every `VF` in
the code and docs is the 23.345 design flap speed — audited alongside this
removal and found free of flutter conflation, which is the other half of #79 and
closes verified-correct.

---

## Considered and declined

An oracle question raised, examined and **answered "replicate as printed"** is
recorded here too. The register exists so a deviation is never accidental; a
decision *not* to deviate is worth the same protection, or the same question
gets re-litigated by whoever next reads the source and thinks it is a bug.

### LANDLOAD's ground-roll attitude resolves at `+BETA(2)` *(declined 2026-08-15 — replicate as printed)*

> **SUPERSEDED 2026-08-29 by the approved deviation above** (issue #133). Kept
> verbatim: the decision was correct on the evidence it had, and its own stated
> reopening condition is what reopened it. What it could not know is that the
> legible output would be a *construction figure* contradicting the program's own
> table, not another table.
>
> **What met the reopening condition**, per [design note
> 38](../40_history/42_ground_frame_note.md): the p231–233 tables read legibly
> when rendered at 200 dpi, bypassing the OCR layer; the Appendix C `.BAS` lines
> are confirmed verbatim; and a second instance of the same sign error was found
> in the datum load-factor lift term. The deviation that replaced this decision,
> and the pin at `ρ = −GRA` on every attitude, are stated in the approved entry
> above. **Everything below this banner is the 2026-08-15 text unchanged** and
> describes the code and the pin test as they stood under that decision.

`LANDLOAD.BAS` resolves each case's wheel resultant into airplane axes through
`PHIM`, and the three attitudes do not carry the ground angle with the same sign:

```
L=1 TO 6, 10 TO 12: PHIM(L) = BETA(1)                  ' BETA(1) = GAMMA - GRA(1)
L=7 TO 9:           PHIM(L) = -BETA(3)                 ' BETA(3) = GRA(3)
L=13 TO 18:         PHIM(L) = ATN(.8)*57.3 + BETA(2)   ' BETA(2) = +GRA(2)
L=19 TO 24:         PHIM(L) = BETA(2)
```

so the ground-line→airplane-datum rotation comes out `ρ = −GRA` in the level and
tail-down attitudes and `ρ = +GRA` in the ground-roll one. The contact patch is
the rolling radius below the axle **along the ground normal**, so the geometry
implies `−GRA` throughout; where the manual differs, its own statements about one
case differ with it. The 23.485 side family's `ROLLP = ±0.83·W·CP` is built on a
**contact-line** arm and its `YAWP = ±0.83·W·BP` on an **axle** arm resolved
through `BETA(2)`: on `ga6_normal` those are 2·GRA(2) = 9.45° apart and no single
rigid rotation of the assembled case reproduces both. The braked-roll family's
pitch carries the same difference (0.6–3.2 % of `PITCHP`).

**Decision (user, 2026-08-15): keep the manual's convention — this is a faithful
replication.** No deviation is taken, `modules/landing.py`'s `phim` block stands
as ported, and the assembled ground cases 13–24 continue to apply their reactions
in the frame LANDLOAD resolved them into. The reasons the bar is not met here:
the airplane-datum `VM`/`DM` have **no legible printed oracle** in the bundled
PDF (the p231–233 wheel-load table is OCR-garbled), so the case rests on a
geometry argument rather than on a figure or an authoritative external reference
of the kind AC 23-19A supplied above; the affected quantity is an intermediate,
not a regulation being encoded wrongly; and the exposure is narrow — `GRA(2)` is
zero on `concept_regional_jet`, `atr42_100` and `dhc8_dash8`, leaving
`ga6_normal` and `cessna_210` as the only fixtures where the question exists.

**What held the decision in place** (while it stood — this entry is superseded,
and the pin below went with it). The state was pinned, not assumed: the test then
named `test_the_ground_roll_attitude_is_resolved_against_the_other_sign` — since
flipped and renamed
`tests/test_gear_report.py::test_rho_is_minus_the_ground_angle_in_every_attitude`
— asserted `ρ = −GRA` per attitude on all five gear fixtures **and `+GRA` on the
ground-roll one**, so a silent change to either went red and landed on this entry.
G-6's rotational gate compares each moment line in the frame LANDLOAD's own arm
is built in and says which; the braked family's pitch line is bounded at 5 % with
this as the named cause. Should a legible Appendix A/B or a `LANDLOAD.OUT`
surface, this entry is where the question resumes.
