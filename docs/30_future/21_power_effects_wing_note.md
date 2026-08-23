# Design note — power effects on the wing: thrust and propeller-wake loads (wing-mounted propellers)

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: AGREED 2026-08-15 (decisions P-0…P-12, §7). PARKED except for one
carve-out, which SHIPPED 2026-08-17 (issue #10, tier M):** the **hub thrust
card** — one user-entered `EngineInput.thrust_lb` per engine, applied as an
axial `FORCE` at that engine's hub in the assembled **flight** cases and on the
LRA model's hub node, reacted by the closure's `n_x` and `q̇`. It takes from
this note only the hub station and the sign; **everything else here stays
parked** — the propeller normal force `N_p`, the slipstream band and its strip
increments, the DATCOM §4.6 derivative increments, the re-trim
(`retrim_with_power`), `power_policy.py`'s per-family thrust rating, the P-6
thrust-line incidence/toe angles, and the `-P` case family. The carve-out
therefore does **not** discharge §4's re-trim: a case carrying hub thrust is
deliberately *not* re-trimmed, and the unbalance is stated in-band and carried
by the closure (option B of §4.2, which this note rejected for the *full* step,
is accepted for the carve-out precisely because the carve-out applies no
slipstream and claims no trim). Shipped behaviour of record:
[`../20_theory/balanced_cases.md`](../20_theory/balanced_cases.md) §2.1 and
`CONVENTIONS.md` §7; gates `tests/test_hub_thrust.py`. The next artefact for the
rest is still the code implementation plan (§8 is its skeleton).** Written to `CLAUDE.md` required practice 1 (design note before
code, physics/L step). Follows the L-7 note's form
([`../40_history/33_l7_lateral_body_aero_note.md`](../40_history/33_l7_lateral_body_aero_note.md)): every
option is listed, the recommendation is marked, agreed decisions will be tagged
**[DECISION P-n]** as they are taken.

**Scope agreed 2026-08-15 (chat):**
- Wing-mounted **propeller** installations only (tractor). Nose-mounted singles
  and pylon-mounted turbofans are out of scope for this note (thrust-line-only
  treatment for those is a stated seam, §9).
- Estimation **and** user-supplied data (option (c) of the scoping questions):
  an empirical estimate by default, user wind-tunnel/CFD increments override it
  field by field.
- Framed **both** as a FAR 23 compliance item (where the rule text supports it)
  and as a concept-mode superset (Phase C mission), the FAR23 core untouched.
- Demonstration fixtures: `examples/atr42_100.project.json`,
  `examples/dhc8_dash8.project.json`.
- **Engine-out is not a wing case here** — it is critical on the empennage for
  the sideslip achieved and stays with `one_engine_out` (v-tail) and the
  balance `out-of-family` skip.

Topics, in the order they are being worked: §1 physics · §2 cases that get
thrust · §3 GUI · §4 balanced-case generation · §5 verification that today's
wing cases are zero-thrust · §6 empennage.

---

## 1. Physics — what "power on" adds to the wing, and how it moves the airplane's `CLα` / `Cmα`

### 1.1 What the suite has today

- **Nothing power-dependent reaches a wing load.** AIRLOADS/NETLOADS, wing
  inertia, the aileron cases and the balanced free-free model
  (`balance.assemble`) are all computed thrust-free; `balance.py:1158` states
  "the suite has no distributed thrust" and closes the x-DOF on net drag alone
  (`n_x = -D/W`). Wing-mounted engines enter the wing model as **mass only**
  (concentrated masses in `wing_inertia`, CONM2 export).
- The only slipstream physics is FLAPLOAD sub 500 (`flap._slipstream_velocity`,
  Ref 1 p109): momentum-theory fully-developed slipstream `U1` absorbing
  0.85·take-off HP, disc contracted to the flap, nacelle/body frontal area added,
  band `BL_eng ± r`, load ×`(V_ss/VF)²` = **1.407** on the GA-6 (App A p201,
  `tests/test_flap.py`). It is applied to the flap panel only.
- The engine-mount module (`engine.py`) already computes the **thrust**
  (`Fx_thrust = T·ω/V`, key `fx_thrust`), the **torque** (`mx_mount_torque`) and
  the **gyroscopic** pitch/yaw couples for FAR 23.361/23.371 — as mount loads
  that stop at the mount.

### 1.2 Regulatory position (bundled text; CFR pull still to do)

| Rule (Ref 1 text as bundled) | What it says about power | Bearing on this step |
|---|---|---|
| 23.301(b) | air loads in equilibrium with inertia, distributed to represent actual conditions | general |
| 23.331(c) | "mutual influence of the aerodynamic surfaces must be taken into account" | the tail-in-slipstream / downwash change is a *mutual influence* |
| 23.345(d) (flap conditions) | "thrust, slipstream, and pitching acceleration **may be assumed to be zero**" for the airplane as a whole | power-on flap-extended *airplane* cases are **not** required — a permitted simplification, not a prohibition |
| 23.457(b) | slipstream at **take-off power**, ≥1.4 VS, n may be 1.0 — for the flaps | already ported (FLAPLOAD); the wing strips under the same slipstream are the natural extension |
| 23.427(a) | tail unsymmetrical loads "arising from yawing and slipstream effects" | tail side (§6) |
| 23.361 / 23.371 | torque and gyro loads on the **engine mount and its supporting structure** | for a wing-mounted engine the supporting structure **is the wing** — thrust/torque/gyro at the nacelle node into the wing box is a compliance load path, not an enhancement |
| 23.367 | engine failure | out of scope (v-tail; agreed) |

**[DECISION P-3, 2026-08-15] Rule basis is the pre-Amendment-64 FAR 23 —
the 23.331/23.421-era Subpart C the suite is written to** — not the current
performance-based Part 23 (§23.2200 ff.).

**Agreed precondition (2026-08-15):** the clean-wing symmetrical conditions (23.331–23.341) as
bundled do not mention power. Pull that era's text of 23.331/23.333/23.361/
23.371/23.421/23.423/23.457 (and 25.331(a) for the concept-mode argument) into
`reference/14CFR_23_power_effects.md` **before** the note is agreed, exactly as
`reference/14CFR_25_335_design_airspeeds.md` was done — nothing here is to be
asserted from memory. Working position until then: the **mount → wing** load path
is required by 23.361/23.371; power-on **airloads** are a *rational-analysis*
choice (23.301(b)) that the concept mission wants and the FAR23 oracle core does
not exercise.

### 1.3 Decomposition of the power increment (propeller-driven, tractor)

The standard decomposition is DATCOM §4.6.1 (lift) / §4.6.2 (pitching moment) /
§4.6.3 (drag), whose Digital-DATCOM implementation is bundled
(`reference/datcom/datcom.f:24395–25200`, `$PROPWR`). Every term below is either
a **point load** at the propeller/nacelle, a **strip increment** on the immersed
wing, or a **tail increment**; that is the split a loads code needs, and it is
also the split the DATCOM routine keeps internally (`DCLT, DCLNP, DCLQ, DCLAW,
DCLHQ, DCLHE, DCMT, DCMNP, DCMQ, DCML, DCMHQ, DCMHE`).

**(a) Direct propeller forces — point loads at the disc / mount**

| Term | Physics | Enters | α-dependence |
|---|---|---|---|
| Thrust `T` along the **user-defined thrust line** (hub point + pitch incidence `i_T` + toe angle `τ`, **[DECISION P-6]** §3.1) | `T = η·P/V` at constant shaft power (suite: `0.85·HP·550/V`); or `T = Q·ω/V` (engine.py) | `Fx = T cos i_T cos τ`, `Fz = T sin i_T`, `Fy = ∓T sin τ` (toe-in → inboard side force, mirrored on the pair: net zero, but a real chordwise/lateral load at each nacelle and a per-engine yaw couple about the CG) at the hub; `ΔCm_T = −T·z_T/(q S c̄)` (thrust-line arm from CG, sign per CONVENTIONS) | `ΔCL_T = T_c sin α_T` → small `CLα` contribution `≈ T_c` |
| Propeller normal force `N_p` | `N_p = q·S_p·f·CNα_p·α_p`; `CNα_p` from blade angle at 0.75R and blade solidity ("engine factor" `K_N`, DATCOM Fig 4.6.1-25a/b); `α_p` = the **in-plane inflow angle to the shaft** — pitch: case α − `i_T` **plus wing upwash at the disc** (Fig 4.4.1-73); yaw: the toe angle `τ` (and sideslip in lateral cases) — the disc's in-plane force is symmetric in any inflow direction, so toe-in gives a steady side force `q S_p f CNα_p τ` at each hub, mirrored on the pair | in-plane point load at the hub (vertical from α, lateral from τ/β), arm `x_p − x_cg` ahead of the CG | **the main `CLα`/`Cmα` driver**: `ΔCLα = f·CNα_p·(S_p/S)·(1+∂ε_u/∂α)` per engine; `ΔCmα = +ΔCLα·(x_cg − x_p)/c̄` — **destabilizing** for a tractor |
| Torque `Q` about the shaft | 23.361, already in `engine.py` | mount `Mx` into the wing box (opposite sign per engine if counter-rotating — `CROT`) | none (inertial/mechanical) |
| Gyroscopic couples | 23.371, already in `engine.py`; need pitch/yaw rate of the case | mount `My`/`Mz` into the wing box | none |

**(b) Slipstream over the immersed wing — strip increments**

| Term | Physics | Enters |
|---|---|---|
| Dynamic-pressure rise | momentum theory: `V_s² = V² + 2T/(ρ A_p)`, i.e. `q_s/q = 1 + T/(q A_p) = 1 + 8 T_c'/π` — the same quantity FLAPLOAD sub 500 computes as `(V_ss/VF)²`; contracted radius at the wing from the same routine | on strips inside `BL_eng ± r_s`: `Δl(y) = (q_s/q − 1)·q·c(y)·c_l(y)·k_q` where DATCOM applies an empirical realisation factor `k_q < 1` (Fig 4.6.1-? via `DCLQ`) — the theoretical full `Δq` over-predicts | 
| Slipstream downwash at the wing | the propeller's own downwash `ε_p = ∂ε_p/∂α_p · α_p` (DATCOM Fig 4.6.1-26, `DEPDAP = C1 + C2·CNα_p`) lowers the effective α of the immersed strips | strip `Δα` → `−a_0·ε_p` on the immersed strips (`DCLAW`); this is a **negative** `CLα` contribution partly cancelling (a)-`N_p` |
| Swirl (slipstream rotation) | local `±Δα` on the two halves of the band; net lift ≈ 0, small rolling moment and a local up/down asymmetry across the nacelle | **not in DATCOM's lumped method**; option only (§1.5) |
| Nacelle drag in the slipstream | `ΔCD0` (DATCOM 4.6.3) | drag carrier (note 20 seam), not a wing lift item |

**(c) Tail — increments that change the balancing load (topic 6, listed here for the derivative picture)**

| Term | Physics | Enters |
|---|---|---|
| Tail dynamic-pressure ratio `q_h/q` | slipstream immersion of the tail (DATCOM computes the immersed tail area from the slipstream centre-line height `Z_s = z_p + x̄_p tan α_p` and radius) | tail load ×`q_h/q` → **stabilizing** `Cmα` term |
| Power-induced downwash `Δε`, `Δ(dε/dα)` | DATCOM 4.6.1 (`DEUDA`, `EPOWR`) | tail effective α down → **destabilizing** `Cmα` term, and a `Cm0`-like shift |

**Net effect on the airplane (what to report):** with all terms,
`CLα_pow = CLα_off + T_c cos α + Σ_eng[ f·CNα_p·S_p/S·(1+∂ε_u/∂α) ] + (q_s/q−1)·k_q·(S_i/S)·a_w − (S_i/S)·a_w·∂ε_p/∂α + (tail terms)`, and `Cmα` moves by the
`N_p` arm (forward, destabilizing), the immersed-wing lift arm (sign set by
`x_ac,wing − x_cg`), and the tail pair (`q_h/q` stabilizing vs `Δε`
destabilizing). The **usual net for a twin-turboprop tractor at high `T_c` (low
speed) is a forward neutral-point shift**; the magnitude is what the estimator
produces, and it is *checkable*: Digital DATCOM ex3 prints case 3 (power off) and
case 4 (`$PROPWR`, `T_c = 0.15`, `Y_p = 0`, 4 blades, `β_0.75 = 18°`) side by
side — `CLA`/`CMA` per α, `q_h/q∞`, `ε`, `dε/dα` — the printed **oracle for the
lumped increments** (`reference/datcom/examples/ex3.out:1468ff`).

**How this reaches the suite's numbers.** The suite does not carry airplane
`CLα`/`Cmα` as inputs; each condition is a load factor at a speed, `CL = nW/(qS)`,
Schrenk-distributed, trimmed by the tail-load moment equation with the wing
`Cm` and Perkins downwash `ε = 114.6·CL_w/(π AR_w)` (Ref 1 p~6140). Power
therefore enters as **per-case increments in the trim** — thrust arm, `N_p` and
its arm, `ΔCm0`, tail `q_h/q` and `Δε` — plus **strip increments** on the immersed
wing; the "effect on `CLα`/`Cmα`" is a *derived, reportable* pair (`ΔCLα`,
`ΔCmα`, `Δx_np/c̄`) that the estimator can print per case and that the DATCOM
oracle checks. It is not a new input field.

### 1.4 Options for the source of the increments

| | Option | Gives | Oracle | Inputs needed | Verdict |
|---|---|---|---|---|---|
| **A** | Momentum theory only — generalize FLAPLOAD sub 500 to the wing strips (`q_s/q` on the band), thrust as a point load | strip `Δq` lift, thrust force/arm | App A p201 (band 22.8–113.2 in, ×1.407) — for the band and factor only | none new beyond today (HP, prop dia, BL, nacelle area) | necessary but **not sufficient**: no `N_p` (so no `CLα`/`Cmα` shift), theoretical `Δq` over-predicts, nothing at the tail |
| **B** | Port DATCOM §4.6.1/4.6.2/4.6.3 (Digital DATCOM `PROPWR` path) — lumped `ΔCL`, `ΔCm`, `ΔCLα`, `ΔCmα`, `q_h/q`, `Δε` per case; **distribute** the wing part onto the strips with A's band | the full derivative picture, tail terms, printed oracle; same provenance/lineage as L-7 | ex3 case 4 vs case 3, ±0.1 % on the *increment* | per engine: hub `x, y, z`, `i_T`, blade count (`prop_blades` — already captured, unused), `β_0.75`, blade-width ratios at 0.3/0.6/0.9 R **or** the engine factor `K_N` (default from Fig 4.6.1-25b), prop radius (have); wing upwash geometry (have); tail `z` vs thrust line (have) | **recommended estimator** — 1976 methods, validated on light twins/singles, but the only *published, oracle-backed* method in the bundle |
| **C** | User-supplied increments — `ΔCL(α,T_c)`, `ΔCm(α,T_c)`, `ΔCLα`, `ΔCmα`, `q_h/q`, `Δε` (or `dε/dα`) from wind tunnel / CFD; distributed onto strips with A's band | whatever the data has | none (data is the authority) | the table itself | **required override** (agreed): each field individually overrides B's estimate; the source is stamped in the methods section |
| D | Higher-fidelity wake model (VLM/lifting-line with actuator disc) | distributed strip loads directly | none in bundle | geometry only | out of mission (no oracle, big build); noted as a future seam |

**[DECISION P-1, 2026-08-15 — agreed]:** **B (DATCOM §4.6.1–4.6.3 port) as
the default estimator, C as field-by-field user override, A as the single
distribution rule** — one owner
(`flap._slipstream_velocity` generalized into a `slipstream` helper) supplies
the band and `q_s/q` to the flap module (unchanged numbers), the wing strips
and the tail immersion. The invariant that ties lumped to distributed:
`Σ_strips Δl·Δy = ΔL_wing,lumped` per case (a drift-guard test).

### 1.5 Terms deliberately excluded (stated, not silent)

- Slipstream **swirl** asymmetry across the nacelle — no DATCOM method; would
  need a swirl model. Recorded as an option, off.
- Nacelle aerodynamic lift/drag in the slipstream — belongs to the body-drag
  carrier seam ([`20_body_drag_carrier_note.md`](../40_history/24_body_drag_carrier_note.md)).
- Power effect on `CL_max`/stall and on the flapped-wing `Cm0` beyond DATCOM's
  terms; compressibility on the propeller (`CNα_p` is low-speed).
- Engine-out (agreed out of scope).

### 1.6 Assumptions carried until decided in later topics

- **[DECISION P-0, 2026-08-15]** The propeller normal force `N_p` (P-factor at
  angle of attack, acting at the disc ahead of the wing) **is included** in the
  load set alongside thrust, torque and gyro — it is the `CLα`/`Cmα` driver;
  without it the step is option A alone.
- **[DECISION P-2, 2026-08-15]** Thrust rating per case: **low-speed,
  gear-down / flaps-down cases use take-off power; flaps-up / gear-up cases use
  max-continuous power.** Thrust from constant shaft power, `T = η·P/V`, with
  `η` an input per engine defaulting to the suite's `0.85` (so the flap
  slipstream and ONENGOUT numbers are reproduced when left at default). §2 turns
  this into the per-family policy table.
