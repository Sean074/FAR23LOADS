# Design note — a carrier for non-wing drag in the assembled model

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: ✅ SHIPPED 2026-08-15** (revision 2 as agreed; D-1's two-branch order,
the `ΔC_D` gate G10 and the passing-band measurement all implemented as written).
Kept as the plan of record. Closure: `CHANGELOG.md`, full step format in
`../40_history/00_completed_development.md`; backlog Pri 5 removed. Written to `CLAUDE.md` required practice 1 (design note before code
for physics/L steps): theory reference, `CONVENTIONS.md` citations, closure
targets with expected numbers, acceptance tolerances — agreed in chat before
implementation.

**What revision 2 changed.** D-1 — the placement of the load, and the decision
the whole step turns on — was reviewed. Its recommendation stands but its
*rationale* was withdrawn and rebuilt (§8.1, marked rather than deleted), one
provision changed (no `root_waterline_z` branch, which was a latent gate-breaker
on `ga6_normal`), the passing-band measurement was added (§6.1), and a new gate
**G10** was added to carry the diagnostic signal that placing the load
necessarily removes from the residual.

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

### 6.1 The passing band — how much latitude `z_b` actually has

Solving `|residual_new(z_b)| < 1 %` for every gated case and intersecting
(23.427(a) `UNSYMMETRICAL` excluded — `balanced_cases.md` §3 deliberately does
not gate it):

| fixture | **every gated case passes for** | width | `zw` | `root_waterline_z` | body mass centroid |
|---|---|---|---|---|---|
| `concept_regional_jet` | **42.02 – 63.66** | 21.6 in | 53.30 ✓ | 45.0 ✓ | 73.65 ✗ |
| `ga6_normal` | **79.88 – 95.81** | 15.9 in | 87.73 ✓ | 78.5 ✗ | 93.57 ✓ |

Three things follow, and together they settle D-1:

1. **The band is centred on `zw` by construction** — the residual is zero there
   and grows linearly either side, so the half-width is `gate/|ΔF_x|` for
   whichever case binds: ±10.6 in on the RJ, ±8.0 in on the ga6. `zw` is
   therefore the *most robust* choice available, not merely the smallest-residual
   one.
2. **Stating the truth later cannot break the gate.** Any plausible body
   centreline for either airplane lies well inside ±8 in of the wing plane. The
   default is a placeholder that a real measurement can replace without
   re-baselining anything.
3. **The one nearby failure is not a body centreline.** ga6's `root_waterline_z`
   = 78.5 misses its band by 1.4 in — and it is the *wing* root, borrowed as a
   body datum by the fin-root fallback. `ga6_normal` has `fuselage_height = 0.0`:
   **no body geometry at all**, the same gap the L-7 note found
   (`19_l7_lateral_body_aero_note.md` §10). There is no body centreline anywhere
   in the schema to derive from — `FuselageSection` carries `x`, `width`,
   `height` and **no `z`**.

## 7. Gates

| # | Gate | Target |
|---|---|---|
| **G1** | `residual_fx == 0` to `1e-9` on every assembled **flight** case, every fixture | The `nx` gap closes in full, at any `z_b` — this is the unambiguous half |
| **G2** | `delta_nx` on a flight case equals the trim's own `dx/W` to `1e-9` | The closure stops standing in for drag; today ga6 PHAA reads 0.661 g against the trim's 0.610 |
| **G3** | Pitch residual with the **default** `z_b` | ≤ 0.086 % (RJ), ≤ 0.075 % (ga6) — the lift-term floor. **Met: 0.086 % (RJ) / 0.075 % (ga6).** `_PITCH_RESIDUAL_CEILING` is **retired** — every family now passes the flat 1 % gate, and `_PITCH_RESIDUAL_RATCHET` replaces it to keep the bite the per-fixture numbers used to provide |
| **G4** | Ground cases carry **no** `body-axial` load | Same rule `fuselage_cm == 0` already holds them to |
| **G5** | Sum identity: `Σ fx(applied) == vn.dx` on every flight case | The correction is defined by this and must be asserted, not assumed |
| **G6** | `z_b` provenance is on the result | `assumed`/`entered` and its basis, exactly as `FinRoot` carries them (`tail_geometry.py:238`) |
| **G7** | Oracles bit-for-bit | `balance` is concept-mode; `_balance`/FLTLOADS is untouched, so Appendix A must not move by a digit |
| **G8** | Export equilibrium | The deck's `ΣFx` re-sums to ~0 with the new card present (`export/equilibrium.py`), and the `nx` line in the deck header states the new value |
| **G9** | Drift guard | One owner for `z_b` with a test, per `CLAUDE.md` practice 3 — the same treatment `fin_root_waterline` got for the same class of quantity |
| **G10** | **`ΔC_D` is reported per case and gated for consistency** | See below — the gate that replaces the signal carrying the load removes from the residual |

