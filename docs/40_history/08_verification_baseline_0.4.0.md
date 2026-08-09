# Verification Baseline — Release 0.4.0

Permanent regression-baseline record for the `0.4.0` release (the mission
extension's first seven steps; `RELEASE_PROCESS.md` §4). This is a **delta
baseline**: it records what 0.4.0 added, and carries the FAR 23 oracle tables
forward from
[`02_verification_baseline_0.3.0.md`](02_verification_baseline_0.3.0.md)
**unchanged** rather than restating them.

**Run at cut (2026-08-08):** `pytest` **1232 passed, 21 skipped, 0 failed**
(coverage 93 %), `ruff check sloads/ cli.py` clean, `scripts/smoke_test.sh`
**PASS** (headless GUI render + CLI export), `SCHEMA_VERSION = 42`.

---

## 1. Why the 0.3.0 oracle tables still stand

Everything 0.4.0 added is **additive to the FAR 23 path**. The 22 Appendix-C
modules' printed-figure assertions in `tests/test_<module>.py` are the same
assertions against the same manual pages, and they pass in the run above. Two
independent confirmations that no oracle figure moved:

- **The approved-deviations register is byte-unchanged since `v0.3.0`** —
  `docs/20_theory/02_approved_corrections.md` has no diff against the tag. No new
  deviation was taken, and none was withdrawn.
- **The Imperial digest baseline** (`tests/fixtures_imperial/digests.json`) gates
  every exported byte in Imperial; each 0.4.0 digest movement was reviewed
  channel-by-channel and is a **new** channel (spanwise tail decks, `GRID` cards
  on the body/tail decks, balance channels), never a changed FAR 23 figure.

So §2–§6 of the 0.3.0 baseline — the per-module oracle rows, the
oracle-vs-closure status table, and the closure-locked module list — remain the
authority for the FAR 23 core at 0.4.0. What follows is only what is new.

**The fixtures did change** (all six `examples/*.project.json`), but as
*additions*: component tags on `weight.items`, tail mass/planform slices, the
`vd_basis` speed fields and the schema hops v33 → v42. `ga6_normal` remains the
Appendix A airplane and its oracle rows are the ones cited above.

---

## 2. New verification in 0.4.0 — all closure, no new oracle

None of the 0.4.0 capabilities has a printed oracle: the manual gives tail
*totals* and a chordwise profile and stops, and it prints no distributed inertia
load, no mass model and no assembled airframe. Per `CLAUDE.md` practice 2 each
therefore ships with a **stated physics-closure or invariant gate in CI**,
written with the feature.

| Area | Module | Gate | Basis |
|---|---|---|---|
| Mass SSOT | `mass_distribution` | `Σw = W`, `Σw·x = W·x_cg`, `Σw·z = W·z_cg`; wing item = 2 × panel weight | drift guards on the itemized model (plan 11 B1) |
| | | partition closes: every item lands on exactly one beam | no-double-count property |
| Mass export | `export/mass_cards` | each `MASSSET` reproduces its loading's mass, CG-x and CG-z | `CONM2` re-summation, **both** unit systems |
| | | mass-check deck carries **no load cards**; no total set and accelerated `CONM2` set share a subcase | C-6 structural anti-double-count |
| | | no overlay `CONM2` left unreferenced by a `MASSSET` row | caught a real defect (see §4) |
| Balanced cases | `balance` | `\|ΣF\|/(n·W) < 1 %` **before** closure | plan 11 acceptance 1 |
| | | `\|Δn\|/n < 1 %` after closure | plan 11 acceptance 2 |
| | | pitch residual per fixture (§3) | plan 11 R3 "state the floor per fixture" |
| Empennage span | `tail_span` | Σ strip `fz` = `LT25 + LT50` + inertia, exactly | SELECT totals, read not recomputed |
| | | root bending = `L_half · ȳ`, `ȳ` the planform area centroid | closed form |
| | | torsion = `(LT25+LT50)·x̄_lra − LT25·x̄_25 − LT50·x̄_50` | area-weighted closed form |
| | | LRA at 25 % chord ⇒ `LT25` contributes no torsion | reduction identity |
| | | inertia = `−n · W_surface` (d'Alembert, signed by `n` alone) | asserts the **increase** on down-load cases |
| | | net centreline moment ≡ 0 for every symmetric case | full-span h-tail beam |
| | | all six closures re-checked on a **tapered and swept** planform | the closures are not properties of the rectangle |
| Export boundary | `export/equilibrium` | every deck's `FORCE`/`MOMENT` cards re-sum to the root totals × per-case SF | every fixture × both unit systems |
| Solver | `export/roundtrip` | the decks **solve in the real sbeam** and recover the root loads; assembled deck reacts to ≈ 0 | `sbeam-roundtrip` CI job, solver pinned by commit |
| | | negative controls: a scaled `FORCE` card, swapped subcase load IDs and a displaced `GRID` each **break** the assertions | the gate is proven non-vacuous |

The sbeam pin is deliberate and by commit
(`ed23b2681feccd9fadfd2e4b829d414094c4b63c`), with a separate weekly
`sbeam-drift` workflow tracking `main` non-blockingly — an unrelated sbeam commit
must never redden an unrelated sloads PR.

---

## 3. Stated exceptions, pinned rather than hidden

Each of these is an asserted upper bound that **goes red when it changes in
either direction**, so the baseline records a measured fact, not a silence.

| What | Where pinned | Figure at 0.4.0 |
|---|---|---|
| Pre-closure pitch residual, `ga6_normal` | `test_balance.py::_PITCH_RESIDUAL_CEILING` | 0.117–0.290 % (ceiling 0.30 %) |
| Pre-closure pitch residual, `concept_regional_jet` | same | PLAA 1.041 %, PMAA 0.967 %, TORS 1.174 % (ceiling 1.20 %) |
| Pre-closure force residual | `test_balance.py` | ga6 0.05–0.62 %, RJ 0.03–0.70 % — inside the 1 % gate everywhere |
| Concentrated wing masses smeared inboard in exported bending | `test_export_equilibrium.py::test_wing_deck_bending_closure` | `atr42_100` +1.91 %, `dhc8_dash8` +1.11 %, `concept_heavy` +0.44 % on root `Mxx`; exact closure on masses-free wings |
| Wing-tank fuel not separable in the item database | `test_mass_distribution.py::test_the_unmodelled_wing_mass_is_pinned_per_fixture` | `atr42_100` 3,800 lb, `dhc8_dash8` 4,000 lb, `concept_heavy` 1,200 lb |
| Which payload cases are derivable from the weight database | `test_mass_cards.py::test_which_payload_cases_are_derivable_is_pinned` | 7 of 18 (ga6 4/4, RJ 2/3, atr42 1/3, dhc8 0/3, cessna 0/4, heavy 0/1) |
| Which conditions assemble into a balanced case | `test_balance.py::test_which_conditions_assemble_is_pinned` | `ga6_normal` and `concept_regional_jet` only |
| Only `ACRL` carries an unbalanced roll | `test_balance.py::test_only_acrl_carries_roll` | every fixture enters `TORS` UNB = 0 |
| Derived ACRL wing case vs the worked example | `test_wing_case_derivation.py` | ~19 % air-load difference; derived route only |
| ATR-42 balanced points above the Mach-capped stall CL | `test_aero_curves.py` | 7 points, CL up to 1.767 vs 1.478 |

All ten are carried as open items or defects in
[`../30_future/00_backlog.md`](../30_future/00_backlog.md).

**Skips at cut (21).** All are capability skips with stated reasons — fixtures
carrying no control-surface, tail or spanwise slice (`concept_heavy`,
`atr42_100`, `dhc8_dash8`), plus the three wing-tie skips that defer to the
pinned-gap test above. No `xfail`, and no skip without a backlog entry
(`RELEASE_PROCESS.md` §3.3).

---

## 4. What measurement changed in this release

Recorded because it is the argument for the gates themselves — each of these was
found by a check, not by review.

- **Overlay `CONM2` cards that no `MASSSET` named were silently counted in every
  loading.** sbeam decides overlay-only status by *reference*; a card no `ADD`
  row names belongs to the baseline. Caught by the no-unreferenced-overlay guard,
  which now exists because of it.
- **`TORS` is not antisymmetric.** Plan 11 §2 assumed it was; every shipped
  fixture enters zero unbalanced rolling moment for it, and correctly so — a
  *steady* roll has no unbalanced rolling moment by definition. `TORS` joined the
  symmetric conditions, with the finding pinned.
- **The round-trip harness's determinate support was implicitly x-axis-only** —
  the fin, which spans `z`, exposed it.
- **The fuselage beam runs ~14 % light in inertia on ga6** — `weight.items` less
  the wing/tail leaves 3,005 lb against the 2,578 lb entered in
  `fuselage_mass.stations`. Found by the balanced-airframe baseline; closed by
  making `weight.items` the mass SSOT.
- **Concept dive speeds were silently overridden (Major)** and **MC/MD had two
  homes the front-ends disagreed on** — both found by F25-2.

---

## 5. Supersession

This document **supplements** the 0.3.0 baseline for the FAR 23 core and
**supersedes** nothing in it. The next full re-statement of the oracle tables
should happen the first time a FAR 23 printed figure is affected — at which
point that release's baseline becomes the standalone record and this one, with
0.3.0, becomes history.
