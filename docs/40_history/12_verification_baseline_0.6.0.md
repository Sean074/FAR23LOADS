# Verification Baseline — Release 0.6.0

Permanent regression-baseline record for the `0.6.0` release
(`RELEASE_PROCESS.md` §4 step 5). Like
[`09_verification_baseline_0.5.0.md`](09_verification_baseline_0.5.0.md) this is
a **delta baseline**: it records what 0.6.0 verified, and carries the FAR 23
oracle tables forward from
[`02_verification_baseline_0.3.0.md`](02_verification_baseline_0.3.0.md)
**unchanged** rather than restating them.

**Run at cut (2026-08-17):** `pytest` **2044 passed, 18 skipped, 1 xfailed,
0 failed**; `ruff check sloads/ cli.py app/ scripts/` clean; `mypy` clean on
`sloads/` (the type gate is new this release); `scripts/smoke_test.sh` **PASS**
(headless GUI render + CLI export); `scripts/backlog_issues.py check` clean;
`SCHEMA_VERSION = 53`.

---

## 1. Why the 0.3.0 oracle tables still stand

Re-established for this release, with one thing that is different from 0.5.0:

- **Everything 0.6.0 added is additive to the FAR 23 path.** The 22 Appendix-C
  modules' printed-figure assertions in `tests/test_<module>.py` are the same
  assertions against the same manual pages, and they pass in the run above.
