# Design review — the LRA beam model (steps 12 / 13 / 14 against the stated target)

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: AGREED 2026-08-15 (user) — the §6 amendments to `00_backlog.md` (step 12/13/14 bodies, Pri 1/10/16), plan 10 §1.1/§8.1, plan 11 §4, plan 09 §10 (T-18) and note 21 (P-6a) are applied; the standard-doc, schema and `bands.py` items in §6 follow the code per the closure tiers. No code.** A review of the
existing design documentation for band B of the priority table (backlog Pri 1–4:
`fuselage_width` fixture data, step 13 side-of-body node, step 12 LRA beam-model
export + import, step 14 real stiffness) against the **target model the user
stated 2026-08-15**, reproduced in §1. It records where the shipped code and the
written plans already meet the target, where they contradict it, and the
decisions that must be taken before code (practice 1). Nothing here changes an
oracle: the FAR 23 core, the per-component decks and the assembled balanced deck
are untouched by every recommendation — the LRA beam model is a **third**
deliverable beside them (§2).

Sources reviewed: `00_backlog.md` (band B rows and the step 12/13/14 bodies),
`10_sbeam_roundtrip_ci_harness_plan.md` §1.1/§8.1, `11_balanced_airframe_cases_plan.md`
§2.1/§3.5/§4, `09_distributed_empennage_loads_plan.md` §10 (T-12…T-17),
`21_power_effects_wing_note.md` P-6, `CONVENTIONS.md` §1 (the open torsion-reference
question), `PROGRAM_SPEC.md` "sbeam export bridge", and the export code
(`sbeam_bridge.py`, `balanced_deck.py`, `bands.py`, `coordinates.py`,
`tail_span.py`, `gear_loads.py`, `mass_cards.py`, `models/inputs.py`).

---

## 1. The target (user, 2026-08-15)

An LRA-based beam model that the `FORCE`/`MOMENT` cards can be applied to,
containing:

| # | Feature |
|---|---|
| F1 | Control-surface **hinge** and **actuator** locations |
| F2 | Wing **side-of-body (SOB) node** — loads are *summed* to it, because loads inside the wing centre box are not accurate |
| F3 | **Fuselage beam** with **posts** attaching the wing; forward-fuselage loads summed to the **front-spar** post, aft-fuselage/tail loads to the **rear-spar** post |
| F4 | **Vertical tail → fuselage** attachment |
| F5 | **Horizontal tail** attachment: 5.1 to the fuselage (conventional), 5.2 to the fin tip (T-tail) |
| F6 | LRA placement: lifting surfaces (wing, v-tail, h-tail) at **40 % chord**; control surfaces on the **hinge line**; fuselage at the **section centre** |
| F7 | **Landing-gear load point**, attached to the fuselage or the wing depending on where the gear is mounted |
| F8 | **Engine thrust point** |

## 2. The single most important clarification — three deliverables, not two

The docs today distinguish two things: the **per-component decks** (analysis
views, oracle-backing, clamped or cut) and the **assembled balanced deck** (the
primary loads deliverable, plan 11 B-5). The step 12 backlog body describes the
LRA export as "the assembled deck's skeleton as its own artifact". Measured
against the target that description is too weak, because the assembled deck is
**not a beam model at all**: it is `GRID` + `FORCE`/`MOMENT` + one `SPC1`, one
node per distinct load position, **no elements of any kind**
(`balanced_deck.py:498-523`), solved on a determinate support whose reaction is
the residual. Its nodes are wherever the loads are, not on any axis line. It has
no SOB, no posts, no attachments — and it must stay that way, because that is
what makes it the stiffness-independent free-free equilibrium proof (B-4).

**Recommendation R-1.** Restate the deliverable set in the backlog and
`PROGRAM_SPEC.md` as three artifacts with distinct contracts:

| Artifact | Contract | Status |
|---|---|---|
| Per-component decks (wing stick, body, tail span, chordwise, control) | oracle-backing views; each takes a free-body cut | shipped |
| Assembled balanced deck | equilibrium proof: nodes at load positions, no elements, determinate support, reactions ≈ 0 | shipped |
| **LRA beam model** (step 12) | a **structural idealization**: node lines on the LRAs, `CBAR` chains, rigid attachments (posts, hinges, gear, engine, tail joints), every load **transferred onto its nodes** with resultant preserved; the same cases as the assembled deck, expressed on this model | **to design** |