- Empennage: power-on tail loads flow through the balanced model's re-trim; whether
  the tail *modules* also gain power variants is §6.

---

## 2. Which cases get thrust, and at what rating

### 2.1 What the wing case set is today

The balanced deck's wing families are `BALANCED_WING_CONDITIONS` =
`PHAA, PLAA, PMAA, NMAA, TORS` (symmetric) + `ACRL` (handed)
(`balance.py:255–264`), each SELECT's pick from the **clean-wing** V-n set
(`select.py:86–91`: `STALL +N / MAN A` → PHAA; `MAN D / GUST D` → PLAA;
`MAN C / GUST +C` → PMAA; negatives → NMAA; `AC ROLL` → ACRL; `ST ROL A/C/D` →
TORS). **There is no flap-extended wing balanced case**: the landing-configuration
V-n points (`STALL 2G, MAN 2G VF, MAN 0G VF, GUST ±VF, BAL VF, BAL 1.4VSF`,
`flight_envelope.py:358–365`) feed only the h-tail `…EXTENDED` conditions and
the FLAPLOAD panel. Gear position is a configuration label only — nothing
aerodynamic in the suite depends on it.

The engine-mount module already defines the FAR power combinations as **mount**
conditions (`engine.py`): 23.361(a)(1) *take-off torque (×factor) with 75 % of
the limit loads of flight condition A*, 23.361(a)(2) *max-continuous torque
(×factor) with 100 % of condition A*, 23.361(a)(3)/(b)(1) turboprop-only torque
cases, and 23.371(b) *gyroscopic couples (yaw 2.5 rad/s, pitch 1.0 rad/s, each
sense) with n = 2.5 and max-continuous thrust* — four sub-cases. Today they stop
at the mount; for a wing-mounted engine 23.361/23.371 name "the mount **and its
supporting structure**", i.e. the wing.

