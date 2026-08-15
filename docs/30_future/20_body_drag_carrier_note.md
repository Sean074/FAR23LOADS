# Design note — a carrier for non-wing drag in the assembled model

**Status: PROPOSED — not agreed, no code.** Written to `CLAUDE.md` required
practice 1 (design note before code for physics/L steps): theory reference,
`CONVENTIONS.md` citations, closure targets with expected numbers, acceptance
tolerances — agreed in chat before implementation.

**Backlog:** Pri 5, "Non-wing drag has no carrier in the assembled model"
(`00_backlog.md`), re-titled and re-diagnosed 2026-08-15 by the element-count
study that item asked for. This note is the design half of that item.

**Tier:** L on the `CLAUDE.md` table — it adds a load to the assembled model and
proposes a new stated input, so it needs affected standard docs, a
`theory_sources.md` citation and full step format at closure. Effort: M.

**Definition of done.** A `body-axial` load in every assembled flight case, with
its application height a *stated* quantity rather than an implicit one; the `nx`
gap closed in full on every fixture; and the pitch residual moved to a number the
project has chosen deliberately rather than inherited. There is **no printed
oracle** for this — the manual ships no assembled-airplane method — so the gate
is a stated physics-closure gate per `CLAUDE.md` practice 2, and §7 states it
with the numbers it must hit.

---

## 1. The finding this exists to fix

`flight_envelope._balance` (the FLTLOADS trim, `flight_envelope.py:167`) balances
the airplane-less-tail drag from the **polar**:

```python
cd = drag_cd(config, cl)          # airplane-less-tail CD(CL), aero_curves.py:96
d  = cd * q * s
dx = d * math.cos(al * _RAD) - ll * math.sin(al * _RAD)     # body-axis X force
```

`balance.assemble` has nothing that carries it. The only `fx` in the assembled
set is the wing strips' own chordwise force (`airloads.py:373`, section profile
drag + lifting-line induced drag, resolved through the same `α`), so
`residual_fx` **equals** `ΣFx_wing` exactly, and the pitch residual is the couple
the missing force leaves about the CG.

Measured (`00_backlog.md` Pri 5 has the full study):

- the pitch residual is **flat in `elements`** — RJ PLAA 1.041 % from 20 to 640 —
  so no strip refinement reaches it;
- an exact three-term identity closes to the last printed digit, and the drag
  term is essentially all of it (lift ≤ 0.086 %, tail-station exactly 0);
- `residual_fx == ΣFx_wing`, so `nx` is the same defect in the `x` DOF.

## 2. What the missing force actually is

Both the trim and the strips resolve through the **same** `α`, so the body-axis
gap decomposes exactly into wind-axis parts:

```
ΔF_x = ΔD·cos α − ΔL·sin α          ⇒   ΔD = ΔF_x·cos α + ΔF_z·sin α
ΔF_z = ΔL·cos α + ΔD·sin α              ΔL = ΔF_z·cos α − ΔF_x·sin α
```

Measured, `ΔL/L` is **≤ 0.6 % everywhere and ≤ 0.16 % on every low-CL case** —
the two lift models agree — so the gap is a *drag*-model gap almost in full. As a
drag-coefficient increment `ΔC_D = ΔD/(q·S)`:

| case | ga6 `α` | ga6 `ΔC_D` | RJ `α` | RJ `ΔC_D` |
|---|---|---|---|---|
| PHAA | 14.75° | −0.0207 | 22.81° | **+0.0558** |
| ACRL | 12.00° | −0.0195 | 19.50° | **+0.0139** |
| PMAA | 5.29° | −0.0186 | 3.27° | −0.0353 |
| TORS | 1.80° | −0.0170 | 0.32° | −0.0237 |
| PLAA | 1.79° | −0.0173 | 1.39° | −0.0255 |
| SIDE GUST | −1.41° | −0.0164 | −1.06° | −0.0190 |
| NMAA | −8.39° | −0.0182 | — | — |

On `ga6_normal` this is **a near-constant −0.018 across every case, at every `α`
and every CL** — which is exactly the signature of a missing **parasite drag**
term: a `C_D` offset independent of `C_L`. The polar carries the whole airplane
less tail; the strips carry the wing. The difference is the fuselage, nacelles
and everything else, and it is real load the assembled model is silently
dropping. That is the physics justification for the step.

**The regional jet's two high-`α` points invert the sign** (+0.0558 at 22.8°,
+0.0139 at 19.5°): there the strip model's induced drag `c_l·α_i` overshoots the
polar's quadratic, and the "missing" force comes out **forward**. See decision
D-4.

## 3. Why the obvious fix is wrong