The equilibrium gate carries over unchanged (plan 07 on the transferred set), but
the beam model's *value* is its **internal** loads at the named nodes — SOB,
posts, attachments — which the assembled deck cannot state. Everything below is
about defining that model.

## 3. Feature-by-feature findings

Format: what ships / what the docs say / gap / recommendation.

### F1 — Control-surface hinges and actuators

- **Ships:** elevator and rudder only, `control_load_mode = "discrete"` (T6):
  hinge and actuator `GRID`s in bands 5001+/5301+, hinge force by tributary span,
  the actuator carrying `−HM` as a pure couple (T-15). **No shipped fixture
  enters hinge geometry** (T-17), so no shipped deck exercises it. Aileron, flap
  and tab have **no `GRID` cards at all** (`sbeam_bridge.py:1762-1780`) — their
  modules produce chordwise fractions with no chord and no span station.
- **Docs say:** plan 09 §10 places the hinge `GRID`s **on the parent surface's
  LRA line** (`tail_span.py:606`) and folds the chordwise offset into a torsion
  `M_i = F_i·(x_lra − x_hl)`.
- **Gap against F1/F6:** the target puts the control surface's own LRA **on the
  hinge line**. A hinge node on the parent LRA with a folded torsion is the
  right *card* for a consumer who has no control-surface beam; it is the wrong
  *node* for a beam model that has one. Wing control surfaces are missing
  entirely — and the aileron cannot be placed spanwise because
  `AileronLoadsInput` has no butt lines (backlog Pri 10 names this).
- **Recommendation R-2.** In the LRA model, a control surface is its own
  `CBAR` chain along the **hinge line** (`x_hl(y) = x_le + c − c_e`, already
  computed at `tail_span.py:607`), with a `GRID` at each hinge and at the
  actuator, each hinge node tied to the parent LRA node at the same span station
  by a rigid link. The hinge force is applied on the hinge node **without** the
  folded torsion (the lever arm is now geometry the solver sees) and the actuator
  couple stays. The two representations must reproduce the same parent-surface
  torsion — that is the gate, and it is closed-form (T-14/T-15 identities). Extend
  the schema so the wing surfaces can do the same: `hinges_span_in` /
  `actuator_span_in` (and inboard/outboard butt lines) on the aileron and flap
  inputs — the same fields T-17 put on `TailMassInput`, in the same shape. Pairs
  with Pri 10 (the aileron increment needs the same butt lines). Note the
  fixture-data rule: hinge stations are **entered**, never invented (T-17).

### F2 — Wing side-of-body node

- **Ships:** nothing. Wing stick model clamped at BL 0 half a strip inboard of
  station 0; `CENTERLINE_CLAMP_NOTE` states it in-band; assembled deck has no
  SOB either.
- **Docs say:** step 13 body (backlog) + plan 10 §1.1 — correctly, that the SOB
  load is internal and needs a node, not a moved clamp; that the SOB source is
  undecided (`fuselage_width/2` unpopulated everywhere; `inboard_rib_y` is a
  mass-panel proxy); and — **hard constraint 1** — that the station set cannot
  be truncated at the SOB because Appendix A's root closure is about station 0.
- **Gap:** the target says loads are **summed** to the SOB because centre-box
  loads are not accurate. That is a *collapse* of the inboard stations onto the
  SOB node — exactly what plan 10 §1.1 forbids. The two are reconcilable only
  once §2's distinction is made: constraint 1 binds the **per-component wing
  deck** (the oracle view) and the SOB item's part (b) "add without truncating";
  the **LRA model** is a new artifact whose wing beam runs **SOB → tip**, with
  the strip loads inboard of the SOB (air + inertia, both sides) transferred to
  the SOB node as an equivalent force + moment (resultant-preserving). The
  Appendix A oracle is untouched because the LRA model never claims the
  station-0 closure.
