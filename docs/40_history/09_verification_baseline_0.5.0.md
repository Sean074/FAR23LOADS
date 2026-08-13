# Verification Baseline — Release 0.5.0

Permanent regression-baseline record for the `0.5.0` release
(`RELEASE_PROCESS.md` §4 step 4). Like
[`08_verification_baseline_0.4.0.md`](08_verification_baseline_0.4.0.md) this is
a **delta baseline**: it records what 0.5.0 verified, and carries the FAR 23
oracle tables forward from
[`02_verification_baseline_0.3.0.md`](02_verification_baseline_0.3.0.md)
**unchanged** rather than restating them.

**Run at cut (2026-08-13):** `pytest` **1494 passed, 21 skipped, 0 failed**
(coverage 93 %), `ruff check sloads/ cli.py app/` clean — the gate now covers
the Streamlit layer — `scripts/smoke_test.sh` **PASS** (headless GUI render +
CLI export), `SCHEMA_VERSION = 44`.

---

## 1. Why the 0.3.0 oracle tables still stand

Unchanged from the 0.4.0 argument, and re-established for this release:

- **Everything 0.5.0 added is additive to the FAR 23 path.** The 22 Appendix-C
  modules' printed-figure assertions in `tests/test_<module>.py` are the same
  assertions against the same manual pages, and they pass in the run above.
- **The approved-deviations register is unchanged** —
  [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md)
  took no new deviation and withdrew none in this release.
- **The Imperial digest baseline** (`tests/fixtures_imperial/digests.json`) gates
  every exported byte in Imperial. 0.5.0 spent the digest wave **four times** —
  the balanced deck three (band-registry node renumber, D-R7's minted subcase
  ids, D-R8's 23.427(a) subcases) and the wing decks once (the `$`-width +
  centreline-clamp header line). Every movement was reviewed channel by channel
  and is a **new or renamed channel**, never a changed FAR 23 figure.

So §2–§6 of the 0.3.0 baseline — the per-module oracle rows, the
oracle-vs-closure status table and the closure-locked module list — remain the
authority for the FAR 23 core at 0.5.0.

---

## 2. New verification in 0.5.0 — all closure, no new oracle

No 0.5.0 capability has a printed oracle: the manual prints no balanced
free-free airplane, no handed asymmetric tail case and no lateral closure. Per
`CLAUDE.md` practice 2 each therefore ships with a **stated physics-closure or
invariant gate in CI**, written with the feature. This table adds to the 0.4.0
one; it does not replace it.

| Area | Module | Gate | Basis |
|---|---|---|---|
| Balanced airframe | `balance` | six-DOF closure: `\|ΣF\|/(n·W)` and `\|ΣM\|/(n·W·MAC)` pre-closure, `\|Δn\|/n` post-closure | plan 11 / plan 13 B8a acceptance |
| | | pitch residual per fixture **and per family** (symmetric / lateral / unsymmetrical) — §3 | plan 11 R3, split per family by B8a-3 |
| | | every SELECT condition is either assembled or **recorded as skipped with a reason** | review F-C7 — no condition drops silently |
| | | `SUBCASE` ids are minted from the case, never from its position in the set | D-R7 / m1 — a dropped condition cannot renumber its neighbours |
| Handed twins | `balance` | an asymmetric case exists only as a starboard/port pair by centreline reflection; symmetric sets are asserted symmetric | D-R8, FAR 23.427(a) |
| | | 23.427(a) is gated at a **maneuver** V-n point, not a gust point | D-R8 |
| Lateral closure | `balance`, `rigid_body` | the lateral three (`fy`, `mx`, `mz`) are closed and gated, not carried untested | plan 13 B8a-3 |
| | | negative control: one reversed lateral `FORCE` card leaves `fy` 3.4 %, `mz` 3.1 %, `mx` 0.20 % out of closure | the lateral gate is proven non-vacuous |
| Report | `report/content`, `report/methods` | every required SUMMARY_REPORT.md §4 section present or explicitly *not analysed*; §4.7 manifest lists every artifact the bundle carries | F-D2 / D-R2 |
| | | the standing-limitations **key set is pinned by test** — opening or closing a caveat is a visible edit | F-R4: the completeness claim is testable |
| | | section cross-references are built from the numbering owner, never literal `§N` | F-R2 |
| | | the standing disclaimer leads `methods_statement`, and the title page quotes the same constant | F-R3 |
| | | every governing row scales by **its own case's** safety factor; the flat-`sf` override is removed | F-R1, M4-8 Layer 1 pre-slice |
| Deliverable units | `export/workbook` | each workbook sheet states **its own** channel's unit set in band; neither channel's set appears on a sheet written in the other | m14, SUMMARY_REPORT.md §3.5/§4.7 |
| Headless parity | `cli.py` | every deliverable reachable headless, the wing export through the LRA transfer, the G8.3 stamp on every headless file, one error contract | F-D1 / F-C2 / F-D3, m2, L-8g |
| Solver | `export/roundtrip` | `concept_heavy` joins the round-trip gate's wing leg | 0.5.0 row 1 |
| Platform | `export/sbeam_bridge` | a zero-by-construction quantity is snapped to an **unsigned** zero relative to its column scale | found by a real CI failure on ARM vs x86 |

The sbeam pin remains by commit
(`ed23b2681feccd9fadfd2e4b829d414094c4b63c`), with the weekly `sbeam-drift`
workflow tracking `main` non-blockingly.

