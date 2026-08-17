  # Changelog

All notable changes to **sloads** (the FAR 23 LOADS replication and
initial-concept distributed-loads tool) are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.6.0] — 2026-08-17

### Added

- **Solo close loop as scripts — `scripts/solo_start.sh` + `scripts/solo_close.sh` (issue #27, tier S, 2026-08-17).**
  `DEVELOPMENT_PROCESS.md` §0's loop is now a guarded command sequence rather
  than a chat transcript (rule 3). `solo_start.sh <issue> <type>/<slug>`
  preflights (on `main`, clean tree, `gh` authenticated, issue open, branch
  new) and opens the branch; `solo_close.sh <issue> "<Subject>"` refuses until
  the tier's `changes/` fragment(s) exist and the item's `(#N)` row has left
  the priority table, then runs gate → commit → `--ff-only` land + push →
  `gh issue close` with the `main` SHA → verify (branch delete,
  `backlog_issues.py check`, issue state, last CI run), stopping at the first
  failure with the recovery printed; `--dry-run`, `--skip-gate`, `--yes`,
  `--slug`, `--suffix`. Guard: `tests/test_solo_scripts.py` (`bash -n`,
  `--help`, dry-run step order). §0 points at the scripts. Closes #27.

- **LRA beam-model design review** (backlog band B, steps 12/13/14; design note
  `docs/30_future/24_lra_beam_model_review_note.md`, **agreed 2026-08-15**, no
  code). The user's eight-feature target — control-surface hinge/actuator nodes,
  wing side-of-body node with inboard loads summed to it, fuselage beam with
  front/rear-spar posts, fin and h-tail attachments (conventional and T-tail),
  LRA at 40 % chord / hinge line / section centre, gear and engine thrust nodes —
  measured against the shipped export code and the written plans. Establishes
  that the LRA model is a **third deliverable** (the assembled balanced deck is
  `GRID`+`FORCE`/`MOMENT` with no elements and stays so), records decisions
  **BM-1…BM-5** (SOB source, split-fuselage idealization, refuse-on-missing
  attachment data, explicit `mounted_on`, named-node contract) and re-sequences
  band B. Docs amended in the same session: backlog step 12/13/14 bodies and
  Pri 1/10/16, plan 10 §1.1 (constraint 1 scoped to the per-component deck),
  plan 11 §4 (LRA-model column, T7 transfer and engine-thrust rows), plan 09
  §10 (**T-18**, hinge-line control chains), note 21 (**P-6a**, hub/mount
  nodes), `docs/00_INDEX.md`. Standard docs, schema and `bands.py` follow the
  code per the closure tiers.
- **`CgCase` gains an explicit loading definition** (backlog Pri 6, decision
  **D-25** + D-25a…d; schema **v50**; design note
  `docs/30_future/22_d25_cgcase_loading_note.md`). A payload case could state a
  weight and a CG but not *what loading produces it*, so the mass model behind
  every case was reconstructed by searching the discretionary subsets of
  `weight.items` for something that reproduced the corner point within a credible
  ballast fraction — which reached **7 of 18** shipped cases and left four
  fixtures with no balanced case at all. `CgCase.loading` (new
  `LoadingDefinition`: items aboard, a fraction for any `consumable` row, an
  optional entered ballast row with its waterline) states it instead. The entered
  loading is **authoritative** (D-25a): the case's `weight_lb`/`xcg`/`zcg` become
  a checked echo — `max(0.5 lb, 0.1 %)` and `0.5 in` — reported by
  `mass_distribution.case_loading_checks` and as two new Weight & CG findings
  (`cg_case_loading_echo`, `cg_case_loading_invalid`), and no ballast is ever
  solved for one. The credibility gate stays on *solved* ballast only (D-25d), so
  an entered ballast exports with its fraction stated rather than being refused.
  **Optional with the search as fallback** (D-25c): every pre-v50 file loads and
  produces byte-identical output, and a case without a loading writes no
  `loading` key. First user: `concept_regional_jet`'s **CG3 fwd light** (12 %
  ballast, previously refused), which brings the fixture's `NMAA` condition into
  the assembled deck — its flight family is now complete, and the payload-case
  table in the report and on the page states `entered` or `derived` per case so
  the provenance travels with the mass model.

- **The assembled model carries the airplane's non-wing drag** (backlog Pri 5,
  design note `docs/30_future/20_body_drag_carrier_note.md`). The FLTLOADS trim
  balances the airplane-less-tail drag from the **polar**; the assembled model's
  only `fx` was the wing strips' own chordwise force, so the fuselage, nacelle
  and remaining parasite drag was simply absent — `residual_fx` *equalled* the
  wing's drag, and the couple that missing force left about the CG was the whole
  of the pre-closure pitch residual. New `balance.body_axial_set` applies it as a
  labelled `body-axial` load, spread over the fuselage outline by
  cross-section-area share where there is one. **Every family on both fixtures
  falls to the lift-model floor — 0.014–0.086 % against a 1 % gate — so the
  per-fixture pitch ceiling is retired** (`_PITCH_RESIDUAL_CEILING` becomes
  `_PITCH_RESIDUAL_RATCHET`, which records what each family actually reaches so
  the flat gate cannot pass a 12× regression in silence), and plan 13's G9
  inherits the flat gate. The longitudinal closure now reads the trim's own drag:
  ga6 PHAA `nx` 0.661 g → **0.610 g**, exactly `dx/W`.

  That the gap is genuinely parasite drag is measured, not assumed: both models
  resolve through the same `α`, so the body-axis difference decomposes exactly
  into wind-axis parts, and `ΔL/L` comes out ≤ 0.6 % while `ΔC_D` is a
  near-constant **−0.018 across all seven `ga6_normal` cases** — a `C_D` offset
  independent of `C_L`. Above `α ≈ 19°` on the regional jet it inverts sign,
  because the strip model's induced drag overshoots the polar there; that is
  reported as a case note rather than clamped, since clamping would hide it.

  New input `LayoutInput.body_drag_waterline_z` (**schema v49**, additive, no
  hop) with its single owner `derived_geometry.body_drag_waterline`. Its
  resolution order is deliberately **two branches** — explicit, else the wing
  reference plane with a loud `assumed` note. There is no geometry branch, and
  its absence is the decision: the suite has no body-centreline datum
  (`FuselageSection` carries no `z`), `root_waterline_z` is the *wing* root, and
  deriving from it would put `ga6_normal`'s `SIDE GUST` residual at −1.173 %,
  over the gate on the Appendix A fixture — as well as being a trap, since that
  fixture's `fuselage_height` is 0.0 and any geometry-conditioned branch would
  flip the first time a fixture gained a body. `BalancedCaseResult` gains
  `body_axial` and `delta_cd`; the latter is reported because carrying the load
  makes the applied axial resultant equal the trim's `dx` **by construction**, so
  the diagnostic that found the defect would otherwise vanish with it.

  Imperial baseline: only `csv/balance`, `txt/balance` and `sbeam/balanced_deck`
  moved, and only on the two fixtures with balanced cases — every per-component
  deck and every Appendix A oracle is byte-unchanged.

- **The authoritative package tree is as-built, has one owner, and is guarded**
  (0.6.0-candidate review finding **R6-D5**). `PROJECT_GUIDE.md` §4 was still the
  *proposed* restructure layout and had drifted past three SSOT owners added in
  one cycle (`cg_cases.py`, `safety_factors.py`, `gear_loads.py`) plus
  `case_ids.py`, `rigid_body.py`, `tail_geometry.py`, `aero_curves.py`,
  `migrations.py`, `spec_names.py`, the `models/` package split, and three
  `export/` lines mis-nested under `mass_distribution.py`. It is now the shipped
  tree, file for file, with a one-line purpose per module. The duplicate,
  staler tree in `00_program_overview.md` is replaced by a shape summary and a
  link (user decision: one owner). New `tests/test_package_layout.py` rebuilds
  each path from the tree's own indentation and asserts the `sloads/` half
  matches the package on disk in **both** directions — an unlisted new module,
  a listed file that does not exist, and a mis-nested line all fail; the second
  tree cannot come back. Docs and test only.

- **The ground family is in the balancing-method theory document** (0.6.0-candidate
  review finding **R6-D7**). `docs/20_theory/balanced_cases.md` described three
  families where four ship; it gains **§9 — the ground families (FAR
  23.471–23.499)**: what a ground case does not have (no V-n point, no given load
  factor, no balancing tail load, its own design weight under 23.473(a)), which
  of LANDLOAD's 33 cases assemble and why the 23.499 family does not, the applied
  set (`gear-main`/`gear-nose` with the exact patch→node transfer, `ground-lift`
  along the ground line on cases 1–12 only), the `n_z = 0` solve against FAR
  23.471 with the `NVP`/`NDP`/`NS` identity and its rotational half, `ρ` measured
  from LANDLOAD's own two resolutions, **why `RESIDUAL_GATE` does not apply** and
  the gates that replace it, and a worked example over three families on
  `ga6_normal`. §2's source table and §3's not-gated list gained their ground
  rows; the pin table is now §10, with ten ground rows. Two new tests in
  `tests/test_gear_report.py` pin every figure the new section quotes, per the
  document's own contract. Docs and test only — no shipped number moves.

- **`balance` and `tail_span` have PROGRAM_SPEC sections, and every module is
  now guarded into having one** (0.6.0-candidate review finding **R6-D6**). The
  two registered modules the per-module spec skipped — `balance`, which carries
  the mission's primary deliverable and the whole ground-case assembly, and
  `tail_span`, which carries steps 7–9's physics including the suite's first
  hinge moment — are specified on the document's own FAR §/Source/Reads/Writes/
  Validation/Notes template, citing plans 09/11/13/18, `CONVENTIONS.md` and
  `balanced_cases.md` rather than restating them. New `sloads/spec_names.py`
  owns the registry-name → spec-heading map (`weight_estimate` → `WTESTIMA`,
  modern modules under their own name) together with the allowlist of sections
  that are not calc modules (`TAU`, `LGFACTOR`, `payload_cases`, `gear_loads`,
  the export bridges), and `tests/test_spec_coverage.py` guards both directions:
  a new module with no section fails, and so does a section matching neither.
  The status-summary note now names all four modern additions. Docs and test
  only — no shipped number moves, no digest channel changes.

- **G-6's rotational gate half, as the design note wrote it** (0.6.0-candidate
  review finding **R6-T1**, with **R6-T2** folded in). The step-10 benchmark
  shipped with its translational half only — `NVP`/`NDP`/`NS` exact at
  `rel_tol 1e-9` — while the three moment lines the note promised
  (`Iyy·θ̈ == PITCHP + the lift term`, `Ixx·φ̈ == ROLLP`, `Izz·ψ̈ == YAWP`) were
  never written. They are now, in
  `test_the_ground_closure_reproduces_landloads_unbalanced_moments`: the solved
  `[I]{ω̇}` is transferred from the mass centroid to the CG, the **G-7a** lift
  term is rebuilt in closed form (`L × W` along the ground line) and subtracted,
  the applied reactions are moved from the **contact patch** to whichever arm
  point that family's own LANDLOAD formula measures to, and the result is rotated
  into the ground line and compared per family. The one-wheel family's
  `ROLLP`/`YAWP` are identities (`rel_tol 1e-9`, measured 4e-16 — the tread arm
  is shared geometry); every other line is bounded at `1e-4 · W · MAC`, the
  cause being that the BASIC truncates its printed lever arms to 3 decimals.
  A negative control pins both corrections as non-trivial (arm point 12.5 %,
  lift term 5.8 % on `ga6_normal` case 4). `NS` is now compared **signed**
  (R6-T2) instead of by magnitude. `InertiaTensor.moment()` — the forward
  direction of `solve()` — is the new single owner of `[I]{ω̇}`, guarded in
  `test_the_solve_inverts_the_tensor_including_its_coupling`. Test-only: no
  shipped number moves and no digest channel changes.

  **What the gate found** (recorded, not fixed — it is an oracle question):
  `LANDLOAD.BAS` resolves the **ground-roll attitude** at `PHIM = +BETA(2)`
  where the level and tail-down attitudes use `GAMMA − BETA(1)` and `−BETA(3)`,
  so on that attitude `ρ = +GRA` against `ρ = −GRA` everywhere else. The port is
  faithful to the BASIC on both. The consequence: on `ga6_normal` the 23.485
  family's own `ROLLP` (built on `CP`, a contact-line arm) and `YAWP` (built on
  `BP`, an axle arm resolved through `BETA`) are stated 2·GRA(2) = 9.45° apart
  and cannot both be reproduced by any single rigid rotation; the braked-roll
  family's pitch carries the same difference (0.6–3.2 %, bounded at 5 % with the
  cause named). An airplane that sits level (`GRA(2) = 0` — the regional jet and
  both twins) cannot see it at all. Pinned on all five gear fixtures by
  `test_the_ground_roll_attitude_is_resolved_against_the_other_sign`. **Decided
  the same day (user, 2026-08-15): keep the manual's convention — this is a
  faithful replication.** No deviation is taken; the reasoning, the exposure and
  the tests that hold it are recorded under "Considered and declined" in
  `docs/20_theory/02_approved_corrections.md`, which is where the question
  resumes should a legible printed oracle ever surface.

- **Ground and landing cases, and the gear load report** (**step 10 piece 3**,
  decisions **G-1/G-6/G-7(+G-7a)/G-8/G-9/G-12(+G-12a)/G-13**, schema **v48**) —
  the 0.6.0 headline, and the step that **absorbs step 11 (plan 11 B8b)**. The
  FAR 23 ground conditions become **balanced free-free cases in the assembled
  full-span deck**, and the gear gets a deliverable of its own.

  **Ground cases are born in the assembled deck, not in a per-component view**
  (G-1). A ground case is irreducibly three-dimensional — on `ga6_normal` braked
  roll is 2,261 lb vertical against 1,809 lb of drag per wheel, and the side
  family 2,261 against −1,700 lb of side load, applied at a contact patch ~41 in
  below the fuselage beam line and ±57 in off the centreline — and those lever
  arms *are* the load case, while the per-component fuselage deck is planar by
  construction. LANDLOAD cases **1–24** assemble (27 cases on `ga6_normal`, 18 on
  `concept_regional_jet`, twins included); the 23.499 supplementary nose-wheel
  family is skipped **with a recorded reason**, because it carries nose reactions
  only and so is not an airplane in equilibrium.

  **The closure is the regulation's own sentence, and its gate is a closed form.**
  FAR **23.471** requires the external reactions to be "placed in equilibrium with
  the linear and angular inertia forces in a rational or conservative manner"; a
  ground case therefore enters the shipped six-DOF rigid-body closure with **no
  base load factor at all** — the whole field is solved (G-6). LANDLOAD's
  `NVP`/`NDP`/`NS` are deliberately **not consumed**: they are translation only,
  they are stated about the ground line, and consuming them would put a frame
  rotation in the load path. They are the **independent check** instead, and the
  agreement is exact — rotate the solved field back to the ground line and it
  reproduces all three factors on **every case of both fixtures** to
  floating-point noise. That is content-carrying rather than self-referential:
  LANDLOAD reaches those factors by lever arms and FAR percentages, with no mass
  matrix anywhere in it.

  **Wing lift on the landing families only** (G-7), on the AIRLOADS Schrenk
  spanwise shape scaled to `L × W` — only the *shape* is borrowed, so no speed,
  CL or V-n point is involved and no aerodynamics is invented. The split is the
  manual's and the regulation's, not a new one: 23.473(a) lets 23.479/481/483 be
  met at the design landing weight, and 23.485/23.493 are the gross-weight ones.
  The ground-handling families carry **no lift** — the wing is lift-free, not
  load-free. New sub-decision **G-7a**: the lift acts along the **ground line**,
  not the airplane `z` axis, because lift is perpendicular to the flight path and
  the ground line is the flight path at touchdown; this is also what keeps G-6's
  gate an identity rather than a tolerance, since LANDLOAD sums `lf·WL` into the
  ground-line vertical.

  **Handedness keeps its single owner and gains an external check** (G-8). The
  23.483 one-wheel family has no twin in the manual, so both hands are minted
  (`LG-10R`/`LG-10L`); the 23.485 side family ships **both** drift directions
  already, so the odd member is assembled and the even one derived by
  **reflection** — which makes LANDLOAD's own even-member `NS`/`ROLLP`/`YAWP` the
  only *external* check the reflection operator will ever get. Their ids stay
  LANDLOAD's (`LG-19` port, `LG-20` starboard, no suffix), so
  `case_ids.balanced_subcase_id` now takes the case's **hand explicitly** instead
  of parsing an id suffix — identical for every previously shipped case.

  **The gear load report** (G-12) — a stamped companion CSV, a numbered report
  section, a Streamlit view, a manifest row and a CLI target
  (`--export-target gear`). It is a **free body**, not a load list: per case and
  per leg it states the reaction at the tyre contact patch in the ground-line
  frame the manual prints, with the strut state, ground angle and stroke it was
  computed at, and the *same* reaction where the airframe receives it. Both ends
  of the leg, so the two ground artifacts are provably one load seen from two
  sides — and that identity is checked **through the real solver**, which
  reassembles the load from the card text and its own `GRID` lever arms. It
  carries **all 33 cases** against the assembled deck's 24, and reaches **five**
  fixtures against the assembled cases' two, because it needs no mass model; both
  coverage sets are pinned. Sub-decision **G-12a** adds
  `LandingGearInput.weight_lb` (the whole leg, trunnion down) so the free body
  closes; `0.0` means *not stated* and the report shows the free body **open**
  rather than closing it against a guess. What the report is **not** is stated
  in-band: sloads has no gear kinematic model, so it claims no drag-brace,
  side-brace, trunnion or axle-bending load, and its inertia term is the leg at
  the *airplane* load factor — unsprung-mass amplification, which is what
  actually sizes an axle, is not modelled.

  **Ground cases are a separate governing family** (G-9): never auto-compared
  with flight cases for a maximum, because the two load different structure by
  different paths and a cross-family `max()` destroys the one thing a governing
  table exists to say. That is now a **standing limitation** and a paragraph in
  the report rather than something to be inferred from the absence of a
  comparison. They are, however, brought within reach of the engineer's opt-out
  filter — the Critical Loads page gains a Landing gear section — so the family
  is scopable instead of silently unreachable.

- **The weight/CG case model and the gear inputs — one schema hop** (**step 10
  piece 2**, decisions **G-2/G-3/G-4/G-5/G-14**, schema **v47**). Three weight/CG
  case lists and six representations of MTOW collapse to **one owner each**,
  `sloads/cg_cases.py`. Each `CgCase` now states the `analyses` it is run for
  (`FLIGHT` / `GROUND`, a *set*, so one case can feed several rather than being
  entered twice under two names and drifting apart) and, where it is one of
  LANDLOAD's three, its `role`. `FlightLoadsInput.cg_cases` and
  `LandingInput.cg_cases` are **removed**: the first had been a derived copy of
  `weight.cg_cases` since v19 kept in step by the *Flight Envelope page* rather
  than by the model, so a calc-only front end could hold two different lists; the
  second never joined the SSOT at all. `WeightInput` gains
  `max_landing_weight_lb` (moved off `LandingInput`) and `max_takeoff_weight_lb`
  as the single owners of those two certified limits, `MassItem` gains
  `consumable`, and `LandingGearInput` gains `carrier` (`body` | `wing`, **no
  default**) and `attach`, the trunnion node the ground export will transfer the
  contact-patch reaction to.

  **Three latent defects leave with the fields they lived on.**
  `landing.gross_weight_lb` fell back to `max(landing cg_cases)` — which is
  **MLW, not MTOW** — making `WR = 1.0` and understating the braked-roll, side and
  supplementary-nose cases by ~5 % for any project that left it unset. LANDLOAD's
  three loadings are indexed **positionally** and their order used to be recovered
  by *matching names*, falling back to entry order with only a warning, so renaming
  a row silently reordered a reaction table oracle-locked to Appendix A p230;
  `CgCase.role` makes that a field, and `cg_cases.landing_role_cases` raises rather
  than reordering or padding. And `direct_totals()`'s first element, documented as
  MTOW, is the sum of every database row — an upper bound wearing the name of a
  design limit, 964 lb high on `atr42_100` and 1,800 lb on the RJ; it is renamed to
  the database total and becomes the **ceiling** of the ordering chain
  `OEW ≤ MLW ≤ MTOW ≤ Σ items`, which replaces four scattered checks with one.

  **Two new physical rules, both regulation-cited.** `consumable` marks mission
  fuel, and deriving a loading for a `GROUND` target now **burns it down**
  continuously and proportionally before dropping any payload — a design landing
  weight is fuel burned off (14 CFR 23.473(b)/(c)), not a passenger left behind.
  Measured on `ga6_normal`, the old subset search dropped the 6th person (x = 150,
  aft cabin) and kept all 409 lb of fuel (x = 70); burn-down reaches the case by
  burning **317 lb** and lands **0.12 in** from its target CG. And `carrier` is an
  input because body-carried and wing-carried gear are different **load paths**:
  applying a wing-carried reaction to the body beam over-loads the fuselage *and*
  hides a real wing sizing case.

  **New guards** (practice 3): the design-weight ordering chain; `MLW < OEW + max
  payload + reserve fuel`, which fires on `concept_regional_jet` (31,000 against
  31,360 — that airplane cannot land at MLW with full payload and reserves);
  carrier ↔ gear-mass agreement, which fires on `dhc8_dash8` (main gear in
  wing-mounted nacelles, mass tagged `fuselage`); `attach` plausibility against the
  wing planform; an empty `analyses` set; a `role` on a case not tagged `GROUND`;
  and MTOW drift between the SSOT and the representations it replaced.

  **GUI:** the Weight & Mass Properties page's **Payload Cases** tab is the sole
  editor, with `FLIGHT`/`GROUND`/`role` columns and the WTENV landing seed (now
  the pure helper `cg_cases.seed_landing_cases`, offered on a button, never written
  by a render); its Weight / CG Envelope tab owns MLW and MTOW and offers the
  derived MLW estimate for acceptance; the Landing Loads page's CG table and both
  weights are **read-only**.

  **Nothing moved.** Migration `_v46_cg_case_model` is output-neutral by
  construction — every value it writes comes from the file's own, MTOW from
  `speeds.weight_lb`, which measurement showed equals the other four
  representations on every shipped fixture. Every Appendix-A oracle, every fixture
  digest and every exported deck is unchanged; the `FLIGHT`-tagged set after
  migration is pinned, per fixture, to equal the pre-hop `flight_loads.cg_cases`
  exactly.

- **The governing safety-factor table — one authority for every case's factor**
  (**M4-8**, step 10 piece 1, decisions **G-10/G-11**). The factor of safety was
  previously decided ad hoc: a dataclass default of 1.5, one module overriding it,
  and two silent `getattr(item, "safety_factor", ULTIMATE_FACTOR)` fallbacks in the
  report that reported 1.5 for a factorless case leaving no trace. `sloads/
  safety_factors.py` is now the single code owner: **one row per condition family**,
  each stating its factor, its regulatory **basis** and its status (`derived` /
  `override` / `defaulted`). The family boundaries are **14 CFR Subpart C's own
  section groupings**, so the granularity is the regulation's, and every per-case
  SF — the report case index's column, the load-case CSVs, a deck's `SF=` marker —
  is a derived view of a row. `GoverningTable.factor_for()` classifies a case from
  its FAR reference and the table **writes the carrier** at the three boundaries
  every front-end shares, so a report figure and its bulk-data card cannot state
  different factors for one case (review **F-R1**'s defect class, re-armed for the
  override path). It travels as report **§3 Governing safety factors** and the
  stamped companion `<project>_safety_factors.csv`, both named in the manifest.
  The table is **fully user-editable including the regulation rows**
  (`Project.safety_factors`, schema **v46**, additive, no hop) — safe for the
  oracles, since the factor is applied at the render/export boundary only, but not
  for the deliverable, so an override is declared in the report **and** the methods
  stamp, must state a basis, and raises a **certification-risk** warning when it
  sits below the value the regulation derives. An unclassifiable case takes 1.5 and
  is **flagged**, never silently accepted. Acceptance is reproduction: the table
  resolves exactly the factor every producer mints, case by case, on all six
  shipped fixtures, with **zero defaulted rows and zero overrides** — **no number
  moved and no digest changed.**
- **Discrete control surfaces, and the suite's first hinge moment** (plan 09
  **T6**). Setting `control_load_mode = "discrete"` on a tail surface — with
  `hinges_span_in` and `actuator_span_in`, new per-surface schema (**v45**,
  additive, no hop) — takes the control surface's own load **out** of the
  smeared spanwise strips and applies it where the airplane applies it: hinge
  reactions by chord-weighted tributary span at dedicated `GRID`s on the load
  reference axis (bands `5001+` elevator, `5301+` rudder), with the
  hinge-moment couple at the actuator node. The control load is **SELECT's own**
  (`elevator_load` / `load_on_rudder`, oracle-locked, now split into its camber
  and angle-of-attack parts so each leaves the distribution at the chord station
  TAILDIST placed it at) where the condition publishes one, and derived from
  TAILDIST's aft-of-hinge pressure block — and marked derived — where it does
  not. The **hinge moment** is that load on a third of the aft-of-hinge chord,
  which is exact rather than approximate because the net trailing-edge pressure
  is identically zero and the block is therefore always a triangle; it is
  reported as a load value, shown on the Tail Span Loads page and stated in the
  deck `$` header. The two modes apply **exactly** the same total force
  (`rel_tol 1e-12`, a property of the construction, not of the quadrature), and
  the root-torsion difference between them is gated as a closed form — one
  chordwise relocation of the control load to its own centre of pressure — not
  as a tolerance. Selecting the mode without attachment geometry raises rather
  than falling back, and `"smeared"` remains the default: **no shipped fixture
  carries hinge geometry and no shipped deck changed by a byte.**
- **A T-tail's fin deck carries the horizontal tail at its tip** (plan 09
  **T7**). `TailType.T_TAIL` had driven only the three-view sketch; it is now a
  load path. Each vertical-tail case's deck gains, at the fin's **last** node
  (no new `GRID`), the h-tail load concurrent with that case — the balancing
  tail load at its own V-n point plus the h-tail's inertia there — as a vertical
  `FORCE` and the `MOMENT` its two lever arms make, the balancing load about the
  tail CP the V-n point publishes and the mass about the planform's own
  centroid. Roll and yaw transfer are zero and the deck says why (the pairing is
  a balancing condition, so the h-tail's halves cancel about the centreline).
  `concept_regional_jet` is the suite's only T-tail fixture, and its fin deck
  was previously the deck a *conventional* airplane would have had.

- **ONENGOUT runs on shipped data.** `atr42_100` and `dhc8_dash8` now enter
  take-off and max-continuous shaft power on both engines (PW120 2000/1700 shp,
  PW121 2150/1950 shp — converted from the certificated kW in EASA TCDS
  IM.E.041 issue 07, 20 Dec 2023 §5). The FAR 23.367 one-engine-out module was
  previously unrunnable on every bundled example, so its simulation path was
  exercised only by unit tests on constructed inputs. Each airplane gains three
  vertical-tail conditions (`VT-30`…`VT-32`). **Their VS cases do not recover**
  — full asymmetric power at the clean stall speed is below VMC — and say so on
  the case, as designed.
- **New standing limitation, `engine-failure-propeller-only`:** the 23.367 model
  is propeller-only (thrust from shaft power over true airspeed, Glauert
  windmilling on the propeller disc), so a turbofan/turbojet multi is not
  covered and its asymmetry would be understated. Carried in every
  methods-and-limitations stamp; `concept_regional_jet` deliberately enters no
  one-engine-out slice. Refusing to run on a non-propeller installation remains
  open (backlog M4-3(b)).

### Changed

- **Documentation currency rule + guard (tier M, 2026-08-16).** A standard doc
  never states a number that describes the code's current state — schema
  version, test count, coverage %, "currently N", "version is now X" — it points
  at the owner (`SCHEMA_VERSION` in `sloads/models/project.py`, CI, the generated
  `DATA_DICTIONARY.md`); provenance stays as `schema vN`. Rule:
  `00_program_overview.md` §Documentation currency, `CLAUDE.md` required
  practices, `CODE_REVIEW_PROCESS.md` step 1. Guard `tests/test_doc_currency.py`:
  literal patterns over `README.md`/`CLAUDE.md`/`docs/00_INDEX.md`/`10_standard/`/
  `20_theory/` (generated data dictionary exempt), plus `docs/00_INDEX.md` ↔ the
  docs tree both ways (a doc with no INDEX row, or a row with no file, fails —
  the R6-D2 class). Swept on first find: four `SCHEMA_VERSION = N` currency
  claims in `GUI_design.md` and `PROGRAM_SPEC.md` rewritten as provenance or
  pointers. Origin: the review's finding that R6-D1…D8 shipped past the
  structural guards.

- **Doc volume: history archived to 0.5.0, changelog fragments, tier S trimmed
  (backlog R11 closed, tier M, 2026-08-16).** Design note
  `docs/30_future/26_doc_volume_reduction_note.md`, all three recommendations
  accepted at user review. (a) `docs/40_history/00_completed_development.md`
  cut at the 0.5.0 release block; ~7,970 pre-0.5.0 lines moved verbatim to the
  frozen `11_completed_development_to_0.5.0.md`. (b) `[Unreleased]` is no
  longer hand-edited: each closure drops one `changes/<slug>.<type>.md`
  fragment (this entry is the first) and `scripts/build_changelog.py X.Y.Z
  --date …` assembles them at release cut; `tests/test_changelog_fragments.py`
  guards fragment names/shape and warns when the live history passes 1,500
  lines. (c) Tier S closure = fragment + backlog removal, no history entry
  (`CLAUDE.md`, `CODE_REVIEW_PROCESS.md` §0). `RELEASE_PROCESS.md` §4 gains a
  mechanical history-roll step. Legacy hand-written `[Unreleased]` text folds
  into 0.6.0 verbatim.

- **Effect-vs-error-bar rule promoted to `CLAUDE.md` rule 6 (tier S,
  2026-08-16).** The 2026-08-16 scope review's ordering rule — a fidelity item is
  ranked only if its stated effect on a delivered load exceeds the base method's
  own uncertainty, otherwise parked *with the number that parks it*; a defect
  with first-order effect on shipped content outranks every fidelity item —
  lived only in the backlog's header, i.e. in a plan file. It is now rule 6 in
  `CLAUDE.md` (pointer, no number: the datum is a new
  `theory_sources.md` §Base-method uncertainty section — rigid airplane, Schrenk
  span load, lumped tail; order 5–10 % on a distributed load, tighter on the
  oracle-pinned totals — stated once, as an order of magnitude that ranks work
  and gates no test); the backlog header points at the rule. `CLAUDE.md` stays
  inside its ~160-line budget (three prose lines tightened, no rule dropped).
  Closes item 10 of the 2026-08-16 code-standard summary.

- **Multi-developer development process (design note 28, MD-1…MD-12, tier M,
  2026-08-16).** Trunk-based branches + protected `main` (PRs only, 1 reviewer ≠
  author, CODEOWNERS review, squash-merge; `self-merge-ok` for tier-S docs/hygiene
  PRs on green CI); **closure travels in the PR**; **history entries become
  `changes/<slug>.history.md` fragments** rolled to the top of the history file
  at release cut by `scripts/build_changelog.py` (tier M paragraph / tier L step;
  guarded in `tests/test_changelog_fragments.py`); **GitHub Issues + Project are
  the system of record** for open work with `00_backlog.md` as the plan
  (`scripts/backlog_issues.py plan|create|rewrite|check`, parser guarded in
  `tests/test_backlog_issues.py`); design note as a PR before code, `Owner:` /
  `Reviewers:` lines on every live note; concurrency rules for `SCHEMA_VERSION`,
  the Imperial digest and case-ID bands ("rebase before you regenerate");
  `.github/CODEOWNERS` (`@Sean074`), `CONTRIBUTING.md`, `PULL_REQUEST_TEMPLATE.md`,
  three issue templates, `docs/10_standard/DEVELOPMENT_PROCESS.md`; `CLAUDE.md`
  points at them (still ≤160 lines); `.claude/settings.local.json` git-ignored.
  Branch protection and the one-off issue migration are the owner's GitHub steps.

- **Development process simplified: solo profile, PR-fast CI, derived backlog
  table, template placeholder made visible (tier S, 2026-08-17).**
  `DEVELOPMENT_PROCESS.md` §0 states which note-28 mechanisms are off while the
  repository has one collaborator — PR-per-item, non-author review and the
  issue mirror become optional; one commit per closed item, the backlog row
  leaving in that commit, and every closure tier / rule stay in force — and
  how the full flow switches back on with a second collaborator. **CI:** a
  pull request now runs the fast gate only (`test (3.12)` with coverage,
  `typecheck`, `sbeam-roundtrip (3.12)`); the 3.9/3.11 compatibility legs run
  on push to `main` and are fixed forward; a re-push cancels the run in flight
  (`concurrency`). **Backlog:** the priority table is a *view* of the issues
  under the multi-developer flow — new `scripts/backlog_issues.py render`
  drops closed rows and re-emits open ones from their issue bodies (one
  row-block writer shared with `create`, round-tripped on the live file by
  `tests/test_backlog_issues.py`), so a closing PR never edits the table, rows
  never renumber, and dependencies name the band or `#N`; the eleven "Body
  moved to issue #N" stubs and their two "Item detail" headings are gone.
  Prompted by the first week on 0.6.0: PR #25 merged with the template's
  invisible `#<!-- issue -->` placeholder unfilled, so issue #1 never
  auto-closed; the template now reads `Closes #___` with the rule beside it.

- **Static typing and lint depth (design note 27, tier M, 2026-08-16).** `mypy`
  joins the merge gate: `[tool.mypy]` in `pyproject.toml` checks `sloads/` (never
  `app/`/`tests/`), zero errors in default mode, in its own CI job on 3.12;
  strictness ratchets per package through `[[tool.mypy.overrides]]` — stage 1
  (`disallow_untyped_defs`/`disallow_incomplete_defs`/`check_untyped_defs`) on
  the single-source owners (`models/`, `safety_factors`, `units`, `case_ids`,
  `load_keys`, `constants`, `registry`). 153 errors → 0 across 31 files by
  narrowing only (no `type: ignore`, no `Any` widening, no `cast`); the frozen
  Imperial digest and every oracle passed unmodified. Latent `None`
  dereferences on already-refused paths now raise per the error contract
  (`balance.py` `_wing_slices`/`_flight_loads`, `engine.py` `_required`);
  `ConditionResult.note` is `""` not `None` when empty; `GearCaseLoads.case_ref`
  is `Optional[CaseRef]`. `ruff` select widens from `E F W` to
  `E F W B SIM PLE PLW ARG RUF I C4` (each ignore reasoned in `pyproject.toml`;
  `UP` off until 3.9 leaves the matrix, `N`/`PERF` off with reasons); 243 new
  findings → 0, five private helpers lost dead parameters, contract-signature
  `ARG001`s carry a reasoned `noqa`, the two side-effect import blocks are
  isort-skipped in place. Rules of engagement:
  `00_program_overview.md` §Static typing & lint; `CODE_REVIEW_PROCESS.md` step 7.

- **Test-suite runtime, CI speed and git hooks (code-standard review item 8,
  tier S, 2026-08-16).** Measured first: the parallel suite was 59 s locally
  and ~12 min per CI leg. (1) One test —
  `test_imperial_csv_is_byte_identical_to_the_no_system_call` — re-loaded the
  project and re-ran *all* modules once per (example, module) key, ~130 full
  pipeline runs for the same assertion; it now builds the defaults once per
  example. Suite 59 → 36 s locally, no test over 10 s. (2) CI runs branch
  coverage on the **3.12 leg only** (matrix `include`), the 3.9/3.11 legs
  uninstrumented; `--durations=15` on every leg so the next hot spot is visible
  in the log. (3) **No `slow` marker** — deliberately: with the numbers above a
  fast subset saves seconds and adds a thing to keep in step
  (`00_program_overview.md` §Testing states the revisit thresholds).
  (4) `.pre-commit-config.yaml` (opt-in, local hooks on the venv's own tools):
  ruff + mypy on commit, whole suite on push. (5) `ruff` and `mypy` **pinned**
  in `[dev]` (`ruff==0.16.3`, `mypy==2.3.1`) — a newer ruff on the runner than on
  the desk is what turned a green local run into a red PR (RUF068); a bump is
  now a one-line PR whose CI run reviews the new rules. `pre-commit` added to
  `[dev]`; `CONTRIBUTING.md` §2 gains the install line.

- **Backlog priority table re-cut, and the `CgCase` loading decision answered**
  (decision **D-25**; docs only, no code and no output). The order now bands by
  what it protects: wrong content in an already-shipped deliverable first (the
  `LATERAL_AERO_NOTE` `n_y` direction defect, the `applicability` design-weight
  re-point, the `dhc8_dash8` gear carrier tag, M4-22), then the [E] sbeam steps
  12/13/14, then the D-25 wave. The open defects and the unscheduled 0.5.0 review
  findings are **interleaved into the one list** by severity instead of sitting
  only in the index, and the table is renumbered 1–36 (the old Pri 5 gap, left by
  the non-wing-drag step above, is closed). **D-25:** `CgCase` gains an explicit
  loading definition rather than the fixtures' CG-envelope corner points being
  rewritten to suit their weight databases — the corner point is the real
  engineering input; the loading is the derived quantity. It unblocks the two
  sibling coverage findings and is the change that takes the assembled balanced
  deck from 2 fixtures to 6 in CI.

- **Pressurization is out of scope — permanently, and the deliverable now says
  so** (decision **D-24**). The standing limitation read "No pressurization load
  cases.", which an analyst could reasonably take as *not yet*. It now states an
  exclusion: no cabin differential-pressure case (14 CFR 23.365 / 25.365) is
  computed, no pressure load is combined with any flight or ground case, and a
  pressurized fuselage must have that assessment from another source — with the
  unrelated WTESTIMA `pressurized` weight-allowance flag named so the two are not
  confused. Four shipped fixtures are pressurized airplanes, so the sentence
  travels where it matters. Scope follows the wording: **M4-6 (step 10) is the
  ground/landing distributed loads and gear reactions alone**, and **F25-5** keeps
  only its 23.415/25.415 ground-gust half. No calc, no output number and no deck
  byte changes.
- **Imperial digests regenerated, once, deliberately** — three channels on
  `concept_regional_jet` only (`sbeam/vtail_span_cards`, `csv/tail_span`,
  `txt/tail_span`), all of them the T-tail transfer arriving in the one fixture
  whose layout has one. Its fin's own station table (`sbeam/vtail_span_csv`) did
  **not** move, and neither did any other example's anything.
- **Case identity is joinable in the report and the GUI.** A solver result
  labelled `SUBCASE 7105` could be traced back to its condition only through the
  case-index **CSV**; neither the summary report nor any GUI page stated the
  integer at all. The case index (report table and CSV) now carries **two**
  deck-number columns — `LOAD/SUBCASE (component)` and `LOAD/SUBCASE (assembled)`
  — because a case legitimately has one number per deck family (`W-05` is `105`
  in the wing deck and `5105`/`7105`/`8105` in the assembled one, **D-R7**), and
  a single unqualified column would be silently wrong for whichever family it
  was not quoting. Each is filled only where the case is actually in that deck: a
  handed twin fills the assembled column alone, a symmetric case that also
  assembles fills both, and an em dash means "not in that deck". The governing
  loads table (report §Results, the Flight Envelope Critical Loads tab, Results
  Review) and the balanced-case table gained `ID` + `LOAD` columns, and every GUI
  case label now comes from one formatter — `W-03 · LOAD 103 · PHAA · FAR
  23.333(b)` — instead of four independent strings. The number's single owner is
  the new `case_ids.deck_load_id`, drift-guarded against the decks' own text
  (`tests/test_case_ids.py`). The assembled deck's `$` map block now leads with
  the case id, as every other deck family's already did — it was the one deck
  whose comment block could not be joined without reading its case control.
  Design note: `docs/30_future/17_case_load_id_linkage_note.md`.
- **Imperial baseline regenerated — deliberate.** Entering engine horsepower
  moves `csv/txt one_engine_out` and `case_index` on both turboprops (three new
  conditions each), plus **`csv/txt weight_estimate` on `dhc8_dash8`**:
  `resolve_max_continuous_hp` (M2-6) prefers the engine list and had been
  falling back to the stored estimation total, which was 4000 hp against the
  engines' real 2×1950, so the statistical MTOW estimate corrects 42,325 →
  41,775 lb (empty 25,395 → 25,065 lb). `atr42_100`'s stored 3400 already
  matched its 2×1700 and did not move. No load path, deck, oracle or other
  example moved.
- **A wing case row states the flight condition its loads were computed at**
  (**D-23**, backlog priority 1). `wing_case_ref` kept SELECT's `CaseRef`
  *whole* when SELECT had named the condition, so a case that restates its own
  CL/speed shipped rows labelled with a speed its numbers were not built from —
  `atr42_100`'s `PHAA` read 185.85 kt (SELECT's V-n point) beside loads computed
  at the entered 170 kt, and `ga6_normal`'s `ACRL` read 117.4 kt against the
  worked example's 116. The `CaseRef` now takes the case's own `v_eas_kt`
  wherever it states one — the same precedence `net_loads._air_cl_v` computes
  the air load by — so the wing CSVs, the case index and the report agree on one
  speed per case. **SELECT's `case_id` is kept** (M4-2 decision 1: one ID per
  physical condition, which the case-index dedupe assumes), as are CG, altitude
  and the FAR reference, which the case does not state; SELECT's own
  governing-loads row keeps its V-n point, which is what *its* numbers were
  computed at. The case index's ordering rule is now explicit and stated in
  `case_index_rows_from` — deck-exported results before SELECT's conditions,
  first-seen defines a row's condition — with the four callers (report, Export
  page, workbook, baseline) put in that order and a drift guard on it
  (`tests/test_case_ids.py::test_the_index_row_states_the_condition_its_cards_were_computed_at`).
  No load number, card, deck or oracle moved.
- **Imperial baseline regenerated — deliberate (wing case conditions).** Three
  channels move on all six examples: `csv/wing_inertia` and `csv/net_loads` (the
  Speed column on the cases that restate their condition) and `case_index` (the
  same speeds, plus the row order the caller change implies). No `sbeam/*` deck
  channel moved — the identity changed, the numbers did not.
- **Imperial baseline regenerated again — deliberate (case-identity linkage).**
  `case_index` moves on all six examples (two new columns) and
  `sbeam/balanced_deck` on the two that assemble (the case id added to the map
  block's comment lines). No load number, card value, oracle or other channel
  moved.

---

### Fixed

- **Constants and conversion factors — one owner, one value, one rule (issue #26, review 2026-08-17 C-1…C-12, tier M, 2026-08-17).**
  `sloads/constants.py` now owns every shared physical constant and suite-internal
  (Imperial↔Imperial) factor — `DEG_PER_RAD`/`RAD_PER_DEG`, `IN_PER_FT`, `IN2_PER_FT2`,
  `KT_TO_FPS`, `FT_LB_S_PER_HP` (→ `HP_TO_TORQUE`), `dynamic_pressure_psf`/
  `eas_from_dynamic_pressure`, `gust_alleviation_factor` + `GUST_LOAD_FACTOR_DIVISOR`
  (FAR 23.341(c)) — and the ~60 open-coded sites (`57.3`, `114.6`, `_G = 32.2`, six
  `144` aliases, `/12.0`, `550`, `V²/295` ×16, the gust triple ×5) read it; the
  `PI`/`TWO_PI` aliases are gone (`math.pi` everywhere). **Exact by default:** 57.3,
  32.2, 295 and FLTLOADS' private 518.688 °R speed of sound go to their exact owners
  (measured: no printed oracle moves; digest and SELECT/dCD/VA-VF self-pins re-pinned,
  register line in `02_approved_corrections.md`); `KT_TO_FPS_SUITE` survives for `VSF`
  only (ENGLOADS `/101.2` oracle). The `constants.py` (Imperial↔Imperial) vs `units.py`
  (Imperial↔SI only) demarcation is written into `CONVENTIONS.md` §7 with grep drift
  guards both ways (`tests/test_constants.py`); UI help text quotes `√(2(W/S)/(ρ₀·CLmax))`.

- **No silent defaults in the export namespace (CH-2, code-standard review item
  9, tier M, 2026-08-16).** Seven `getattr(obj, name, default)` reads in
  `sloads/export/sbeam_bridge.py` — the shape the error contract forbids
  ("flagged, never silently defaulted") — are gone: `case_ref`, `case`,
  `tip_transfer` and `hand` are declared fields on every exportable result and
  are now read as the typed attributes they are (`_sid`, `subcase_map`,
  `_tail_span_case_block`, the case-index builder, where the assembled case's
  `hand` is **passed** to `add()` and a component-deck item takes the bare id by
  statement, not by a probe that happened to miss); the one lookup by name (the
  `htail`/`vtail` span slice in `_tail_span_results`) is an explicit map that
  refuses an unknown component with a `ValueError` instead of reading as "no
  loads". Frozen Imperial digest unchanged — no default was ever being taken on
  a fixture, which is what makes this hygiene rather than a load change. Guards:
  `tests/test_sbeam_bridge.py::test_the_export_package_takes_no_silent_defaults`
  (AST walk over `sloads/export/`, three-argument `getattr` forbidden; the
  two-argument dynamic-name form stays allowed) and
  `::test_tail_span_export_refuses_an_unknown_component`. `00_program_overview.md`
  §Error handling and `PROGRAM_SPEC.md` §Export bridges state the rule;
  `CONVENTIONS.md` §7 gains the row; CH-2 struck from backlog row 5 (issue #5's
  remaining clauses stay open).

- **The fin-root "fuselage-top" formula has a body-centreline datum (backlog
  Pri 1, defect from T-8a, tier M, 2026-08-16).**
  `tail_geometry.fin_root_waterline`'s fuselage-top branch was
  `root_waterline_z + fuselage_height/2`, which reads the **wing** root as the
  body centreline — the substitution `CONVENTIONS.md`'s body-drag row refuses
  for D-1 — and on the three high-wing outline fixtures stacked half a body
  above the real top. With a fuselage outline present the branch is now
  **`z_centre(x_fin) + height(x_fin)/2`**: the v52 section-centre line
  (`derived_geometry.fuselage_centreline`, note 24 R-4) plus half the **local**
  body height (new sibling owner `derived_geometry.fuselage_height_at`), both
  at the fin's `xv25`. The old formula survives only as the no-outline fallback
  and its note now names the wing-root substitution it makes; a pointed tail
  cone (zero local height at `x_fin`) declines the branch rather than seating a
  fin on nothing. The new project-level resolver `tail_geometry.fin_root`
  is read by both the load path and the three-view
  (`configuration.tail_planform` gained an optional `project` argument), so the
  single-owner guard holds. **Re-pins (the un-pinning the backlog row
  promised):** fin roots `atr42_100` 223.15 → 191.17 in, `dhc8_dash8` 232.95 →
  203.45, `cessna_210` 109.60 → 100.24 (`ga6_normal` — no outline — and the
  T-tail regional jet unchanged); the twelve lateral-case pins moved in `p_dot`
  (roll arm) and slightly in `r_dot` (`Ixz` coupling) with fin load and `n_y`
  byte-identical; the Imperial digest baseline regenerated deliberately for the
  three fixtures' `balance`/`tail_span`/vtail cards and decks (plus a
  note-text-only move on `ga6_normal`'s fin deck header).

- **Hygiene batch — one authority for σ, ρ₀ and every SI display factor; the
  guards that were claimed to exist now exist (backlog Pri 5, tier S, 2026-08-17).**
  Closes the 2026-08-05 conventions-extraction findings (a)–(d), M4-23, CH-3, CH-6,
  CH-7 and the 427 lb fuselage-mass pin in one change. **(a)** `tests/test_load_keys.py`
  written — `LoadValue` keys unique within every `ConditionResult`, every module ×
  every example project (verified zero duplicates before writing). **(b)**
  `constants.py`/`models/results.py` cite "14 CFR 23.303 / 25.303", the SF
  authority's phrasing. **(c)** already carried the comment. **(d)** the three
  partially-shared SI factor maps consolidated: `units.HUMAN_SI` is the one owner
  (every factor a named constant, products derived — `FT2_TO_M2`, `IN2_TO_M2`,
  `HP_TO_KW`, `SLUG_FT2_TO_KG_M2 = FT_LB_TO_N_M`); `SI_PER_IMPERIAL`,
  `UNIT_LABELS`, `_RESULT_TO_SI`, `_SI_BY_QUANTITY`, `_SCALAR_TO_SI`,
  `_KIND_FACTORS` are views built by `_view()`, no call site moved; **CH-7**
  `report/content._EXTRA_DIMENSIONS` takes its four factors from it (labels stay
  the report's ASCII ones, so no deliverable byte moved). **CH-6** `constants.RHO_SL`
  replaces the eight `0.002378` literals under three private names; **M4-23**
  `flight_envelope.density_ratio` now returns `standard_atmosphere(alt)[1]` and
  keeps only FLTLOADS' own speed of sound. **CH-3** `tests/test_tail_transforms.py`
  tests the three empennage maps directly against `CONVENTIONS.md` §7, with the fin
  torsion sign recomputed as `r × F` rather than asserted. **427 lb pin retired as
  superseded** — verified: no FAR23 oracle module reads `fuselage_mass`; `body_loads`
  builds its beam from `weight.items` via B1's `fuselage_beam_stations`, and
  `mass_distribution.fuselage_reconciliation` (+ `test_mass_distribution`) is the
  standing guard on the entered table. The review-§1.7 `[Unreleased]` currency check
  is out of scope: `[Unreleased]` is build-generated from `changes/` since 2026-08-16.
  Guards: `test_constants.py` (ρ₀ literal has one owner; σ delegated),
  `test_units.py::test_every_si_view_reads_the_one_owner` /
  `::test_si_factor_literals_have_one_owner`; `CONVENTIONS.md` §7 gains the two owner
  rows, §8 is closed. Suite, digests and oracles unchanged.

- **Analysis-page LIMIT CSVs follow the unit toggle and label their units (L-8i,
  backlog Pri 3, tier S, 2026-08-16).** The Wing/Fuselage/Tail Loads pages built
  their LIMIT download inline from the raw Imperial row dicts, so an SI session
  downloaded Imperial numbers under unit-less headers while the table above was
  converted — the units-defect class M4-20 already paid for. New `app/limit_csv.py`
  is the one owner per page of the column→unit map, the display conversion and the
  unit-suffixed header (`Fz (lbf)`/`Fz (N)`, `Mxx (lb-in)`/`Mxx (N·m)`, tail
  `PSI(Xn) (psi, LIMIT)`/`(kPa, LIMIT)`), and feeds **both** the on-screen table and
  the download so they cannot disagree; the two hand-authored tail header sets
  collapse into one. Decisions: map stays per page (the row builders return
  pre-formatted strings with no quantity kind); units in the headers and basis in
  the `Basis` column / `*_LIMIT.csv` filename, **no** `units_statement` line — the
  LIMIT analysis-page carve-out, not a deliverable (`CONVENTIONS.md` §3). On review
  `loads_plots` was already converted and labels units in its `Field` cell, so it
  is verified conformant and unchanged (the issue's "four pages" is three). The
  sbeam/export channel is untouched. Guard: `tests/test_limit_csv.py` (Imperial in
  → Imperial out, SI cells equal `to_si_scalar` of the Imperial ones, no bare load
  header in either system).

- **LRA deck: one `PBAR`/`MAT1` pair per section family, editable in place
  (backlog Pri 7 / #7 — step 14 descoped, tier S, 2026-08-17).** The LRA
  model wrote a single placeholder pair that every `CBAR` referenced; a
  sizing tool with real sections had nowhere to put them. The deck now
  carries four pairs — `wing` / `fuselage` / `htail` / `vtail`
  (`lra_model.SECTION_FAMILIES`, `MID = PID` 1–4, each tagged
  `$ SLOADS-SECTION <family>`), the left wing sharing the right's and the
  fwd/aft fuselage chains one — with **identical placeholder values** in all
  four (a different default per family would be invented stiffness and would
  move the indeterminate paths for no reason), and every `CBAR` carries its
  family's PID. Decision of record (user, 2026-08-17): **no input path** —
  not the review's "consumer-supplied" sidecar/schema, because section
  properties are the sizing half's output (scope review §2.3), so the seam is
  the deck a sizing tool edits, not `sloads`' schema; the 0.6.0 freeze holds
  at v53. `STIFFNESS_NOTE` rewritten to say which cards to overwrite. Solved
  results unchanged (same numbers, new IDs); guard
  `test_lra_model.py::test_every_cbar_references_its_family_section_and_the_four_pairs_are_identical`;
  round-trip leg still solves; Imperial digest regenerated on `sbeam/lra_model`
  for the four fixtures that export one.

- **A forward non-wing "drag" is no longer applied where the polar is not
  trusted (backlog Pri 2, fixture aero-data defect, tier M, 2026-08-17).**
  Design note 20 D-4 revised (§8.2): the airplane-less-tail polar less the wing
  strips (`balance.body_axial_set`) is a physical `body-axial` load only where
  both drag models are trusted, and the trim `α` is now tested against a
  **one-sided** window, the single owner `constants.POLAR_TRUSTED_ALPHA_DEG =
  (−10°, +15°)` (`balance.polar_alpha_trusted`, read by the code and by the G10
  gate). Outside it a forward difference is **not applied** — no card,
  `body_axial = 0`, new result flag `BalancedCaseResult.body_axial_clamped`, the
  raw value and the window in the case note — while `ΔC_D` is still reported
  unclamped, so the diagnostic that found the defect keeps its signal. Inside
  the window a forward value is a fixture-data defect and fails G10; the three
  excused `NMAA` entries the test carried are gone. What this removes from the
  decks: **1,004 / 1,097 / 1,445 lb forward** on `atr42_100` / `dhc8_dash8` /
  `concept_heavy` `NMAA` (α = −12.9…−14.3°, 3–8 % of `W`) and the regional
  jet's four high-`α` cases (1.7–2.6 klb). Stated consequence: on those cases
  and only those, both pre-closure residuals re-open by the un-applied force
  and its couple about the CG (pitch **1.5–2.1 %** of `n·W·MAC` on the three
  `NMAA` points, the wing plane being ~40 in from the CG), reacted by the
  closure and pinned per case in `test_balance.py::_CLAMPED_BODY_AXIAL` under a
  2.5 % hard stop; G1/G5 and G2 read the same flag. `ga6_normal`, `cessna_210`
  and every in-window case are byte-identical. Imperial digest regenerated for
  the four fixtures' `balance` channels and three `lra_model` channels; polars
  not re-derived (out of scope by the row's own words).

- **One-engine-out refuses non-propeller installations (M4-3(b), issue #4, tier S, 2026-08-16).**
  `one_engine_out._case_inputs` raises `MissingInputError` when the failed engine
  has no propeller diameter, so `run`, `time_history` and the UI page all refuse
  instead of simulating with a 0-in windmilling disc; `PROPELLER_ONLY_NOTE` now
  states the enforcement. The gate is the propeller disc rather than
  `engine_type` — `EngineType` has no turbofan member (a fan is entered as `T`
  with a 0-in disc) and the schema is frozen. Reciprocating twins still run;
  the turboprop scope of 23.367(a) stays a coverage-table statement.
  Guard: `tests/test_one_engine_out.py::test_no_propeller_disc_is_refused`.
  (a)/(c) remain parked. Closes #4.

- **CI red on every `main` run since step 12: platform-dependent bytes in the
  frozen Imperial digest and the 3.9 data dictionary (tier M, 2026-08-16).**
  Two classes, both invisible locally (macOS, Python 3.11) and red on the Linux
  matrix: (a) `select.py` picked critical cases with `max()`/`min()` over keys
  that tie *exactly* in exact arithmetic — `BAL A` at two altitudes carries the
  same VA — but land one ulp apart on another libm (and under 3.12's
  compensated `sum()`), so `atr42_100`'s SUDDEN RUDDER came from V-n 74 in CI
  and V-n 14 on the Mac; every keyed pick now goes through **`_extreme`**, first-
  in-order inside a `_TIE_REL` (1e-9 relative) band, which is exactly what
  `max` returned for a bit-exact tie, so no local pick moved. (b) FORCE/MOMENT
  components that are zero by construction printed their ~1e-14 cancellation
  residue (`6.101335E-15` here, `1.987480E-14` there) or `-0.000000E+00`;
  every vector card (FORCE, MOMENT, GRID, CONM2 offset — 26 sites across five
  exporters) now formats through **`sbeam_bridge._fmt3`**, which snaps a
  component below `_TOL ×` its own card's scale to `0.000000E+00` (the
  per-component form of `_closed`). Digest regenerated: every one of the 23,649
  changed lines is `-0` → `0` or dust → `0`, no load value moved. (c) With (a)
  and (b) in, the 3.12 leg alone still failed on `concept_regional_jet`: Python
  3.12 changed the built-in `sum()` of floats to compensated summation, so
  `resultant6`'s `sum(ld.fz …)` landed a few ulp from 3.9/3.11 and two values
  sat on print boundaries (an integer-valued residual `65013` vs `6.501e+04`;
  a FORCE card's 7th digit). **Every float summation in `sloads/` — 102 sites
  in 20 files — is now `math.fsum`**, exactly rounded and therefore identical
  on every interpreter and platform; the digest moved by 20 lines, all
  last-digit, and every oracle/closure pin passed unmodified. Also
  `docs/generate_data_dict.py` drops the `"An enumeration."` placeholder that
  Python ≤ 3.10's `EnumMeta` stamps into a docstring-less enum's own `__dict__`
  (the 3.9-only `DATA_DICTIONARY.md is stale` failure). New guards
  `tests/test_select.py::test_extreme_pick_is_first_in_order_across_a_platform_ulp_tie`,
  `tests/test_sbeam_bridge.py::test_card_components_snap_dust_and_negative_zero`
  and `tests/test_platform_stability.py::test_every_float_summation_in_sloads_is_fsum`
  (all grep for bypasses); `CONVENTIONS.md` §7 gains the row.

- **`atr42_100`/`dhc8_dash8` are T-tails, and are now modelled as such
  (backlog Pri 1, from T-8a, tier M, 2026-08-16).** Both fixtures set
  `tail_type: t_tail` (their own `xt25`/`xv25` were the tell); the fin root
  stays on the outline datum (`h_tail_z` left `0`, so the just-closed
  fuselage-top branch governs: atr42 191.2 in, dhc8 203.5 in — unchanged), and
  the horizontal tail now attaches at the fin tip. Consequences in the
  deliverables: every fin case on both airplanes carries the **T7 tip
  transfer** (the concurrent balancing h-tail load plus h-tail inertia at the
  fin's last `GRID` — a load that was missing, not merely absent), the h-tail
  beam has the single fin-tip joint instead of a fuselage-side pair, and the
  LRA model ties the h-tail centreline to the fin tip. Two same-class sweeps
  (rule 4): the h-tail's **stations sit on the fin tip** on any T-tail
  (`tail_span._h_tail_waterline` read the wing root waterline regardless of
  layout — 146–180 in low on every T-tail fixture including
  `concept_regional_jet`; no load moves, the h-tail carries `fz` only, but the
  `GRID`s and the fin-tip joint were at the wrong waterline), and the
  three-view's defaulted T-tail/cruciform h-tail is drawn on the *resolved*
  fin (`fin_root + span`) instead of `fuselage_height/2 + span` above the wing
  root (32 in apart on atr42). Also rides this digest wave: the tail-span CSV
  `Fax`/`Sax` columns no longer print `-0.00` (a negated zero by construction,
  180 rows per h-tail CSV on every fixture) — the `-0.000000E+00` card half of
  the old Pri 13 was already closed by `_fmt3`. Imperial digest regenerated for
  the two twins' tail/balanced/LRA channels and `concept_regional_jet`'s
  h-tail/LRA channels; the negative-zero guard
  (`test_export_equilibrium.py::test_the_body_deliverables_never_render_a_negative_zero`)
  now covers the tail-span decks; the two tests that used atr42 as the
  conventional-with-outline example run on `cessna_210` / a reset layout.

- **Wing-tank fuel no longer rides both beams — `MassItem.wing_fraction`
  (backlog Pri 6 / #6, design note 29, tier L, 2026-08-17; schema **v53**, the
  0.6.0 freeze's one hop, additive with a `0.0` default, no migration hop).**
  On `atr42_100`, `dhc8_dash8` and `concept_heavy` the wing-tank fuel sat inside
  an undivided `"Fuel to gross"` row tagged `fuselage` while WINGINER's
  `concentrated` hung the same 3,800 / 4,000 / 1,200 lb on the wing — 11.6 /
  14.5 / 7.4 % of the derived body beam, above the base-method band, so every
  body inertia load, shear, bending moment and carry-through reaction on those
  fixtures was over-stated by `n ×` those pounds while the wing deck relieved
  with them, and the assembled case carried the fuel as body inertia with no
  wing relief. A row now states the fraction of its weight (and own inertias)
  the wing reacts; the remainder stays on `component`; both parts sit at the
  row's position, so WTONECG/WTENV/`cg_cases`/every derived `CaseLoading` are
  bit-identical (they read rows). One owner, `mass_distribution.reacted_parts`,
  turns rows into parts for `distribution()`, `balance` (wing/body inertia,
  self-inertia, body-drag fallback) and the CONM2 header; a drift guard pins
  that they agree. Fixture fractions are derived from WINGINER's own entries
  (3800/9174, 4000/4660, 1200/5500 — no number invented); the per-fixture
  "unmodelled wing mass" pin is deleted and survives as the reduction gate
  (strip the fraction, exactly those pounds reappear). The wing tie is now a
  validator (`wing_mass_tie_open`, both signs, with the remedy) plus two entry
  rules (`wing_fraction_out_of_range`, `wing_fraction_on_wing_row`). Measured
  consequences, all on the three fixtures only: body beams 32,751 → 28,951 /
  27,500 → 23,500 / 16,200 → 15,000 lb; wing-inertia scale 1.898 → 3.332 /
  2.333 → 3.667 / 1.000 → 1.667; and — the one effect the note did not predict
  in size — `Izz(closure)` **+33 / +31 / +29 %** because the fuel left the
  centreline lump for WINGINER's spanwise spread, so the twins' yaw and roll
  accelerations under the same fin load fell by a quarter to a third (fin load
  and `Ny` unchanged — inertia moved, not aero). Imperial digest regenerated
  for exactly those fixtures on the body / balance / LRA channels; every wing
  deck, every CONM2 card and every other fixture byte-unchanged; Appendix A
  untouched. `dhc8_dash8`'s hand-entered station table (25,890 lb) now
  *exceeds* the derived beam by 2,390 lb — it was written with the fuel on the
  body — and is pinned as such.

- **Flight Envelope: the SELECT Apply no longer persists un-applied geometry
  edits** (backlog **M4-22**). The "SELECT search inputs" form handler wrote the
  page's *probe* copy of the project back to session state, and that copy carries
  the live merge of the sidebar's "Apply geometry & altitudes" widgets — so
  pressing **Apply** inside the SELECT expander silently committed whatever the
  user had typed into that other form (tail CP stations XTC/XTF, the reference
  Mach, the altitudes editor) without its own Apply ever being pressed. The
  handler now writes only `select_input`, onto the session project, restoring the
  M2-3 "persist only on Apply" contract for both forms. New headless
  `AppTest` guard `tests/test_flight_envelope_view.py` pins both directions; the
  probe-copy pattern exists on this page alone.

- **The Dash 8's wing-carried main gear was fuselage mass in both mass models**
  (backlog Pri 1, decision **G-2**; the guard `gear_carrier_mass_disagrees`
  shipped 2026-08-14 and this is the correction it was written to force). The
  fixture states `main_gear.carrier = wing` — the leg sits in the wing-mounted
  nacelle — while the 1,200 lb `Main gear` item was tagged `fuselage` and
  WINGINER's `wing_mass.concentrated` listed only engine+nacelle and fuel: the
  same structure carried the ground load but not the weight, so the body beam
  carried 1,200 lb it does not hold and the wing lost the inertia relief of its
  own gear. The item is now tagged `wing` and a 600 lb/side `main gear`
  concentrated mass (BL 75, the trunnion butt line, at the item's own station)
  joins the wing model, so both models describe one airplane: the wing tie's gap
  stays **4,000 lb = wing-tank fuel alone** (up 1,200 on each side of the tie),
  and the "each gap has one cause" reading of
  `mass_distribution.unmodelled_wing_mass` survives. Dash 8 wing inertia moves as
  the physics says — root `Sz` −18,320 → −20,570 lb-ULT (exactly the leg's
  2,250 lb-ULT per side), `Mxx` −3.375e6 → −3.515e6, `Myy` 0.993e5 → 1.286e5
  lb-in-ULT — and the relief reaches the deliverable: net wing root shear
  50,400 → 48,150 lb-ULT (−4.5 %) and root bending 1.070e7 → 1.056e7 lb-in-ULT.
  Ten Imperial channels re-pinned on that fixture alone (an intended digest
  wave); the gear now brackets a second offset-couple node (BL 75 is inboard of
  the engine and fuel at BL 168/180), pinned per fixture in
  `test_offset_couples_exist_only_where_a_concentrated_mass_does`. No shipped
  fixture fires the carrier/mass guard now, and a new test re-mistags the leg to
  prove it still would.
- **The FAR 23 applicability gate read the item-database total as the design
  weight** (decision **G-14**'s deferred half; `WeightInput.direct_totals()` is
  renamed `database_totals()`). `applicability.design_weight_lb` took
  `speeds.weight_lb` when set and otherwise the *sum of every weight-database
  row* — an upper bound wearing the name of a design limit, since a database can
  hold full fuel **and** full payload at once (964 lb above MTOW on `atr42_100`,
  1,800 lb on `concept_regional_jet`). It now reads the MTOW SSOT through
  `cg_cases.max_takeoff_weight`, so the certification gate and every other
  consumer take the same number, and the database total — the *ceiling* of
  `OEW ≤ MLW ≤ MTOW ≤ Σ items`, owned by `cg_cases.database_total` — is no longer
  reachable from it.

  **Correcting the record:** the backlog, plan 18 §G-14 and the 2026-08-14
  history entry all state this moves the exceedance line 37,781 → 36,817 on
  atr42 and 34,800 → 33,000 on the RJ. Measured 2026-08-15, **it does not**:
  both fixtures set `speeds.weight_lb`, which won ahead of the database branch,
  so the gate already read the right number on all six fixtures. The defect was
  **latent** — live only for a project whose STRSPEED design weight is unset,
  i.e. one caught mid-entry, exactly when the banner is first consulted.

  Swept in the same change (practice 4), same defect class: the read-throughs on
  Structural Speeds and Weight & Mass Properties now offer the MTOW SSOT instead
  of the database total; Aircraft Comparison plots MTOW through its single owner
  rather than a weight no loading can reach; and the report's weights table row
  labelled **"Maximum takeoff weight (item sum)"** becomes two honest rows —
  "Maximum takeoff weight (MTOW)" from the SSOT and "Item database total
  (ceiling, not MTOW)". `test_design_weight_is_the_mtow_ssot_and_never_the_database_total`
  pins the *fallback*, where the defect lived, not just the happy path.
  Digest: `txt/weight_estimate` on the four concept fixtures (the concept note
  names the renamed method); no numeric channel moved.

- **`LATERAL_AERO_NOTE` stated the `n_y` error in the wrong direction** (defect
  found 2026-08-15 while writing the L-7 design note; text only — no computed
  number moves). The in-band lateral caveat shipped with B8a-3 told every reader
  that `n_y` *and* the yaw acceleration were **over-stated** and that the inertia
  they drive was therefore conservative. The yaw half is right — the missing body
  yawing couple is destabilizing and opposes the fin's — but the `n_y` half was
  backwards: at `+β` the missing body-and-wing side force acts the **same** way
  as the fin's restoring load, so it **adds**, `|n_y|` is **under**-stated, and
  the lateral translational inertia is **not** conservative. The sentence now
  states a direction **per degree of freedom**; both magnitudes stay *unknown* in
  band, because the measured figures (`docs/30_future/19_l7_lateral_body_aero_note.md`
  §7: `|n_y|` 4.1–12.0 % low on `concept_regional_jet`) come from a scratch run
  no shipped code reproduces, and a deck-header number must be one this tool can
  produce — quoting them stays part of backlog L-7. Corrected at every carrier:
  `balance.LATERAL_AERO_NOTE` (quoted verbatim by `report/methods.py`, so the
  report, the deck `$` header, the case notes and the UI follow), the
  `balance` module docstring, `CONVENTIONS.md` §1's L-7 bullet and
  `PROGRAM_SPEC.md`'s two lateral bullets. New
  `tests/test_methods_stamp.py::test_the_lateral_caveat_states_a_direction_per_degree_of_freedom`
  pins the two directions **separately**, since one sentence covering both is
  what got it wrong. Digest: `sbeam/balanced_deck` and `txt/balance` on the two
  fixtures with lateral cases (`ga6_normal`, `concept_regional_jet`); Imperial
  baseline regenerated, no numeric channel moved.

- **The balanced cases' pitch residual was attributed to two causes that the
  measurement refutes** (backlog Pri 5, the element-count study that item asked
  for; documentation and diagnosis only, no calc changed). Sweeping
  `SurfaceInput.elements` 5 → 640 shows the pitch residual converging by ~20
  elements onto a **non-zero plateau** (RJ PLAA 1.041 %, TORS 1.174 %, SIDE GUST
  1.586 %, flat to three decimals), which rules out the strip-quadrature lift
  floor (plan 11 R3). An exact three-term identity — derived by subtracting
  `flight_envelope._balance` from the assembled sum, where `wing_about_ac`
  cancels against `fuselage_cm` and the wing/body inertia moments cancel — then
  closes to the last printed digit on every case and shows the residual is
  `(zw − zcg)·(ΣFx_wing − dx)` almost in full: **the assembled model carries no
  non-wing drag**. The lift term never exceeds 0.086 % and the tail-station term
  is exactly zero on a clean configuration. M4-19 is ruled out on structural
  grounds as well as measured ones — `fuselage-cm` is a *free couple*, so no
  redistribution of it can change the resultant. The same missing load is the
  whole of the `nx` gap (ga6 PHAA closure 0.661 g against the trim's 0.610;
  `residual_fx` equals `ΣFx_wing` exactly), also element-independent. Backlog
  Pri 5 is re-titled "non-wing drag has no carrier in the assembled model", its
  superseded hypothesis marked rather than deleted, and its M4-19 pairing
  dropped. Corrected in `balance` (module and `_closure` docstrings),
  `report/content.py`'s over-the-gate message, `PROGRAM_SPEC.md`,
  `balanced_cases.md` and `theory_sources.md`.

- **"Strip quadrature" was the wrong name for the force-residual floor too**
  (same study; swept alongside the above per `CLAUDE.md` practice 4). The `Fz`
  residual also converges to a non-zero plateau — ga6 PHAA **−42.3 lb / 0.327 %**
  at 640 elements, against the −34.6 lb / 0.268 % seen at the default 20, which
  is that floor partly cancelled by the quadrature transient. Plan 11 R3's
  *identification* stands (strip lift integral vs the trim's closed-form
  `CL·q·S`); only the name was wrong, and it is now stated as a model difference
  with the converged number beside the default-element one.

- **The lumped fuselage `Cm` was documented as a small positive constant**
  (found by the same study). It is a slope term and **changes sign with `α`**:
  measured across every fixture case, −6.6 to +4.9 % of `n·W·MAC` on
  `ga6_normal` (the negative-`α` `NMAA` point) and −8.5 to +5.8 % on
  `concept_regional_jet`. The shipped "+4.3 to +6.3 %, positive (destabilising)"
  reading was taken over the symmetric wing conditions only and did not survive
  the negative-`α` and lateral points. Corrected in the five live sources that
  quoted it (`balance.py`, `PROGRAM_SPEC.md`, `balanced_cases.md`,
  `theory_sources.md`); the `40_history` and plan-13 copies are left as the
  record of what was measured at the time.

- **A ground case's LANDLOAD case number was printed as a "V-n point"**
  (0.6.0-candidate review finding **R6-C3**). `BalancedCaseResult.vn_case`
  carries the case's **source** case number, and the ground family's comes from
  LANDLOAD's 1–33 table rather than FLTLOADS' V-n envelope — but every surface
  that printed it used the flight family's wording, so "V-n point 19" on
  LANDLOAD case 19 sent a reader to a **real and unrelated** flight point: the
  silent-wrong-join class design note 17's case identity exists to prevent.
  The wording now has one owner, `balance.source_case_name` (family read off
  `is_ground`, with `case_source_name` for an assembled case), and all five
  surfaces the review named go through it: the assembled deck's `$` case header
  (`-- LANDLOAD case 19,`) and case map, `run()`'s condition titles, the
  balanced-case rows table — whose column is now headed **`Source case`** with a
  family-aware value, since the header itself claimed a table the row might not
  belong to — and `SkippedCondition.name`, which gained a `ground` field so the
  record states its own family rather than inferring it. Swept in the same
  change (CLAUDE.md practice 4): the shared `no-cg-case` skip reason, which the
  ground family also reaches, now says "its **source case** names a loading this
  project does not define"; and the Balanced Cases page's selector, which
  labelled a ground case's drift-direction hand a "roll". **Display wording
  only** — no case identity, number, load or `CaseRef` changed. The new owner is
  registered in the `CONVENTIONS.md` §7 single-source table with its guard,
  `tests/test_balance.py::test_no_surface_calls_a_ground_case_a_v_n_point`,
  which checks all five surfaces on every fixture that assembles ground cases
  and pins the flight wording in the same breath. **Digest wave:**
  `txt/balance`, `csv/balance` and `sbeam/balanced_deck` on the two fixtures
  with ground cases (`ga6_normal`, `concept_regional_jet`) — six hashes, one
  channel wider than the backlog row declared, because two of the five surfaces
  are in the assembled deck; no other channel or fixture moved.

- **The gear report CSV did not meet the load-output contract's column rules**
  (0.6.0-candidate review finding **R6-C2**, with the **R6-C4** hygiene items
  folded in per the backlog pairing). The G-12 companion file carried no unit
  on any force/moment column — and therefore no `-ULT` marker anywhere in the
  table — no per-case `SF` column, and in SI showed a millimetre value under a
  hard-coded `Stroke (in)` header, because no test read the SI gear CSV at all.
  The header row is now built from the resolved unit set
  (`_gear_report_headers`): every dimensional column states its unit, load
  columns carry `-ULT` (`lbs-ULT`/`lb-in-ULT`, `N-ULT`/`Nmm-ULT`), the two
  weights (inputs, never factored) carry the plain force unit, and `SF` is the
  last column on every row, per the F-R1 rule. The row dicts keep bare,
  system-independent keys — only the file header carries units. New `Wheel`
  column says which wheel a `main` row describes (starboard of the pair; the
  port twin is the mirror), previously said only in a code comment (R6-C4);
  the other two R6-C4 items landed byte-neutral (`balance.gear_sets` dropped
  its unused `nvp` parameter; `_gear_stroke_table`'s docstring paste blemish
  removed). Digest wave: `gear_report` on the five gear fixtures, exactly as
  declared — nothing else moved. Pinned both ways: an Imperial header/SF/Wheel
  contract test, and the SI-channel assertion whose absence let the defect ship
  (header labels plus one converted value per dimension).
- **Ground condition rows cited FAR 23.321, the flight balancing reference**
  (0.6.0-candidate review finding **R6-C1**). `balance.run()` derived every
  non-lateral, non-unsymmetrical row's regulation from the flight literals, so
  all up-to-27 assembled ground conditions rendered with 23.321 in the module
  result, the load-case CSV and the Results Review page — while the case's own
  `CaseRef` (which the deck map, case index and gear report flow through)
  correctly said 23.479(a)/23.481/23.483/23.485/23.493. A ground row now cites
  its `CaseRef`'s reference (fallback 23.471, the family's general sentence);
  the symmetric flight families deliberately keep their literals, because their
  `CaseRef`s name the V-n envelope source (23.333) while the *balancing* of
  that point is 23.321's requirement. The safety factor never moved (flight and
  ground families both derive 1.5, now classified under the right family row).
  Digest wave: `txt/csv balance` on the two ground fixtures, exactly as the
  backlog row declared. Pinned per fixture: every ground row's FAR equals its
  `CaseRef`'s, and every flight row still reads 23.321/23.349.
- **The loading named on LANDLOAD cases 20–24 was the wrong one.** The per-case
  record indexed the three roled loadings as `(m - 1) % 3` for every case up to
  24, but the 23.485 side family is three loadings × **two drift directions** —
  which the `WL` weight table and both unbalanced-moment tables already say
  (`wl[19] = wl[20] = wcg[0]·wr`). So five of the six side cases were reported
  against the wrong loading: case 21 is computed at *fwd max landing* and was
  labelled *fwd light*. `cg_name` was documented as cosmetic and the reactions
  themselves were always right, so **no load ever moved**; what moved is the label
  a reader joins a case to its loading by, and the `CG` column of the exported
  case index. Found while building the assembled ground cases, which have to
  build their inertia set at the loading their reactions were computed at.
  `landing._loading_index` is now the single owner of that mapping.
- **`is_handed` read "any load carries a free moment" where it meant the net.**
  Indistinguishable while the aileron couple was the suite's only free `mx` (one
  lumped couple at the centreline is its own net), and wrong the moment a ground
  case transferred both main-wheel reactions to their trunnions with equal and
  opposite lever-arm couples: every symmetric level-landing case minted handed,
  emitting a twin that was the same load set mirrored onto itself. No shipped
  flight case changes hand.
- **Documentation currency batch** (0.6.0-candidate review findings
  **R6-D1/D2/D3/D4**, `docs/50_reviews/2026-08-15_review_0_6_0_candidate.md`):
  this changelog's `[Unreleased]` headings restored to Keep-a-Changelog order
  (five `Added`-class entries had been filed under `### Fixed`); the backlog's
  "shipped since the tag" narrative gains step 9 and D-24, which a release-notes
  drafter working from it would otherwise have dropped; plan 09's status header
  now says T6–T8 shipped (it read "T6–T8 remain" against the history file); and
  `docs/00_INDEX.md` gains rows for design notes 14 and 18 (the latter is the
  0.6.0 headline's decision record). Documentation only — no code, no digest.

## [0.5.0] — 2026-08-13

### Release notes — what a 0.5.0 deck does and does not carry

0.5.0 makes the **assembled full-span free-free airplane deck** the primary
loads deliverable: aero and inertia together, left and right hands, a CONM2
mass model beside it, and global equilibrium proved continuously in CI. Four
standing caveats govern how far a deck from this release can be carried. Each
travels in band — on the deck's `$` header, the case notes and the report's
methods & limitations section — so this list is a summary, not the source.

- **The fuselage deck is flight-only.** No ground reaction, landing or
  pressurization case is distributed onto the body; the ground/landing families
  are the 0.6.0 headline (decision **D-R3**). A body deck from 0.5.0 sizes
  flight cases and nothing else.
- **Lateral aerodynamics are fin-only (decision L-7).** The fin's own side load
  is the only lateral aerodynamic force the suite computes — there is no
  fuselage or nacelle `Cy_β`/`Cn_β` — so lateral load factors and yaw
  accelerations are **over-stated and conservative**, not correct. Do not read
  `n_y` or `ψ̈` as a lateral response of the airplane.
- **The 23.427(a) unsymmetrical horizontal tail ships as a handed pair, and it
  is a *maneuver* case.** An asymmetric case exists only as a starboard/port
  twin by centreline reflection; a reader given one hand must know the other
  exists. Its V-n point is the maneuver point, not a gust point.
- **`concept_heavy` is closure-locked, not oracle-locked** (decision **D-R6**),
  as is every concept-mode result above the FAR 23 calibrated band. Concept mode
  is an unverified extrapolation with a stated physics-closure gate behind it —
  it is not a validated analysis, and the report says so wherever the figures
  are read.

The FAR 23 replication core remains oracle-locked to Appendix A within ±0.1 %;
concept mode reduces exactly to it on GA inputs. Verification baseline for this
release: [`docs/40_history/09_verification_baseline_0.5.0.md`](docs/40_history/09_verification_baseline_0.5.0.md).


### Added

- **The report's known-limitations list is every open caveat, and says so
  testably.** 0.5.0 row 2, review finding **F-R4**, decision **D-R3**. The list
  claimed completeness and was missing four: the **fin-only lateral aero** (the
  only lateral aerodynamic load the suite computes, so `n_y` and yaw
  acceleration are over-stated), the **lumped aileron couple** (23.349 applied
  at the wing AC because there is no aileron spanwise geometry), the **wing
  stick model's centreline clamp** (its SPC reaction is the half-span total, not
  a wing root design load) and the **flight-only fuselage deck** (no ground
  case, per D-R3 — stated now as a positive claim, not as two adjacent absences).
  - **The assumed tail planform now reaches the report.** `resolve_tail_planform`
    derives a rectangle from the area/span scalars when `geometry.surfaces`
    carries no entry for the surface and marks it ASSUMED; that marker reached
    the page, the CSV and the result and stopped, so the controlling document
    described the distribution as if the planform had been entered. It is a
    **conditional** limitation, resolved from the project's own inputs so a
    headless bundle states it too, and it names the surface — no shipped fixture
    enters a tail planform, so every current bundle carries both.
  - **One wording per caveat.** Where a caveat also travels in band, the report
    quotes the owning module's constant verbatim rather than paraphrasing it:
    `balance.LATERAL_AERO_NOTE`, the new `balance.AILERON_COUPLE_NOTE` (extracted
    from the ACRL case note, unchanged text, so no deck byte moved) and
    `sbeam_bridge.CENTERLINE_CLAMP_NOTE` (reworded once to serve both the deck
    and the document; `wing_stick` digests regenerated).
  - **The completeness guard:** standing limitations are declared with stable
    keys and the key set is pinned by test, so opening or closing a caveat is a
    visible edit in the same commit rather than a silent omission; separate tests
    assert each one reaches the statement, that the in-band and report wordings
    are one string, and that the conditional planform caveat is absent when a
    planform is entered. `SUMMARY_REPORT.md` §4.6 now states the contract.

- **The wing stick deck states its centerline clamp, and every deck `$`
  comment now fits the card width.** 0.5.0 row 1, closing the last of the
  release's Phase-1 deliverable items and the wing/tail decks' own digest
  regeneration. Two parts, landed together because they move the same exported
  wing bytes:
  - **The clamp caveat** (plan 10 §1.1, filed 2026-08-08 and not shippable then
    because that step's acceptance forbade any exported byte change). The wing
    stick model's `SPC1` now carries a `$` note naming the clamped node as the
    aircraft **centerline** (BL 0, half a strip inboard of station 0 — every
    fixture defines the wing LE polyline from the centerline) and its reaction
    as the **half-span total applied load**, not a wing root design load. It
    states why relocating the SPC would not help — one clamp reacts the whole
    applied load wherever it sits, so the side-of-body quantity is an internal
    CBAR load, and the deck has no node at the side of body — so a consumer
    reads the limitation off the deck instead of discovering it against a
    23 %-high root bending. The real fix stays filed as the side-of-body
    reporting-node item.
  - **The 72-column sweep now covers the wing decks.** Free-field bulk data is
    72 columns; the wing `$ Axes:` and `$ FORCE set sums to root Sz … Myy …`
    lines overran, reaching ~100 columns in SI where the same numbers are wider
    (cosmetic — `$` is a comment to every parser — but the carve-out was the
    only deck family the width guard skipped). Every generated `$` sentence in
    the bridge now goes through one `_comment()` emitter that wraps at 70, so
    the width is a property of the emitter rather than of each hand-fitted
    sentence, and `test_deck_comments_fit_the_free_field_card_width` sweeps
    `wing_cards` and `wing_stick` in both unit systems alongside body/tail/
    control. The unit statement moved to its own `$ Lengths in <unit>.` line:
    wrapping can split a clause anywhere, and that is the one line consumers
    grep for.
  - **Imperial digests regenerated deliberately**, and the diff is exactly the
    two intended channels — `sbeam/wing_cards` and `sbeam/wing_stick` on all
    six examples, 12 lines. No calc number moved; the balanced deck, whose
    digest regeneration was spent three times over on D-R7/D-R8, is untouched.

- **The 23.427(a) unsymmetrical horizontal tail is a balanced case.** 0.5.0
  row 1 — decision **D-R8**, review finding **F-R5**, the release's one L-tier
  physics step. `build_balanced_cases` gained a third component branch, and with
  it the assembled deliverable gained the one horizontal-tail condition that has
  a **hand**: FAR 23.427(a) puts 100 % of half the governing tail load on one
  side and `min(100 − 10(n−1), 80)` percent on the other, and until now that
  left/right content had no assembled representation at all — the full-span tail
  topology (plan 09 **T-8**) had been built for it and nothing used it. It ships
  as a handed pair per fixture (`HT-09R`/`HT-09L`, SUBCASE 7209/8209 on
  `ga6_normal` and `concept_regional_jet`), which is precisely 23.427(a)'s
  "either side".

  - **SELECT's split is distributed, never recomputed**, through the full-span
    `tail_span` table (`balance.htail_sets`, `source="htail-air"`) — air only,
    the surface mass riding the closure field with everything else, so each mass
    still enters exactly one field. It **replaces** the lumped trim tail load
    `vn.lt`: `RH + LH` *is* the condition's whole tail load, and carrying both
    would count the balancing part twice.
  - **The pre-closure residual is the maneuver, and is reported rather than
    gated.** 23.427(a)'s load is a *maneuver* load and its V-n point is a
    balanced one at `n_z ≈ 1` — an abrupt elevator input with the wing still at
    trim lift — so the airplane is genuinely out of trim: −49.8 % of `n·W` and
    144 % of `n·W·MAC` on `ga6_normal`, closing as Δn −0.496 g and
    q̇ +637 deg/s². That is the standard treatment of an unbalanced pitching
    maneuver, and it is the case that sizes the aft fuselage. What **is** gated,
    at the usual 1 %, is the case's *trim half* — the same case with the lumped
    load restored (0.301 % on the ga6). Said in-band on the deck header, the
    case notes, report §6 and the Balanced Cases page, never left to be worked
    out from a number that looks like a failure.
  - **Two closed forms check what is applied**, standing in for the printed
    oracle concept mode does not have: each half sums to SELECT's own `RH`/`LH`
    exactly (6.7e-16), and the applied rolling moment is `(RH − LH)·ȳ` with `ȳ`
    the chord-weighted half-planform centroid — ratio 1.000000000 on both
    fixtures.
  - **Handedness now reads the distribution's own roll.** This case carries no
    side force and no free `mx`, so `is_handed` would have minted it *unhanded*
    and emitted one twin; it gains a net-rolling-moment test against
    `HANDEDNESS_TOL · n·W · b/2`, where the two populations are fifteen orders
    apart (a mirror-symmetric set nets 1e-17 of that scale, this case 1.7e-2).
  - **Fixed, found by building it: the closure was referred to the entered CG.**
    The rigid-body relief field is now solved about the **mass set's own
    centroid**. The two coincide on every loading the fixtures had before — which
    is why a decoupled `n = F/W` solve never showed it — but `ga6_normal`'s
    `CG4` sits 0.0024 in forward and 0.0052 in below its entered CG, and an
    angular acceleration about the wrong point leaves `−ω̇ × Σ wᵢrᵢ` of unclosed
    force: nothing at a trimmed case's ω̇, **0.31 lb of `Fx`** at 637 deg/s²,
    four orders above the closure gate. The reported residual is still stated
    about the CG; only the relief is solved where it is exact.
  - **The assembly record stops calling the h-tail out-of-family.** Its
    symmetric conditions are not excluded — they are *already in* every balanced
    case as the trim tail load — so they are recorded under a new
    `htail-symmetric` reason that says so, leaving `out-of-family` for the
    fuselage, ground and one-engine-out conditions it actually describes.

  Design note: [`docs/30_future/16_d_r8_unsymmetrical_htail_note.md`](docs/30_future/16_d_r8_unsymmetrical_htail_note.md);
  method and worked numbers in `docs/20_theory/balanced_cases.md` §8. Gates:
  eight in `tests/test_balance.py` plus the solver leg. **Bytes moved:** the
  four new subcases regenerate `csv/balance`, `txt/balance` and
  `sbeam/balanced_deck` on the two fixtures that assemble — and nothing else,
  the closure's new reference point being a no-op everywhere the two points
  coincide.

- **`concept_heavy` joins the sbeam round-trip gate.** 0.5.0 row 1 — the
  remainder of decision **D-R6**, whose diagnosis (review **F-C6**) had already
  restored the fixture's export. Its wing deck now solves in the real solver, in
  both unit systems, on the `WING_MATRIX` leg of
  `tests/test_sbeam_roundtrip.py`. It is the only fixture in that matrix whose
  wing cases name **only** a V-n case reference — no `cl`, no `v_eas_kt`, no
  `nz` — so until now the *derived* CL/V route, the one F-C6 found broken, had
  no solver coverage at all: the deck it produces was never handed to sbeam in
  CI. It also carries a second, differently-shaped concentrated wing item (a
  600 lb store per side, offset in `z` as well as `x`), so the offset-couple
  `MOMENT` cards are now exercised on two independent geometries rather than
  `atr42_100` alone. Wing leg only — the fixture assembles no balanced case, so
  it has no body, tail or assembled deck to gate. No shipped bytes move.

- **The assembled deck and the mass model are first-class deliverables.** 0.5.0
  row 1 — decision **D-R2**, review finding **F-D2**. The mission's *primary*
  loads output was a page-only download: `balanced_airframe.bdf` left the tool
  from the Balanced Cases page carrying no methods stamp, named by no report
  section, no manifest row and no Export bundle, and the three CONM2/MASSSET
  files left it the same way from the Weights page. An artifact the controlling
  document does not name travels without a basis — which is exactly the state
  the G8.3 stamp and the manifest exist to prevent. All of it closes together:

  - **Report §6, "Balanced free-free airframe cases."** Per case: load factor
    `Nz`, the **pre-closure** residuals against the 1 % gate, the applied roll
    couple and the closure relief (`Δn`, `Δn_y`, yaw and roll acceleration) —
    literally `balanced_case_rows`' own rows, the ones the deck header and the
    Balanced Cases page render, so the report cannot describe a different
    assembly from the deck beside it. Plus the handed twin-pair statement (an
    asymmetric case ships as a starboard/port pair; a reader shown one hand must
    be told of the other) and the **mass-case identity** table: which payload
    case is which `MASSSET`, at what weight and CG, with every case the weight
    database cannot produce marked NOT EXPORTED and its reason. A project that
    assembles nothing keeps the section and says so.
  - **Manifest rows** for `balanced_airframe.bdf`, `mass_model.bdf`,
    `mass_check.bdf` and `inertia_only.bdf` — each with its units, its
    convention and the section that summarises it — listed only when the bundle
    will actually contain them, because a manifest naming a file that was never
    written sends the reader looking for it.
  - **The Export bundle** carries all four, stamped with the same `_bdf_stamp`
    and written in the same resolved unit system as every other deck, so "one
    bundle, one system, one basis" still holds by construction; they also get
    their own download row on the page.
  - **The two page-level downloads are stamped** (the routes F-D2 named): the
    Balanced Cases deck and all three Weights-page mass files. A CONM2 set whose
    `M` is read as weight is wrong by 386× in a file that parses cleanly, so the
    unit statement travelling in-band is not a formality.
  - **One mint for the mass-case identity** (CLAUDE.md practice 3):
    `mass_cards.massset_identity(loading, index)` is now the sole source of a
    case's `MASSSET` SID and label, read by the cards, the report and the
    manifest; `mass_case_rows` is its row form. The balanced assembly likewise
    runs **once** per report (`content.balanced_run`), shared by §4's
    skipped-conditions record and §6, so the two halves of that statement cannot
    describe different runs.

  No exported byte moves: the deck writers were already stamp-capable and the
  digests are unchanged. Guards: the Export page's stamp-and-system source
  guards extended from 5 decks to 9 and from 11 writer calls to 14 plus the
  balanced deck, and seven new report-content tests pin the section, the twin
  pairs, the identity mint, the NOT EXPORTED path, the absence statement and
  both directions of the manifest rule.

- **The deliverable is scriptable: every export target, stamped, with one error
  contract.** 0.5.0 row 1 — review findings **F-D1**, **F-C2**, **F-D3**, minor
  **m2**, decision **D-R5**, absorbing the long-open **L-8g**. The mission is a
  *scripted* concept-loads → sbeam sizing loop, and the headless route did not
  reach the deliverable: `--export-target` offered wing, tail, the two spanwise
  empennage surfaces and control surfaces, so the **fuselage** deck (FORCE cards,
  span CSV and the wing-attach fitting loads) was unwritable from the CLI and the
  **assembled full-span balanced deck** — the mission's *primary* artifact — had
  no headless route at all, downloadable only from a Streamlit page. It does now,
  as does the CONM2 mass model (`--export-target mass`, the same owner and file
  names as `--export-conm2`). `cli.EXPORT_TARGETS` is the one list, handed to
  argparse and pinned against the CLI docstring, so a target cannot be
  implemented without being offered or offered without being implemented.

  Two things travel with it. **The CLI wing deck is now stated about the loads
  reference axis** (decision D-R5): the CLI passed the writers a bare result
  list, so the LRA boundary transfer never ran and a headless deck's torsion,
  station X and lever arms were about the 25 % chord while the GUI's were about
  the LRA — labelled in-band, so not silently wrong, but the module contract was
  defeated on exactly the route the sizing loop scripts. The two front-ends now
  emit the same deck, pinned by test on a project whose LRA is *not* the quarter
  chord; on every shipped fixture `ref_axis_pct` is 0.25, so **no exported byte
  moves and no digest regeneration was needed**. And **every headless CSV and BDF
  now carries the Step G8.3 methods & limitations stamp** (L-8g / F-D3),
  including `-o` module CSVs and all three `--export-conm2` artifacts: a headless
  export stated its ULTIMATE basis, its category and its approved corrections
  nowhere, which made it the one channel in the suite whose files were not
  self-describing when forwarded. One stamp per run, built from the resolved unit
  system and handed to every writer; no timestamp unless `--generated` supplies
  one, so two runs of one project stay byte-identical and diffable.

- **One CLI error contract.** Review **m2**: the `control` target caught every
  `ValueError`, so a mistyped aileron area was indistinguishable from an airplane
  with no aileron — the deck simply came out a case short — while an all-skipped
  run raised through `main` as a traceback, the wing and tail targets let
  `MissingInputError` reach the terminal raw, and only `--export-conm2` caught
  and printed. Now, on every route: `error: <message>` on stderr, exit status 1,
  no traceback and no partial artifact set. The one deliberate exception is that
  an **absent** control-surface slice still skips that surface (the three are
  independent inputs) while an **invalid** one fails the run — the
  `MissingInputError`-vs-`ValueError` distinction the error-handling contract
  already draws, applied at the CLI boundary.

- **The balanced assembly now states what it did *not* assemble.** Review
  finding **F-C7**: a condition whose V-n point was missing, whose CG case was
  unknown, or whose payload loading the weight database cannot derive was
  dropped by `build_balanced_cases` with no record on the `ModuleResult`, in the
  deck, or in the report — and the only thing standing between that and a user's
  project was a test that pins the *shipped fixtures'* drop set. On
  `concept_regional_jet` the primary deliverable has been quietly missing NMAA;
  it now says so, in the deck's own `$ CONDITIONS NOT ASSEMBLED` block, in report
  §4, on the Balanced Cases page, and as a final "Assembly record" condition on
  the module result. Each entry names the condition, its V-n point and a reason
  from one of five codes, with the deliberate exclusions (h-tail, fuselage,
  ground, one-engine-out) recorded as such rather than left to be inferred from
  their absence. The record is emitted whether or not anything was skipped:
  "every condition assembled" is the completeness statement. The gate is the
  property rather than the fixture — assembled ∪ recorded is exactly SELECT's
  condition set, and the two are disjoint, on every example — so a sixth
  `continue` cannot be added without a reason travelling with it. Imperial
  baseline regenerated for the three affected channels (balance CSV, balance
  text report, assembled deck) on the two fixtures that assemble.

- **One owner for every exported id band: `sloads/export/bands.py`.** Review
  findings **F-C1** (the defect) and **F-G3** (its root cause). GID/EID/SID runs
  were per-file constants with docstrings claiming disjointness, checked by two
  tests that hand-enumerated the families their authors remembered — so when the
  balanced deck opened `4001+` for its right wing, which the spanwise h-tail deck
  already owned as `4001–4500`, nothing saw it for two months. A splice of those
  two decks would have summed a wing load and a tail load on one node in a file
  that parses cleanly. The registry declares every band (name, kind, start, size,
  owner, and why it sits where it does) with the whole map in its module
  docstring; every allocator now goes through `Band.allocate`, which raises on
  overflow instead of walking into the next family — closing review **m5**, the
  wing station allocator that had no capacity guard at all, and giving the
  control-surface band its first one (`control_station_gid`).
  `tests/test_bands.py` asks the disjointness question of the **whole registry**
  pairwise, and — the part that makes it blind-spot-free — sweeps the module
  globals of every module under `sloads/export`, failing any id-base constant
  that is not a registered band's start. A future deck family cannot re-open the
  hole by forgetting a test. `case_ids.SUBCASE_BLOCK` stays the allocator for the
  per-component subcase SIDs (calc must not import export); the registry mirrors
  them and a test pins the mirror so neither can move alone.

- **The assembled deck's card-text closure gate now checks all six DOF.** Review
  finding **F-G1**: `test_the_deck_balances_from_its_own_cards` asserted `fx`,
  `fz` and `my` while `equilibrium.Resultant` had carried the lateral three all
  along — so the node-collapse failure mode the gate exists for (in memory 1e-13,
  in the deck 3.9–21.9 % out) could hit a fin `FORCE` card or a reflected
  port-twin node and unbalance `fy`/`mx`/`mz` with nothing looking. Not
  theoretical since B8a-3: every assembled deck carries eight lateral cases, and
  the handed twins differ *only* in those components. Roll and yaw are judged
  against the **semi-span**, the same lever `roll_residual_fraction` uses, so the
  deck gate and the closure report agree on what "small" means.
  `test_the_lateral_half_of_the_deck_gate_has_teeth` measures the gain: one
  reversed lateral `FORCE` card leaves `fy` 3.4 %, `mz` 3.1 % and `mx` 0.20 % out
  while `fx`/`fz`/`my` stay at 1e-9…1e-8 — the old gate would have called that
  deck balanced. Swept to the sibling free-free gate in the same change (required
  practice 4): the body deck's `Σ = 0` claim now covers its other four
  components, which are zero by construction on a planar flight-only deck and
  will go red — deliberately — when the ground cases bring side and drag loads.

- **The CONM2 mass model is now solved in CI — the fourth deck family, in both
  unit systems.** Plan 12's **C6** leg, open since 2026-08-08 and the reason the
  `GRAV` defect below could ship: the mass-check deck is handed to the real
  sbeam, which accelerates the `CONM2` set through its own mass matrix and must
  reproduce sloads' per-case inertia **at every node**, Imperial and SI
  (`tests/test_sbeam_roundtrip.py`, `ga6_normal` / `concept_regional_jet` /
  `atr42_100`, at Nz = 2.5). Three statements with independent producers: the
  clamp reacts the case's own weight, the recovered nodal loads equal
  `inertia_only_cards(loading=...)` card for card, and the cases differ from each
  other *in their distribution* (the regional jet's two cases weigh the same and
  differ only in CG, so a total-only check would pass vacuously). The leg's teeth
  are a reproduction of the C1 defect itself: a 25.4×-low `GRAV` must fail it.
- **`inertia_only_cards` can state a payload case.** Given a `loading` it writes
  that case's mass node by node — wing items included, on the node their `CONM2`
  hangs on — which is the only form that can equal sbeam's recovery rather than
  merely resemble it (the gross Ch 15 beam table is case-independent and carries
  no wing). Default output is byte-identical; the CLI and the Weights page are
  unchanged. New `mass_cards.case_station_weights` owns the gathering, built on
  the same `_attach_gid` the cards are written with.
- **Known sbeam limitation, pinned rather than worked around silently.** sbeam's
  SOL 101 assembles its `GRAV` load vector from the **baseline** mass matrix and
  never reaches the `MASSSET` resolver, so at the pinned commit every payload
  subcase of the shipped mass-check deck accelerates the same mass (`ga6_normal`:
  2063 lb four times, against case weights 3400/3400/2800/2063). The round-trip
  leg therefore folds each case into a baseline deck first
  (`export/roundtrip.flatten_mass_case`, test-only, and it may re-select cards
  but never rewrite one). `test_the_shipped_mass_deck_hits_the_sbeam_massset_gap`
  records the behaviour and is *meant* to go red when sbeam fixes it.

- **The summary report states its sign conventions, with pictures.** A new
  required section **"2. Axes and sign conventions"** (SUMMARY_REPORT.md
  §4.2.1, design note 15): the frame and reflection prose, a
  conventions-of-record table citing the charter per row, and three static
  inline-TikZ figures (`sign_axes` / `sign_controls` / `sign_beams`) drawing
  +α/+β, the moment senses, the control and rotation signs, and the
  per-component shear/moment/torsion diagram conventions. Single-sourced in
  `sloads/report/conventions_tex.py`, drift-guarded by
  `tests/test_report_conventions.py` (frame vs `export/coordinates.py`, the
  §3.3 sentences verbatim, greyscale/ASCII/determinism). Downstream sections
  renumbered (Envelope figures → 3 … Methods → 6). With it, the six formerly
  unstated conventions are decisions of record **SC-1…SC-6**
  (`CONVENTIONS.md` §1.1, user-approved 2026-08-10): +β = wind from starboard,
  +rudder = TE to port, rates right-handed/attitudes not modelled, twist
  nose-up-positive (verified in the Schrenk basic-lift formula), gear V/D/S in
  airplane axes, aileron hand named per case. Labels only — no computed number
  changed anywhere.


- **The vertical tail carries inertia on both of its axes** (user decision
  2026-08-10, **superseding plan 13 decision L-8 for the per-condition view**).
  A fin's normal axis is lateral, so the vertical acceleration that *bends* a
  horizontal tail *compresses* a vertical one, and the fin needs two terms where
  the h-tail needs one:
  - **bending**, `−n_y·W_vt`, with `n_y = (LT25+LT50)/W_case` — the free-free
    lateral response to the fin's own load, the only lateral aerodynamic force
    this suite models. It relieves the surface total by **exactly** `W_vt/W_case`
    (0.68 % on `ga6_normal`, 1.84 % on the RJ), which is what makes it
    self-checking, and it inherits decision **L-7**'s caveat: with no fuselage or
    wing sideslip force modelled, the real airplane's `n_y` is smaller and that
    relief is an upper bound on itself. Stated in-band on every fin result, deck
    header and UI row — including that it is the unconservative direction.
  - **axial**, `−n_z·W_vt`, along the span: it compresses the fin and bends
    nothing. New `WingStationLoad.f_span`/`.s_span` columns, mapped to airplane
    axes by the new `coordinates.tail_axial_to_airplane`, and carried in the same
    `FORCE` cards as the normal load.

  A fin condition naming no V-n point has no case weight, so it gets **no**
  lateral term and says so, rather than dividing by a gross-weight stand-in.

- **`component` is editable on the Weights page.** The weight data base's item
  editor exposed `kind` but never `component`, so the tag that decides which beam
  carries each item — and which is now the *only* way to enter tail mass — could
  not be set in the GUI at all. It is a select column with a blank (untagged,
  inferred) option, and the Tail Span Loads page's own mass form is **gone**:
  that page now shows the derived weight read-only, names any untagged surface,
  reports any override, and links back to the page that owns the data.

- **Tail gates**: the fin's `Σ inertia / Σ air ≡ −W_vt/W_case` identity; the axial
  column against `−n_z·W_vt` with a proof it makes no bending; the derived weight
  against each fixture's tagged items; a regression gate that **no shipped
  fixture produces an air-only h-tail deck**; the override/reconciliation path;
  the v44 migration hop; and a balance gate that the applied fin set is air only.

- **`coordinates.bending_moment_vector`** — the single owner of the wing bending
  sign map. `Mxx` maps to `+x` but `Mzz` maps to `−z` (the calc stores both as
  positive-magnitude integrals, against a right-handed `r × F`); that asymmetry
  now lives in one function instead of being spelled out at the card writer and
  copied again at its gate.
- **Wing deck gates**: bending closure now covers **both** channels on **all six**
  fixtures with no exception (the old test asserted the *negation* on the three
  affected ones); a new station-by-station gate asserts shear and bending at
  *every* node, which is what separates the offset couple from the force split
  originally proposed; and a guard pins that the couples exist at exactly the
  nodes bracketing a concentrated mass and nowhere else.
- **`atr42_100` joins the sbeam round-trip wing leg** (`WING_MATRIX`). The solver
  matrix was `ga6_normal` + `concept_regional_jet`, both mass-free, so nothing
  proved the real solver *honours* an `Mx` component rather than dropping it.
  Assertion W-d — element 1's end-B bending against the NETLOADS root `Mxx` —
  read 1.91 % high there until the couples existed.
- **Span-load CSV** gains `Mx`/`Mz` columns, keeping its stated contract that the
  applied-load columns *are* the exported `FORCE`/`MOMENT` cards.


- **Lateral balanced airplane cases — the ±β empennage set** (mission phase 4
  step 8, [plan 13](docs/30_future/13_b8a_lateral_closure_plan.md) step
  **B8a-3**, decisions **L-6**/**L-7**/**L-8**). The four vertical-tail
  conditions (`SUDDEN RUDDER`, `YAW TO SIDESLIP`, `YAW 15 NEUTRAL`, `SIDE GUST`)
  now assemble as full-span free-free cases, each as a **handed pair** —
  `VT-01R`/`VT-01L` … `VT-04R`/`VT-04L`, the starboard case computed and the port
  one its mirror. Eight new cases per fixture on `ga6_normal` and
  `concept_regional_jet` (15 and 14 balanced cases in total).

  The fin's distributed side load is SELECT's, strip for strip, reaching the case
  through `tail_span` and the existing frame map in `export/coordinates.py` (span
  → `z`, normal force → `fy`, torsion → `mz` **negated**). Fin **inertia** rides
  in the closure field at the case's own `n_y`/`ω̇` rather than in the
  per-component v-tail deck, which stays air-only (decision **L-8**).

  **Nothing balances a rudder kick**, and the deck says so: a lateral case's
  pre-closure `Fy`/`Mz` *are* the fin load in full, by construction, so plan 11's
  1 % residual gate does not apply to them — exactly the standing `ACRL`'s roll
  residual has had since B7. What is gated is that the case's **symmetric half**,
  with the fin set removed, still closes as it always did; it does, to the last
  digit, because the fin set carries `fy` and `mz` only.

  Reported per case, in the deck header, the balanced-case table and the module
  result: the applied fin side load, the lateral load factor `n_y = L_v/W`, and
  the yaw and roll accelerations it drives — for example `ga6_normal`
  `SUDDEN RUDDER` +585.7 lb, `n_y` +0.172 g, `ψ̈` +178.0 deg/s², `ṗ` −12.0
  deg/s²; the RJ's `YAW 15 NEUTRAL` −8042.7 lb, −0.244 g, −55.7, +68.4. All four
  numbers are pinned per fixture in CI in both directions.

  **A stated limitation, carried in-band** (decision **L-7**): the fin is the
  only lateral aerodynamic load this suite computes — fuselage and wing side
  force in sideslip are not modelled — so `n_y` and the yaw acceleration are
  **over-stated by an unknown amount**, and the inertia they drive is
  conservative on every component. The fin's own design load is SELECT's,
  unchanged. The caveat travels as a case note into the deck `$` header and the
  report rather than living only in documentation.

  **The assembled deck carrying these cases solves in the real sbeam** with its
  determinate support reacting zero in all six components (plan 13 **G3**, step
  **B8a-4**) — the first time the round-trip gate exercises `fy`, `mx` and `mz`.
  Two additions make that statement worth its zero target: every assembled case
  must appear as a subcase and each lateral one must carry real side load into
  the solver, and a **negative control** reverses the fin load alone and asserts
  the support then reacts `+2·L_v·SF` in `y`, with the roll and yaw reactions
  moving with it. Both unit systems, both fixtures, in CI.
- **Theory document for the balancing method** —
  [`docs/20_theory/balanced_cases.md`](docs/20_theory/balanced_cases.md): how a
  balanced free-free case is assembled and closed, with worked examples on the
  shipped fixtures (ga6 PHAA symmetric, ga6/RJ ACRL antisymmetric) and the
  design-of-record lateral empennage cases on a conventional low tail (ga6) and
  a T-tail (RJ), every shipped figure mapped to the CI gate that pins it.
- **`VTailLoadsInput.vtail_root_waterline_z`** (schema **v43**) — the fin root
  waterline, stated rather than derived. `0` means "derive it and mark it
  `assumed`", which every shipped fixture still does; the derived value and the
  branch that produced it are carried in-band on the result, the page and the
  deck `$` header. Additive with a default, so no migration hop: a pre-v43
  project keeps exactly the placement it would have been given.


### Fixed

- **`scripts/smoke_test.sh` — the §3.5 release gate — read the G8.3 methods
  stamp as the CSV header row and failed the release it was gating.** It took
  line 1 of the CLI's output as the header, but since G8.3 every exported CSV
  carries the methods & limitations statement as `#` lines above it, so the
  script saw `# METHODS AND LIMITATIONS` and reported an unexpected header. The
  in-repo *Python* readers were audited when the stamp landed
  (`workbook._csv_to_df` reads with `comment="#"`); this shell one was not. It
  now skips comment lines like every other reader, counts rows from the data
  block, and additionally **requires** the stamp to be present — so the gate
  proves the CLI's deliverable states its own basis rather than merely tolerating
  the lines that say so.

- **The `.xlsx` workbook stated one unit system for two channels** (review
  **m14**; SUMMARY_REPORT.md §3.5/§4.7). One workbook carries both: the module
  and case-index sheets are the HUMAN channel, the span-load sheets are the
  SOLVER channel that feeds the sbeam decks — and in SI those sets differ
  (`N·m`/`kPa` against `N·mm`/`MPa`). The Project sheet's single `Units` row
  therefore mis-stated every span sheet in the workbook by a factor of 1000 in
  moment, which is exactly the failure the in-band statement exists to prevent
  ("a per-file units column that disagrees with that statement is a conformance
  failure, not a footnote"). `build_workbook` now owns the statement instead of
  taking it from the caller: it resolves both channels once from the deliverable
  `system` it is given, writes each data sheet's own set into cell `A1` above
  that sheet's header row, and names both channels plus the unconverted
  KEAS/ft exception on the Project sheet. The case index, which carries no load
  quantity at all, states that rather than claiming either set. Two new tests
  build the workbook in **SI** — where the channels are distinguishable — and
  require each sheet to carry its own set and neither to carry the other's, plus
  a guard that the header row still parses one row down.

- **The "not a certification document" disclaimer travelled on the report's
  title page only** (review **F-R3**; SUMMARY_REPORT.md §4.6 item 9) — the one
  page that does *not* travel with a forwarded file. It was absent from
  `methods_statement`, which is what lands in `METHODS.txt`, every CSV `#`
  header, every BDF `$` header and the workbook's *Methods* sheet, so a deck or
  a span CSV read on its own carried ULTIMATE loads with no statement of what
  they are not. The disclaimer is now a `STATUS:` block **leading** the
  statement — ahead of `BASIS:`, so a reader who skims only the head of a
  stamped file still meets it — and `latex.py`'s title page quotes the same
  `STANDING_DISCLAIMER` constant instead of restating the sentence, adding only
  its pointer to the methods section (two wordings of one disclaimer is two
  disclaimers). The stamp guard, which previously enumerated only the
  implemented blocks and so pinned the omission, now requires `STATUS:`, checks
  the sentence survives both comment wrappers, and pins the single wording
  across the cover and the statement.

- **The governing-loads tables applied a flat 1.5 instead of each case's own
  safety factor** (review **F-R1**; the report-side slice of M4-8 Layer 1).
  `report.governing_loads_table` scaled and labelled every row with
  `ULTIMATE_FACTOR`, ignoring `CriticalCondition.safety_factor` — the model's
  stated contract and what the export side already reads
  (`sbeam_bridge._sf`). No shipped number changes (SELECT stamps the 23.303
  default on every condition today), but the first non-1.5 critical case would
  have been silently mis-scaled and mis-labelled in report §5 and in **both**
  GUI views (Results Review headline, Flight Envelope "Critical Loads"), which
  read the same helper — a report figure and its bulk-data card could have
  stated different factors for one case. Each row now scales by its own case's
  factor and its `SF` cell states that factor; the caller-supplied `sf`
  override is **removed**, so the case stays the single owner of its factor and
  there is no path back to a flat one. The test that pinned the hole (every row
  `SF == 1.5`) now asserts the contract, and a new test sets one condition to
  `SF = 1.0` and checks that row is neither re-scaled nor mislabelled while its
  neighbours are untouched.

- **The fuselage deliverables rendered a platform-dependent negative zero, and
  CI failed on a difference that was not a difference.** Found from a CI report
  of `sbeam/body_cards` drift against the Imperial digest baseline while the
  same commit passed locally. The body deck's stated `Applied Fz set sums to …`
  and `Terminal Myy …`, and the span CSV's terminal cumulative `Sz`/`Myy`, are
  the free-free equilibrium — exactly zero in exact arithmetic, ~1e-11 of
  cancellation dust in floating point. The magnitude is far below any printed
  precision, but the **sign** of that dust is not reproducible across platforms
  (x86 and ARM reassociate the upstream arithmetic differently), so the same
  code printed `0.00` on one machine and `-0.00` on another. New
  `sbeam_bridge._closed()` snaps a zero-by-construction quantity to an unsigned
  zero relative to its own column's scale — the rule the `FORCE` cards already
  had (nothing under `_TOL` is emitted) extended to the totals that describe
  them. Guarded by
  `test_the_body_deliverables_never_render_a_negative_zero`, both unit systems
  (SI is the worse case: the same dust is 175× larger in newtons). `body_cards`
  and `body_span` digests regenerated.

  *Not swept in the same change:* structural negative zeros elsewhere (~2,000
  `-0.000000E+00` components in the balanced deck, the tail span CSV's `Fax`
  column) come from `-1 × 0.0`, are bit-identical on every platform, and are
  cosmetic only. Normalising them would move every deck family's digests, so it
  is filed rather than folded in here.

- **The bundle manifest pointed three companion files at the wrong report
  section, and now the numbering has an owner.** 0.5.0 row 1, review finding
  **F-R2**. The manifest's "Summarised in" column sent the case index to §3
  (envelope figures), the load-case CSVs and the text report to §4 (conditions
  analysed) and METHODS.txt to §5 (results) — one short after the §2
  sign-conventions insertion, and two short for methods after the §6 balanced
  section moved it to §7. They now read §4, §5 and §7. The tail rows pointed at
  a "§4 Tails" subsection that does not exist; they name the real
  `Horizontal tail / Vertical tail` headings.
  - **Structural, not a re-typing** (`CLAUDE.md` practice 3): `content.SECTIONS`
    is the single ordered source of the numbering, headings come from
    `section_heading(key)` and every cross-reference — the manifest column and
    the rendered prose in the references table, the gear note and the balanced
    section — from `section_ref(key[, subsection])`. Inserting a section now
    renumbers its references with it; a literal `§N` in rendered text is a
    defect.
  - **Pinned four ways**, since the review's actual finding was "no test pins
    the § values": the owner's numbers must equal the document's own section
    positions; each companion file's target section is pinned by key in
    `SUMMARISED_IN` (exhaustive on the GA fixture, so a new manifest row cannot
    slip in unpinned); every manifest reference must resolve to a real section
    and each suffix to a real subsection; and a document-wide sweep of every
    rendered string rejects a reference past the last section.


- **The chordwise fin deck applies a side load, not a vertical one.** Review
  finding **F-C3**, decision of record **D-R4**. `tail_force_moment_cards` wrote
  every component's strip force through `to_force(0, 0, fz)` — the vertical tail
  included — which is the exact hand-rolled pattern `export/coordinates.py`
  names as the canonical trap: the fin's normal force is a **side** force, so a
  consumer splicing those cards into an airplane-axes model loaded the fin in the
  one direction it is not designed for. The deck now takes its axis from
  `coordinates.tail_force_to_airplane`, the single owner the spanwise tail family
  already used, so the two tail deck families no longer disagree about the fin.
  Byte-changing, and stated in-band rather than only in the code:

  - Each case block carries `$ Load is normal to the surface = Fy|Fz in airplane
    axes` and names that axis in its applied-sum line; the shared `GRID` block
    says the same for both components. The label is read out of the map
    (`_tail_force_axis`) rather than tabled a second time, so a header and its
    cards cannot drift apart.
  - `tail_chordwise.csv`'s `Fz` column becomes `Fn` (the normal force) with an
    `Axis` column beside it — the CSV was mislabelling the fin's rows the same
    way, and the two chordwise deliverables now state one axis between them; the
    report's companion-file manifest states the same convention for both rows.
  - `test_tail_deck_resultants` and the tail round-trip leg are re-pinned to all
    six resultant components, the zeros included: summing `v[2]` for both
    components is what enshrined the defect, and the fin's chordwise first moment
    is `Mz`, not `My`. The Imperial baseline is regenerated — only
    `sbeam/tail_cards` and `sbeam/tail_chordwise` moved.

- **WING-tagged item mass can no longer vanish from the balanced model, and an
  empty panel weight no longer builds a sign-flipped wing.** Review finding
  **F-C5**. The two halves of the same degeneracy:

  - `balance._wing_inertia_scale` returned `0.0` whenever WINGINER integrated no
    panel, zeroing every wing-inertia load — while `assembly_distributes_mass`
    went on excluding those same WING items from `body_inertia`, because the wing
    set is what is supposed to carry them. The whole WING item weight left the
    model and the six-DOF closure absorbed it silently, under a case note that
    blamed the panel. It now **raises**, naming the orphaned item weight and both
    ways out (enter a panel weight, or retag the items onto the fuselage beam);
    only a loading with no WING item mass scales to zero, and its note says that
    instead of misattributing the cause. No shipped fixture reaches it, which is
    why `test_wing_items_with_no_panel_model_raise_rather_than_vanish` builds the
    case explicitly, with the no-WING-items half beside it.
  - Found while gating it: `panel_weight_lb = 0` never produced the zero panel
    the finding assumed. The BASIC density iteration's ±1 % acceptance band is
    empty at a zero target, so it walked the area density down *through* zero and
    returned **negative** strip masses — −0.108 lb integrated on `ga6_normal`,
    which the scale then turned into a ×−3045 sign-flipped inertia set that still
    summed to the right weight and so passed every existing mass gate.
    `wing_inertia._root_density` short-circuits a non-positive target to an empty
    panel (`test_an_empty_panel_weight_gives_an_empty_panel`), which is also what
    lets the partition gate above fire on the input that actually reaches it.

- **A degenerate chordwise profile raises instead of silently emitting an empty
  load set.** Review finding **F-C4**. Both chordwise writers scale their
  trapezoidal tributary set so it sums to the condition's own critical load;
  when the profile integrated to zero the scale fell back to `0.0`, so the tail
  or control-surface deck carried **no load at all** while its case header still
  claimed the non-zero applied sum — a deck contradicting itself, against the
  raise-loudly contract every neighbouring path in `sbeam_bridge` honors. The
  shared owner `_trapezoid_tributary_forces` now raises, naming the component
  or surface, its case, the profile integral and the load it cannot carry. A
  zero case load is not contradictory and keeps its zero set.
  `test_degenerate_chordwise_profile_raises` pins both writers, on the all-zero
  profile and on the antisymmetric one that cancels to the same degeneracy.

- **The `project.envelope` bypass class is closed, and it now has a drift guard.**
  Review finding **F-C6**, the sweep the `tail_span` `n = 1.0` defect (below) was
  the first-found instance of. One fact drives all of them:
  `registry.run_all_modules` — the path the Export page, the CLI and every
  deliverable take — **never assigns `Project.envelope`**, so a module that reads
  it directly does not get "the persisted envelope when there is one"; headless it
  gets `None`, and every one of the four surviving sites then did something wrong
  *quietly*:

  - `wing_inertia._critical_wing_conditions` returned `[]`, so a project that left
    `wing_mass.cases` empty derived **no wing cases at all** and both WINGINER and
    NETLOADS raised "needs at least one load case" — the SELECT-derived case route
    (M4-2 decision 2) was dead headless, exactly like `tail_span`'s V-n read.
  - `wing_inertia.wing_case_ref` read the V-n point the same way, so every wing
    case in the case index shipped with **no CG and no altitude** — the deck named
    a load without the flight condition it was flown at.
  - `net_loads._air_cl_v` raised `MissingInputError` on a derived case it could
    have resolved.
  - `body_loads` did the inverse: `_critical_fuselage` preferred the *persisted*
    conditions while the distribution loop integrated them against a **freshly
    rebuilt** V-n matrix — one case, `nz`/`lt` from a different envelope than the
    one that selected it.
  - `balance` duplicated the owner's rule as `project.envelope or
    build_envelope(project)`, which accepts a persisted envelope carrying an
    **empty `vn`**: every condition then failed its V-n lookup and dropped out
    under a misleading "nothing to balance".

  `select` now owns the whole rule: `default_envelope` (unchanged),
  `default_critical` for the critical set, and `vn_points`/`vn_by_case` as the
  tolerant read for consumers with a documented in-band fallback. `tail_span` and
  `taildist` delegate to them instead of carrying their own copies, and the two
  wing modules share one `wing_case_sources(project)` resolved per build and
  threaded into every helper (the `envelope=` threading convention of M2R-8), so
  `wing_inertia` and `net_loads` cannot resolve different points for the same case
  list and the envelope is not rebuilt once per case.

  The guard is `tests/test_envelope_owner.py`: an **AST scan** of `sloads/` fails
  any new direct `project.envelope` read, with a five-entry allowlist whose
  entries each state why they are not the persisted-else-compute rule (and a second test that
  drops a stale allowlist entry). Six of its gates fail against the pre-fix code,
  including the `tail_span` instance, which had no pin until now.

  **Imperial output moves in one place, by metadata only:** `atr42_100`'s wing
  case index and stick-deck `$ SUBCASE` line now state `CGfwd / 185.9 kt / 0 ft /
  FAR 23.333(b)` where they stated a blank CG, `170 kt`, no altitude and
  `23.301(b)`. That is M4-2 decision 1 (a condition SELECT already named keeps
  SELECT's `CaseRef`) finally applying headless as it always did with a persisted
  envelope. **No load number changes, on any fixture, in any channel** — the
  digests for the other five examples are byte-identical. The fixture enters
  `PHAA` by hand at CL 1.55 / 170 kt while SELECT's `PHAA` point is 1.7283 /
  185.85 kt (`balance.py`'s module docstring records the divergence), so the row
  now states a flight condition the entered numbers were not computed at; filed as
  its own backlog row rather than settled inside this sweep.

- **The SI mass-check deck's gravity was 25.4× low — `GRAV` now carries g in the
  deck's own length unit.** `mass_cards.mass_check_deck` wrote
  `force/(mass × length)`, which is the mass channel's *dimensional identity* and
  therefore 386.0886 in **both** unit systems by construction — g in in/s²,
  always. The SI deck needs 9806.65 mm/s² and instead shipped 386.0886 under a
  header stating "mm/s²": the artifact whose entire purpose is an independent
  check of sloads' inertia "proved" that inertia wrong by a factor of 25.4, in a
  file that parses cleanly (2026-08-10 code review, finding **C1**; Imperial
  masked it completely, `length.factor = 1.0`). The number now has a single
  owner — `units.DeliverableUnits.gravity` (`force.factor / mass.factor`) — with
  a drift guard pinning 386.0886 in/s² and 9806.65 mm/s² against quoted figures,
  because a derived expectation would have agreed with the defect. The card
  magnitude is asserted on the parsed card *and* on the `$` header line in both
  systems; the header now states the product `Nz × g` it actually writes. Only SI
  `--export-conm2` output changes; no Imperial byte, and no calc, moves.

- **The empennage carries its own mass at last — every h-tail deck the suite has
  ever shipped was air-only.** `tail_span` read the surface weight from
  `Project.tail_mass` and nothing else, and **no shipped fixture ever set one**,
  so `_surface_weight` returned 0 on all six airplanes while `weight.items`
  carried the tail mass correctly the whole time (`ga6_normal` 42/23 lb,
  `concept_regional_jet` 520/640). Plan 11 decision **B-2** made `weight.items`
  the mass SSOT and step B1 derived `fuselage_mass.stations` from it;
  `TailMassInput` was never brought along. It is now: the new
  `mass_distribution.tail_surface_weight` derives each surface's weight from its
  `htail`/`vtail`-tagged items, `panel_weight_lb` is demoted to an explicit
  override behind `weight_is_override` (exactly as `stations_are_override` did
  for the fuselage), and `tail_reconciliation` reports the difference either way.
  A surface with no tagged item is **named** as a data gap rather than reported
  as weightless.

  Effect on `ga6_normal`'s h-tail surface total: `BAL UP` −30.9 %, `BAL DN`
  **+26.0 %**, `UNCHECKED MAN DN` +3.0 %. The down-load cases grow, which is
  decision T-9's whole point — those are the conditions that size a GA
  horizontal tail.

- **Every exported tail deck was taking the `n = 1.0` fallback.**
  `tail_span._load_factor` read `project.envelope` directly instead of going
  through `select.default_envelope`, the single owner (M2R-8) — and
  `registry.run_all_modules`, which is the path the Export page and the CLI use,
  never assigns `project.envelope`. So every condition reported "names no V-n
  point" and took `n = 1.0`, understating the h-tail inertia by up to **3.8×** on
  exactly the balancing cases that size the surface. Invisible while the surface
  weight was always zero; a wrong number the moment it was not. Found while
  closing the item above, and swept with it per `CLAUDE.md` practice 4.

- **`balance.fin_sets` would have applied the fin's mass twice.** An assembled
  lateral case accounts for fin mass in its closure field through the
  `VTAIL`-tagged items (decision L-8), so the applied aerodynamic set it reads
  from `tail_span` must be air only — which `WingStationLoad.fz` silently
  stopped being once the fin gained inertia. The strip's inertia is now carried
  separably as `f_inertia` and the applied set takes `fz - f_inertia`. Caught by
  a pinned number; it now has a gate that says what it means.

- **Concentrated wing masses no longer smear to the nearest node in the
  exported bending** ([plan 14](docs/30_future/14_concentrated_wing_mass_nodal_split_plan.md),
  decision **D-1**). WINGINER adds an engine/gear/fuel/store mass to the
  cumulative bending at its *true* spanwise station, but the sbeam export
  recovers nodal loads by differencing the cumulative shear — so the mass was
  picked up whole at the node inboard of it and its lever arm moved inboard by
  up to one strip width. Shear telescoped exactly; **bending did not**. A deck
  for a twin sized wing structure to a root bending moment ~2 % above the
  NETLOADS value printed beside it.

  The lost first moment turns out to be recoverable **from the published table
  alone** — no new input, no schema change. The per-station defect
  `δ[k] = mxx[k] − mxx[k+1] − sz[k+1]·dy` is identically zero wherever the
  lumped-at-nodes recursion built the column (which is how both `airloads` and
  the panel part of `wing_inertia` build it) and equals exactly `w·(y_c − y[j])`
  at the one station bracketing the mass. It is restored as an applied **offset
  couple** on that node's `MOMENT` card: a force at `y_c` is statically
  equivalent to that force at node `j` plus that couple, so nothing moves and the
  exported set now reproduces the cumulative shear **and** bending at *every*
  node, not merely at the root.

  Measured, root bending before → after: `atr42_100` +1.91 % → exact,
  `dhc8_dash8` +1.11 % → exact, `concept_heavy` +0.44 % → exact. The **`Mzz`
  in-plane channel carried the same defect, unfiled and ungated** (+1.14 /
  +0.67 / +0.32 %) and is swept with it. `δ` is machine-zero on every wing
  without concentrated masses, so the BDF decks of `ga6_normal`, `cessna_210`
  and `concept_regional_jet` are **byte-identical** and no Appendix A oracle is
  touched (no calc file changed).


- **The assembled balanced deck was not in the Imperial baseline.** Found while
  changing the closure field: the 6-DOF rewrite moved every closure card in every
  assembled deck and no digest noticed, because `tests/imperial_baseline.py` only
  ever rendered the per-component channels. Plan 11 acceptance #5 — *"if a digest
  moves, something leaked"* — cannot mean anything for a deliverable that has no
  digest, and the assembled deck is the mission's aim-2 deliverable. Now covered
  (`sbeam/balanced_deck`, 297 channels across six fixtures). Every other Imperial
  channel is **byte-unchanged** by B8a-2, verified before regeneration.

- **The vertical tail was modelled on the waterline datum, not on the airplane**
  (mission phase 4 step 8, [plan 13](docs/30_future/13_b8a_lateral_closure_plan.md)
  step **B8a-1**, decision **L-1**). `tail_span` computed the fin's root
  waterline and then discarded it, passing `z_offset = 0` for the v-tail, so
  every fin's `GRID` cards ran from `z = 0` to its span. On `ga6_normal` that put
  the fin's load centroid at `z = 28.5` against a CG at 93 — **64.5 in below its
  own centre of gravity** — and on `concept_regional_jet` within 1 in of it.

  Nothing shipped consumed the fin's roll arm, so no delivered number was wrong;
  but the roll moment a side load makes about the CG is `−Fy·(z − z_cg)`, and
  B8a's lateral balanced cases are built on it. Measured after the fix, both fins
  sit above the CG at the arms plan 13 §5.1 predicted: `ga6_normal` **+14.0 in**,
  `concept_regional_jet` **+86.0 in**.

  - **One owner, because there were already two** — `tail_geometry.fin_root_waterline`
    resolves the fin root (explicit input → the T-tail relation → the fuselage
    top → a zero that says so, loudly), and both the load path **and the
    three-view** read it. `configuration.tail_planform` had its own copy of the
    formula; on `concept_regional_jet` that drew the fin tip 18 in above the
    horizontal tail it is supposed to carry. Registered in `CONVENTIONS.md` §7
    with a drift guard that fails if either grows a private copy again.
  - **The T-tail branch is not a new convention.** It is the inverse of the
    three-view's own default, which places a T-tail's horizontal surface at the
    fin tip; solving that relation for the root is what keeps the two in contact
    when `h_tail_z` is entered rather than defaulted.
  - Every fixture's fin root, and ga6's and the RJ's roll arms, are **pinned per
    fixture** — including a sign assertion, since the sign is what was wrong.


### Changed

- **`app/` joined the lint gate, and the repository root was cleaned for the
  cut** (review **m19–m21**). The merge gate was `ruff check sloads/ cli.py`,
  which left the whole Streamlit layer unlinted — and it had drifted: an unused
  `build_tail_span` import sat in `export_report.py`. The gate is now
  `ruff check sloads/ cli.py app/` in CI and in every document that states it.
  Alongside: `.DS_Store` is gitignored (and untracked at the cut);
  `CODE_REVIEW_2026-07-21.md` and `PROJECT_REVIEW_2026-07-19.md` moved from the
  root to `docs/50_reviews/`, which is their home, and are indexed there;
  `requirements.txt` is **deleted** rather than regenerated — it was a second
  dependency source that had already drifted from `pyproject.toml` (streamlit
  ≥1.30 vs ≥1.36, listing pytest, omitting plotly and openpyxl), and one source
  that is right beats two that disagree. `RELEASE_PROCESS.md` §1 now points at
  `sloads/models/project.py` for `SCHEMA_VERSION` (it named the pre-M3-1
  `sloads/models.py`), and the pyproject classifiers list 3.9 / 3.11 / 3.12 —
  the CI matrix — instead of claiming 3.9 alone.

- **The assembled deck's `SUBCASE` ids are minted from the case, not from its
  position.** 0.5.0 row 1 — decision **D-R7**, review finding **m1**. The
  flagship deliverable was the last deck family still numbering
  `BALANCED_SID_BASE + i`, which is exactly the instability M4-2 decision 8
  removed everywhere else: one condition dropping out of the set (a missing V-n
  point, a payload loading that will not derive) renumbered every case after it,
  so `SUBCASE 5007` meant nothing without the run that produced it. New
  `case_ids.balanced_subcase_id` mints `block + subcase_id`, the block naming
  the hand — symmetric `5000`, starboard `7000`, port `8000`, so `W-05R` is
  `7105` and its port twin `8105` in every run of every project that assembles
  them. `6000` is skipped deliberately: it is this same deck's own GID range.
  Handedness is a block rather than a suffix because a `SUBCASE` id is an
  integer and `7105L` is not one.
  - Minting can collide where positional numbering could not, so
    `balanced_deck.case_sids` **refuses** two cases that share one case id and
    hand rather than letting the solver sum two load sets under one `SUBCASE`.
  - The three blocks are registered bands (`export/bands.py`) pinned against
    `case_ids.BALANCED_HAND_BLOCK` by `tests/test_bands.py`, and the survival
    property is a test in its own right: drop a case from the middle of the set
    and the deck writes every survivor under the number it had.
  - A case carrying no `CaseRef` at all (a bare list built in a test — nothing
    the suite assembles) still falls back to its position, in the separate
    `5001-5100` band so it can never land on a minted id.
  - `sbeam_bridge`'s case-index `SUBCASE` column now maps a handed id through
    the same minting instead of printing an empty cell (no shipped bytes move:
    no handed id reaches the index today).
  - **Byte-changing**: the two balanced-deck digests in
    `tests/fixtures_imperial/digests.json` are regenerated for this and no other
    reason; every other Imperial digest is unchanged.
- **The balanced deck's nodes moved out of the tail-span range: `4001/4201/4401`
  → `6001/6201/6401`** (the F-C1 fix). Node **numbering** only — the
  reconstructed pre-fix deck is byte-identical to the shipped one, and the two
  balanced-deck digests in `tests/fixtures_imperial/digests.json` are regenerated
  for that reason and no other; every other Imperial digest is unchanged.
- **The two chordwise writers share their tributary arithmetic** (review
  **m6**): `_tail_nodal_forces` and `_control_nodal_forces` had the
  trapezoid-width-times-pressure-then-rescale loop written out twice, verbatim.
  One `_trapezoid_tributary_forces` now owns it — which is also the single place
  backlog row 3's degenerate-profile raise will need to land.


- **A balanced case now closes in six degrees of freedom, with one rigid-body
  field** (mission phase 4 step 8, [plan 13](docs/30_future/13_b8a_lateral_closure_plan.md)
  step **B8a-2**, decisions **L-2**/**L-3**). The relief is the d'Alembert field
  `f = −m(a_cg + ω̇ × r)`, written once in the new `sloads/rigid_body.py`. It
  replaces four hand-rolled one-component slices of the same field — each correct
  as far as it went, each missing the companion force component that makes the
  moment it produces equal `−[I]{ω̇}` rather than `−Σw·d²`.

  **The three omissions were worth 0.08 %, 20 % and 55 % of their own degree of
  freedom**, which is the argument for writing the field once rather than adding
  a fifth special case:

  - **pitch** gained `fx = −w·q̈·dz`. The companion is negligible, but the pitch
    inertia stopped being `Σw·dx²`, so **`q̈` fell 18–22 % on `ga6_normal`** and
    3–4 % on `concept_regional_jet`. The deck barely moved (pitch relief is
    0.06–0.56 % of a peak node load); the reported acceleration did, towards the
    truth;
  - **roll** gained `fy = +w·ṗ·dz` — **89.8 lb at a peak node on `ga6_normal`,
    551.9 lb on the RJ**, larger than the roll term already in the deck, because
    `fz = −w·ṗ·dy` reaches only the wing strips (every database item sits at
    `y = 0`) while the companion reaches every mass off the roll axis. A roll
    acceleration throws a mass above the roll axis sideways; the shipped model
    could not say so;
  - **yaw** is new, is coupled to roll through `Ixz`, and gives `ACRL` an induced
    yaw of **+18.93 deg/s²** (ga6) / **−0.993** (RJ). A rolling airplane with
    non-zero `Ixz` yaws.

  The three rotational DOF are now **one 3×3 solve**, not three ratios: `Ixz` is
  8.4 % of the ga6's pitch inertia and larger on the RJ, so treating them as
  independent would be wrong rather than approximate. A singular tensor raises
  rather than pseudo-inverting. All six DOF close to **≤ 2e-16 of `n·W`**.

  - **Item self-inertia now reacts** (decision **L-3**): a mass the assembly
    carries as a *point* applies its own `−[I_self]{ω̇}` as a free moment —
    13.3 % of `ga6_normal`'s `Izz`, and the reason `Izz(closure)` comes out at
    **2933.5 slug-ft²**, matching to 0.0 % the identity `Izz(WTONECG) − wing
    self-Izz + Σw·y²(spread)`. A mass the assembly *spreads* does not, or the
    spread is counted twice; the predicate has one owner
    (`mass_distribution.assembly_distributes_mass`) and a drift guard.
  - **`BalancedCaseResult`** gains `delta_ny` and `closure_inertia`, and
    `delta_pitch`/`delta_roll` become the accelerations they are:
    `p_dot`/`q_dot`/`r_dot`. Result-only fields — nothing on disk has this shape,
    so `SCHEMA_VERSION` stays at **43**.
  - **The B7 roll gate was restated, not weakened.** WINGINER's wing-only model
    reacts 100 % of the aileron moment on the span; the assembled airplane reacts
    about a fifth of it elsewhere, so the old equality could not survive. The
    gate now asserts the *shape* strip-for-strip (unchanged, `rel = 1e-9`) **and**
    pins the magnitude ratio — the wing span's share of the roll moment,
    **0.795230** ga6 / **0.769455** RJ — which the equality could not see at all.


- The balanced-case pitch-residual ceiling is now stated **per family** as well
  as per fixture (`symmetric` / `lateral`) rather than widened. The lateral cases
  sit at V-n points the symmetric families never visit, and their pitch residual
  is larger there (`ga6_normal` `SUDDEN RUDDER` 0.341 %, the RJ's `SIDE GUST`
  1.586 % — the largest instance yet of the already-filed "RJ low-CL cases exceed
  the 1 % pitch gate" item). Keeping the symmetric bounds where they were
  preserves their bite; one widened number would have let a real symmetric
  regression through.
- Imperial baseline digests regenerated for **`csv/balance`**, **`txt/balance`**
  and **`sbeam/balanced_deck`** on `ga6_normal` and `concept_regional_jet` — the
  eight new lateral cases and the lateral columns. No other channel moved on any
  fixture: every per-component deck is byte-identical and every Appendix A oracle
  is unchanged.
- Imperial baseline digests regenerated for **`sbeam/vtail_span_cards`** and
  **`txt/tail_span`** on the five fixtures with a modelled fin — the v-tail deck
  `GRID` waterlines and the in-band notes. No other channel moved: the wing,
  body, h-tail and control decks are byte-identical and every Appendix A oracle
  is unchanged.
- The per-component v-tail deck's "no inertia" note now states the reason of
  record ([plan 13](docs/30_future/13_b8a_lateral_closure_plan.md) decision
  **L-8**): fin inertia belongs to a balanced case, because `n_y` is a property
  of the case and not of a single-condition view — replacing "the suite has no
  lateral load factor", which will stop being true at B8a-3.
- **The backlog is reorganized around a single priority table** (user-agreed
  2026-08-09, [`docs/30_future/00_backlog.md`](docs/30_future/00_backlog.md)):
  every open item, [E] and [V] alike, ranked in one order of work driven by the
  primary deliverable — sbeam (NASTRAN-style) `FORCE`/`MOMENT` cards for the
  wing, body and tail load cases. Agreed ordering rules: wrong cards outrank
  missing cards; landing follows directly after the tail; completed rows are
  **removed** on closure per the lifecycle rule. Historic step numbers are kept
  in item names for plan traceability.

---

## [0.4.0] — 2026-08-08

### Added

- **Distributed empennage loads** — `sloads/modules/tail_span.py`,
  `sloads/tail_geometry.py`, spanwise decks in `sbeam_bridge`, and a **Tail Span
  Loads** page (mission phase 4 step 7; [plan 09](docs/30_future/09_distributed_empennage_loads_plan.md)
  **T1–T5**, phase 1). The tail finally has what the wing has had all along: a
  load at every span station, on a stated load reference axis, that a beam model
  can be sized from. The chordwise TAILDIST profile and every Appendix A figure
  are **unchanged** — this is a pure consumer of SELECT's totals.

  - **Analytic closure gates, because there is no oracle.** Appendix A gives tail
    totals and a chordwise profile and stops. The chord-proportional shape makes
    every target closed-form instead: force to `LT25+LT50` exactly, root bending
    to `L_half·ȳ` with `ȳ` the planform area centroid, torsion to the
    area-weighted chordwise means, inertia to `−n·W`, and the LRA reduction
    identity. All six are checked against a **tapered and swept** planform as
    well, since every shipped fixture takes a derived rectangle.
  - **The horizontal tail is one full-span beam**, tip to tip through the
    centreline, reacted at fuselage attachment stations — not a semispan table
    doubled. That is what lets FAR **23.427(a)**'s unsymmetrical condition live in
    one deck, and it buys a closure a per-side deck cannot state: the net moment
    about the centreline is **identically zero for every symmetric case** and the
    asymmetry moment for 23.427(a).
  - **Tail inertia is d'Alembert — `−n·W`, signed by the load factor alone.** The
    intuitive "inertia opposes the air load" is wrong here and wrong in the
    unconservative direction: the conditions that size a GA horizontal tail are
    *down*-load ones, so an opposing rule would relieve exactly them. A test
    asserts the increase.
  - **The vertical tail is not the horizontal tail rotated.** It spans `z`, its
    air load is a **side force `fy`**, and its torsion is about its own span axis
    — `mzz`, with the sign reversed. One owner in `export/coordinates.py`, because
    the h-tail's convention copy-pasted onto the fin gives a deck that parses,
    solves, and twists the fin the wrong way.
  - **Planform derived where absent, and marked.** No fixture carries tail
    polylines, so a rectangular planform is derived from the authoritative
    area/span and flagged `assumed` everywhere it travels — result, page, CSV,
    deck header — with the cost quantified: a real tapered tail carries its load
    further inboard, so a derived planform is conservative in root bending but its
    station distribution is not the surface's own. Entered polylines win, and are
    validated against the scalars to 1 %.
  - Gated three ways: the closed-form closures, two new rows in the export
    equilibrium sweep (every fixture × both unit systems), and a solver leg in the
    sbeam round-trip harness.
  - `SCHEMA_VERSION` **42** — `Project.tail_mass`, `LoadsResult.htail_span`/
    `.vtail_span`, and `WingStationLoad.myy_free` (the *free* per-strip torsion,
    which the cumulative `myy` is not). All additive; no migration hop.


- **M3-3b / Step G8 — the consolidated summary report renders.** A loads bundle
  now ships its **controlling document**: the airplane and its inputs, the three
  envelope figures with their corner-point tables, the case index and FAR 23
  Subpart C coverage matrix, every governing **ULTIMATE** load with the safety
  factor and station it acts at, the methods & limitations statement, and a
  manifest of the companion files. Four new pure modules — `report/content.py`
  (`Project` → `ReportDocument`), `report/latex.py` (`.tex`), `report/plots_tex.py`
  (V-n, weight/CG and the new speed–altitude figure as pgfplots source) — plus
  `export/pdf.py`, the one impure piece (engine discovery `tectonic` → `latexmk` →
  `pdflatex`, overridable with `SLOADS_TEX_ENGINE`; it returns a log instead of
  raising, because decision G8-1 makes the `.tex` the deliverable and the PDF
  best-effort). Available from the Export page's **Summary report** section and
  headless via `cli.py --report out.tex|out.pdf`. The document honours the
  selected unit system throughout (M4-20), states its basis and units on the title
  page, and is byte-identical between two renders of one project — a caller
  supplies the timestamp, nothing reads the clock.

  The Export page and the report now build their component loads through one
  shared `report.content.component_loads()`, so a bundle's document and its
  CSV/BDF files cannot describe different numbers. Sections whose inputs are
  absent say so with a reason rather than vanishing or rendering an empty table.


- **M4-9 — a standing relabel guard** (`tests/test_report.py`). Three tests
  replace every display label with a meaningless one and require the load-case
  CSV, the schema choice and the four gyro sub-cases to be unaffected — the
  regression the whole item exists to prevent. Each was verified to fail when its
  own code path is reverted to label matching.
- **M4-9 — `sloads/load_keys.py`**, the canonical `LoadValue.key` constants for
  the load-case schema (`loc_x`, `fz_vertical`, `fy_side`, `fx_thrust`,
  `mx_mount_torque`, and the `gyro_case{n}_{myy,mzz}` sub-cases), imported by
  both producer and consumer.
- **M4-9 — schema v37 backfill hop** (`migrations._v36_load_value_keys`). The
  persisted SELECT critical conditions get their keys filled from a frozen
  label→key table; an unrecognised label keeps an empty key rather than an
  invented one. M4-10's fields-hash tripwire fired on the shape change, as built.
- **M4-10 — two schema guards** (`tests/test_schema_guards.py`). A **sentinel
  round-trip** walks every persisted scalar of a real project and asserts none is
  dropped by `io.py`'s hand-written field lists — the failure mode where a new
  field works perfectly in memory and in every calc test, then vanishes on
  save/reload. And a **fields-hash tripwire** over every persisted dataclass's
  field names, so changing a persisted shape without bumping `SCHEMA_VERSION` now
  fails loudly; the discipline was previously unenforced. The tripwire is itself
  tested by injecting a change and asserting it fires.


- **M4-11a — `components.unit_number_input`: the GUI input unit boundary, in one
  place.** Imperial in, Imperial out, so a view cannot convert twice, convert the
  wrong way, or forget to convert on the way home. Three modes, stated by the
  caller and never inferred from a label: `kind=` (converted; unit-suffixed
  label, per-system widget key, bounds converted too), `fixed_unit=KEAS` /
  `ALTITUDE_FT` (decision D-16's aviation carve-out — displayed, never converted,
  key deliberately *not* per-system), or neither (dimensionless). Both together
  raise `ValueError`.
- **M4-11a — `components.page_header(key)` / `page(key)`**: a view's title,
  caption, applicability banner and `PageContext` in one call, with `page()`
  adding a workflow-derived upstream gate as a context manager. The title *and*
  the required slices come from `workflow.py`, and each gate links to the step
  that produces the missing slice, so re-sequencing the workflow re-points every
  gate without touching a view.
- **M4-11a — `components.active_system()`**, the single read of the unit
  selection in the whole app layer (D-16); backlog M4-20 re-points that one
  function at a `Project` field without touching any call site.
- **M4-11a — two new test files, 50 tests.**
  `tests/test_app_components.py` pins the helper in isolation (round-trip per
  unit kind per system, carve-out exactness, bound conversion, key discipline);
  `tests/test_view_unit_roundtrip.py` pins it end-to-end through real views via
  `AppTest`, typing in each system and asserting the same stored Imperial value.
- **`radon`** added to the `dev` extra (decision D-17) for cyclomatic-complexity
  and maintainability-index reporting. **Explicitly not a CI gate** — `ruff` and
  `pytest` remain the merge gate.


- **Step G8 specification & plan (M3-3, the first M4 item) — docs only, no code.**
  The consolidated loads summary report is now specified before it is built:
  `docs/10_standard/SUMMARY_REPORT.md` is the **document standard** (purpose and
  audience, whole-document content rules — ultimate-load marking, case-ID
  traceability, axis/sign/station statements, absence handling, units — the
  required section structure, the **excluded-content** list with the reason for
  each exclusion, and an eleven-point conformance checklist), and
  `docs/30_future/05_step_g8_summary_report_plan.md` is the implementation plan
  (locked decisions G8-1…G8-4: a LaTeX renderer emitting `.tex` always and PDF
  when a TeX engine is present, pgfplots/TikZ figures generated as text, the
  methods/limitations statement stamped into BDF `$` comments + CSV `#` headers +
  `METHODS.txt` + a workbook sheet, and report depth = summary plus every
  governing case pointing at the bundle's CSV/BDF companions; the `sloads/report/`
  package layout; seven ordered sub-steps; risks; the test matrix). The backlog
  entry and `docs/00_INDEX.md` link both. No calc, module or export code changed.
- **`cspell.json` — the domain wordlist referenced by `CLAUDE.md`, `README.md`
  and `PROJECT_GUIDE.md` now actually exists.** 119 verified terms (the 21 `.BAS`
  program names, structural/aero vocabulary, the suite's variable and unit
  abbreviations, tooling names, and the LaTeX toolchain terms Step G8 will need),
  plus `ignorePaths` for the venv, caches, `reference/` PDFs and generated data
  files. Entries were checked against the repo rather than assumed, so no
  misspelling is whitelisted.

- **M4-18 — the loads reference axis (LRA) + two-sided load envelopes**
  (2026-08-03 loads-plots review). Two review findings closed:
  1. **Wing torsion is now stated about a defined loads reference axis.**
     New `SurfaceInput.ref_axis_pct` (schema v34, lenient default 0.25) names
     the chordwise axis of the beam model the delivered loads apply to — the
     elastic axis, typically 40–50 % chord. The calc stays on the original
     25 % chord (oracle-locked); `net_loads.to_loads_ref_axis` transfers the
     cumulative torsion at the render/export boundary
     (`Myy_lra = Myy_25 + Sz·(x_lra − x_25)`; a bitwise no-op at 0.25), and
     `WingLoadResult.torsion_axis` stamps the axis on every result. **Every
     torsion output now names its axis** (mixed axes stay allowed but always
     labelled): the Loads-Plots/Export pages and the sbeam artifacts deliver
     LRA torsion (in-band span-CSV `MyyAxis` column + BDF `$` comments +
     stick-model beam-axis note), the Wing Loads analysis page and
     `wing_load_rows` stay at the labelled 25 % chord for manual cross-checks,
     and `net_loads.run` reports the root torsion at both axes when they
     differ. The LRA is set per surface on the Geometry page (with definition
     help text, seed carry-over) and drawn dash-dot on the three-view planform.
  2. **The Loads-Plots envelope is now two-sided.** The single max-|value|
     trace hid the opposite-sign extreme (which can govern a different part of
     the structure) and could jump where the governing sign flips; the overlay
     now draws pointwise **max and min** envelopes (`report.envelope_extremes`)
     and writes both into the page's CSV download.

- **M4-17e — the full 33-case LANDLOAD matrix in the ULTIMATE deliverable.**
  `landing.run()` now emits **40** `ConditionResult`s (LGFACTOR + 6 family
  summaries + 33 per-case): VMP/DMP/SMP/RMP and VNP/DNP/SNP/RESULT
  (`lbs-ULT`, SF 1.5), the unbalanced pitch/roll/yaw moments (`lb-in-ULT`,
  SF 1.5) and the **dimensionless** ground-line inertia factors NVP/NDP/NS
  (unscaled, no `-ULT` — they are load factors). The moments and factors — a
  third of the original LANDLOAD printout, computed since the port but reaching
  no deliverable and no test — are also shown on the Landing Loads page
  (LIMIT-marked) and are the gear-attachment inputs **M4-6** needs. The CSV grows
  from 7 conditions to ~430 rows, so the deliverable is no longer thinner than
  the LIMIT analysis screen.
- **M4-17d — landing hierarchy & sanity validation** in the pure
  `sloads/validation.py`: `gross_ge_max_landing` (WR = GW/W below 1
  under-predicts the braked-roll, side and supplementary-nose cases),
  `landing_light_le_max`, `landing_cg_ordering`, `landing_cg_below_axle`,
  `landing_cg_names`; plus a post-compute `landing_reaction_warnings`
  (`landing_negative_vertical`, `landing_zero_nose`) kept **outside**
  `consistency_warnings` so no definition page pays for a gear solve. Warn-only,
  and silent on the Appendix-A GA fixture.

### Fixed

- **The round-trip harness's determinate support was implicitly x-axis-only.**
  It constrained rotation about `x`, which restrains a beam running along `x` —
  the fuselage and chordwise-tail decks. The h-tail's spanwise deck is the first
  beam in the suite to run along `y`, and it came back *exactly singular*: the
  model was free to spin about its own axis. The support now picks its
  axial-rotation DOF from the beam's direction. A latent defect in step 2's
  machinery that only a non-`x` beam could find.

- **Antisymmetric (rolling) balanced cases, and the handedness machinery** —
  `modules/balance.py`, the reflection operator in `export/coordinates.py`
  (mission phase 3 step 6; plan 11 **B7**, decisions B-6/B-7). An accelerated-roll
  case now assembles as a full-span airplane, and every asymmetric family from
  here on inherits its left/right twin for free.

  **Only `ACRL` is antisymmetric, which was measured rather than assumed.**
  Handedness lives entirely in `unbal_moment` (FAR 23.349), and every fixture
  enters zero for `TORS` — a *steady* roll has no unbalanced moment, the aileron
  being balanced by roll damping. `TORS` is therefore assembled as the symmetric
  case it is, and a test pins the finding so a fixture that ever enters a rolling
  `TORS` goes red instead of being assembled symmetrically and meaning nothing.

  **The roll residual is not an error, and is not gated like one.** On a rolling
  case `residual_mx` is the *applied* aileron couple — 6.71 % of n·W·b/2 on ga6,
  2.00 % on the RJ — which the airplane is supposed not to balance. It is reacted
  in full by a fourth closure degree of freedom, roll acceleration, distributed
  over every mass; the same standing `nx` already has for drag, because nothing
  else in a free-free model can react either.

  **That relief reproduces WINGINER's own unit-roll distribution, strip for
  strip, ratio 1.000000 on both fixtures** — the wing-item/panel scale cancelling
  identically. Two producers, one answer: oracle-locked FAR 23 code and a residual
  solve that knows nothing about it. That identity is the step's closure gate,
  standing in for the printed oracle concept mode does not have. All six DOF then
  close to machine precision, and both twins solve in the real sbeam with
  reactions ≈ 0.

  **Twins by reflection, not recomputation.** `y → −y`, with a force mirrored as
  a true vector and a moment as an axial one — so roll and yaw reverse and pitch
  does not. One owner in `export/coordinates.py` with an involution drift guard,
  because a sign convention copied to a second call site is what produces a deck
  that parses, solves, and sizes structure to a load the airplane never sees.
  Handedness is a suffix on the existing case id (`W-05L`/`W-05R`), not a new ID
  series; a symmetric case has no hand and gets no twin.

  **Limitation, stated in-band:** the aileron's own spanwise lift increment is not
  distributed — the schema has aileron *areas* and no butt lines — so the couple
  is lumped at the wing aerodynamic centre. This reduces *exactly* to the
  oracle-locked model, which likewise carries only the inertia reaction, but
  `ACRL` wing bending omits the differential lift itself. Filed on the backlog,
  and printed in the deck header, the case notes and the Balanced Cases page.

- **The exported decks are solved in the real sbeam, in CI** —
  `sloads/export/roundtrip.py`, `tests/test_sbeam_roundtrip.py`, the `solver`
  extra and the `sbeam-roundtrip` CI job (mission phase 1 step 2;
  [plan 10](docs/30_future/10_sbeam_roundtrip_ci_harness_plan.md)). The mission's
  claim is that a concept configuration's loads come out as a deck **that
  solves**. That was verified once, by hand, and nothing had re-checked it since.

  It is now a standing gate over `ga6_normal` + `concept_regional_jet` ×
  {Imperial, SI}, and the assertions that matter have two independent producers:
  - the **wing** stick deck's reaction and its element-1 end-B internal loads are
    compared against the NETLOADS quadrature — different code from the cards;
  - the **fuselage** deck's entire Ch 15 cumulative shear and bending table is
    reassembled by sbeam from the `FORCE` cards and `GRID` coordinates alone;
  - the **tail** deck's total and chordwise first moment;
  - the **assembled full-span deck** — the primary deliverable — is solved, and
    all six reaction components at its determinate support come out zero. That
    is the free-free claim proved through a solver's own assembly, on the lever
    arms it derives from the deck rather than the ones sloads used.

  Body and tail are solved through a **test-only** stick wrapper that supplies
  elements from the deck's own `GRID` cards; it is never written by the CLI or
  the GUI, and no exported byte changed in this step. Control-surface decks stay
  permanently out of scope — a chord *fraction* is not geometry.

  **The gate is shown to bite**: three mutation tests assert it fails — a wing
  `FORCE` card scaled by 1.01, two `SUBCASE`s' `LOAD` ids swapped, and one body
  `GRID` displaced by 1 %, which leaves every force sum in the deck closing
  exactly and can only be caught by solving.

  sbeam enters as a **pinned** optional extra (`pip install -e '.[solver]'`), so
  an unrelated sbeam commit can never redden an unrelated sloads PR; a weekly
  non-blocking `sbeam drift` workflow tracks its `main` so drift is visible
  without gating. Without sbeam installed the gate skips; the CI job sets
  `SLOADS_REQUIRE_SBEAM=1` so a broken install fails instead of reporting green.

- **Balanced free-free airplane cases** — `sloads/modules/balance.py`,
  `sloads/export/balanced_deck.py`, and a **Balanced Cases** page (mission phase 3
  step 5; plan 11 **B2–B6**). The mission's aim 2: *a full airplane balanced case,
  wing tip to wing tip, nose to tail, with no need for a constraint, because the
  loads balance.*

  The airplane has always balanced at **trim** (`LZW + LT = Nz·W`, asserted for a
  long time). What never inherited that balance was the **distributed** load set —
  the wing distribution, the tail load, the fuselage inertia and the trim solve
  were four calculations nothing assembled. They are assembled now, and every case
  states what was left over.

  Achieved on the fixtures that can produce one: pre-closure residuals of
  **0.05–0.70 % of n·W** in force and **0.12–1.04 % of n·W·MAC** in pitch, against
  plan 11's 1 % gate — and after closure all three symmetric degrees of freedom
  come to zero at machine precision, verified again by re-deriving the resultant
  from the exported deck's own card text.

- **The assembled full-span deck is now the primary loads deliverable** (decision
  B-5). Both wings on separate GID bands (`4001+` / `4201+` — the first deck in
  the suite carrying more than a half-span), a determinate six-DOF support whose
  recovered reaction *is* the residual, and a `$` header stating the pre-closure
  residual, the relief applied, and that the fuselage `Cm` is lumped. Verified to
  parse with sbeam's own reader.


- **CONM2 / MASSSET mass export** — `sloads/export/mass_cards.py`, the mass
  channel on `DeliverableUnits`, and `cli.py --export-conm2` (mission phase 2
  step 4; plan 12 C1–C5). The `FORCE`/`MOMENT` deck is the *total* applied load
  and stays that way, but its inertia half is computed by the same code that
  writes it, so nothing outside sloads could contradict it. The mass model now
  exports as `CONM2` cards with one `MASSSET` per derivable payload case, so
  sbeam parses the masses independently and can disagree.
  - **Three artifacts**: a pasteable `CONM2`+`MASSSET` fragment; a self-contained
    runnable mass-check deck (`MASSSET` + `GRAV`, a massless placeholder beam,
    and **no load cards at all**); and sloads' own inertia contribution as a
    separate, clearly-marked comparison set.
  - **Not double-counting inertia is structural, not a warning** (C-6): the
    check deck carries no `FORCE`/`MOMENT` cards by construction, which is a
    property a test asserts. Applying the total set *and* accelerating the masses
    reads as a heavier airplane rather than a crash, which is why it is ruled out
    rather than flagged.
  - **`DeliverableUnits` gains `mass` and `mass_inertia`** with their own
    dimensional identity, `force / (mass × length) == g`, exact and *identical*
    in both systems (one standard gravity, expressed per length unit and derived
    from a single constant). `CONM2`'s `M` is mass while the database stores
    weight, so a set written from the human channel is wrong by 386× in a file
    that parses cleanly — the writer refuses it, as the moment channel already
    does.
  - **Verified against sbeam itself** (2026-08-08, by hand — sbeam is not a
    dependency, so CI cannot run it): both decks parse with sbeam's own reader,
    and its grid-point-weight generator reproduces sloads' mass, CG-x and CG-z
    for all four ga6 payload cases exactly.

- **Per-payload-case itemization** — `mass_distribution.derive_case_loadings`.
  Each `flight_loads.cg_cases` entry is resolved to an actual loading (which
  discretionary items are aboard, plus a ballast row solved from the case's
  weight, xcg and zcg), so the mass model can be exported per case rather than
  once. A case is exported only when the required ballast is credible; the rest
  are reported with the number and the reason.


- **The mass single source of truth** — `sloads/mass_distribution.py` (mission
  phase 2 step 3; plan 11 decision **B-2**, step B1). The suite carried **two
  mass models that never reconciled**: the itemized `weight.items` database, and
  a short hand-entered `fuselage_mass.stations` lump table which was the only
  input the Ch 15 fuselage beam ever read. Nothing compared them, and the entered
  table was short on **every** shipped fixture — ga6 492 lb (16 % of the beam),
  cessna_210 430, dhc8_dash8 2,810, atr42_100 7,541 (23 %),
  concept_regional_jet 12,600 (41 %), and concept_heavy had no table at all. Every
  fuselage inertia load, shear, bending moment and exported body card was computed
  from a beam carrying less mass than the airplane weighed.

  The item database is now authoritative and the beam is **derived** from it.
  `MassItem.component` tags which structural component carries each item;
  `mass_distribution` partitions the database, builds the station table, and owns
  the reconciliation checks. The beam carries everything except the wing — the
  empennage included, since it hangs off the aft fuselage — while the wing enters
  as the carry-through *reaction*, never as mass (plan 11 §4's seam rule).

- **`concept_heavy` has fuselage loads for the first time.** It carries no
  `fuselage_mass.stations`, and that was the only reason it had no body deck;
  16,200 lb of airplane had no fuselage distribution. A project no longer needs a
  hand-entered station table to have a fuselage. It is now the sixth of six
  examples reaching the solver channel.


- **Export-boundary equilibrium gate** (`sloads/export/equilibrium.py`, mission
  phase 1 step 1; design note
  `docs/30_future/07_export_equilibrium_invariant_plan.md`). Every exported deck
  states a closure in its `$` header; until now those claims were verified — where
  at all — against *in-memory* objects, by four separately hand-rolled,
  force-only, Imperial-only summations. The new module is the single owner of the
  other half: parse a deck, re-derive Σ`FORCE`/Σ`MOMENT` **from its own card
  text** about a stated reference point, and compare at one tolerance policy
  (`parse_cards`, `card_totals`, `resultant`, `deck_resultants`, `closes`;
  `parse_cards` moved out of `tests/helpers.py`, which re-exports it).
  `tests/test_export_equilibrium.py` sweeps **every shipped example × {Imperial,
  SI} × every deck family** — closing three gaps at once: no moment was ever
  checked from any deck's text (the body deck's "Terminal Myy … (moment
  equilibrium)" header claim had been unverified since C6); `system=` was never
  varied, so a unit set with `moment.factor ≠ force.factor × length.factor` (the
  D-19 failure mode) was invisible to force-only sums; and the ga6 oracle
  fixture's body/tail/control decks had no deck coverage at all. The four
  existing hand-rolled sums in `test_concept_closure.py` / `test_sbeam_bridge.py`
  now go through the same owner.

- **`GRID` cards on the body and tail decks.** Both decks previously named GIDs
  that had no `GRID` card in any file: a consumer could not place the loads
  without a second artifact, and neither deck could be moment-checked from its own
  text. Both now open with a shared station `GRID` block (`y = z = 0` — the
  component's beam line in isolation). Control-surface decks deliberately get
  **none** and say so in-band: `ControlSurfaceStation.x` is a fraction of chord
  and the result carries no chord length, so any coordinate emitted there would be
  silently wrong (revisit if the result ever gains a chord).

- **Design-airspeeds theory document** — new
  `docs/20_theory/design_airspeeds.md`: the STRSPEED/MACHLIM chapter, defining
  the FAR 23.335/23.337 design speeds and load factors (VS/VSF, n, VC, VD, VA,
  VF, MC/MD) with the equations and coefficient schedules as implemented, the two
  25.335(b) dive-speed routes (F25-2) with the margin policy table, the MACHLIM
  Mach lines, and the Subpart-G operating-limitation relationship (the design
  speeds cap the placards; VMO ≤ VC, with equality the usual choice) — plus the
  documented Part 25 gaps (VB/U_ref deferred to F25-1, upset criterion
  backlogged). Appendix A oracle figures tabulated with page citations. Docs
  only; no code change.

- **F25-2 — Part 25 speeds & placards: the 25.335(b) Mach-margin dive-speed route.**
  14 CFR 25.335(b) selects VD by **either** the speed ratio `VC/MC ≤ 0.8·VD/MD`
  (algebraically `VD ≥ 1.25·VC`) **or** a minimum Mach margin between MC and MD;
  23.335(b)(4) has the same "or". The suite only ever implemented the first half.
  `speeds.vd_basis` now picks the route (`speed_ratio` — the default and previous
  behaviour — or `mach_margin`), available in the concept category **"C" only** so
  the Appendix-A-oracle-locked FAR 23 path is provably untouched.
  - **Margin policy has one owner**, `structural_speeds.resolve_mach_margin`:
    default **0.07 M** (the 25.335(b)(2) rule figure since Amdt 25-91, 1997;
    AC 25.335-1A calls it sufficient without further investigation); **0.05–0.07 M
    accepted only with a written rational-analysis basis**
    (`speeds.mach_margin_basis`), flagged in the results, in `validation.py` and
    with a GUI warning that it needs significant justification and represents a
    certification risk; **below 0.05 M refused** (the CFR's absolute floor). The
    floor constrains what may be *declared* — a chosen VD short of the declared
    margin is raised to meet it, like every other design-speed minimum.
  - The M2-10 placard ladder's hardcoded `0.05` is gone: `operational_target_checks`
    now uses the resolved margin, and the placard block reports the implied MC→MD
    margin with a `< 0.07` flag.
  - `speeds.vb_kt` (rough-air speed, 25.335(d)) is accepted and checked for
    25.335(a) ordering against VC. **Input only** — the full `VC ≥ VB + 1.32·U_ref`
    margin needs the 25.341 reference-gust schedule and is deferred to F25-1.
  - Regulation text captured in `reference/14CFR_25_335_design_airspeeds.md`
    (25.335(a)/(b)/(d), verbatim) and `reference/14CFR_MC_MD_speed_margin.md` §5.
  - **Not a sufficiency demonstration, and it says so:** 25.335(b) requires the
    *greater of* the Mach margin and the (b)(1) upset-criterion speed increase;
    only the Mach term is implemented, and every margin-route output states that.

- **M4-5 — aero-coefficient curves + closure on Aerodynamic Data (decision D-10).**
  The page now plots CL–α, the drag polar (CL vs CD) and CM–α for each
  configuration, with the balanced V-n points overlaid and the stall clamps drawn,
  so a coefficient-entry error shows as a shape instead of hiding in a table — the
  concept-aircraft case, where the polynomials are hand-built.
  - New pure module `sloads/aero_curves.py` is the **single authority for
    evaluating** the airplane-less-tail polynomials: `modules/flight_envelope`
    imports `lift_cl`/`drag_cd`/`moment_cm`/`clmax_curve` instead of inlining
    them. The FLTLOADS arithmetic is unchanged bit-for-bit (Glauert passed as
    `(g, gmn)`, not a pre-divided ratio); all Appendix A oracles unmoved.
  - Two closure metrics, gated in CI on the GA oracle and both concept fixtures:
    **recovered CL** (each point's CL re-derived from its own `LZW`/`DX`/α/V by
    inverting the balance rotation, vs the polynomial — a drift guard at 1e-9,
    since the two are algebraically the same number) and the **stall-clamp
    margin** (no balanced point above its Mach-adjusted stall CL by more than the
    balance's 0.005 band).
  - New `sloads.validation` coefficient-entry checks tagged for the page:
    `aero_clmax_unreachable`, `aero_lift_slope_sign`, `aero_drag_negative`,
    `aero_drag_polar_shape`, `aero_clmax_neg_sign`. Advisory only; silent on every
    shipped fixture.
  - `flight_envelope.balance_configs` is now public (the page needs the same
    fuselage-moment-augmented configs the balance flies).


- **Overlay `CONM2` cards no `MASSSET` named were silently counted in every
  payload case.** sbeam decides overlay-only status by *reference* — a card no
  `ADD`/`REPLACE` row names belongs to the baseline mass. The first cut exported
  every discretionary item, including ga6's own `Ballast` row (superseded by the
  per-case ballast this step derives), so sbeam's grid-point-weight generator
  recovered 9.0083 slinch against sloads' 8.8063 for CG1: **78 lb too much, in
  every case, from a deck that parsed without complaint.** Found by running
  sbeam's GPWG over the exported deck rather than by inspection. The overlay list
  is now built from what the loadings actually carry, which makes an unreferenced
  overlay card impossible to write, and `unreferenced_overlay_eids` guards it.


- **Deck `$` comments overran the 72-column free-field card width.** The body deck
  had a one-off assertion of this; the tail deck's "Applied Fz set sums to … =
  SF × (LT25 + LT50) = …" line overran on any five-figure load (73 columns on
  `ga6_normal`) because nothing swept the other families. Fixed for the body,
  tail and control decks and replaced with a swept guard over every example in
  both unit systems. The wing decks overrun too; that fix changes wing Imperial
  bytes and is filed on the backlog rather than folded in here.

- **Concept dive speeds were silently overridden (Major, F25-2).** In concept mode
  the `1.25·VC` floor was applied unconditionally, so a concept user could not
  enter a margin-route VD at all. On `examples/concept_regional_jet.project.json`
  its own `chosen_vd = 350` kt (MD 0.8511, margin +0.097) was overridden to
  387.5 kt → **MD 0.9423, margin +0.189**, inflating every dive-speed case
  (`MAN ±D`, `GUST ±D`, `BAL D`, `ST ROL D`) and cascading into MACHLIM
  (MNE 0.848, **MFC 1.13** — supersonic flutter clearance for a subsonic
  transport). The RJ fixture now ships on the Mach-margin route and its dive-line
  loads **decrease**; MNE 0.766, MFC 1.021. Non-dive cases are numerically
  unchanged, pinned by a new mechanism test. No FAR 23 category is affected.
- **MC/MD had two homes and the front-ends disagreed (F25-2).** `mach_limit.mc`/
  `.md` were persisted in the project file *and* recomputed from the design speeds
  by the Streamlit page, which ignored the stored pair. The registry/CLI path
  honoured it, so the same RJ project reported **MNE 0.738 from the CLI and 0.848
  from the GUI** — breaking the "GUI, CLI and tests are interchangeable
  front-ends" contract. `MachLimitInput.mc/md` are removed; `mach_limit_lines`
  takes MC/MD as arguments and `structural_speeds.design_speed_values` is the sole
  producer, guarded by a new test over every shipped example. MACHLIM output moves
  slightly for the GA fixtures too — their stored MC/MD were the manual's *rounded*
  printed figures (0.323/0.403 vs the derived 0.32264/0.40330); the Appendix A
  oracles still pass at ±0.1 % and no load channel moved.

- **Aerodynamic Data: the fuselage-moment Apply no longer rewrites the CLmax
  scalars** (found while implementing M4-5; same defect class as M4-22). That
  form rebuilt the whole `aero_coeffs` slice without `clmax_clean` /
  `clmax_clean_neg` / `clmax_flap`, so `__post_init__` re-derived them from the
  per-config `stall_cl` — silently moving VS/VSF and hence VA/VF wherever the two
  legitimately differ, and **zeroing `clmax_flap`** on a project with no
  flaps-down coefficient set (the regional-jet concept: VF then failed to
  compute). Pinned by two `AppTest` guards.


- **Twelve views read `st.session_state["unit_system"]` directly**, a second
  authority for the unit selection that decision D-16 says must not exist (found
  implementing M4-20 step 6). It was latent rather than live — `Home.py` rewrites
  the session key from `Project.unit_system` on every render, so the two agree in
  practice — but it meant step 2's re-point of `active_system()` at the project
  field reached only the views that go through `unit_number_input`/`page`. All
  twelve now call `active_system()`, whose own fallback is that same session key.
- **`weight_mass.py` handed `load_cases_csv` its display-converted results.**
  Since M4-20 step 3 the writer converts internally, so that page's CSV came out
  SI while every other page's came out Imperial — an inconsistency no error
  reported. It now passes the raw results plus `system=`; only the unit-agnostic
  `module_text_report` gets the converted copy.
- **The four sbeam `.bdf` decks shipped with no methods or units statement at
  all** (found implementing M4-20 step 5). The Export page built a
  `bdf_comment_block` and then never applied it — the decks were the one channel
  in a bundle carrying neither their ULTIMATE basis nor their unit set. `ruff`
  could not catch it: the unused name is module-level, and its unused-variable
  rule is a *local* check. Every BDF writer now takes `header_comment=` (matching
  the CSV writers), the page passes the stamp it builds, and a source-level test
  asserts all five deck artifacts do. `$` is inert to any bulk-data parser and an
  unstamped call is byte-identical, so no existing caller changes.

- **`lb-in` and `lb/in^2` had no SI conversion.** `units.convert_results` left
  them Imperial while converting everything around them, so an SI results table
  mixed `N` and `lb-in` in adjacent rows with no error anywhere — **1580 values
  across the six examples**, covering root bending/torsion, pitching moments and
  every control-surface design pressure. Both now convert (`N·m`, `kPa`) and both
  are recognised by the ultimate boundary, so they keep their `-ULT` marker. A
  standing guard asserts every unit in `render._LOAD_UNITS` has an SI mapping and
  an `-ULT` marker, so the next one added without them fails loudly; it was
  verified to fail when the `lb-in` row is removed again.
- **Dead `"knot" → m/s` row removed from the SI table.** The calc emits
  `kt(EAS)`, never `"knot"`, so the row never matched a value — the KEAS
  carve-out held by accident. Removing it means the first producer to emit
  `"knot"` cannot silently convert an airspeed the standard says is never
  converted. Pinned by test for both `kt(EAS)` and `ft`.
- **The `lb-in → N·m` factor was quoted twice as a rounded `0.1129848333`** against
  an exact product of `0.11298482902761668`. Both sites now derive it. SI-only,
  3.8e-8, below display precision.


- **M4-10 — a pre-Phase-G0 file lost its horizontal-tail length.** The v24
  unit-rename hop covered `vtail_loads` but not `tail_loads`, so
  `airplane_length_ft` was dropped rather than rescaled to inches. Caught by the
  existing `test_legacy_ft_sqin_keys_migrate_to_canonical`.

- **G8.3 — every export channel now carries its own methods & limitations
  statement.** A loads CSV forwarded on its own, or a BDF handed to sbeam, now
  states in band that its numbers are ULTIMATE, under what category, how the tool
  is verified (including that twin-turboprop cases are **closure-locked, not
  oracle-locked**, because Appendix B is not bundled), the three approved
  deviations from the source manual, and what the tool does not do. Built once in
  `sloads/report/methods.py` and wired into `io.load_cases_csv`, all five sbeam
  CSV writers, the case index, `METHODS.txt` in the zip bundle, and a new
  *Methods* sheet in the workbook. The statement adapts per project: the concept
  caveat lists the actual applicability exceedances, and the fuselage
  closure-artifact caveat appears verbatim only when a case took the fallback
  path. Deterministic — nothing reads the clock, so two exports of one project
  are byte-identical. CSV consumers need `comment="#"`; every in-repo reader was
  audited in the same change.
- **G8.4 — FAR 23 Subpart C coverage matrix** (`sloads/report/coverage.py`): 52
  regulations classified against what a run actually produced — *covered* (with a
  case count), *not applicable* (with the engineering reason), *not analysed*
  (the gap list), or *out of scope* (the tool does not implement it). The
  fourth status is a deliberate departure from the plan's three: without it, the
  16 regulations the suite never implements read as gaps and bury the 9 real ones.
- **G8.2 — document-control fields** `Project.revision` / `.checked_by` /
  `.approved_by` / `.description` (**schema v36**), editable on the Dashboard.
  All free text defaulting to `""`, so older files load unchanged and a project
  that never sets them serialises exactly as before. `revision` is deliberately
  free text, not a tool-managed counter (decision G8-5).


- **`report.strip_comment_lines` corrupted CRLF line endings.** The reader-side
  helper split on `\n` and rejoined, silently rewriting the line endings
  `csv.DictWriter` emits — in the payload it exists to leave untouched.

- **M4-11a — the Geometry page ignored the SI unit toggle on ~40 fields.** The
  empennage (33 fields), landing-gear (7) and engine-CG (3) forms hard-coded
  Imperial unit strings into their labels (`"H-tail area ST (ft²)"`, `"Tread
  between mains (in)"`) and performed no conversion, so with the sidebar set to
  SI a user saw `(in)`/`(ft²)` and their entry was stored as inches. The gear
  caption had documented the behaviour rather than fixed it. All now render in
  the active system and store canonical Imperial. Two `"CG station … (in)"`
  fields on the Flight Envelope trim tab had the same defect.
- **M4-11a — a 184 ft² wing was stored as 1982 ft² in SI.** With the widgets
  returning canonical Imperial, the Geometry page's Apply handler converted a
  second time. Found by the new through-the-view test, not by review.
- **M4-11a — an untouched field drifted the project on every Apply in SI.** The
  display seed is rounded to 4 decimals for legibility; converting *that* back
  returned a value a hair off the original. `unit_number_input` now returns the
  caller's own Imperial value when the field was not edited.
- **M4-11a — `min_value`/`max_value` were not converted with the value**, so a
  non-zero Imperial bound would have become an SI-magnitude bound and silently
  stopped constraining.


- **M4-12a — AppTest Apply buttons are selected by form key, not list
  position.** `at.button` flattens every form's submit button into one list, so
  `test_dirty_flag`'s `_apply_buttons(at)[0]`/`[1]` silently rebound whenever a
  view gained, lost or reordered a form — the test kept passing while asserting
  something else, and M4-11 is about to rewrite 22 apply handlers. All eight
  positional/label lookups (`test_dirty_flag`, `test_configuration_layout_view`,
  `test_landing`) now go through `helpers.apply_button(at, form_key)`, which
  asserts it matched exactly one button. Two `__main__` self-runners that drove
  views through `AppTest` without putting `app/` on `sys.path` are repaired.
  The bad selection had been masking a real app defect, now logged as **M4-22**
  (the Flight Envelope SELECT Apply also persists un-applied geometry edits).

- **M4-1 — fuselage body loads now close the moment, not just the force**
  (Ref 1 Ch 15 p103). `body_loads` applied a single vertical wing reaction and
  closed ΣFz only, so the delivered body beam carried a net pitching couple
  (terminal `Myy` 7.3e4 – 5.5e5 lb-in on the GA6 conditions). It now follows the
  manual's two passes: the terminal moment of the inertia + tail-load set **is**
  the unbalanced moment `M_ub`, which is reacted with the vertical residual at
  the wing **front and rear spar attachments**
  (`R_r = (M_ub + R_total·(x_ref − x_f))/(x_r − x_f)`, `R_f = R_total − R_r`).
  Both residuals now close to ~1e-15 of the loads that produce them. New
  `SurfaceInput.front_spar_pct`/`.rear_spar_pct` (**schema v35**; `None` = not
  entered → module defaults 0.15/0.65, flagged `assumed` on every deliverable)
  and `derived_geometry.carry_through`. The two reactions are applied as the
  statically equivalent **linear line load** over the carry-through rather than
  as two point loads — same resultant and first moment, no `±M_ub/d` shear
  spike, and it collapses onto the manual's literal two-point solve as `d → 0`;
  closure is independent of the node count. Where the spar stations can't be
  derived, a flagged whole-body fallback closes the beam and is labelled a
  **closure artifact** (it has no physical source). Wing-attach fitting loads
  are reported — `body_loads.fitting_load_rows` (LIMIT) and the new
  `sbeam_bridge.body_fitting_load_csv` (ULTIMATE, also in the `.zip` bundle and
  as a workbook sheet) — deliberately *outside* the `FORCE` set, which already
  carries them. The 2026-07-23 caveat comes off its three stamp sites: BDF
  blocks now state both residuals and the spar provenance (`$ CAVEAT:` only on
  the artifact path), the **Net Fuselage Loads** page trades its warning for a
  terminal-`Myy` metric and a *Wing-attach reactions (LIMIT)* panel, and the
  **Export** page's Fuselage caption branches artifact/closed. The FAR 23 flight
  oracles are unaffected (no flight-loads or envelope calc changed).
  Full record: `docs/40_history/00_completed_development.md` and the design note
  `docs/40_history/04_m4-1_body_moment_closure.md`.


- **M4-17a — the landing-loads ↔ mass-model disconnection.**
  `weight_onecg.build_mass` had **zero production callers**: no page, no CLI path
  and no example ever produced `Project.mass`. The dashboard therefore showed
  Landing Loads "⛔ blocked — Needs: mass" on every shipped example while the
  landing results computed fine, and the One Engine Out gate was **unsatisfiable
  through the GUI**. The Weight & Mass Properties **Apply weight items** handler
  now persists `project.mass = build_mass(project)`, and the landing workflow
  step's `requires` drops `"mass"` — the LANDLOAD calc has read no mass slice
  since M2-8. `one_engine_out` still requires it (IZZ).
- **M4-17c — the landing CG seed could emit a zero waterline.** The seed read
  `project.mass.cases[0].cg_z`, always absent, and fell back to `0.0` against a
  ~60 in axle waterline — computing silently with nose-gear reactions of
  −233…−2887 lb (nonphysical) and braked-roll main loads 2.6× the p230 oracle.
  Missing-source cells are now **blank, never zero**; the page names the missing
  source and **blocks the reaction compute** until a real waterline is entered.
  Legacy project files carrying `zcg: 0` are blocked with an explanation rather
  than computed — an intentional, load-bearing behaviour change.
- **M4-17c — the forward CG limit is interpolated at the landing weight.** The
  seed paired the weight-agnostic outer-hull forward station (72.64 in) with the
  max-landing weight, where the manual reads the forward limit *at* that weight
  (76.12 in, Appendix A p230). New public
  `validation.wtenv_fwd_cg_limit_at_weight(project, weight_lb)` lerps the WTENV
  forward limit between the forward-regardless and forward-gross anchors,
  **clamped, never extrapolated**. Max-landing rows are also no longer seeded at
  full MTOW when the max landing weight is unset.
- **M4-17e — `_critical` excluded the side load.** The 23.485 family pick was a
  tie-break accident (cases 19–22 share an identical VMP); the ranking now uses
  the full √(V²+D²+S²) magnitude. Ranking only — no stored value changes, and the
  picks are unchanged on every bundled example.
- **M4-17b — seven stale `Project.mass` doc/help references** in
  `modules/landing.py`, `models/inputs.py` (four) and `app/views/landing_loads.py`
  (docstring + the gross-weight-override help), all of which contradicted the
  M2-8 removal note in the same files.

### Changed

- **The residual closure is three degrees of freedom, not two.** Plan 11 B-3
  specified `Δn` plus a pitch term. Nothing in an assembled model reacts **drag** —
  the suite has no distributed thrust — so leaving x open put 17–26 % of n·W into
  the support reaction and made "reactions ≈ 0" untrue in a deck that still
  solved. FAR 23's longitudinal load factor `nx` is exactly this quantity; on ga6
  PHAA the closure gives 0.661 g against the fixture's entered 0.6065. All three
  DOF are mutually decoupled, because the loading's centroid *is* the CG.

- **Imperial output gains two channels** (`csv/balance`, `txt/balance`) and
  `tests/fixtures_imperial/digests.json` was regenerated for exactly those. No
  existing channel moved — this step is additive, and the Appendix A oracles and
  every per-component deck are unchanged.


- **Schema v41.** `MassItem` gains `component`; `FuselageMassInput` gains
  `stations_are_override`. Both are optional and additive, but the *meaning* of
  `fuselage_mass.stations` changed — it is now an explicit override of the derived
  distribution rather than the sole input. Migration hop
  `_v40_fuselage_stations_override` therefore marks any pre-B1 file that already
  carries a station table as an override, so migrating a project **cannot silently
  move its fuselage loads**; the gap against the SSOT is reported instead
  (Fuselage Loads page), and adopting it stays the user's decision. Untagged mass
  items are deliberately *not* migrated to a guessed `component`.

- **Imperial output changed for the body channels** — `sbeam/body_cards`,
  `sbeam/body_span`, `sbeam/body_fitting` on all six examples, plus
  `csv/body_loads` and `txt/body_loads` newly present on `concept_heavy` — and
  `tests/fixtures_imperial/digests.json` was regenerated deliberately for exactly
  those. **This is an intended change**: the fuselage beam now carries the mass it
  should. Wing, tail and control decks, every other report/CSV channel and the
  case index are byte-identical, and the Appendix A oracle suites are unchanged
  (verified explicitly, plan 11 risk R2 — no oracle module reads `fuselage_mass`).


- **Imperial output changed for three deck channels** — `sbeam/body_cards`,
  `sbeam/tail_cards`, `sbeam/control_cards`, plus the `sbeam/tail_chordwise` CSV's
  `GID` column — and `tests/fixtures_imperial/digests.json` was regenerated
  deliberately for exactly those. **This is an intended change.** Wing decks,
  every report/CSV channel and the case index are byte-identical. The content
  changes are: the new `GRID` blocks; the h-tail/v-tail GID split below; the
  control deck's chord-fraction note; and two header lines re-wrapped to the
  72-column free-field width.

- **The h-tail and v-tail now take separate GID blocks** (`2001–2100` /
  `2101–2200`, via the new `sbeam_bridge.tail_station_gid`). They shared one
  `2001+` run, which was harmless only while the GIDs were bare references — the
  two components have different average chords, so their chord stations are
  *different points*, and one shared `GRID` block would have defined one node at
  two locations. **v-tail GIDs therefore shift** in both the tail deck and the
  tail chordwise CSV.

- **Schema v40 (F25-2).** `speeds` gains `vd_basis`, `mach_margin_min`,
  `mach_margin_basis` and `vb_kt`; `speeds.mach_limit.mc`/`.md` are **removed**.
  Migration hop `_v39_mach_limit_mc_md` drops the dead keys and `vd_basis`
  defaults to `speed_ratio`, so every pre-v40 project loads with exactly the
  numbers it had — pinned by a reduction-invariant test that compares VD/VC/VA/VF
  for all six shipped examples against values read off the pre-change build. An
  unrecognised `vd_basis` is refused at read rather than silently defaulted.

- **M4-2 — unified load-case identity + deck SUBCASE map (schema v39).** One
  case ID per physical condition, from the SELECT pick to the exported deck.
  - **Wing.** `select_wing`'s separate `W-40..49` band is retired: a wing
    condition's sequence now comes from its **name** (`case_ids.WING_SLOTS` —
    PHAA 1 … TORS 6), and `wing_inertia.wing_case_ref` returns SELECT's own
    `CaseRef` for the matching condition, so the WINGINER/NETLOADS distribution
    and the SELECT condition are one case with one id (they were two, with two
    independently-typed sets of Nz/Nx). **Wing case ids change** where a case's
    list position differed from its slot (ga6: TORS `W-02` → `W-06`, ACRL
    `W-03` → `W-05`).
  - **Vertical tail.** `one_engine_out` moves to its own `VT-30..` band. It
    previously minted `VT-01..` from a fresh allocator — the same ids
    `select_vtail` mints, for different physical cases.
  - **Wing cases derive from SELECT when none are entered**
    (`wing_inertia.resolve_wing_cases`), with a **Pull cases from SELECT** button
    on the Wing Loads page. An explicit list always wins, so no shipped example
    or oracle changes path.
  - **Decks.** `SUBCASE` and load-set `SID` are one integer derived from the case
    id (`case_ids.subcase_id`: `W-03` → 103), not the case's position — a
    filtered export can no longer renumber the subcases that survive. Every deck
    opens with a `$` subcase-map block naming the condition behind each number,
    the stick deck carries `LABEL = <case id>`, and the case-index CSV gained a
    `SUBCASE` column.
  - **Loading a project** now drops a `selected_case_ids` entry that matches no
    condition **with a warning** (it silently widened the governing-set export
    before). Re-pick the governing set on the Critical Loads page if warned.
  - The frozen Imperial baseline (`tests/fixtures_imperial/digests.json`) was
    **regenerated deliberately**: case ids, deck SIDs and the new index column
    move Imperial bytes. No load *value* changes.

- **Development-process overhaul (2026-08-05).** Documentation-only change set
  implementing the 2026-08-05 process review
  (`docs/50_reviews/2026-08-05_development_process_review.md`; findings F1–F7,
  recommendations R1–R11), which also assessed sloads against the sbeam 2026-08-04
  process changes. No code touched.
  - **Mission re-stated** in `CLAUDE.md` and the backlog: a *demonstrated* concept-loads
    → sbeam sizing loop, continuously verified in CI. **Backlog re-pointed**
    (`docs/30_future/00_backlog.md`): every item mission-tagged [E]/[V]; new
    mission-path items filed — the **sbeam round-trip CI harness**, the **global
    equilibrium invariant on exported decks**, the deck SUBCASE mapping (into M4-2),
    the load-axis/elastic-axis convention note, and the gust spanwise-distribution
    decision; ~20 off-mission items (M4-10b/11b, F25-3/5, the L long tail, the
    future-direction placeholders) moved with full write-ups to the new
    `docs/30_future/02_parked.md`; no new parallel ID series going forward. Stale
    D-refs and the `models.py` citation fixed in `01_concept_loads_plan.md`.
  - **Tiered S/M/L closure** replaces the uniform full-step-format rule in `CLAUDE.md`
    (small fixes: changelog + backlog + one-line history entry), plus five working
    rules: design-note-before-code, benchmark-first DoD (closure/invariant gates for
    concept mode with the same force as the oracle rule), **make-it-structural**
    (SSOT owner + drift-guard test on first need — the units/SI three-rebuild lesson),
    generalize-on-first-find, findings-filed-with-bodies. `CLAUDE.md` rewritten as
    rules + pointers (278 → ~160 lines) with named authoritative single sources.
  - **Review process tiered** (`CODE_REVIEW_PROCESS.md` §0): light checklist for S,
    touched-area scoping for M, full process + design-note check for L; ~2-week/5-step
    review cadence; doc drift reclassified `[CRITICAL]` → `[MAJOR]`.
  - **Release cadence rule** (`RELEASE_PROCESS.md`): release every ~2–3 weeks or ~5
    steps behind a bounded gate; the unbounded docs-consistency audit dropped
    (enforced per-change instead). `[Unreleased]` is release-ripe — 0.4.0 due.
  - **Conventions charter added** (`docs/10_standard/CONVENTIONS.md`): axes/frames
    (+aft/+right/+up inches, identity map to sbeam CID 0), the two-channel unit sets,
    the LIMIT→ULTIMATE contract, case identity, preserved ENGLOADS signs — all
    code-verified with citations — plus the SSOT-owner/drift-guard table. Its
    extraction flagged four inconsistencies (chief: `load_keys.py` cites a
    **nonexistent** `tests/test_load_keys.py` as its uniqueness guard), filed on the
    backlog as an S-tier batch.
  - **Docs index** gains the `50_reviews/` section, the parked file and the charter;
    the resolved-decision count corrected (D-1…D-18). The history-file split (R11) is
    deferred to its own session (the file carries in-flight changes) and filed on the
    backlog.


- **The methods & limitations statement no longer cites backlog IDs.** It is now
  a report section as well as a CSV/BDF stamp, and `SUMMARY_REPORT.md` §5 excludes
  internal development artifacts from a deliverable: the two affected limitations
  are stated in engineering terms and the tracking IDs stay in the repository.
  Wording only — no channel gains or loses a limitation, and the frozen Imperial
  baseline (which renders unstamped) is unchanged.

- **M4-20 step 7 — the Imperial baseline is frozen, and M4-20 is closed.**
  `tests/imperial_baseline.py` renders every deliverable channel of all six
  examples and freezes a SHA-256 each in `tests/fixtures_imperial/digests.json`
  (**256 channels**); the guard is decision D-21's guarantee that adding SI cost
  the Imperial user nothing, and its failure message names the drifted channel.
  Regenerate deliberately with `.venv/bin/python tests/imperial_baseline.py`.
  Joined by the bundle-single-system, per-dimension round-trip and end-to-end CLI
  tests, and by a source guard that no `sloads/modules/*.py` calls a conversion
  function — the calc is structurally outside this path, which is what leaves the
  Appendix A oracles untouched. M4-20 moved to
  `docs/40_history/00_completed_development.md`, D-19…D-22 to
  `03_resolved_decisions.md`, and **M3-3b G8.5 is unblocked**.

- **M4-20 step 6 — the GUI writes its downloads in the selected system.** The
  Export page resolves `components.active_system()` **once** into `_system` and
  passes it to all eleven artifact calls (five decks, five sbeam CSVs, the
  per-module load-case CSVs) plus the text report and workbook, and states the
  bundle's system in a caption built from `deliverable_units` itself — so the
  caption and the files cannot drift. The ten other views with download buttons
  (wing / fuselage / tail / control-surface / landing / weight / speeds /
  configuration) take their page's system too. `case_index_csv` deliberately takes
  none: its only dimensional columns are `Speed (kt)` and `Altitude (ft)`, the two
  aviation carve-outs.

- **M4-20 step 5 — every deliverable states its unit system in band.** The
  methods & limitations block (`report/methods.py`) takes `system=` and gains a
  `UNITS:` paragraph, so the one statement wrapped for every channel (G8-3) puts
  the unit set into every file: `# UNITS: …` in each CSV, `$ UNITS: …` in each
  BDF, the paragraph in `METHODS.txt` and the report. It is *bundle*-wide, not
  per-channel — the same block lands on both the human CSVs and the sbeam decks,
  so in SI it names both sets and attributes each (`N·m, kPa` for the readable
  files, `N·mm, MPa` for the decks); in Imperial one set does both jobs and the
  statement says so without inventing a split.
- **M4-20 step 5 — the BASIS `-ULT` marker list is derived, not hard-coded.** It
  listed `lbs-ULT, ft-lb-ULT, N-ULT, Nm-ULT` regardless of system: markers no
  Imperial file carries, and missing every marker step 4 added. It is now
  generated from both channels' unit sets, so it cannot fall out of step with what
  the writers emit.
- **M4-20 step 5 — `units_statement` names all four dimensions.** `Imperial (lb,
  in, lb-in, lb/in^2)` / `SI (N, mm, N·mm, MPa)`; pressure joined it because step
  4 found that dimension silently wrong, and kPa-vs-MPa is exactly what a reader
  cannot infer from the numbers.

- **M4-20 step 4 — the sbeam solver channel writes the consistent N/mm/N·mm set.**
  Every public `export/sbeam_bridge` writer (all 17: wing / body / tail /
  control-surface CSVs, the four `FORCE`/`MOMENT` card sets and the CBAR stick
  model, plus the `write_*` wrappers) takes `*, system=UnitSystem.IMPERIAL` and
  resolves it to `deliverable_units(system, Channel.SOLVER)`. In SI that is
  **N / mm / N·mm / MPa** — deliberately *not* the `N·m`/`kPa` a report uses,
  because a deck whose GRIDs are millimetres and whose forces are newtons is only
  correct when every derived unit is its base units combined (decision D-19).
  `cli.py --units si --export-sbeam` now works; the temporary refusal added in
  step 2 is gone.
- **M4-20 step 4 — `export/coordinates.py` is the enforced single scale point.**
  `to_grid` / `to_force` / `to_moment` and the new `to_pressure` take the unit set
  and apply its factor; **no arithmetic in `sbeam_bridge` scales anything.** CSV
  cell values go through the same three functions the cards do, so a span CSV and
  the deck it accompanies are the same numbers in the same units by construction.
  All four **raise** on a unit set that fails `is_consistent`: `deliverable_units(SI)`
  defaults to the *human* channel, so handing it to a deck writer is a plausible
  slip, and it now fails loudly instead of writing a 1000×-wrong torsion into a
  file that parses cleanly.
- **M4-20 step 4 — the solver unit set gained its own pressure (`MPa`), fixing a
  step-1 defect.** Step 1 gave the solver channel a consistent *moment* but left
  *pressure* at the human channel's `kPa` — the identical D-19 error one dimension
  over, since pressure is force / length². The solver set now carries `MPa`
  (N/mm²) from the **derived** `units.PSI_TO_MPA = LBF_TO_N / IN_TO_MM²`, and
  `DeliverableUnits.is_consistent` checks **both** derived dimensions
  (`moment == force × length` *and* `pressure == force / length²`), so the next one
  cannot be missed the same way.
- **M4-20 step 4 — every sbeam CSV header states its units.** The span-load,
  body, tail and control-surface CSV headers carry the unit and the `-ULT` marker
  on every dimensional column (`X (in)` → `X (mm)`, `Fz (lbs-ULT)` → `Fz (N-ULT)`,
  `My (lb-in-ULT)` → `My (Nmm-ULT)`), where they were previously bare (`X`, `Fz`,
  `My`) and a reader had to know from elsewhere that the file was Imperial. The
  BDF's axes and equilibrium comment lines take the active labels too. This is a
  visible **Imperial** change, which D-21 authorises; verified across all six
  examples × wing/tail/control × stick model, Imperial output changed by **zero
  numeric characters** — only header rows and two `$` comment lines. The
  fitting-load CSV's force marker moved from its own `lb-ULT` to the renderer's
  `lbs-ULT`, so the export channel and the report share one vocabulary.
- **M4-20 step 3 — the load-case CSV writer takes the unit system.**
  `io.load_cases_csv(results, header_comment="", *, system=UnitSystem.IMPERIAL)`
  and `io.write_load_cases_csv(..., system=...)` convert the whole table **once**,
  inside the writer, via `units.convert_results`. `report/render.py` is
  **unchanged**: it reads each `LoadValue.units` string, so an SI table's headers
  (`Vertical load (N-ULT)`, `Engine mount torque (Nm-ULT)`, `Loc X (mm)`) come out
  of the existing `_detect_unit` with no unit-system knowledge in the renderer at
  all, and `Speed (kt)` / `Altitude (ft)` stay byte-identical in both systems
  (the aviation carve-out). `system=IMPERIAL` is the identity — swept over every
  example × every module, the output is byte-identical to the call without the
  parameter, so no existing caller moves. `cli.py`'s `-o` path now hands the
  writer *unconverted* results plus the system; the two text reports still take
  pre-converted results plus their display label. A guard test pins
  `load_cases_csv` as the **only** `convert_results` caller in `io.py`, so the
  human export channel has exactly one conversion point and a caller cannot
  double-convert by pre-converting and passing `system=` as well.
- **M4-20 step 2 — the unit selection is now part of the project.**
  `Project.unit_system` (**`SCHEMA_VERSION` 37 → 38**) records which system every
  *deliverable* is rendered in. It is a **preference only** — `io.py` still never
  converts, so the values stored beside it are canonical Imperial as always, and
  a project written on an SI machine holds the same numbers as one written on an
  Imperial machine. Absent (every pre-v38 file) reads as Imperial, so an older
  project's output is unchanged. The field is **additive with a total default and
  therefore needs no migration hop**: absent *is* its documented value. Written to
  `project.json` only when non-default, on the v36 document-control precedent, so
  the six shipped examples gain no key at all.
- **M4-20 step 2 — `--units imperial|si` on the CLI**, with `cli.resolve_units`
  resolving flag → project preference → Imperial. A run with neither reproduces
  today's output exactly. `--units si --export-sbeam` **errors** rather than
  exporting: the sbeam writers are Imperial-only until step 4, and a deck written
  in units the user did not ask for is the exact failure this item exists to
  prevent.
- **M4-20 step 2 — the sidebar Imperial/SI toggle writes the project** (decision
  D-22), so changing units is a project edit and shows as an unsaved change.
  `app/components.active_system()` — the single read of the unit selection in the
  whole app layer (D-16) — was re-pointed at the field, and **no call site
  changed**: every view follows through `unit_number_input`/`page`, which is what
  that resolver was built for. `st.session_state["unit_system"]` survives only as
  the fallback for a render with no project yet.
- **M4-20 step 1 — deliverable unit sets (`units.py`).** `Channel`,
  `DeliverableUnits`, `deliverable_units(system, channel)` and `units_statement()`:
  the one authority for what units a deliverable is written in. Resolve it **once
  per bundle** and hand it to every writer, so two files in one export cannot
  disagree. Imperial is the all-1.0 identity set, so a writer needs no
  `if system == IMPERIAL` branch — "Imperial output is unchanged" becomes
  structural rather than a promise. Nothing consumes it yet; steps 2–7 wire it to
  the CSV/BDF/report writers. Plan:
  `docs/30_future/06_m4-20_deliverable_units_plan.md`.
- **The human/solver channel split (decision D-19).** Human-readable deliverables
  report moments in `N·m`; the sbeam decks and their companion span CSVs use
  **`N·mm`**, because sbeam is only correct in a dimensionally consistent set — a
  deck whose GRID coordinates are millimetres and whose forces are newtons needs
  `N·mm` moments, and an `N·m` one is wrong by 1000× in a file that parses
  cleanly and sizes structure. Moment factors are now *derived* as force × length
  from named base constants, and a test asserts `moment == force × length` for
  the solver set in both systems.


- **`PROJECT_GUIDE.md`'s schema-change convention contradicted the tripwire.** It
  said a new optional field with a default "needs nothing", while
  `test_schema_guards.py`'s fields-hash tripwire fails on *any* persisted-shape
  change — as it duly did for `unit_system`. The convention now states the
  additive case explicitly: bump `SCHEMA_VERSION`, write no hop.
- **`Pa-ULT` → `kPa-ULT` (decision D-20).** `units.py` already converted psi → kPa
  everywhere in the GUI while three documents specified `Pa`. The code was right;
  CLAUDE.md, `00_program_overview.md` and `SUMMARY_REPORT.md` §3.5 now say
  `kPa-ULT`, keeping one pressure unit across GUI and exports. `SUMMARY_REPORT.md`
  §3.5 also gains the solver-deck carve-out its "no dual display" clause would
  otherwise have forbidden.

- **Backlog review — M4 re-prioritised and the future-development tree pruned
  (docs only).** **M4-20** (deliverables render in the user-selected unit
  system) is now the first M4 item: **M3-3b** (the G8 report document) was
  listed first while being explicitly blocked on it, so the head of the list
  could not actually be worked. M3-3b follows, with its one unit-independent
  sub-step (`content.py`) called out as startable in parallel. The backlog's
  shipped-work narrative is replaced by pointers to `40_history/`, **M4-23**
  gained a full entry (it was previously only a line in the defect index), and
  the ~25-nit **L-8** bucket is split into **L-8a…L-8f** (SI-toggle conformance,
  tooltip rollout, results/export parity, widget freshness, uncovered fields,
  and a clearly-marked display-only tail) so the items can close independently.
- **Three spent plan documents moved from `docs/30_future/` to
  `docs/40_history/`**, so `30_future/` holds only live plans:
  `02_gui_workflow_plan.md` → `40_history/05_phase_d_gui_workflow_plan.md`
  (Phase D, executed; nav grouping superseded by Phase G), `04_m3-1_rename_procedure.md`
  → `40_history/06_m3-1_rename_procedure.md` (executed with 0.3.0), and
  `06_m4_maintainability_sequence_plan.md` →
  `40_history/07_m4_maintainability_sequence_plan.md` (all six steps shipped
  2026-08-03/04). Each carries an "executed and closed" banner; all inbound
  links across `docs/`, `sloads/`, `tests/` and this changelog were repointed,
  and every markdown link target under `docs/` was verified to resolve.

- **M4-9 — a result's meaning is now its `key`, not its display label.**
  `LoadValue` gains a stable snake_case `key`; `report`, `export`, the views and
  the tests match on it and nothing branches on `label` any more. Rewording a
  column heading used to make the lookup return `None`, which `_val` turned into
  `""` — the CSV shipped with a blank cell and no error anywhere. All **327**
  producing sites across 21 modules are keyed, the cross-module keys live in the
  new `sloads/load_keys.py`, and the 23.371(b) gyro sub-cases come off the key
  instead of a regex over the label. **No output changed**: a snapshot of every
  value, every rendered row and every text report across all six examples is
  byte-identical before and after. `SCHEMA_VERSION` 36 → 37.
- **M4-9 — six calc-side modules stopped reading another module's labels.**
  `validation`, `structural_speeds`, `landing`, `weight_envelope`,
  `weight_estimate` and `flight_envelope.design_inputs` looked up `"Total area"`,
  `"MAC"`, `"XBAR (fus station)"` and the design speeds by label across a module
  boundary. `configuration.cg_estimate` no longer takes a dict at all: it indexed
  `geom["MAC"]`, and the Configuration page was passing it the *LoadValue* table
  rather than the geometry dict — which worked only because the two happened to
  spell `"MAC"` the same way.
- **M4-10 — `project.json` loading is now a migration chain, not key sniffing.**
  `io.project_from_dict` decided what it was reading with a 19-clause `or` gate
  enumerating every slice name, and handled each legacy file shape with an inline
  shim threaded through the readers. Both are gone. `sloads/migrations.py` holds a
  chain of pure `dict -> dict` hops — one per version that changed the file's
  *shape*, with the archaeology of which legacy path belongs to which version
  finally written down — and `io.py` reads the current schema only.
  **All five legacy shims deleted**, the three `legacy_*` reader parameters
  removed, `io.py` down from 1,290 to 1,180 lines. The project/engine
  discriminator now derives its key set from `Project`'s own dataclass fields, so
  adding a slice can no longer silently downgrade a real project to an
  engine-only read. All six examples round-trip byte-identically; six frozen
  fixtures (v0 bare engine, v18, v24, v26, v28, v36) pin every reachable
  historical shape. *(M4-9 later renamed the v36 fixture and added a v37 one, so
  the set is seven.)*
- **M4-10 — legacy migrations are version-gated.** The old shims ran on *every*
  file regardless of version, which meant a current project that legitimately had
  no `weight.cg_cases` had them invented from `flight_loads`, and one with no
  `aero_coeffs` had a set resurrected from a stale
  `flight_loads.configurations`. The hops run only for files old enough to need
  them. Two tests that claimed to cover "pre-schema-18/19 files" were in fact
  mutating a current dict and passing for the wrong reason; they now declare the
  version they test.


- **G8.1 — `sloads/report.py` is now the `sloads/report/` package**, the same
  mechanical move `models.py` → `models/` made at M3-1. Existing code is
  `report/render.py` verbatim and every public name is re-exported, so all 15
  importing modules are unchanged. One exception surfaced by the move:
  `report._fmt` was imported across the module boundary by a test, so it is
  promoted to **`report.format_value`** per the M4-12b public-symbol contract.


- **M4-12b — public import contract: seven private symbols promoted, `__all__`
  on the four defining modules.** `app/` no longer imports any underscored name
  from `sloads` — the two live violations
  (`configuration_layout` → `wing_geometry._interp_x`, `components` →
  `structural_speeds._maneuver_load_factors`) are gone, along with five
  cross-module private imports inside `sloads/`. Promotions (66 sites):
  `interp_x`, `maneuver_load_factors`, `design_inputs`, `density_ratio`,
  `elevator_load`, `flaps_by_config_name`, `default_envelope`. Names outside a
  module's `__all__` are module-private, and there is deliberately no
  `sloads/api.py` facade. **No behaviour change:** a full result snapshot — every
  module, condition, `LoadValue` and safety factor across all 6 examples — is
  byte-identical before and after, and every Appendix A figure and tolerance
  literal is unedited.
- **M4-12b — `select.htail_balance` returns a typed `HtailBalance`.** The
  rational tail balance crossed three module boundaries as a `Dict[str, float]`
  whose string keys were the API; it is now a `NamedTuple` with lowercase
  attributes (`lt25`, `lt50`, `at`, `delta`, `lt`, `cp`) and the Ref 1 Ch 9
  symbols tabulated in its docstring. BALLOADS' `verify_balancing` row dicts are
  a separate structure and keep their keys.
- **M4-12b — porting contract extended** (`PROJECT_GUIDE.md` §5):
  `sync_geometry_derived(project)` is called first inside `run()` (seven sites,
  previously convention-by-imitation); cross-module results are typed, not
  stringly-keyed; the public surface is explicit; and no new property proxies on
  `Project`. The `Project.tail_loads`/`.vtail_loads` trap-doors — invisible to
  `dataclasses.fields`/`asdict`/`replace`, and a setter that silently no-ops on
  `None` — are now documented beside the properties, with retirement assigned to
  **M4-10**.

- **M4-12a — test architecture: shared helpers and form-key button selection.**
  Nine near-identical `_value` lookups (three different signatures) collapse into
  `tests/helpers.py` — `value_of` / `load_value` / `values_by_label`, each
  accepting a `ModuleResult`, a `ConditionResult` or a nested list of either.
  Shared input builders move to `tests/fixtures.py` and the sbeam free-field BDF
  reader to `helpers.parse_cards`, so **no test module imports another test
  module** (eight did). The helper signature is deliberately the one **M4-9**
  will re-point at `LoadValue.key`, which is why the consolidation lands first.
  Tests-only: no `sloads/` or `app/` change; 536 tests pass with every numeric
  assertion unedited.


- **BREAKING (sbeam body decks): fuselage GIDs are now keyed off station
  provenance, not table index.** The carry-through reaction inserts nodes into
  the *middle* of the beam, so the old `1001 + i` numbering would have silently
  renumbered every mass station aft of the wing whenever a spar fraction moved.
  `BodyStationLoad.source` (`mass`/`tail`/`carry`/`correction`) now drives
  `sbeam_bridge.body_station_gids`: mass + tail stations keep `1001 +` in
  nose→tail order, reaction nodes take a disjoint `1501 +` block (each block
  holds 500; the tail family still starts at 2001, and the function raises
  rather than collide). **Body decks exported before this release must be
  re-exported** — `fuselage_loads.bdf` and `fuselage_span_loads.csv` GIDs no
  longer match a previously issued deck. Wing, tail and control-surface GIDs are
  unchanged.
- **The Configuration & Layout page takes the wing spar fractions.** Optional
  front/rear `% chord` inputs per surface; **left blank they stay `None`**,
  which is what makes the entered-vs-assumed provenance reachable from the GUI —
  before this every project necessarily resolved as `assumed`.

- **Backlog hygiene sweep** (docs only, no open work dropped).
  `docs/30_future/00_backlog.md` 570 → 469 lines: removed the completed-M3
  section, the shipped-item recitals and the 2026-07-21/07-23 review narratives
  (all recorded in history), dropped the stale gate snapshots in favour of CI,
  and stripped the superseded "(was 2-x)" legacy IDs. The resolved
  design-decision table D-1…D-11 moved to the new register
  `docs/40_history/03_resolved_decisions.md` (open **D-5** stays in the
  backlog); M4-1's diagnosis, A–E options trade and formulas moved to the new
  `06_m4-1_body_moment_closure.md` (now closed and filed as
  `docs/40_history/04_m4-1_body_moment_closure.md`), leaving the decided approach
  and acceptance criteria in the backlog. Both new docs are indexed in
  `docs/00_INDEX.md`.
- **Backlog ID collision fixed.** `M4-18` was in use by two different items —
  the shipped loads-reference-axis step (history, `CHANGELOG`, `GUI_design.md`
  v34, `PROGRAM_SPEC.md`, `project.py`) and the open fuselage pitching
  load-factor item. The open item is renumbered **M4-21**; the shipped step
  keeps M4-18 everywhere it is already cited.

- **Standard: deliverable units follow the user's selection** (docs only; the
  code change is backlog **M4-20**). Exports are no longer fixed to the calc's
  Imperial units — the report, the load-case CSV, the span-load CSVs and the sbeam
  `FORCE`/`MOMENT` cards all render in the system the user chose (GUI toggle,
  persisted in the project, overridable headless by `--units imperial|si`,
  default Imperial), one system per bundle, each file stating its system in-band.
  The `-ULT` marker converts with the unit (`N-ULT`, `Nm-ULT`, `Pa-ULT`); no dual
  display; airspeed (KEAS) and altitude (ft) remain aviation-standard and
  unconverted in both systems. Calc and the stored `project.json` values stay
  canonical Imperial, so the Appendix A/B oracles are unaffected. Updated
  `docs/10_standard/SUMMARY_REPORT.md` §2/§3.5/§4.1/§4.7/§6,
  `00_program_overview.md`, `GUI_design.md` §4/§7/§10, `PROJECT_GUIDE.md`,
  `CODE_REVIEW_PROCESS.md` (checklist + finding table),
  `docs/30_future/01_concept_loads_plan.md` and
  `05_step_g8_summary_report_plan.md` §10.1 (open question resolved).


- Landing CG-case rows are **name-locked and order-canonical**: the data editor's
  `Loading` column is read-only and Apply writes the canonical names, while
  `landing._cg_cases` reorders by name when all three canonical names are present
  (otherwise positional, exactly as before). The editor could previously be
  renamed or reordered into a silent mis-assignment of the braked-roll/side
  weight groups, which are indexed positionally.
- Every bundled `examples/*.project.json` now carries a regenerated `mass` block.
  Consequence: `configuration.cg_estimate` flips from the 25%-MAC fallback to its
  "Weight DB" branch, so the tip-back / overturn / CG-station figures change on
  five examples (e.g. GA-6 CG 74.07 → 85.0 in, tip-back 33.11 → 13.49°, overturn
  43.01 → 48.69°). `one_engine_out` on the twin turboprops now passes the mass
  gate and stops at the next missing input (engine horsepower) instead.
- Removed the never-assigned, never-read `nv`/`nd`/`nns` fields from
  `GearReactionCase`. The airplane-datum `vm`/`dm`/`vn`/`dn` are kept (they *are*
  computed) and documented as an M4-6 hook.
- **`SCHEMA_VERSION` is unchanged (33):** the `mass` block already round-tripped
  through `io.mass_from_dict`/`mass_to_dict` and is optional on read. Only its
  *presence* changes, not the schema shape.
- **`report._LOAD_CASE_LABELS` is deliberately not extended.** A LANDLOAD case is
  a *pair* of reactions at two stations with three unbalanced moments;
  `load_cases_to_rows`' single-point-load schema cannot hold that without losing
  the nose reaction or fabricating locations, so landing keeps routing through
  `results_to_rows` (locked by a test).
- **No calc-math change.** The Appendix-A landing oracles (p230 K/GAMMA/BETA and
  the lever-arm table; p236 V/N/NLG) and all existing tests pass unchanged; the
  p230 oracles are additionally re-asserted through the full
  `build_landing(load_project(...))` pipeline as a regression guard.

---

## [0.3.0] — 2026-07-23

**Concept-loads v1** — the suite becomes an initial-concept distributed-loads
tool: the `concept` category (caps beyond FAR 23), fleet comparison, per-component
distributed loads (wing/body/tail + simplified control surfaces) and the sbeam
`FORCE`/`MOMENT` export, on top of the oracle-locked FAR 23 replication core.
This release also **renames the suite `farloads` → `sloads`** (decision D-6/D-11;
package, CLI entry point and docs), completes GUI Phase G (workflow navigation,
six-phase analysis flow, per-page unit boundary), and lands the per-case
safety-factor chain end-to-end (M4-7, M4-13 … M4-16): every deliverable is
ULTIMATE with its case's `SF` stated, LIMIT analysis artifacts are basis-marked
in-band, and a corrupt persisted factor can neither crash nor under-scale an
export. Suite at cut: 501 tests, ~93% coverage, ruff clean, smoke test PASS,
`SCHEMA_VERSION = 33`.

### Added

- **`SF` column on the four sbeam span/chordwise CSVs** (wing, fuselage, tail
  chordwise, control surface) — the case's limit→ultimate factor, satisfying
  "every load case SHALL state its safety factor". Appended as the **last**
  column, so positional parsers are unaffected (`Case,GID,X,Fz,Sz,Myy` →
  `Case,GID,X,Fz,Sz,Myy,SF`).

- **Trim & static-margin plots — Flight Envelope page (Phase G, Step G5).** A new
  **Trim & Stability** tab on the Flight Envelope page plots the balancing
  horizontal-tail load at 1-g trim (FLTLOADS BAL A/C/D) swept across the CG range,
  and the tail-volume static margin. A pure `flight_envelope.trim_sweep()` helper
  re-runs the existing FLTLOADS balance (subroutine 3900) at ~15 interpolated CG
  stations at a fixed weight/waterline — no new load equations, so a swept station
  that coincides with a project CG case reproduces that case's `build_envelope` BAL
  load exactly. The static-margin sweep reads the tail-volume **neutral point** from
  the Configuration module (`SM = NP − CG`, %MAC) and overlays the WTENV
  forward/aft CG limits; it is shown only when the project carries a parametric
  layout (Appendix A/B fixtures show just the trim plot). Tail loads on the tab are
  **LIMIT** (marked, with the ULTIMATE deliverables pointed to on the Critical
  Loads tab / Results Review / exports). GUI-only over existing calc — no schema
  change. (Config-building for the balance was factored into
  `flight_envelope._balance_configs`, shared by `build_envelope` and `trim_sweep`
  so both see the same G4 fuselage-augmented coefficients; behaviour unchanged.)
- **Fuselage pitching-moment estimator — Munk slender-body (Phase G, Step G4).** A
  pure, geometry-only helper (`farloads/fuselage_moment.py`) derives the fuselage's
  contribution to the airplane-less-tail moment slope `dCm/dα` from the G1 fuselage
  outline (Munk apparent-mass method, NACA TR-184 / DATCOM 4.2.1.1; see
  `reference/fuselage_pitching_moment.md`), so a concept airplane built from a
  planform no longer has to hand-fold the fuselage into the FLTLOADS input
  coefficients. Surfaced on the **Aerodynamic Data** page: the estimate (volume,
  fineness ratio, `k₂−k₁`, ΔM1) is displayed and overridable, with an enable
  checkbox. A new `AeroCoefficientsInput.fuselage_moment` field
  (`FuselageMomentInput{enabled, d_cm_dalpha}`) carries it; when enabled,
  `flight_envelope.build_envelope` adds ΔM1 to every configuration's M1 (a local
  copy — the stored raw coefficients are untouched) and the compressibility factor
  applies automatically. **Off by default → Appendix A/B oracles bit-for-bit
  unchanged** (their coefficients already include the fuselage). `SCHEMA_VERSION`
  25 → 26; older files load with no fuselage moment.

- **Concept engine gyroscopic guard + warn (Phase 1, Step P1-5).** The optional
  FAR 25.371 gyroscopic concept case (`engine.condition_25_371`) uses a fixed
  FAR 23.371(b) stand-in (2.5 rad/s yaw, 1 rad/s pitch); the gyro moment is linear
  in body rate, so the stand-in under-predicts for a concept whose real rates are
  higher. `EngineInput` gains two optional advisory fields —
  `design_yaw_rate_rad_s` / `design_pitch_rate_rad_s` (**`SCHEMA_VERSION` 22 → 23**,
  additive; older files load with both unset) — and when a declared rate exceeds its
  stand-in the case's note becomes an explicit `WARNING -- gyroscopic loads
  UNDER-PREDICTED …` (naming the axis, rate and moment ratio). Per decision D-2 this
  is **warn-only**: the reported moment stays at the fixed stand-in (the declared
  rates are advisory, not a re-derivation). The engine GUI page adds the two rate
  inputs and renders `WARNING` notes as `st.warning`. The GA/oracle path is
  unchanged (no declared rates → no warning). Guarded by five new tests in
  `tests/test_engine_far25.py`.

- **Complete export package public API (Phase 1, Step P1-4).**
  `farloads/export/__init__.py` now re-exports all four component families +
  the case index: the body (`body_span_load_csv`, `body_force_moment_cards`),
  control-surface (`control_surface_csv`/`control_surface_force_moment_cards` +
  their `write_*` variants), and case-index (`case_index_csv`,
  `write_case_index_csv`, `filter_by_selected_case_ids`) functions were previously
  reachable only via the `sbeam_bridge` submodule (`__all__` advertised wing + tail
  only). The package docstring is rewritten from "wing-only" to enumerate all four
  families. Guarded by `test_sbeam_bridge.py::test_export_package_exposes_all_component_families`.
  API-surface-only (no calc-math or schema change).

- **Concept↔FAR23 identity test (Phase 1, Step P1-3).** `tests/test_concept.py`
  now guards the C-1 invariant ("concept mode reduces **exactly** to FAR23 on GA
  inputs") *directly, through the concept branch* — previously it was only assumed
  via the absence of GA-oracle regression. `test_concept_reduces_to_far23_on_ga_inputs`
  runs `ga6_normal` through `run_all_modules` twice — once as Normal (`category="N"`)
  and once flipped to concept (`category="C"`) with the FAR23-computed load factors
  (n = 3.8, nneg = −1.52 per 14 CFR 23.337, derived from the baseline) — and asserts
  full-pipeline parity (every module's every `LoadValue` matches at `rel_tol=1e-3`;
  only the appended concept `note` may differ). `test_concept_load_factors_match_far23_caps`
  pins the single numeric divergence point (`structural_speeds._maneuver_load_factors`).
  Test-only (no calc-math or schema change); FAR23 oracles unmoved.

- **Concept distributed-loads closure suite (Phase 1, Step P1-2).**
  `tests/test_concept_closure.py` (10 tests) drives `net_loads`, `body_loads`,
  `taildist`, `aileron`/`flap`/`tab` through the P1-1 concept fixture
  (`concept_regional_jet`) and asserts **physics-closure per component** — concept
  mode's only validation above the 12,500 lb FAR23 oracle band. Checks: wing lift
  closes vertically (`LZW + LT = Nz·W`); the balancing tail load reacts the pitching
  moment about the CG (`LT·(Xt−Xcg) = LZW·(Xcg−Xw) − DX·(Zcg−Zw) + M(W+F)`); the
  fuselage net distribution is free-free (terminal cumulative shear = 0); TAILDIST
  carries SELECT's `lt25`/`lt50` split verbatim; each control surface's `build_*`
  load matches its `run` analysis report; and every component family's nodal FORCE
  set (and its re-parsed cards) sums to that component's root/total at ULTIMATE —
  the whole concept airframe exports cleanly through `sbeam_bridge`. Test-only
  (no calc-math or schema change); FAR23 oracles unmoved.

- **Full-airframe concept reference fixture (Phase 1, Step P1-1).**
  `examples/concept_regional_jet.project.json` — "RJ-50 concept", a swept-wing,
  high-subsonic twin-turbofan regional jet (MTOW 33,000 lb, S 500 ft², c/4 sweep
  24°, cruise M 0.74, 50 seats; `category="C"`, Part 25 load factors, `include_far25`).
  It is the first concept example to drive **every** component path — the wing chain,
  `body_loads`, `taildist`, `aileron`/`flap`/`tab`, and the swept `AIRLOAD4` branch
  (19 modules, no missing-slice skips) — where `concept_heavy` reached the wing only.
  Carries the two slices no GA fixture had (`fuselage_mass`, `configuration`); the
  turbofan is modelled with a fan-spool `Rotor` and no propeller (25.371 gyro path).
  Guarded by `tests/test_concept_regional_jet.py`. Airplane per decision D-1, engine
  per D-2.

- **Aircraft Comparison page (Phase F, Step F2).** A dedicated
  `app/views/aircraft_comparison.py` view in the **Export** phase (before Results
  Review; GUI-only `WorkflowStep`) is now the single home for the fleet comparison.
  It carries a quantitative readout (nearest-3, W/S & W/P percentile band, outliers),
  a **parameter table** (subject + nearest-N over MTOW/OEW/power/W-S/W-P/wingspan/
  area/AR/seats), and **six scatter tabs** (W/S-vs-W/P, MTOW-vs-OEW, and wingspan /
  wing area / aspect ratio / seats vs. MTOW). `Subject` (and `FleetPoint`) gain
  presentation-only `wingspan_ft`/`aspect_ratio`/`seats` fields plus `span` /
  `aspect_ratio_effective` derivations (`span = √(AR·S)`); the nearest-N distance
  stays on MTOW / W/S / W/P, so `fleet_stats` is byte-identical (decision D-F2-a).
  Guarded by new `tests/test_aircraft_comparison.py` and extended
  `tests/test_fleet_compare.py`. No calc-math or oracle change.

- **Reference-fleet expansion for the Aircraft Comparison page (Phase F, Step
  F1).** `app/data/reference_aircraft.csv` gains an `aspect_ratio` column (span²/area)
  and six aircraft (PA-28-181 Archer, Cirrus SR22, Diamond DA40, Extra 300, PA-44
  Seminole, TBM 940 — 23 → 29) to broaden the geometric spread. `FleetPoint` carries
  optional `seats` / `wingspan_ft` / `aspect_ratio` (defaults; `fleet_stats`
  unaffected), and `_fleet_points` maps them. Data-only; no calc-math or oracle
  change. Guarded by `tests/test_reference_aircraft.py`.

- **`farloads.constants.convert_airspeed` + `eas_to_mach`/`mach_to_eas` (Phase E,
  Step E7).** Presentation-layer airspeed conversions: KEAS→KTAS (=KEAS/√σ) and
  KEAS→KCAS (standard subsonic compressible impact-pressure relation, exact at sea
  level). Backed by `tests/test_airspeed_conversions.py`.

- **Quantitative fleet comparison (Phase E, Step E4).** The visual, duplicated
  fleet scatters on **Configuration & Layout** and **Weight Estimate** are unified
  behind one shared helper that adds a **quantitative readout** above the scatters:
  the **nearest-3** similar reference aircraft (by a normalized distance over
  log-MTOW plus W/S and W/P where known), the **W/S and W/P percentile band**, and
  **outlier flags** (outside the fleet p10–p90). The numeric core is the new pure,
  unit-tested `farloads/fleet.py` (`fleet_stats(subject, fleet) -> FleetStats`; no
  pandas / file access / Streamlit); the CSV load and rendering are the single
  `app/components.render_fleet_comparison`, reused by both pages. Jets (`max_hp = 0`)
  are excluded from the W/P comparison only, never from the comparator pool.
  GUI-only: no schema change (`SCHEMA_VERSION` stays **22**) and no calc-math change
  — the Appendix A/B oracles are untouched (343 tests pass, +10). Implements
  `GUI_design.md §8.4`.
- **Graphical review + input-consistency validation (Phase E, Step E3).** Two new
  pure, unit-tested helpers and their GUI surfacing. `farloads/vn_diagram.py` builds
  a proper **V-n diagram** — the curved stall boundary `n = (V/VS)²`, the flaps-up
  and flaps-down (n ≤ 2.0, 14 CFR 23.337(b)) manoeuvre envelopes and the gust lines
  at VC/VD (textbook Pratt form, 14 CFR 23.341) — now shown on the **Structural
  Speeds** page (Flaps up/down/both + gust toggle, LIMIT-marked; the rigorous
  Mach-corrected gust V-n stays on the Flight Envelope page, unchanged).
  `farloads/validation.py` adds `consistency_warnings(project)` — taper > 1,
  non-positive area, LE/TE ordering, Configuration-vs-WINGGEOM wing-area mismatch,
  and CG outside the WTENV structural envelope — surfaced as `st.warning` on the
  relevant definition pages. The **Weight/CG/Inertia** page gains a CG-marker +
  mass-distribution plot (with the WTENV limits when defined). GUI-only in effect:
  no schema change (`SCHEMA_VERSION` stays **22**) and no calc-math change — the
  Appendix A/B oracles are untouched (333 tests pass, +18). Implements
  `GUI_design.md §8.2/§8.3`.
- **Parameter explanation — tooltips + guides (Phase E, Step E2).** Every domain
  input widget across the six Airplane-definition pages (Configuration & Layout,
  Wing / Surface Geometry, Weight Estimate, Weight/CG/Inertia, Structural Speeds,
  Aerodynamic Data) now carries a `help=` hover tooltip citing the relevant FAR
  paragraph and Reference-1 program/chapter; the three grid (`st.data_editor`)
  pages and the dense pages additionally carry a collapsible **"ℹ️ Parameter
  guide"** expander defining the jargon (MAC, XLEMAC, static margin, neutral
  point, tip-back/overturn, shoulder altitude, KEAS, the aero `C0…C4`
  polynomials, per-item inertias and the parallel-axis convention). GUI-only:
  no schema change (`SCHEMA_VERSION` stays **22**) and no calc-math change — the
  Appendix A/B oracles are untouched (314 tests pass). Implements
  `GUI_design.md §8.1`.
- **FAR 23 applicability detection + occupants/crew fields (Phase E, Step E1).** The
  GUI now surfaces — never blocks — when an airplane exceeds the FAR 23 applicability
  band. New pure, unit-tested `farloads.far23_applicability(project)` returns the
  structured exceedances (field / value / limit / label) against the non-commuter
  FAR 23 tier (12,500 lb / 9 passenger seats, the required flight crew excluded);
  the limits live once in `farloads/constants.py` (`FAR23_MAX_WEIGHT_LB` etc.,
  `DEFAULT_FLIGHT_CREW = 1`, with the 19,000 lb / 19-seat commuter tier encoded but
  dormant until a distinct Commuter category exists). Two additive schema fields
  (`SCHEMA_VERSION` **20 → 22**, older files load with defaults): a
  `StructuralSpeedsInput.occupants` field (total souls; falls back to the Weight
  Estimate seat count) entered on **Structural Speeds** and echoed read-only on
  **Configuration & Layout**; and a `WeightEstimationInput.crew` field (flight crew,
  default 1) entered on **Weight Estimate**, subtracted from occupants for the seat
  check (`passenger seats = occupants − crew`) and carried in a new derived
  **operating empty weight** line WTESTIMA reports (`OEW = empty + crew×170`, a
  reporting-only figure — `MTOW`/`useful`/`empty` and their Appendix-A oracles are
  untouched). A shared `app/components.render_applicability_banner` renders a
  non-blocking banner on the **Dashboard** and the definition pages with a one-click
  **"Switch to Concept"** action that flips `speeds.category = "C"` and seeds
  `chosen_n`/`chosen_nneg` from the computed FAR 23.337 factors so the switch is
  continuous. No calc-math change — the Appendix A/B oracles pass unmodified and
  concept mode still reduces exactly to FAR 23 on GA inputs. Tests:
  `tests/test_applicability.py` (GA → no exceedances; 20,000 lb / 12-occupant Normal
  → weight + seat exceedances; crew reduces the seat count), the OEW line in
  `tests/test_weight_estimate.py`, and occupants/crew io round-trip / old-file
  defaults in `tests/test_io.py`.

- **Definition pages seed defaults from upstream project data.** Pages no longer
  re-ask for a quantity another slice already owns. New
  `farloads.modules.configuration.wing_layout_from_surface()` (the inverse of
  `wing_polylines`) lets **Configuration & Layout** seed its parametric wing
  fields (area / aspect ratio / taper / LE sweep / LE station) from an existing
  WINGGEOM `wing` surface; **Flight Envelope** seeds MAC / wing area / 25%-MAC
  station from that surface (and waterline from `configuration`) instead of
  hardcoded Appendix-A literals; **Mach Limit** seeds `MC`/`MD`/shoulder
  altitude from STRSPEED's `design_speed_values`; **Tail Loads** seeds the
  h/v-tail spans from `configuration.h_tail_span_ft`/`v_tail_span_ft`; **Wing
  Loads** seeds dihedral from `configuration.dihedral_deg`. Each seed fires only
  when the page's own field is still unset, so an explicit value is never
  overwritten. No calc-math change, no new `Project` slice, `SCHEMA_VERSION`
  unchanged at 20.

- **Airplane-phase GUI usability pass: tail geometry, wing planform plot,
  aero-data naming.** `LayoutInput` gains `tail_type` (`TailType`:
  `CONVENTIONAL`/`T_TAIL`/`V_TAIL`/`CRUCIFORM`, additive, default
  `CONVENTIONAL`) plus `h_tail_span_ft`/`h_tail_z`/`v_tail_span_ft` (all
  default `0.0`, backward-compatible — an older project with these unset draws
  no tail, exactly as before). New `farloads.modules.configuration.
  tail_planform()` sketches the tail panel(s) for the Configuration & Layout
  three-view, which now draws them in Top/Side/Front alongside the existing
  wing/fuselage/gear overlays. The Wing/Surface Geometry page gains a top-view
  planform plot (new shared `farloads.modules.wing_geometry.
  surface_top_outline()` helper, also used by the three-view's wing outline).
  The `aero_coefficients` Airplane-phase step is retitled "Aerodynamic Data"
  (key unchanged) with a cross-link caption to the Wing Loads page, where the
  per-surface spanwise (Schrenk) aero input stays, with a matching caption
  pointing back. `SCHEMA_VERSION` bumped 19 → 20 (additive fields only).

- **Session-wide Imperial/SI display toggle + Project JSON Editor page.** A
  single sidebar control (`app/Home.py`, `st.session_state["unit_system"]`)
  now drives Imperial/SI display consistently across every GUI page (all 24
  views), replacing the handful of pages that previously had their own local,
  uncoordinated toggle. New `farloads.units` scalar helpers (`to_si_scalar`,
  `si_scalar_label`) convert per-station/per-case dataclass values (wing/
  fuselage/tail/landing-gear results) that aren't `ConditionResult`/`LoadValue`
  based; every conversion is display-only — the objects feeding sbeam BDF
  export, project persistence and CSV downloads stay canonical Imperial.
  Airspeed (KEAS) and altitude (ft) are never converted (aviation-standard
  units in both systems). New `app/views/project_editor.py` (Start section):
  the whole project shown/hand-editable as JSON in the selected units, backed
  by new `farloads.units.project_dict_to_display`/`project_dict_to_imperial`
  (a field-name-driven whole-project converter, distinct from mass-vs-force
  `_lb` fields); Apply converts back to Imperial before updating the session.
  `project.json` on disk is unchanged — still Imperial-only, no unit tag ever
  written, no new `Project` slice, `SCHEMA_VERSION` unchanged at 19.

- **Export & report upgrades** (Phase D Step D8 — closes Phase D). Export page
  gains a "📊 Download workbook (.xlsx)" button (new `farloads/export
  /workbook.py::build_workbook`, `openpyxl` dependency): one workbook tab per
  module/component (Project info, per-module load-case CSVs, the case-index
  table, and the tabular sbeam span-load CSVs), a sibling alternative to the
  `.zip` bundle. Export page also gains an "Export scope" toggle (Full set /
  Governing set) that filters the fuselage/tail sbeam artifacts and the case
  index to the D5 Critical Loads page's selection (new pure helper
  `sbeam_bridge.filter_by_selected_case_ids`); wing and control-surface
  exports always include the full set since their case ids don't overlap
  `envelope.critical`'s (a known, documented gap — see the backlog). No
  calc-math change, no new `Project` slice, `SCHEMA_VERSION` unchanged at 19.

- **Loads Plots page** (Phase D Step D7). New `app/views/loads_plots.py`, the
  sixth workflow section: a read-only, consolidated viewer over the
  distributed-load results already persisted on `Project.loads` by the
  Analysis pages — a component picker (wing / fuselage / horizontal tail /
  vertical tail / aileron / flap / tab), overlay plots by case ID with a
  max-|value| envelope trace, a combined wing+fuselage "total loads" snapshot,
  and an external-comparison CSV importer reusing
  `farloads.export.sbeam_bridge.span_load_csv`/`body_span_load_csv`'s exact
  column schema. `farloads/workflow.py` gains the `loads_plots` step
  (`module=None`, like `dashboard`/`results_review`/`export_report`), which
  makes "5 · Loads Plots" appear in `Home.py`'s sidebar automatically. Pure
  GUI addition — no calc-math change, no new `Project` slice,
  `SCHEMA_VERSION` unchanged at 19. The graphics audit (confirm every plot the
  original suite rendered has a Streamlit equivalent) found no gaps.

- **Analysis merged into nine component pages** (Phase D Step D6). The 11
  per-BAS-program Analysis pages are now 9: **Wing Loads**
  (`app/views/wing_loads.py`) merges AIRLOADS (Schrenk) + WINGINER + NETLOADS
  behind one form; **Tail Loads** (`app/views/tail_loads.py`) merges TAILDIST +
  BALLOADS. `farloads/workflow.py`'s `wing_loads`/`tail_loads` steps are the
  shared nav step for each pair (`"airloads"`/`"balloads"` added to
  `FOLDED_MODULES`, reusing the existing `wing_inertia` precedent). The other 7
  pages (Engine Out, Fuselage Loads, Aileron, Flap, Tab, Engine Mount, Landing
  Gear) converted to the Phase-D page conventions: inputs moved into
  `st.form` + an explicit Apply button; Wing Loads' `Project.aero.surfaces`
  write-back changed from a wholesale replace to an upsert-by-name; Fuselage
  Loads' hardcoded 5-row station table and Engine Mount's baked-in Continental
  IO-520-BB `default_engine()` replaced with blank defaults; Aileron/Fuselage/
  Landing Gear/Engine Mount gained the LIMIT caption+marker they were missing.
  Engine Mount additionally retired its separate `st.session_state
  ["engine_inputs"]` store and ad hoc local `Project`, now reading/writing
  `Project.engines`/`Project.engine_layout`/`Project.include_far25` directly
  like every other page. No calc-math change; Appendix A/B oracles pass
  unmodified; `SCHEMA_VERSION` unchanged at 19 (pure GUI reorg).

- **Envelopes & Critical Conditions section** (Phase D Step D5,
  `SCHEMA_VERSION` 18 → 19). New **Weight/CG Grid & Payload Cases** page
  (`app/views/payload_cases.py`) owns a shared `WeightInput.cg_cases` list of
  named loading scenarios; the Weight/CG Envelope page's chart overlays them
  read-only against the forward-loading-envelope boundary, and the Flight
  Envelope page reads them read-only and merges them into the calc-facing
  `FlightLoadsInput.cg_cases` (unchanged for SELECT/WINGINER/NETLOADS/
  BALLOADS), so the two views can no longer diverge. Old project files migrate
  automatically (`io._legacy_cg_cases_from_flight_loads`). The Mach Limit
  page's chart now overlays the VA/VC/VD/VF design speeds as reference lines
  over the Mach-limit boundary. The Flight Envelope page exposes
  `FlightLoadsInput.altitudes_ft` as a real, fully-editable list (multi-altitude
  V-n), with a CG-case selector, an altitude selector and an "overlay all
  altitudes" toggle on the V-n chart. The Critical Loads page adds a per-
  condition opt-out checkbox persisted as `CriticalLoadSet.selected_case_ids`
  (empty = unfiltered); Results Review's governing-loads summary honors it —
  the structural calc modules and the sbeam export bridge are unaffected. No
  calc-math change; Appendix A/B oracles pass unmodified.

- **Form+Apply conversion, Airplane section** (Phase D Step D4.7, closing
  Phase D Step D4). `configuration_layout.py`, `wing_geometry.py`,
  `weight_estimate.py`, `weight_cg_inertia.py` and `structural_speeds.py`
  converted to `st.form`+explicit-Apply (matching `aero_coefficients.py`);
  every remaining Appendix-A-shaped literal default in these pages (GA6
  geometry, WTESTIMA mission figures, STRSPEED speeds/load-factor figures, the
  WINGGEOM Appendix-A wing polyline) replaced with 0/blank/derived defaults.

- **Engine write-back + mass-item overlay on the three-view** (Phase D Step
  D4.6). The Configuration & Layout page's three-view now overlays a marker
  per `Project.weight.items` `MassItem` (colored by `MassItemKind`, sized by
  `weight_lb`) and a diamond marker per `Project.engines[]` entry at its
  `engine_cg`, in all three views. A new "Engine positions (engine_cg)"
  expander lets you numerically override each engine's X/Y/Z station
  (defaulted to the current `engine_cg`); Apply writes back into
  `Project.engines` and re-renders the marker. Page-only change — no
  calc-math, no schema change.

- **True CG from `Project.mass`** (Phase D Step D4.5). New
  `farloads/modules/configuration.cg_estimate(project, layout, geom)` returns
  the weight-averaged CG station from `Project.mass.cases[0]` (WTONECG's
  itemized loading) when present, else the pre-existing `xlemac + 0.25*mac` /
  wing-reference-waterline first cut, plus a `source` label
  ("Weight DB" / "25% MAC estimate"). The landing-gear tip-back/overturn
  `ConditionResult` and the Configuration & Layout page's three-view CG marker
  (top and side views) both switch to it automatically once a mass slice
  exists, with the source named in the `ConditionResult` label and the
  three-view legend. Prop ground clearance is CG-independent and unaffected.
  No schema change.

- **Design-weight read-through, Structural Speeds / Weight Envelope** (Phase D
  Step D4.4). `app/views/structural_speeds.py` reads the design weight from
  `Project.weight.direct_totals()[0]` (the Weight DB total) when items exist,
  read-only with an "Override design weight" checkbox, instead of asking for
  it a second time; when no Weight DB is present it shows an info message
  pointing at the Weight, CG & Inertia page instead of falling back to a
  `3400.0`-shaped literal default (same treatment for its wing-area fallback,
  now `0.0` with its own info message; the pre-existing wing-area
  read-through from `Project.geometry` is unchanged). `app/views/weight_envelope.py`
  (WTENV) gets the same weight read-through + override checkbox for its
  `gross` weight. No calc-math or schema change; the GA6 example is
  unaffected since its stored `speeds.weight_lb` already equals its Weight DB
  total.

- **Component-station derivation + Weight DB seeding** (Phase D Step D4.3).
  `farloads/modules/configuration.py` gained two pure functions:
  `component_stations(layout)` derives approximate `(x, y, z)` stations for
  named airframe components (wing, fuselage, h-tail, v-tail, a lumped "tail"
  average, main/nose gear, a lumped "landing_gear" average) from
  `LayoutInput`'s existing coarse scalars — no schema change; and
  `match_component_station(name, stations)` maps a `MassItem.name` to one of
  those keys by case-insensitive substring alias, most-specific first. The
  Configuration & Layout page gained a "Seed component stations into Weight
  DB" button (mirroring the existing "Seed wing geometry" button) that fills
  a weight item's station only when it is still `(0, 0, 0)`, never
  overwriting a hand-entered value — closing the gap `estimate_to_mass_items`
  (WTESTIMA) leaves (component weights with no station). No calc-math or
  schema change.

- **Aero Coefficients page** (Phase D Step D4.2). New `app/views/aero_coefficients.py`
  is now the single owner of the `Project.aero_coeffs` slice (Step D4.1):
  a form+Apply page (page conventions §5) editing the cruise coefficient set
  plus an optional flaps-down (landing) set behind a checkbox, with no
  Appendix-A-shaped widget defaults (0/blank). Apply wholesale-replaces
  `project.aero_coeffs` — correct for this page since it is the slice's sole
  owner. `app/views/flight_envelope.py` drops the cruise-coefficient editor it
  carried since Step D4.1, gains a "no aero coefficients — define them on the
  Aero Coefficients page" guard alongside its existing missing-speeds guard,
  and shows the coefficients it reads as a read-only caption. No calc-math or
  schema change (reuses the D4.1 `Project.aero_coeffs` slice).

- **`Project.aero_coeffs` slice — single-owner airplane-less-tail aero
  coefficients** (Phase D Step D4.1). New `AeroCoefficientsInput` (`cruise`,
  `flaps_down`, both `Optional[AeroCoeffSet]`) replaces
  `FlightLoadsInput.configurations` (a list of `AeroCoeffSet` keyed by
  `flaps_down`), which is dropped from the schema. `flight_envelope`
  (FLTLOADS) now reads `Project.aero_coeffs` instead of owning the coefficient
  list; `select` and `balloads` read it too (via `select._flaps_by_config_name`)
  for the flaps-retracted/extended split. A new **Aero Coefficients** workflow
  step (`aero_coefficients`, Airplane section, `produces="aero_coeffs"`) and
  placeholder page (`app/views/aero_coefficients.py`, read-only) land in the
  nav; `flight_envelope`'s step now also `requires=("aero_coeffs",)`. The
  cruise-coefficient editor stays on the **Flight Envelope** page for now,
  writing into `Project.aero_coeffs.cruise` while preserving any existing
  `.flaps_down` set — it moves to the new page, plus a flaps-down editor, in
  Step D4.2. `SCHEMA_VERSION` 17 → 18; older project files (with
  `flight_loads.configurations`) migrate automatically
  (`io._legacy_aero_coeffs_from_flight_loads`) so they still load unchanged.
  No calc-math change (Appendix A/B oracles pass unmodified).

- **Local-disk project persistence + Engineer/Date metadata** (Phase D Step D3,
  decision D-3). `app/Home.py` now owns a global **Project file** sidebar
  widget (visible on every page): Open (from a local `projects/` directory,
  newest-first), New from example (`examples/*.project.json`), Save to disk
  (overwrites `<name>.project.json`), the existing browser upload/download, and
  an unsaved-changes indicator; Open/New-from-example confirm via a dialog
  before discarding unsaved edits. `farloads/io.py` gains
  `default_projects_dir()` (repo-relative, not cwd-relative) and
  `list_saved_projects()`. `Project.engineer`/`Project.date` (freeform text,
  blank by default) are new optional metadata, shown on the dashboard and as a
  header line in the Export & Report page's text report / zip bundle.
  `SCHEMA_VERSION` 16 → 17 (additive; omitted from the JSON when blank, so
  existing files round-trip unchanged). `projects/` is git-ignored. No
  calc-math change.

- **Structured load-case IDs** (Phase D Step D1, decision D-1). Every
  delivered load case now carries a stable, traceable `case_id`
  (`"<component>-<seq>"`, e.g. `W-01`, `HT-03`, `VT-02`, `F-04`, `EM-01`,
  `LG-05`) that replaces `report.py`'s old render-time, per-module, unstable
  `LC{idx}`. New `CaseRef` dataclass (`farloads/models.py`) and
  `farloads/case_ids.py` (the six-prefix taxonomy + a per-call-site
  `CaseIdAllocator`, no shared/global state). Minted once by the module that
  first names a physical condition (`select.py`, `engine.py`, `landing.py`,
  `aileron.py`, `flap.py`, `tab.py`, `one_engine_out.py`,
  `wing_inertia.py`/`net_loads.py`) and copied downstream by consumers
  (`taildist.py`, `body_loads.py`) rather than re-minted. `report.py`'s
  load-case tables gain `Component`/`Condition`/`CG`/`Speed`/`Altitude`
  columns; `export/sbeam_bridge.py` stamps the case id into every sbeam
  `FORCE`/`MOMENT` card comment and adds a new case-index CSV
  (`case_index_csv_from`/`case_index_rows`), surfaced on the Export page.
  `SCHEMA_VERSION` 15 → 16 (additive; older files load with `case_ref = None`,
  back-filled on the next compute). No calc-math change — the Appendix A/B
  oracles pass unmodified. **Accepted, not closed:** `select_wing`'s own wing
  `CriticalCondition` list and `WingMassInput.cases` (which drives
  WINGINER/NETLOADS) remain two independent case lists sharing the `W` prefix
  in disjoint numeric bands (not the same case object); same gap between
  `one_engine_out` and `select_vtail`'s vertical-tail sequence — tracked as a
  deferred refinement. See `docs/30_future/00_backlog.md` → history for the
  full design and the banding-collision bug caught during implementation.

### Changed

- `SCHEMA_VERSION` 32 → **33** for the new `safety_factor` field. Migration is
  lenient: a file predating it simply lacks the key and takes
  `ULTIMATE_FACTOR`, so every reloaded project exports identical numbers. The
  bundled `examples/*.project.json` are restamped.

- **Body-load moment-closure caveat on every deliverable (M3 pre-release
  obligation for M4-1).** The Ch 15 fuselage distribution applies a *single*
  vertical wing reaction, so it closes ΣFz but **not** ΣM — the terminal `Myy` is
  non-zero and the bending carries a net pitching couple (the Ref 1 p103
  front/rear-spar two-reaction solve is open work, backlog M4-1). The limitation
  is now single-sourced as `body_loads.CLOSURE_CAVEAT` and stamped onto every
  body-load deliverable: wrapped `$ CAVEAT:` comment lines opening each case
  block in `fuselage_loads.bdf` (`sbeam_bridge.body_force_moment_cards`), an
  `st.warning` on the **Net Fuselage Loads** page, and a caption under the
  **Export** page's Fuselage row. `tests/test_body_loads.py::
  test_body_bdf_carries_closure_caveat` locks it (one block per case, text
  matches the constant, comment lines ≤ 72 cols). En route, corrected the
  **overstated** Net Fuselage Loads caption — it claimed "Validated by
  equilibrium closure" on the exact axis that is known-open. No calc, schema or
  oracle change (`SCHEMA_VERSION` stays 32); the CSV export shape is untouched
  (`Case,GID,X,Fz,Sz,Myy`), so no parser breaks.

- **GUI editors for the blocking uncovered fields (M2R-5).** Two inputs that
  drove the results but had no on-screen knob (JSON-only) are now editable in the
  app. **(a) Landing CG cases** — a fixed 3-row `st.data_editor` on **Landing
  Loads** for `landing.cg_cases` (name / weight / Xcg / Zcg), seeded from the
  **WTENV structural CG envelope** (fwd/aft stations via the newly-public
  `validation.wtenv_cg_limits`, with the gross / fwd-regardless weights and the
  itemized-loading waterline) and editable from there; the page's hard "provide
  WTONECG or edit the JSON" gate is replaced by an in-place info until the three
  positive-weight rows are applied. **(b) SELECT search inputs** — a form on the
  **Critical Loads** tab for `SelectInput.full_down_aileron_deg` /
  `basic_airfoil_cm` / `wing_weight_lb` (each with `help=`), which drive the
  23.349(b) steady-roll wing-torsion score and the critical-fuselage wing weight
  and previously defaulted silently (0 / 0 / 0.09·MTOW). Both persist only on
  **Apply** (a plain render leaves the project byte-for-byte unchanged — the M2R-4
  guard, now covering `landing_loads` too). No calc or schema change
  (`SCHEMA_VERSION` stays 32); the two slices already round-trip in `io.py`. En
  route, promoted `validation._wtenv_cg_limits` → public `wtenv_cg_limits` and
  re-pointed the existing `app/views/weight_mass.py` importer (removes one
  `app/`-imports-`farloads`-underscore violation, per M4-12).

- **`project.json` data dictionary + GUI user guide (M2-11).** Two new docs.
  `docs/10_standard/DATA_DICTIONARY.md` is **generated** by
  `docs/generate_data_dict.py`, which introspects the `farloads.models` Project
  input slices (type/default from `dataclasses`/`typing.get_type_hints`, units
  from inline comments) and emits a per-slice map (owning page + consuming
  modules, at slice granularity from `workflow.py` + a source scan) plus a field
  table per input dataclass and an enums appendix; result slices are out of
  scope. `docs/10_standard/GUI_USER_GUIDE.md` is a task-oriented walkthrough —
  workflow phases, the single-source seed chain, LIMIT-vs-ULTIMATE reading rules,
  and an end-to-end `ga6_normal` example with four hand-checkable numbers.
  `tests/test_data_dictionary.py` guards the generated doc against drift.
- **Operating-limitation implications on the Design Speeds page (M2-10).** The
  structural design speeds (Subpart C) now explain and surface the **operating
  limitations / cockpit placards** they bound (Subpart G) — advisory only, no
  loads-math change. Three tiers: **Explain** (a constraint-ladder expander with
  citations); **Derive** (`operational_placards`/`operational_implications` in
  `structural_speeds.py` — a read-only panel showing **both** placard families:
  recip yellow-arc VNE=0.9·VD, VNO=min(VC, 0.89·VNE), MNE=0.9·MD and turbine
  VMO=VC/MMO=MC, plus VFE=VF); **Constrain** (optional operational targets
  `no_yellow_arc` + `target_vne`/`vno`/`vmo`/`mmo`/`vfe` on `StructuralSpeedsInput`,
  `SCHEMA_VERSION` 30 → 31 with lenient migration). Targets invert the ladder into
  the required design minima (`operational_target_checks`) and **warn-only** on
  infeasibility — never mutating a design speed or load; infeasible targets also
  surface on the dashboard via `validation._check_operational_targets`. Sources:
  new `reference/14CFR_operating_limitations.md` (14 CFR 23.1505/23.1511, web-
  verified; Ref 1 p47; 23.335(b)(4) margin). GA6 placards unit-tested (VNE 191.25,
  VNO 170, MNE 0.363, VMO 170, MMO 0.3226, VFE 105.5).

- **Persistence verification + guards (M2-7, Step G7).** Verified decision G-3: every
  input-bearing value lives on a `Project` slice `io.py` round-trips, with no input data
  stranded in `st.session_state`. New `tests/test_persistence.py`: (a) every example is a
  **save→reload no-op**; (b) a **field-coverage completeness guard** — each input dataclass
  is filled with all-non-default sentinels (recursively) and round-tripped through its `io`
  pair, so a field added later without `io` wiring fails the build (intentionally-derived
  fields sit in a rename-guarded `DERIVED_NOT_PERSISTED` allowlist); (c) a **session_state
  audit** — a static scan of `app/` asserting every `st.session_state[...] =` write uses an
  allow-listed UI key (`project`/`unit_system`/`_saved_project_snapshot`/`engine_sel` + the
  Project Editor scratchpad), so a new key that could smuggle input data outside `project`
  trips a review. The audit found the acceptance already met (the D5/G-series/M2-6
  single-source work); the Streamlit `key=`+`value=` display-freshness footgun is deferred
  to the L-8 long-tail batch.

- **Renamed the project `FAR23LOADS`/`farloads` → `sloads`; split `models.py` into a
  `models/` package (M3-1).** The Python package/import, CLI command
  (`sloads = "cli:main"`), GUI title/brand, README H1, doc-set titles, and
  `pyproject` name are now **`sloads`** (lowercase); the sbeam export deck headers and
  `export/` axis references are **`SLOADS`** (with `tests/test_workbook.py` updated in
  lockstep). The 1,862-line `models.py` monolith was split AST-deterministically
  (verified byte-identical) into `sloads/models/{enums,inputs,results,project}.py` with
  a re-exporting `__init__.py`, so every prior `from sloads.models import X` form
  resolves unchanged. **No calc/oracle/schema change** — `SCHEMA_VERSION` stays 32;
  registry names, JSON schema keys and session-state keys are untouched, so saved
  project files load as-is. The "FAR 23 LOADS" mark survives only as
  McMaster/DARcorporation attribution (disclaimer retained in README + GUI About); the
  repo folder name and historical CHANGELOG/`40_history` entries are intentionally left
  as-is. Full suite green (483 passed); ruff clean; smoke test exit 0.
- **Geometry & power single-source cleanup (M2-6, Step G6c).** Closed the last of the
  softer geometry/power double-entry the G6 audit surfaced. **Wing:**
  `FlightLoadsInput.mac`/`wing_area_sqft`/`xw`/`zw`, `WingMassInput.dihedral_deg`/
  `wrp_waterline` and `LandingInput.wing_area_sqft` are now **derived from
  `Project.geometry`** — MAC/S/XW from the WINGGEOM wing surface (`XW = XLEMAC +
  0.25·MAC`), ZW from the parametric wing (`root_waterline_z + Y_MAC·tan(dihedral)`),
  dihedral/wrp from the parametric wing — via a shared
  `farloads.derived_geometry.sync_geometry_derived` every consuming module calls (the
  `landing._sync_gear_from_geometry` pattern). They are no longer persisted and the GUI
  shows them read-only, so there is no independently-editable copy; a project with no
  wing geometry keeps its slice values (the STRSPEED fallback). **Fuselage:** the
  `GeometryInput.fuselage` outline is the sole editable shape source; the
  `LayoutInput.fuselage_length`/`_width`/`_height` scalars are a derived read-only
  summary of it (length = station span, width/height = max section), not persisted.
  **Power:** `WeightEstimationInput.max_continuous_hp` is single-sourced from
  `sum(engines[].max_cont_hp)` (new `resolve_max_continuous_hp`), overridable behind the
  new `override_max_continuous_hp` toggle; the per-engine vs combined-total and
  takeoff vs max-continuous concepts stay distinct. `SCHEMA_VERSION` 29 → 30 (lenient:
  older files' stored copies are read but ignored/re-derived, the fuselage outline is
  defaulted from the length/width/height scalars when absent, `override` defaults False).
  All six shipped examples migrated (GA6 gained a parametric wing slice; the derived
  values fold in within Appendix A ±0.1% — ZW 87.725 → 87.734); every example is a
  save→reload no-op. Calc unchanged; Appendix A oracles bit-for-bit.

- **Navigation: whole workflow visible + cross-page links (M2-2, review
  G3+G6).** (a) `st.navigation(..., expanded=True)` in `app/Home.py` so all eight
  sidebar groups (Start + the six analysis phases, **including Export**) stay open
  on first run instead of collapsing phases 3–6 behind a "View 10 more" expander
  (G3). (b) A workflow-derived link helper — `components.workflow_page_link(key)`
  and `components.gate(message, *keys)` — that derives every link's target path
  *and* label from `farloads.workflow` (the single source of navigation truth), so
  a page rename re-labels every link automatically and hand-typed stale page names
  can't recur. (c) The **Project Dashboard** checklist rows are now `st.page_link`s
  (status emoji as icon, summary/status/BAS in the tooltip); blocked steps stay
  navigable so the user lands on the page and reads its own now-linked gating
  message. (d) Every "define X on the Y page first" gate across 14 views now
  renders a page link to the page that unblocks it, and the **stale page names**
  from the G1 merge are fixed — "Wing Geometry" / "Configuration & Layout" →
  **Geometry**, "Flight Envelope" → **Flight Envelope (V-n)**. The helper degrades
  to a non-clickable label when run outside `st.navigation` (e.g. AppTest), so
  standalone rendering never breaks. Bumped the `streamlit` floor to `>=1.36`
  (`st.navigation(expanded=…)`). New `tests/test_page_links.py` asserts every link
  key resolves to a real workflow step with a matching view file. GUI-only; no
  calc/schema change (424 tests green, `ruff` clean).

- **AIRLOAD4 Mach threshold 0.4 verified and documented (M1-8).** The design-Mach
  gate that auto-selects the swept/high-Mach AIRLOAD4 branch (`_AIRLOAD4_MACH = 0.4`)
  was flagged against the FAA User's Guide's **0.5** (§9.1, §10.1). Verification
  confirmed **0.4 is sourced to Ref 1** (Ch 12: *"AIRLOAD4.BAS for Mach >.4 or
  sweepback > 15 degrees"*, `FAR23Loads_Code.pdf`); the User's Guide is the outlier
  and no `.BAS` oracle pins the value (selection was a human-operator choice, not a
  hardcoded comparison). Ref 1's **0.4** is retained — higher-authority source, the
  conservative gate, and nearly moot for output since compressibility enters via
  FLTLOADS' upstream Glauert `CL`. **No code value change**; a source-conflict note
  was added to `airloads.py`, `docs/20_theory/00_theory_sources.md` and
  `docs/10_standard/PROGRAM_SPEC.md`.

- **23.427(a) unsymmetrical tail: restore the full candidate set (M1-4, review T6;
  approved oracle deviation).** `select_htail_unsymmetrical` no longer filters the
  **unchecked** maneuvers out of the 23.427 search. `SELECT.BAS` lines 6070–6175
  (Ref 1 Appendix C p440–441) load the unchecked cases into the candidate array
  (`L(5)=U1CK`, `L(6)=U2CK`) and take the max over all 12 conditions; 23.427(a)
  applies the unsymmetrical distribution to "the loads prescribed in 23.421
  **through** 23.425", spanning the 23.423 unchecked case. The earlier exclusion
  (citing a "CAM 3.216" rationale) was an undocumented, non-conservative deviation.
  On the Appendix A GA6 the DN unchecked maneuver governs, so the unsymmetrical
  total moves from **−1111.8 → −1204.7** (RH −700.4, LH −504.3, 72%). The Appendix A
  sample output's −1111.8 (gust-governed) is a **stale printout from a superseded
  `SELECT.BAS` revision** — it is inconsistent with its own Appendix C listing, which
  the larger unchecked case (`U2CK` = −1397.835) would win. The listing + the CFR
  are authoritative. The governing condition carries a documented `note`;
  `CriticalCondition` gains a `note` field. `test_htail_gust_and_unsymmetrical_match_appendix_a`
  updated (manual's −1111.8 kept in a comment). Source:
  `reference/23_427_unsymmetrical_candidate_set.md`; register in `CLAUDE.md`.

- **Single-source stall from CLmax (M1-1b; closes old 2-13(b)).** Stall speeds are
  no longer hand-entered scalars. The maximum lift coefficients live once on
  `AeroCoefficientsInput` — `clmax_clean` / `clmax_clean_neg` / `clmax_flap` — and
  STRSPEED, `flap` and `one_engine_out` **derive** VS/VSF from them at the design
  weight (`constants.stall_speed_kt`: `VS = √(295·(W/S)/CLmax)`, User's Guide p7-5),
  which in turn set VA and VF. The `StructuralSpeedsInput.stall_clean_kt` /
  `stall_flap_kt` fields are removed; CLmax is entered on the **Aerodynamic Data**
  page, which now precedes **Structural Speeds** in the workflow (STRSPEED
  `requires=("aero_coeffs",)`). The FLTLOADS balance clamp `AeroCoeffSet.stall_cl`
  stays authored per config (it can differ from the stall-speed CLmax by the 0.9
  stall-margin factor — e.g. Appendix A ga6: `clmax_clean` 1.4068 from the printed
  VS vs FLTLOADS `stall_cl` 1.41); `AeroCoefficientsInput.__post_init__` fills either
  representation from the other only when one is missing, never overwriting. All
  Appendix-A oracles (STRSPEED VA/VF and the FLTLOADS/SELECT envelope) are preserved
  exactly. `SCHEMA_VERSION` → 29; example projects updated.

- **Single-source landing-gear geometry (Phase G, Step G6b).** The tricycle-gear
  geometry native to LANDLOAD — main/nose axle `(X, Z)` at the three strut states,
  rolling radius, strut type, and the main-wheel tread — is now entered **once**, on
  the Geometry page, in a new `GeometryInput.landing_gear` (`LandingGearGeometry`).
  It drives both the three-view (strut + wheels, ground line) and the ground-load
  analysis: `landing.build_landing` syncs it onto `Project.landing` before the
  reaction solve, so the LANDLOAD math is unchanged. The duplicated coarse
  `LayoutInput` gear fields (`main_gear_x`/`nose_gear_x`/`track`/`gear_height`) are
  retired — the three-view and the tip-back/overturn/prop-clearance estimate now
  **derive** the station/track/height from the native axle geometry (ground = static
  axle `Z` − rolling radius), so a stored coarse height that disagreed with the axles
  no longer diverges silently. The Landing Loads page drops its gear/tread widgets
  (reads the geometry read-only), keeping only the non-geometry LANDLOAD inputs. `io`
  migrates a pre-v28 file's top-level `landing` gear (and legacy `LayoutInput` gear
  fields) into `geometry.landing_gear`; `SCHEMA_VERSION` 27 → 28. **Appendix A gear
  reactions unchanged bit-for-bit** (`tests/test_landing_gear_geometry.py`,
  `tests/test_landing.py`).
- **Single-source empennage & control-surface geometry (Phase G, Step G6).** The
  horizontal-/vertical-tail + **elevator/rudder** geometry is now entered **once**,
  on the Geometry page, and drives both the three-view and the rational tail-load
  analysis. A new `GeometryInput.empennage` (`EmpennageInput{htail, vtail}`) is the
  single stored home; `Project.tail_loads`/`.vtail_loads` become **properties**
  proxying to it (so SELECT/TAILDIST/BALLOADS/one-engine-out read them unchanged),
  and the duplicated `LayoutInput` h-/v-tail area/span/arm fields are retired (the
  three-view and the tail-volume static-margin estimate now read the analysis-native
  values; the tail arm is derived from `xt25`/`xv25` minus the 25% wing-MAC station,
  not stored twice). The **three-view draws the elevator and rudder** as the aft
  `Saft/S` chord band, and the Geometry page gains an *Empennage & control surfaces*
  editor (the elevator/rudder geometry's first GUI home — previously JSON-only); the
  Tail Loads page becomes analysis-only (reads the geometry read-only). `io` migrates
  a pre-v27 file's top-level `tail_loads`/`vtail_loads` (and the retired `LayoutInput`
  tail fields) into `geometry.empennage`; `SCHEMA_VERSION` 26 → 27. The derived
  slices are byte-identical, so the **Appendix A SELECT tail-load oracles are
  unchanged** (`tests/test_empennage.py`, `tests/test_select.py`).

- **Phase-1 page consolidation — Develop V-n diagram (Phase G, Step G3).** The
  *Develop V-n diagram* section collapses from ten nav pages to five, using
  `st.tabs` where a page gathers formerly-separate pages. New **Weight & Mass
  Properties** page (`app/views/weight_mass.py`) with tabs *Estimate* (WTESTIMA) ·
  *Weight, CG & Inertia* (WTONECG) · *Payload Cases* · *Weight / CG Envelope*
  (WTENV) — the single owner of all weight/mass data. **Structural Speeds** gains a
  *Design Speeds* / *Speed–Altitude Envelope* (MACHLIM) tab split; **Flight Envelope
  (V-n)** gains a *V-n diagram* / *Critical Loads (SELECT)* tab split (the FLTLOADS
  balance inputs stay on the page, shared by both tabs). Six view files are deleted
  and folded (`weight_estimate`, `weight_cg_inertia`, `payload_cases`,
  `weight_envelope`, `mach_limit`, `critical_loads`); `workflow.FOLDED_MODULES` gains
  `weight_estimate`, `weight_envelope`, `mach_limit`, `select` (each still a
  registered/tested calc module, now without its own nav step). **No calc, schema,
  or oracle change** — the folded modules and `Project` slices are untouched; only
  which page edits a slice moved. Cross-page captions/warnings updated to the new tab
  locations.
- **Workflow-aligned navigation re-sequence (Phase G, Step G2).** The GUI sidebar
  is re-grouped from the historical Phase-D sections into the FAR 23 analysis flow
  (decision G-4): an un-numbered **Start** app-shell group (Project Dashboard, JSON
  Editor) above the six numbered analysis phases **1 · Develop V-n diagram → 2 ·
  Flight loads → 3 · Other loads → 4 · Landing loads → 5 · Load-case plotting → 6 ·
  Export**. The old **Airplane**/**Envelopes & Critical Conditions** split dissolves
  — geometry, all weight/CG pages, both speed pages, aero data, and V-n + SELECT now
  sit together under *Develop V-n diagram*; *Landing Loads* moves after the
  control-surface/engine *Other loads* group. `farloads/workflow.py` (`PHASES`
  renamed, `STEPS` reordered/reassigned) and `app/Home.py` (`_PHASE_LABEL`) carry the
  change; the Dashboard caption follows. **Grouping/labels only — no page bodies, no
  calc, no schema change** (the per-page consolidation into §4's 1a–1e sub-steps is
  the separate Step G3). The nav-drift guard test stays green.
- **Geometry single source of truth, incl. fuselage (Phase G, Step G1).** The two
  geometry-owning pages — Configuration & Layout (parametric `LayoutInput`) and
  Wing / Surface Geometry (WINGGEOM planforms) — are merged into **one Geometry
  page**, and their two project slices are **unified into one** (`SCHEMA_VERSION`
  **24 → 25**): the parametric layout (formerly the top-level `Project.configuration`)
  and a new **fuselage outline** move onto `GeometryInput` as `.parametric` and
  `.fuselage`, alongside the unchanged `.surfaces`. The oracle-locked `.surfaces`
  consumers (AIRLOADS, WINGINER, NETLOADS, …) are untouched. The **fuselage is now a
  real geometry entity** — a station-area table (`FuselageOutline`/`FuselageSection`,
  cross-section width/height vs. station) that drives the three-view body profile and
  seeds the future Step G4 pitching-moment estimator; older files default it from the
  `fuselage_length/width/height` scalars on load. Downstream pages (flight envelope,
  structural speeds, weight, tail/wing loads, aircraft comparison) read geometry
  **read-only** through the unified slice. `workflow.py` collapses to one **Geometry**
  step (the `wing_geometry` module is folded in via `FOLDED_MODULES`); legacy project
  files migrate on load (`io.py` folds the top-level `"configuration"` block onto
  `geometry.parametric`). **Appendix A/B oracles unchanged.** New tests:
  fuselage-outline default + round-trip (`test_configuration.py`, `test_io.py`) and
  the legacy-`configuration`→`geometry` migration (`test_io.py`).
- **Canonical display units — one unit per dimension (Phase G, Step G0).** The GUI
  now shows a single unit per physical dimension: **length → `in` (SI `mm`), area →
  `ft²` (SI `m²`)**. The geometry inputs that previously carried a different unit are
  renamed to canonical-unit field names and stored in canonical units
  (**`SCHEMA_VERSION` 23 → 24**): `TailLoadsInput.airplane_length_ft` and
  `VTailLoadsInput.{airplane_length_ft, wing_span_ft, vtail_mac_ft}` → `*_in` (×12);
  `LayoutInput.{h_tail_span_ft, v_tail_span_ft}` → `*_in` (×12);
  `TabSpec.area_sqin` → `area_sqft` (÷144). The redundant `length_ft`/`area_sqin`
  kinds are removed from `farloads/units.py` (`SI_PER_IMPERIAL`, `UNIT_LABELS`,
  `_KIND_FACTORS`); `_PROJECT_FIELD_KIND` maps the renamed keys. **Calc results are
  unchanged** — the original ft/in² math is restored internally, so the Appendix A/B
  oracles are untouched. Older project files migrate on load (`io.py`
  `_rename_legacy_units`); the bundled `examples/*.json` (older schema versions) load
  via that path. New guardrail tests: one-label-per-dimension (`test_units.py`) and
  legacy-key migration (`test_io.py`).

- **Fleet comparison moved to its own page (Phase F, Step F2).** The shared
  `app/components.render_fleet_comparison` helper (its private `_fleet_points` /
  `_fleet_readout`) and the fleet block on **Configuration & Layout** and **Weight
  Estimate** are removed; the comparison now lives only on the new Aircraft
  Comparison page. `app/components.py` retains just the FAR 23 applicability banner.

- **Mach Limit page reworked into the Speed–Altitude Envelope (Phase E, Step E7).**
  MC, MD and the shoulder altitude are now read from the Structural Speeds `speeds`
  slice instead of being re-entered — only the max operating altitude and increment
  remain as inputs. The chart is now a transport-category-style speed–altitude
  flight-limits diagram: altitude on the y-axis, a **KEAS/KCAS/KTAS** selectable
  x-axis, a constant-Mach fan, and the design-speed boundary drawn EAS-limited below
  the shoulder and Mach-limited above it (VC/MC and VD/MD kink at the shoulder). The
  workflow step is retitled "Speed–Altitude Envelope". GUI + one new pure helper; no
  calc-math or oracle change (`mach_limit_lines` untouched).

- **V-n diagram consolidated onto the Flight Envelope page (Phase E, Step E6).**
  The suite had two V-n diagrams: the continuous LIMIT textbook envelope on the
  **Structural Speeds** page (Step E3) and the rigorous, Mach-corrected balanced
  corner points on the **Flight Envelope (V-n)** page — redundant. The continuous
  LIMIT envelope (from the pure `farloads/vn_diagram.py` helper) is now drawn as a
  grey backdrop on the Flight Envelope page, behind the rigorous balanced markers,
  so the envelope visibly *bounds* them in a single figure. It is rebuilt there from
  `project.speeds` (already a required slice) via `design_speed_values` — no new
  inputs. The Structural Speeds page now shows only its numeric design-speed tables
  plus a pointer to the Flight Envelope page. GUI-only; no calc math changed
  (`vn_diagram` and its tests are untouched).

- **Load-path robustness (Phase E, Step E5).** The three sidebar load actions
  (Open saved, Load example, Upload) now fail **gracefully**: a malformed or
  wrong-shape file shows an `st.error` ("Couldn't load …: …") instead of an
  uncaught traceback, matching the JSON Editor's behavior. Both the sidebar and the
  Project JSON Editor now run a **soft `SCHEMA_VERSION` check**: a file from a
  *newer* app version warns and still loads (unrecognized fields ignored); an
  *older* file is migrated in place (its field-presence migration already ran in
  `io.py`; the version stamp is bumped to the current `SCHEMA_VERSION`), surfaced as
  a brief toast in the sidebar / an info line in the editor. The classification is
  the new pure, unit-tested `farloads.io.schema_status(version) -> (status,
  message)` (no Streamlit). GUI-only: no schema change (`SCHEMA_VERSION` stays
  **22**) and no calc-math change — the Appendix A/B oracles are untouched (347
  tests pass, +4). Implements `GUI_design.md §10`.

- **Six-section GUI navigation restructure** (Phase D Step D2, regroup only).
  `farloads/workflow.py`'s four phases (Define/Analyze/Review/Export) are
  replaced with the six Phase-D sections: Start, Airplane, Envelopes &
  Critical Conditions, Analysis, Loads Plots, Export. `airloads` moves from
  Define into Analysis; `balanced_tail_verification` and `critical_loads` move
  alongside their related pages (Analysis and Envelopes & Critical Conditions
  respectively); `results_review` moves into Export (pre-export summary,
  alongside `export_report`). The dashboard is now a real `WorkflowStep`
  (`"dashboard"`, phase Start) instead of a Home.py special case, so
  `app/Home.py` builds every sidebar group — including Start — uniformly from
  `wf.by_phase()`; a section with no steps yet (`Loads Plots`, pending Step D7)
  is omitted from the sidebar rather than shown empty. No page merges, no
  calc-math or schema change — `requires`/`produces` on every step are
  unchanged; this is metadata + display only.

### Fixed

- **2026-07-23 review nits batch (M4-16).** (1) **[CRITICAL]**
  `docs/10_standard/GUI_design.md`'s "currently `SCHEMA_VERSION = …`" paragraph
  was stale for the **third** time (still 32 after the M4-7 bump to 33) — fixed,
  the migration-history list gains the `v33 M4-7 per-case safety_factor` row,
  and a new guard test
  (`tests/test_data_dictionary.py::test_gui_design_schema_line_current`) asserts
  the line matches `models.SCHEMA_VERSION`, making a fourth regression
  unmergeable. (2) `sbeam_bridge._sf()` is now typed (`Union` of the four
  distributed-load result types) and reads `safety_factor` directly — the
  `getattr` fallback only served hand-built doubles while masking a future
  attribute rename (every producer mints the field since M4-13). (3) The SF on
  deliverables renders as `SF=1.0`, not `SF=1` (`_sf_str` helper across the card
  `$` headers, closure comments and the four CSV `SF` columns). (4) `io.py`'s
  intra-package imports reordered alphabetically (`.constants` moved above the
  `.models` block).

- **Analysis-page LIMIT CSV downloads now carry their basis in the file
  (defect M4-15, 2026-07-23 review MINOR, contract).** The Wing Loads page's
  "Download net wing loads (CSV)" (and, found by the sweep, the Fuselage Loads
  CSV and the Loads Plots comparison CSV) shipped **LIMIT** station loads with
  no marker and a neutral filename — the on-page "(LIMIT)" caption did not
  travel with the file, violating the CLAUDE.md ultimate-deliverable contract.
  Now: the canonical station-row shapes (`net_loads.wing_load_rows`,
  `body_loads.body_load_rows`) append an in-band **`Basis = LIMIT`** column;
  every LIMIT download is filename-marked `*_LIMIT.csv` (wing, fuselage, loads
  plots, plus the already-column-marked tail-chordwise and one-engine-out
  files); the Loads Plots CSV `Field` strings gain the `, LIMIT` marker its
  plot axes already showed; and the Wing/Fuselage Loads pages add a
  side-by-side **ULTIMATE** download (`*_ULT.csv`, per-case `SF` column) routed
  through the existing `sbeam_bridge.span_load_csv` /
  `body_span_load_csv` renderers (user decision 2026-07-23: offer both). A new
  source-scan guard, `tests/test_ultimate_contract.py`, fails any future view
  that offers a load CSV with no basis marking and no ULTIMATE channel.

- **A corrupt persisted `safety_factor` can no longer crash or under-scale the
  export (defect M4-14, 2026-07-23 review MAJOR).** The five `io.py` readers
  added by M4-7 took `d.get("safety_factor", ULTIMATE_FACTOR)` unchecked, and
  the field is hand-editable (Project JSON Editor / the file itself):
  `"safety_factor": null` crashed `body_span_load_csv` with a `TypeError`
  (breaking the lenient-reader contract), and `0.5` silently **under-scaled**
  every exported card while still labelled ULTIMATE — including on the headless
  `cli.py --export-sbeam` path where no GUI warning can surface. The readers now
  coerce through one helper (`io._safety_factor`): anything non-numeric (null,
  string, bool, NaN/inf) **or outside the legal [1.0, 1.5] band** (14 CFR
  23.303; the factor is owned by the load-case definition — a case already at
  ultimate is 1.0, an agreed 23.302/25.302 failure-case factor lies between)
  falls back to the conservative `ULTIMATE_FACTOR` default. Companion
  advisories: a new `safety_factor_out_of_range` consistency warning
  (`validation._check_safety_factors`, rendered on the Export page) covers
  in-session values, and the Project JSON Editor scans the **raw** edited dict
  at Apply — the built project is already coerced, so only the raw dict can
  show what was typed — and warns that the value was reset. The shared
  predicate is the new public `validation.safety_factor_valid`. GA path
  unchanged (the fixture stays warning-free); covered by
  null/string/bool/NaN/0.5/negative/0.999/1.6 fixtures, legal-band round-trips
  at 1.0/1.25/1.5, and the exact null-then-export repro.

- **Wing and control-surface producers now mint their per-case safety factor
  once (defect M4-13, 2026-07-23 review MAJOR).** M4-7 threaded the factor for
  the tail and fuselage families only; `net_loads` (`WingLoadResult`) and
  `aileron`/`flap`/`tab` (`ControlSurfaceLoadResult`) left their result slice
  **and** their rendered `ConditionResult` to default the field independently —
  two sources of truth that would let the report and the exported FORCE/MOMENT
  cards disagree at the first non-1.5 case. Each of the four modules now mints
  the factor once in `build_*` (`net_loads` sets it on the air, inertia and net
  families of the same case; aileron's up/down throws share one mint) and
  `run()` copies it from the built result — the taildist/body pattern, closing
  the `PROJECT_GUIDE.md` §5 "minted once, copied unchanged" invariant. Aileron's
  `ConditionResult` also gains its previously missing `case_ref`, and its
  rendered pressures/loads now come from the same result records the export
  consumes. **Every number is unchanged** (all factors are 1.5); locked by an
  agreement test plus a mutation test that forces a 1.25 mint through each
  `run()` (`tests/test_sbeam_bridge.py`).

- **The sbeam export now scales by each case's own safety factor (defect M4-7).**
  `export/sbeam_bridge` hardcoded a flat `_SF = 1.5` at every scaling site and
  ignored `ConditionResult.safety_factor` — latent, because the four
  distributed-load result types it consumes carried **no** factor at all, so a
  case already at ultimate (`SF = 1.0`, per the ultimate-load contract) would have
  been multiplied by 1.5 a second time, and a future 14 CFR 23.302 / Appendix K
  probability-based factor could never reach the exported cards. `safety_factor`
  (default `constants.ULTIMATE_FACTOR` = 1.5) is now a field on `CriticalCondition`,
  `WingLoadResult`, `BodyLoadResult`, `TailChordResult` and
  `ControlSurfaceLoadResult`; TAILDIST and the fuselage net distribution copy it
  from the governing `CriticalCondition` (and TAILDIST's rendered `ConditionResult`
  carries the same value, so the report and the export can never disagree); the
  bridge resolves it per result via `_sf()`. **Every number is unchanged** — all
  defaults are 1.5 — verified by diffing the GA wing span CSV and FORCE/MOMENT
  cards before and after.
- The `$ Loads are ULTIMATE (limit x 1.5)` card comment, previously a hardcoded
  string on all four component families, now states the factor actually applied
  (`limit x SF=<sf>`).
- `io._critical_condition_from_dict` silently dropped `CriticalCondition.note` on
  reload, losing the approved-correction provenance a condition carries; it now
  round-trips.

- **`MissingInputError` — genuine calc defects no longer vanish from run-all (M2R-8).**
  `run_all_modules` caught *every* `ValueError`, so a real defect in a module was
  indistinguishable from "its inputs aren't entered" and silently disappeared from
  run-all/export. Added `MissingInputError(ValueError)` (`models.py`), raised at every
  module's input-absence guards (slice is `None`, a required upstream result/geometry/
  aero slice is absent, or a required input list is empty), and narrowed
  `run_all_modules` to catch **only** that — a plain `ValueError` (invalid domain input
  such as `<2` cylinders / non-positive area / mismatched element counts, or a genuine
  defect) now propagates and is visible. `MissingInputError` subclasses `ValueError`,
  so every existing `except ValueError` (GUI pages, CLI) still catches it; only the
  registry narrowed. The error-handling contract (`docs/10_standard/00_program_overview.md`)
  is updated to match. **While in the area:** `select.build_critical` now builds the V-n
  envelope **once** and threads it into all seven `select_*` searches (via a new
  `envelope=` parameter and the single `_envelope` fallback site) instead of each
  rebuilding it — up to a 7× saving when no envelope is persisted (the test suite runs
  noticeably faster). No calc/oracle change; the SELECT figures are unchanged.

- **`io.py` tolerant readers — unknown fields no longer crash load (M2R-7).** A
  project file carrying one field this app version doesn't recognize (saved by a
  newer or older build, or hand-edited) crashed on load with e.g.
  `MassItem.__init__() got an unexpected keyword argument …`, despite
  `schema_status()` promising "unrecognized fields are ignored". Every `*_from_dict`
  now routes its `cls(**d)` splat through one shared `_filtered(cls, d)` helper that
  drops keys not belonging to the target dataclass — the ~21 raw splats
  (`MassItem`, `EngineInput`, `WeightEnvelopeInput`, `CgCase`, `MachLimitInput`,
  `StructuralSpeedsInput`, `LoadValue`, `VnPoint`, `TailBalanceLoad`, `MassCase`,
  `FuselageStation`, the wing/body/tail/control station-load families, `CaseRef`, …)
  plus the pre-existing ad-hoc filter comprehensions all share it. Additive
  forward-compat: known fields load, unknown ones are ignored, missing ones take
  their defaults. Tests poison **every** slice of `ga6_normal` (and the result
  slices it lacks — envelope/mass/loads/one_engine_out, with nested VnPoint/CaseRef/
  LoadValue/station objects) with an unknown key and assert load succeeds and
  re-serializes identically. No schema change; the full migration-chain overhaul
  stays M4-10.

- **Geometry Apply validates before persisting (M2R-6).** The **Geometry** page's
  sidebar *Apply geometry* used to store whatever was typed — including an invalid
  wing (e.g. Area S = 0) — which then crashed `configuration_properties` in the page
  body and hit `st.stop()`, blanking the *unrelated* empennage / landing-gear /
  fuselage-outline / surfaces forms further down. Apply now validates the candidate
  `LayoutInput` first (`_layout_errors`: positive area, aspect ratio and taper λ) and,
  when invalid, rejects the Apply with a targeted message while keeping the last valid
  layout — so the rest of the page stays alive. GUI-only; no calc or schema change.

- **Kill the last on-render `Project` mutation (M2R-4).** Opening the **Landing
  Loads** page no longer flips 🟠 *Unsaved changes*: `landing.build_landing()`
  wrote gear geometry, a derived gross-weight default, and the LGFACTOR result
  back onto `Project.landing` on every render, so merely visiting the page dirtied
  the project and `run()` was impure in the calc layer. `build_landing`/`run` are
  now **pure** — the gear geometry (from the single-source
  `geometry.landing_gear`) and the gross-weight default are resolved onto a local
  *effective* input copy via `dataclasses.replace` (`_effective_gear_input`),
  nothing is written to `Project`. The airplane load factor N is returned on
  `LoadFactorResult.airplane_load_factor` (already displayed by the view); the
  redundant write-back `LandingInput.n` field is removed. **Schema:**
  `SCHEMA_VERSION` 31 → **32**; migration is lenient (the tolerant
  `landing_from_dict` ignores an older file's `"n"` key). Added a
  render-leaves-project-unchanged test (the exact `_has_unsaved_changes`
  predicate); the Appendix-A ground-load oracle is byte-identical (the math runs
  on an identical effective input).

- **Ship working examples (M2R-3).** Bundled examples no longer dead-end a
  first-time user with a red error on Fuselage Loads or Landing Loads. Authored
  five examples to a clean end-to-end run (all six workflow phases): added
  `fuselage_mass` to `ga6_normal` / `cessna_210`; a 3rd landing `cg_case` to
  `concept_regional_jet`; and `fuselage_mass` + a `landing` slice (3 CG cases) +
  `geometry.landing_gear` to `dhc8_dash8` / `atr42_100`. Station masses and CG
  cases are derived from each file's own weight items / wing MAC / weight
  envelope. `concept_heavy` is intentionally kept as the minimal concept-core
  demo (V-n → Flight Envelope only) and documented as such in the README and GUI
  user guide. Data-only — no calc or schema change (`SCHEMA_VERSION` stays 31);
  three fixture-coupled tests updated for the completed state.

- **`scripts/smoke_test.sh` portability (M2-9).** The release smoke test hardcoded
  `$ROOT_DIR/.venv/bin/{python,streamlit,farloads}` and failed on any layout without a
  project-local `.venv` (conda, `pyenv`, system, or a differently-named venv). It now
  resolves a single interpreter — explicit `PYTHON` override → `.venv` when present →
  `python3`/`python` on PATH — and invokes tooling through it (`"$PYTHON" -m streamlit run`,
  `"$PYTHON" cli.py engine`); the three-way `-x` guard becomes one usable-interpreter check
  plus an `import streamlit, farloads` probe. Script-only; no calc/schema/module change.

- **Landing CG cases: require three explicit distinct loadings + concept 23.473(g)
  floor (M2-8, review — landing minor).** `landing._cg_cases` previously auto-derived
  the fwd/aft max-landing pair from the **single heaviest** `Project.mass` case, so
  both max-landing corners were byte-for-byte identical — a **degenerate** fwd/aft
  distinction that under-predicted the nose-gear and braked-roll reactions (their
  `AP/BP/CP` lever arms turn on `xcg`) whenever a project leaned on the fallback;
  UG fig 18.2 uses three genuinely distinct loadings. LANDLOAD now **requires**
  `landing.cg_cases` (three distinct entries) and raises a clear error when it is
  empty rather than silently building the degenerate pair; the WTENV structural
  fwd/aft CG limits (`validation._wtenv_cg_limits`) are the intended source. Added a
  **concept-mode-only, warn-only** 23.473(g) floor note on the LGFACTOR condition when
  `N < 2.67` or `NLG < 2.0`; the computed `N`/`NLG` are unchanged, so the Appendix-A
  oracle (3.0951 / 2.4281, both above the floors) is untouched. All six shipped
  examples already carry explicit `cg_cases`, so none regress. New tests in
  `tests/test_landing.py` (missing-`cg_cases` raise; the floor note present in concept
  mode and absent in FAR23). Calc-local; no schema change (457 tests green, `ruff` clean).

- **Aircraft Comparison: subject geometry from the wing surface + a Develop-phase
  link (M2-5, review G7).** The comparison **subject** read wing geometry only from
  `geometry.parametric` (the `LayoutInput`), so of the six shipped examples only
  `concept_regional_jet` (the one with a parametric layout) showed a wing area,
  aspect ratio or span — every other example printed "—" for W/S, span and AR
  because they carry `geometry.surfaces` (WINGGEOM planforms) instead. Added a wing-
  surface fallback via `wing_geometry.surface_properties(geometry.by_name("wing"))`
  (the same pattern the Flight Envelope page uses): wing **area** priority is now
  `parametric → WINGGEOM surface → speeds.wing_area_sqft`; **aspect ratio** and
  **span** fall back `parametric → surface`; and `Subject.wingspan_ft` is populated
  directly from the surface span (rather than back-derived from √(AR·area)). Every
  shipped example now places fully on the fleet scatters (e.g. GA-6 recovers AR 6.095
  / span 33.5 ft from its wing planform). The page **stays in the Export phase**
  (unchanged `workflow.py` order); a workflow-derived `page_link` on the **Weight &
  Mass Properties** page now points to it so the fleet check is reachable at
  definition time. Presentation-only — the reference fleet is never a FAR input, so
  no calc/oracle/schema change. Extended `tests/test_aircraft_comparison.py`.
- **Governing-loads tables now render ULTIMATE with units + SF (M2-4, review
  G5).** The "Governing loads (SELECT)" tables on **Results Review** and the
  **Flight Envelope → Critical Loads** tab hand-formatted each cell as
  `round(lv.value, 2)` — dropping `LoadValue.units`, the mandatory `-ULT` marker
  and the safety factor, printing literal `None` in the sparse cells where
  components carry different label sets, and (the substantive bug) **never applying
  the limit→ultimate factor** — so both consolidation surfaces were showing
  unmarked LIMIT loads as if they were the deliverable, violating the
  ultimate-output contract. Both tables now render through one shared
  `report.governing_loads_table(conditions, system, sf)` helper built on the
  existing `report.py` ultimate boundary (promoted to the public wrappers
  `ultimate_units` / `to_ultimate`): load columns scale by the SF and carry `-ULT`
  in the header (`lbs-ULT`, `ft-lb-ULT`; SI `N-ULT`, `Nm-ULT`); dimensionless/speed
  columns (n, CL, V) pass through unscaled and unmarked; a trailing `SF` column
  states the factor (flat 1.5 per 14 CFR 23.303 — the per-case carrier on
  `CriticalCondition` is deferred to M4-8); and absent cells render `"—"` (no
  `None`/NaN). The two views can no longer diverge (same helper). The duplicated
  `_display_loads` in both views is deleted in favor of the shared one. Render-only:
  no calc/oracle/model/schema change (the calc still emits LIMIT; Appendix A
  oracles untouched). New `tests/test_results_review.py`.
- **"Unsaved changes" no longer trips on a plain page visit (M2-3, review G4).**
  `flight_envelope.py` and `structural_speeds.py` auto-seeded derived slices on
  every render (`flight_loads`; `speeds.mach_limit`), so merely visiting them
  dirtied the project and fired the discard-confirm dialog spuriously — violating
  the app's own "Form + Apply, merge not replace" convention. Both now persist
  **only on an explicit Apply** (`st.form_submit_button`): the FLTLOADS geometry
  and the MACHLIM altitude inputs live in `st.form`s, and the live V-n / Mach-limit
  diagrams compute from an in-memory value (Flight Envelope uses a shallow-copy
  *probe* project carrying the effective input) without mutating the saved project.
  The SELECT (Critical Loads) tab now persists **only** `selected_case_ids`, and
  **only when it changed**, onto the stored critical set — instead of reassigning
  the whole recomputed object every render. Consequence (intended): visiting these
  pages no longer seeds downstream slices; the engineer clicks Apply once, and the
  existing downstream gates now correctly mean "hit Apply". New
  `tests/test_dirty_flag.py` drives both views via `AppTest` and asserts a
  no-interaction render leaves `project_to_dict` byte-for-byte unchanged for every
  example, plus that Apply *does* persist. No calc/oracle/schema change (438 tests
  green).

- **Loads Plots page now recomputes from the project (M2-1).** The Load-case
  plotting page read `Project.loads`, a result slice **no code path ever
  constructs** — so it was permanently empty behind an unsatisfiable "visit the
  Analysis pages first" message. It now recomputes the wing/fuselage/tail/
  control-surface distributions live from the inputs (`build_net_loads`,
  `build_body_loads`, `build_tail_chordwise`, `build_aileron`/`build_flap`/
  `build_tabs`) behind the same defensive wrapper the Export page uses, so the two
  pages can never diverge. Removed the matching dead `if project.loads is not
  None:` write-backs from the five Analysis views (fuselage/tail/aileron/flap/tab
  loads). GUI-only; no calc change (422 tests green).

- **Flap slipstream now uses takeoff power, not max-continuous (M1-9).**
  `flap._engine_power` preferred `max_cont_hp`; FAR 23.457(b) sizes the flaps-
  extended slipstream on **takeoff power** (Ref 1 p109; FAA User's Guide p14-2).
  The MAXHP preference is flipped to `takeoff_hp` (falling back to `max_cont_hp`
  only when takeoff power is unset), so the GA6 example pipeline now feeds 285 hp
  instead of 265. The Appendix A "Critical Flap Loads" oracle passes `maxhp=250`
  directly and is unaffected; the manual's 250 hp is a confirmed stale figure that
  matches neither GA6 engine rating. Docstring + `PROGRAM_SPEC.md`/theory-doc notes
  cite 23.457(b).

- **Ballast station rejected when it falls outside the fuselage (M1-11).**
  `weight_envelope`'s forward-regardless reference is selected by weight only, so on
  synthetic over-gross concept databases whose forward-loading vertices all sit
  *aft* of the forward-regardless limit the moment balance could land the ballast at
  a nonphysical station (e.g. `dhc8_dash8` → −112 in, forward of the nose datum).
  Every computed ballast station is now gated against a physical fore/aft fuselage
  station extent — an explicit `envelope.fuselage_nose_x`/`fuselage_tail_x` override,
  else the Step G1 fuselage outline, else the station-0 datum with an unbounded tail
  (only a station *ahead of the nose* is rejected). A station outside the extent
  emits the same `"(none — <reason>)"` marker as M1-7's other degeneracies. GA6
  oracle (158 lb @ 71.08) and the physical concept stations (`atr42_100` +112,
  `concept_regional_jet` +64, inside its [0, 1056] outline) are unchanged. Adds
  optional `fuselage_nose_x`/`fuselage_tail_x` to `WeightEnvelopeInput`. Datum-,
  outline-, and explicit-extent-branch tests in `test_weight_envelope.py`.

- **Aft-gross ballast reference no longer collapses to zero on over-gross
  loadings (M1-7, review T8).** `weight_envelope` used the *full* discretionary
  loading as the aft-gross ballast reference; when that full loading exceeded gross
  weight (`WB = gross − max_load < 0`) the case silently reported **0 lb ballast**
  — the twin/concept databases (`concept_regional_jet`, `atr42_100`). The aft-gross
  reference is now the **heaviest loading not exceeding gross** (mirroring the
  forward-regardless selection): unchanged on the GA6 (max load 3322 < gross 3400 →
  78 lb @ 108.4, oracle intact) but correct on over-gross databases. Degenerate
  references — an empty candidate set, a loading already at/above the target weight,
  or a heaviest ≤-gross loading already at/aft of the aft-CG limit — now emit an
  explicit `"(none — <reason>)"` marker row instead of silently dropping the
  structural point or printing a nonphysical moment-balance station. The manual's
  hand-rounded 103.7 aft-gross station stays a documented deviation (exact balance
  108.4 retained). Over-gross regression + marker tests in `test_weight_envelope.py`.

- **VC/VD speed coefficients clamp at W/S = 100 (M1-6, review T9).** The FAR
  23.335(a)/(b) minimum-speed coefficients Kc/Kd are tabulated only to a wing
  loading of 100 lb/ft² (Kc → 28.6, Kd → 1.35). `constants.cruise_speed_coefficient`
  / `dive_ratio_coefficient` kept extrapolating the W/S = 20→100 taper *below* those
  endpoints past 100, understating VC(min)/VD(min) — inert for GA (W/S ≈ 20) but
  non-conservative for the heavy-concept band this tool targets. Both coefficients
  now hold constant at 28.6 / 1.35 for W/S ≥ 100 (matching STRSPEED.BAS, which clamps
  there); the clamp is continuous (the taper reaches the endpoint exactly at 100).
  For W/S > 100 — outside 23.335's tabulated range — `structural_speeds` attaches an
  OUT-OF-BAND note to the design-speeds condition, flagging VC(min)/VD(min) as
  GA-extrapolated advisories and pointing to chosen VC/VD (warn-only, mirroring the
  P1-5 pattern). Boundary + note tests in `test_structural_speeds.py`.

- **One-engine-out 23.367(a)(2) case no longer double-factored (M1-5, review T7).**
  The VC (ultimate) condition carried the default safety factor 1.5 even though
  23.367(a)(2) loads are *defined as ultimate*, so the render/export layer multiplied
  an already-ultimate load by 1.5. The safety factor is now owned by the **load-case
  definition** — set by how the regulation *classifies* the load (LIMIT vs ULTIMATE),
  not by the speed — and each case definition also fixes the **speed range** it is
  considered over (evaluated at the critical high end). Being a *failure* case does
  not by itself reduce the factor. 23.367(a) (turbopropeller; Ref 1 Ch 11 p87;
  VMC = minimum control speed) defines two cases: **(a)(1)** fuel-flow interruption,
  **LIMIT → SF 1.5**, considered VMC→VD (a failure that keeps the full factor);
  **(a)(2)** compressor-from-turbine disconnection / turbine-blade loss,
  **ULTIMATE → SF 1.0**, considered VMC→VC ("limit treated as ultimate"). The VS
  point (VS substituted for VMC per the Ch 11 Method) is a **LIMIT → SF 1.5** design
  point. Each case declares its `load_class`/`safety_factor`, speed range and basis
  as a row in the `_load_cases` table (new `_LoadCase` NamedTuple), carried onto each
  `ConditionResult` (`safety_factor` + `note`), so the VC deliverable now renders
  `lbs-ULT` at `SF=1.0` instead of `SF=1.5`. Three tests added
  (`test_safety_factors_by_failure_mode`, `test_load_case_owns_sf_and_speed_range`,
  `test_rendered_loads_are_ultimate_with_correct_sf`). Not an oracle change (no
  printed ONENGOUT oracle exists; the factor is applied only at the render/export
  boundary).

- **AIRLOAD4 swept-wing renormalization restored (M1-3, review T4 — `[Major]`).**
  The swept-branch span-load correction subtracted the Pope & Haney sweepback term
  but omitted AIRLOAD4.BAS's `COL20 = COL19/CLCOL19` renormalization, so a swept
  concept wing's span load integrated to **less** than the operating CL — the
  shipped `concept_regional_jet` flagship (Λ=24°) lost **9.6%** of its lift
  (`recovered_cl` 0.452 vs target 0.50; 6–13% across Λ=20–30°), non-conservative and
  flowing into the `net_loads` → sbeam FORCE/MOMENT export. `airloads._apply_sweep`
  is replaced by `_sweep_operating`, which applies the Pope subtraction **and** the
  renormalization to the **combined operating** distribution (matching AIRLOAD4.BAS
  `COL16` — twist is redistributed too, not additive-only), at `target_cl` for the
  report/closure path and per-condition at each case's CL for the deliverable path.
  Renormalization uses the physically-correct span-load integral (the literal
  chord-weighted `CLCOL19` line is OCR-garbled and closes only to ~0.3%; span-load
  form closes exactly — Decision 3). `recovered_cl` on the flagship now recovers
  0.500; the unswept GA Appendix-A additive and the Λ=0 reduction invariant are
  unchanged. Guarded by a Λ≠0 closure test, a listing-traceable COL18/COL19/COL20
  reconstruction, and a deliverable per-case CL-recovery test.

- **`BAL 1.4VSF` balances at the 1-g flaps-down stall (M1-2, review T2 — `[Critical]`).**
  In the flaps-extended envelope corner set, `flight_envelope._flap_config_points`
  captured the **STALL 2G** speed and ran the `BAL 1.4VSF` balancing point at 1.4×
  that. `FLTLOADS.BAS` (Code.pdf p300–302) saves the **STALL 1GL** (1-g flaps-down
  stall) speed for this condition; since STALL 2G ≈ √2 × STALL 1G, the balance speed
  was ~1.4× too high and the balancing tail load (∝ V²) ~2.2× too large, feeding the
  SELECT search and sbeam export. Fixed to balance at 1.4× the STALL 1GL speed. On
  Appendix A p181 (LANDING CG5, case 89 `BAL 1.4VS`) the corrected point is V 83.6 kt
  / LT −430 lb; the defect produced ~116 kt / −957 lb. The real landing-config aero
  polynomials (Appendix A p179 input listing) are now transcribed into the
  `flight_envelope` test fixture — correcting the 0.2.0 baseline note that the repo
  lacked them — and the new `test_bal_1p4vsf_balances_at_one_g_flaps_down_stall`
  asserts both the exact fix invariant and the p181 oracle. The shipped
  `examples/ga6_normal.project.json` is unchanged (it carries no `flaps_down` set),
  so no existing envelope/SELECT/export result moved; activating the full
  flaps-extended SELECT→TAILDIST pipeline in the example stays with L-2.

- **VD floor now enforces `K_d·VCmin` (M1-1, review T1 — `[Critical]`).**
  `structural_speeds.py` computed the K_d dive-speed term as `K_d·VC` and reported
  it only as a "recommended" advisory, so on the **no-chosen-speeds** path VD fell
  to the `1.25·VC` floor. FAR 23.335(b) and `STRSPEED.BAS` (`V2DMIN=K2·V1CMIN`,
  lines 380/390) require **both** minimums with the K_d term on the *minimum* cruise
  speed: `VD ≥ max(K_d·VCmin, 1.25·VC)`. On the Appendix A Cat-N no-chosen-speeds
  case (p155) the corrected VD is **198.53 kt**; the prior code returned 177.26 —
  10.7% non-conservative, propagating into MD/MACHLIM and every case at VD. The
  chosen-speeds worked example (p156, VD 212.5) clears both floors and is unchanged.
  Concept mode (Cat C) keeps only the absolute 1.25·VC floor and reports K_d·VCmin
  as advisory (behavior unchanged). Reported `LoadValue` renamed
  "Recommended dive VD (gust, K*VC)" → **"Minimum dive VD(min)"** (the enforced
  floor). New oracle `test_vd_floor_no_chosen_speeds` (p155).

- **FAR-citation labels corrected (found via the FAA User's Guide review).**
  `WTONECG` (`weight_onecg.py`) cited `23.21/23.23` (proof-of-compliance + load
  distribution); changed to **`23.23/23.29`** — load-distribution limits and empty
  weight & corresponding CG, the quantities the module actually computes (User's
  Guide §4.3). `FLTLOADS` (`flight_envelope.py`) `_FAR` omitted **23.345**
  (high-lift devices) despite building the oracle-tested flaps-down envelope; now
  `23.333/23.337/23.341/23.345/23.421`. Labels only — no load value changes. (The
  SELECT v-tail side-gust `23.443(b)` was reviewed and deliberately kept: the
  McMaster `SELECT.BAS` grounds the gust-load formula in (b).)

- **TAILDIST mis-cited every chordwise tail condition as `23.421` (found via the
  FAA User's Guide review).** `taildist.run` hardcoded `far_reference="23.421"`
  (balancing loads) on every emitted `ConditionResult`, so the v-tail distributions
  (23.441/23.443) and the h-tail maneuver/gust/unsymmetrical rows (23.423/425/427)
  were all reported as "23.421 Balancing Loads." The correct citation was already on
  the source SELECT `CriticalCondition.far_reference` but was discarded because
  `TailChordResult` did not carry it. `TailChordResult` gains a `far_reference` field
  (populated verbatim from the governing condition, serialized by `io`), and
  `taildist.run` now cites `r.far_reference or "23.421"`. Load magnitudes are
  unchanged (citation-only). Regression: `test_far_reference_propagates_from_select`
  in `tests/test_taildist.py`. Additive field, defaulted `""`; older projects load
  unchanged. Source: FAA User's Guide §20.2.2/20.2.3 (DOT/FAA/AR-96/46).

- **Swept-wing aero fields dropped by the JSON round-trip (found via Step P1-1).**
  `AeroSurfaceInput.sweep_deg` / `design_mach` (the fields that auto-select the
  swept/high-Mach `AIRLOAD4` branch, added in Step C7) were never serialized by
  `io._aero_surface_from_dict` / `aero_to_dict`, so a swept wing loaded from disk
  silently reverted to the low-speed Schrenk path. No GA fixture set these fields,
  so the gap was invisible until the swept `concept_regional_jet` fixture. Both
  directions now carry them; additive and defaulted (0.0), so every existing project
  loads unchanged. Regression: `tests/test_concept_regional_jet.py`.

- **Weight Estimate page crashed on beyond-GA projects.** The Mission-inputs form
  hard-capped its widgets at GA-tier limits (`max_value = 3000 hp`, 12 seats, 6
  engines, 10 hr) while seeding each widget from the loaded project, so opening a
  project whose value exceeded a cap raised `StreamlitValueAboveMaxError` before
  the page could render (e.g. `examples/dhc8_dash8.project.json` at 4000 hp / 39
  seats). The hard `max_value` caps are removed (keeping `min_value` for physical
  sanity), consistent with the concept-aware superset that must accept airplanes
  beyond the GA band (`GUI_design.md §9` — warn, don't block). Regression:
  `tests/test_views_smoke.py::test_weight_estimate_accepts_beyond_ga_power` loads
  the DHC-8 into the page and asserts no exception.

- **GUI input widgets ignored the Imperial/SI toggle.** The global unit toggle
  (`app/Home.py`, `st.session_state["unit_system"]`) governed *results*
  everywhere but not *inputs* — every sidebar form and `data_editor` accepted
  and displayed Imperial regardless of the setting, so an SI user's entries were
  stored as Imperial. All remaining pages with domain inputs now follow the
  `engine_mount.py` pattern: seed via `farloads.units.to_display`, unit-suffixed
  labels, widget `key`s suffixed with `system.value` (re-seed on toggle), and
  `to_imperial_scalar` back to canonical Imperial on Apply (`configuration_
  layout`, `structural_speeds`, `wing_geometry`, `weight_cg_inertia`,
  `aileron_loads`, `flap_loads`, `flight_envelope`, `fuselage_loads`,
  `landing_loads`, `mach_limit`, `payload_cases`, `tab_loads`, `tail_loads`,
  `weight_envelope`, `weight_estimate`, `wing_loads`). `loads_plots.py`, which
  never referenced the toggle, gained display-only conversion of its plotted
  values and axis labels. `farloads/units.py`'s scalar kind tables gained
  `area_sqft`/`length_ft`/`inertia_lbin2`/`area_sqin`. Airspeed (KEAS) and
  altitude (ft) stay aviation-standard in both systems. Display/boundary only —
  `project.json` and the calc core stay Imperial, `SCHEMA_VERSION` unchanged at
  20; 303 tests pass.

- **`project.weight` merge-write dropped `envelope`.** `configuration_layout.
  py`'s station-seed button and both `project.weight` writes in
  `weight_estimate.py`/`weight_cg_inertia.py` rebuilt `WeightInput` without
  carrying forward `.envelope`, silently discarding the Weight Envelope
  page's inputs on the next save from any of those three pages. Found while
  verifying the Phase D Step D4 regression DoD item; all three now pass
  `envelope=project.weight.envelope` through.

### Documentation

- **Pre-release doc-currency sweep (0.3.0 gate, `RELEASE_PROCESS.md` §3.1).**
  Fixed the schema-version drift the M2R-2 landing-purity change left behind: the
  `31 → 32` bump was recorded in the changelog but never propagated, so
  `GUI_design.md` ("currently `SCHEMA_VERSION = 31`", plus the migration-history
  list, now carrying `v32 M2R-2 LandingInput.n write-back removed`) and the
  `PROGRAM_SPEC.md` schema-version trail both read one version stale — a
  recurrence of the 2026-07-21 review's sole `[CRITICAL]`. Recorded the
  `body_loads` moment-closure limitation in `PROGRAM_SPEC.md` (Validation) and
  `20_theory/00_theory_sources.md` (both the module row and the closure-check
  table row, which claimed a free-free build without qualifying it to ΣFz).
  Refreshed the backlog "Current state" header (2026-07-21 → 2026-07-23, 466 →
  **483** passed, smoke test PASS, M2R + M3-1 noted closed) and marked the M4-1
  caveat-note obligation discharged.

- **Non-affiliation & attribution notice (M2R-2).** Added a non-affiliation
  statement to the README Disclaimer and an app-wide **About** section in the GUI
  sidebar (built once in `app/Home.py`, shown on every page): a modern **open
  replication** of the FAR23 loads suite (DOT/FAA/AR-96/46; Hal C. McMaster's CAE
  theory manual), **not affiliated with, endorsed by, or associated with
  McGettrick Structural Engineering, Inc. or DARcorporation**, whose "FAR 23
  LOADS" is a separate commercial product. Legal-exposure mitigation, decoupled
  from the M3-1 rename.
- **Doc currency sweep (M2R-1).** Retired stale/contradictory statements the
  2026-07-21 review flagged (1 CRITICAL + 3 MAJOR). (a) `GUI_design.md`: replaced
  the baked `SCHEMA_VERSION = 28` line with a pointer to the generated
  `DATA_DICTIONARY.md` (currently v31) so it can no longer drift. (b) `CLAUDE.md`:
  retired the "Appendix A/B ±0.1% oracle-lock" claim (Appendix B is not in the
  bundled scan) → "Appendix A ±0.1%; twin cases closure-locked", linking the
  Oracle-status anchor in `00_theory_sources.md`. The "Appendix A **and/or** B"
  per-module test convention and the frozen history record are correct and left
  as-is. (c) `PROGRAM_SPEC.md`: filled the schema-version trail — inserted v29
  (single-source CLmax stall, M1-1b), appended v31 (M2-10 operational placards).
  (d) `00_INDEX.md`: added rows for `01_far25_gap_analysis.md` and
  `01_verification_baseline_0.2.0.md`, enumerated the `reference/` CFR/AC text
  extracts, and replaced the stale "two-phase plan" backlog description with the
  M2R→M3→M4→F25 milestone structure; corrections-register pointer `CLAUDE.md` →
  `02_approved_corrections.md` in both `00_theory_sources.md` and
  `PROGRAM_SPEC.md`; README examples line → all six fixtures (added `atr42_100`,
  `concept_regional_jet`).
- **Documentation consistency sweep (M1-10).** (a) Corrected the stale reference
  filenames across 8 docs — `FAR23 loads (1).pdf` → `FAR23Loads_Code.pdf`,
  `ADA324952.pdf` → `FAR23Loads_UserGuide.pdf` (the dated `PROJECT_REVIEW` finding is
  left verbatim as it describes the mapping). (b) Stopped baking `SCHEMA_VERSION 15`/
  `242 tests` into README prose (points at CI + this changelog) and replaced the
  stale "4-phase Define→Analyze→Review→Export" nav description in README/CLAUDE.md
  with the real 7 workflow phases. (c) Added a canonical **Oracle status** section to
  `docs/20_theory/00_theory_sources.md` (Appendix A oracle-locked; Appendix B absent
  from the bundled scan → twin/turboprop cases closure-locked) and pointed
  README/PROGRAM_SPEC at it, retiring the contradictory "every module is
  Appendix-checked" claim. (d) Moved the approved-corrections **register of record**
  from `CLAUDE.md` to `docs/20_theory/02_approved_corrections.md` (CLAUDE.md keeps the
  policy + link) and added the FAA User's Guide §17.2.1 corroboration to
  `engine_loads.md`.

- **Phase G — detailed plan for G0/G1 + canonical-units decision.** Locked the
  G-1 canonical display units (length → `in`/`mm`, area → `ft²`/`m²`) in
  `docs/30_future/03_gui_rework_plan.md` §2, and expanded `00_backlog.md` → Phase G
  steps **G0** (units collapse: retire the redundant `length_ft`/`area_sqin` kinds
  in `units.py`, remap `_PROJECT_FIELD_KIND`, sweep the views — display-only, no
  oracle change) and **G1** (geometry single-source-of-truth: consolidate
  `configuration_layout` + `wing_geometry`, add the fuselage as a geometry entity
  with schema bump, downstream read-through) with file-level scope, guardrails and
  sequencing. Docs only — no code, calc, or schema change.

- **Phase G — workflow-aligned GUI rework plan.** Added
  `docs/30_future/03_gui_rework_plan.md` (renamed/expanded from the draft
  `fix_the_gui.md`): assessment of the redesign proposal against the shipped
  Phase D/E/F GUI, locked decisions G-1…G-4 (one-unit-per-dimension,
  single-source-of-truth geometry incl. the fuselage, re-entry vs. true-loss
  persistence, genuine analysis-flow re-sequencing), and the target six
  analysis-flow sections with their page mapping. Seeded the step-by-step plan
  into `00_backlog.md` → Phase G (Steps G0–G8) plus the split-out calc item 2-12
  (ground-case distributed fuselage loads + pressurization); indexed in
  `00_INDEX.md` and cross-linked from `GUI_design.md`. Docs only — no code, calc,
  or schema change.

---

## [0.2.0] — 2026-07-08

### Added

- **`scripts/smoke_test.sh`** (release step R2, `RELEASE_PROCESS.md` §3.5): a
  permanent, repeatable GUI/CLI smoke test. Starts `app/Home.py` headless,
  waits for `/_stcore/health`, checks the root page returns HTTP 200 with no
  traceback in the server log, then runs `farloads engine
  examples/ga6_normal.project.json -o out.csv` and checks the CSV header/row
  count. `RELEASE_PROCESS.md` §3.5 now points at the script instead of manual
  steps. No calc or schema change.

### Fixed

- **Flight Envelope page no longer destroys unedited `flight_loads` data**
  (Phase D Step D0, release step R1). The page previously rebuilt
  `FlightLoadsInput` wholesale (`configurations=[cruise]`,
  `altitudes_ft=[altitude]`) on every rerun, so merely opening it deleted any
  flaps-down configuration or extra altitudes a loaded project carried.
  `FlightLoadsInput` gains a pure `merged()` method (`farloads/models.py`) that
  merges one page-edit into the existing slice — the edited altitude replaces
  `altitudes_ft[0]`, the edited configuration replaces its same-`flaps_down`
  peer (appended if none), and everything else is preserved — and
  `app/views/flight_envelope.py` persists through it. This is the first
  application of the Phase-D "Apply merges into the project slice" page
  convention (`docs/40_history/05_phase_d_gui_workflow_plan.md §5`). Regression tests in
  `tests/test_flight_envelope.py` load a slice with a flaps-down configuration
  and two altitudes through the persist path and assert both survive. No calc
  or schema change.

### Added

- **`docs/40_history/01_verification_baseline_0.2.0.md`** (release step R4,
  `RELEASE_PROCESS.md` §4.4): the permanent regression-baseline record — one
  table per module (all 22 ported programs + `configuration`/`body_loads`)
  mapping each printed Appendix A/B figure the test suite locks against to
  its reference-page citation and tolerance, plus a dedicated section for the
  closure-locked modules (ONENGOUT, the LANDLOAD wheel table, swept AIRLOAD4,
  FAR 25 optional engine cases, `body_loads`, `configuration`, concept-mode
  closure) that have no printed oracle. Docs-only.

### Changed

- **`PROGRAM_SPEC.md` docs-drift fix** (release step R3, `RELEASE_PROCESS.md`
  §3.1): `body_loads` (shipped in Step C6) now has its own module-spec entry
  (it was previously only mentioned inside SELECT's write-up) and the
  cross-module field-ownership table gained the `fuselage_mass` row it reads.
  Docs-only; no code/schema change.
- **Per-module analysis pages now mark their on-screen LIMIT loads.** The
  `flap_loads`, `tab_loads`, `one_engine_out` and `balanced_tail_verification`
  Streamlit pages display the calc's LIMIT values (the oracle-traceable numbers);
  each now carries a caption stating the on-screen loads are LIMIT and that the
  CSV/FORCE-card downloads and Review/Export pages are ULTIMATE (= limit × 1.5), and
  a `LIMIT` marker on every load column/metric. The mandate was scoped accordingly
  (`CLAUDE.md`, `docs/10_standard/00_program_overview.md`): **all deliverable load
  output is ULTIMATE**; a per-module analysis page may show explicitly-marked LIMIT
  oracle values as the sole exception.
- **The `ULT` marker is now part of the load's units string.** All rendered load
  output (the load-case CSV headers, the `results_to_rows` `Units` column, and the
  text reports) carries the marker inline — force `lbs-ULT`/`N-ULT`, moment
  `ft-lb-ULT`/`lb-in-ULT`/`Nm-ULT`, pressure `lb/in^2-ULT` — replacing the previous
  separate `ULT` suffix on the column header. `report.py` gains `_ult_units()`
  (keyed off the existing load-unit detection), so non-load quantities (weights,
  locations, inertias, dimensionless load factors) keep their plain units. The `SF`
  column is unchanged; a case held at ultimate is `SF=1.0`. Render tests
  (`test_report.py`) updated to the `-ULT` unit forms.
- **Documented the ULTIMATE-output convention as a mandatory standard.** Codified in
  `CLAUDE.md`, `docs/10_standard/00_program_overview.md`,
  `docs/10_standard/PROGRAM_SPEC.md`, `docs/10_standard/PROJECT_GUIDE.md §5`,
  `docs/20_theory/00_theory_sources.md` and `docs/30_future/01_concept_loads_plan.md`:
  **all load output SHALL be ultimate**, the `ULT` marker is **part of the load's
  units string** (`lbs-ULT`/`N-ULT`, `ft-lb-ULT`/`lb-in-ULT`/`Nm-ULT`,
  `lb/in^2-ULT`), **every load case states its safety factor** (default 1.5 per 14
  CFR 23.303; Part 25 equivalent 25.303), and a value already at ultimate is
  **`ULT SF=1.0`**.
- **Rendered/exported loads are now ULTIMATE (= limit × factor of safety).** The
  calc still emits LIMIT loads (oracle-locked to the manual), but `report.py` and
  `export/sbeam_bridge.py` now multiply the load quantities (forces/moments/
  pressures — never geometry, weights, inertias, or dimensionless load factors) by a
  per-case factor of safety to report ultimate = limit × 1.5 (14 CFR 25.303). New
  `constants.ULTIMATE_FACTOR = 1.5` and `ConditionResult.safety_factor` (default
  1.5); the field is per-case so a future 14 CFR 25.302 / Appendix K probability-
  based factor (1.0–1.5) can be assigned to a failure case — sudden engine stoppage
  is held at the conservative 1.5 for now. The load-case CSV gains an `SF` column and
  marks the force/moment headers `ULT`; the sbeam FORCE/MOMENT cards, span-load CSVs
  and closure comments are ultimate (the set still sums to 1.5 × the root/total).
  Reference: `reference/14CFR_factor_of_safety.md`. Calc oracle tests unchanged;
  render/export tests (`test_report.py`, `test_io.py`, `test_sbeam_bridge.py`) updated
  to ultimate.


- **GUI restructured into the four-phase workflow (Define → Analyze → Review →
  Export).** `app/Home.py` is now an `st.navigation` entry point that builds the
  phase-grouped sidebar from the new `farloads/workflow.py` — the ordered,
  dependency-aware step graph (each step names its calc `module` and the slices it
  `requires`/`produces`). The 20 page files moved `app/pages/NN_*.py` →
  `app/views/<workflow-key>.py` (clean names, no numeric prefixes; the duplicate
  `06_` index is gone), and each page's `set_page_config` was removed (called once,
  in `Home.py`, as `st.navigation` requires). The old Phase-0 Home page (which only
  inspected four of the ~20 project slices) is replaced by `views/dashboard.py`: an
  Overview that loads/saves the project and shows per-step completeness.

### Added (GUI)

- **Results Review & Export pages.** `views/results_review.py` consolidates the
  governing (critical) loads on every component plus all module results by phase;
  `views/export_report.py` gathers every output in one place — project JSON,
  per-module load CSVs + a combined text report, sbeam wing/fuselage/tail/
  control-surface BDF cards, and a single **Download all `.zip`** bundle. Both
  recompute from the project inputs, so exports are never stale. *(Closes the
  "Combined workbook export" backlog item.)*
- **GUI regression tests.** `tests/test_workflow.py` (step-graph well-formedness;
  every registered module has a workflow step) and `tests/test_views_smoke.py`
  (headless `AppTest` runs the entry point + all 20 views with the example project,
  asserting no uncaught exception). +24 tests.
- **Multi-engine engine-mount page.** `app/views/engine_mount.py` now exposes the
  first-class multi-engine `Project`: a sidebar **layout** selector (1 nose / 2 or
  4 wing-mounted engines) drives the engine count, and an **engine selector** picks
  which engine is being assessed. Each engine's inputs (type, CG, weights, rotors)
  are held canonically in Imperial in `st.session_state["engine_inputs"]` — keyed
  per engine and unit system — so switching engine or unit system preserves every
  engine's data. Results default to the selected engine with a **"Show all engines"**
  toggle for the full `engine.run(project)` (each condition prefixed with the engine
  designation); the JSON/CSV/text exports cover every engine. A single engine
  reduces exactly to the previous behaviour (no prefixes, identical to `run_all`).

### Fixed

- **Engine-mount page crash.** `app/views/engine_mount.py` still built its
  save-project payload with the removed single-engine `Project(engine=...)` keyword;
  now uses `engines=[...]` + `EngineLayout.SINGLE_NOSE`. Caught by the new view
  smoke test.

### Changed

- **Corrected FAR 23.361(a)(1) takeoff torque (AC 23-19A).** The takeoff-case engine
  mount torque is now `factor × mean takeoff torque` (the same cylinder/turboprop
  factor as (a)(2)), where the original program and McMaster's manual left it
  **unfactored**. Per **AC 23-19A**, the unfactored form is the **Amendment 23-26**
  drafting error (non-conservative, lower loads), corrected by **Amendment 23-45**:
  23.361(c) applies the factor to all of paragraph (a). For the IO-520-BB the
  takeoff mount torque changes 554.39 → **737.34 ft-lb**; for a turbopropeller it
  becomes 1.25× mean takeoff, identical to 25.361(a)(1)(i). This is a **user-approved,
  documented deviation from the Appendix A oracle** (CLAUDE.md "Approved corrections
  to the source"); `test_361_a1` asserts the corrected value and retains 554.39 as
  the mean-torque figure. Source text: `reference/AC_23-19A_engine_torque.md`.
- **Corrected FAR 23.361(a)(3) turboprop-malfunction torque (AC 23-19A).** The
  propeller-control-malfunction mount torque is now `1.6 × 1.25 × mean takeoff
  torque` (= 2.0× mean), where the original program (`TTP=1.6*ENGTORQ`) and
  McMaster's manual applied only the 1.6 factor. The (a)(3) base limit takeoff
  torque is the same quantity as (a)(1), so 23.361(c)'s 1.25 turbopropeller
  mean-torque factor applies before the 1.6 — the same **Amendment 23-26** omission
  / **Amendment 23-45** restoration as the (a)(1) correction above. A **user-approved,
  documented deviation** (CLAUDE.md "Approved corrections to the source"); no printed
  Appendix B engine-mount oracle exists, so it is formula-checked in
  `test_361_a3_applies_mean_torque_factor`. Source: `reference/AC_23-19A_engine_torque.md`.

### Added

- **Optional supplemental FAR 25 engine cases (concept superset).**
  `Project.include_far25` (default off) appends only the **non-duplicative**
  **14 CFR 25.361 / 25.371** engine-mount cases on top of the oracle-locked FAR 23
  set, for **turbopropeller** engines: (a)(3)(i) stoppage `@ 1g`, (a)(3)(ii)
  max-accel torque `@ 1g` (no FAR 23 analog), and 25.371 gyroscopic on the A2 limit
  load factor. The FAR 25 torque cases 25.361(a)(1)(i)/(ii)/(iii) are **omitted** —
  with the AC 23-19A correction factoring the FAR 23 takeoff case, they are
  bit-for-bit duplicates of the corrected 23.361(a)(1)/(a)(2)/(a)(3) for a
  turbopropeller. 25.371 reuses the fixed FAR 23.371(b) rates (2.5/1.0 rad/s) as a
  conservative concept stand-in for the maneuver-derived rates. New optional input
  `EngineInput.max_accel_torque` (blank → `max_engine_torque`); recip/jet engines get
  no FAR 25 cases. The engine-mount GUI gains an **"Add supplemental FAR 25 cases"**
  checkbox. Kept opt-in (not folded into the FAR 23 path) so the Appendix A/B oracle
  — 6 turboprop conditions, 2.5g gyro vertical — is byte-identical when off. Source
  text in `reference/14CFR_Part25_engine_torque.md`; formula-closure tested
  (`tests/test_engine_far25.py`). No oracle exists for Part 25.
- **Balanced-tail-load verification — BALLOADS (Step C11).** New
  `modules/balloads.py` (registers `"balloads"`): the off-pipeline cross-check of
  `BALLOADS.BAS` (Reference 1 Ch 8–9). For every flaps-retracted V-n condition it
  recomputes the rational balancing horizontal-tail load — AoA load at 25% tail MAC
  (`LT25`) + camber/elevator load at 50% (`LT50`), elevator deflection and elevator
  load — **reusing SELECT's oracle-locked `htail_balance`/`_elevator_load`** (no
  re-derivation), converts the rational CP (% tail MAC) to a fuselage station and
  reports it against FLTLOADS' *approximate* `XTC`/`XTF`. Verification report only —
  no schema change, no pipeline output. New `app/pages/16_Balanced_Tail_Verification.py`.
  Oracle-locked against the Ch 9 case-202 hand-calc (`LT = 519.845 lb`, LT25 +907.62,
  LT50 −387.78, δ −5.39°, CP 6.35% tail MAC); the rational up/down loads equal
  SELECT's `BAL UP/DN RETRACTED` exactly. 4 new tests (211 total). **This completes
  all 22 of Reference 1's Appendix-C programs.**
- **Landing / ground loads — LGFACTOR + LANDLOAD (Step C10).** New
  `modules/landing.py` (registers `"landing"`): the FAR Part 23 Subpart C
  ground-load conditions (Reference 1 Ch 20). **LGFACTOR** estimates the landing
  load factor from the FAR 23.473 drop-test work-energy balance (descent velocity
  `V = 4.4·(W/S)^0.25` clamped 7–10 fps, tyre/strut energy efficiencies → airplane
  load factor `N`, gear factor `NLG = N − L`). **LANDLOAD** computes the tricycle-gear
  reaction loads (24 main-wheel + 33 nose-wheel cases) for the level, tail-down,
  one-wheel, braked-roll, side and supplementary-nose-wheel conditions
  (FAR 23.473–23.499) — the drag factor `K`, ground angles, `BETA`, the `AP/BP/DP/CP`
  lever arms, per-wheel ground-line and airplane-datum reactions and the unbalanced
  moments. New `LandingInput`/`LandingGearInput` input slice (`Project.landing`,
  carrying the gear strut geometry that has no home in the aerodynamic
  `Project.geometry`) and `GearReactionCase` result record; `SCHEMA_VERSION` 14 → 15
  (additive). New `app/pages/15_Landing_Loads.py`. LGFACTOR is oracle-locked against
  Appendix A p236 (V 9.0048 / N 3.0951 / NLG 2.4281); LANDLOAD's gear-geometry
  intermediates are oracle-locked against p230, with the OCR-garbled printed
  wheel-load table closure- + legible-cell-validated (the ONENGOUT precedent). 9 new
  tests; **all 22 Reference 1 Appendix-C suite programs except the optional BALLOADS
  utility are now ported.**
- **One-engine-out vertical-tail loads — ONENGOUT (Step C9).** New
  `modules/one_engine_out.py` (registers `"one_engine_out"`): a time-marching yaw
  simulation of the FAR 23.367 critical-engine failure (Reference 1 Ch 11). The
  failed engine's thrust/windmill-drag asymmetry yaws the airplane about its
  vertical axis (`IZZ`) until the pilot — at peak yaw rate but ≥2 s after failure
  (23.367(b)) — applies full rudder and recovers; `run()` reports the maximum
  vertical-tail load per speed (VC ultimate / VD limit / VS) with engine thrust,
  windmill drag, max yaw rate, the 25%/50% MAC loads at peak and time to recovery,
  and `time_history()` returns the full transient on demand (below VMC the run is
  time-bounded and flagged non-recovered). New shared `modules/_vtail.py` (the v-tail
  lift slope AVT, rudder effectiveness EFFECTV and the large-deflection EF chart),
  with SELECT's private `_avt`/`_effectv`/`_ef` refactored to delegate to it. New
  `app/pages/20_One_Engine_Out.py` (per-speed summary + on-demand time-history
  charts/CSV). First module to exercise the first-class multi-engine `Project`.
  **Validation:** the printed Appendix B twin oracle is unavailable (Appendix B is
  absent from the bundled references), so C9 is locked by sub-formula exactness vs
  `ONENGOUT.BAS` + integration/physics closure + refactor-parity with SELECT (11 new
  tests; 198 pass).

- **Schema v14 (Step C9).** `Project.one_engine_out` (`OneEngineOutInput`) input
  slice and `VTailLoadsInput.xv50` (FS of 50% v-tail MAC) — additive; older files
  load unchanged.

- **Control-surface simplified distributions — AILERON / FLAPLOAD / TABLOADS (Step
  C8).** New `modules/aileron.py`, `modules/flap.py`, `modules/tab.py` (register
  `"aileron"` / `"flap"` / `"tab"`): the FAR-style simplified pressure
  distributions. **Aileron** (Ch 16, FAR 23.455 / CAM 3.222) — deflected up/down
  rolling loads over the VA/VC/VD schedule, constant LE→hinge then taper to 0 at
  the TE. **Flap** (Ch 17, FAR 23.345 / 23.457) — the four-condition flaps-extended
  envelope (Abbott & von Doenhoff Fig 98) with the momentum-theory propeller
  slipstream and the head-on 25 fps gust amplifications, taper LE→half at TE.
  **Tab** (Ch 18, FAR 23.409 / CAM 3.224) — full deflection at VC, trapezoidal
  (LE = 2× TE). New input slices `AileronLoadsInput` / `FlapLoadsInput` /
  `TabLoadsInput`(+`TabSpec`), the `ControlSurfaceLoadResult` slice on
  `LoadsResult.control_surface`, the `sbeam_bridge` control-surface export
  (`control_surface_csv` / `control_surface_force_moment_cards`, FORCE set scaled to
  the critical load), and `app/pages/12_Aileron_Loads.py` /
  `13_Flap_Loads.py` / `14_Tab_Loads.py`. `structural_speeds.design_speed_values()`
  exposes the scalar design speeds the modules read. Oracle-locked against the
  Appendix A reports (p200/p201/p202) within ±0.1%.

- **Schema v13 (Step C8).** `Project.aileron_loads` / `flap_loads` / `tab_loads`
  input slices and `LoadsResult.control_surface` — all additive; older files load
  unchanged.

- **Chordwise tail-load distribution — TAILDIST (Step C7).** New `modules/taildist.py`
  (registers `"taildist"`): the five-station chordwise net pressure profile on the
  average tail chord — the additive (angle-of-attack, 25% chord) plus camber (50%
  chord) distributions (TAILDIST.BAS subroutine 3000, Reference 1 Ch 10) — for each
  critical horizontal/vertical-tail condition from SELECT. SELECT now attaches the
  rational `lt25`/`lt50` split to every tail `CriticalCondition`. New
  `app/pages/11_Tail_Distribution.py`, the `sbeam_bridge` tail export
  (`tail_chordwise_csv` / `tail_force_moment_cards`) and the `cli.py`
  `--export-target tail` option. Oracle-locked against the Appendix A "Chordwise
  Distribution of Tail Loads" tables (13 horizontal p237 + 4 vertical p245) within
  ±0.1%.

- **Swept / high-Mach airloads — AIRLOAD4 (Step C7).** `modules/airloads.py` gains
  the AIRLOAD4 branch (Ref 1 Ch 12): the Pope & Haney sweepback redistribution of
  the additive Schrenk span load, auto-selected (`use_airload4`) when the 25%-chord
  sweep exceeds 15° or the design Mach exceeds 0.4, reducing exactly to AIRLOADS at
  zero sweep / low Mach. New `AeroSurfaceInput.sweep_deg` / `design_mach` triggers.

- **Schema v12 (Step C7).** `TailLoadsInput.htail_semispan_in`,
  `VTailLoadsInput.vtail_span_in`, `CriticalCondition.lt25`/`lt50`, the
  `TailChordResult` slice on `LoadsResult.tail_chordwise`, and the
  `AeroSurfaceInput` sweep fields — all additive; older files load unchanged.

- **Critical Loads + Fuselage Loads UI pages (Step C6, R9).** New Streamlit pages
  `app/pages/09_Critical_Loads.py` (the SELECT critical wing / h-tail / v-tail /
  fuselage conditions, grouped per component with their loads and FAR cites; persists
  `envelope.critical`) and `app/pages/10_Fuselage_Loads.py` (the Ch 15 fuselage net
  shear/bending per critical condition, editable fuselage mass distribution, closure
  metric, plots and CSV download). Both flag concept-mode results as unverified
  extrapolation.

- **Flaps-extended tail loads + flapped V-n envelope (Step C6, R3/R4).**
  `flight_envelope` gains the flaps-extended (LANDING) V-n corner set at the flap
  speed VF (FLTLOADS.BAS subroutine 3000: stall at 2/3 g / 1 g / 2 g, the n=2 / n=0
  maneuver points at VF, ± gusts at VF, and the VF / 1.4 Vs balancing points,
  n-limited to 2 per FAR 23.345 and investigated at sea level). SELECT extends the
  balancing search to the flaps-extended points (FAR 23.421) and adds the
  flaps-extended gust (FAR 23.425(a)(2), 25 fps at VF). The real landing-config aero
  polynomials are not in the repo fixtures, so R3/R4 are validated by **closure**
  (the flapped points achieve their target NZ; the rational balancing tail load
  zeroes the flapped pitching moment) rather than the printed flaps-extended oracle
  (Appendix A cases 81/106/88/108). `tests/test_flight_envelope.py` /
  `tests/test_select.py` extended.

- **Net fuselage loads + sbeam body export (Step C6, R6/R8).** New `body_loads`
  module (Ref 1 Ch 15) computes the fuselage longitudinal net distribution for each
  critical fuselage condition: each station's inertia (`-NZ·w`), the balancing tail
  air load at the tail station, and the wing reaction at 25% wing MAC, integrated
  nose→tail to running shear `Sz` and bending `Myy` → `Project.loads.body_net`
  (`BodyLoadResult`/`BodyStationLoad`) + a per-station CSV (`body_load_rows`). Ch 15
  ships no program/oracle, so it is validated by **equilibrium closure** (applied
  `ΣFz=0`, shear returns to 0 aft of the wing). The sbeam bridge gains
  `body_span_load_csv` / `body_force_moment_cards` (FORCE Fz per station, the set
  summing to ~0). New `tests/test_body_loads.py`.

- **WTONECG — persisted mass slice (Step C6, R7).** `weight_onecg.build_mass`
  emits the long-deferred `Project.mass` slice (`MassResult`): weight, CG and the
  airplane moments/product of inertia (lb-in²) about the CG for the itemized
  loading. Validated against Appendix A p136 and the io round-trip. SELECT's oracle
  searches keep their documented Ch 9 inertia approximations (so the slice is
  available for reporting/future per-CG work without changing the locked results).

- **SELECT — critical fuselage conditions (Step C6).** Adds the Ch 9 fuselage
  condition search (SELECT.BAS subroutine 4000): the maximum fuselage load reacted
  at the wing (`LZW − NZ·WW`, FAR 23.301), the aft-fuselage down/up bending (the
  largest signed product of that load and the tail load, 23.331), and the greatest
  vertical inertia factor for concentrated-weight installations (23.301). `WW`
  (wing weight) is a new `SelectInput` field (default `0.09·MTOW`). These are
  condition *selections* (scalar criticals) distinct from the Ch 15 fuselage net
  *distribution* (R6). Oracle-locked against Appendix A "Critical Fuselage Loads":
  max down load on wing 13347.6 (GUST +C), aft down bending 12569.6, aft up bending
  −6390.3 (GUST −C), greatest NZ 5.81. `tests/test_select.py` extended.

- **SELECT — horizontal-tail maneuver / gust / unsymmetrical loads (Step C6).**
  Extends the `select` module with the remaining flaps-retracted h-tail conditions:
  unchecked maneuver up/down (FAR 23.423(a) — full elevator deflection at the 1g VA
  points), checked maneuver up/down (23.423(b) — a pitch-acceleration increment
  `Iyy·θ̈/arm` with the approximate `Iyy=0.44·W·LF²/384` and `θ̈=39·n(n−1.5)/V` at
  VC/VD), up/down gust (23.425(a)(1) — the balancing load plus the rational gust
  increment `KG·Ude·V·ST·AHT·(1−36aw/ARW)/498`), and the unsymmetrical load
  (23.427(a) — 100% one side / `100−10(n−1)`% the other, excluding the locally
  carried unchecked-maneuver loads per FAA CAM 3.216). The large-deflection
  effectiveness factor `EF(δ, Se/St)` is reconstructed exactly from SELECT.BAS
  subroutine 10000. `TailLoadsInput` extended with the elevator geometry, airplane
  length and wing lift slope (`SCHEMA_VERSION` 10 → 11, additive). Oracle-locked
  against Appendix A "Critical Horizontal Tail Loads": unchecked −1397.8 / +1227.2,
  checked −671.5 / +787.8, gust +908.6 / −1292.8, unsymmetrical −1111.8 (RH −646.4,
  LH −465.4). `tests/test_select.py` extended.

- **SELECT — rational vertical-tail loads (Step C6).** Extends the `select` module
  with the four critical vertical-tail loads (Ch 9 / SELECT.BAS subroutine 8300),
  searched over the V-n `BAL A` (VA) and `BAL C` (VC) points: sudden full rudder
  deflection (FAR 23.441(a)(1)), yaw to a 19.5° sideslip with the rudder held
  (23.441(a)(2)), a 15° yaw with the rudder neutral (23.441(a)(3)), and the lateral
  gust at VC (23.443(b)). Side loads use the tail lift slope `AVT=2π/(1+2/ARVT)`,
  the rudder effectiveness `EFFECTV=cubic(SR/SV)`, and the gust mass-ratio /
  alleviation `UGT`/`KGT` with a default yaw inertia `IZZ`. New `VTailLoadsInput`
  slice (`Project.vtail_loads`); `SCHEMA_VERSION` 9 → 10 (additive) with the `io.py`
  round-trip. Oracle-locked against Appendix A "Critical Vertical Tail Loads" —
  yaw-15 −526, side gust +604 (IZZ 4169.2) and the angle-of-attack components are
  exact; the rudder-deflection loads (sudden rudder +591, rudder load 167) carry an
  `EFV≈1.009` large-deflection chart factor that is illegible in the scanned source
  (a `VTailLoadsInput` field, default 1.0). `tests/test_select.py` extended.
  Vertical-tail `CriticalCondition`s land alongside the wing and htail sets in
  `Project.envelope.critical`.

- **SELECT — rational horizontal-tail balancing loads (Step C6).** Extends the
  `select` module with the Ch 9 / BALLOADS rational balancing method: for every
  balanced V-n point it resolves the total balanced tail load into the
  angle-of-attack load at 25% tail MAC (`LT25=(AT·AHT/57.3)·Q·ST`, tail AoA
  `AT=αwl+IT−E`, downwash `E=114.6·CL/(π·ARW)`, slope `AHT=2π/(1+2/ARHT)`) and the
  camber/elevator load at 50% MAC (`LT50` from balancing the pitching moment about
  the CG for the elevator deflection), then selects the largest up and largest down
  balancing load with flaps retracted (FAR 23.421) into `Project.envelope.critical`
  as `htail` `CriticalCondition`s. New `TailLoadsInput` slice (`Project.tail_loads`:
  tail incidence, wing/tail aspect ratios, tail area, elevator effectiveness, 25%/50%
  tail-MAC stations, wing zero-lift angles); `SCHEMA_VERSION` 8 → 9 (additive) with
  the `io.py` round-trip. Oracle-locked against the Ch 9 case-202 hand-calc
  (LT25 +907.62, LT50 −387.78, δ −5.39°, **LT 519.845**, CP 6.35%) and Appendix A
  "Critical Horizontal Tail Loads" (UP STALL +N CG1 18000 +519.85, DOWN MAN D CG3
  12000 −613.92). The H-tail maneuver/gust/unsymmetrical, the flaps-extended
  balancing (needs the flapped V-n envelope), the vertical tail and the fuselage net
  are still later C6 increments. `tests/test_select.py` extended.

- **SELECT — critical wing loads (Step C6).** New registered `select` module
  (`farloads/modules/select.py`) porting SELECT.BAS's wing critical-load search
  (Ref 1 Ch 9, SELECT.BAS ~2990-3540): it scans the balanced FLTLOADS V-n matrix
  for the governing wing condition of each design point — **PHAA**/**PLAA**
  (largest resultant `√(LZW²+DX²)`), **PMAA** (largest LZW), **NMAA** (largest
  negative resultant), **ACRL** (accelerated roll), and **TORS** (steady-roll
  aileron torsion `(cm−0.01·δ)·G·V²`, deflection per CAM 3.222) — and writes them
  as wing `CriticalCondition`s into `Project.envelope.critical`. New `SelectInput`
  slice (`Project.select_input`: full-down aileron deflection + basic-airfoil cm
  for the steady-roll search); `SCHEMA_VERSION` bumped 7 → 8 (additive) with the
  `io.py` round-trip. Oracle-locked against Appendix A "Critical Wing Loads" (PHAA
  STALL +N CL +1.519/V 117.40, PLAA MAN D +0.472/212.40, PMAA GUST +C +0.810/170,
  NMAA GUST −C −0.433/170, ACRL AC ROLL +1.328/116, TORS ST ROL C +0.470/170);
  `tests/test_select.py`. The rational horizontal/vertical-tail and fuselage
  critical loads (rest of Ch 9) and the fuselage net distribution are a later C6
  increment; `select` joins the `run_all_modules` set.

- **C6 schema foundation (SELECT + fuselage/body loads).** First step of Step C6:
  the `Project` schema additions the SELECT module and fuselage net distribution
  build on, all additive (`SCHEMA_VERSION` bumped 6 → 7; older files load
  unchanged). New `Project.mass` slice (`MassResult`/`MassCase`: persisted WTONECG
  weight/CG/inertia per loading) — the long-deferred persisted mass slice, landed
  now that SELECT needs the inertia. New `Project.fuselage_mass` input slice
  (`FuselageMassInput`/`FuselageStation`: the fuselage longitudinal mass
  distribution for the body net loads). New SELECT critical-load set
  (`CriticalLoadSet`/`CriticalCondition`) on `EnvelopeResult.critical` (previously
  reserved). New fuselage net distribution (`BodyLoadResult`/`BodyStationLoad`) on
  `LoadsResult.body_net`, the body analogue of `wing_net`. Full `io.py` JSON
  round-trip for every new slice; the new types are re-exported from `farloads`.
  Validated by `tests/test_io.py::test_c6_slices_round_trip`.

- **Configuration & Layout page + fleet assessment (Step C5).** New
  `Project.configuration` slice (`LayoutInput`: fuselage, parametric wing, tail
  areas/arms, landing gear) and a registered `configuration` calc module that
  derives the wing planform (MAC/XLEMAC/Y_MAC/AR/span via the WINGGEOM strip
  integrator on generated polylines), a tail-volume neutral point + static margin,
  tip-back / overturn angles and prop ground clearance. New Streamlit page
  `app/pages/00_Configuration_Layout.py` (Plotly three-view with CG/NP markers,
  assessment panel, a WINGGEOM seed button, and W/S-vs-W/P + MTOW-vs-OEW fleet
  plots). `app/data/reference_aircraft.csv` extended with a heavier/concept tier
  (twin pistons, commuters, a bizjet, light transports). Modern addition — no
  `.BAS` and **no regression oracle**; figures are first-order estimates flagged in
  concept mode. `SCHEMA_VERSION` bumped 5 → 6 (additive). Validated by
  analytic-vs-WINGGEOM-strip MAC consistency (±0.1%) and Appendix A trapezoid
  plausibility (±10%).

- **sbeam export bridge (Step C4).** New `farloads/export/` subpackage turns the
  NETLOADS net wing load (`Project.loads.wing_net`) into sbeam-consumable
  artifacts: a **span-load CSV**, **FORCE/MOMENT** bulk-data cards (comma
  free-field unit-scale form matching `sbeam/results/load_export.py`, one load set
  per case), and an optional minimal **CBAR stick-model BDF** (GRID + CBAR chain +
  PBAR/MAT1 placeholder + root SPC1 + a SOL 101 subcase per case). The applied
  nodal load at each station is the *increment of the cumulative* NETLOADS column,
  so the FORCE set sums to the root shear and the MOMENT(My) set to the root
  torsion exactly (and the FORCE moments reproduce the root bending). Coordinate
  map (`export/coordinates.py`) is FAR23LOADS station/butt/waterline inches →
  sbeam global CID 0 (identity, single edit-point). New CLI flag
  `--export-sbeam <prefix> [--stick-model]`. The bridge is a pure renderer, not a
  registered calc module. Validated by force/moment closure + a self-contained
  free-field round-trip; the stick deck parses **and solves SOL 101** in the real
  sbeam (manual verification).

- **Net wing loads — WINGINER + NETLOADS (Step C3).** New `wing_inertia` and
  `net_loads` modules compute the spanwise wing **shear, bending moment and
  torsion** along the 25% chord as the algebraic sum of the air loads and the
  inertia loads — the headline structural deliverable (root values size the wing).
  `AIRLOADS` is extended with an air-load distribution (`air_load_distribution`):
  it scales the C1 Schrenk lift to the operating CL, builds per-strip
  lift/drag/pitching-moment forces, rotates them into the airplane reference and
  integrates to the cumulative shears/moments/torsion (drag = computed induced +
  input profile). `WINGINER` models the wing-panel mass as a linearly-tapered area
  density (root density iterated to the panel weight) plus concentrated weights,
  forming 1g-vertical / 1g-drag / unit-roll cases combined per condition.
  `NETLOADS` sums air + inertia per station. Adds a `Project.wing_mass` input slice
  (`WingMassInput`/`ConcentratedWeight`/`WingLoadCase`) and a `Project.loads`
  result slice (`LoadsResult`/`WingLoadResult`/`WingStationLoad`), with section
  `profile_drag`/`section_cm` added to `AeroSurfaceInput`; schema bumped to **v5**
  (additive). New Streamlit page `app/pages/08_Net_Wing_Loads.py` (air/inertia/net
  shear-BM-torsion plots + CSV). FAR23 oracle-locked against the Appendix A air-load
  (p206), wing-inertia (p217-221) and net-load (p222) tables; the critical
  conditions come from the FLTLOADS V-n matrix (the C3-before-SELECT bridge).

- **Flight envelope + balancing tail loads — FLTLOADS (Step C2).** New
  `flight_envelope` module (`farloads/modules/flight_envelope.py`) builds the
  FAR 23.333 maneuver + gust **V-n diagram** and the **balancing horizontal-tail
  load** at every cruise corner — a faithful port of FLTLOADS.BAS subroutine 3900
  (iterate angle of attack to the required load factor, then dynamic pressure to
  the Mach-adjusted stall line; Glauert compressibility; CLmax-vs-Mach curve) and
  4864 (gust load factor, FAR 23.341). Reads the design speeds and limit load
  factors from STRSPEED. Adds a `Project.flight_loads` input slice
  (`FlightLoadsInput`/`AeroCoeffSet`/`CgCase`: geometry scalars, airplane-less-tail
  aero-coefficient polynomials, weight-CG cases) and a `Project.envelope` result
  slice (`EnvelopeResult`/`VnPoint`/`TailBalanceLoad`) with `io.py` round-trip;
  schema bumped to **v4** (additive — older files load unchanged). New Streamlit
  page `app/pages/07_Flight_Envelope.py` (V-n chart + balanced-condition table).
  The GA and concept example fixtures gain a `flight_loads` slice. FAR23
  oracle-locked against the Appendix A "V-n Data" cruise matrix (p179-180); concept
  mode validated by physics closure (attains the user load factor; LZ+LT = NZ·W).

- **Spanwise wing airloads — AIRLOADS + TAU (Step C1).** New `airloads` module
  (`farloads/modules/airloads.py`) computes the wing spanwise lift distribution by
  **Schrenk's method** (Reference 1 Ch 7): the additive distribution (untwisted
  wing at CL=1), the twist-driven basic distribution, and their combination at a
  target CL — the `c·cl` span load every downstream wing-load module consumes. Folds
  in the **TAU** lift-curve-slope planform correction (`TAU.BAS` curve-fit, p407).
  Adds a `Project.aero` slice (`AeroInput`/`AeroSurfaceInput`: section lift-curve
  slope, taper/tip ratio, twist table, target CL) with `io.py` round-trip; schema
  bumped to v3 (additive — older files load unchanged). New Streamlit page
  `app/pages/06_Airloads.py` with a span-load plot (additive / basic / total) and
  the integrated-CL closure check. The GA and concept example fixtures gain an
  `aero` wing slice. FAR23 oracle-locked: the additive (`CC(LA1)`/`C(LA1)`) and
  basic (`Awo`/`CC(lb)`/`Clb`) distributions match Appendix A p161-162 within ±0.1%;
  concept mode is validated by physics closure (integrated `∫c·cl dy` recovers the
  target CL; basic distribution carries zero net wing lift). Known limitation: the
  cosine fairing of the basic distribution across a flap/aileron discontinuity is
  not yet modelled (arises only with deflected flaps).

- **Concept mode (Step C0) — foundation for >12,500 lb configurations.** Adds a
  `"C"` (concept) certification category to `StructuralSpeedsInput`: STRSPEED
  bypasses the GA-only FAR 23.337 maneuver-load-factor formula and cap, instead
  using the user's `chosen_n`/`chosen_nneg` verbatim (both now required in concept
  mode). Adds a **direct-weight path** (`WeightInput.direct_totals()`) that derives
  MTOW/OEW/useful by summing the itemized `MassItem` data base by kind, replacing
  WTESTIMA's GA regression for a heavy concept; WTESTIMA still runs but flags itself
  as a sanity-only estimate (`Project.is_concept` is the single concept read-point).
  Schema bumped to v2 (additive — v1 files load unchanged). The Structural Speeds
  page gains the Concept category with `n`/`n_neg` inputs and an unverified-
  extrapolation warning; the Weight Estimate page shows a concept sanity banner.
  Example fixture `examples/concept_heavy.project.json` (MTOW 18,000 lb). The FAR23
  path stays oracle-locked: all Appendix-A/B tests pass unchanged, and concept mode
  reduces exactly to FAR23 on GA inputs. Confirmed no hard ≤12,500 lb / seat-count
  assertion was load-bearing.

- **Phase C — initial-concept loads tool plan** — adopted a development plan that
  grows the suite from a ≤12,500 lb FAR Part 23 replication into an
  initial-concept distributed-loads tool: a `concept` mode that generalizes the
  FAR23 weight/seat/load-factor caps, configuration assessment against similar
  airplanes, per-component distributed loads (wing / body / tail + standard
  simplified control-surface distributions), and a `FORCE`/`MOMENT` bulk-data
  export bridge to **sbeam**. Locked decisions: concept-mode generalization,
  Schrenk analytical aero, sbeam export bridge, vertical-slice-first build order.
  Steps C0–C8 are tracked in `docs/30_future/00_backlog.md`; the full narrative,
  schema additions and per-step detail are in
  `docs/30_future/01_concept_loads_plan.md`. Reframed the project scope in
  `README.md` and `CLAUDE.md` accordingly (FAR23 replication core *being grown
  into* a concept loads tool). The FAR23 replication core stays oracle-locked
  (Appendix A/B ±0.1%) and concept mode reduces exactly to it on GA inputs.
  *(Planning docs only — no analytical code changed yet.)*
- **MTOW-vs-OEW reference plot on the Weight Estimate page** — the page now plots
  the estimated max take-off and empty weights against a bundled reference fleet
  (Cessna 150/172/182/206/210, Van's RV-7/8/10/14, Bonanza A36, PA-46, King Air
  200, ATR 42-500, Dash 8-100) as a log-log Plotly scatter, with the analysis
  airplane highlighted. Reference figures live in `app/data/reference_aircraft.csv`
  (nominal published specs, UI reference only — never used in a FAR computation) and
  are guarded by `tests/test_reference_aircraft.py`. Adds `plotly>=5.0` as a runtime
  dependency.
- **Seed the weight data base from the estimate** — new pure-calc helper
  `weight_estimate.estimate_to_mass_items(inp)` expands WTESTIMA's structure,
  powerplant and systems component weights (plus options/miscellaneous) into
  empty-weight `MassItem` rows, skipping the group totals and the propeller line
  already inside "Engine installed". `app/pages/01_Weight_Estimate.py` gains a
  "Seed Weight, CG & Inertia from this estimate" button that writes those rows
  into `Project.weight.items`, so the Weight, CG & Inertia page opens pre-filled
  (stations/inertias left at zero for the user). Covered by
  `tests/test_weight_estimate.py::test_seed_mass_items_from_estimate`.
- **MACHLIM Mach-limit lines** — `mach_limit` (MACHLIM) ported against Appendix A
  p160: never-exceed and flutter-clearance Mach (`MNE = 0.9·MD`, `MFC = 1.2·MD`)
  and the per-altitude Mach-limited equivalent airspeeds `V(M) = M·a·√σ` from the
  shoulder altitude to the max operating altitude. Reproduces MNE 0.3627, MFC
  0.4836 and V(MC) 170.16→150.77 (12000→18000 ft). New `MachLimitInput` on
  `Project.speeds.mach_limit`, reusing `constants.standard_atmosphere`;
  `app/pages/06_Mach_Limit.py` (with a V-vs-altitude chart), inputs in the example,
  and `tests/test_mach_limit.py`. **Completes Phase 2.**
- **STRSPEED structural design speeds** — `structural_speeds` (STRSPEED) ported
  against the Appendix A V-n table: limit maneuver load factors (FAR 23.337,
  `n = 2.1 + 24000/(W+10000)` capped by category, negative −0.4n/−0.5n) and design
  airspeeds VA/VC/VD/VF (FAR 23.335) with their minimums, plus cruise/dive Mach at
  the shoulder altitude. Reproduces VA 121.3, VC 170, VD 212.5, VF 105.5, n
  +3.8/−1.52, MC 0.323/MD 0.403 @ 12000 ft. New `StructuralSpeedsInput` /
  `Project.speeds` slice, a shared `constants.standard_atmosphere` helper (also for
  MACHLIM) plus `cruise_speed_coefficient`/`dive_ratio_coefficient`, wing area read
  from the WINGGEOM geometry slice (2·13257/144 = 184.1 ft²),
  `app/pages/05_Structural_Speeds.py`, speeds slice in the example, and
  `tests/test_structural_speeds.py`. VD uses the 1.25·VC floor (the worked
  example's governing bound); K_d·VC is reported as the recommended gust value.
- **WTENV weight/CG envelope** — `weight_envelope` (WTENV) ported against the
  Chapter 3 worked example: structural CG-limit stations (`X = XLEMAC + pct·MAC`,
  reading wing XLEMAC/MAC from the geometry slice via WINGGEOM), minimum/maximum
  loadings, the forward discretionary-loading envelope, and the ballast to reach
  each structural limit (`WB = WL−WA`, moment-balance station). Reproduces the
  manual's stations (85.1/77.49/72.64), min flight 2063@73.09, max load 3322@84.56
  and ballast weights 78/418/158. New `WeightEnvelopeInput` under `Project.weight`,
  `app/pages/04_Weight_Envelope.py`, envelope inputs in the example, and
  `tests/test_weight_envelope.py`. The aft-gross ballast station is the exact
  moment balance (~108.5 in); the manual's hand calc rounded it to 103.7 (limit
  station 85.0 vs the precise 85.107) — documented in the module.
- **Phase 2 geometry** — `wing_geometry` (WINGGEOM) ported against Appendix A
  p141: spanwise strip-sum of area, MAC, YLE(MAC), XLEMAC, aspect ratio and span
  per aerodynamic surface (the wing reproduces MAC 69.246 / XLEMAC 63.641 / AR
  6.095 within ±0.1% at the manual's 20-element count). New `Project.geometry`
  slice (`GeometryInput` → `SurfaceInput` with LE/TE point polylines, `symmetric`,
  `elements`), `geometry_from_dict`/`geometry_to_dict`, wing+aileron surfaces in
  the example, `app/pages/03_Wing_Geometry.py`, and `tests/test_wing_geometry.py`.
  `units.py` gained area (in²→m²) and airspeed (knot→m/s) SI output. Wing-mounted
  engine spanwise stations are derived from `engine_layout`.
- **First-class multi-engine layout** — the `Project` engine slice is now a list
  (`engines: List[EngineInput]`) plus an `EngineLayout` enum constrained to the
  modelled layouts (`SINGLE_NOSE` = 1 nose, `TWIN_WING` = 2 wing, `QUAD_WING` =
  4 wing, symmetric). `Project.__post_init__` validates the engine count against
  the layout; a read-only `Project.engine` property returns the first engine so
  single-engine call sites are unchanged. `io.py` reads either the new
  `"engines"`/`"engine_layout"` JSON or the legacy single `"engine"` key, and the
  engine module's `run(project)` loops over every engine (single-engine output is
  byte-identical; multi-engine prefixes each condition with the engine
  designation). Resolves PROJECT_GUIDE open decision #2 ("model the field now").
  Full one-engine-out *loads* still land at `ONENGOUT`.
- **Phase 1 mass properties** — two modules ported against Appendix A:
  `weight_estimate` (WTESTIMA, statistical weight estimate; reproduces the p133
  figures exactly) and `weight_onecg` (WTONECG, one-loading weight/CG/inertia;
  matches the p136 figures within ±0.1%). New `Project.weight` slice
  (`WeightInput` = mission `estimation` + itemized `items` mass list), with
  `EngineWeightType`/`MassItemKind` enums and the installed-engine-weight
  correlation centralised in `constants.py`. New Streamlit pages
  `01_Weight_Estimate.py` and `02_Weight_CG_Inertia.py`, example weight slice in
  `examples/ga6_normal.project.json`, and `tests/test_weight_estimate.py` /
  `tests/test_weight_onecg.py`. The pages offer an SI **output** toggle (weight →
  kg, inertia → kg·m², CG → mm). `WTENV` re-scoped to Phase 2 (needs `WINGGEOM`'s
  `XLEMAC`/`MAC`).
- `report.module_text_report` — module-agnostic text output, used by the
  generalised `cli.py` stdout path so non-engine modules render correctly.
- **Packaging & tooling** — `pyproject.toml` (editable install via
  `pip install -e '.[dev]'`; `ruff` and `pytest`/coverage config), `cspell.json`
  domain wordlist, and a GitHub Actions CI workflow running `ruff` + `pytest` on
  Python 3.9 / 3.11 / 3.12.
- **Documentation structure** — `docs/` reorganised by type
  (`10_standard` / `20_theory` / `30_future` / `40_history`) with an index
  (`docs/00_INDEX.md`). Added `docs/20_theory/00_theory_sources.md`,
  `docs/30_future/00_backlog.md`, and `docs/40_history/00_completed_development.md`.
- **Process guides** — `docs/10_standard/CODE_REVIEW_PROCESS.md` and
  `RELEASE_PROCESS.md`, specialised for the module-porting workflow.
- **`LICENSE`** (MIT) backing the `pyproject.toml` license declaration, plus
  README License and Disclaimer sections (results are not certified for design).
- **`docs/10_standard/00_program_overview.md`** — consolidated program code
  standard & developer guide (coding standards, an error-handling contract,
  units, entry points, testing/coverage), with `docs/00_INDEX.md` and `CLAUDE.md`
  pointing to it as the authoritative standard.
- **CI coverage floor** — the pytest step now runs with `--cov-fail-under=80` so
  coverage cannot silently regress (a ratchet, to be raised toward 85%).

### Changed

- **Documentation critical review & consistency pass.** Brought the docs in line
  with the as-built code (Phases 0–2 + Phase-C C0–C6; 13 of 22 suite programs +
  `configuration`/`body_loads`; `SCHEMA_VERSION` 11). Rewrote
  `docs/30_future/00_backlog.md` as a dependency-ordered step-by-step plan
  (Steps C7–C11 + deferred refinements + open decisions + a release/versioning
  item). Corrected stale status in `docs/10_standard/00_program_overview.md`
  (structure tree + "Phase 0 complete"), `README.md` ("7 of 22" → 13 of 22; layout
  tree), `CLAUDE.md` (`Project` "currently just engine"; the contradictory
  `sys.path`-shim line), `PROJECT_GUIDE.md` ("exactly one is ported", §2 inventory
  status, §7 roadmap, examples list), `PROGRAM_SPEC.md` (status-summary Phase 0
  row), and `docs/00_INDEX.md`. Removed the superseded `Phase1_2_review.md`
  GUI-review notes (its one live item — Home Engineer/Date fields — moved to the
  backlog). No analytical code changed.
- **SI mass vs Imperial force units.** `LoadValue` gained an optional `quantity`
  hint so the SI converter can tell a pounds-*mass* weight (→ kg) from a
  pounds-*force* load (→ N) — both labelled `lb`. Added `lb-in² → kg·m²` to the
  result converter; weights set `quantity="mass"`. Engine load output is
  unchanged.
- `cli.py` text output is now module-agnostic (was engine-specific), and
  `io.load_cases_csv` falls back to the generic property table for modules that
  emit no structural load cases, so the mass-properties modules export usable CSV.
- `farloads` and `cli` are now an editable install, so they import from any cwd;
  removed the `sys.path` shims from `app/Home.py` and `app/pages/19_Engine_Mount.py`.
- Renamed the ambiguous local helper `l` to `ln` in `farloads/units.py` (lint).
- Fixed stale `calc.py` references (the module is `farloads/modules/engine.py`) in
  `farloads/models.py` and `farloads/report.py` comments/docstrings.
- `CLAUDE.md` mandate strengthened: consult the `reference/` PDFs when generating
  analysis code, keep `docs/` in sync with every code change, and follow the
  backlog → history → changelog move-on-completion rule.
- `docs/PROGRAM_SPEC.md` and `docs/PROJECT_GUIDE.md` moved to `docs/10_standard/`;
  cross-references in `README.md` and `CLAUDE.md` updated.

---

## [0.1.0]

Phase 0 baseline — the package restructure with the engine-mount module ported.
See `docs/40_history/00_completed_development.md` for the full record.

### Added

- `farloads/` pure-calc package (`models`, `modules/engine`, `registry`, `io`,
  `units`, `report`, `constants`), the `app/` Streamlit multi-page UI, and
  `cli.py`. Engine-mount module (`ENGLOADS`) validated against Appendix A/B.