The correction is `F_x = dx − ΣFx_wing`, and adding a pure axial force at height
`z_b` changes the pitch residual by exactly `(z_b − z_cg)·F_x`. So

```
residual_new(z_b) = residual_old − (z_b − z_cg)·ΔF_x = (zw − z_b)·ΔF_x + (small)
```

which is **zero at `z_b = zw`** — the wing reference plane, i.e. exactly where
the trim assumed the whole airplane's drag acted — and which **improves only for**

```
z_b ∈ (2·zw − z_cg,  z_cg)
```

Placing the load at the body's own mass centroid, the natural first instinct and
the one-line fix suggested when Pri 5 was re-filed, lands **outside** that band on
the regional jet and makes the residual **worse**:

| RJ case | today | at the body mass centroid `z_b = 73.65` |
|---|---|---|
| SIDE GUST | 1.586 % | **1.881 %** |
| TORS | 1.174 % | **1.402 %** |
| PLAA | 1.041 % | **1.278 %** |

This is not a detail of placement. It says something about what the residual
*is*: the trim is a 3-DOF idealisation that lumps the entire airplane-less-tail
force system at `(xw, zw)`, and the assembled model is the real distribution. The
pitch residual measures their disagreement. **Putting the body drag where it
physically belongs makes the assembled model more correct and the residual
larger.** Any design that treats "drive the residual to zero" as the goal will
end up putting a real load somewhere false to get there.

**The trim cannot be changed to meet it.** `_balance`'s output `lt` is
oracle-locked to Appendix A p179 (`tests/test_flight_envelope.py:79`), ±0.1 %.
Giving the trim its own drag application height would move a printed oracle and
would need the full approved-deviation trail of
`docs/20_theory/02_approved_corrections.md`. Out of scope, and not proposed.

## 4. Signs and frames

`CONVENTIONS.md` §1: body axes, `x` **+aft**, `y` +right, `z` +up; all values
Imperial-internal (`units.py`), pounds and inch-pounds.

- `dx` and `ΣFx_wing` are already body-axis `x` forces in these axes, so the
  correction `F_x = dx − ΣFx_wing` needs **no rotation** — it is a subtraction of
  two quantities in the same frame. Positive is aft, i.e. drag.
- Moment about the CG from a pure axial load at `(x, z)`:
  `my += (z − z_cg)·fx`. The `x` station does **not** enter, because `fz = 0`.
  Consequence worth stating plainly: **the `x` distribution of this load is free**
  — it can be made as physical as the geometry allows without touching the pitch
  gate. Only `z` matters to the residual.
- FAR 23's longitudinal load factor `nx` is this quantity (`balance._closure`
  docstring): closing it is the same act as carrying the drag.

## 5. Where it plugs in

`balance.assemble` (`balance.py:1097`), beside the existing labelled lumped
terms and under the same rule stated at `balanced_cases.md` §2 item 5 — *a real
load with no distributed carrier is lumped and labelled, never dropped*:

```python
loads.append(BalancedLoad(x=..., y=0.0, z=z_b, fx=vn.dx - sum_fx_wing,
                          source="body-axial", side="C"))
```

Scope boundaries:

- **Flight cases only.** The ground families carry no aero (`fuselage_cm` is 0 on
  every one of them today, and the same test applies here).
- **Not `body_loads`.** That module's Ch 15 procedure is vertical-only (`fz`,
  `Sz`, `Myy`); giving the per-component fuselage beam an axial load is a
  separate question and is *not* proposed here. Stated so the seam is explicit.
- **The seam rule holds** (plan 11 §4): this is an applied external load, not a
  cut reaction, so it belongs in the assembled model by construction.

## 6. Worked numbers — residual against application height

Exact, since adding a pure `fx` at `z_b` changes `my` by exactly `(z_b − z_cg)·fx`.
`*` marks over the 1 % gate.

**`concept_regional_jet`** — `zw = 53.30`, `z_cg = 70.00`, improvement band
`(36.60, 70.00)`, `root_waterline_z = 45.0`:

| case | `F_x` corr | today | `z_b = 45.0` | `z_b = 53.3` | `z_b = 60.0` | `z_b = 70.0` |
|---|---|---|---|---|---|---|
| PHAA | −2,646 | −0.442 | 0.349 | 0.086 | −0.126 | −0.442 |
| PLAA | +5,262 | 1.041* | −0.528 | −0.007 | 0.413 | 1.041* |
| PMAA | +5,726 | 0.967 | −0.527 | −0.031 | 0.369 | 0.967 |
| ACRL | −696 | −0.148 | 0.078 | 0.003 | −0.057 | −0.148 |
| TORS | +3,849 | 1.174* | −0.550 | 0.022 | 0.484 | 1.174* |
| SIDE GUST | +3,085 | 1.586* | −0.725 | 0.042 | 0.662 | 1.586* |

