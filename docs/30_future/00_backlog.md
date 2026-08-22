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
(i)–(ii) are done. **L-7 shipped 2026-08-17** (`changes/l7-lateral-body-aero.*`): the lateral cases can carry the wing-body sideslip term, off by default, and state it either way. **The oracle GUI shipped OG-A…OG-F 2026-08-18/20** (note 32, `changes/oracle-gui-*`): a second
Streamlit front-end over the same calc, gates G1–G8. **The 2026-08-20 four-pass
critical review**
([`../50_reviews/2026-08-20_critical_review.md`](../50_reviews/2026-08-20_critical_review.md))
found no CRITICALs and ten MAJORs; band A of the table below is the **0.7.0**
scope (re-cut 2026-08-20).
Reference-authority hierarchy: (1) `.BAS` listings + Appendix A printed output,
(2) User's Guide CFR quotes (Jan-1994), (3) Code-manual 1990 prose.

---

# Priority table (re-cut 2026-08-20 after the critical review — the single order of work)

**Re-cut 2026-08-20 (user, from
[`../50_reviews/2026-08-20_critical_review.md`](../50_reviews/2026-08-20_critical_review.md)).**
The release themes are fixed by the user: **0.7.0 — the oracle GUI fully
functional**, plus the review's non-GUI MAJOR defect fixes (defects outrank
capability, rule 6); **0.8.0 — the main-GUI review (#29) completed and its
findings addressed** (#29 and every CR-D finding move wholesale out of the
0.7.0 band); **1.0.0 — additional analysis capability** (the former band-B
consumer-gated rows move there). Band A is ordered by fix dependency: the
shared shell first (both GUIs inherit CR-D-1), then the oracle form's persist
path, then one-owner-at-render (which closes the two top-ranked backlog items
riding it), then scope/nav polish, then the six non-GUI MAJORs grouped by
fix-site, with **#33 promoted from band C** per the review's §6 rank 2 (its
band-C placement under-ranked its blast radius). The review's MINOR/NIT
findings are one sweep row, worked with their modules (practice 4). **No
schema hop is needed anywhere in band A** — every fix is widget-, test-,
guard- or report-side; the schema freeze holds through 0.7.0. The Streamlit
freeze splits: `oracle_app/` + `app_shell/` are **open** for exactly the band-A
rows; `app/views/` stays frozen pending #29 (0.8.0). Cut **0.7.0 when band A
is empty**.