- **The approved-deviations register took one entry** —
  [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md),
  *"Truncated `.BAS` constants go exact"* (issue #26, 2026-08-17): the shared
  constants the programs wrote truncated (`57.3`, `32.2`, `V²/295`,
  `1.15·88/60`, FLTLOADS' private speed of sound) now read their exact owners in
  `sloads/constants.py`. The entry records that **each move was measured against
  the whole suite before it was made** and that **no page-cited oracle moved** —
  Appendix A ±0.1 % holds throughout; what moved were self-pins only, each
  re-pinned with the entry cited. One survivor (`KT_TO_FPS_SUITE`, `VSF` only) is
  kept by the ENGLOADS gyro-thrust oracle. This is the register working as
  designed, not a change to the FAR 23 figures.
- **The Imperial digest baseline** (`tests/fixtures_imperial/digests.json`)
  still gates every exported byte in Imperial. 0.6.0 spent the wave several
  times, each deliberately and each recorded in the changelog entry that spent
  it — the ground family, the T-tail twins, the case-identity linkage, the
  trusted-α clamp, the wing-tank split, the constants move, and the
  platform-stable snap (`-0`/dust → `0` only). Every movement is a new channel, a
  renamed channel or a stated re-pin — never a changed FAR 23 figure.

So §2–§6 of the 0.3.0 baseline — the per-module oracle rows, the
oracle-vs-closure status table and the closure-locked module list — remain the
authority for the FAR 23 core at 0.6.0.

---

## 2. New verification in 0.6.0 — closure and invariant gates

No 0.6.0 capability has a printed oracle beyond LANDLOAD's own tables (which the
ground family reproduces, below). Per `CLAUDE.md` practice 2 each ships with a
**stated physics-closure or invariant gate in CI**, written with the feature.
This table adds to the 0.5.0 one; it does not replace it.

| Area | Module | Gate | Basis |
|---|---|---|---|
| Ground and landing cases | `gear_loads`, `balance` | the assembled ground case reproduces LANDLOAD's reactions and its unbalanced moments (`test_gear_report.py::test_the_ground_closure_reproduces_landload`, `…_landloads_unbalanced_moments`); closes in all six DOF | plan 18 (now `23_step10_ground_cases_plan.md`) G-6/G-7 |
| | | negative controls: a static contact patch breaks the level-landing gate; dropping the offset couple breaks the transfer; the rotational gate's two departures are not no-ops | the gate is proven non-vacuous |
| | | the reflected side case reproduces LANDLOAD's own twin; the handed ground families are pinned | G-13 |
| Gear report | `gear_report` | transfer to the reference point preserves the resultant; the couple is the cross product and nothing else; rows are ULTIMATE at the governing factor; CSV states units, factor and wheel in both channels | load-output contract, `safety_factors.py` |
| Governing safety factors | `safety_factors` | one row per condition family with a basis; a case the table cannot classify is flagged, never defaulted | M4-8 / G-11 |
| LRA beam model | `export/lra_model` | the transferred set has the balanced deck's resultant; an exported model re-imports with every family mapped and the imported loads reproduce the resultant; the split fuselage has no element through the carry-through; every `CBAR` references its family section (one `PBAR`/`MAT1` pair per family) | notes 24/25 (BM-1…BM-5, LM-1…LM-7), #7 |
| Wing-tank fuel separability | `mass_distribution` | the wing tie holds on every shipped fixture (`test_the_wing_tie_holds_on_every_shipped_fixture`); stripping the fraction re-opens **exactly** the wing-tank fuel; every consumer agrees with `reacted_parts` on the wing share | note 29 WF-3/WF-4, schema v53 |
| Non-wing drag carrier | `balance` | G10 `ΔC_D` consistency inside the trusted-α window; outside it the forward difference is not applied and the residual is reacted, pinned per case under a 2.5 % hard stop (`FORCE_RESIDUAL_CEILING`, `CLAMPED_PITCH_CEILING`) | note 20 D-4 rev. |
| `CgCase.loading` | `mass_distribution` | the entered loading is authoritative; the case's weight/CG is a checked echo (`max(0.5 lb, 0.1 %)`, `0.5 in`); pre-v50 files byte-identical | note 22 D-25a…d |
| Constants and conversions | `constants`, `units` | grep drift guards both ways: Imperial factors have one owner, SI factors live only in `units.py`, no private aliases, exact-by-default values (`test_constants.py`) | `CONVENTIONS.md` §7, #26 |
| Platform-stable bytes | `select`, `export/sbeam_bridge` | keyed picks are first-in-order inside a 1e-9 band; zero-by-construction card components snap; every summation in `sloads/` is `math.fsum` | `CONVENTIONS.md` §7 row |
| Export namespace | `export/` | AST guard: no three-argument `getattr` anywhere in the package | CH-2 |
| Process | `scripts/`, `docs/` | `test_doc_currency` (no copied numbers in the standard; INDEX ↔ tree both ways), `test_changelog_fragments`, `test_backlog_issues` (every row carries `(#N)`), `test_solo_scripts` | notes 26/28, #27 |

---

## 3. Stated exceptions, pinned rather than hidden

Each is an asserted bound that goes red when it changes in either direction.
The 0.5.0 list is carried forward with these changes:

| What | Where pinned | At 0.6.0 |
|---|---|---|
| Pre-closure pitch residual, per fixture and family | `test_balance.py::_PITCH_RESIDUAL_RATCHET` (was `_CEILING`) | a ratchet of what each family actually reaches, under `FORCE_RESIDUAL_CEILING = 0.025` / `CLAMPED_PITCH_CEILING = 0.025` hard stops; the clamped `NMAA` points on `atr42_100`/`dhc8_dash8`/`concept_heavy` are the cases that re-opened (note 20 §8.2) |
| Wing-tank fuel not separable | — | **closed** — `test_the_unmodelled_wing_mass_is_pinned_per_fixture` deleted; the tie is a validator (`wing_mass_tie_open`) and a gate (§2) |
| Which payload cases are derivable | `test_mass_cards.py` | superseded by entered loadings (D-25/D-26): **6 of 6** fixtures assemble |
| Concentrated wing masses smeared inboard | — | closed in 0.5.0's cycle (note 14) |
| Which conditions assemble / which decks each fixture produces | `test_balance.py`, `test_export_equilibrium.py` | carried forward; the ground families added, the 23.499 supplementary nose-wheel family skipped with a recorded reason |
| The SELECT unsymmetrical split | `test_balance._UNSYMMETRICAL_SPLIT` | re-pinned ≤ 0.08 % per value at the exact constants (register entry) |
| ATR-42 balanced points above the Mach-capped stall CL | `test_aero_curves.py` | carried forward |

**Skips at cut (18) and the one xfail.** The skips are capability skips with
stated reasons (fixtures carrying no control-surface, tail or spanwise slice;
the `roundtrip`-marked tests, which run in their own CI job with the pinned
solver); the `xfail` is a stated, reasoned expectation, not a hidden failure. No
skip without a backlog entry (`RELEASE_PROCESS.md` §3.3).

---

## 4. Standing limitations of a 0.6.0 deliverable

All travel **in band** (deck `$` headers, case notes, the report's methods &
limitations section) and the key set is pinned by test.

1. **The fuselage deck is no longer flight-only** — the ground and landing
   families are in the assembled deck (D-R3 discharged). **Pressurization is out
   of scope, permanently**, and the deliverable says so.
2. **Lateral aerodynamics are fin-only** (decision **L-7**, note 19 still
   PROPOSED) — `n_y` and `ψ̈` over-stated and conservative.
3. **23.427(a) ships as a handed pair and is a maneuver case.**
4. **Concept mode is closure-locked, not oracle-locked** (decision **D-R6**).
5. **Engine failure is propeller-only** (`engine-failure-propeller-only`, #4) —
   ONENGOUT refuses an installation without a propeller disc.
6. **Power effects on the wing are not modelled** (note 21 AGREED, no code) —
   today's wing cases are exactly zero-thrust.

---

## 5. What measurement changed in this release

Each was found by a check, not by review — the argument for the gates.

- **`main`'s CI had been red on every run since the LRA model shipped** on two
  tests that pass on the developer's Mac: exactly-tied V-n picks flipping
  between platforms, cancellation residue printing as `-0.000000E+00`, and
  Python 3.12's compensated `sum()` moving float sums a few ulp. Nothing blocked
  on CI until branch protection did.
- **The same fuel pounds rode both beams** on the three fuel-in-wing fixtures
  (3,800 / 4,000 / 1,200 lb — 7–15 % of the derived body beam, above the base
  method's own band), pinned as an "unmodelled" gap since 0.5.0; now a split with
  one owner and a validator.
- **The polar's `ΔC_D` inverted sign at the negative-α end as well as the
  positive**, carrying a 1.0–1.4 klb *forward* body-axial card on three
  fixtures' `NMAA` — excused inside a symmetric window that was the wrong shape.
- **Shared constants were spelled six ways** (deg/rad), two ways (`g`), and
  inline at ~24 sites (`/12.0`) and 16 sites (`V²/295`); no oracle moved when
  they were given one owner, which is itself the measured result.
- **The Dash 8's wing-carried main gear was fuselage mass in both mass models;
  the FAR 23 applicability gate read the item-database total as the design
  weight** — both defects of shipped content, both first-order.

---

## 6. Supersession

This document **supplements** the 0.3.0 baseline for the FAR 23 core, the 0.4.0
baseline for the mission-extension gates and the 0.5.0 baseline for the balanced
free-free deliverable, and **supersedes** nothing in them except the two 0.5.0
§3 rows marked closed above. The next full re-statement of the oracle tables
should happen the first time a FAR 23 printed figure is affected.
