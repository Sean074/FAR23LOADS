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
A–C are a reading aid; the **Pri** column is the order. Item bodies stay where
they were — a defect promoted into the table keeps its body in *Open
defects*, and the [E]/[V] detail sections hold the rest.

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
- *2026-08-16 — effect-vs-error-bar rule.* A [V] physics or fidelity item is
  ranked only if its stated effect on a delivered load exceeds the base
  method's own uncertainty for that quantity (order 5–10 % on distributed
  loads, per the Schrenk / rigid-airplane / lumped-tail basis in
  [`../20_theory/00_theory_sources.md`](../20_theory/00_theory_sources.md)).
  Below that it is parked, with the number that parks it. Defects with a
  first-order effect on shipped content rank above every [V] item regardless
  of mission trace.
- *2026-08-16 — schema freeze through 0.6.0.* `SCHEMA_VERSION` moves once more
  before the cut (Pri 7's one additive field); no other hop. v47 → v52 in nine
  days is the churn the freeze answers.

> **Removal rule (hard requirement, restating the lifecycle rule).** Once a
> step is complete it **SHALL be removed** from this table and this file in the
> same session, with its tiered closure trail. Renumber the remaining rows
> freely — priorities are an order, not IDs.

| Pri | Item (detail below / in its plan) | What ships | Tag | Tier / effort | Depends on |
|---|---|---|---|---|---|
| **A — 0.6.0: defects in shipped output, contract gaps, and the cost-of-change fixes (review §1, §5.1)** ||||||
| 1 | Fin-root "fuselage-top" formula has no body-centreline datum *(defect, from T-8a)* | `z_centre(x_fin) + height(x_fin)/2` — a fin root that is not the wing root plus half a body; un-pins three fin roots and twelve lateral cases | E | M / S | — (`z_centre` shipped v52) |
| 2 | `atr42_100`/`dhc8_dash8` are modelled as conventional tails and are **T-tails** *(defect, from T-8a)* | Both fin decks gain the T7 tip transfer; the h-tail attaches at the fin tip. **Same digest wave as Pri 1**, carrying the structural negative-zero normalisation (`-0.000000E+00`, ~2,000 per balanced deck; tail span CSV `Fax`) so cosmetics never get a wave of their own | E | M / S–M | Pri 1 |
| 3 | Fixture aero-data quality — the `NMAA` `dCD` sign *(defect)* | A one-sided trusted-α window (clamp or flag) so no shipped balanced deck carries a positive `dCD`; **not** a re-derivation of the polars | E | M / S–M | — (recorded per fixture in `test_balance.py`) |
| 4 | L-8i — per-page LIMIT CSV units | Converted, unit-suffixed analysis-page downloads (four pages) — Imperial-in-SI is a units defect | E | S / S | — |
| 5 | M4-3(b) — turboprop gate as **enforcement** | Refuse (or caption) `one_engine_out` when the failed engine is not a propeller installation — `PROPELLER_ONLY_NOTE` becomes a gate, not a sentence; (a)/(c) parked | E | S / S | — |
| 6 | Hygiene batch *(one session)*: conventions findings (a)–(d); M4-23 duplicate sigma; **`RHO_SL`** for the seven `0.002378` literals (CH-6) and the stray lb→kg factor in `report/content.py` (CH-7); the three export silent defaults (CH-2: `sbeam_bridge.py` `hand`, `tip_transfer`, empty condition); direct tests for `coordinates.py`'s three tail transforms (CH-3); verify-and-retire the 427 lb fuselage-mass pin | Guards that are claimed to exist, exist; the D-19 failure class closed in the export namespace; one authority for σ and ρ₀ | E | S / S | — |
| 7 | Wing-tank fuel separability | Ends the same pounds riding both beams on the three fuel-in-wing fixtures — a `wing_fraction` on `MassItem` (or a second row) + the tie validator; **the freeze's one schema hop**; **not** plan 12 C1 | E | L / M | after Pri 1–6 |
| 8 | Step 14 **descoped** — `PBAR`/`MAT1` pass-through per LRA element family (was "real stiffness", L-1) | Consumer-supplied section properties written in place of the `_MAT1_E` placeholder; no physics, no gate beyond "the deck still solves"; the indeterminate-path half is parked | E | S / S | — |
| — | **Cut 0.6.0** when Pri 1–8 are closed (RELEASE_PROCESS §2 cadence rule; `[Unreleased]` already holds two unreleased schema hops) | | | | |
| **B — 0.7+: capability the base method is missing at first order, fixture data, and report polish (review §2.1)** ||||||
| 9 | Lateral body aero `Cy_β`/`Cn_β` (L-7) — design note in [`19_l7_lateral_body_aero_note.md`](19_l7_lateral_body_aero_note.md) (**proposed, awaiting agreement**) | Honest lateral `n_y`/`ψ̈` (today `ψ̈` over-stated 73–84 %, `n_y` under-stated 4–12 % — a missing term of the order of the one kept, not a refinement); DATCOM 5.2.3.1/5.2.1.1 makes it an **oracle** step | V | L / M | — |
| 10 | Fixture-data pass: empennage planform polylines **+** the WTENV envelopes entered independently of the item database (four fixtures) | Real taper in the tail card distributions instead of the `assumed` rectangle; CG limits derived from (or reconciled with) each fixture's own loading extremes | V | S / S | — |
| 11 | Thrust `FORCE` at the engine hub *(carved out of note 21; the seven-step wake plan is parked)* | One user-entered thrust per engine as a card on the LRA hub node the skeleton already has — what a wing with a wing-mounted engine needs from a loads tool | V | S / S | — |
| 12 | Combined flight + ground station envelope *(from step 10 decision G-9)* | Two-sided max/min per station over both families, each extreme naming its governing case | V | M / M | — |
| 13 | Gust spanwise-distribution decision | Study + recorded decision (Schrenk shape reused) | V | S / S | — |
| 14 | Decisions, not effort: derived-`ACRL` air-load divergence (which point `ACRL` names); ATR-42 Mach-capped stall exceedance (`_balance` reports an infeasible corner rather than an unconverged point) | Two recorded decisions; each is pinned by test today | V | S / S | — |
| 15 | The aileron's own lift increment is not distributed | `ACRL` wing cards gain the aero half of the couple (~70 % span); the schema fields shipped v52 and wait for data and a consumer | V | L / M | only if a consumer sizes to `ACRL` |
| **C — maintenance and hygiene, when the module is next touched (review §5.2)** ||||||
| 16 | Export deck-writing primitives out of `sbeam_bridge.py` (CH-4) | `_fmt`/`_sf_str`/`_stamped`/`_MAT1_*`/`_PBAR_*` in a shared module; the four private cross-imports gone | V | S / S | — |
| 17 | Dead code (CH-5) | Delete `write_balanced_deck`, `write_conm2_fragment`, `write_mass_check_deck`, `all_checks`; demote the ~12 no-consumer public names | V | S / S | — |
| 18 | Calc-side function size (CH-8) — `build_lra_model` (336 lines), `landing_reactions` (200) | Split when touched; **the view functions are under the GUI freeze and are not worked** | V | S / S | — |
| 19 | Review 2026-08-10 unscheduled findings m3–m13, m15–m18 + NITs *(defect sweep)* | Swept opportunistically (practice 4) or promoted individually | V | S / S–M | — |
| 20 | Split `40_history/00_completed_development.md` by era | Mechanical split + index file | V | S / S | after the working tree is committed |

**Frozen (review §3) — no further investment; tests and gates kept; touched
for defects only:** the FAR 23 core; the balanced assembler + handedness;
CONM2/MASSSET export; the sbeam round-trip harness; the ground/landing
families + gear report; the governing safety-factor table (Layer 2 parked);
distributed empennage loads, control surfaces, hinge moment, T-tail transfer;
the **LRA beam model at its determinate paths**; the summary report, PDF,
workbook, manifest and methods stamp; the **Streamlit UI outright** (the CLI is
the delivery path — parked M4-11b and the L-8 UX rows stay parked); F25-2.

---

# Item detail — mission path [E]

### [V] No lateral aerodynamic load exists but the fin *(new 2026-08-09, from plan 13 decision L-7)*
Nothing in the suite computes fuselage or wing side force in sideslip, so a B8a
lateral balanced case reacts the fin's load with inertia alone, and the two
lateral DOF err in **opposite directions**: `ψ̈` is **over-stated** (the missing
body couple is destabilizing and opposes the fin's) while `n_y` is
**under-stated** (the missing side force *adds* to the fin's), so the lateral
translational inertia is **not** conservative. Neither is the airplane's real
acceleration. In-band the magnitudes stay unknown — no shipped code computes
them, and only this item's DATCOM work makes them quotable. Stated in-band on
every lateral case (deck `$` header, case notes, UI) per plan 13 §5.6 —
**shipped with B8a-3, 2026-08-09**, as `balance.LATERAL_AERO_NOTE`, whose
direction claim was **corrected 2026-08-15** (the original said both DOF were
over-stated); the eight lateral cases now in every assembled deck each carry it,
so the caveat travels with the numbers rather than sitting in a document beside
them.

Closing it means the lateral analog of **M4-19**'s Multhopp/Nelson body aero —
`Cy_β` and `Cn_β` from the same slender-body integrand, lumped at the body
centroid like `fuselage-cm` or distributed once M4-19 gives it a carrier. The
sideslip angle is already available in three of the four v-tail conditions
(19.5°, 15°, and the gust case's effective β); `SUDDEN RUDDER` is rudder
deflection at zero sideslip and has no body side force to add. Pairs with M4-19
(parked 2026-08-16 — a lumped `Cy_β`/`Cn_β` needs no distributed carrier).
Tier L (new physics, no oracle → a stated closure gate). Effort: M.

**Design note (revision 2, 2026-08-15):**
[`19_l7_lateral_body_aero_note.md`](19_l7_lateral_body_aero_note.md) — proposed,
awaiting agreement, no code. Sourcing Digital DATCOM (USAF, public domain) made
the **whole lumped step** deliverable in one go and overturned three conclusions
of the first draft, which are marked as corrections in the note rather than
quietly replaced:

- The method is **DATCOM 5.2.3.1 / 5.2.1.1**, transcribed from the Digital
  DATCOM source, whose `K_N` chart data is bundled as `DATA` statements and whose
  `K_Rl` is closed form — so **no constant has to be invented**, and its 11
  sample cases with printed `CYB`/`CNB` make this an **oracle** step (+-0.1 %)
  rather than a closure-gate step.
- **`Cn_beta,body` is 2.3x Munk, not a fraction of it** (`+0.2026` vs `+0.0876`
  /rad on the RJ): Munk is an isolated body in ideal flow, while `K_N` correlates
  the wing-body combination whose interference Munk omits. The "reduction factor"
  premise of the first draft is void.
- **`Cy_beta` is reachable lumped** (`-0.0213`/rad, mostly the wing-dihedral
  term), so both halves of `LATERAL_AERO_NOTE` close, not just the yaw half.

Case effects on `concept_regional_jet` (the only lateral fixture with body
geometry — `ga6_normal` has none): `|psi_dd|` down 73-84 % on the two
rudder-neutral conditions, `|n_y|` **up** 4.1-12.0 %. Net `Cn_beta` =
`-0.257 + 0.2026 = -0.054`/rad: statically stable with 21 % margin. Two open
items and one filed defect (below) in §9-§10.

### [V] The aileron's own lift increment is not distributed *(new 2026-08-08, from B7)*
The assembled `ACRL` case applies the unbalanced rolling moment (FAR 23.349) as a
**lumped** free couple at the wing aerodynamic centre, because
`AileronLoadsInput` carries `area_fwd_hinge_sqft`/`area_aft_hinge_sqft` and **no
spanwise station** — there is nowhere to put a distributed increment. Decision of
record (user, 2026-08-08): lump it, because that reduces *exactly* to the
oracle-locked FAR 23 model, where WINGINER likewise carries only the inertia
reaction and never the aileron's own aero.

The reaction **is** distributed (the roll-acceleration relief, spanwise over
every mass), so the assembled wing does see a genuinely antisymmetric load; what
is missing is the aero half of the couple. Consequence for a consumer: `ACRL`
wing bending omits the aileron's differential lift, which acts near ~70 % span
and is therefore not negligible for sizing. Stated in the deck `$` header, the
case notes and the Balanced Cases page rather than left to be discovered.

Closing it means **new geometry input** — an inboard/outboard butt line on
`AileronLoadsInput`, entered for six fixtures, with no printed oracle to check
the resulting shape against — hence a step of its own: schema bump + migration,
a spanwise shape integrating to `UNB`, and a closure gate. Pairs naturally with
plan 09's spanwise work, which is already building strip integrators.
**Extension (2026-08-15, note 24 R-2 / F1):** the same butt lines are what the
LRA model needs to place the **aileron and flap as their own beams on the hinge
line**, so the schema addition should carry the T-17 shape in one go —
inboard/outboard butt line **plus** `hinges_span_in`/`actuator_span_in` on the
aileron and flap inputs — entered, never invented (no fixture gets any until the
data exists). Tier L. Effort: M.

### [V] Wing-tank fuel is not separable in the item database *(new 2026-08-08, found by the step-B1 wing tie)*
`mass_distribution.wing_mass_tie` asserts the two models of the same physical
wing agree: `Σ(items tagged wing) == 2 × (panel_weight_lb + Σ concentrated)`.
It holds exactly on `ga6_normal`, `cessna_210` and `concept_regional_jet`, and
fails on the three fixtures that hang fuel on the wing:

| fixture | gap | cause |
|---|---|---|
| `atr42_100` | 3,800 lb | `concentrated` "wing fuel" 1,900 lb/side |
| `dhc8_dash8` | 4,000 lb | `concentrated` "wing fuel" 2,000 lb/side |
| `concept_heavy` | 1,200 lb | `concentrated` "fuel" 600 lb/side |

The engine+nacelle half of the twins' concentrated model reconciles **exactly**
(atr42 `Engines (2)` 1780 + `Nacelles (2)` 600 = 2 × 1190; dhc8 2100 + 700 =
2 × 1400), as does the Dash 8's nacelle-mounted main gear since 2026-08-15
(`Main gear` 1200 = 2 × 600), so the fixtures were built consistently — the gap
is fuel alone. Each
airplane's wing-tank fuel lives inside an undivided `"Fuel to gross"` row, so the
item database cannot show it as wing mass while WINGINER also hangs it on the
wing. Consequence: that fuel is carried on **both** beams — inertia relief on the
wing and inertia load on the fuselage, for the same pounds.

Closing it means **splitting item rows into wing-tank and body-tank fractions**,
which is new fixture data with no oracle behind it — hence filed rather than
guessed. Options: a `wing_fraction` on `MassItem`, or separate rows. Either is a
schema change; the natural pairing is plan 12 **C1** (per-case itemization from
WTENV), which is already splitting the database per payload case.

Pinned, not hidden: `tests/test_mass_distribution.py::
test_the_unmodelled_wing_mass_is_pinned_per_fixture` asserts each gap to the
pound and goes red when it changes in either direction. Tier L (schema). Effort: M.

### [V] The five non-oracle fixtures do not close as tightly as ga6 *(new 2026-08-15, from Pri 5 / D-26)*
Bringing four fixtures into the balanced assembly for the first time exposed two
symptoms of one cause, both recorded per fixture in `tests/test_balance.py`
rather than absorbed by widening a gate:

| fixture | worst symmetric force residual | `NMAA` `dCD` at alpha ~ -13 deg |
|---|---|---|
| `ga6_normal` | 0.624 % | negative (correct) |
| `cessna_210` | 1.190 % | negative (correct) |
| `concept_regional_jet` | 1.506 % | negative (correct) |
| `dhc8_dash8` | 1.626 % | **+0.027** |
| `atr42_100` | 1.929 % | **+0.023** |
| `concept_heavy` | 1.990 % | **+0.040** |

Plan 11's acceptance 2 is a flat **1 %** on the pre-closure force residual, and it
was met when only `ga6_normal` and the RJ assembled. A positive `dCD` says the
wing strips carry more axial force than the whole airplane less tail, which cannot
be true of a real airplane; it appears on `NMAA` and only `NMAA`, the negative-g
corner, on the three fixtures with the crudest polars.

The ordering is the diagnosis: ga6 -- the one fixture whose aero and planform come
from a printed source -- is best by 2x, and the concept configurations are worst.
This reads as **fixture aero data**, not an assembly defect: every case still
closes exactly after correction, the pitch residual (the DOF that would expose a
mis-placed force) stays at 0.07-0.84 %, and the airplane-less-tail polar on the
three is a fit that was never meant to be evaluated 13 deg below zero lift.

Closing it means revisiting those fixtures' `aero_coeffs` sets against a stated
source, and deciding whether the trusted-alpha window is one-sided. Pinned by
`_FORCE_RESIDUAL_RATCHET` and `_DELTA_CD_POSITIVE_AT_TRUSTED_ALPHA`, both of which
go red if the spread widens or reaches a positive alpha -- which would be a
different and much worse thing. Tier M. Effort: M.

### [V] The empennage planform is derived, not entered, on every fixture *(new 2026-08-08, from T1)*
No shipped airplane carries an `htail`/`vtail` entry in `geometry.surfaces`, so
`tail_geometry.resolve_tail_planform` **derives a rectangular planform** from the
oracle-authoritative area and span — the same first-order derivation the
three-view has always used — and marks it `assumed`, which travels into the
result, the page, the CSV and the deck `$` header.

Quantified: the half-planform area centroid is `b/2` for the rectangle against
`(b/3)(c_r + 2c_t)/(c_r + c_t)` for a straight taper, falling toward `b/3` for a
pointed tip. A real tapered tail therefore carries its load **further inboard**,
so the derived planform is conservative in root bending — but the station-by-
station distribution it delivers is not the surface's own, which is what a
consumer sizing ribs and spars actually needs.

Closing it is **fixture data, not code**: enter LE/TE polylines for the six
airplanes' tails (validated against the scalars to 1 %, which is already
enforced). The code path is shipped and tested against a tapered *and* swept
planform. Tier S per fixture. Effort: S.

### [V] The fin-root "fuselage-top" formula has no body-centreline datum *(new 2026-08-15, from T-8a)*
`tail_geometry.fin_root_waterline`'s third branch is
`root_waterline_z + fuselage_height/2`, which reads `root_waterline_z` as the
**body centreline**. It is the **wing** root — the same substitution
`CONVENTIONS.md`'s body-drag row already refuses for D-1, and for the same
reason. The error stayed invisible while no fixture carried a `fuselage_height`
(the branch silently returned `root_waterline_z`); T-8a gave `atr42_100`,
`dhc8_dash8` and `cessna_210` a published fuselage outline, and since all three
are **high-wing** their wing root already sits near the body top, so the branch
now stacks half a body height above it: `atr42_100` 170 → 223.15 in,
`dhc8_dash8` 180 → 232.95, `cessna_210` 86 → 109.60. That is the fin's **roll
arm**, so it is first-order: `cessna_210`'s lateral `p_dot` moved by a factor of
2.6 (−28.99 → −74.59 deg/s²). The three fin roots and twelve lateral cases are
pinned to the formula's output, and the pins say so.

The fix is the datum the suite has never had: **note 24 R-4's
`FuselageSection.z_centre`** (waterline per section, defaulted from
`body_drag_waterline` and marked assumed) — **shipped v52 with step 12**
(`derived_geometry.fuselage_centreline` is its owner) — after which the branch
becomes `z_centre(x_fin) + height(x_fin)/2` and needs no wing quantity at all.
What remains is the formula change and its pin wave. Until then a project that
knows its fin root should enter `vtail_root_waterline_z`, which wins outright.
Tier M. Effort: S.

### [V] `atr42_100` and `dhc8_dash8` are modelled as conventional tails, and are T-tails *(new 2026-08-15, from T-8a)*
Both fixtures set `tail_type: conventional` with `h_tail_z: 0`, and both real
types have the horizontal tail **on top of the fin** — the fixtures' own
`xt25` 825 / `xv25` 820 and `xt25` 810 / `xv25` 805 are the tell. Consequence
today: their h-tail is reported as fuselage-attached (T-8a puts it at
`±10.9`/`±10.8` in of tail cone) when it should be a single fin-tip joint, and
their **fin decks carry no T7 tip transfer** — on a T-tail that is a missing
load, not an absent load path, and `tail_span` already says so in band for a
project that declares the layout. `concept_regional_jet` is the only shipped
fixture exercising either.

Not swept with T-8a deliberately: flipping `tail_type` switches on the T7
transfer, moves both fin decks and their lateral cases, and needs the fin root
those airplanes actually have (the row above) — the two are one change. Fixture
data plus a digest wave. Tier M. Effort: S–M. Depends on the fin-root datum row.

### [E] Step 14 — **descoped 2026-08-16** to a `PBAR`/`MAT1` pass-through (was L-1 "real stiffness")
The original item: real/parametric section properties replacing the
`sbeam_bridge._MAT1_E = 1.0e7` placeholder, unlocking the LRA model's
**indeterminate** paths (a continuous fuselage beam on two posts, BM-2's opt-in;
a wing carry-through element between the SOB nodes; redundant hinge sets on a
control-surface beam — note 24 R-12). **Descoped by the 2026-08-16 review
(§2.3):** the mission is a loads → sbeam *sizing* loop, and section properties
are the sizing half's output; a loads tool that owns a stiffness model reports
redundant-path internal loads that depend on properties it invented or was
handed. The shipped LRA model already states (header, R-12) that only the
**determinate** paths — SOB, fin root, split-fuselage post sums, gear and
engine links — give honest internal loads with placeholder properties, and
those are the interface loads a concept designer needs from a loads tool.

**What remains ranked (Pri 9, S):** if a consumer supplies `PBAR`/`MAT1` per
LRA element family (wing, fuselage, fin, h-tail, control surfaces — the
named-node contract of BM-5), `lra_model.py` writes them in place of the
placeholder. No physics, no new gate beyond "the deck still solves" in the
round-trip leg, no schema field beyond an optional per-family properties map.
The indeterminate-path half is **parked** ([`02_parked.md`](02_parked.md),
"Parked 2026-08-16") and the mission text's "unlocks the indeterminate paths"
is retired with it. Prior notes kept for the trail: D-7 (load-cards-only
default, assembled model opt-in), 2026-08-08 (the assembled export shipped as
plan 11 B5), 2026-08-16 (step 12 shipped, implementation note 25).

---

# Item detail — valuable [V] (ranked in the priority table above; parked bodies live in `02_parked.md`)

### [V] Combined flight + ground station envelope *(new 2026-08-14, from step 10 decision G-9)*
Ground cases are a **separate** governing family and are never auto-compared with
flight cases — a cross-family `max()` destroys the one thing the governing tables
exist to say (*which* case governs), and it compares numbers carrying different
safety factors. But a consumer sizing a fuselage frame genuinely wants the worst
of both at a station, so the honest form of that answer is an **envelope, not a
down-selection**: two-sided max/min per station over both families, with each
extreme **labelled with the case id that produced it**, so identity survives the
aggregation. Natural home is the `loads_plots` VMT envelope rather than the
governing tables. Needs ground cases to exist first (step 10). Reasoning of
record: [`18_step10_ground_cases_plan.md`](18_step10_ground_cases_plan.md) §G-9.
Tier M. Effort: M.

### [V] Gust spanwise-distribution decision *(new 2026-08-05, R9)*
Gust cases currently reuse the maneuver (Schrenk-based) spanwise shape.
Decide-and-document (or change): is that adequate for the concept mission, or do
gust cases need their own distribution? One study + a recorded decision in the
resolved-decision register (S). Not a defect — an undocumented assumption.

### [V] L-8i — Per-page LIMIT CSVs ignore the unit toggle and state no units
`wing_loads`, `fuselage_loads`, `tail_loads` and `loads_plots` each build a
download CSV from their own row dicts (`csv.DictWriter` over `wing_load_rows(...)`
and friends) instead of a `sloads` writer, so those files are **Imperial in both
systems** — while the table rendered above them on the same page is converted —
and their column headers carry no unit at all. They are the LIMIT analysis-page
channel (the `CLAUDE.md` carve-out allows LIMIT *display*), but a downloaded file
still leaves the tool, so it owes a unit statement. The work is per-page: convert
the rows with the page's existing display helper and give the headers
unit-suffixed names, the same shape M4-20 step 4 applied to the sbeam CSVs. Found
while implementing M4-20 step 6; pairs with **L-8a** (parked).

### [V] Split `40_history/00_completed_development.md` by era *(new 2026-08-05, R11)*
6,038 lines and the third-most-churned file in the repo. Split by era/area with
an index file (the sbeam `40_history` layout is the template); with the tiered
closure rule, S-tier items become one-line entries. Deferred from the 2026-08-05
process-doc session because the file carries uncommitted in-flight changes.
Mechanical (S); do after the current working tree is committed.

---

## Open defects (index)

- **Review 2026-08-10 unscheduled findings [Minor/NIT].** The 0.5.0 review's
  MINOR findings not promoted into the release rows (m3–m13, m15–m18: `stick_model_bdf`
  single-case GRIDs, CONM2 card width vs classical free-field, wing-band
  capacity guard, tail-arm duplicate entry `xt25` vs `xtc`, flap-config tail
  station, zero-ballast z-check asymmetry, tail-strip chordwise inertia torsion,
  derived-ACRL docstring mismatch, uncapped 2^n loading derivation, per-case
  pitch pins, NaN/Inf report behaviour, `_CALC_ERRORS` divergence, factor-map
  duplication, PDF staleness key, non-ASCII escape) and the NITs stay filed with
  bodies in [`../50_reviews/2026-08-10_code_review_0_5_0.md`](../50_reviews/2026-08-10_code_review_0_5_0.md)
  §3 — sweep opportunistically (practice 4) or promote individually.
- **Fuselage beam mass and the itemized mass model differ by 427 lb on ga6
  [Minor, found 2026-08-08 by the balanced-airframe baseline].**
  `weight.items` totals 3400.0 lb at cg_x 85.00 (matching `mass.cases[0]`
  exactly); less the wing panel (330), h-tail (42) and v-tail (23) it leaves
  3005 lb belonging to the fuselage beam, against the **2578 lb** entered in
  `fuselage_mass.stations`. Nothing reconciles the two representations. No
  deliverable moves today — the FAR23 oracles do not read `fuselage_mass`
  (**verify explicitly before changing anything**) — but the fuselage beam is
  running ~14 % light in inertia. Closed by the balanced-airframe item's step
  B1, which makes `weight.items` the mass SSOT and adds the reconciliation
  validator; filed separately because the discrepancy is real whether or not
  that item is worked.
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
- **M4-23 — `flight_envelope.density_ratio` duplicates `constants.standard_atmosphere` [Minor].**
  `density_ratio` (promoted from `_sigma` in M4-12b) reproduces the sigma computed
  by `constants.standard_atmosphere` bit-for-bit. Collapse to one authority —
  `density_ratio` becomes a thin read of `standard_atmosphere`, or is deleted and
  its callers re-pointed. Numerically inert by construction: assert the Appendix A
  oracles and both concept fixtures are unchanged.
- **Conventions-extraction findings (2026-08-05) [Minor, S — batch as one fix].**
  From the `CONVENTIONS.md` charter extraction (§8 there): (a) `load_keys.py:11-12`
  cites `tests/test_load_keys.py` as its uniqueness guard but **the test file does
  not exist** — write the guard or fix the docstring; (b) `constants.py:15` cites
  25.303 as the SF authority while `report/methods.py:230` and the docs cite 23.303
  — align on 23.303 (Part 25 as equivalent); (c) add an explicit comment on
  `coordinates.py`'s module-level Imperial/SOLVER default; (d) `units.py` carries
  three partially-shared SI factor maps — consolidation candidate.

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