- **Recommendation R-3.** Rewrite the step 13 body so that (a) the per-component
  wing deck **adds** a SOB reporting node (as written), and (b) the LRA model
  **starts** at the SOB and sums the inboard load there — two behaviours, one
  SOB source. State the SOB internal load two ways and gate them against each
  other: sloads' closed-form sum of applied loads outboard of the SOB, and the
  solver's `CBAR` end force in the first element outboard. **SOB source
  decision (BM-1, below):** an explicit `SurfaceInput.sob_y_in` (butt line, per
  surface — the h-tail attachment needs the same quantity), falling back to
  `parametric.fuselage_width/2` **marked assumed**, and never `inboard_rib_y`.
  This makes Pri 1 the fallback supplier for both F2 and F5.1, which is what its
  "feeds Pri 2" note already implies.

### F3 — Fuselage beam and posts

- **Ships:** the body deck's node line is `(x, 0, 0)` — "the component in
  isolation, not its station on the airplane" (`sbeam_bridge.py:922-923`); the
  assembled deck deliberately does **not** flatten waterlines and puts each
  fuselage mass item at its true `(x, y, z)`. The carry-through reaction exists
  only as an *applied load* on the body deck's 1501+ nodes at the front/rear
  spar stations (`derived_geometry.carry_through`, root-chord spar fractions
  `front_spar_pct`/`rear_spar_pct`, defaults marked assumed) — and is
  **excluded** from the assembled deck by the seam rule.
- **Docs say:** step 12 says "GRID on … the fuselage axis" without defining the
  axis; nothing describes posts; plan 11 §4's authority table says the
  carry-through is internal to an assembled model, which is right and is
  exactly why the LRA model needs the posts as elements.
- **Gaps:** (i) **section centre is not in the schema** — `FuselageSection`
  carries `x, width, height` only; there is no centre waterline per section
  (`body_drag_waterline` is a single scalar). (ii) The load-path idealization
  is not stated. "Forward fuselage summed to the front spar, tail to the rear
  spar" is a **split-fuselage** idealization: the forward body is a cantilever
  ending at the front-spar post, the aft body + empennage a cantilever ending at
  the rear-spar post, and the two posts carry the two sums into the wing
  centre-box/SOB. That is statically determinate and stiffness-independent — the
  right choice while `PBAR`/`MAT1` are placeholders (step 14). A *continuous*
  fuselage beam on two rigid posts is indeterminate and its post loads are
  stiffness-dependent, which the placeholder properties cannot honestly deliver.
- **Recommendation R-4.** Define the fuselage LRA as the **section-centre line**
  `(x, 0, z_c(x))` and add `z_centre` (waterline) to `FuselageSection`, defaulted
  from `body_drag_waterline`/`wrp_waterline` and marked assumed (same pattern as
  the fin root waterline, B8a-1). Record the **split-fuselage** idealization as
  the default (BM-2) with the continuous beam as the step-14 opt-in, and say in
  the deck header which one the file is. Posts: rigid links (`RBE2` — already
  the element the round-trip wrapper uses; promote it from test scaffolding to a
  production band) from the fuselage node at each spar station to the wing
  **SOB** node on each side. The post stations are `carry_through`'s existing
  spar stations. **Consequence to state:** the front/rear-spar split of the
  wing–body load is then a *geometry* result of the two cantilever sums, not the
  `body_loads` p103 distribution — the two must agree in resultant, and that is
  a gate.

### F4 — Vertical tail → fuselage

- **Ships:** the fin's node line starts at the fin root waterline (B8a-1,
  `tail_geometry.fin_root_waterline`, entered → derived → assumed precedence);
  the fin span deck is "root-supported" **in prose only** — no `SPC`, no element
  (`sbeam_bridge.py:1613-1624`).
- **Recommendation R-5.** Fin root LRA node rigid-linked to a fuselage node
  **inserted** at the fin root x station on the section-centre line (not the
  nearest existing station). The v-tail LRA % chord is the same `ref_axis_pct`
  field (F6). Nothing else new; the docs only need the element stated.

### F5 — Horizontal tail attachment

