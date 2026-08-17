# Backlog — Open Work & Development Plan

The authoritative list of **open** items, mission-tagged, in one order — the
**priority table** below; item bodies follow it. Rules of the road (closure
tiers, definition of done, the removal rule, naming) are in
[`../../CLAUDE.md`](../../CLAUDE.md) and restated once above the table; they
are not repeated here. Off-mission items live in [`02_parked.md`](02_parked.md);
completed work in [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)
and [`../../CHANGELOG.md`](../../CHANGELOG.md); the pre-2026-08-16 running
"current state" narrative is archived in
[`../40_history/10_backlog_state_narrative_to_2026-08-16.md`](../40_history/10_backlog_state_narrative_to_2026-08-16.md).
Narratives and plans: [`01_concept_loads_plan.md`](01_concept_loads_plan.md)
(concept mode), [`03_gui_rework_plan.md`](03_gui_rework_plan.md) (GUI),
notes 09–25 per step; architecture
[`../10_standard/PROJECT_GUIDE.md §7`](../10_standard/PROJECT_GUIDE.md); per-module
spec [`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md).

> **Invariant:** no calc-math change to the FAR23 path — Appendix A oracles pass
> throughout; concept mode reduces exactly to FAR23 on GA inputs; ultimate-load
> output rules hold; `workflow.py` stays the single source of navigation truth.

## Mission

**A demonstrated concept-loads → sbeam sizing loop** (2026-08-05): a concept
configuration goes in, distributed ULTIMATE loads come out as `FORCE`/`MOMENT`
cards, and the exported deck solves in sbeam with verified global equilibrium,
continuously in CI; the FAR23 core stays oracle-locked. **Primary deliverable
(2026-08-08):** the **full-span balanced free-free airplane model** — mass
model exported (CONM2), wing/fuselage/empennage/landing cases carrying aero +
inertia, left/right twins by reflection, and an LRA beam model exported and
importable — decisions of record plan 11 §2 (B-1…B-8), plan 12 (C-1…C-6),
note 24 (BM-1…BM-5). **Order of work (2026-08-09):** the sbeam
`FORCE`/`MOMENT` cards for the wing, body and tail cases. Items are tagged
**[E]** (essential to the loop) or **[V]** (valuable, not blocking).
**Definition of done** for a calc step: module merged and self-registered;
`tests/test_<module>.py` passing (±0.1 % oracle where printed, else a stated
closure gate in CI, benchmark-first); a page in `workflow.py`; the `Project`
schema round-trips with `SCHEMA_VERSION` bumped and older files loading; docs
synced per the closure tier.

**Where things stand (2026-08-16):** 0.5.0 cut 2026-08-13; `[Unreleased]`
holds steps 9–13 (control surfaces, ground/landing cases, the SF table, the
`CgCase` loading definition, the SOB node and the LRA beam model; schema v52),
with every shipped fixture assembling balanced flight and ground cases. Band A
of the table below is the 0.6.0 scope. Reference-authority hierarchy: (1) `.BAS`
listings + Appendix A printed output, (2) User's Guide CFR quotes (Jan-1994),
(3) Code-manual 1990 prose.

---

# Priority table (re-cut 2026-08-16 from the scope and deficiency review — the single order of work)

**Re-cut 2026-08-16 (user, from
[`../50_reviews/2026-08-16_scope_and_deficiency_review.md`](../50_reviews/2026-08-16_scope_and_deficiency_review.md)).**
The review sorted every row against the **base method's own error bar** rather
than by mission trace alone, and three things changed: (1) **band A is now the
whole of 0.6.0** — the first-order defects in shipped output, the units and
gate gaps, and the code-health items that make every later session cheaper;
the release is cut when band A is empty and **nothing in band B holds it**;
(2) **step 14 is descoped** from "real stiffness" to a `PBAR`/`MAT1`
pass-through (§2.3 of the review) — the indeterminate-path half is parked;
(3) **fourteen rows are parked** to
[`02_parked.md`](02_parked.md) ("Parked 2026-08-16") — the band-E physics
that adds fidelity above the base analysis (power effects' seven-step plan,
Multhopp `Cm`, the pitching load factor, per-CG inertia), the whole band-H
Part 25 pack, and the fixture-only rows — with bodies kept in full. Two
standing rules were added to the ordering rules below: the
**effect-vs-error-bar rule** and a **schema freeze through 0.6.0**. Bands
A–C are a reading aid; the **Pri** column is the order.

**System of record (design note 28 MD-5, 2026-08-16):** open work is **GitHub
Issues** (labels `tier:*`, `tag:*`, `band:*`, `kind:*`; a milestone per release;
the Project board is the view). This file keeps the **plan** — mission,
definition of done, the reference hierarchy, and this table — and each row names
its issue as `(#N)` once `scripts/backlog_issues.py create` + `rewrite` have run
(owner, once); item bodies then live in the issues, a PR says `Closes #N`, and
`scripts/backlog_issues.py check` holds table ↔ open issues both ways. Until the
migration runs, bodies stay where they are — a defect promoted into the table
keeps its body in *Open defects*, and the [E]/[V] detail sections hold the rest.

Previously re-cut 2026-08-15 (post-0.6.0-headline: defects interleaved by
severity, band C from D-25), 2026-08-13 at the 0.5.0 tag, and 2026-08-10 from
the 0.5.0 code review
([`../50_reviews/2026-08-10_code_review_0_5_0.md`](../50_reviews/2026-08-10_code_review_0_5_0.md))
and its user-resolved decisions **D-R1…D-R8**
([`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md)).
The 0.5.0 scope and the 0.6.0-candidate review's rows
([`../50_reviews/2026-08-15_review_0_6_0_candidate.md`](../50_reviews/2026-08-15_review_0_6_0_candidate.md))
are gone from this table under the removal rule; what shipped is in
[`../../CHANGELOG.md`](../../CHANGELOG.md) and
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).
Review finding IDs still cited per row (m\*, CH-\*) resolve in their review
document. Historic step numbers (steps 8–14) are kept inside item names for
traceability with plans 09/11/12/13; the **Pri** column is ordinal only.

**Ordering rules (cumulative):**

- *2026-08-09:* wrong cards outrank missing cards; [V] items are ranked, not
  opportunistic.
- *2026-08-16 — effect-vs-error-bar rule* — promoted to **`CLAUDE.md` rule 6**
  (the datum it measures against is
  [`../20_theory/00_theory_sources.md` §Base-method uncertainty](../20_theory/00_theory_sources.md#base-method-uncertainty)):
  a [V] item is ranked only if its stated effect exceeds that; below it, parked
  with the number. Defects with first-order effect on shipped content outrank
  every [V] item.
- *2026-08-16 — schema freeze through 0.6.0.* `SCHEMA_VERSION` moves once more
  before the cut (Pri 6's one additive field); no other hop. v47 → v52 in nine
  days is the churn the freeze answers.

> **Removal rule (hard requirement, restating the lifecycle rule).** Once a
> step is complete it **SHALL be removed** from this table and this file in the
> same session, with its tiered closure trail. Renumber the remaining rows
> freely — priorities are an order, not IDs.

| Pri | Item (detail below / in its plan) | What ships | Tag | Tier / effort | Depends on |
|---|---|---|---|---|---|
| **A — 0.6.0: defects in shipped output, contract gaps, and the cost-of-change fixes (review §1, §5.1)** ||||||
| 6 | Wing-tank fuel separability (#6) | Ends the same pounds riding both beams on the three fuel-in-wing fixtures — a `wing_fraction` on `MassItem` (or a second row) + the tie validator; **the freeze's one schema hop**; **not** plan 12 C1 | E | L / M | after the other band-A rows |
| 7 | Step 14 **descoped** — `PBAR`/`MAT1` pass-through per LRA element family (was "real stiffness", L-1) (#7) | Consumer-supplied section properties written in place of the `_MAT1_E` placeholder; no physics, no gate beyond "the deck still solves"; the indeterminate-path half is parked | E | S / S | — |
| 8 | **Constants and conversion factors — one owner, one value, one rule** (review [`2026-08-17_constants_and_conversions_review.md`](../50_reviews/2026-08-17_constants_and_conversions_review.md) C-1…C-12): `DEG_PER_RAD`/`IN_PER_FT`/`FT_LB_S_PER_HP`/gust 498-0.88-5.3 owners added and the six spellings of deg/rad, the two `_G = 32.2`, six `144` aliases + ~24 inline `/12.0` and 15 inline `V²/295` routed through `constants.py` (`aero_curves.dynamic_pressure` for q); `.BAS`-truncated values go **exact by default**, a survivor only as a named `*_SUITE` twin with its oracle cited (FLTLOADS 518.688 °R stays so; 295 measured before deciding); the **`constants.py` vs `units.py` demarcation** (Imperial↔Imperial vs Imperial↔SI only) written into `CONVENTIONS.md` §7 with grep drift guards both ways (#26) | One value of g, of deg/rad, of q in the whole package; measured effect ≤0.08 % (no printed oracle moves; frozen digest + `test_balance` SELECT pins re-pinned, register lines in `02_approved_corrections.md`); the CH-6 defect class closed for every shared constant, not just ρ₀ | E | M / M | after Pri 5 (done) |
| — | **Cut 0.6.0** when band A is empty (RELEASE_PROCESS §2 cadence rule; `[Unreleased]` already holds two unreleased schema hops) | | | | |
| **B — 0.7+: capability the base method is missing at first order, fixture data, and report polish (review §2.1)** ||||||
| 9 | Lateral body aero `Cy_β`/`Cn_β` (L-7) — design note in [`19_l7_lateral_body_aero_note.md`](19_l7_lateral_body_aero_note.md) (**proposed, awaiting agreement**) (#8) | Honest lateral `n_y`/`ψ̈` (today `ψ̈` over-stated 73–84 %, `n_y` under-stated 4–12 % — a missing term of the order of the one kept, not a refinement); DATCOM 5.2.3.1/5.2.1.1 makes it an **oracle** step | V | L / M | — |
| 10 | Fixture-data pass: empennage planform polylines **+** the WTENV envelopes entered independently of the item database (four fixtures) (#9) | Real taper in the tail card distributions instead of the `assumed` rectangle; CG limits derived from (or reconciled with) each fixture's own loading extremes | V | S / S | — |
| 11 | Thrust `FORCE` at the engine hub *(carved out of note 21; the seven-step wake plan is parked)* (#10) | One user-entered thrust per engine as a card on the LRA hub node the skeleton already has — what a wing with a wing-mounted engine needs from a loads tool | V | S / S | — |
| 12 | Combined flight + ground station envelope *(from step 10 decision G-9)* (#11) | Two-sided max/min per station over both families, each extreme naming its governing case | V | M / M | — |
| 13 | Gust spanwise-distribution decision (#12) | Study + recorded decision (Schrenk shape reused) | V | S / S | — |
| 14 | Decisions, not effort: derived-`ACRL` air-load divergence (which point `ACRL` names); ATR-42 Mach-capped stall exceedance (`_balance` reports an infeasible corner rather than an unconverged point) (#13) | Two recorded decisions; each is pinned by test today | V | S / S | — |
| 15 | The aileron's own lift increment is not distributed (#14) | `ACRL` wing cards gain the aero half of the couple (~70 % span); the schema fields shipped v52 and wait for data and a consumer | V | L / M | only if a consumer sizes to `ACRL` |
| **C — maintenance and hygiene, when the module is next touched (review §5.2)** ||||||
| 16 | Export deck-writing primitives out of `sbeam_bridge.py` (CH-4) (#15) | `_fmt`/`_sf_str`/`_stamped`/`_MAT1_*`/`_PBAR_*` in a shared module; the four private cross-imports gone | V | S / S | — |
| 17 | Dead code (CH-5) (#16) | Delete `write_balanced_deck`, `write_conm2_fragment`, `write_mass_check_deck`, `all_checks`; demote the ~12 no-consumer public names | V | S / S | — |
| 18 | Calc-side function size (CH-8) — `build_lra_model` (336 lines), `landing_reactions` (200) (#17) | Split when touched; **the view functions are under the GUI freeze and are not worked** | V | S / S | — |
| 19 | Review 2026-08-10 unscheduled findings m3–m13, m15–m18 + NITs *(defect sweep)* (#18) | Swept opportunistically (practice 4) or promoted individually | V | S / S–M | — |
| 20 | mypy strictness ratchet — stage 2 `export/`, stage 3 `modules/` *(design note 27 ST-3; detail below)* (#19) | `sloads.export.*` then `sloads.modules.*` added to the `[[tool.mypy.overrides]]` list and narrowed to zero under ST-4 (no `ignore`, no `Any` widening, no `cast`); then `warn_return_any`/`disallow_any_generics` toward `--strict`; `UP` on when 3.9 leaves the matrix | V | S / S per stage | — |

**Frozen (review §3) — no further investment; tests and gates kept; touched
for defects only:** the FAR 23 core; the balanced assembler + handedness;
CONM2/MASSSET export; the sbeam round-trip harness; the ground/landing
families + gear report; the governing safety-factor table (Layer 2 parked);
distributed empennage loads, control surfaces, hinge moment, T-tail transfer;
the **LRA beam model at its determinate paths**; the summary report, PDF,
workbook, manifest and methods stamp; the **Streamlit UI outright** (the CLI is
the delivery path — parked M4-11b and the L-8 UX rows stay parked); F25-2.

---

## Open defects (index)

- #18 — Review 2026-08-10 unscheduled findings [Minor/NIT].
- **Derived ACRL wing case disagrees with the worked example's air load [Minor,
  found 2026-08-05 by M4-2's decision-7 gate].** With `wing_mass.cases` left empty,
  `wing_inertia.resolve_wing_cases` derives the wing cases from `envelope.critical`.
  Nz/Nx then reproduce the Appendix A figures closely for every ga6 condition, but
  the **ACRL** air-load point does not: SELECT's 23.349(a)(2) pick carries CL ≈ 1.30
  at 117.4 kt where the worked example (Ref 1 p217-221) enters CL 1.55 at 116 kt —
  a ~19% air-load difference for the same named condition. A derived ACRL case also
  carries `unbal_moment = 0`, since SELECT's condition does not name the unbalanced
  rolling moment (it comes from AILERON, Ch 13). **Only the derived route is
  affected** — every shipped example enters its cases explicitly, and explicit
  always wins — so no oracle or deliverable moves today. Decide which point ACRL
  should name (and where the rolling moment comes from) before the derived route is
  recommended for anything but a first pass. Pinned by
  `tests/test_wing_case_derivation.py::test_the_acrl_divergence_is_the_documented_one`,
  which fails if the two ever start agreeing — at which point close this and make
  the assertion an equality.
- **ATR-42 example: seven balanced points sit above the stall CL at 25,000 ft
  [Minor, found 2026-08-05 by M4-5's stall-clamp closure].** In
  `examples/atr42_100.project.json`, MAN A / MAN C / AC ROLL at 25,000 ft carry a
  balanced CL up to **1.767 against a Mach-adjusted stall CL of 1.478** (+0.29).
  The local Mach is pinned exactly at MC = 0.4555, so `_balance`'s
  dynamic-pressure iteration cannot raise q any further and never brings CL back
  onto the stall line: the airplane cannot reach n = 2.5 at that altitude within
  its own Mach cap and CLmax. The loads reported at those points are therefore
  not physically attainable. Not a solver defect and not an oracle fixture — a
  property of that example's speeds/altitude set (or of the Mach-cap handling:
  arguably the balance should report such a corner as *infeasible* rather than
  returning an unconverged point). Decide which, then either fix the fixture's
  altitude list / CLmax or teach `_balance` to flag a Mach-capped non-convergence.
  Pinned by
  `tests/test_aero_curves.py::test_the_atr42_stall_exceedance_is_the_documented_mach_capped_one`,
  which fails if the count or the cause changes. The GA oracle and both concept
  fixtures close cleanly.
- **The WTENV structural CG envelope is entered independently of the item
  database on four fixtures [Minor, restated 2026-08-15 after Pri 5 / D-26].**
  `cg_outside_envelope` fires on `cessna_210`, `atr42_100`, `dhc8_dash8` and
  `concept_regional_jet`: each one's **all-up itemized loading** sits 15–22 in aft
  of its own `%MAC` aft limit (cessna 84.0 vs 69.5; atr42 417.7 vs 402.1; dhc8
  420.4 vs 398.8; RJ 619.4 vs 593.8). Pre-existing and unchanged in set by D-26 —
  which corrected the *cases* to the database and left the *envelope* alone — but
  it is the third symptom of the same root cause, and now the conspicuous one:
  the fixtures' `envelope.fwd/aft_gross_pct_mac` were entered from a type's
  published envelope rather than derived from the loadings the database can
  produce. Warned in CI, so nothing is silent. Closing it means either deriving
  the fixtures' limits from their own loading extremes or accepting the entered
  limits and saying which loadings they exclude. Pairs with the fixture aero-data
  row (Pri 10, the fixture-data pass) as fixture-input hygiene.

---

## Open design decisions requiring user input

- [ ] **D-5 — Appendix B twin fixture (blocks parked L-9).** The swept (C7) and
  ONENGOUT (C9) printed oracles want the 10-place twin turboprop as a fixture,
  but Appendix B is **not in the bundled PDF**. *Can the user supply a legible
  Appendix B or the original `.INP`/`.OUT` files?* Until then
  `examples/twin_turboprop.project.json` can't be built and these oracles stay
  blocked. **(Reviewed 2026-07-20: keep blocked as-is.)**

D-1 … D-18 (all but D-5) are answered and recorded in
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md).
