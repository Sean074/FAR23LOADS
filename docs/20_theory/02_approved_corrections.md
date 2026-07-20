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
