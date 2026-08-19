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
design notes per step (open ones here — 09/11/12/19/21/24; shipped ones rolled
to [`../40_history/`](../00_INDEX.md#40_history--historic-record) at each cut); architecture
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

**Where things stand (2026-08-17):** **0.6.0 cut 2026-08-17** (`v0.6.0`,
schema v53) — the ground/landing families, the governing SF table, discrete
control surfaces, the LRA beam model, the `CgCase` loading, wing-tank fuel
separability and one owner for every constant; every shipped fixture assembles
balanced flight and ground cases and the lateral cases carry fin-only aero.
The fixture-data pass (#9, Pri 1) shipped in full on 2026-08-17
(`changes/fixture-data-pass.*`, `changes/fixture-cg-datum-reconciliation.*`, D-27):
entered tail planforms, the ga6 fin-root pin and body outline, and the fixture CG
datum reconciled with the flight cases pinned to the WTENV limits; note 19 §10.2
(i)–(ii) are done. **L-7 shipped 2026-08-17** (`changes/l7-lateral-body-aero.*`): the lateral cases can carry the wing-body sideslip term, off by default, and state it either way. Band A of the table below is the **0.7.0** scope (re-cut 2026-08-17,
[`../50_reviews/2026-08-17_backlog_review_0_7_0.md`](../50_reviews/2026-08-17_backlog_review_0_7_0.md)).
Reference-authority hierarchy: (1) `.BAS` listings + Appendix A printed output,
(2) User's Guide CFR quotes (Jan-1994), (3) Code-manual 1990 prose.

---

# Priority table (re-cut 2026-08-17 after the 0.6.0 cut — the single order of work)

**Re-cut 2026-08-17 (user, from
[`../50_reviews/2026-08-17_backlog_review_0_7_0.md`](../50_reviews/2026-08-17_backlog_review_0_7_0.md),
BR-1…BR-13).** Band A is now the **0.7.0** scope: the fixture-data pass first
(it carries the `ga6_normal` body outline the headline needs and closes the
WTENV-envelope defect), then **L-7 lateral body aero as the headline** (**shipped 2026-08-17**, note 19 rev. 3, schema v54; `changes/l7-lateral-body-aero.*`) — then the hub thrust card (**shipped 2026-08-17**, issue #10, tier M; note 21's carve-out on L-7's v54 field, `changes/hub-thrust-force.*`), the combined station envelope (**closed
2026-08-18 as decided-against**, decision **D-28**, `changes/no-combined-station-envelope.*`:
flight and ground fuselage cases are assessed with different internal-pressure
companion cases, so no envelope over both is supportable from a tool that
excludes pressurization — the two families stay separate deliverables and the
ground family's own missing per-station view is filed as **#31**, band B),
the recorded decisions (the gust-shape study **merged** into them: reusing
Schrenk is inside the Schrenk band by construction, so it is a decision, not
work; #12 closed into #13), and the **GUI review** (#29) the user asked for,
which re-opens the UI freeze to the extent its findings justify. Nothing was
promoted from `02_parked.md`; the aileron increment stays in band B; band C is
unchanged. Schema: the freeze is lifted for exactly L-7's additive hop; anything
else rides it or waits. Cut **0.7.0 when band A is empty**.

**Previously re-cut 2026-08-16 (user, from
[`../50_reviews/2026-08-16_scope_and_deficiency_review.md`](../50_reviews/2026-08-16_scope_and_deficiency_review.md)).**
The review sorted every row against the **base method's own error bar** rather
than by mission trace alone, and three things changed: (1) **band A is now the
whole of 0.6.0** — the first-order defects in shipped output, the units and
gate gaps, and the code-health items that make every later session cheaper;
the release is cut when band A is empty and **nothing in band B holds it**;
(2) **step 14 is descoped** from "real stiffness" to a `PBAR`/`MAT1`
pass-through (§2.3 of the review; shipped 2026-08-17 as consumer-*editable*
per-family cards, no input path) — the indeterminate-path half is parked;
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
- *2026-08-16 — schema freeze through 0.6.0* (held: one hop, v53). *2026-08-17
  — 0.7.0:* lifted for exactly **one additive hop**, L-7's lateral inputs
  (off by default, note 19 L-7.3); any other field change in 0.7.0 rides that hop
  or waits for 0.8. v47 → v52 in nine days is the churn the rule answers.

> **Removal rule (hard requirement, restating the lifecycle rule).** Once a
> step is complete it **SHALL be removed** from this table and this file in the
> same session, with its tiered closure trail. Renumber the remaining rows
> freely — priorities are an order, not IDs.

| Pri | Item (detail below / in its plan) | What ships | Tag | Tier / effort | Depends on |
|---|---|---|---|---|---|
| **A — 0.7.0: the lateral term the base method is missing, the fixture data it needs, the recorded decisions, and the GUI review (review BR-2…BR-7, BR-11)** ||||||
| 1 | Decisions, not effort: derived-`ACRL` air-load divergence (which point `ACRL` names); ATR-42 Mach-capped stall exceedance (`_balance` reports an infeasible corner rather than an unconverged point); **gust spanwise shape = Schrenk** (merged from #12: the gust-vs-manoeuvre shape difference is inside the Schrenk band by construction — recorded, not worked) (#13) | Three recorded decisions; the first two are pinned by test today | V | S / S | — |
| 2 | **GUI review** — the Streamlit UI against the 0.6.0 deliverables: page order vs `workflow.py`, unit toggle/labels conformance, the ground/gear and LRA-model pages, CLI-vs-UI delivery gaps, plan 03 status; body of record in `50_reviews/`, findings filed as issues (rule 5), re-cut follows (#29) | The UI freeze re-opened to the extent the findings justify — a reviewed list, not a rework | V | S (review) / M | — |
| — | **Cut 0.7.0** when band A is empty (RELEASE_PROCESS §2 cadence rule) | | | | |
| **B — 0.8+: capability that waits for a consumer (review BR-8)** ||||||
| 3 | The aileron's own lift increment is not distributed (#14) | `ACRL` wing cards gain the aero half of the couple (~70 % span); the schema fields shipped v52 and wait for data and a consumer | V | L / M | only if a consumer sizes to `ACRL` |
| 4 | Ground-case fuselage station distribution — the ground family has no per-station view *(from the #11 closure, D-28)* (#31) | Per-station shear/bending/torsion for the ground family on the fuselage beam, its own envelope beside the flight one and never merged with it, each station naming its ground case | V | L / M | a frame-sizing consumer; design note first |
| **C — maintenance and hygiene, when the module is next touched (review 2026-08-16 §5.2; BR-9)** ||||||
| 5 | Export deck-writing primitives out of `sbeam_bridge.py` (CH-4) (#15) | `_fmt`/`_sf_str`/`_stamped`/`_MAT1_*`/`_PBAR_*` in a shared module; the four private cross-imports gone | V | S / S | — |
| 6 | Dead code (CH-5) (#16) | Delete `write_balanced_deck`, `write_conm2_fragment`, `write_mass_check_deck`, `all_checks`; demote the ~12 no-consumer public names | V | S / S | — |
| 7 | Calc-side function size (CH-8) — `build_lra_model` (336 lines), `landing_reactions` (200) (#17) | Split when touched; **the view functions wait for the GUI review (#29)** | V | S / S | — |
| 8 | Review 2026-08-10 unscheduled findings m3–m13, m15–m18 + NITs *(defect sweep)* (#18) | Swept opportunistically (practice 4) or promoted individually | V | S / S–M | — |
| 9 | mypy strictness ratchet — stage 2 `export/`, stage 3 `modules/` *(design note 27 ST-3; detail below)* (#19) | `sloads.export.*` then `sloads.modules.*` added to the `[[tool.mypy.overrides]]` list and narrowed to zero under ST-4 (no `ignore`, no `Any` widening, no `cast`); then `warn_return_any`/`disallow_any_generics` toward `--strict`; `UP` on when 3.9 leaves the matrix | V | S / S per stage | — |

**Frozen (review §3) — no further investment; tests and gates kept; touched
for defects only:** the FAR 23 core; the balanced assembler + handedness;
CONM2/MASSSET export; the sbeam round-trip harness; the ground/landing
families + gear report; the governing safety-factor table (Layer 2 parked);
distributed empennage loads, control surfaces, hinge moment, T-tail transfer;
the **LRA beam model at its determinate paths**; the summary report, PDF,
workbook, manifest and methods stamp; the **Streamlit UI — pending the 0.7.0
GUI review (#29)**, whose findings decide what re-opens (the CLI is the delivery
path — parked M4-11b and the L-8 UX rows stay parked until then); F25-2.

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
  balanced CL up to **1.767 against a Mach-adjusted stall CL of 1.478** (+0.29)
  (2026-08-17, D-27 limit-point cases: 9 of 300 points, worst `MAN A` at
  `fwd gross`, +0.27 — full gross weight at 25,000 ft; same cause).
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
