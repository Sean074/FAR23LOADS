# Completed Development

The authoritative record of what has shipped: completed modules/phases, key
decisions, and resolved defects. Items move here from
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) the moment they close,
with a matching `CHANGELOG.md` entry.

Each entry uses the step format: **Objective**, **Deliverables**, **Test /
Acceptance**, **Key decisions**.

---

**A ground case's source case is named as LANDLOAD's, not as a V-n point
(complete 2026-08-15, tier M)** — 0.6.0-candidate review finding R6-C3: the
wording of `BalancedCaseResult.vn_case` gained one owner
(`balance.source_case_name` / `case_source_name`, family from `is_ground`,
registered in the `CONVENTIONS.md` §7 SSOT table), and all five surfaces the
review named go through it — deck `$` header, deck case map, `run()` titles,
the rows table (column re-headed `Source case`, family-aware value) and
`SkippedCondition.name` (which gained a `ground` field). Swept alongside: the
shared `no-cg-case` skip reason and the Balanced Cases selector's ground hand.
Display wording only. Pinned by
`test_no_surface_calls_a_ground_case_a_v_n_point` (all five surfaces, both
ground fixtures, flight wording pinned too) and
`test_the_source_case_label_has_one_owner`. Digest wave: `txt/csv balance` +
`sbeam/balanced_deck` on the two ground fixtures — one channel wider than the
backlog row declared, because two surfaces live in the deck.

**Gear report CSV meets the load-output contract (complete 2026-08-15,
tier M)** — 0.6.0-candidate review finding R6-C2, with the R6-C4 hygiene row
folded in by user decision: the `gear_report` channel's header row is now built
from the resolved unit set (`-ULT` on every load column, plain force unit on
the two weights, the SI `Stroke` header no longer hard-coded `(in)`), every row
states its `SF` (last column), and a `Wheel` column says which wheel a `main`
row describes (starboard of the pair; port is the mirror). Hygiene:
`balance.gear_sets` dropped its unused `nvp` parameter; `_gear_stroke_table`
docstring paste blemish removed. Pinned by an Imperial contract test and the
SI-channel assertion whose absence let the defect ship; spec: the `gear_loads`
PROGRAM_SPEC section's Writes bullet. Digest wave `gear_report` on the five
gear fixtures, exactly as declared.

**Ground condition rows cite their own FAR condition (complete 2026-08-15,
tier S)** — 0.6.0-candidate review finding R6-C1: `balance.run()` ground rows
now read the case's `CaseRef.far_reference` (23.479…23.493) instead of the
flight-balancing literal 23.321; flight rows keep their literals by design;
pinned per ground fixture; digest wave `txt/csv balance` as declared.

**Documentation currency batch (complete 2026-08-15, tier S)** — 0.6.0-candidate
review findings R6-D1/D2/D3/D4 (`docs/50_reviews/2026-08-15_review_0_6_0_candidate.md`):
changelog `[Unreleased]` headings unscrambled, backlog "shipped since the tag"
gains step 9 + D-24, plan 09 marked closed, `00_INDEX.md` gains plans 14 and 18.

## Step 10 piece 3 — ground/landing cases + the gear load report (complete 2026-08-15, tier L)

**Objective.** The last piece of M4-6, and the one that **absorbs step 11 (plan 11
B8b)**: put the FAR 23 ground conditions into the assembled free-free deck as
balanced cases, and give the gear a deliverable of its own. Design note:
[`../30_future/18_step10_ground_cases_plan.md`](../30_future/18_step10_ground_cases_plan.md),
decisions **G-1, G-6, G-7 (+G-7a), G-8, G-9, G-12 (+G-12a), G-13**.

**Deliverables.**

- `sloads/gear_loads.py` — the gear as a **free body**, and the single owner of
  everything geometric about it: the per-attitude contact patch
  (`x + r·sin GRA`, `z − r·cos GRA`, compressed axle for cases 1–12 and static for
  13–33), the strut stroke recovered from the three entered axle states, the
  ground-line ↔ airplane-datum rotation `ρ`, the resultant-preserving transfer to
  the reference point, and the wheel placement an assembled case needs.
- `modules/balance.assemble_ground` + `build_ground_cases` — the ground family,
  sharing `_closure`, `body_inertia`, `resultant6`, `point_mass_self_inertia` and
  the new `wing_inertia_strips` / `place_wing_inertia` (factored out of
  `wing_sets`, behaviour-neutral) with the flight families. Plus
  `ground_lift_sets`, `gear_sets`, `is_ground`, and two new `SKIP_REASONS`
  (`gear-design-only`, `side-twin-by-reflection`).
- The **gear load report**: `export.gear_report_csv` / `gear_report_rows`, report
  §8 with the strut-state table, a manifest row, the Landing Loads page's free-body
  section, and the CLI's `--export-target gear`.
- Schema **v48** — `LandingGearInput.weight_lb` (G-12a), additive, `0.0` = not
  stated, no migration hop. Two result types gain fields that existed only
  implicitly: `GearReactionCase.weight_lb` (the design weight the case is computed
  at) and `BalancedCaseResult.cg_x`/`cg_z` (the point its residuals are stated
  about).
- `export/bands.py` gains the **`balanced-gear` GID band** (10001+) so a gear node
  is findable by id rather than by coordinate; `case_ids.balanced_subcase_id` and
  `deck_load_id` take the case's **hand explicitly** (G-8).
- Fixture data: leg weights on five airplanes × two legs, **per leg** — half the
  database's main-gear rows, all of its nose-gear rows.

**Test / Acceptance.** `tests/test_gear_report.py` (44 tests) is the step's
benchmark-first gate; the whole suite is green (1670 passed / 21 skipped), lint
clean, and the **real solver** leg passes in 16.5 s with the solve count roughly
doubled — G-13's "one cost to check rather than assume", answered.

- **The closed-form gate is an exact identity** (G-6). The solved rigid-body
  field, rotated back to the ground line, reproduces LANDLOAD's `NVP`, `NDP` and
  `NS` on **every** case of both fixtures at `rel_tol 1e-9`. Two completely
  different routes — a mass matrix here, lever arms and FAR percentages there —
  one answer.
- **The transfer preserves resultants exactly** (G-2's third guard, the one it
  owed this piece): worst relative moment error **3.4e-16** over all 33 cases and
  both legs, taken about a deliberately arbitrary reference rather than the CG,
  where a dropped couple could cancel against something.
- **Two negative controls**, per G-13: dropping the offset couple breaks the
  transfer, and computing a level-landing case at the *static* contact patch
  breaks the moment gate. The second is asserted on the **moment**, not on `NVP`
  — moving the patch does not change the vertical force factor, so a control
  watching `NVP` would have passed and proved nothing.
- **G-13's ground-specific solver assertion**: the reaction sbeam recovers at each
  gear GID is the gear report's reference-point reaction, in both unit systems.
  This is what stops the inherited "reactions ≈ 0" leg passing vacuously — a
  transfer that dropped its lever arm *consistently* would still sum to zero at
  the support.
- **LANDLOAD's own twins check the reflection operator** (G-8): `reflect(19)`
  reproduces case 20's `NS`/`ROLLP`/`YAWP` sign-flipped and equal. Every other
  reflection in the suite is guarded against itself; this is the only external
  check it will ever get.
- **Coverage is pinned twice and the two sets differ by design**: assembled ground
  cases on **2** fixtures (ga6 3/3 loadings, the RJ 2/3 — the already-pinned Pri 9
  fixture-data finding, inherited not created), the gear report on **5**.
- The digest wave is exactly G-13's stated expectation: `sbeam/balanced_deck` +
  `case_index` on ga6 and the RJ, a **new** `gear_report` channel on five
  fixtures, and `csv/landing` + `txt/landing` on five from the case-labelling fix
  below.

**Key decisions.**

- **G-7a — the lift acts along the ground line, not along airplane `z`.** Raised
  by implementation, because G-7's wording and G-6's promise of an exact gate
  could not both hold: LANDLOAD sums `lf·WL` into the *ground-line* vertical, so
  a lift on `z` enters that sum short by `cos ρ` — 0.053 % of `NVP` on ga6, small
  and *not* solver noise. It is also the physics: lift is perpendicular to the
  flight path, the ground line is the flight path at touchdown, and the airplane
  sits at `ρ` to it (152 lb of ga6's 2,154 lb lift acts forward).
- **`ρ` is taken from LANDLOAD's own two resolutions of one reaction**,
  `atan2(dm, vm) − atan2(DMP, VMP)`, not re-derived from `GRA`. That means this
  step never has to adjudicate a sign inconsistency that is in LANDLOAD.BAS
  itself — `beta` is `gamma − GRA(1)` for the level attitude and `+GRA(2)` for
  the ground-roll one — and the rotation appears only in the **check**, never in
  the load path.
- **G-12a — the leg weight is an input, one number per leg.** Nothing marks a
  `weight.items` row as gear; on every fixture they are identifiable only by name,
  and matching on that is the `LANDING_CG_NAMES` failure mode G-3a had just
  retired one layer up. Deliberately *not* a sprung/unsprung split: only the
  unsprung mass sees the impact amplification that sizes an axle, and sloads does
  not model that, so entering the split would imply a capability the tool lacks.
- **A correction to G-12's own arithmetic.** The note read "155 lb → 491 lb, 12 %
  of a 4,038 lb reaction", pairing the **whole main gear** with a **per-wheel**
  reaction. `weight_lb` is therefore defined per leg (consistent with `attach`,
  likewise one leg's node), ga6's main leg is 77.5 lb, and the real figure is
  **6.1 %** — still far too large to leave out of a free body, which is what the
  paragraph exists to argue.
- **The report and the assembled deck carry different case sets, and say so.**
  33 against 24. The 23.499 family is not merely excluded from the assembly, it
  has a home.
- **What the report is not travels with it**, in the CSV stamp, the report
  section and the GUI: no gear kinematic model, so no drag-brace, side-brace,
  trunnion or axle-bending loads. Overstating it would be the "a wrong card
  outranks a missing card" failure in its purest form.

**Two defects found on the way, both fixed here.** The per-case record labelled
the wrong loading on five of the six 23.485 side cases (`(m-1) % 3` against a
family that is three loadings × two drift directions) — cosmetic, so no load ever
moved, but it is the label a reader joins on and it matters now that the assembled
case builds its inertia set from it. And `is_handed` tested "any load carries a
free moment" where it meant the net, which minted every symmetric level-landing
case handed once both wheels carried a transfer couple.

## Step 10 piece 2 — the weight/CG case model + gear inputs (complete 2026-08-14, tier L)

**Objective.** Land the whole schema hop decisions G-2/G-3/G-4/G-5/G-14 imply as
**one** `SCHEMA_VERSION` bump rather than four, and prove it moves nothing. Three
weight/CG case lists and six representations of MTOW become one owner each, so the
ground-case physics (piece 3) has inputs to consume instead of inventing them.

**Deliverables.**

- `sloads/cg_cases.py` — the one resolver. `cases_for` / `flight_cases` /
  `ground_cases` / `landing_role_cases`, `max_landing_weight` /
  `max_takeoff_weight` / `max_landing_weight_estimate` / `database_total`, and
  `seed_landing_cases` (the WTENV seed, moved out of the Landing Loads view into
  the calc package where it can be tested as a function).
- Schema **v47**. `CgCase.analyses: Set[AnalysisKind]` (`FLIGHT` | `GROUND`,
  default `{FLIGHT}`) and `CgCase.role: Optional[GroundCaseRole]`;
  `WeightInput.max_landing_weight_lb` / `.max_takeoff_weight_lb`;
  `MassItem.consumable`; `LandingGearInput.carrier` (no default) / `.attach`.
  **Removed:** `FlightLoadsInput.cg_cases`, `LandingInput.cg_cases`,
  `LandingInput.gross_weight_lb`, `LandingInput.max_landing_weight_lb`.
  New enums `AnalysisKind`, `GroundCaseRole` (+ `GROUND_CASE_ROLE_ORDER`),
  `GearCarrier`.
- `migrations._v46_cg_case_model` — tags existing `weight.cg_cases` `FLIGHT`,
  folds `landing.cg_cases` in as `GROUND` with roles from the canonical names
  (merging onto an existing case where name **and** `(weight_lb, xcg, zcg)`
  match), moves MLW across, and seeds MTOW from `speeds.weight_lb`. It also
  recovers a pre-v19 file whose cases live only on `flight_loads` and that carries
  no `weight` dict — a case `_v19_cg_cases` gave up on.
- `landing.py` reads the roled cases and takes `mlw`/`mtow` as explicit arguments;
  every flight consumer (`select`, `flight_envelope`, `balance`, `balloads`,
  `tail_span`, `wing_inertia`, `mass_distribution`) reads `flight_cases(project)`.
- `mass_distribution.derive_case_loadings(project, cases=None)` is generalized to
  any case list, with the **G-5 burn-down** path for `GROUND` targets
  (`_burn_down`: one fraction applied to every `consumable` row, so a tank layout
  survives).
- Validation: `_check_weight_case_model` (`cg_case_no_analysis`,
  `cg_case_role_without_ground`, `ground_role_incomplete`, `weight_order_chain`,
  `mlw_below_landing_estimate`, `mtow_representation_drift`) and
  `_check_gear_carrier` (`gear_carrier_unset`, `gear_carrier_mass_disagrees`,
  `gear_attach_missing`, `gear_attach_off_the_wing`).
  `_check_landing_hierarchy` loses `gross_ge_max_landing` and `landing_cg_names`
  with the fields they policed and gains `landing_case_weight_is_mlw`.
- GUI: the **Payload Cases** tab becomes the sole editor (`FLIGHT`/`GROUND`
  checkboxes, a landing-`role` selectbox, and the WTENV seed on a button); the
  **Weight / CG Envelope** tab owns MLW and MTOW and shows the derived MLW
  estimate; the mass-item editor gains a `consumable` checkbox; the **Landing
  Loads** page's CG table and both design weights become read-only.
- Fixture data: `carrier` + `attach` on five airplanes × two legs, and the mission
  fuel row tagged `consumable` on each.

**Test / Acceptance.** `tests/test_cg_cases.py` (43 tests) is the drift guard.
The whole suite is green (1614 passed / 21 skipped) with **`digests.json`
unchanged** — the piece's stated expectation, "nothing moves", and if something
had, the migration would not be output-neutral. Specifically pinned:

- The `FLIGHT`-tagged set after migration equals the pre-hop
  `flight_loads.cg_cases` **exactly, per fixture**, compared against the file on
  disk rather than a re-derivation (G-3b's stated guard). Likewise the `GROUND`
  set against the pre-hop `landing.cg_cases`.
- MTOW agrees with every representation it replaced, per fixture, and is *not*
  the heaviest landing case (3,400 against 3,230 on ga6) — the latent `WR = 1.0`
  defect, pinned so it cannot return.
- The role fixes the order: reversing the entry order changes nothing, renaming
  every case changes nothing, and a missing or duplicated role **raises**.
- G-5, reproducing the plan's measurements exactly: ga6's aft landing case burns
  **317 lb** of fuel, needs **no ballast** and lands **0.12 in** from its target;
  burn-down is proportional across two tanks; and marking *every* item consumable
  leaves every flight loading unchanged on all six fixtures — the acceptance test
  for the field, and why the Appendix-A oracles cannot move.
- Ground-loading coverage is exactly what G-3/G-5 predicted: ga6 3/3, the RJ 2/3,
  `cessna_210` / `atr42_100` / `dhc8_dash8` 0/3, each skipped and recorded.
- The MLW floor fires on `concept_regional_jet` **and no other fixture**; the
  carrier ↔ mass guard fires on `dhc8_dash8` **and no other fixture**. Both are
  asserted as set equalities, so a second fixture drifting into either is a red
  build rather than a longer warning list.

**Key decisions.**

- **The removals are the point.** A proxy field would have left a second way to
  say the same thing, which is what G-3 exists to remove (the G6b single-source
  precedent, deliberately not the `tail_loads` proxy precedent). That is also why
  this hop needs a migration where v44-v46 did not: absent is *not* the old
  behaviour for a removed or relocated field.
- **`max_takeoff_weight` keeps a documented fallback chain** to
  `speeds.weight_lb` → `weight.envelope.gross_weight` → the heaviest `FLIGHT`
  case. A loaded project never reaches it (the hop seeds the SSOT); a
  directly-constructed test project does. `mtow_representation_drift` is what
  keeps it a compatibility path rather than a second authority.
- **Two findings are left firing rather than fixed here**, because fixing either
  moves output and this piece is claimed as "nothing moves": `dhc8_dash8`'s gear
  mass tag (correcting it re-pins `mass_distribution.wing_mass_tie`) and the
  `applicability` / `direct_totals` design-weight re-point (the FAR 23 exceedance
  line changes 37,781 → 36,817 on atr42 and 34,800 → 33,000 on the RJ). Both are
  in the backlog with the guard that found them.
- **The `atr42_100` sponson and the RJ's wing-body junction are `BODY`**, stated
  rather than guessed: a sponson is a fuselage fairing and an RJ's main-gear
  trunnion lands on the keel beam in the wing-body fairing. `dhc8_dash8` is the
  `WING` fixture — gear in wing-mounted nacelles — and so is the one that will
  prove the wing load path in piece 3.
- **G-2's third guard is deferred with its subject.** "The transfer preserves
  resultants about the CG at `rel_tol 1e-12`" tests the transfer, which lands with
  the ground export in piece 3; the two input-side guards ship here.

---

## Step 10 piece 1 — the governing safety-factor table (M4-8, complete 2026-08-14, tier L)

**Objective.** Make the factor of safety a stated authority instead of a
distributed default. Before this, `ConditionResult.safety_factor` defaulted to
`constants.ULTIMATE_FACTOR`, exactly one module (`one_engine_out`) overrode it, and
`report/content.py` twice read `getattr(item, "safety_factor", ULTIMATE_FACTOR)` —
so a factorless case was reported at 1.5 with no trace that anything had been
assumed. Sequenced **first** of step 10's three pieces so the ground family
consumes an existing authority rather than becoming a third ad-hoc factor site.

**Deliverables.**
- `sloads/safety_factors.py` — the single code owner. `LoadClass` +
  `DERIVED_FACTOR` (Layer 1: `LIMIT → 1.5`, `ULTIMATE → 1.0`, 14 CFR 23.303/25.303);
  eight `FAMILIES` rows whose boundaries are **14 CFR Subpart C's own section
  groupings**; `classify()` mapping a case to a family from its FAR reference (with
  the case ref as fallback, since the distributed component results carry theirs
  only there); `GoverningTable` with `resolve` / `factor_for` / `stamp`.
- `Project.safety_factors` (`SafetyFactorPolicyInput` / `SafetyFactorOverride`) —
  schema **v46**, additive, written only when it carries an override, no hop.
- Report **§3 Governing safety factors** (renumbering §3–§7 → §4–§8 through
  `section_ref`, which is what F-R2 built it for), the case index's `SF` column
  re-pointed to the table, an override paragraph and a live `DEFAULTED:` line.
- `export.safety_factors_csv` / `write_safety_factors_csv`, the bundle channel
  `<project>_safety_factors.csv`, and its manifest row.
- `report.methods._safety_factor_block` — the override declaration, silent when
  there is nothing to declare.
- `validation._check_safety_factor_overrides` — unknown family, missing basis,
  out-of-band factor, and the below-regulation **certification-risk** warning.
- Docs: `CONVENTIONS.md` §3 (the owner named), `CLAUDE.md` load-output contract,
  `00_program_overview.md`, `PROGRAM_SPEC.md` (SELECT notes + the export SF note),
  `00_theory_sources.md` (the family/citation table), `GUI_design.md` v46,
  `DATA_DICTIONARY.md` regenerated.

**Test / Acceptance.** `tests/test_safety_factors.py` (37 tests). The authority
claim is **reproduction, not assertion**: for all six shipped fixtures, case by
case, the table resolves exactly the factor the producing module mints — including
`one_engine_out`'s 23.367(a)(2) at 1.0 — and **no case falls through
unclassified**. A defaulted case in any shipped fixture is a red build, which is
what stops "flagged" from normalising. Also pinned: an exact row beats the range it
sits inside (23.367(a)(2) is an ultimate case inside the limit flight range, and
double-factoring it was the live risk); a multi-section reference whose families
disagree on a factor is left unclassified rather than decided by word order; an
override reaches the carrier, the case index, the companion CSV and the methods
stamp together. **No shipped fixture carries an override, no digest moved, no
number changed.** Suite: 1561 passed, 21 skipped; ruff clean.

**Key decisions.**
- **G-10** — every FAR ground case is limit × 1.5, read from the CFR text rather
  than inherited from the default; the deliverable can now say why.
- **G-11** — the table is the authority, at **condition-family** granularity, and
  is **fully user-editable including the regulation rows** (user decision, taken
  against the recommendation, with the risk stated). Safe for the oracles — the
  factor is applied at the render/export boundary only, so no override can move an
  Appendix-A figure — but *not* for the deliverable, so the four mitigations are
  part of the decision: an override is never silent, must state a basis, warns when
  below the regulation, and no shipped fixture carries one.
- **An unresolved case defaults to 1.5 and is flagged** rather than raising (user
  decision), with the zero-defaulted-rows test as the guard against drift.
- The **carrier stays the carrier** (M4-8's original design): the table *writes*
  `safety_factor` at `registry.run_all_modules`, `component_loads` and
  `balanced_run` rather than replacing the field, so ~18 `_sf()` call sites in the
  export bridge and every report reader needed no change — and an override cannot
  reach the report without also reaching the cards.

---

## Pressurization removed from scope (decision D-24 — complete 2026-08-14, tier S)

User decision, taken while scoping step 10 (M4-6): **pressurization is out of
scope for sloads, permanently.** The `pressurization` standing limitation is
reworded from "No pressurization load cases." — which reads as pending — to an
explicit exclusion naming 23.365/25.365, disclaiming the deliverable as a
complete set for a pressurized fuselage (four shipped fixtures are pressurized
airplanes), and separating it from the unrelated WTESTIMA `pressurized`
weight-allowance flag. The key stays in the pinned `STANDING_LIMITATION_KEYS`
set; `tests/test_methods_stamp.py` gains a guard that the sentence reads as an
exclusion. M4-6 is re-scoped to the ground/landing distributed loads and gear
reactions alone, and **F25-5** loses its ΔP-combination half (§1.8's 25.365 row
becomes disposition **X**), keeping only the 23.415/25.415 ground-gust module.
One consequence is carried forward rather than assumed: the old "for a
pressurized airplane, ground cases cannot be down-selected against flight" rule
leaves with the case, so the ground-case down-selection question is now open for
step 10's design note. Docs synced: backlog row + M4-6 body,
`03_gui_rework_plan.md` (§3 table, Phase 4, §5 item 3, §6),
`01_far25_gap_analysis.md` (§1.8 + F25-5), `02_parked.md`,
`05_step_g8_summary_report_plan.md` §6, `03_resolved_decisions.md` (D-24).

---

## Mission step 9 — discrete control surfaces + the T-tail transfer (plan 09 T6–T8, complete, 2026-08-13)

**Objective.** Close plan 09's phase 2, the two load paths its phase 1 left
unstarted: a control surface whose load reaches the parent surface through
**hinges and an actuator** rather than smeared into it — producing the suite's
first hinge-moment output — and a **T-tail** whose fin deck carries the
horizontal tail it is holding up. Tier L (new physics, schema change, new result
types), design note agreed in chat first as
[`plan 09 §10`](../30_future/09_distributed_empennage_loads_plan.md).

**Deliverables.**
- **T6 — the discrete control-load path.** `control_load_mode = "discrete"`,
  per surface, with new `TailMassInput.hinges_span_in` / `.actuator_span_in`
  (`SCHEMA_VERSION` 45, additive, no hop). The control surface's own load leaves
  the smeared strips over the span its hinges hold and re-enters at dedicated
  `GRID`s on the load reference axis: hinge reactions by chord-weighted
  tributary span, and the hinge-moment couple at the actuator. New GID bands
  `tail-control-htail` 5001-5300 and `tail-control-vtail` 5301-5600, registered
  in `export/bands.py` like every other family. New result types
  `ControlPointLoad` and the `TailSpanResult.control_loads` /
  `.control_surface_load_lb` / `.hinge_moment_lbin` / `.hinge_moment_arm_in`
  fields, surfaced on the **Tail Span Loads** page, in the module's own
  `LoadValue`s and in the deck `$` header.
- **T7 — the T-tail transfer.** `TailType.T_TAIL`'s first load-path consumer.
  Each v-tail case's deck carries, at the fin's **last** node, the concurrent
  h-tail set (balancing load at that case's own V-n point plus `−n·W_ht`) as a
  vertical `FORCE` and the `MOMENT` its two lever arms make. New `TipTransfer`
  result and `coordinates.ttail_transfer_to_airplane` — the one load in a fin
  deck that is not in the fin's local frame, so it gets its own named map.
- **`select.py` gained two part-returning helpers** (`elevator_load_parts`,
  `rudder_load_parts`) whose sums are the existing expressions in the existing
  order, so the oracle-locked `elevator_load` / `load_on_rudder` values are
  unchanged to the bit and the discrete path has one producer to read rather
  than a second copy of the arithmetic. `taildist._surface_geom` became public
  (`surface_geom`) so the hinge line has one owner across the two tail views.
- **Closure trail:** `CONVENTIONS.md` (two SSOT-table rows + five prose bullets:
  the two control-load paths, the hinge-moment arm, and the T-tail transfer
  reference point), `PROGRAM_SPEC.md` (two module/deck rows),
  `theory_sources.md` (both gate tables as the R10 oracle substitute),
  `GUI_design.md` (v45), regenerated `DATA_DICTIONARY.md`, `cspell.json`.

**Test / Acceptance.** Ten new gates in `tests/test_tail_span.py` and a rewritten
v-tail row in `tests/test_export_equilibrium.py`. The strong ones:
- **Cross-mode force identity, exact** (`rel_tol 1e-12`, both surfaces, every
  condition) — a property of the construction, since exactly the control load is
  removed and exactly it is applied. Distributing the removal by the raw strip
  fractions would have rested the identity on `Σ frac == 1`, which is exact for a
  derived rectangle and only 1 %-true for an entered polyline: the T1 validator's
  own tolerance, quietly become a load error.
- **The hinge moment against its closed form**, `HM = L_cs · c_e/3` — 4.856 in of
  arm on ga6, hand-derived in the test from `Saft/S = 0.40039` of a 36.388 in
  chord.
- **Hinge torsion + actuator couple = the control load at its own CP.** Reverse
  the actuator's sign and the sum lands on the hinge *line* instead — a 4.86 in
  chordwise error with nothing else in the deck to catch it.
- **The cross-mode torsion difference as an identity, not a tolerance**: exactly
  the chordwise relocation `att·x_25 + cam·x_50 − L_cs·x_cp`, printed as the
  physical explanation. Plan §5's T6 asked only for "within a stated tolerance".
- **T7's free-body gate**, read from the deck's own card text: the fin deck's
  resultant about the origin is the axial column at its own stations plus the
  transferred set at the node it is stated to be applied at.
- **Gating and mode isolation, byte-level**: flip `tail_type` back to
  conventional and the deck returns exactly; no shipped fixture carries hinge
  geometry, so every smeared deck is unchanged. Imperial digests moved on
  **three** channels of one fixture only (`concept_regional_jet`'s
  `sbeam/vtail_span_cards`, `csv/tail_span`, `txt/tail_span`) — the fin's own
  station table did not.

Suite green: 1523 passed, 21 skipped; `ruff check sloads/ cli.py app/` clean.

**Key decisions** (recorded as T-12…T-17 in plan 09 §10.1, agreed with the user
before implementation).
- **T-12 — the control-surface load is SELECT's, read never recomputed.** This
  **supersedes T6's own sentence**, which said "the control part (`LT50`)".
  `LT50` is the *camber* load and its TAILDIST trapezoid runs leading edge to
  trailing edge, so hanging all of it on the hinges would move stabilizer load
  onto the elevator while ignoring the angle-of-attack share the elevator really
  carries. `select.elevator_load` (SELECT.BAS 5216-5218) is oracle-locked, is the
  load on the surface *including* its aerodynamic-balance area forward of the
  hinge, and the module contract forbids recomputing it. Where a condition
  publishes none — the balancing, checked, gust and unsymmetrical h-tail
  conditions, and the rudder-neutral fin ones — the load is derived from
  TAILDIST's aft-of-hinge block and **marked**, the derive-and-mark contract the
  tail planform is already under.
- **T-13 — the hinge-moment arm is exactly `c_e/3`**, not an approximation:
  TAILDIST's net trailing-edge pressure is identically zero (`WATT3 = WCAM3 = 0`),
  so the block aft of the hinge is always a triangle, whatever the condition.
- **T-14 — the removal is normalised**, so the force identity is structural.
- **T-15 — the actuator carries a couple, not a force.** With no horn radius in
  the schema a rotary actuator is the honest model, and it is what makes the
  chordwise identity exact.
- **T-16 — the transfer set is `Fz` and `Myy` only.** The T-5 pairing is a
  *balancing* condition, which is symmetric, so the h-tail's halves cancel about
  the centreline; a transferred `Mxx` would be a number with no producer.
- **T-17 — no shipped fixture gets hinge geometry.** Inventing hinge stations for
  six aircraft with no oracle is the fabrication §9.1 refused for the tail
  polylines. The discrete gates run against a project the test builds, and every
  shipped deck stays byte-identical in the mode nobody changed.

**Measured, and worth recording.** The fin is shorter than the h-tail's semispan
(57.0 in against 73.1 on ga6), so the first version of the cross-mode test —
written with one set of hinge stations for both surfaces — was refused by the
new validator rather than silently accepted. That is the validation working on
its author.

---

## Release cut: **sloads 0.5.0** (the assembled free-free deliverable), tag `v0.5.0`, 2026-08-13

**Objective.** Close the review of record's Phase 3 (release mechanics) and cut
the release decision **D-R1** had held for the deliverable — the summary report
plus wing/body/tail and balanced/CONM2 sbeam output. `[Unreleased]` had grown to
~900 content lines across three review phases; unreleased work has no regression
baseline.

**Deliverables.**
- **Workbook per-sheet unit statements** (review **m14**, tier M). One `.xlsx`
  carries both unit channels — module and case-index sheets are HUMAN, span-load
  sheets are the SOLVER channel the sbeam decks use — and in SI those sets differ
  (`N·m`/`kPa` vs `N·mm`/`MPa`), so the single Project-sheet `Units` row
  mis-stated every span sheet by 1000× in moment (SUMMARY_REPORT.md §3.5/§4.7:
  "a per-file units column that disagrees ... is a conformance failure, not a
  footnote"). `build_workbook` now **owns** the statement instead of taking a
  pre-formatted one from the page: it resolves both channels once from the
  `system` it is given, writes each data sheet's own set into cell `A1` above
  that sheet's header row, and names both channels plus the unconverted KEAS/ft
  exception on the Project sheet. The case index, carrying no load quantity,
  states that rather than claiming either set.
- **`app/` joined the lint gate** (review **m21**). The merge gate left the whole
  Streamlit layer unlinted and it had drifted — an unused `build_tail_span`
  import in `export_report.py`. Now `ruff check sloads/ cli.py app/` in CI and in
  every document that states the gate (`CLAUDE.md`, `00_program_overview.md`,
  `RELEASE_PROCESS.md` §3.2, `CODE_REVIEW_PROCESS.md` ×2, `PROJECT_GUIDE.md`,
  `README.md`).
- **Root cleanup** (review **m19**). `.DS_Store` gitignored and untracked;
  `CODE_REVIEW_2026-07-21.md` and `PROJECT_REVIEW_2026-07-19.md` moved to
  `docs/50_reviews/` and indexed in `00_INDEX.md` (which also gained the
  2026-08-10 code review, previously unlisted); `requirements.txt` **deleted**
  rather than regenerated — a second dependency source that had already drifted
  from `pyproject.toml` (streamlit ≥1.30 vs ≥1.36, listing pytest, omitting
  plotly and openpyxl), and one source that is right beats two that disagree.
  `README.md` and `PROJECT_GUIDE.md` §4's tree updated.
- **Release-doc currency** (review **m20**). `RELEASE_PROCESS.md` §1 pointed at
  the pre-M3-1 `sloads/models.py` for the schema version — now
  `sloads/models/project.py`, and named `SCHEMA_VERSION` as the code does.
  pyproject classifiers list 3.9 / 3.11 / 3.12, the CI matrix, instead of 3.9
  alone.
- **`scripts/smoke_test.sh` fixed — the §3.5 gate failed the release it gates.**
  It read line 1 of the CLI's CSV as the header, but since G8.3 every exported
  CSV carries the methods & limitations statement as `#` lines above it, so the
  script saw `# METHODS AND LIMITATIONS` and reported an unexpected header. The
  Python readers were audited when the stamp landed (`workbook._csv_to_df` reads
  with `comment="#"`); this shell one was not — practice 4 (generalize on first
  find) applied late. It now skips comment lines, counts rows from the data
  block, and **requires** the stamp to be present, so the gate proves the
  headless deliverable states its own basis.
- **Version** `0.4.0` → **`0.5.0`** in `pyproject.toml` (MINOR: new capability,
  no breaking change — `SCHEMA_VERSION` 44 is reached by additive hops and
  `io.py` loads every older save).
- **Changelog cut** — `[Unreleased]` dated to `## [0.5.0] — 2026-08-13` with its
  **ten headings merged to three** (Added / Fixed / Changed), verified
  content-preserving as a line multiset before and after, and a fresh empty
  `[Unreleased]` opened — the same consolidation the 0.3.0 and 0.4.0 cuts
  performed. It opens with a **release-notes block** stating the four standing
  caveats a 0.5.0 deck carries: the flight-only fuselage deck (D-R3), fin-only
  lateral aerodynamics (L-7, over-stated and conservative), the handed
  23.427(a) maneuver pair (D-R8), and concept mode as closure-locked rather than
  oracle-locked (D-R6).
- **Verification baseline** —
  [`09_verification_baseline_0.5.0.md`](09_verification_baseline_0.5.0.md), a
  **delta** baseline like 0.4.0's: the closure gates for everything 0.5.0 added
  (six-DOF balanced closure, handed twins, the lateral three, the report's own
  conformance gates, per-sheet workbook units), the nine pinned exceptions with
  their measured figures, the four standing limitations, and what measurement
  changed — carrying the 0.3.0 oracle tables forward unchanged on the same two
  confirmations (register unchanged; every Imperial digest movement a new or
  renamed channel, the wave spent four times inside the release).
- **Backlog re-cut to post-release form** — the 0.5.0 row and its whole "Item
  detail — 0.5.0 release scope" section removed per the removal rule, the
  remaining 31 rows renumbered with their `Pri` cross-references followed, and
  the release prose replaced with the cut record.
- **Gates at cut:** `pytest` **1494 passed / 21 skipped / 0 failed** (coverage
  93 %), `ruff check sloads/ cli.py app/` clean, `scripts/smoke_test.sh` **PASS**
  (headless GUI render + CLI export), every skip carrying a stated reason and a
  backlog entry, no open CRITICAL/MAJOR review findings.

**Key decisions.** `build_workbook` owns the unit statement rather than
receiving it (practice 3, single owner + drift guard): the source guard in
`test_deliverable_units.py` that used to pin the *defect* (`"Units":
units_statement(` present in the page) now pins the contract — the page passes
`system=_system` and states nothing itself. `requirements.txt` deleted rather
than regenerated, for the same reason.

**Post-release.** The cadence rule (`RELEASE_PROCESS.md` §2) restarts from this
tag. Per **D-R3** the ground/landing case families (backlog Pri 4–5) are the
0.6.0 headline; the sequence-independent rows — ONENGOUT fixture data, the
wing-case-condition naming decision, M4-8 Layer 1's full resolver — ship in any
gap. `scripts/smoke_test.sh` into CI (review **m20**) remains the stated
fast-follow, not a gate.

---

## A wing case row states the condition its loads were computed at (post-0.5.0 Pri 1 — complete 2026-08-13, tier M)

Decision **D-23**: where a `WingLoadCase` states its own `v_eas_kt`, that speed —
the one `net_loads._air_cl_v` builds the air load from — is what `wing_case_ref`
puts on the `CaseRef`, even where SELECT named the same condition at a different
V-n point. Previously SELECT's ref was returned whole, so `atr42_100`'s `PHAA`
row read 185.85 kt beside loads computed at the entered 170 kt (and ga6's `ACRL`
117.4 against 116 — the M4-2 derived-ACRL divergence, showing up as a label).
SELECT's `case_id` is kept (M4-2 decision 1, which the case-index dedupe
assumes), as are CG, altitude and the FAR reference, which the case does not
state; SELECT's own governing-loads row keeps its V-n point, which is what its
numbers were computed at, and the case-index note now says so. The index's
ordering rule became explicit in the same change — deck-exported results before
SELECT's conditions, first-seen defines a row's condition — with all four callers
(report, Export page, workbook, Imperial baseline) put in that order. Gates:
`test_every_wing_case_row_names_the_speed_its_loads_were_computed_at` (every
entered case on every fixture, ref speed == `_air_cl_v` speed),
`test_the_case_id_stays_selects_when_the_speed_is_the_cases_own`, the atr42 pin,
and `test_the_index_row_states_the_condition_its_cards_were_computed_at` for the
caller ordering. Imperial baseline regenerated deliberately: `csv/wing_inertia`,
`csv/net_loads` and `case_index` on all six examples; **no deck channel moved**
— the identity changed, the numbers did not.

---

## Case identity ↔ deck LOAD id linkage (post-0.5.0 Pri 2 — complete 2026-08-13, tier M)

The case id, the deck `LABEL` and the deck `LOAD`/`SUBCASE` integer are one
identity in three notations, and until now they appeared together only in the
case-index **CSV** — the summary report's case index printed no deck number and
no GUI page printed one at all, so a reader holding `SUBCASE 7105` had to open a
file to find out what it was. Both now state it, in **two** columns qualified by
deck family (user decision, 2026-08-13): a case legitimately holds one number per
family (`W-05` → `105` component, `5105`/`7105`/`8105` assembled, **D-R7**), so
one unqualified column would be silently wrong for whichever family it was not
quoting. A column is filled only where the case is in that deck — the assembled
column is driven by the assembled deck's own case set, not by the id alone —
which makes a handed twin's blank component cell a statement rather than a gap.
`case_ids.deck_load_id` is the single owner (the rule previously lived in the
private `sbeam_bridge._subcase_column`, which `report/` and `app/` could not
import) and `case_ids.case_label` the one formatter behind every GUI case label;
the governing-loads and balanced-case tables gained `ID` + `LOAD`, and the
assembled deck's `$` map block now leads with the case id like every other deck
family's. Gates in `tests/test_case_ids.py` check the printed number against the
**decks' own text**, that no row is blank in both columns, that a handed id is
numbered in the assembled deck only, and that the report table and the CSV agree
cell for cell. Imperial baseline regenerated deliberately: `case_index` on all
six examples, `sbeam/balanced_deck` on the two that assemble; no load number
moved. Design note: [`../30_future/17_case_load_id_linkage_note.md`](../30_future/17_case_load_id_linkage_note.md).

---

## ONENGOUT fixture data — the module executes on shipped data (post-0.5.0 Pri 1 — complete 2026-08-13, tier M)

`one_engine_out` was registered, oracle-cited and **unrunnable on every shipped
fixture**: `atr42_100`/`dhc8_dash8` entered the slice but no engine horsepower
(`MissingInputError`), the other four entered no slice, so the 23.367 simulation
path was exercised only on constructed inputs — the `tail_mass` gap's class.
Both turboprops now carry take-off **and** max-continuous shaft power (PW120
2000/1700 shp, PW121 2150/1950 shp; converted from the certificated kW in **EASA
TCDS IM.E.041 issue 07, 20 Dec 2023, §5** at 745.7 W/shp, rounded to 10 shp), both
fields entered rather than left to `_engine_power`'s fallback because
`use_takeoff_power` is the user's choice of rating. Tier M, not S: HP is not
ONENGOUT's alone — `weight_estimate.resolve_max_continuous_hp` (M2-6) prefers the
engine list and had been falling back to the stored estimation total, so entering
the ratings corrected `dhc8_dash8`'s statistical estimate (stored 4000 hp vs the
engines' 2×1950 → MTOW 42,325 → 41,775 lb, empty 25,395 → 25,065 lb; `atr42_100`'s
stored 3400 already matched 2×1700 and did not move). The Imperial baseline was
regenerated deliberately: five channels on `dhc8_dash8`, three on `atr42_100`, and
no load path, deck or oracle anywhere. The **RJ half was dropped** (user decision, 2026-08-13) — see the
limitation below. `tests/test_one_engine_out.py::test_the_shipped_turboprops_execute_onengout`
is the standing gate (both ratings present, positive thrust/drag/tail load per
speed, VC/VD recover, VS does not — below VMC, stated in band); plan 13's G1 gate
dropped its `_G1_SYNTHETIC_HP` injection and now reads a history built entirely
from fixture data.

**New standing limitation — `engine-failure-propeller-only`.** The 23.367 model is
propeller-only: thrust `= HP·550·0.85/V` and Glauert windmilling `∝ DIA²`, both
from `ONENGOUT.BAS`, and 23.367(a) is itself turbopropeller-specific (Ref 1 Ch 11
p87). `concept_regional_jet` therefore enters **no** slice — run with a
shaft-power surrogate it produced 41–52 klb fin loads that never recover, with
windmill drag identically zero on a 0-in disc, which is the wrong-card-outranks-
missing-card case. Single owner `one_engine_out.PROPELLER_ONLY_NOTE`, quoted by
`report.methods._standing_limitations()` so it reaches every methods stamp, with
the key set and the one-wording guard extended in `tests/test_methods_stamp.py`.
Enforcing it (refuse/caption on a non-propeller installation) stays open as
backlog M4-3(b).

---

## Standing disclaimer in the methods statement (0.5.0 Phase 2 row 1 — complete 2026-08-11, tier S)

Closed review finding **F-R3**: the "initial-concept loads analysis, not a
certification document" statement (SUMMARY_REPORT.md §4.6 item 9) lived on the
LaTeX title page alone and not in `methods_statement`, so it reached neither
`METHODS.txt`, the CSV `#` headers, the deck `$` headers nor the workbook. It is
now the `STATUS:` block leading the statement (ahead of `BASIS:`), one
`STANDING_DISCLAIMER` constant that the title page quotes rather than restates,
with `tests/test_methods_stamp.py` requiring the block, both wrappers and the
single wording.

---

## Per-case SF in the governing-loads tables (0.5.0 Phase 2 — complete 2026-08-11, tier M)

Closed review finding **F-R1**, the report-side pre-slice of M4-8 Layer 1.
`report.governing_loads_table` scaled and labelled every row with the flat
`ULTIMATE_FACTOR` while the model contract puts the factor on the case
(`CriticalCondition.safety_factor`) and the export side already read it
(`sbeam_bridge._sf`) — so the first non-1.5 critical case would have been
mis-scaled and mis-labelled in report §5 and in both GUI views that share the
helper, and a report figure could have disagreed with its own bulk-data card.
Each row now takes its own case's factor and states it in the `SF` cell. The
**caller-supplied `sf` override is removed** rather than defaulted (practice 3:
one owner, no second path to a flat factor); no caller passed it. No shipped
number moves — SELECT stamps the 23.303 default throughout today — so no digest
regenerated. `tests/test_results_review.py` stops pinning the hole (every row
`SF == 1.5`) and asserts the contract instead, with a new test that sets one
condition to `SF = 1.0` and checks the row is neither re-scaled nor stripped of
its `-ULT` marker while its neighbours are unchanged. `PROGRAM_SPEC.md` (SELECT,
M2-4) states the per-case rule.

---

## Limitations completeness, and the caveat's one wording (0.5.0 Phase 2 row 2 — complete 2026-08-11, tier M)

Closed review finding **F-R4**; decision **D-R3** for the ground-case statement.
`_STANDING_LIMITATIONS` claimed to be every open caveat and was missing four —
the fin-only lateral aero (L-7), the lumped aileron couple, the wing stick
model's centreline clamp and the flight-only fuselage deck, the last now a
positive claim rather than two adjacent absences. The **assumed tail planform**
joins them as a *conditional* limitation: `resolve_tail_planform` marks a derived
rectangle ASSUMED and that marker reached the page, the CSV and the result and
stopped, so the controlling document described the distribution as if the
planform had been entered. It is resolved from the project's own inputs, so a
headless bundle states it too, and no shipped fixture enters one.

**One wording per caveat.** Where a caveat also travels in band, the report
quotes the owning module's constant rather than paraphrasing it —
`balance.LATERAL_AERO_NOTE`, the new `balance.AILERON_COUPLE_NOTE` (extracted
from the ACRL case note with its text unchanged, so no deck byte moved) and
`sbeam_bridge.CENTERLINE_CLAMP_NOTE` (reworded once to serve both the deck and
the document; `wing_stick` digests regenerated). **The completeness guard** is
the point of the step: standing limitations carry stable keys, the key set is
pinned by test, and separate tests assert each one reaches the statement, that
the in-band and report wordings are one string, and that the conditional
planform caveat disappears when a planform is entered. `SUMMARY_REPORT.md` §4.6
states the contract.

---

## The fuselage deliverables rendered a platform-dependent negative zero (defect — complete 2026-08-11, tier S)

Found from a CI report of `sbeam/body_cards` drift against the Imperial digest
baseline on a commit that passed locally. The body deck's stated `Applied Fz set
sums to …` and `Terminal Myy …`, and the span CSV's terminal cumulative
`Sz`/`Myy`, are the free-free equilibrium: exactly zero in exact arithmetic,
~1e-11 of cancellation dust in floating point. The magnitude is far below any
printed precision; the **sign** is not reproducible across platforms, because
x86 and ARM reassociate the upstream arithmetic differently — so one machine
printed `0.00` and the other `-0.00`, and a digest baseline whose job is to
answer "did any Imperial byte move?" answered yes for a difference that is not
one.

`sbeam_bridge._closed()` snaps a zero-by-construction quantity to an unsigned
zero, relative to its own column's scale so it cannot mask a real residual on a
heavy airplane — the rule the `FORCE` cards already had (nothing under `_TOL` is
emitted) extended to the totals that describe them. Guarded by
`test_the_body_deliverables_never_render_a_negative_zero` in both unit systems,
SI being the worse case at 175× the dust. Structural negative zeros elsewhere
(`-0.000000E+00` from `-1 × 0.0`, ~2,000 in a balanced deck) are bit-identical
on every platform and cosmetic; filed as its own backlog row rather than folded
in, because normalising them moves every deck family's digests.

---

## Manifest § renumber + a single owner for the report's section numbering (0.5.0 Phase 2 row 1 — complete 2026-08-10, tier M)

Closed review finding **F-R2**. The bundle manifest's "Summarised in" column
sent the case index to §3, the load-case CSVs and the text report to §4 and
METHODS.txt to §5 — each one section short after the §2 sign-conventions
insertion, and methods two short after the §6 balanced section moved it to §7 —
and the tail rows named a "§4 Tails" subsection that never existed. Corrected to
§4 / §5 / §7 and to the real `Horizontal tail / Vertical tail` headings.

Fixed **structurally** rather than by re-typing (`CLAUDE.md` practice 3, second
time this bit): `content.SECTIONS` is the ordered `(key, title)` single source,
`section_heading(key)` builds every heading and `section_ref(key[, subsection])`
every cross-reference — the manifest column plus the rendered prose in the
references table, the gear note and the balanced section. A literal `§N` in
rendered text is now a defect. Pinned four ways in `tests/test_report_content.py`,
since the finding was precisely that nothing pinned the values: the owner's
numbers must equal the document's own section positions; each companion file's
target is pinned by key in `SUMMARISED_IN`, exhaustive on the GA fixture so a new
row cannot slip in unpinned; every manifest reference must resolve to a real
section and each suffix to a real subsection; and a document-wide sweep of every
rendered string rejects a reference past the last section. Spec updated in
`PROGRAM_SPEC.md` (summary-report section) and `SUMMARY_REPORT.md` §4.7.

---

## Wing deck `$` width + centerline-clamp header line (0.5.0 Phase 1 row 1 — complete 2026-08-10, tier S)

The wing stick model's `SPC1` now carries the plan 10 §1.1 caveat naming the
clamped node as the aircraft **centerline** (BL 0) and its reaction as the
**half-span total applied load**, not a wing root design load — with why moving
the SPC would not help (one clamp reacts the whole load wherever it sits; the
side-of-body quantity is an internal CBAR load and the deck has no node there) —
and every generated `$` sentence in the bridge is emitted through one
`sbeam_bridge._comment()` wrapper at the 72-column free-field card width, so
`test_deck_comments_fit_the_free_field_card_width` drops its wing carve-out and
sweeps `wing_cards`/`wing_stick` in both unit systems. The unit statement became
its own `$ Lengths in <unit>.` line (wrapping can split a clause, not a line).
Closed the release's last Phase-1 row and spent the wing decks' digest
regeneration: `fixtures_imperial/digests.json` moved on exactly
`sbeam/wing_cards` + `sbeam/wing_stick` across all six examples, no calc number
and no other deck family.

---

## The 23.427(a) handed balanced h-tail family (0.5.0 Phase 1 row 1 — complete 2026-08-10, tier L)

Closed review finding **F-R5**; decision of record **D-R8**; design note
[`../30_future/16_d_r8_unsymmetrical_htail_note.md`](../30_future/16_d_r8_unsymmetrical_htail_note.md)
(agreed in chat before code, `CLAUDE.md` practice 1). The release's one L-tier
physics step.

**Objective.** Give the assembled deliverable the one horizontal-tail condition
that has a **hand**. FAR 23.427(a) applies 100 % of half the governing symmetric
tail load on one side and `min(100 − 10(n−1), 80)` percent on the other; the
full-span tail topology (plan 09 decision **T-8**) was built to carry exactly
that asymmetry, and nothing assembled it — the gap was not even filed. Every
other h-tail condition is symmetric and already rides every balanced case as its
trim tail load, which is a statement the record should make rather than an
absence a reader has to infer.

**Deliverables.**
1. **A third component branch in `build_balanced_cases`**, with `htail_sets` as
   `fin_sets`' sibling: SELECT's split **distributed** over the full-span
   `tail_span` table through the `coordinates.py` frame owner (span → `y`,
   normal → `fz`, torsion → free `my`), tagged `htail-air`, at the tail's own
   waterline. **Air only** — the surface's mass items stay in `body_inertia` and
   are accelerated by the closure field, so each mass enters exactly one field
   (the seam decision L-8 holds for the fin). The set **replaces** the lumped
   trim tail load: `RH + LH` is the condition's whole tail load, and carrying
   `vn.lt` beside it would count the balancing part twice.
2. **The residual restated for the family, in-band.** 23.427(a)'s load is a
   *maneuver* load whose V-n point is a balanced one at `n_z ≈ 1`, so the
   airplane is genuinely out of trim: pre-closure −49.8 % of `n·W` and 144 % of
   `n·W·MAC` on `ga6_normal`, closing as Δn −0.496 g and q̇ +637 deg/s² — an
   abrupt elevator input, reacted by inertia relief, which is what sizes the aft
   fuselage. Reported, never gated; the gated statement is the case's **trim
   half** (0.301 % / 0.694 %). Said on the deck header, the case notes, report
   §6, the case table and the Balanced Cases page.
3. **Handedness from the distribution's own roll.** The case carries no side
   force and no free `mx`, so `is_handed` gained a net-rolling-moment test
   against `HANDEDNESS_TOL · n·W · b/2`; the twins come from the existing
   reflection machinery, and `HT-09R`/`HT-09L` (SUBCASE 7209/8209) are
   23.427(a)'s "either side" in the deck.
4. **A defect the family exposed: the closure was referred to the entered CG.**
   The relief field is now solved about the **mass set's own centroid**. The two
   coincide on every loading the fixtures carried before, which is why a
   decoupled `n = F/W` solve never showed it; `ga6_normal`'s `CG4` sits
   0.0024 in forward / 0.0052 in below its entered CG, and an angular
   acceleration about the wrong point leaves `−ω̇ × Σ wᵢrᵢ` unclosed — 0.31 lb of
   `Fx` at 637 deg/s², four orders above the closure gate. Reported residuals
   stay about the CG; only the relief moved.
5. **The assembly record stops mis-stating the h-tail.** New reason code
   `htail-symmetric` ("already in every balanced case, as the trim tail load"),
   plus `no-htail-loads`; `out-of-family` narrows to the fuselage, ground and
   one-engine-out conditions it actually describes.

**Test / Acceptance.** No printed oracle exists for an assembled airplane, so
the gates are closed forms and independent producers (`CLAUDE.md` practice 2),
all in `tests/test_balance.py` unless noted: each applied half equals SELECT's
own `RH`/`LH` exactly and the twins swap them; the applied roll equals
`(RH − LH)·ȳ` from the planform (ratio 1.000000000 on both fixtures); the trim
half closes inside 1 %; the case's whole roll is the tail split's own moment and
nothing else; six-DOF closure in memory **and** re-derived from the deck's own
card text; the deck reacts to zero in sbeam in both unit systems
(`tests/test_sbeam_roundtrip.py`); the closure's centroid reference asserted as a
property against a loading where the two points really differ; and the assembled
set pinned per fixture. Imperial baseline regenerated for `csv/balance`,
`txt/balance` and `sbeam/balanced_deck` on the two fixtures that assemble — and
nothing else.

**Key decisions.** **D-R8.1** the full 23.427(a) load is applied and replaces
the trim load (rejected: the asymmetric increment alone, which keeps the case
inside the 1 % gate but puts one sixth of the tail's design load in the
assembled model). **D-R8.2** `Fz`/`My` reported rather than gated, with the trim
half as the gate (rejected: widening the gate for every family). **D-R8.3** air
only. **D-R8.4** handedness from the net applied roll. **D-R8.5** the relief
field is referred to the mass centroid. SELECT, `tail_span` and every
per-component deck are *read*, never recomputed — no Appendix A figure moves.

---

## `concept_heavy` in the sbeam round-trip gate (0.5.0 Phase 1 row 1 — complete 2026-08-10, tier S)

Closed the remainder of decision **D-R6** (its diagnosis, review **F-C6**, had
already restored the export): `concept_heavy.project.json` joins `WING_MATRIX`
in `tests/test_sbeam_roundtrip.py`, so its wing deck solves in the real solver
in both unit systems. It is the matrix's only fixture whose wing cases name only
a V-n `case` reference, which puts the *derived* CL/V route — the one F-C6 fixed
— under solver coverage for the first time, and its 600 lb-per-side store gives
the offset-couple `MOMENT` cards a second geometry beside `atr42_100`. Wing leg
only (the fixture assembles no balanced case); no shipped bytes move; plan 10
§8.2's defect note is marked closed.

---

## Minted balanced SUBCASE ids (0.5.0 Phase 1 row 1 — complete 2026-08-10, tier M)

Closed review finding **m1**; decision of record **D-R7**. The assembled deck's
`SUBCASE`/`SID` ids are minted from the case's own `CaseRef` through the new
`case_ids.balanced_subcase_id` — a per-hand block plus `subcase_id` (symmetric
`5000`, starboard `7000`, port `8000`: `W-05R` → `7105`) — retiring the
positional `BALANCED_SID_BASE + i` that renumbered every later case whenever one
condition dropped out of the set; the three blocks are registered bands pinned
against `case_ids` by `tests/test_bands.py`, `balanced_deck.case_sids` refuses
two cases minting one id, survival across a dropped case is a test of its own,
and the two balanced-deck Imperial digests are regenerated for this and nothing
else.

---

## Fin chordwise deck → Fy (0.5.0 Phase 1 row 1 — complete 2026-08-10, tier M)

Closed review finding **F-C3**; decision of record **D-R4**. The chordwise tail
deck routes every station through `coordinates.tail_force_to_airplane` (the
single owner the span family already used), so the fin's normal force leaves as
`Fy` — a side force — instead of the hand-rolled `Fz` that `coordinates.py`
itself names as the canonical splice trap; each case block and the `GRID` block
state the axis in-band, and the CSV's `Fz` column becomes `Fn` plus an `Axis`
column so the two chordwise deliverables cannot disagree.
`test_tail_deck_resultants` and the tail round-trip leg are re-pinned to all six
resultant components (the zeros included — summing `v[2]` for both components is
what enshrined the defect); Imperial baseline regenerated, `sbeam/tail_cards` +
`sbeam/tail_chordwise` only.

---

## Balanced deck + CONM2 first-class (0.5.0 Phase 1 row 1 — complete 2026-08-10, tier M–L)

Closed review finding **F-D2**; decision of record **D-R2**.

**Objective.** End the state where the mission's *primary* deliverable was
page-only and invisible to the controlling document. `balanced_airframe.bdf`
downloaded from the Balanced Cases page unstamped, appeared in no report
section, no manifest row and no Export bundle; the three CONM2/MASSSET files
left the Weights page the same way. An artifact the report does not name travels
without a basis, which is the one thing the G8.3 stamp and the manifest exist to
prevent.

**Deliverables.**
1. **Report §6 — "Balanced free-free airframe cases."** What the model is (full
   span, aero + inertia, free-free, the determinate support whose reaction *is*
   the residual), then per case: `Nz`, the **pre-closure** residuals against the
   1 % gate, the applied roll couple, and the closure relief `Δn`/`Δn_y`/yaw and
   roll acceleration. The rows are literally `balanced_case_rows`' — the deck's
   and the page's own row builder — so §5's nothing-is-recomputed rule holds for
   the primary deliverable too. Plus the handed twin-pair statement and the
   **mass-case identity** table (payload case → `MASSSET` SID/label, the
   loading's own weight and CG, ballast fraction, and NOT EXPORTED with its
   reason for a case the database cannot produce). Sections renumbered: methods
   is now §7.
2. **Manifest rows** for the assembled deck and all three mass files, each with
   units, convention and summarising section — and *only* when the bundle will
   contain them.
3. **The Export bundle and page** carry all four artifacts, stamped and in the
   bundle's resolved unit system.
4. **The two page-level routes are stamped** — the Balanced Cases deck and the
   Weights page's fragment / check deck / inertia-only set.
5. **Single owners, per practice 3.** `mass_cards.massset_identity` is the sole
   mint of a payload case's identity in the exported model (cards, report and
   manifest read it); `mass_cards.mass_case_rows` is its row form;
   `content.balanced_run` assembles the balanced cases **once** per document and
   is shared by §4's skipped-conditions record and §6.

**Test / Acceptance.** Seven new `tests/test_report_content.py` cases: the §6
table *is* `balanced_case_rows`' output column for column; the twin-pair
statement and both hands appear; the MASSSET identity matches
`massset_identity`'s mint and every payload case is listed; a non-derivable case
reads NOT EXPORTED (`concept_regional_jet`); an empty project keeps §6 and
states the absence; the manifest lists all four files pointing at §6, and lists
none of them when the bundle would not contain them. The Export page's two
source guards were extended in the same motion — stamp application from 5 decks
to 9, bundle-system coverage from 11 writer calls to 14 plus the balanced deck.
Full suite green, ruff clean. **No exported byte moved** and no digest
regenerated: every writer was already stamp-capable and the decks themselves are
unchanged.

**Key decisions.**
- **D-R2 (user, 2026-08-10):** the balanced deck and the CONM2 model are 0.5.0
  deliverables, not polish — CLI targets and stamps (shipped with the CLI row),
  bundle and manifest rows, and a balanced-cases report section.
- **§6 is a top-level section, not a subsection of the results summary.** The
  assembled model is the primary output and the per-component results are views
  of it; burying it under them would state the opposite. `SUMMARY_REPORT.md`
  §4.5.1 is its normative clause (the standard's numbering has never mapped 1:1
  onto document section numbers).
- **The manifest is two-sided.** Listing an artifact that was not written is a
  worse failure than omitting one, so both directions are pinned by test.
- **The mass table reports the loading's own weight and CG**, never the payload
  case's nominal figures — the same rule the exported cards follow.

---

## CLI deliverable completion (0.5.0 Phase 1 row 1 — complete 2026-08-10, tier M)

Closed review findings **F-D1**, **F-C2**, **F-D3** and minor **m2**, absorbing
the long-open **L-8g**; decision of record **D-R5**.

**Objective.** Make the 0.5.0 deliverable set *scriptable*. The mission is a
concept-loads → sbeam sizing loop run headless, and the CLI reached only part of
it.

**Deliverables.**
1. **The export menu is the deliverable menu** (F-D1). `--export-target` gains
   `body` (FORCE deck + span CSV + wing-attach fitting CSV), `balanced` (the
   assembled full-span free-free deck — the mission's *primary* artifact, until
   now downloadable only from the Balanced Cases page) and `mass` (the
   CONM2/MASSSET model, routed to the same owner and the same file names as
   `--export-conm2`). `cli.EXPORT_TARGETS` is the single list, handed to argparse
   and pinned against the CLI docstring in both directions. Three `write_body_*`
   writers were added for symmetry with every other component family, and
   re-exported from `sloads.export`.
2. **The CLI wing deck is stated about the LRA** (F-C2 / D-R5). `_export_sbeam`
   passed the writers a bare result list, so `_as_results`' `Project` branch —
   the one calling `loads_ref_axis_results` — never ran, and headless torsion,
   station X and lever arms were about the 25 % chord while the GUI's were about
   the loads reference axis. Both front-ends now build the deck the same way.
3. **The G8.3 methods stamp reaches every headless file** (F-D3 / L-8g),
   including `-o` module CSVs and all three `--export-conm2` artifacts. Required
   threading `header_comment` through `write_span_load_csv`,
   `write_tail_chordwise_csv`, `write_control_surface_csv`, `conm2_fragment`,
   `mass_check_deck`, `inertia_only_cards` and `balanced_deck` (+ their writers),
   all applied through the existing `_stamped` owner. One stamp per run, built
   from the resolved unit system and shared by every writer.
4. **One error contract** (m2): `error: <message>` on stderr, exit 1, no
   traceback and no partial artifact set, on every route.

**Test / Acceptance.** New `tests/test_cli.py` (35 cases): every target writes
its named artifacts non-empty on `ga6_normal`; the balanced deck and the
`mass`/`--export-conm2` pair are byte-identical to the page/CLI counterpart;
`MyyAxis` reads `LRA 40% chord` and both front-ends' wing artifacts match, on a
constructed non-quarter-chord project; every exported file starts with its
methods block, stays parseable (`csv.DictReader`, `export.equilibrium.parse_cards`)
and is byte-stable across runs; and each target on an empty project returns 1
with one `error:` line. Full suite green (1444 passed), ruff clean.

**Key decisions.**
- **D-R5 (user, 2026-08-10):** the CLI transfers to the LRA; the 25 %-chord CLI
  behaviour is retired, not optioned.
- **`--export-target mass` and `--export-conm2` are two spellings of one owner**,
  the second kept only because it shipped first; pinned byte-identical so they
  cannot drift into two copies of the mass model.
- **No `$` analogue of `strip_comment_lines`.** A deck's `$` lines are mostly the
  deliverable itself (subcase map, axis statement, residuals), so the stamp is
  not separable by line prefix; tests assert a stamped deck *ends with* its
  unstamped build instead. Stated in the function's own docstring.
- **The stamp carries no timestamp unless `--generated` supplies one**, so two
  headless runs of one project stay byte-identical and diffable.

**Measured.** Contrary to the backlog's sequencing note, this row moved **no
exported bytes** and forced no digest regeneration: `ref_axis_pct` is 0.25 on
every shipped fixture, so the LRA transfer is a no-op there — which is why the
axis gate is pinned on a constructed project rather than a fixture.

---

## Skipped-conditions record (0.5.0 row 1 — complete 2026-08-10, tier M)

Closed review finding **F-C7**: a condition SELECT named could drop out of the
assembled balanced deliverable — no V-n point, unknown CG case, non-derivable
loading — with no record on the `ModuleResult`, in the deck or in the report,
and the only guard was a test pinning the *shipped fixtures'* drop set
(`concept_regional_jet` has been silently missing NMAA). `build_balanced_cases`
now takes an optional `skipped` list and records a `SkippedCondition`
(component, condition, V-n point, one of five reason codes, and a reader-facing
reason owned by `SKIP_REASONS`) at every drop path, including the deliberate
out-of-family exclusion. Stated on three surfaces from the one wording owner
(`skipped_condition_lines`, grouped by reason): the module result's final
"Assembly record" condition, the deck's `$ CONDITIONS NOT ASSEMBLED` block, and
report §4 — always emitted, so "every condition assembled" is itself a
statement. The gate is the property rather than the fixture:
`test_every_condition_is_either_assembled_or_recorded` asserts assembled ∪
recorded == SELECT's set, disjoint, with every reason a declared one, on all six
examples. `PROGRAM_SPEC.md` (balanced-cases bullet) states the contract; the
Imperial baseline was regenerated for the three affected channels on the two
fixtures that assemble.

---

## WING-item mass partition guard (0.5.0 row 1 — complete 2026-08-10, tier M)

**Objective.** Close review finding **F-C5**: WING-tagged item mass could leave
the balanced model entirely when WINGINER integrated no wing panel.

**Deliverables.** `balance._wing_inertia_scale` raises `MissingInputError` when
the loading carries WING item mass against a non-positive panel, naming the
orphaned weight and both remedies; only a loading with no WING item mass scales
to 0.0, and `assemble`'s note now states *that* cause instead of blaming the
panel. `wing_inertia._root_density` short-circuits a non-positive target to an
empty panel. `PROGRAM_SPEC.md` states both (WINGINER notes; the balanced-cases
bullet).

**Test / Acceptance.**
`test_wing_items_with_no_panel_model_raise_rather_than_vanish` (ga6's 330 lb of
wing items against an emptied panel) with
`test_no_wing_items_and_no_panel_still_weighs_the_case` as its other half, and
`test_an_empty_panel_weight_gives_an_empty_panel` on the density iteration.

**Key decisions.** *Raise, not lump* (user, 2026-08-10): the input is
inconsistent rather than a load case, and `wing_mass_tie` already reports it —
lumping the items at their own stations would also have to move the L-3
self-inertia predicate to keep the point set and the free-moment set together.
*Fix the density iteration at source*: `panel_weight_lb = 0` never produced the
zero panel the finding assumed — the ±1 % band is empty at a zero target, so the
iteration returned **negative** strip masses (−0.108 lb on `ga6_normal`) and the
scale turned them into a ×−3045 sign-flipped inertia set that still weighed the
case, passing every existing mass gate. Practice 4 (generalize on first find):
the guard is worthless without it, since the raise would never have fired on the
input that actually reaches it.

---

## Degenerate-profile raise (0.5.0 row 1 — complete 2026-08-10, tier S)

Closed review finding **F-C4**: `_trapezoid_tributary_forces` — the one owner of
both chordwise writers' arithmetic — raises when a profile integrates to zero
under a non-zero case load, instead of scaling by 0.0 and emitting an empty load
set under a header still claiming the applied sum. A zero case load keeps the
zero set (nothing to contradict). Pinned by
`tests/test_sbeam_bridge.py::test_degenerate_chordwise_profile_raises`, which
covers both the all-zero and the cancelling-antisymmetric profile on the tail
and control-surface paths.

---

## Envelope single-owner sweep (0.5.0 row 1 — complete 2026-08-10, tier M)

Closed review finding **F-C6**: the four surviving `project.envelope` bypasses
(`net_loads._air_cl_v`, `wing_inertia` ×2, `body_loads`, `balance`) now go through
`select.default_envelope` / the new `default_critical` / `vn_points` / `vn_by_case`
— `registry.run_all_modules` never assigns `Project.envelope`, so headless the
derived wing-case route yielded no cases, wing `CaseRef`s named no CG or altitude,
`body_loads` integrated persisted conditions against a rebuilt V-n matrix, and
`balance` accepted a persisted envelope with an empty `vn` and dropped every case.
`tail_span`/`taildist` delegate to the owners too, and the two wing modules share
one `wing_case_sources(project)` resolved per build. Guard:
`tests/test_envelope_owner.py` — an AST scan of `sloads/` for direct reads
(allowlist entries each state their reason) plus a behaviour gate per site, six of
which fail against the pre-fix code. Imperial output moves in one place, metadata
only (`atr42_100`'s wing case index/`$ SUBCASE` line now state SELECT's CG, speed,
altitude and FAR reference, as they always did with a persisted envelope); no load
number changes anywhere.

---

## GID/EID/SID band registry + exhaustive disjointness (0.5.0 row 1 — complete 2026-08-10, tier M)

**Objective.** Close review **F-C1** (the balanced deck's `4001+` nodes collided
completely with the spanwise tail decks' `4001–5000`) by fixing the root cause the
review filed as **F-G3**: id bands were per-file constants plus prose, and both
disjointness guards hand-enumerated the families they knew about, so neither could
see a new one. `CLAUDE.md` practice 3 — one owner plus a drift guard.

**Deliverables.** `sloads/export/bands.py`: `Band` (name, kind, start, size,
owner, note, `clear_of_gids`), the `BANDS` registry with the whole GID/EID/SID map
in its module docstring, `band()` / `bands_of_kind()` / `owner_of()` /
`overlaps()`. Every allocator in `sbeam_bridge`, `balanced_deck`, `mass_cards` and
`roundtrip` now draws from it through `Band.allocate`, which raises on overflow;
the per-module `*_BASE` constants remain as aliases for callers and deck headers.
New `control_station_gid`, and a capacity guard on `station_gid` (review **m5**).
The balanced deck re-banded to `6001/6201/6401`. `_trapezoid_tributary_forces`
folds the duplicated chordwise tributary arithmetic (review **m6**).

**Test / Acceptance.** `tests/test_bands.py`: pairwise disjointness over the whole
registry; the pre-fix `4001+` band re-declared and shown to collide (the gate has
teeth); allocator end-points and overflow raises per band; the public base
constants pinned to their bands; `case_ids.SUBCASE_BLOCK` pinned against its
mirror. The blind-spot killer is
`test_every_export_base_constant_is_a_registered_band`, which walks the **module
globals** of every module under `sloads/export` and fails any id-base constant
that is not a registered band's start — a new deck family cannot re-open the hole
by forgetting a test. The two former hand-enumerated guards
(`test_gid_blocks_are_disjoint`, `test_mass_eids_are_disjoint_from_every_gid_band`)
now assert only what a registry cannot: that the ids on the cards each fixture
actually emits fall inside their owner's band.

**Key decisions.** (1) Balanced GIDs went to `6001+`, not `5001+`, so the number
does not read as the balanced `SUBCASE`/SID base. (2) GID/EID cross-namespace
disjointness is declared **per band** (`clear_of_gids`) rather than assumed: the
`CONM2` bands take it so a spliced mass-plus-load deck has one owner per id, and
the stick model's `CBAR` chain declines, having numbered 1..n alongside its own
GRIDs since the first deck. (3) `case_ids.SUBCASE_BLOCK` stays the allocator for
per-component subcase SIDs — calc must not import export — and the registry
mirrors it under test. (4) The re-band moves exported bytes: the two balanced-deck
digests were regenerated after confirming the pre-fix deck is reconstructible
byte-for-byte from the new one by shifting node numbers alone.

---

## Six-DOF deck closure gate (0.5.0 row — complete 2026-08-10, tier S)

Closed review finding **F-G1**: `test_the_deck_balances_from_its_own_cards` now
re-derives `fy`/`mx`/`mz` from the card text beside `fx`/`fz`/`my`, roll and yaw
judged against the semi-span (the lever `roll_residual_fraction` uses).
`test_the_lateral_half_of_the_deck_gate_has_teeth` calibrates the gain — one
reversed lateral `FORCE` card puts `fy` 3.4 %, `mz` 3.1 % and `mx` 0.20 % out
while the three DOF the gate already had stay at 1e-9…1e-8. Swept to the body
deck's free-free gate in the same change (practice 4); those four are zero by
construction on a planar flight-only deck and are meant to go red when the ground
cases land.

---

## SI mass-check `GRAV` fix + CONM2 round-trip CI leg (0.5.0 row 1 — complete 2026-08-10, tier M)

Closed the 0.5.0 review's CRITICAL **C1** and MAJOR **F-G2** together, because
they are one defect and its missing gate. `mass_check_deck` wrote
`force/(mass × length)` as its `GRAV` acceleration — the mass channel's
dimensional identity, 386.0886 in **both** systems — so the SI deck shipped
gravity 25.4× low under a header claiming mm/s², and the mass family was the one
deck family the round-trip harness never solved. Fix: `units.DeliverableUnits.gravity`
(`force.factor / mass.factor`) as the single owner, with a drift guard pinning
386.0886 in/s² / 9806.65 mm/s² against quoted figures. Gate: the mass-check deck
is now the harness's fourth family, solved in **both** unit systems on three
fixtures — sbeam accelerates the `CONM2` set through its own mass matrix and must
reproduce sloads' per-case inertia at every node, with the C1 defect itself
reproduced as the leg's sensitivity test. `inertia_only_cards` gained an optional
`loading` so there is something exact to compare against (the gross Ch 15 table is
case-independent and carries no wing mass; default output unchanged).

**Found on the way, and pinned rather than worked around:** sbeam's SOL 101
assembles its `GRAV` load vector from the **baseline** mass matrix and never
reaches the `MASSSET` resolver, so every payload subcase of the shipped deck
accelerates the same mass (`ga6_normal`: 2063 lb four times, against
3400/3400/2800/2063). The leg folds each case into a baseline deck first
(`roundtrip.flatten_mass_case`, test-only, re-selects cards but never rewrites
one); `test_the_shipped_mass_deck_hits_the_sbeam_massset_gap` records the
behaviour and is meant to go red when the sbeam pin is bumped past the fix.

---

## The report's sign-convention section, and decisions SC-1…SC-6 (design note 15 — complete 2026-08-10, tier M)

The summary report gained a required **"2. Axes and sign conventions"** section
(SUMMARY_REPORT.md §4.2.1): frame/reflection prose, a conventions-of-record
table, and three static inline-TikZ figures, single-sourced in
`report/conventions_tex.py` and drift-guarded by
`tests/test_report_conventions.py`. The full-code sign-convention extraction
behind it is stamped in `CONVENTIONS.md` §1.1, and its six genuinely unstated
conventions were user-approved as **SC-1…SC-6** (β, rudder, rate/attitude
labels, twist sign — verified in the Schrenk basic-lift formula, gear V/D/S,
aileron hand). Labels and presentation only; every oracle bit-for-bit.

---

## The empennage mass SSOT, and the fin's two-axis inertia (complete 2026-08-10, tier L)

**Objective.** Close the filed defect "`tail_mass` is a parallel mass model no
fixture populates — the tail decks carry no inertia", and, by user decision taken
with it, give the vertical tail the inertia that plan 13 decision **L-8** had
deferred to the balanced case. Design note agreed in chat 2026-08-10 (this
entry records it); it extends plan 09 decisions **T-3**/**T-9** and plan 11
decision **B-2**.

**The defect.** `tail_span._surface_weight` read `Project.tail_mass` and nothing
else, and **no shipped fixture ever set one** — so it returned 0 on all six
airplanes and *every h-tail deck the suite had ever produced was air-only*, while
`weight.items` carried the tail mass correctly the whole time (`ga6_normal`
42/23 lb, `concept_regional_jet` 520/640). Plan 11 B1 had derived
`fuselage_mass.stations` from the item SSOT and left `TailMassInput` behind. The
consequence was an *omission* that announced itself in a note and in no number,
which is why it survived: plan 09's T-3 inertia had never actually run on a
shipped fixture.

**Two further defects it exposed**, both swept here per required practice 4:

1. **Every exported tail deck took the `n = 1.0` fallback.**
   `_load_factor` read `project.envelope` directly rather than through
   `select.default_envelope`, the single owner (M2R-8) — and
   `registry.run_all_modules`, the path the Export page and CLI use, never
   assigns `project.envelope`. Every condition reported "names no V-n point" and
   took `n = 1.0`, understating h-tail inertia by up to **3.8×** on exactly the
   balancing cases that size the surface. Invisible while the weight was zero;
   a wrong number the moment it was not.
2. **`balance.fin_sets` would have applied the fin's mass twice** — its docstring
   promised an air-only applied set, and `WingStationLoad.fz` silently stopped
   being one when the fin gained inertia.

**Deliverables.**

- **`mass_distribution.tail_surface_weight`** — the single owner. Derived from
  the `htail`/`vtail`-tagged items; `TailMassInput.panel_weight_lb` demoted to an
  explicit override behind the new `weight_is_override` (v44, hop
  `_v43_tail_mass_override`), exactly as `stations_are_override` did for the
  fuselage; `tail_reconciliation` reports the gap either way and
  `untagged_tail_surfaces` **names** a surface with no tagged item rather than
  reporting it as weightless (`concept_heavy` has no v-tail item).
- **The fin's two inertia terms.** A fin's normal axis is lateral, so the
  acceleration that bends an h-tail compresses a v-tail: bending
  `−n_y·W_vt` with `n_y = (LT25+LT50)/W_case` (new `lateral_load_factor`), and
  axial `−n_z·W_vt` along the span (new `WingStationLoad.f_span`/`.s_span`, new
  `coordinates.tail_axial_to_airplane`, carried in the same `FORCE` cards).
  `distribute()` now takes `n_normal`/`n_axial` separately so that passing a
  vertical factor for a fin's bending direction is not expressible.
- **`WingStationLoad.f_inertia`** — the inertia part of `fz`, carried separably so
  `balance.fin_sets` can take `fz - f_inertia` and each mass enters exactly one
  set.
- **GUI: `component` is editable on the Weights page** (it never was — `kind` was
  the only tag exposed), and the Tail Span Loads page's mass form is **deleted**:
  it shows the derived weight read-only, names untagged surfaces, reports
  overrides, and links to the page that owns the data. The fin's `n_y` and axial
  column join the case summary.

**Test / Acceptance.** 1322 passed, 21 skipped; `ruff` clean. Imperial baseline
regenerated — **only the six tail channels moved**, on all five tail-carrying
fixtures; no wing, body, control or oracle channel changed.

| Gate | Target | Achieved |
|---|---|---|
| Fin lateral inertia identity | `Σ inertia / Σ air ≡ −W_vt/W_case` | exact to `rel=1e-12`, every fin case, five fixtures |
| Fin axial column | `Σ f_span = −n_z·W_vt`, and no bending from it | exact; normal-direction closure unchanged to `1e-12` |
| H-tail inertia | `Σ = −n_z·W_ht` | exact — **non-trivial for the first time**, the weight having always been 0 |
| Derived weight | = each fixture's tagged items | 42/23, 45/25, 320/270, 350/300, 520/640, 400/none |
| **No air-only h-tail deck** on any shipped fixture | regression gate | passes on the untouched files |
| Applied fin set is air only | `= LT25+LT50` exactly | `rel=1e-12`, while the fin deck itself carries the inertia |
| Appendix A oracles | unmoved | unmoved (pure consumer, T-7) |

**Effect on the numbers.** `ga6_normal` h-tail surface total: `BAL UP` −30.9 %,
`BAL DN` **+26.0 %**, `UNCHECKED MAN DN` +3.0 % — the *down*-load cases grow,
which is decision T-9's point, since those are the conditions that size a GA
horizontal tail. Fin: `n_y` 0.155–0.178 on ga6, lateral inertia −0.68 % of air on
every case, axial −23.1 lb.

**Key decisions.**

1. **The tail weight is derived, not entered** (mirroring plan 11 B-2/B1). The
   entered value survives only as an explicit, marked override, because a stale
   file must not outrank the SSOT by accident while a deliberate one still can.
2. **L-8 is superseded for the per-condition view** (user, 2026-08-10). The
   balanced case remains the authority for a *balanced* lateral field; what
   changed is that the fin's own mass now appears in the fin's own deck.
3. **`n_y` is the fin's own load over the case weight, and the relief it produces
   is reported as unconservative.** It is the free-free lateral response to the
   only lateral aero the suite models, so it inherits decision **L-7** verbatim:
   with no fuselage or wing sideslip force, the real airplane's `n_y` is smaller
   and this relief is an upper bound on itself. Stated in-band on every fin
   result, deck header and UI row — the alternative, a silent 0.7 % relief in the
   unconservative direction, is exactly the kind of thing a reviewer must not have
   to derive.
4. **A fin condition with no V-n point gets no lateral term at all.** No case
   weight means `n_y` has no denominator; falling back to a gross-weight stand-in
   would put a number nobody entered into a structural load.
5. **The two load factors are separate parameters, not one.** `distribute()`
   takes `n_normal` and `n_axial`, so "a pull-up bends the fin sideways" is not a
   mistake the signature permits.

---

## Concentrated wing masses: offset couples in the exported deck (plan 14 — complete 2026-08-09, tier L)

**Objective.** Stop the exported wing deck smearing a concentrated wing mass
(engine, gear, fuel, store) to the nearest node, which made a twin's deck size
wing structure to a root bending moment ~2 % above the NETLOADS value the report
prints beside it. Design note
[`../30_future/14_concentrated_wing_mass_nodal_split_plan.md`](../30_future/14_concentrated_wing_mass_nodal_split_plan.md),
decision **D-1**.

**Deliverables.**

- **`sbeam_bridge._moment_defect`** — the per-station defect
  `δ[k] = mxx[k] − mxx[k+1] − sz[k+1]·dy`. The key result of the design note is
  that this is **recoverable from the published table alone**: it is identically
  zero wherever the lumped-at-nodes recursion built the column (both `airloads`
  and the panel part of `wing_inertia` do) and equals exactly `w·(y_c − y[j])` at
  the one station bracketing a mass at `y_c`. So the fix needed **no new input,
  no schema change and no access to `wing_mass.concentrated`** — and, being
  export-side only, **no calc file was modified**.
- **Offset couples on the `MOMENT` card** (`NodalLoad.mx`/`.mz`). A force at
  `y_c` is statically equivalent to that force at node `j` plus the couple
  `w·(y_c − y[j])`, so no load moves and the exported set reproduces the
  cumulative shear **and** bending at *every* node. The alternative in the filed
  item — splitting the force between bracketing nodes — closes only at the root
  and corrupts that node's shear by **22 % on `atr42_100`**; measuring that is
  what moved D-1.
- **`coordinates.bending_moment_vector`** — single owner of the bending sign map
  (`Mxx → +x`, `Mzz → −z`), so the asymmetry is not spelled out at the writer and
  copied again at its gate (required practice 3).
- **`Mzz` swept with `Mxx`** (required practice 4): the in-plane channel carried
  the identical defect, unfiled and ungated.
- **Span-load CSV** gains `Mx`/`Mz`, keeping its contract that the applied-load
  columns *are* the exported cards; deck `$` header states the couples and the
  consequence of discarding them.

**Test / Acceptance.** 1295 passed, 21 skipped; `ruff` clean.

| Gate | Target | Achieved |
|---|---|---|
| Root bending closure, **both channels, all six fixtures**, no exception | exact | `Mxx` was +1.91 / +1.11 / +0.44 %, `Mzz` +1.14 / +0.67 / +0.32 % → exact |
| **Every station**, shear *and* bending, deck-derived | exact | passed — the gate that separates the couple from the force split |
| Couples exist only where a concentrated mass does | zero elsewhere | exact zero on the three mass-free fixtures |
| **Real solver** (`atr42_100` added to the round-trip wing leg) | W-d = NETLOADS root `Mxx` | passed, both unit systems — proves sbeam honours `Mx` |
| No-op proof | BDF byte-identical | `ga6_normal`, `cessna_210`, `concept_regional_jet` unchanged; only their CSVs move (new columns) |
| Mutation check | gates must bite | couples suppressed → 15 card-text + **2 real-solver** failures, mass-free fixtures still green |

**Key decisions.**

1. **An offset couple, not a force split (D-1).** Both preserve `ΣF` and close at
   the root; only the couple is *exact*, because it is the rigid-offset transfer
   rather than an approximation. It also handles a mass outboard of the last
   station, which a split cannot (no node to transfer to). Stated cost: a
   consumer who applies the `FORCE` cards and discards the `MOMENT` set gets the
   old smeared bending back — said in the deck `$` header, not left to be found.
2. **The zero threshold is relative, not absolute.** `δ` is a difference of large
   nearly-cancelling numbers, so its noise floor scales with the column: residue
   reached **8e-10 lb-in**, straddling the bridge's existing `_TOL = 1e-9`.
   Emitting it unconditionally replaced clean `0.000000E+00` moment columns on
   every mass-free deck with float noise. `_DEFECT_REL_TOL = 1e-9` of the
   column's own scale gives ~14 orders of separation and is unit- and
   size-independent.
3. **Two findings recorded rather than silently absorbed.** `concept_heavy` has
   no wing deck in the Imperial baseline at all (the baseline does not build the
   envelope) — filed as its own backlog item, since it means one shipped wing
   deck is digest-uncovered. And the round-trip matrix contained no
   concentrated-mass wing, so the solver leg could not have caught this class at
   all; `atr42_100` was added to close that.

---

## The lateral (±β) empennage balanced cases (mission phase 4, step 8 — plan 13 B8a-3/B8a-4/B8a-5 — complete 2026-08-09, tier L)

**Objective.** Assemble the vertical tail's own FAR 23.441/23.443 conditions as
full-span free-free airplane cases — the first cases in the suite with a lateral
load factor at all — and put the assembled deck that carries them through the
sbeam solve leg. Plan 13 decisions **L-5** (what the residual of such a case
means), **L-6** (the handedness predicate), **L-7** (the lateral-aero
limitation) and **L-8** (where fin inertia lives).

**Deliverables.**

- **`balance.fin_sets`** — the fin's distributed side load in airplane axes, a
  pure consumer of `tail_span` (itself a pure consumer of SELECT), so the load a
  lateral case carries is the Appendix-A-locked one strip for strip and **no
  oracle is at risk from assembling it**. The frame change goes through the
  single owner in `export/coordinates.py`: span → `z` from the fin root
  waterline, normal force → `fy`, torsion → `mz` negated.
- **`balance.is_handed`** — one predicate, registered in `CONVENTIONS.md` §7 with
  its own drift guard, replacing B7's "a non-zero `unbal_moment`". Four handed
  pairs per fixture: `VT-01R`/`VT-01L` … `VT-04R`/`VT-04L`, eight new cases each
  (ga6 15 balanced cases, the RJ 14).
- **`balance.is_lateral` / `fin_load`** — the only readers of the `vtail-air`
  tag, so the deck header, the row table, the UI and the gates cannot drift about
  what a lateral case is.
- **Reporting**: the applied fin side load, `n_y`, `ψ̈` and `ṗ` on the module
  result; `Closure dNy`/`Yaw acc`/`Roll acc` columns in `balanced_case_rows`; a
  `LATERAL case:` block in the deck `$` header; a `ΣFy` column and a fin-load row
  in the Streamlit breakdown, which reported every lateral case as a row of zeros
  without it. The L-7 caveat travels as a **case note**, into the deck and the
  report, not only into documentation.

**Test / Acceptance.** 1275 passed, 21 skipped; `ruff` clean. Imperial baseline
regenerated for `csv/balance`, `txt/balance` and `sbeam/balanced_deck` on the two
fixtures that assemble cases — **every other channel byte-unchanged**, so every
per-component deck and every Appendix A oracle is untouched (**G8**).

| Gate | Target | Achieved |
|---|---|---|
| **G3** the assembled deck solves in sbeam, reactions ~0, now exercising `fy`/`mx`/`mz` | ~0 | passed unchanged, both fixtures, both unit systems |
| **G3 (control)** reverse the fin load alone and the support must react it | `+2·L_v·SF` | to export tolerance, both unit systems |
| **G7** handed twins are mirror images, extended to an odd *applied* set | exact | `fy`/`mx`/`mz` negate, `fx`/`fz`/`my` identical |
| **G9** the symmetric half still closes with the fin removed | 1 %, per-fixture ceiling | **exact** — a fin set carries `fy`/`mz` only |
| **G10** the four conditions pinned per fixture | as measured | fin load, `n_y`, `ψ̈`, `ṗ` at `rel_tol = 1e-4`; `n_y` also asserted as `L_v/W` |
| **L-6** the predicate itself | drift guard | handed on a set that nets zero; unhanded on a symmetric one |

**Key decisions.**

1. **Nothing balances a rudder kick, and the gate says so instead of pretending
   otherwise** (L-5). A lateral case's pre-closure `Fy`/`Mz` *are* the fin load
   in full, so plan 11's 1 % residual gate is meaningless on them — the same
   standing `ACRL`'s roll residual has had since B7. Gating them would either be
   vacuous or force a fictitious balancing load into the case. What is gated is
   the **symmetric half**, and it holds *exactly*, because a fin set carries
   `fy` and `mz` only. Asserted rather than argued: a frame-map slip landing the
   fin's normal force back on `fz` is precisely what would break it, silently.
2. **The pitch ceiling was split per family, not widened.** ga6 `SUDDEN RUDDER`
   0.341 % and the RJ's `SIDE GUST` 1.586 % are over the symmetric bounds — and
   are *not* lateral contamination, since the symmetric half of those cases has
   the identical residual to the last digit. They come from V-n points (14, 35,
   95) the symmetric families never visit. One merged number would have stopped
   the symmetric bounds from biting; the RJ figure is the largest instance yet of
   the already-filed "RJ low-CL cases exceed the 1 % pitch gate" item.
3. **Handedness is decided by the distribution, pre-closure** (L-6). `ga6_normal`'s
   `YAW TO SIDESLIP` nets −97.8 lb from parts worth −683 and +586, so a
   net-based predicate would mint a rudder-kick case **unhanded** and assemble it
   symmetrically — plan 11 §10's `TORS` failure from the opposite direction. And
   reading the *final* load set would hand every rolling case, since B8a-2 gives
   those a lateral relief field.
4. **A zero-target gate is worth only its sensitivity** (B8a-4). G3 passed on the
   lateral subcases at the first attempt, which is exactly when to distrust it,
   so it gained vacuity guards (every case present as a subcase; each lateral one
   carrying real side load into the solver) and a **negative control** that
   reverses the fin load alone and asserts the support then reacts `+2·L_v·SF` —
   the load twice over, since the closure still relieves the original.
5. **G10's `ψ̈` targets were restated from measurement, and the plan amended.**
   Plan 13 §3.1's figures were taken against the placement-only `Izz` that
   preceded L-3; against the shipped tensor ga6 `SUDDEN RUDDER` is 178.05 deg/s²
   rather than 205.7 — ratio 0.866 where `Izz` alone gives 0.886, the difference
   being the `Ixz` coupling. Fin loads and `n_y` are unchanged from §3.1 to the
   last digit, because they do not depend on the closure.

**Found and fixed in passing.** The deck's subcase-map `$` lines ran past 72
columns once the condition names got longer than the four-letter wing ones; they
are wrapped now rather than hand-broken. `roll_moment_fraction`'s docstring
claimed the aileron as the only source of `residual_mx` — a fin above the roll
axis is another (1.2 % of `n·W·b/2` on ga6's `SUDDEN RUDDER`).

**Not delivered here.** The missing lateral aero itself (L-7) — fuselage and wing
side force in sideslip — stays filed with M4-19; `n_y` and `ψ̈` are over-stated
by an unknown amount until it lands, which is conservative everywhere and leaves
the fin's own design load unchanged.

## The six-DOF closure (mission phase 4, step 8 — plan 13 B8a-2 — complete 2026-08-09, tier L)

**Objective.** Replace the four hand-rolled one-component relief fields a balanced
case closed with by the one field they are slices of — the rigid-body d'Alembert
field `f = −m(a_cg + ω̇ × r)` — so that the moment the relief produces is
`−[I]{ω̇}` with a real inertia tensor rather than `−Σw·d²`, and so that the yaw
degree of freedom B8a's lateral cases need exists at all. Plan 13 decisions
**L-2** (the full field) and **L-3** (item self-inertia as free-moment relief).

**The argument for doing it once.** Each of the three shipped DOF was missing the
companion force component of its own acceleration, and the three omissions were
worth wildly different amounts — **0.08 %, 20 % and 55 %** of their own degree of
freedom. A suite that adds a fourth and fifth special case is a suite betting the
next omission is the small kind:

| DOF | Companion it lacked | What the companion is worth |
|---|---|---|
| pitch | `fx = −w·q̈·dz` | the force is ≤ 0.08 % of a node load, but the *inertia* was wrong, so **`q̈` fell 18–22 %** on ga6 and 3–4 % on the RJ |
| roll | `fy = +w·ṗ·dz` | **89.8 lb / 551.9 lb** at a peak node — larger than the roll term already in the deck, because `fz = −w·ṗ·dy` reaches only the wing strips while this reaches every mass off the roll axis |
| yaw | (the whole DOF) | new; would have been **55 % high** had it copied the pitch DOF's one-component pattern |

**Deliverables.**

- **`sloads/rigid_body.py`** — the single owner: `InertiaTensor` (products of
  inertia stored as sums `Σw·a·b`, negated only in `matrix()`, which is the form
  WTONECG prints), a pivoting 3×3 solve that **raises** on a singular tensor
  rather than pseudo-inverting (risk R4), `relief_force`, `relief_moment`, and
  the weight-space→rad/s² conversion. Registered in `CONVENTIONS.md` §7.
- **`mass_distribution.assembly_distributes_mass`** — the L-3 predicate, as a
  predicate rather than a comment (`CLAUDE.md` practice 3). It decides whose
  entered self-inertia joins the tensor: a component the assembly *spreads* has
  its rotational inertia in the spread already (ga6 wing: 4.444e6 entered against
  4.288e6 built, −3.5 %, the check that they are the same quantity), a component
  it carries as a point does not (13.3 % of ga6's `Izz`). `balance.body_inertia`
  and `balance.point_mass_self_inertia` both ask it, so the set carried as points
  and the set given a free moment cannot drift apart.
- **`balance._closure`** — six DOF, three decoupled ratios plus one coupled 3×3
  solve. The rotational relief is emitted as three attributable sources
  (`closure-roll`/`-pitch`/`-yaw`) plus `closure-self`, not one lumped field, so
  the B7 gate can still isolate the roll strips and a deck reader can see which
  acceleration put a card where.
- **`BalancedCaseResult`** gains `delta_ny` and `closure_inertia`;
  `delta_pitch`/`delta_roll` become `p_dot`/`q_dot`/`r_dot`, the accelerations
  they always were. Result-only fields — nothing on disk has this shape, so
  `SCHEMA_VERSION` stays at **43** (recorded in the fields-hash tripwire).
- **The assembled deck header** states the six-DOF field, `n` and `ω̇` in deg/s².

**Test / Acceptance.** 1268 passed, 21 skipped; `ruff` clean.

| Gate | Target | Achieved |
|---|---|---|
| **G1** yaw ≡ ONENGOUT's `ψ̈ = M/Izz`, step by step against its own time history | exact | `rel_tol = 1e-12`, vacuity-guarded |
| **G2** all six components close | ~0 | **≤ 2e-16** of `n·W` |
| **G4** `Izz(closure)` = `Izz(WTONECG) − wing self + Σw·y²` | ga6 2934 | **2933.5** (0.0 %); RJ +0.40 % |
| **G5** symmetric reduction: `n_x`/`n_z` by construction, `n_y = 0`, lateral relief noise-level | identical | `< 1e-9·n·W` |
| **G6** `ACRL`'s companion field and induced yaw | as measured | 89.83 / 551.85 lb; **+18.93 / −0.993 deg/s²**; net `Fy` zero |
| **B7 (restated)** roll ≡ WINGINER | shape exact + ratio pinned | strip ratio constant to 1e-9; 0.795230 / 0.769455 |

Plus a new `tests/test_rigid_body.py` gating the owner on properties rather than
fixtures — the field's defining identity on a deliberately lopsided mass set with
every product of inertia non-zero, the no-moment property of a uniform load
factor, the sign convention, and the singular-tensor raise.

**Key decisions.**

1. **The B7 roll gate is restated, not weakened** (user, 2026-08-09, three options
   offered). It could not survive as an equality: WINGINER's wing-only model puts
   100 % of the aileron moment on the span, while the assembled airplane reacts
   about a fifth of it on mass off the roll axis and on item self-`Ixx` — so `ṗ`
   falls 20.7 % / 23.2 %. The gate now asserts **shape** (the ratio is the same
   constant on every strip, `rel = 1e-9` — the whole of what WINGINER's
   distribution says, untouched) **and magnitude** (that constant is the span's
   share of the roll moment, pinned per fixture, and independently equal to
   `ṗ/(Mx/Σw·y²)`). Strictly stronger: the old equality could not see a drift in
   the roll-inertia model at all, because under it the span *was* the roll
   inertia by construction. Rejected: excluding `dz²` and self-`Ixx` from the
   roll DOF to preserve the equality — physically wrong and self-inconsistent
   with the companion `fy`.
2. **The assembled deck joined the Imperial baseline.** Found while making the
   change: the 6-DOF rewrite moved every closure card in every assembled deck and
   **no digest noticed**, because `imperial_baseline.artifacts` only ever rendered
   the per-component channels. Plan 11 acceptance #5 — *"if a digest moves,
   something leaked"* — is empty for a deliverable with no digest, and this is the
   mission's aim-2 deliverable. Now covered; every other Imperial channel verified
   byte-unchanged **before** regenerating.
3. **`SCHEMA_VERSION` does not bump for a result-only rename.** The fields hash
   covers every dataclass on `sloads.models`' public surface, not only what `io.py`
   writes. `Project` holds no `BalancedCaseResult` and `io.py` names none of these
   fields, so there is no on-disk shape and no hop to write — the same standing
   the B7 change to this class had.
4. **Noise is bounded, not rounded away.** A symmetric case's roll and yaw
   residuals are zero only up to summation order, so the solve returns ~1e-18.
   The tests bound the resulting relief (`< 1e-9·n·W`) rather than asserting an
   exact zero the arithmetic does not produce; the deck suppresses the *display*
   of an angular acceleration below 1e-6 deg/s², ten orders below the smallest
   real one, so a meaningless number does not read as a result or churn a digest.

**Found and filed, not folded in.** `one_engine_out` cannot execute on any shipped
fixture — `atr42_100`/`dhc8_dash8` enter the slice but no engine horsepower, the
other four enter no slice — so G1 supplies that one input itself. Same class as
B8a-1's `tail_mass` finding: the calc is right and the data never reaches it.

## The fin's vertical placement (mission phase 4, step 8 — plan 13 B8a-1 — complete 2026-08-09, tier M)

**Objective.** Give the vertical tail a place on the airplane. B8a's lateral
balanced cases need the fin's height above the CG, because the roll moment a side
load makes about the CG is `−Fy·(z − z_cg)` — and the load path was using zero.

**Deliverables.**

- `tail_geometry.fin_root_waterline` — the single owner of where a fin's root
  sits, resolving explicit input → the T-tail relation
  (`root_waterline_z + h_tail_z − vtail_span`) → the fuselage top
  (`root_waterline_z + fuselage_height/2`) → a zero that announces itself. Returns
  a `FinRoot` carrying the value, whether it was assumed, the branch that produced
  it and the in-band sentence it owes its consumer.
- `VTailLoadsInput.vtail_root_waterline_z` (schema **v43**, additive, no hop).
- `tail_span` uses `planform.root_z` for the v-tail's `z_offset` instead of `0`,
  and states the fin root and its basis in the result notes.
- `configuration.tail_planform` reads the same owner instead of its own copy.
- `CONVENTIONS.md` §1 (the fin has a vertical position; a v-tail station stores
  its root in `z` and its span in `y`) and §7 (the new owner + its drift guard).

**Test / Acceptance.**

- `test_the_fin_root_waterline_is_pinned_per_fixture` — all five fixtures with a
  fin: ga6 78.5, RJ 87.0 (T-tail), cessna 86.0, atr42 170.0, dhc8 180.0, each with
  the branch that produced it.
- `test_the_fin_sits_above_the_cg_with_the_pinned_roll_arm` — ga6 **+14.0 in**,
  RJ **+86.0 in**, both exactly as plan 13 §5.1 predicted, with an explicit
  *sign* assertion because the sign is what was wrong.
- `test_the_three_view_and_the_load_path_place_one_fin_once` — the drift guard
  for the new owner.
- `test_the_t_tail_branch_puts_the_fin_tip_at_the_horizontal_tail`,
  `test_an_entered_fin_root_wins_and_is_not_assumed`,
  `test_a_fin_with_no_placement_at_all_says_so_loudly`.
- Imperial baseline: **`sbeam/vtail_span_cards`** and **`txt/tail_span`** only,
  on the five fixtures with a fin. Wing, body, h-tail and control decks
  byte-identical; every Appendix A oracle unchanged. 1247 passed, ruff clean.

**Key decisions.**

- **L-1 (user, 2026-08-08):** explicit input with a tail-type-aware derived
  default, marked `assumed` and stated in-band — the pattern
  `resolve_tail_planform` already uses for the derived planform.
- **Correction while implementing:** the fallback is `fuselage_height / **2**`,
  not the full height the design note first wrote. That is the established
  meaning of "the top of the fuselage" here — the three-view has drawn every fin
  from it since Step G6 — and a load path using a different formula would have
  silently disagreed with the sketch beside it. No quoted number moved: ga6 has
  `fuselage_height = 0` and the RJ takes the T-tail branch.
- **The T-tail branch is not a new convention** — it is the inverse of the
  three-view's own default, which places a T-tail's horizontal surface at the fin
  tip. Implementing it fixed the three-view too: the RJ was drawing its fin tip
  18 in above the horizontal tail it carries.
- **Generalized on first find** (`CLAUDE.md` practice 4): `configuration.py` held
  a second copy of the formula, so the fix swept both and left a drift guard
  rather than fixing only the caller that prompted it.

**Not delivered here** (later B8a steps): the six-DOF closure (B8a-2), the
lateral case assembly and its handed twins (B8a-3), the assembled deck and sbeam
leg (B8a-4).

---

## Release cut: **sloads 0.4.0** (the mission extension, steps 1–7), tag `v0.4.0`, 2026-08-08

**Objective.** Cut the release the backlog's development sequence names as its
housekeeping precondition — `[Unreleased]` had grown to ~1,180 lines and seven
closed mission steps, well past `RELEASE_PROCESS.md` §2's "never let
`[Unreleased]` grow past roughly a release-worth of work", and unreleased work
has no regression baseline.

**Deliverables.**
- **Version** `0.3.0` → **`0.4.0`** in `pyproject.toml` (MINOR: new modules
  `mass_distribution`, `balance`, `tail_span`, new export and round-trip
  capability, new GUI pages; no breaking change — `SCHEMA_VERSION` 42 is
  reached by additive hops and `io.py` loads every older save).
- **Changelog cut** — `[Unreleased]` dated to `## [0.4.0] — 2026-08-08` with its
  **twenty duplicate headings merged to three** (Added 16 entries / Fixed 41 /
  Changed 49; 1,064 content lines), verified content-preserving as a multiset
  before and after, and a fresh empty `[Unreleased]` opened. Same consolidation
  the 0.3.0 cut performed for the same reason.
- **Verification baseline** —
  [`08_verification_baseline_0.4.0.md`](08_verification_baseline_0.4.0.md), a
  **delta** baseline: it records the closure gates for everything 0.4.0 added
  (all closure, no new printed oracle exists for distributed inertia, mass models
  or an assembled airframe), the ten pinned exceptions with their measured
  figures, and what measurement changed in the release — and carries the FAR 23
  oracle tables forward from the 0.3.0 baseline unchanged, on two independent
  confirmations: the approved-deviations register is byte-unchanged against
  `v0.3.0`, and every Imperial digest movement is a **new** channel.
- **Backlog spot-check (§3.1)** — the stale `[E] CONM2 distributed-mass export
  per payload case` item removed: plan 12 C1–C5/C7 shipped 2026-08-08 and its
  C6 remainder already has its own entry, so the item was a lifecycle-rule
  violation (the backlog holds open items only). "Current state" and the
  sequence table's housekeeping line updated to post-release form.
- **Gates at cut:** `pytest` **1232 passed / 21 skipped / 0 failed** (coverage
  93 %), `ruff check sloads/ cli.py` clean, `scripts/smoke_test.sh` PASS, every
  skip carrying a stated reason and a backlog entry, no open CRITICAL/MAJOR
  review findings.

**Post-release.** The mission sequence resumes at **step 8** (plan 11 **B8a** —
empennage balanced cases, ±β yaw pairs, opening with the lateral-closure design
note for `Δn_y` + `Δψ̈`, since no lateral load factor exists in the suite today).
The one cheap `[E]` remainder — plan 12 **C6**'s solver-side CONM2 inertia gate,
unblocked by step 2's round-trip harness — is a natural first slot.

---

## Distributed empennage loads, phase 1 (mission phase 4, step 7 — plan 09 T1–T5 — complete 2026-08-08, tier L)

**Objective.** Give the empennage the wing's deliverable: per-station distributed
ULTIMATE loads on a user-defined load reference axis, exported as
`GRID`+`FORCE`+`MOMENT` cards that close in force **and** moment from their own
card text. Before this the tail had totals (SELECT) and a chordwise pressure
profile (TAILDIST) and nothing in between — no planform, no spanwise
distribution, no surface mass, no `GRID`, no `MOMENT`.

**Result.** Both surfaces distribute, on all five fixtures with an empennage, and
close against **analytic** targets: force, bending, centreline rolling, torsion,
inertia and the LRA reduction identity. Two new rows in the export-equilibrium
sweep (every fixture × both unit systems) and a solver leg in the round-trip
harness. **Appendix A and the chordwise path are bit-unchanged** — every Imperial
digest change is a new channel, verified channel-by-channel.

**Deliverables.** `sloads/tail_geometry.py` (planform resolution, the 1 %
validator, the half/full bookkeeping); `sloads/modules/tail_span.py`; the
empennage axis map in `export/coordinates.py`; `tail_span_*` writers and GID
bands 4001+/4501+ in `sbeam_bridge.py`; the **Tail Span Loads** page and its
workflow step; `Project.tail_mass`, `LoadsResult.htail_span`/`.vtail_span`,
`WingStationLoad.myy_free` (`SCHEMA_VERSION` 42, additive, no hop);
`cli.py --export-target htail-span|vtail-span`; `tests/test_tail_geometry.py`
(34) and `tests/test_tail_span.py` (58).

**Test / Acceptance.** No printed oracle exists for a spanwise tail
distribution, so the chord-proportional shape's **closed forms are the gate**
(`CLAUDE.md` practice 2). Each target is computed independently of the module's
own quadrature — the bending centroid from the planform, the torsion from
area-weighted chordwise means, the force from SELECT's totals. All six run
against a **tapered and swept** planform too, because every shipped fixture takes
the derived rectangle and the sweep-transfer term would otherwise never be
exercised.

**Key decisions, and the five places measurement changed the plan:**

- **No fixture carries a tail planform**, so one is *derived* (a rectangle from
  the authoritative area/span — the same first-order shape the three-view has
  always used) and marked `assumed` everywhere it travels. Cost quantified in
  band: `ȳ = b/2` for the rectangle against `(b/3)(c_r+2c_t)/(c_r+c_t)` for a
  taper, so it is conservative in root bending but its station distribution is not
  the surface's own. Entered polylines win and are validated to 1 %.
- **The fin's torsion is `Mzz`, not `Myy`** — a surface twists about its *span*
  axis, and the fin's span is `z`. The sign is the stored value negated, because
  `r × F` reverses for a side force. Derived in `coordinates.py` with the
  derivation written down; the v-tail invariant row asserts `Myy == 0` for it.
- **The determinate support was implicitly x-axis-only** and returned an *exactly
  singular* matrix on the h-tail's `y`-running beam. Fixed in step 2's own
  machinery (`roundtrip._determinate_components`), which now picks the
  axial-rotation DOF from the beam's direction. Only a non-`x` beam could have
  found it.
- **`WingStationLoad` gained `myy_free`.** The tail deck applies strip loads
  directly rather than differencing a cumulative column — which is what smears a
  concentrated wing mass inboard in the wing bridge — so it needs the per-strip
  free torsion. The cumulative `myy` carries the sweep transfer and is not that;
  same distinction plan 11 had to make for the wing.
- **The h-tail attachment stations have no fuselage width to sit on**
  (`fuselage_width` is `None` on every fixture), so they fall back to the
  innermost strip pair — stated on the result, filed on the backlog, same
  direction as the wing's centreline-clamp limitation.

**Deliberate scope limits, stated in-band:** the v-tail carries **no inertia**
(the suite has no lateral load factor; applying normal `n` to a fin's mass is a
fabricated load in the wrong direction — it lands with plan 11 B8a), and
`control_load_mode="discrete"` **raises** rather than falling back to smeared, so
no deck can claim a hinge/actuator load path it does not contain.

**Also filed:** the derived-planform gap (fixture data, per airplane) and the
missing fuselage width for the attachment stations.

**Open from plan 09:** T6 (discrete hinge/actuator controls, the suite's first
hinge-moment output) and T7 (T-tail transfer) — now step 9.

---

## Antisymmetric wing cases + the handedness machinery (mission phase 3, step 6 — plan 11 B7 — complete 2026-08-08, tier L)

**Objective.** Phase 2 of the balanced-airframe work: assemble the rolling wing
condition as a full-span free-free case, and build the left/right machinery every
later ± family (yaw ±β, OEI, unsymmetrical tail) reuses — without the
oracle-locked FAR 23 path ever seeing handedness.

**Result.** `ACRL` assembles and closes in **all six** rigid-body DOF to machine
precision, on both fixtures and both twins; the roll relief reproduces WINGINER's
own unit-roll inertia distribution **strip for strip (ratio 1.000000)**; and both
twins solve in the real sbeam with determinate-support reactions ≈ 0 through plan
10's assembled leg. Coverage went from 4 and 3 balanced cases to **7 and 6**.

**Deliverables.** `ROLLING_WING_CONDITIONS` + `resultant6` + `handed_twin` +
`reflect_load` + the roll DOF in `_closure` (`modules/balance.py`); the reflection
operator `reflect_point`/`reflect_force`/`reflect_moment`/`reflect_side`
(`export/coordinates.py`, the B-6 single owner); `handed_case_id`/`unhanded_case_id`
(`case_ids.py`); `BalancedCaseResult.residual_fy/mx/mz`, `delta_roll`,
`unbal_moment`, `hand`, `semi_span`, `roll_moment_fraction`; deck header and UI
statements; nine new tests in `tests/test_balance.py`.

**Test / Acceptance.** The gate is an **identity against an independent
producer**, not a smallness bound — see "Key decisions" for why a smallness bound
would have been wrong. `test_roll_closure_reproduces_winginer` compares the
balance layer's roll-acceleration solve against WINGINER's `fz_r`/`iwxx`
recurrence, which this step did not touch and which knows nothing about the
balance layer. Supporting gates: `residual_mx == -UNB` exactly and zero on every
non-rolling case; all six DOF closed after relief; the twins mirror load-by-load
(not merely in total, which would pass for a case that reflected nothing); the
reflection operator is an involution; lateral DOF identically zero.

**Key decisions, and the three places measurement overrode the plan:**

- **`TORS` is not antisymmetric** — plan 11 §2 names it as one. Handedness lives
  in `unbal_moment`, and every fixture enters zero for `TORS`, because a *steady*
  roll has no unbalanced rolling moment (aileron balanced by roll damping) and
  the remaining up-going/down-going aero asymmetry has no spanwise representation
  in this suite. Assembled as the symmetric case it is, with the finding pinned.
- **The roll residual is not an error.** On a rolling case `residual_mx` is the
  *applied* couple — 6.71 % of n·W·b/2 on ga6, 2.00 % on the RJ — which the
  airplane is supposed not to balance. Gating it at 1 % would have failed a
  correct case. Reported, and reacted in full by the fourth closure DOF, on the
  same standing `delta_nx` has for drag.
- **The closure DOF *is* WINGINER's model**, which is what makes it gateable: the
  wing-item/panel scale (0.9903 ga6, 1.0100 RJ) cancels identically because the
  closure normalises on the masses the assembled model carries, so the agreement
  is exact rather than approximate.
- **The applied couple is lumped** (user decision, 2026-08-08). No aileron butt
  lines exist in the schema, and lumping reduces *exactly* to the oracle-locked
  model — WINGINER also carries only the inertia reaction. The reaction is fully
  distributed; the aero half is not. Stated in-band and filed.
- **Sign recovered, not assumed.** WINGINER's unit-roll set produces `+UNB`
  (its normalisation makes `Σ y·fz_r = 100,000`), and NETLOADS enters inertia
  opposing the air load, so the aero couple is `−UNB`. The strip-for-strip
  identity confirms it rather than merely being consistent with it.

**Deliberate output change.** `csv/balance` and `txt/balance` moved on the two
fixtures that assemble cases — new conditions in the balance module's own report.
**Nothing else moved**: every deck, every per-component artifact and every
Appendix A channel is byte-identical, verified channel-by-channel before the
digest was regenerated.

**Filed alongside:** the aileron lift increment is not distributed (needs schema);
and the RJ's three high-speed low-CL cases exceed the 1 % pitch gate (PLAA
1.041 %, PMAA 0.967 %, TORS 1.174 %) — PLAA has been over since B2 and `TORS`
merely exposed the pattern, now bounded per fixture per plan R3 rather than by
widening the gate for everyone.

---

## sbeam round-trip CI gate (mission phase 1, step 2 — plan 10 — complete 2026-08-08, tier M)

**Objective.** Make the mission's core claim testable. "An exported deck solves
in sbeam with verified global equilibrium, continuously in CI" rested on a manual
check performed once, in 2026, and never repeated. The 2026-08-08 spike showed
the round trip already agreed exactly — so this is a harness step, not a physics
one, and its whole value is turning an unrepeated manual act into a standing gate.

**Result.** `pytest -m roundtrip` — 24 solver tests over `ga6_normal` +
`concept_regional_jet` × {Imperial, SI} × {wing, body, tail, assembled}, plus 7
wrapper tests that need no solver — green, in its own blocking CI job. **No
exported byte changed** (acceptance §6), so no digest was regenerated.

**Deliverables.** `sloads/export/roundtrip.py` (`solve_deck`,
`wrap_as_stick_model`, `total_reaction`, `Support`, `Topology`);
`tests/test_sbeam_roundtrip.py`; the `sbeam` fixture in `tests/conftest.py`; the
pinned `solver` extra and the `roundtrip` marker in `pyproject.toml`; the
`sbeam-roundtrip` job in `ci.yml`; `.github/workflows/sbeam-drift.yml`.

**Test / Acceptance.** The assertions that carry weight have **two independent
producers**: the wing deck's reaction and element-1 end-B internal loads are
checked against the NETLOADS quadrature (`r.stations[0]`) while the cards come
from `wing_nodal_loads`; the fuselage deck's *entire* Ch 15 cumulative shear and
bending table is reassembled by sbeam from the `FORCE` cards and `GRID`
coordinates alone; and the free-free legs target the constant zero. Three
mutation tests assert the gate **fails** — a wing `FORCE` scaled by 1.01, two
`SUBCASE`s' `LOAD` ids swapped, and a body `GRID` displaced by 1 %, the last of
which leaves every force sum closing exactly and can only be caught by solving.
Without sbeam the suite skips and stays green; with `SLOADS_REQUIRE_SBEAM=1` and
sbeam absent it fails.

**Key decisions, and the four places the design note was wrong** (full detail in
plan 10 §10):

- **The determinate body support is `1234` + `23`, not the note's 3-2-1.** Three
  translation constraints are not six, and on a **collinear** node line no
  translation scheme restrains rotation about the beam axis — the solve is
  singular. Beam nodes carry rotational stiffness, so the collinear analog
  constrains that rotation directly.
- **B-c became the whole cumulative table.** The note's "aft-most element shear
  ~ 0" is false (that element carries the last station's load: −136.79 lb on
  ga6); what is true, and far stronger, is the station-by-station comparison.
- **The tail deck is two disjoint beams.** The h-tail and v-tail chord lines are
  each stated from their own leading edge, so their stations interleave and their
  first stations are coincident. Wrapping them as one run solves happily and means
  nothing — a silent failure — hence the wrapper's `groups`, and a test pinning
  the consequence.
- **The assembled deck ships with no elements.** It is a load set on a node cloud,
  which is all a load deliverable needs to be; the wrapper adds a tree of bars and
  keeps the deck's own determinate support, since that support is what is under
  test.
- **The pin is `ed23b26`, not `origin/main`** — the commit plan 12 and this
  step's spike were verified against; `main` predates `MASSSET`, which C6 needs.
  The weekly drift job tracks `main` non-blockingly.

**Finding recorded against sbeam (not sloads).** `recover_reactions` subtracts
the unreduced applied vector at constrained DOFs, so a load a rigid element
transfers onto a constrained node reappears as reaction — measured at 1738.13 lb
on `concept_regional_jet`'s fuselage, exactly the tied node's own load, against
an applied set closing to 0.007 lb. The harness supports away from tied nodes.

**Unblocks.** Plan 12 **C6**'s solver-side mass leg (a fourth deck family, no
structural change needed) and plan 09's **T-11** sequencing gate, which required
both export-boundary items.

---

## Balanced free-free airplane cases (mission phase 3, step 5 — plan 11 B2–B6 — complete 2026-08-08, tier L)

**Objective.** Aim 2, in the user's words: *a full airplane balanced case — wing
tip to wing tip, nose to tail — with no need for a constraint, because the loads
balance.* The airplane already balanced at **trim**; the distributed loads never
inherited it, because the wing distribution, tail load, fuselage inertia and trim
solve were four separate calculations nothing assembled.

**Result.** Pre-closure residuals of **0.05–0.70 % of n·W** and **0.12–1.04 % of
n·W·MAC** against plan 11's 1 % gate; all three symmetric DOF close to machine
precision after relief, re-verified from the exported deck's own card text. The
assembled deck parses in sbeam.

**Deliverables.** `modules/balance.py` (assembly + 3-DOF closure),
`export/balanced_deck.py` (the primary deliverable), `BalancedLoad` /
`BalancedCaseResult`, a **Balanced Cases** view, `tests/test_balance.py`.

**Four design questions resolved by measurement before any code was written**
(the user's explicit instruction), and each answer changed the build:

- **R1, plan 11's "one genuine unknown" — where `m_wf` goes.** Quantified at last:
  the trim carries `Cm` for the airplane *less tail* (wing **and** fuselage) while
  the distributed wing carries only its own section `Cm`. The gap is the
  fuselage's Munk moment, **+4.3 to +6.3 % of n·W·MAC**, positive, with no
  distributed carrier until M4-19. Applied as a single labelled free moment
  (user's call); omitting it would leave a systematic ~5 % residual that the
  closure would silently absorb — a real aero load disguised as a correction.
- **Case pairing, which B-1 assumed was solved.** It was not: `wing_mass.cases`
  carry `case=None` on 5 of 6 fixtures and their hand-entered `cl`/`v` are a
  *different flight condition* from the V-n point SELECT pairs them with (atr42
  enters CL 1.55 at 170 kt against 1.7283 at 185.85). Assembling the two halves
  then compares different conditions, and the force residual runs **10–37 %**. The
  wing distribution is now recomputed at the V-n point's own condition (user's
  call). The entered distributions are untouched and remain the FAR 23
  deliverables — this adds a case, it does not change one.
- **The mass model is the items, not WINGINER's own** (plan 11 §4, confirmed by
  measurement). Taking wing inertia from `panel_weight_lb + concentrated`
  double-counts anything in both models; on atr42 and dhc8 the wing-tank fuel is,
  and the residual runs 12–13 % instead of 1.9 %. Sourcing it from the WING-tagged
  items made the wing-fuel defect filed at step B1 **stop mattering here**, which
  is why those fixtures needed no data fix after all.
- **The closure needs three DOF, not two.** Nothing reacts drag; see the CHANGELOG.

**Three errors found while building, each only visible by checking rather than
reasoning** — worth recording because all three produced plausible wrong answers:

1. **A cumulative torsion is not a free moment.** `WingStationLoad.myy` already
   contains the sweep/dihedral transfer of outboard shear to the inboard
   reference. Assembling from it *and* applying the strip's position offset
   double-counts the transfer: **20.5 % of n·W·MAC** instead of 0.12 %. Only the
   section `Cm` is free, and `_free_moments` recovers it by undoing the two
   transfer accumulations.
2. **Wing inertia sits at the 50 % chord, not the 25 %.** WINGINER models the
   panel mass CG there (its torsion carries `−w·(c50x − c25x)` for exactly that
   reason); placing it where the *air* load acts drops ~2.5 % of n·W·MAC. It is
   additionally anchored so the set's centroid is the WING items' own — the item
   database owns *where* the mass is, WINGINER owns *how it spreads*.
3. **The deck's nodes must be at true positions.** Keying wing nodes on span
   station alone collapsed air (25 % chord) and inertia (50 % chord) onto one
   node; reusing the fuselage beam's `z = 0` line flattened real waterlines; and
   ballast items — which have no beam station, the beam being derived from the
   untouched database — fell through to a shared node. Together **3.9–21.9 % of
   the deck's balance**, while the in-memory case still closed to 1e-13. Found
   only by re-deriving the resultant from the card text, which is now the
   acceptance test.

**Scope, pinned rather than skipped.** Balanced cases assemble on `ga6_normal`
(all four symmetric conditions) and `concept_regional_jet` (three). The other
four fixtures produce none, because **no payload case of theirs is a loading their
weight database can produce** — the step-4 finding, biting again. `ACRL`/`TORS`
are antisymmetric and wait for plan 11 B7's handedness machinery: a symmetric
assembly of an antisymmetric case would balance and mean nothing.

## CONM2 distributed-mass export (mission phase 2, step 4 — plan 12 C1–C5, C7 — complete 2026-08-08, tier L)

**Objective.** Break a circularity. The `FORCE`/`MOMENT` deck is the *total*
applied load — aero plus inertia — and stays that way, but its inertia half is
computed by the same code that writes the cards, so nothing outside sloads can
contradict it, and there is no printed oracle for a distributed inertia load.
Exporting the mass distribution as `CONM2` cards gives sbeam a mass model it
parses for itself.

**Deliverables.**

1. `sloads/export/mass_cards.py` — `CONM2` + `MASSSET` fragment, a self-contained
   runnable mass-check deck (`MASSSET` + `GRAV` + a massless placeholder beam,
   and no load cards), and sloads' own inertia contribution as a separate marked
   comparison set.
2. `mass_distribution.derive_case_loadings` — each payload case resolved to an
   actual loading (discretionary items aboard + a solved ballast row), with a
   credibility gate.
3. `DeliverableUnits.mass` / `.mass_inertia` + `is_mass_consistent` (C-5).
4. `cli.py --export-conm2`; a **Mass Export** tab on the Weights page.
5. `tests/test_mass_cards.py`.

**Test / acceptance.** 1030 passed, 16 skipped; `ruff check sloads/ cli.py app/`
clean. No existing deck or digest moved — the step is purely additive.

**Verified against sbeam itself** (by hand; sbeam is not a dependency, so CI
cannot run it — the same precedent as C4's "the deck parses and solves in
sbeam"): both artifacts parse with sbeam's own `parse_bdf`, and
`sbeam.gpwg.compute_gpwg` reproduces sloads' mass, CG-x and CG-z for all four
ga6 payload cases **exactly** (CG1 8.806269 slinch at x 85.1000, z 93.0000).
That is plan 12 acceptance 2 and 3, through an independent parser.

**Key decisions, and where the plan was wrong.**

- **C-1's premise fails on 5 of 6 fixtures.** "Per-case itemization derived from
  WTENV's ballast machinery … reproduces CG1–CG4 with no new user input" holds
  for `ga6_normal` only — it is the Appendix A airplane and its `cg_cases` *are*
  WTENV's structural points. Everywhere else the cases are free-standing
  CG-envelope corners (RJ: 619/599/595 in against WTENV's 594/574/569). Targeting
  them through WTENV's forward-loading *sequence* derives 6 of 18 cases; the rest
  want a ballast station up to 3800 in off the airplane, or land on a vertex that
  already weighs the target with the CG 13–60 in away, which no ballast can move.
- **So the search is over discretionary subsets**, not the station-sorted prefix
  — dropping aft passengers is how a real loading moves its CG forward. That
  reaches 16 of 18, over 8–128 subsets, so exhaustive search is the right
  algorithm rather than an optimisation.
- **A credibility gate was added** (user decision, 2026-08-08). Six of those 16
  need ballast worth 12–31 % of the airplane — `atr42_100` CGfwd wants 7,196 lb;
  `concept_heavy` 5,500 lb on an 18,000 lb aircraft. That is not ballast, it is a
  statement that the case is not a loading. And since decision C-2's entire point
  is an *independent* mass model, a set containing a 7,196 lb invention would
  make the check validate fiction. Cases over 10 % ballast, or whose solved
  ballast waterline falls outside the airframe, are reported rather than
  exported: **7 of 18**, including all four ga6 cases.
- **Acceptance 1 is weaker than it reads.** "Each derived case reproduces its
  `cg_cases` weight, xcg and zcg within a stated tolerance" is *exact by
  construction* wherever a ballast row exists — it is solved from those three
  numbers. Recorded so it is not mistaken for evidence.
- **The mass channel's Imperial factor is not 1.0**, and cannot be: the canonical
  stored quantity is a pound of *force*, so a consistent Imperial deck's mass unit
  is a division by g away. Documented as the one exemption from the all-1.0
  identity, with its own `is_mass_consistent` property rather than an extension of
  `is_consistent`, so no existing caller of the latter changes behaviour. Its
  identity — `force / (mass × length) == g` — is exact *and identical* in both
  systems, because one standard gravity is expressed per length unit and derived
  from a single constant. Quoting 386.088 alongside 9806.65 would have broken it
  in the eighth digit.
- **Wing items attach to the fuselage beam**, pending plan 11 B5's left/right
  bands. Mass, CG and inertia are exact regardless — the CONM2 offsets carry the
  true position — and the deck header states the limitation rather than implying
  the wing mass is where it is drawn.

**Defect found by the work, and the reason to run the external tool rather than
reason about it.** sbeam decides overlay-only status by *reference*: a `CONM2`
that no `MASSSET` `ADD` row names belongs to the **baseline**, and is therefore
in every payload case. The first cut exported every discretionary item, including
ga6's own `Ballast` row — superseded by the per-case ballast this step derives —
so sbeam's GPWG recovered **9.0083 slinch against sloads' 8.8063 for CG1: 78 lb
too much, in every case, from a deck that parsed without complaint.** Exactly the
plausible-wrong-answer failure mode decision C-6 exists to rule out, and it would
not have been caught by inspecting the deck. Fixed structurally: the overlay list
is built from what the loadings actually carry, so an unreferenced overlay card
cannot be written, and `unreferenced_overlay_eids` is the drift guard.

**Not shipped, filed:** C6's solver-side gate (sbeam applying `GRAV` and its
recovered inertia matching card for card) needs the step-2 round-trip harness.
Also filed: the finding that most fixtures' payload cases are not loadings their
weight databases can produce — a fixture-data decision, pinned per fixture in the
tests.

## The mass single source of truth (mission phase 2, step 3 — plan 11 B1 — complete 2026-08-08, tier L)

**Objective.** Make `weight.items` the mass SSOT and derive the Ch 15 fuselage
beam from it, so the distributed loads and the airplane's own weight statement
describe one airplane (plan 11 decision **B-2**).

**What was actually wrong.** The suite carried two mass models and **nothing
compared them**. `weight.items` closes to W and to the CG by construction and is
what every mass-properties deliverable is computed from;
`fuselage_mass.stations` was a short hand-entered lump table, and it was the only
input `body_loads` ever read. Measured across the shipped fixtures:

| fixture | item model | entered | shortfall | of beam |
|---|---|---|---|---|
| `ga6_normal` | 3,070 | 2,578 | 492 | 16 % |
| `cessna_210` | 3,450 | 3,020 | 430 | 12 % |
| `atr42_100` | 32,751 | 25,210 | 7,541 | 23 % |
| `dhc8_dash8` | 28,700 | 25,890 | 2,810 | 10 % |
| `concept_regional_jet` | 30,600 | 18,000 | 12,600 | 41 % |
| `concept_heavy` | 16,200 | 0 | 16,200 | 100 % |

Plan 11 §1.3 had recorded 427 lb, for ga6 alone. The real figure is every
fixture, up to 41 % of the beam — and `concept_heavy`'s missing table was the
sole reason it had no body deck at all. Every fuselage inertia load, shear,
bending moment and exported body card came from a beam carrying less mass than
the airplane weighed.

**Deliverables.**

1. `sloads/mass_distribution.py` — the SSOT. Partitions the database by carrying
   component, derives the beam station table, and owns the reconciliation checks
   (`partition_closes`, `wing_mass_tie`, `fuselage_reconciliation`,
   `unmodelled_wing_mass`, `component_summary`).
2. `MassComponent` + `MassItem.component`; all six fixtures explicitly tagged.
3. `FuselageMassInput.stations_are_override`; `body_loads` reads the SSOT.
4. Schema **v41** + migration hop `_v40_fuselage_stations_override`.
5. `tests/test_mass_distribution.py` — the drift guards, swept over every fixture.
6. Fuselage Loads page: the component summary, the reconciliation warning, and an
   explicit override checkbox.

**Test / acceptance.** 968 passed, 16 skipped; `ruff check sloads/ cli.py app/`
clean. Imperial digests regenerated deliberately, diff confined to the body
channels (`body_cards`, `body_span`, `body_fitting` on all six, plus
`csv`/`txt/body_loads` newly present on `concept_heavy`); wing, tail and control
decks and every other channel byte-identical. **Plan 11 risk R2 verified rather
than assumed**: the Appendix A oracle suites (`test_engine`, `test_airloads`,
`test_balloads`, `test_net_loads`, `test_select`, `test_landing`,
`test_weight_envelope`, `test_weight_onecg`, `test_flight_envelope` — 123 tests)
pass unchanged, because no oracle module reads `fuselage_mass`.

**Key decisions.**

- **Component tagging is explicit, and geometric inference was abandoned.** Plan
  11 §3.1 specified defaulting `component` from `(x, y, z)`. That cannot work:
  **every item in every fixture sits at `y = 0`** — the rows are lumped airplane
  totals on the centreline, so `"Engines (2)"` on a wing-mounted twin carries no
  side information at all. Station `x` cannot separate it from a fuselage item
  either (atr42's wing is at x = 395, its engines at x = 370, both inside the
  fuselage's own range). `infer_component` survives as a fallback that returns
  `FUSELAGE` for everything — a deliberate refusal to guess, which guarantees the
  one thing it can (the beam is *complete*, never light, never mis-attributed) and
  lets `wing_mass_tie` fail loudly on an untagged file, which is the correct
  signal.
- **The beam carries the empennage; plan 11 §1.3 had excluded it.** The h-tail
  and v-tail hang off the aft fuselage, so their weight is reacted by that beam.
  Excluding them leaves mass unaccounted for between the two models; including
  them makes `Σ(wing) + Σ(beam) == Σ(items) == W` exact, which is what
  `partition_closes` asserts. The wing is the one exclusion, because it enters as
  the carry-through *reaction* (plan 11 §4's seam rule).
- **Derived by default, entered as an explicit override** (user, 2026-08-08).
  The alternative — hand-rewriting each fixture's station weights to sum to the
  item model — would have meant inventing the per-station split of e.g. atr42's
  32,751 lb across 8 stations, with no oracle. Deriving closes the gaps by
  construction and invents nothing.
- **A migrated file keeps its beam.** Silently moving somebody's fuselage loads
  on load is not ours to do — on ga6 it is a 19 % change to every body shear. The
  hop marks an existing table an override and the gap is *reported*, so adopting
  the SSOT is a decision taken in front of the number.
- **Zero-tolerance ties only where the data supports them.** The cg-case
  reconciliation the plan implied belongs to plan 12 **C1** (the item database
  yields one loading; matching it to a named `cg_case` *is* C1's problem), so it
  was left out rather than shipped as a fitted tolerance.

**Finding filed rather than folded in.** `wing_mass_tie` fails on the three
fixtures that hang fuel on the wing — atr42 3,800 lb, dhc8 4,000, concept_heavy
1,200 — because each airplane's wing-tank fuel sits inside an undivided
`"Fuel to gross"` row and cannot be shown as wing mass. That fuel is therefore
carried on both beams. The engine+nacelle half of the twins' concentrated model
reconciles exactly, so the fixtures are otherwise consistent. Closing it needs
item rows split into wing-tank and body-tank fractions — new fixture data with no
oracle — so it is on the backlog and pinned to the pound by
`test_the_unmodelled_wing_mass_is_pinned_per_fixture`.

## Export-boundary equilibrium gate (mission phase 1, step 1 — complete 2026-08-08, tier M documented to L depth)

**Objective.** Every deck the sbeam bridge writes makes a claim about itself in
its `$` header ("FORCE set sums to root Sz", "Applied Fz set sums to 0 (vertical
equilibrium)", "Terminal Myy … (moment equilibrium)"). Verify those claims **from
the deck's own card text**, at the boundary where the numbers leave the tool.
Concept mode has no printed oracle, so a stated physics-closure gate in CI is
what stands in for one (`CLAUDE.md` required practice 2). Design note:
`docs/30_future/07_export_equilibrium_invariant_plan.md`.

**What was actually wrong.** Four closure checks existed. All four were
force-only, Imperial-only, and hand-rolled four separate times
(`sum(sc * v[2] for _, sc, v in forces[sid])`, in two test files). So:

- **No moment was ever checked from any deck.** The body deck's "Terminal Myy …
  (moment equilibrium)" header claim had been unverified since step C6. The
  wing's in-memory bending check summed `NodalLoad` objects, never the deck's own
  `GRID` coordinates — which are what a solver integrates.
- **`system=` was never varied.** A unit set with
  `moment.factor ≠ force.factor × length.factor` — the exact D-19 failure mode
  `coordinates._checked` exists to prevent — passed the whole suite, because a
  force-only sum is blind to it.
- **The body, tail and control decks emitted no `GRID` cards at all.** They named
  GIDs that existed in no file: not moment-checkable from their own text, and a
  consumer could not place the loads without a second artifact.
- **ga6 — the FAR23 oracle fixture — had no body/tail/control deck coverage.**
  Only the concept fixture was exercised.

**Deliverables.**

1. `sloads/export/equilibrium.py` — the single owner. `parse_cards` (moved out of
   `tests/helpers.py`, which re-exports it), `card_totals` (geometry-free, for the
   two decks that carry no `GRID`s), `resultant` / `deck_resultants` (full
   rigid-body sums about a caller-chosen reference), `ref_first_loaded` /
   `ref_aftmost_loaded`, and `closes` — one tolerance policy, not five.
   Production module, so the round-trip harness (step 2) and any later runtime
   validator consume this authority rather than reimplementing it.
2. `GRID` cards on the body and tail decks; the control deck's explicit
   "carries no geometry" note.
3. The h-tail/v-tail GID split (`tail_station_gid`, blocks `2001+`/`2101+`).
4. `tests/test_export_equilibrium.py` — the sweep: every example × {Imperial, SI}
   × every deck family, force **and** moment, plus GID-block disjointness, a
   non-vacuousness test, and a deck-comment-width guard.
5. The four hand-rolled sums re-pointed at the owner.

**Test / acceptance.** 903 passed, 17 skipped; `ruff check sloads/ cli.py` clean.
`tests/fixtures_imperial/digests.json` regenerated **once, deliberately**, with
the diff confined to `sbeam/body_cards`, `sbeam/tail_cards`,
`sbeam/control_cards` and `sbeam/tail_chordwise` — wing decks, every report/CSV
channel and the case index byte-identical. Appendix A oracles unchanged.

**Key decisions.**

- **E-1 — the invariant is per-deck resultant re-derivation, not `Σ FORCE = n·W`.**
  This is the part worth recording, because the `n·W` form is the one that gets
  re-proposed. It is unrealizable per-component as literally worded: the body deck
  already closes to *zero* (it is a free-free beam — inertia + balancing tail load
  + wing carry-through, Ch 15 p103), the decks' case ids are banded into disjoint
  ranges on purpose so no case pairs a wing, body and tail block, and the wing
  deck is a root-clamped half-span whose root shear is **not** `n·W/2` (ga6 PHAA:
  5836.9 lb against 6460 lb — fuselage-carried lift plus inertia relief), with
  doubling wrong outright for the antisymmetric `ACRL`/`TORS` cases. The
  assembled-airframe `n·W` closure is a separate item pairing with the assembled
  stick model.
- **A beam torsion is not a rigid-body moment.** Found while implementing §4 of
  the design note, which had specified the wing's `ΣM.y = SF × root Myy` as a
  rigid sum. It is not: the wing station `x` sweeps aft and `z` rises with
  dihedral, so the transfer term `Σ (p − ref) × F` is of the *same order* as the
  torsion (≈ −93,300 lb-in against a −91,400 lb-in root torsion on ga6 PHAA). The
  deck's header claims the applied-`MOMENT`-card sum, and that is what is
  asserted; only bending integrates the `FORCE` lever arms. `Resultant` carries
  both sums (`m0`, `m`) so a checker cannot silently pick the wrong one. Recorded
  in `CONVENTIONS.md`.
- **The wing reference point is the root *station*, not the clamped root node.**
  The design note said "clamped root node"; that node sits half a strip inboard,
  which would offset the target by `Sz·dy/2`. The root station is the point
  `stations[0].mxx` is actually about.
- **Zero-target tolerance scales with `Σ|term|`, not `max|term|`.** The error
  being bounded is *accumulated* `%.6E` truncation (~5e-7 per card), so a
  max-sized budget is too tight by the card count — `concept_regional_jet`'s body
  deck closed to −11.5 lb-in against an 11.3 lb-in budget, which is the format,
  not the physics.
- **h-tail and v-tail must not share a GID block.** Harmless while the GIDs were
  bare references; the moment a `GRID` card is emitted it would define one node at
  two locations, because the two components have different average chords (ga6:
  0→36.39 in vs 0→37.49 in). v-tail GIDs shift as a result.
- **Control decks carry no geometry, by design (E-5 amended, §3.1).**
  `ControlSurfaceStation.x` is a fraction of chord and
  `ControlSurfaceLoadResult` carries no chord length, so `x = 0.35` cannot become
  a station in inches or millimetres. Emitting it would be a silently wrong
  coordinate. Revisit when the result gains a chord (natural pairing: the
  assembled stick model).

**Findings filed rather than folded in** (both discovered *by* the sweep, both
with bodies on the backlog):

- **Concentrated wing masses are smeared to the nearest node in the exported
  bending.** WINGINER adds a point mass at its true station
  (`mxx[i] += w·(cw.y − ye[i])`); the export recovers nodal loads as increments of
  the cumulative shear, so the mass is picked up entirely at the outermost station
  *inboard* of it and its lever arm moves inboard by up to one strip width. Shear
  closes exactly; bending runs high — `atr42_100` +1.91 %, `dhc8_dash8` +1.11 %,
  `concept_heavy` +0.44 %. `ga6_normal` and `cessna_210` carry no concentrated
  masses and close exactly, so **no Appendix A oracle is affected**. Pinned, not
  hidden: `test_wing_deck_bending_closure` asserts exact closure on masses-free
  wings and asserts the *negation* plus a one-strip-width bound on the three
  affected fixtures, so the day it is fixed the suite goes red.
- **Wing deck `$` comments overrun the 72-column free-field width** (up to ~100
  columns in SI). Cosmetic — `$` is a comment to every parser — and fixing it
  changes wing Imperial bytes, which this step's acceptance excluded. The
  body/tail/control decks were swept and are guarded.

## Design-airspeeds theory document (complete 2026-08-08, tier S)

New `docs/20_theory/design_airspeeds.md` — the STRSPEED/MACHLIM theory chapter (23.335/23.337 equations as implemented, both 25.335(b) dive-speed routes, MACHLIM lines, the Subpart-G design-speed → operating-limitation relationship, Part 25 gaps, Appendix A oracle table with page cites). Docs only.

## F25-2 — Speeds & placards, Part 25 variant: the Mach-margin dive-speed route (complete 2026-08-08, tier L)

**Objective.** Give a concept configuration the dive speed the regulation
actually allows it, and fix the Major concept-mode defect that made this urgent.
14 CFR 25.335(b) reads: "VD must be selected so that VC/MC is not greater than
0.8 VD/MD, **or** so that the minimum speed margin between VC/MC and VD/MD is the
greater of [the (b)(1) upset criterion and the (b)(2) Mach margin]"; 23.335(b)(4)
has the identical "need not be shown if" structure. Since `VD ≥ 1.25·VC` **is**
`VC ≤ 0.8·VD` written the other way round, what STRSPEED had always implemented
was precisely, and only, the first half of that disjunction. There was no route
by which a user could select the margin basis, in any category.

**The defect, as reproduced 2026-08-08.** On
`examples/concept_regional_jet.project.json` (VC 310 kt, shoulder 24,000 ft,
where √σ·a = 411.19 kt per unit Mach) the fixture's own `chosen_vd = 350` kt —
MD 0.8511, margin +0.097, an ordinary transport margin — was silently overridden
to 1.25·VC = **387.5 kt**, MD **0.9423**, margin **+0.189**. No warning, no note,
no validation entry: the user's input simply did not survive. Consequences, in
order of severity: (1) `flight_envelope.design_inputs` reads VD/MD straight out
of STRSPEED, so `MAN ±D`, `GUST ±D`, `BAL D` and `ST ROL D` were all flown 11 %
too fast, feeding SELECT, the distributions and the exported decks; (2) MACHLIM
went nonphysical — MNE 0.848, **MFC 1.13**, a supersonic flutter-clearance Mach
for a subsonic transport.

**A second defect found while reproducing the first.** `MachLimitInput.mc/md`
were persisted in the project file *and* recomputed from the design speeds by the
Streamlit Speed–Altitude tab, which ignored the stored pair outright. The
registry/CLI path did not. The same RJ project therefore reported **MNE 0.738
from the CLI and MNE 0.848 from the GUI** — one project, one module, two answers,
against the `PROJECT_GUIDE` contract that "GUI, CLI and tests are interchangeable
front-ends". Fixed here rather than filed, per CLAUDE.md required practices 3
(*make it structural*) and 4 (*generalize on first find*): the margin is a
statement **about** MC and MD, so there must be exactly one MC/MD.

**Deliverables.**

- **`resolve_mach_margin` — the single owner of the margin decision**
  (`modules/structural_speeds.py`), with `MACH_MARGIN_DEFAULT = 0.07` and
  `MACH_MARGIN_FLOOR = 0.05` as its only constants. Consumed by the design-speed
  resolution, the M2-10 placard ladder and `validation.py`; the ladder's
  hardcoded `_MC_MD_MARGIN = 0.05` is deleted, so the two can no longer disagree
  about one project's margin.
- **`_resolve_vd`** implements the regulation's disjunction. On the margin route
  the 1.25·VC floor is deliberately **not** also applied — applying both would
  re-impose exactly the constraint the "or" exists to relieve — and the value it
  *would* have imposed is reported (`vd_ratio_floor`) so the difference between
  the two regulatory routes is auditable rather than implicit. Preconditions,
  each raising with a concrete message: category "C", a non-zero shoulder
  altitude, a chosen VD.
- **Schema v40.** `speeds.vd_basis` (`VdBasis.SPEED_RATIO` | `MACH_MARGIN`),
  `mach_margin_min`, `mach_margin_basis`, `vb_kt`; `mach_limit.mc`/`.md`
  **removed**; hop `migrations._v39_mach_limit_mc_md`; frozen fixture
  `tests/fixtures_schema/v39_mach_limit_mc_md.json` (and a new `v40_current.json`).
  An unrecognised `vd_basis` is refused at read — silently reading it as
  `speed_ratio` would reapply the 1.25·VC floor to a project that asked for the
  margin route, i.e. the defect re-entering through the file path.
- **MC/MD single-sourced.** `mach_limit_lines(inp, mc, md)`; `mach_limit.run`,
  `report/content.py` (both the design-speed table and the speed–altitude figure)
  and the Streamlit tab all take them from `design_speed_values`.
- **VB (25.335(d))** accepted as input and checked for 25.335(a) ordering only.
- **GUI**: a dive-speed-basis radio, the margin and basis inputs (widget
  `min_value` = 0.05 so an illegal value cannot be expressed), a persistent
  certification-risk warning below 0.07 M, a three-metric headline of the route's
  result, and the VB input.
- **Regulation text captured first** (the blocking step): new
  `reference/14CFR_25_335_design_airspeeds.md` with verbatim 25.335(a)/(b)/(d)
  and the amendment history; `reference/14CFR_MC_MD_speed_margin.md` §5 records
  the policy as implemented.

**Test / Acceptance.** 809 tests green, ruff clean, coverage 93 %.

- **FAR 23 oracles unmoved** — Appendix A p155 VD 198.53, p156 VD 212.5,
  MC 0.323 / MD 0.403 (±0.1 %).
- **Reduction invariant** — `test_speed_ratio_route_reproduces_todays_numbers_on_every_example`
  compares VD/VC/VA/VF for all six shipped examples at 1e-6 against values read
  off the pre-change build (commit 5c7809b), so it is a real before/after
  comparison rather than a restatement of current behaviour. It caught one wrong
  expectation while being written: `cessna_210`'s VD is governed by the K_d·VCmin
  term (214.53), not the 1.25·VC floor (208.75).
- **Margin route** — VD 350 honoured (MD 0.85112, margin +0.09728, unflagged);
  VD 320 raised to 338.79 (margin exactly 0.07000); the policy table
  parametrised; category and precondition gates; the "not a sufficiency
  demonstration" sentence asserted present.
- **MC/MD drift guard** (`test_mc_md_come_from_strspeed_on_every_front_end`) —
  for every shipped example, the registry path's MC/MD/MNE/MFC equal
  `design_speed_values`' at 1e-12, plus a structural check that the duplicate
  fields no longer exist. This is the test that would have caught the second
  defect.
- **Containment, verified explicitly** rather than eyeballed: the Imperial
  digest baseline shows the RJ moving in its dive-line channels only
  (`flight_envelope`, `select`, `balloads`, `taildist`, the body and tail decks,
  the case index) and **every other example moving only in `mach_limit`** — no
  load channel on any other fixture, and the RJ wing deck unchanged because its
  governing wing cases are not dive-line. A new mechanism test
  (`test_only_the_dive_line_moves_with_vd`) pins the cause permanently: every
  `*D` envelope case flies at VD and no `*A`/`*C` case does.
- **Re-baselined:** `tests/fixtures_imperial/digests.json`, `DATA_DICTIONARY.md`,
  `EXPECTED_FIELDS_HASH`. The RJ's dive-line loads **decrease** — recorded as a
  defect fix, not a methodology change: the previous values were wrong.
  MACHLIM output moves for the GA fixtures too, because their stored MC/MD were
  the manual's *rounded* printed figures (0.323/0.403) and the derived pair is
  full precision (0.32264/0.40330); the printed oracles still pass at ±0.1 %.

**Key decisions** (user, 2026-08-08; recorded in
[`03_resolved_decisions.md`](03_resolved_decisions.md)).

- **D-1 — concept category "C" only.** FAR 23.335(b)(4) offers the margin route
  to N/U/A as well; it is withheld so the oracle-locked FAR 23 path is *provably*
  untouched. `vd_basis = "mach_margin"` in a FAR 23 category raises. Extension is
  a backlog item.
- **D-2 — explicit `vd_basis` enum**, not automatic selection: the governing rule
  stays visible in the JSON and no existing project changes behaviour on load.
- **D-3 — fix the MC/MD single source in this step** rather than filing it.
- **D-4 — 0.07 default, 0.05 floor, justification in between.** The floor
  constrains what may be **declared**; a chosen VD short of the declared margin is
  **raised**, like every other design-speed minimum in STRSPEED.
- **D-5 — VB input-only.** 25.335(a) is `VC ≥ VB + 1.32·U_ref`, verified against
  the CFR in step 0; U_ref (25.341(a)(5)(i)) does not exist in the suite until
  F25-1, so only the ordering is checked and the deferral is stated in the module
  docstring, the reference file and the gap-analysis row — shipping half a margin
  check silently is the failure mode the reference-first rule exists to prevent.
- **D-7 — the 25.335(b)(1) upset criterion is out of scope**, filed. It matters
  that this is loud: 25.335(b) wants the *greater of* two terms and only one is
  implemented, so every margin-route output carries a "NOT A SUFFICIENCY
  DEMONSTRATION" sentence.

Plan: [`../30_future/08_f25-2_speeds_placards_plan.md`](../30_future/08_f25-2_speeds_placards_plan.md).

## M4-5 — Aero-coefficient curves + closure on Aerodynamic Data (complete 2026-08-05, tier M)

CL–α / drag-polar / CM–α plots with the balanced V-n points overlaid, the stall
clamps drawn and two closure metrics (recovered CL — a 1e-9 **drift guard**, since
the recovery and the polynomial are algebraically the same number within a
converged point — and the stall-clamp margin, which does carry content). New pure
`sloads/aero_curves.py` is the single authority for evaluating the
airplane-less-tail polynomials; `modules/flight_envelope` imports it (arithmetic
bit-for-bit unchanged — Glauert passed as `(g, gmn)`, oracles unmoved). Five
coefficient-entry checks added to `sloads.validation`, tagged for the page,
silent on every shipped fixture; **no** moment-slope check (a positive M1 is the
normal airplane-less-tail state, including on the Appendix A oracle). Gates:
`tests/test_aero_curves.py` (22) + `tests/test_aero_coefficients_view.py` (6);
closure asserted on ga6 + both concept fixtures. Two findings raised on the way:
the fuselage-moment Apply was rewriting the CLmax scalars (fixed here, see
`CHANGELOG.md`), and the ATR-42 example's seven Mach-capped points above the
stall CL (filed in the backlog, pinned by test). Closes decision **D-10**.

## M4-2 — Unified load-case identity + deck SUBCASE map (complete 2026-08-05)

**Objective.** One case-ID authority per component, end to end: from the SELECT
pick, through the structural module that consumes it, into the exported deck.
Three defects sat under the heading. (1) The same wing condition was entered
**twice** — `select_wing` searched the V-n matrix and stamped `W-40..49`, while
the hand-authored `WingMassInput.cases` that actually drives WINGINER/NETLOADS
stamped `W-01..39` positionally — so one physical PHAA appeared in the exported
case index under two ids, with two independently-typed sets of Nz/Nx free to
disagree. (2) `one_engine_out` minted `VT-01..` from a fresh allocator, as did
`select_vtail`: an **outright collision**, the exact failure `case_ids.py` bands
away everywhere else, left un-banded. (3) Deck `SUBCASE`/`SID` were the case's
*position* in the export, so `filter_by_selected_case_ids` silently renumbered
every surviving subcase and `TITLE` carried the V-n number, not the case id —
nothing let a deck consumer trace `SUBCASE 3` back to its governing condition.

**Deliverables.**

- **`case_ids.py` — the authority.** `WING_SLOTS` (PHAA 1, PLAA 2, PMAA 3,
  NMAA 4, ACRL 5, TORS 6) makes the wing `seq` a property of the **condition**,
  not of a list position; `WING_BAND_SELECT` (40–49) is retired; `WING_BAND_EXTRA`
  (20–39) holds a hand-authored case SELECT does not emit; `VTAIL_BAND_ONENGOUT`
  (30–49) ends the ONENGOUT collision; `subcase_id()` maps a case id to its deck
  integer (per-component block of 100: `W-03` → 103, `VT-31` → 331).
- **One ID per physical condition.** `select.py` takes wing ids from the slot
  table; `wing_inertia.wing_case_ref` **returns SELECT's own `CaseRef`** when the
  condition matches by name, so the spanwise distribution is another deliverable
  of the same case, which is what `case_index_rows_from`'s dedupe-by-`case_id`
  always assumed.
- **`wing_inertia.resolve_wing_cases`.** An empty `WingMassInput.cases` derives
  one case per `envelope.critical` wing condition; a non-empty list is returned
  untouched, so every shipped example and every Appendix A oracle takes the path
  it always did. Both WINGINER and NETLOADS resolve through it, and the Wing Loads
  page gained a **Pull cases from SELECT** button that materialises the same list
  into the editable table rather than deriving behind the page's back.
- **Deck case identity.** `SUBCASE` and `SID` are one integer from
  `subcase_id(case_id)` across all four card writers; each deck opens with a `$`
  subcase-map block (`$ SUBCASE 103 = W-03 -- PHAA -- FAR 23.333(b)`); the
  stick deck carries `LABEL = W-03`; the case-index CSV gained a `SUBCASE`
  column. `sid_base + index` survives only for results carrying no `CaseRef`.
- **Schema v39 + doc sync.** No field added or removed — what changes is which
  *string* a wing/ONENGOUT case carries. `io._critical_from_dict` now drops a
  `selected_case_ids` entry that matches no condition **with a warning** (a stale
  id never filtered anything, so it silently *widened* the governing-set export).
  `PROGRAM_SPEC.md` (case-ID section + the sbeam-bridge SUBCASE scheme),
  `CONVENTIONS.md` §4, `GUI_design.md`, `DATA_DICTIONARY.md` regenerated.

**Test / Acceptance.** Appendix A oracles unchanged (derivation never fires for a
project that has cases). `tests/test_case_ids.py` rewritten around the new rule:
the same wing condition has one id everywhere, a missing pick leaves a gap rather
than renumbering, ONENGOUT cannot collide with `select_vtail`, and `subcase_id`
is injective across every band in use. New `tests/test_wing_case_derivation.py`
is the decision-7 closure gate. `tests/test_sbeam_bridge.py` gained the
filtered-export stability test (deselecting a case leaves the others' `SUBCASE`
numbers exactly where they were) and a subcase-map content test. The frozen
Imperial digest baseline was **deliberately regenerated**: wing case ids, deck
SIDs and the new index column all move Imperial bytes. 759 tests pass; ruff clean.

**Key decisions.** Ten, agreed in chat 2026-08-05 before implementation and
recorded on the backlog item: unify rather than link (1); derive only when empty,
explicit always wins (2); derive from all conditions, not the D5 opt-out subset
(3); fixed slots rather than positions (4); band ONENGOUT rather than share
SELECT's counter — "link" means documented disjointness, since the 23.367 dynamic
case is not one of SELECT's picks (5); migrate in the cheap direction, warn on
stale ids (6); hold the derivation to a closure gate instead of touching the
oracle path (7); deterministic per-component subcase blocks, chosen now so L-1's
assembled deck needs no re-cut (8); SID := SUBCASE (9); record the map in the
deck, the index, `PROGRAM_SPEC.md` and `CONVENTIONS.md` (10).

**Found while implementing (decision 7's gate paying for itself).** The derived
and hand-entered ACRL cases agree on Nz/Nx but **not** on the air-load CL/V
(derived ≈1.30 at 117.4 kt vs the worked example's 1.55 at 116 kt), and a derived
ACRL carries no unbalanced rolling moment. Filed as an open defect rather than
absorbed into a loose tolerance; the hand-entered route every example uses is
unaffected.

---

## M3-3b — Step G8 remainder: the summary report document (complete 2026-08-05)

**Objective.** Finish Step G8. G8.1–G8.3 and the coverage matrix had shipped
(the `sloads/report/` package, the v36 document-control fields, the methods &
limitations statement in every export channel); the **document itself** did not
render. This step built the content model, the LaTeX renderer with its three
pgfplots figures, the PDF compile step and the two front-ends, against the
standard in [`../10_standard/SUMMARY_REPORT.md`](../10_standard/SUMMARY_REPORT.md).

**Deliverables.**

- **G8.4 (rest) — `sloads/report/content.py`.** `Project` + module results →
  `ReportDocument` (`Section` / `Table` / `Figure` / `PlotData`), covering §§1–5
  plus the bundle manifest. Every load is scaled to ULTIMATE by **its own case's**
  `safety_factor`, carries the `-ULT` marker of the selected system in its column
  header, and names the case *and* station it occurs at; envelopes are reported
  two-sided (max **and** min). Nothing is recomputed: the governing tables are
  `report.governing_loads_table`'s own output, and the distributions come from
  `component_loads()` — a new shared builder the Export page now uses too, so the
  report and the CSV/BDF files beside it in a bundle cannot describe different
  numbers. Sections whose inputs are absent carry an `absent_reason` instead of
  disappearing or rendering an empty table.
- **G8.5 — `latex.py` + `plots_tex.py`.** The `.tex` renderer (title page +
  document-control/signature block, ToC, `fancyhdr` running heads, "page *n* of
  *m*", `longtable`/`booktabs` tables) and the three figures as pgfplots source:
  V-n, weight/CG, and the speed–altitude envelope (new work — the Mach-limit
  lines had no GUI equivalent). Traces are distinguished by **line style, not
  colour**, so the document survives greyscale print. Two things earned their own
  machinery: **escaping** (every user string, plus a Unicode→LaTeX
  transliteration so one `.tex` compiles under both tectonic/XeTeX and pdflatex)
  and **column widths** (a `p` column never wraps inside a word, so widths are
  proportioned in points with a floor at each column's longest token, dropping to
  `\footnotesize` rather than overflowing).
- **G8.6 — `sloads/export/pdf.py` + the two front-ends.** Engine discovery
  (`tectonic` → `latexmk` → `pdflatex`, overridable with `SLOADS_TEX_ENGINE`),
  compile in a temp directory, return bytes. It **never raises**: a missing engine
  or a failed compile comes back as a `CompileResult` with a log, which the Export
  page shows as a caption. A new **Summary report** section on the Export page
  (`.tex` always, PDF on demand, both in the bundle `.zip`), and `cli.py --report
  PATH` (a `.pdf` path compiles; `--generated` supplies the timestamp).
- **G8.7 — doc sync + close-out.** This entry, the backlog removal, the
  `CHANGELOG` entry, `SUMMARY_REPORT.md` §6 (each conformance box now names the
  test that holds it), `PROGRAM_SPEC.md`, `PROJECT_GUIDE.md` §4/§5,
  `GUI_design.md`, `GUI_USER_GUIDE.md`, `00_INDEX.md` and `cspell.json`.

**Test / Acceptance.** `tests/test_report_content.py` (23 tests: structure,
degradation, ultimate marking, two-sided maxima with stations, SI conversion and
the aviation-standard carve-out, the governing-table identity, deselected-case
scoping, the §5 excluded-content sweep), `tests/test_report_latex.py` (17:
escaping, determinism, greyscale, figure/corner-point agreement, the
concept-caveat conditionality), `tests/test_pdf_compile.py` (engine discovery
everywhere; the real compile `skipif` no engine — CI skips it by design, since
tectonic downloads its support bundle on first use), plus additions to
`test_methods_stamp.py` (the report is a stamped channel like the others),
`test_views_smoke.py` (the Export page on an empty project) and
`test_persistence.py` (the three compiled-PDF session keys allow-listed as
output, not input). Suite green; `ruff` clean; the Appendix A oracles and
`test_deliverable_units.py`'s frozen Imperial baseline are untouched.

**Key decisions.**

- **Live recompute, not persisted slices.** The report builds its results the way
  the Export page does, so it works on a project loaded from JSON that has never
  been through the GUI, and cannot lag the exports in its own bundle.
- **Depth follows G8-4.** Modules that emit tens of discrete reaction cases
  (landing gear, engine mount) are summarised as two-sided extremes naming the
  governing case and SF, with the full set in the case index and the module CSV —
  inlining them would bury the governing cases.
- **The derived gust velocities are tabulated, not plotted.** They are a velocity
  in fps and share no axis with the Mach-limited equivalent airspeeds; plotting
  both on one figure would have been a unit error rendered as a picture.
- **The methods statement lost its backlog IDs.** `SUMMARY_REPORT.md` §5 excludes
  internal development artifacts from the deliverable, and the statement is now a
  report section — so the standing limitations are phrased in engineering terms
  with the tracking IDs left in the repository.

## M4-20 — Deliverables render in the user-selected unit system (complete 2026-08-04)

**Objective.** Close the gap the 2026-08-03 standard change opened. `00_program_overview.md`
(*Deliverable units follow the user's selection*) and `SUMMARY_REPORT.md` §3.5 declared that
the whole export bundle renders in the system the user chose; the code still wrote every
deliverable in Imperial, so the Imperial/SI toggle was display-only and the documentation
described behaviour that did not exist. Blocking **M3-3b** G8.5: a `.tex` renderer written
against Imperial-only writers would have to be retrofitted.

**Deliverables.** Seven steps, each approved and shipped separately.

- **Step 1 — the unit sets (`units.py`).** `Channel` (HUMAN / SOLVER), `Dimension`,
  `DeliverableUnits`, `deliverable_units(system, channel)`, `units_statement`,
  `system_name`. Imperial is the **all-1.0 identity**, so no writer needs an
  `if system == IMPERIAL` branch and "Imperial is unchanged" is structural rather than
  promised. Derived factors (`LB_IN_TO_N_M`, `LB_IN_TO_N_MM`, `PSI_TO_MPA`) are computed
  from named base constants, never quoted.
- **Step 2 — the selection (`Project.unit_system`, schema v38).** A *preference* field,
  additive with a total default so it needs no migration hop; `units.unit_system_from`
  degrades an unrecognised value to Imperial rather than raising; CLI `--units imperial|si`
  with `resolve_units` (flag → project → Imperial); the sidebar toggle writes the project
  field, so a unit change reads as an unsaved change (**D-22**).
  `components.active_system()` re-pointed at the field — one function, no call-site changes.
- **Step 3 — the human channel.** `io.load_cases_csv` / `write_load_cases_csv` take
  `system=` and convert **once**, inside the writer. `report/render.py` was not touched: it
  reads each `LoadValue.units` string, so the SI headers fell out of the existing
  `_detect_unit`.
- **Step 4 — the solver channel.** All 17 `sbeam_bridge` writers take `system=`;
  `export/coordinates.py` is the single scale point (`to_grid`/`to_force`/`to_moment`/
  `to_pressure`), and card fields *and* CSV cells both route through it, so a span CSV
  cannot disagree with the deck beside it. Those four **raise** on a dimensionally
  inconsistent set.
- **Step 5 — the in-band statement.** `methods_statement(project, system=…)` gains a
  `UNITS:` paragraph, so the block already wrapped per channel (G8-3) carries the unit set
  into every file at once: `# UNITS:` in each CSV, `$ UNITS:` in each BDF, the paragraph in
  `METHODS.txt`; the workbook gets a `Units` row. The BASIS `-ULT` marker list is derived
  from the unit sets rather than hard-coded.
- **Step 6 — the GUI.** The Export page resolves `active_system()` **once** and hands that
  value to all eleven artifact calls, stating the system in a caption built from
  `deliverable_units` itself. The ten other views' download buttons follow their page's
  system.
- **Step 7 — close-out.** The frozen Imperial baseline, the bundle/round-trip/CLI tests,
  and this record.

**Defects found and fixed along the way** (none were the announced work):

- **`lb-in` and `lb/in^2` had no SI mapping** — **1580 values across the six examples**
  stayed Imperial inside an otherwise-converted SI table (root bending/torsion, pitching
  moments, every control-surface design pressure). The dead `"knot"` row, which converted
  nothing because no producer emits that string, is gone.
- **The solver set had the human channel's `kPa`** — the D-19 defect one dimension over.
  Fixed with a derived `PSI_TO_MPA`; `is_consistent` now checks **both** derived dimensions
  (`moment == force × length` *and* `pressure == force / length²`) so the next one cannot be
  missed the same way.
- **The four sbeam `.bdf` decks carried no methods or units statement at all.** The Export
  page built a `bdf_comment_block` and never applied it; `ruff` could not catch it because
  the unused name is module-level and its unused-variable rule is a *local* check.
- **Twelve views read `st.session_state["unit_system"]` directly**, a second authority for
  the selection that `GUI_design.md` §7 already forbade, and that made step 2's re-point of
  `active_system()` reach only the views going through `unit_number_input`/`page`.
- **`weight_mass.py` passed display-converted results to `load_cases_csv`**, whose writer
  converts internally since step 3 — so that one page's CSV came out SI while every other
  page's came out Imperial.

**Test / Acceptance.** `tests/test_deliverable_units.py` (47 tests) plus
`tests/imperial_baseline.py` + `tests/fixtures_imperial/digests.json`:

| Guarantee | Test |
|---|---|
| **Imperial output is unchanged** (D-21) | 6 examples × 256 channels digested and frozen; the guard names the drifted channel |
| Dimensional identity | `moment == force × length` and `pressure == force / length²`, both systems |
| Channel split | HUMAN ≠ SOLVER in SI, identical in Imperial |
| One bundle, one system | every channel of a real bundle states the same system, and not the other |
| SI closure | the SI FORCE set sums to the stated root shear, the MOMENT set to the stated torsion |
| Aviation carve-out | KEAS/altitude columns byte-identical in both systems, CSV and report |
| Round trip | Imperial → SI → Imperial exact, per dimension and through `LoadValue` |
| Oracles untouched | no `sloads/modules/*.py` calls a conversion function — the calc is structurally out of this path |
| CLI | `--units si` vs. default; `--units si --export-sbeam` writes the solver set |
| No silent defaults | source guards: the Export page resolves the system once and no writer call omits it |

Suite: **653 → 702 passed**, 93 % coverage, `ruff` clean.

**Key decisions.** **D-19** the solver deck is one *consistent* set (N / mm / N·mm, extended
in step 4 to MPa) — an `N·m` moment in a deck whose GRIDs are mm is a silent 1000× torsion
error in a file that parses cleanly and sizes structure wrongly; **D-20** SI design pressure
is `kPa-ULT` in the human channel; **D-21** the in-band unit statement wins over
byte-identical Imperial output, so the guard is strip-and-compare; **D-22** the sidebar
toggle writes `Project.unit_system` and marks the project dirty. Plan and full rationale:
[`../30_future/06_m4-20_deliverable_units_plan.md`](../30_future/06_m4-20_deliverable_units_plan.md).

**Left open** (logged, not folded in): **L-8g** the CLI carries no G8.3 methods stamp;
**L-8h** `ft^2`/`lb/ft^2`/`ft/s` still have no SI result mapping (17 values, none a load);
**L-8i** the per-page hand-built LIMIT CSVs ignore the toggle and state no units.

---

## M4-9 — `LoadValue.key`: de-string the load-case semantics (complete 2026-08-04)

**Objective.** Take the meaning of a result off its display label. Before this,
`report.load_cases_to_rows` decided which CSV column a value belonged in by
comparing `v.label` against string literals (`"Vertical down load"`,
`"Applied at X"`, a `Case (\d+) \((.*)\): (Myy|Mzz)` regex over the label),
and 13 view lookups plus ~150 test assertions did the same. Rewording a column
heading — an editorial change with no engineering content — made the lookup
return `None`, `_val` turned that into `""`, and the CSV shipped with an empty
cell. No exception, no warning, no failing test. The 2026-07-21 review's top
refactor, and the last wall before the Phase-F25 supplements start emitting new
quantities.

**Deliverables.**

- **`LoadValue.key`** (`models/results.py`) — a stable snake_case machine
  identity, declared last so the long-standing positional
  `LoadValue(label, value, units)` calls keep working. `label` is now explicitly
  cosmetic: it may be reworded, re-annotated or translated freely and nothing may
  branch on it.
- **`sloads/load_keys.py`** — the canonical keys that cross a module boundary:
  `loc_x/y/z`, `fz_vertical`, `fz_vertical_2_5g`, `fy_side`, `fx_thrust`,
  `mx_mount_torque`, `LOAD_CASE_KEYS`, and `gyro_key`/`parse_gyro_key` for the
  four 23.371(b) sign combinations. Producer and consumer import the same
  constant. Keys internal to one module are named inline at the producing site.
- **327 producing sites keyed** across 21 modules — 303 static labels applied by
  script, 23 dynamic-label sites (`f"Root torsion Myy ({axis})"`, the per-station
  and per-engine series, the ballast marker rows) done by hand. `net_loads`'
  root-torsion row is the case in miniature: its label changes with the
  elastic-axis input while the quantity does not.
- **Consumers re-pointed** — `report/render.py` (`has_load_case_data`, `_find`,
  `_find_any`, `_detect_unit`, `_result_location`, the gyro sub-case split),
  10 view lookups across 8 pages, and three calc-side cross-module lookups that
  were reading `"Total area"` / `"MAC"` / `"XBAR (fus station)"` off another
  module's labels (`validation.py`, `structural_speeds`, `landing`,
  `weight_envelope`, `weight_estimate`, `flight_envelope.design_inputs`).
- **`tests/helpers.py` re-pointed at `key`** and ~154 call sites converted —
  one edit to three functions, which is exactly what M4-12a consolidated them
  for. `values_by_label` → `values_by_key`.
- **Schema v36 → v37 + a real backfill hop.** `migrations._v36_load_value_keys`
  fills `key` on the persisted SELECT critical conditions from a **frozen**
  label→key table of the 31 labels `select.py` could ever have written. M4-9 is
  the migration chain's first genuine customer (decision D-12(a)), which is why
  M4-10 was sequenced ahead of it.
- **`cg_estimate` no longer takes a dict.** It indexed `geom["MAC"]`, and the
  Configuration page passed it the *LoadValue* table instead of the geometry
  dict — the two worked only because they happened to spell `"MAC"` the same
  way. It now takes `mac`/`xlemac` as numbers.

**Test / Acceptance.** 653 pass (648 → 653), `ruff` clean, coverage 93 %.

- **Nothing changed.** A 405k-line snapshot of every module's every
  `(label, value, units, quantity)`, every rendered row and every text report,
  across all six examples, is **byte-identical** before and after — captured
  before the first edit and re-diffed after each stage.
- **The relabel guard** — `test_report.py`'s three new tests replace every label
  with `"relabelled i-j"` and require the CSV, the schema choice
  (`has_load_case_data`) and the four gyro sub-cases to be unaffected. Each was
  verified to be **load-bearing** by reverting its own code path to label
  matching and confirming it fails. The first draft passed for the wrong reason —
  a globally broken lookup blanks *both* sides and the equality assertion still
  held — so it now also requires the load cells to be non-blank.
- **Key hygiene** — every `LoadValue` produced by every module across all six
  examples has a non-empty key, unique within its `ConditionResult`.
- The **fields-hash tripwire from M4-10 fired on cue**, which is what it was
  built for.
- `test_migrations.py` gains a fixture that actually exercises the backfill
  (nothing shipped carries persisted SELECT loads — the slice is computed
  in-session), including a label no build ever emitted, plus a test that the
  frozen table has not drifted from what `select.py` emits today.

**Key decisions.**

1. **An unknown label backfills to an empty key, not a guessed one.** Inventing
   an identity for a label this build has never emitted would be worse than
   admitting ignorance; the row still renders, and re-running SELECT regenerates
   it properly.
2. **The gyro sub-case *description* still comes off the label** — deliberately,
   because it is display text. Which rows exist and which component each value
   is now come from the key, so a relabel degrades the wording of one cell
   instead of dropping four rows.
3. **Keys were seeded by slugifying the labels, then frozen.** The initial
   choice came from the label; its stability does not. `load_keys.key_from_label`
   survives for the one case where the "label" genuinely *is* data —
   `weight_estimate`'s group rows, whose names are the keys of the
   `WT_*_FRACTIONS` tables.
4. **Asserting on a label stays correct where the label is the subject** —
   `test_net_loads` (every root torsion names its axis) and `test_weight_envelope`
   (the ballast marker rows explain *why* there is no ballast). Both are noted in
   `PROJECT_GUIDE.md` §5 so the exception is not mistaken for an oversight.

---

## M4-10 — io.py migration chain + schema guards (complete 2026-08-04)

**Objective.** Replace `io.py`'s two structural weaknesses: deciding what it was
reading by **sniffing keys** (a 19-clause `or` gate enumerating every slice name),
and handling each legacy file shape with an **inline shim threaded through the
readers** as a `legacy_*` parameter. Adding a slice meant remembering to extend
the gate, or a real project would be silently misread as a bare engine file; and
"is this key absent because the file is old, or because the user never set it?"
was answered ad hoc, differently, at five separate sites.

**Archaeology (sub-step 1 — the plan noted no document recorded this).**
Reconstructed from the version history in `models/project.py` and the step
records here, and now committed as the table in `sloads/migrations.py`'s
docstring:

| hop | file-shape change | was handled by |
|---|---|---|
| v0 | the whole file is a bare `EngineInput` (Phase-0 `engloads`, pre-`Project`) | the or-gate's `else` branch |
| v0 | singular `"engine"` instead of `"engines": [...]` | `_engines_from_dict` |
| v18 | `aero_coeffs` split out of `flight_loads.configurations` | `_legacy_aero_coeffs_from_flight_loads` |
| v19 | `weight.cg_cases` split out of `flight_loads.cg_cases` | `_legacy_cg_cases_from_flight_loads` |
| v24 | ft/in² geometry keys renamed to in/ft² | `_rename_legacy_units` (5 call sites) |
| v25 | top-level `configuration` → `geometry.parametric` | `legacy_configuration=` |
| v27 | top-level `tail_loads`/`vtail_loads` → `geometry.empennage` | `legacy_tail_loads=` / `legacy_vtail_loads=` |
| v28 | top-level `landing` gear → `geometry.landing_gear` | `legacy_landing=` |

Versions 1–17, 20–23, 26 and 29–36 are additive-only and need no hop.

**Deliverables.**
- **`sloads/migrations.py`** — `MIGRATIONS: {from_version: hop}` applied in
  ascending order on a deep copy, then **one tolerant reader**.
  `project_from_dict` now sees a current-shape dict only. A file claiming a
  *newer* version passes through untouched, so forward compatibility degrades to
  "read what you understand" instead of being mangled by hops that do not apply.
- **`is_project_dict`** replaces the 19-clause gate with a set intersection
  against `Project`'s **own dataclass fields** plus the four historical top-level
  names — so adding a slice can no longer silently downgrade a project to an
  engine-only read. A test asserts every `Project` field is recognised.
- **All five shims deleted** and the three `legacy_*` reader parameters removed.
  `io.py` 1,290 → **1,180 lines**; the legacy handling that was scattered across
  five call sites is 282 documented lines in one module.
- **Frozen fixtures** — `tests/fixtures_schema/`, one per historical shape
  actually reachable: v0 bare engine, v18, v24, v26, v28, v36.
- **Two schema guards** (`tests/test_schema_guards.py`): a **sentinel round-trip**
  that walks every persisted scalar on a real project and asserts none is lost by
  `io.py`'s hand-written field lists, and a **fields hash** tripwire over every
  persisted dataclass's field names — the `SCHEMA_VERSION` discipline was
  previously unenforced. Its failure message says exactly what to do.

**One real bug found by the existing suite.** The v24 unit-rename hop initially
covered `vtail_loads` but not `tail_loads`, so a pre-G0 file's
`airplane_length_ft` was dropped instead of rescaled.
`test_legacy_ft_sqin_keys_migrate_to_canonical` caught it. The ordering
constraint behind it is now a comment in the hop: both tail slices are still
top-level at v24, because the v27 hop that folds them into `geometry.empennage`
runs *after*.

**A deliberate behaviour change, with two tests updated to match.** The shims ran
on **every** file regardless of version; the hops are version-gated. Two tests
named "pre-schema-18/19 files" were in fact mutating a *current* dict, so they
passed for the wrong reason — and the old behaviour meant a v36 project that
legitimately had no `weight.cg_cases` had them silently invented from
`flight_loads`, and one with no `aero_coeffs` had a set resurrected from a stale
`flight_loads.configurations`. Both fixtures now declare the version they claim
to test (18 and 17). This is a correctness improvement, not a loosening.

**Test / Acceptance.** **646 tests pass** (611 → 646, +35), `ruff` clean.
- All 6 `examples/*.project.json` round-trip **byte-identically** — asserted on
  the round-tripped dict, not the file, per the plan.
- Every frozen fixture loads, and each is asserted to carry its data *across* the
  hop (geometry present, tail slices on the empennage, gear on the geometry, CG
  cases recovered) — the hops move data, they do not merely tolerate its absence.
- `migrate` is idempotent, does not mutate the caller's dict (the GUI hands the
  same dict to the JSON editor), and is a **no-op for a current file**.
- The fields-hash tripwire is itself tested: a test injects a new persisted
  dataclass and asserts the hash notices, then that it resets. A tripwire that
  cannot fire is worse than none.

**Not done — sub-step 6, tracked as M4-10b.** Retiring the
`tail_loads`/`vtail_loads` property proxies (D-15) is **73 reads and 19 writes
across 21 files**. The risk is the writes: the current setter silently no-ops on
`None` when there is no geometry, so each assignment site needs looking at rather
than a regex. The M4-10 plan sequenced it last precisely so it could be attributed
separately, and that is where it stays — this step is the one that can break a
user's saved project, and it is now green and verified.

---

## G8.1–G8.3 + coverage matrix — the report package, document control, and universal methods stamping (complete 2026-08-04)

**Objective.** The first four sub-steps of Step G8 (backlog M3-3): make room for
the summary report, add its document-control schema, and — the backlog item's
**explicit ask** — get a methods-and-limitations statement into every export
channel so downstream sizing inherits the concept-mode caveat the UI already
shows. The report *document* is not part of this entry; it is backlog **M3-3b**.

**Deliverables.**
- **G8.1 — `sloads/report.py` → `sloads/report/`**, the same mechanical move
  `models.py` → `models/` made at M3-1. Today's code is `render.py` verbatim
  (relative imports rebased one level) and every public name is re-exported, so
  all 15 importing modules are untouched. The move surfaced one thing that was
  not mechanical: `tests/test_results_review.py` imported `report._fmt` across
  the module boundary, which the M4-12b public-symbol contract makes a defect —
  promoted to **`format_value`** and listed in `__all__` rather than re-exported
  under its private name.
- **G8.2 — document control at schema v36.** `Project.revision` /
  `.checked_by` / `.approved_by` / `.description`, round-tripped in `io.py`,
  written only when set so a project that never fills them in serialises exactly
  as before. Editable on the Dashboard behind a *Document control* expander. All
  six example fixtures, `DATA_DICTIONARY.md` and `GUI_design.md`'s guarded
  version paragraph updated.
- **G8.3 — `report/methods.py`, and the stamp in every channel.** One builder
  produces the eight-block statement (basis, category, verification, math,
  approved corrections, limitations, scope, provenance); two thin wrappers emit
  it as `#` (CSV) and `$` (BDF) comment blocks. Wired into `io.load_cases_csv`,
  all five sbeam CSV writers, the case-index CSV, `METHODS.txt` in the zip, and a
  new *Methods* sheet in the workbook. The statement adapts per project: the
  concept caveat lists the actual `far23_applicability` exceedances, and the
  fuselage `CLOSURE_ARTIFACT_CAVEAT` appears **verbatim** only when a case
  actually took the fallback path.
- **G8.4 (part) — `report/coverage.py`**, the FAR 23 Subpart C matrix: 52
  regulations, each classified against the `far_reference` values a run actually
  produced.

**Two corrections to the plan, made while building.**
1. **The coverage table needed a fourth status.** The plan specified three
   (covered / not applicable / not analysed). With three, the 16 regulations the
   suite does not implement at all — water loads, jacking, towing, emergency
   landing — came out as *not analysed*, i.e. as gaps, burying the 9 real ones in
   26 rows of noise. Added **`out_of_scope`**: a permanent boundary of the tool,
   declared rather than silently omitted. The GA fixture now reports 25 covered,
   2 not applicable, **9 actionable gaps**, 16 out of scope.
2. **Combined citations were being under-credited.** `flight_envelope` cites
   `"23.333/23.337/23.341/23.345/23.421"` in one string; a prefix test against
   the whole string credits only 23.333 and reports the other four as gaps
   despite their having been analysed. The matcher now splits on `/` and
   prefix-matches each token.

**One real bug found and fixed:** `strip_comment_lines` (the reader-side helper)
split on `\\n` and rejoined, silently rewriting the CRLF line endings
`csv.DictWriter` emits — corrupting the payload it exists to leave alone.

**Test / Acceptance.** **611 tests pass** (586 → 611, +25), `ruff` clean, calc
untouched.
- `tests/test_methods_stamp.py` (16) — every required block present; the
  ULTIMATE basis and default 1.5 factor stated; all three approved corrections
  listed; the twin closure-locked caveat present; the concept caveat in the
  concept fixture and **not** in the GA one; deselected case IDs named, never
  silently dropped; determinism (no clock read); every comment line marked; and
  for each channel, that a stamped CSV parses to the **same rows** as an
  unstamped one — via `csv.DictReader`, `pandas.read_csv(comment="#")`, and the
  workbook's own `_csv_to_df`.
- `tests/test_far_coverage.py` (9) — no regulation dropped or duplicated; every
  absent row carries a reason; out-of-scope rows are never gaps; the gap list
  stays short enough to be read and every gap names the module that would close
  it; turboprop-only and unflapped conclusions land as *not applicable*.

**CSV-reader audit (the plan's top risk).** Every in-repo reader was fixed in the
same change: `export/workbook._csv_to_df` (`comment="#"`), the Export page's
case-index `DictReader`, and `loads_plots`' upload reader — which can legitimately
be handed one of this tool's own stamped CSVs.

**Decision resolved: G8-5** — `revision` is **free text**, not an
auto-incrementing counter. A tool-managed number would disagree with the
drawing/report system of record the moment a project is copied.

**Outstanding, and a prerequisite the sequence missed.** `content.py`,
`latex.py`, `plots_tex.py`, `export/pdf.py` and the Export-page section are
backlog **M3-3b**. The G8 plan's §10.1 states that **M4-20 is a prerequisite for
G8's conformance tests** (the report renders in the user's selected unit system);
M4-20 is still open, so M4-20 should land **before** G8.5 — a `.tex` renderer
written against the Imperial-only writers would need retrofitting, which is the
exact trap the M4 sequence exists to avoid.

---

## M4-11a — App scaffold: the unit boundary and the page header (complete 2026-08-04)

**Objective.** Build the two shared app helpers **before** the next wave of views
is written — specifically before G8.6 adds a Summary-report section to
`export_report.py`, which is free to write against a `page()` helper that exists
and expensive to retrofit. The 2026-07-21 review scoped this as removing repeated
per-field idiom; the work turned up that the idiom was not merely repeated but
**wrong in places**, which became the step's real value.

**Baseline, re-measured 2026-08-04** (`radon`, added to the `dev` extra per
D-17 — a reporting tool, explicitly not a CI gate). The 2026-07-21 figures the
plan quoted were stale; the measured worst offenders were `_tab_design_speeds`
**CC 72**, `_three_view` **63**, `_tab_vn` **44**, `_tab_cg_inertia` **40**,
`_subject_from_project` **34**, `_tab_trim` **33**; worst MI
`configuration_layout` **B (16.92)**; 20 views / 6 572 lines.

**Deliverables.**
- **`components.unit_number_input`** — the whole GUI input unit boundary in one
  function: Imperial in, Imperial out. Three explicit modes, chosen by the
  caller and never inferred from a label: `kind=` (converted, unit-suffixed
  label, per-system widget key), `fixed_unit=KEAS`/`ALTITUDE_FT` (the D-16
  aviation carve-out — shown, never converted, key *not* suffixed), or neither
  (dimensionless). Passing both raises `ValueError`. `min_value`/`max_value` are
  Imperial too and convert with the value.
- **`components.active_system()`** — per D-16, the single read of the unit
  selection in the entire app layer; **M4-20 re-points this one function** at the
  `Project` field without touching a call site.
- **`components.page_header(key)` / `page(key)`** — the view opening (title,
  caption, applicability banner, `PageContext`), with `page()` adding an upstream
  gate as a context manager. `key` is the `workflow.BY_KEY` step key, so the
  title *and* the required slices come from `workflow.py`; each gate links to the
  step that **produces** the missing slice, so re-sequencing the workflow
  re-points every gate with no view edited. Two forms because most views are
  top-level scripts, where a context manager would mean reindenting whole files;
  `page()` is what new code and G8.6 use.

**Four real defects fixed** (all found by building the helper, none previously
reported):
1. **~40 fields ignored the unit toggle entirely.** The Geometry page's
   empennage (33), landing-gear (7) and engine-CG (3) forms hard-coded Imperial
   unit strings into their labels — `"H-tail area ST (ft²)"`, `"Tread between
   mains (in)"` — and did no conversion, so an SI user saw `(in)` and had their
   entry stored as inches while the sidebar said SI. The gear caption even
   documented it: *"Values are Imperial (in)."*
2. **A double conversion in the layout Apply handler.** With the widgets now
   returning Imperial, the handler's own `to_imperial_scalar` fired a second
   time: a 184 ft² wing was stored as **1982 ft²**, in SI only. Caught by the new
   through-the-view test, not by review.
3. **Untouched fields drifted the project.** The display seed is rounded to 4
   decimals for legibility; converting *that* home returns a value a hair off the
   original, so an SI user's project changed on every Apply, forever. The helper
   now returns the caller's own Imperial value when the field is untouched.
4. **Bounds were not converted.** A non-zero `min_value` (an Imperial floor)
   would have become an SI-magnitude floor and silently stopped constraining.

Also fixed: two `"CG station … (in)"` fields in `flight_envelope`'s trim tab, and
`structural_speeds`' shoulder altitude moved onto the explicit `ALTITUDE_FT`
carve-out rather than a hand-typed unit.

**Adopted in** `configuration_layout` (all 43 converted fields + the `_num`
adapter), `flight_envelope`, `structural_speeds`, and the `page_header` preamble
in five views.

**Test / Acceptance.** **586 tests pass** (536 → 586, +50), `ruff` clean, and the
M4-12b result snapshot is untouched — this step changes no calc.
- `tests/test_app_components.py` (40 tests) pins the helper in isolation:
  Imperial→Imperial round-trip for **every** unit kind in **both** systems,
  SI-typed entry converting home, exact pass-through for the carve-out, bound
  conversion, widget-key discipline, and the ambiguity error.
- `tests/test_view_unit_roundtrip.py` (10 tests) pins it **through real views**
  via `AppTest`: type a number in a system's display units, press that form's
  Apply (by form key, per M4-12a), assert the project holds the Imperial
  equivalent — Imperial and SI runs asserting the *same* stored value from
  different typed numbers, which is precisely what a conversion bug breaks. Plus
  the no-edit drift guard. This is the M4-11 definition-of-done addition; without
  it the step's headline benefit would have been unverified — and in fact defects
  2 and 3 were found by it.

**Deliberately not done — tracked as M4-11b.** The complexity-splitting half:
the six CC-E/F view functions are **unchanged** (re-measured after; identical),
and the projected "1.5–2k lines removed" was not earned — the app layer *grew*
~170 net lines, trading duplicated idiom for one documented, tested helper.
`engine_mount` was left alone on purpose: it is already correct by a different
route (whole-`EngineInput` conversion at Apply via `units.to_imperial`), so
per-field adoption there would reintroduce defect 2. None of this blocks G8 —
G8.6 needs `page()` and `unit_number_input`, which exist.

---

## M4-12b — Contract cleanups: public symbols, typed balance result, documented trap-doors (complete 2026-08-03)

**Objective.** Close the second half of the 2026-07-21 review's M4-12 batch —
the import contract — **before** M4-11 rewrites the modules that violate it.
Two `app/` files imported `sloads` underscore names outright
(`app/views/configuration_layout.py` → `wing_geometry._interp_x`,
`app/components.py` → `structural_speeds._maneuver_load_factors`), and five more
private symbols crossed module boundaries inside `sloads/`. Separately,
`htail_balance` returned a `Dict[str, float]` whose string keys *were* its API
across three modules.

This is the batch's **oracle re-run gate**: it touches `select`, `balloads`,
`flight_envelope`, `structural_speeds`, `wing_geometry`, `wing_inertia`,
`net_loads` and `airloads` — the Appendix-A-locked and twin closure-locked path.

**Deliverables.**
- **Seven symbols promoted** (D-14: underscore-drop in place + `__all__`, no
  facade), 66 sites: `wing_geometry._interp_x` → `interp_x`;
  `structural_speeds._maneuver_load_factors` → `maneuver_load_factors`;
  `flight_envelope._design_inputs` → `design_inputs`, `._sigma` →
  `density_ratio`; `select._elevator_load` → `elevator_load`,
  `._flaps_by_config_name` → `flaps_by_config_name`, `._envelope` →
  `default_envelope`. Both `app/` violations are gone.
- **`__all__` on the four defining modules** (`wing_geometry`,
  `flight_envelope`, `structural_speeds`, `select`), each under a header stating
  that an underscore-free name outside the list is still not an import contract.
- **`select.HtailBalance`** (D-13) — a `typing.NamedTuple` with lowercase
  attributes `lt25/lt50/at/delta/lt/cp`, the Ch 9 symbols tabulated in its class
  docstring. 64 dict accesses converted across `select`, `balloads` and
  `test_select`. BALLOADS' own `verify_balancing` **row** dicts are a different
  structure and deliberately keep their string keys.
- **Property-proxy trap-door documented** (D-15) — a warning block beside
  `Project.tail_loads`/`.vtail_loads` in `models/project.py` naming both hazards
  (invisible to `dataclasses.fields`/`asdict`/`replace`; the setter silently
  no-ops on `None` with no geometry) and stating that retirement is **M4-10's**.
- **Three conventions written into the porting contract** (`PROJECT_GUIDE.md`
  §5): `sync_geometry_derived(project)` first inside `run()` (seven sites, until
  now convention-by-imitation); explicit public surface with no underscored
  imports in `app/`; cross-module results typed, not stringly-keyed; and "do not
  add property proxies to `Project`".

**Test / Acceptance — the oracle gate, met.** A full result snapshot was taken
**before** any edit — every registered module, every `ConditionResult`, every
`LoadValue` (label, value, units, quantity) and every `safety_factor`, across
all **6** `examples/*.project.json` (137,589 lines of JSON) — and re-taken after.
The two are **byte-identical**, so the rename and the dict→attribute conversion
provably changed no number anywhere, including both concept fixtures. **536
tests pass** with every printed Appendix A figure and every tolerance literal
unedited (the Ch 9 case-202 hand-calc — LT25 +907.62, LT50 −387.78, δ −5.39°,
LT 519.845, CP 6.35 % — asserted through the new attributes at the same
tolerances). `ruff check sloads/ cli.py` clean.

**Key decisions.**
- **D-14 carve-out extended to `_sigma`.** D-14 resolved "mechanical strip
  unless a bare strip reads badly", with `_envelope`/`_design_inputs` named as
  the known cases. `_sigma` is a third: `constants.standard_atmosphere` already
  returns a density ratio called `sigma`, and its own comment records that
  FLTLOADS' density-ratio branch is *identical* — a public
  `flight_envelope.sigma` would present two public names for one quantity. It
  was promoted as **`density_ratio`**, and the duplication itself is logged as
  **M4-23** rather than resolved here (deduplicating it is a calc-path change,
  out of this step's scope).
- `HtailBalance` is a `NamedTuple` rather than a dataclass: it stays
  tuple-unpackable, is 3.9-compatible, and is immutable by construction, which
  suits a computed result that several modules read and none should mutate.

---

## M4-12a — Test-architecture cleanup: shared helpers + form-key button selection (complete 2026-08-03)

**Objective.** Close the first half of the 2026-07-21 review's M4-12 batch, the
half that must land **before** M4-11 rewrites the app layer. Two defects:

1. **Nine duplicated `_value` lookups** across the test suite, with three subtly
   different signatures, plus **seven modules importing fixtures out of
   `test_engine`** (and an eighth importing a BDF reader out of
   `test_sbeam_bridge`) — a test module doubling as a library.
2. **Positional Apply-button selection.** `test_dirty_flag._apply_buttons(at)`
   collected *every* button whose label contained "Apply" and indexed it
   `[0]`/`[1]`. `AppTest` flattens every form's submit button into one list, so
   an index silently rebinds the moment a view gains, loses or reorders a form —
   the test keeps passing while asserting something else. M4-11 rewrites 22
   apply handlers, so this had to be fixed first or the refactor would have been
   unverified.

Sequenced and scoped by
[`07_m4_maintainability_sequence_plan.md`](07_m4_maintainability_sequence_plan.md) §4 step 1.

**Deliverables.**
- **`tests/helpers.py`** — the D-18 API: `value_of(source, label) -> float`,
  `load_value(source, label) -> LoadValue`, `values_by_label(source) -> Dict`.
  All three take a `ModuleResult`, a `ConditionResult`, or a nested list of
  either (the normalisation `io._as_conditions` already models) and raise
  `KeyError` on a missing label, matching the helpers they replace. **This
  signature is the one M4-9 re-points at `LoadValue.key`** — fixing it here is
  the reason the consolidation comes first.
- **`tests/helpers.apply_button(at, form_key)`** — selects a form's submit
  button through `proto.form_id` and **asserts it found exactly one**, so a
  renamed key fails loudly instead of selecting nothing.
- **`tests/fixtures.py`** — `io520bb()` / `turboprop()` moved out of
  `test_engine.py`; `parse_cards` (the self-contained free-field BDF reader)
  moved out of `test_sbeam_bridge.py` into `helpers.py`. **No test module
  imports another test module** — recorded as a convention in
  `conftest.py` and `PROJECT_GUIDE.md §7`.
- **Call-site migration.** 10 files re-pointed at the shared lookups (~180
  sites, mechanical rename); `test_configuration` keeps a one-line `_props()`
  composing `values_by_label(configuration_properties(project))`.
- **Form-key selection everywhere**, not just the two sites the backlog named:
  `test_dirty_flag` (4 sites), `test_configuration_layout_view` (3, including a
  label-list presence assertion rewritten as two `apply_button` lookups) and
  `test_landing` (1).
- **Two `__main__` self-runners repaired** (`test_dirty_flag`,
  `test_configuration_layout_view`): both drove `app/views/*.py` through
  `AppTest` without putting `app/` on `sys.path`, which `conftest.py` only does
  under pytest, so the documented zero-dependency fallback died on
  `No module named 'components'`.

**Test / Acceptance.** **536 passed** — the baseline count, with every numeric
assertion unedited (this step touches `tests/` only; no `sloads/` or `app/`
change at all, verified against the plan's acceptance clause). `ruff check
sloads/ cli.py` clean. Every `__main__` self-runner exercised individually.
Negative control run on the new selector: an unknown form key raises
`AssertionError` naming the keys that *are* present, rather than returning an
empty selection.

**Key decisions.**
- **D-18** (resolved 2026-08-03): three named functions rather than one
  overloaded helper — the three call-site contracts are genuinely distinct
  (value vs. `LoadValue`, one condition vs. many).
- Fixtures live in a **separate `fixtures.py`**, not in `conftest.py`: they are
  plain builders, not pytest fixtures, and the self-runners import them directly.
- Confirmed by inspection that **all 24 `st.form(...)` calls across 13 views
  already carry unique string keys**, so this step needed no `app/` change —
  correcting the plan's initial assumption that keys would have to be added.

**Follow-on defect found (not fixed here — logged as M4-22).** Clicking the
`select_inputs_form` Apply on the Flight Envelope page also persists the
*un-applied* `flight_geometry_form` edits: the SELECT handler writes the page's
probe copy (which already carries `fl_effective`) back to session state at
`app/views/flight_envelope.py:324`. Positional button selection had been hiding
it — `test_flight_loads_persists_only_on_apply` passed while clicking the wrong
form. It is an `app/` fix, out of M4-12a's tests-only scope.

---

## M4-1 — Fuselage body loads: moment closure (complete 2026-08-03)

**Objective.** Close the 2026-07-23 review finding T5: `body_loads` applied a
single vertical wing reaction at 25 % wing MAC and closed **ΣFz only**, so the
delivered fuselage beam carried a net pitching couple (terminal `Myy` ran to
7.3e4 – 5.5e5 lb-in on the GA6 conditions, signed the wrong way forward of the
wing and the right way aft of it — not uniformly conservative). Reference 1
Ch 15 p103 instead reacts the unbalanced moment **at the wing front and rear
spar attachments**. Shipped since 2026-07-23 as a caveat on every deliverable.

The diagnosis, the A–E options trade, the reaction formula derivation and the
per-step verification figures are the design note
[`04_m4-1_body_moment_closure.md`](04_m4-1_body_moment_closure.md).

**Deliverables.**
- **Spar geometry, schema v35.** `SurfaceInput.front_spar_pct` /
  `.rear_spar_pct` (fraction of root chord, `None` = *not entered*) and
  `derived_geometry.carry_through(project)`, which resolves them against the G1
  planform to a `CarryThrough(x_f, x_r, d, …, assumed)` or `None`. `None` fields
  substitute the `constants.DEFAULT_FRONT_SPAR_PCT` / `DEFAULT_REAR_SPAR_PCT`
  (0.15 / 0.65) defaults and mark the result `assumed`, so an assumed station
  can never be mistaken for an entered one. Both fields round-trip through `io`
  with `None` preserved.
- **The p103 two-pass calc.** `body_loads.body_distribution` now runs the
  manual's two passes explicitly: pass 1 integrates inertia + the tail air load
  alone, and *its* terminal moment **is** the unbalanced moment `M_ub` ("the
  moment at the aft end is the unbalanced moment"); pass 2 reacts `M_ub` and the
  vertical residual `R_total = NZ·W_fus − LT` at the spar attachments and
  re-integrates. The 2×2 solve, written against the integrator's own aft-most
  reference station `x_ref`, is
  `R_r = (M_ub + R_total·(x_ref − x_f))/(x_r − x_f)`, `R_f = R_total − R_r`.
- **Distributed carry-through reaction (a refinement of p103, ours).** The two
  point reactions are applied as the statically equivalent **linear line load
  over `[x_f, x_r]`** — identical resultant and first moment, but without the
  `±M_ub/d` shear spike two point loads put across a short carry-through, and it
  collapses continuously onto the manual's literal two-point solve as `d → 0`.
  Each segment is lumped by its *exact* static equivalent
  (`P_left = h(2w_k + w_{k+1})/6`), so closure is independent of the node count
  (`CARRY_THROUGH_NODES = 5`).
- **Flagged fallback.** With no derivable spar stations the historical single
  wing reaction is kept and the residual moment cancelled by a zero-net-force
  whole-body correction. It closes the beam but has **no physical source** (it
  relieves wing-region bending and loads the tail cone), so the result is
  flagged `closure_artifact`, reports no fitting loads, and carries the renamed
  `CLOSURE_ARTIFACT_CAVEAT` onto every deliverable.
- **Fitting loads reported, never re-applied.** `BodyLoadResult` gained
  `m_unbalanced`, `r_front`/`r_rear`, `x_front`/`x_rear`, `spars_assumed` and
  `closure_artifact`; `body_loads.fitting_load_rows` (LIMIT) and
  `sbeam_bridge.body_fitting_load_csv` (ULTIMATE) emit the wing-attach fitting
  loads. They are deliberately **outside** the `FORCE` set — the exported
  distribution already carries them as the carry-through line load, and adding
  the point reactions on top would double them. Every renderer says so.
- **Provenance-keyed sbeam GIDs (breaking).** `BodyStationLoad.source`
  (`mass`/`tail`/`carry`/`correction`) drives `sbeam_bridge.body_station_gids`:
  mass + tail stations keep the historical `1001 +` nose→tail numbering, and the
  reaction nodes take a disjoint `1501 +` block. Index-based GIDs would have
  silently renumbered every mass station aft of the wing whenever a spar
  fraction moved, because the carry-through inserts nodes into the *middle* of
  the beam. Body decks issued before this step must be re-exported.
- **Caveat removed from the three stamp sites** it was placed on 2026-07-23, and
  replaced by the closure evidence: `fuselage_loads.bdf` blocks state both
  residuals (ΣFz and terminal `Myy`) and the spar provenance, stamping
  `$ CAVEAT:` only on the artifact path; the **Net Fuselage Loads** page dropped
  its warning for a terminal-`Myy` closure metric and a *Wing-attach reactions
  (LIMIT)* panel; the **Export** page's Fuselage row branches artifact/closed.
  The **Configuration & Layout** page gained the optional spar-fraction inputs
  (blank = not entered) that make the entered-vs-assumed provenance reachable at
  all — before this every project necessarily resolved as `assumed`.

**Test / Acceptance (met).** `tests/test_body_loads.py` carries the closure
suite: both residuals on every critical fuselage condition, relative to the
loads that produced them (terminal `Myy` at 2e-16 … 1.4e-15 of peak bending,
versus 7.3e4 – 5.5e5 lb-in before); `R_f + R_r = R_total` and the pair's moment
about `x_ref` recovering `−M_ub`; node-count independence at 2/3/5/9/33 nodes;
`d → 0` collapse onto the two-point solve (closure held while the reactions grow
as `±M_ub/d` — the spike the distributed form avoids); the fallback closing,
flagging, emitting no fitting loads and carrying the caveat; GID stability
across a spar move and the disjointness of the two blocks; the ULTIMATE fitting
CSV's schema and scaling; and the io round-trip of the new fields.
`tests/test_derived_geometry.py` covers the resolver (entered, assumed,
underivable, GA6, round-trip). The FAR 23 flight oracles are untouched — no
flight-loads or envelope calc changed. Gate: 536 passed, `ruff` clean.

**Key decisions.**
1. **React over the carry-through, not the whole body** (option C over B): the
   couple physically lives at the wing box; smearing it over the whole fuselage
   closes the beam while making a known unknown invisible.
2. **Default spar fractions are used but always flagged.** 0.15 / 0.65 of root
   chord; `None` means not entered, and every deliverable states which it got.
3. **Fitting loads are reported, not applied** (own CSV, not the FORCE set).
4. **GIDs key off provenance, not index** — accepting a breaking change to body
   deck numbering in exchange for numbering that survives a geometry edit.
5. **Split, not folded:** the pitching load factor (**M4-21**) and the
   distributed body aero moment (**M4-19**) stay separate items. Neither
   substitutes for this closure — for the balanced trim cases `θ̈ = 0`, so M4-21
   contributes nothing there, and M4-19 changes `M_ub` without reacting it.

---

## M4-18 — Loads reference axis (LRA) + two-sided load envelopes (complete 2026-08-03)

**Objective.** Close the two findings of the 2026-08-03 loads-plots review:
(1) the Loads-Plots "envelope" was a single max-|value| trace, which hides the
opposite-sign extreme (the negative-side load can govern a different part of the
structure) and jumps discontinuously where the governing sign flips; (2) the wing
torsion `Myy` was computed and delivered about the 25 % chord with the axis
stated nowhere in the GUI or the exports — and the beam model the loads apply to
uses an **elastic axis** (typically 40–50 % chord), not the quarter chord. Both
per the user's direction: every torsion must name its reference axis (mixed axes
allowed but always labelled), and the axis should be visible on the three-view.

**Deliverables.**
- **Loads reference axis (LRA), schema v34.** `SurfaceInput.ref_axis_pct`
  (fraction of chord, lenient default 0.25) defines each surface's LRA — the
  beam-model elastic axis the delivered torsion is stated about.
  `WingLoadResult.torsion_axis` stamps the axis label (`"25% chord"` /
  `"LRA 40% chord"`) on every result; both fields round-trip through `io`.
- **Boundary transfer, calc untouched.** `net_loads.to_loads_ref_axis`
  (+ `loads_ref_axis_results`, `wing_lra`, `torsion_axis_label`) applies
  `Myy_lra(y) = Myy_25(y) + Sz(y)·(x_lra(y) − x_25(y))` — the statics of moving
  the moment reference of the outboard load set, WINGINER sign convention —
  at the render/export boundary only, the same pattern as the limit→ultimate
  factor. Shears/bending unchanged; `ref_axis_pct = 0.25` is a **bitwise no-op**,
  so the Appendix A oracles and twin closure are unaffected.
- **Axis labelled everywhere.** Loads-Plots and the sbeam bridge deliver LRA
  torsion (the `Project` export path transfers automatically; in-band span-CSV
  `MyyAxis` column, BDF `$` axis comments, stick-model beam-axis note — the
  stick-model GRID line follows the LRA). The Wing Loads analysis page and
  `wing_load_rows` stay at the **labelled** 25 % chord (the oracle-traceable
  numbers an engineer checks against the manual, with a pointer to the LRA
  deliverables); `net_loads.run` reports root torsion at both axes (labelled)
  when the LRA differs. The Geometry page gets a per-surface LRA input
  (definition help text; re-seeding the wing carries a user-set LRA over) and
  the three-view top view draws each surface's LRA dash-dot with a legend entry.
- **Two-sided envelopes.** `report.envelope_extremes` (pure, tested) replaces
  the view-local max-|value| helper; the Loads-Plots overlay draws
  "envelope (max)" and "envelope (min)" traces and writes both into the CSV
  download (`ENVELOPE (max)` / `ENVELOPE (min)` rows).

**Test / Acceptance.** `test_net_loads.py::test_loads_ref_axis_transfer`
(25 %-no-op identity + per-station formula/invariance checks at 40 %),
`::test_run_labels_torsion_axis`, `::test_wing_load_rows_shape` (`MyyAxis`
in-band); `test_sbeam_bridge.py::test_project_export_transfers_to_loads_ref_axis`
(CSV value = 25 %-chord root + SF·Sz·Δx, axis label in CSV/BDF/stick),
`::test_span_load_csv_shape` (header + untransferred axis label);
`test_report.py::test_envelope_extremes_is_two_sided`;
`test_io.py::test_surface_ref_axis_pct_round_trips`,
`::test_wing_load_result_torsion_axis_round_trips`. Full suite 523 passed,
`ruff` clean; `DATA_DICTIONARY.md` regenerated (v34), GUI_design schema line
bumped.

**Key decisions.** The LRA is *input geometry on the surface* (not a wing-mass
analysis field) with default 0.25 so every existing project reproduces the
original quarter-chord reporting bit-for-bit — the reduces-to-FAR23 principle;
the transfer lives at the render/export boundary (never in the calc) exactly
like the ULTIMATE factor; mixed axes are permitted but every torsion output must
carry its axis label in-band (`MyyAxis` column / `$` comments / plot+metric
labels), following the M4-15 Basis-column pattern; the envelope is two-sided
max/min rather than max-|value| (a signed extreme pair, not a magnitude).

---

## M4-17 — Landing loads ↔ mass model disconnection + CG-seed hazards (complete 2026-08-03)

**Objective.** Close all five sub-items of the 2026-08-03 landing-loads review.
Its root finding: `weight_onecg.build_mass` had **zero production callers**, so
`Project.mass` was never produced anywhere — no page, no CLI path, no example.
Everything downstream of the slice was broken or stale in code shipped with
**0.3.0**, while the LANDLOAD calc core itself was sound (the oracles pass). Every
defect sat at the seam between the weight model and the landing inputs.

**Deliverables.**
- **(a) Mass-slice wiring.** `app/views/weight_mass.py`'s **Apply weight items**
  handler now persists `project.mass = build_mass(project)` (guarded — a
  degenerate item list warns and leaves any prior slice), so the `weight_mass`
  step's `produces="mass"` finally turns ✅ and the One Engine Out gate becomes
  satisfiable. Separately, `workflow.py`'s landing step drops `"mass"` from
  `requires` (now `requires=()`): the calc has read no mass slice since M2-8, so
  the requirement blocked the step on every shipped example for a dependency that
  does not exist. `one_engine_out` keeps it — it genuinely dereferences IZZ. The
  OEO gate text now names the button that satisfies it. This also unblocks
  **M4-4** (per-CG precise inertia into SELECT).
- **(b) Doc/help sync.** Seven stale `Project.mass` references corrected —
  `modules/landing.py` (module + `_cg_cases` docstrings), `models/inputs.py`
  (four: the `LandingInput` docstring, the `gross_weight_lb` comment and the
  `cg_cases` comment), and `app/views/landing_loads.py` (page docstring + the
  gross-weight-override help, which cited `(Project.mass)` for a default actually
  taken from `landing.cg_cases`).
- **(c) Seed hardening + a weight-interpolated forward limit.** `_seed_cg_rows`
  rewritten so **every cell without a real source is blank, never `0.0`**: the
  waterline from `project.mass.cases[0].cg_z` or blank; the max-landing rows blank
  rather than seeded at full MTOW when the max landing weight is unset; and the
  forward stations from the new public
  `validation.wtenv_fwd_cg_limit_at_weight(project, weight_lb)`, which lerps the
  WTENV forward limit between its forward-regardless and forward-gross anchors
  (**clamped, never extrapolated** — `wing_geometry._interp_x` extrapolates and is
  private, so it was not reused). `validation.wtenv_cg_limits` keeps its
  weight-agnostic outer-hull semantics unchanged; both now share a
  `_wtenv_stations` helper. The page names each missing source with its
  consequence, refuses to save an incomplete row, and **blocks the reaction
  compute** until every row has a positive weight, station and waterline.
- **(d) Hierarchy & sanity validation.** `validation._check_landing_hierarchy`
  (input-side: `gross_ge_max_landing`, `landing_light_le_max`,
  `landing_cg_ordering`, `landing_cg_below_axle`, `landing_cg_names`) and
  `validation.landing_reaction_warnings` (post-compute:
  `landing_negative_vertical`, `landing_zero_nose`), the latter deliberately
  outside `consistency_warnings` so that aggregate stays input-only and no
  definition page pays for a gear solve. Warn-only; silent on the GA fixture. The
  positional-ordering hazard is closed at both ends: the editor's `Loading` column
  is read-only and Apply writes the canonical names, and `landing._cg_cases`
  reorders by canonical name when all three are present (a verified no-op on every
  bundled example and the test fixture).
- **(e) The undelivered LANDLOAD output.** `landing.run()` emits **40**
  `ConditionResult`s — LGFACTOR + 6 family summaries + the **full 33-case
  matrix** — carrying the reactions (`lbs-ULT`, SF 1.5), the unbalanced
  pitch/roll/yaw moments (`lb-in-ULT`, SF 1.5) and the dimensionless ground-line
  inertia factors NVP/NDP/NS (unscaled, no `-ULT`, blank SF). Cases 25–33 are
  nose-only. The moments and factors are also shown on the page (LIMIT-marked).
  `_critical` now ranks on the full √(V²+D²+S²) rather than the printed
  two-component `RMP`/`RESULT`, which excluded the side load. The never-assigned
  `nv`/`nd`/`nns` fields were deleted from `GearReactionCase`.
- **Examples.** All six `examples/*.project.json` regenerated with a `mass` block.
- **Docs.** `PROGRAM_SPEC.md` (LANDLOAD Reads/Writes/Notes, WTONECG Notes, both
  slice-table rows), `20_theory/00_theory_sources.md` (the moment and
  inertia-factor equations, the ranking basis, the forward-limit interpolation
  with its p230 citation; WTONECG production note), this history entry, the
  backlog removal (item + Known-defects bullet) and the `CHANGELOG.md`
  `[Unreleased]` entry.

**Test / Acceptance.**
- `tests/test_landing.py` +7: the p230/p236 oracles re-asserted **through**
  `build_landing(load_project(...))` as a regression guard; closure on
  PITCHP/ROLLP/YAWP and on NVP/NDP/NS across all three regimes; the 40-condition
  emission with shared case ids and a uniform SF 1.5; the ULTIMATE CSV
  (`lbs-ULT`/`lb-in-ULT` at ×1.5, NVP blank-units/blank-SF **unscaled**, and
  `has_load_case_data is False` locking the `results_to_rows` routing);
  the side-load ranking; the canonical-name reorder; and an `AppTest` proof that
  with no waterline source the seed blanks the cell, Apply refuses to save and the
  reactions never compute.
- `tests/test_validation.py` +8: the interpolation (**76.117 in @ 3230 lb vs the
  manual's 76.12**, anchors 72.6431 / 77.4903, clamped outside, `None` with no
  source), each of the five hierarchy codes on its own perturbed fixture, and the
  zero-waterline reproduction yielding `landing_negative_vertical`.
- `tests/test_dirty_flag.py` — the landing seed expectation updated from
  `[72.6, 72.6, 85.1]` to **`[72.6, 76.1, 85.1]`** (the intended M4-17c change,
  cited to p230) plus a non-zero-waterline assertion.
- **Gates:** `pytest` **517 passed** (was 501), `ruff check sloads/ cli.py` clean,
  `scripts/smoke_test.sh` **PASS**, both `__main__` self-runners green.
- **Acceptance met:** on the shipped GA-6 example `missing_requirements` is now
  `[]` for Landing Loads (was `['mass']`) and `is_produced` is `True` for
  `weight_mass`; the seed cannot emit a zero waterline; the fwd max-landing
  station comes from the interpolated WTENV limit; the moments and factors are
  asserted, shown and exported alongside the full 33-case matrix.

**Key decisions.**
- **Both halves of (a), not either/or** — wire `build_mass` *and* drop landing's
  `requires`. They are independent facts: the slice genuinely had no producer, and
  landing genuinely has no such dependency.
- **Blank-and-block over a geometry fallback** for a missing waterline. A derived
  CG can still be wrong quietly; the failure mode being fixed is precisely
  "computes plausibly with no warning".
- **`SCHEMA_VERSION` not bumped (stays 33).** The JSON *shape* is unchanged —
  `mass` already round-tripped and is optional on read; only its presence changes.
- **`report._LOAD_CASE_LABELS` not extended.** A LANDLOAD case is a *pair* of
  reactions at two stations plus three unbalanced moments;
  `load_cases_to_rows`' single-point-load schema would lose the nose reaction or
  fabricate locations. Landing stays on `results_to_rows`, locked by a test.
- **Moments emitted in `lb-in`, not ft-lb** — `bp`/`cp`/`tread_in` are inches and
  `report.py` already maps `lb-in → lb-in-ULT`; converting inside the calc would
  be a presentation change in a pure module.
- **Examples regenerated (user decision).** Accepted deltas, verified by
  before/after CLI diffs: `configuration` tip-back/overturn/CG-station move on
  five examples as `cg_estimate` flips to its "Weight DB" branch (GA-6: CG
  74.07 → 85.0 in, tip-back 33.11 → 13.49°, overturn 43.01 → 48.69°); the twin
  turboprops' `one_engine_out` passes the mass gate and stops at the next missing
  input (engine horsepower). No test expectations moved.
- **No calc-math change**, so the oracle status is untouched; every value M4-17
  delivers was already computed by the port.

---

## M3-2 — Release cut: **sloads 0.3.0** (concept-loads v1), tag `v0.3.0`, 2026-07-23

**Objective.** Cut the first concept-loads release per `RELEASE_PROCESS.md`,
gated on the four 2026-07-23 review items (M4-13 … M4-16, all shipped the same
day) plus M2R and M3-1.

**Deliverables.**
- **Version** `0.2.0` → **`0.3.0`** in `pyproject.toml` (MINOR: new modules +
  new GUI/CLI capability since 0.2.0; no breaking schema/CSV change —
  `SCHEMA_VERSION` 33 loads all older saves through the lenient readers).
- **Changelog cut** — the ~1,350-line `[Unreleased]` dated to
  `## [0.3.0] — 2026-07-23` with its twenty duplicate headings merged to four
  (Added 440 / Changed 344 / Fixed 454 / Documentation 75 lines), a release
  intro paragraph added, and a fresh empty `[Unreleased]` opened. Changelog
  title updated to the `sloads` name.
- **Verification baseline** —
  [`02_verification_baseline_0.3.0.md`](02_verification_baseline_0.3.0.md)
  supersedes the 0.2.0 baseline: header re-verified against the 0.3.0 run
  (**501 passed, ~93% coverage, ruff clean, smoke PASS**); the **new M1 oracle
  rows** added — STRSPEED p155 VD floor (M1-1, 198.53 kt), FLTLOADS
  landing-config set (M1-2, p179 polynomials → p181 case 89: 83.6 kt /
  −430 lb / −2.54°), AIRLOAD4 swept renormalization closure (M1-3), and the
  SELECT 23.427 approved-deviation figures (M1-4, −1204.7 / −700.4 / −504.3
  replacing the superseded sample-output prints); a **one-page
  oracle-vs-closure status table** covering all 24 modules/areas; a LIMIT-basis
  note tying the oracle figures to the M4-7…M4-16 ultimate-output chain; two
  stale 0.2.0 claims corrected in place. `00_INDEX.md` updated (0.3.0 baseline
  current, 0.2.0 marked superseded).
- **Gates at cut:** `pytest` 501 passed / 0 failed, `ruff check sloads/ cli.py`
  clean, `scripts/smoke_test.sh` PASS (headless GUI render + CLI export), no
  open CRITICAL/MAJOR review findings, backlog/history/CHANGELOG lifecycle
  current.
- **Tag:** `v0.3.0` (annotated), per `RELEASE_PROCESS.md` §4.3.

**Post-release.** M3-3 (Step G8 summary report), the un-shipped stretch, opens
M4; the backlog is restructured to post-release form.

---

## M4-16 — 2026-07-23 review nits batch (doc-currency CRITICAL + maintainability, complete 2026-07-23)

**Objective.** Close the four MINOR/NIT findings of the 2026-07-23 M4-7 review,
led by its CRITICAL: `GUI_design.md`'s hand-written "currently
`SCHEMA_VERSION = …`" paragraph stale for the **third** time (still 32 after the
M4-7 bump to 33; the 2026-07-21 review's single CRITICAL was the same line at
v31→v32). Fourth item of the M3 release gate.

**Deliverables.**
- **`GUI_design.md` schema paragraph** fixed to 33; the recent-steps migration
  list gains `v33 M4-7 per-case safety_factor`; the paragraph now names its own
  guard test. **New guard:**
  `tests/test_data_dictionary.py::test_gui_design_schema_line_current` asserts
  the doc contains `` `SCHEMA_VERSION = {models.SCHEMA_VERSION}` `` with a
  pointer failure message — verified to bite by perturbing the line locally
  (fails with the message) and restoring. A fourth regression is unmergeable
  (CI runs pytest). Sited in `test_data_dictionary.py` beside the generated-doc
  drift guards; the deeper fields-hash enforcement remains M4-10.
- **`sbeam_bridge._sf()`** typed (`Union[WingLoadResult, BodyLoadResult,
  TailChordResult, ControlSurfaceLoadResult]`) and reads `result.safety_factor`
  directly — the `getattr` fallback is gone (every producer mints the field
  since M4-13; the fallback only served hand-built doubles while masking a
  future attribute rename). `_SF` survives as the default constant the closure
  tests read; module docstring/comments updated to match.
- **`_sf_str()` helper** — deliverable SF formatting: always a decimal point
  (`SF=1.0`, `SF=1.5`, `SF=1.25`), replacing all eleven `f"{sf:g}"` sites
  (card `$` headers, closure comments, the four CSV `SF` columns). The six test
  assertions pinning `SF=1` / `{"1"}` moved with it.
- **`io.py`** intra-package imports ordered alphabetically
  (`.constants` → `.models` → `.report` → `.validation`).

**Test / Acceptance.** Suite green (**501** passed, +1), `ruff` clean (incl.
`app/`), self-runners pass (`test_data_dictionary.py`, `test_sbeam_bridge.py`
24/24). No calc, schema or persisted-format change; the only output change is
the cosmetic `SF=1` → `SF=1.0` rendering.

**Key decisions.**
- *Guard test lives with the existing doc-drift tests* — not a new file; the
  natural companion to `test_schema_version_recorded`.
- *`Union` over a `Protocol`* for `_sf` — the four concrete types are already
  imported in the module and the closed set is the point.
- *`_sf_str` helper over a format-spec* — no single format spec renders 1.0 as
  `1.0` and 1.25 as `1.25` without trailing-zero noise elsewhere.

---

## M4-15 — LIMIT-marked deliverables: analysis-page CSV downloads (defect, contract, complete 2026-07-23)

**Objective.** The CLAUDE.md analysis-page exception lets a per-module page show
LIMIT values only when explicitly marked and pointing at the ultimate
deliverables — but the marking must travel with a *download*. The 2026-07-23
review found `app/views/wing_loads.py`'s "Download net wing loads (CSV)"
(`net_loads.wing_load_rows`) shipped LIMIT station loads with no marker, no `SF`
column and a neutral filename; the mandated sweep found the same pattern on the
Fuselage Loads CSV and (partially) the Loads Plots comparison CSV, whose plot
axes said `(unit, LIMIT)` while its CSV `Field` column dropped the marker.
Tail-chordwise and one-engine-out downloads were already column-marked in-band;
everything else (aileron/flap/tab, engine mount, landing loads, airloads,
Export page) already routes through the ULTIMATE channels. Third item of the M3
release gate.

**Deliverables.**
- **`Basis = LIMIT` column** appended to the two canonical station-row shapes,
  `net_loads.wing_load_rows` and `body_loads.body_load_rows` — single source, so
  the on-page tables and every CSV built from the rows state the basis in-band.
- **Filename convention `*_LIMIT.csv`** applied to every LIMIT download: wing
  (`net_wing_loads_LIMIT.csv`), fuselage (`net_fuselage_loads_LIMIT.csv`),
  loads-plots comparison (`loads_plots_<comp>_LIMIT.csv`), tail chordwise and
  one-engine-out time history (already column-marked; renamed for uniformity).
  The Loads Plots CSV `Field` strings gain `, LIMIT`, matching the plot axes.
- **ULTIMATE twins (user decision 2026-07-23: offer both buttons).** Wing and
  Fuselage Loads pages add a side-by-side ULTIMATE download —
  `net_wing_loads_ULT.csv` via `sbeam_bridge.span_load_csv` and
  `net_fuselage_loads_ULT.csv` via `sbeam_bridge.body_span_load_csv` (renderers
  reused as-is; per-case `SF` column) — with a caption tying the LIMIT file to
  the on-page oracle-traceable table and the ULT file to the Export page.
- **`tests/test_ultimate_contract.py`** — source-scan guard: every view CSV
  `download_button` must be `*_LIMIT.csv`/`*_ULT.csv`, route through an ULTIMATE
  channel (`sbeam_bridge`/`load_cases_csv`/`load_cases_to_rows`/
  `case_index_csv`), or sit on the explicit non-load allowlist (geometry,
  speeds, mass-properties tables). A new page adding an unmarked load CSV fails
  the suite.
- Docs: `PROGRAM_SPEC.md` limit-vs-ultimate scope statement and
  `GUI_design.md` LIMIT-marking convention both extended with the in-band
  download rule and the guard test.

**Test / Acceptance.** Suite green (**500** passed, +1), `ruff` clean (incl.
`app/`), self-runners pass. Shape tests extended (`Basis` key + all-rows-LIMIT
assert); both edited pages render clean under headless `AppTest` on the GA
fixture. No calc/schema change (`SCHEMA_VERSION` stays 33); the SI display
converters spread `**r`, so the new string column passes through untouched.

**Key decisions.**
- *Both buttons* (user decision): keep the LIMIT download (the oracle
  cross-check artifact matching the on-page table) **and** add the ULTIMATE twin
  from the bridge, rather than replacing one with the other.
- *Basis column lives in the canonical row helpers*, not the views — the basis
  travels with the rows wherever they are rendered next.
- *Source-scan guard over a runtime test* — cheap, page-agnostic, and fails at
  the moment a new unmarked load CSV is added, which is when the author has the
  context to fix it.

---

## M4-14 — Validate `safety_factor` on load (defect, correctness, complete 2026-07-23)

**Objective.** The five `io.py` readers added by M4-7 took
`d.get("safety_factor", ULTIMATE_FACTOR)` with no type or range check, and the
field is persisted in `project.json` and hand-editable (Project JSON Editor page
or the file directly). Verified failure modes: `"safety_factor": null` →
`TypeError` out of `body_span_load_csv` (breaking the lenient-reader contract);
`"safety_factor": 0.5` → every exported card silently **under-scaled while still
labelled ULTIMATE** — the worst failure mode in the suite, and reachable on the
headless `cli.py --export-sbeam` path where no GUI warning can surface. From the
2026-07-23 M4-7 review (MAJOR); second item of the M3 release gate. **Policy
locked with the user 2026-07-23:** the legal band is **[1.0, 1.5] inclusive**,
per case, owned by the load-case definition (14 CFR 23.303; a case already at
ultimate is 1.0, an agreed 23.302/25.302 failure-case factor lies between) —
anything else is corrupt.

**Deliverables.**
- **`io._safety_factor(d)`** — one shared coercion helper replacing all five
  `d.get(...)` sites: anything non-numeric (null, string, bool, NaN/inf) **or
  outside [1.0, `ULTIMATE_FACTOR`]** falls back to the conservative
  `ULTIMATE_FACTOR` default (not clamped to the nearest bound — an out-of-band
  value is treated as corrupt, and coercing a high value *down* or a low value
  *up to 1.0* would silently trust corrupt data). Read-time coercion is what
  makes the headless CLI path safe, not just the GUI.
- **`validation.safety_factor_valid(value)`** — the public shared predicate
  (public because `app/` must not import underscore names, M4-12), used by the
  reader, the new check and the JSON editor.
- **`validation._check_safety_factors`** — advisory `safety_factor_out_of_range`
  `ConsistencyWarning` (one per offending case, case named in the message)
  scanning `envelope.critical.conditions` plus all six `Project.loads` families;
  new `PAGE_EXPORT = "export_report"` tag, rendered by the Export page (which
  previously rendered no consistency warnings). Catches in-session/programmatic
  values — a corrupt *persisted* value is coerced before validation ever sees it.
- **Project JSON Editor** — Apply now scans the **raw** edited dict (recursive
  `_bad_safety_factors` walk) and warns, per field path, that an invalid value
  was reset to 1.5: `project_from_dict` has already coerced by the time the
  project is built, so only the raw dict can show what the user typed.
- No schema change (`SCHEMA_VERSION` stays 33 — readers got *more* lenient).
  Docs: `PROGRAM_SPEC.md` "Read-side validation (defect M4-14)" bullet,
  `GUI_design.md` §8.3, `validation.py` docstring check list.

**Test / Acceptance.** Suite green (**499** passed, +6), `ruff` clean (incl.
`app/`), both no-pytest self-runners pass. `tests/test_io.py`: corrupt fixtures
(null / `"1.25"` string / `True` / NaN / inf / 0.5 / −1.5 / 0 / 0.999 / 1.6)
each coerce to 1.5 across all five readers; the legal band (1.0/1.25/1.5) loads
verbatim; the exact null-then-`body_span_load_csv` repro no longer raises.
`tests/test_validation.py`: `safety_factor_out_of_range` fires per case with the
right page tag for 0.9 and 2.0, is silent across [1.0, 1.5], plus direct
predicate coverage; the GA fixture stays warning-free (the module's documented
invariant). GA path unchanged.

**Key decisions.**
- *Coerce-to-safe-default over warn-only or hard-reject* (user-ratified D1):
  warn-only leaves the CLI export emitting under-scaled ULTIMATE cards with no
  human in the loop; hard-reject bricks a saved project over one field. Coercion
  keeps every deliverable conservative and the file loadable; the warnings
  explain what happened.
- *Band is [1.0, 1.5] inclusive, both sides enforced* (user decision 2026-07-23:
  "the safety factor can be any number between 1.0 and 1.5", set by the case
  definition). This supersedes the plan's earlier keep-with-warning treatment of
  values above 1.5 and the backlog's literal `(1.0 …` exclusive lower bound
  (SF = 1.0 is legal — `one_engine_out` ships such cases).
- *Warnings surface at the consequence (Export page) and the cause (JSON editor
  Apply)* — not on Results Review or the Dashboard, kept small (D2).

---

## M4-13 — Wing + control-surface producers mint the per-case safety factor once (defect, correctness/latent, complete 2026-07-23)

**Objective.** Finish what M4-7 started. M4-7 threaded the factor for the tail
and fuselage families only; `net_loads` (`WingLoadResult`) and
`aileron`/`flap`/`tab` (`ControlSurfaceLoadResult`) left their result slice
**and** their rendered `ConditionResult` to default `safety_factor`
*independently* — two sources of truth for the same case. Harmless while every
factor is 1.5, but the first non-default case (M4-8 Layer 1, or a 25.302 named
case) would make the rendered report and the exported FORCE/MOMENT cards
disagree — the exact failure M4-7 closed for tail/body. `PROJECT_GUIDE.md` §5
already asserted the stronger invariant ("minted by the module that owns the
condition and copied unchanged by everything derived from it"); this brings the
code up to the doc. Promoted from M4 to the M3 release gate (first item),
2026-07-23 consolidation; from the 2026-07-23 M4-7 review (MAJOR).

**Deliverables.**
- **`net_loads.build_net_loads`** mints the wing case's factor once per case
  (`sf = ULTIMATE_FACTOR`, the line M4-8's Layer-1 resolver will replace) and
  sets it on the **air, inertia and net** `WingLoadResult`s of that case — the
  three families describe the same case and are all accepted by the export's
  `ResultsArg` API. `run()` copies `r.safety_factor` onto each `ConditionResult`
  (the taildist pattern).
- **`aileron.build_aileron`** mints one shared factor for both throws (up/down
  can never diverge); **`run()` now consumes `build_aileron()`** instead of
  recomputing `aileron_loads` a second time — the rendered loads/speeds/pressures
  and the exported records now have a single source — and its `ConditionResult`
  gains the previously missing `case_ref` (the down-throw's) plus the copied
  factor.
- **`flap.build_flap` / `tab.build_tabs`** pass `safety_factor=ULTIMATE_FACTOR`
  explicitly at the mint site; each `run()` copies `case_ref` **and**
  `safety_factor` from the built result.
- No model/io/schema change: the fields shipped with M4-7 (`SCHEMA_VERSION`
  stays 33); `sbeam_bridge._sf()`'s `getattr` fallback now never fires for a
  project-produced result (its annotation cleanup is M4-16).
- Docs: `PROGRAM_SPEC.md` sbeam-bridge section gains a "Factor mint sites
  (defect M4-13)" bullet naming the mint per producer.

**Test / Acceptance.** Suite green (**493** passed, +2), `ruff` clean, the
no-pytest self-runner passes. Two new tests in `tests/test_sbeam_bridge.py`
(the acceptance shape of `test_taildist_and_body_copy_the_condition_factor`,
adapted because these four modules own their conditions and have no persisted
upstream to mutate): an **agreement test** asserting per-case equality between
every result slice (incl. `wing_air`/`wing_inertia`) and its rendered
`ConditionResult` on the GA fixture, and a **mutation test** that wraps each
module's `build_*` to force a 1.25 mint and asserts `run()`'s conditions carry
it — failing against the old independent-default code. **Numbers unchanged**
at SF 1.5 (full suite incl. the Appendix-A oracles p222/p200/p201/p202).

**Key decisions.**
- *Mint locally in `net_loads`* (option (a)): wing cases have no upstream
  `CriticalCondition` (their W- case-id band is disjoint from
  `envelope.critical`), and linking them upstream is M4-2's case-identity
  unification, kept out of scope. When M4-2 lands, the wing mint moves upstream.
- *Aileron keeps one `ConditionResult`* covering both exported throws (report
  shape unchanged); splitting it 1:1 with the export was deferred until after
  M4-9 de-strings the label lookups.
- *`wing_air`/`wing_inertia` carry the factor too*, not just `wing_net` —
  scoping to net only would recreate the two-sources problem for anyone
  exporting those families directly.

---

## M4-7 — sbeam export honours the per-case safety factor (defect, correctness/latent, complete 2026-07-23)

**Objective.** Close the double-factor trap in `export/sbeam_bridge`. The bridge
hardcoded a flat `_SF = ULTIMATE_FACTOR` at every scaling site and ignored
`ConditionResult.safety_factor`. The root cause sat one level deeper: the four
distributed-load result types the bridge consumes (`WingLoadResult`,
`BodyLoadResult`, `TailChordResult`, `ControlSurfaceLoadResult`) — and the
`CriticalCondition` upstream of two of them — carried **no** factor at all, so
there was nothing to read. Latent while every case is 1.5, but (a) a case already
at ultimate (`SF = 1.0`, per the CLAUDE.md ultimate-load contract) would be
multiplied by 1.5 a second time, and (b) a future 14 CFR 23.302 / 25.302 /
Appendix K probability-based factor (1.0–1.5) set on a failure case could reach
`report.py` but never the exported cards — the report and the deliverable would
disagree.

**Deliverables.**
- **`safety_factor: float = ULTIMATE_FACTOR`** added to `CriticalCondition`,
  `WingLoadResult`, `BodyLoadResult`, `TailChordResult` and
  `ControlSurfaceLoadResult` (`sloads/models/results.py`), each docstring stating
  that the stored station values are **LIMIT** and this is the factor the
  render/export boundary applies.
- **Producers propagate it:** `modules/taildist.py` and `modules/body_loads.py`
  copy the governing `CriticalCondition`'s factor into the slice they emit;
  TAILDIST's rendered `ConditionResult` carries the same value, so the report path
  and the export path are structurally incapable of disagreeing. The
  wing/control-surface producers have no upstream factor today and keep the
  default — the field is now the single place a future refinement sets it.
- **Bridge scales per result:** new module-private `_sf(result)` (a defensive
  `getattr` falling back to `_SF`) replaces all nine flat `* _SF` sites across the
  wing, fuselage, tail-chordwise and control-surface families. `_SF` survives only
  as the fallback default (and as the constant `tests/test_sbeam_bridge.py` reads).
- **Cards state the factor they used:** the four hardcoded
  `$ Loads are ULTIMATE (limit x 1.5)` comment lines, plus the two closure comments
  spelling out `1.5 x …`, now interpolate the applied factor (`limit x SF=<sf>`).
- **`SF` column** appended (last, so positional parsers are unaffected) to all four
  span/chordwise CSVs — the "every load case SHALL state its safety factor"
  mandate, mirroring `report.py`'s existing `SF` column.
- **Persistence:** the five `io.py` readers round-trip the field with a lenient
  `d.get(..., ULTIMATE_FACTOR)`. `SCHEMA_VERSION` 32 → **33**; bundled
  `examples/*.project.json` restamped. En route, fixed
  `_critical_condition_from_dict` silently dropping `CriticalCondition.note` on
  reload (it carried approved-correction provenance).

**Test / Acceptance.** Suite green (491 passed), `ruff check sloads/ cli.py` clean.
Six new tests in `tests/test_sbeam_bridge.py`: closure against *that case's* factor
for SF ∈ {1.0, 1.25, 1.5}; two cases with different factors in one export each
scaling by its own; the card header quoting the actual SF (and never `SF=1.5` when
the case is 1.0); the `SF` column present and correct on all four CSVs; and the
taildist/body producers copying a mutated `CriticalCondition.safety_factor`. Plus
`tests/test_io.py::test_safety_factor_round_trips_on_result_slices` (save/load
survival + the missing-key default). **Numbers unchanged:** the GA wing span CSV
load columns and the FORCE/MOMENT cards diff byte-identical against a pre-change
run — only the new `SF` column and the reworded `$` comment differ.

**Key decisions.**
- *Full propagation over a bridge-local patch.* A `getattr` in the bridge alone
  would have been a no-op (no result carried the field); wiring the 23.302 hook
  end-to-end is what actually closes the defect.
- *Factor stays per **case**, not per station.* Uniform within one exported load
  set, which is exactly what the C4 force/moment-closure guarantee requires
  (`sum(dFz) == safety_factor × root`).
- *`SF` appended last* in every CSV, so existing positional consumers
  (`app/views/export_report.py`, `export/workbook.py`, `cli.py`) are unaffected.

---

## M3-1 — Full rename `FAR23LOADS`/`farloads` → **`sloads`** + `models/` package split (decided 2026-07-20, complete 2026-07-23)

**Objective.** Retire the `FAR23LOADS`/`farloads` name — it is the exact mark of a
commercial product marketed by McGettrick Structural Engineering / DARcorporation
(`reference/FAR-23-Loads-Brochure-2023.pdf`), and the tool's identity is now a
concept-development tool extending beyond FAR 23. Adopt `sloads` (joining the
**sbeam** / **smodal** family) across package/import, CLI, GUI/brand, and docs,
**batched** (same churn event, per the 2026-07-21 review) with splitting the
1,862-line `models.py` monolith into a lifecycle-ordered `models/` package. Executed
per the step-by-step runbook
[`06_m3-1_rename_procedure.md`](06_m3-1_rename_procedure.md).

**Key decisions (2026-07-23 consultation).**
- *Display brand:* lowercase **`sloads`** (app `page_title`, dashboard title, README
  H1, package/module docstrings, doc-set H1 titles). The pyproject `description` and
  README/CLAUDE intros keep "*the FAR 23 LOADS suite (McMaster)*" as **attribution**,
  not rebranded.
- *sbeam export headers:* rebranded the `$ FAR23LOADS …` deck comments and `export/`
  axis-convention references to uppercase **`SLOADS`** (machine deck-tag), with
  `tests/test_workbook.py`'s `startswith("$ …")` assertion updated in lockstep.
- *History kept verbatim:* `CHANGELOG.md` and `docs/40_history/*` past entries retain
  their `farloads/…` path references (Keep-a-Changelog convention); the two
  point-in-time review docs (`PROJECT_REVIEW_2026-07-19.md`,
  `CODE_REVIEW_2026-07-21.md`) argue *about* the `farloads` name and are untouched.
- *Repo folder name* (`Loads_Programs/FAR23LOADS`) left as-is — out of scope (renaming
  it would break the local `.venv`/absolute paths); folder name ≠ package name.

**Deliverables (no calc/oracle/schema change — `SCHEMA_VERSION` stays 32).**
- **Package move:** `farloads/` → `sloads/` (history-preserving `git mv`).
- **`models/` package split:** `models.py` → `sloads/models/{enums,inputs,results,project}.py`
  + a re-exporting `__init__.py` (each submodule with an explicit `__all__`; 72 public
  names). Dependency order enums → inputs → results → project; every prior import form
  (`from sloads.models import X`, the `sloads/__init__.py` re-export block) resolves
  unchanged. Split done AST-deterministically and verified byte-identical (68 defs, 0
  missing/extra/different).
- **Import rewrite:** mechanical `farloads` → `sloads` across ~100 `.py` files
  (imports, attribute paths, Sphinx xrefs, the `farloads_io` alias). Registry
  `MODULE_NAME` values, JSON schema keys and session-state keys carry no `farloads`
  token — saved projects load untouched.
- **`pyproject.toml`:** `name`, `[project.scripts]` (`sloads = "cli:main"`),
  `packages.find include`, `--cov=sloads`, `[tool.coverage.run] source`.
- **Brand strings:** `app/Home.py` (docstring + `page_title`), `app/views/dashboard.py`
  title, README H1, `sloads/__init__.py` docstring → `sloads`; seven doc-set H1 titles
  (`00_INDEX`, `PROGRAM_SPEC`, `PROJECT_GUIDE`, `RELEASE_PROCESS`, `GUI_design`,
  `00_program_overview`, `CODE_REVIEW_PROCESS`) → `sloads`.
- **Docs / CI / scripts sweep:** 17 living docs, `.github/workflows/ci.yml`
  (`ruff check sloads/`), `scripts/smoke_test.sh`, `.claude/settings.local.json`,
  `docs/generate_data_dict.py`, and the generated `DATA_DICTIONARY.md` regenerated.
- **Reinstall:** deleted stale `farloads.egg-info`, `pip install -e '.[dev]'` →
  `sloads 0.2.0`; `sloads --list` prints all 21 modules.

**Test / Acceptance.** Full suite green (**483 passed**, ~93% cov); `ruff check
sloads/ cli.py app/` clean; `scripts/smoke_test.sh` exit 0 (headless GUI HTTP 200, no
traceback, under the new name). Acceptance grep proves **zero** `farloads`/`FAR23LOADS`
in any `.py`/`.toml`/`.yml`/`.sh`; every remaining brand token is an intended keep
(the "FAR 23 LOADS suite/manual" attribution family, the DARcorporation disclaimer, the
kept-verbatim history/review docs, and the repo-folder path). Disclaimer present in
README and the GUI About.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M3-1 removed (its D-6
decision-log row and the `01_concept_loads_plan.md §7` naming note reconciled to point
here). Supersedes decision **D-6** (2026-07-16 "keep FAR23LOADS"). Feeds **M3-2** (the
`sloads 0.3.0` release cut).

---

## M2R-8 — MissingInputError in the registry + single SELECT envelope build (2026-07-21 review, MAJOR, complete 2026-07-22)

**Objective.** `registry.run_all_modules` caught *every* `ValueError`, so a genuine
calc defect in a module vanished from run-all/export, indistinguishable from "inputs
not entered". Distinguish the two so defects surface while incomplete-project modules
still skip. The existing error-handling contract
(`docs/10_standard/00_program_overview.md`) already drew the line ("required slice
absent → skip" vs "invalid domain input → surface"); this formalizes it in code.

**Key decisions (2026-07-22 consultation).**
- *Classification (borderline guards):* "present but not yet filled in" — an empty
  required list, or an absent required **upstream** slice/named surface — is treated as
  **not-ready → `MissingInputError` → skip**, preserving run-all's tolerance of
  partially-built projects. Only genuinely malformed/contradictory data (`<2` cylinders,
  non-positive area/weight/MC/MD, `>=2` element/point counts, out-of-range index,
  exactly-3-CG-cases, aero-surface-with-no-matching-geometry, an unknown V-n case
  reference) stays a plain `ValueError` and now surfaces.
- *Scope:* both parts — the `MissingInputError` core **and** the "while in the area"
  SELECT single-envelope-build refactor.

**Deliverables (no calc/oracle change).**
- `farloads/models.py` — `class MissingInputError(ValueError)`; exported from
  `farloads/__init__.py`.
- `farloads/registry.py` — `run_all_modules` catches **only** `MissingInputError`;
  a plain `ValueError` propagates.
- The 21 modules — input-absence guards converted from `raise ValueError` to
  `raise MissingInputError` (slice `None`, absent upstream result/geometry/aero slice,
  empty required list); malformed-data guards left as `ValueError`.
- `farloads/modules/select.py` (Part 2) — `_envelope` is the single fallback site
  (raises `MissingInputError` when no V-n matrix is obtainable); every `select_*`
  helper (`select_wing`/`select_htail{,_balancing,_maneuver,_gust}`/`select_vtail`/
  `select_fuselage`/`_stamp_case_refs`) takes an optional `envelope=` parameter
  resolved by `_resolve_envelope`; `build_critical` builds it **once** and threads it
  in — was up to 7 rebuilds. Backward-compatible: `body_loads.select_fuselage(project)`,
  `balloads._envelope(project)` and the tests keep the `(project)` form.
- `docs/10_standard/00_program_overview.md` — error-handling contract table updated to
  name `MissingInputError` and the surface-vs-skip split.

**Test / Acceptance.** New `tests/test_registry.py`:
`test_missing_input_error_is_value_error`; `test_run_all_skips_missing_input_but_propagates_value_error`
(a `MissingInputError` module skips, a genuine `ValueError` propagates out of run-all);
`test_run_all_skips_all_modules_on_engine_only_project` (the ~21 guards are complete);
`test_build_critical_builds_envelope_once` (spies `build_envelope`, asserts exactly 1
call). Full suite green (483 passed); ruff clean; suite runtime dropped (~44s → ~27s)
from the removed rebuilds. SELECT oracles unchanged.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M2R-8 removed (M2R section
now complete — all eight items in history).

---

## M2R-7 — io.py tolerant readers: unknown fields no longer crash load (2026-07-21 review, MAJOR, complete 2026-07-22)

**Objective.** Make good on `schema_status()`'s forward-compat promise ("unrecognized
fields are ignored"). A project file carrying one field this app version doesn't know
(saved by a newer/older build, or hand-edited) crashed load with e.g.
`MassItem.__init__() got an unexpected keyword argument …` because ~21 `*_from_dict`
readers splatted the raw dict (`cls(**d)`) straight into the dataclass constructor.
Matters for release users sharing files across app versions.

**Deliverables (no schema or calc change).**
- `farloads/io.py` — one shared `_filtered(cls, d)` helper (keep only keys that are
  fields of dataclass `cls`) routed through **every** `*_from_dict` splat: the raw
  splats (`_case_ref`, `engine`, `_mass_item`, weight `estimation`/`envelope`/
  `cg_cases`, `_legacy_cg_cases_from_flight_loads`, `speeds`+`mach_limit`,
  `flight_loads` cg_cases, `_critical_condition` loads, `_vn_point`, `envelope`
  tail_balance, `mass`, `fuselage_mass`, `wing_mass` concentrated/cases, and the
  wing/body/tail/control station-load result readers) **and** the pre-existing ad-hoc
  `{k: v … if k in fields}` comprehensions (select/tail/vtail/oeo/gear/landing/
  aileron/flap/tab/configuration), which now call the shared helper. Explicit-key
  readers (`.get(...)`) were already tolerant and unchanged.

**Test / Acceptance.** `tests/test_io.py`: `test_unknown_field_in_every_ga6_slice_is_ignored`
recursively injects an unknown key into every dict (all depths, incl. list items) of
the serialized `ga6_normal` and asserts it loads and re-serializes identically (garbage
dropped); `test_unknown_field_in_every_result_slice_is_ignored` does the same for a
project augmented with the result slices ga6 lacks (envelope/mass/loads/one_engine_out
with nested VnPoint+CaseRef, CriticalCondition+LoadValue, the four station-load
families). Full suite green (479 passed); ruff clean.

**Key decision.** Minimal tolerant-read guard now (unblocks cross-version file sharing
for the release); the full migration-chain overhaul — per-version `MIGRATIONS` hops +
one frozen fixture per historical schema + a fields-hash version-bump gate — stays
**M4-10** (pre-F25), which now builds on this helper.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M2R-7 item and its
Known-defects bullet removed; M4-10 note updated to reference the shared readers.

---

## M2R-6 — Geometry Apply: validate before persisting (2026-07-21 review, MAJOR, complete 2026-07-21)

**Objective.** The **Geometry** page's sidebar *Apply geometry* button did a
wholesale replace of `Project.geometry.parametric` with no validation. Applying an
invalid wing (e.g. Area S = 0) stored it, then `configuration_properties` in the
page body raised (`wing_planform` requires positive area/AR) and the
`try/except → st.error + st.stop()` blanked everything below — including the
*unrelated* empennage / landing-gear / fuselage-outline / surfaces forms, which live
past that `st.stop()`.

**Deliverables (GUI-only; no calc or schema change).**
- `app/views/configuration_layout.py` — new `_layout_errors(layout)` helper (positive
  wing area, aspect ratio, taper λ) run on the candidate `LayoutInput` **before**
  `_set_geometry`. An invalid Apply is rejected with a targeted `st.error` listing the
  offending field(s) and is **not** persisted; the last valid layout survives, so the
  page body and the downstream forms keep rendering. A valid Apply is unchanged.

**Key decision.** Chose *reject-before-persist* over *persist + warn*: never store a
layout that would crash the geometry-derived consumers (three-view, assessment,
downstream seeds, exports), so the invalid value cannot propagate to other pages or a
saved file.

**Test / Acceptance.** New `tests/test_configuration_layout_view.py` drives the page
via `AppTest`: setting Area S = 0 and pressing Apply leaves
`geometry.parametric.wing_area_sqft` unchanged, shows a "not applied" error, and the
`Apply empennage` / `Apply landing gear` buttons still render (page not blanked); a
valid edit (S = 200) still persists. Full suite green (477 passed); ruff clean.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M2R-6 removed.

---

## M2R-5 — GUI editors for the blocking uncovered fields (2026-07-21 review, MAJOR, complete 2026-07-21)

**Objective.** Two inputs that govern the results had **no on-screen widget** —
editable only by hand-editing `project.json`: (a) `landing.cg_cases`, the three
distinct landing loadings LANDLOAD requires (aft-max / fwd-max / fwd-light); (b)
`SelectInput.full_down_aileron_deg` / `basic_airfoil_cm` / `wing_weight_lb`, which
drive the 23.349(b) steady-roll wing-torsion score and the critical-fuselage wing
weight and defaulted silently (0 / 0 / 0.09·MTOW).

**Key decision (2026-07-21 consultation).** Seed the landing CG editor from the
**WTENV structural CG envelope**, not `project.mass.cases` as the backlog literally
said: `weight_onecg.build_mass` emits only **one** `MassCase` ("itemized loading"),
so `mass.cases` cannot supply three *distinct* fwd/aft/light rows (the very
degeneracy M2-8 removed auto-derivation to avoid). WTENV gives the fwd-most/aft-most
structural CG stations (`validation.wtenv_cg_limits`) plus the gross /
fwd-regardless weights; the waterline comes from the itemized loading when present.
The fwd/aft split is a seed the engineer confirms (WTENV cannot distinguish it per
loading).

**Deliverables (no schema change; `SCHEMA_VERSION` stays 32).**
- `app/views/landing_loads.py` — a fixed 3-row `st.data_editor` (`_seed_cg_rows`
  helper) in the page form; Apply writes `landing.cg_cases`; the hard "provide
  WTONECG results or edit the JSON" gate replaced by an in-place info until three
  positive-weight rows are applied.
- `app/views/flight_envelope.py` — a `_select_inputs_form` (`st.expander` + form) on
  the Critical Loads tab for the three `SelectInput` fields, each with `help=`;
  Apply writes `project.select_input`.
- `farloads/validation.py` — promoted `_wtenv_cg_limits` → public
  `wtenv_cg_limits`; re-pointed the existing `app/views/weight_mass.py` importer
  (removes one `app/`-imports-`farloads`-underscore violation — partial M4-12).

**Test / Acceptance.** `tests/test_dirty_flag.py`: `landing_loads.py` added to the
render-leaves-project-unchanged parametrization (both new forms persist only on
Apply); `test_landing_cg_editor_seeds_and_persists_on_apply` (WTENV seed → Apply →
3 CG cases at the fwd/aft stations & gross/fwd-regardless weights);
`test_select_inputs_persist_only_on_apply` (DN / Cm / WW → Apply →
`project.select_input`). Full suite green (475 passed); ruff clean. No calc change —
the SELECT/landing oracles are untouched.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M2R-5 removed and the
M4-12 note updated for the `wtenv_cg_limits` promotion.

---

## M2R-4 — Kill the last on-render Project mutation (2026-07-21 review, MAJOR, complete 2026-07-21)

**Objective.** Make rendering the **Landing Loads** page non-mutating.
`landing.build_landing()` wrote three things back onto the live `Project` on every
render — gear geometry synced from `geometry.landing_gear` onto `project.landing`,
the derived gross-weight default (`gross_weight_lb`), and the LGFACTOR result
(`n`) — so merely opening the page flipped 🟠 *Unsaved changes* (the last G4
residue, verified by per-page bisection) and `run()` was impure in the calc layer.

**Deliverables (`SCHEMA_VERSION` 31 → 32).**
- `farloads/modules/landing.py` — replaced the mutating `_sync_gear_from_geometry`
  (returned `None`, wrote onto `project.landing`) with the pure
  `_effective_gear_input(project, inp)`, which returns a `dataclasses.replace` copy
  carrying the single-source `geometry.landing_gear`. `build_landing` resolves the
  gear geometry **and** the heaviest-CG gross-weight default onto that local
  effective copy and passes it to `landing_reactions`; the `inp.n =` write-back is
  deleted (N is already returned on `LoadFactorResult.airplane_load_factor`).
- `farloads/models.py` — removed the redundant write-back `LandingInput.n` field
  (a mirror of the returned load factor that nothing consumed); updated the
  `LandingInput`/`LandingGearGeometry` docstrings and the `SCHEMA_VERSION`
  changelog comment (v32).
- `examples/*.project.json` — bumped `schema_version` 31 → 32 and dropped the dead
  `"n"` key from the `landing` block (data-only; loads are byte-identical).
- `docs/10_standard/DATA_DICTIONARY.md` regenerated; `PROGRAM_SPEC.md` LGFACTOR/
  LANDLOAD **Writes/Reads** rows updated (pure; effective-input copy, no
  write-back).

**Test / Acceptance.** New `test_landing.py::test_render_leaves_project_unchanged`
asserts `io.project_to_dict(p)` is unchanged after `build_landing(p)` + `run(p)`
(the exact `_has_unsaved_changes` predicate) on both the full GA-6 fixture and a
`gross_weight_lb = 0` project (the derived-default path). `test_landload_pipeline_and_run`
updated to read `lf.airplane_load_factor` instead of the removed `p.landing.n`. The
Appendix-A ground-load oracle is byte-identical
(`test_landloads_reactions_unchanged_bit_for_bit` unchanged — the math runs on an
identical effective input). Full suite green (467 passed); ruff clean.

**Key decisions.** `LandingInput.n` **removed**, not merely left unwritten — it was
a result-shaped duplicate of `LoadFactorResult.airplane_load_factor` with no
consumer; migration stays lenient (the tolerant `landing_from_dict` ignores an
older file's `"n"` key), so a `SCHEMA_VERSION` bump with no migration code suffices.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]` entry; backlog M2R-4 item and
its Known-defects bullet removed.

---

## M2R-3 — Ship working examples (2026-07-21 review, MAJOR, complete 2026-07-21)

**Objective.** Remove the red errors a first-time user meets when loading a
bundled example: **Fuselage Loads** hard-errored on the 5 examples missing
`fuselage_mass`, and **Landing Loads** hard-errored on `concept_regional_jet`
(2 of the required 3 `cg_cases`) and the examples with none.

**Key decisions (2026-07-21 consultation).** Widened the backlog's literal
two-edit scope after finding every example is also a **test fixture** (loaded
directly from `examples/`): (1) **complete five** examples to a clean end-to-end
run rather than the scoped two; (2) **remove nothing** — deletion would only
trade example-authoring for test-rewriting and lose category coverage; (3) keep
`concept_heavy` as the **deliberate minimal-core** fixture (it anchors
`test_concept.py`; no engines/select_input by design), documented as such.

**Deliverables (data-only; `SCHEMA_VERSION` unchanged at 31).**
- `examples/concept_regional_jet.project.json` — added the 3rd landing `cg_case`
  (`fwd light`, 26000 lb @ xcg 595).
- `examples/ga6_normal.project.json`, `examples/cessna_210.project.json` — added
  `fuselage_mass` (stations binned from the file's own non-wing weight items;
  centroid ≈ the airplane CG).
- `examples/dhc8_dash8.project.json`, `examples/atr42_100.project.json` — added
  `fuselage_mass`, a `landing` slice with 3 CG cases (fwd/aft from the wing MAC +
  weight-envelope pct-MAC limits), and `geometry.landing_gear` (main aft of the
  aft CG for tip-back; consistent ground plane).
- `docs/10_standard/GUI_USER_GUIDE.md`, `README.md` — a bundled-examples table;
  `concept_heavy` annotated as the minimal concept core (V-n → Flight Envelope).
- Three fixture-coupled tests updated to the completed state:
  `test_body_loads.py` (clears `fuselage_mass` locally to still exercise the
  guard), `test_io.py` (GA6 now runs `body_loads` in run-all), `test_workbook.py`
  (a module with an empty cases-CSV, like `body_loads`, gets no module sheet).

**Test / Acceptance.** All five completed examples run `body_loads` + `landing`
and `run_all_modules` with no missing-slice error; the sbeam fuselage span CSV
exports for each; `concept_heavy` stops cleanly at Flight Envelope. Full suite
green (466 passed); ruff clean.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]` entry; backlog M2R-3 item and
its Known-defects bullet removed.

---

## M2R-2 — Non-affiliation & attribution sentence (2026-07-21 review, MAJOR, complete 2026-07-21)

**Objective.** State plainly, in both the README and the GUI, that this project
is an independent open replication and is **not affiliated with** the vendor of
the commercial "FAR 23 LOADS" product — legal-exposure mitigation, decoupled
from the M3-1 rename ("immediately, regardless", per the 2026-07-19 review).

**Deliverables.**
- **`README.md` Disclaimer.** Reworded the opening to "modern **open
  replication** of the FAR23 loads suite (DOT/FAA/AR-96/46; Hal C. McMaster's CAE
  theory manual)" and added a dedicated paragraph: **not affiliated with,
  endorsed by, or associated with McGettrick Structural Engineering, Inc. or
  DARcorporation**, whose "FAR 23 LOADS" is a separate commercial product.
- **`app/Home.py` sidebar.** Added an app-wide **ℹ️ About** expander plus a
  one-line footer caption, built once in the sidebar block so they appear on
  every page under `st.navigation`. The About text carries the open-replication
  description, the not-certified caveat, and the same non-affiliation sentence.

**Test / Acceptance.** Documentation/GUI-copy only — no calc/schema/test change.
`app/Home.py` compiles and passes `ruff`; the About/footer render in the sidebar
on every page.

**Key decisions.** Placed the GUI notice in the **sidebar** (built once in
`Home.py`) rather than per-view, so it shows app-wide with no per-page
duplication; kept it collapsed in an expander plus a persistent one-line footer.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]` Documentation entry; backlog
M2R-2 removed.

---

## M2R-1 — Doc currency sweep (2026-07-21 review, 1 CRITICAL + 3 MAJOR, complete 2026-07-21)

**Objective.** Retire the stale and contradictory documentation the 2026-07-21
code & documentation review flagged, so no shipped doc asserts a false schema
version or oracle-lock claim.

**Key decisions (2026-07-21, user-confirmed).** (1) The stale `GUI_design.md`
schema line is fixed by **pointing at the generated `DATA_DICTIONARY.md`** (the
single source, currently v31) rather than re-baking a number that would rot at
the next bump. (2) The `CLAUDE.md` oracle-lock sweep fixes the three cited lines
**plus** a grep-sweep for exact duplicates; the "Appendix A **and/or** B"
per-module test convention and the frozen `40_history` record are correct and
left untouched.

**Deliverables.**
- **(a) `docs/10_standard/GUI_design.md`.** Replaced `SCHEMA_VERSION = 28` + its
  baked migration trail with a pointer to `DATA_DICTIONARY.md` (v31) and the
  per-step history in `40_history/`.
- **(b) `CLAUDE.md`.** Retired the "Appendix A/B ±0.1%" oracle-lock claim at
  `:19`/`:28`/`:189` → "Appendix A ±0.1%; twin cases closure-locked", linking the
  Oracle-status anchor in `00_theory_sources.md#oracle-status` (Appendix B is not
  in the bundled scan). Repo-wide grep confirmed no remaining exact dupes of the
  false present-tense claim.
- **(c) `docs/10_standard/PROGRAM_SPEC.md`.** Filled the schema-version trail —
  inserted **v29** (single-source CLmax stall, M1-1b), appended **v31** (M2-10
  operational placards).
- **(d) Cross-doc currency.** `00_INDEX.md`: added rows for
  `01_far25_gap_analysis.md` and `01_verification_baseline_0.2.0.md`, enumerated
  the `reference/` CFR/AC text extracts, and replaced the "two-phase plan"
  backlog description with the M2R→M3→M4→F25 milestone structure.
  `00_theory_sources.md`: corrections-register pointer `CLAUDE.md` →
  `02_approved_corrections.md`. `README.md`: examples line → all six fixtures
  (added `atr42_100`, `concept_regional_jet`).

**Test / Acceptance.** Documentation-only — no calc/schema/test change,
`SCHEMA_VERSION` stays 31. Re-grep shows no `SCHEMA_VERSION = 28`, no false
"Appendix A/B ±0.1%" oracle-lock assertion, and no orphaned docs in `00_INDEX.md`.
Suite unaffected (no code touched).

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]` Documentation entry; backlog
M2R-1 removed.

---

## M2-11 — Input data dictionary + short GUI user guide (review D4 part 1, complete 2026-07-20)

**Objective.** Give the project two missing references: a `project.json` **data
dictionary** (the schema is `SCHEMA_VERSION` 31 deep and `models.py` was its only
reference) and a task-oriented **GUI user guide**.

**Key decisions (2026-07-20, user-confirmed).** (1) The data dictionary is
**generated by an introspection script**, not hand-written — type/default from
`dataclasses`/`typing.get_type_hints`, units parsed from each field's inline
comment (suffix fallback). (2) Owning-page / consuming-modules columns are
**slice-level** (the honest granularity `workflow.py` records), not per-field.
(3) **Input slices only** (result slices `envelope`/`mass`/`loads` excluded).
(4) The user guide is written **brand-neutral now** and takes a rename pass at
M3-1 rather than being deferred.

**Deliverables.**
- **`docs/generate_data_dict.py`.** Introspects `farloads.models` Project input
  slices → `docs/10_standard/DATA_DICTIONARY.md`: per-slice map (type, owning
  page, consuming modules from a source scan, role) + one field table per input
  dataclass (field, type, units/notes, default) + an enums appendix. Owning page
  from `workflow.py` `produces` plus a small override table for slices workflow
  doesn't attribute; consumers from a word-bounded `.<slice>` scan of
  `farloads/modules/*.py`.
- **`docs/10_standard/DATA_DICTIONARY.md`** (generated, 581 lines).
- **`docs/10_standard/GUI_USER_GUIDE.md`.** Workflow phases + page map, the
  seed chain, what-to-enter-where tour, LIMIT-vs-ULTIMATE reading rules, the
  `ga6_normal` end-to-end walkthrough with four hand-checkable numbers
  (WTESTIMA MTOW 3468, WTONECG XBAR 84.99936 / IYY 2058.209, STRSPEED n₊ 3.8 /
  VA 121.3, FLTLOADS MAN A NZ 3.80) traced from the 0.2.0 verification baseline.
- **`docs/00_INDEX.md`.** Both new docs indexed under 10_standard.

**Test / Acceptance.** `tests/test_data_dictionary.py`: committed doc equals the
generator output (drift guard — a schema change that skips regeneration fails
CI), every input slice documented, schema version recorded. Full suite green
(466 passed); ruff clean on `docs/generate_data_dict.py`.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M2-11 removed.

---

## M2-10 — Operational-speed linkage on the Design Speeds page (all three tiers, complete 2026-07-20)

**Objective.** Make the Design Speeds page explain and surface how the structural
design speeds (Subpart C) bound the eventual **operating limitations / cockpit
placards** (Subpart G) — advisory only, no loads-math change.

**Key decisions (2026-07-20, user-confirmed).** (1) **All three tiers ship now**
(Explain + Derive + Constrain), closing M2-10 before the 0.3.0 cut. (2) **Both
placard families are always shown** in the Derive advisory — the recip yellow-arc
set (VNE/VNO/MNE) and the turbine VMO/MMO set — each captioned with when it
applies, rather than inferring one from project data. (3) **Targets are warn-only:**
an infeasible operational target produces a concrete warning and never mutates a
design speed or blocks Apply (display/validation only).

**Reference (mandatory consult).** New `reference/14CFR_operating_limitations.md`
(web-verified 2011 CFR ed.): 14 CFR 23.1505(a) VNE ≤ 0.9·VD; 23.1505(b) VNO ≤
min(VC, 0.89·VNE); 23.1511 VFE ≤ VF; and Ref 1 p47 (`code.txt` 4147–4152) for
VNE/MNE = 0.9·VD/MD, the yellow arc, and the turbine/23.335(b)(4) VMO/MMO ≤ VC/MC
rule. MC→MD 0.05 Mach margin per 23.335(b)(4)(ii) (`14CFR_MC_MD_speed_margin.md`).

**Deliverables.**
- **`farloads/modules/structural_speeds.py`.** `operational_placards(ds)` →
  `OperationalPlacards` (VNE=0.9·VD, VNO=min(VC, 0.89·VNE), MNE=0.9·MD, VMO=VC,
  MMO=MC, VFE=VF); `operational_target_checks(inp, ds)` → `List[TargetCheck]`
  inverting the ladder into required design minima; `operational_implications(
  project, inp)` → the advisory `ConditionResult`s (both families + optional
  feasibility). No load quantity involved, so plain (non-`ULT`) units.
- **`farloads/models.py`.** `StructuralSpeedsInput` gains `no_yellow_arc` +
  `target_vne`/`vno`/`vmo`/`mmo`/`vfe`; **SCHEMA_VERSION 30 → 31** (lenient — older
  files lack the keys and take the defaults; io round-trips via `asdict`/`**d`).
- **`farloads/validation.py`.** `_check_operational_targets` emits the
  `operational_target_infeasible` warning (page `structural_speeds`) so infeasible
  targets also surface on the dashboard.
- **`app/views/structural_speeds.py`.** Explain expander (constraint ladder +
  citations); optional operational-target inputs on the form (turbine flag + the
  five targets); read-only "Operating-limitation implications (advisory)" panel
  rendering the placards, feasibility and any infeasibility warning.
- **Examples.** All six fixtures bumped to `schema_version` 31 (pure metadata).

**Test / Acceptance.** `tests/test_structural_speeds.py`:
`test_operational_placards_ga6` (VNE 191.25, VNO 170, MNE 0.363, VMO 170, MMO
0.3226, VFE 105.5 within ±0.1%), `test_operational_implications_shows_both_families`,
`test_operational_target_feasible_and_infeasible`, `test_operational_target_mmo_margin`.
`tests/test_validation.py`: `test_operational_target_infeasible_fires`,
`test_operational_target_feasible_silent`. The M2-7 persistence field-coverage guard
round-trips the new v31 fields. Full suite green (463 passed); ruff clean.

**Docs.** `PROGRAM_SPEC.md` (STRSPEED reads/advisory writes + Notes),
`20_theory/00_theory_sources.md` (placard-ladder citations), this move,
`CHANGELOG.md`.

---

## M2-9 — `scripts/smoke_test.sh` portability (release-mechanics, complete 2026-07-20)

**Objective.** Make the release smoke test run under any install layout, not only a
project-local `.venv`.

**Problem.** The script hardcoded `$ROOT_DIR/.venv/bin/{python,streamlit,farloads}` and
guarded each with an `-x` executable check, so any machine that installed into a
differently-named venv, a conda env, or a `pyenv`/system interpreter failed the guard
immediately even with a perfectly good editable install.

**Key decisions (2026-07-20, user-confirmed).** (1) **Interpreter = venv-preferred with
PATH fallback** — honour an explicit `PYTHON` env override, else prefer
`$ROOT_DIR/.venv/bin/python` when present, else fall back to `python3`/`python` on PATH;
keeps the existing dev flow unchanged while unbreaking other layouts. (2) **Invoke through
the one resolved interpreter** — `"$PYTHON" -m streamlit run …` and `"$PYTHON" cli.py
engine …` replace the hardcoded `streamlit`/`farloads` binaries.

**Deliverables.**
- **`scripts/smoke_test.sh`.** Interpreter-resolution block (`PYTHON` override → `.venv` →
  PATH); the three-way `-x` guard collapses to one usable-interpreter check plus a single
  `"$PYTHON" -c 'import streamlit, farloads'` importability probe with a generalized
  `pip install -e .[dev]` hint; both invocation sites routed through `"$PYTHON"`.

**Test / Acceptance.** `bash scripts/smoke_test.sh` passes under the default `.venv`; the
PATH-fallback path verified via `PYTHON="$(command -v python3)" bash scripts/smoke_test.sh`
(both: Streamlit HTTP 200 + no traceback, CLI writes 3 load-case rows). Script-only change —
no calc, schema, or module touched; suite unaffected.

**Key decisions.** See above.

---

## M2-8 — Landing CG cases: require explicit distinct loadings + concept 23.473(g) floor (review — landing minor, complete 2026-07-20)

**Objective.** Remove the degenerate landing CG-case fallback and flag the FAR 23.473(g)
load-factor floors in concept mode.

**Problem.** `landing._cg_cases` auto-derived the "aft max landing" and "fwd max landing"
loadings from the **single heaviest** `Project.mass` case, so the two were byte-for-byte
identical (same weight, `xcg`, `zcg`). LANDLOAD's nose-gear and braked-roll reactions turn
on the fwd/aft `xcg` through the `AP/BP/CP` lever arms, so the degenerate pair
**under-predicted** those reactions whenever a project relied on the fallback. UG fig 18.2
uses three genuinely distinct loadings.

**Key decisions (2026-07-20, user-confirmed).** (1) **Require explicit `cg_cases`** —
stop auto-deriving entirely and raise a clear error unless three distinct loadings are
supplied (rejected the alternative of deriving fwd/aft from the WTENV envelope: it cannot
supply a per-corner weight or waterline, only the longitudinal station). The WTENV
structural fwd/aft CG limits (`validation._wtenv_cg_limits`) remain the intended *authoring*
source. (2) **23.473(g) floors → warn-only, concept mode.** A note on the LGFACTOR
condition when `N < 2.67` or `NLG < 2.0`, gated on `project.is_concept`; the computed
`N`/`NLG` are left untouched (Appendix-A 3.0951 / 2.4281 sit above the floors, oracle
unaffected).

**Deliverables.**
- **`farloads/modules/landing.py`.** `_cg_cases(inp)` (no longer takes `project`) requires
  a non-empty, exactly-three `cg_cases` and raises otherwise — the `Project.mass` fallback
  is gone. `run` appends the concept-mode 23.473(g) floor note when a load factor is short.
- **`tests/test_landing.py`.** `test_landing_requires_explicit_cg_cases` (empty `cg_cases`
  raises with a `cg_cases` message); `test_landing_473g_floor_warning_concept` (soft-strut
  GA gear drives `N`/`NLG` below the floors → the note appears in concept mode);
  `test_landing_473g_floor_not_warned_in_far23` (the same project in FAR23 mode is silent).
- **Docs.** `PROGRAM_SPEC.md` (LANDLOAD reads/notes), `20_theory/00_theory_sources.md`
  (473(g) floor + distinct-CG requirement), this move, `CHANGELOG.md`.

**Test / Acceptance.** Full suite green (457 passed), `ruff` clean. All six shipped
examples already carry explicit `cg_cases`, so none regress. Calc-local; no schema change.

---

## M2-7 — Step G7 — Persistence verification (G-3, complete 2026-07-20)

**Objective.** Verify (and lock) decision **G-3**: every input-bearing value lives on a
`Project` slice `io.py` round-trips, with no input data stranded in `st.session_state`;
save→reload of each example is a no-op.

**Audit result (already satisfied by the D5/G-series/M2-6 single-source work).**
(1) All six example projects are save→reload no-ops (JSON-normalized dict comparison).
(2) The only session_state keys the GUI writes are UI state — `project` (the canonical
store), `unit_system` (display preference), `_saved_project_snapshot` (the dirty-flag
baseline), `engine_sel` (the Engine Mount radio selection), the Project Editor's re-seeded
JSON text scratchpad, and Streamlit-managed widget keys — none holding un-persisted
airplane input. Transient in-form edits before **Apply** are the deliberate Form+Apply
design (M2-3/G-4), not a violation: the acceptance reads as *persistent* input data.

**Key decisions (2026-07-20, user-confirmed).** (1) **Completeness guard**, not just an
example no-op check: a field-coverage test constructs each input dataclass with every
field set to a distinct non-default sentinel (recursively, through nested dataclasses /
lists / enums), round-trips it through its `io` pair, and asserts every field survives —
so a field added later without `io` wiring fails the build. Intentionally-derived fields
(the M2-6 single-source set + the G6/G6b geometry moves) sit in a `DERIVED_NOT_PERSISTED`
allowlist, itself guarded against rename drift. (2) **Defer** the Streamlit `key=`+`value=`
display-freshness footgun (orthogonal to data persistence; no data is lost today) to the
L-8 long-tail UX batch.

**Deliverables.**
- **`tests/test_persistence.py` (new).** `test_every_example_save_reload_is_a_noop`
  (relocated from `test_derived_geometry.py`); `test_input_dataclasses_round_trip_every_field`
  (the completeness guard, with the recursive filler + `DERIVED_NOT_PERSISTED` allowlist);
  `test_derived_allowlist_entries_are_real_fields` (guards the allowlist against renames);
  `test_no_input_data_written_outside_project_session_state` (static scan of `app/` — every
  `st.session_state[...] =` write uses an allow-listed UI key, tripping a review when a new
  key appears).

**Test / Acceptance.** Full suite green (454 passed), ruff gate clean; the completeness
guard verified to catch a dropped field (removing an allowlist entry fails the test).

---

## M2-6 — Step G6c — Geometry single-source cleanup (wing + fuselage + power, complete 2026-07-20)

**Objective.** Close the remaining *softer* geometry/power double-entry the G6 audit
surfaced (after G6/G6b single-sourced the empennage and landing-gear geometry): the wing
scalars several downstream slices carried as independently-editable copies, the fuselage
length/width/height that duplicated the outline, and the weight-estimate power that
restated the engine list.

**Key decisions (2026-07-20, user-confirmed).** (1) **Wing → pure proxy, no override.**
`FlightLoadsInput.mac`/`wing_area_sqft`/`xw`/`zw`, `WingMassInput.dihedral_deg`/
`wrp_waterline`, `LandingInput.wing_area_sqft` derive from `Project.geometry`; not
persisted; GUI read-only. Rather than remove the dataclass fields (dozens of tests
construct these slices directly), they stay as a derived cache filled by a sync at calc
entry (mirroring `landing._sync_gear_from_geometry`), and fall back to the stored value
when no wing geometry is present (the STRSPEED pattern) so bare unit tests are unaffected.
(2) **Full fixture work now.** GA6 had no `geometry.parametric`, so ZW/dihedral/wrp had no
source; a parametric wing slice (wing scalars backed out of the WINGGEOM surface +
`root_waterline_z = 78.5`, `dihedral_deg = 6.0`) was added, and the real derivation
`ZW = wrp + Y_MAC·tan(dihedral)` implemented (GA6 87.734 vs the old stored 87.725, +0.01%,
inside the ±0.1% oracle band). (3) **Concept S drift accepted** — the RJ closure fixture's
reference area 500 re-baselines to the WINGGEOM strip integral 497.75 (no printed oracle).
(4) **Fuselage → outline sole editable**, `LayoutInput` L/W/H a derived read-only summary.
(5) **Power → derive from `sum(engines[].max_cont_hp)` + override toggle.**

**Deliverables.**
- **`farloads/derived_geometry.py` (new).** `wing_reference(project)` (the shared wing
  derivation, subsuming the three scattered copies in `structural_speeds`,
  `flight_envelope` and `landing`), `fuselage_summary(outline)`, and
  `sync_geometry_derived(project)` — called at the top of `build_envelope`/`trim_sweep`/
  `build_critical`/`build_body_loads`/`verify_balancing`/`build_wing_inertia`/
  `build_net_loads` and by `io.project_from_dict` after load.
- **`weight_estimate.resolve_max_continuous_hp(project)`** — engine-list total unless
  `override_max_continuous_hp`; `run` applies it; `estimate` itself unchanged.
- **`models.py`** — `WeightEstimationInput.override_max_continuous_hp` (default False);
  `FlightLoadsInput.merged()` drops the wing-geometry args; derived-field docstrings;
  `SCHEMA_VERSION` 29 → 30.
- **`io.py`** — `flight_loads_to_dict`/`wing_mass_to_dict`/`landing_to_dict`/
  `configuration_to_dict` drop the derived wing/fuselage fields; `from_dict` still reads
  them (migration); post-load `sync_geometry_derived`.
- **GUI** — Flight Envelope, Wing Loads, Landing show the wing geometry read-only;
  Geometry page shows fuselage L/W/H as a read-only summary of the outline (the outline
  the sole editable shape); Weight & Mass adds the engine-total caption + override toggle.
- **Fixtures** — all six examples migrated to schema 30 (GA6 gained the parametric slice;
  derived copies dropped).

**Test / Acceptance.** New `tests/test_derived_geometry.py` (wing derivation, sync,
no-persistence, no-geometry fallback, fuselage summary, power resolver). The
save→reload-no-op check now lives in `tests/test_persistence.py` (Step M2-7).
Updated `test_flight_envelope`/`test_io`/`test_empennage` for the
derived/dropped fields and the newly-running `configuration` module on GA6. Full suite
green (451 passed), ruff clean; Appendix A oracles bit-for-bit.

---

## M2-5 — Aircraft Comparison: surface-planform fallback + Develop-phase link (GUI fix, complete 2026-07-20)

**Objective.** Review finding **G7**: the Aircraft Comparison subject showed "None"
for W/S, wing area, span and aspect ratio on nearly every shipped example.
`_subject_from_project` (`aircraft_comparison.py`) read wing geometry only from
`geometry.parametric` (the `LayoutInput`) — area `parametric.wing_area_sqft →
speeds.wing_area_sqft`, AR `parametric.aspect_ratio` only, span back-derived from
`√(AR·area)`. But of the six shipped examples only `concept_regional_jet` carries a
parametric layout; the rest carry `geometry.surfaces` (WINGGEOM planforms), so AR and
span were `None` on every non-parametric example (and area/W/S `None` wherever
`speeds.wing_area_sqft` was also absent, e.g. `ga6_normal`). Also (G7 second half):
the fleet check lived in the **Export** phase, after the load analysis, when it is
most useful at *definition* time.

**Key decisions (2026-07-20, user-confirmed).** (1) **Surface-planform fallback with
area priority `parametric → surface → speeds`.** Add a `geometry.by_name("wing")`
fallback via `wing_geometry.surface_properties` (which yields **Total area** in²,
**Aspect ratio**, and **Span** in — full-planform figures), the same pattern
`flight_envelope.py:89-96` uses; AR and span use the surface as their sole
non-parametric source. The computed planform is trusted over the scalar
`speeds.wing_area_sqft`. (2) **Link, do not move.** Keep the page in the Export phase
(unchanged `workflow.py` order — `03_gui_rework_plan.md §4 Phase 6` placement holds)
and add a workflow-derived `page_link` from the Develop phase, so the single source
of navigation truth is untouched.

**Deliverables.**
- **`aircraft_comparison.py` — `_wing_surface_props(project)`** returns the WINGGEOM
  `wing`-surface properties keyed by label (`{}` on a missing/degenerate wing).
  `_subject_from_project` now resolves wing **area** `parametric → surface (Total
  area ÷ 144) → speeds`, **AR** `parametric → surface`, and sets
  `Subject.wingspan_ft` directly from the surface **Span** (÷ 12) instead of
  back-deriving it. The `Subject` constructor now receives `wingspan_ft`.
- **`weight_mass.py`** — a `components.workflow_page_link("aircraft_comparison")` at
  the top of the Weight & Mass Properties page (the definition-time point where
  MTOW/OEW/power are set), captioned as the fleet W/S / W/P check.

**Test / Acceptance.** Extended `tests/test_aircraft_comparison.py`:
`test_subject_geometric_axes_from_wing_surface` (GA-6 recovers area/W/S and the
Appendix-A wing AR 6.095 / span 33.5 ft from its planform with no parametric layout
and no `speeds.wing_area_sqft`); `test_area_priority_surface_over_speeds` (the
computed planform wins over the scalar `speeds.wing_area_sqft`); the existing
example/synthetic/no-MTOW tests still hold (parametric still wins where present).
Every shipped example now places fully on the fleet scatters. Presentation-only — the
reference fleet is never a FAR input, so no calc/oracle/schema change; `workflow.py`
step order unchanged. Full suite green (443 passed); `ruff` clean.

**Observation (not blocking, logged).** With the chosen `parametric → surface →
speeds` order, `atr42_100`'s wing-surface area (≈480 ft²) — a coarser WINGGEOM
planform — now supersedes its scalar `speeds.wing_area_sqft` (586.6 ft²), shifting
its displayed W/S. This is the intended "trust the planform" behavior; the underlying
fixture-area discrepancy is a data-quality item for the ATR planform, not a logic
defect.

---

## M2-4 — Results Review header tables: units, ULT marking, SF (GUI fix, complete 2026-07-20)

**Objective.** Review finding **G5**: the "Governing loads (SELECT)"
per-component tables on **Results Review** and the **Flight Envelope → Critical
Loads** tab hand-built each row as `row[lv.label] = round(lv.value, 2)` — dropping
`LoadValue.units`, the mandatory `-ULT` marker and the safety factor, and printing
literal `None`/NaN in the sparse cells where components carry different label sets.
The substantive bug: the shared `_display_loads` did only the Imperial→SI
conversion and **never applied the limit→ultimate factor**, so the headline an
engineer screenshots into a design review was showing **unmarked LIMIT loads as if
they were the deliverable** — violating the ultimate-output contract on a
consolidation page while contradicting the lower per-section tables (which render
correctly through `report.py`).

**Key decisions (2026-07-20, user-confirmed).** (1) **Flat SF 1.5 at the render
boundary.** `CriticalCondition` carries no `safety_factor` field, but every SELECT
governing condition is a standard limit flight-load (SF 1.5 per 14 CFR 23.303);
apply `constants.ULTIMATE_FACTOR` at the helper and show `SF 1.5` — no
`models.py`/`io.py`/`SCHEMA_VERSION` change. The per-case carrier is deferred to
**M4-8** (centralized two-layer SF policy), which is where a non-1.5 governing case
would first arise. (2) **One shared helper for both tables** so they can't diverge;
both render ULTIMATE.

**Deliverables.**
- **`report.py` public wrappers.** `ultimate_units(units, quantity="") -> str` and
  `to_ultimate(value, units, quantity="", sf=ULTIMATE_FACTOR)` — thin public
  exposures of the existing privates (`_ult_units`/`_ult`), keeping the
  limit→ultimate boundary owned by `report.py` (CLAUDE.md: applied "once, at the
  render/export boundary").
- **`report.governing_loads_table(conditions, system, sf=ULTIMATE_FACTOR)`.**
  Returns row dicts (pandas stays in the views). For a list of `CriticalCondition`,
  it converts each condition's `loads` to display units (the `_display_loads`
  unit-conversion path, factored out of the two views into `report.py`), builds one
  row per condition (`Condition`, `FAR`, `V-n case`, then one column per load label
  headed `f"{label} ({ultimate_units(units, quantity)})"`), scales load cells via
  `to_ultimate` and formats with `_fmt`, appends an `SF` column, and fills cells
  absent from a given condition with `"—"` across the column union.
- **Both views rewired.** `results_review.py` (headline) and `flight_envelope.py`
  `_tab_select` now call `governing_loads_table(...)`; the duplicated
  `_display_loads` in each view is deleted. Captions on both surfaces state the
  tables are ULTIMATE (`-ULT` + `SF`), and the unused `ConditionResult` import is
  dropped from `flight_envelope.py`.

**Test / Acceptance.** New `tests/test_results_review.py`: (a) a force column
header carries `-ULT` and its value is `limit × 1.5`; (b) dimensionless columns
(load factor NZ / CL) are unscaled with no `-ULT`; (c) every row's `SF` column is
`1.5`; (d) sparse cells render `"—"` with no `None`/NaN and every row spans the
full column union; plus a determinism check (both views, same helper → identical
table). Render-only — no calc/oracle/model/schema change (the calc still emits
LIMIT; Appendix A oracles untouched). Full suite green (441 passed); `ruff` clean.
Closes the last unmarked-LIMIT deliverable surface found by the review; dovetails
with **M4-8** (which will let `governing_loads_table` read `c.safety_factor`
instead of the flat `sf` argument).

---

## M2-3 — Dirty flag: move on-render writes into Apply handlers (GUI fix, complete 2026-07-20)

**Objective.** Review finding **G4**: `flight_envelope.py` and
`structural_speeds.py` mutated the project **on render** (auto-seeding
derived/defaulted sub-slices outside any Apply handler), so the sidebar's "Unsaved
changes" flag — `project_to_dict(p) != saved_snapshot` (`Home.py`) — tripped with
zero user edits and the discard-confirm dialog fired spuriously (reviewer: load
ATR-42 → "No unsaved changes"; three page-visits later → "Unsaved changes"). Root
cause: seeding a slice on visit violates the app's own **"Form + Apply, merge not
replace"** design principle (`03_gui_rework_plan.md §7`). All three written slices
(`flight_loads`, `speeds.mach_limit`, `envelope.critical`) round-trip through
`io.py`, so a render-time seed genuinely changed the persisted dict.

**Key decision (2026-07-20, user-confirmed): require an explicit Apply.** Persist
only on submit; compute the live diagram from an in-memory *effective* input.
Accepted consequence: visiting no longer seeds downstream slices — the engineer
clicks Apply once, and the existing downstream gates ("Define the flight-loads
inputs on the Flight Envelope (V-n) page first") now correctly mean "hit Apply".
No `SCHEMA_VERSION`/calc-math change; oracles untouched.

**Deliverables (the three write sites fixed; a fourth was already correct).**
- **`flight_envelope.py` — `flight_loads` (primary).** Wrapped the sidebar
  FLTLOADS geometry + reference Mach in `st.form("flight_geometry_form")` with an
  "Apply geometry & altitudes" submit. Each render builds `fl_effective =
  fl.merged(...)` locally; the page then computes from a **shallow-copy probe** —
  `session_project = project; project = copy.copy(session_project);
  project.flight_loads = fl_effective` — so the V-n / SELECT / trim tabs and
  `build_envelope`/`flt_run` see the effective input without mutating the saved
  project. `project.flight_loads` is written to the real `session_project` **only**
  on Apply. Dropped the redundant per-render `st.session_state["project"] =
  project`. (The page's calc modules were verified pure — no `project.X =`
  mutation — so the probe sharing the other slices by reference is safe.)
- **`structural_speeds.py` — `speeds.mach_limit` (primary).** The Speed–Altitude
  tab (`_tab_speed_altitude`) had **no form**: `max_operating_altitude`/`increment`
  were bare widgets and the `MachLimitInput` was persisted every render. Wrapped
  them in `st.form("mach_limit_form")` + Apply; the Mach-limit chart renders live
  from the local `inp`, and `speeds.mach_limit` persists only on submit. `axis_unit`
  stays outside the form (display-only). Mirrors the Design Speeds tab, whose form
  (`if applied:` at :212) was already the correct pattern.
- **`flight_envelope.py` — SELECT selection.** `_tab_select` reassigned the whole
  recomputed `critical` object every render (which could differ from stored even
  with no deselection). Now it writes **only** `selected_case_ids`, and **only when
  it differs** from the stored value, onto `project.envelope.critical` (shared with
  the saved project via the probe) — a no-op render leaves the project untouched;
  a real deselection dirties (correct).

**Test / Acceptance.** New `tests/test_dirty_flag.py`: (1) parametrized over both
views × all six example projects — an `AppTest` render with **no** widget
interaction leaves `project_to_dict(session_state["project"])` byte-for-byte equal
to the loaded project (12 cases); (2) positive path — clearing `mach_limit` /
`flight_loads`, rendering, then clicking the form's Apply persists the slice.
GUI-only; full suite green (**438 passing**, `ruff` clean); no calc/oracle/schema
change.

**Notes / follow-on.** Persistence-hygiene sibling of **M2-7** (Step G7 — full
save→reload no-op audit); M2-3 fixes the two known offenders, M2-7 verifies the
whole app. The `flight_loads` geometry-echo fields kept behind the form become pure
read-throughs under **M2-6** (G6c) — the form is where the override-behind-a-toggle
pattern will live.

---

## M2-2 — Navigation: show the whole workflow; link between pages (GUI fix, complete 2026-07-20)

**Objective.** Two review findings, one step. **G3:** half the workflow — phases
3–6, *including Export* — was collapsed behind a "View 10 more" expander in the
sidebar on first run. **G6:** the app had zero `st.page_link`s; the dashboard
checklist and every "define X on the Y page first" gating message were dead text,
and two messages named pages that the Step-G1 geometry merge had renamed away
("Wing Geometry", "Configuration & Layout"). Display/navigation only — no
calc-math and no schema change; `farloads/workflow.py` stayed the single source of
navigation truth.

**Deliverables.**
- **(a) Root-cause link helper (`app/components.py`).** `workflow_page_link(key,
  *, label, icon, help, disabled)` renders an `st.page_link` to `views/<key>.py`
  with the label defaulting to the step's canonical `wf.BY_KEY[key].title` — so a
  page rename re-labels every link automatically and stale hand-typed names can't
  recur (the G6 root cause). `gate(message, *keys, kind="warning"|"info")` renders
  the notice plus one link per unblocking page. The helper degrades to a
  non-clickable `st.markdown` label when `st.page_link` can't resolve a target
  (standalone execution outside `st.navigation`, e.g. AppTest), so a dashboard row
  or gate hint never silently vanishes.
- **(b) Un-hid the workflow (G3).** `app/Home.py` → `st.navigation(sections,
  expanded=True)`; all eight groups (Start + six analysis phases incl. Export)
  render open. Bumped the `streamlit` floor `>=1.30` → `>=1.36` in `pyproject.toml`
  (`expanded=` was added in 1.36).
- **(c) Linked the dashboard checklist (G6).** `app/views/dashboard.py` rows are
  now `workflow_page_link`s (status emoji as `icon=`, `summary`/status/BAS folded
  into the `help=` tooltip). Blocked (⛔) steps stay navigable so the user lands on
  the page and reads its own now-linked gating message.
- **(d) Linked + de-staled every gating message (G6).** Converted the "define X
  first" gates across 14 views to `gate(...)`/`workflow_page_link(...)`:
  `wing_loads`, `flight_envelope` (×3 + the static-margin info), `fuselage_loads`,
  `tail_loads`, `weight_mass`, `structural_speeds` (×2, incl. migrating the one
  pre-existing raw `st.page_link`), `aero_coefficients`, `flap_loads`,
  `aileron_loads`, `tab_loads`, `one_engine_out` (×2), `results_review` (×2),
  `loads_plots` (×2), `export_report` (×2), `configuration_layout` (weight-seed
  gate). Fixed the stale page names: "Wing Geometry" / "Configuration & Layout" →
  **Geometry**, "Flight Envelope" → **Flight Envelope (V-n)**; and the stale phase
  word "Airplane pages" / "Analysis page" → concrete page links.

**Test / Acceptance.** GUI-only, no calc/schema change; full suite green (424
passing, `ruff` clean). New `tests/test_page_links.py`: (1) every `wf.BY_KEY` key
has a matching `app/views/<key>.py` (the helper's path assumption); (2) an AST
scan of all views asserts every literal key handed to `gate`/`workflow_page_link`
is a real workflow step (guards future stale links). The existing `test_views_smoke`
AppTest suite exercises the rendered links (it caught the standalone
`st.page_link` `url_pathname` failure, which the helper's fallback resolves). A
grep for the old page-name references in gating strings is clean.

**Key decisions.** (1) Dashboard rows render as `st.page_link` with icon+help
(BAS name folds into the tooltip) rather than keeping the markdown row and adding
a separate link — user-confirmed 2026-07-20. (2) Blocked steps stay **navigable**,
not disabled — user-confirmed 2026-07-20. (3) Links derive label+path from
`workflow.py` via one helper, making stale names structurally impossible rather
than a discipline to maintain. (4) `st.page_link` can't deep-link to a tab within
a merged page — the tab name stays in prose and the link points at the page.

---

## M2-1 — Loads Plots must recompute from the project (GUI fix, complete 2026-07-20)

**Objective.** The **Loads Plots** page (Load-case plotting phase) read
`Project.loads`, which **no code path ever constructs** — the slice is always
`None`, so the page stopped at its "No distributed loads computed yet" info box
with instructions (visit Wing/Fuselage/Tail/Aileron/Flap/Tab Loads) that could
never succeed. The five Analysis views each carried a matching dead
`if project.loads is not None:` write-back that never executed. (Review finding
G2; known defect M2-1, Major/GUI.)

**Deliverables.**
- **(a) Recompute in `loads_plots.py`.** Removed the `loads = project.loads` /
  `if loads is None: st.stop()` gate. The page now recomputes the four
  distributed-load channels live from the project inputs — `build_net_loads`
  (`.wing_net`), `build_body_loads`, `build_tail_chordwise`, and
  `build_aileron`/`build_flap`/`build_tabs` (control surfaces) — behind the same
  defensive `_try` wrapper `export_report.py` uses (catches
  `ValueError`/`ZeroDivisionError`/`KeyError`/`IndexError` so a channel whose
  upstream inputs are absent degrades to an empty list). Results are bound to a
  `SimpleNamespace` with the `LoadsResult` attribute names so the existing
  curve-extraction and plotting code is unchanged. The page stops only when
  **all four** channels are empty.
- **(b) Deleted the five dead write-backs.** Removed the
  `if project.loads is not None:` guarded writes (and their stale "Persist so the
  sbeam … export can reuse it" comments) from `fuselage_loads.py`,
  `tail_loads.py`, `aileron_loads.py`, `flap_loads.py`, `tab_loads.py`. Fixed the
  one remaining `project.loads.tail_chordwise`-referencing comment in
  `tail_loads.py`.

**Test / Acceptance.** GUI-only (no calc change); full suite green (422 passing,
`ruff` clean). Verified the recompute against both shipped fixtures:
`ga6_normal` → wing 3 / tail 13 / control 4 (body 0 — no fuselage-mass inputs,
correctly empty); `concept_regional_jet` → wing 3 / body 4 / tail 13 /
control 4. The page now displays the same distributions the Export page ships.

**Key decisions.** Match the Export page exactly — recompute-from-inputs, never
read a persisted result slice — so the two pages can never diverge. `LoadsResult`
stays a valid schema type (the build functions still return those objects); only
the never-constructed `Project.loads` *slice* is now unused by the GUI.

---

## M1-10 — Documentation consistency sweep (docs, complete 2026-07-20)

**Objective.** Retire the review's three documentation-inconsistency findings
(D1–D3): stale reference filenames, stale currency claims, and the contradictory
Appendix-B/oracle status — plus move the approved-corrections register to a durable
home.

**Deliverables.**
- **(a) Reference filenames.** Global replace of `FAR23 loads (1).pdf` →
  `FAR23Loads_Code.pdf` and `ADA324952.pdf` → `FAR23Loads_UserGuide.pdf` across 8
  docs (`README.md`, `CLAUDE.md`, both history docs, `PROJECT_GUIDE.md`,
  `CODE_REVIEW_PROCESS.md`, `PROGRAM_SPEC.md`, `00_theory_sources.md`). Left
  verbatim in `PROJECT_REVIEW_2026-07-19.md` (the dated finding that *describes* the
  stale→correct mapping) — rewriting it would make it self-contradictory.
- **(b) Currency.** `README.md` no longer bakes `SCHEMA_VERSION 15`/`242 tests` into
  prose (points at the CI badge + `CHANGELOG.md`); the "4-phase sidebar
  (Define→Analyze→Review→Export)" nav description in `README.md`, `CLAUDE.md` (×2)
  now names the real 7 phases from `workflow.py` (`Start → Develop V-n diagram →
  Flight loads → Other loads → Landing loads → Load-case plotting → Export`).
- **(c) Appendix-B status.** New **canonical "Oracle status"** section in
  `00_theory_sources.md` (`#oracle-status`): Appendix A in-hand/oracle-locked;
  Appendix B absent from the bundled scan → twin/turboprop-only cases closure-locked;
  partial-OCR cases noted. `README.md` (which had claimed Appendix B "prints full
  loads reports" and "each module" is appendix-checked) and `PROGRAM_SPEC.md` now
  defer to it. Resolves the engine-doc casualty (`one_engine_out` no oracle; `engine`
  `23.361(a)(3)` formula-checked).
- **(d) Register move.** The approved-corrections **register of record** moved from
  `CLAUDE.md` into [`docs/20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md);
  CLAUDE.md keeps the policy + a link. `docs/00_INDEX.md`, `00_theory_sources.md` and
  `PROGRAM_SPEC.md` repoint at the register. Added the **FAA User's Guide §17.2.1**
  (post-1994 CFR text of 23.361(c)) corroboration to `engine_loads.md`.

**Test / Acceptance.** Docs-only; `ruff`/`pytest` unaffected (422 passing). No
remaining `FAR23 loads (1).pdf`/`ADA324952.pdf`, `4-phase`, `SCHEMA_VERSION 15`, or
`242 tests` outside the two intentional description lines.

**Key decisions.** Single canonical oracle-status statement lives in the theory doc;
all other docs link rather than restate. Historical review artifacts that describe a
now-fixed defect are left intact.

---

## M1-9 — FLAPLOAD slipstream power: takeoff HP (fix, complete 2026-07-20)

**Objective.** `flap._engine_power` preferred `max_cont_hp` (`max_cont_hp or
takeoff_hp`) for the flap slipstream MAXHP; FAR 23.457(b) sizes the slipstream on
**takeoff power**. Flip the preference to `takeoff_hp`. (Review finding, was
backlog item 2-15.)

**Verification.** Both authoritative sources quote takeoff power — Ref 1 p109 and
the FAA User's Guide p14-2. The sole ambiguity is `FLAPLOAD.BAS`'s "MAX HP OF ONE
ENGINE" input prompt, which does not distinguish the rating; the surrounding text
in both PDFs resolves it to takeoff power.

**Resolution.** `flap._engine_power` now reads `takeoff_hp or max_cont_hp` (was
`max_cont_hp or takeoff_hp`), falling back to max-continuous only when takeoff
power is unset. The Appendix A "Critical Flap Loads" oracle (`tests/test_flap.py`)
calls `flap_loads(..., maxhp=250.0)` directly and is unaffected by the selection
order — the manual's 250 hp is a **stale figure** (user-confirmed 2026-07-20) that
matches neither the GA6 example's `takeoff_hp=285` nor `max_cont_hp=265`; the
oracle tolerance test remains the authority for the slipstream math, and the
example pipeline now feeds takeoff power (285) as 23.457(b) requires.

**Deliverables.** `farloads/modules/flap.py` `_engine_power` preference flip +
docstring citing 23.457(b); `docs/10_standard/PROGRAM_SPEC.md` (FLAPLOAD Reads
line) and `docs/20_theory/00_theory_sources.md` (FLAPLOAD row) note MAXHP = takeoff
power; `CHANGELOG.md`.

**Test / Acceptance.** `tests/test_flap.py` (5 tests) green — Appendix A oracle
unchanged.

**Key decisions.** 250 hp is a stale manual figure, not reconciled to the example
engine data; the tolerance-based oracle stays the math authority (per project
Decision 3). A separate single-source concern — `WeightEstimationInput.max_continuous_hp`
duplicating `sum(engines[].max_cont_hp)` — is **out of scope** here and left for the
G6-series single-source cleanup (M2-6).

---

## M1-8 — AIRLOAD4 Mach threshold 0.4 vs 0.5 (verify, complete 2026-07-20)

**Objective.** Resolve whether `airloads._AIRLOAD4_MACH = 0.4` (the design-Mach
gate that auto-selects the swept/high-Mach AIRLOAD4 branch) is sourced, given the
FAA User's Guide (§9.1, §10.1) states the trigger as **0.5**. (Review finding,
was backlog item 2-14.)

**Verification.** Both authoritative sources were checked directly:
- **Ref 1** (McMaster, the primary source of truth) — Ch 12 aileron-torsion
  air-loads section states the trigger as *"AIRLOAD4.BAS for Mach >.4 or sweepback
  > 15 degrees"* (`FAR23Loads_Code.pdf`). So **0.4 is sourced.**
- **FAA User's Guide** §9.1 and §10.1 — *"If the Mach number is greater than 0.5,
  then AIRLOAD4 should/must be used"*. The **0.5** is the outlier.
- **No `.BAS` oracle** pins the value either way: AIRLOAD4 selection in the
  original suite is a human-operator choice ("should be used when…"), not a
  hardcoded `IF MN > …` — the AIRLOAD4.BAS listing carries no Mach comparison.

**Resolution.** Keep Ref 1's **0.4**. It is the higher-authority source and the
conservative gate (swept branch triggers earlier), and it is nearly moot for
output regardless — compressibility is carried upstream by FLTLOADS' Glauert `CL`,
so high Mach alone leaves the span-load shape unchanged. Per the backlog decision
rule ("if 0.4 is unsourced → 0.5, else document the conservatism"), this is the
"else" branch: **no code value change**, documentation only. The 15° sweep trigger
matches across both sources.

**Deliverables.** Source-conflict note on `_AIRLOAD4_MACH` in
`farloads/modules/airloads.py`; matching notes in `docs/20_theory/00_theory_sources.md`
(AIRLOAD4 row) and `docs/10_standard/PROGRAM_SPEC.md` (AIRLOADS §); `CHANGELOG.md`.

**Test / Acceptance.** No behavior change (constant unchanged); existing AIRLOAD4
suite (`test_airloads.py`) stays green. Documentation-only closure.

**Key decisions.** Ref 1 outranks the User's Guide on a source conflict (CLAUDE.md
source hierarchy); the conservative value is retained; a source is documented on
the constant so the discrepancy is traceable and does not re-open.

---

## M1-5 — One-engine-out 23.367(a)(2) case: safety factor 1.0 (complete, 2026-07-20)

**Objective.** Stop double-factoring the one-engine-out **VC (ultimate)** load. The
23.367(a)(2) loads are defined as ultimate, but the `ConditionResult` carried the
default SF 1.5, so the render/export layer multiplied an already-ultimate load by
1.5. (Review finding T7.)

**Regulatory basis.** 14 CFR 23.367(a) (turbopropeller; Ref 1 Ch 11 p87, verbatim
quote) prescribes two failure modes whose severity fixes both the safety factor and
the speed ceiling — VMC is the minimum control speed, and the Method allows VS/VSF
to be substituted for it:
- **(a)(1)** power failure from **fuel-flow interruption**, VMC→**VD**, loads are
  **LIMIT** → SF 1.5 (the VD case).
- **(a)(2)** **compressor-from-turbine disconnection / turbine-blade loss**,
  VMC→**VC**, loads are **ULTIMATE** → SF 1.0 (the VC case — "limit treated as
  ultimate").
- **VS** substitutes for VMC (the shared floor of both ranges) and is taken as a
  **LIMIT** design point → SF 1.5 (decided 2026-07-20 — the conservative reading;
  the VD limit case envelopes the fuel-flow load at any lower speed).

**Deliverables.**
- `one_engine_out._load_cases` returns a case-definition table of `_LoadCase`
  (new `NamedTuple`: label, far_reference, **load_class**, **safety_factor**,
  **v_lo_kt/v_hi_kt** speed range, **basis**). The SF is owned by the case definition
  (its LIMIT/ULTIMATE classification), *not* the speed; the case also carries the
  speed range it is considered over and is evaluated at the critical high end.
  `run()` carries `safety_factor` and the basis `note` onto each `ConditionResult`.
  Explicit `speeds_kt` overrides are single-speed LIMIT cases (SF 1.5).
- Doc syncs: `PROGRAM_SPEC.md` (ONENGOUT §), `docs/20_theory/00_theory_sources.md`
  (ONENGOUT row), `CHANGELOG.md`. Backlog **M4-3** extended with the turbopropeller-
  gate citation and a VSF-substitution note surfaced here.

**Test / Acceptance.** `test_safety_factors_by_failure_mode` (SF 1.0 / 1.5 / 1.5 by
case + basis note), `test_load_case_owns_sf_and_speed_range` (classification owns the
SF; the case carries its speed range and evaluates at the high end) and
`test_rendered_loads_are_ultimate_with_correct_sf` (rendered load-case rows carry
`-ULT` and `SF` 1 for VC, 1.5 for VD). Full suite green (413 passed), `ruff` clean.
Not an oracle change — no printed ONENGOUT oracle exists and the factor applies only
at the render/export boundary.

**Key decisions.** (1) The safety factor is an attribute of the **load-case
definition** — set by the regulation's LIMIT/ULTIMATE classification of the load, not
by the speed — and the same definition fixes the speed range the case is considered
over. Being a *failure* case does not by itself reduce the factor (the (a)(1)
fuel-flow failure is a failure and stays LIMIT / 1.5). Future flight-test / 14 CFR
23.302/25.302 probability-interpolated (1.0–1.5) cases slot in as new rows with their
own classification. (2) VS = limit (SF 1.5), the reported VMC-substitute floor.
(3) An SF *basis* string is carried now (`_LoadCase.basis` → the `note`); a
first-class `safety_factor_basis` field and a cross-module case-spec are deferred
until a second module needs them.

## M1-11 — Ballast station rejected when outside the fuselage extent (complete, 2026-07-20)

**Objective.** Stop `weight_envelope` from printing a nonphysical moment-balance
ballast station on synthetic over-gross concept databases (e.g. `dhc8_dash8`
forward-regardless → −112 in, forward of the nose datum). Surfaced by M1-7 and
deferred as a follow-up.

**Investigation (overturned the backlog premise).** The backlog assumed a clean
"mirror M1-7's aft direction guard for the forward points." Empirically that is
**oracle-unsafe** and mis-scoped:
- Forward-gross is already safe — its candidate set is station-filtered (≤ fwd_s),
  so its reference is always forward of the limit; it cannot produce the bug.
- Forward-regardless is selected by *weight only*, so its reference CG can land aft
  of the forward limit. On **every** database — including the GA6, whose oracle
  reference (2642 @ 72.74) sits 0.1 in aft of the reg limit 72.64 — a direction-only
  "reference aft of the limit → marker" guard would fire, destroying the 158 lb @
  71.08 oracle. The real defect is narrower: only `dhc8` produced a station outside
  the physical airplane (−112, ahead of the datum); `atr42_100` (+112) and
  `concept_regional_jet` (+64) are physical nose-ballast stations that must be kept.

**Decision (2026-07-20, user).** Guard on **"outside the fuselage extent,"** not a
direction mirror. A physical fore/aft station extent gates every computed ballast
station: an explicit `envelope.fuselage_nose_x`/`fuselage_tail_x` override, else the
Step G1 fuselage outline (`Project.geometry.fuselage` min/max section station), else
the station-0 datum with an unbounded tail (only a station *ahead of the nose* is
rejected — the graceful fallback for databases carrying no outline, as `dhc8` does).

**Deliverables.**
- `WeightEnvelopeInput` — new optional `fuselage_nose_x`/`fuselage_tail_x` (round-trip
  automatically via `io`'s generic `**dict`).
- `weight_envelope.py` — `_fuselage_extent(project, env)` helper; `add_ballast` rejects
  a computed station outside `[nose, tail]` (tail `None` ⇒ only `< nose`) with a
  `"(none — moment-balance station … {ahead of the station-N datum | outside the
  fuselage extent […]})"` marker. Module + `WeightEnvelopeInput` docstrings updated.
- PROGRAM_SPEC, theory-source row, CHANGELOG updated.

**Test / Acceptance.** GA6 p28 triple unchanged (158 @ 71.08 physical). New in
`test_weight_envelope.py`: `test_fwd_regardless_station_inside_extent_kept` and
`test_fwd_regardless_station_outside_extent_marks_none` (synthetic DB, ~580 in station,
explicit extent both sides of it), `test_fwd_regardless_negative_station_marks_none_via_datum`
(`dhc8_dash8` −112 → datum-branch marker), `test_fwd_regardless_extent_from_geometry_outline_kept`
(`concept_regional_jet` +64 inside its G1 outline [0, 1056] → kept, exercising the
outline path). Full suite 422 passing; ruff clean.

**Key decisions / notes.** (1) The direction-only mirror the backlog proposed was
rejected as oracle-unsafe (would fire on the GA6). (2) Applied with the *actually
available* extents the guard flags only `dhc8`: `atr42_100` carries no outline (datum
fallback, +112 kept) and `concept_regional_jet`'s +64 sits inside its [0, 1056]
outline. To also flag those the operator would supply their fuselage extents — the
override fields exist for exactly that. (3) The guard is centralized in `add_ballast`,
so it covers all three ballast points, complementing (not replacing) M1-7's aft
direction-degeneracy guard.

## M1-7 — Aft-gross ballast reference point (complete, 2026-07-20)

**Objective.** Stop `weight_envelope`'s aft-gross ballast case from collapsing to
0 lb whenever the full discretionary loading exceeds gross weight. The reference was
the *full* (max) loading, so `WB = gross − max_load` went negative and `_ballast`
returned `None` → 0 lb — on the twin/concept databases (`concept_regional_jet`,
`atr42_100`). Inert on the GA6 (max load 3322 < gross 3400, so the full loading is
itself the correct reference → 78 lb). (Review finding T8.)

**Regulatory / source basis.** Reference 1 Ch 3 p21-22: the aft-gross ballast
reference is "the heaviest loading not exceeding gross," the same "≤ target"
selection already used for the forward-regardless point (WTONECG/WTENV data base).

**Deliverables.**
- `weight_envelope.py` — aft-gross reference is now the heaviest forward-loading
  vertex with `weight ≤ gross_weight` (mirroring `reg_cands`). Docstring updated.
- **Degenerate-case hardening** (decided 2026-07-20, "harden all three"): all three
  ballast references emit an explicit `"(none — <reason>)"` marker row instead of
  silently dropping the structural point (empty candidate set) or, for aft-gross,
  printing a nonphysical moment-balance station when the heaviest ≤-gross loading
  already sits at/aft of the aft-CG limit (the aft-CG case is then reached with no
  ballast).
- Theory-source row + CHANGELOG updated.

**Test / Acceptance.** GA6 p28 triple unchanged (78/418/158; stations 108.4/80.27/
70.97 — the existing 6 tests stay green). New: `test_aft_gross_uses_heaviest_loading_below_gross`
(synthetic over-gross DB → 100 lb from the 1100-lb reference, not 0 from the 1500-lb
full loading), `test_aft_gross_degenerate_reference_reports_marker` and
`test_ballast_marker_rows_not_dropped` (`concept_regional_jet`). Full suite 418
passing; ruff clean.

**Key decisions.** (1) The aft-gross ballast **station** stays the exact moment
balance (~108.4); the manual's hand-rounded 103.7 (which used limit station 85.0 vs
the exact 85.107) remains a *documented* deviation and is **not** reintroduced — the
backlog's "@ 103.7" target was stale. (2) Degeneracy is reported, not hidden: a real
loading that already achieves the aft-CG extreme yields "no ballast," parallel to the
existing "already at/above target weight" guard. (3) The pre-existing forward-*
nonphysical-station behavior on synthetic concept databases (e.g. `dhc8_dash8`
forward-regardless) is out of scope — it is not introduced by this change and lives
in the oracle-validated forward paths; deferred as a follow-up (M1-11).

## M1-6 — VC/VD coefficient clamp at W/S ≥ 100 (complete, 2026-07-20)

**Objective.** Stop the FAR 23.335(a)/(b) minimum-speed coefficients Kc/Kd from
extrapolating past their tabulated range. `constants.cruise_speed_coefficient` /
`dive_ratio_coefficient` taper linearly from W/S = 20 to 100 (Kc → 28.6, Kd → 1.35)
but kept tapering *below* those endpoints for W/S > 100, understating VC(min)/VD(min).
Inert for GA (W/S ≈ 20) but non-conservative for the heavy-concept band this tool
targets. (Review finding T9.)

**Regulatory basis.** FAR 23.335(a)/(b) tabulate the coefficients only to a wing
loading of 100 lb/ft²; STRSPEED.BAS clamps Kc/Kd at 28.6 / 1.35 there. Above W/S = 100
the schedule is outside the certification basis, so the GA-calibrated minimum becomes
an extrapolated advisory rather than a governing floor.

**Deliverables.**
- `constants.py` — both coefficient functions clamp `wing_loading` to 100 before the
  taper (holds Kc = 28.6, Kd = 1.35 for W/S ≥ 100); docstrings updated.
- `structural_speeds.py` — the design-speeds `ConditionResult` carries an OUT-OF-BAND
  note for W/S > 100 flagging VC(min)/VD(min) as GA-extrapolated advisories and
  pointing to chosen VC/VD (warn-only, mirroring the P1-5 pattern; decided 2026-07-20).
- Docs/theory-source row + CHANGELOG updated.

**Test / Acceptance.** `test_speed_coefficients_clamp_at_wing_loading_100` (continuity
at 100; Kc/Kd held at 28.6/1.35 for W/S = 180, all categories) and
`test_out_of_band_note_above_wing_loading_100` (note present for a W/S ≈ 143 concept,
absent for the GA6). Appendix A oracle unchanged (W/S ≈ 20, below the clamp). Full
suite green (incl. the 2 new tests); ruff clean.

**Key decisions.** Above-100 policy is **clamp + warn note** (not silent clamp, not a
hard error): the clamped minimum is emitted *and* flagged, so the no-chosen-speeds
concept path degrades safely. The clamp is continuous — the taper reaches 28.6/1.35
exactly at W/S = 100 — so no boundary discontinuity is introduced.

## M1-4 — 23.427 unsymmetrical tail: restore the full candidate set (complete, 2026-07-20) **[Major]**

**Objective.** Restore SELECT.BAS's full 12-condition candidate set for the
23.427(a) unsymmetrical horizontal-tail load — specifically, stop excluding the
**unchecked** maneuvers from the search. (Review finding T6; decision D-9.)

**Problem fixed.** `select_htail_unsymmetrical` filtered `"UNCHECKED" not in
c.label` out of the candidate list (citing a "FAA CAM 3.216" rationale). That was
an undocumented, non-conservative deviation from the BASIC: `SELECT.BAS` lines
6070–6175 (Ref 1 Appendix C p440–441; PDF pp315–316) load the unchecked maneuvers
into the candidate array (`L(5)=U1CK`, `L(6)=U2CK`) and take the max over all 12
conditions, and 23.427(a) applies the unsymmetrical distribution to "the loads
prescribed in 23.421 **through** 23.425" — which spans the 23.423 unchecked case.
On the Appendix A GA6 the DN unchecked maneuver (`U2CK` = −1397.835, ref case 274
BAL A) governs over the down gust (−1292.8), so the exclusion under-predicted the
unsymmetrical load.

**Approved oracle deviation.** The Appendix A **sample output** prints the
unsymmetrical governed by GUST −C (total −1111.8, RH −646.4) — which the current
code reproduced. That printout is **inconsistent with its own Appendix C listing**
(the `FOR I=1 TO 12` search would select the larger unchecked case, not the gust);
it was produced by a **superseded SELECT.BAS revision that excluded the unchecked
cases**. The two Reference-1 tier-1 sources conflict; the listing + the CFR are
authoritative. Approved 2026-07-20. Full trace:
`reference/23_427_unsymmetrical_candidate_set.md`; register entry in `CLAUDE.md`.

**Deliverables.**
- `select.py::select_htail_unsymmetrical` searches the full candidate set (unchecked
  included); docstring documents the deviation, the sign rule (`SELECT.BAS` 6180
  `RHSIDE=.5*HTMAX*SGN(LT(HZCASE))`, which coincides with the condition's total-load
  sign for the governing cases), and the confirmed-faithful 80% clamp (6010/6020).
- The governing `CriticalCondition` carries a documented `note`; `models.py`
  `CriticalCondition` gains a `note: str = ""` field, merged into the emitted
  `ConditionResult.note` by `_critical_conditions`.
- `reference/23_427_unsymmetrical_candidate_set.md` (new) — the listing transcription
  + the inconsistency analysis + the regulation citation.
- Doc syncs: `CLAUDE.md` approved-corrections register, `PROGRAM_SPEC.md`,
  `docs/20_theory/00_theory_sources.md`, `CHANGELOG.md`.

**Test / Acceptance.** `test_htail_gust_and_unsymmetrical_match_appendix_a` asserts
the restored unsymmetrical: total **−1204.7** (RH −700.4, LH −504.3, 72%), with the
stale −1111.8 sample-output figures preserved in comments. Full suite green
(410 passed), `ruff` clean.

**Key decisions.** (1) The Appendix C listing (unchecked included) + 23.427(a)'s
"23.421 through 23.425" scope override the stale Appendix A sample output — this is
the tie-break where two tier-1 sources disagree. (2) `rh = 0.5 * total` is retained
for the RH sign because it reproduces `SGN(LT(HZCASE))` for the governing
conditions (verified vs Appendix A). (3) The 80% other-side cap is faithful to
`SELECT.BAS` 6020, not a defect.

## M1-3 — AIRLOAD4 sweep: restore the renormalization step (complete, 2026-07-19) **[Major]**

**Objective.** Restore AIRLOAD4.BAS's sweepback renormalization (the
`COL20 = COL19/CLCOL19` divide) so a swept concept wing's span load re-integrates
to the operating CL. (Review finding T4.)

**Problem fixed.** `airloads._apply_sweep` subtracted the Pope & Haney sweep term
(`(1−2y/b)·2(1−cosΛ)`) from the additive distribution but never renormalized, so
the swept span load integrated to **less** than the operating CL — measured
**recovered_cl 0.452 vs target 0.50 (−9.6%)** on the shipped flagship
`concept_regional_jet` (Λ=24°); 0.94 at Λ=20°, 0.87 at Λ=30°. Non-conservative,
and it reached the deliverables: `net_loads.build_net_loads` →
`air_load_distribution` reads the swept `cl_additive`, feeding the sbeam
FORCE/MOMENT export. The regression was unguarded because the only closure test
used the **unswept** `concept_heavy` fixture.

**Deliverables.**
- **`airloads.py`:** `_apply_sweep` replaced by `_sweep_operating(...)`, which
  applies the Pope subtraction **and** the `COL20` renormalization to the
  **combined operating** distribution (matching AIRLOAD4.BAS's `COL16 = c·kcl/(MAC·CL)`,
  so wing twist is redistributed too — not additive-only). `schrenk_distribution`
  sweeps `ccl_total` at `target_cl` (report/closure path), leaving the
  additive/basic split as the unswept decomposition; `air_load_distribution` sweeps
  the assembled operating distribution per condition at that condition's CL
  (deliverable path). Renormalization uses the physically-correct span-load integral
  (Decision 3 "modernize the math"): the literal chord-weighted `COL16`/`CLCOL19`
  line is OCR-garbled and closes only to ~0.3% (0.4983), so the port renormalizes to
  the operating CL exactly. Documented in the `_sweep_operating` docstring.
- **Tests (`tests/test_airloads.py`):** `test_swept_closure_recovers_target_cl`
  (Λ≠0 closure on the regional-jet fixture — the guard the branch lacked);
  `test_sweep_operating_matches_basic_listing` (listing-traceable COL18/COL19/COL20
  per-station reconstruction + closure); `test_swept_deliverable_recovers_case_cl`
  (the fix reaches `build_net_loads` — each case's root shear implies its own CL).
  `tests/test_taildist.py::test_airload4_sweep_shifts_load_outboard` updated to
  assert on the swept `ccl_total` (root reduced, tip ~unchanged) + closure, since
  the additive split is now left unswept.
- **Docs:** `00_theory_sources.md` AIRLOAD4 row and `PROGRAM_SPEC.md` AIRLOAD4
  validation line record the renormalization as the method's final step and the new
  closure + listing-traceable checks; backlog M1-3 removed (M1 entry + Known-defect
  bullet); `CHANGELOG.md` `[Unreleased] → Fixed`.

**Test / Acceptance.** `ruff` (`farloads/ cli.py`) clean; full suite green (410
passed). `recovered_cl` on the flagship moves 0.452 → 0.500; the unswept GA
Appendix-A additive (`CC(LA1)` 91.05576) and the Λ=0 reduction invariant are
unchanged.

**Key decisions (with the user, 2026-07-19).** (1) **Sweep the combined operating
distribution, not additive-only** — matches AIRLOAD4.BAS (`COL16`), redistributes
twist, and is oracle-faithful (the flagship wing is twisted 3°→0°, so it changes
that deliverable). (2) **Validate with closure + a listing-traceable per-station
test** (no printed Appendix B swept oracle exists). (3) **Renormalize on the
span-load integral, not the literal chord-weighted `CLCOL19`** — the COL16 line is
OCR-garbled and the chord-weighted form closes only to ~0.3%; the span-load form
closes exactly and matches Decision 3. A documented ~0.3% normalization deviation.

---

## M1-2 — BAL 1.4VSF: balance at 1.4× the 1-g flaps-down stall (complete, 2026-07-19) **[Critical]**

**Objective.** Correct the flaps-extended envelope's `BAL 1.4VSF` condition to
balance the airplane at **1.4× the 1-g flaps-down stall (`STALL 1GL`)** speed, per
`FLTLOADS.BAS` (Code.pdf p300–302, which saves the STALL 1GL speed for this case).
(Review finding T2; was old 2-6 in part.)

**Problem fixed.** `flight_envelope._flap_config_points` captured the **STALL 2G**
speed (`v3 = add("STALL 2G", …).v_eas`) and ran `BAL 1.4VSF` at `1.4·v3`. Because
STALL 2G ≈ √2 × STALL 1G, the balance speed was ~1.4× too high and the balancing
tail load (∝ q ∝ V²) ~2.2× too large — a wrong load that fed the SELECT search and
the sbeam export. Against Appendix A p181 (LANDING CG5, case 89 `BAL 1.4VS`), the
oracle is V 83.6 kt / LT −430 lb; the defect produced ~116 kt / −957 lb. The defect
was masked because the shipped `examples/ga6_normal.project.json` carries no
`aero_coeffs.flaps_down` set, so the flaps-extended branch was dormant and the only
prior flapped test used a *synthetic* landing config (closure-checked, no oracle).

**Deliverables.**
- **`flight_envelope.py`:** `_flap_config_points` now captures the STALL 1GL
  balanced EAS (`v_1gl = add("STALL 1GL", …).v_eas`) and runs `add("BAL 1.4VSF",
  1.0, 1.4 * v_1gl, di.mc)`; STALL 2G stays a plain corner point. Docstring updated
  to state the STALL 1GL basis + the T2 history.
- **Test:** the real Appendix A p179 landing-config aero polynomials
  (`lift/drag/moment`) are transcribed into `tests/test_flight_envelope.py` as
  module-level `_LANDING`, replacing the synthetic deepcopy in `_with_landing()`
  (whose stale comment claiming the polynomials "are not in the repo" is corrected).
  New `test_bal_1p4vsf_balances_at_one_g_flaps_down_stall` asserts the exact fix
  invariant (`BAL 1.4VSF v == 1.4·STALL 1GL v`, and **not** `1.4·STALL 2G v`) plus
  the p181 case-89 oracle (V 83.6 kt / LT −430 lb / α −2.54° / CL 0.89) within print
  precision (LT is a small CG-moment residual, so it carries the widest tolerance).
- **Docs:** `00_theory_sources.md` FLTLOADS + TAILDIST rows; `PROGRAM_SPEC.md`
  FLTLOADS notes + the SELECT flaps-extended known-limit; backlog M1-2 removed and
  L-2 updated; the 0.2.0 verification-baseline "no landing polynomials in the repo"
  deferrals annotated with the M1-2 correction; `CHANGELOG.md` `[Unreleased] → Fixed`.

**Test / Acceptance.** `ruff` (`farloads/ cli.py`) clean; full suite green (407
passed) — the new p181 oracle passes; all cruise Appendix-A oracles and the
concept fixture are unchanged (the shipped example has no `flaps_down` set, so no
existing SELECT/TAILDIST/export result moved).

**Key decisions (folded into the plan, 2026-07-19).** (1) **Dedicated test
fixture, not the shipped example** — the p179 landing polynomials are injected in
the test only; `examples/ga6_normal.project.json` is left without `flaps_down`, so
the full flaps-extended SELECT→TAILDIST→export activation stays with **L-2** and
this `[Critical]` fix stays small and reviewable (mirrors M1-1). (2) **Oracle scope
= the one fixed case** (`BAL 1.4VSF`, p181 case 89); the fuller p181 landing rows
stay L-2. (3) **Uniform fix, no concept carve-out** — capturing the wrong speed was
a pure correctness bug, so FAR23 and concept both use the 1-g flaps-down stall.
(Note: the review cited the pages as p176/p178; the actual printed pages are p179
for the input listing and p181 for the LANDING CG5 block.)

---

## M1-1b — CLmax → stall-speed single-source (complete, 2026-07-19)

**Objective.** Enter the maximum lift coefficients **once** and derive the stall
speeds from them, instead of hand-entering `stall_clean_kt`/`stall_flap_kt` on the
speeds slice (closes old 2-13(b), User's Guide p7-5; split out of M1-1).

**Locked decisions (AskUserQuestion, 2026-07-19).** (1) Level B — CLmax is the
single stall-speed source across STRSPEED and the flight envelope. (2) CLmax lives
on `aero_coeffs` (not `speeds`). (3) No back-compat — remove the scalars and edit
the example files; CLmax is the input. (4) CLmax entered on the Aerodynamic Data
page, which **moves before** Structural Speeds in the workflow.

**Deliverables.**
- `AeroCoefficientsInput.clmax_clean`/`clmax_clean_neg`/`clmax_flap` — the single
  authored stall-speed source, decoupled from the polynomial sets so an airplane
  with stall data but no balance polynomials still carries its CLmax.
- `constants.stall_speed_kt(W, S, CLmax)` = `√(295·(W/S)/CLmax)`; STRSPEED derives
  VS/VSF (exposed on `DesignSpeeds.vs`/`.vsf`), `flap` and `one_engine_out` read
  them. `StructuralSpeedsInput.stall_clean_kt`/`stall_flap_kt` removed; STRSPEED
  `requires=("aero_coeffs",)`; workflow reordered (Aerodynamic Data before
  Structural Speeds). `SCHEMA_VERSION` → 29; `io.py` (de)serializes `clmax_*`;
  GUI: CLmax entered on the Aerodynamic Data page, VS/VSF read-only on Structural
  Speeds with a page link. Six example projects migrated.

**Key finding — the two stall representations cannot be a single number.** The
STRSPEED stall *speed* (simple `√(295·(W/S)/CLmax)`) and the FLTLOADS stall *CL*
(the 0.9-margin balance clamp `AeroCoeffSet.stall_cl`) are entered independently in
the manual and differ by ~0.1% (Appendix A ga6: `clmax_clean` 1.4068 from the
printed VS 62.226 vs FLTLOADS `stall_cl` 1.41). Both Appendix-A oracles are tight
enough to pin each (VA 121.3 needs 1.4068; the SELECT ACRL CL 1.328 needs 1.41), so
forcing them equal breaks one. Resolution: `clmax_*` is the stall-*speed* source;
`AeroCoeffSet.stall_cl` stays the FLTLOADS clamp, authored per config;
`AeroCoefficientsInput.__post_init__` fills either from the other only when one is
missing (never overwrites). Both round-trip in JSON.

**Test / Acceptance.** `ruff` (`farloads/ cli.py`) clean; full suite green (406);
all Appendix-A oracles preserved exactly (STRSPEED VA/VF and the FLTLOADS/SELECT
envelope); ga6 derived VS 62.228 / VSF 58.612 / VA 121.304 / VF 105.502; every
example project save→reload is a no-op.

**Key decisions.** As above — CLmax on aero_coeffs; hard-replace (no migration);
stall-speed CLmax kept distinct from the FLTLOADS clamp to preserve both oracles.

---

## M1-1 — VD floor: enforce `K_d·VCmin` (complete, 2026-07-19) **[Critical]**

**Objective.** Correct the `structural_speeds` (STRSPEED) dive-speed minimum to
enforce **both** FAR 23.335(b) floors — `VD ≥ max(K_d·VCmin, 1.25·VC)` — with the
K_d term applied to the *minimum* cruise speed VCmin, matching `STRSPEED.BAS`
(`V2DMIN=K2·V1CMIN`, lines 380/390). (Review finding T1; was old 2-13(a).)

**Problem fixed.** `design_speed_values` computed the K_d dive term as `K_d·VC` and
folded it only into a "recommended" advisory (`vd_recommended`), enforcing just the
`1.25·VC` floor. On the **no-chosen-speeds** path VD therefore collapsed to
1.25·VCmin. On the Appendix A Cat-N case (p155) the manual prints VD(min) **198.53
kt** (= K_d·VCmin = 1.40·141.8); the code returned **177.26** — 10.7% non-
conservative, propagating into MD/MACHLIM and every downstream case evaluated at VD.
The chosen-speeds worked example (p156, chosen VD 212.5, which clears both floors)
masked the defect, which is why the 0.2.0 baseline missed it.

**Locked decisions (AskUserQuestion, 2026-07-19).**
1. **Concept mode (Cat C) — advisory.** The GA-calibrated K_d term is *not*
   enforced for concept; Cat C retains only the pre-existing absolute 1.25·VC floor
   (behavior byte-for-byte unchanged), and reports K_d·VCmin as advisory. Preserves
   the "concept governs / reduces exactly to FAR23 on GA inputs" invariant.
2. **CLmax → stall-speed path (old 2-13(b)) split out** into new backlog item
   **M1-1b** at **Level B** (single-source everywhere); M1-1 lands the VD floor
   alone to keep the `[Critical]` fix small and reviewable.

**Deliverables.**
- **`structural_speeds.py`:** `vd_min = max(kd*vc_min, 1.25*vc)`; `hard_floor =
  1.25*vc` for Cat C else `vd_min`; `vd = max(chosen_vd, hard_floor)` (or the floor
  when no chosen VD). `DesignSpeeds.vd_recommended` → **`vd_min`**; reported
  `LoadValue` "Recommended dive VD (gust, K*VC)" → **"Minimum dive VD(min)"**.
  Module docstring rewritten to state the two-term floor + the Cat-C carve-out.
- **Test:** new `test_vd_floor_no_chosen_speeds` — Cat N, no chosen speeds, asserts
  VD and VD(min) = 198.53 kt (Appendix A p155, printed number + citation inline).
- **Docs:** `00_theory_sources.md` STRSPEED row (equation `VD=max(Kd·VCmin,
  1.25·VC)` + the p155/p156 distinction, replacing the Code-manual prose error);
  `PROGRAM_SPEC.md` STRSPEED notes; `CHANGELOG.md` `[Unreleased] → Fixed`.

**Test / Acceptance.** `ruff` clean; full suite green (406 passed) — the new p155
oracle passes, the p156 chosen-speeds oracle (VD 212.5) and the concept fixture are
unchanged (no regression).

**Key decisions.** As above — Cat C advisory; CLmax split to M1-1b (Level B).

---

## Phase G — Step G6b: Single-source landing-gear geometry (complete, 2026-07-19)

**Objective.** Make the Geometry page the single source of truth for the landing
gear, using the parameters native to LANDLOAD (axle stations at each strut state,
tread, rolling radius, strut type — not a synthetic coarse gear station). The
three-view depicts the gear from that data, and the ground-load analysis reads it —
every value entered once. Sibling to Step G6.

**Problem fixed.** Gear geometry was entered twice, unreconciled: the coarse
`LayoutInput` `main_gear_x`/`nose_gear_x`/`track`/`gear_height` (three-view +
tip-back/overturn/clearance) and the detailed `LandingInput` axle geometry (LANDLOAD).
In `concept_regional_jet` the stations/tread agreed but the stored `gear_height`
(75 in) contradicted the axles (static Z 20 − rolling radius 14 → ground WL 6 → ~39
in) — a silent divergence.

**Locked decision (AskUserQuestion, 2026-07-19).** `gear_height` → *derive from the
axles* (ground = static axle Z − rolling radius; fully single-source), shifting the
no-oracle tip-back/overturn/clearance estimate where the old stored value disagreed.
Plus the three backlog-locked decisions: data home = `GeometryInput.landing_gear`;
analysis wiring = derive/sync (calc math untouched); scope = landing gear only.

**Forced by fixture inspection.** Only the regional jet has both homes; cessna/ga6
carry gear only in `LandingInput` and have no parametric geometry — so
`LandingGearGeometry` **stores the native axle geometry verbatim** (LANDLOAD reads
the one authoritative copy; the reactions are byte-identical).

**Deliverables.**
- **`LandingGearGeometry{main_gear, nose_gear: LandingGearInput, tread_in}`** on
  `GeometryInput.landing_gear` (`farloads/models.py`); the coarse `LayoutInput` gear
  fields retired. `SCHEMA_VERSION` 27 → 28.
- **`farloads/io.py`** — `geometry.landing_gear` (de)serialization; `landing_to_dict`
  strips the gear (written under geometry); migration of a pre-v28 file's top-level
  `landing` gear (and legacy `LayoutInput` gear) into `geometry.landing_gear`.
- **`farloads/modules/landing.py`** — `_sync_gear_from_geometry(project)` fills the
  landing slice's gear from `geometry.landing_gear` at the top of `build_landing`
  (math unchanged → LANDLOAD oracle bit-for-bit).
- **`farloads/modules/configuration.py`** — `gear_stations(layout, landing_gear)`
  derives `{main_x, nose_x, track, gear_height, ground_z}` from the native axles;
  `component_stations` and `_gear_condition` read it (ground = static axle Z −
  rolling radius).
- **`app/views/configuration_layout.py`** — a *Landing gear* form (per-leg axle
  3-states + rolling radius + strut, tread); the three-view draws the strut + wheels
  and the derived ground line. **`app/views/landing_loads.py`** — drops the gear/tread
  widgets, reads the gear read-only, keeps the non-geometry LANDLOAD inputs.

**Test / Acceptance** (`tests/test_landing_gear_geometry.py`, 4 tests; plus updated
`test_landing`/`test_configuration`/`test_io`). The gear serializes under
`geometry.landing_gear` (not the landing block); a pre-v28 top-level file migrates;
`gear_stations` derives the coarse values from the axles (ground = static Z − rolling
radius); the LANDLOAD reactions are **bit-for-bit** across a JSON round-trip. Full
suite **405 passing**; `ruff` clean (`farloads/`, `cli.py`, `app/`).

**Key decisions.** Store (not derive) the native axle geometry → LANDLOAD oracle-safe;
`gear_height` derived from the axles (single-source, shifts the no-oracle estimate);
gear synced onto `Project.landing` at calc time (mixed slice — the non-geometry
LANDLOAD params stay stored there).

---

## Phase G — Step G6: Single-source empennage & control-surface geometry (complete, 2026-07-19)

**Objective.** Make the Geometry page the single source of truth for the empennage
and its control surfaces (elevator + rudder), using the parameters native to the
analysis programs (areas, spans, stations, deflections, effectiveness — not a
synthetic hingeline/overhang). The three-view depicts the elevator/rudder from that
same data, and the tail-load analysis reads it — every value entered once. Fixes the
double-entry (h-/v-tail area/span duplicated between `LayoutInput` and the tail-load
slices) and the elevator/rudder geometry that had no GUI home (JSON-only) and was
undrawn.

**Locked decisions (AskUserQuestion, 2026-07-19).** (1) **Representation** → *fully
derived*: `Project.tail_loads`/`.vtail_loads` become properties proxying to
`GeometryInput.empennage`; removed from stored JSON (nothing stored twice). (2)
**Depiction** → *hinge line + shaded band*: the three-view draws the elevator/rudder
as the aft `Saft/S` chord band. Plus the three carried from the backlog plan: data
home = `GeometryInput.empennage`; analysis wiring = derive at the boundary (calc
untouched); scope = elevator + rudder only (ailerons/flaps/tabs later).

**Forced by fixture inspection.** 4 of 5 tail fixtures (incl. GA/Appendix A) carry
*no* parametric geometry — the tail data lives only in the analysis slices — so
`EmpennageInput` **stores the native analysis values verbatim** and the property is
an identity (bit-for-bit). Where the two old homes disagreed (regional-jet h-tail
span 278.0 analysis vs 278.4 sketch), the analysis value wins.

**Deliverables.**
- **`EmpennageInput{htail: Optional[TailLoadsInput], vtail: Optional[VTailLoadsInput]}`**
  on `GeometryInput.empennage` (`farloads/models.py`); `Project.tail_loads`/
  `.vtail_loads` are now `@property` + setter proxying to it (via `_ensure_empennage`);
  the duplicated `LayoutInput` `h_tail_area`/`h_tail_arm`/`h_tail_span_in`/`v_tail_area`/
  `v_tail_arm`/`v_tail_span_in` fields retired (kept `tail_type`, `h_tail_z`).
  `SCHEMA_VERSION` 26 → 27.
- **`farloads/io.py`** — `geometry.empennage` (de)serialization (`{htail, vtail}` via
  the existing `tail_loads_to_dict`/`vtail_loads_to_dict`); migration of a pre-v27
  file's top-level `tail_loads`/`vtail_loads` into it; top-level write removed.
- **`farloads/modules/configuration.py`** — `tail_planform(layout, empennage)`,
  `component_stations(layout, empennage)` and `_stability_condition` read the
  single-source empennage (area/span/`xt25`/`xv25`; arm derived); `tail_planform` adds
  `elevator`/`rudder` panels (aft `_hinge_fraction(Saft, S)` chord band).
- **`app/views/configuration_layout.py`** — an *Empennage & control surfaces* form
  (all native h-/v-tail + elevator/rudder fields); the Tail expander drops the
  area/span/arm widgets (arrangement only); the three-view shades the elevator/rudder.
  **`app/views/tail_loads.py`** — analysis-only: drops the semi-span/span widgets
  (now on Geometry), reads the geometry read-only.

**Test / Acceptance** (`tests/test_empennage.py`, 4 tests; plus updated
`test_configuration`/`test_io`/`test_taildist`). The property proxies to
`geometry.empennage` (set/get/clear); the slice round-trips and serializes under
`geometry.empennage` (no top-level keys); a pre-v27 top-level file migrates; the
governing SELECT horizontal-tail loads are **bit-for-bit** across a JSON round-trip
(the exact Appendix A values stay locked in `test_select.py`, which now feeds the
tail input through the property → empennage and still passes). `test_configuration`
asserts the three-view draws the elevator/rudder when the hinge areas are set. Full
suite **401 passing**; `ruff` clean (`farloads/`, `cli.py`, `app/`).

**Key decisions.** Store (not derive) the native analysis values so the mapper is an
identity → oracle-safe; analysis value authoritative where the old homes disagreed;
non-geometry tail-aero params the manual bundles (wing zero-lift IW, wing lift-slope
AW, ARW, LF) kept on `EmpennageInput` for now (the wing/fuselage read-through cleanup
is the separate Step G6c).

---

## Phase G — Step G5: Longitudinal-stability / trim plots (complete, 2026-07-19)

**Objective.** Add standard longitudinal-stability plots to the flight-loads
section to check trim and balancing tail loads across the CG range
(CG-vs-balanced-tail-load; static-margin sweep). GUI plots over existing calc — no
new load equations.

**Scope decisions (AskUserQuestion, 2026-07-19).** (1) **CG axis** → *continuous
sweep*: re-run the existing `_balance()` at ~15 interpolated CG stations across the
forward–aft range (reuses the calc, no new math) rather than plotting only the 2–4
discrete stored CG cases. (2) **Condition** → *BAL trim cases (n = 1)*: trace the
BAL A / BAL C / BAL D balanced 1-g tail loads (the true "trim" loads), one line
each. (3) **Placement** → a *new "Trim & Stability" tab* on the merged Flight
Envelope page (alongside V-n and Critical Loads), keeping all balance-derived plots
together.

**Deliverables.**
- **`flight_envelope.trim_sweep(project, *, weight_lb, zcg, xcg_stations,
  altitude_ft=0)`** (new, pure) → `List[TrimCurve]` — re-runs the FLTLOADS balance
  (`_balance`, subroutine 3900) at each CG station for BAL A/C/D at `n = 1`, holding
  weight/waterline and every other flight-loads/speeds input fixed. Adds no load
  equations, so a station coinciding with a project CG case reproduces that case's
  `build_envelope` BAL load exactly. Uses the cruise (flaps-up) coefficient set
  including the Step-G4 fuselage increment when enabled. **LIMIT** output
  (`TrimCurve.lt_lb`).
- **`flight_envelope._balance_configs(aero)`** (refactor) — the flaps-up-then-down
  coefficient list (with the G4 fuselage-moment augmentation) extracted from
  `build_envelope` and shared with `trim_sweep`, so both see identical coefficients.
  `build_envelope` behaviour is bit-for-bit unchanged.
- **`app/views/flight_envelope.py`** — a third **Trim & Stability** tab: a
  "reference loading" selector (sets the swept weight & waterline), forward/aft CG
  station bounds and a station-count slider; a *balancing tail load vs CG* Plotly
  chart (BAL A/C/D lines, with the real CG cases at that weight overlaid as open
  markers that land on the curve), a swept-value table, and — when the project
  carries a parametric layout — a *static margin vs CG* chart (`SM = NP − CG`, %MAC)
  using the Configuration module's tail-volume neutral point, with the WTENV
  forward/aft CG limits overlaid. Tail loads are marked **LIMIT** with a caption
  pointing to the ULTIMATE deliverables (Critical Loads tab / Results Review /
  exports).

**Test / Acceptance** (`tests/test_trim_sweep.py`, 5 tests). The sweep reproduces
the Appendix A `build_envelope` BAL A/C/D loads exactly at the CG1/CG2 stations
(both share 3400 lb / zcg 93, so one sweep validates both — the traceability
guarantee); the tail load rises monotonically moving aft (physical shape); the
balanced `NZ ≈ 1` at every station; the Configuration neutral point is exposed as a
sensible %MAC for a layout project and the static-margin arithmetic shrinks moving
aft; the sweep raises without a cruise coefficient set. No schema change; full suite
396 passing, `ruff` clean.

**Key decisions.** Continuous sweep (not discrete scatter) reusing `_balance`;
LIMIT display on this analysis/check tab (marked, deliverables ULTIMATE elsewhere)
consistent with the sibling V-n tab; static-margin sweep gated on the Configuration
neutral point so oracle fixtures without a parametric layout degrade to the trim
plot alone.

---

## Phase G — Step G4: Fuselage pitching-moment estimator (Munk slender-body) (complete, 2026-07-19)

**Objective.** Derive the fuselage's contribution to the airplane-less-tail
pitching-moment slope `dCm/dα` from the G1 fuselage outline and feed it into the
FLTLOADS balance, so a **concept** airplane built from a planform no longer has to
hand-fold the fuselage into the input coefficients. The FAR23 GA/twin oracles
(whose coefficients already include the fuselage) must reduce exactly.

**Scope decisions (AskUserQuestion, 2026-07-19).** (1) **Method** → *Munk
slender-body* (apparent-mass), integrating the G1 ellipse-area station table —
geometry-only, matches the reading `FuselageSection` committed to in G1. (2)
**Coupling** → *separate off-by-default field*: a new `fuselage_moment` sub-slice,
disabled by default, added to the balance only when enabled (raw stored
coefficients stay pristine; a SCHEMA bump). (3) **Terms** → *dCm/dα slope only*:
for an uncambered outline the Munk moment is a pure α-couple, so the estimator
populates only ΔM1 and leaves the zero-α free moment M0 as a user input (it
depends on wing downwash the outline can't supply).

**Deliverables.**
- **`farloads/fuselage_moment.py`** (new, pure helper) — `estimate(outline, S, mac)
  → FuselageMomentEstimate` computing `dCm/dα (per rad) = (k₂−k₁)·Vol/(S·mac)`,
  returned per degree to match M1. Section area = ellipse `π/4·w·h`; `Vol` = the
  trapezoidal integral; fineness `l/d` = length ÷ max equivalent diameter
  `√(w·h)`; `(k₂−k₁)` from the Munk prolate-spheroid table (interpolated, clamped).
  Returns `None` on insufficient geometry (< 2 stations, non-positive S/mac). The
  result is reference-point independent (volume-based) → no CG station needed.
- **`FuselageMomentInput{enabled=False, d_cm_dalpha=0.0}`** on
  `AeroCoefficientsInput.fuselage_moment` (`farloads/models.py`); serialized in
  `io.py`; `SCHEMA_VERSION` 25 → 26 (additive, older files load with no fuselage
  moment).
- **`flight_envelope.build_envelope`** — when `fuselage_moment` is enabled and
  non-zero, augments each config's M1 by ΔM1 via `dataclasses.replace` on a **local
  copy** (stored coefficients untouched); `_balance` is unchanged, so the Glauert
  `g/gmn` compressibility factor applies to the increment automatically. Disabled →
  no change.
- **`app/views/aero_coefficients.py`** — a *Fuselage pitching-moment (Munk
  slender-body)* section: shows volume / fineness / `k₂−k₁` / estimated ΔM1 from
  the Geometry outline + the Flight-Envelope wing S & MAC, with an enable checkbox
  and an overridable ΔM1 input. The main aero form's Apply now carries the
  `fuselage_moment` sub-slice through unchanged.
- **`reference/fuselage_pitching_moment.md`** — method derivation + the `(k₂−k₁)`
  table, cited to Munk (NACA TR-184), USAF DATCOM 4.2.1.1, and Perkins & Hage.

**Test / Acceptance** (`tests/test_fuselage_moment.py`, 6 tests). The estimator
matches the closed form on a known cylinder (volume, fineness, `k₂−k₁`, ΔM1) and
the interpolation table endpoints; returns `None` on insufficient geometry; a
**disabled** (or zero) fuselage moment leaves the Appendix A V-n matrix
bit-for-bit unchanged (`m_wf`/`lt`/`nz` exact); an **enabled** positive ΔM1 shifts
the balancing tail load (wiring reaches the balance); the field round-trips through
`io.save/load`. Full suite **391 passed**; `ruff` clean. Oracles unchanged.

**Key decisions.** Off-by-default is the oracle-safety mechanism (the manual's
coefficients already include the fuselage; enabling on GA inputs would
double-count). Slope-only keeps the estimate honestly geometric. Local-copy M1
augmentation (not baking into stored coefficients) keeps the raw coefficients
auditable and the fuselage term toggleable. Reduces exactly to the FAR23 core on
GA inputs (estimator disabled).

---

## Phase G — Step G3: Phase-1 page consolidation (Develop V-n diagram) (complete, 2026-07-19)

**Objective.** Collapse the *Develop V-n diagram* section from ten nav pages into
the five sub-steps 1a–1e of `03_gui_rework_plan.md` §4, so "define the airplane &
load environment" is one coherent sequence and each shared quantity is entered once.

**Scope decisions (AskUserQuestion, 2026-07-19).** (1) **Merge layout** → *tabs*:
each merged page uses `st.tabs` for its sub-pages (rather than one long scrolling
page of stacked sections). This introduces tabs as the multi-page merge convention
(previously only Aircraft Comparison used tabs). (2) **1e V-n inputs** → *keep on
1e*: the FLTLOADS balance-geometry/CG inputs (MAC, wing area, X/Z at 25% MAC,
tail-CP stations, reference Mach, altitudes) stay on the V-n page where they run;
1e is input + compute + display + SELECT, not results-only.

**Deliverables.**
- **`app/views/weight_mass.py`** (new, **1b Weight & Mass Properties**) — one page,
  four tabs: *Estimate* (WTESTIMA), *Weight, CG & Inertia* (WTONECG), *Payload
  Cases* (shared `weight.cg_cases`), *Weight / CG Envelope* (WTENV). The single
  owner of all weight/mass data (decision G-2). Each tab is a function so a
  missing-prerequisite guard `return`s instead of `st.stop()` (which would kill the
  sibling tabs); sub-page inputs moved from the sidebar into the tab body so the
  sidebar doesn't stack four forms.
- **`app/views/structural_speeds.py`** (rewritten, **1c**) — two tabs: *Design
  Speeds* (STRSPEED) + *Speed–Altitude Envelope* (MACHLIM). The Design Speeds tab
  preserves the existing `speeds.mach_limit` sub-slice on Apply.
- **`app/views/flight_envelope.py`** (rewritten, **1e**) — two tabs: *V-n diagram*
  (FLTLOADS) + *Critical Loads (SELECT)*. Balance inputs stay in the sidebar
  (shared by both tabs); the SELECT include/exclude selection persists to
  `envelope.critical.selected_case_ids` as before.
- **`app/views/aero_coefficients.py`** (**1d**) — unchanged (the reference-Mach
  input stayed on 1e per the decision, so 1d needed no move).
- **Deleted views** (folded into the tabs above): `weight_estimate.py`,
  `weight_cg_inertia.py`, `payload_cases.py`, `weight_envelope.py`, `mach_limit.py`,
  `critical_loads.py`.
- **`farloads/workflow.py`** — the ten Develop-V-n steps become five
  (`configuration_layout`, `weight_mass`, `structural_speeds`, `aero_coefficients`,
  `flight_envelope`); `FOLDED_MODULES` gains `weight_estimate`, `weight_envelope`,
  `mach_limit`, `select` (each still a registered/tested calc module without its own
  nav step — the wing_inertia precedent). `weight_onecg`/`structural_speeds`/
  `flight_envelope` are the named primary modules.
- **Cross-page copy** — warnings/captions in `one_engine_out.py`, `tail_loads.py`,
  `export_report.py`, `results_review.py`, `configuration_layout.py`, and the merged
  pages themselves updated to point at the new tab locations (the six deleted pages
  are no longer nav destinations).
- **`tests/test_views_smoke.py`** — the beyond-GA power-cap regression fixture
  repointed from the deleted `weight_estimate.py` to `weight_mass.py`.

**Test / Acceptance.** Full suite green (**385 tests**; the −5 vs. G2's 390 is purely
the six folded views leaving / one new view joining the auto-globbed smoke
parametrization). `ruff check farloads/ app/ cli.py` clean. The nav-drift guard
(`test_every_registered_module_has_a_step`) stays green via `FOLDED_MODULES`.
Functional render check (headless `AppTest`, ga6 fixture): weight_mass = 4 tabs / 12
dataframes / 2 plots; structural_speeds = 2 tabs / 1 chart; flight_envelope = 2 tabs
/ 1 V-n plot. Appendix A/B oracles unchanged (no calc touched).

**Key decisions.** G-4 phase-1 consolidation into 1a–1e; tabs as the merge
convention; balance inputs stay on 1e; keep the validation page-tags stable and
filter for them in the merged views (the G1 `wing_geometry`-tag precedent), so
`validation.py` and its tests are untouched.

---

## Phase G — Step G2: Re-sequence `workflow.py` into the analysis-flow phases (complete, 2026-07-18)

**Objective.** Reorder the GUI navigation (decision G-4) into the six analysis-flow
sections of `03_gui_rework_plan.md` §4 so page order follows how a FAR 23 analysis
is actually performed, not the historical 22-program packaging.

**Scope decisions (AskUserQuestion, 2026-07-18).** (1) **Shell pages** → *keep a
"Start" section*: the two non-analysis app-shell pages (Project Dashboard, JSON
Editor) stay in a dedicated un-numbered **Start** group above the six analysis
phases, rather than being folded into an analysis phase (§4 defines only the six
analysis phases; the shell needs a home). (2) **Label style** → *numbered + §4
names*: the six analysis phases carry a numeric prefix (`1 · Develop V-n diagram`
…`6 · Export`); Start is un-numbered to mark it as the shell.

**Deliverables.**
- **`farloads/workflow.py`** — the `PHASES` constants renamed/re-grouped to
  `START, DEVELOP_VN, FLIGHT_LOADS, OTHER_LOADS, LANDING, LOADS_PLOTTING, EXPORT`;
  every `WorkflowStep`'s `phase` reassigned and the `STEPS` tuple reordered into
  analysis-flow order. The old **Airplane**/**Envelopes & Critical Conditions**
  split dissolves — geometry, all four weight/CG pages, both speed pages, aero, and
  the V-n + SELECT pages now sit together under **Develop V-n diagram** in §4's
  1a→1e order; **Landing Loads** moves *after* the control-surface/engine **Other
  loads** group. Module docstring updated to point at `03_gui_rework_plan.md §4`.
- **`app/Home.py`** — `_PHASE_LABEL` remapped to the new phases with the
  Start-un-numbered / analysis-numbered scheme; module docstring nav diagram updated.
- **`app/views/dashboard.py`** — the left-to-right section caption updated to the
  new phase names.
- **No page bodies changed** — grouping/labels only; the per-page consolidation into
  §4's 1a–1e sub-steps is the separate Step G3.

**Test / Acceptance.** Full suite green (390 tests, unchanged count — the workflow
tests are phase-name-agnostic: they read `wf.PHASES`/`wf.by_phase()` dynamically, so
`test_keys_unique_and_phases_valid`, `test_by_phase_partitions_all_steps`, and the
nav-drift guard `test_every_registered_module_has_a_step` all validate the new
grouping automatically). `ruff check farloads/ cli.py` clean. Probe confirms the
sidebar order: Start → Develop V-n (Geometry…Critical Loads) → Flight loads →
Other loads → Landing loads → Load-case plotting → Export. Oracles untouched (no
calc change).

**Key decisions.** G-4 (genuine re-sequence, not relabel); keep a Start shell
section (7 groups); numbered analysis phases + §4 names. Page consolidation deferred
to G3 so this step is a safe metadata-only move.

---

## Phase G — Step G1: Geometry single source of truth, incl. fuselage (complete, 2026-07-18)

**Objective.** All geometry (parametric fuselage/wing/tail/gear, the WINGGEOM
lifting-surface planforms, and a new fuselage outline) is defined on **one** page;
every downstream page reads it read-only and never re-asks it. Closes the doc's
"Is geometry before weight?" decision (geometry first) and the perceived
"data-not-stored" issue (G-3): re-entry, not true loss.

**Scope decisions (AskUserQuestion, 2026-07-18).** (1) **Fuselage outline** →
*station-area table* (`FuselageSection` width/height vs. station), because it
serves both the three-view body profile and the Step G4 slender-body moment
estimator (cross-section area ≈ π/4·w·h) from one model. (2) **Slice strategy** →
*unify into one slice* (the heavier refactor): the parametric `LayoutInput`
(formerly the top-level `Project.configuration`) and the fuselage outline move onto
`GeometryInput`, alongside the unchanged `.surfaces`. (3) **Nav / guard** → *one
step, relax guard*: one **Geometry** step, the `wing_geometry` module folded via
`FOLDED_MODULES` (the existing "one step, multiple modules" mechanism).

**Deliverables.**
- **`farloads/models.py`** — `GeometryInput` gains `parametric: Optional[LayoutInput]`
  and `fuselage: Optional[FuselageOutline]` beside `surfaces`; new `FuselageSection`
  /`FuselageOutline` dataclasses + `default_fuselage_outline(parametric)` (nose →
  0.35·L max section → tapered tail cone). `Project.configuration` **removed**.
  **`SCHEMA_VERSION` 24 → 25** with a v25 migration note.
- **`farloads/io.py`** — `geometry_from_dict`/`geometry_to_dict` carry
  `parametric` + `fuselage`; `project_from_dict` folds a legacy top-level
  `"configuration"` block onto `geometry.parametric` and defaults the fuselage
  outline from the scalars; the top-level `configuration` write is dropped.
- **`farloads/modules/configuration.py`**, **`validation.py`** — read
  `project.geometry.parametric`. Oracle-locked `.surfaces` consumers (AIRLOADS,
  WINGINER, NETLOADS, …) are untouched.
- **`app/views/configuration_layout.py`** — retitled **Geometry**; the sole editor
  of the unified slice (`_set_geometry` preserves the other fields on every write).
  New **Fuselage outline** editor (station-area `data_editor`) and **Lifting-surface
  planforms** editor (WINGGEOM surface polylines, merged in from the deleted
  `wing_geometry.py`). Three-view draws the fuselage from its outline sections.
- **Downstream read-through** — `flight_envelope.py`, `tail_loads.py`,
  `wing_loads.py`, `aircraft_comparison.py` read `geometry.parametric` read-only
  (they never wrote geometry — only the Geometry page does).
- **`farloads/workflow.py`** — one `configuration_layout`/**Geometry** step
  (`produces="geometry"`); `wing_geometry` added to `FOLDED_MODULES`.
- **`app/views/wing_geometry.py` deleted** (folded onto the Geometry page).

**Test / Acceptance.** Full suite green (390 tests: +`test_default_fuselage_outline_*`
and +`test_legacy_configuration_folds_into_geometry` /
+`test_explicit_fuselage_outline_round_trip_and_not_defaulted`; the smoke suite
loses one param with the removed view). Appendix A/B oracles unchanged (fixtures
re-expressed as `geometry=GeometryInput(parametric=…)`, same outputs). Views smoke
test renders the merged Geometry page. `ruff check farloads/ cli.py` clean. Verified
`examples/concept_regional_jet` migrates (`configuration` → `geometry.parametric` +
defaulted fuselage sections) and round-trips with no top-level `configuration` key.

**Key decisions.** G-2 (one geometry page, geometry first); unify into one slice;
fuselage = station-area table (feeds G4); one nav step + fold `wing_geometry`.
G0 already consumed the schema bump's predecessor, so G1 builds on v24 → v25.

---

## Phase G — Step G0: One unit per dimension, app-wide (complete, 2026-07-18)

**Objective.** Every quantity type has exactly one display unit per system, so no page
shows the same physical dimension two ways (the pre-G0 Configuration page mixed `in`,
`ft` and `ft²`). **Canonical units (locked 2026-07-18, decision G-1):** length →
**`in`** (SI **`mm`**), area → **`ft²`** (SI **`m²`**).

**Scope decision (deviation from the planned display-only G0).** The backlog framed G0
as display-only (relabel at the widget boundary, no schema change). On review the only
offending fields (tail spans in ft, tab area in in²) are *stored* with their unit baked
into the field name and feed oracle-locked calc, so a display-only relabel would have
put an `in` label on a feet value. The user chose the **strict rename** option
(AskUserQuestion, 2026-07-18): rename the fields to canonical-unit names, store
canonical units, and bump the schema — accepting that G0 thereby overlaps G1's schema
work. Calc results are held identical by converting back to the original ft/in² inside
the calc, so the Appendix A/B oracles are untouched.

**Deliverables.**
- **`farloads/models.py`** — renamed `TailLoadsInput.airplane_length_ft` and
  `VTailLoadsInput.{airplane_length_ft, wing_span_ft, vtail_mac_ft}` → `*_in` (store
  inches); `LayoutInput.{h_tail_span_ft, v_tail_span_ft}` → `*_in`;
  `TabSpec.area_sqin` → `area_sqft`. **`SCHEMA_VERSION` 23 → 24** with a v24 migration
  note.
- **`farloads/modules/select.py`** — the `Iyy`/`IZZ` default formulas substitute
  `LF_ft = LF_in/12`, `B_ft = B_in/12`, `VMAC_ft = VMAC_in/12` so the results are
  unchanged. **`configuration.py`** — tail-planform spans read inches directly (drop
  the `×12`). **`tab.py`** — `STAB_in = area_sqft × 144` at the call sites; the
  `LTAB = M·δ·Q·STAB/144` math is unchanged.
- **`farloads/units.py`** — removed the redundant `length_ft` and `area_sqin` kinds
  from `SI_PER_IMPERIAL`, `UNIT_LABELS` and `_KIND_FACTORS`; `_PROJECT_FIELD_KIND` maps
  the renamed keys to `length_in`/`area_sqft`.
- **`farloads/io.py`** — `_rename_legacy_units` migrates old files on load (feet keys
  `×12` → `*_in`, `area_sqin` `/144` → `area_sqft`), wired into
  `tail_loads_from_dict`, `vtail_loads_from_dict`, `configuration_from_dict`,
  `tab_loads_from_dict`. The new key wins if both are present (no double-conversion).
- **Views** — `configuration_layout.py` (spans as `length`/inches), `tail_loads.py`
  (span defaults read inches), `tab_loads.py` (area column as `area_sqft`).
- The bundled `examples/*.json` (older schema versions) are left to migrate via the
  load path rather than rewritten, matching existing practice.

**Test / Acceptance.** Full suite green (387 tests: +`test_one_display_unit_per_dimension`
in `test_units.py`, +`test_legacy_ft_sqin_keys_migrate_to_canonical` in `test_io.py`).
Appendix A/B oracles unchanged (`test_select`, `test_balloads`, `test_tab`,
`test_configuration` fixtures re-expressed in the new units, same asserted outputs).
`ruff check farloads/ cli.py` clean. Verified `examples/ga6_normal` and
`examples/concept_regional_jet` migrate and round-trip to the expected canonical values.

**Key decisions.** G-1 (one unit per dimension; length `in`, area `ft²`); strict rename
over display-only relabel (user, 2026-07-18) — calc-result-preserving, oracle-locked.

## Phase 1 — Step P1-5: Concept engine gyroscopic rates — guard + warn (complete, 2026-07-16)

**Objective.** `engine.py`'s `condition_25_371` (the optional FAR 25 gyroscopic
concept case) uses a fixed FAR 23.371(b) stand-in (2.5 rad/s yaw, 1 rad/s pitch) in
lieu of the maneuver-derived 25.371 rates the tool does not solve. The gyro moment is
linear in body rate, so the stand-in is conservative *only while the concept's real
rates stay at or below it* — for an agile concept it under-predicts silently. Add a
guard so the non-conservative case cannot pass silently, per decision **D-2 (guard +
warn, keep the fixed stand-in)**.

**Deliverables.**
- **`farloads/models.py`** — `EngineInput` gains two optional advisory fields,
  `design_yaw_rate_rad_s` / `design_pitch_rate_rad_s` (default `None`), the concept's
  real 25.371 body rates if known. `SCHEMA_VERSION` **22 → 23** (additive; older files
  load with both unset → no guard, fixed stand-in unchanged). No `io.py` change needed
  — `engine_from_dict`/`engine_to_dict` use `**d`/`asdict`, so the fields round-trip
  automatically; `units.to_imperial` uses `replace`, and rad/s are system-independent
  (like RPM), so they pass through both unit systems unchanged.
- **`farloads/modules/engine.py`** — `condition_25_371` keeps computing Myy/Mzz at the
  **fixed** stand-in rates (the moment never changes — advisory rates, not a
  re-derivation). When a declared rate exceeds its stand-in, the `ConditionResult.note`
  is replaced with a `WARNING -- gyroscopic loads UNDER-PREDICTED …` message naming the
  offending axis, the rate, and the moment ratio (`Myy x1.40`), pointing the engineer
  to scale by the ratio or solve the real 25.371 rates.
- **`app/views/engine_mount.py`** — two advisory rate inputs under the FAR 25 block
  (0 = leave unset), wired into the `EngineInput`; the per-condition note now renders as
  `st.warning` (not `st.info`) when it starts with `WARNING`, so the under-prediction
  case is visually flagged.
- **`tests/test_engine_far25.py`** — five tests: no-rates → no warning + stand-in note;
  rates at/below stand-in → no warning, moment unchanged; yaw > 2.5 and pitch > 1.0 →
  `WARNING`/`UNDER-PRED` note with the moment value **identical** to the fixed
  stand-in; and a JSON round-trip of the new fields (schema v23) that re-fires the
  warning through `calc.run`.

**Test / Acceptance (met).** A concept declaring a rate above the stand-in produces a
load result carrying an explicit under-prediction warning while the reported moment is
unchanged; the GA/light path (no declared rates) is untouched — no warning, oracle
intact. Full suite **385 passed** (379 → 385), `ruff check farloads/ cli.py` clean, the
edited view compiles.

**Key decisions.** **Warn-only, keep the fixed value** (D-2 literal / the acceptance's
"under-prediction warning" wording) — the declared rates are *advisory*, driving only
the guard, not the moment (the "solve for real rates" re-derivation stays deferred). The
override lives on `EngineInput` (per-engine, local to the case that uses it) rather than a
global concept slice. **Phase 1 is now complete** (P1-1…P1-5 all shipped).

## Phase 1 — Step P1-4: Complete the export package public API (complete, 2026-07-16)

**Objective.** The concept deliverable is "all components to sbeam", but
`farloads/export/__init__.py`'s `__all__` advertised only the **wing + tail**
families — `body_span_load_csv`, `body_force_moment_cards`, `control_surface_csv`,
`control_surface_force_moment_cards`, their `write_*` variants, and
`case_index_csv`/`filter_by_selected_case_ids` were reachable only via the
`sbeam_bridge` submodule. Re-export the missing surface and rewrite the wing-only
package docstring to describe all four component families + the case index.

**Deliverables.**
- **`farloads/export/__init__.py`** — imports and `__all__` extended with the body
  family (`body_span_load_csv`, `body_force_moment_cards`), the control-surface
  family (`control_surface_csv`/`control_surface_force_moment_cards` + their
  `write_*` variants), and the case-index family (`case_index_csv`,
  `write_case_index_csv`, `filter_by_selected_case_ids`). `__all__` is now grouped
  by component family (Wing / Body / Tail / Control / Case index). The module
  docstring is rewritten from "wing-only" to enumerate all four families plus the
  case index. (Body has no `write_*` CSV/card variants in `sbeam_bridge`, so none
  were invented; the case-index `write_case_index_csv` companion is included to keep
  the family's public surface complete.)
- **`tests/test_sbeam_bridge.py`** — `test_export_package_exposes_all_component_families`
  imports the full body/control/case-index surface directly `from farloads.export`,
  and asserts each re-exported name is in `export.__all__` and resolves (identity) to
  the `sbeam_bridge` implementation (no accidental shadowing).

**Test / Acceptance (met).** `from farloads.export import body_force_moment_cards,
control_surface_force_moment_cards` (and the rest of the surface) now works; the new
test imports the full surface. Full suite **379 passed** (378 → 379), `ruff check
farloads/ cli.py` clean. **API-surface-only step:** no calc-math change, no new
function, no `SCHEMA_VERSION` bump — only which names the package re-exports.

**Key decisions.** Re-export only functions that already exist (no new `write_body_*`
variants were invented, since the body family never had them); include
`write_case_index_csv` alongside `case_index_csv` so every CSV/cards producer that is
re-exported carries its `write_*` companion.

## Phase 1 — Step P1-3: True concept↔FAR23 identity test (complete, 2026-07-16)

**Objective.** The C-1 invariant ("concept mode reduces **exactly** to FAR23 on GA
inputs") was only *assumed* — guarded indirectly by the absence of regression on the
GA Appendix-A oracles, never verified *through the concept branch itself*. Add a
direct identity test: take a GA project, flip it to `category="C"` with the
FAR23-computed load factors, run the whole pipeline through the concept code path,
and assert the per-component loads reproduce the FAR23 result.

**Deliverables.**
- **`tests/test_concept.py`** — two tests + a comparison helper on
  `examples/ga6_normal.project.json` (Normal category, MTOW 3400 lb):
  - `test_concept_load_factors_match_far23_caps` pins the single numeric divergence
    point (`structural_speeds._maneuver_load_factors`): the FAR23 Normal cap
    (n = 3.8, nneg = −0.4·3.8 = −1.52 per 14 CFR 23.337), fed back as explicit
    `chosen_n`/`chosen_nneg` in concept mode, is echoed verbatim.
  - `test_concept_reduces_to_far23_on_ga_inputs` runs `run_all_modules` twice —
    baseline (`category="N"`) and concept (`category="C"` with the *derived* FAR23
    load factors) — and asserts full-pipeline parity: `_assert_modules_identical`
    compares by module name → condition `(title, far_reference)` → `LoadValue` label,
    checking equal `units`, `safety_factor`, and `value` (`math.isclose(rel_tol=1e-3)`,
    exact for dimensionless/int). `ConditionResult.note` is deliberately ignored — the
    appended concept note is the *only* permitted difference.
  - The file docstring is updated to record that the invariant is now guarded
    directly (not only via the oracle tests). Load factors are *derived* from the
    baseline STRSPEED result and fed forward (with a `3.8 / −1.52` citation assert),
    so the test stays robust if the fixture changes.

**Test / Acceptance (met).** GA-as-concept run reproduces the FAR23 loads to
`rel_tol=1e-3` across every module `run_all_modules` produces; the sweep fails if any
concept branch diverges numerically on GA inputs. Full suite **378 passed** (376 →
378), `ruff check farloads/ cli.py` clean. **Test-only step:** no calc-math change, no
new module, no `SCHEMA_VERSION` bump. (Removed one pre-existing unused import
(`StructuralSpeedsInput`) from the touched test file.)

**Key decisions.** Test lives in `test_concept.py` (extended, not a new file) —
concept tests stay together. Assertion breadth is the **full-pipeline sweep** (every
`LoadValue` of every module) rather than a few representative modules, since the whole
point is guarding *any* concept branch. N-factors are **derived from the baseline**
rather than hardcoded. Confirmed by investigation that
`_maneuver_load_factors` is the sole numeric concept↔FAR23 branch; every other
`is_concept` branch is note-text only — so the sweep's note exclusion is exactly the
permitted-difference boundary.

## Phase 1 — Step P1-2: Concept distributed-loads end-to-end + closure suite (complete, 2026-07-16)

**Objective.** Concept mode has no printed oracle above 12,500 lb, so physics
*closure* is its only validation — yet before P1-2 the only concept closure test
(`test_sbeam_bridge.py::test_concept_closure`) covered the **wing alone**. Drive
`net_loads`, `body_loads`, `taildist`, `aileron`, `flap`, `tab` through the P1-1
concept fixture and assert closure for every component, so concept results for the
tail/body/control surfaces stop being unverified.

**Deliverables.**
- **`tests/test_concept_closure.py`** (10 tests) on
  `examples/concept_regional_jet.project.json`, with its envelope + SELECT critical
  set materialised. Three kinds of check:
  - **Physics closure** (equilibrium identities evaluated through the concept code
    path, so a concept blow-up can't pass silently): wing
    `LZW + LT = Nz·W` (FLTLOADS vertical equilibrium) over all 120 V-n points; tail
    `LT·(Xt−Xcg) = LZW·(Xcg−Xw) − DX·(Zcg−Zw) + M(W+F)` (balancing load reacts the
    pitching moment about the CG); body terminal cumulative shear `= 0` (the
    fuselage net distribution is built free-free from inertia + tail air load + wing
    reaction).
  - **Cross-module ties** (per the chosen closure-depth decision): TAILDIST carries
    SELECT's `lt25`/`lt50` split verbatim (exact field equality across all 13 tail
    conditions — chosen over label-matching the "Total tail load" `LoadValue`, which
    diverges for the UNSYMMETRICAL and v-tail conditions); each control surface's
    `build_*` critical load matches a `lb`-unit `LoadValue` in that module's `run`
    analysis report (the distributed and analysis paths agree on the concept
    airframe).
  - **Export integrity**: every component family's nodal FORCE set — and its
    re-parsed `FORCE` cards (via the shared free-field reader imported from
    `test_sbeam_bridge`) — sums to that component's root/total at ULTIMATE
    (`limit × 1.5`); `test_full_airframe_exports_cleanly` is the P1-2 acceptance —
    wing + body + tail + control all export cleanly through `sbeam_bridge`.

**Test / Acceptance (met).** All closure identities hold to machine precision
(wing/tail rel ≈ 1e-16, body terminal shear ≈ 1e-12 lb) on the concept fixture;
the whole component set exports parseable, self-consistent decks. Full suite **376
passed** (366 → 376), `ruff` clean. **Test-only step:** no calc-math change, no new
module, no `SCHEMA_VERSION` bump — the FAR23 oracles are untouched.

**Key decisions.** Closure tests live in one dedicated `test_concept_closure.py`
(not scattered per-module); closure depth is nodal-sum + export integrity **plus
cross-module ties** (SELECT→TAILDIST field equality, control build↔run agreement),
not an independent physics re-derivation of tail balancing / control hinge moments.
The wing `Nz·W` and tail-moment identities re-use the FLTLOADS equilibrium formulas
deliberately — their value is asserting the concept branch stays balanced, not
re-deriving the aero.

## Phase 1 — Step P1-1: Full-airframe concept reference fixture (complete, 2026-07-16)

**Objective.** Concept mode (`category="C"`) was broadly wired into calc but its
headline deliverable — per-component distributed loads for a beyond-FAR23 airframe —
was only ever demonstrated for the *wing*. The one concept fixture
(`concept_heavy.project.json`) defined a wing surface only; run through
`run_all_modules` it fired 7 modules and skipped `net_loads`, `body_loads`,
`taildist`, `aileron`/`flap`/`tab`. P1-1 builds the full-airframe concept example so
the whole pipeline can be validated (closure checks are the follow-on Step P1-2).

**Deliverables.**
- **`examples/concept_regional_jet.project.json`** — "RJ-50 concept": a swept-wing,
  high-subsonic twin-turbofan regional jet (MTOW 33,000 lb, S 500 ft², b 66 ft,
  AR 8.7, c/4 sweep 24°, cruise M 0.74, 50 seats), `category="C"` with Part 25
  maneuver load factors (`chosen_n=2.5`, `chosen_nneg=-1.0`, `include_far25=true`).
  Carries every input slice — including the two no GA fixture had: `fuselage_mass`
  (body longitudinal mass stations) and `configuration` (`LayoutInput`). Drives
  **all 19** applicable modules with no missing-slice skip and selects the swept
  `AIRLOAD4` branch. Airplane chosen per **decision D-1** (2026-07-16); the twin
  turbofan is modelled with an empty propeller + a fan-spool `Rotor` (gyroscopic
  case via the 25.371 path, per **D-2**).
- **`farloads/io.py`** — bug fix: `_aero_surface_from_dict` / `aero_to_dict` now
  serialize `sweep_deg` and `design_mach`. These `AeroSurfaceInput` fields were
  added in Step C7 but never wired into the JSON round-trip; no GA fixture set them,
  so the gap was invisible until this swept concept fixture. Additive and defaulted
  (0.0), so every existing project loads unchanged and no oracle moves.
- **`tests/test_concept_regional_jet.py`** — 4 tests: fixture is concept + Part 25
  load factors; all required component modules run; AIRLOAD4 swept branch selected;
  `sweep_deg`/`design_mach` round-trip through `io` (the regression guard for the
  fix above).

**Test / Acceptance (met).** `run_all_modules` on the fixture reaches wing, body,
tail and all three control-surface modules without a `ValueError`; `airloads`
selects the AIRLOAD4 swept branch; the project round-trips through `io.py`. Full
suite **366 passed**, `ruff` clean. No FAR23 oracle change (concept path only; the
io fix is additive with GA-preserving defaults).

**Key decisions.** D-1 (regional-jet archetype), D-2 (fan-spool rotor for the
turbofan gyro case). **Accepted limitation:** the suite's `EngineLayout` has no
aft-fuselage option, so the aft-mounted twin is encoded as `2W` (symmetric mirror
butt lines) — a layout-sketch limitation, not a structural one; noted in the
backlog for a possible future `EngineLayout` addition.

## Phase F — Step F2: Aircraft Comparison page (complete, 2026-07-16)

**Objective.** Give the fleet comparison a first-class home. Before F2 the
comparison was bolted onto two *input* pages (Configuration & Layout, Weight
Estimate) via one shared helper, showing the same scatters twice with split subject
metrics and no single "how does this airplane compare?" view. F2 consolidates it
onto one dedicated **Aircraft Comparison** page in the Export phase and adds the
geometric plots the F1 data enables. Input-assessment only — no calc-math, no oracle
change; the reference set never enters a FAR computation.

**Deliverables.**
- **`app/views/aircraft_comparison.py`** — new GUI-only page (Export phase, before
  Results Review). Assembles the comparison subject from the best-available slices
  (`_subject_from_project`: MTOW ← speeds/direct-weight/WTESTIMA; OEW ← direct/
  WTESTIMA; area ← configuration/speeds; power ← Σ engines/estimation; AR ←
  configuration; seats ← speeds/estimation), showing a clear "—" when a metric is
  absent rather than dropping the subject. Renders the quantitative readout (nearest-3,
  W/S & W/P percentile band, outliers), a **parameter table** (subject on top + the
  nearest-N over MTOW/OEW/power/W-S/W-P/wingspan/area/AR/seats), **six scatter tabs**
  (W/S-vs-W/P, MTOW-vs-OEW, wingspan/area/AR/seats-vs-MTOW), and the reference-fleet
  expander. Owns its own `_REFERENCE_CSV` + `_fleet_points`.
- **`farloads/fleet.py`** — `Subject` gains presentation-only `wingspan_ft`,
  `aspect_ratio`, `seats` fields plus `span` (= `wingspan_ft`, else `√(AR·S)`) and
  `aspect_ratio_effective` (= `aspect_ratio`, else `span²/S`) derivations; the same
  two derivations added to `FleetPoint` for uniform handling. `fleet_stats` is
  untouched — geometry is never a distance term.
- **`farloads/workflow.py`** — new
  `WorkflowStep("aircraft_comparison", "Aircraft Comparison", EXPORT, module=None, …)`
  positioned immediately before `results_review`.
- **`app/views/configuration_layout.py` / `app/views/weight_estimate.py`** — the
  fleet block and its subject-metric assembly removed; the `render_fleet_comparison`
  imports dropped.
- **`app/components.py`** — `render_fleet_comparison`, `_fleet_readout`,
  `_fleet_points` and `_REFERENCE_CSV` deleted (no remaining callers); the module now
  holds only the FAR 23 applicability banner. Imports trimmed.
- **`tests/`** — new `test_aircraft_comparison.py` (subject assembly from an example
  project, the geometric-axis path from a synthetic project, and `None` without
  MTOW); `test_fleet_compare.py` extended with span/AR derivation tests and a
  distance-invariance test proving geometry adds no distance term.

**Test / Acceptance.** `ruff check farloads/ cli.py app/` clean; full `pytest` suite
passes (362, +15 over F1's 354). `test_workflow` still passes (GUI-only steps exempt
from the module↔step coverage assertion); the auto-discovered view smoke test runs
the new page without exception; `grep` confirms no remaining `render_fleet_comparison`
reference.

**Key decisions (locked with user, 2026-07-16).** **D-F2-a** — the nearest-N
similarity distance stays on MTOW / W/S / W/P; the new geometry is presentation-only
(table columns + plot axes), so the `fleet_stats` oracle is byte-identical.
**D-F2-b** — six tabs, one plot each (not a grid). **D-F2-c** — no category coloring
/ no `category` CSV column in F2 (kept as an Open question). The larger
comparator-set curation and in-UI user-supplied comparators remain **open questions
on Phase F** in the backlog.

---

## Phase F — Step F1: Reference-fleet expansion (complete, 2026-07-16)

**Objective.** Groundwork for the proposed Aircraft Comparison page (Phase F, see
`../30_future/00_backlog.md`): grow and enrich the reference-fleet data set so the
new page's geometric plots (span / area / aspect-ratio vs. MTOW) and parameter
table have the columns and spread they need. Data-only step — no calc-math, no
oracle change; the reference set never enters a FAR computation.

**Deliverables.**
- **`app/data/reference_aircraft.csv`** — new `aspect_ratio` column on every row
  (span²/area from the same row, so the geometric plots and the loading scatters
  stay consistent). Six aircraft added to broaden the geometric spread —
  Piper PA-28-181 Archer, Cirrus SR22, Diamond DA40, Extra 300 (low-AR aerobatic
  endpoint), Piper PA-44 Seminole (light twin), Daher TBM 940 (fast single
  turboprop) — 23 → 29 aircraft. Header comment updated (page reference + the
  aspect-ratio provenance note).
- **`farloads/fleet.py`** — `FleetPoint` gains optional `seats`, `wingspan_ft` and
  `aspect_ratio` fields (defaults, so `fleet_stats` and older callers are
  unaffected — the loading placement still runs on MTOW / W/S / W/P only).
- **`app/components.py`** — `_fleet_points` now maps the three new fields onto
  `FleetPoint`, tolerating a missing/NaN cell (an `_opt` helper) so a partially
  populated row still loads.
- **`tests/test_reference_aircraft.py`** — `aspect_ratio` added to the required
  columns; new `test_aspect_ratio_consistent_with_geometry` (positive and within
  5% of span²/area); the four added aircraft asserted present.

**Test / Acceptance.** `ruff check farloads/ cli.py` clean; full `pytest` suite
passes (354). The CSV round-trips through `_fleet_points` with all 29 rows carrying
the new geometry.

**Key decisions.** `aspect_ratio` is **stored** (not derived at plot time) so the
geometric plots need no computation and can honour a published AR that differs from
naïve span²/area for a cranked/tapered reference wing; the F1 rows use the
consistent span²/area value. The larger comparator-set curation (specific
concept-tier types, extra columns like `cruise_kt` / a `category` tag) and in-UI
user-supplied comparators remain **open questions on Phase F** in the backlog,
pending user direction; F1 ships the unambiguous column + a confident GA→turboprop
spread.

---

## Phase E — Step E7: Speed–altitude envelope consolidation (complete, 2026-07-16)

**Objective.** Remove the input redundancy between **Structural Speeds** and **Mach
Limit**, and upgrade the Mach-limit chart into a transport-category-style
speed–altitude flight-limits diagram (altitude on y, selectable KEAS/KCAS/KTAS on
x, constant-Mach fan + the composite design-speed boundary). No calc-math or oracle
change — `mach_limit_lines` is untouched; the airspeed conversions are a new
presentation-layer helper.

**Deliverables.**
- **`farloads/constants.py`** — new `convert_airspeed(eas_kt, altitude_ft, unit)`
  (KEAS/KTAS/KCAS), plus `eas_to_mach`/`mach_to_eas` and `SEA_LEVEL_SOUND_KT`. KTAS =
  KEAS/√σ; KCAS via the standard subsonic compressible impact-pressure relation
  (`qc/P0 = δ·((1+0.2M²)^3.5−1)`, `δ = σ·(a/a0)²`), exact at sea level. Pure calc,
  no I/O.
- **`app/views/mach_limit.py`** — retitled **Speed–Altitude Envelope**. MC, MD and
  the shoulder altitude are now READ from the `speeds` slice
  (`design_speed_values`) instead of re-entered — only the max operating altitude
  and increment remain as inputs (same unused-upstream-data fix class as Config &
  Layout). The old V-vs-altitude chart is replaced by a speed–altitude diagram:
  altitude on y; a **KEAS/KCAS/KTAS** radio for the x-axis; a thin constant-Mach
  fan; and the operating boundary drawn as EAS-limited (constant) below the shoulder
  and Mach-limited (V=M·a·√σ) above it, so VC/MC and VD/MD kink at the shoulder
  exactly like a placard chart. `use_container_width` replaced by `width="stretch"`.
- **`farloads/workflow.py`** — the `mach_limit` step is retitled "Speed–Altitude
  Envelope" with an updated summary (module name unchanged, so the CLI/oracle path
  and the every-module-has-a-step nav test are unaffected).
- **`tests/test_airspeed_conversions.py`** — new: sea-level unit equality,
  KTAS = KEAS/√σ, EAS < CAS < TAS at altitude, Mach round-trip, unknown-unit error.
- **Docs** — `PROGRAM_SPEC.md` MACHLIM notes and `docs/20_theory/00_theory_sources.md`
  updated; `cspell.json` gains KCAS/KTAS.

**Test / Acceptance.** `ruff check farloads/ cli.py` clean; full `pytest` suite
passes (353). Smoke-checked against `examples/ga6_normal.project.json`: the VC/MC
boundary is ~170 KEAS constant to the 12000 ft shoulder then curves in to ~151 KEAS
at 18000 ft; VA/VF are constant-EAS lines; the Mach fan and MNE/MFC lines render.

**Key decisions.** The diagram stays on its own page (following the Step E6 V-n
precedent: inputs on the owning page, picture on a dedicated page). MC/MD/shoulder
are read-only echoes of Structural Speeds; the page adds only the two quantities
Structural Speeds does not carry. All chart speeds are design *limit* speeds — the
diagram is a speed boundary, not a load deliverable, so the ULT rule does not apply.

---

## Phase E — Step E6: V-n diagram consolidation (complete, 2026-07-15)

**Objective.** Remove the redundant second V-n diagram: consolidate the two V-n
plots (the continuous LIMIT textbook envelope on **Structural Speeds**, added in
Step E3, and the rigorous Mach-corrected balanced corner points on **Flight
Envelope (V-n)**) into a single figure on the Flight Envelope page. GUI-only:
**no schema change** and **no calc-math change** — `farloads/vn_diagram.py` and its
oracle/closure tests are untouched.

**Deliverables.**
- **`app/views/flight_envelope.py`** — the continuous LIMIT design envelope
  (`build_vn_diagram` from `farloads/vn_diagram.py`) is now drawn as a grey backdrop
  behind the rigorous balanced markers, so the envelope visibly *bounds* them. It is
  rebuilt from `project.speeds` (a required slice here) via `design_speed_values` —
  no new input widgets. Gust lines (altitude-dependent, textbook Pratt) are drawn
  only for a single selected altitude; the altitude-independent maneuver envelope is
  always drawn. Backdrop build is wrapped in `try/except (ValueError,
  ZeroDivisionError)` so it degrades to the rigorous-points-only plot rather than
  erroring. The `gust_approximate` caption (missing lift-curve slope / MAC) carried
  over from Structural Speeds.
- **`app/views/structural_speeds.py`** — the Step E3 V-n block removed; the page now
  shows only its numeric design-speed tables plus a caption pointing to the Flight
  Envelope (V-n) page. Now-unused imports (`plotly.graph_objects`, `build_vn_diagram`,
  `resolve_gust_inputs`, `design_speed_values`) dropped.
- **Docs** — `docs/10_standard/GUI_design.md` §8.2/§11 updated to reflect the single
  consolidated V-n on the Flight Envelope page.

**Test / Acceptance.** `ruff check` clean (no unused imports left); full `pytest`
suite passes unchanged (347) — no calc or schema change. Manual: the Flight Envelope
V-n renders the balanced markers on the LIMIT-envelope backdrop; toggling single
altitude (gust lines shown) vs "Overlay all altitudes" (gust lines suppressed,
maneuver envelope still drawn) behaves; a project missing aero/MAC degrades
gracefully. Structural Speeds shows no diagram, only tables + pointer.

**Key decisions.** The two diagrams were *complementary*, not literal duplicates
(continuous textbook envelope vs discrete rigorous points), but share LIMIT
load-factor-vs-KEAS axes — so they were overlaid rather than one simply deleted
(user choice), keeping the classic envelope shape as a bound on the rigorous points.
This supersedes the Step E3 "V-n lives on Structural Speeds only" decision.

---

## Phase E — Step E5: Load-path robustness (complete, 2026-07-15)

**Objective.** Make the sidebar project load fail gracefully and be schema-aware.
GUI-only: **no schema change** (`SCHEMA_VERSION` stays 22) and **no calc-math
change** — the Appendix A/B oracles pass unmodified.

**Deliverables.**
- **`farloads/io.py`** — a new pure, unit-tested `schema_status(version) ->
  (status, message)` helper (no Streamlit): classifies an on-disk
  `schema_version` as `"ok"` / `"newer"` (loads anyway; unrecognized fields
  ignored) / `"older"` (its field-presence migration already ran in
  `project_from_dict`; the caller bumps the stamp to `SCHEMA_VERSION`).
- **`app/Home.py`** — a `_safe_load(build, source) -> Project | None` wrapper
  around all three sidebar load actions (Open saved, Load example, Upload) that
  catches `(json.JSONDecodeError, OSError, TypeError, ValueError, KeyError,
  AttributeError)` and shows `st.error("Couldn't load …: …")` instead of an
  uncaught traceback, returning `None` so the load is skipped. On success it runs
  `_apply_schema_check`: a newer file toasts a ⚠️ warning, an older file is
  migrated in place and toasts a 🔁 notice. Toasts (not `st.warning`) because the
  adopt path ends in `st.rerun()`, which would discard an ordinary message.
- **`app/views/project_editor.py`** — the same schema check wired into **Apply**
  after the existing graceful `project_from_dict` guard (this page does not rerun
  before render, so it surfaces `st.warning` / `st.info` inline rather than a
  toast).
- **Tests** — `tests/test_io.py` (+4): `schema_status` for older/current/newer and
  a malformed-dict guard asserting `project_from_dict` raises one of the caught
  types (the contract `_safe_load` relies on to show `st.error`).

**Test / Acceptance.** Full suite (**347 passed**, +4) + `ruff check farloads/
cli.py app/` clean, confirming the no-calc-change invariant. A malformed /
newer-schema file shows a message, not a traceback (sidebar and editor); a valid
older file (e.g. `examples/ga6_normal.project.json`, schema 12) still loads and is
migrated. Docs synced (`GUI_design.md §10/§11`, this history + `CHANGELOG.md`,
backlog E5 removed / Phase E marked complete).

**Key decisions.** (D-E5-1) The classification is a **pure, unit-tested**
`schema_status` in `io.py` (mirroring `fleet.py` / `applicability.py`), exceeding
the backlog's manual-only acceptance so the version logic is regression-safe.
(D-E5-2) The schema check is **shared into both** the sidebar and the JSON Editor
(user-approved 2026-07-15), not sidebar-only, so behavior is consistent wherever a
project is built from raw JSON. (D-E5-3) An older file is **migrated with a visible
toast** ("Migrated from schema N to 22"), not silently — nothing is written to disk
until the user Saves. A newer file **warns and still loads** rather than blocking,
per the backlog direction.

---

## Phase E — Step E4: Fleet comparison upgrade (complete, 2026-07-15)

**Objective.** Turn the visual, duplicated fleet comparison into a shared,
quantitative one. GUI-only in effect: **no schema change** (`SCHEMA_VERSION` stays
22) and **no calc-math change** — the Appendix A/B oracles pass unmodified; the new
`fleet.py` is an additive pure helper.

**Deliverables.**
- **`farloads/fleet.py`** — a pure, unit-tested placement helper (no pandas / file
  access / Streamlit): `FleetPoint` / `Subject` records (with derived `w_s`/`w_p`,
  `w_p = None` for a jet), `fleet_stats(subject, fleet, *, n=3, band=(10, 90))
  -> FleetStats`, and `percentile_rank` / `percentile` helpers. Nearest-N uses a
  normalized-Euclidean distance over whichever metrics the subject supplies (always
  `log10(MTOW)`, plus W/S and W/P when known), each divided by the fleet spread so
  the axes are commensurate; a fleet point missing an axis (a jet's W/P) simply
  drops that term. Percentile rank + p10–p90 outlier band on the subject's W/S and
  W/P.
- **`app/components.render_fleet_comparison(project, *, name, mtow, oew, wing_area,
  power)`** — the single shared presentation wrapper: loads
  `app/data/reference_aircraft.csv`, builds the `FleetPoint`s + `Subject`, renders
  the quantitative readout (W/S & W/P percentile-band metrics, a nearest-3 table
  with distances, an outlier warning) then the W/S-vs-W/P and MTOW-vs-OEW scatters.
- **`configuration_layout.py` / `weight_estimate.py`** — the duplicated ~65-line
  fleet blocks are deleted; each page now calls `render_fleet_comparison` with the
  subject values it already computes (Configuration supplies wing area + installed
  power; Weight Estimate supplies estimated MTOW/OEW + power, no subject wing area
  → its W/S shows "—").
- **Tests** — `tests/test_fleet_compare.py` (10): nearest-N ordering/count, the
  jet-as-neighbour case, percentile rank + band, outlier firing / silence on a
  central design, the no-wing-area (Weight-Estimate) subject, the standalone
  percentile helpers, and an empty-fleet guard.

**Test / Acceptance.** Full suite (**343 passed**, +10 for the new test file) +
`ruff check farloads/ cli.py app/` clean, confirming the no-calc-change invariant;
`app/components.py` imports cleanly and exposes `render_fleet_comparison`. The
existing `tests/test_reference_aircraft.py` still guards the CSV shape. Docs synced
(`GUI_design.md §8.4/§11`, `PROJECT_GUIDE.md` package layout, this history +
`CHANGELOG.md`, backlog E4 removed).

**Key decisions.** (D-E4-1) The numeric core lives in a **pure, unit-tested
`farloads/fleet.py`** (mirroring `applicability.py` / `validation.py`) with the CSV
load + rendering in an `app/components.py` wrapper, exceeding the backlog's
manual-only acceptance to keep the math regression-safe. (D-E4-2) Nearest-N is an
**adaptive normalized-Euclidean** metric over the metrics the subject has; the
outlier flag is the fleet **p10–p90** band. (D-E4-3) The readout lists the
**nearest 3** from the **whole fleet**, with jets (`max_hp = 0`) excluded from W/P
distance and the W/P percentile only, never from the comparator pool. Both pages
now render **both** scatters (the readout is the unification), where previously
Weight Estimate showed only MTOW-vs-OEW.

---

## Phase E — Step E3: Graphical review + input-consistency validation (complete, 2026-07-15)

**Objective.** Give the input-heavy definition pages a visual sanity check and
explicit input-consistency warnings. GUI-only in effect: **no schema change**
(`SCHEMA_VERSION` stays 22) and **no calc-math change** — the Appendix A/B oracles
pass unmodified, and the two new modules are additive pure helpers, not edits to
any oracle-locked calc.

**Deliverables.**
- **`farloads/vn_diagram.py`** — a pure, unit-tested V-n diagram builder:
  `build_vn_diagram(...)` returns the plottable polylines — the curved stall
  boundary `n = (V/VS)²` sampled VS→VA (fixing the corner-to-corner straight line),
  the closed positive/negative flaps-up manoeuvre envelope, the flaps-down envelope
  off VSF/VF capped at n = 2.0 (14 CFR 23.337(b)), and the up/down gust lines at
  VC/VD (textbook Pratt form, 14 CFR 23.341). `resolve_gust_inputs(...)` resolves
  the wing lift-curve slope + MAC from the aero/geometry slices when present, else
  textbook defaults (flagged `approximate`).
- **`farloads/validation.py`** — pure input-consistency predicates,
  `consistency_warnings(project) -> list[ConsistencyWarning]`, each tagged with the
  page that renders it: taper ratio > 1, non-positive reference area,
  leading-/trailing-edge ordering, Configuration-vs-WINGGEOM wing-area mismatch
  (5% tol), and CG outside the WTENV structural CG envelope (skipped when that
  envelope or the wing geometry is absent).
- **Structural Speeds page** — a **V-n diagram** section (Flaps up/down/both radio,
  gust-line toggle) rendered from `vn_diagram`, LIMIT-marked, captioned that the
  gust lines are approximate and pointing to the rigorous Flight Envelope V-n.
- **Weight/CG/Inertia page** — a **CG marker + mass-distribution** plot (per-item
  weight stem at its fuselage station, coloured by mass kind, the loading CG line,
  and the WTENV fwd/aft structural limits when defined) plus the CG-outside-envelope
  warning.
- **Wing Geometry** and **Configuration & Layout** pages render their tagged subset
  of `consistency_warnings` as `st.warning`.
- **Tests** — `tests/test_vn_diagram.py` (8) and `tests/test_validation.py` (10):
  physics-closure on the V-n geometry and each predicate firing on crafted bad
  input while silent on the Appendix-A GA fixture.

**Test / Acceptance.** Headless `AppTest` on the four touched pages: all render with
**no exceptions** on the GA fixture; the CG warning fires on a far-aft ballast
loading and is silent on good input. Full suite (**333 passed**, +18 for the two new
test files) + `ruff check farloads/ cli.py app/` clean, confirming the
no-calc-change invariant. Docs synced (`GUI_design.md §8.2/§8.3/§11`,
`PROJECT_GUIDE.md` package layout, `20_theory/00_theory_sources.md`, this history +
`CHANGELOG.md`, backlog E3 removed).

**Key decisions.** The V-n lives on **Structural Speeds only** (user choice); its
gust lines use the **textbook Pratt form** rather than FLTLOADS' Mach-corrected
iteration, so the **Flight Envelope page is left unchanged** and the two can differ
slightly — the Structural Speeds caption makes this explicit. The CG check is
against the **WTENV structural envelope** (not the simpler `cg_cases` extents),
skipped silently when undefined. Predicates live in a **pure, unit-tested
`farloads/validation.py`** (mirroring `applicability.py`) rather than an app-side
helper, exceeding the backlog's manual-only acceptance to keep the warnings
regression-safe.

---

## Phase E — Step E2: Parameter explanation (tooltips + guides) (complete, 2026-07-15)

**Objective.** Make every airplane-definition input self-explanatory. GUI-only:
no schema change (`SCHEMA_VERSION` stays 22) and no calc-math change — the
Appendix A/B oracles pass unmodified. Scope is the six Airplane-section pages;
the Analysis-phase pages are out of scope.

**Deliverables.**
- **`help=` hover tooltips** on every non-grid domain input widget across
  `app/views/configuration_layout.py` (23 widgets — fuselage/wing/tail/gear
  geometry + tail-type + engine X/Y/Z), `weight_estimate.py` (airplane, power,
  engines, seats, endurance, baggage, pressurized, engine type),
  `structural_speeds.py` (category, design weight, wing area, VH/VS/VSF, shoulder
  altitude, VC/VD, concept n/n_neg), `aero_coefficients.py` (config names, stall
  CL / neg-stall CL, include-flaps-down), and `wing_geometry.py` (symmetric,
  integration elements). The `configuration_layout._num` helper gained a
  pass-through `help` parameter. Each tooltip cites the FAR paragraph and/or the
  Reference-1 program/chapter (regulation + chapter, not exact PDF pages).
- **"ℹ️ Parameter guide" expanders** (collapsible, `expanded=False`) on the five
  pages that need one: Configuration & Layout (MAC / XLEMAC / neutral point /
  static margin / tip-back / overturn / datum convention), Wing / Surface
  Geometry (XLE/YLE/XTE/YTE / symmetric / integration elements / derived
  Area·MAC·XLEMAC·AR·span), Weight/CG/Inertia (weight_lb / x·y·z stations /
  ixx·iyy·izz per-item inertias with the parallel-axis note / mass `kind`),
  Structural Speeds (VS/VSF/VA/VC/VD/VF/VH / shoulder altitude / KEAS / concept
  factors), and Aerodynamic Data (the `C0…C4` lift/drag/moment polynomials, α in
  degrees / stall CL / cruise-vs-flaps-down balancing).
- **Grid (`st.data_editor`) pages** (Weight/CG inertias, Wing Geometry LE/TE
  points, the Aero `C0…C4` table) explain their columns in the guide expander
  rather than per column (no per-column `help=`).

**Test / Acceptance.** Headless `AppTest` end-to-end on all six pages: every page
renders with **no exceptions**; widgets carry their tooltips (config 23, speeds
12, aero 7, wing-geometry 2 once a surface exists) and each guide expander +
glossary term renders. Full suite (**314 passed**) + `ruff check farloads/ cli.py
app/` clean, confirming the GUI-only / no-calc-change invariant. Docs synced
(`GUI_design.md §8.1`/§11, this history + `CHANGELOG.md`, backlog E2 removed).

**Key decisions.** Citations are **regulation paragraph + Reference-1
program/chapter**, not exact PDF page numbers (user choice — avoids a per-field
371-page trawl for equivalent traceability). Grid inputs are covered by the
**guide expander only**, not per-column `help=` (user choice — the column-header
tooltip is more limited and the grids' fields are better defined together).
Tooltips are **inline `help=` strings** next to each widget (matching the existing
E1 pattern on `occupants`/`crew`), not a shared help-text module. Guide expanders
landed on **five** pages, not only the three "dense" pages the backlog named,
because the grid pages' "guide-only" decision makes the expander the sole
explanation vehicle for their columns.

---

## Phase E — Step E1: FAR 23 applicability + occupants/crew fields (complete, 2026-07-15)

**Objective.** Detect and surface — never block — when an airplane exceeds FAR 23
applicability (higher MTOW / more occupants), so a beyond-FAR23 configuration no
longer runs GA-calibrated math silently; add the occupant count the seat-limit
check needs and a user-set flight-crew count carried in the operating empty weight.
No calc-math change: the Appendix A/B oracles pass unmodified and concept mode still
reduces exactly to FAR 23 on GA inputs.

**Deliverables.**
- **Limits block** in `farloads/constants.py`: `FAR23_MAX_WEIGHT_LB = 12500`,
  `FAR23_MAX_PASSENGER_SEATS = 9`, the encoded-but-dormant commuter tier
  (`FAR23_COMMUTER_MAX_WEIGHT_LB = 19000` / `FAR23_COMMUTER_MAX_PASSENGER_SEATS = 19`),
  and `DEFAULT_FLIGHT_CREW = 1` (the crew assumed when no weight-estimation slice is
  present), cited to 14 CFR 23.1.
- **Pure helper** `farloads/applicability.py`: `Exceedance(field, value, limit,
  label)`, `effective_occupants` (speeds.occupants, else Weight Estimate seats),
  `effective_crew` (weight.estimation.crew, else `DEFAULT_FLIGHT_CREW`),
  `design_weight_lb` (speeds.weight_lb, else Weight DB total), and
  `far23_applicability(project)` (`passenger seats = occupants − crew`) — no
  Streamlit, unit-tested, yields `[]` on Appendix-A GA inputs. Exported from
  `farloads` (`far23_applicability`, `Exceedance`).
- **Schema fields** (`SCHEMA_VERSION` **20 → 22**, additive; older files load with
  defaults): `StructuralSpeedsInput.occupants: Optional[int] = None` (falls back to
  `weight.estimation.seats`), entered on **Structural Speeds** and echoed read-only
  on **Configuration & Layout**; and `WeightEstimationInput.crew: int = 1`, entered
  on **Weight Estimate**, subtracted from occupants for the seat check and carried
  in a derived **operating empty weight** line WTESTIMA reports
  (`OEW = empty + crew×170`; reporting-only, `MTOW`/`useful`/`empty` and their
  Appendix-A oracles untouched, so it is not re-summed with the useful load).
- **Shared banner** `app/components.render_applicability_banner(project)` on the
  Dashboard + definition pages: non-blocking `st.warning` + per-exceedance rows +
  a one-click **"Switch to Concept"** button that sets `speeds.category = "C"` and
  seeds `chosen_n`/`chosen_nneg` from the computed FAR 23.337 factors (via
  `structural_speeds._maneuver_load_factors`) so the flip never raises. Suppressed
  when the project is already concept. `tests/conftest.py` adds `app/` to the path
  so the view smoke test resolves `components` (Streamlit provides it at runtime via
  the `app/Home.py` entrypoint).

**Test / Acceptance.** `tests/test_applicability.py` (new): GA Appendix-A →
no exceedances; a 20,000 lb / 12-occupant Normal → weight (20,000 > 12,500) + seat
(12 − 1 crew = 11 > 9) exceedances; crew reduces the passenger-seat count;
`effective_occupants`/`effective_crew`/`design_weight_lb` fallbacks.
`tests/test_weight_estimate.py`: the derived OEW line (empty 2150 + crew×170) with
the empty/MTOW oracles unchanged. `tests/test_io.py`: `occupants`/`crew` round-trip
and old files (no key) load with the defaults. Headless `AppTest` end-to-end: banner
renders for an over-limit Normal airplane, "Switch to Concept" seeds n=2.9 /
n_neg=−1.16 with no exception and hides the banner, GA inputs show none. Full suite
(314 passed) + `ruff check farloads/ cli.py app/` clean. Docs synced
(`PROGRAM_SPEC.md`, `20_theory/00_theory_sources.md`, `GUI_design.md §9`, this
history + `CHANGELOG.md`).

**Key decisions.** Seat limit counts **passenger seats excluding crew**, where crew
is the **user-set `WeightEstimationInput.crew`** (default 1), not a hardcoded
constant. Crew weight is carried in a **derived OEW reporting line** (`empty +
crew×170`) rather than reclassifying the itemized crew items into the `EMPTY`
bucket — that keeps the WTESTIMA empty (2150) and WTENV empty-weight-station (85.1)
oracles intact (the oracle-safe option the user chose over a documented oracle
deviation). `occupants` is an **independent field seeded from `weight.seats`**
(seed-chain), not a re-use of it. The MTOW check reads **`speeds.weight_lb`, falling
back to the Weight DB total**. "Switch to Concept" **auto-seeds the concept load
factors** from the FAR 23.337 values. The commuter tier (19,000 / 19) is **encoded
but dormant** — the merged "Normal / commuter" category maps to `"N"`, so the check
uses the non-commuter tier until a distinct Commuter category lands (see backlog
"Distinct Commuter category").

## GUI fix — Imperial/SI input widgets & upstream-data seeding (complete, 2026-07-15)

**Objective.** Complete the session-wide Imperial/SI toggle so it governs
**inputs**, not just results, and stop the definition pages re-asking for data
the project already holds. The global toggle (`app/Home.py`,
`st.session_state["unit_system"]`) was advertised as applying "everywhere," but
only *results* respected it — every input widget (sidebar forms, `data_editor`
tables) accepted and displayed Imperial regardless, so an SI user entered SI-
looking numbers that were stored as Imperial (bug A). Separately, several pages
opened with blank/duplicate fields for quantities an upstream slice already
owned (bug B). Pure GUI/presentation-boundary work: no calc-math change, the
Appendix A/B oracles pass unmodified, no new `Project` slice, `SCHEMA_VERSION`
stays at 20. 19 files, ~698 insertions.

**Deliverables.**
- **Bug A — input widgets respect the toggle.** Extended `farloads/units.py`'s
  scalar kind tables (`SI_PER_IMPERIAL`/`UNIT_LABELS`) with `area_sqft`,
  `length_ft`, `inertia_lbin2` and `area_sqin`, then applied the
  `engine_mount.py` input pattern to every remaining page with domain inputs:
  read `system`, `U = labels_for(system)`, seed via `to_display(value, kind,
  system)`, unit-suffix the label, suffix the widget `key` with `system.value`
  (so switching units re-seeds the widget), and convert back with
  `to_imperial_scalar` on Apply so the `Project` stays canonical Imperial.
  Pages: `configuration_layout`, `structural_speeds`, `wing_geometry`,
  `weight_cg_inertia`, `aileron_loads`, `flap_loads`, `flight_envelope`,
  `fuselage_loads`, `landing_loads`, `mach_limit`, `payload_cases`,
  `tab_loads`, `tail_loads`, `weight_envelope`, `weight_estimate`,
  `wing_loads`. `loads_plots.py` — which never referenced the toggle at all —
  gained display-only conversion of its plotted values and axis/legend labels
  (its external-comparison CSV overlay is forced Imperial, since imported span-
  load CSVs are always canonical Imperial). Airspeed (KEAS) and altitude (ft)
  stay aviation-standard in both systems, unchanged.
- **Bug B — seed from upstream data.** New
  `farloads.modules.configuration.wing_layout_from_surface()` (the inverse of
  `wing_polylines`) lets **Configuration & Layout** seed its parametric wing
  fields (area / aspect ratio / taper / LE sweep / LE station) from an existing
  WINGGEOM `wing` surface when no `configuration` slice exists yet. **Flight
  Envelope** seeds MAC / wing area / 25%-MAC station from the `wing` surface
  (and waterline from `configuration`) instead of hardcoded Appendix-A literals;
  **Mach Limit** seeds `MC`/`MD`/shoulder altitude from STRSPEED's
  `design_speed_values`; **Tail Loads** seeds the h/v-tail spans from
  `configuration.h_tail_span_ft`/`v_tail_span_ft`; **Wing Loads** seeds dihedral
  from `configuration.dihedral_deg`. Every seed fires only when the page's own
  field is still unset, so an explicit value is never overwritten.

**Test / Acceptance.**
- Full suite (`pytest -q`): **303 passed**; `ruff check farloads/ cli.py app/`
  clean. No test change needed — the calc core, `Project` schema and
  CSV/report units are untouched.
- Runtime verification via `streamlit.testing.v1.AppTest` (no browser tooling
  in-env): confirmed the Imperial→SI display conversion and the SI→Imperial
  Apply round-trip on representative pages (e.g. Configuration & Layout
  fuselage length 5000 mm → stored 196.85 in; Structural Speeds 1000 kg →
  2204.62 lb), that VH/VS/VC/VD/altitude stay kt/ft under SI, and each bug-B
  seed (Config wing area 138.89 ft² from a surface; Flight Envelope MAC 50.665;
  Mach Limit MC/MD from STRSPEED; Wing Loads dihedral 5.5° from Config).

**Key decisions.**
- **Input-boundary conversion, not a stored unit.** `project.json` and the calc
  core stay Imperial-only; the toggle converts at each widget's seed/Apply
  boundary exactly like the results path — no unit tag is ever written to disk,
  so oracle fixtures and older files are unaffected.
- **Occupancy/`seats` left as-is.** Time-in-hours and the weight-regression
  `seats` count have no unit kind and were not converted (consistent with the
  airspeed/altitude aviation-standard exception); a real applicability
  occupants field is scoped to backlog **Phase E1**, not this fix.
- **Aero-coefficient page unchanged.** Its inputs are dimensionless polynomial
  coefficients, so no unit handling applies.

---

## Phase D — Step D8: Export & report upgrades (complete, 2026-07-09)

**Objective.** Close out Phase D (the six-section GUI restructure) with the
last Export-page item: a multi-sheet `.xlsx` workbook alternative to the
`.zip` bundle, and wiring the D5 Critical Loads case selection into the
sbeam/case-index exports where the case-id lineage actually supports it. Pure
GUI/export-layer step, no calc-math change; no new `Project` slice, so
`SCHEMA_VERSION` stays at 19. D8.1 (the case-index table) had already shipped
as part of D1.

**Deliverables.**
- **D8.2 — `.xlsx` workbook.** New `farloads/export/workbook.py::build_workbook`
  (pure renderer, `openpyxl` dependency added to `pyproject.toml`): re-shapes
  the strings/rows the Export page already computes for the CSV/`.zip`
  channel into one workbook — a `Project` sheet, one tab per module with
  results, a `Case Index` sheet, and the tabular sbeam span-load CSVs (wing/
  fuselage span loads, tail chordwise, control-surface loads); BDF card text
  is excluded (not tabular). Export page gained a "📊 Download workbook
  (.xlsx)" button, a sibling alternative to the `.zip` (not nested inside it).
- **D8.3 — export scope filter.** New pure helper
  `sbeam_bridge.filter_by_selected_case_ids(results, selected_ids)`
  (`selected_ids is None` = unfiltered; a result with no `case_ref` is always
  kept). The Export page gained an "Export scope" toggle (Full set /
  Governing set), disabled when nothing is deselected on the Critical Loads
  page. Tracing the case-id lineage found the filter is **exact only for
  fuselage and tail** (`body_loads.py`/`taildist.py` copy `case_ref` verbatim
  from `envelope.critical.conditions`) — wing (`WingMassInput.cases`, user-
  authored) and control-surface (aileron/flap/tab) results mint independent
  case ids on disjoint bands that never overlap `envelope.critical`'s (the
  known "Unify select_wing/one_engine_out case identity" gap), so those two
  always export the full set with an explanatory caption rather than
  silently filtering to nothing.

**Test / Acceptance.**
- `tests/test_workbook.py` (new): builds a workbook from `ga6_normal
  .project.json`, re-opens it with `openpyxl.load_workbook`, and asserts
  expected sheet names, `Project`-sheet field/value round-trip, module-sheet
  row counts matching their source CSVs, and that no BDF card text leaked
  into any sheet.
- `tests/test_sbeam_bridge.py`: three new cases for
  `filter_by_selected_case_ids` (unfiltered passthrough, keep-only-selected,
  empty-selection drops all tagged cases).
- Full suite (`pytest -q`): 290 passed; `ruff check farloads/ cli.py app/`
  clean.
- Manual verification: `streamlit run app/Home.py` against `examples/
  ga6_normal.project.json` — Export page loads, the workbook button produces
  a valid `.xlsx`, the scope toggle is disabled until a condition is
  deselected on Critical Loads, and the wing/control-surface caption appears
  once the toggle is enabled.

**Key decisions** (resolved with the user before implementation).
- **xlsx library.** `openpyxl` (pandas' default xlsx engine) over `xlsxwriter`
  — no rich formatting needed here.
- **D8.3 scope for the wing/control-surface gap.** Filter where the case-id
  lineage genuinely matches (fuselage/tail); leave wing/control-surface always
  full-set with a caption, rather than deferring D8.3 until the id-unification
  mini-step lands.
- **Toggle blast radius.** The scope toggle affects only the sbeam BDF/CSV
  artifacts and the case index; per-module load-case CSVs and the combined
  text report always show every computed case (the oracle-traceable record,
  not the structural hand-off).

Closes Phase D (Steps D0–D8) — the six-section GUI restructure is complete;
remaining work is the deferred calc refinements and open design decisions in
`docs/30_future/00_backlog.md`.

---

## Phase D — Step D7: Loads Plots page (complete, 2026-07-09)

**Objective.** Add the sixth workflow section's page: a consolidated,
read-only viewer over the distributed-load results the Analysis pages already
persist on `Project.loads` — overlay shear/moment/torsion by case ID, an
enveloped (max |value|) curve, a wing+fuselage whole-airframe snapshot, and an
external-comparison CSV import — plus the "confirm every plot the original
suite rendered has a Streamlit equivalent" graphics audit. Pure GUI/view-layer
step, no calc-math change; no new `Project` slice, so `SCHEMA_VERSION` stays
at 19.

**Deliverables.**
- `app/views/loads_plots.py` (new): component picker (Wing / Fuselage /
  Horizontal Tail / Vertical Tail / Aileron / Flap / Tab — the six
  `case_ids.py` structural-component prefixes, control surfaces folded into
  their host per the D-1 taxonomy) reading `Project.loads.wing_net` /
  `body_net` / `tail_chordwise` / `control_surface`; a case-ID multiselect per
  component; one overlay figure per load quantity (thin trace per selected
  case + a dotted max-|value| envelope trace); a "Total loads" section
  combining one wing case + one fuselage case into a single two-subplot figure
  (shear on the primary axis, moments on a secondary axis); and a CSV importer
  that reuses `farloads.export.sbeam_bridge.span_load_csv` /
  `body_span_load_csv`'s exact column schema, auto-detects wing vs. fuselage
  shape by column-subset match, and overlays the imported curve (dashed)
  against a computed one. Writes nothing back to `Project` — no `st.form`/
  Apply (page convention #1 doesn't apply to a pure viewer).
- `farloads/workflow.py`: one new `WorkflowStep("loads_plots", "Loads Plots",
  LOADS_PLOTS, module=None, produces=None, ...)`, mirroring the other
  GUI-only consolidation steps (`dashboard`, `results_review`,
  `export_report`). This is the only step in the `LOADS_PLOTS` phase, so
  `Home.py`'s existing "hide empty section" guard now shows "5 · Loads Plots"
  in the sidebar with no `Home.py` change needed.
- **Graphics audit (item 3): no gaps found.** Every plot an original program
  rendered already has a Streamlit equivalent: weight/CG envelope
  (`weight_envelope.py`), V-n diagram (`flight_envelope.py`), spanwise shear/
  bending/torsion (`wing_loads.py`, `fuselage_loads.py`), Mach-limited speed
  boundary (`mach_limit.py`), and the three-view (`configuration_layout.py`).
  Engine Mount and Landing Gear are scalar reaction-load components with no
  spanwise distribution to plot — the original suite never rendered a chart
  for them either, so they are intentionally **not** in the Loads Plots
  component picker (a locked design decision, see Key decisions).

**Test / Acceptance.**
- `tests/test_workflow.py` (the registered-module ↔ workflow-step guard) —
  passes unchanged; `module=None` steps are already tolerated (three prior
  precedents).
- Full suite (`pytest -q`): 283 passed, no calc module touched.
- Manual verification via `streamlit.testing.v1.AppTest` on
  `app/views/loads_plots.py`: (1) an empty project shows the "visit an
  Analysis page first" message with no exception; (2) `examples/ga6_normal
  .project.json` run through `net_loads`/`taildist`/`aileron`/`flap`/`tab`
  renders the wing-component overlay (3 quantity charts, no exception); (3)
  `span_load_csv(project.loads.wing_net)`'s column set round-trips through the
  page's wing/fuselage schema-detection logic correctly, including the
  case where a wing CSV's columns are also a superset of the body schema (the
  wing check is ordered first, so it always wins when both match).

**Key decisions** (resolved with the user before implementation).
- **Component-picker scope.** Distributed components only (wing, fuselage,
  htail, vtail, aileron, flap, tab) — Engine Mount / Landing Gear stay off the
  picker; they're scalar and have no curve to overlay, and the original suite
  didn't plot them either.
- **Envelope definition.** Max |value| per station across the selected case
  IDs (the classic structural-design envelope), not SELECT's governing-set
  filter — the user picks the cases to overlay freely.
- **Total-loads view.** A combined wing+fuselage figure (one case each), not
  just a metrics table — gives a whole-airframe-at-a-glance read.
- **Import schema.** Reuses the existing `sbeam_bridge` span-load export
  schema exactly rather than inventing a new generic station/value mapping —
  a user can export, optionally round-trip through sbeam, and re-import to
  compare on the same axes with zero new format to document. (The more
  generic station/value CSV mapping remains a possible future extension, not
  needed for this step.)

---

## Phase D — Step D6: Merge Analysis into nine component pages (complete, 2026-07-09)

**Objective.** Reorganize the 11 per-BAS-program Analysis pages into the target
nine component pages (decision D-2), and apply the Phase-D page conventions
(`05_phase_d_gui_workflow_plan.md` §5 — form+Apply, merge-writes, read-don't-re-ask, no
airplane-shaped defaults, LIMIT-marked analysis views) to every one of them.
Design decisions locked 2026-07-09 (`05_phase_d_gui_workflow_plan.md` §3 D-7). No
calc-math change throughout — Appendix A/B oracles pass unmodified;
`SCHEMA_VERSION` stays at 19 (pure GUI reorg, no new project fields).

**Deliverables.**
- **Wing Loads** (`app/views/wing_loads.py`, new) merges `airloads.py` +
  `net_wing_loads.py`: one `st.form` + Apply for the Schrenk aero inputs and the
  WINGINER/NETLOADS mass distribution. Fixes the `Project.aero.surfaces`
  wholesale-replace on Apply (upsert-by-name instead, so a future non-wing aero
  surface would survive this page); scrubs the Appendix-A-shaped widget
  defaults (section-slope/taper/TAU/target-CL/panel-weight/density-ratio/rib/
  waterline/dihedral/case-row literals); adds the missing LIMIT caption/column
  markers to the net-load output.
- **Tail Loads** (`app/views/tail_loads.py`, new) merges `tail_distribution.py`
  + `balanced_tail_verification.py` behind one `st.form` + Apply for the
  chordwise geometry; the balancing-load cross-check keeps its existing
  correct LIMIT caption.
- The other 7 pages (Engine Out, Fuselage Loads, Aileron, Flap, Tab, Engine
  Mount, Landing Gear) converted 1:1 to the conventions: every page's inputs
  moved into `st.form` + Apply; Fuselage Loads' hardcoded 5-row station table
  and Engine Mount's baked-in Continental IO-520-BB `default_engine()` (weight/
  CG/RPM/HP/rotor literals) replaced with blank defaults; Aileron/Fuselage/
  Landing Gear/Engine Mount gained the LIMIT caption+marker they were missing
  (Flap/Tab/Engine Out already had it); Landing Gear's max-landing-weight/
  gross-weight/wing-area inputs got read-only-derivation help text pointing at
  `Project.mass`/`Project.geometry` (max landing weight stays a page-only
  input — FAR 23.473(b)/(c) is an engineering judgment call, not derivable).
- **Engine Mount normalization** (decision D-7): retired the page's separate
  `st.session_state["engine_inputs"]` store and the ad hoc local `Project(...)`
  built only for compute/export. The page now reads/writes
  `Project.engines`/`Project.engine_layout`/`Project.include_far25` directly
  via `st.session_state["project"]`, matching every other page; an unapplied
  per-engine edit is discarded on engine/unit switch (Phase-D convention, not a
  regression — the old separate store's job was working around exactly this).
  A partially-filled multi-engine layout (a newly-added, still-blank engine)
  now surfaces as a caught, friendly warning on the export bundle instead of
  crashing the page.
- `farloads/workflow.py`: the 11 Analysis steps collapsed to 9. `wing_loads`
  (`module="net_loads"`) and `tail_loads` (`module="taildist"`) are each the
  shared nav step for two independently-registered calc modules; `"airloads"`
  and `"balloads"` were added to `FOLDED_MODULES` (decision D-7, reusing the
  existing `wing_inertia` precedent rather than adding a `modules` tuple to
  `WorkflowStep`). `dashboard.py` and `Home.py` needed no code change — both
  already derive their content purely from `wf.STEPS`/`wf.by_phase()`.

**Key decisions (D-7, locked 2026-07-09).**
- Merged-page nav steps reuse the `FOLDED_MODULES` precedent rather than adding
  a `modules: Tuple[str, ...]` field to `WorkflowStep` — zero dataclass/test-
  shape churn, consistent with the existing `wing_inertia` fold.
- Engine Mount's state-management is normalized onto the standard
  `st.session_state["project"]` pattern in this same step, rather than deferred
  — D6 is exactly the step meant to retire this kind of one-off pattern, and
  the other convention fixes there are small by comparison.

**Test/Acceptance.** Full suite: 282 tests pass, `ruff check farloads/ cli.py
app/` clean. `tests/test_workflow.py` updated for the `wing_loads` key (drops
the `"aero"` requirement, now internal to the merged page).
`tests/test_views_smoke.py` globs `app/views/*.py` so it picked up the 2 new
files and dropped the 4 retired ones with no test-code change (24 view/entry
smoke tests still pass). Every changed page verified with a
`streamlit.testing.v1.AppTest` script against `examples/ga6_normal.project.json`
— ran each form's Apply and inspected the resulting `Project` mutation
(including a multi-engine Engine Mount round-trip: layout switch to Twin,
edit + Apply both engines, confirm `Project.name` is untouched and both
engines' data matches what was typed).

---

## Phase D — Step D5: Envelopes & Critical Conditions section (complete, 2026-07-09)

**Objective.** Give the Envelopes & Critical Conditions section a shared
weight/CG input (so the CG envelope and the flight-envelope balance cannot
diverge), a combined speed–altitude chart, real multi-altitude V-n, and a
persisted critical-case selection Review/Export can reuse. Design decisions
locked 2026-07-09 (`05_phase_d_gui_workflow_plan.md` §3 D-6). No calc-math change
throughout — Appendix A/B oracles pass unmodified.

**Deliverables.**
- **D5.1 — Weight/CG Grid & Payload Cases page.** New `WeightInput.cg_cases`
  field (`SCHEMA_VERSION` 18 → 19) holding named `CgCase` loading scenarios,
  owned by the new GUI-only `payload_cases` workflow step
  (`app/views/payload_cases.py`). `FlightLoadsInput.cg_cases` — the field
  SELECT/WINGINER/NETLOADS/BALLOADS all read directly — is **not removed**
  (unlike the D4.1 `aero_coeffs` precedent, cg_cases has too many calc
  consumers to safely relocate); instead the Flight Envelope page reads
  `weight.cg_cases` read-only and merges it into `FlightLoadsInput.cg_cases` on
  every Apply, so there is exactly one place an engineer edits the numbers.
  `weight_envelope.py`'s chart (new: `loading_envelope_points()` exposes the
  forward-boundary vertices `envelope()` already computed) overlays the same
  cases as read-only markers. Old project files migrate via
  `io._legacy_cg_cases_from_flight_loads` (copies `flight_loads.cg_cases` into
  `weight.cg_cases` on load; the calc-facing field is unaffected either way).
- **D5.2 — Speed–altitude chart.** `app/views/mach_limit.py`'s EAS-vs-altitude
  chart converted from `st.line_chart` to `plotly`, with VA/VC/VD/VF
  (`structural_speeds.design_speed_values`) added as horizontal reference
  lines over the existing V(MC)/V(MNE)/V(MD)/V(FC) boundary — display only, no
  calc change.
- **D5.3 — Multi-altitude V-n.** `FlightLoadsInput.altitudes_ft` exposed as a
  real, fully-editable list on the Flight Envelope page (previously a single
  `number_input` that only ever touched `altitudes_ft[0]`); `merged()`'s
  `altitude_ft: float` param replaced with `altitudes_ft: List[float]`. The
  V-n chart gained a CG-case selector, an altitude selector, and an "overlay
  all altitudes" checkbox. `build_envelope`'s `for alt in fl.altitudes_ft`
  loop already supported this since Step C2 — confirmed by regression test
  (`test_multi_altitude_vn_regression`), no equation change.
- **D5.4 — Critical-case selection.** `CriticalLoadSet.selected_case_ids`
  (additive, empty = unfiltered) + `.selected()` helper. The Critical Loads
  page adds a per-condition checkbox (default checked); Results Review reads
  `.selected()` instead of `.conditions` for its governing-loads summary.
  Deliberately scoped to that one GUI page — WINGINER/NETLOADS, `body_loads`
  and the sbeam export bridge all keep reading `.conditions` unfiltered, so a
  deselected condition can never silently drop out of a structural
  deliverable (D8.3 is expected to wire the export bundle to this same
  selection later).

**Test/Acceptance.** `SCHEMA_VERSION` 19 round-trip + legacy-migration tests
(`tests/test_io.py`: `test_weight_cg_cases_round_trips_through_io`,
`test_legacy_flight_loads_cg_cases_migrate_to_weight`,
`test_critical_load_set_selected_case_ids_round_trip`); multi-altitude
regression (`tests/test_flight_envelope.py::test_multi_altitude_vn_regression`);
`merged()` signature test rewritten
(`test_merged_replaces_altitudes_and_cg_cases`); `CriticalLoadSet.selected()`
unit tests (`tests/test_select.py`). No automated UI test suite exists, so
every page change (`payload_cases`, `weight_envelope`, `flight_envelope`,
`mach_limit`, `critical_loads`, `results_review`) was verified with a
`streamlit.testing.v1.AppTest` script against `examples/ga6_normal.project.json`
— no exception, expected `Project` slice mutations. Full suite: 284 tests
pass, `ruff check farloads/ cli.py` clean.

**Key decisions** (locked 2026-07-09, `05_phase_d_gui_workflow_plan.md` §3 D-6): manual
weight/CG rows over item-toggle scenario derivation; `WeightInput.cg_cases` as
the schema home with `FlightLoadsInput.cg_cases` kept as the untouched
calc-facing field; the speed–altitude chart extends Mach Limit rather than a
new page; critical-case selection is opt-out (default = everything), display-
only, never a structural-calc input.

---

## Phase D — Step D4: Authoritative shared inputs + Aero Coefficients page (complete, 2026-07-09)

**Objective.** Kill duplicate wing-area/MAC/weight/CG entry across the
Airplane-section pages, remove Appendix-A-shaped widget defaults from those
pages, seed component stations into the Weight DB, compute the true CG from
`Project.mass`, wire up engine three-view write-back, and apply the Phase-D
page conventions (`05_phase_d_gui_workflow_plan.md §5` — `st.form`+Apply, merge-writes,
read-don't-re-ask, no airplane-shaped defaults) across the section. Design
decisions locked 2026-07-09 (`05_phase_d_gui_workflow_plan.md` §3 D-5). No calc-math
change throughout — Appendix A/B oracles pass unmodified at every sub-step.

**Deliverables (D4.1–D4.7).**
- **D4.1 — `Project.aero_coeffs` slice.** New `AeroCoefficientsInput`
  (`cruise`/`flaps_down` `AeroCoeffSet`s) replaces `FlightLoadsInput.
  configurations`; `SCHEMA_VERSION` 17 → 18 with a legacy-file migration
  (`io._legacy_aero_coeffs_from_flight_loads`); new `aero_coefficients`
  workflow step; `select`/`balloads` read the new slice via
  `select._flaps_by_config_name`.
- **D4.2 — Aero Coefficients page.** `app/views/aero_coefficients.py` owns the
  whole slice as a single `st.form`+Apply (cruise + optional flaps-down
  coefficient tables, 0/blank defaults); `flight_envelope.py` dropped its
  interim cruise-coefficient editor for a read-only caption + a
  no-aero-coefficients guard.
- **D4.3 — Station derivation + Weight DB seeding.** `configuration.
  component_stations(layout) -> Dict[str, Vec3]` and `match_component_station`
  (alias substring matching, most-specific first) derive approximate component
  stations from `LayoutInput`'s existing scalars, no new schema; a
  "Seed component stations into Weight DB" button on `configuration_layout.py`
  fills only zero-station `MassItem`s, never overwriting a hand-entered one.
- **D4.4 — `XLEMAC`/`MAC`/weight read-through.** `structural_speeds.py` and
  `weight_envelope.py` read the Weight DB total
  (`project.weight.direct_totals()[0]`) read-only with an explicit "Override"
  checkbox, replacing hardcoded `3400.0`/`184.125`-shaped fallbacks with
  0/info-message defaults when no Weight DB exists.
- **D4.5 — True CG from `Project.mass`.** `configuration.cg_estimate(project,
  layout, geom) -> (x_cg, z_cg, source)` returns the weight-averaged station
  from `Project.mass.cases[0]` when present, else the prior 25%-MAC/wing-
  waterline first cut; the gear tip-back/overturn condition and the three-view
  CG marker both switch to it automatically, with the source named in the
  label/legend.
- **D4.6 — Engine write-back + mass-item overlay.** The three-view overlays a
  marker per `Project.weight.items` `MassItem` (colored by `MassItemKind`,
  sized by weight) and a diamond per `Project.engines[]` at its `engine_cg`; a
  new "Engine positions" expander offers numeric X/Y/Z overrides (not
  drag-and-drop) that write back into `Project.engines[i].engine_cg` and
  re-render via `st.rerun()`.
- **D4.7 — Form+Apply conversion.** `configuration_layout.py`, `wing_geometry.
  py`, `weight_estimate.py`, `weight_cg_inertia.py` and `structural_speeds.py`
  converted to `st.form`+explicit-Apply (matching `aero_coefficients.py` from
  D4.2); every remaining Appendix-A-shaped literal default (GA6 wing/fuselage/
  tail/gear geometry, WTESTIMA mission figures, STRSPEED VH/VS/VSF/altitude/
  VC/VD/load-factor figures, the WINGGEOM Appendix-A wing polyline) replaced
  with 0/blank/derived defaults; conditionally-hidden form fields (override
  checkboxes, the Concept-category load-factor inputs) changed to always-
  rendered-but-conditionally-applied, since `st.form` fields don't react live
  to a sibling widget's value. While verifying the D4 regression check below,
  found and fixed a **merge-write defect** predating D4.7: `configuration_
  layout.py`'s station-seed button, and both `project.weight` writes in
  `weight_estimate.py` and `weight_cg_inertia.py`, constructed a fresh
  `WeightInput(estimation=..., items=...)` without carrying forward
  `envelope`, silently dropping the Weight Envelope page's inputs on the next
  write from any of those three pages — now all three pass `envelope=project.
  weight.envelope` through.

**Test/Acceptance.** `aero_coefficients` step registered and the nav-drift
test (`tests/test_workflow.py`) green; `SCHEMA_VERSION` bump with an
old-project-file load test (`tests/test_flight_envelope.py`); `tests/
test_configuration.py` gained 8 direct-function tests across D4.3/D4.5
(`component_stations`, `match_component_station`, `cg_estimate`); no automated
UI test suite exists, so every page change was verified with a
`streamlit.testing.v1.AppTest` script (blank project, populated project, and —
where relevant — clicking Apply/seed buttons), each confirming no exception
and the expected `Project` slice mutation. D4's regression DoD item — loading
`examples/ga6_normal.project.json`, running the D4.3 seed logic, and comparing
`design_speeds`/`weight_envelope.envelope` output before vs. after — confirmed
bit-identical (the example's 24 items already carry real stations, so the seed
is a no-op there; the check also caught the merge-write defect above, since
the pre-fix seed silently cleared `weight.envelope` and made the "after" run
raise instead of matching). Full suite: 277 tests pass throughout D4.1–D4.7,
`ruff check farloads/ cli.py` clean at every sub-step.

**Key decisions** (locked 2026-07-09, `05_phase_d_gui_workflow_plan.md` §3 D-5): the
default-scrub scope is the five Airplane-section pages + Aero Coefficients
only (`flight_envelope`/`weight_envelope`/`mach_limit`/`airloads` keep their
literals until their own D5/D6 rework); aero coefficients get a dedicated
owned slice rather than nesting in `FlightLoadsInput`; component stations are
derived from `LayoutInput`'s existing scalars rather than a new per-component
sub-model; engine three-view write-back is numeric-override, not
drag-and-drop, and landed in D4 rather than deferred.

---

## Phase D — Step D3: Start (landing) page & local-disk persistence (complete, 2026-07-09)

**Objective.** Decision D-3: give the locally-run app real project persistence —
Open/Save against a local `projects/` directory (recent list, New-from-example),
a global sidebar file widget on every page, and optional `engineer`/`date`
project metadata carried in the JSON and shown in exports. No autosave; no calc
change.

**Deliverables.**
- `farloads/models.py`: `Project.engineer: str = ""`, `Project.date: str = ""`
  (freeform text, additive). `SCHEMA_VERSION` 16 → 17.
- `farloads/io.py`: `project_from_dict`/`project_to_dict` round-trip
  `engineer`/`date` (omitted from the dict when blank, so old files are
  byte-identical on save). New `default_projects_dir()` (resolved from
  `io.py`'s own file location — repo root / `projects` — not the process cwd,
  so it's stable regardless of where `streamlit run app/Home.py` is invoked
  from) and `list_saved_projects(directory)` (`*.project.json` files,
  newest-mtime-first, `[]` if the directory doesn't exist yet).
- `app/Home.py`: the project (`st.session_state["project"]`) and the global
  **Project file** sidebar widget now live here, above `pg.run()`, so they
  render on every page regardless of the active view. The widget offers Open
  (a selectbox of `list_saved_projects`), New from example
  (`examples/*.project.json`), Save to disk (writes/overwrites
  `<name>.project.json` into `projects/`, created lazily on first save), the
  existing browser upload/download, and an unsaved-changes caption (diffs the
  live project's dict against a snapshot taken on every load/save).
  Discarding unsaved edits via Open/New-from-example is guarded by an
  `st.dialog` confirmation.
- `app/views/dashboard.py`: dropped its own sidebar uploader/download block
  (superseded by `Home.py`'s); added **Engineer**/**Date** text inputs beside
  the project-name field.
- `app/views/export_report.py`: the combined text report and zip bundle now
  open with a `Project: … / Engineer: … / Date: …` header line (fields omitted
  when blank); fixed a leftover D2 doc-sync miss ("fill in the Define pages
  first" → "Airplane pages").
- `.gitignore`: added `projects/`.

**Test/Acceptance.** New `tests/test_io.py` cases: engineer/date round-trip
through `project_to_dict`/`project_from_dict`, blank-by-default omission from
the serialized dict (old files unaffected), `default_projects_dir()` resolves
repo-relative, `list_saved_projects()` sorts newest-first and returns `[]` for
a missing directory. Full suite: 266 tests pass; `ruff check farloads/ cli.py`
clean. Manual: `scripts/smoke_test.sh` passes; a headless Streamlit run hit
`dashboard`, `export_report`, `configuration_layout` and `results_review` with
no traceback in the server log.

**Key decisions** (resolved 2026-07-09, see the conversation that opened this
step for the options considered):
- **Save overwrite:** silent overwrite of an existing `<name>.project.json` in
  `projects/` — matches the pre-existing browser-download Save behavior; the
  directory listing itself is the snapshot/undo mechanism (each file is a full
  project snapshot; nothing is merged in place).
- **Unsaved-edit guard:** Open and New-from-example both confirm via a
  `st.dialog` before replacing `st.session_state["project"]` if the
  unsaved-changes indicator is active; no guard existed before this step (the
  old browser uploader silently replaced).
- **Date field default:** blank, freeform text — no auto-fill to today's date,
  consistent with page convention §5.4 (no non-project-derived widget
  defaults).

---

## Phase D — Step D2: Six-section navigation restructure (complete, 2026-07-08)

**Objective.** Regroup the GUI navigation from the four generic Define →
Analyze → Review → Export phases into the six Phase-D sections — Start,
Airplane, Envelopes & Critical Conditions, Analysis, Loads Plots, Export — per
`docs/40_history/05_phase_d_gui_workflow_plan.md §2`. Regroup only: no page merges (those
land in Step D6), no calc-math or schema change.

**Deliverables.**
- `farloads/workflow.py`: `PHASES` replaced with `(START, AIRPLANE, ENVELOPES,
  ANALYSIS, LOADS_PLOTS, EXPORT)`. Every `WorkflowStep.phase` reassigned per the
  target table: **Airplane** = `configuration_layout`, `wing_geometry`,
  `weight_estimate`, `weight_cg_inertia`, `structural_speeds`; **Envelopes &
  Critical Conditions** = `weight_envelope`, `mach_limit`, `flight_envelope`,
  `critical_loads`; **Analysis** = `airloads` (moved from Define),
  `net_wing_loads`, `fuselage_loads`, `tail_distribution`,
  `balanced_tail_verification` (moved from Review), `aileron_loads`,
  `flap_loads`, `tab_loads`, `landing_loads`, `engine_mount`,
  `one_engine_out`; **Loads Plots** = no steps yet (new page lands in Step D7);
  **Export** = `results_review` (moved from Review) and `export_report`.
  `requires`/`produces` on every step are byte-identical to before the move.
- New `dashboard` `WorkflowStep` (`phase=START`, `module=None`,
  `produces=None`), so the dashboard is a first-class step instead of a
  `Home.py` special case.
- `app/Home.py`: dropped the hardcoded `dashboard = st.Page(...)` /
  `{"Overview": [dashboard]}` special case; every sidebar group (including
  Start) is now built uniformly from `wf.by_phase()`, with `default=True` set
  via `step.key == "dashboard"`. Sections with no steps (`Loads Plots`) are
  skipped rather than shown empty.
- `app/views/dashboard.py`: per-section status-board columns now iterate the
  non-empty sections (excluding the dashboard step's own Start entry, to avoid
  self-listing); docstring/caption updated to the six-section language.
- `app/views/results_review.py`: docstring/captions updated ("Review-phase" →
  "Export-section pre-export summary"); no logic change (`step_by_module`
  already filters on `s.module`, so the module-less `dashboard`/
  `results_review`/`export_report` steps were already excluded from its
  module-results rollup).
- Docs synced: `docs/10_standard/00_program_overview.md`,
  `docs/10_standard/PROJECT_GUIDE.md` (nav description + package-layout
  comments); `docs/40_history/05_phase_d_gui_workflow_plan.md` narrative status.

**Test/Acceptance.** `tests/test_workflow.py` (phase/key validity, the
registered-module ↔ workflow-step nav-drift guard, `produces`-path resolution)
passes unchanged with 6 phases instead of 4. Full suite: 262 tests pass;
`ruff check farloads/ cli.py` clean.

**Key decisions.**
- `results_review` is not named in the `05_phase_d_gui_workflow_plan.md §2` target
  table (which only lists the future D6-merged Analysis pages). Placed in
  **Export** (alongside `export_report`) as the pre-export consolidated
  summary, rather than Envelopes & Critical Conditions or Start.
- The dashboard becomes a real `WorkflowStep` rather than staying a `Home.py`
  special case, so `wf.by_phase()` is the single uniform builder for all six
  sections including Start.
- `Loads Plots` is omitted from the sidebar entirely while it has zero steps,
  rather than shown as an empty placeholder group, until Step D7 adds its page.

---

## Phase D — Step D1: Structured load-case IDs (complete)

**Objective.** Decision D-1: replace `report.py`'s render-time, per-module,
unstable `LC{idx}` with a stable, traceable `case_id` (`"<component>-<seq>"`)
on every delivered load case, assigned by the **calc** modules, so a loads
release can trace a case from the V-n matrix through SELECT to a component
load case and its sbeam card. No calc-math change — `CaseRef` is an added
field; the Appendix A/B oracles pass unmodified (`SCHEMA_VERSION` 15 → 16,
additive).

**Deliverables.**
- `CaseRef` dataclass (`case_id`, `component`, `condition`, `cg`, `speed_kt`,
  `altitude_ft`, `far_reference`) plus an optional `case_ref` field on
  `ConditionResult`, `VnPoint`, `CriticalCondition`, `WingLoadResult`,
  `BodyLoadResult`, `TailChordResult`, `ControlSurfaceLoadResult`,
  `GearReactionCase` (`farloads/models.py`).
- `farloads/case_ids.py` (new): the six-entry `COMPONENT_PREFIX` map (`wing`→`W`,
  `htail`→`HT`, `vtail`→`VT`, `fuselage`→`F`, `engine_mount`→`EM`,
  `landing_gear`→`LG`) and `CaseIdAllocator`, a per-call-site sequential
  counter with no shared/global state.
- Minting sites, each in its own already-deterministic emission order:
  `select.py` (`build_critical`, one allocator for wing/htail/vtail/fuselage,
  the `CaseRef` also copied back onto the originating `VnPoint`);
  `wing_inertia.py`/`net_loads.py` (`wing_case_ref`, a pure function of
  position in `WingMassInput.cases` so both modules agree without shared
  state); `engine.py` (`EM-`, incl. the 23.371(b) gyro condition's single base
  id whose 4 sign-combination sub-ids are *derived* at render time —
  `report.py`'s `_gyro_subcase_id`, an a/b/c/d suffix, since one
  `ConditionResult` can't carry 4 `CaseRef`s); `landing.py` (`LG-` per
  `GearReactionCase`, the manual's own 1-based case number kept separately for
  oracle traceability); `aileron.py`/`flap.py`/`tab.py` (`W-`/`HT-`/`VT-` from
  their own bands); `one_engine_out.py` (its own `VT-` sequence).
  `taildist.py`/`body_loads.py` **copy** `case_ref` from SELECT's
  `CriticalCondition` rather than re-minting.
- Numeric banding wherever two independent allocators mint into the same
  prefix (not just across modules but *within* `wing`, since `select_wing`'s
  own list and WINGINER/NETLOADS's are genuinely separate — see Key decisions):
  `W-01..39` WINGINER/NETLOADS, `W-40..49` `select_wing`, `W-50..59` AILERON,
  `W-60..69` FLAPLOAD, `W-70+` a wing tab; `HT-50+`/`VT-50+` for TABLOADS'
  htail/vtail-hosted tabs.
- `report.py`: `load_cases_to_rows`/`results_to_rows` emit `ID` from
  `case_ref.case_id` (falling back to `LC{idx}` only when absent) plus
  `Component`/`Condition`/`CG`/`Speed (kt)`/`Altitude (ft)` traceability
  columns.
- `export/sbeam_bridge.py`: the case id is stamped into the `$`-comment header
  of every wing/body/tail/control-surface `FORCE`/`MOMENT` card block; new
  `case_index_rows_from`/`case_index_csv_from` (explicit result groups) and
  `case_index_rows`/`case_index_csv` (from a `Project`'s persisted slices)
  build the ID → full-definition case-index table, deduplicated by
  `case_id`. Wired into the Export page (`app/views/export_report.py`): a new
  "Case index" section + download button, and the CSV included in the `.zip`
  bundle.
- `io.py`: `CaseRef` (de)serialization for the persisted result slices
  (`EnvelopeResult.vn`/`.critical`, `LoadsResult.*`); `ConditionResult`/
  `GearReactionCase` are transient (never written to `project.json`), so they
  need none.
- `tests/test_case_ids.py`: ids present across all four bundled example
  projects; the real uniqueness invariant (a `case_id` may legitimately repeat
  across pipeline stages for the *same* case, but never means two different
  conditions); stability across two identical runs; the wing-gap bands
  verified disjoint; `CaseIdAllocator` is a pure per-call counter. Full
  existing suite (262 tests) passes unmodified, confirming no oracle drift.

**Test / Acceptance.** `pytest` (262 passed, incl. the 5 new D1 tests);
`ruff check farloads/ cli.py app/views/export_report.py` clean. Manual smoke
run against all four `examples/*.project.json`: every project emits at least
one `case_ref`, and — after the banding fix below — zero id collisions
(no `case_id` maps to two different `condition` labels) across 51-53 cases
per project.

**Key decisions.**
- `CaseRef` is a standalone dataclass (not inline fields on eight result
  types), assigned once by the module that first names a physical condition
  and copied downstream, with exactly six component prefixes (control
  surfaces fold into their host — no `AIL`/`FLP`/`TAB` prefix) and stability
  from each module's own fixed emission order rather than a persisted
  registry — all locked 2026-07-08 (see `docs/30_future/
  05_phase_d_gui_workflow_plan.md` D-1).
- **Banding bug caught and fixed during implementation.** The original plan
  text claimed `select_wing`'s own `W-` sequence and WINGINER/NETLOADS's could
  safely share the `W-01..49` numeric range "so no collision" — a smoke run
  immediately disproved this (`select_wing`'s `W-02` = PLAA, WINGINER's
  `W-02` = TORS, same id, two different cases): two independent counters over
  the same range collide by construction. Fixed by splitting the range
  (`select_wing` → its own `W-40..49` sub-band) and adding
  `test_wing_gap_is_banded_not_colliding` to lock it. This is a narrower
  problem than the accepted "two independent case lists" gap below — banding
  fixes the collision; it does not unify the lists.
- **Accepted, not closed:** `select_wing`'s wing `CriticalCondition` list and
  `WingMassInput.cases` (which actually drives WINGINER/NETLOADS) remain two
  independent, unlinked case lists — same for `one_engine_out` vs.
  `select_vtail`. Banding prevents an id collision between them but they are
  still not the same case object. Tracked as a deferred refinement ("Unify
  `select_wing`/`one_engine_out` case identity...") — needs its own oracle
  re-check since closing it changes which case list WINGINER/NETLOADS iterate.
- Transient results (`ConditionResult`, `GearReactionCase`) get no `io.py`
  round-trip since they're never persisted on `Project` — only `case_ref` on
  the persisted result slices needs (de)serialization.

---

## Release 0.2.0 — Step R2: GUI / CLI smoke test (complete)

**Objective.** Close `RELEASE_PROCESS.md` §3.5 as a permanent, repeatable
check instead of a manual checklist pass, so every future release runs the
same script.

**Deliverables.** `scripts/smoke_test.sh`: starts `app/Home.py` headless on a
fixed local port, polls Streamlit's `/_stcore/health` endpoint until it comes
up, curls the root page (asserts HTTP 200) and scans the server log for a
traceback, stops the server, then runs `farloads engine
examples/ga6_normal.project.json -o out.csv` and asserts the CSV is non-empty
with an `ID` header and at least one load-case row. `RELEASE_PROCESS.md` §3.5
now points at the script instead of prose steps. No `SCHEMA_VERSION` bump, no
calc change — tooling-only.

**Test / Acceptance.** `scripts/smoke_test.sh` run against a clean `.venv`
checkout: exits 0, root page 200 with no traceback, CLI wrote 3 load-case rows
for the `engine` module against `ga6_normal.project.json`.

**Key decisions.** Committed as a standalone bash script rather than a pytest
case in the main suite — the headless-server subprocess is slow and
port/timing-sensitive, so it stays out of the default `pytest` gate rather
than risk flaking CI; not wired into CI in this step. Uses
`examples/ga6_normal.project.json` only (matches the CLI bullet the release
process already named). "Renders without error" is checked by process +
HTTP 200 + log scan, not a manual browser pass.

---

## Release 0.2.0 — Step R3: docs-drift check (complete)

**Objective.** `RELEASE_PROCESS.md` §3.1 — confirm `PROGRAM_SPEC.md`,
`PROJECT_GUIDE.md` and `20_theory/00_theory_sources.md` match the released
code (verification pass, not a writing pass).

**Deliverables.** Reviewed all three docs against `farloads/modules/__init__.py`
(the registered-module list), `models.py` (`Project` slices, `SCHEMA_VERSION`),
`registry.py`/`workflow.py`, and recent `CHANGELOG.md`/history entries.
`PROJECT_GUIDE.md` and `20_theory/00_theory_sources.md` matched the code with
no changes needed. `PROGRAM_SPEC.md` had one gap: `body_loads.py` (registered,
shipped in Step C6) was documented only as a subordinate mention inside
SELECT's write-up, with no `### body_loads` entry of its own (unlike
`configuration`, its sibling "modern addition"), and the cross-module
field-ownership table omitted the `fuselage_mass` slice it reads. Fixed by
adding a full `### body_loads — Fuselage net-load distribution (Step C6)`
entry (FAR §/Source/Reads/Writes/Validation/Notes, matching the template) and
a `fuselage_mass | direct input | body_loads` row to the ownership table.

**Test / Acceptance.** Cross-checked the new entry's Reads/Writes claims
directly against `farloads/modules/body_loads.py` (it calls
`select.select_fuselage(project)` rather than reading a persisted
`Project.envelope.critical` slice, and reads `Project.tail_loads`/
`Project.fuselage_mass`) and `models.py`'s `FuselageMassInput`/`FuselageStation`
dataclasses before writing the doc text, so the fix itself doesn't introduce
new drift.

**Key decisions.** No code/schema change — docs-only. Did not flag anything
already tracked as an open item in `docs/30_future/00_backlog.md` (known-open
≠ drift).

---

## Release 0.2.0 — Step R4: archive verification baseline (complete)

**Objective.** `RELEASE_PROCESS.md` §4.4 — create a permanent regression-
baseline artifact recording every printed Appendix A/B figure the test suite
locks against, since none existed yet.

**Deliverables.** `docs/40_history/01_verification_baseline_0.2.0.md`: one
table per module — condition, printed figure, reference-page citation,
tolerance — for all 22 ported Appendix-C programs plus the two modern
modules (`configuration`, `body_loads`), extracted directly from the current
`tests/test_*.py` assertions (fanned out across four parallel read-only
sweeps of the test files, one per pipeline stage: mass/geometry/speeds;
envelope/critical; wing/tail component loads; control-surface/engine/gear/
body). Modules with no printed oracle — ONENGOUT, the LANDLOAD wheel-load
table past the legible p231 spot-check cells, AIRLOAD4's swept branch, the
FAR 25 optional engine cases, `body_loads`, `configuration`, and concept-mode
AIRLOADS/NETLOADS — are recorded in a dedicated "Closure-locked modules"
section with the specific closure or sub-formula check each relies on,
instead of an invented printed figure. Also captures the WTENV aft-gross-
ballast-station approved deviation and the AC 23-19A engine-torque
corrections (ENGLOADS), calling out the manual's raw pre-correction figure
alongside the corrected value the code asserts.

**Test / Acceptance.** Every row traces to a currently-passing assertion; the
document states the run it was extracted against (`pytest`: 257 passed, 0
failed, coverage ~92%, `ruff check farloads/ cli.py` clean) rather than
re-deriving numbers by hand. No code/schema change — docs-only.

**Key decisions.** Presented as "what the suite locks against" (printed
figure + tolerance + citation) rather than a duplicate "computed" column,
since a passing `math.isclose` assertion already proves computed == printed
within tolerance; re-stating the computed number would just be the same
literal copied twice.

---

## Release 0.2.0 — Step R5: version bump + changelog dating (complete)

**Objective.** `RELEASE_PROCESS.md` §4.1–4.2 — bump the package version and
date the changelog so the release is cuttable.

**Deliverables.** `pyproject.toml` `version` `0.1.0` → `0.2.0` (MINOR: new
modules ported and new GUI/CLI capability since `0.1.0`, per §1's version-
numbering table). `CHANGELOG.md` `[Unreleased]` renamed to
`## [0.2.0] — 2026-07-08`, with a fresh empty `[Unreleased]` opened above it.
No code/schema change.

**Test / Acceptance.** `pytest` and `ruff check farloads/ cli.py` unaffected
(metadata-only change); `grep version pyproject.toml` shows `0.2.0`.

**Key decisions.** None — mechanical application of §4.1–4.2's two steps.

---

## Release 0.2.0 — Step R6: tag & GitHub release (complete)

**Objective.** `RELEASE_PROCESS.md` §4.3 — tag the version-bump commit and
publish the GitHub Release.

**Deliverables.** Annotated tag `v0.2.0` (`git tag -a v0.2.0 -m "Release
v0.2.0"`) on `50e2c9c` ("Version bump and change log", the commit where
`pyproject.toml` reads `0.2.0`), pushed to `origin`. GitHub Release `v0.2.0`
published from that tag with the `CHANGELOG.md` `[0.2.0]` section as the
release body. No code/schema change; user-run per `CLAUDE.md` (all git/GitHub
actions are the user's to execute).

**Test / Acceptance.** `git ls-remote --tags origin` shows `v0.2.0` resolving
to `50e2c9c`; GitHub Release page confirmed published.

**Key decisions.** A `v0.2.0` tag already existed pointing at `a182006`
("Archive verification baseline", release step R4) — one commit *before* the
version bump, where `pyproject.toml` still read `0.1.0`. Deleted that tag
locally and on `origin` and recreated it at `50e2c9c` so the released tag
matches the versioned commit, rather than leaving the release one commit
short of its own version bump.

---

## Release 0.2.0 — Step R7: post-release (complete)

**Objective.** `RELEASE_PROCESS.md` §5 — close out the release-priority work
in the backlog now that `0.2.0` has shipped, and hand off to the next active
step.

**Deliverables.** Removed the "Release 0.2.0 — priority work" section (steps
R1–R7) from `docs/30_future/00_backlog.md` in full — all seven steps closed,
nothing open remains for the release. Updated the Phase D intro in the same
file: the release gate is recorded as met (tag `v0.2.0` on `50e2c9c`, GitHub
Release published, 2026-07-08) and **Step D1 (structured load-case IDs)** is
marked the active step.

**Test / Acceptance.** N/A — docs-only backlog/history bookkeeping; no
code/schema change.

**Key decisions.** No new defects surfaced during final release testing, so
§5's "add any new defects found" bullet is a no-op this release.

---

## ULTIMATE load output with a per-case factor of safety (complete)

**Objective.** The suite emitted LIMIT loads everywhere, so downstream structural
sizing (the sbeam FORCE/MOMENT export and the load-case CSV) consumed limit loads
where it needed ULTIMATE, producing spurious sizing failures. Report ultimate =
limit × factor of safety and state the factor, keeping the factor **per-case** (14
CFR 25.302 / Appendix K make it failure-probability-dependent).

**Deliverables.**
- `constants.ULTIMATE_FACTOR = 1.5` (14 CFR 25.303) and a per-case
  `ConditionResult.safety_factor` (default 1.5).
- `report.py`: a unit-gated `_is_load_unit` classifier scales only force/moment/
  pressure quantities; `load_cases_to_rows` (new `SF` column, `ULT`-marked headers),
  `results_to_rows`, `text_report` and `module_text_report` now report ultimate.
- `export/sbeam_bridge.py`: wing/body/tail/control-surface FORCE/MOMENT cards,
  span-load CSVs and closure comments scaled to ultimate (`_SF`).
- `reference/14CFR_factor_of_safety.md` documenting the FS basis.
- Docs synced: `PROGRAM_SPEC.md`, `PROJECT_GUIDE.md §5`, `theory_sources.md`,
  `01_concept_loads_plan.md` (C4), `CHANGELOG.md`.

**Test / Acceptance.** Calc oracle tests unchanged (assert on the calc's LIMIT
`run()` results). Render/export tests updated to ultimate: `test_report.py` adds
ultimate-value + `SF`-column + locations-unscaled asserts; `test_io.py` checks the
`SF`/`ULT` header; `test_sbeam_bridge.py` closure now sums to 1.5 × root/total. Full
suite green (254 passing); `ruff` clean.

**Key decisions.** (1) Apply the factor at the **render/export boundary only** — the
calc stays oracle-locked, so Appendix A/B regressions are unaffected. (2) Factor is
**per-case** (the hook for a future 25.302/Appendix K probability curve), but every
case is **1.5** today, including **sudden engine stoppage** (held conservative; the
1.0 relief floor is reserved for failures substantiated at ≤1e-9/flt-hr). (3) Scaling
is **unit-gated** so weights/inertias/geometry/load-factors are never scaled, which
makes "all rendered output → ultimate" safe for the mass-properties modules that share
the renderers.

---

## Reduced the FAR 25 supplement to the non-duplicative cases (complete)

**Objective.** After the AC 23-19A correction factored the FAR 23 takeoff case, the
FAR 25 torque cases became near-identical to the FAR 23 set for a turbopropeller. Trim
the opt-in superset to only what is genuinely additive, removing the duplication that
was doubling the load-case CSV with equal numbers.

**Deliverables.**
- `farloads/modules/engine.py`: removed `condition_25_361_a1i/_a1ii/_a1iii` — for a
  turbopropeller they are bit-for-bit equal to the corrected
  23.361(a)(1)/(a)(2)/(a)(3). `run_far25` now returns only the three additive cases:
  `condition_25_361_a3i` (stoppage + 1g vertical), `condition_25_361_a3ii` (max engine
  acceleration torque — no FAR 23 analog), `condition_25_371` (gyro on the A2 vertical).
- The additive cases stay **behind `Project.include_far25`** rather than being folded
  into the FAR 23 path: making them unconditional would change the Appendix B turboprop
  case count (6) and gyro vertical (2.5g), breaking oracle-lock. `Project.include_far25`,
  `EngineInput.max_accel_torque`, and the JSON/units plumbing are unchanged.
- GUI checkbox relabelled "Add **supplemental** FAR 25 cases" with help text explaining
  the duplicates were dropped (`app/views/engine_mount.py`).
- Docs synced: PROGRAM_SPEC § ENGLOADS, PROJECT_GUIDE §3.4.4, theory sources, CHANGELOG.

**Test / Acceptance.** `tests/test_engine_far25.py` updated: the duplicate-case tests
were removed and replaced by `test_far25_supplement_drops_duplicate_torque_cases`
(asserts `run_far25` = `[25.361(a)(3)(i), 25.361(a)(3)(ii), 25.371]`); the turboprop
opt-in count is now 6 + 3 = 9 (was 12). Full suite green (`ruff` clean, `pytest` 252
passing).

**Key decisions.** Chose *partial* removal over deleting the whole FAR 25 block — the
max-engine-acceleration-torque case (25.361(a)(3)(ii)) has no FAR 23 equivalent and can
govern, and the stoppage-with-1g / A2-gyro cases add marginal conservatism. Kept the
opt-in gate (not unconditional) to preserve the oracle lock.

---

## Correction — FAR 23.361(a)(1) takeoff-torque factor (AC 23-19A) (complete)

**Objective.** Correct a non-conservative error inherited from the original
ENGLOADS.BAS / McMaster manual: the 23.361(a)(1) takeoff-case engine torque was left
**unfactored**, encoding the **Amendment 23-26** drafting error that **AC 23-19A**
identifies (it "failed to require the multiplying factor," yielding lower loads) and
that **Amendment 23-45** corrected — 23.361(c) applies the mean-torque factor to all
of paragraph (a).

**Deliverables.**
- `condition_361_a1` now applies `factor × mean takeoff torque` (`torque_factor`,
  i.e. 1.25 turboprop / 1.33·2·3·4 by cylinder), echoes the torque factor + mean
  takeoff torque, and carries an explanatory `note`. IO-520-BB takeoff mount torque
  554.39 → **737.34 ft-lb**; turbopropeller → 1.25× mean takeoff = identical to
  25.361(a)(1)(i).
- `reference/AC_23-19A_engine_torque.md` — verbatim AC 23-19A policy + corroborating
  2013 CFR text (the citable basis).
- CLAUDE.md gains an **"Approved corrections to the source"** policy (deviations from
  the oracle allowed only when user-approved *and* documented) with this correction
  recorded; PROGRAM_SPEC, theory sources, CHANGELOG updated.

**Test / Acceptance.** `test_361_a1` asserts the corrected −737.34 ft-lb (and retains
554.39 as the "mean takeoff torque" figure for traceability). Full suite green
(`ruff` clean, `pytest` passing).

**Key decisions.** Approved as a documented deviation from the Appendix A oracle (the
manual reproduces a rule the FAA declared defective). The replication charter is
preserved for everything else; the manual's original figure is retained in the test
as the unfactored mean torque so the deviation stays traceable.

---

## Optional FAR 25 engine cases — concept superset (complete)

**Objective.** Let the engine-mount module emit the **14 CFR 25.361 / 25.371**
engine-torque cases as an *additive, opt-in* superset on top of the oracle-locked
FAR 23 set, for the concept-loads direction — without altering FAR 23 output or its
appendix regression.

**Deliverables.**
- `Project.include_far25` (default `False`) + optional `EngineInput.max_accel_torque`
  (ft-lb; blank → `max_engine_torque`); both round-trip through `io.py`, and
  `max_accel_torque` is unit-converted in `units.to_imperial`.
- `farloads/modules/engine.py`: six new turbopropeller-only conditions —
  `condition_25_361_a1i/_a1ii/_a1iii/_a3i/_a3ii` and `condition_25_371` — assembled
  by `run_far25(inp)` and appended by `run_all(inp, include_far25=...)` /
  `run(project)`. The FAR 23 functions are untouched (oracle lock preserved by
  construction). 25.371 reuses the fixed FAR 23.371(b) rates (2.5/1.0 rad/s) as a
  conservative concept stand-in for the maneuver-derived rates the rule references,
  with the vertical load on the A2 limit load factor. *(Superseded — see "Reduced the
  FAR 25 supplement to the non-duplicative cases" above: `_a1i/_a1ii/_a1iii` were
  later removed as duplicates of the corrected FAR 23 set, leaving three cases.)*
- GUI: an **"Add FAR 25 cases"** sidebar checkbox + a FAR-25-only max-accel-torque
  input on `app/views/engine_mount.py`.
- `reference/14CFR_Part25_engine_torque.md` — verbatim 25.361 + 25.371 source text
  (user-supplied from eCFR), the citable basis for the equations.

**Test / Acceptance.** `tests/test_engine_far25.py` (+13) — formula-closure (no
Part-25 oracle exists): FAR 23 unchanged when off; recip/jet emit nothing; the 1.25
factor applied to takeoff (a)(1)(i) = 1.25× the FAR 23 takeoff torque; max-accel
default + override; 25.371 on A2 load factor; `Project.include_far25` JSON round-trip.
Full suite green (`ruff check farloads/ cli.py` clean, `pytest` 255 passing); GUI
`AppTest` shows six FAR 25 expanders on a turboprop with no exception.

**Key decisions.** Turbopropeller scope only — 25.361(a)(2) defines a factor only for
turbopropeller (1.25) and "other turbine engines" (= max accelerating torque), is
silent on recip, and the tool's mass/gyro math is propeller-centric. Conservative
fixed-rate gyro stand-in accepted for initial-concept use (valid while the concept's
real pitch/yaw rates stay ≤ 1 / 2.5 rad/s), flagged in the condition note and the
reference file as an assumption to revisit with real maneuver analysis.

---

## GUI — workflow-phased restructure (complete)

**Objective.** Reorganise the Streamlit UI to mirror the engineering workflow —
**Define → Analyze → Review → Export** — replacing the flat, filename-numbered page
list (which had drifted: a Phase-0 Home page, a duplicate `06_` index, no review or
export surface) with a navigation driven by a single source of truth.

**Deliverables.**
- `farloads/workflow.py` — the ordered, dependency-aware step graph. Each
  `WorkflowStep` names its calc `module` and the slices it `requires`/`produces`,
  grouped into the four phases. Pure metadata + predicates over a `Project` (no
  Streamlit), the seed of a future dependency DAG.
- `app/Home.py` rewritten as the `st.navigation` entry point: a four-phase sidebar
  built from `workflow.py`, so page order/titles come from workflow metadata, not
  filename prefixes. `set_page_config` is called once, here only.
- `app/pages/NN_*.py` → `app/views/<workflow-key>.py` (20 pages, clean names, no
  numeric prefixes — the duplicate-`06` collision is gone); each view's own
  `set_page_config` removed.
- New `app/views/dashboard.py` (Overview: load/save project + per-step completeness
  panel), `results_review.py` (Review: consolidated governing loads, recomputed live
  from inputs), `export_report.py` (Export: project JSON, per-module load CSVs +
  combined text report, sbeam wing/fuselage/tail/control-surface BDF cards, and a
  single **Download all `.zip`** bundle).
- Fixed a pre-existing crash in the engine-mount page (still used the removed
  single-engine `Project(engine=...)` API → `engines=[...]` + `SINGLE_NOSE`).

**Test / Acceptance.** `tests/test_workflow.py` (graph well-formedness; every
registered module has a step) and `tests/test_views_smoke.py` (headless `AppTest`
runs the entry point + all 20 views with the example project, asserting no uncaught
exception — the guard that would have caught the engine-mount regression). Full
suite green (242 tests).

**Key decisions.**
1. **`st.navigation`, not the implicit `pages/` directory** — explicit page list
   decouples nav order/titles from filenames and removes numeric-prefix coupling.
2. **One workflow source of truth** (`workflow.py`) drives both the nav and the
   dashboard completeness, so the GUI can never silently omit a shipped module.
3. **Consolidation pages recompute from inputs**, never from persisted result slices
   (which were only half-wired and could go stale) — Review/Export are always current.
4. **JSON stays the spine, CSV stays at the edges** — `project.json` remains the
   single typed source of truth; CSV/BDF are export-only hand-offs (CSV *import* for
   bulk tabular inputs deferred — see backlog).

---

## Phase 0 — Package restructure (complete)

**Objective.** Recast the standalone `engloads` program into the shared
pure-calc package + thin-shell architecture that every subsequent module will
follow, with the engine-mount module as the proof of pattern.

**Deliverables.**
- `farloads/` pure-calc package: `models.py` (`Project`, `EngineInput`/`Rotor`,
  `ConditionResult`/`LoadValue`, `ModuleResult`, `SCHEMA_VERSION`),
  `modules/engine.py` (port of `ENGLOADS.BAS`), `registry.py`, `io.py`,
  `units.py`, `report.py`, `constants.py`.
- `app/` Streamlit multi-page UI (`Home.py` + `pages/19_Engine_Mount.py`).
- `cli.py` argparse front-end.
- `tests/` suite vs the manual's Appendix A/B figures.

**Test / Acceptance.** Green build — full `pytest` suite passing, engine module
checked against Appendix A (p131) and Appendix B (p251) figures within ±0.1%.

**Key decisions.**
1. **Hybrid architecture** — one shared calc package, interchangeable GUI/CLI/test
   front-ends; calc does no I/O.
2. **Single reloadable `Project`** — one JSON bundle carries every module's input
   slice; `schema_version` from day one.
3. **Modernize the math** — `math.pi` and clean equations, *not* the BASIC's
   `3.1416`. The manual's printed figures become **tolerance-based** regression
   oracles (±0.1%), not exact oracles. Constants centralised in `constants.py` so
   this stays a one-file decision.
4. **Preserved engineering conventions** — engine-mount reaction torque reported
   negative; "clockwise from the pilot's view is positive"; selected intermediate
   quantities truncated to 3 decimals (`int(x*1000)/1000`) to mirror the BASIC.

---

## Phase 1 — Mass properties: WTESTIMA + WTONECG (complete)

**Objective.** Port the head of the mass-properties pipeline: weight estimation
(`WTESTIMA`) and one-loading weight/CG/inertia (`WTONECG`), establishing the
shared `Project.weight` slice the downstream load modules will read. `WTENV` was
**re-scoped to Phase 2** (its structural-CG-limit math needs `XLEMAC`/`MAC` from
`WINGGEOM`); see the backlog.

**Deliverables.**
- `farloads/models.py` — `Project.weight` slice (`WeightInput`) carrying mission
  `estimation` inputs (`WeightEstimationInput`) and the itemized `items` mass list
  (`MassItem`), plus `EngineWeightType` and `MassItemKind` enums.
- `farloads/modules/weight_estimate.py` (`WTESTIMA.BAS`) and
  `farloads/modules/weight_onecg.py` (`WTONECG.BAS`), self-registered as
  `weight_estimate` / `weight_onecg`. Mass-properties constants and the
  installed-engine-weight correlation centralised in `constants.py`.
- `farloads/io.py` — `weight_from_dict`/`weight_to_dict` wired into the project
  JSON round-trip; `load_cases_csv` falls back to the generic property table for
  modules that emit no structural load cases.
- `report.module_text_report` and a generalised `cli.py` text path so non-engine
  modules render to stdout.
- `app/pages/01_Weight_Estimate.py`, `app/pages/02_Weight_CG_Inertia.py` (Imperial
  units; the CG page edits the weight data base in a `st.data_editor`).
- `examples/ga6_normal.project.json` extended with the Appendix A weight slice;
  `tests/test_weight_estimate.py` and `tests/test_weight_onecg.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing with the coverage floor held (≥80%). `WTESTIMA` reproduces
Appendix A p133 exactly (integer-truncated figures); `WTONECG` matches Appendix A
p136 within ±0.1% (weight and lb-in² accumulators are g-independent and exact).

**Key decisions.**
1. **One input slice, pure-calc outputs.** `Project.weight` is the shared input
   "weight database"; modules stay pure (`run → ModuleResult`). No persisted
   `Project.mass` slice yet — it is added when a consumer (FLTLOADS/LANDLOAD)
   exists.
2. **Property table, not load cases.** Mass-properties results render via
   `results_to_rows`/`module_text_report`, not the engine-specific
   `load_cases_to_rows`.
3. **Force vs mass units.** A weight is pounds-*mass* and must convert to kg, but
   a load in `lb` is pounds-*force* and converts to N — the same `"lb"` label.
   `LoadValue` gained an optional `quantity` hint; a weight sets `quantity="mass"`
   so `units.py` routes it to kg, while loads (blank hint) convert by unit string
   to N. Inertia (slug-ft²/lb-in²) → kg·m². The mass-properties pages expose an SI
   output toggle on this basis; inputs stay Imperial.
4. **Preserved BASIC quirks** — `INT(...)` truncation on `WTESTIMA` outputs, and
   the single-engine "misc other system wt = 0" (the program prints an unset
   variable there).

---

## Phase 2 — Geometry: WINGGEOM + first-class multi-engine (complete)

**Objective.** Port aerodynamic-surface geometry (`WINGGEOM`) — the wing's
`MAC`/`XLEMAC` seed `WTENV` and `STRSPEED` — and, alongside it, promote the engine
slice to first-class multi-engine support (resolving PROJECT_GUIDE open decision
#2) so geometry/weight/speeds can reference the engine layout now and `ONENGOUT`
can exercise it fully later.

**Deliverables.**
- **Multi-engine schema** — `EngineLayout` enum (`SINGLE_NOSE`/`TWIN_WING`/
  `QUAD_WING`, symmetric); `Project.engines: List[EngineInput]` + `engine_layout`
  with `__post_init__` count validation and a read-only `Project.engine` compat
  property. `io.py` reads the new `engines`/`engine_layout` JSON or the legacy
  single `engine` key; `modules/engine.py` `run()` loops over every engine
  (single-engine output byte-identical, multi-engine prefixed by designation).
- `farloads/models.py` — `Project.geometry` slice (`GeometryInput` →
  `SurfaceInput` per surface: LE/TE point polylines, `symmetric`, `elements`).
- `farloads/modules/wing_geometry.py` (`WINGGEOM.BAS`), self-registered as
  `wing_geometry`: strip-sum area/MAC/YBAR/XLEMAC/AR/span per surface, plus
  wing-mounted engine spanwise stations driven by `engine_layout`.
- `farloads/io.py` — `geometry_from_dict`/`geometry_to_dict`; `units.py` gained
  area (`in²`→m²) and airspeed (`knot`→m/s) SI output conversions.
- `app/pages/03_Wing_Geometry.py` (per-surface point editors, SI output toggle);
  `examples/ga6_normal.project.json` extended with wing + aileron surfaces and the
  multi-engine layout form; `tests/test_wing_geometry.py` and new multi-engine
  assertions in `tests/test_engine.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). The **wing** reproduces
Appendix A p141 within ±0.1% (AREA/SIDE 13257, MAC 69.246, YLE(MAC) 87.854,
XLE(MAC) 63.641, AR 6.095) at the manual's 20-element strip count; the aileron
exercises the unsymmetric path (checked loosely, since Appendix A does not
tabulate its element count).

**Key decisions.**
1. **Strip count is an input, oracle is H-specific.** The manual's printed figures
   *are* the `H`-element midpoint strip sum, so `elements` must match the manual's
   value (20 for the wing) to reproduce them — kept as a per-surface field.
2. **Multi-engine first-class now.** Engine list + layout modelled this phase;
   the engine module loops over engines, but one-engine-out *loads* remain at
   `ONENGOUT`. Backward-compatible: legacy single-`engine` JSON still loads.
3. **Wing is the authoritative oracle.** `XLEMAC`/`MAC` (the figures the whole
   pipeline cites) are matched tightly; secondary surfaces use the same calc.

---

## Phase 1 (deferred item) — WTENV weight/CG envelope (complete)

**Objective.** Complete the mass-properties phase by porting `WTENV` — the
discretionary-loading envelope, structural CG limits and ballast — which was
re-scoped to land after `WINGGEOM` because its limit stations need the wing
`XLEMAC`/`MAC`.

**Deliverables.**
- `farloads/models.py` — `WeightEnvelopeInput` under `Project.weight.envelope`
  (gross weight, the three %-MAC CG limits, the forward-regardless reduced weight,
  and an optional XLEMAC/MAC override).
- `farloads/modules/weight_envelope.py` (`WTENV.BAS`), self-registered as
  `weight_envelope`: empty / minimum-flight / maximum loadings; structural-limit
  stations `X = XLEMAC + pct·MAC` (reading the wing geometry through WINGGEOM's
  `surface_properties`, not re-deriving it); the forward loading envelope; and the
  ballast per limit by moment balance.
- `farloads/io.py` — envelope (de)serialization on the weight slice;
  `app/pages/04_Weight_Envelope.py`; envelope inputs in the example;
  `tests/test_weight_envelope.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). Reproduces Chapter 3 p21-22:
stations 85.1 / 77.49 / 72.64, minimum flight weight 2063 @ 73.09, maximum loading
3322 @ 84.56, and ballast weights 78 / 418 / 158 lb (forward-gross/forward-
regardless ballast *stations* also match: 80.27 / 70.97).

**Key decisions.**
1. **Read geometry, don't re-derive.** WTENV obtains XLEMAC/MAC by calling
   WINGGEOM's pure `surface_properties` on the wing surface — honouring "read
   shared, write own".
2. **Ballast is the exact moment balance.** Per Decision 3 the aft-gross ballast
   station is reported as the precise balance (~108.5 in); the original manual's
   hand calc rounded the limit station to 85.0 (giving the 103.7 its own WTONECG
   data base then carried). The ballast *weights* match exactly.
3. **Documented reference-point selection.** The ballast reference loadings are
   chosen as in the worked example (full load for aft gross; the forward-boundary
   knee for forward gross; the heaviest forward point ≤ reduced weight for forward
   regardless), reproducing all three manual ballast weights.

---

## Phase 2 — Structural design speeds: STRSPEED (complete)

**Objective.** Port the design-airspeed and limit-maneuver-load-factor module
(`STRSPEED`), which seeds the flight-envelope and control-surface load modules
(FLTLOADS, AILERON, FLAPLOAD) and shares its standard-atmosphere/Mach machinery
with `MACHLIM`.

**Deliverables.**
- `farloads/models.py` — `StructuralSpeedsInput` and the `Project.speeds` slice
  (category, design weight, stall speeds, VH, shoulder altitude, chosen speeds and
  load factors).
- `farloads/modules/structural_speeds.py` (`STRSPEED.BAS`), self-registered as
  `structural_speeds`: FAR 23.337 maneuver load factors, FAR 23.335 design speeds
  (VA/VC/VD/VF) with their minimums, and cruise/dive Mach at the shoulder altitude.
- `farloads/constants.py` — shared `standard_atmosphere(altitude)` (a, sigma, with
  the tropopause branch) plus `cruise_speed_coefficient`/`dive_ratio_coefficient`,
  reused by MACHLIM next.
- `farloads/io.py` — speeds (de)serialization; `app/pages/05_Structural_Speeds.py`;
  speeds slice in the example; `tests/test_structural_speeds.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). Reproduces the Appendix A V-n
table within ±0.1%: VA 121.3, VC 170, VD 212.5, VF 105.5 kt (EAS); n = +3.8 /
−1.52; MC 0.323 / MD 0.403 at the 12000 ft shoulder altitude; VC(min) 141.8 kt;
wing area 184.1 ft².

**Key decisions.**
1. **Wing area from geometry.** S is read from the WINGGEOM wing surface
   (total area in² → ft²), not re-entered — "read shared, write own".
2. **VD floor is 1.25·VC.** The worked example's governing dive-speed bound is the
   absolute FAR 23.335(b) floor 1.25·VC (212.5 kt); the gust-based K_d·VC (238 kt)
   is reported as the recommended value but not enforced, matching the manual.
3. **Shared atmosphere helper.** `standard_atmosphere` lives once in
   `constants.py` so STRSPEED and MACHLIM cannot drift; the shoulder altitude
   (12000 ft for the example) is an input.

---

## Phase 2 — Mach-limit lines: MACHLIM (complete)

**Objective.** Port the Mach-limit-line module (`MACHLIM`) — the V-vs-altitude
limit lines for the flight-limits diagram — completing Phase 2.

**Deliverables.**
- `farloads/models.py` — `MachLimitInput` on `Project.speeds.mach_limit` (MC, MD,
  shoulder/max altitudes, increment).
- `farloads/modules/mach_limit.py` (`MACHLIM.BAS`), self-registered as
  `mach_limit`: `MNE = 0.9·MD`, `MFC = 1.2·MD`, and the per-altitude
  Mach-limited equivalent airspeeds `V(M) = M·a·√σ` (reusing
  `constants.standard_atmosphere`, including its tropopause branch).
- `farloads/io.py` — nested `mach_limit` (de)serialization on the speeds slice;
  `app/pages/06_Mach_Limit.py` (with a V-vs-altitude line chart);
  mach_limit inputs in the example; `tests/test_mach_limit.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). Reproduces Appendix A p160
within ±0.1%: MNE 0.3627, MFC 0.4836, and the EAS table from V(MC) 170.16 /
V(MD) 212.31 at 12000 ft down to V(MC) 150.77 / V(MD) 188.11 at 18000 ft.

**Key decisions.**
1. **Reuses the shared atmosphere.** No second copy of the atmosphere law; the
   program's `a = 29.02` vs the helper's `29.02436` is a ~0.01% difference
   absorbed by the ±0.1% tolerance (Decision 3).
2. **Per-altitude condition rows.** Each altitude is its own `ConditionResult`, so
   the CSV/text/GUI render the limit-line table directly and the GUI can chart it.

---

## Phase C — Step C0: concept-mode foundation & mission reframe (complete)

**Objective.** Remove the two GA-only assumptions that block >12,500 lb /
greater-than-GA-seat configurations — the FAR 23.337 maneuver-load-factor
formula/cap and WTESTIMA's statistical estimate — without disturbing the
oracle-locked FAR23 path. (Prerequisite for the Phase-C concept loads tool;
narrative in [`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md).)

**Deliverables.**
- `models.py` — `StructuralSpeedsInput.category` gains `"C"` (concept), documented
  as requiring explicit `chosen_n`/`chosen_nneg`; `WeightInput.direct_totals()`
  (the direct-weight path: MTOW/OEW/useful summed from the itemized `items` by
  `MassItemKind`); `Project.is_concept` (single concept read-point); `SCHEMA_VERSION`
  bumped 1 → 2 (additive — v1 files load unchanged via the `from_dict` defaults).
- `modules/structural_speeds.py` — `_maneuver_load_factors` branches on concept,
  using the user's load factors verbatim with no FAR floor/cap; the load-factor
  result note flags the unverified extrapolation. The GA-calibrated VC(min)/VD(min)
  coefficients remain as out-of-band advisories (concept supplies chosen speeds).
- `modules/weight_estimate.py` — `run()` flags the WTESTIMA summary as a GA
  sanity estimate in concept mode; `estimate()` is unchanged so the Appendix-A
  oracle still holds.
- UI — Structural Speeds page adds the Concept (C) category with `n`/`n_neg`
  inputs and an unverified-extrapolation warning; the Weight Estimate page shows a
  concept sanity banner.
- `examples/concept_heavy.project.json` — an 18,000 lb concept commuter twin.

**Test / Acceptance.** All pre-existing tests pass unchanged (FAR23 identity
invariant). New `tests/test_concept.py` (`direct_totals` by kind; end-to-end
fixture run; IO round-trip) and concept cases in `tests/test_structural_speeds.py`
(cap bypassed; missing load factors raise). The fixture (MTOW > 12,500, user n)
runs STRSPEED and WTESTIMA end-to-end with the chosen factors (4.0 / -2.0) honoured
verbatim. **Confirmed** no hard ≤12,500 lb / seat-count assertion was load-bearing
(STRSPEED only checks `w > 0`; WTESTIMA only `engines >= 1` / `seats >= 1`; WTENV
none).

**Key decisions.**
1. **Concept is a strict superset** — `category == "C"` switches off the GA caps;
   the physics is unchanged and reduces exactly to FAR23 on GA inputs.
2. **Direct-weight = sum the itemized data base by kind** — one source of truth (no
   parallel direct-MTOW field that could disagree with the items list).
3. **Docs scope reframe landed with the plan** — CLAUDE.md / README.md /
   PROJECT_GUIDE.md were reframed when the Phase-C plan was adopted; C0 is the code.

---

## Phase C — Step C1: AIRLOADS (Schrenk spanwise lift) + TAU (complete)

**Objective.** Compute the wing spanwise lift distribution (`c·cl` span load) —
the first real distributed-load deliverable and the input every downstream
wing-load module (FLTLOADS balancing, WINGINER, NETLOADS, the sbeam export)
consumes. Method: **Schrenk's** (Reference 1 Ch 7, p46-47; CAA-accepted per CAM 04
App V) — average the planform-chord and elliptic lift distributions. (Narrative in
[`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md) §C1.)

**Equations (Ref 1 Ch 7).** Per strip (mid-station `ye`, chord `c`, width `dy`),
reusing the WINGGEOM strip integrator so stations align with the geometry table:
- additive (CL=1): `c·cl = 0.5·( mo·c/Mo + 4S/(π·B)·√(1−(2ye/B)²) )`, with
  `Mo = Σ(mo·c·dy)/(S/2)`, `S = 2·Σ(c·dy)`, `B = 2·ytip`;
- basic (twist): `Awo = Σ(mo·c·ac·dy)/Σ(mo·c·dy)`, `aa = ac − Awo`,
  `c·cl_basic = (mo/2)·aa·c`;
- combine at target CL: `c·cl = c·cl_additive·CL + c·cl_basic` (basic integrates to
  zero net wing lift);
- TAU planform correction from the `TAU.BAS` quartic curve-fit in taper ratio,
  interpolated by tip ratio (p407); wing slope `M = mo_rad/(1 + mo_rad/(π·AR)·(1+τ))`.

**Deliverables.**
- `models.py` — `AeroSurfaceInput` (section slope `mo`, taper/tip ratio, optional
  `tau` override, spanwise `twist` table, `target_cl`) + `AeroInput`; `Project.aero`;
  `SCHEMA_VERSION` 2 → 3 (additive — older files load unchanged).
- `modules/airloads.py` — registers `"airloads"`; `_tau` curve-fit helper;
  `schrenk_distribution()` returns the per-strip `SpanwiseTable` (additive/basic/
  total `c·cl` and `cl`, plus `Mo`/`M`/`τ`/`Awo`/area/span and the integrated-CL
  closure); `spanwise_distribution()` wraps it as a reportable `ConditionResult`;
  `run(project)` flags concept mode as an unverified extrapolation. Reuses
  `wing_geometry._interp_x` for chord and twist interpolation.
- `io.py` — `aero_from_dict`/`aero_to_dict` round-trip; wired into the project
  load/save. `modules/__init__.py` imports `airloads` for self-registration.
- UI — `app/pages/06_Airloads.py`: aero inputs + editable twist table, a span-load
  plot (additive / basic / total), and the recovered-CL closure metric.
- Fixtures — the GA (`ga6_normal`) and concept (`concept_heavy`) projects gain an
  `aero` wing slice (concept also gains a wing planform).

**Test / Acceptance.** New `tests/test_airloads.py` (10 tests). FAR23 oracle
(±0.1%, `math.isclose(rel_tol=1e-3)`) vs Appendix A p161-162: additive `CC(LA1)`
elem 1/10/20 = 91.05576 / 69.44847 / 31.82978, `C(LA1)` elem 1 = 0.9275981, additive
integral CL = 1.00061; basic `Awo` = 3.988146, `CC(lb)` elem 1 = +5.09762, `Clb`
elem 1 = 0.05193; area/span/AR match WINGGEOM (26513.4 / 402 / 6.095). TAU curve-fit
(square-tip `τ(λ=0)` = 0.206209; `τ = 0` at tip ratio 1). Concept closure: the
`concept_heavy` integral recovers `target_cl` and the basic distribution carries
zero net lift. IO round-trip + missing-slice `ValueError`. All pre-existing tests
pass unchanged (FAR23 identity) — 93 passing.

**Key decisions.**
1. **Full Schrenk (additive + basic + combine)** — needed to reproduce the Appendix A
   wing, which has washout (root 5° → tip 1.9°).
2. **Aero slice carries inputs; the distribution flows out as a `ModuleResult`** —
   no persisted result-in-project field until a consumer (C2) needs one (avoids
   speculative state); matches the existing module pattern.
3. **Basic-distribution fairing deferred** — the cosine fairing across a flap/aileron
   lift discontinuity (Ref 1 p47) only arises with deflected flaps and is absent from
   the Appendix A wing; left as a documented limitation for a later step.

---

## Phase C — Step C2: FLTLOADS (V-n envelope + balancing tail loads) (complete)

**Objective.** Port the FAR 23.333 maneuver + gust flight envelope and the
balancing horizontal-tail load at every corner — the candidate-condition matrix
SELECT later prunes and WINGINER/NETLOADS consume.

**Deliverables.**
- `farloads/models.py` — new **`Project.flight_loads`** input slice
  (`FlightLoadsInput`: `mac`/`wing_area_sqft`/`xw`/`zw`/`xtc`/`xtf`, reference Mach
  `mn`, altitude list, per-configuration `AeroCoeffSet` aero-coefficient polynomials
  CL(α)/CD(CL)/CM(α) + stall CLs, weight-CG `CgCase` list) and the new
  **`Project.envelope`** result slice (`EnvelopeResult.vn` / `.tail_balance`:
  `VnPoint` + `TailBalanceLoad`). `SCHEMA_VERSION` bumped to **4** (additive — older
  files load unchanged); `io.py` round-trip extended for both slices.
- `farloads/modules/flight_envelope.py` — faithful port of FLTLOADS.BAS subroutine
  **3900** (iterate AoA to the required load factor, then dynamic pressure to the
  Mach-adjusted stall line; Glauert `G/Gmn`; CLmax-vs-Mach 5th-order fit) and **4864**
  (gust load factor, FAR 23.341). Balancing
  `LT = [M(W+F) + LZ·(Xcg−Xw) − DX·(Zcg−Zw)]/(XT−Xcg)` with approximate tail CP
  (XTC≈5% / XTF≈25% tail MAC). Reads VA/VC/VD/VF, MC/MD and the limit load factors
  from STRSPEED (`design_speeds` + `_maneuver_load_factors`, the single owner).
  Registered `"flight_envelope"`; pure entry `build_envelope(project) → EnvelopeResult`.
- New Streamlit page `app/pages/07_Flight_Envelope.py` (V-n diagram + balanced-
  condition table + editable aero coeffs / CG cases). Example fixtures gain a
  `flight_loads` slice.

**Test / Acceptance.** `tests/test_flight_envelope.py` oracle-locks the Appendix A
"V-n Data" cruise matrix (p179-180) for CG1/CG2: corner speeds, load factors, α, G,
and the balancing tail load LT (e.g. STALL 1G LT 132, MAN A LT 493 / LZW 12419,
GUST +C NZ +3.96, AC ROLL LT 412, CG2 MAN A LZW 12970 / LT −59). The AoA balance
converges NZ to ±0.005 (FLTLOADS.BAS line 4130), so LT and corner speeds/factors
use tight tolerances while low-load-factor quantities use the ~0.5% convergence
floor. Concept mode checked by physics closure (the balance attains the user load
factor with no GA cap; LZ+LT = NZ·W). Full suite green (106 tests), ruff clean.

**Key decisions.**
1. **Aero coefficients are inputs** — the airplane-less-tail CL/CD/CM polynomials
   come from the Ch 7 aero-coefficients program and are entered via `AeroCoeffSet`
   (AIRLOADS/C1 does not yet emit them), faithful to the BAS prompts.
2. **Explicit CG cases, no `Project.mass`** — the balance uses the four weight-CG
   envelope cases entered directly (matching the BAS), so the original data-flow's
   `Project.mass`/WTONECG read is unnecessary for C2; seeding the CG cases from
   WTENV is a later refinement. The planned WTONECG `MassProperties` refactor was
   dropped from C2 as unneeded.
3. **Cruise scope** — the cruise maneuver+gust corner set (20 conditions); the
   flapped LANDING/ENROUTE envelopes share the balance engine and drop in later.
4. **Local atmosphere constant** — FLTLOADS' own speed-of-sound constant (518.688
   vs the shared `standard_atmosphere`'s 518.4) is replicated locally for oracle
   fidelity near the Mach cap; documented in the module.

---

## Phase C — Step C3: WINGINER + NETLOADS (wing net span loads) (complete)

**Objective.** The headline structural deliverable: net spanwise wing **shear,
bending moment and torsion** (air load + inertia) along the 25% chord at the
critical conditions.

**Deliverables.**
- `farloads/models.py` — new **`Project.wing_mass`** input slice (`WingMassInput`:
  panel weight, tip/root area-density ratio, inboard rib, wing-reference-plane
  waterline + dihedral, `ConcentratedWeight` list, `WingLoadCase` list) and the
  **`Project.loads`** result slice (`LoadsResult` = `wing_air`/`wing_inertia`/
  `wing_net`, each `WingLoadResult` of `WingStationLoad`). `AeroSurfaceInput`
  gains the section `profile_drag` (CDO) and `section_cm` (CM) tables.
  `SCHEMA_VERSION` 4→5 (additive); `io.py` round-trip extended.
- `farloads/modules/airloads.py` — `air_load_distribution()` (AIRLOADS load option,
  subr 4500/4600-5060): scales the C1 Schrenk section lift to the operating CL,
  builds per-strip lift/drag/moment at `Q=V²/295`, rotates by `α=CL/M−Awo`, and
  integrates tip→root to Sz/Mxx/Myy and Sx/Mzz; drag = induced `cl·ai/57.3` +
  profile CDO.
- `farloads/modules/wing_inertia.py` (`register("wing_inertia")`) — tapered
  panel-mass distribution (root density iterated to panel weight), 1g-vertical /
  1g-drag / unit-roll unit cases combined per `(Nz, Nx, UNB)`; concentrated
  weights as spanwise steps.
- `farloads/modules/net_loads.py` (`register("net_loads")`) — net = air + inertia
  per station; per-station CSV (`wing_load_rows`). The C3-before-SELECT bridge:
  `Nz=−NZ`, `Nx=−DX/W`, CL/V read from the FLTLOADS `envelope.vn` point.
- New Streamlit page `app/pages/08_Net_Wing_Loads.py` (air/inertia/net shear, BM,
  torsion plots + station table + CSV). Example fixtures gain a `wing_mass` slice
  (and the GA wing aero gains `tau=0.05`, profile drag and section CM).

**Test / Acceptance.** `tests/test_wing_inertia.py` + `tests/test_net_loads.py`
oracle-lock the Appendix A worked example to ±0.1%: the air-load Case 22 PHAA
table (p206 — root Sz +6470, Mxx +516955, Myy −79003, Mzz −91283), the WINGINER
density (2.213/2.102 lb/ft²) and unit/combined inertia tables (p217-221), and the
Net Loads Case 22 table (p222 — root Sz +5837, Mxx +455555, Myy −60940). Concept
mode checked by the net = air + inertia identity and a trapezoidal-Schrenk root-BM
closure. Full suite green (123 tests), ruff clean.

**Key decisions.**
1. **Air-load shear/BM/torsion lives in AIRLOADS** (its "load distribution" option),
   not NETLOADS — faithful to the original; NETLOADS is the algebraic sum.
2. **TAU = 0.05 override** on the GA wing aero reproduces the manual's printed wing
   lift-curve slope exactly (C1's computed 0.0397 differs), making the full
   distribution oracle-exact; C1's oracle is independent of TAU.
3. **Full fidelity** — all of Fx/Fz/Sx/Sz/Mxx/Myy/Mzz (added the section profile-drag
   and pitching-moment inputs the drag/torsion components need), per the locked C3
   scope decision.
4. **Explicit load cases / no `Project.mass`** — the critical conditions come from
   the V-n matrix (C2) as `WingLoadCase`s (SELECT, C6, will pick them automatically);
   `Nz`/`Nx` default from the V-n point. Concentrated wing masses are supported.

---

## Phase C — Step C4: sbeam export bridge (complete)

**Objective.** Turn the NETLOADS net wing load into an sbeam-consumable
structural load set, proving the sbeam integration on the wing vertical slice.

**Deliverables.**
- `farloads/export/` — new output-renderer subpackage (pure strings + thin
  `write_*` wrappers; **not** a registered calc module).
  - `coordinates.py` — FAR23LOADS station-X / butt-Y / waterline-Z inches → sbeam
    global CID 0, identity map (single edit-point for any future sign/axis/unit
    change).
  - `sbeam_bridge.py` — consumes `Project.loads.wing_net` (accepts a `Project`, a
    list of `WingLoadResult`, or one result) and emits: (1) `span_load_csv` (one
    row per station per case: applied nodal `Fx/Fz/My` + cumulative
    `Sx/Sz/Mxx/Myy/Mzz`); (2) `force_moment_cards` — comma free-field unit-scale
    `FORCE, SID, GID, 0, 1.0, Fx, Fy, Fz` / `MOMENT …` (`%.6E`, ~zero components
    skipped), one SID per case, mirroring `sbeam/results/load_export.py`; (3)
    `stick_model_bdf` — a minimal SOL 101 CBAR cantilever (root clamp node + GRID
    per station + CBAR chain + PBAR/MAT1 placeholder + SPC1 + one subcase/load set
    per case).
- The applied nodal load at each station is the **increment of the cumulative**
  NETLOADS column (`dFz[i]=sz[i]−sz[i+1]`), so the FORCE set sums to the root
  shear and the MOMENT(My) set to the root torsion exactly, and (under the
  WINGINER quadrature `y[i]−y[0]=i·dy`) the FORCE moments reproduce the root
  bending exactly.
- `cli.py` — `--export-sbeam <prefix> <project.json> [--stick-model]` writes
  `<prefix>.span_loads.csv`, `<prefix>.loads.bdf` (and `<prefix>.stick.bdf`).

**Test / Acceptance.** `tests/test_sbeam_bridge.py` (10 tests) validates by
closure (no printed oracle in concept mode): re-summed FORCE/MOMENT = NETLOADS
root totals (exact); a **self-contained** free-field reader (no sbeam import)
round-trips the cards; stick-deck structure (one root clamp, connected CBAR
chain, one load set per case) and station-grid geometry checked; runs on both the
GA and concept examples. Manually verified that the real sbeam
(`/Users/seanomeara/Documents/99-Tests/sbeam`) parses the deck and **solves all
SOL 101 subcases** (`run_sol101`) with the load sets summing to the NETLOADS root
shear. Full suite green (133 tests), ruff clean.

**Key decisions.**
1. **Export bridge, not a calc module** — `farloads/export/` is a renderer
   alongside `io.py`; physics stays in `modules/net_loads.py`.
2. **Increment-of-cumulative nodal loads** — gives exact force/torsion/bending
   closure even with concentrated wing masses, since the cumulative columns
   telescope.
3. **Card style copied from sbeam** — comma free-field, unit scale + `%.6E`
   components, one SID per case, matching `sbeam/results/load_export.py`.
4. **Self-contained test parser** (no sbeam dependency in CI); the
   parses-and-solves-in-sbeam check is a documented manual step.
5. **Stick model behind a flag** — both deliverables (load-cards-only for splicing
   into a user's model, and the auto stick model) per the C4 working assumption;
   nominal placeholder PBAR/MAT1 (reactions are stiffness-independent for the
   determinate cantilever).

---

## Phase C — Step C5: Configuration & Layout page + fleet assessment (complete)

**Objective.** Satisfy "assess the configuration against similar airplanes": a
modern Configuration & Layout page that owns the high-level parametric geometry,
derives the wing/stability/gear assessment, seeds the geometry downstream, and
places the design against an extended reference fleet. No original `.BAS`; **no
manual regression oracle** (Appendix A/B geometry used only as a sanity fixture).

**Deliverables.**
- `models.py` — new `Project.configuration` slice (`LayoutInput`: fuselage L/W/H +
  datum; parametric wing area/AR/taper/dihedral/LE-sweep/LE-root/root-waterline;
  H/V tail areas + arms; gear nose/main stations, track, height). `SCHEMA_VERSION`
  bumped 5 → 6 (additive); `io.py` round-trip extended (`configuration_*_dict`).
- `modules/configuration.py` (pure, registered `"configuration"`) — trapezoidal
  wing planform → WINGGEOM LE/TE polylines; MAC/XLEMAC/Y_MAC/AR/span obtained by
  running the generated polylines through the WINGGEOM strip integrator (WINGGEOM
  stays the owner); tail-volume neutral point + static margin; tip-back / overturn
  angles; prop ground clearance.
- `app/pages/00_Configuration_Layout.py` — fuselage/wing/tail/gear input groups,
  Plotly three-view (top/side/front) with CG (25% MAC) and neutral-point markers,
  assessment panel, a "Seed wing geometry (WINGGEOM)" button, and a fleet
  comparison (W/S-vs-W/P and MTOW-vs-OEW).
- `app/data/reference_aircraft.csv` — extended with a heavier/concept tier (twin
  pistons, commuters, a bizjet, light transports); jets carry `max_hp = 0` and are
  excluded from the W/P plot.

**Test / Acceptance.** `tests/test_configuration.py` — analytic-vs-WINGGEOM-strip
MAC/Y_MAC/XLEMAC consistency ±0.1%; area/AR round-trip; Appendix A trapezoid
plausibility (MAC 69.246 / MAC butt line 87.854 within ±10%, the real wing having
an inboard strake); stability + gear quantities present when data given.
`tests/test_io.py` configuration round-trip; `tests/test_reference_aircraft.py`
extended for the new tier. Full suite green; `ruff` clean.

**Key decisions.**
1. **WINGGEOM stays the MAC owner** — configuration generates polylines and reads
   MAC/XLEMAC back from `wing_geometry.surface_properties` rather than integrating
   independently (per the "don't recompute another module's quantity" rule).
2. **First-order estimates, flagged** — tail-volume NP (`h_acw=0.25`, `a_t/a_w=1`,
   `1−dε/dα=0.6`), CG at 25% MAC when no mass slice is present; concept-mode results
   labelled unverified extrapolation. No oracle (documented).
3. **Seeding scoped to WINGGEOM** — the wing surface seed is enough for WTENV /
   STRSPEED (they read `XLEMAC`/`MAC`/area from `Project.geometry`); WTONECG station
   seeding and engine write-back deferred (recorded in the backlog).

---

## Phase C — Step C7: TAILDIST + AIRLOAD4 (complete)

**Objective.** The chordwise horizontal/vertical-tail load distribution for
SELECT's critical tail conditions (TAILDIST, Reference 1 Ch 10), and the
sweepback / high-Mach spanwise-airload branch for concept jets (AIRLOAD4,
Ch 12). The FAR23 path is oracle-locked against the Appendix A chordwise tables;
concept mode reduces to it on GA inputs.

**Deliverables.**
- `modules/taildist.py` (registers `"taildist"`) — `chordwise_pressures()` builds
  the five-station net pressure profile (additive angle-of-attack distribution at
  25% chord + camber distribution at 50% chord, TAILDIST.BAS subroutine 3000) for
  each critical h-tail / v-tail condition; `build_tail_chordwise()` reads
  `Project.envelope.critical` (SELECT) + the chordwise geometry and persists
  `Project.loads.tail_chordwise`.
- `modules/select.py` — every h-tail / v-tail `CriticalCondition` now carries the
  rational `lt25`/`lt50` split (balancing / unchecked / checked / gust /
  unsymmetrical / rudder / yaw / side-gust), the uniform TAILDIST input.
- `modules/airloads.py` — the AIRLOAD4 swept branch (`_apply_sweep`,
  `use_airload4`): the Pope & Haney sweep redistribution of the additive Schrenk
  span load, auto-selected when 25%-chord sweep > 15° or design Mach > 0.4, exactly
  identity at zero sweep / low Mach.
- `models.py` — `TailLoadsInput.htail_semispan_in`, `VTailLoadsInput.vtail_span_in`,
  `AeroSurfaceInput.sweep_deg`/`design_mach`, the `TailChordResult`/`TailChordStation`
  result types on `LoadsResult.tail_chordwise`, `CriticalCondition.lt25`/`lt50`;
  `SCHEMA_VERSION` 11 → 12 (additive, older files load unchanged).
- `io.py` — `tail_chordwise` + `CriticalCondition.lt25`/`lt50` round-trip;
  `export/sbeam_bridge.py` — `tail_chordwise_csv` / `tail_force_moment_cards`
  (FORCE set scaled to the total tail load); `cli.py` — `--export-target tail`.
- `app/pages/11_Tail_Distribution.py` — the chordwise tail-distribution page.
- `examples/ga6_normal.project.json` — the Appendix A tail slices + chordwise spans.

**Test / Acceptance.** `tests/test_taildist.py`: the Appendix A "Chordwise
Distribution of Tail Loads" oracle — all **13 horizontal** (p237) + **4 vertical**
(p245) conditions' `PSI(X1..X5)` within ±0.1%; the SELECT→TAILDIST pipeline (9
flaps-retracted h-tail + 4 v-tail); the AIRLOAD4 reduction invariant + swept
closure; the schema-12 round-trip (older files still load). 174 tests pass.

**Key decisions.**
- **Full-area unified form.** TAILDIST.BAS halves the both-sides `LT25/LT50` over
  the half (LH) tail area; the suite stores full both-sides areas, so the two
  factors of two fold into the unified `WATT=LT25/S`, `WCAM=LT50/(S−Saft)` —
  verified to reproduce the oracle exactly (PSI(X1)=4·907.62/5320=0.682).
- **Deferred (recorded in the backlog):** the *printed* Appendix B swept spanwise
  oracle (needs a legible swept fixture; the reduction invariant + closure stand
  in), and the 4 flaps-extended chordwise rows (need the C6-deferred flapped V-n
  landing aero; `chordwise_pressures` covers all 13 rows directly).

## Phase C — Step C8: control-surface simplified distributions (AILERON / FLAPLOAD / TABLOADS) (complete)

**Objective.** The explicit concept-tool requirement that control surfaces use
**standard simplified distributions** — port AILERON (Ch 16), FLAPLOAD (Ch 17) and
TABLOADS (Ch 18) as FAR-style simplified pressure distributions with hinge
loads + distributed loads + CSV + sbeam bridge. The FAR23 path is oracle-locked
against the Appendix A control-surface tables; concept mode reduces to it on GA
inputs.

**Deliverables.**
- `modules/aileron.py` (registers `"aileron"`) — `aileron_loads()` computes the
  deflected up/down rolling loads (`LAIL=0.04·DEFL·SA·V²/295`, the VA/VC/VD
  deflection schedule, FAR 23.455 / CAM 3.222) and the constant-LE→taper-to-TE
  pressure; `build_aileron()` returns the two `ControlSurfaceLoadResult`s.
- `modules/flap.py` (registers `"flap"`) — `flap_loads()` over the four-condition
  flaps-extended envelope (Abbott & von Doenhoff Fig 98), the momentum-theory
  slipstream (FAR 23.457(b), sub 500) and the head-on 25 fps gust (FAR
  23.345(c)(1)); reads stall speeds/VF/weight from STRSPEED, wing area from
  geometry and MAXHP/prop diameter from the engine.
- `modules/tab.py` (registers `"tab"`) — `tab_load()` per `TabSpec` at full
  deflection at VC (FAR 23.409 / CAM 3.224, trapezoid LE = 2× TE).
- `models.py` — `AileronLoadsInput`, `FlapLoadsInput`, `TabLoadsInput`/`TabSpec`
  input slices; `ControlSurfaceLoadResult`/`ControlSurfaceStation` on
  `LoadsResult.control_surface`; `Project.aileron_loads`/`flap_loads`/`tab_loads`;
  `SCHEMA_VERSION` 12 → 13 (additive, older files load unchanged). `constants.py` —
  `KT_TO_FPS_SUITE`, `DYNAMIC_PRESSURE_DIVISOR`.
- `modules/structural_speeds.py` — `design_speed_values()` exposes the scalar
  VA/VC/VD/VF + load factors the control-surface modules read (extracted from
  `design_speeds`).
- `io.py` — round-trip for the three new slices + `control_surface`;
  `export/sbeam_bridge.py` — `control_surface_csv` / `control_surface_force_moment_cards`
  (FORCE set scaled to the critical surface load, closure-checked).
- `app/pages/12_Aileron_Loads.py`, `13_Flap_Loads.py`, `14_Tab_Loads.py`.
- `examples/ga6_normal.project.json` — the Appendix A aileron/flap/tab slices.

**Test / Acceptance.** `tests/test_aileron.py`, `test_flap.py`, `test_tab.py` vs
the Appendix A reports (p200/p201/p202): aileron down 271.44 / up −180.96 lb,
psi +0.484 / −0.323; flap CLf 1.7046/1.7046/1.5593/1.5476, critical 629 lb, LE
0.545 psi, slipstream ×1.407 (BL 22.828…113.172), gust ×1.301, combined 819 lb;
tab E 0.17735, LTAB 84.62 lb, LE 0.4992 / TE 0.2496 — all within ±0.1%. Plus io
round-trip (older files load) and the sbeam control-surface FORCE-closure test.
187 tests pass.

**Key decisions.**
- **Separate per-surface input slices** (not folded into `Project.geometry`),
  mirroring `TailLoadsInput`/`VTailLoadsInput` — geometry has no hinge split.
- **Aileron oracle uses the manual's rounded VA=121**; the integrated pipeline's
  computed VA≈121.3 shifts the load ~0.3% (tested at 0.4%) — an artifact of the
  original separate-programs workflow, not an error.
- **Suite knots→ft/s factor** (`1.15·88/60`) kept verbatim for the FLAPLOAD
  slipstream so the BL band reproduces the oracle (22.828…113.172) exactly.
- **Full FLAPLOAD scope** — slipstream and head-on-gust amplifications implemented
  now (not deferred), matching the full Appendix A flap table.

## Phase C — Step C10: landing / ground loads (LGFACTOR + LANDLOAD) (complete)

**Objective.** The FAR Part 23 Subpart C ground-load conditions: the landing load
factor (LGFACTOR, FAR 23.473) and the tricycle-gear reaction loads for the level,
tail-down, one-wheel, braked-roll, side and supplementary-nose-wheel conditions
(LANDLOAD, FAR 23.473–23.499), Reference 1 Ch 20.

**Deliverables.**
- `modules/landing.py` (registers `"landing"`) — `landing_load_factor()` (LGFACTOR
  drop-test work-energy: descent `V = 4.4·(W/S)^0.25` clamped 7–10 fps, tyre/strut
  energy efficiencies, `N` and `NLG = N − L`); `landing_reactions()` (LANDLOAD: the
  drag factor `K`, ground angles, `BETA`, the `AP/BP/DP/CP` lever arms, then the 24
  main-wheel + 33 nose-wheel ground-line and airplane-datum reactions and the
  unbalanced PITCHP/ROLLP/YAWP moments); `build_landing()` resolves inputs (wing
  area from `geometry`, per-CG weight/CG from `mass` or `landing.cg_cases`) and
  persists `N → Project.landing.n`; `run()` emits one summary `ConditionResult` per
  FAR ground-load family (the critical wheel reaction).
- `models.py` — `LandingInput` + `LandingGearInput` (the dedicated `Project.landing`
  slice carrying the gear strut geometry, which has no home in the aerodynamic
  `Project.geometry`); `GearReactionCase` result record; `Project.landing`;
  `SCHEMA_VERSION` 14 → 15 (additive, older files load unchanged).
- `io.py` round-trip for the nested slice (gear tuples + CG cases);
  `farloads/__init__.py` exports `LandingInput`/`LandingGearInput`/`GearReactionCase`;
  `modules/__init__.py` self-registration import.
- `app/pages/15_Landing_Loads.py` — LGFACTOR inputs + sink-rate/factor metrics, the
  gear geometry editor, the full ground-line reaction table and CSV download.
- `examples/ga6_normal.project.json` — the Appendix A GA-6 landing slice (p230 gear
  geometry, p236 LGFACTOR inputs); the file stays at `schema_version 12` to keep the
  "old file loads under v15 code" regression coverage.

**Test / Acceptance.** `tests/test_landing.py` (9 tests). **LGFACTOR fully
oracle-locked** against Appendix A p236 (V 9.0048 / N 3.0951 / NLG 2.4281; N within
+0.07% — the Decision-3 `G=32.174` vs `32.2` drift) plus the velocity-clamp and
spring-vs-oleo branches. **LANDLOAD's gear-geometry intermediates oracle-locked**
against p230 (K 0.324, GAMMA 17.978, ground angles, BETA, the AP/BP/DP/CP table).
The printed wheel-load table (p231–233) is **OCR-garbled** in the bundled PDF, so
the 24-main/33-nose matrix is **formula-closure + legible-cell spot-checked** (case
1 VMP 3144 / VNP 1787 / nose resultant 1879; level case 4 VMP 4038 / RMP 4245; side
cases VMP 2261, SMP −1700/1122). 207 tests pass; coverage ~89%.

**Key decisions.**
- **Dedicated `Project.landing` slice** rather than overloading `geometry`
  (aerodynamic surfaces) or `configuration` (which lacks the three strut-deflection
  states, rolling radii and tail-down angle LANDLOAD needs).
- **Gear load factor is a rounded design input** (2.5 on p230), kept distinct from
  LGFACTOR's computed 2.428 (`gear_load_factor` override; 0 → use `N − L`) — the
  oracle's `NAP = NLG + L = 3.167` confirms 2.5, not 2.428.
- **OCR-garbled wheel-load table → closure + legible-cell validation** (the ONENGOUT
  C9 precedent), recorded as a deferred item: add the printed ±0.1% wheel-load oracle
  if a legible Appendix A/B or `LANDLOAD.OUT` surfaces. The light-landing CG weight
  (2803 lb) was back-solved from the legible side-load cell (½·1.33·W = 1864).
- **Terminal module** (no downstream consumer), so reactions render via `ModuleResult`
  + a `build_landing()` table rather than a persisted result slice, mirroring ENGLOADS.

## Phase C — Step C9: ONENGOUT (one-engine-out vertical-tail loads) (complete)

**Objective.** Asymmetric vertical-tail loads from a critical-engine failure
(FAR 23.367, Reference 1 Ch 11) — the first module to exercise the first-class
multi-engine `Project`. Unlike SELECT's static v-tail conditions, ONENGOUT is a
**time-marching yaw simulation**: the failed engine's thrust/windmill-drag asymmetry
yaws the airplane about its vertical axis (`IZZ`) until the pilot — at peak yaw rate
but ≥2 s after failure (23.367(b)) — applies full rudder and recovers; the headline
output is the maximum vertical-tail load.

**Deliverables.**
- `modules/one_engine_out.py` (registers `"one_engine_out"`) — `simulate()` Euler-marches
  the yaw transient (thrust `MAXHP·550·.85/VTFPS`, Glauert windmill drag, tail loads
  `LT25`/`LT50` at 25%/50% MAC, moment about the CG, integrate `THETA`/`THETADOT` to
  recovery); `run()` emits one `ConditionResult` per speed (VC ultimate / VD limit / VS)
  with engine thrust, windmill drag, max yaw rate, **max tail load**, 25%/50% MAC loads
  at peak and time to recovery; `time_history()` returns the full table on demand. Below
  VMC the run is bounded (60 s) and flagged non-recovered.
- `modules/_vtail.py` — shared v-tail aero helpers (`vtail_lift_slope` AVT,
  `rudder_effectiveness` EFFECTV, `large_deflection_factor` EF); `select.py`'s private
  `_avt`/`_effectv`/`_ef` refactored to delegate (pure refactor, SELECT oracle unchanged).
- `models.py` — `OneEngineOutInput` (failure-transient timing + failed-engine index);
  `VTailLoadsInput.xv50` (FS of 50% v-tail MAC); `Project.one_engine_out`;
  `SCHEMA_VERSION` 13 → 14 (additive, older files load unchanged).
- `io.py` round-trip for the new slice + `xv50`; `farloads/__init__.py` exports
  `OneEngineOutInput`; `modules/__init__.py` self-registration import.
- `app/pages/20_One_Engine_Out.py` — per-speed summary table + an on-demand time-history
  re-run (THETA/THETADOT and LT25/LT50/LT charts + CSV).

**Test / Acceptance.** The printed Appendix B (10-place twin turboprop) oracle is
**unavailable** — Appendix B is absent from the bundled `reference/FAR23Loads_Code.pdf`
(only the Appendix A GA single is present, physical pp. 128–247; Appendix C source from
248) and the FAA User's Guide Ch 22 gives partial/illegible inputs and **no output
numbers**. C9 is therefore locked at the **sub-formula level** (`tests/test_one_engine_out.py`:
engine thrust, windmill drag, AVT, EFFECTV exact to `ONENGOUT.BAS`) plus
**integration/physics closure** (recovery, yaw-rate peak, `DT`-halving convergence,
below-VMC non-recovery) and **refactor-parity** with SELECT's v-tail helpers. 11 new
tests; 198 pass; SELECT oracle unchanged.

**Key decisions.**
- **No printed oracle → closure + sub-formula validation** (user-confirmed), recorded as
  a deviation from the usual ±0.1% Appendix oracle because the reference data is missing,
  not optional. The printed twin oracle + an `examples/twin_turboprop.project.json`
  fixture (also unblocks the C7 swept oracle) are deferred items.
- **Reuse SELECT's validated EF chart** (`_vtail.large_deflection_factor`) rather than the
  garbled `ONENGOUT.BAS` subr-10000 OCR; the same Dommasch fig 12:3 fits both. Wiring this
  recovered curve into SELECT's static v-tail loads (replacing `rudder_large_deflection_factor=1.0`)
  is left as a deferred mini-step.
- **Output = per-speed summary, time history on demand** (user direction): the headline
  max tail load is the primary result; the full transient is recomputed for a chosen case
  in the UI and not persisted in the schema.
- **Below-VMC handling**: the march is time-bounded (60 s) and the case flagged
  "NOT recovered" rather than looped to a step cap, mirroring the manual's note that
  recovery performance is an aero/flight-test responsibility.

## Phase C — Step C6: SELECT + fuselage/body distributed loads (complete)

**Objective.** Compute the critical flight load on each major component (wing,
horizontal tail, vertical tail, fuselage) from the FLTLOADS V-n matrix (SELECT,
Reference 1 Ch 9), and emit the fuselage longitudinal net distribution (Ch 15) +
sbeam body export. The FAR23 path stays oracle-locked against the Appendix A loads
report; concept mode reduces to it on GA inputs.

**Deliverables (R1–R10).**
- `models.py` — new slices: persisted `Project.mass` (`MassResult`/`MassCase`),
  `Project.fuselage_mass` (`FuselageMassInput`/`FuselageStation`), SELECT
  `EnvelopeResult.critical` (`CriticalLoadSet`/`CriticalCondition`), the fuselage
  net result `LoadsResult.body_net` (`BodyLoadResult`/`BodyStationLoad`),
  `Project.select_input` (`SelectInput`: aileron/airfoil-cm + wing weight),
  `Project.tail_loads` (`TailLoadsInput`: h-tail geometry/aero + elevator/maneuver/
  gust fields) and `Project.vtail_loads` (`VTailLoadsInput`). `SCHEMA_VERSION`
  6 → 11 (all additive); `io.py` round-trip extended for every slice.
- `modules/select.py` (registered `"select"`) — **wing** (PHAA/PLAA/PMAA/NMAA,
  accelerated + steady-roll TORS); **horizontal tail** balancing (23.421),
  unchecked/checked maneuver (23.423), gust (23.425(a)(1)/(2)) and unsymmetrical
  (23.427(a)), flaps retracted and extended, with the exact SELECT.BAS subr-10000
  large-deflection chart; **vertical tail** (23.441(a)(1)/(2)/(3), 23.443(b));
  **fuselage** critical conditions (23.301/23.331).
- `modules/flight_envelope.py` — the flaps-extended (LANDING) V-n corner set at VF
  (FLTLOADS subr 3000), n-limited to 2 (FAR 23.345), sea level.
- `modules/body_loads.py` (registered `"body_loads"`) — Ch 15 fuselage net shear/
  bending per critical condition → `Project.loads.body_net` + CSV.
- `modules/weight_onecg.py` — `build_mass` emits the persisted `Project.mass`.
- `export/sbeam_bridge.py` — `body_span_load_csv` / `body_force_moment_cards`.
- `app/pages/09_Critical_Loads.py`, `app/pages/10_Fuselage_Loads.py`.

**Test / Acceptance.** Oracle-locked against Appendix A (±0.1%, plus FLTLOADS'
~0.5% V-n noise): wing PHAA STALL +N (CL +1.519/V 117.40), PLAA/PMAA/NMAA/ACRL/
TORS; h-tail balancing +519.85/−613.92 (Ch 9 case-202 hand-calc LT 519.845),
unchecked −1397.8/+1227.2, checked −671.5/+787.8, gust +908.6/−1292.8,
unsymmetrical −1111.8; v-tail rudder +591 / sideslip −92 / yaw-15 −526 / side gust
+604; fuselage 13347.6 / 12569.6 / −6390.3 / Nz 5.81. Modern/closure-validated:
the fuselage net distribution (equilibrium `ΣFz=0`, shear→0 aft) and the
flaps-extended tail loads (the flapped points achieve their target NZ; the rational
balancing tail load zeroes the flapped pitching moment). Full suite green; `ruff`
clean.

**Key decisions / known limits.**
1. **Modernized-math tolerances** — selected CL/V/LT inherit FLTLOADS' ±0.005-NZ
   convergence noise (~0.5%); the renumbered envelope assigns different integer case
   indices than the manual, so tests assert the selected *condition* + values, not
   the case number.
2. **Illegible effectiveness charts modelled exactly where possible** — the
   elevator/rudder large-deflection factor `EF(δ, Se/St)` is reconstructed from
   SELECT.BAS subr 10000; the v-tail rudder-deflection loads carry an `EFV≈1.0`
   factor (a `VTailLoadsInput` input, default 1.0) since its chart is illegible in
   the scan (the AoA/gust loads are exact).
3. **Flaps-extended oracle deferred** — the real landing-config aero polynomials
   (and CG5–7 loadings) are not in the repo fixtures, so R3/R4 are closure-validated
   rather than matched to Appendix A cases 81/106/88/108. Recorded as a follow-up.
   *(Update, M1-2: the landing polynomials — printed at Appendix A p179 — are now in
   the `flight_envelope` test fixture and the envelope `BAL 1.4VSF` point is
   oracle-matched at p181; the SELECT→TAILDIST cases 81/106/88/108 with the CG5–7
   loadings remain L-2.)*
4. **`Project.mass` persisted but not yet consumed by SELECT** — the checked-
   maneuver `Iyy` and v-tail `IZZ` use the documented Ch 9 approximations (which
   match the oracle); per-CG precise inertia from `Project.mass` is a follow-up.

---

## Tooling & documentation standard (complete)

**Objective.** Bring the project's tooling and documentation standard in line
with the sibling `sbeam` project before the module-porting work scales up.

**Deliverables.**
- `pyproject.toml` — editable install (`pip install -e '.[dev]'`), so `farloads`
  and `cli` import from any cwd; the `sys.path` shims were removed from `app/`.
  `ruff` (select `E`/`F`/`W`, ignore `E741`) and `pytest`/coverage config.
- `cspell.json` domain wordlist.
- `.github/workflows/ci.yml` — `ruff` + `pytest` on Python 3.9 / 3.11 / 3.12.
- `docs/` reorganised by type (`10_standard` / `20_theory` / `30_future` /
  `40_history`) with `docs/00_INDEX.md`.
- `docs/10_standard/CODE_REVIEW_PROCESS.md` and `RELEASE_PROCESS.md`;
  `CHANGELOG.md` (Keep a Changelog).
- `CLAUDE.md` mandate strengthened: consult `reference/`, keep `docs/` in sync,
  and the backlog→history→changelog move-on-completion rule.

**Test / Acceptance.** `ruff check farloads/ cli.py` clean; full `pytest` suite
passing after the `sys.path` shims were removed.

**Key decisions.**
- CI lints `farloads/` and `cli.py` (the pure calc + CLI). Streamlit pages in
  `app/` are not lint-gated: their long widget-label lines and the deliberate
  late `from farloads.modules import engine` import are acceptable there.
- `requires-python = ">=3.9"` to match `sbeam` (the code uses
  `from __future__ import annotations`, so 3.9 is safe).

---

## Phase C — Step C11: BALLOADS (balanced-tail-load verification utility) (complete)

**Objective.** Port the off-pipeline `BALLOADS.BAS` cross-check: recompute the
horizontal-tail balancing load **rationally** (AoA load at 25% tail MAC + camber/
elevator load at 50%) per flaps-retracted V-n condition and verify FLTLOADS'
*approximate* tail centre of pressure (`XTC`~5% MAC flaps-up / `XTF`~25% flaps-down,
Ch 8). This closes the **last** of Reference 1's 22 Appendix-C programs.

**Deliverables.**
- `modules/balloads.py` (registered `"balloads"`) — `verify_balancing(project)`
  iterates every flaps-retracted V-n point (the search set of SELECT's
  `select_htail_balancing`), **reuses** `select.htail_balance` for the rational
  `LT25`/`LT50`/`DELTA`/`LT`/`CP` split and `select._elevator_load` for the elevator
  load, converts the rational CP (% tail MAC) to a fuselage station `XT` and reports
  it against FLTLOADS' assumed `XTC` (`DXT = XT − XTC`). `run(project)` emits a
  `ConditionResult` per point (FAR 23.421); raises `ValueError` (skipped by
  `run_all_modules`) when `tail_loads`/`flight_loads` are absent.
- `farloads/modules/__init__.py` — `balloads` self-registration import.
- `app/pages/16_Balanced_Tail_Verification.py` — read-only report: up/down headline
  metrics + the per-condition rational-vs-approximate CP table.
- `tests/test_balloads.py` — the Ch 9 case-202 oracle and SELECT-consistency check.
- **No schema change, no new pipeline output** (a verification report only).

**Test / Acceptance.** Oracle-locked against the Ch 9 case-202 hand-calc: the
largest up balancing load is `LT = 519.845 lb` (LT25 +907.62, LT50 −387.78, δ
−5.39°, CP 6.35% tail MAC), within the FLTLOADS ±0.5% V-n noise. The rational
up/down loads equal SELECT's `BAL UP/DN RETRACTED` conditions exactly (same
routine), and the rational CP station tracks FLTLOADS' assumed `XTC`. Full suite
green (211 tests); `ruff` clean.

**Key decisions.**
1. **Reuse over re-derivation.** Per the project convention ("must not recompute a
   quantity another module owns"), BALLOADS calls SELECT's oracle-locked
   `htail_balance`/`_elevator_load` rather than transcribing `BALLOADS.BAS`'s own
   balance equations — the verification can never silently drift from production.
   The cross-check value is preserved by comparing the rational CP station to
   FLTLOADS' *approximate* `XTC`/`XTF`.
2. **Search set = all flaps-retracted points**, not only the trimmed `BAL`
   conditions: the governing case-202 up load falls on `STALL +N` (CG1, 18000 ft),
   mirroring `select_htail_balancing`.
3. **Off-pipeline.** Runs under `run_all_modules` when its slices exist but writes
   nothing to the `Project` schema — a teaching/verification report only,
   demonstrating the elevator load is not always opposite the stabilizer load.

---

## Phase D — Step D0: flight-envelope destructive slice overwrite fix (complete, 2026-07-08)

**Objective.** Close the data-loss defect found in the 2026-07-08 GUI review
before cutting release `0.2.0` (release step **R1**; §3.2 of the release process
requires no open critical findings). `app/views/flight_envelope.py` rebuilt
`FlightLoadsInput` wholesale (`configurations=[cruise]`,
`altitudes_ft=[altitude]`) on every rerun, so merely opening the page deleted
any flaps-down configuration or extra altitudes a loaded project carried.

**Deliverables.**
- `farloads/models.py` — `FlightLoadsInput.merged(...)`: a pure method that
  merges one page-edit into the existing slice. The edited altitude replaces
  `altitudes_ft[0]` (the entry a single-altitude widget displays); the edited
  configuration replaces the first entry with the same `flaps_down` state
  (appended if there is none); every other altitude/configuration is carried
  over unchanged. Returns a new instance; no I/O, no schema change.
- `app/views/flight_envelope.py` — persists via `fl.merged(...)` instead of the
  wholesale `FlightLoadsInput(...)` rebuild. Write-on-rerun behavior otherwise
  unchanged (the `st.form` + Apply conversion is Step D6 scope).
- `tests/test_flight_envelope.py` — two regression tests: a slice with a
  flaps-down configuration and two altitudes survives the persist path (edits
  land, unedited content preserved, original slice untouched); an empty slice
  simply gains the edited configuration.
- `CHANGELOG.md` `[Unreleased]` `Fixed` entry.

**Test / Acceptance.** Full suite green (257 tests, was 255); `ruff` clean;
Appendix A/B oracles unmodified (no calc-math change).

**Key decisions** (user-approved 2026-07-08).
1. **Merge helper lives on the model** (`FlightLoadsInput.merged`) — pure
   dataclass logic, directly unit-testable, and the reusable seed of the
   Phase-D "Apply merges into the project slice" page convention
   (`40_history/05_phase_d_gui_workflow_plan.md §5.2`) that Step D6 applies suite-wide.
2. **Altitude merge = replace first, keep rest** — the widget displays
   `altitudes_ft[0]`, so an edit updates entry 0 and preserves the tail; the
   real multi-altitude UI arrives in Step D5.
3. **Merge-write only** — minimal defect fix appropriate for a pre-release
   patch; the form+Apply rework stays in Step D6.

---

## Phase D — GUI: session-wide Imperial/SI toggle + Project JSON Editor (complete, 2026-07-14)

**Objective.** The Imperial/SI display toggle existed on only 5 of 24 GUI
pages, each with its own independent, uncoordinated `st.radio` (no shared
session state), and 4 of those 5 converted output only (inputs stayed
Imperial regardless). The remaining 19 pages had no SI display at all. No page
let a user review/hand-edit the project file itself in their preferred units.

**Deliverables.**
- `app/Home.py` — a single sidebar "Units" control
  (`st.session_state["unit_system"]`), read by every view; the 5 pages with a
  local radio now read this shared value instead.
- `farloads/units.py` — `to_si_scalar`/`si_scalar_label`, scalar display
  converters for per-station/per-case dataclasses (wing/fuselage/tail/
  landing-gear results) that are not `ConditionResult`/`LoadValue`-based, so
  `convert_results` doesn't reach them.
- All 19 previously Imperial-only view files wired to the shared toggle,
  display-only: metrics/tables render in the selected system, but every
  object feeding sbeam BDF export, `Project` persistence
  (`st.session_state["project"]`) or a CSV/BDF download stays canonical
  Imperial, untouched. Airspeed (KEAS) and altitude (ft) are never converted
  (aviation-standard units in both systems, an explicit user decision).
  `structural_speeds`/`mach_limit` needed no changes — every field they show
  is speed/altitude/dimensionless, already outside the toggle's scope.
- New `app/views/project_editor.py` (Start section, new `WorkflowStep
  ("project_editor", ...)` in `farloads/workflow.py`): the whole project shown
  as hand-editable JSON in the selected units. New
  `farloads.units.project_dict_to_display`/`project_dict_to_imperial` — a
  field-name-driven whole-project converter (`_PROJECT_FIELD_KIND`, audited
  against every dimensional field in `models.py`) distinct from the two
  `_lb`-suffixed *force* fields (`load_lb`, `tail_load_lb`) that must not use
  the mass factor. Apply parses the edited JSON, converts back to Imperial,
  and rebuilds the session `Project` via the existing `io.project_from_dict`;
  the sidebar's existing Open/Save/Download widget is unchanged and still
  reads/writes one Imperial `project.json`, unmodified format, no unit tag.
- `tests/test_project_units.py` — round-trip fidelity on all 4 example
  projects, a regression test pinning the mass-vs-force `_lb` distinction to
  its correct (different) factors, and confirms airspeed/altitude/unknown
  fields pass through unconverted.
- `CHANGELOG.md` `[Unreleased]` `Added` entry;
  `docs/10_standard/PROJECT_GUIDE.md` file-tree + units-convention updates.

**Test / Acceptance.** Full suite green (297 tests, was 290); `ruff` clean; a
`streamlit.testing.v1.AppTest` sweep of every view file against 2 example
projects, in both unit systems, found zero new exceptions (one pre-existing,
unrelated `st.number_input` `max_value` issue on `weight_estimate.py`,
reproduced identically on the pre-change branch). No calc-math change, no
`SCHEMA_VERSION` change (still 19).

**Key decisions** (user-directed 2026-07-14).
1. **One session-wide toggle, not per-page.** A structural engineer needs
   consistent units across a session; per-page-independent toggles (the prior
   state) risked a wing sized in SI next to a fuselage read in Imperial.
2. **`project.json` stays Imperial-only.** Rejected tagging the file with a
   stored unit system (see the in-conversation risk review): the schema's
   field names are themselves unit-suffixed (`_lb`, `_in`, `_kt`...), so a
   file whose *content* changes meaning under a stored flag while its *field
   names* don't would silently mislead a hand-editor. The Project JSON Editor
   page solves the actual need (review/edit in preferred units) at the
   display layer instead, with no schema/migration risk.
3. **KEAS/ft stay aviation-standard in SI mode.** Airspeed and altitude are
   never converted by this toggle, in either the per-page views or the whole-
   project editor.
4. **Weight-database externalization considered and declined.** A separate
   referenced weights (and future aero) JSON file was considered for the
   project's largest section, but rejected: it would fragment the "one
   reloadable project.json" architecture (multi-file Open/Save/upload,
   drift-if-edited-independently risk) for a problem better solved by a
   readable in-app editor — exactly what this step delivers.

---

## Airplane-phase GUI usability pass: tail geometry, wing planform plot, aero-data naming (complete, 2026-07-14)

**Objective.** A GUI review requested by the user (mental model: Geometry →
Weight/CG → Three-view → Aerodynamic data) found the existing 6-step Airplane
phase already matched that order structurally, but with three real gaps: (1)
the three-view (`configuration_layout.py`) drew wing/fuselage/gear/CG/NP but
**no tail at all** — `LayoutInput` stored the tail as area+arm only, with no
type or enough geometry to sketch one; (2) `wing_geometry.py` (WINGGEOM
surface-polyline tables) had **zero visualization**; (3) aerodynamic data was
split across two schema slices in two phases (`aero_coeffs` on its own
Airplane-phase page, `aero` — per-surface spanwise Schrenk — buried inline on
the Analysis-phase Wing Loads page) with no naming/cross-link connecting them.

**Deliverables.**
- `farloads/models.py` — `TailType` enum (`CONVENTIONAL`/`T_TAIL`/`V_TAIL`/
  `CRUCIFORM`, default `CONVENTIONAL`) and four new additive `LayoutInput`
  fields (`tail_type`, `h_tail_span_ft`, `h_tail_z`, `v_tail_span_ft`, all
  zero-valued defaults). `SCHEMA_VERSION` bumped 19 → 20.
- `farloads/modules/configuration.py` — `tail_planform(layout)`, a pure
  function returning per-panel `top`/`side`/`front` outline polylines for the
  three-view, branching on `tail_type` (T-tail places the h-tail atop the fin,
  cruciform mid-fin, V-tail derives two mirrored diagonal panels from
  `v_tail_area` at a fixed 40° dihedral instead of separate h/v rectangles).
  Returns `{}` (draws nothing) when both span fields are unset, so older
  projects render identically to before this change.
- `farloads/modules/wing_geometry.py` — `surface_top_outline(le, te,
  symmetric)`, a shared presentation helper (polyline → plotly-ready top-view
  outline) used by both `configuration_layout.py` (wing outline, replacing
  duplicated inline logic) and the new `wing_geometry.py` planform plot.
- `app/views/configuration_layout.py` — tail-type selector + span/offset
  inputs in the existing form; the three-view now draws the tail panel(s) in
  Top/Side/Front alongside the existing wing/fuselage/gear/mass-item/engine
  overlays.
- `app/views/wing_geometry.py` — a lightweight top-view planform plot above
  the per-surface polyline tables, one trace per surface.
- `app/views/aero_coefficients.py` / `farloads/workflow.py` — the
  `aero_coefficients` step retitled "Aerodynamic Data" (key unchanged); a
  cross-link caption added pointing to the Wing Loads page for per-surface
  spanwise aero, with a matching caption added there pointing back.
- `tests/test_configuration.py` — 6 new tests covering each `TailType` branch
  and the empty-when-unset backward-compat case.
- Docs: `docs/10_standard/PROGRAM_SPEC.md` updated for the `configuration` and
  `WINGGEOM` module entries and the `aero_coefficients` rename; `cspell.json`
  extended.

**Test / Acceptance.** Full suite green (303 tests); `ruff check farloads/
cli.py app/` clean; `tests/test_views_smoke.py`'s headless `AppTest` sweep
passes for both changed views (this caught an initial relative-import mistake
— the shared trace helper had to live in `farloads/modules/wing_geometry.py`,
not a same-directory `app/views/_*.py` module, since Streamlit executes each
page as a standalone script, not as a package member, so `from .x import y`
fails both in `AppTest` and in the real multipage app).

**Key decisions** (user-directed, via `AskUserQuestion` during planning).
1. **Geometry editor and three-view stay one combined page**, not split into
   two — matches the existing `weight_envelope.py` precedent (edit + its own
   chart on one page) and avoids duplicating `LayoutInput` editing state
   across two `st.navigation` pages.
2. **Tail-type field and its three-view drawing built now**, not deferred —
   this was the one genuine functional gap (no tail geometry existed at all).
3. **Aero-data consolidation kept to a rename + cross-link**, not a full
   `AeroInput` migration onto the Airplane phase — moving spanwise aero input
   away from Wing Loads' immediate per-strip-distribution feedback loop was
   judged a net usability loss for a naming-only complaint.
4. **`workflow.py` step order left unchanged** — investigation found the
   existing Airplane-phase step order already matches the user's Geometry →
   Weight/CG → (three-view, combined) → Aero mental model; no reorder needed.

**Deferred (flagged as recommendations, not built this pass).** Full
`AeroInput`-onto-Airplane-phase migration if the rename+cross-link proves
insufficient; seeding `tail_type` into the example `.project.json` fixtures.

---

## Resolved defects

- **Weight Estimate page crashed opening a beyond-GA project** *(resolved
  2026-07-15)*. The Mission-inputs form hard-capped its widgets at GA-tier limits
  (`max_value = 3000 hp` / 12 seats / 6 engines / 10 hr) while seeding each widget
  from the loaded project, so a project whose stored value exceeded a cap raised
  `StreamlitValueAboveMaxError` before the page rendered (e.g.
  `examples/dhc8_dash8.project.json` at 4000 hp / 39 seats: value 2982.8 kW > max
  2237.1 kW in SI). Pre-existing (from the earlier input-units work, not Step E2,
  which only added the widget's `help=`). Fixed by removing the hard `max_value`
  caps (keeping `min_value` for physical sanity), consistent with the concept-aware
  superset that must accept airplanes beyond the GA band (`GUI_design.md §9` — warn,
  don't block; WTESTIMA's ≤12,500 lb calibration limit is surfaced as a concept-mode
  warning, not enforced on the inputs). Regression:
  `tests/test_views_smoke.py::test_weight_estimate_accepts_beyond_ga_power` loads the
  DHC-8 into the page and asserts no exception.

- **Flight Envelope page destroyed unedited `flight_loads` data** *(resolved
  2026-07-08, Phase D Step D0 / release step R1 — see above)*. Wholesale
  `FlightLoadsInput` replacement on every rerun deleted flaps-down
  configurations and extra altitudes from loaded projects. Fixed by the pure
  `FlightLoadsInput.merged()` merge-write; regression-tested in
  `tests/test_flight_envelope.py`.