### 2.2 The two kinds of power-on wing case

**Kind I — FAR-defined combinations (compliance).** The 23.361/23.371 mount
cases carried into the wing box at the nacelle node, each on top of the airplane
state the rule names. Their thrust rating is the rule's, not the P-2 default:

| ID (proposed) | Rule | Airplane state | Nacelle load set | Rating |
|---|---|---|---|---|
| `361A1` | 23.361(a)(1) | 0.75 × condition A (PHAA parent, same CG/weight, loads scaled 0.75) | torque `Q_TO × factor`, thrust `T_TO`, `N_p` at the parent α | **take-off** (rule) |
| `361A2` | 23.361(a)(2) | 1.00 × condition A (PHAA) | torque `Q_MC × factor`, `T_MC`, `N_p` | **max-continuous** (rule) |
| `371-1..4` | 23.371(b) | n = 2.5 symmetric case at **VA** (**[DECISION P-7]** — 23.371 names no speed; `engine.py`'s VSF-based thrust stays as the *mount* number, the wing-box case is assembled at VA with the thrust of that speed; the two are stated side by side) | gyro `My`/`Mz` (four sense combinations), `T_MC`, `N_p`, `Q_MC` | **max-continuous** (rule) |

23.361(a)(3)/(b)(1) (turboprop torque-only cases) stay mount-local: they carry no
flight loads, so there is nothing for a balanced case to balance (same logic as
the gear-design-only skip, `balance.SKIP_REASONS`).

**Kind II — rational power-on variants of the wing families (P-2 policy).** The
same SELECT case, re-trimmed with the full power increment of §1.3. The rating
follows **P-2**: flaps-up/gear-up → max-continuous; flaps-down/gear-down →
take-off.

| Family | Variant | Rating | Why it can govern | Recommend |
|---|---|---|---|---|
| PHAA (VA, +n_max, high α) | `PHAA-P` | MC | highest clean `T_c` (lowest V), `N_p` largest (highest α), slipstream up-bending inboard, thrust/`N_p` torsion at the nacelle | **yes — the primary case** |
| PMAA (VC, +n_max) | `PMAA-P` | MC | moderate `T_c`; torque/`N_p` torsion at higher q | yes |
| PLAA (VD, +n_max, low α) | `PLAA-P` | MC | `T_c` small at VD, `N_p` small at low α; torque is speed-independent and full | yes (cheap; envelope decides; expected non-governing — stated) |
| NMAA (−n) | `NMAA-P` | MC | `N_p` reverses with α and **adds** to down-bending; `T sin α` negative | yes |
| ACRL (aileron roll, handed) | `ACRL-P` (pair) | MC | thrust/`N_p`/slipstream on a rolling case; **no gyro from roll rate** (the shaft is the roll axis) | yes |
| TORS (steady roll) | `TORS-P` | MC | as ACRL | yes |
| **flap-extended, 23.457(b) point** `BAL 1.4VSF` (n = 1.0, flaps down) | `SLIP-P` (new wing condition) | **TO** | the maximum-slipstream case — lowest speed, take-off power; the same slipstream the flap module already amplifies ×1.407 on the GA-6, now on the wing strips under it | **yes — the flap-config power case** |
| flap-extended 23.345 airplane cases (`MAN 2G VF`, `GUST ±VF`) | `…-P` | TO | 23.345(d) *permits* thrust = 0; **their power-off wing parents do not exist today** | **no** — out of this note; recorded as a seam (§9): if flap-extended wing balanced cases are ever added, this row is TO power |
| v-tail / h-tail families | — | — | topic 6 | — |

**Options considered for Kind II's extent.**
- (i) variants for **every** clean wing family (table above): +6 symmetric/handed
  cases + `SLIP-P` ≈ **+8 cases** (ACRL pair). Uniform, honest, the envelope
  arbitrates; the deck already carries 24 ground families, so the growth is modest.
- (ii) PHAA/PMAA/SLIP only: leaner, but "PLAA/NMAA don't govern" becomes an
  unverified prose claim — exactly what the practice-3 rule forbids.
- (iii) power-on **replaces** power-off (no duplicate): breaks the oracle
  reduction and hides that power-off can still govern (`n_x`, tail-load sign).

**[DECISION P-4, 2026-08-15 — agreed]:** (i). Also agreed: `SLIP-P` on `BAL 1.4VSF` is the flap-config power case and the 23.345 flap-extended power cases are deferred (seam, §9). Every row lives in **one policy table
with a basis column** (`power_policy.py`, the `safety_factors.py` pattern): a
family it cannot classify is flagged, never defaulted; the FAR-defined Kind I
rows carry the rule's rating in place of P-2's default and say so.

### 2.3 Thrust magnitude — the arithmetic, per case

- `T = η·P_rating / V_TAS` at the case's altitude (`VnPoint.altitude_ft`), with
  `η` per engine (default `0.85`, the suite's ONENGOUT/FLAPLOAD constant) —
  **P-2**. `T_c = T/(q S)` uses the case q (EAS). Guard: cap `T` at the
  momentum-theory static thrust `T_s = (2ρA_p)^{1/3}(ηP)^{2/3}` so a very low
  `V` cannot blow it up (never active at ≥1.4 VSF, stated).
- Torque `Q = P/ω` at the rating's shaft speed, ×the 23.361(c) factor —
  **owned by `engine.py`**, unchanged.
- `N_p` at the parent case's α (from the trim), including wing upwash at the disc.
- Slipstream `q_s/q`, band, contraction: the §1.4 single owner, at the case's
  `T` and `V`.
- Kind I cases apply the mount module's own numbers (`Fx_thrust`,
  `Mx_mount_torque`, gyro `Myy/Mzz`) — the wing sees exactly what the mount
  report shows, one owner.

### 2.4 Case identity

Power state is an attribute of the case definition (extends note 17's
case/load-ID linkage): `power_state ∈ {OFF, MC, TO}` plus, for Kind I, the rule
sub-case. Every existing ID is unchanged (`OFF` is the default and prints no
suffix); variants append `-P` (`PHAA-P`), the rating being in the case table
rather than the ID because P-2 makes it a function of the family. Kind I IDs are
the mount module's (`361A1`, `361A2`, `371-1..4`), so the mount report and the
wing deck name the same case. Detail (deck subcase sequence, handed pairs) in §4.

---

## 3. GUI — where the inputs live and what the engineer sees

### 3.1 What the model already holds, and what is new

`Engine` (`models/inputs.py:70–108`) already carries per engine: designation,
type, weight, `engine_cg`, `prop_cg` (**the hub position**, `XPROP/YPROP/ZPROP`),
`prop_diameter_in`, `prop_blades` (captured, unused today), `takeoff_hp` /
`max_cont_hp`, `takeoff_rpm` / `max_cont_rpm`, torque, rotors. So the geometry
and ratings for §1–§2 exist; **new per-engine inputs** are only the propeller
aerodynamics for the DATCOM estimator:

| New field (per engine) | Meaning | Default | Needed by |
|---|---|---|---|
| **thrust line** — `thrust_incidence_deg` `i_T` (pitch, nose-up +) and `thrust_toe_deg` `τ` (toe-in +) through the hub point `prop_cg` **[DECISION P-6, agreed]** — the user defines it; engines are often toed slightly inboard. Stored canonically as **hub point + two angles**; the GUI also accepts a **second point on the shaft** and converts it to the angles (with the derived angles displayed), so either way of defining the line is available and only one representation is persisted | 0 / 0 | thrust components, `N_p` inflow angles, torque axis, gyro axis |
| `prop_efficiency` `η` | for `T = η P/V` | 0.85 (suite) | P-2 |
| `blade_angle_075_deg` `β_0.75` | blade angle at 0.75 R | optional | `CNα_p` (Fig 4.6.1-25a) |
| `blade_width_ratio_03/06/09` **or** `engine_factor_kn` `K_N` | blade solidity → `CNα_p` correction | optional; `K_N` estimated from `prop_blades` and Fig 4.6.1-25b when blank | `CNα_p` |
| `rotation` (CW/CCW seen from behind) | torque sign; counter-rotating pair | CW | torque hand, `CROT` |

and **one new project slice** `power_effects` (`PowerEffectsInput`):
`enabled` (default **False** → the project reduces exactly to today), `method`
(`estimate` = DATCOM B / `user` = C, per field), the user override table (§3.3),
and nothing else — the policy table is code (`power_policy.py`), not data.

### 3.2 Options for placement

| | Option | For | Against |
|---|---|---|---|
| A | A **new workflow page** "Power Effects" (Flight-loads phase, before Balanced Cases) holding engine prop-aero inputs, the enable/method switch, the override table and the per-case increments review | one place to look; the derived `ΔCLα/ΔCmα/Δx_np` review sits next to its inputs | splits `Engine` editing across two pages (Engine Mount already owns the per-engine form); adds a `workflow.py` step (drift-guarded, fine, but the FAR23-only user sees a page that is off by default) |
| B | **Fold into existing pages** — prop-aero on Engine Mount; enable/method/override on Aerodynamic Data; case column + policy on Balanced Cases | every slice keeps its single owner page; no new step; the FAR23 user's flow is unchanged | the inputs an engineer needs for one feature are on three pages; Engine Mount is a *later* phase than Balanced Cases (precedent: the flap slipstream already reads HP from Engine Mount, and Weight & Mass says so in a caption) |
| C | **Hybrid** — B's ownership, plus a read-only **"Power effects" review section on Balanced Cases** that shows the whole picture (per-engine `T, T_c, N_p, q_s/q`, band, `ΔCLα/ΔCmα/Δx_np`, policy row, source stamp) and links to the two input pages | single owners kept; the review lives where the cases are | slightly more UI code |

**[DECISION P-5, 2026-08-15 — agreed]: C.**

### 3.3 The pages, concretely

**Engine Mount Loads page** (per-engine form, existing radio selector) — a new
sub-section *"Propeller aerodynamics (power effects on the wing)"* with the five
fields of §3.1, unit-aware via the existing `dflt()/k()` helpers, hidden with a
one-line caption when the engine's `prop_cg.y = 0` (not wing-mounted) or the
type is not a propeller. `prop_blades` moves from "captured, unused" to used.

**Aerodynamic Data page** — after the fuselage-moment form, a new form
*"Power effects (wing-mounted propellers)"*:
- `enabled` checkbox, caption stating the oracle-lock consequence ("off: every
  case is power-off, exactly the FAR23 replication").
- method per field: **estimate (DATCOM §4.6)** / **user** — a `st.data_editor`
  in the Aero-Data pattern (`aero_coefficients.py:128`), one row per power state
  the policy uses (`MC`, `TO`) × configuration (`clean`, `flaps`), columns
  `T_c` (informational, from the case), `ΔCL0`, `ΔCLα`, `ΔCm0`, `ΔCmα`,
  `q_h/q`, `Δε` (or `Δ(dε/dα)`), each blank = *estimate*. **User data varies
  with `T_c`**, so the table optionally takes several `T_c` rows per state and
  the case interpolates linearly in `T_c` (stated; extrapolation flagged).
- a read-only side table showing the **estimator's** values for the shipped
  cases' `T_c` so the user sees what an override replaces, and a source stamp
  (`estimate: DATCOM 4.6.1–4.6.3 (Digital DATCOM ex3 oracle)` / `user: <label
  the user typed>`) that reaches the methods section.

**Balanced Cases page** — the case table gains a **`power`** column
(`OFF/MC/TO`, `361A1`…); the "not assembled" expander also lists power variants
that could not be built (no wing-mounted propeller, missing prop data, `T_c`
outside the user table) with the reason; a new expander *"Power effects
review"* (option C's read-only picture) and the **policy table** rendered from
`power_policy.py` with its basis column, exactly as the safety-factor table is
surfaced.

**Wing Loads page** — the case selector includes the `-P` variants; one overlay
plot power-off vs power-on distributions for the selected family (shear /
bending / torsion), the immersed band shaded, so the engineer can see *where*
the increment sits.

**Report / export** — the methods-and-limitations stamp gains the estimator/
override provenance line and the §1.5 exclusions; the report's case table
carries the power column; the sbeam deck's case names carry the `-P` suffix
(§4). The `safety_factors.csv` pattern is reused for a `power_policy.csv`.

### 3.4 Validation / guardrails (GUI-facing)

- `enabled` with no wing-mounted propeller engine → the slice validates with a
  warning and no `-P` case is minted (nothing to add), stated in the skipped list.
- Wing-mounted propeller engines present, `enabled=False` → an *advisory* on the
  Balanced Cases page ("wing-mounted engines: power effects are off; the FAR23
  core is power-off by design — enable for the concept deliverable"), never an
  error, so the FAR23 fixtures stay clean.
- Missing `β_0.75` and `K_N` → estimator uses the `K_N` default and says so in
  the review table; missing `prop_cg.x`/`z` → the variant is skipped with a
  reason (the `N_p` arm and thrust arm cannot be invented).
- Units: all new fields go through `units.py` channels (deg, dimensionless) —
  no new unit kinds.

---

## 4. How the balanced power-on cases are generated

### 4.1 The machinery today (what a power-on case must fit into)

- **Trim is owned by `flight_envelope._balance`** (`flight_envelope.py:125ff`):
  for each V-n point it iterates α at the point's `n, V` until lift = `nW` and
  pitch = 0, using the config's `CL(α)`, `CD(CL)`, `Cm(α)`, the Perkins downwash
  and the tail arm `xtc/xtf`, and writes `VnPoint.lt` (trim tail load) and
  `m_wf` (airplane-less-tail moment). SELECT picks the critical points; balance
  never re-trims.
- **`balance.assemble`** (`balance.py:1245`) builds the applied set: R-side wing
  air strips (`wing_sets`, AIRLOADS' Schrenk distribution scaled to the case) +
  their mirror; a lumped `tail-air` at `xtc` = `vn.lt`; body inertia at the case
  `n_z`; the `fuselage-cm` free moment (`m_wf` − wing-about-ac); the body drag
  carrier; optional aileron couple / fin / h-tail sets. `resultant6` about the
  CG → `_closure` solves `(n_x, n_y, n_z, ṗ, q̇, ṙ)`. **Handedness is measured**
  (`is_handed`) on the applied set and the port twin is minted by *reflection*
  (`handed_twin`, `reflect_load`). The 1 % pre-closure residual gate (`Fz` on
  `nW`, `My` on `nW·MAC`) is the acceptance test that trim and assembly agree.
- Wing-mounted engines are in the case as **mass only** (CONM2 / concentrated
  wing masses split to the adjacent beam nodes, plan 14). There is no nacelle node.

### 4.2 Options for generating a power-on case

| | Option | What it does | Verdict |
|---|---|---|---|
| **A** | **Re-trim at V-n level, then assemble with the power load set** — a `retrim_with_power(vn, power_set)` in `flight_envelope` returns a power-on `VnPoint'` (`lt'`, `α'`, `CL_w'`, `m_wf'`) for the *same* `n, V, CG, weight`; `assemble(..., power=...)` adds the nacelle point loads and immersed-strip increments and reads `lt'` | the case is **in trim** — the 1 % gate still applies and proves the trim and the assembly share one decomposition; trim stays with its single owner; the V-n *diagram* stays power-off (load factors are unchanged) | **[DECISION P-8, 2026-08-15 — agreed]** |
| B | Add the power loads to the existing power-off case and let the closure absorb the residual (`Δn`, `q̇`) | trivial; but the case is *not balanced* — the untrimmed thrust/`N_p` moment appears as a pitching acceleration; the 1 % gate would have to be exempted for every `-P` case | rejected — a diagnostic overlay at most (the Wing Loads page's power-on/off comparison can be built from A, not from B) |
| C | Re-trim inside `assemble` (solve wing scale + `lt` from `Fz`/`My`) | self-contained; but it is a second trim owner (α, `Cm(α)`, `N_p(α)` all iterate) and drifts from `_balance` | rejected — practice 3 (single owner) |

### 4.3 The pipeline (option A), stage by stage

1. **`power_effects.py` (new pure-calc owner).** For one engine at one case
   (`V`, altitude, `q`, α, `power_state`): the **`PowerLoadSet`** — thrust vector
   along the P-6 thrust line, `N_p` vector (pitch and toe/β inflow), torque
   `Q` (from `engine.py`, unchanged), gyro couples when the case defines rates,
   the slipstream band `[BL_in, BL_out]`, `q_s/q`, realisation factor `k_q`,
   `ε_p`, and the **lumped increments** `ΔCL0, ΔCLα, ΔCm0, ΔCmα, q_h/q, Δε` —
   from the DATCOM estimator or the user table (C overrides field by field,
   linear in `T_c`). One helper `slipstream(...)` generalized from
   `flap._slipstream_velocity` is the band/`q_s` owner for flap, wing and tail.
2. **`power_policy.py`.** The §2 table: family → `(power_state, rating,
   kind, basis)`; `cases_for(condition)` yields the variants to mint;
   unclassifiable → flagged. Kind I rows point at the `engine.py` case IDs.
3. **Re-trim** (`flight_envelope.retrim_with_power`). Same iteration as
   `_balance`, with: `CL_total(α) = CL_w(α)·[1 + (q_s/q−1)k_q S_i/S] + ΔCL_Np(α)
   + T_c sin α_T`; `Cm_cg(α) = Cm_wf(α) + ΔCm_slip(α) − T·z_T/(qSc̄) +
   ΔCm_Np(α) − (q_h/q)·V_H·a_t·(α − ε − Δε + i_t)…` — i.e. the increments of
   §1.3 in the *same* place `_balance` already balances the tail. Output:
   `VnPoint'` tagged `power_state`, with `lt'`, `α'`, and the wing-only CL used
   to scale AIRLOADS' distribution. **Guard:** `power_state=OFF` returns the
   input `VnPoint` unchanged (identity, tested bit-for-bit).
   - Kind I `361A1`: the parent is condition A at `n = 0.75·n_A` (the same
     reading `engine.py` uses — "75 % limit maneuver vertical load factor");
     `361A2` at `n_A`; `371-k` at `n = 2.5`, **VA** (P-7).
4. **Assemble** (`assemble(..., power=PowerCaseLoads)`), additions to the
   applied set, each with its own `source` label so the report and the closure
   can see them:
   - **hub point loads per engine** at `prop_cg` (`x_p, ±y_p, z_p`):
     `prop-thrust` (`Fx, Fy, Fz`), `prop-normal` (`Fz` from α, `Fy` from τ/β),
     `engine-torque` (`Mx = ±Q`, sign by rotation hand), `engine-gyro`
     (`My/Mz`, Kind I 371 only). **Applied per engine from the `engines` list,
     never by mirroring** — torque and gyro are rotation-fixed, not
     mirror-symmetric (see 4.4).
   - **immersed-strip increments** `wing-air-power`: on strips inside each
     engine's band, `Δfz = (q_s/q−1)·k_q·fz_strip − a_0·ε_p·(q c Δy)`, `Δmy`
     from the same `Δq` on the strip's `c_m` — built per engine on that
     engine's side (a symmetric pair gives a symmetric set; an odd
     installation is still right).
   - **`tail-air`** uses `lt'`; the **`fuselage-cm`** free moment is computed
     exactly as today from `m_wf'` minus the wing-about-ac of the wing strips
     **including** the `wing-air-power` strips — so no power moment is carried
     twice: hub loads carry the thrust/`N_p` moments as point loads, strips carry
     the slipstream lift and `Δm`, `lt'` carries the tail's `q_h/q` and `Δε`.
     The re-trim uses the *same* split; the 1 % gate is what proves it.
   - **engine-torque reaction [DECISION P-9, 2026-08-15 — agreed]:** in steady trimmed flight the
     airframe reaction to the pair's torque is aileron trim, so a
     `aileron-trim` free couple `+ΣQ` is applied at the wing ac (the ACRL
     couple pattern, same `AILERON_COUPLE_NOTE` caveat); a counter-rotating pair
     sums to zero. Alternative (closure absorbs `ṗ`) is rejected: it turns a
     steady case into a rolling-acceleration case *and* would mint a spurious
     port twin (4.4). Kind I `361Ax` use the same reaction, stated in the case
     note (the rule's torque is applied to the mount and supporting structure;
     the airframe reaction is not the rule's business, but a free-free model
     needs one).
   - **gyro couples** (Kind I 371) are external couples reacted by the closure's
     `q̇`/`ṙ` — a rate case is not in pitch/yaw trim by definition; the `My`/`Mz`
     residual gate is exempted for those four cases exactly as it is for
     `UNSYMMETRICAL`, and the note says so.
   - **`n_x`:** with thrust in the set the x-closure becomes
     `n_x = (ΣT_x − D)/W` — the missing carrier `balance.py:1158` names. A
     constructed check with `ΣT_x = D` must give `n_x = 0` (gate).
5. **Handedness and twins** — see 4.4.
6. **Export.** Cases append **after** the existing sequence (the ground-family
   precedent, `balance.py:1559`), so every shipped deck's subcase numbers are
   untouched; `-P` and Kind I IDs from §2.4. Hub loads have no node: they are
   **transferred to the nearest LRA beam node with the rigid-offset moment**
   (`F` + `r × F`), the same rule CONM2 offsets follow — stated in the deck
   header; a nacelle stick/RBE2 is a future stiffness-step seam (plan L-1).
   `wing-air-power` strips ride the existing strip → node mapping. CONM2 mass
   export is unchanged (mass is power-independent).

### 4.4 Handedness with engine loads — a required change to reflection

`is_handed` measures net lateral content; `handed_twin` **reflects every load**.
Two consequences the design must handle:

- A **symmetric power variant** (`PHAA-P` …) has, per engine, `Fy = ∓T sin τ`
  (mirror-symmetric, nets to zero) and `Mx = ±Q` (rotation-fixed: a same-rotation
  pair does **not** net to zero). Without P-9 the case would be *handed* and a
  port twin minted with the torque reversed — which is a counter-rotating
  airplane, not the port case. With the aileron-trim couple the applied set nets
  to zero lateral content and the case is unhanded — correct.
- The genuinely handed families (`ACRL-P`, `TORS-P` if handed) must reflect the
  aileron/roll content **but not the engine torque/gyro**: `reflect_load` gains
  a rotation-fixed exclusion for `engine-torque` / `engine-gyro` sources (a
  guard test: the port twin's engine torque equals the starboard case's, and
  its aileron couple is reversed).

### 4.5 Gates for §4 (all in CI, written with the code)

| # | Gate | Kind |
|---|---|---|
| G4-1 | `power_effects.enabled=False` (default) → every fixture digest identical (`tests/fixtures_imperial/digests.json`) | oracle-lock |
| G4-2 | `retrim_with_power(vn, OFF)` is the identity | oracle-lock |
| G4-3 | every `-P` and `361Ax` case passes the 1 % pre-closure residual gate | closure |
| G4-4 | `Σ wing-air-power Δfz` per engine = the lumped slipstream `ΔL` the re-trim used; `Σ moments of hub loads about the CG` = the trim's thrust + `N_p` moment | consistency |
| G4-5 | constructed case `ΣT_x = D` → `n_x = 0` | closure |
| G4-6 | same-rotation pair with P-9 → unhanded, `Σ applied Mx = 0`; counter-rotating pair → zero trim couple | invariant |
| G4-7 | `ACRL-P` port twin: engine torque unchanged, aileron couple reversed | invariant |
| G4-8 | deck subcase sequence of every shipped fixture unchanged with power off; new cases append | drift-guard |
| G4-9 | DATCOM ex3 case 4 − case 3 increments reproduced ±0.1 % by the estimator (§1) | oracle |

### 4.6 Should the V-n diagram and the design speeds also be power-on / power-off?

**Question raised 2026-08-15.** Where power *could* enter the envelope:

| Envelope element | Definition (pre-Amdt-64) | Power-dependent? |
|---|---|---|
| Limit load factors `n` | 23.337 — fixed by category / weight | no |
| `VS` (hence the stall boundary and `VA = VS√n`) | 23.49 — stalling speed determined with **engines idling / throttles closed** *[VERIFY wording in the CFR pull]* | **no by rule** — `VS` and therefore `VA` are power-off quantities |
| `VC` | 23.335(a) — from `W/S`; "need not be more than 0.9 VH" where `VH` is the max level-flight speed at max continuous power | only through the `VH` cap (a performance number the user enters, not something this step computes) |
| `VD` | 23.335(b) — `≥ 1.25 VC` / margin / dive demonstration | no |
| Gust load factor | 23.341 — `Kg`, `Ude`, `a` = "slope of the airplane normal force coefficient curve" — conventionally the power-off wing-body slope | the formula is written to a slope the user supplies; power-on `CLα` (§1) is higher, so a power-on slope would raise `n_gust` |
| Positive stall boundary at low speed | `CN_max` power-off | slipstream raises the achievable `CL_max` — the boundary would move left — but the estimator has **no** method for power-on `CL_max` (excluded in §1.5) |

**Options.**
- (a) **Envelope stays power-off; power is applied to the load *cases* at the
  same `(n, V)` points.** The airplane must sustain `n` at `V` at any throttle
  setting; power changes the *distribution* of that load, not the envelope. All
  design speeds are unchanged; the V-n plot is unchanged.
- (b) A full power-on V-n (power-on stall line, power-on gust `n`) and power-on
  design speeds. Would need power-on `CL_max` (user data only), a rule reading
  that `VA` may use it (23.49 says otherwise), and would create a second
  envelope the oracle-locked FLTLOADS/STRSPEED cannot reduce to.
- (c) (a) plus an **informational overlay** on the V-n page: the power-on
  positive stall boundary drawn from a *user-supplied* `CL_max,pow` (option C
  data only), and the power-on gust `n` from the estimator's `CLα_pow`,
  both dashed and never selected as design points.

**[DECISION P-10, 2026-08-15 — agreed]: (a), with (c) as an optional later overlay.**
`VS`, `VA`, `VC`, `VD`, the load factors and the gust formula stay exactly the
FAR23 replication; the design points SELECT picks are the same points; only
the load set on those points gains the power increment. This is what keeps
`retrim_with_power(vn, ·)` a *re-trim at fixed `(n, V)`* rather than a second
envelope, and it is what 23.345(d)/23.457(b) imply for the one flap-config
case (`SLIP-P` is at the envelope's own `BAL 1.4VSF` point). The `VH` cap on
`VC` and the 23.341 slope choice are the two places the user's own inputs
already carry power implicitly; both are stated in the report's methods
section, neither is changed by this step.

---

## 5. Verification that today's wing cases are zero-thrust

### 5.1 Evidence (measured 2026-08-15, scratch run — no shipped test pins it yet)

- **No thrust source exists in any balanced case.** The union of `source` labels
  over every `ga6_normal` balanced case is `aileron-roll, body-axial,
  body-inertia, closure-*, fuselage-cm, gear-*, ground-lift, htail-air,
  tail-air, vtail-air, wing-air, wing-inertia` — nothing from the powerplant.
- **The x-closure is the drag alone.** `n_x` of the GA-6 flight cases: PHAA
  `−0.610 g`, PMAA `−0.066`, NMAA `−0.132`, ACRL `−0.392`, TORS `+0.127`, PLAA
  `+0.200`, v-tail families `+0.08…+0.18` — a non-zero longitudinal
  acceleration in every case, i.e. the airplane is decelerating (or, at low α /
  high speed, being pushed by the lift vector's forward tilt) under its own
  drag with **no thrust to balance it**. A trimmed powered airplane would close
  at `n_x ≈ 0`. This is exactly `balance.py:1158`'s statement made numerical.
- **Trim is thrust-free.** `flight_envelope._balance` has no thrust or `N_p`
  term; `VnPoint.lt` is the power-off balancing load.
- **The two places power *is* computed do not reach the wing:** the flap
  slipstream factor is applied to the flap panel result only; the mount
  module's `fx_thrust`/torque/gyro stop at the mount (`report/render.py`
  gyro table). Verified by grep in §1.1.

**Conclusion:** the wing cases are not "essentially" zero-thrust — they are
*exactly* zero-thrust, and this is the FAR23 replication's intent (23.345(d)
permits it for the flap cases; the clean cases inherit the suite's convention).

### 5.2 The one place a power effect could hide: the user's aero data

`AeroCoeffSet` (`CL(α)`, `CD(CL)`, `Cm(α)`, `CL_max`) is user-supplied and the
suite has no way to know whether it was measured power-on. If a user enters
power-on wind-tunnel curves *and* enables this step, the increments would be
carried twice. **[DECISION P-12, 2026-08-15 — agreed]:** `AeroCoeffSet.power_state` provenance field
(`"off"` default, caption on the Aerodynamic Data page: "enter **power-off**
data; power effects are added by the Power effects step") and a validation
**warning** when `power_effects.enabled` and any coefficient set is flagged
`"on"`. Not an error — the user may know better — but stated in the methods stamp.

### 5.3 Make it structural (gates written with this step, all cheap)

| # | Gate | What it pins |
|---|---|---|
| G5-1 | with `power_effects.enabled=False`, the set of `source` labels of every fixture's balanced cases is a **whitelist** that contains no `prop-*`, `engine-*`, `wing-air-power`, `aileron-trim` label | no power load leaks into a power-off case |
| G5-2 | for every power-off flight case, `delta_nx·W == −(Σ_x applied air loads)` — the x-closure is the drag carrier alone (identity, not tolerance) | "no thrust carrier" as an invariant rather than a docstring sentence |
| G5-3 | `retrim_with_power(vn, OFF) is vn` (identity) and `flap` results are unchanged when the power slice is toggled | the flap slipstream and the trim are untouched by the switch |
| G5-4 | fixture digests (`tests/fixtures_imperial/digests.json`) unchanged with the slice absent/disabled | oracle-lock, already the standing mechanism |

### 5.4 Prerequisite finding — the demonstration fixtures cannot demonstrate yet

**`atr42_100` and `dhc8_dash8` assemble zero flight balanced cases today**: all
six wing conditions (`PHAA, PLAA, PMAA, NMAA, ACRL, TORS`) and every tail
condition skip with `loading-not-derivable` — their SELECT CG cases do not
resolve to a derivable weight-database loading (step C1's rule: no invented
inertia set). Only the GA-6 (nose-mounted single, out of scope) and the
regional jet have balanced decks. **Checked 2026-08-15 against HEAD
(`4acbb48`):** decision **D-25 is closed** — the schema shipped (`CgCase.loading`,
v50, note [`22_d25_cgcase_loading_note.md`](../40_history/25_d25_cgcase_loading_note.md)) —
but it delivered the *mechanism*, not the twins' data: `atr42_100` (1/3
derivable) and `dhc8_dash8` (0/3) still assemble no flight case on HEAD. What
clears the way is the consumer item **backlog Pri 5 — "Payload cases the weight
database can produce"**: enter a `CgCase.loading` for each twin case (the RJ
`CG3 fwd light` is the worked example — an engineering statement of the ballast/
discretionary items instead of the solved-ballast gate), Tier M–L, effort M, no
schema left in it; pinned by `test_mass_cards.py::
test_which_loadings_are_entered_is_pinned` and `test_balance.py::
test_which_conditions_assemble_is_pinned`. So the demonstration fixtures have a
**hard prerequisite: Pri 5 for `atr42_100` and `dhc8_dash8`** before any
power-on case can be minted on them. The power step's fixture gate depends on
it; this note does not fold that work in (practice 5) but sequences after it
(§8, to follow).

---

## 6. Empennage — does power (and the changed wing aerodynamics) need power-on tail cases?

### 6.1 How the tail loads are computed today

- **Balancing** (23.421): `select.htail_balance` (`select.py:278`) resolves the
  V-n point's trim load into `LT25` (tail α: `AT = α + i_t − E`,
  `E = 114.6·CL/(π·AR_w)` Perkins, `Q = V²/295` **free-stream**) and `LT50`
  (elevator, from the moment balance) — the pre-Amdt-64 Ch 9 method.
- **Maneuver** (23.423) unchecked/checked and **gust** (23.425) add rational
  increments on the `BAL A/C/D` (and `BAL VF` flap-extended) points; the gust
  increment uses `Kg`, `Ude`, `a_ht` and the downwash relief `1 − 36·a_w/AR_w`
  (`select.py:491`).
- **Unsymmetrical** (23.427): (b)'s "absence of more rational data" split
  (`100 % / (100 − 10(n−1)) %`) on the worst symmetric case; the balanced deck
  distributes it (`BALANCED_HTAIL_CONDITIONS`).
- **Vertical tail** (23.441/23.443, `_vtail`, `BALANCED_VTAIL_CONDITIONS`):
  fin lift slope, rudder effectiveness, sideslip — no propeller term; engine-out
  is ONENGOUT (out of scope here).
- In every balanced **wing** case the tail is the lumped `tail-air = vn.lt`.

### 6.2 Where power reaches the tail (three routes)

| Route | Physics | Where it enters | On the T-tail fixtures |
|---|---|---|---|
| **R1 — re-trim** | thrust-line moment, `N_p` and its arm, wing `ΔCm0`/`ΔCmα` (§1.3) move the balancing load `lt → lt'` | `retrim_with_power` (§4, single trim owner); every `-P` wing case already carries `lt'` as `tail-air` | **yes** — independent of tail height |
| **R2 — downwash** | the wing's altered lift distribution (extra inboard lift) and the slipstream's own deflection raise `ε` and change `dε/dα` (DATCOM 4.6.1 `Δε`, `Δ(dε/dα)`) | tail α in `htail_balance` (`E + Δε`), the gust relief `(1 − dε/dα)` and the maneuver increments | **yes**, reduced with tail height (DATCOM's `Δε` decays with the tail's height above the slipstream centre-line) |
| **R3 — tail in the slipstream** | `q_h/q > 1` on the immersed tail area (DATCOM's `Z_s = z_p + x̄_p tan α_p` vs tail height, immersed span from the contracted radius) | multiplies every tail load term (`Q → Q·q_h/q`) | **no** — ATR-42 and Dash-8 are T-tails: `q_h/q = 1` exactly by the immersion geometry (a low tail behind a wing-mounted pair may be partly immersed) |

So the answer to "does the changed wing aerodynamics change the tail loads?" is
**yes, through R1 and R2, even when R3 is zero** — and R1/R2 are already inside
the re-trim decided in §4; the question is only whether they are *reported as
h-tail design cases* or left inside the balanced wing cases.

**Regulatory hook (pre-Amdt-64):** 23.421–23.425 name no power; 23.331(c)'s
"mutual influence of the aerodynamic surfaces" is the hook for R2;
23.427(a) names "slipstream effects" explicitly for the unsymmetrical case, and
(b)'s formula is the permitted route in the absence of rational data. Same
framing as the wing: the mount → structure path is compliance, the airloads are
rational analysis the concept mission wants.

### 6.3 Options

| | Option | Gives | Cost / risk | Verdict |
|---|---|---|---|---|
| (i) | **Balanced-model only** — the tail sees power solely as `lt'` inside the `-P` wing cases; the h-tail SELECT families (`BAL/MAN/GUST …`) and the tail-span decks stay power-off | nothing new on the tail side | the h-tail **design** loads (23.423 maneuver = balancing + increment, 23.425 gust) are never evaluated power-on, so a low-tail airplane could have an unreported governing case; and the wing `-P` deck's `tail-air` would disagree with the h-tail report for the "same" condition | not enough |
| **(ii)** | **h-tail families gain `-P` variants under the same policy table** — `BAL A/C/D`, `UNCHECKED/CHECKED MAN`, `GUST` at MC; the flap-extended `BAL/GUST … EXTENDED` at **TO** (P-2, and this is where the "flaps-down → take-off power" rule bites first, because these cases *exist* today unlike the flap-extended wing cases); each computed by the tail module from the re-trimmed point with the `PowerLoadSet`'s `q_h/q`, `Δε`, `Δ(dε/dα)`; `UNSYMMETRICAL` rides on the `-P` base when the policy row says so; **v-tail: no power variants** | consistent design loads; the tail-span decks and the balanced h-tail family inherit the variants from the case list with no extra machinery | + ~10 h-tail cases; the flap `BAL 1.4VSF` point gains a tail row alongside `SLIP-P` | **[DECISION P-11 — agreed]** |
| (iii) | (ii) + v-tail power terms — propeller side force at sideslip (`CNβ_p`, destabilizing, ahead of the CG) and slipstream on the fin | complete | for wing-mounted twins the fin is outside the slipstream and `CNβ_p` is a *lateral derivative* — L-7's territory (`Cy_β`/`Cn_β`), where it belongs as one more term | **defer to L-7** as a stated seam (§9); the sideslip cases' fin load is what L-7 owns |

**[DECISION P-11, 2026-08-15 — agreed]: (ii).** One policy table drives wing and h-tail
rows alike; the h-tail `-P` balancing load *is* the balanced deck's `lt'` for
the same condition (single trim owner, gate G6-2), so the wing deck and the tail
report cannot disagree. Wing lift slope `a_w` in the gust relief stays the
power-off wing slope; the power effect on the gradient enters as `Δ(dε/dα)`
(DATCOM), stated in the methods section.

### 6.4 Gates for §6

| # | Gate | Kind |
|---|---|---|
| G6-1 | ATR-42 / Dash-8: `q_h/q == 1.0` exactly (T-tail above the slipstream by the immersion geometry) — pinned, so a geometry edit that drops the tail into the slipstream is a visible change | invariant |
| G6-2 | for every `-P` condition, the h-tail `BAL…-P` balancing load equals the balanced wing case's `tail-air` (`lt'`) — identity | consistency / single owner |
| G6-3 | `power_state=OFF`: every h-tail/v-tail family bit-identical to today (fixture digests) | oracle-lock |
| G6-4 | DATCOM ex3 case 4 vs 3: `q_h/q∞`, `ε`, `dε/dα` per α reproduced ±0.1 % by the estimator (the tail terms of the printed oracle) | oracle |
| G6-5 | `GUST…-P` uses `(1 − dε/dα)_pow` and `q_h/q` in the increment; `GUST…` (OFF) unchanged — formula test | drift-guard |
| G6-6 | `UNSYMMETRICAL-P` split reproduces 23.427(b)'s ratios on the `-P` base load | drift-guard |

---

## 7. Decisions register

| ID | Decision (all 2026-08-15) | Where |
|---|---|---|
| P-0 | Propeller normal force `N_p` is included with thrust, torque and gyro | §1.6 |
| P-1 | Estimator = DATCOM §4.6.1–4.6.3 port (Digital DATCOM ex3 case 4 oracle); user data (C) overrides field by field; momentum-theory band (A) is the single distribution rule | §1.4 |
| P-2 | Rating: flaps-down/gear-down → take-off power; flaps-up/gear-up → max-continuous; `T = η·P/V_TAS`, `η` per engine default 0.85 | §1.6, §2.3 |
| P-3 | Rule basis: pre-Amendment-64 FAR 23 (23.331/23.421 era); CFR pull of that text is a precondition | §1.2 |
| P-4 | Kind II extent (i): `-P` variant for every clean wing family + `SLIP-P` on `BAL 1.4VSF` (TO); 23.345 flap-extended power cases deferred | §2.2 |
| P-5 | GUI placement C: inputs on their owner pages + read-only power review on Balanced Cases | §3.2 |
| P-6 | Thrust line is user-defined: hub point + pitch incidence + toe angle (GUI also accepts a second point, converted) | §3.1 |
| P-6a *(added 2026-08-15, note 24 R-9)* | In the LRA beam model (step 12) each engine has a **hub node** at `prop_cg` (the thrust point — the thrust `FORCE` along the P-6 line goes there) and a **mount node** at `engine_cg` (ENGLOADS torque/gyro `MOMENT`s, the engine `CONM2`s), hub → mount rigid, mount rigid to the wing LRA node at the engine butt line or to the fuselage node at `engine_cg.x` per an explicit `mounted_on` (BM-4). **Half discharged 2026-08-17 (#10):** the hub node carries the entered `thrust_lb` as an **axial** `FORCE` — not along the P-6 line, which stays parked with the rest of this note — and the mount node is still emitted with no applied card, so the torque/gyro `MOMENT`s wait for this step | [`24_lra_beam_model_review_note.md`](24_lra_beam_model_review_note.md) R-9 |
| P-7 | 23.371 gyro wing-box cases at VA (mount numbers stay VSF-based, stated side by side) | §2.2 |
| P-8 | Generation = re-trim at V-n level (`retrim_with_power`) then assemble with the power load set; the 1 % gate applies | §4.2 |
| P-9 | Pair torque reacted by an `aileron-trim` free couple (counter-rotating → 0); gyro couples reacted by closure `q̇/ṙ` with the residual gate exempted | §4.3 |
| P-10 | V-n diagram and design speeds stay power-off; power applies to the load cases at the same `(n, V)`; optional informational overlay later | §4.6 |
| P-11 | h-tail families gain `-P` variants under the same policy table (flap-extended at TO); v-tail power terms deferred to L-7 | §6.3 |
| P-12 | `AeroCoeffSet.power_state` provenance flag (`"off"` default) with a double-count warning | §5.2 |

Also agreed in scope: wing-mounted propellers only; engine-out stays a
v-tail/ONENGOUT case; fixtures ATR-42 and Dash-8.

## 8. Sequencing — the skeleton of the implementation plan

Tier **L** (new physics, case-identity contract, schema). Every step ships with
its gates from §4.5 / §5.3 / §6.4 and its own closure per `CLAUDE.md`.

| Step | Content | Depends on | Gates |
|---|---|---|---|
| **0 (prereq, separate backlog item)** | **Pri 5** for `atr42_100` and `dhc8_dash8`: enter `CgCase.loading` so the twins assemble flight balanced cases at all | D-25 ✅ | existing pins go red → green |
| **0b (prereq)** | CFR pull: pre-Amdt-64 23.331/.333/.361/.371/.421/.423/.425/.457 (+ 23.49 for the VS/VA statement, 25.331(a)) → `reference/14CFR_23_power_effects.md`; resolve the [VERIFY] tags | — | doc only |
| **1** | `power_effects.py` estimator: `slipstream()` helper generalized from `flap._slipstream_velocity` (flap numbers unchanged), DATCOM §4.6 port (`CNα_p`, `K_N`, `f`, upwash at disc, `Δε`, `q_h/q`, `k_q`), `PowerLoadSet`; user-override table with `T_c` interpolation; `Engine` prop-aero fields + thrust line (P-6) — **schema bump** | 0b | G4-9 / G6-4 (DATCOM ex3 ±0.1 %), flap App-A p201 unchanged, `OFF` identity |
| **2** | `power_policy.py` (§2 table with basis) + `power_state` case attribute / `-P` IDs (note 17 linkage) + `AeroCoeffSet.power_state` (P-12) — schema | 1 | G5-1, G5-4, unclassifiable → flagged |
| **3** | `flight_envelope.retrim_with_power` (P-8) | 1, 2 | G4-2, G5-3 |
| **4** | `balance.assemble(..., power=)`: hub loads per engine, `wing-air-power` strips, `aileron-trim` couple (P-9), gyro reaction, `n_x` carrier; `reflect_load` rotation-fixed exclusion; Kind I `361A1/361A2/371-k` (P-7); export append + rigid-offset transfer | 3 | G4-1, G4-3…G4-8, G5-2 |
| **5** | h-tail `-P` families (P-11) in `select` + tail-span inheritance | 3 | G6-1…G6-6 |
| **6** | GUI (P-5): Engine Mount prop-aero + thrust line; Aerodynamic Data power form + override table + provenance; Balanced Cases power column / review / policy table; Wing Loads overlay; report methods stamp, `power_policy.csv`, deck names | 4, 5 | UI smoke; `workflow.py` drift-guard unchanged |
| **7** | Demonstration on the twins: `PHAA-P`, `SLIP-P`, `361A2`, `371-k` decks solved in sbeam in CI; report section | 0, 4–6 | equilibrium invariant (plan 07) on every `-P` case |

Closure per step: CHANGELOG + backlog removal + history full-step format;
`PROGRAM_SPEC.md` (SELECT / balance / engine / flap / tail sections);
`CONVENTIONS.md` (case identity `power_state`; thrust-line sign convention);
`theory_sources.md` (DATCOM §4.6 citations, ex3 oracle);
`DATA_DICTIONARY.md` regenerated; `cspell.json` terms.

## 9. Seams (stated, not silent)

- **Nose-mounted singles / pylon turbofans**: thrust-line-only treatment (no
  wing slipstream) — reuse `PowerLoadSet` with `k_q = 0`, no `N_p` for a
  turbofan; a later note.
- **23.345 flap-extended airplane cases** with power (`MAN 2G VF-P`, gusts):
  after flap-extended *wing* balanced cases exist at all; TO rating.
- **V-tail power terms** (`CNβ_p`, fin in slipstream): the L-7 (`Cy_β`/`Cn_β`)
  note; engine-out stays ONENGOUT.
- **Slipstream swirl asymmetry**, power effect on `CL_max`, nacelle aero
  (body-drag carrier, note 20), compressibility on `CNα_p`: excluded (§1.5).
- **Nacelle stick / RBE2** for the hub loads: with the stiffness step (L-1);
  until then rigid-offset transfer to the LRA node.
- **Power-on V-n overlay** (P-10 (c)): optional, user `CL_max,pow` only.
- **`VH` cap on `VC` and the 23.341 slope**: user inputs that carry power
  implicitly; stated in methods, unchanged.
