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
design notes per step (open ones here — 09/11/21/24/32/34/35; shipped ones rolled
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

**Where things stand (2026-08-25):** **0.7.2 is cut** — `v0.7.2`, 2026-08-25,
schema v55 unchanged (release-cut block in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)).
Defect-only by construction: the seven `b`-class items of the C210 build review
(#76/#81/#82/#83/#84/#85/#86), closed 2026-08-24, plus the two first-order
defects the code review of the oracle GUI found inside eight lines of one
function (#88 — the row counter that deleted entered rows with no confirmation
and attached a blank CG case that stopped the flight envelope) and the **narrow
half of #71** with it (`ZeroDivisionError` out of the not-ready catch, which is
what hid it). The cut carried the re-cut of this table for the two GUI
milestones that follow
([code review 2026-08-24](../50_reviews/2026-08-24_oracle_gui_code_review.md)).
**Band A retired with the cut; band B is the milestone in flight — cut 0.8.0
when band B is empty.** Before it: **0.7.1 cut 2026-08-23** (`v0.7.1`, schema
v55 unchanged) — the 0.7.0 beta tested by building a Cessna 210 from blank in the
oracle GUI ([build review](../50_reviews/2026-08-23_c210_oracle_gui_build_review.md)):
51 findings, the two `a`'s fixed in-cycle (**none surviving**, so 0.8.0 keeps its
planned content), the whole-project results zip shipped, and seven `b`'s
(#76/#81/#82/#83/#84/#85/#86) carried to **0.7.2**. Before it: **0.7.0 cut 2026-08-23** (`v0.7.0`,
schema v55; release-cut block and delta baseline in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md) /
[`../40_history/36_verification_baseline_0.7.0.md`](../40_history/36_verification_baseline_0.7.0.md))
— the oracle GUI beta, L-7, the hub thrust, the fixture-data pass, the
derived-scalar consolidation and the 2026-08-20 review's MAJORs; band B
(the main-GUI review #29, the docs/CI sweep #46, the beta's known issues
#67–#74) is the 0.8.0 plan, awaiting its re-cut. Before it: **0.6.0 cut 2026-08-17** (`v0.6.0`,
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

# Priority table (re-cut 2026-08-26 — the single order of work)

**Re-cut 2026-08-26 (owner, in session).** Band B is unchanged in content;
this re-cut sets its **closure order** and renumbers the whole table densely
(a re-cut owns the table). Three rulings:

1. **The 0.8.0 order is dependency-driven:** #99 first (small,
   self-contained), then #97 (the collapsed-override widget, the registry
   `derived_from` link and its drift guard — the shared mechanism #95
   consumes), then #98 (its C210-29 seed half now lives at #97, so it follows
   rather than re-touch the same pages), then #95 (needs #97's `derived_from`;
   its re-shaped table is where C210-26's caption lands), then #100's
   implementation, then #94 (the text-only residue, written against the
   shipped mechanisms so no caption describes a page that then changes), and
   **#96 last** — the guide's screenshots and generated field tables capture
   finished pages (owner ruling, this session). **#100's design note is the
   band's first act** (rule 1: AGREED before code), drafted while #99/#97 are
   worked, so the tier-L row is never the long pole.
2. **#92 is ruled (b) — re-aimed at the coverage leg.** The clause's
   thresholds are written against the local command, which the 2026-08-26
   re-measurement shows already passes them; the cost is real only under CI's
   `--cov` leg on the push to `main`. The row stays band D with its
   done-condition rewritten against that leg — not closed as no-longer-tripped,
   because the whole-pipeline-per-assertion shape is confirmed and the
   refactor is small.
3. **#78 and #29 stay B2/0.9.0 with their `band:B` labels** — the milestone,
   not the label, is what separates B from B2 (#29 carries `band:B` the same
   way), so no label move is made.

# Previously re-cut 2026-08-24

**Re-cut 2026-08-24 (owner, from
[`../50_reviews/2026-08-24_oracle_gui_code_review.md`](../50_reviews/2026-08-24_oracle_gui_code_review.md)).**
The release themes are re-set by the owner: **0.8.0 — oracle-GUI development**
(it was "the main-GUI review completed"), and a new **0.9.0 — main-GUI
development and bug correction**, which is where #29 and its findings now land.
1.0.0 is unchanged. Four rulings govern the placement:

