# Design note — B8a lateral closure: the ±β empennage cases

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Raised:** 2026-08-08. **Status: SHIPPED 2026-08-09** — decisions L-1…L-8
answered by the user 2026-08-08/09, and all five steps (B8a-1…B8a-5) complete
and green with the Tier-L closure trail. Written per `CLAUDE.md` required
practice 1 (design note before code for a physics/L step) and plan 11 decision
**B-8**, which requires "stating the lateral trim balance first"; §8's steps
were the implementation order, and each records what actually shipped —
including where measurement amended this note (**G5**, **G6**, **G10**).

Each decision's answer of record is in §5's table and expanded in §5.1–§5.7 —
the resolution order for the fin waterline, the relief field, the self-inertia
rule, the gust `Izz`, the handedness predicate, the lateral-aero statement and
where fin inertia lives. Three things the decision session **changed** relative
to the note as first drafted, all from measurement:

1. the roll companion `fy` is **not** negligible (113 lb/node ga6, 717 lb RJ) —
   `ACRL`'s physics moves, not just its bytes (§3.6, §5.2);
2. the gust load is **insensitive** to `Izz` (0.04 % for a 38 % change), because
   `KGT` is saturated — which is what makes L-4 cheap (§5.4);
3. the symmetric half of the RJ's `SIDE GUST` point misses the 1 % pitch gate at
   **1.586 %**, the largest instance yet of an already-filed item (§7 G9).

**Closure tier:** L — new physics (a lateral load factor exists nowhere in the
suite), a new closure degree-of-freedom pair, a schema addition, and a change to
what the residual of a balanced case *means*.

Parent plan: [`11_balanced_airframe_cases_plan.md`](../30_future/11_balanced_airframe_cases_plan.md)
(step **B8a**, decisions B-6/B-7/B-8, and §10's B7 findings, which govern how a
non-closing degree of freedom is reported). Sibling:
[`09_distributed_empennage_loads_plan.md`](../30_future/09_distributed_empennage_loads_plan.md)
— its phase-1 scope note says *"v-tail inertia is omitted … revisit with plan 11
B8a, which is where a lateral load factor first has to exist."* This is that.

**Conventions cited** (`docs/10_standard/CONVENTIONS.md`): §1 frames and axes
(`y` +starboard, `fy` side force, moments `mx`/`my`/`mz`); §1 "an assembled
balanced case closes in three symmetric DOF" — **this note extends that
sentence**, so the charter changes with the step; §1 "the residual is part of the
deliverable"; §1 the free-body-cut seam rule; §4 case identity and §7.1
handedness (`handed_case_id`, reflection owned by `export/coordinates.py`); §7.2
empennage axes (v-tail spans `z`, load `fy`, torsion `mzz` **negated**); §6 the
concept-mode benchmark rule (no printed oracle ⇒ a stated closure gate in CI).

**Theory references** (never from memory — `CLAUDE.md`):