**`ga6_normal`** — `zw = 87.73`, `z_cg = 93.00`, improvement band
`(82.47, 93.00)`, `root_waterline_z = 78.5`:

| case | `F_x` corr | today | `z_b = 78.5` | `z_b = 87.7` | `z_b = 85.0` | `z_b = 90.0` |
|---|---|---|---|---|---|---|
| PHAA | +175 | 0.117 | −0.168 | 0.013 | −0.040 | 0.058 |
| PLAA | +488 | 0.290 | −0.501 | 0.002 | −0.147 | 0.126 |
| PMAA | +335 | 0.197 | −0.324 | 0.008 | −0.090 | 0.089 |
| NMAA | +325 | 0.219 | −0.712 | −0.075 | −0.263 | 0.081 |
| ACRL | +166 | 0.126 | −0.188 | 0.012 | −0.047 | 0.061 |
| TORS | +307 | 0.268 | −0.478 | −0.003 | −0.144 | 0.114 |
| SIDE GUST | +296 | 0.648 | **−1.173*** | −0.014 | −0.357 | 0.271 |

Read across the two tables:

- `z_b = zw` collapses the pitch residual to the **lift and tail terms alone** —
  ≤ 0.086 % on the RJ, ≤ 0.075 % on the ga6. That is the residual floor plan 11
  R3 predicted, now reached in both DOF instead of one.
- `z_b = root_waterline_z` — the suite's *existing* "body centreline", the datum
  `tail_geometry.fin_root_waterline` measures the fuselage top from — **fixes the
  RJ and breaks the ga6**: every RJ case passes (worst 0.725 %) but ga6 SIDE GUST
  goes to −1.173 %, a new exceedance on the Appendix A fixture. It is not a safe
  default.
- The ga6's improvement band is only **10.5 in wide**, and `root_waterline_z`
  sits 4 in below it. The RJ's is 33 in wide and `root_waterline_z` sits inside.
  The difference is geometry the fixtures do not carry: `ga6_normal` has
  `fuselage_height = 0.0` — **no body geometry at all**, the same gap the L-7
  note found (`19_l7_lateral_body_aero_note.md` §10).

## 7. Gates

| # | Gate | Target |
|---|---|---|
| **G1** | `residual_fx == 0` to `1e-9` on every assembled **flight** case, every fixture | The `nx` gap closes in full, at any `z_b` — this is the unambiguous half |
| **G2** | `delta_nx` on a flight case equals the trim's own `dx/W` to `1e-9` | The closure stops standing in for drag; today ga6 PHAA reads 0.661 g against the trim's 0.610 |
| **G3** | Pitch residual with the **default** `z_b` | ≤ 0.086 % (RJ), ≤ 0.075 % (ga6) — the lift-term floor. Every per-fixture `_PITCH_RESIDUAL_CEILING` in `tests/test_balance.py` **falls**, and plan 13's G9 ceiling with it |
| **G4** | Ground cases carry **no** `body-axial` load | Same rule `fuselage_cm == 0` already holds them to |
| **G5** | Sum identity: `Σ fx(applied) == vn.dx` on every flight case | The correction is defined by this and must be asserted, not assumed |
| **G6** | `z_b` provenance is on the result | `assumed`/`entered` and its basis, exactly as `FinRoot` carries them (`tail_geometry.py:238`) |
| **G7** | Oracles bit-for-bit | `balance` is concept-mode; `_balance`/FLTLOADS is untouched, so Appendix A must not move by a digit |
| **G8** | Export equilibrium | The deck's `ΣFx` re-sums to ~0 with the new card present (`export/equilibrium.py`), and the `nx` line in the deck header states the new value |
| **G9** | Drift guard | One owner for `z_b` with a test, per `CLAUDE.md` practice 3 — the same treatment `fin_root_waterline` got for the same class of quantity |

## 8. Decisions requested

