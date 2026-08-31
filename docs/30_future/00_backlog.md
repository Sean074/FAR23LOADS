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
design notes per step (open ones here — 09/11/21/24/32/34/44; notes 35/36/37
shipped 2026-08-27 and rolled to
[`../40_history/`](../00_INDEX.md#40_history--historic-record) at the 0.8.0 cut); architecture
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

**Where things stand (2026-08-29):** **0.8.2 (band B3, the oracle technical
report — design note 44, AGREED 2026-08-29) is the milestone in flight**,
inserted deliberately ahead of 0.9.0: the oracle report is developed and agreed
section by section first, then becomes the starting point for B2's main-report
rebuild. **0.9.0 (band B2, main-GUI development, anchored by #29) follows.** Before it: **0.8.1 is cut** —
`v0.8.1`, 2026-08-29, schema v59 (release-cut block in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)).
The released-defect-correction milestone: a
patch band (**B1**) opened 2026-08-28 against defects the 0.8.0 cut shipped
(re-cut below): the attitude-1 airplane-datum sign error and the dual-frame
landing output that makes it visible (#133/#134, design note 38 AGREED
2026-08-28 — **both closed 2026-08-29**, along with #139, the application-point
defect that opening #134 uncovered, [note 39](../40_history/43_application_point_note.md)),
the blank-derive crash pair (#121/#122, **both closed 2026-08-29** — the loader
refuses a `null` where `None` is not a value, which is where #121's `float(None)`
came from), and **#132** — the
released distribution claims Python 3.9 while its own dependency floor refuses
to resolve there, which is why `main`'s full-matrix run is red at the tag —
closed on the milestone branch 2026-08-28, before the band was named; the branch
is renamed `dev/v0.8.1` rather than re-cut, so the fix reaches users at 0.8.1
instead of waiting for 0.9.0. Band B1 also carries the three documentation
items the 2026-08-29 independent review of `dev/v0.8.1` raised — **#141** (the
delivered CSV states neither the frame nor the application point — **closed
2026-08-29**: both words ride on the value, as `LoadValue.point` beside
`LoadValue.frame`, and the CSV states them in a `Frame` and an `Applied at`
column; schema v58 → v59, an additive identity hop), **#140** (the guide's
landing chapter still described the pre-0.8.1 output — **closed 2026-08-29**:
chapter 14 describes the shipped two-frame, three-wheel deliverable with its
application point, and `03_conventions.md` carries the frame statement it
leans on) and **#142** (the docs-hygiene pass — **closed 2026-08-29**: the
standard and theory docs state what is rather than how it got there, every
measured effect kept in the present tense as the evidence for its rule, and the
superseded `BETA(2)` register entry no longer contradicts its own banner) —
folded in from the 0.8.2 band they were first tabled as
(re-cut 2026-08-29), and, ahead of them, the two defects found the same day
diagnosing the GA6 V-n failure: **#143** (the oracle GUI attaches a phantom
zero-coefficient LANDING set on one stray touch and saves it into the project
file) and **#144** (the calc side launders a zero lift polynomial into a 400-trip
`SolverFailure` instead of refusing it by name), one defect class in two fix
sites — **both closed 2026-08-29**: the set refuses by name at the consumer, and
an Optional record block is created and removed by a named gesture rather than
attached by a stray touch. **#145 closed 2026-08-29** — the GUI release gate
proved boot, not use; the whole-GUI journey walk it adds found the same
attachment class live in `app/views/` (the #143 fix had reached `oracle_app/`
only) crashing Results Review and Export on three of the seven bundled
examples, and swept it, with the residue filed as a B2 row. **#146 closed
2026-08-29** — an oracle cell states its provenance and no gate re-derives the
rule it checks (P-1/P-2), with the bounded sweep naming `one_engine_out` as the
one load family whose gate reads the listing its port was written from.
**Band B1 retired with the 0.8.1 cut; cut 0.9.0 when band B2 is empty.**
Before it: **0.8.0 is cut** — `v0.8.0`, 2026-08-28,
schema v57 (release-cut block in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md)).
The oracle-GUI development milestone, 27 issues: the derive-by-default override
mechanism and its `derived_from` registry links (#97/#98/#95, note 36), the
oracle user guide with both worked-example appendices (#96, note 34), the
landing load factor entered as N (#123, note 37) with its HP-precedence sweep
finding (#124), and the four cut blockers of the
[production-release review](../50_reviews/2026-08-27_oracle_gui_production_review.md)
closed in-band (#126 the Tools station unit boundary, #127 the smoke gate boots
both front-ends, #128 a design note cannot claim unbuilt work, #129 the
container-width migration taken whole with the dependency ceiling policy
stated); the release states its maturity once (`4 - Beta`;
`app_shell.components.RELEASE_STATE`). **Band B retired with the cut; band B2
became the milestone in flight until the 0.8.1 patch band opened ahead of it
2026-08-28** (B2's anchor is still the main-GUI review #29, whose findings
drive the re-cut that owns the table).
Before it: **0.7.2 cut 2026-08-25** (`v0.7.2`, schema v55 unchanged) —
defect-only by construction: the seven `b`-class items of the C210 build review
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

# Priority table (re-cut 2026-08-29, second — the single order of work)

**Re-cut 2026-08-29 (owner, in session; the second of the day — the first, the
band B3 fold, is kept below).** Two defects found the same day diagnosing the
GA6 V-n failure — **#143** (the oracle GUI attaches a phantom zero-coefficient
LANDING set on one stray touch, and saves it into the project file) and **#144**
(the calc side launders a zero lift polynomial into a 400-trip `SolverFailure`
instead of refusing it by name) — **enter band B1 ahead of the documentation
rows**, and the table is renumbered densely (a re-cut owns the table). Nothing
else moves. Two rulings:

1. **They are one defect class in two fix sites, and both are fixed.** The
   phantom set is the writer; the missing refusal is why it presents as an
   opaque solver hang on a page the user never edited. This is the #121/#122
   binding of the 2026-08-28 re-cut applied again — rule 4 does not permit
   fixing the GUI that writes the set and leaving the guard that should have
   named it, and #144's refusal belongs at the consumer for **every** writer,
   not only this one. **#144 goes first:** it is the smaller, self-contained
   half, and landing it makes #143's repro produce a named `MissingInputError`
   to verify against instead of a 400-iteration failure.
2. **They rank ahead of #141/#140/#142 on rule 6, not on their tag** — a defect
   with first-order effect on shipped content outranks every non-defect row
   regardless of mission trace. #143 is the inverse of the #51 data-loss class,
   silent data *gain* that persists into a saved `.project.json` and takes
   Flight Envelope and SELECT down with it: a released-artefact defect of
   exactly the kind band B1 exists to correct. **The `app/views/` freeze is
   untouched** — #143's fix site is `oracle_app/`, open since band A, and
   #144's is `sloads/modules/flight_envelope.py`, which the frozen list admits
   for defects. No calc-math change: the guard is a refusal, and the GA6 oracle
   and twin closure suites are unmoved by it.

**Cut 0.8.1 when band B1 is empty, then 0.9.0 when band B2 is** — unchanged.

# Previously re-cut 2026-08-29 (the band B3 fold)

**Re-cut 2026-08-29 (owner, in session).** The three documentation items the
2026-08-29 independent review of `dev/v0.8.1` raised — filed the same day as
**#141**, **#140** and **#142**, and tabled that day as a separate **band B3
(0.8.2)** — **join band B1 and ship in the 0.8.1 cut**. Band B3 is dissolved and
the table is renumbered densely (a re-cut owns the table); nothing is added and
nothing is dropped. Two rulings:

1. **The band that corrects a released defect carries the documentation of that
   correction.** #133/#134/#139 changed the shipped landing output — a load
   change, a second frame, and a stated application point — and #141 (the CSV
   names neither the frame nor the point the force acts at) and #140 (the guide
   chapter still describes the primed-only output) are that change reaching the
   reader. Cutting 0.8.1 without them ships corrected numbers behind an output
   and a guide that describe the numbers they replace — which is the failure
   ruling 3 of the 2026-08-28 re-cut pulled #134 into the band to prevent.
   **#142** rides with them as one pass over the same documents (rule 4), not as
   a third errand.
2. **#141 is a tier-M row inside a patch band, and that is the 2026-08-28
   ruling 3 applied a second time, deliberately.** It emits no new load and no
   new quantity — only the frame and application-point words for values 0.8.1
   already ships — and its channel (a landing methods-preamble line, which the
   CSV already has, and/or an emitted point-name row) is decided in the issue.
   #140 and #142 are tier S and prose-only. **The `app/views/` freeze is
   untouched by all three**, so ruling 4 below stands unchanged.

**Cut 0.8.1 when band B1 is empty, then 0.9.0 when band B2 is.** There is no
0.8.2 band and no 0.8.2 milestone: the milestone list is 0.8.1 → 0.9.0 → 1.0.0,
which is what GitHub carries.

# Previously re-cut 2026-08-28

**Re-cut 2026-08-28 (owner, in session).** A **0.8.1 patch band (B1)** is opened
ahead of the 0.9.0 work and the table is renumbered densely (a re-cut owns the
table). Nothing is added and nothing is dropped: four rows move up out of B2 and
D. The band exists because 0.8.0 shipped defects, and
[`../10_standard/RELEASE_PROCESS.md`](../10_standard/RELEASE_PROCESS.md) §2 makes
a verified fidelity fix its own release signal. Four rulings:

1. **The band is the 2026-08-24 ruling 1 applied to a released version** —
   defects with a first-order effect on shipped output, at any size. **#133**
   (the attitude-1 airplane-datum resolution: +14 % / −19 % on exported ground
   `FORCE` cards) is the band's reason for existing and its own row already
   named this pull as the owner's option. **#121** and **#122** join it as one
   defect class, not two rows: both are a blank registry sentinel escaping as a
   raw `TypeError` out of a derive chain, both found the same day building the
   guide's baron_58, and rule 4 does not permit fixing one and leaving the
   other. Neither has an oracle consequence; both are unhandled crashes on a
   documented, meaningful input state in a shipped GUI.
2. **#132 is a 0.8.1 row, and was already built as one.** The 0.8.0
   distribution claims Python 3.9 while its own dependency floor refuses to
   resolve there — a defect *in the released artifact*, and the reason `main`'s
   full-matrix run is red at the tag. It closed on the milestone branch before
   this band was named; the branch is renamed rather than re-cut, so the fix
   reaches users at 0.8.1 instead of waiting for 0.9.0. It carries no row here
   (it is closed) and no history is rewritten.
3. **#134 rode the patch band, and that was a stretch taken deliberately.**
   §1's table calls a new emitted quantity MINOR, and #134 emitted three (both
   frames, the fuselage-axis angle, NR/NV/ND). Design note 38 GF-6 permits
   "with or after", so the split was available and was declined: shipping the
   corrected sign without the p232 tables would deliver a load change no output
   lets the reader see. Recorded here as an owner ruling so the release-cut
   block can restate it, not as an oversight. *(Closed 2026-08-29; it grew a
   fourth emitted quantity — p233's datum moments — because the primed set
   could not leave the CSV without them, and a schema hop, v57→v58, for the
   frame the value now names.)*
