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

> **Question resumed 2026-08-28** — the reopening condition below has been met:
> the p231–233 table now reads legibly (rendered at 200 dpi, bypassing the OCR
> layer), the Appendix C `.BAS` lines are confirmed verbatim, and a second
> instance of the same sign error was found in the datum load-factor lift term.
> [Design note 38](../30_future/38_ground_frame_note.md) (AGREED 2026-08-28)
> supersedes this decision: when issue #133 lands, this entry converts in place
> to an approved deviation and its pin test flips to ρ = −GRA on every
> attitude. Until then the code and pin test stand as described below.

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

**What holds the decision in place.** The state is pinned, not assumed:
`tests/test_gear_report.py::test_the_ground_roll_attitude_is_resolved_against_the_other_sign`
asserts `ρ = −GRA` per attitude on all five gear fixtures **and `+GRA` on the
ground-roll one**, so a silent change to either goes red and lands on this entry.
G-6's rotational gate compares each moment line in the frame LANDLOAD's own arm
is built in and says which; the braked family's pitch line is bounded at 5 % with
this as the named cause. Should a legible Appendix A/B or a `LANDLOAD.OUT`
surface, this entry is where the question resumes.