**Previously re-cut 2026-08-17 (user, from
[`../50_reviews/2026-08-17_backlog_review_0_7_0.md`](../50_reviews/2026-08-17_backlog_review_0_7_0.md),
BR-1…BR-13).** Band A is now the **0.7.0** scope: the fixture-data pass first
(it carries the `ga6_normal` body outline the headline needs and closes the
WTENV-envelope defect), then **L-7 lateral body aero as the headline** (**shipped 2026-08-17**, note 19 rev. 3, schema v54; `changes/l7-lateral-body-aero.*`) — then the hub thrust card (**shipped 2026-08-17**, issue #10, tier M; note 21's carve-out on L-7's v54 field, `changes/hub-thrust-force.*`), the combined station envelope (**closed
2026-08-18 as decided-against**, decision **D-28**, `changes/no-combined-station-envelope.*`:
flight and ground fuselage cases are assessed with different internal-pressure
companion cases, so no envelope over both is supportable from a tool that
excludes pressurization — the two families stay separate deliverables and the
ground family's own missing per-station view is filed as **#31**, band B),
the recorded decisions (**closed 2026-08-18**, decisions **D-29**/**D-30**/**D-31**,
`changes/recorded-decisions.*`: the derived `ACRL` point names SELECT's own pick;
the ATR-42's Mach-capped corner is ordinary stall-limited flight, with the real
finding — coefficients evaluated past their fit on nine published rows, no
governing load affected — filed as **#32**/**#33**; and the gust-shape study
**merged** in, reusing Schrenk being inside the Schrenk band by construction, so
a decision and not work; #12 closed into #13), and the **GUI review** (#29) the user asked for,
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
> same session, with its tiered closure trail. A closing change deletes **its
> own row and touches nothing else** — no renumbering (gaps in **Pri** are
> fine: it is the order at the last re-cut, not an ID; dense numbering returns
> only at a re-cut, which owns the whole table) — and rows never cite another
> row's ordinal (dependencies name the band or the `#N`), so two in-flight
> changes cannot conflict on this table (`DEVELOPMENT_PROCESS.md` §0).

| Pri | Item (detail below / in its plan) | What ships | Tag | Tier / effort | Depends on |
|---|---|---|---|---|---|
| **A — 0.7.0: the oracle GUI fully functional + the 2026-08-20 review's MAJOR defect fixes (CR-\* keys resolve in that review)** ||||||
| 1 | **Oracle GUI scope + nav polish** (CR-A-4, CR-A-5/CR-D-10, CR-A-9) (#37) | No Switch-to-Concept action in the oracle GUI (`banner=False` or warning-only); the shell's bare `except Exception` narrowed to `StreamlitAPIException`; `oracle_steps()[0]` hoisted | V | S / S | — |
| 2 | **SELECT keyed pick through `_extreme` + AST drift guard** (CR-B-1 `[MAJOR]`) (#38) | The 23.423(a) `BAL A` pick routed through `_extreme`; the §7 guard rebuilt as an AST walk (builtin `min`/`max` with `key=`); the `landing.py:596` tie-family sibling adopts the tie rule | E | M / S | — |
| 3 | **Concept→FAR23 reduction identity gated exactly** (CR-B-2 `[MAJOR]`) (#39) | `_assert_modules_identical` at `==` (bit-for-bit), not ±0.1 %; if any value fails exact equality, that divergence is investigated as its own finding | E | S / S | — |
| 4 | **23.361(b)(1) stoppage torque: formula closure + truncation basis** (CR-B-3 `[MAJOR]`) (#40) | A formula-closure assertion (`I·ω/Δt` summation) on the twin fixture; `int()` vs BASIC `INT()` verified against ENGLOADS.BAS (App. C p373 ff) at both sites and recorded in CONVENTIONS §5 | E | M / S | — |
| 5 | **Residual-gate exemption predicate: one owner** (CR-C-2 `[MAJOR]`) (#41) | `balance.residual_gate_applies(case)` owns the exemption (ground / lateral / 23.427(a)); report §6 and the Balanced Cases page compute `worst` over the gate-applicable family only, state the exempt families, drop the retired drag cause; the rendered §6 sentence pinned on a ground-assembling fixture; the stale page caption fixed | E | M / S | — |
| 6 | **Manifest conformance: LRA row + zip↔manifest gate + basis cells** (CR-C-1 `[MAJOR]`, CR-C-3 `[MAJOR]`) (#42) | The LRA model deck (and CLI `lra_loads.bdf`) manifested; a structural gate asserting the shipped zip's `namelist()` ⊆ manifest rows (the F-D2 class closed for good); `inertia_only.bdf`'s basis cell reads LIMIT-comparison-only and is pinned by text, not filename | E | M / S | — |
| 7 | `_balance` has no failure channel — both iteration loops return their last iterate with no signal *(promoted from band C: review 2026-08-20 §6 rank 2 — every V-n point, SELECT pick and balanced case consumes the unsignalled iterate)* (#33) | A converged/exhausted state on `_Balanced` covering **both** loops (rule 4), asserted in the closure tests; internal only, no published number and no schema field | V | S / S | — |
| 8 | **Review 2026-08-20 MINOR/NIT sweep** (CR-B-4/B-5/B-6, CR-C-4/C-5/C-6, CR-A-7/A-8; + close stale parked L-8a as shipped) (#43) | Swept with their modules (practice 4) or opportunistically; the CG-name mismatch (CR-B-4) first — it is the one silent-zero into a load path | V | S / S–M | — |
| — | **Cut 0.7.0** when band A is empty (RELEASE_PROCESS §2 cadence rule) | | | | |
| **B — 0.8.0: the main-GUI review completed and its findings addressed** ||||||
| 9 | **GUI review resumption** — the five unswept sections (Flight, Other, Ground, Plotting, Export) against the 0.7.0 deliverables; findings filed at close (rule 5); re-cut follows (#29) | The review body completed; the UI freeze on `app/views/` re-opened to the extent the findings justify — a reviewed list, not a rework; parked **L-8c** (Results Review omits the 8 folded modules' results) promotes at this re-cut | V | S (review) / M | 0.7.0 cut |
| 10 | **Unit-boundary rollout: `unit_number_input` everywhere** (CR-D-2 `[MAJOR]`) (#44) | The ~7 hand-paired views (and the data-editor grids) on the boundary helper; a no-op-Apply-in-SI bit-identity test per converted view; `GUI_design.md` §11's rollout claim made true; do together with **#51's residual (row 10a)** and what is left of parked **L-8d** (the mutation case) — the fixes interact | V | M / M | #29 findings order |
| 10a | **#51 residual: the unkeyed half of `app/views/`** (reopened 2026-08-22; scope in the issue's 2026-08-22 comment) (#51) | The 98 unkeyed project-seeded widgets keyed through `widget_key`; `test_widget_freshness.py`'s `_stamped` fails closed (a project-seeded input without `key=` is a failure, shell-owned widgets on an explicit allowlist); `_INPUT_CALLS` gains the missing input calls (`pills`, `segmented_control`, `file_uploader`, …); a behavioural guard that edits a widget *before* the load | V | M / M | rides #44 — `unit_number_input` stamps for its callers |
| 11 | **`workflow.requires` vs self-entered slices** (CR-D-3) (#45) | A `WorkflowStep.edits` (or equivalent) so self-sufficient pages stop showing "blocked"; a DAG-completeness guard: every `requires` is some step's `produces` or declared self-entered | V | M / S | — |
| 12 | **Docs/CI conformance sweep** (CR-D-4/D-5/D-6/D-7/D-8, CR-D-11) (#46) | The CI-matrix asymmetry stated where the docs claim otherwise (`DEVELOPMENT_PROCESS` §2 self-contradiction fixed); version-copy and phase-table drift fixed with the cheap guards; the one-way nav guard made two-way; the tripped runtime clause filed or re-stated; cspell gets a gate or the prose rule is dropped | V | S / S–M | — |
| **C — 1.0.0: additional analysis capability (consumer-gated; design notes first)** ||||||
| 13 | The aileron's own lift increment is not distributed (#14) | `ACRL` wing cards gain the aero half of the couple (~70 % span); the schema fields shipped v52 and wait for data and a consumer | V | L / M | only if a consumer sizes to `ACRL` |
| 14 | Ground-case fuselage station distribution — the ground family has no per-station view *(from the #11 closure, D-28)* (#31) | Per-station shear/bending/torsion for the ground family on the fuselage beam, its own envelope beside the flight one and never merged with it, each station naming its ground case | V | L / M | a frame-sizing consumer; design note first |
| 15 | Mach-capped balanced points are published with their coefficients extrapolated past the fitted stall alpha, and nothing says so *(from the #13 closure, D-30)* (#32) | A derived past-fit marker wherever a per-point quantity is published (BALLOADS' 300 rows first); rows stay published and marked, never withheld; no schema field — the marker is the point's own CL against its Mach-adjusted stall CL | V | M / S–M | — |
| 16 | **Certification basis / case manifest** *(review 2026-08-20 §6 rank 7)* (#47) | The per-condition coverage matrix as a deliverable, so the next FAR 25 case lands against a stated basis rather than a blind matrix | V | L / M | design note first |
| **D — maintenance and hygiene, when the module is next touched (review 2026-08-16 §5.2; BR-9)** ||||||
| 17 | **Two quantities are still entered twice, with nothing reconciling them** (note 33 DS-7; the class-C half of CR-A-2) (#52) | `speeds.mach_limit.shoulder_altitude_ft` vs `speeds.shoulder_altitude_ft`, and `geometry.empennage.vtail.airplane_length_in` vs the htail's: both members persisted, both read by their own consumer, so MC/MD can be computed at two different altitudes with no warning. Every shipped example happens to agree, which is why nothing has caught it. Removing either needs a **schema hop** with a migration that takes the owner's value and warns on disagreement — note 33 filed it rather than folding it in behind a no-hop change | V | **L** / S | the next schema hop (band A is hop-free by its own preamble) |
| 18 | Export deck-writing primitives out of `sbeam_bridge.py` (CH-4) (#15) | `_fmt`/`_sf_str`/`_stamped`/`_MAT1_*`/`_PBAR_*` in a shared module; the four private cross-imports gone | V | S / S | — |
| 19 | Dead code (CH-5) (#16) | Delete `write_balanced_deck`, `write_conm2_fragment`, `write_mass_check_deck`, `all_checks`; demote the ~12 no-consumer public names | V | S / S | — |
| 20 | Calc-side function size (CH-8) — `build_lra_model` (336 lines), `landing_reactions` (200) (#17) | Split when touched; **the view functions wait for the GUI review (#29)** | V | S / S | — |
| 21 | Review 2026-08-10 unscheduled findings m3–m13, m15–m18 + NITs *(defect sweep)* (#18) | Swept opportunistically (practice 4) or promoted individually | V | S / S–M | — |
| 22 | mypy strictness ratchet — stage 2 `export/`, stage 3 `modules/` *(design note 27 ST-3; detail below)* (#19) | `sloads.export.*` then `sloads.modules.*` added to the `[[tool.mypy.overrides]]` list and narrowed to zero under ST-4 (no `ignore`, no `Any` widening, no `cast`); then `warn_return_any`/`disallow_any_generics` toward `--strict`; `UP` on when 3.9 leaves the matrix | V | S / S per stage | — |

**Frozen (review §3) — no further investment; tests and gates kept; touched
for defects only:** the FAR 23 core; the balanced assembler + handedness;
CONM2/MASSSET export; the sbeam round-trip harness; the ground/landing
families + gear report; the governing safety-factor table (Layer 2 parked);
distributed empennage loads, control surfaces, hinge moment, T-tail transfer;
the **LRA beam model at its determinate paths**; the summary report, PDF,
workbook, manifest and methods stamp; the **`app/views/` UI — pending the
0.8.0 GUI review (#29)**, whose findings decide what re-opens
(`oracle_app/` + `app_shell/` are open for exactly the band-A rows; the CLI is
the delivery path — parked M4-11b and the L-8 UX rows stay parked until #29
closes; parked **L-8d**'s keyed data-loss half shipped 2026-08-21 as #51 —
`app_shell/widget_keys.py` — with #51 reopened 2026-08-22 for the unkeyed
half of `app/views/` (row 10a), and L-8d's remaining mutation case landing
with Pri 10); F25-2.

---

## Open defects (index)

- #18 — Review 2026-08-10 unscheduled findings [Minor/NIT].

Two long-standing entries left this list on 2026-08-18 at the issue #13 closure —
**decided, not fixed**, which is why neither survives here under the removal
rule. Both keep their pins; the decisions carry what the bodies used to:

- The **derived `ACRL` air-load divergence** is **D-29**: SELECT's own
  23.349(a)(2) pick is what the derived case names, the ~19 % difference against
  the worked example is accepted and stated, and an `ACRL` case used for sizing is
  **entered, never derived**. Pin:
  `tests/test_wing_case_derivation.py::test_the_acrl_divergence_is_the_documented_one`.
- The **ATR-42 Mach-capped stall exceedance** is **D-30**: nine of 300 points at
  25,000 ft are ordinary stall/Mach-limited flight, not a defect — `nz = n` and
  `n·W` are exact and the fixture is not edited to hide the corner. What is real
  is that CM/CD are evaluated 0.9–3.1 deg past their fit there, moving the
  published tail split by 3.3–44 % with **0 of the 9 SELECTed**, so no sizing load
  moves: filed as **#32** (mark the rows, band B) and **#33** (the solver's own
  silence, band C). Pin:
  `tests/test_aero_curves.py::test_the_atr42_stall_exceedance_is_the_documented_mach_capped_one`.
  The GA oracle and both concept fixtures close cleanly.

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