1. **0.7.2 admits defects with a first-order effect on shipped output, at any
   size** — presentation, UX and capability wait. One row qualified (the row
   counter); the narrow half of #71 came with it because it is what made the
   defect invisible.
2. **Rows are placed by fix site.** Work whose implementation is in the shared
   `app_shell/` lands in 0.8.0 with the oracle work even where the main GUI
   benefits — so **#80** (sidebar Tools, one shared implementation) and **#70**
   (the shell's unit radio) are 0.8.0 rows, not 0.9.0 ones. **#79**
   (flutter-clearance removal) and **#46** (docs/CI sweep) are neither GUI; both
   stay in 0.8.0 rather than slip two milestones.
3. **A row that genuinely has two halves is split at the seam**, not deferred
   whole: **#78** and **#21** each keep an oracle half in 0.8.0 and a main-GUI
   half in 0.9.0, as their bodies already describe.
4. **The mission stays at 1.0.0**, behind both GUI milestones. Recorded as a
   choice, not a drift: the full-span balanced free-free airplane model and the
   concept-loads → sbeam loop — the deliverable §Mission above names first — are
   now two GUI releases away. The alternative (re-ranking mission rows against
   the GUI rows on merit) was offered and declined
   (review §5.4).

The parked rows the 0.9.0 theme promotes at #29's re-cut are named in its row
below rather than moved here early, so `02_parked.md` keeps their bodies until
the review that scopes them.

# Previously re-cut 2026-08-22 for the 0.7.0 beta

**Re-cut 2026-08-22 (user, from
[`../50_reviews/2026-08-22_backlog_review_0_7_0_beta.md`](../50_reviews/2026-08-22_backlog_review_0_7_0_beta.md),
BB-1…BB-10).** The 2026-08-20 band A emptied on 2026-08-22; before cutting,
the user re-scoped **0.7.0 as a beta release of the oracle GUI** — everything
that supports a *usable* oracle GUI is in. Band A is repopulated with four
rows: **#51** (the unkeyed half of `app/views/` — reproduced data loss on a
shipped example; the reopen comment of 2026-08-22 is the scope of record) with
**#44** pulled forward to land as the same pass (the fixes share their call
sites; `unit_number_input` stamps for its callers); **#45** promoted on a
measurement — 2 of the 14 oracle pages give a fresh project wrong "run the
pages before this one first" guidance for a slice their own form enters; and
**#52** pulled forward because both duplicate fields render side by side on
one oracle page each. Two amendments to the 2026-08-20 preamble: the
`app/views/` freeze lifts **for exactly #51/#44's call sites** (`key=` + the
boundary helper; layout/behaviour stays frozen pending #29), and the schema
freeze is lifted **for exactly one hop** — #52's v55 duplicate retirement with
its reconciling migration (ordering rule below). #50 closed as a duplicate of
#51. Nothing promoted from `02_parked.md` (BB-9: the L-8 GUI rows are
`app/views/`-only or below the criterion, with the numbers). A fifth row was
added at the user's direction after the review: a **pre-cut beta review** of
the oracle GUI's function end-to-end (the 2026-08-15 candidate-review
pattern), last, so the cut signal includes it by construction. Cut **0.7.0
when band A is empty**.