| Quantity | Source |
|---|---|
| V-tail maneuver loads, FAR 23.441(a)(1)/(2)/(3) | Ref 1 Ch 9; `SELECT.BAS` subr 8300. Printed oracle: Appendix A "Critical Vertical Tail Loads" — sudden rudder **+591**, sideslip 19.5° **−92**, yaw 15° neutral **−526** |
| Lateral gust, FAR 23.443(b) | Ref 1 Ch 9; `SELECT.BAS` 8840-8930. Printed oracle: side gust at VC **+604 lb**, with **IZZ 4169.2 slug-ft²** |
| Airplane inertia from the item database | `WTONECG.BAS`, Ref 1 Ch 4, Appendix C p377-381. Printed oracle: **Appendix A p136** — aft gross 3400 lb, XBAR 84.999, ZBAR 92.579, IXX/IYY/**IZZ** 1201.5 / 2058.2 / **3022.8** slug-ft² |
| Yaw acceleration from an unbalanced yaw moment | `ONENGOUT.BAS` 282-286, Ref 1 Ch 11 p87-88 (FAR 23.367): `THETA2DOT = MOM/12/IZZ·57.3` — i.e. **ψ̈ = M/I_zz**. This is the independent producer B8a's yaw DOF is checked against |
| Rigid-body d'Alembert relief | The relief field is `f_i = −m_i (a_cg + ω̇ × r_i)`; the moment it produces about the CG is `−[I]{ω̇}` with the **full** inertia tensor. Standard rigid-body mechanics; no suite source, so §7's gate carries it |

---

## 1. What B8a has to produce

For each of the four SELECT vertical-tail conditions — `SUDDEN RUDDER`,
`YAW TO SIDESLIP`, `YAW 15 NEUTRAL`, `SIDE GUST` — a **balanced full-span
free-free airplane case**, emitted as a **handed pair** (`VT-01R`/`VT-01L` …),
carrying the fin's distributed side load together with the concurrent symmetric
flight case, closed in **six** degrees of freedom, and exported as one assembled
deck that solves in sbeam with determinate-support reactions ≈ 0.

All four conditions sit on V-n points at **n_z ≈ 1.0** (`ga6_normal` case 14 =
BAL A, case 35 = BAL C), so the vertical/longitudinal/pitch half of the case is
the shipped B2 machinery **unchanged**. B8a adds the lateral half.

## 2. The lateral balance, stated

Applied set = the symmetric set already assembled (wing strips both sides, tail
air, body inertia, lumped fuselage `Cm`) **plus** the fin's distributed side load
from `tail_span` (`fy` per strip, `mzz = −torsion` per §7.2).

Equilibrium about the CG:

```
ΣFy = 0 :   L_v  −  W·n_y                      = 0     ->  n_y = L_v / W          [g]
ΣMz = 0 :   L_v·(x_v − x_cg) + Σ mzz  −  Izz·ψ̈ = 0     ->  ψ̈  = Mz / Izz         [rad/s²]
ΣMx = 0 :  −L_v·(z_v − z_cg)          −  Ixx·ṗ − Ixz·ψ̈ = 0
```

Three things follow immediately, and each is a decision in §5:

1. **There is nothing for the fin load to cancel against.** Unlike the symmetric
   case — where aero and inertia nearly cancel and the residual is 0.3 % — the
   pre-closure lateral residual **is the entire fin load, by construction**. Plan
   11's "residual < 1 % of n·W before closure" gate is therefore *meaningless*
   laterally, in exactly the way plan 11 §10 finding 2 records for B7's roll
   residual: the airplane is *supposed* not to balance a rudder kick. It yaws.
2. **The roll equation needs the fin's height above the CG**, which the suite
   does not model today (§3.3).
3. **The roll and yaw equations are coupled through `Ixz`**, which is not small
   (§3.5). The rotational closure is a 3×3 solve, not three independent ratios.

## 3. Measured baseline (2026-08-08, current `main`)

Every figure below was computed from the shipped fixtures before any change.

### 3.1 The four cases

`ga6_normal` (W = 3400 lb, MAC 69.25 in, semi-span 201 in, x_v25 = 266.83):

| Case | FAR | L_v (lb) | n_y (g) | Mz about CG (lb-in) | ψ̈ (deg/s²) |
|---|---|---|---|---|---|
| `SUDDEN RUDDER` | 23.441(a)(1) | +585.7 | **+0.1723** | +111,931 | **+205.7** |
| `YAW TO SIDESLIP` | 23.441(a)(2) | −97.8 | −0.0288 | −12,277 | −22.6 |
| `YAW 15 NEUTRAL` | 23.441(a)(3) | −525.7 | −0.1546 | −95,544 | −175.6 |
| `SIDE GUST` | 23.443(b) | +604.0 | **+0.1776** | +114,360 | **+214.9** |

`concept_regional_jet` (W = 33,000 lb, semi-span 396 in, x_v25 = 1010):

| Case | L_v (lb) | n_y (g) | Mz (lb-in) | ψ̈ (deg/s²) |
|---|---|---|---|---|
| `SUDDEN RUDDER` | +6,907 | +0.2093 | +2,895,659 | +53.9 |
| `YAW TO SIDESLIP` | −3,548 | −0.1075 | −1,187,425 | −22.1 |
| `YAW 15 NEUTRAL` | −8,043 | −0.2437 | −3,140,834 | −58.5 |
| `SIDE GUST` | +7,080 | +0.2146 | +2,908,780 | +41.9 |

The side loads reproduce the Appendix A printed figures (+591 / −92 / −526 /
+604) inside the documented `EFV ≈ 1.009` band — they are **read**, never
recomputed (plan 09 decision T-7), so no oracle is at risk here.

**n_y runs 0.03–0.24 g and ψ̈ runs 22–215 deg/s².** These are the first lateral
load factors the suite has ever produced, and they are the numbers the gate in §7
has to defend.

### 3.2 The fin is the only lateral aero the suite has

In a 19.5° sideslip a real airplane carries side force on the fuselage, on the
wing and on the h-tail; none of the three exists anywhere in this suite. So the
whole of `n_y` and `ψ̈` above is the *fin's* load being reacted by inertia alone.
This is the lateral counterpart of the lumped fuselage `Cm` (`balance.py`,
`source="fuselage-cm"`) and of the un-distributed aileron lift increment — and
unlike the first of those, there is **no scalar to lump**: nothing in the suite
computes a body side force. Consequence: `n_y` and `ψ̈` are **over-stated**, so
the inertia loads on every non-fin component are conservative, and the fin's own
design load is unaffected (it is SELECT's, unchanged). Decision **L-7**.

### 3.3 The fin is modelled *below* the centre of gravity — blocking

`tail_span.build_tail_span` passes `z_offset = 0` for the v-tail (the h-tail gets
`root_waterline_z`), and `tail_station_to_airplane` then places fin stations at
`z = 0 … span`. Measured:

| Fixture | fin load centroid `z` | `z_cg` | roll arm `z_v − z_cg` |
|---|---|---|---|
| `ga6_normal` | 28.5 | 93.0 | **−64.5 in** (fin below the CG) |
| `concept_regional_jet` | 69.0 | 70.0 | **−1.0 in** (fin at the CG) |

Both are physically wrong, and wrong in the way that matters: the induced roll
moment `−L_v·(z_v − z_cg)` comes out with the **reversed sign** on `ga6_normal`
and with essentially **zero magnitude** on the RJ. If the ga6 fin root sat at the
wing root waterline (78.5), the arm would be **+14 in** — a sign flip and a 4.6×
magnitude change. **No roll number in a lateral case means anything until this is
fixed**, so it is step 1, and it changes the exported v-tail span deck's `GRID`
z-coordinates (a deliberate, stated exception to plan 11 acceptance #5 — see §7).

The suite has no input for it: no fixture carries an `htail`/`vtail` entry in
`geometry.surfaces` (the filed "empennage planform is derived" item), and
`parametric.fuselage_height` is 0 on `ga6_normal`. Decision **L-1**.

### 3.4 Three different `Izz` for the same airplane — and an exact reconciliation

| Producer | ga6 (slug-ft²) | Authority |
|---|---|---|
| `select._default_izz` — Ch 9 approximation | **4169** | Printed in Appendix A beside the side-gust load; **it sizes the gust load** |
| `weight_onecg` (WTONECG) from the item database | **3023** (CG1) / 2967 (CG2) | **Printed oracle, Appendix A p136** |
| The assembled balanced case's own mass set | **2598** (CG1) / 2540 (CG2) | What actually reacts the load in the deck |

The manual prints two of these for the same airplane and they differ by **+38 %**.
The third is what the assembled model carries. The differences are not noise, and
they are fully explained — this identity holds **exactly**:

```
Izz(assembled)  =  Izz(WTONECG)  −  Σ item self-Izz  +  Σ w_i·y_i²(WINGINER spread)

ga6 CG2:   2540  =  2967 − 1353 + 926        ->   2540    (0.0 %)
RJ  CG1: 256,508 = 224,869 −   0 + 30,617    -> 255,486   (+0.40 %)
```

Two readings of it, both worth having in the note:

* **The wing's spread is right.** `ga6_normal` enters the wing item's own
  `izz = 4.444e6 lb-in²` for exactly the spanwise spread the assembled model
  builds from WINGINER's distribution, `Σw·y² = 4.288e6` — the same physical
  quantity from two independent producers, agreeing to **−3.5 %**. Adding the
  item self-inertia *on top of* the spread would double-count it.
* **Every other item's self-inertia is silently dropped.** On `ga6_normal` that
  is 394 slug-ft², **13.3 %** of the airplane's `Izz` (the fuselage-structure
  lump alone is 1.131e6 lb-in²). The RJ's database enters no self-inertias at
  all, which is why its assembled `Izz` is *higher* than WTONECG's rather than
  lower. Neither model is a superset of the other. Decision **L-3**.

`Iyy` shows the same pattern (ga6 −15.7 %, RJ +0.3 %) and `Ixz` agrees closely
(ga6 CG1 140.5 assembled vs 141.3 WTONECG, −0.6 %), because WTONECG carries no
self-`Ixz` either.

### 3.5 The roll/yaw coupling is first-order

`Ixz / Σw·(x−x_cg)² = +0.084` (ga6 CG1), `+0.046` / `−0.015` (RJ CG1/CG2). The
roll moment a yaw relief field induces through `Ixz` is **17–25 % of the fin's
own roll moment on ga6, and larger than it on the RJ**. Solving roll and yaw as
two independent ratios is therefore not an approximation, it is wrong.

### 3.6 The shipped relief fields are one-component, and the yaw DOF cannot copy them

`balance._closure` applies `fz = k·(x−x_cg)·w` for pitch and `fz = k_roll·y·w`
for roll. The true d'Alembert field for an angular acceleration has **two**
force components, and the omitted one is the whole difference between `Σw·dx²`
and a moment of inertia:

* **Pitch.** The missing companion is `fx = −m·q̈·dz`. Measured, it is worth
  `Σw·dz² / Σw·dx² = 4.1–4.5 %` of the pitch inertia, and at most **0.45 lb**
  per node on ga6 (against 1,920 lb node loads) and **11.3 lb** on the RJ
  (against 23,400 lb) — **≤ 0.08 %** of any node load. Physically negligible;
  it does mean `delta_pitch` is not exactly `q̈`.
* **Roll.** The missing companion is `fy = +m·ṗ·dz`, and it is **not** small.
  Measured on `ACRL`, the only shipped case that rolls:

  | | ga6 `ACRL` | RJ `ACRL` |
  |---|---|---|
  | companion `fy`, peak node | **113 lb** (6.9 % of the peak node load) | **717 lb** (3.8 %) |
  | the roll field's own `fz`, peak node (unchanged) | 44.6 lb | 100.9 lb |
  | net `Fy` added | 1e-13 (zero, as required) | 1e-12 |
  | yaw moment induced via `Ixz` | +14,625 lb-in = **+0.66 %** of n·W·(b/2) | −89,733 = **−0.30 %** |

  The companion is **2.5–7× larger than the roll term already in the deck**,
  because `fz = k·w·y` touches only the wing strips — every item in every
  fixture's database sits at `y = 0` — while `fy = −k·w·dz` touches every item
  off the roll axis. It is real physics: a roll acceleration throws a mass above
  the roll axis sideways. **The assembled `ACRL` decks omit it today.**
* **Yaw.** The missing companion is `fx = +m·ψ̈·y`. It is worth
  `Σw·y² / Σw·dx² = 55 %` on ga6. **A yaw DOF built on the pitch DOF's pattern
  would report ψ̈ 55 % high** and put no fore-and-aft load on the wing at all —
  when a yaw acceleration's most obvious structural consequence is precisely a
  fore-and-aft load at the wing tips.

Three different error magnitudes from one omission — negligible, 7 %, and 55 % —
is the argument for decision **L-2**: do the whole field properly once, rather
than add a fourth and fifth special case and hope the next one is the small kind.

## 4. What is *not* in scope

* **T-tail transfer** (plan 09 T7) — the fin-tip h-tail load in a yaw case is
  step 9, not this step.
* **Discrete rudder hinge/actuator loads** (plan 09 T6) — the fin's control load
  stays smeared, as `control_load_mode` already declares in-band.
* **A distributed body side force** — nothing computes one (§3.2, decision L-7).
* **ONENGOUT as a balanced case.** 23.367 is a genuinely handed lateral case and
  it belongs in this family eventually, but it is a *transient* with its own time
  history; B8a takes the four static SELECT conditions and uses ONENGOUT only as
  the independent producer for the yaw identity (§7 G1).
* **Landing/ground lateral cases** — B8b / M4-6.

## 5. Decisions needed before code

| # | Question | Options | Recommendation |
|---|---|---|---|
| **L-1** ✅ | **Where is the fin root waterline?** (§3.3 — blocking) | (a) explicit input **plus** a tail-type-aware derived default marked `assumed`; (b) explicit input only, raise if absent; (c) derive only, no schema change | **ANSWERED (user, 2026-08-08): (a).** See §5.1 for the resolution order of record |
| **L-2** ✅ | **What is the relief field?** (§3.6) | (a) full rigid-body field `f_i = −m_i(a_cg + ω̇ × r_i)` with the complete 3×3 tensor; (b) one-component fields throughout; (c) full field for the new lateral DOF only | **ANSWERED (user, 2026-08-08): (a).** See §5.2 for the field of record and what it moves |
| **L-3** ✅ | **Does the closure tensor carry item self-inertia?** (§3.4) | (a) non-wing self-inertia as free-moment relief; (b) placement only, report and pin the gap; (c) all self-inertia with the wing lumped instead of spread | **ANSWERED (user, 2026-08-08): (a).** See §5.3 for the rule of record |
| **L-4** ✅ | **Which `Izz` sizes the side-gust load?** | (a) Ch 9 default stays, report the ratio; (b) feed the item-model `Izz` into SELECT; (c) Ch 9 for FAR 23, item model in concept mode | **ANSWERED (user, 2026-08-08): (a).** See §5.4 — and note the measured sensitivity, which is what makes this cheap |
| **L-5** ✅ | **What is the acceptance gate for a lateral case?** (§2) | (a) identity backbone + symmetric-half gate + pinned lateral values; (b) identity backbone + symmetric-half only; (c) identity backbone only | **ANSWERED (user, 2026-08-08): (a).** Plan 11's "residual < 1 % before closure" is unpassable and meaningless laterally — the pre-closure residual *is* the applied fin load, 100 % of it, by construction. §7 carries the replacement set; the two additions are **G9** and **G10** |
| **L-6** ✅ | **What gives a case a hand?** | (a) any lateral content in the applied set, pre-closure; (b) non-zero *net* side force; (c) every v-tail condition by definition | **ANSWERED (user, 2026-08-08): (a).** See §5.5 for the predicate of record |
| **L-7** ✅ | **The missing body side force** (§3.2) | (a) state it in-band and file it; (b) add a first-order slender-body side force now; (c) block B8a until a body side-force model exists | **ANSWERED (user, 2026-08-08): (a).** See §5.6 for the statement of record and what gets filed |
| **L-8** ✅ | **Does the per-component v-tail deck gain inertia now?** | (a) no — fin inertia lives in the balanced case; (b) thread `n_y` down into the deck; (c) (a) plus fixing the tail-mass SSOT in the same step | **ANSWERED (user, 2026-08-09): (a).** See §5.7 — and the tail-mass finding it surfaced, which is filed rather than folded in |

### 5.1 L-1 as answered — the fin root waterline resolution order

Decision of record (user, 2026-08-08). One owner, resolved once, `assumed`
carried on the result and into the deck `$` header exactly as
`tail_geometry.resolve_tail_planform` already does for the derived planform:

```
vtail root waterline:
  explicit input        -> use it                                     (assumed = False)
  T-tail with h_tail_z  -> root_waterline_z + h_tail_z - vtail_span   (assumed = True)
  otherwise             -> root_waterline_z + fuselage_height / 2     (assumed = True)
  neither available     -> 0.0 + a loud in-band note                  (assumed = True)
```

> **Correction applied while implementing B8a-1** (2026-08-09). The conventional
> branch is `fuselage_height / **2**`, not the full height as this note first
> wrote it. `root_waterline_z + fuselage_height/2` is the established meaning of
> "the top of the fuselage" in this suite — `configuration.tail_planform` has
> drawn every fin from it since Step G6 — and a load path using a different
> formula would have silently disagreed with the three-view beside it, which is
> the exact failure this decision exists to prevent. **No quoted number changes:**
> `ga6_normal` enters `fuselage_height = 0`, so both formulas give 78.5, and the
> RJ takes the T-tail branch. The T-tail branch also turned out **not** to be a
> new convention — it is the inverse of the three-view's own default, which
> places a T-tail's horizontal surface at `fuselage_height/2 + v_span`, i.e. at
> the fin tip.

Effect on the shipped fixtures, and the reason this is step 1:

| Fixture | route | fin root `z` | roll arm `z_v − z_cg` | was |
|---|---|---|---|---|
| `ga6_normal` | fuselage top (`fuselage_height` = 0) | 78.5 | **+14.0 in** | −64.5 |
| `concept_regional_jet` | T-tail (45 + 180 − 138) | 87.0 | **+86.0 in** | −1.0 |
| `cessna_210` | fuselage top | 86.0 | — | — |
| `atr42_100` | fuselage top | 170.0 | — | — |
| `dhc8_dash8` | fuselage top | 180.0 | — | — |

The ga6 value is the wing root waterline standing in for the fuselage top,
because that fixture enters no `fuselage_height` — defensible as a floor, and it
is `assumed`, so it says so. Populating `fuselage_height` on the fixtures is the
already-filed S-tier item that improves it (risk R2).

**SHIPPED 2026-08-09** — see §8 step B8a-1. Both roll arms came out at exactly
the predicted values.

### 5.2 L-2 as answered — the relief field of record

Decision of record (user, 2026-08-08). The relief is the **rigid-body d'Alembert
field**, `f_i = −m_i (a_cg + ω̇ × r_i)`, in full:

```
translation  a_cg = g*(n_x, n_y, n_z)   ->  f_i = -w_i * (n_x, n_y, n_z)
roll   p_dot ->  fy = +m p_dot dz ,  fz = -m p_dot dy
pitch  q_dot ->  fx = -m q_dot dz ,  fz = +m q_dot dx
yaw    r_dot ->  fx = +m r_dot dy ,  fy = -m r_dot dx
```

The moment this field produces about the CG is exactly `−[I]{ω̇}` with the full
inertia tensor of the assembled mass set, so the rotational closure is **one
symmetric 3×3 solve**, coupled through `Ixz` (`Ixy`/`Iyz` vanish for a
mirror-symmetric mass model but are computed, not assumed — the same standing
`resultant6` already gives `Fy`/`Mz`). The three translational DOF stay
decoupled ratios, because the loading's centroid *is* the CG.

Consequences, all deliberate:

* **`delta_pitch`/`delta_roll` become true accelerations** (`q̈`, `ṗ`) rather
  than moment-distribution coefficients, and are renamed accordingly.
* **`ACRL`'s physics changes**, not merely its bytes: it gains the companion
  lateral field (113 lb/node ga6, 717 lb/node RJ) and, through `Ixz`, a yaw
  residual of +0.66 % / −0.30 % of `n·W·(b/2)` that the new yaw DOF closes. A
  rolling airplane with non-zero `Ixz` yaws; the shipped model could not say so.
* ~~**B7's closure gate survives untouched.**~~ **Wrong — corrected while
  implementing B8a-2 (2026-08-09), and the correction is a decision of record.**
  The roll field's `fz` component is still exactly `−m·ṗ·y`, so WINGINER's
  **shape** is reproduced strip for strip as this note said. But `ṗ` itself
  moves: once the companion `fy = +m·ṗ·dz` exists, the roll inertia is
  `Σw(y² + dz²) + Σ self-Ixx` rather than `Σw·y²`, and **`ṗ` falls 20.7 % on
  `ga6_normal` and 23.2 % on the regional jet** (`Σw·dz²` alone is +30 % of
  `Σw·y²` on the RJ). The equality `fz == ur·fz_r` therefore fails at
  `rel = 1e-9`, and it fails for a real reason: WINGINER's wing-only model puts
  100 % of the aileron moment on the span, while the assembled airplane reacts
  about a fifth of it on mass off the roll axis — which is the load a wing-only
  model has no term for and the assembled model exists to find.

  **Restated gate (user decision, 2026-08-09 — option (a) of three):** assert the
  two halves separately — *shape*, that `fz/(ur·fz_r)` is the **same constant on
  every strip** to `rel = 1e-9`; and *magnitude*, that the constant is the wing
  span's share of the roll moment, **pinned per fixture at ga6 0.795230 / RJ
  0.769455** and independently equal to `ṗ / (Mx / Σw·y²)`. Strictly stronger
  than the equality: it keeps the whole of the two-producer check and adds a
  pinned physical fact that goes red if the roll-inertia model drifts — something
  the equality could not see, because under it the span *was* the roll inertia by
  construction.
* **This subsumes M4-21** (the fuselage pitching load factor): the pitch DOF's
  `fz = +m·q̈·dx` *is* M4-21's `−m_i·θ̈·(x_i − x_cg)`, now with its companion
  term and a real `q̈`. The backlog item reduces to supplying `θ̈` for the
  unbalanced conditions.

### 5.3 L-3 as answered — self-inertia in the closure tensor

Decision of record (user, 2026-08-08). On top of the §5.2 placement field, each
mass item **whose mass the assembly does not itself distribute** contributes its
own rotational resistance as a free moment at its node:

```
for each item i:
    placement:  f_i = -m_i (a_cg + omega_dot x r_i)
    if i is not distributed by the assembly:
        m_i = -[I_self,i] {omega_dot}          (a free MOMENT at the item's node)
```

**"Distributed by the assembly" is a structural predicate, not a comment.**
Today it is exactly `MassComponent.WING` — WINGINER spreads the wing item over
the span, so its entered self-inertia is the *same physical quantity* and adding
it would count the wing's spread twice (measured: 4.444e6 entered against
4.288e6 spread, −3.5 %). The predicate gets a single owner beside
`mass_distribution.component_of` and a guard test, so the day the empennage or
the fuselage gains a distributed mass model the exclusion follows it instead of
being rediscovered.

Effect, and the reason G4 becomes an equality:

| | ga6 CG2 | RJ CG1 |
|---|---|---|
| `Izz` placement only | 2540 | 256,508 |
| `+` non-wing self-inertia | **2934** | 256,508 (database enters none) |
| identity `Izz(WTONECG) − wing self + spread` | 2967 − 959 + 926 = **2934** | 224,869 − 0 + 30,617 = 255,486 |
| agreement | **0.0 %** | **+0.40 %** |

It also brings the two decks for the same airplane into line: `export/mass_cards`
already emits `I11`/`I22`/`I33` per item on its `CONM2` cards, so before this
decision the mass deck carried self-inertia and the load deck did not. The
residual +0.40 % on the RJ is the wing's x-redistribution under the WINGINER
spread and is the tolerance G4 is stated at.

### 5.4 L-4 as answered — the gust `Izz`, and why the choice is cheap

Decision of record (user, 2026-08-08). `select._default_izz` (Ch 9, oracle-locked
— Appendix A prints **IZZ 4169.2** beside the **+604 lb** gust load) keeps sizing
the load. The closure tensor of §5.2/§5.3 reacts it. The balanced case **states
both and their ratio** in-band — result, UI and deck `$` header — the way the
`wing inertia scaled ×…` note already does. `VTailLoadsInput.izz_slugft2` remains
the per-project override.

**Measured sensitivity — a 38 % change in `Izz` moves the load by 0.04 %:**

| | SELECT default | WTONECG | closure (post L-3) |
|---|---|---|---|
| ga6 `Izz` | 4169.2 | 3022.8 | 2934.0 |
| ga6 side gust | **604.0 lb** | 604.2 (+0.04 %) | 604.2 (+0.04 %) |
| RJ side gust | **7080.4 lb** | 7088.1 (+0.11 %) | 7086.5 (+0.09 %) |

The reason, worth recording because it is not obvious from the formula: the gust
alleviation factor `KGT = 0.88·UGT/(5.3 + UGT)` is **saturated**. ga6's mass
ratio comes out `UGT ≈ 3100` against the 5.3 in the denominator, so `KGT` sits on
its 0.88 asymptote and the whole `Izz`-dependent term is inert. Not a defect — it
is Ch 9's own formula and it is oracle-locked — but it *would not* be inert for a
light airplane at altitude, so a future fixture can put this decision back in
play. Recorded here rather than filed, since nothing is wrong.

Noted for the record: option (b) was feasible — ga6 moves +0.03 %, inside the
±0.1 % Appendix A band — and was declined anyway, because an oracle that passes
by saturation is not an oracle that passes by design.

### 5.5 L-6 as answered — the handedness predicate

Decision of record (user, 2026-08-08). A balanced case is handed iff its
**applied** load set carries lateral content, evaluated **before** closure:

```
handed(case) :=  sum(|fy|) over the applied loads  >  tol
             or  any applied mx / mz couple        != 0
```

Two properties this buys, both of which the alternatives lose:

* **It reads the distribution, not the resultant.** `ga6_normal`'s
  `YAW TO SIDESLIP` nets only −97.8 lb from parts of −683 (yaw) and +586
  (rudder); `Σ|fy| ≈ 1270 lb`. A net-based predicate would mint it unhanded on
  the strength of a near-cancellation and assemble a rudder-kick case as a
  symmetric one — the same silent-symmetry failure plan 11 §10 records for
  `TORS`, arrived at from the opposite direction.
* **It is evaluated pre-closure, so it cannot feed on its own output.** Once L-2
  gives a rolling case a lateral relief field (§5.2), a predicate reading the
  final load set would find lateral content in every case that rolls.

`R` is the computed case — the fin load with the sign SELECT gives it — and `L`
is its reflection through `handed_twin`. This extends B7's rule rather than
replacing it: `ACRL` stays handed through its applied aileron couple, and
`SYMMETRIC_WING_CONDITIONS` stay unhanded because their applied sets have no
lateral component at all. All four v-tail conditions are handed on both fixtures.

### 5.6 L-7 as answered — the lateral-aero limitation, stated

Decision of record (user, 2026-08-08). The fin is the only lateral aero the suite
computes. B8a ships that load reacted by inertia alone, and says so wherever the
case is rendered — deck `$` header, case notes, UI — with the direction of the
error stated, not just its existence:

> The fin is the only lateral aerodynamic load this suite computes. Fuselage and
> wing side force in sideslip are not modelled, so `n_y` and `ψ̈` are
> **over-stated** and the inertia they drive is conservative on every component.
> The fin's own design load is SELECT's, unchanged.

**The magnitude of the overstatement is unknown, and is stated as unknown.**
Quantifying it *is* building the model, so no bound is claimed — unlike the
lumped fuselage `Cm`, where a scalar existed to lump and its size could be quoted
(+4.3 to +6.3 % of `n·W·MAC`). This is the weaker of the two honesty statements
and the note does not dress it up as the stronger one.

Filed on the backlog, paired with **M4-19**: the Multhopp/Nelson strip work is
already building the longitudinal body-aero carrier, and the lateral analog
(`Cy_β`, `Cn_β` from the same slender-body integrand) is its natural sibling.
The sideslip angle the model would need already exists in three of the four
conditions — 19.5°, 15°, and the gust case's effective β; `SUDDEN RUDDER` is
rudder deflection at zero sideslip and has no body side force to add.

### 5.7 L-8 as answered — where fin inertia lives

> **SUPERSEDED IN PART, 2026-08-10** (user decision, taken with the tail-mass
> SSOT step — see `../40_history/00_completed_development.md`). The
> per-component fin deck **does** now carry inertia: `−n_y·W_vt` bending with
> `n_y = (LT25+LT50)/W_case`, plus `−n_z·W_vt` axial along the span. The
> circularity objection below was answered by deriving `n_y` from the fin's own
> side load — SELECT's, already on the condition — so `tail_span` still does not
> import `balance`. **What survives unchanged is the second half of this
> decision:** the assembled balanced case accounts for fin mass in its closure
> field, so the applied set it reads from `tail_span` is `fz − f_inertia` and
> each mass is applied exactly once. The partial-coverage objection also stands
> and is honoured: a condition naming no V-n point gets no lateral term and says
> so.

Decision of record (user, 2026-08-09). The per-component v-tail deck **stays
air-only**. Fin inertia appears in the balanced case, arriving through the
`VTAIL`-tagged items in the §5.2 closure field, at the case's own `n_y`/`ω̇`.

Two reasons, one physical and one structural:

* A per-component deck is a **single-condition beam view**; `n_y` is a property
  of a *balanced case*, and a condition with no derivable payload loading has no
  `n_y` at all — so threading it down would give partial coverage even if it
  worked.
* `balance` imports `tail_span` to read the fin distribution, so `tail_span`
  importing `balance` is **circular**. Doing it anyway would need a third module
  both read — real complexity bought for a partial result.

Plan 09's in-band note is re-worded accordingly: from *"the suite has no lateral
load factor, and applying the airplane's normal `n` to a fin's mass would be a
fabricated load in the wrong direction"* to a statement that fin inertia is
carried in the balanced case, with a pointer to it. The claim that changes is the
reason, not the behaviour.

**Filed, not folded in — the tail-mass SSOT gap.** *(Closed 2026-08-10, along
with the inertia decision above.)* Checking this decision
surfaced that **no shipped fixture populates `tail_mass` at all**, so
`_surface_weight` returns 0 for both surfaces and the **h-tail decks carry no
distributed inertia either** — the "no `tail_mass` entry for this surface" note
is firing on all six airplanes. Meanwhile `weight.items` tags the empennage mass
correctly (ga6 42 lb h-tail / 23 lb v-tail; RJ 520 / 640). This is the same class
as the 427 lb fuselage discrepancy: `TailMassInput` is a parallel mass model that
plan 11's decision **B-2** ("`weight.items` is the mass SSOT") should have
subsumed and did not. It is unrelated to lateral closure — folding it in would
move h-tail per-component deck bytes and digests inside a lateral-closure step —
so it goes on the backlog in its own right.

## 6. What changes, by area

* **`sloads/export/coordinates.py`** — nothing new for reflection (`reflect_*`
  already covers `fy`/`mx`/`mz`; B7 deliberately routed the zero-valued
  components through it "so the lateral families of B8a inherit it already
  checked"). The fin root waterline enters `tail_station_to_airplane`'s existing
  `root_z` argument.
* **`sloads/modules/tail_span.py`** — the v-tail's `z_offset` becomes the fin
  root waterline (L-1); the `inertia_modelled=False` note is re-worded (L-8).
* **`sloads/modules/balance.py`** — `_closure` becomes a 6-DOF solve: three
  translational ratios plus a 3×3 rotational solve on the assembled tensor
  (L-2/L-3); `assemble` gains the fin load set and the lateral resultants;
  `build_balanced_cases` iterates `vtail` conditions as well as `wing` ones,
  minting handed pairs on the `VT-xx` `CaseRef` (§7.1, `handed_case_id`).
* **`sloads/models/results.py`** — `BalancedCaseResult` gains `delta_ny` and
  `delta_yaw` beside `delta_n`/`delta_nx`/`delta_pitch`/`delta_roll`, plus the
  reported tensor and its WTONECG comparison. Schema bump + migration.
* **`sloads/export/sbeam_bridge.py`** — the assembled deck already emits general
  `FORCE`/`MOMENT`; the lateral components flow through unchanged. New `$` header
  lines: `n_y`, `ψ̈`, the fin-waterline provenance, and the L-7 caveat.
* **`app/views/`** — the balanced-case table gains the lateral columns.
* **`CONVENTIONS.md`** — §1's "closes in three symmetric DOF" sentence is
  rewritten for six; §7 gains the lateral-closure owner row; §7.1 gains the
  ±β family as a worked example.

## 7. Acceptance — the gates, with their expected numbers

No printed oracle exists for a balanced lateral case, so per `CONVENTIONS.md` §6
the gate is a stated closure/identity set in CI, written with the feature.

| # | Gate | Target | Tolerance |
|---|---|---|---|
| **G1** | **The yaw DOF reproduces ONENGOUT's ψ̈.** For a given applied yaw moment and a given `Izz`, the closure returns `ψ̈ = M/Izz` — `ONENGOUT.BAS` 282-286, oracle-locked and an entirely independent producer. This is B8a's counterpart to B7's `test_roll_closure_reproduces_winginer`, and the stronger of the two, because the other producer is FAR 23 code rather than a sibling closure. Checked step by step against ONENGOUT's **own time history**. **Found on implementation:** the two producers meet on *no* fixture — `atr42_100`/`dhc8_dash8` enter the `one_engine_out` slice but assemble no balanced case, the other four assemble no `one_engine_out`, and **neither of the two enters engine horsepower, so ONENGOUT cannot execute on any shipped fixture at all** (filed). The gate supplies that one input and reads every other number from the fixture | exact identity | `rel_tol = 1e-12`, >10 steps, vacuity-guarded |
| **G2** | **Six-DOF closure.** All six post-closure resultants about the CG vanish | 0 | machine precision (as B7's four) |
| **G3** | **The assembled deck solves in sbeam with determinate-support reactions ≈ 0** — through plan 10's assembled leg, now exercising `fy`/`mx`/`mz`. This is the gate that catches a lateral sign error. **Shipped with two additions (B8a-4)**, because a zero-target gate is worth only its sensitivity: (a) **vacuity guards** — every assembled case must appear as a subcase and each lateral one must carry >10 % of its own `L_v` in side load into the solver, so the gate cannot pass by applying nothing lateral; (b) a **negative control**, `test_a_flipped_fin_load_breaks_the_assembled_solve` — reverse the fin's `fy`/`mz` alone, leave the closure that balanced the original, and the support must react `+2·L_v·SF` in `y` with the roll and yaw reactions moving too. It does, to the export tolerance, in both unit systems | ≈ 0; control `+2·L_v·SF` | plan 07 §4.1 zero-target |
| **G4** | **The `Izz` reconciliation identity** (§3.4, §5.3) holds per fixture — with L-3 answered it is an **equality**: `Izz(closure) = Izz(WTONECG) − Σ wing self-Izz + Σw·y²(spread)` | ga6 2934 = 2934 (0.0 %), RJ +0.40 % | 1 % |
| **G5** | **Reduction.** A **symmetric** case (`PHAA`/`PLAA`/`PMAA`/`NMAA`/`TORS`) run through the 6-DOF closure keeps `n_x`/`n_z` identical by construction (`F/W`), gives `n_y = 0` exactly, and leaves the lateral relief below 1e-9·n·W. **Amended on implementation (2026-08-09):** the note's "`delta_pitch` unchanged" was wrong — the pitch DOF now solves on a real `Iyy`, so **`q̈` falls 18-22 % on ga6 and 3-4 % on the RJ**. The *deck* still barely moves (the pitch relief is 0.06-0.56 % of a peak node load), but a reported scalar changed, and the gate asserts `q̈ = My/Iyy` with `Iyy > Σw·dx²` rather than claiming equality with the old value | as stated | `rel_tol = 1e-12` on `n`; `1e-9` on `q̈`; lateral relief `< 1e-9·n·W` |
| **G6** | **`ACRL` moves, and by the measured amount.** The one shipped case whose *physics* L-2 changes: the peak nodal companion `fy` of the **roll DOF alone** (ga6 **89.83 lb**, RJ **551.85 lb**), the induced yaw (**+18.93** / **−0.993 deg/s²**), the net `Fy` the companion adds asserted zero, and the yaw shown to vanish when `Ixz` is zeroed. **Amended:** §3.6's 113/717 lb were the *combined* rotational field measured on the shipped `ṗ`; the per-DOF figures above are what the split field applies | as measured | `rel_tol = 1e-3`; `abs_tol = 1e-9·W` on the net `Fy` |
| **G7** | **Handed twins are mirror images** — the existing involution guard extended to a lateral case: `fy`/`mx`/`mz` negate, `fx`/`fz`/`my` identical, `n_y`/`ψ̈`/`ṗ` negate, `n_z`/`q̈` identical | exact | `rel_tol = 1e-12` |
| **G8** | **Appendix A oracles bit-unchanged**, and every per-component deck byte-unchanged **except the v-tail span deck**, whose `GRID` z-coordinates move by the L-1 fin waterline. That single exception is deliberate, is a defect fix (§3.3), and is called out against plan 11 acceptance #5 with a regenerated digest | — | exact |
| **G9** | **The symmetric half still closes** (L-5). With the fin load removed, every lateral case meets plan 11 §6's 1 % force and moment gate — i.e. adding a lateral load did not contaminate the symmetric physics | ga6 V-n 14: Fz +0.014 %, My +0.341 %; V-n 35: +0.275 / +0.648 %. RJ V-n 14: +0.214 / +0.663 %; **V-n 95: +0.344 / +1.586 %** | 1 %, with a **per-fixture ceiling** where it already bites — the RJ's BAL C point is over, and it is the largest instance yet of the filed "RJ low-CL cases exceed the 1 % pitch gate" item (previous worst `TORS` 1.174 %). Bounded per fixture as `_PITCH_RESIDUAL_CEILING` already does, never by widening the gate |
| **G10** | **The lateral quantities are pinned per fixture** (L-5) — `n_y` and `ψ̈` for all four conditions on both fixtures, so a self-consistent-but-wrong fin load cannot balance beautifully and pass silently. **Extended on implementation** to four numbers per condition (the net fin load and `ṗ` as well), and `n_y` additionally asserted structurally as `L_v/W` rather than only pinned | fin load and `n_y` exactly §3.1's tables; **`ψ̈` restated from measurement** — see below | `rel_tol = 1e-4`; red in either direction |
| **G11** | `ruff` clean, `pytest` green on 3.9 / 3.11 / 3.12 | — | — |

**G10 amended on implementation (2026-08-09).** §3.1's `ψ̈` figures were measured
against the *placement-only* `Izz` that preceded decision L-3; the shipped
tensor is larger (ga6 2933.5 against 2598), so every yaw is smaller. The fin
loads and `n_y` are **unchanged from §3.1 to the last digit** — they do not
depend on the closure — and the roll accelerations are new (§3.1 predated the
six-DOF field). The gate's table, restated from measurement and now the record:

| Condition | ga6: `L_v` lb / `n_y` g / `ψ̈` / `ṗ` deg/s² | RJ: `L_v` lb / `n_y` g / `ψ̈` / `ṗ` deg/s² |
|---|---|---|
| `SUDDEN RUDDER` | +585.7 / +0.17227 / +178.05 / −12.04 | +6907.3 / +0.20931 / +51.57 / −57.75 |
| `YAW TO SIDESLIP` | −97.8 / −0.02875 / −19.44 / +3.24 | −3548.2 / −0.10752 / −20.84 / +31.13 |
| `YAW 15 NEUTRAL` | −525.7 / −0.15463 / −151.91 / +11.75 | −8042.7 / −0.24372 / −55.70 / +68.37 |
| `SIDE GUST` | +604.0 / +0.17764 / +185.51 / −20.16 | +7080.4 / +0.21456 / +42.93 / −77.88 |

ga6 `SUDDEN RUDDER` is 178.05 deg/s² against §3.1's 205.7 — a ratio of 0.866
where the `Izz` ratio alone gives 0.886, the difference being the `Ixz` coupling
L-2 introduced. The RJ's roll is large because B8a-1 gave its fin a real
waterline (+86.0 in against the pre-B8a-1 −1.0 in), which is the defect that
step existed to fix.

**Pinned facts** (recorded per fixture, red when they change, per the project's
"pin the finding" practice): the four cases' `n_y` and `ψ̈` (§3.1); the
`Izz(assembled) / Izz(SELECT)` ratio (ga6 0.62, RJ 0.67 / 0.86); the
`Ixz`-coupling fraction (§3.5); and which fixtures can produce a lateral balanced
case at all — `ga6_normal` and `concept_regional_jet` only, for the same
payload-case reason already pinned in `test_balance.py`.

## 8. Steps

| Step | Scope | Tier | Effort |
|---|---|---|---|
| ~~**B8a-1**~~ ✅ | Fin root waterline (L-1): input + derived default + `assumed` flag; v-tail deck `GRID` z fixed; digest regenerated. **SHIPPED 2026-08-09** — schema v43, `tail_geometry.fin_root_waterline` as the single owner (read by the three-view too, which had the same defect), roll arms +14.0 / +86.0 in as predicted, `sbeam/vtail_span_cards` + `txt/tail_span` the only Imperial channels that moved | M | S |
| ~~**B8a-2**~~ ✅ | The 6-DOF closure (L-2/L-3): full d'Alembert field, 3×3 rotational solve on the assembled tensor, non-wing self-inertia relief; G1/G2/G4/G5/G6. **SHIPPED 2026-08-09** — `sloads/rigid_body.py` as the single owner, `mass_distribution.assembly_distributes_mass` as the L-3 predicate, `BalancedCaseResult` gaining `delta_ny`/`p_dot`/`q_dot`/`r_dot`/`closure_inertia`. All six DOF close to ≤ 2e-16 of `n·W`; `Izz(closure)` 2933.5 ga6 CG2 against G4's predicted 2934. **The B7 gate was restated** (see §5.2) and **the assembled deck was added to the Imperial baseline**, which had never covered it | L | M |
| ~~**B8a-3**~~ ✅ | Lateral case assembly (L-6/L-7): the fin load set, the `VT-xx` handed pairs, in-band caveats; G7/G9/G10 (§8's "G6" was a slip — G6 shipped with B8a-2). **SHIPPED 2026-08-09** — `balance.fin_sets` consuming `tail_span` through the `export/coordinates` frame map, `balance.is_handed` as the single L-6 predicate (with its own drift guard) and `is_lateral`/`fin_load` as the single readers of the `vtail-air` tag. Eight new cases per fixture (`VT-01R/L`…`VT-04R/L`), the L-7 caveat carried as a case note into the deck and the report. The pitch ceiling became **per family** rather than wider (ga6 lateral 0.70 %, RJ 1.60 %), so the symmetric bounds keep their bite; only `csv/balance`, `txt/balance` and `sbeam/balanced_deck` moved in the Imperial baseline — every per-component deck and every Appendix A oracle is byte-unchanged (**G8**) | L | M |
| ~~**B8a-4**~~ ✅ | Assembled deck + sbeam leg + UI columns; G3. **SHIPPED 2026-08-09** — deck `$` header `LATERAL case:` block, `Closure dNy`/`Yaw acc`/`Roll acc` columns in `balanced_case_rows`, a `ΣFy` column and a fin-load row in the Streamlit breakdown (which reported every lateral case as a row of zeros without it), and G3 through plan 10's existing assembled leg, now vacuity-guarded and calibrated by a negative control. The subcase-map comment line is wrapped: the longer condition names pushed it past 72 columns | M | S–M |
| ~~**B8a-5**~~ ✅ | Closure trail: `CONVENTIONS.md` §1/§7/§7.1, `PROGRAM_SPEC.md`, `theory_sources.md`, `DATA_DICTIONARY.md` regen, CHANGELOG, history (Tier L, full step format). **SHIPPED 2026-08-09** — `CONVENTIONS.md` §1 gained the "a residual the airplane is not meant to balance is reported, never gated" rule (with the per-family ceiling rule), the L-7 in-band caveat and the L-8 fin-inertia location; §7 gained `is_handed` and `is_lateral`/`fin_load` as owners with their guards; §7.1's "decided by a non-zero `unbal_moment`" was replaced by the predicate and the ±β family written up as its worked example. `DATA_DICTIONARY.md` regenerates to **no change** — B8a-3 added no schema fields, so `SCHEMA_VERSION` stays at 43. Step 8 removed from the backlog's priority table | S | S |

**Effort: M–L, ≈ 2–2.5 sessions**, matching plan 11 §8's estimate for phase 3.

## 9. Risks and open questions

| # | Item | Notes |
|---|---|---|
| R1 | **L-2 changes a shipped case, and `ACRL` changes by more than bytes.** | Symmetric cases move by ≤ 0.08 % of a node load (the pitch companion). `ACRL` gains a 113/717 lb-per-node lateral field and a yaw DOF — a **physics** change to a shipped deliverable, so it carries the Tier-L trail (design note ✓, `theory_sources.md` citation, history entry) rather than passing as a refinement. Plan 11 acceptance #5 says "if a digest moves, something leaked"; here it moves for a stated reason, and G5/G6 assert the delta instead of re-baselining silently |
| R2 | **The fin waterline has no fixture data.** | Every fixture will run on the derived default at first, marked `assumed` — the same position the empennage planform is already in (filed `[V]` item). Entering the six airplanes' fin waterlines is S-tier fixture work and pairs with that item |
| R3 | **`n_y` and `ψ̈` are over-stated by the missing body side force** (§3.2, L-7). | Conservative for structure everywhere it lands, but the *acceleration* is not the airplane's real one, and the deck must say so rather than let a consumer read `ψ̈` as a flight-mechanics quantity |
| R4 | **`Ixz` makes the rotational solve genuinely coupled.** | A 3×3 solve, not three ratios (§3.5). The tensor is symmetric positive-definite for any real mass set, so the solve is unconditionally well-posed; a singular tensor means a degenerate mass model and should raise, not silently pseudo-invert |
| R5 | **Which `Izz` a reader believes.** | Three producers, all defensible, two of them printed in Appendix A (§3.4). The mitigation is that the case states all three and the reconciliation identity, rather than picking one and hiding the others |
| R6 | **Scope creep into ONENGOUT.** | 23.367 is a transient and stays out (§4); it is used only as G1's reference identity |