- **Ships (5.1):** **superseded 2026-08-15 by T-8a** (Pri 1 closed). The
  attachment is now `tail_span.htail_attachment`, a resolution order with
  provenance: T-tail → the single fin-tip joint at `y = 0`; else the fuselage
  outline interpolated at the h-tail **root LRA station** (`±w/2`, marked
  assumed); else the stated `±ds/2` pair. The *maximum* section is never used —
  it is five times too wide at `atr42_100`'s h-tail. `atr42_100`, `dhc8_dash8`
  and `cessna_210` carry published outlines; `ga6_normal` and `concept_heavy` are
  synthetic and stay on the flagged fallback. `attachment_y` and its new
  `attachment_basis` are on the result but **no exporter consumes them yet**. **Ships (5.2):** T7 transfers a **lumped**
  `Fz`/`Myy` (balancing load + h-tail inertia at that V-n point) to the fin's
  **last** node; the h-tail has no nodes of its own in a T-tail fin deck.
- **Gap:** in the LRA model the h-tail is a beam in its own right on both
  layouts. Conventional: its two attachment nodes (at `±sob_y`/`±width/2`) tie
  to a fuselage node inserted at the h-tail LRA x. T-tail: its **centreline
  node** ties rigidly to the **fin tip** node. That means the T7 lumped transfer
  must **not** be applied in the LRA model when the h-tail cards are present —
  the same class of double count plan 11 §4 already polices for the
  carry-through and the point tail load.
