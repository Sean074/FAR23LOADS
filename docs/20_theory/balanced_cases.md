# Balanced Free-Free Airplane Cases — the Balancing Method

How `sloads/modules/balance.py` assembles a **full-span, free-free airplane load
case** — aero and inertia together, wing tip to wing tip, nose to tail — and
closes it so the exported deck solves in sbeam with **no constraint doing any
work**. With worked examples on the shipped fixtures: a symmetric wing case, an
antisymmetric (rolling) wing case, the ±β empennage cases on a conventional low
tail and on a T-tail, the unsymmetrical horizontal-tail case of FAR 23.427(a),
and the ground/landing families of FAR 23.471–23.499.

- **Authority:** axes/signs/seam rule/closure charter in
  [`CONVENTIONS.md`](../10_standard/CONVENTIONS.md) §1 and §7 (this document
  explains; it never overrides). Module spec:
  [`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md) "Balanced cases and the
  assembled deck". Decision records: plans
  [11](../30_future/11_balanced_airframe_cases_plan.md) (B-1…B-8) and
  [13](../40_history/18_b8a_lateral_closure_plan.md) (L-1…L-8) and
  [18](../40_history/23_step10_ground_cases_plan.md) (G-1…G-13, the ground
  families, §9), and decision
  **D-R8** in [`03_resolved_decisions.md`](../40_history/03_resolved_decisions.md)
  (the 23.427(a) family, §8).
- **Code:** `sloads/modules/balance.py` (assembly + closure),
  `sloads/rigid_body.py` (the relief field, single owner),
  `sloads/gear_loads.py` (the gear free body the ground families apply),
  `sloads/export/balanced_deck.py` (the deck),
  `sloads/export/coordinates.py` (reflection, single owner).
- **Gates:** every number quoted here is pinned in CI —
  `tests/test_balance.py`, `tests/test_rigid_body.py`,
  `tests/test_gear_report.py` (§10 maps figure → test).
- **Units:** Imperial internal (lb, in, lb-in); loads in this document are
  **LIMIT** (the ×1.5 ultimate factor is applied once at the export boundary,
  per the load-output contract). Frame: `x` +aft, `y` +starboard, `z` +up;
  moments by the right-hand formulas of `balance.resultant6`.
- **Status:** every family in this document is **shipped and gated** — the wing
  symmetric cases (steps B2–B6), the antisymmetric rolling cases (B7), the
  six-DOF rigid-body closure (B8a-2), the lateral empennage cases (B8a-3), the
  unsymmetrical horizontal tail (D-R8, §8) and the ground/landing families
  (step 10 piece 3, §9). Figures marked *design of
  record* are the plan-13 baseline measurements the lateral assembly was built
  against; where the shipped gate states a different number, the gate is
  authoritative and says so.

---

## 1. The problem, and the shape of the solution

The airplane has always balanced **at trim**: the flight-envelope balance closes
`LZW + LT = Nz·W` exactly, and `test_concept_closure` has asserted it for a long
time. What never inherited that balance was the **distributed** load set — the
wing spanwise distribution, the tail load, the fuselage inertia and the trim
solve were four separate calculations that nothing assembled. Each per-component
deck papered over this by taking a free-body cut and clamping the model at it.

A free-free deck cannot. sbeam's SOL 101 has no inertia relief and no `SUPORT`
entry, so a full-airplane model must balance **by construction**: every applied
load card, summed over the whole deck, must produce zero force and zero moment
about any point. The method is therefore, in one sentence:

> **Assemble every load the airplane actually carries, at the flight condition
> the case actually describes, from the one mass model; measure what fails to
> balance; then close the remainder the way flight does — by accelerating the
> airplane — with the residual stated, gated, and part of the deliverable.**

The proof is structural: the deck is exported on a **determinate support** (one
node, six DOF), so the support reaction *is* the residual, and the CI gate is
that sbeam's recovered reactions are ≈ 0. A constraint that carries no load is
the free-free demonstration.

## 2. The applied set

One `BalancedLoad` list per case, each load tagged with its `source`:

| source | What it is | Where it acts |
|---|---|---|
| `wing-air` | Spanwise strip lift/drag + **free** section moment, both wings | strip 25 % chord, per side |
| `tail-air` | The balancing tail load `LT` from the case's own V-n point | tail CP station, centreline |
| `wing-inertia` | The loading's `WING`-tagged item mass, spread over WINGINER's spanwise shape, × `−n_z` | strip 50 % chord, per side |
| `body-inertia` | Every item the assembly does not spread, × `−n_z` | each item's own `(x, y, z)` |
| `fuselage-cm` | The fuselage's share of the trim pitching moment (lumped free moment) | wing AC, centreline |
| `aileron-roll` | The FAR 23.349 unbalanced rolling moment `−UNB` (rolling cases only, lumped free couple) | wing AC, centreline |
| `vtail-air` | The fin's distributed side load from `tail_span` (`fy` per strip, `mzz` torsion) | fin strip stations on the L-1 waterline |
| `htail-air` | The 23.427(a) tail load from `tail_span`, distributed full span (`fz` per strip, `myy` torsion) — **replaces** `tail-air` on that case | h-tail strip stations, both halves |
| `engine-thrust` | The user-entered `EngineInput.thrust_lb`, one axial force per engine, `fx = −T` (flight families only, §2.1) | that engine's hub, `prop_cg` |
| `gear-main`, `gear-nose` | LANDLOAD's own wheel reaction + its patch→node couple (ground families only, §9) | the leg's reference point |
| `ground-lift` | `L × W` on the AIRLOADS spanwise shape, along the ground line (ground families 1–12 only, §9) | strip stations, per side |
| `closure-n`, `closure-roll/pitch/yaw`, `closure-self` | The rigid-body relief (§4) | on the modelled masses |

The ground families are the exception to the first two rows: they have no flight
condition, so they carry no `wing-air` and no `tail-air`, and their only aero is
`ground-lift` (§9).

Five rules govern the set. Each was measured, not assumed — the cost of breaking
it is part of the record:

1. **The wing load is recomputed at the balanced case's own flight condition**
   (the V-n point's `cl`/`V`/`n_z`), never taken from the hand-entered
   `wing_mass.cases`, which may describe a *different* condition. Assembling two
   halves at different conditions put the force residual at 10–37 % of `n·W`.
   The entered distributions are untouched and remain the FAR 23 deliverables.
2. **A cumulative torsion is not a free moment.** `WingStationLoad.myy` is the
   torsion about the root reference and already contains the sweep/dihedral
   transfer of outboard shear. An assembly applies position offsets itself, so
   only the **section `Cm` free moment** may ride on the strip — recovered by
   subtracting the transfer accumulations back out (`balance._free_moments`).
   Using the cumulative figure double-counts the transfer: 20.5 % of `n·W·MAC`
   instead of 0.12 %. (ga6 PHAA root torsion −79,003 lb-in = −60,474 sweep
   transfer − 9,594 dihedral transfer − 8,935 actually-free moment.)
3. **The mass is `weight.items`, once** (decision B-2 — the mass SSOT). Wing
   inertia is the loading's `WING`-tagged items spread over WINGINER's spanwise
   *shape* and shifted so the set's centroid is the items' own; everything else
   is carried at each item's entered position. Taking WINGINER's own panel mass
   instead double-counts whatever is in both models (wing-tank fuel on two
   fixtures: 12–13 % of `n·W`). The guard: Σ modelled mass equals the payload
   case's weight to 1e-9, every case.
4. **A load that a free-body cut introduces is never applied in the assembled
   model** (the seam rule, plan 11 §4). The wing carry-through reaction is
   *internal* to a full-span model — the solver recovers it. `assemble` never
   reads `body_loads`, and `carry_sources_absent` is the drift guard.
5. **A real load with no distributed carrier is lumped and labelled, never
   dropped.** The trim's `Cm` covers wing *and* fuselage; the distributed wing
   carries only its own section `Cm`. The difference — the fuselage's Munk
   moment — is applied as one free moment (`fuselage-cm`) until M4-19 distributes
   it. Omitting it would leave a moment residual of the same size for the closure
   to absorb silently: a real aero load disguised as a correction. It is a slope
   term and **changes sign with `α`**: −6.6 to +4.9 % of `n·W·MAC` on
   `ga6_normal`, −8.5 to +5.8 % on `concept_regional_jet` (an earlier "+4.3 to
   +6.3 %, destabilising" reading here covered the symmetric wing conditions
   only; corrected 2026-08-15).
6. **The airplane's non-wing drag is carried, and where it acts is stated.**
   The FLTLOADS trim balances the airplane-less-tail drag from the *polar*; the
   assembled model's only `fx` is the wing strips' own chordwise force. The
   difference is the fuselage, the nacelles and the rest of the parasite drag,
   and until 2026-08-15 nothing carried it — `residual_fx` *equalled* the wing's
   drag, and the couple the missing force left about the CG was the whole pitch
   residual. It is now the `body-axial` load. Two things about it are worth
   stating here because neither is obvious:

   - **It is genuinely parasite drag.** Both models resolve through the same `α`,
     so the body-axis gap splits exactly into wind-axis parts; `ΔL/L` comes out
     ≤ 0.6 % while `ΔC_D` is a near-constant **−0.018 across all seven ga6
     cases** — a `C_D` offset independent of `C_L`, which a lift-model
     disagreement would not produce.
   - **Where it acts is a stated input, not a derived one.** `z_b` is the only
     free parameter (a pure axial force contributes `my = (z − z_cg)·fx`, with no
     `x` term), and the suite has **no body-centreline datum** to derive it from —
     `root_waterline_z` is the *wing* root. Absent an entered
     `body_drag_waterline_z` it is the wing reference plane, marked `assumed`,
     which is where the trim itself assumes the whole airplane's drag acts. Design
     note [`20_body_drag_carrier_note.md`](../40_history/24_body_drag_carrier_note.md)
     §8.1; the `ΔC_D` diagnostic is reported per case because carrying the load
     makes the applied axial resultant equal the trim's `dx` by construction.

### 2.1 Engine thrust — the one load nothing balances (#10)

Carved out of design note
[`21_power_effects_wing_note.md`](../30_future/21_power_effects_wing_note.md),
whose seven-step wake plan stays parked. The user enters one thrust per engine
(`EngineInput.thrust_lb`) and it becomes a `FORCE` at that engine's hub — the
node the LRA skeleton has carried since R-9 and, until this step, never had a
load on. Four rules, all in the single owner `balance.hub_thrust_set`:

1. **Sign and station.** `x` is +aft (`CONVENTIONS.md` §1), so thrust is
   `fx = −T`, acting at `prop_cg`; `engine_cg` is the fallback for a project
   that entered a mount and no propeller, and thrust with **neither** raises,
   naming the datum, rather than being placed on a guess.
2. **The line is axial.** The thrust-line incidence `i_T` and toe `τ` (note 21
   decision P-6) have no fields and no estimator; inventing them would put a
   lateral and a vertical component into every case on an assumed geometry. The
   propeller normal force, the slipstream band and every DATCOM power derivative
   stay with note 21.
3. **Flight families only.** A ground case's thrust rating — take-off on a
   ground roll, max-continuous elsewhere — is note 21's parked power-policy
   table, and this step carries one user-entered value with no rating. The
   ground case *states* the entered thrust and does not apply it.
4. **Nothing balances it, and that is the physics.** The V-n point the case is
   assembled at is thrust-free: FLTLOADS balances the airplane's drag from the
   polar and knows nothing about power. So the applied thrust is a genuine
   unbalance in two degrees of freedom — `Fx` in full, and its couple
   `−T·(z_hub − z_cg)` in pitch — and the closure carries both:

   ```
   n_x = (D − ΣT) / W          (§4's longitudinal DOF, +aft)
   ```

   which is the carrier the assembled model has always lacked. A powered case is
   therefore not in longitudinal or pitch trim by construction, and the 1 %
   pre-closure gate does not apply to its `My` — the same standing as the
   23.427(a) maneuver tail load (§8) and the lateral families (§7). What is
   gated instead is stronger than a bound: the residual *is* the thrust, in
   closed form, and `tests/test_hub_thrust.py` G-3 asserts the identity. G-4
   asserts the one that names the physics — a case whose entered thrust equals
   its own net drag closes at `n_x = 0`.

**Asymmetric installations are stated, not handled.** A different thrust per
engine (or one engine of a pair) yaws the airplane, and that yaw is a moment
`is_handed` cannot see: decision L-6 measures lateral force and rolling moment,
and a pure `fx` off the centreline makes neither. So the case is emitted
unhanded, the closure's `ṙ` carries the moment in full, and the case note says
both that no twin was minted from the asymmetry *and* that a twin got from
another source (a fin load, a 23.427(a) split) mirrors the installation along
with everything else — making that twin the mirror-image airplane's case, not
this one's. Reflection with engine loads is note 21 §4.4's own decision and
stays parked with it; the mirror installation is a project the user enters.
Gate G-11.

Off unless entered, which is every shipped fixture: the suite's cases were
exactly zero-thrust before this step and are bit-for-bit unchanged after it
(G-1).

## 3. The residual — measured before closure, and part of the deliverable

The six-component resultant of the applied set is taken about the case's CG
(`balance.resultant6`) **before** any relief is applied. That number is the
physics: how well the independently-computed wing, tail, and inertia sets agree.
The acceptance gate (plan 11 §6) sits on it, not on the corrected result:

```
|ΣFz| / (n·W)        < 2.5 %    (force -- `balance.FORCE_RESIDUAL_ACCEPTANCE`)
|ΣMy| / (n·W·MAC)    < 1 %      (pitch  -- `balance.RESIDUAL_GATE`)
```

**The two halves carry different numbers (owner, 2026-08-22, closing CR-C-2).**
Plan 11 stated a flat 1 % for both. Pitch meets it everywhere with an order of
magnitude to spare (0.07–0.84 % on the judged family). Force does not: the type
fixtures reach 1.209–2.360 %, in an ordering that tracks **fixture lift-model
quality** rather than the assembly — `ga6_normal`, the one fixture whose aero and
planform come from a printed source, is best at 0.624 %, and the concept
configurations are worst. None of the six is a printed oracle; the balanced
full-span model is a mission-extension deliverable with no Appendix A/B figure
behind it, and the FAR23 replication core stays oracle-locked independently of
this number. So the force acceptance is stated at the value the suite already
enforced as its hard stop, and the report judges force against the same number
the tests do — `tests/test_balance.py`'s per-fixture, per-family
`_FORCE_RESIDUAL_RATCHET` is unchanged beneath it and remains the regression
guard. A **clamped** case (§ design note 20 D-4: the trim α outside the polar's
trusted window, the forward non-wing force not applied) is out of trim by exactly
that force and its couple, so it is gated per case instead and is split out by
`balance.residual_gate_family`.

Neither floor is noise, and the two have **different** causes (measured
2026-08-15 — the element-count study behind backlog Pri 5):

- **Force.** The ~0.3 % floor on the ga6 is the strip lift distribution's
  integral against the trim's closed-form `CL·q·S` — the difference plan 11 R3
  predicted. It is a *model* difference, not a quadrature error: it converges to
  −42.3 lb / 0.327 % on ga6 PHAA as `elements` → ∞ (the −34.6 lb seen at the
  default 20 is that floor partly cancelled by the quadrature transient).
- **Pitch.** The pitch residual *was* `(zw − zcg)·(ΣFx_wing − dx)` almost in full
  — the assembled model carried **no non-wing drag** — and it was flat in
  `elements` (RJ PLAA 1.041 % from 20 to 640), so no refinement reached it. Since
  the `body-axial` load landed (§2 item 6) it is the lift-model floor too:
  **0.014–0.086 % across every fixture and family**, and the per-fixture ceiling
  the RJ's low-CL cases needed is retired.

The residual and the relief applied are stated in the result, the UI and the deck
`$` header (CONVENTIONS §1: *the residual is part of the deliverable*).

**Two degrees of freedom are deliberately not gated this way**, because in them
the airplane is *supposed* not to balance:

- **`Fx` (drag).** Nothing else in the assembled model reacts drag — the suite
  has no distributed thrust. The longitudinal closure *is* FAR 23's `n_x`.
- **`Mx`/`Mz` on a handed case.** A rolling case's `Mx` residual is exactly the
  applied aileron couple; a yawing case's `Mz` residual is the fin load's whole
  yaw moment. The airplane rolls, or yaws — the residual is the case's content,
  and the gates for it are identities and pinned values (§5, §7), not smallness.
- **`Fz`/`My` on the 23.427(a) case** (§8). Its applied tail load is a
  *maneuver* load and replaces the trim tail load its V-n point balances at, so
  the airplane is genuinely out of trim: the residual is that mismatch in full
  (49.8 % of `n·W` on the ga6) and the vertical and pitch closure is the motion
  it causes. What is gated at 1 % is the case's **trim half** — the same case
  with the lumped trim load restored.
- **Every component of a ground case** (§9). The inertia set enters at
  `n_z = 0`, so the pre-closure resultant *is* the gear reactions plus the lift,
  and the load factors are the answer rather than an error. The gate is
  LANDLOAD's own closed form, `NVP`/`NDP`/`NS` from the solved field at
  `rel_tol 1e-9`.

## 4. The closure — one rigid-body field

Whatever the applied set fails to balance is closed the way flight closes it:
the airplane accelerates, and every mass reacts. The relief is the **rigid-body
d'Alembert field**, written once in `sloads/rigid_body.py` (decision L-2):

```
f_i = −w_i (n + ω̇ × r_i)          moment about the CG:  −[I]{ω̇}

translation:  n = (n_x, n_y, n_z) = ΣF / W        (decoupled ratios, in g)
rotation:     [I]{ω̇} = {ΣM}                       (one coupled 3×3 solve)

roll   ṗ  →  fy = +w·ṗ·dz ,  fz = −w·ṗ·dy
pitch  q̈  →  fx = −w·q̈·dz ,  fz = +w·q̈·dx
yaw    ṙ  →  fx = +w·ṙ·dy ,  fy = −w·ṙ·dx
```

Six degrees of freedom, six properties worth knowing:

- **The translational three stay decoupled ratios** `n = F/W` because the mass
  set's centroid *is* the CG reference — a uniform load factor produces no
  moment, and the load factors come out directly in g, the way FAR 23 states
  them. Everything is **weight-space**: items contribute `w_i` (lb), inertias
  are `Σw·d²` (lb-in², directly comparable with `MassItem.ixx` and WTONECG),
  and angular accelerations come out in `1/in` (g per inch of arm) —
  `rigid_body.radians_per_s2` is the only conversion.
- **The rotational three are one coupled solve**, because `Ixz` is first-order:
  8.4 % of the ga6's own pitch inertia. Three independent ratios would be wrong,
  not approximate — a rolling airplane with non-zero `Ixz` yaws (§5).
- **Every angular acceleration applies two force components.** The omitted
  companion is the whole difference between `Σw·d²` and a moment of inertia,
  and it is not uniformly small: measured, the one-component ancestors were off
  by ≤ 0.08 % (pitch), ~7 % of a peak node load (roll) and 55 % (yaw) in their
  own degrees of freedom — three different magnitudes from one omission, which
  is why the field has one owner instead of five special cases.
- **A mass carried as a point still resists rotation about its own centre**
  (decision L-3): items the assembly does not spread contribute
  `−[I_self]{ω̇}` as a free moment at their node (13.3 % of the ga6's `Izz`).
  Items the assembly *does* spread (today: exactly the wing) must not — the
  spread already is that inertia (entered 4.444e6 lb-in² vs spread 4.288e6,
  −3.5 %). The predicate has one owner,
  `mass_distribution.assembly_distributes_mass`.
- **The relief is spread over the inertia loads already in the model** — the
  same masses, at the places the assembled model actually carries them (wing
  mass out along the span, not on the centreline where the database enters it)
  — so no relief lands on a node the airplane has no mass at.
- **After closure, all six resultants about the CG are zero to machine
  precision** (≤ 2e-16 of `n·W`), and the same closure is re-derived from the
  exported deck's own `GRID`/`FORCE`/`MOMENT` card text — which is what caught
  distinct loads collapsing onto shared nodes (3.9–21.9 % of deck balance,
  invisible in memory).

**Handedness** (decisions B-6/B-7): the starboard case is computed; the port
twin is its **reflection** through the single owner in `export/coordinates.py`
(`y → −y`; forces `fy` negates; moments `mx`/`mz` negate, `my` does not — a
moment is an axial vector). The FAR 23 core never sees handedness; the case id
gains an `L`/`R` suffix. Everything even under the mirror is *identical* in the
twin (vertical, longitudinal, pitch); everything odd reverses (`ṗ`, `ṙ`,
`n_y`, the couple). A case is handed iff its **applied** set carries lateral
content, evaluated pre-closure (decision L-6) — read from `Σ|fy|` and applied
couples, not from a net that may cancel.

## 5. Worked example 1 — symmetric wing case (ga6_normal, PHAA)

`ga6_normal`, condition **PHAA** at V-n point 22 (STALL +N), CG2
(x 77.49, z 93.0), `n_z` = 3.8017, W = 3400 lb, MAC 69.25 in. Target
`n·W` = 12,926 lb.

**The vertical ledger** (both wings assembled, LIMIT):

| source | ΣFz (lb) |
|---|---|
| `wing-air` (both sides) | +12,934.7 |
| `tail-air` (`LT`) | −43.4 |
| `wing-inertia` (330 lb of WING items × −n_z) | −1,254.6 |
| `body-inertia` (3,070 lb of beam items × −n_z) | −11,671.3 |
| **residual `ΣFz`** | **−34.6** |

The inertia rows sum to −12,925.9 = −n·W exactly (the mass model weighs the
case); the air rows overshoot by 34.6 lb — **0.268 % of n·W**, the strip-lift
floor above (which converges to −42.3 lb / 0.327 % as `elements` → ∞; the value
at the default 20 is that floor net of the quadrature transient). The lumped
`fuselage-cm` moment for this case is +44,095 lb-in.

**The residual, about CG2:**

| DOF | residual | fraction | closed by |
|---|---|---|---|
| `Fz` | −34.6 lb | 0.268 % of n·W | `Δn_z` = −0.0102 g |
| `Fx` | −2,248.8 lb | (drag — nothing reacts it) | `n_x` = 0.661 g (fixture entered 0.6065) |
| `My` | +1,043 lb-in | 0.117 % of n·W·MAC | `q̈` = +2.52 deg/s² |
| `Fy`, `Mx`, `Mz` | 0 exactly | — | lateral DOF solve to 0 (mirror symmetry) |

The pitch relief solves on the **real** `Iyy` of the assembled set — 1,974.7
slug-ft² including `Σw·dz²` and the point-item self-inertia — not on `Σw·dx²`
(the G5 reduction gate pins that `q̈ = My/Iyy` and that `Iyy` exceeds the old
planar sum). After relief, all six resultants are zero to machine precision, in
memory and re-derived from the deck's cards.

## 6. Worked example 2 — antisymmetric wing case (ga6_normal, ACRL)

Condition **ACRL** (FAR 23.349 accelerated roll) at V-n point 40, CG2,
`n_z` = 3.2494. The symmetric half is Example 1 over again (residuals `Fz`
0.237 %, `My` 0.126 %). What is new is the hand.

**The applied couple is lumped; the reaction is distributed.** The entered
unbalanced rolling moment is `UNB` = −149,043 lb-in, applied as a single
labelled free couple `mx = −UNB = +149,043` at the wing AC — WINGINER's
Appendix-A-locked model never distributes the aileron's own lift increment (the
suite has no aileron butt lines; stated in-band), so neither does the assembly.
The pre-closure `Mx` residual is therefore **exactly** the applied couple, and
gated as such: the airplane is *meant* not to balance it. It rolls.

**The coupled rotational solve** on the assembled tensor
(Ixx 1,166.7, Izz 2,933.5, Ixz 90.8 slug-ft²; Ixy = Iyz = 0 by mirror
symmetry):

| quantity | ga6 ACRL | RJ ACRL |
|---|---|---|
| applied couple `−UNB` | +149,043 lb-in | +600,000 lb-in |
| roll acceleration `ṗ` | 611.4 deg/s² | 72.0 deg/s² |
| **induced yaw `ṙ` (via `Ixz`)** | **+18.93 deg/s²** | **−0.993 deg/s²** |
| companion `fy` at the peak node | 89.8 lb | 551.9 lb |
| roll field's own `fz` at the peak node | 44.6 lb | 100.9 lb |
| wing-span share of the roll moment | 0.795230 | 0.769455 |

Three physical facts in that table:

1. **A rolling airplane with non-zero `Ixz` yaws.** The induced yaw vanishes
   when `Ixz` is zeroed (asserted in G6) — it is the coupling, not an artifact.
2. **The companion `fy = +w·ṗ·dz` is larger than the roll term already in the
   deck**, because `fz = −w·ṗ·dy` reaches only the wing strips (every database
   item sits at `y = 0`) while the companion throws every mass off the roll
   axis sideways.
3. **The two-producer check.** The closure's roll strips reproduce WINGINER's
   oracle-locked unit-roll distribution `ur·fz_r` **strip for strip in shape**
   (same ratio on every strip, to 1e-9), and the ratio — the wing span's share
   of the roll moment — is pinned per fixture and independently equals
   `ṗ / (Mx / Σw·y²)`. The share is below 1.0 because the assembled airplane
   reacts about a fifth of the aileron moment on mass off the roll axis
   (`Σw·dz²` + self-`Ixx`), which a wing-only model has no term for.

The case is emitted as a **handed pair**: `ACRL·R` computed, `ACRL·L` =
`handed_twin(R)` by reflection. The twin's `Fz`/`Fx`/`My`/`Δn`/`q̈` are
bit-identical; its `ṗ`, `ṙ`, `Δn_y` and couple negate; the pairwise
load-by-load mirror is asserted, not just the totals.

## 7. The lateral balance — the empennage cases

> **Status.** Shipped and gated: decisions L-1…L-8, the fin waterline (B8a-1),
> the six-DOF closure (B8a-2) and the case assembly itself (B8a-3, 2026-08-09).
> Figures marked *(baseline)* below are plan 13 §3's measurements, kept because
> they are what the design was agreed against; the **shipped** values are pinned
> by gate G10 (`test_the_lateral_cases_are_pinned`) and win where the two
> differ. Note the baseline `ψ̈` figures
> were computed on the placement-only `Izz` (pre-L-3); the shipped closure
> solves on the full tensor, so the ga6 figures will land ~13 % lower (§7.3).

Each of the four SELECT vertical-tail conditions — `SUDDEN RUDDER`,
`YAW TO SIDESLIP`, `YAW 15 NEUTRAL`, `SIDE GUST` — becomes a balanced full-span
case: the shipped symmetric machinery at the condition's V-n point (all four sit
near `n_z` ≈ 1) **plus** the fin's distributed side load, closed in six DOF and
emitted as a handed pair. The lateral equilibrium about the CG:

```
ΣFy:   L_v − W·n_y = 0                    →  n_y = L_v / W
ΣMz:   L_v·(x_v − x_cg) + Σ mzz = Izz·ψ̈   →  ψ̈  from the coupled solve
ΣMx:  −L_v·(z_v − z_cg) = Ixx·ṗ + Ixz·ψ̈   →  ṗ  from the coupled solve
```

**The pre-closure lateral residual is the entire applied lateral aero, by
construction.** Unlike the symmetric case, where aero and inertia nearly cancel
to a 0.3 % residual, there is nothing for a rudder kick to cancel against — the
lateral aero (the fin's load, plus the wing-body term of §7.4 when enabled) is
reacted by rigid-body motion alone. So the 1 % smallness gate is meaningless
laterally, and the replacement gates (decision L-5) are: the yaw identity
against ONENGOUT's oracle-locked `ψ̈ = M/Izz` (G1), the symmetric half still
meeting its own 1 % gate with the fin load (and the body term) removed (G9), and
the lateral quantities pinned per fixture (G10).

**Decision L-7, as shipped 2026-08-17 (design note 19 rev. 3):** the fin is no
longer the only lateral aero the suite can apply — §7.4 — but the wing-body term
is **off by default**, and with it off the two lateral degrees of freedom err in
opposite directions: `ψ̈` is over-stated (the body's couple opposes the fin's;
conservative) and `n_y` is **under**-stated (the body-and-wing side force adds
to the fin's; not conservative). Every lateral case states which state it is in
and the numbers (decision L-7.16); the fin's own design load is SELECT's,
unchanged.

### 7.1 Where the fin sits — the L-1 waterline

The roll equation needs the fin's height above the CG, and no fixture enters
one, so it is resolved once, with the provenance (`assumed`) carried into the
result and the deck header:

```
vtail root waterline:
  explicit input        →  use it                                    (assumed = False)
  T-tail with h_tail_z  →  root_waterline_z + h_tail_z − vtail_span  (assumed = True)
  otherwise             →  root_waterline_z + fuselage_height / 2    (assumed = True)
```

The conventional branch is the suite's established "top of the fuselage" (the
three-view has drawn every fin from it since step G6); the T-tail branch is the
inverse of the three-view's own default, which puts a T-tail's horizontal
surface at the fin tip. Before this fix the fin was modelled *below* the CG —
the ga6 roll arm came out **−64.5 in** (reversed sign) and the RJ's **−1.0 in**
(no magnitude): no lateral roll number meant anything, which is why the
waterline was step 1.

### 7.2 Worked example 3 — conventional low tail (ga6_normal, SUDDEN RUDDER) *(baseline)*

W = 3400 lb, fin AC at x_v = 266.83 (yaw arm 189.3 in), fin root on the
fuselage top at z = 78.5, load centroid z_v ≈ 107, CG z 93 → **roll arm
+14.0 in**.

| quantity | value | note |
|---|---|---|
| fin side load `L_v` | +585.7 lb | SELECT's, read not recomputed (Appendix A +591 within the EFV band) |
| lateral load factor `n_y` | +585.7 / 3400 = **+0.1723 g** | the suite's first lateral load factor |
| yaw moment about the CG | +111,931 lb-in | `L_v·(x_v − x_cg) + Σ mzz` |
| yaw acceleration `ψ̈` | +205.7 deg/s² *(baseline `Izz`)* | ~179 deg/s² on the shipped L-3 tensor |
| induced roll couple | −585.7 × 14.0 ≈ **−8,200 lb-in** | 5.5 % of the ACRL aileron couple |

On a low tail the rudder kick is almost purely a yaw event: the induced roll
input is 7 % of the yaw moment and a twentieth of the airplane's design aileron
couple. The roll DOF still solves — coupled through `Ixz`, which contributes
roll of the same order as the fin arm itself on this airplane — but the case's
structural content is the yaw inertia sweep (`fx = +w·ṙ·dy` fore-and-aft loads
at the wing tips, `fy = −w·ṙ·dx` side loads along the fuselage) reacting the
fin load.

### 7.3 Worked example 4 — T-tail (concept_regional_jet, SUDDEN RUDDER) *(baseline)*

W = 33,000 lb, fin AC at x_v = 1010 (yaw arm ≈ 411 in), fin root waterline from
the **T-tail branch**: 45 + 180 − 138 = **z 87**, load centroid z_v ≈ 156, CG z
70 → **roll arm +86.0 in**.

| quantity | value | note |
|---|---|---|
| fin side load `L_v` | +6,907 lb | SELECT's |
| lateral load factor `n_y` | +6,907 / 33,000 = **+0.2093 g** | |
| yaw moment about the CG | +2,895,659 lb-in | |
| yaw acceleration `ψ̈` | +53.9 deg/s² *(baseline)* | RJ `Izz` is placement-only (no entered self-inertia), so this one survives L-3 |
| induced roll couple | −6,907 × 86.0 ≈ **−594,000 lb-in** | **99 % of the ACRL aileron couple (600,000)** |

The same condition, the opposite character: on the T-tail the fin's load
centroid rides ~7 ft above the CG, and the rudder kick applies a rolling moment
**as large as the airplane's design aileron couple** — 21 % of its own yaw
moment. A T-tail's `SUDDEN RUDDER` is a rolling case that happens to yaw, and
the coupled `[Ixx, Ixz; Ixz, Izz]` solve is mandatory, not a refinement: solving
roll and yaw as independent ratios mis-assigns load between the two largest
lateral inertia sweeps in the model. Before the L-1 waterline fix this entire
effect was invisible (arm −1.0 in).

**What the T-tail example does *not* yet include:** the h-tail riding at the
fin tip. In a yaw case the T-tail's horizontal surface sees fin-tip sideslip
and rolls the fin through its own asymmetric lift and inertia (fin bending and
torsion from mass at the tip). That transfer is plan 09 **T7**, deliberately
out of B8a scope — backlog step 9 — and is the stated boundary of this
document's T-tail treatment.

### 7.4 The wing-body sideslip term (L-7, 2026-08-17)

Method, signs and the DATCOM oracle: `00_theory_sources.md` (`lateral_body_aero`
row); conventions: `CONVENTIONS.md` §1 (the L-7 bullet) and §7 (owners). Here,
what the term does to the lateral balance.

With `aero_coeffs.lateral_body_aero.enabled` the applied lateral set gains one
`body-aero` load: the wing-body side force `Y = Cy_β·q·S·β` at the body
side-area centroid on the fuselage centreline, and a free couple such that the
pair's yawing moment about the wing 25 %-MAC station `xw` is exactly
`N = Cn_β·q·S·b·β` (gate G6). `β` and the fin's own derivatives come from
SELECT's condition; the body's come from DATCOM 5.2.1.1 / 5.2.3.1 on the fuselage
outline at the case's own Reynolds number, unless entered. About the case CG the
pair reads `N_cg = N − (x_cg − xw)·Y` (`lateral_body_aero.transfer_cn_beta`).
The lateral equilibrium becomes

```
ΣFy:   L_v + Y − W·n_y = 0                          →  n_y = (L_v + Y)/W
ΣMz:   L_v·(x_v − x_cg) + N_cg + Σ mzz = Izz·ψ̈       →  ψ̈  from the coupled solve
ΣMx:  −L_v·(z_v − z_cg) − Y·(z_b − z_cg) = Ixx·ṗ + Ixz·ψ̈
```

At `+β` `Y < 0` (port) like the fin's restoring load, so `|n_y|` rises; the
body couple `N > 0` (nose port, destabilizing) opposes the fin's, so `|ψ̈|`
falls — and on `YAW TO SIDESLIP` (23.441(a)(2)) reverses, which is the
regulation's overswing under full rudder, not a failure (note 19 §4). The gate
that does apply is static directional stability, fin + body `Cn_β` restoring
about `xw`, stated on every case and flagged when it fails (G3). Measured on the
shipped fixtures (term on vs off, starboard case): `concept_regional_jet`
`Cy_β −0.00101/deg`, `Cn_β +0.00332/deg` (fin `−0.00486`; net `−0.00154`) —
`|n_y|` +11 % / +11 % / +33 % and `|ψ̈|` −73 % / −71 % / reversed on `YAW 15
NEUTRAL` / `SIDE GUST` / `YAW TO SIDESLIP`; `ga6_normal` `Cy_β −0.00104`,
`Cn_β +0.00069` (fin `−0.00176`; net `−0.00107`) — `|n_y|` +27 % / +27 % / ×2.9
and `|ψ̈|` −41 % / −40 % / reversed. `SUDDEN RUDDER` (`β = 0`) is untouched
exactly (G2). Munk's isolated-body couple, retained as the independent producer
(`fuselage_moment.munk_yaw_slope_per_deg`), sits below DATCOM's wing-body value
on both fixtures (G7). The magnitude of `Cy_β` on the RJ is larger than the
design note's scratch estimate (which took `CL_α,B` from the base area):
DATCOM's `S_0` sits at 90 % of the body length, and on the fixture's
three-section outline — a linear cone from the maximum section to the tail —
that is ~10× the base area; a finer entered outline moves it, and the case note
carries the number either way.

## 8. The unsymmetrical horizontal tail — FAR 23.427(a)

**Decision D-R8** (review finding F-R5). One h-tail condition has a genuine
hand: 23.427(a) takes the largest-magnitude symmetric tail load and applies
100 % of half of it on one side and `pc = min(100 − 10(n−1), 80)` percent on the
other. SELECT owns that split (`select_htail_unsymmetrical`, oracle-locked with
the approved M1-4 deviation); the assembly **distributes** it and never
recomputes it. Every other h-tail condition is symmetric and is already in the
deliverable, as the `tail-air` trim load of every wing case — recorded as such
in the assembly record rather than dropped (`SKIP_REASONS["htail-symmetric"]`).

**The tail load replaces the trim load.** `RH + LH` *is* the condition's whole
tail load, so a case carrying `vn.lt` beside it would count the balancing part
twice. The strips come from the full-span `tail_span` table (plan 09 decision
T-8 — the topology built for exactly this), **air only**: the surface's mass
items stay in `body-inertia` and are accelerated by the closure field, so each
mass enters one set, as with the fin.

**The residual is the maneuver.** The governing condition on both fixtures is an
unchecked maneuver, and its V-n point is a balanced one at `n_z ≈ 1` — an abrupt
elevator input, with the wing still at trim lift:

| | ga6_normal (V-n 74, CG4) | concept_regional_jet (V-n 34) |
|---|---|---|
| applied tail load (RH / LH) | −700.4 / −504.3 lb (pc 72 %) | +5877.7 / +4702.2 lb (pc 80 %) |
| trim tail load at that point | −177.7 lb | +389.3 lb |
| pre-closure `Fz` | −1023 lb (−49.8 % `n·W`) | +10 109 lb (+30.6 %) |
| pre-closure `My` | +205 333 lb-in (144 % `n·W·MAC`) | −4 656 513 (−139 %) |
| pre-closure `Mx` (roll) | −7 168 lb-in (−1.73 % `n·W·b/2`) | +81 700 (+0.62 %) |
| closure | Δn −0.496 g, q̇ +637 °/s², ṗ −33.7 °/s² | Δn +0.306 g, q̇ −71.6 °/s², ṗ +9.8 °/s² |
| trim half (lumped `vn.lt` restored) | 0.187 % `n·W`, 0.301 % `n·W·MAC` | −0.246 %, 0.694 % |

That is the standard treatment of an unbalanced pitching maneuver — the pitch
acceleration is what 23.423/23.427 are about, and inertia relief is what sizes
the fuselage under it. The case is a **tail and fuselage** design case: its wing
loads carry ~0.5 g of relief and are not the wing's critical set.

**Two closed forms check what is applied**, because concept mode has no printed
oracle here (`CLAUDE.md` practice 2):

```
Σ fz over each half   =  SELECT's own RH, LH            (exact, both fixtures)
Σ y·fz                =  (RH − LH) · ȳ                  (ratio 1.000000000)
```

with `ȳ` the chord-weighted centroid of the half planform (36.550 in on the ga6,
69.500 in on the regional jet) — the chord-proportional distribution puts the
same shape on both halves, so only the scale differs.

**Handedness comes from the distribution.** The case carries no side force and no
free `mx`, so `is_handed` reads the **net applied rolling moment** against
`HANDEDNESS_TOL · n·W · b/2` (D-R8). The two populations do not overlap: a
mirror-symmetric applied set nets 1e-17 of that scale, this case 6e-3 to 1.7e-2.
The port twin is the starboard case reflected, which is precisely 23.427(a)'s
"either side" — the two halves' loads swap, and both hands are in the deck.

**One structural fix came with it.** The relief field is referred to the mass
set's **own centroid**, not to the entered CG. The two coincide on nearly every
loading (step C1 solves the ballast from the items), but ga6's `CG4` sits
0.0024 in forward and 0.0052 in below its entered CG, and an angular acceleration
about the wrong point leaves `−ω̇ × Σ wᵢrᵢ` of unclosed force: nothing at a
trimmed case's ω̇, and **0.31 lb of `Fx`** at this case's 637 °/s². The reported
residual is still stated about the CG; only the relief is solved where it is
exact.

## 9. The ground families — FAR 23.471–23.499

**Decisions G-1, G-6, G-7 (+G-7a), G-8** of plan
[18](../40_history/23_step10_ground_cases_plan.md). The fourth family, and the
one that breaks the shape of every section above: it has **no V-n point**. The
LANDLOAD conditions — level and tail-down landing, one-wheel landing, braked
roll, side load — are assembled here rather than in a per-component view because
a ground case is irreducibly three-dimensional. On `ga6_normal`'s braked roll
each main wheel carries 1,307 lb vertical against 1,235 lb of drag, and in the
side family the two wheels carry 2,253 lb vertical against −1,700 and −1,122 lb
of side load (23.485's own inboard/outboard split), all of it applied at a
contact patch **41 in below the CG waterline and ±57.25 in off the centreline**.
**Those lever arms are the load case**, and the per-component fuselage deck is
planar by construction, so building it there first and in the primary deliverable
second would be backwards.

### 9.1 What a ground case does not have

| | flight families (§2–§8) | ground families |
|---|---|---|
| case source | SELECT's condition + its V-n point | `landing.py` cases 1–24, through `gear_loads` |
| load factor | **given** by the V-n point | **solved** — the inertia set enters at `n_z = 0` |
| aero | the wing distribution at the point's `cl`/`V` | none, except `L × W` lift on cases 1–12 |
| balancing tail load | `tail-air` (`vn.lt`) | none — Ch 20 has no balancing tail load to invent |
| weight / CG | the payload case at the V-n point's CG | the roled landing loading at the **case's own design weight** (23.473(a): 23.479/481/483 at the design landing weight, 23.485/23.493 at take-off weight) |
| acceptance | force < `FORCE_RESIDUAL_ACCEPTANCE` 2.5 %, pitch < `RESIDUAL_GATE` 1 % (§3) | the LANDLOAD closed-form identity (§9.3) |

The weight split is why the loadings are keyed by **case number**, not by name:
cases 1–12 and 19–22 both name `aft max landing` at different design weights, and
a name lookup returned whichever was derived first — measured, when the defect
was found, at 170 lb light and `n_y` 5 % high on the ga6's side family. A ground
case whose loading the weight database cannot produce is skipped and
**recorded**, never invented (G-3), through the same `SkippedCondition` path the
flight families use.

**Which cases assemble.** 1–24, one balanced case each plus a twin where the
family has a hand. The even members of the three 23.485 pairs (20, 22, 24) are
LANDLOAD's *own* opposite drift direction and are minted by **reflecting** the
odd member (G-8) — so the reflection operator gains the only external check it
will ever get, `reflect(19)` reproducing case 20's `NS`/`ROLLP`/`YAWP`
sign-flipped and equal. Cases **25–33**, the 23.499 supplementary nose-wheel
family, carry nose reactions only — no main-gear reaction exists in them, so they
are gear-design cases, not an airplane in equilibrium. They are recorded as
`gear-design-only` and they have a home: the gear load report carries all 33.
The two deliverables therefore carry different case sets, 24 against 33, and say
so.

### 9.2 The applied set

| source | What it is | Where it acts |
|---|---|---|
| `gear-main`, `gear-nose` | LANDLOAD's own reaction, per wheel, **unchanged** | the leg's reference point, with the patch→node lever-arm couple |
| `ground-lift` | `L × W_case` on the AIRLOADS spanwise **shape**, both wings (cases 1–12 only) | strip stations, along the **ground line** |
| `wing-inertia`, `body-inertia`, `closure-*` | exactly as §2/§4, entered at `n_z = 0` | unchanged |

Three rules, each measured:

1. **The reaction is LANDLOAD's, and the transfer is exact.** `gear_loads` is a
   pure consumer of the oracle-locked reaction table, so assembling a ground case
   puts no Appendix A figure at risk. Each wheel arrives as a force **and** the
   couple `M = (patch − node) × F`, so the pair has the identical resultant the
   reaction had at the patch — worst relative error **3.4e-16** over all 33 cases
   and both legs, taken about a deliberately arbitrary reference (about the CG a
   dropped couple could cancel). Applying the force without the couple still sums
   to zero at a determinate support, which is why the guard exists and why a
   negative control drops the couple on purpose.
2. **Lift is on the landing families only, and it acts along the ground line**
   (G-7, G-7a). `L = lift_factor × W_case` on cases 1–12 — the manual's own split,
   since `landing.landing_reactions` carries the `lf·WL` term for exactly those
   cases, and 23.473(a) draws the same line. Only the *shape* is borrowed from
   AIRLOADS, so no speed, `CL` or V-n point is involved; the section `Cm` and the
   induced `fx` are deliberately **not** carried, because they scale with `q·CL`
   and this case has neither. The vector is `(L sin ρ, 0, L cos ρ)`: lift is
   perpendicular to the flight path, at touchdown the flight path is the runway,
   and the airplane sits at `ρ` to it. On the ga6 that puts **152 lb of the
   2,154 lb forward**, and it is what keeps the gate below an identity rather
   than a tolerance, since LANDLOAD sums `lf·WL` into the **ground-line**
   vertical: a lift applied along `z` enters that sum short by `cos ρ`, measured
   at G-7a as 0.053 % of `NVP` — small, and *not* solver noise.
3. **The ground-handling families carry no lift at all** (23.485/23.493), and the
   wing is emphatically not load-free there: it still carries its own inertia at
   the case's solved load factor. `GROUND_NO_LIFT_NOTE` says exactly that, in
   band, because "no lift" and "no load" are easy to confuse.

The masses are §2 rule 3 unchanged — one model, `weight.items`, spread for the
wing and carried at its own node for everything else. The legs' own weights ride
that same field (`LandingGearInput.weight_lb`, per leg, `0.0` = *not stated*), so
each mass enters exactly one set; unsprung-mass impact amplification is **not**
modelled and says so wherever it renders.

### 9.3 Nothing is given, so everything is solved

The inertia set enters at `n_z = 0` and the whole rigid-body field of §4 is
solved. That is not a convenient reuse — it is what the regulation asks for:

> **FAR 23.471.** *"the external reactions must be placed in equilibrium with the
> linear and angular inertia forces in a rational or conservative manner."*

A six-DOF rigid-body closure over the itemized mass model is that sentence, and
the solved field has an independent closed-form check, because LANDLOAD reaches
its own inertia factors by lever arms and FAR percentages with no mass matrix
anywhere in it. Rotate the solved translation back to the ground line:

```
NVP = n_z cos ρ − n_x sin ρ        NDP = n_x cos ρ + n_z sin ρ
NS  = n_y                          (lateral, normal to the rotation — unrotated)

Iyy·q̈ = PITCHP + the G-7a lift term       Ixx·ṗ = ROLLP       Izz·ṙ = YAWP
```

The translational three are an **exact identity** — `rel_tol 1e-9` on every case
of both fixtures. The rotational three (R6-T1) are compared after three named
frame moves — centroid → CG, contact patch → whichever arm point that family's
own formula measures to, body axes → ground line — with the G-7a lift term
rebuilt in closed form and subtracted; an identity on the one-wheel family's
shared tread arms, bounded at `1e-4·W·MAC` elsewhere, the cause being that the
BASIC truncates its printed lever arms to three decimals. Both corrections are
pinned as non-trivial by a negative control (12.5 % and 5.8 % of `PITCHP` on
`ga6_normal` case 4).

**`ρ` is measured, never re-derived.** It is `atan2(dm, vm) − atan2(DMP, VMP)` —
the angle between LANDLOAD's own two resolutions of one reaction — so this method
is independent of how `beta` is built. **That independence mattered:** `beta` in
`LANDLOAD.BAS` is `gamma − GRA(1)` for the level attitude but `+GRA(2)` /
`+GRA(3)` for the other two, which is the wrong sign — adjudicated and corrected
on 2026-08-29 (design note 38 GF-1/GF-2′, approved deviation in
[`02_approved_corrections.md`](02_approved_corrections.md), superseding the
"Considered and declined" decision of 2026-08-15). `ρ` is now `−GRA` in **every**
attitude, which is what `test_rho_is_minus_the_ground_angle_in_every_attitude`
pins. Recovering `ρ` per case is still the right construction, but it is no
longer a way of declining the question. **`ρ` appears in the
check and in the G-7a lift axis, and nowhere in the load path.**

**Handedness** works as §4 states it, with one exception the manual owns: for the
23.485 pairs the hand is *passed in*, because LANDLOAD supplies both drift
directions under ids of their own (`LG-19` port, `LG-20` starboard). Every other
family's hand is **measured** by `is_handed`, including the one-wheel family —
caught by the net-rolling-moment source added for 23.427(a), since all the
vertical reaction sits at one `y` and there is no side force at all, so a
lateral-content-only predicate would have minted it unhanded. Its two hands are
`LG-10L`/`LG-10R`.

### 9.4 Why `RESIDUAL_GATE` does not apply

**The pre-closure residual is the whole applied load, by construction** — the
same standing as the lateral cases (§7) and the 23.427(a) case (§8), and for the
same reason: there is nothing to cancel against. At `n_z = 0` the inertia sets
contribute exactly zero force, so `ΣF` before closure *is* the gear reactions
plus the lift, and `n = ΣF/W` is the answer rather than an error. Nothing trims
the case in pitch either: distributing the lift on the wing, where LANDLOAD nets
it at the CG (`NLG = N − L`), leaves a pitching moment the manual never forms —
+1.36 % of `n·W·MAC` on the ga6's level families, −2.38 % on the tail-down one —
reacted by pitch acceleration alone. An airplane at touchdown is an accelerating
body, not a trimmed one.

The exemption itself has one code owner, `balance.residual_gate_applies`
(CONVENTIONS §7): this section, §7 and §8 state *why* each family is exempt, and
every surface that reports a worst residual asks that predicate which cases the
maximum is taken over — it had been answering the question three different ways
(CR-C-2).

The gates that **do** apply, in place of smallness:

- the LANDLOAD identity above (translational `1e-9`; rotational as bounded);
- the six-DOF closure to machine precision, as for every other family;
- the deck re-balancing from its own exported card text, and — ground-specific —
  the reaction sbeam recovers at each gear `GID` being the gear report's own
  reference-point reaction, in both unit systems. That is what stops the
  inherited "reactions ≈ 0" leg passing vacuously: a transfer that dropped its
  lever arm *consistently* would still sum to zero at the support;
- two negative controls: dropping the offset couple, and computing a level
  landing at the **static** contact patch — the second asserted on the *moment*,
  because moving the patch does not change the vertical force factor and a
  control watching `NVP` would have passed while proving nothing.

### 9.5 Worked example 5 — three ground cases (ga6_normal)

`LG-04` (2-wheel level landing, nose clear — 23.479, lift), `LG-13` (braked roll
nose-down — 23.493, no lift) and `LG-19` (side load — 23.485, handed by the
manual). MAC 69.246 in throughout.

| | LG-04 | LG-13 | LG-19 |
|---|---|---|---|
| design weight / CG case | 3,230 lb, `aft max landing` | 3,400 lb, `aft max landing at 3,400 lb` | 3,400 lb, same |
| `ρ` | −4.057° | **−4.724°** | **−4.724°** |
| applied gear (`ΣFx`, `ΣFz`) | +2,042.3, +8,240.1 lb (2 wheels) | **+2,161.9, +3,213.0 main; −123.4, +1,492.9 nose** | **−372.4**, +4,506.6 lb, `ΣFy` −2,822.0 |
| applied lift | 2,154.4 lb (`0.667 × W`), −152.4 lb along `x` | none | none |
| pre-closure `Fx`/`Fz` | +1,889.9 / +10,389.1 lb | **+2,038.5 / +4,705.9 lb** | **−372.4** / +4,506.6 lb |
| pre-closure `My` | **−158,271 lb-in** | **−0.7 lb-in** | **−39,838 lb-in** |
| solved `n_z` / `n_x` / `n_y` | 3.2165 / 0.5851 / 0 | **1.3841 / 0.5996** / 0 | 1.3255 / **−0.1095** / **−0.8300** |
| rotated to the ground line | `NVP` **3.1670**, `NDP` **0.8112** | `NVP` **1.3300**, `NDP` **0.7115** | `NVP` **1.3300**, `NS` **−0.8300** |
| LANDLOAD prints (corrected) | 3.1670 / 0.8112 | 1.3300 / 0.7115 | 1.3300 / −0.8300 |
| `q̈` (1/in) | **−1.701e-2** | **−7.4e-8** | **−4.218e-3** |
| G-7a lift moment | +9,787 lb-in (1.360 % `n·W·MAC`) | — | — |

> **Updated 2026-08-29, twice.** First for the `BETA(2)` correction (design note
> 38 GF-1/GF-2′; register
> [`02_approved_corrections.md`](02_approved_corrections.md)), which moved the
> `LG-13` and `LG-19` columns and left `LG-04` alone — the level attitude was
> never affected by the sign. Then for the **application point** ([design note
> 39](../30_future/39_application_point_note.md), #139), which moved `LG-04`
> alone: the level attitude is applied at the **axle**, where the deck had been
> transferring it from the tyre. Only `My` and `q̈` move — the forces are
> LANDLOAD's own and were never touched by either fix, which is why `n_z`, `n_x`
> and the rotated `NVP`/`NDP` are the same figures throughout.

Three things to read off it. `n_z` is an **output** — 3.2165 in body axes,
LANDLOAD's 3.1670 once rotated, and the case reports the solved value rather than
a placeholder nobody computed. The braked roll's pre-closure `My` is **−0.7 lb-in**
against the landing case's −158,271 — a ground-handling case carries no lift, so
nothing pitches it but the drag arm, and with the corrected lever arms that arm
closes to essentially nothing. The landing case's residual is **not** slack: it
is LANDLOAD's own `PITCHP` (−168,057) plus the G-7a lift moment (+9,787) that the
manual nets at the CG and this suite distributes on the wing, and the two agree
to **1.1 lb-in**. Applying the case at the tyre made that agreement −20,962 —
which is what #139 was. **This figure is the correction's independent
witness:** it read −757.1 lb-in until 2026-08-29, and the residual is measured
against LANDLOAD's own unbalanced moments, which the correction does not touch.
A thousand-fold fall in `q̈` (−8.0e-5 → −7.4e-8) is what a wrong lever arm
looks like when it stops being wrong. And `LG-19`'s `n_y` is
LANDLOAD's `NS` to the last digit, with its twin `LG-20` — the reflection —
carrying +0.8300 and the mirrored `ṗ`/`ṙ`, which is how the manual's own second
drift direction becomes the check on the reflection operator.

## 10. Where every number is pinned

| Figure quoted here | Gate |
|---|---|
| which fixtures/conditions assemble, and handedness | `test_which_conditions_assemble_is_pinned` |
| pre-closure residuals < 1 % (per-fixture pitch ceilings) | `test_the_pre_closure_residual_is_within_the_gate` |
| Σ modelled mass = case weight | `test_the_inertia_set_weighs_the_case` |
| seam rule (no cut reaction applied) | `test_no_free_body_cut_reaction_is_applied` |
| six-DOF closure to machine precision | `test_the_case_closes_in_all_six_dof` |
| deck re-balances from its own card text; every load its own node | `test_the_deck_balances_from_its_own_cards`, `test_every_load_has_its_own_node` |
| `Mx` residual = the applied couple, exactly | `test_the_roll_moment_is_the_applied_couple` |
| WINGINER shape + pinned span share 0.795230 / 0.769455 | `test_roll_closure_reproduces_winginer` |
| companion `fy` 89.8 / 551.9 lb; induced yaw +18.93 / −0.993 deg/s² | `test_acrl_gained_the_companion_field_and_an_induced_yaw` |
| closure `Izz` pinned + WTONECG reconciliation identity | `test_the_closure_izz_is_pinned_and_reconciles` |
| yaw DOF ≡ ONENGOUT's `ψ̈ = M/Izz`, step by step | `test_the_yaw_dof_reproduces_onengout` |
| symmetric reduction (`n_y` = 0, `q̈ = My/Iyy`) | `test_a_symmetric_case_reduces_to_three_dof` |
| twins are load-by-load mirror images; reflection is an involution | `test_the_handed_twins_are_mirror_images`, `test_the_reflection_operator_is_an_involution` |
| §7's lateral `n_y`/`ψ̈` | `test_the_lateral_cases_are_pinned` (plan 13 G10) |
| §8's RH/LH split = SELECT's, and the twins swap it | `test_the_unsymmetrical_case_carries_selects_own_split` |
| §8's roll closed form `(RH − LH)·ȳ` | `test_the_unsymmetrical_roll_is_the_closed_form` |
| §8's trim half closes inside 1 % | `test_the_trim_half_of_an_unsymmetrical_case_still_closes` |
| §8's centroid reference for the relief field | `test_the_closure_is_solved_at_the_mass_centroid` |
| §9's which ground cases assemble, and which are recorded instead | `test_which_ground_cases_assemble_is_pinned`, `test_every_condition_is_either_assembled_or_recorded` |
| §9's `NVP`/`NDP`/`NS` identity (`rel_tol 1e-9`, every case, both fixtures) | `test_the_ground_closure_reproduces_landload` |
| §9's rotational half + the two departures' negative control | `test_the_ground_closure_reproduces_landloads_unbalanced_moments`, `test_the_rotational_gates_two_departures_are_not_no_ops` |
| §9's worked example (LG-04 / LG-13 / LG-19 figures, the patch, the lift moment) | `test_the_ground_worked_example_is_pinned` |
| §9's patch→node transfer preserving the resultant, and the control that drops the couple | `test_the_transfer_to_the_reference_point_preserves_the_resultant`, `test_dropping_the_offset_couple_breaks_the_transfer` |
| §9's static-patch negative control on the moment | `test_the_static_contact_patch_breaks_the_level_landing_gate` |
| §9's six-DOF ground closure; the deck applying the report's own reaction | `test_the_ground_case_closes_in_all_six_dof`, `test_the_deck_applies_the_reports_reference_point_reaction` |
| §9's reflected 23.485 twin reproducing LANDLOAD's own opposite drift | `test_the_reflected_side_case_reproduces_landloads_own_twin` |
| §9's `ρ` measured from the two resolutions, and the ground-roll attitude finding | `test_the_two_frames_round_trip_through_the_rotation`, `test_the_ground_roll_attitude_is_resolved_against_the_other_sign` |