**G10, and why it is not optional.** Placing the load makes `residual_fx ≡ 0` by
construction and (at the default `z_b`) removes the drag term from the pitch
residual as well: §8.1 sets out why that is unavoidable. So the quantity that
*found* this defect must not become invisible the moment it is carried. Report

```
ΔC_D = (dx − ΣFx_wing) / (q·S)
```

on every flight case as a named diagnostic, and gate its **consistency across
cases**, which is where its physical content lives: a missing parasite term is a
`C_D` offset independent of `C_L`. On `ga6_normal` it is **−0.018 within ±11 %
across all seven cases** (§2) — a real bound, tight enough to bite. That same
gate is what surfaces the unexplained high-`α` sign flip on the regional jet
(§9.2) rather than burying it inside a load that now balances.

## 8. Decisions requested

| # | Decision | Recommendation |
|---|---|---|
| **D-1** | **Where does the load act vertically?** | **A new stated input `body_drag_waterline_z`, with a deliberately *two-branch* resolution order ending at `zw`.** See §8.1 — this is the decision the step turns on, and the reasoning matters more than the answer |
| **D-2** | **How is it distributed in `x`?** | Free — `x` does not enter the pitch residual (§4). Distribute over the body stations by **frontal-area share** where a `FuselageOutline` exists, else lump at the body-inertia centroid `x`, flagged. Physical where the geometry allows, harmless where it does not |
| **D-3** | **What is it called?** | `source="body-axial"`, not `body-drag`. At the RJ's two high-`α` points the quantity is **forward** (§2), and a card labelled "drag" pointing forward is a lie in the deck. The rendered label states it as *the airplane-less-tail axial force the wing strips do not carry* |
| **D-4** | **Clamp the negative (forward) values?** | ~~**No.**~~ **Revised 2026-08-17 (§8.2): not applied outside a stated one-sided trusted-`α` window; a defect inside it.** The original answer — the correction is defined as whatever closes the two drag models, and clamping would (a) reopen `residual_fx`, killing G1/G5, and (b) hide a real finding — is superseded as set out in §8.2 |
| **D-5** | **Does the ga6 get body geometry first?** | **Recommend yes, as a separate step before this one** — merged with what the L-7 note §10 and Pri 10 need from the same geometry. `fuselage_height = 0.0` means the ga6 cannot state a body centreline at all, so D-1's default is doing all the work there. Sequencing it first keeps this step's digest wave attributable, the same reasoning the L-7 note applied |

### 8.1 D-1 in full — the placement of the load

**[REVISED 2026-08-15]** Revision 1 of this note recommended defaulting to `zw`
**because it is residual-neutral**. That justification is withdrawn: it optimises
the wrong thing — it chooses where to put a physical load so that a *validation
number* comes out small. The recommendation survives the review; the reasoning
did not, and one provision changes with it (no `root_waterline_z` branch). The
superseded rationale is left stated here rather than deleted, so that a reader
who remembers it can see why it was dropped.

**What makes the argument invalid.** Placing the load at *any* `z_b` makes
`residual_fx ≡ 0` by construction, and placing it at `zw` additionally deletes
the drag term from the pitch residual. **The residual stops being a cross-check
on drag either way** — which is unavoidable, because what is being closed is a
known-missing load, not a disagreement between two models. Choosing `z_b` to
minimise it therefore buys nothing real, and would buy a false load position.
The signal has to move somewhere else instead: see G-10.

#### The options, measured

