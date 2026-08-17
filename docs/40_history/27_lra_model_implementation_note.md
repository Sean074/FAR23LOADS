# Step 12 implementation note — the LRA beam model (export + import)

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: implementation decisions of record, 2026-08-16.** The governing design
note is [`24_lra_beam_model_review_note.md`](../30_future/24_lra_beam_model_review_note.md)
(AGREED 2026-08-15): the target features F1–F8, the three-artifact statement
(R-1) and decisions BM-1…BM-5 are decided there and are not re-opened here.
This note records the choices note 24 §7 deliberately delegated to the
implementation — the transfer rule, the concrete topology, the id bands, the
gates and their expected numbers — under the step-12 backlog body as rewritten
from that note. Conventions: `docs/10_standard/CONVENTIONS.md` §1 (axes/signs),
§3 (units channels), §5 (ULT/SF contract).

## 1. What the deliverable is

One solvable SOL 101 deck per unit system, `<project>.lra_model.bdf` — the
**third artifact** beside the per-component decks and the assembled balanced
deck (note 24 §2): node lines on the load reference axes, `CBAR` chains with
the placeholder `PBAR`/`MAT1` (step 14 owns real stiffness), rigid ties
(`RBE2`) for the posts / attachments / gear / engine, and **the assembled
balanced cases' load sets transferred onto the model's nodes** — the same
cases, same `SUBCASE`/`SID` minting (`case_ids.balanced_subcase_id`), same
ULTIMATE boundary scaling as the balanced deck, expressed on a structural
idealization whose value is its internal loads at the named nodes.

Import (§6): an external `GRID`/`CBAR` model becomes the LRA — the same
transfer machinery lands the same load sets on the imported nodes under the
imported GIDs, mapped by the `$ SLOADS-NODE` contract.

## 2. The transfer rule (LM-1) — the one owner

