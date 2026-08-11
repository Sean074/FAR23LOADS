# Balanced Free-Free Airplane Cases — the Balancing Method

How `sloads/modules/balance.py` assembles a **full-span, free-free airplane load
case** — aero and inertia together, wing tip to wing tip, nose to tail — and
closes it so the exported deck solves in sbeam with **no constraint doing any
work**. With worked examples on the shipped fixtures: a symmetric wing case, an
antisymmetric (rolling) wing case, the ±β empennage cases on a conventional low
tail and on a T-tail, and the unsymmetrical horizontal-tail case of FAR
23.427(a).

- **Authority:** axes/signs/seam rule/closure charter in
  [`CONVENTIONS.md`](../10_standard/CONVENTIONS.md) §1 and §7 (this document
  explains; it never overrides). Module spec:
  [`PROGRAM_SPEC.md`](../10_standard/PROGRAM_SPEC.md) "Balanced cases and the
  assembled deck". Decision records: plans
  [11](../30_future/11_balanced_airframe_cases_plan.md) (B-1…B-8) and
  [13](../30_future/13_b8a_lateral_closure_plan.md) (L-1…L-8), and decision
  **D-R8** in [`03_resolved_decisions.md`](../40_history/03_resolved_decisions.md)
  (the 23.427(a) family, §8).
- **Code:** `sloads/modules/balance.py` (assembly + closure),
  `sloads/rigid_body.py` (the relief field, single owner),
  `sloads/export/balanced_deck.py` (the deck),
  `sloads/export/coordinates.py` (reflection, single owner).
- **Gates:** every number quoted here is pinned in CI —
  `tests/test_balance.py`, `tests/test_rigid_body.py` (§9 maps figure → test).
- **Units:** Imperial internal (lb, in, lb-in); loads in this document are
  **LIMIT** (the ×1.5 ultimate factor is applied once at the export boundary,
  per the load-output contract). Frame: `x` +aft, `y` +starboard, `z` +up;
  moments by the right-hand formulas of `balance.resultant6`.
- **Status:** every family in this document is **shipped and gated** — the wing
  symmetric cases (steps B2–B6), the antisymmetric rolling cases (B7), the
  six-DOF rigid-body closure (B8a-2), the lateral empennage cases (B8a-3) and
  the unsymmetrical horizontal tail (D-R8, §8). Figures marked *design of
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
| `closure-n`, `closure-roll/pitch/yaw`, `closure-self` | The rigid-body relief (§4) | on the modelled masses |

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
   moment, +4.3 to +6.3 % of `n·W·MAC`, destabilising — is applied as one free
   moment (`fuselage-cm`) until M4-19 distributes it. Omitting it would leave a
   systematic ~5 % moment residual for the closure to absorb silently: a real
   aero load disguised as a correction.

## 3. The residual — measured before closure, and part of the deliverable

The six-component resultant of the applied set is taken about the case's CG
(`balance.resultant6`) **before** any relief is applied. That number is the
physics: how well the independently-computed wing, tail, and inertia sets agree.
The acceptance gate (plan 11 §6) sits on it, not on the corrected result:

```
|ΣFz| / (n·W)        < 1 %      (force)
|ΣMy| / (n·W·MAC)    < 1 %      (pitch; per-fixture ceiling where it bites)
```

The ~0.3 % floor that remains on the ga6 is the strip-quadrature-versus-
closed-form lift difference — predicted by plan 11 R3, not noise. The residual
and the relief applied are stated in the result, the UI and the deck `$` header
(CONVENTIONS §1: *the residual is part of the deliverable*).

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
case); the air rows overshoot by 34.6 lb — **0.268 % of n·W**, the quadrature
floor. The lumped `fuselage-cm` moment for this case is +44,095 lb-in.

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

**The pre-closure lateral residual is the entire fin load, by construction.**
Unlike the symmetric case, where aero and inertia nearly cancel to a 0.3 %
residual, there is nothing for a rudder kick to cancel against — the suite
computes no other lateral aero (no fuselage, wing, or h-tail side force). So
the 1 % smallness gate is meaningless laterally, and the replacement gates
(decision L-5) are: the yaw identity against ONENGOUT's oracle-locked
`ψ̈ = M/Izz` (G1), the symmetric half still meeting its own 1 % gate with the
fin load removed (G9), and the lateral quantities pinned per fixture (G10).

**Stated limitation (decision L-7), carried in-band wherever the case renders:**
because the fin is the only lateral aero modelled, `n_y` and `ψ̈` are
**over-stated**, the inertia they drive is conservative on every component, and
the fin's own design load is SELECT's, unchanged. The magnitude of the
overstatement is unknown and is stated as unknown.

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

## 9. Where every number is pinned

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