| # | Option | Result |
|---|---|---|
| 1 | `z_b = zw`, fixed, no input | Residual → lift floor. Simple, but a placement by convenience that can never become honest, and unfalsifiable |
| 2 | `z_b = root_waterline_z`, derived, no new input | RJ passes (0.725 %); **ga6 SIDE GUST −1.173 %**, a new exceedance on the Appendix A fixture. Rejected — *and* a landmine: ga6 has `fuselage_height = 0.0`, so any branch conditioned on body geometry would **flip** the moment Pri 10 or L-7 §10 give ga6 a body, breaking a gate through a fixture-data change |
| 3 | New input, two-branch order ending at `zw` | **Recommended** |
| 4 | Derive from the fuselage outline | Not possible today — `FuselageSection` has no `z` (§6.1 point 3). The right long-run answer; needs a schema change |
| 5 | Do not place it; report `ΔC_D` and leave the residual | Cheapest, no new physics — but `nx` stays wrong and the deck stays short a real load. Fails what the mission asks of the assembled model |

#### The recommendation

Option 3, with the middle branch **deliberately omitted**:

```
explicit body_drag_waterline_z  -> use it                      (assumed False)
otherwise                       -> zw, with a loud note        (assumed True)
```

Do **not** derive `z_b` from `root_waterline_z` under any condition.

The rationale, restated: **the suite has no datum for the body centreline.** Not
a missing default — a genuinely absent quantity (§6.1 point 3). Given that, `zw`
is the right fallback because it is *the trim's own assumption*, so the step
asserts nothing the project cannot yet support and flags that it is doing so. The
small residual is a consequence of that choice, not its purpose. What makes it
comfortable rather than merely convenient is §6.1: `zw` sits at the **centre** of
the passing band on both fixtures, with ±8 in of latitude, so a later stated
measurement can replace it without re-baselining anything.

This is the `fin_root_waterline` pattern (`tail_geometry.py:238`) applied to the
same class of quantity — a geometric input that was an implicit constant, given a
single owner, a resolution order, an `assumed` flag and a loud note.

#### Consequence to accept

At the default the load sits on a node at the wing plane, not on the body line.
Harmless in the balanced deck — it is a load set with no elements
(`export/roundtrip.py:26`), and `deck_nodes` allocates a node at each load's true
position — but **Pri 1** (LRA beam export) and **step 14** (real stiffness) will
care. Option 4 is the answer there, and it pairs with L-7 §10, Pri 10 and M4-19,
all of which want body geometry the fixtures do not have.

### 8.2 D-4 revised — a forward value outside the polar's fitted range is not a load

**[REVISED 2026-08-17, backlog Pri 2, agreed in chat under the solo profile
(`DEVELOPMENT_PROCESS.md` §0).]** Revision 2 answered D-4 "no clamp; note it",
for two reasons: clamping would reopen `residual_fx` and so kill G1/G5, and it
would hide the high-`α` overshoot (§9 item 2). Both reasons were about the two
RJ points above `α ≈ 19°`. When Pri 5 / D-26 brought the other four fixtures
into the assembly (2026-08-15) the same sign inversion appeared at the **other**
end of the range — `NMAA` at `α = −12.9…−14.3°` on `atr42_100`, `dhc8_dash8`
and `concept_heavy`, forward by **1,004 / 1,097 / 1,445 lb** — and the test
suite recorded them as excused points inside a symmetric `|α| ≤ 15°` window
while the balanced decks carried the forward "drag" as a `body-axial` card.
That is 3–8 % of `W` as a forward body force on a negative-g corner: a
first-order defect in shipped content (`CLAUDE.md` rule 6), and it is what
overturns the recommendation.

**What is wrong with the original reasoning.** The correction is "whatever
closes the two drag models" *only where both models are trusted*. The entered
polar is a `CD(CL)` fit over the positive-lift range; read 13° below zero lift
(the `NMAA` points) or above the stall line (the RJ points) it is an
extrapolation, and the difference between an extrapolated polar and the strip
model is not a fuselage force — it is the extrapolation error, with a sign
that says nothing about the airplane. Applying it as a load so that a
*validation number* (`residual_fx`) comes out zero is the same mistake §8.1
withdrew for `z_b`: choosing where a physical load goes, or whether it exists,
to make a gate pass.

**The revised answer.**