**Decision LM-1 (note 24 §7's delegated choice): nearest-node transfer with the
exact lever-arm couple, not tributary interpolation.** A load `(F, M)` at `p`
applied to node `n` becomes `(F, M + (p − n) × F)`. Chosen because:

* it is **exactly** resultant-preserving per load — the plan-07 invariant on
  the transferred set closes to card-format precision by construction, with no
  distribution weights to tune;
* it is what the suite already does everywhere a load moves (the gear
  patch→trunnion transfer, the concentrated-mass offset couples, the step-13
  `sob_collapsed_load`), so it is one rule, not a second one;
* tributary interpolation splits a force across two nodes and preserves the
  resultant only in aggregate; internal loads between the two nodes then
  depend on the split, which is a modelling claim nearest-node does not make.
  The cost — a load's internal-load entry point is off by up to half an
  element length — is bounded by the chain's own discretisation.

The rule's **single owner is `export/coordinates.transfer_couple()`** beside
the axis maps (note 24 R-11), with a drift guard in `tests/test_lra_model.py`;
`sob_internal_loads`/`sob_collapsed_load` (step 13) are prior instantiations
and their docstrings now point at the owner.

A useful consequence: the balanced cases' wing strip loads sit on the calc's
25 %-chord line, and the wing chain sits on the LRA (40 % on the fixtures).
The chordwise offset couple `(p − n) × F` **is** the torsion transfer — the
LRA model needs no special-cased `to_loads_ref_axis` call, and the invariant
gate proves the transfer instead of assuming it.

## 3. Topology (LM-2…LM-7)

Free-free, like the balanced deck: one node clamped in six DOF (the forward
fuselage chain node nearest the front post that is in no `RBE2` — no rigid
element may touch the support, `roundtrip._supportable`, and clamping beside
the wing keeps every flexible path short: at the nose the SI/mm stiffness
conditions at 1.6e15, over sbeam's 1e15 refusal; here 2.8e14), and the
recovered reaction **is** the case residual ≈ 0. Internal member loads are the
value; the constraint proves the balance.

| member | nodes | connection |
|---|---|---|
| wing, right | SOB_R (interpolated onto the beam line at `sob_station().y`) → tip, the wing-net LRA stations outboard of the SOB | `CBAR` chain; **starts at the SOB** (note 24 R-3) |
| wing, left | mirror of the right chain | `CBAR` chain |
| centre box | one hub node C at the wing LRA centreline point | `RBE2`: C independent → SOB_R, SOB_L, F, A dependent (rigid, **not** a stiffness element — R-12's carry-through CBAR stays step 14) |
| fuselage, forward | outline section-centre nodes `(x, 0, z_c(x))` with `x ≤ x_f`, plus the front-spar post node F at `x_f` | `CBAR` chain ending at F — the **split-fuselage** cantilever (BM-2) |
| fuselage, aft | rear-spar post node A at `x_r`, plus section-centre nodes `x ≥ x_r` (fin-root / h-tail / gear / engine stations inserted) | `CBAR` chain starting at A |
| fin | root node at `(x_fin, 0, fin root waterline)` → the fin-span LRA stations | `CBAR` chain; root node `RBE2`-tied to the aft-chain node inserted at `x_fin` (R-5) |
| h-tail | full-span tail-span LRA stations, with attachment nodes inserted at `±attach_y` (conventional) or the centreline node (T-tail) | `CBAR` chain; attachments `RBE2`-tied to the aft-chain node at the h-tail LRA station, or the centreline node tied to the **fin tip** (T-tail) |
| gear | one node per leg at `attach` | `RBE2` to the parent per `carrier` (BODY → inserted aft/forward-chain node at `attach.x`; WING → nearest non-dependent wing LRA node) |
| engine | hub node at `prop_cg` + mount node at `engine_cg` | **one** `RBE2` per engine: parent beam node independent → {mount, hub} dependent (sbeam refuses chained RBE2, so hub→mount→parent is folded into one element) |

* **LM-2 — fuselage section-centre line.** `FuselageSection.z_centre`
  (schema v52) per section; unset sections default to
  `body_drag_waterline(project).z` and the deck header marks the line assumed.
  There is **one** fuselage LRA node per distinct station after merging the
  outline sections with the inserted special stations.
* **LM-3 — split fuselage is structural, not prose.** No element spans
  `x_f < x < x_r`: the forward chain's last element and the aft chain's first
  element end at the posts, so "forward body summed to the front-spar post" is
  the recoverable `CBAR` end force there, and the fore/aft split is geometry
  (the two cantilever sums), stated against `body_loads`' p103 spar reactions
  as a **reported comparison, not a gate** — the two are different models of
  the same joint (p103 reacts a moment over both spars; the split fuselage
  assigns each half-body wholly to one post) and forcing them equal would
  fake agreement. The deck header states both.
* **LM-4 — refusals (BM-3).** The exporter raises, naming the missing datum,
  when: the wing surface's `ref_axis_pct` is unset (R-7c — v52 makes the field
  `Optional`, `None` = "not entered", effective default 0.25 everywhere else);
  no SOB resolves (`sob_station() is None`); the project has no fuselage
  outline (no section-centre line to build); `carry_through()` returns `None`
  (no posts); or the h-tail attachment basis is `ATTACH_STRIP_PAIR` (not a
  fuselage dimension). `ATTACH_OUTLINE` is accepted **and stated**;
  `ATTACH_FIN_TIP`/`ATTACH_ENTERED` accepted outright. Accepted-but-assumed
  geometry (section centres, spar fractions, SOB fallback) is listed in the
  header.
* **LM-5 — gear parent (BM-4).** The already-shipped `LandingGearInput.carrier`
  (decision G-2, `BODY | WING`, no default) **is** BM-4's `mounted_on` for the
  gear — a second field would be a duplicate. The engine gains the new field:
  `EngineInput.mounted_on` (`"fuselage" | "wing"`, `None` = infer by
  `|engine_cg.y| > sob_y`, marked assumed in the header).
* **LM-6 — control surfaces.** The elevator/rudder hinge + actuator nodes ship
  as **tagged skeleton nodes with their rigid parent ties** (no chain of their
  own yet: `CBAR`s between hinge nodes that are each rigidly tied to the
  parent would be R-12's redundant hinge set) wherever
  a surface runs `control_load_mode = "discrete"` (T6 geometry entered, T-17).
  No shipped fixture enters hinge geometry and no *balanced case* carries a
  control-surface load set, so on every shipped fixture the deck simply has no
  control chain — exercised by a synthetic-project test instead, exactly like
  the engine node before thrust ("the skeleton is complete before the load
  exists", R-9). R-2's full shape — chain moved to the hinge line with the
  folded torsion un-folded, and the two-representation torsion identity gate —
  activates with the case family that actually applies a control load to this
  model, and is recorded against Pri 10 (which also consumes the new wing
  control-surface schema fields: `AileronLoadsInput`/`FlapLoadsInput`
  `inboard_y_in`/`outboard_y_in`/`hinges_span_in`/`actuator_span_in`, entered
  never invented).
* **LM-7 — load routing.** Each `BalancedLoad` transfers to the nearest node
  of the member its `source` names: `wing-*` → that side's wing chain
  (inboard-of-SOB strips therefore land **on** the SOB node — R-3's collapse,
  by the same rule, not a special case); `htail-air`/`tail-air` → the h-tail
  chain; `vtail-air` → the fin chain; `gear-*` → the gear nodes;
  `ground-lift` → that side's wing chain (it is the wing spanwise shape);
  `body-*`/`fuselage-cm` → the fuselage chains; `closure-*`,
  `aileron-roll` and anything unrecognised → nearest node in the whole
  skeleton (relief acts at each mass's own position; the header states the
  rule). A member that was refused/absent falls back to nearest-in-skeleton
  rather than dropping the load — the invariant gate is on the full set.
* **T7 exclusion (R-6).** On a T-tail the h-tail beam is attached to the fin
  tip, so the fin deck's lumped T7 tip transfer is **never** applied here —
  the balanced cases already carry the tail load on its own nodes and the
  solver recovers the joint load. Plan 11 §4 carries the authority row.

## 4. Identity contract (BM-5) — bands and tags

New rows in `sloads/export/bands.py` (all allocated only by
`export/lra_model.py`): GIDs `lra-wing-left 7101+`, `lra-fuselage 7601+`,
`lra-centre 7801+`, `lra-engine 7811+`, `lra-attach 7861+` (h-tail attachment
pair, fin root, T-tail joint); EIDs `lra-cbar 11001+` and the **production**
`lra-rbe2 12001+` (the 900001+ band stays test-only), both `clear_of_gids`.
Reused, byte-traceably, because the registry proves them disjoint: `wing-stick`
(right wing stations), `lra-sob` (index 0 = R, 1 = L), `tail-span-*`
(h-tail/fin stations), `tail-control-*` (hinge/actuator), `balanced-gear`
(gear nodes), `spc`, and the balanced `SUBCASE`/`SID` bands.

Tags, one comment line above the `GRID`: `$ SLOADS-NODE <family> <side>` with
family ∈ {`lra-sob`, `lra-post`, `lra-fin-root`, `lra-fin-tip`, `lra-attach`,
`lra-gear`, `lra-engine-mount`, `lra-engine-hub`, `lra-hinge`, `lra-actuator`}
and side ∈ {`R`, `L`, `C`, `F`, `A`} (`F`/`A` = the front/rear-spar posts).
The step-13 wing stick deck's `lra-sob R` tag is the same contract.

## 5. Gates (benchmark-first, CI)

1. **Plan-07 invariant on the transferred set** (the acceptance gate the
   backlog names): for every case, `equilibrium.deck_resultants` of the LRA
   deck equals the balanced deck's, same SID, same reference point, at
   `closes()` tolerance — forces and all three moments. Expected: identical to
   card format (~1e-6 relative); the transfer is exact in arithmetic.
2. **Free-free proof through the solver**: the support node's recovered
   reaction ≈ 0 at `closes()` scale on every subcase (round-trip CI, both unit
   systems, the fixtures that build). **Known sbeam limitation, pinned as a
   strict xfail:** the regional jet's SI (mm) deck is refused by sbeam's
   dense-path 1e15 condition heuristic — a units artifact (the same matrix
   Jacobi-equilibrated conditions at ~1.3e9, and the Imperial twin solves
   exactly); the deck is valid bulk data and solves in any solver that
   equilibrates before its singularity check.
3. **SOB internal load, two ways on this model**: solver `CBAR` end force in
   the first element outboard of SOB_R equals the closed-form sum of the
   transferred cards outboard of it (rotation computed from the element
   geometry, the step-13 sign map) — all six components.
4. **Post sums**: the forward chain's last-element end force equals the
   closed-form sum of the cards on the forward chain; same for the aft chain's
   first element (which is the "aft body + empennage → rear-spar post" number).
5. **Byte gates**: per-component and balanced digests unchanged except the
   deliberate `ref_axis_pct = 0.40` fixture wave (R-7a/R-14), each file's move
   with its own CHANGELOG line; `ga6_normal`/`concept_heavy` (no fuselage
   outline) refuse with the stated error, and the CLI/Export page surface the
   refusal as a stated skip, not a failure.
6. **Import round-trip**: exporting the model, re-importing it, and
   transferring the same cases reproduces the exported card set node-for-node
   (the tags map every family); a doctored import whose tagged SOB is > 2 in
   (`LRA_IMPORT_TOL_IN`) from the geometry value fails loudly (T1 validator
   pattern).

## 6. Import contract

`lra_import.py`: `read_lra_model(text)` parses the `GRID`/`CBAR` subset plus
`$ SLOADS-NODE` tags (a sidecar JSON map `{family-side: gid}` is accepted as
the tag substitute); `lra_loads_on_imported_model(project, model, system)`
routes each balanced load by LM-7 against the imported node set — a family the
import tags gets its own nodes; a family it does not tag falls back to
nearest-imported-node **marked assumed in the header**. The imported GIDs win
(the imported numbering is the consumer's); the emitted file is
FORCE/MOMENT + subcase map only, to splice into the consumer's own model.
Tolerance validation: every tagged node within `LRA_IMPORT_TOL_IN = 2.0` in of
the geometry-derived position for its family, else raise naming both points.
An imported beam line is the consumer's elastic axis by definition — the
header states R-7d's sentence and closes the CONVENTIONS §1 open question.

## 7. Explicitly out of scope (stated deferrals)

* Real section properties, the continuous-fuselage opt-in, the carry-through
  CBAR, redundant hinge sets — step 14 (R-12).
* The hinge-line reposition + torsion identity gate and the wing
  control-surface chains — with Pri 10 / the discrete fixture data (LM-6).
* Power-effects thrust on the hub node — the P-6 case family; the node ships,
  the `FORCE` is absent until then (R-9).
* `mass_cards` CONM2 attachment to the mount node — the CONM2 set is the
  consumer-solves-inertia channel (R-11); moving its attach point is a
  mass-deck change and rides with the power-effects step.
* The fin-root datum fix (`z_centre + height/2`) — its own backlog row; this
  step only adds the `z_centre` field that row needs.