---

## 3. Stated exceptions, pinned rather than hidden

Each is an asserted bound that **goes red when it changes in either direction**,
so this records a measured fact rather than a silence.

| What | Where pinned | Figure at 0.5.0 |
|---|---|---|
| Pre-closure pitch residual ceiling, `ga6_normal` | `test_balance.py::_PITCH_RESIDUAL_CEILING` | symmetric 0.30 %, lateral 0.70 %, unsymmetrical 0.35 % |
| Pre-closure pitch residual ceiling, `concept_regional_jet` | same | symmetric 1.20 %, lateral 1.60 %, unsymmetrical 0.80 % |
| Which conditions assemble into a balanced case | `test_balance.py::test_which_conditions_assemble_is_pinned` | `ga6_normal` (PHAA/PLAA/PMAA/NMAA, ACRL R+L, TORS + the unsymmetrical and lateral families) and `concept_regional_jet` (as above less NMAA) only |
| Only `ACRL` carries an unbalanced roll | `test_balance.py::test_only_acrl_carries_roll` | every fixture enters `TORS` UNB = 0 |
| Which payload cases the weight database can produce | `test_mass_cards.py::test_which_payload_cases_are_derivable_is_pinned` | ga6 4/4 (CG1–CG4), RJ 2/3, atr42 1/3 (CGaft), dhc8 0/3, cessna 0/4, `concept_heavy` 0/1 |
| Concentrated wing masses smeared inboard in exported bending | `test_export_equilibrium.py::test_wing_deck_bending_closure` | `atr42_100` +1.91 %, `dhc8_dash8` +1.11 %, `concept_heavy` +0.44 % on root `Mxx`; exact on masses-free wings |
| Wing-tank fuel not separable in the item database | `test_mass_distribution.py::test_the_unmodelled_wing_mass_is_pinned_per_fixture` | `atr42_100` 3,800 lb, `dhc8_dash8` 4,000 lb, `concept_heavy` 1,200 lb |
| Which decks each fixture produces | `test_export_equilibrium.py` | `concept_heavy` wing + body only (no tail, no control surfaces) |
| Derived ACRL wing case vs the worked example | `test_wing_case_derivation.py` | ~19 % air-load difference; derived route only |
| ATR-42 balanced points above the Mach-capped stall CL | `test_aero_curves.py` | 7 points, CL up to 1.767 vs 1.478 |

Every row above is carried as an open item in
[`../30_future/00_backlog.md`](../30_future/00_backlog.md).

**Skips at cut (21).** All are capability skips with stated reasons — fixtures
carrying no control-surface, tail or spanwise slice (`concept_heavy`,
`atr42_100`, `dhc8_dash8`), the wing-tie skips deferring to the pinned-gap test
above, and the `roundtrip`-marked tests, which skip unless the pinned solver is
installed (`pip install -e '.[solver]'`) and run in their own CI job. No
`xfail`, and no skip without a backlog entry (`RELEASE_PROCESS.md` §3.3).

---

## 4. Standing limitations of a 0.5.0 deliverable

Recorded here because a regression baseline that states only what is verified
overstates what the release is. All four travel **in band** — deck `$` headers,
case notes and the report's methods & limitations section — and are summarised
in the 0.5.0 changelog entry.

1. **The fuselage deck is flight-only.** No ground, landing or pressurization
   case is distributed onto the body (decision **D-R3**; the 0.6.0 headline).
2. **Lateral aerodynamics are fin-only** (decision **L-7**) — no fuselage or
   nacelle `Cy_β`/`Cn_β`, so `n_y` and `ψ̈` are over-stated and conservative,
   not correct.
3. **23.427(a) ships as a handed pair and is a maneuver case** — a reader given
   one hand must be told the other exists.
4. **Concept mode is closure-locked, not oracle-locked** (decision **D-R6**) —
   an unverified extrapolation above the FAR 23 calibrated band, stated as such
   wherever its figures are read.

---

## 5. What measurement changed in this release

Recorded because it is the argument for the gates themselves — each was found by
a check, not by review.

- **A platform-dependent negative zero failed CI on a difference that was not a
  difference.** The fuselage deck's free-free residuals are ~1e-11 of
  cancellation dust whose *sign* is not reproducible across x86 and ARM, so the
  same code printed `0.00` on one machine and `-0.00` on another. Found from a
  CI digest failure while the same commit passed locally.
- **The governing-loads tables applied a flat 1.5 instead of each case's own
  safety factor** — no shipped number moved (SELECT stamps the 23.303 default on
  every condition today), but the first non-1.5 case would have been silently
  mis-scaled in the report and in both GUI views.
- **The limitations list claimed completeness and was missing four caveats**
  (F-R4), which is why the key set is now pinned by test.
- **The `.xlsx` workbook stated one unit system for two channels** (m14) — in SI
  a factor of 1000 in moment on every span-load sheet.
- **`scripts/smoke_test.sh`, the §3.5 release gate itself, could not read the
  G8.3 methods stamp** and failed the release it was gating. The Python CSV
  readers were audited when the stamp landed; this shell one was not.

---

## 6. Supersession

This document **supplements** the 0.3.0 baseline for the FAR 23 core and the
0.4.0 baseline for the mission-extension gates, and **supersedes** nothing in
either. The next full re-statement of the oracle tables should happen the first
time a FAR 23 printed figure is affected.