- **A trusted-`α` window is a single owner**, `constants.POLAR_TRUSTED_ALPHA_DEG
  = (−10°, +15°)`, **one-sided on purpose**: the upper bound is where the RJ's
  strip induced drag overshoots the polar; the lower bound separates the three
  crude-polar fixtures' cross-over (−12.9° and below) from the Appendix A
  airplane and `cessna_210`, both still consistent at −8.4/−8.9°. The predicate
  is `balance.polar_alpha_trusted`, read by the code and by the test (rule 3).
- **Outside the window a forward difference is not applied.** No `body-axial`
  card, `body_axial = 0`, `body_axial_clamped = True` on the case, the raw value
  and the window in the case note and the deck header. **`ΔC_D` is still
  computed and reported from the unclamped difference**, so G10 keeps the
  signal that found the defect — this answers reason (b): nothing is hidden,
  the window is stated and the number is printed.
- **Inside the window a forward value is a fixture aero-data defect**, applied
  as computed, noted, and **failed by G10** — the three excused entries are
  gone from the test; there is nothing left to excuse.
- **G1/G5 and G2 read the same flag.** On a clamped case the applied `fx` is
  the strips' own (strictly more drag than the trim's `dx`, never less) and
  `delta_nx` is that over `W`; `residual_fx` re-opens by exactly the clamped
  force, on those cases only — this answers reason (a): the gate is not
  killed, it states its exception and pins it per case.
- **The pitch residual re-opens too, and that is stated rather than absorbed.**
  The forward force sat at the body-drag waterline — the wing plane, ~40 in
  from the CG on a high-wing turboprop — so removing it re-opens `residual_my`
  by that couple: **1.48 % / 1.80 % / 2.09 %** of `n·W·MAC` on the three
  `NMAA` points (RJ: 0.15–1.12 %), against plan 11's flat 1 %. That residual
  *is* the polar/strip inconsistency at an `α` where the polar is untrusted; it
  is reacted by the closure (`q_dot`, ≤ 0.0008 rad/s²) and gated **per case**
  in `tests/test_balance.py::_CLAMPED_BODY_AXIAL` with `(force, pitch)`
  ceilings measured at this revision, under a 2.5 % hard stop
  (`CLAMPED_PITCH_CEILING`, the twin of `FORCE_RESIDUAL_CEILING`). The
  alternative — keep the forward card so the residual reads 0.05 % — is the
  comfortable number the original D-4 warned against, pointed the other way.
- **Effect on delivered loads (rule 6):** the seven affected balanced decks lose
  a 1.0–2.6 klb forward axial card on the body; the closure inertia set moves by
  the re-opened residual. Nothing moves on `ga6_normal` or `cessna_210`, or on
  any case inside the window. Imperial digest regenerated for the four
  fixtures' `balance` channels and three `lra_model` channels.

§9 item 2 (the overshoot itself) stays open: this revision decides what the
model *does* with an untrusted difference, not why the strip model and the
polar disagree there — re-entering the polars is explicitly **not** this item
(backlog Pri 2, "not a re-derivation of the polars").

## 9. Open items

1. **D-5's sequencing is a real fork**, not a formality: with D-1's recommended
   default this step ships and gates cleanly *without* ga6 body geometry, so the
   two can be done in either order — but only if the reviewer accepts that on the
   Appendix A fixture `z_b` is the wing plane by default rather than by
   measurement. Worth an explicit yes. Note that under D-1's **two-branch** order
   (§8.1) giving ga6 a body later does *not* move `z_b` on its own: only an
   entered `body_drag_waterline_z` does. That is deliberate — it is what stops a
   fixture-data change from silently moving a gate — but it does mean the body
   geometry step must enter the waterline explicitly to have any effect here.
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
- `DATA_DICTIONARY.md` — via its generator, never the file, for the new
  `body_drag_waterline_z` input;
- `tests/test_balance.py` — **checked at implementation and confirmed**: no gated
  case on either fixture exceeds 1 % at the default `z_b`, so the per-fixture
  ceiling mechanism was retired outright. `_PITCH_RESIDUAL_CEILING` becomes
  `_PITCH_RESIDUAL_RATCHET` — the flat gate would otherwise pass a 12x regression
  on the RJ in silence. Plan 13's G9 inherits the flat gate;
- the case result and its renderings — `ΔC_D` as a reported per-case diagnostic
  (G10), beside the existing residual and relief figures that `CONVENTIONS.md` §1
  makes part of the deliverable.

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