4. **The `app/views/` freeze does not lift for this band.** #121 moves ahead of
   #29 with its scope cut at the seam its own body already describes — the
   *survives it* half plus the rule-4 sweep — and the layout half stays with
   the review. **#29 remains the anchor of 0.9.0**; its dependency simply
   becomes the 0.8.1 cut. Cut 0.8.1 when band B1 is empty, then 0.9.0 when
   band B2 is. (The 2026-08-29 independent review's documentation rows joined
   band B1 rather than opening a 0.8.2 band — the issues carry the 0.8.1
   milestone.)

# Previously re-cut 2026-08-26

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
| **B3 — 0.8.2: the oracle technical report (design note 44; worked ahead of B2)** ||||||
| 24 | **Oracle technical report** — a clean, modern formal LaTeX report of the oracle GUI's analysis, generated from a new `oracle_app` page (amending note 32's exclusion list): derived section per `oracle_steps()` result step, computed pgfplots figures, `SUMMARY_REPORT.md` §2–§3 rules by citation, nothing recomputed. Built **one section at a time, owner-agreed per section** (OR-8), each agreement accruing in the new `10_standard/ORACLE_REPORT.md` with its guard (OR-9/G-OR-8). Decisions OR-1…OR-37, gates G-OR-1…G-OR-19: [note 44](44_oracle_report_note.md), AGREED 2026-08-29. **The milestone works under note 44 §6:** the solver and the existing oracle GUI are frozen additive-only (OR-13, manifest guard `tests/test_frozen_set.py`), a defect found in frozen code is filed and not fixed (OR-14), and findings triage to 0.8.2 / 0.8.3 / 0.9.0 by OR-15. **§7 settles the report file and page:** metadata is its own `<stem>.report.json` (`ReportSpec`) so one project yields many issues, sections are excluded with a stated reason rather than omitted, and provenance is human identity plus a versioned fingerprint over the oracle-consumed inputs (OR-16…OR-21). **§8 settles what the build produces:** an **issue package** directory per issue — `report.tex`, the stamped `report.json`, a copy of `project.json`, `MANIFEST.txt` and `data/<step_key>.csv` — whose data files are the document's source (`\input` fragments and pgfplots read them, so no drift is possible), self-containment read at package level, rebuild clobbering the revision and a new revision making a new directory (OR-22…OR-27). **§9 settles iteration 1:** the package directory is the spec's home (OR-28, superseding OR-24), the as-built stamp moves to `build.json` so the build never rewrites what the user typed (OR-30), *not yet implemented* becomes a third gap state distinct from excluded and absent (OR-32), and `MANIFEST.txt` is a full `SUMMARY_REPORT.md` §4.7 manifest (OR-35). **Iteration 1 shipped 2026-08-30**: the report page, `ReportSpec`, the fingerprint owner, the issue package builder and the front matter (cover, abstract, contents, figure and table lists, §1 Introduction), with the analysis sections present as stated placeholders. **§10 settles iteration 2:** section 2 groups four steps as subsections so G-OR-2 survives (OR-38), the document owns its section titles rather than borrowing the GUI's nav labels (OR-39), the V-n envelope is the polyline through FLTLOADS' produced points and not `build_vn_diagram`'s constant-CLmax curve, which is 8% low at the reference wing's STALL +N corner (OR-40), the `data/*.csv` externalisation of OR-23 is deferred to its own iteration with G-OR-15/G-OR-17 (OR-42), and the document is built from the oracle projection so no concept-mode field can reach it (OR-43). **Iteration 2 shipped 2026-08-30**: §2 Loads Configuration — geometry, weight and mass properties, structural design speeds and the flight envelope, with one V-n figure per loading and altitude block (#151) | The report page in `oracle_app`; `sloads/report/oracle_content.py` over the existing renderer; `.tex` (+ locally compiled PDF) from `ga6_normal` and `baron_58` in CI, byte-deterministic, ULT-marked, concept-content-free by guard. **The starting point for B2's main-report rebuild** | V | L / L | 0.8.1 cut; whole milestone is this one row |
| **B4 — 0.8.3: the empennage geometry model (after the note 44 OR-13 freeze lifts)** ||||||
| 25 | **Tail and control-surface geometry: enter the boundary lines, derive the summary parameters** — boundaries that are physically one line are entered several times with nothing checking the copies agree: `htail.trailing_edge` and `elevator.trailing_edge` are byte-identical, and the flap and aileron TEs lie exactly on the wing TE. Five independent entered lines per tail group (tail LE, tail TE, fixed-surface TE, control hinge, control LE); the control's TE is the parent's along the interior of its span, with an end-closure point where it departs (clipping to the LE span costs +1.00 % on the GA6 aileron). **Two steps:** group and mark the derived fields (`models/inputs.py`, tier M), then the boundary model (schema, tier L, design note first). Stabilizer **dihedral is deferred as unexercised** — 0 of 7 fixtures declare one — explicitly *not* a rule-6 park, but the per-surface reference plane is reserved now, since the fin already stores waterline as its span axis (#156) | One entered boundary per tail group, from which `wing_geometry.surface_properties` derives every area, span, MAC, MAC station and aspect ratio the h-tail and v-tail input blocks carry today as hand-entered scalars (9 of 17 and 9 of 15 fields); control travels and setting angle stay where they are. Appendix A's printed elevator/stabilizer/rudder figures become **predictions** rather than transcriptions once those surfaces are no longer entered | V | L / M | #151; the OR-13 freeze lifting at the 0.8.2 cut |
| **B2 — 0.9.0: main-GUI development and bug correction** ||||||
| 7 | **GUI review resumption** — the five unswept sections (Flight, Other, Ground, Plotting, Export) against the 0.7.2 deliverables; findings filed at close (rule 5); re-cut follows (#29) | The review body completed; the UI freeze on `app/views/` re-opened to the extent the findings justify — a reviewed list, not a rework. **The anchor of 0.9.0**, and the re-cut that promotes the parked main-GUI rows: **L-8c** (Results Review omits the 8 folded modules' results), **L-8e** (uncovered input fields + UX nits), **L-8f** (display-only nits), **M4-11b** (the six F/E-complexity view functions) and the **mutation half of L-8d** — which the 2026-08-24 code review showed is a live mechanism, not a theoretical one (a retained widget beat a model grown underneath it; the row-counter fix closed that instance, the class stays open) | V | S (review) / M | 0.8.1 cut |
| 8 | **Seeding the item table from the estimate is destructive, and its rows are silently zero-stationed** — the oracle half shipped **2026-08-25** (`changes/weight-estimate-advisory.changed.md`): WTESTIMA's block captioned with what reads it (nothing — WTONECG and WTENV read the itemized data base) and the estimate shown beside the entered empty weight and MTOW with the delta. The **seed button itself already exists** and has since before the review (`app/views/weight_mass.py`, `weight_estimate.estimate_to_mass_items`, specified in `PROGRAM_SPEC.md` §WTESTIMA) — C210-9, issue #78 and the 2026-08-24 re-cut all recorded it as unbuilt because the whole C210 build was in the oracle GUI, which has no such button. What is open is the #62-class hardening the issue actually asked for *(C210-9, class c; build review 2026-08-23)* (#78) | Seeded rows **loudly incomplete** until positioned and tagged, rather than arriving at station 0 and untagged — `mass_distribution.infer_component` then lumps every one of them on the fuselage beam, the defect `fuselage_mass_warnings` already reports from the other side; and the button either merges, refuses, or says before the click that it **replaces every item already entered** (its caption says so today, after the fact). Main GUI, so it lands with the `app/views/` freeze lift | V | S–M / S–M | #29 |
| 23 | **A no-op Apply still writes to the project — the residue after #145's sweep** — the whole-GUI journey test (`tests/test_gui_journey.py`) walks every bundled example through every `workflow.py` page pressing every Apply with nothing entered, and asserts the project byte-identical. #145 closed the *attachment* half of what it found (an Apply creating an `Optional` slice out of nothing, which crashed Results Review and Export on three shipped examples). Ten writes remain, carried as the file's `KNOWN_OPEN` list, each still asserted to reproduce so none can lapse into silence. **Silent gain:** `speeds.occupants` seeded from the WTESTIMA seat count on any Apply; `speeds.mach_limit` and `weight.envelope` attached with the form's defaults. **Silent loss** — a rebuild dropping what its form does not render, the same class #145 fixed in three other places: `speeds.wing_area_sqft` (the D4.4 Geometry read-through), `speeds.chosen_va`/`chosen_vf`, `weight.items[].wing_fraction` (not a column of the item table), and `engines[].max_cont_hp`/`takeoff_hp`/`hub_weight_lb` (the power fields render for reciprocating engines only, so a turboprop's entered 2000 hp is erased by its own page's Apply) *(filed 2026-08-29 from #145's journey walk)* (#148) | Each write either happens only on an edit to the field it writes, or is carried through the rebuild that drops it; `KNOWN_OPEN` empties as they close, and the journey test fails on the last entry's removal until the list goes with it. The engine-power erasure is the sharpest: it silently changes a shipped input on two bundled examples | V | M / M | #29 (the `app/views/` freeze lift) |
| **C — 1.0.0: additional analysis capability (consumer-gated; design notes first)** ||||||
| 9 | The aileron's own lift increment is not distributed (#14) | `ACRL` wing cards gain the aero half of the couple (~70 % span); the schema fields shipped v52 and wait for data and a consumer | V | L / M | only if a consumer sizes to `ACRL` |
| 10 | **Wing fuel (and any tank/store band) is a point mass in WINGINER** — faithful to WINGINER.BAS lines 1180–1270 (every concentrated mass is a spanwise step; only the structure panel is spread), but a wet wing's fuel occupies a span band, so the point model concentrates the inertia relief and puts a fictitious jump in mid-span shear/torsion (**owner, C210 build: "fuel should be spread through the wing not just at one point mass location"**, C210-50, build review 2026-08-23) (#111) | `WingMassInput` gains a distributed-mass band (y_start, y_end, weight, chordwise CG) folded into the per-strip density `w[i]`, reducing exactly to today's point when the band collapses; Appendix A oracle case (concentrated gear only) untouched, lock holds. Interim (documented in the review): split the fuel into N concentrated rows across the tank span with the same centroid — root bending and total shear identical | V | L / M | design note first (physics/L) |
| 11 | Ground-case fuselage station distribution — the ground family has no per-station view *(from the #11 closure, D-28)* (#31) | Per-station shear/bending/torsion for the ground family on the fuselage beam, its own envelope beside the flight one and never merged with it, each station naming its ground case | V | L / M | a frame-sizing consumer; design note first |
| 12 | Mach-capped balanced points are published with their coefficients extrapolated past the fitted stall alpha, and nothing says so *(from the #13 closure, D-30)* (#32) | A derived past-fit marker wherever a per-point quantity is published (BALLOADS' 300 rows first); rows stay published and marked, never withheld; no schema field — the marker reads `EnvelopeResult.is_clamped`, the owner #33 left (2026-08-22), rather than re-deriving the point's CL against its Mach-adjusted stall CL; the two are pinned to name the same rows | V | M / S–M | — |
| 13 | **Certification basis / case manifest** *(review 2026-08-20 §6 rank 7)* (#47) | The per-condition coverage matrix as a deliverable, so the next FAR 25 case lands against a stated basis rather than a blind matrix | V | L / M | design note first |
| **D — maintenance and hygiene, when the module is next touched (review 2026-08-16 §5.2; BR-9)** ||||||
| 14 | Export deck-writing primitives out of `sbeam_bridge.py` (CH-4) (#15) | `_fmt`/`_sf_str`/`_stamped`/`_MAT1_*`/`_PBAR_*` in a shared module; the four private cross-imports gone | V | S / S | — |
| 15 | Dead code (CH-5) (#16) | Delete `write_balanced_deck`, `write_conm2_fragment`, `write_mass_check_deck`, `all_checks`; demote the ~12 no-consumer public names | V | S / S | — |
| 16 | Calc-side function size (CH-8) — `build_lra_model` (336 lines), `landing_reactions` (200) (#17) | Split when touched; **the view functions wait for the GUI review (#29)** | V | S / S | — |
| 17 | Review 2026-08-10 unscheduled findings m3–m13, m15–m18 + NITs *(defect sweep)* (#18) | Swept opportunistically (practice 4) or promoted individually | V | S / S–M | — |
| 18 | mypy strictness ratchet — stage 2 `export/`, stage 3 `modules/` *(design note 27 ST-3; detail below)* (#19) | `sloads.export.*` then `sloads.modules.*` added to the `[[tool.mypy.overrides]]` list and narrowed to zero under ST-4 (no `ignore`, no `Any` widening, no `cast`); then `warn_return_any`/`disallow_any_generics` toward `--strict`; `UP` on when 3.9 leaves the matrix | V | S / S per stage | — |
| 19 | **Whole-pipeline-per-assertion tests, re-aimed at the coverage leg** *(CR-D-6, filed from #46; hygiene; **ruled 2026-08-26 (owner): option (b)**. The 2026-08-26 re-measurement showed the trip figure was a coverage-instrumented run: plain `pytest`, the documented local command the clause's thresholds are written against, measures 62.1/62.7 s on two runs with 1 call over 16 s and none over 30 s — inside all three thresholds — while CI's coverage leg (`--cov=sloads`, `COVERAGE_CORE=sysmon`, the push to `main`) measures 265.6 s with 13 calls over 16 s and 8 over 30 s, reproducing the trip's 269 s; the test the trip named as the critical-path floor measures 2.3 s in isolation, so its 62.3 s was instrumentation cost, not the test. Not closed as no-longer-tripped: the shape the row names is confirmed and real, and the refactor is small — the row is re-aimed at the run that pays for it)* (#92) | The tests that re-run the whole pipeline once per assertion — `test_case_ids` plus the four deliverable-units/balance tests share that one shape — reduced to one pipeline run per example with the assertions reading its result, as the 2026-08-16 case was fixed. Done when the **coverage leg's** `--durations` shows the repeated-pipeline shape gone and its critical path inside the clause's own thresholds; the local command already passes them and stays the clause's datum. **No `slow` marker** — `00_program_overview.md` §Testing states why | V | S / S–M | — |
| 20 | **The oracle form reaches into a `field_registry` private** — `oracle_app/form.py:709` calls `fr._locate(paths[0])` to answer "which dataclass does this path live on", the only access to a `sloads` private from either shell package (whole-surface scan). A public question asked privately: the registry should answer it *(production-release review 2026-08-27 §3.7)* (#130) | `field_registry` exposes the lookup publicly (`record_class_of(path)` or equivalent) and `row_class` calls it; the private stays private | V | S / S | when `field_registry` is next touched |

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
- **Non-load conditions carry `safety_factor = 1.5`** — geometry, mass properties and design speeds claim a limit-to-ultimate factor that does not apply to them. No number is affected (the boundary scales by units and quantity) but the text report prints `[ULTIMATE, SF=1.5]` above a geometry table. **Not frozen code**: the source is the `ConditionResult.safety_factor` dataclass default plus `safety_factors.GoverningTable.stamp`. Owner's ruling 2026-08-30 — non-loads have no safety factor: `Optional[float] = None` rendered "N/A", fixed at the data model so every consumer inherits it, a mixed condition keeping its factor and showing N/A against its non-load rows. Tier L, ~12 consumer sites, drift guard owed both directions. **#154**; note 44 §10; raised in the 0.8.2 GUI review.

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