- **Recommendation R-6.** Add two rows to the plan 11 §4 authority table:
  "T7 tip transfer — per-component fin deck: applied; LRA model: **excluded**
  (the h-tail beam is attached, the solver recovers it)" and "gear reactions /
  engine thrust — see F7/F8". Consume `attachment_y` in the exporter. Pri 1
  supplies the stations; until it does, the LRA model should **refuse** to
  build a conventional h-tail attachment on the `±ds/2` fallback (or build it
  and mark it assumed in the header — decision BM-3; refusing is the "flag,
  never silently default" rule).
  **Resolved 2026-08-15 (T-8a, Pri 1 closed).** The stations exist and carry
  their own provenance, so the exporter gates on `attachment_basis`, not on a
  guess: refuse `ATTACH_STRIP_PAIR`, accept-and-state `ATTACH_OUTLINE`, accept
  `ATTACH_FIN_TIP` outright. Note the third branch is **new** and changes this
  recommendation's shape — a T-tail h-tail has one centreline support, so on
  `concept_regional_jet` there is no conventional attachment to build at all,
  and R-6's "T-tail: centreline node ties to the fin tip" is now what the
  physics layer already reports rather than something the exporter infers.

### F6 — LRA placement

- **Ships:** `SurfaceInput.ref_axis_pct` (M4-18) exists, default **0.25**, and
  **no shipped fixture sets it** — so every wing, h-tail and fin deck today is on
  the 25 % line and `to_loads_ref_axis` is a no-op (`net_loads.py:118-119`).
  The docstring says "typically 40–50 %". Control surfaces: hinge nodes on the
  parent LRA (F1). Fuselage: `y = z = 0` (F3). `CONVENTIONS.md` §1 still lists
  the load-axis vs elastic-axis torsion reference as an **open question**;
  backlog Pri 16 is the doc-only item for it.
- **Recommendation R-7.** (a) Enter `ref_axis_pct = 0.40` on the wing, h-tail
  and v-tail surfaces of all six fixtures (fixture data, S) — this moves the
  wing/tail deck digests once, deliberately, and leaves Appendix A untouched
  because the calc stays at 25 %. (b) Do **not** change the schema default:
  0.25 = "the original reporting" is what keeps the oracle path bit-identical
  on a bare project. (c) Make the LRA-model exporter **require** an explicit
  `ref_axis_pct` on every surface it builds — a beam on an unstated axis is the
  "silently defaulted" case the SF table refuses. (d) Close the CONVENTIONS
  open question and Pri 16 with one sentence in the deck header: *"grid line =
  LRA = the assumed elastic axis at NN % chord; torsion is about it."* An
  imported beam line (step 12 import) is the consumer's elastic axis by
  definition, which is what the backlog already says.

### F7 — Landing-gear load point

- **Ships:** the gear node exists — `LandingGearLegInput.attach` (trunnion),
  band 10001+, contact-patch reaction transferred there with its lever-arm
  couple (`gear_loads.py:272-285`) — but only in the assembled deck's ground
  cases, and it **floats**: no element connects it to anything.
- **Recommendation R-8.** Rigid-link each leg's `attach` node to its parent
  beam: nose gear → fuselage node inserted at `attach.x`; main gear → fuselage
  node **or** the wing LRA node at `attach.y` (Dash 8 nacelle-mounted mains are
  wing mass per G-2 and are wing-attached here). Decide the parent from an
  explicit `LandingGearLegInput.mounted_on: fuselage | wing` (BM-4), with
  inference by `|attach.y| > sob_y` as the marked-assumed fallback. In flight
  cases the node carries the gear mass only (its `CONM2`), which is already how
  the mass SSOT tags it.

### F8 — Engine thrust point

- **Ships:** nothing exported — no engine, mount, nacelle or hub node in any
  deck. `EngineInput` carries `engine_cg` and `prop_cg` (hub); ENGLOADS produces
  mount torque/gyro `LoadValue`s only; the balance states there is no
  distributed thrust and files it. Power-effects note P-6 (agreed) defines the
  thrust line as **hub point + incidence + toe**.
- **Recommendation R-9.** Two nodes per engine: a **hub node** at `prop_cg`
  (the thrust point — the `FORCE` along the P-6 line goes here) and a **mount
  node** at `engine_cg`, hub → mount rigid, mount → wing LRA node at the
  engine butt line (wing-mounted) or fuselage node at `engine_cg.x`
  (nose/tail-mounted), chosen by an explicit `mounted_on` (BM-4 again). ENGLOADS'
  23.361/23.371 torque + gyro become `MOMENT` cards on the mount node in the
  power-effects Kind I cases; engine `CONM2` items attach to the mount node
  instead of the nearest fuselage station (which `mass_cards._attach_gid`
  already names as a limitation). Until the power-effects step ships, the
  thrust `FORCE` is zero on every case and the node is still emitted — the
  skeleton is complete before the load exists.

## 4. Cross-cutting recommendations

**R-10 — a skeleton contract shared by export and import.** Step 12's import
("use the imported node line as the LRA") only works if the imported model can
tell sloads *which* node is the SOB, the posts, the fin root, the h-tail
attachments, the gear and engine points. Define the node families as a
**named-node contract** — a `$ SLOADS-NODE <family> <side>` comment on each
special `GRID` on export, and the same tags (or a sidecar JSON map) accepted on
import, with nearest-node-per-family as the marked-assumed fallback. Bands
(`bands.py`) gain one production family per node class: `lra-sob`, `lra-post`,
`lra-hinge-wing`, `lra-gear-link`, `lra-engine`, and an `RBE2` EID band that is
**not** the test-only 900001+ range.

**R-11 — the transfer rule applies to every load, not just wing strips.** In the
assembled deck loads sit at their own positions; in the LRA model every load
must land on a beam node. State once (owner: `export/coordinates.py` beside the
axis maps, drift-guarded) that a load at `p` applied to node `n` carries the
couple `(p − n) × F`, and that plan 07's invariant on the transferred set is the
acceptance gate — the step 12 body already says this for strips; generalize it.
Mass items keep `CONM2` with offsets where the consumer solves inertia itself;
the `FORCE`/`MOMENT` inertia set is the transferred form.

**R-12 — say what is stiffness-independent.** With rigid links and placeholder
`PBAR`/`MAT1`, only determinate paths give honest internal loads: wing SOB (a
cantilever from the SOB outboard, provided the wing is attached *only* through
the SOB/posts), fin root, the split-fuselage post sums, gear and engine links.
Anything indeterminate (a continuous fuselage on two posts, a wing carry-through
element between the two SOB nodes, a redundant hinge set on a control-surface
beam) is **stiffness-dependent** and must wait for step 14 or be stated as
placeholder-dependent in the header. This is the strongest reason to keep the
split-fuselage default (BM-2) and to sequence step 14 last.

**R-13 — sequencing.** The table has step 13 (SOB) before step 12 (LRA model),
but the SOB is a *node of the skeleton*: choosing its source, its collapse rule
and its reporting form is a step 12 topology decision. Recommend: **Pri 1
(closed 2026-08-15, T-8a) →
step 12 phase 0 (this note's decisions BM-1…BM-5 agreed) → step 13 built as the
first skeleton node → step 12 export → step 12 import → step 14.** The
per-component wing deck's SOB reporting node (constraint 1 of plan 10 §1.1)
ships with step 13 as written; the LRA model's SOB-start wing ships with step
12 export.

**R-14 — the assembled deck is unchanged.** Every recommendation is additive.
Gate: assembled-deck and per-component digests byte-identical except where a
fixture-data change (R-7a `ref_axis_pct`, Pri 1 `fuselage_width`) moves them
once, each with its own `CHANGELOG` line.

## 5. Decisions to agree before code (BM-1 … BM-5)

| # | Decision | Recommended | Alternatives |
|---|---|---|---|
| BM-1 | SOB source | explicit `SurfaceInput.sob_y_in`, fallback `fuselage_width/2` marked assumed; never `inboard_rib_y` | `fuselage_width/2` only. **2026-08-15:** the fallback has data on the three real types (T-8a), so it no longer blocks step 13 |
| BM-2 | Fuselage load-path idealization | **split fuselage**: forward cantilever → front-spar post, aft cantilever + empennage → rear-spar post; continuous beam is a step-14 opt-in | continuous beam on two rigid posts (indeterminate now) |
| BM-3 | Missing attachment data | the LRA exporter **refuses** to build on the `±ds/2` h-tail fallback and on an unset `ref_axis_pct`; header states any assumed geometry it does accept (section centre, spar fractions) | build and mark assumed. **2026-08-15 (T-8a):** the discriminator is `TailSpanResult.attachment_basis` — refuse on `ATTACH_STRIP_PAIR` (not a fuselage dimension at all), accept-and-state `ATTACH_OUTLINE`, accept `ATTACH_FIN_TIP` outright. Gate on the basis, **not** on `attachment_assumed`, which the outline branch always sets |
| BM-4 | Gear / engine parent | explicit `mounted_on: fuselage \| wing` on the leg and engine inputs; inference by butt line vs `sob_y` as marked-assumed fallback | inference only |
| BM-5 | Node/element identity contract | `$ SLOADS-NODE` tags + sidecar map; production `RBE2` band; one band per node family | coordinate matching only |

## 6. Document updates this review implies (by file)

- `00_backlog.md`: rewrite the step 12 body per §2/R-10/R-11 (three artifacts,
  skeleton contract, transfer rule for all loads); step 13 body per R-3 (two
  behaviours, one source, BM-1); step 14 per R-12 (what it unlocks); Pri 1 note
  "feeds Pri 2 **and** F5.1"; Pri 16 folds into R-7d; add the F1 wing
  control-surface hinge geometry to Pri 10's body; re-sequence per R-13.
- `10_sbeam_roundtrip_ci_harness_plan.md` §1.1: scope hard constraint 1 to the
  per-component deck; add the sentence that the LRA model *starts* at the SOB.
- `11_balanced_airframe_cases_plan.md` §4: two rows (T7 tip transfer; gear /
  engine thrust) and a column for the LRA model.
- `09_distributed_empennage_loads_plan.md` §10: T-15/T-17 gain the hinge-line
  node placement for the LRA model (R-2), the identity gate between the two
  representations, and the wing-surface extension.
- `21_power_effects_wing_note.md`: P-6 thrust line → the hub/mount nodes (R-9).
- `CONVENTIONS.md` §1: replace the open torsion-reference question with R-7d's
  statement; §7 owner table gains the transfer rule (R-11) and node-family
  contract (R-10) owners with their guard tests.
- `PROGRAM_SPEC.md` sbeam bridge: the three-artifact statement (R-1) and the
  LRA-model section once designed.
- Schema (one bump, `DATA_DICTIONARY.md` regenerated): `SurfaceInput.sob_y_in`;
  `FuselageSection.z_centre`; `LandingGearLegInput.mounted_on`;
  `EngineInput.mounted_on`; wing control-surface hinge/actuator/butt-line
  fields; fixtures gain `ref_axis_pct = 0.40`.
- `bands.py` docstring: the new node/element families.
- `cspell.json`: any new terms.

## 7. What this note does not do

It does not decide the step 12 **transfer rule** (nearest-node vs tributary
interpolation) — the backlog body already frames that correctly and it is a
numerical choice inside R-11's contract. It does not touch step 14's section
properties. It does not propose any change to a FAR 23 calc path.