**Pre-cut beta review 2026-08-22 (#61, from
[`../50_reviews/2026-08-22_pre_cut_beta_review.md`](../50_reviews/2026-08-22_pre_cut_beta_review.md),
PB-1…PB-24).** The fresh-project journey on all 14 oracle pages, the
`oracle_app/` + `app_shell/` delta and the G1–G8 rot check found the
mechanics sound and the cut **not ready**: eight BLOCKS-CUT findings enter
band A as five rows — the oracle GUI's project
is not the project gate G5 tests (`mass` never produced, items untagged,
rotors and station tables outside the reduction; **closed #62, 2026-08-23**), blank-seeded selector and
code fields that silently change loads (**closed #63, 2026-08-23**), the stale project download
(**closed #64, 2026-08-23**), no
project name (every save overwrites the last; **closed #65, 2026-08-23**), and an engine-layout state
that saves a file the loader refuses (**closed #66, 2026-08-23**; band A empty — cut 0.7.0). Sixteen KNOWN-ISSUE findings go to band
B as rows 11–18 (release notes for 0.7.0; fixed in 0.7.x/0.8.0). The cut
signal is unchanged in form: **0.7.0 when band A is empty**.

**Previously re-cut 2026-08-20 (user, from
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
  *2026-08-22 — 0.7.0 beta:* lifted for exactly **one hop**, #52's retirement
  of the two duplicate entries (v55) with a migration that takes the owner's
  value and warns on disagreement; anything else rides that hop or waits.

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
| **B — 0.8.0: oracle-GUI development** ||||||
| 1 | **Oracle page placement moves and the validation/error-display pair** *(split from #94, owner 2026-08-26)*. The Geometry page grows an aileron/flap planform section beside the empennage forms, writing to the same `aileron_loads`/`flap_loads` slices — no schema move, the load pages keep their condition inputs (C210-37, owner-raised: "very similar information"); `engine_layout` re-tagged to Geometry — Step C5 configuration whose one calc consumer is WINGGEOM's engine stations, and the page set is registry-derived so the move is one field (C210-44, **owner directive**); a validation *error* when a FLIGHT case balances with `xtc`/`xtf` at 0/unset — a tail CP at the datum sign-flips the tail arm and runs clean — plus a `validation.py` cross-check when a CG case's `role` weight/CG contradicts its meaning (C210-21); the run-crash catch showing exception type + expandable traceback, not `str(e)` alone (C210-24) (#99) | Both sections render from the registry with no page spelling a step key; each validation case has a test that fails without the check | V | S–M / S | — |
| 2 | **The derive-by-default override mechanism — seven duplicated inputs** *(split from #94, owner 2026-08-26)*. Each is a field duplicating a value the project already holds, asked blank, with a silent fallback behind it: WTENV's four derivable copies plus `envelope.gross_weight` (C210-13); the per-set `stall_cl` pair (C210-15); `aero.surfaces[].taper_ratio` and `tip_ratio` — the 0.0 default silently produced the pointed-wing τ 0.206 against a 0.68-taper planform, ≈2 % on the wing slope M (C210-31, **owner directive**); `htail.aspect_ratio_wing` and `wing_lift_slope_per_rad` — a hand-entered 7.2 against the planform's 7.737 sat undetected until an off-GUI diff (C210-36); `full_down_aileron_deg` entered on two pages with no cross-check (C210-38); `flap_loads.gust_load_factor`, which the envelope helper already computes (C210-39, **owner directive**); the engine weight/CG/LIMNZ linkage, step 2 after #69 shipped step 1 (C210-41, **owner directive**); and — **split from #98 on 2026-08-26 (owner)** — seeding `aero.surfaces` one row per lifting geometry surface, which is a derive-from-an-owner, not a caption: the invisibility half of C210-29 stays at #98 (C210-29 seed half) (#97) | One collapsed-override widget serving all seven — blank derives from the owner, a typed value overrides, the computed value shows beside the field (the C210-15 ruling) — plus a registry `derived_from` link naming each owner, and a **drift guard** failing on a duplicated input that has an owner but no link (rule 3: the mechanism is the single-source owner). MAC/XLEMAC resolution is already single-sourced at #80 (`derived_geometry.mac_reference`); what is open is the GUI half | V | M / M | — |
| 3 | **Fields the user must state are filtered off the oracle pages** *(split from #94, owner 2026-08-26)*. One cause — the `_SLDS`-origin filter in `field_registry.py` — and the same failure three times: `tab_loads.tabs[].surface` is hidden, so every tab silently defaults to h-tail though it picks the case-ID band, the exported component tag and the BL-vs-WL reading of `station_in`, and a rudder or aileron tab cannot be entered at all (C210-46, **owner directive**; the registry's :443 "the oracle GUI resolves surface selectors" rationale degenerated into a hardcode); the gear `carrier` (G-2, no default), `attach` trunnion node and `weight_lb` are hidden (:571/:579), so an oracle-built project cannot export ground cases and the page does not say so (C210-49); the empty `aero.surfaces` list renders as a bare rows counter with no trace of the AIRLOADS block it hides — `render_table` returns at `oracle_app/form.py:1051` before either row branch, so section slope, the TAU ratios, target CL and the twist/CDO(Y)/CM(Y) grids have no visible trace at zero rows; owner: "I can not find that anywhere" (C210-29 — **split 2026-08-26 (owner)**: the caption half is here, the seed half moved to #97, where deriving rows from an owner is already the mechanism) (#98) | Every field the user must state is rendered or its absence captioned, with a guard failing on a filtered field that has no default and no caption. C210-29's caption is emitted at that one early return and **generated from the row class's own fields** — hand-written it would be one caption per list, drifting the moment a field is added (the doc-currency failure mode); generated, every empty list in the GUI gains it, not just this one (rule 4) | V | M / S–M | — |
| 4 | **Geometry-page presentation family from the C210 build** — parametric wing not seeded from the planform (C210-1), derived `fuselage_length` editable (C210-2), duplicate owners in SELECT's tail block incl. the *governing* MTOW copy (C210-3), elevator/rudder area triples unchecked (C210-5), wing aero and mass data placed under Htail/Vtail (C210-6), geometry results in the load-case table shape (C210-8), the SELECT trio misplaced/duplicated — `wing_weight_lb` derivable from the items' wing-component sum with an undisclosed 0 → 0.09·MTOW fallback, `basic_airfoil_cm` a second owner of the section-cm quantity, the aileron deflection beside V-n inputs (C210-22); SELECT's checked-man Iyy and side-gust IZZ are undisclosed rod estimates (+34 %/+49 %) while WTONECG's database inertias exist, ≈10 % on the checked-man tail load (C210-25); the oracle results page renders SELECT in the stacked one-row-per-quantity shape (~150 rows for 27 conditions, per-case SF invisible on wing cases whose quantities are all non-loads) — **owner directive: one line per case, and every summary table so far revised** (C210-27) *(class c; build review 2026-08-23; **issue filed 2026-08-25** — this row was recorded as #77 at the 2026-08-24 re-cut and #77 is the grid/Tab defect, so the family had no issue at all: the same wrong number is in the two reviews' routing cells and the completed-development class-c list, which are dated records and keep what they said — read #77 there as this row)* (#95) | `wing_layout_from_surface` called from the oracle Geometry page with override; registry `derived_from` on the SELECT copies and a display-group so placement follows the quantity, not the dataclass; SE/SR derived from the hinge halves; a Quantity / Value / Units table when `has_load_case_data` is false — and, per the C210-8 extension (owner, Weight & Mass results), table shapes specific to the data shown: WTENV's envelope as (weight, station) rows, the CG-limit block as corner × (station, weight), paired "X weight / X station" values folded into one row per point; the oracle results page rendering SELECT (and any `CriticalCondition`-shaped output) through the shared `report.governing_loads_table` per component group — one row per case with a per-case SF column, the table Results Review already uses (M2-4), so a wiring change in `oracle_app/results.py`, not a new renderer — and **the exported CSV moves with it (owner, 2026-08-26)**: `results_to_rows`/`load_cases_to_rows` are shared by the screen (`oracle_app/results.py:194`) and the CSV writer (`sloads/io.py:1578`) behind the same `has_load_case_data` branch, so re-shaping one alone would print the same data two ways; this is an accepted **deliverable-format change** and the frozen Imperial digests move with it; C210-26's search-scope caption lands on the same table (C210-27 — upgrades the C210-8 data-shaped-tables direction to an owner requirement across every summary table) | V | M / M | #97 (`derived_from`); #73 closed 2026-08-25 |
| 5 | **TAILDIST states the aero state of each case it distributes** *(split from #94, owner 2026-08-26 — **tier L**, so it would otherwise gate twenty-five presentation findings behind a schema change)*. **Owner directive: "it would be useful in TAILDIST to record the alpha, beta and rudder or elevator deflections for each case"** — with the AVT/EFFECTV intermediates printed once per component; subsumes the SELECT v-tail no-intermediates observation. `CriticalCondition` (`models/results.py`) carries `beta_deg`/`cy_beta_fin`/`cn_beta_fin` and **no alpha field and no control-deflection field**, and the review records the upstream values as loose or absent for the checked-maneuver and gust conditions — so some are not merely unplumbed but uncomputed (C210-32) (#100) | A **design note merged at AGREED first** (rule 1): the contract change, which conditions can supply each quantity, what a condition that cannot supply one emits, and the closure/invariant gate. Then the fields on the contract with a drift guard, and every TAILDIST condition either stating its aero state or saying why it has none | V | L / M–L | design note (drafted first in the band; implementation lands here) |
| 6 | **Oracle form presentation — help and captions** — **PB-22 shipped 2026-08-25** (`changes/oracle-form-precision-and-labels.fixed.md`): per-`FieldUnit` widget precision owned by `sloads.units.display_format`, the hand-declared field-label table in `oracle_app/labels.py`, the `flight_loads.mn` basis, the longest-suffix unit match and the `kt (EAS)`/`(project)` label nits. **Split 2026-08-26 (owner):** the C210 family the 2026-08-24 re-cut folded into this row was 26 findings over 14 pages sharing nothing but a review date, so it is now five rows by *mechanism* — the derive-by-default overrides at #97, the fields filtered off the page at #98, the placement/validation pair at #99 and the tier-L TAILDIST aero-state contract at #100. **What is left here is the text-only residue**, eleven findings that change no behaviour: the summary's "OEW" figure sums EMPTY rows only, excluding the `minimum` pilot, and is relabelled "empty weight" (OEW = EMPTY + MINIMUM) (C210-12); `role` help stating the field assigns a slot and validates nothing (C210-14); chosen-speed help stating "blank = computed minimum; below-min values are raised", and `chosen_vf` captioned as the 23.345 design flap speed vs VFE (C210-16 — its MFC/V(FC) half is **moot since #79 removed flutter clearance from the tool 2026-08-26**; the withdrawal is registered in `02_approved_corrections.md`); xtc/xtf help carrying the full convention (flaps up ≈5 % tail MAC, flaps down ≈25 %) **and a computed suggestion beside the fields** from the empennage record (tail MAC from ST/span, Xtf = xt25, Xtc = xt25 − 0.20·MAC; user still types — owner chose suggestion over blank-derive), mn = coefficient-source Mach ~0.1 (not a design Mach), altitudes = cruise-set list with flaps at SL only (C210-20); the SELECT results' search-scope caption — "each critical condition is the governing case searched over the full V-n matrix: all loadings, CGs and altitudes" (C210-26; the theory-doc half already landed in `00_theory_sources.md`); `aero.surfaces.section_slope` help stating it is the 2-D section slope, not the aero page's AR-reduced C1 — entering C1 double-counts the AR reduction (C210-28); `wing_mass.cases` captioned "0 rows = the SELECT governing set; typed rows REPLACE it entirely" — a user adding one case silently drops the six verified conditions from the deliverable (C210-30; the additive mode is the fuller fix, noted at #95); a caption on the oracle Tail Loads page pointing at the spanwise deliverable's home — the main GUI Tail Span Loads page and the export decks — since `tail_span_loads` is correctly not an oracle page (OG-2, `bas=None`) but nothing says so where the owner looked (C210-33); `fuselage_mass.ref_waterline` captioned "reserved — not consumed by the current Ch 15 beam" rather than withheld — **owner ruling 2026-08-26**: it is inert (stored, round-tripped, displayed, consumed by nothing; reserved for M4-19/M4-21), and hiding it would be #98's own defect chosen deliberately (C210-34); blank Optional number inputs get a `placeholder` ("empty — type a value") so Streamlit's inert +/− steppers on a None-valued field stop reading as a locked widget (C210-42; the #35 blank-render contract unchanged); the sidebar's Save-to-disk button captioned with its fixed server-side target *before* the click ("writes `projects/<name>.project.json` beside the app; listed by Open") and Download captioned "your browser chooses the location" — the two are complementary routes but nothing says so and the pair reads as one mislabeled button (**owner: "save to disk button is there, but the user does not select the location"**, C210-48) *(build review 2026-08-23; PB-22 was this row's other half and closed as #73)* (#94) | Help and caption text only — no behaviour change, no schema change, no new mechanism | V | S / S | #95 (C210-26's caption lands on its table) |
| 7 | **Write the oracle GUI user guide** — design note 34 (`docs/30_future/34_oracle_user_guide_note.md`) moved to **AGREED 2026-08-26 (owner, in session)** with milestone 0.8.0; its four open questions were answered 2026-08-25 as UG-9…UG-12, but the note sat at PROPOSED for a day — the state that blocked note 32's step OG-B and would have blocked the first chapter here *(decisions UG-1…UG-12)* (#96) | A new `docs/60_guide/` section, one chapter per derived page in `sloads.workflow.oracle_steps()` order; per-page field tables **generated** from `field_registry.py` (prose never restates a units string or a default); re-runnable Playwright screenshots; two worked examples carried through every chapter — `ga6_normal` plus a new `examples/baron_58.project.json` (UG-9: Continental IO-550 keeps engine provenance continuous with the IO-520 examples, the TCDS gives citable MTOW/category/speeds/CG range, and wing-mounted engines make ENGLOADS and ONENGOUT real rather than degenerate). `10_standard/GUI_USER_GUIDE.md` is **not** superseded (UG-2). Acceptance gates G-UG-1…G-UG-6 | V | L / M | note 34; after every other band-B row (owner, 2026-08-26) |
| **B2 — 0.9.0: main-GUI development and bug correction** ||||||
| 8 | **GUI review resumption** — the five unswept sections (Flight, Other, Ground, Plotting, Export) against the 0.7.2 deliverables; findings filed at close (rule 5); re-cut follows (#29) | The review body completed; the UI freeze on `app/views/` re-opened to the extent the findings justify — a reviewed list, not a rework. **The anchor of 0.9.0**, and the re-cut that promotes the parked main-GUI rows: **L-8c** (Results Review omits the 8 folded modules' results), **L-8e** (uncovered input fields + UX nits), **L-8f** (display-only nits), **M4-11b** (the six F/E-complexity view functions) and the **mutation half of L-8d** — which the 2026-08-24 code review showed is a live mechanism, not a theoretical one (a retained widget beat a model grown underneath it; the row-counter fix closed that instance, the class stays open) | V | S (review) / M | 0.8.0 cut |
| 9 | **Seeding the item table from the estimate is destructive, and its rows are silently zero-stationed** — the oracle half shipped **2026-08-25** (`changes/weight-estimate-advisory.changed.md`): WTESTIMA's block captioned with what reads it (nothing — WTONECG and WTENV read the itemized data base) and the estimate shown beside the entered empty weight and MTOW with the delta. The **seed button itself already exists** and has since before the review (`app/views/weight_mass.py`, `weight_estimate.estimate_to_mass_items`, specified in `PROGRAM_SPEC.md` §WTESTIMA) — C210-9, issue #78 and the 2026-08-24 re-cut all recorded it as unbuilt because the whole C210 build was in the oracle GUI, which has no such button. What is open is the #62-class hardening the issue actually asked for *(C210-9, class c; build review 2026-08-23)* (#78) | Seeded rows **loudly incomplete** until positioned and tagged, rather than arriving at station 0 and untagged — `mass_distribution.infer_component` then lumps every one of them on the fuselage beam, the defect `fuselage_mass_warnings` already reports from the other side; and the button either merges, refuses, or says before the click that it **replaces every item already entered** (its caption says so today, after the fact). Main GUI, so it lands with the `app/views/` freeze lift | V | S–M / S–M | #29 |
| **C — 1.0.0: additional analysis capability (consumer-gated; design notes first)** ||||||
| 10 | The aileron's own lift increment is not distributed (#14) | `ACRL` wing cards gain the aero half of the couple (~70 % span); the schema fields shipped v52 and wait for data and a consumer | V | L / M | only if a consumer sizes to `ACRL` |
| 11 | **Wing fuel (and any tank/store band) is a point mass in WINGINER** — faithful to WINGINER.BAS lines 1180–1270 (every concentrated mass is a spanwise step; only the structure panel is spread), but a wet wing's fuel occupies a span band, so the point model concentrates the inertia relief and puts a fictitious jump in mid-span shear/torsion (**owner, C210 build: "fuel should be spread through the wing not just at one point mass location"**, C210-50, build review 2026-08-23) (#111) | `WingMassInput` gains a distributed-mass band (y_start, y_end, weight, chordwise CG) folded into the per-strip density `w[i]`, reducing exactly to today's point when the band collapses; Appendix A oracle case (concentrated gear only) untouched, lock holds. Interim (documented in the review): split the fuel into N concentrated rows across the tank span with the same centroid — root bending and total shear identical | V | L / M | design note first (physics/L) |
| 12 | Ground-case fuselage station distribution — the ground family has no per-station view *(from the #11 closure, D-28)* (#31) | Per-station shear/bending/torsion for the ground family on the fuselage beam, its own envelope beside the flight one and never merged with it, each station naming its ground case | V | L / M | a frame-sizing consumer; design note first |
| 13 | Mach-capped balanced points are published with their coefficients extrapolated past the fitted stall alpha, and nothing says so *(from the #13 closure, D-30)* (#32) | A derived past-fit marker wherever a per-point quantity is published (BALLOADS' 300 rows first); rows stay published and marked, never withheld; no schema field — the marker reads `EnvelopeResult.is_clamped`, the owner #33 left (2026-08-22), rather than re-deriving the point's CL against its Mach-adjusted stall CL; the two are pinned to name the same rows | V | M / S–M | — |
| 14 | **Certification basis / case manifest** *(review 2026-08-20 §6 rank 7)* (#47) | The per-condition coverage matrix as a deliverable, so the next FAR 25 case lands against a stated basis rather than a blind matrix | V | L / M | design note first |
| **D — maintenance and hygiene, when the module is next touched (review 2026-08-16 §5.2; BR-9)** ||||||
| 15 | Export deck-writing primitives out of `sbeam_bridge.py` (CH-4) (#15) | `_fmt`/`_sf_str`/`_stamped`/`_MAT1_*`/`_PBAR_*` in a shared module; the four private cross-imports gone | V | S / S | — |
| 16 | Dead code (CH-5) (#16) | Delete `write_balanced_deck`, `write_conm2_fragment`, `write_mass_check_deck`, `all_checks`; demote the ~12 no-consumer public names | V | S / S | — |
| 17 | Calc-side function size (CH-8) — `build_lra_model` (336 lines), `landing_reactions` (200) (#17) | Split when touched; **the view functions wait for the GUI review (#29)** | V | S / S | — |
| 18 | Review 2026-08-10 unscheduled findings m3–m13, m15–m18 + NITs *(defect sweep)* (#18) | Swept opportunistically (practice 4) or promoted individually | V | S / S–M | — |
| 19 | mypy strictness ratchet — stage 2 `export/`, stage 3 `modules/` *(design note 27 ST-3; detail below)* (#19) | `sloads.export.*` then `sloads.modules.*` added to the `[[tool.mypy.overrides]]` list and narrowed to zero under ST-4 (no `ignore`, no `Any` widening, no `cast`); then `warn_return_any`/`disallow_any_generics` toward `--strict`; `UP` on when 3.9 leaves the matrix | V | S / S per stage | — |
| 20 | **Whole-pipeline-per-assertion tests, re-aimed at the coverage leg** *(CR-D-6, filed from #46; hygiene; **ruled 2026-08-26 (owner): option (b)**. The 2026-08-26 re-measurement showed the trip figure was a coverage-instrumented run: plain `pytest`, the documented local command the clause's thresholds are written against, measures 62.1/62.7 s on two runs with 1 call over 16 s and none over 30 s — inside all three thresholds — while CI's coverage leg (`--cov=sloads`, `COVERAGE_CORE=sysmon`, the push to `main`) measures 265.6 s with 13 calls over 16 s and 8 over 30 s, reproducing the trip's 269 s; the test the trip named as the critical-path floor measures 2.3 s in isolation, so its 62.3 s was instrumentation cost, not the test. Not closed as no-longer-tripped: the shape the row names is confirmed and real, and the refactor is small — the row is re-aimed at the run that pays for it)* (#92) | The tests that re-run the whole pipeline once per assertion — `test_case_ids` plus the four deliverable-units/balance tests share that one shape — reduced to one pipeline run per example with the assertions reading its result, as the 2026-08-16 case was fixed. Done when the **coverage leg's** `--durations` shows the repeated-pipeline shape gone and its critical path inside the clause's own thresholds; the local command already passes them and stays the clause's datum. **No `slow` marker** — `00_program_overview.md` §Testing states why | V | S / S–M | — |

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
`app_shell/widget_keys.py` — and its unkeyed half shipped 2026-08-22, closing
#51's reopen as one pass with #44's unit-boundary rollout: that pass consumed
**the one carve-out from this freeze** — `key=` plus the boundary helper at
exactly those call sites, no layout/behaviour rework — so the freeze is whole
again; L-8d's mutation case stays parked); F25-2.

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
  silence — **closed 2026-08-22**: the nine are reported *clamped*, and #32's
  marker reads that owner). Pin:
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