| # | Decision | Recommendation |
|---|---|---|
| **D-1** | **Where does the load act vertically?** | **A new stated input, `body_drag_waterline_z`, defaulting to `zw` and flagged `assumed`.** Defaulting to `zw` makes the step reach the R3 floor in both DOF on every existing fixture (G3), so nothing re-baselines upward and CI stays green, while a real labelled load replaces silence. Where the user states the true body centreline, the residual becomes the honest measure of the trim's own lumping and is *reported*, not hidden. This is the `fin_root_waterline` pattern exactly: single owner, resolution order, `assumed` flag, loud note. **Do not** default to `root_waterline_z` (breaks the ga6, §6) or to the body mass centroid (breaks the RJ, §3) |
| **D-2** | **How is it distributed in `x`?** | Free — `x` does not enter the pitch residual (§4). Distribute over the body stations by **frontal-area share** where a `FuselageOutline` exists, else lump at the body-inertia centroid `x`, flagged. Physical where the geometry allows, harmless where it does not |
| **D-3** | **What is it called?** | `source="body-axial"`, not `body-drag`. At the RJ's two high-`α` points the quantity is **forward** (§2), and a card labelled "drag" pointing forward is a lie in the deck. The rendered label states it as *the airplane-less-tail axial force the wing strips do not carry* |
| **D-4** | **Clamp the negative (forward) values?** | **No.** The correction is defined as whatever closes the two drag models, and clamping would (a) reopen `residual_fx`, killing G1/G5, and (b) hide a real finding — the strip model's induced drag overshoots the polar above `α ≈ 19°`. Emit a **note** on the case instead, and file the overshoot as its own observation. Clamping trades a measurable gate for a comfortable number |
| **D-5** | **Does the ga6 get body geometry first?** | **Recommend yes, as a separate step before this one** — merged with what the L-7 note §10 and Pri 10 need from the same geometry. `fuselage_height = 0.0` means the ga6 cannot state a body centreline at all, so D-1's default is doing all the work there. Sequencing it first keeps this step's digest wave attributable, the same reasoning the L-7 note applied |

## 9. Open items

1. **D-5's sequencing is a real fork**, not a formality: with D-1's recommended
   default this step ships and gates cleanly *without* ga6 body geometry, so the
   two can be done in either order — but only if the reviewer accepts that on the
   Appendix A fixture `z_b` is the wing plane by default rather than by
   measurement. Worth an explicit yes.
2. **The high-`α` induced-drag overshoot (§2, D-4) is unexplained.** `ΔC_D` should
   be a roughly constant parasite offset; on the RJ it swings +0.076 between
   `α = 3.3°` and `α = 22.8°`. Either the polar is being extrapolated past its
   fitted range at the stall-line points, or the lifting-line induced drag is
   wrong at high `α`, or both. It does not block this step — the correction is
   defined by subtraction either way — but it should be measured before anyone
   reads `body-axial` as a physical fuselage drag at those points.
3. **`xtf` vs `xtc`.** The tail-station term of the §1 identity is exactly zero
   today only because every assembled V-n point is clean-configuration:
   `_balance` uses `xtf` for a flaps-down point while `assemble` applies the tail
   load at `xtc` (a 28 in difference on the RJ, 7.7 in on the ga6). It costs
   nothing to guard now and is a latent exceedance the moment a flapped point is
   assembled.

## 10. What moves at closure

Tier L closure per `CLAUDE.md`: `CHANGELOG.md`, backlog removal, **full step
format** in `40_history/00_completed_development.md`, plus —

- `PROGRAM_SPEC.md` — the `balance` notes paragraph (the labelled-lumped-terms
  list gains this one, and the residual-floor sentence changes);
- `CONVENTIONS.md` §7 — `z_b`'s owner in the single-source table with its drift
  guard;
- `balanced_cases.md` §2 item 5 and §3 — the pitch floor statement, now the same
  R3 floor as the force floor;
- `theory_sources.md` — the `balance` row's closure targets, and the citation for
  the wind-axis decomposition of §2;
- `DATA_DICTIONARY.md` — via its generator, never the file, for the new input;
- `tests/test_balance.py` — every `_PITCH_RESIDUAL_CEILING` entry falls to the
  floor; plan 13's G9 ceiling likewise.

## 11. Sources

- `flight_envelope._balance` (`flight_envelope.py:125-180`) — the trim whose
  idealisation this note measures against; oracle-locked to Ref 1 Appendix A
  p179 (`tests/test_flight_envelope.py:79`).
- `aero_curves.drag_cd` (`aero_curves.py:96`) — "airplane-less-tail `CD` at lift
  coefficient `cl` (the drag polar)", the polynomial `FlightLoadsInput` carries.
- `airloads` (`airloads.py:360-402`) — the strip chord force: section profile
  drag `aero.profile_drag` plus induced `c_l·α_i`, resolved with lift through the
  case `α`.
- `CONVENTIONS.md` §1 (axes/signs), §7 (single-source owners and drift guards).
- `balanced_cases.md` §2 item 5 (the lumped-and-labelled rule this load is filed
  under), §3 (the residual gates).
- `tail_geometry.fin_root_waterline` (`tail_geometry.py:238`) — the precedent
  D-1 follows: a geometric quantity that was an implicit zero, given an owner, a
  resolution order and an `assumed` flag.
- Pri 5 in `00_backlog.md` — the measurement this note builds on, with the
  element sweep and the three-term identity.
