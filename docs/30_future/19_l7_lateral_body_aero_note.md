# Design note — lumped lateral body aero, `Cy_β` and `Cn_β` (L-7)

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: SHIPPED 2026-08-17** (revision 3 agreed in chat the same day —
decisions L-7.8…L-7.17 below). Implementation: `sloads/lateral_body_aero.py`,
`sloads/atmosphere.py`, `select.py` (β and fin-derivative publication),
`balance.py` (`lateral_aero_terms` / `body_aero_loads` / the two case
sentences), schema v54; gates `tests/test_lateral_body_aero.py` (G1) and
`tests/test_l7_lateral_balance.py` (G2–G12). **Three things the implementation
settled differently from the text below, recorded rather than rewritten:**
(a) the DATCOM transcription in §3 is from `SUPLAH` (the *supersonic* h-tail
slot); the subsonic path is `SUBLAT` (`datcom.f:29027-29052`), which differs in
three details — `K_i` from the wing height (`2·z_w/d`, fig. 5.2.1.1-7), chart C's
argument is `h_max/w_max` (not 1.0), and the side area is `∫(ZU−ZL)` when the
profile is given — and is what the printed oracle reproduces (all applicable
sample values within 0.05 %); (b) the moment reference of the computed `Cn_β`
is the wing 25 %-MAC station `xw` (the suite's aerodynamic reference, where the
trim's force system already acts) rather than a "reference CG" — L-7.9's linear
transfer to each case CG is unchanged; (c) the applicable oracle set is
`ex1` c1, `ex3` c1 (M 0.6 and 0.8), `ex4` c1, `ex5` — `ex7`/`ex8` print only the
fin-inclusive total and drop out. §7's scratch numbers stand as the design
baseline; the shipped values (`Cy_β` on the RJ is ~2.7× the scratch value,
because DATCOM's `S_0` on the fixture's three-section tail cone is ~10× the base
area the scratch used) are in `docs/20_theory/balanced_cases.md` §7.4. Written to `CLAUDE.md`
required practice 1 (design note before code, physics/L step). Backlog item
**Pri 2** — the 0.7.0 headline, issue #8 ([`00_backlog.md`](00_backlog.md), re-cut 2026-08-17), from plan 13 decision **L-7**
([`13_b8a_lateral_closure_plan.md`](../40_history/18_b8a_lateral_closure_plan.md) §5.6).

**Revision 2, 2026-08-15.** Revision 1 proposed a Munk-only couple with a
reduction factor and no side force. Sourcing Digital DATCOM
(now bundled at `reference/datcom/`, USAF public domain — see its
`PROVENANCE.md`) overturned three of its conclusions;
every one is marked **[R1 CORRECTION]** below rather than quietly replaced.

**Revision 3, 2026-08-17.** Agreed in chat before code. Ten open points were
resolved; each is marked **[R3]** where it lands and collected in §9 as
L-7.8…L-7.17. The largest change is that **G1's oracle is rescoped** (§8):
of Digital DATCOM's 11 sample problems only the *subsonic body-alone and
wing-body* cases exercise the method ported here — the rest are wing-alone,
supersonic/hypersonic, or carry experimental-data overrides — so G1 pins the
applicable printed values (~5–6 checks over ~3 distinct geometries), enumerated
by file/case/α-row, and says which are inapplicable and why. Revision 2's
"11 printed cases" claim is corrected in place.

**Definition of done is an oracle, not a closure gate.** Digital DATCOM ships
sample cases with printed `CYB`/`CNB` output. The port is validated against the
applicable ones at ±0.1 %, exactly as the FAR23 core is validated against
Appendix A. This replaces revision 1's "no oracle exists → stated closure gate"
premise.

This note covers the **lumped** step. The distributed (per-station) body load
still pairs with **M4-19**; §10 states the seam.

---

## 1. What is missing today, and one thing that is wrong

`balance.assemble` (`sloads/modules/balance.py:1097`) applies the fin's
distributed side load (`fin_sets`, `:630`) and lets `_closure` (`:957`) absorb
**the whole** pre-closure `Fy`/`Mz` as rigid-body `n_y` and `r_dot`. The fin is
the only lateral aerodynamic load in the suite. That is stated in-band by
`LATERAL_AERO_NOTE` (`:307`), which says both `n_y` and the yaw acceleration are
**over-stated by an unknown amount** and that the inertia they drive is therefore
conservative.

**[R1 CORRECTION / SHIPPED DEFECT] The `n_y` half of that sentence has the
direction backwards.** At `+β` the body and wing side force acts to **port** —
the *same* direction as the fin's restoring load — so it **adds**. Measured with
the DATCOM derivatives (§7): `|n_y|` rises **4.1 %** on the two rudder-neutral
conditions and **12.0 %** on `YAW TO SIDESLIP`. So `n_y` is **under**-stated
today, and the lateral translational inertia it drives is **not** conservative.
The yaw half of the sentence is correct — `ψ̈` genuinely is over-stated, because
the body's yawing couple is destabilizing and opposes the fin's.

This is a defect in shipped text and it is independent of whether this step is
worked: `balance.LATERAL_AERO_NOTE`, `report/methods.py:156` (which quotes the
constant), `CONVENTIONS.md` §1's L-7 bullet and `PROGRAM_SPEC.md`'s two lateral
bullets all carried it. It was filed as its own backlog defect (practice 5), not
folded silently into this step, and **fixed 2026-08-15**: the sentence now states
a direction per degree of freedom, with both magnitudes still *unknown* in band —
the numbers below are measured in a scratch run, and no shipped code reproduces
them, so quoting them stays part of this step. `tests/test_methods_stamp.py`
pins the two directions separately so they cannot be collapsed again.

## 2. The two derivatives, and why one of them is not Munk

The suite already has the **pitch** analog of the missing physics:
`sloads/fuselage_moment.py` (step G4), Munk slender-body,
`dCm/dα = (k2−k1)·Vol/(S·mac)`, built from the G1 `FuselageOutline`. Revision 1
proposed the direct yaw rotation of it, `N = (k2−k1)·q·Vol·β`, and reasoned that
because a **closed body in ideal flow carries zero net force** (d'Alembert) the
step would deliver a couple only, leaving `n_y` untouched.

That reasoning about Munk is correct and is confirmed numerically — but Munk is
the wrong model for this axis.

**[R1 CORRECTION] DATCOM's wing-body `Cn_β` is 2.3× Munk's, not a fraction of
it.** Measured on `concept_regional_jet`: Munk gives `+0.0876 /rad`, DATCOM
5.2.3.1 gives **`+0.2026 /rad`**. Revision 1's whole "apply a reduction factor to
Munk" premise (its decision L-7.3a) is **void**. The reason is specific: Munk is
an *isolated body in ideal flow*, while DATCOM's `K_N` correlates the **wing-body
combination**, whose wing contribution and interference are destabilizing and
which Munk omits entirely. The "Munk over-predicts by 10–40 %" statement that
motivated the factor is a **pitch**-axis result — the aft body sits in wing
downwash — and it does not transfer to yaw, where there is no comparable relief.

**[R1 CORRECTION] A lumped `Cy_β` is reachable, so both halves close.** DATCOM
gives `Cy_β,WB = −K_i·CL_α,B − 0.0001·|Γ°|`. Revision 1 said the side-force half
had to wait for the distributed cross-flow step; it does not. It is small —
`−0.0213 /rad` on the RJ, of which `−0.0172` is the **wing dihedral** term and
only `−0.0041` the body base term — but small-with-a-number is exactly what
converts `LATERAL_AERO_NOTE`'s "unknown" into a statement.

So this step closes **both** halves of the L-7 honesty statement, and corrects
the direction of one of them.

## 3. Method and citations

The method is transcribed from the Digital DATCOM source, which contains it in
full **including its digitized chart data** — the reason no invented constant is
needed anywhere in this step.

```fortran
!  reference/datcom/datcom.f:33413-33444  (subsonic wing-body sideslip derivatives)
      CYBWB = -RKI*CLAB - 0.0001*ABS(DIHEQ)          ! DATCOM 5.2.1.1
      RNN   = <Reynolds number on body length>
      RKRL  = 1.+ALOG(1.E-6*RNN)/4.86                ! FIG 5.2.3.1-9, closed form
      CALL TRAPZ(...)  -> SBS = 2*integral of half-height dx
      ARG12 = SQRT(RH1/RH2)                          ! heights at 0.25 / 0.75 l_B
      ARG13 = RLB**2/SBS ,  ARG14 = XCG/RLB
      ... three chained TLINEX lookups -> RKN        ! FIGURE 5.2.3.1-8 (A/B/C)
      CNBWB = -RKN*RKRL*SBS*RLB/(SR*BLREF)           ! DATCOM 5.2.3.1
```

| Piece | Source |
|---|---|
| Wing-body `Cn_β`, figures 5.2.3.1-8 (`K_N`) and 5.2.3.1-9 (`K_Rl`) | USAF DATCOM **5.2.3.1**. *(Revision 1 cited 5.2.1.1 for `Cn_β`; that is the side-force section — corrected.)* |
| Wing-body `Cy_β` | USAF DATCOM **5.2.1.1** |
| The implementation, and the `K_N` chart as data | `reference/datcom/datcom.f`: method at `:33413-33444`; `X158A/Y58A`, `X158B/Y58B`, `X158C/Y58C` at `:28725-28756`, labelled `Q52318 = "5.2.3.1-8"` |
| **The oracle** | `reference/datcom/examples/ex1..ex11.{inp,out}`, printed `CYB`/`CNB` columns; body geometry in each `.inp` as `X`/`R`/`S`/`ZU`/`ZL`, convertible to `FuselageSection` |
| Munk apparent-mass couple (retained as the isolated-body cross-check) | Munk, NACA TR-184 (1924); table already in `fuselage_moment.py:_K_TABLE`; `reference/fuselage_pitching_moment.md` |
| Sideslip / yaw sign definitions | `CONVENTIONS.md` §1.1 **SC-1** (+β = wind from starboard, nose left of the flight path); §1.1 physical senses (**+mz = nose to port**) |
| Six-DOF closure, free moments, mirror operator | `CONVENTIONS.md` §1 (decisions L-2/L-3), §7.1 (handedness) |
| The regulation | FAR **23.441(a)** — §4 below |

**A confirmation worth keeping.** Digital DATCOM's `ex1.out` prints, for a body
alone, `CLA = 3.433E-03`, `CMA = 3.415E-03`, `CYB = -3.433E-03`,
`CNB = -1.979E-03` (per degree). Two identities fall out exactly:
`CYB = −CLA`, and `CNB = −CMA · c̄/b` (3.415e-3 × 2.48 / 4.28 = 1.979e-3). The
second is this note's "same integrand rotated 90°" claim, verified against
DATCOM's own printed answer rather than argued.

**Documents still worth sourcing** (not blocking — the code and its sample output
are self-contained): AFWAL-TR-83-3048 (the DATCOM document, for page-level
citation of §5.2.3.1/§5.2.1.1 and to upgrade G4's existing §4.2.1.1 citation);
AFFDL-TR-79-3032 **Vol II**, *Implementation of DATCOM Methods*, which maps the
Fortran to the equations and records where it simplifies; **NACA Report 705**
(House & Wallace 1941), the lateral wing-body-fin interference correlation that
almost certainly underlies figure 5.2.3.1-8; and **NACA Report 1048** (Allen &
Perkins 1951) for the viscous cross-flow term the M4-19-paired distributed step
will need.

## 4. What FAR 23.441(a) says, and the gate it does *not* license

Checked 2026-08-15 against both bundled sources, which quote it **identically** —
User's Guide §12.2.10 (`reference/ug.txt:5454`, Jan-1994 CFR text, authority
level 2) and the code manual p77 (`reference/code.txt:6520`, level 3):

> **(a)** At speeds up to V_A, the vertical surfaces must be designed to
> withstand the following conditions. **In computing the loads, the yawing
> velocity may be assumed to be zero:**
> **(1)** With the airplane in unaccelerated flight at zero yaw, it is assumed
> that the rudder control is suddenly displaced to the maximum deflection […]
> **(2)** With the rudder deflected as specified in paragraph (a)(1) […] it is
> assumed that the airplane yaws to the resulting sideslip angle. In lieu of a
> rational analysis, an **overswing angle equal to 1.3 times the static sideslip
> angle** of paragraph (a)(3) […] may be assumed.
> **(3)** A yaw angle of **15 degrees** with the rudder control maintained in the
> neutral position […]

**19.5° is derived, not chosen:** 1.3 × 15° = 19.5°, the constant at
`select.py:727`. The suite is using the regulation's own shorthand.

**Near-zero `ψ̈` is not the target at (a)(2).** The rule is an *overswing* past
equilibrium, so a substantial `ψ̈` is correct.

**[R1 CORRECTION] Neither is "the net case moment must be restoring".**
Revision 1 argued that at an overswing peak `β̇ = r = 0`, so the net yawing
moment must oppose β, and made that a hard gate on all β ≠ 0 conditions. That is
sound for a *computed* overswing peak, but (a)(2) is not one: 19.5° is a
prescribed regulatory angle, and the rudder is a **control input** driving the
airplane away from equilibrium, not toward it. With the derivatives of §7 the
linearised equilibrium under full rudder lies far beyond 19.5° (formally ~65°,
well outside the linear range — the figure is not meaningful, the conclusion is).
A destabilizing net moment at (a)(2) is therefore physically correct, and
revision 1's gate would have rejected the right answer.

**The valid gate is on the derivatives, with control input excluded.** FAR
**23.177** requires static directional stability, so:

> `Cn_β,fin + Cn_β,body` must remain restoring.

Measured on the RJ (§7): `−0.257 + 0.2026 = −0.054 /rad`, **stable, with 21 % of
the fin's contribution as margin.** The net-moment form of the check survives
only where the rudder is neutral — (a)(3) and 23.443(b) — and both pass.

**"The yawing velocity may be assumed to be zero"** is also direct regulatory
backing for the suite's rate-free closure (`CONVENTIONS.md` §1.1: attitude angles
and body rates as state do not exist).

### 4.1 Provenance: the section no longer exists in current Part 23

14 CFR Part 23 was restructured into performance-based rules by **Amdt. 23-64**
(Doc. FAA-2015-1621, 81 FR 96689, 30 Dec 2016; effective 30 Aug 2017). Current
Part 23 runs §§ 23.2000–23.2620 and contains **no § 23.441** — verified against a
current consolidated text. This suite replicates **pre-Amdt-23-64 Part 23**,
which is its stated scope, so the Jan-1994 text is the correct authority and the
reference hierarchy needs no change. Recorded because "check the current CFR" is
a standing practice (F25-0), and the honest answer here is *withdrawn, not
amended*.

## 5. Signs — derived, not asserted

At **+β** the apparent-mass couple acts to *increase* β (destabilizing, as the
pitch term increases α). Increasing β is further nose-left, which is **+mz**
(SC-1 + §1.1). The fin's restoring load at +β is `−fy` aft of the CG, giving
**−mz**. So the body couple **opposes** the fin couple and `|ψ̈|` falls.

The side force is the opposite story and is why §1's correction exists: DATCOM's
`Cy_β,WB < 0` means at +β the wing-body force is to **port**, the same sense as
the fin's, so the two **add** and `|n_y|` rises.

β of the **computed** (starboard-hand) case, from SELECT (`select.py:725-754`):

| Condition | FAR | β | Source |
|---|---|---|---|
| `SUDDEN RUDDER` | 23.441(a)(1) | **0** | rudder at zero sideslip — no body term at all |
| `YAW TO SIDESLIP` | 23.441(a)(2) | **+19.5°** | SELECT's entered `−19.5` is the +β case (SC-1) |
| `YAW 15 NEUTRAL` | 23.441(a)(3) | **+15.0°** | as above |
| `SIDE GUST` | 23.443(b) | **−4.81°** on the RJ | `β_eff = Kgt·Ude/V`; the returned load is `+fy`, so the computed case is the −β hand |

The port twin follows from `reflect_load` (`:446`) → `reflect_force`/
`reflect_moment`, which already flip `fy` and `mz`; nothing new for the hand.

**`β_eff` must be produced by SELECT, not re-derived.** `_vt_side_gust`
(`select.py:680`) computes `Kgt` and `Ude` inline and returns only the load.
Re-deriving them in `balance` would be a second opinion of an oracle-locked
quantity — the defect class `CONVENTIONS.md` §7 exists to prevent.

## 6. Where it plugs in

| Seam | Change |
|---|---|
| new `sloads/lateral_body_aero.py` | `Cy_β`/`Cn_β` from `FuselageOutline` + CG + wing reference + dihedral: `S_BS`, `l_B`, `h(0.25l)/h(0.75l)`, `Re_l`, the three `K_N` tables, the closed-form `K_Rl` |
| `sloads/fuselage_moment.py` | expose `munk_couple(outline, q, angle)` and re-express `estimate()` through it, so the apparent-mass couple has one owner (practice 3). Used here only as the isolated-body cross-check |
| `select.py` | `SIDE GUST` publishes `β_eff`; the maneuver conditions publish their entered β |
| `balance.assemble` | one applied load carrying **both** terms, beside the existing `source="fuselage-cm"` line (`:1157`) |
| `BalancedCaseResult` | `fuselage_cy` / `fuselage_cn` fields, siblings of `fuselage_cm` |
| `balance.LATERAL_AERO_NOTE` | replaced by a quantified statement, both halves; `report/methods.py:156` and `tests/test_methods_stamp.py:182` follow |
| `models/inputs.py` | `LateralBodyAeroInput(enabled, cy_beta, cn_beta)` on `AeroCoefficientsInput` — the shape of the shipped `FuselageMomentInput` (computed default, overridable; **per degree**, L-7.15). Schema bump v53 → **v54** + migration. **[R3] Passenger on the hop (L-7.10):** an additive per-engine thrust field on `EngineInput` (e.g. `thrust_lb: Optional[float] = None`), reserved for backlog Pri 3 (#10) so 0.7.0 keeps to its one hop |
| new `sloads/atmosphere.py` | **[R3, L-7.13]** ISA temperature + Sutherland kinematic viscosity, one owner with a drift-guard test; `Re_l` from TAS and local `ν` |
| `select.py` (vtail conditions) | **[R3, L-7.11]** each 23.441/23.443 condition also carries `cy_beta_fin` / `cn_beta_fin` (about that condition's CG) beside its `beta_deg` |

**Application point.** The couple is free and needs no carrier — that is what let
revision 1 propose shipping ahead of M4-19. The **side force does have a
station**, and it is the one new modelling choice here: apply `Y` at the
**centroid of the body side area** (the same integral that produces `S_BS`), then
carry the remainder of the yawing moment as a free couple so the pair reproduces
`(Cy_β, Cn_β)` about the CG exactly. Resultants are then right by construction
and the station is defensible; the *internal* distribution along the body is
still lumped, exactly as `fuselage-cm` is, and that stays M4-19's job. Said
in-band rather than left to be discovered.

**The pitch path cannot be copied.** G4's Munk term enters the *trim solve*
through `flight_envelope._apply_fuselage_moment`, and the `fuselage-cm` load in
`assemble` is a different quantity — the residual `vn.m_wf − wing_about_ac`.
Laterally there is no trim solve and no `m_wf`, so both terms are applied
directly.

## 7. Worked numbers — `concept_regional_jet`

Geometry from the G1 outline: `l_B = 1056 in`, `S_BS = 69,538 in²`,
`h(0.25l)/h(0.75l) = 85.71/57.23`, `l_B²/S_BS = 16.04`, `x_cg/l_B = 0.587`,
`Re_l = 1.77e8` → `K_Rl = 2.065`, `K_N = 0.001324`.

### Derivatives

| Contribution | `Cy_β` /rad | `Cn_β` /rad (suite sign; − = restoring) |
|---|---|---|
| **Fin**, measured from the suite's own two rudder-neutral conditions | **−0.521** (−0.5211 / −0.5206) | **−0.257 … −0.270** |
| **Body + wing**, DATCOM 5.2.1.1 / 5.2.3.1 | **−0.021** (dihedral −0.017, body base −0.004) | **+0.2026** |
| Body alone, Munk (ideal flow) — cross-check only | 0 (closed body) | +0.0876 |
| **Net** | −0.542 | **−0.054 → stable, 21 % margin** |

The fin figures come from two independent conditions and agree to 0.1 % on
`Cy_β` and 5 % on `Cn_β`, which is itself a useful check that the assembled
lateral cases are self-consistent.

### Case effects

Measured by adding the applied set to each assembled case and re-solving
`_closure` (scratch run, this session):

| Condition | β | `N_body` (lb·in) | `Y_body` (lb) | `ψ̈` now | `ψ̈` with term | Δ`\|ψ̈\|` | `n_y` now | with term | Δ`\|n_y\|` |
|---|---|---|---|---|---|---|---|---|---|
| `SUDDEN RUDDER` | 0° | 0 | 0 | +51.6 °/s² | +51.6 | 0 % | +0.20931 | +0.20931 | 0 % |
| `YAW TO SIDESLIP` | +19.5° | +3.220e6 | −427 | −20.8 | **+39.7** | +90 % | −0.10752 | −0.12047 | **+12.0 %** |
| `YAW 15 NEUTRAL` | +15.0° | +2.477e6 | −329 | −55.7 | **−9.1** | −84 % | −0.24372 | −0.25368 | +4.1 % |
| `SIDE GUST` | −4.81° | −2.181e6 | +290 | +42.9 | **+11.5** | −73 % | +0.21456 | +0.22333 | +4.1 % |

Reading these:

- **`SUDDEN RUDDER` is untouched, exactly** — β = 0. A free gate (§8 G2).
- **The two rudder-neutral conditions keep their restoring sign** (−9.1 and
  +11.5 °/s²) while dropping 73–84 % in magnitude. §4's net-moment check applies
  to these two and both pass.
- **`YAW TO SIDESLIP` reverses and grows**, and per §4 that is now the *expected*
  result, not a failure: the rudder is driving the airplane toward a much larger
  sideslip and the case is genuinely divergent at the prescribed angle.
- **`n_y` rises everywhere**, by 4.1 % where the fin load is a clean sideslip
  load and 12.0 % on `YAW TO SIDESLIP`, whose fin net is a near-cancellation of
  its yaw and rudder terms (−3548 lb out of parts worth several times that).

**This is a load-increasing change on the lateral translational DOF and a
load-decreasing one on the yaw DOF.** It is not uniformly conservative in either
direction, which is the honest reason it must be a user-visible input rather than
a silent default.

### The other lateral fixture cannot exercise this at all

`ga6_normal` — the Appendix A airplane, and one of only two fixtures with lateral
cases — has **no body geometry**: `geometry.parametric.fuselage_length/_width/
_height` are all `0.0` and `geometry.fuselage.sections` is empty, so
`default_fuselage_outline` yields nothing and the estimator correctly returns
`None`. The step lands on **one fixture**. The graceful-`None` path is already
G4's, but it must be said out loud — and it makes the companion fixture-data item
of §9 more than cosmetic.

## 8. Gates

| # | Gate | Expected |
|---|---|---|
| **G1** | **Oracle [R3 rescoped]**: the ported `Cy_β`/`Cn_β` reproduce Digital DATCOM's printed `CYB`/`CNB` for every **applicable** sample case — the subsonic body-alone and wing-body rows: `ex1` cases 1–2 (body alone, M 0.6), `ex3` case 1 (`BUILD`, the **wing-body** row of the buildup, M 0.6/0.8 — *not* the total including the fin), `ex4` case 1 (M 0.6), and the shared body+wing geometry of `ex5`–`ex8` (one geometry, counted once). **Inapplicable, stated as such in the test:** `ex2` (wing alone), `ex1` cases 3–4 and `ex4` case 2 (supersonic), `ex3` cases 2–5 (experimental-data overrides — not the method), `ex9`–`ex11` (hypersonic / lifting body). Pinned at the α row nearest 0° (5.2.3.1's `Cn_β` is α-independent; this isolates any α-dependence of `Cy_β`). Informational, not gated: on `ex3` the fin share (total − WB) is reported as a cross-check of the suite's own fin derivative (L-7.11). **`reference/` is gitignored** (`.gitignore:9`), so the test carries the printed numbers and the case geometry **as literals with the line citation** — exactly how the Appendix A oracle tests carry theirs, and the reason CI needs nothing from `reference/` | ±0.1 %, per the FAR23 core's own standard; ~5–6 checks over ~3 geometries |
| **G2** | `SUDDEN RUDDER` (β = 0) takes **exactly zero** body load | `0.0`, exact |
| **G3** | **Static directional stability (§4)**: `Cn_β,fin + Cn_β,body` restoring on every fixture that assembles lateral cases. **[R3]** `Cn_β,fin` is *published by SELECT* per vtail condition (L-7.11), the body term is transferred to the same case CG (L-7.9), and the sum is formed about each case's CG | −0.054 /rad on the RJ (ga6 value added at implementation); flagged, not silently emitted, if it ever goes positive |
| **G4** | **Net-moment sign on the rudder-neutral conditions only** — (a)(3) and 23.443(b) keep a restoring `ψ̈` | −9.1 and +11.5 °/s² |
| **G5** | **Direction**: `\|ψ̈\|` falls and `\|n_y\|` rises on every β ≠ 0 case — the corrected §1 statement, asserted | −73…−84 % and +4.1…+12.0 % |
| **G6** | **Closed form**: the applied force and couple reproduce `Cy_β·q·S·β` and `Cn_β·q·S·b·β` about the CG | ratio 1.000000 |
| **G7** | **Independent producer**: Munk's isolated-body couple sits **below** DATCOM's wing-body value, by the interference margin | 0.0876 vs 0.2026 /rad; a Munk value *above* DATCOM means a porting error |
| **G8** | Appendix A / twin cases bit-for-bit with the feature off | unchanged, digest-verified |
| **G9** | Six-DOF closure holds, in memory **and from the deck's own card text** | ~1e-16 / card-format floor |
| **G10** | The deck still solves free-free in sbeam, both unit systems | reactions ≈ 0 |
| **G11** | The **symmetric half** still closes inside `RESIDUAL_GATE` with the fin and both body terms removed | unchanged to the last digit |
| **G12** | Handedness unchanged: the twins mirror, `fy` and `mz` flipping through the single owner | pinned case ids |
| **G13** | Registry↔spec drift guard and the methods stamp see the new note wording | `test_methods_stamp.py` |

G1 is the definition of done. G3 and G5 carry the physics; the rest are fences.

## 9. Decisions requested

| # | Proposal | Alternative, and why it is rejected |
|---|---|---|
| **L-7.1** | Ship the **lumped** `Cy_β` **and** `Cn_β` together; the distributed per-station body load follows with M4-19 | Couple only (revision 1). Rejected: `Cy_β` is reachable from the same source with no extra input, and shipping half would leave `LATERAL_AERO_NOTE`'s wrong half (§1) standing |
| **L-7.2** | **DATCOM 5.2.3.1 / 5.2.1.1 is the method**; Munk is retained as the isolated-body cross-check (G7) | Munk with a reduction factor (revision 1's L-7.3a). **Rejected on evidence**: DATCOM is 2.3× Munk, so the factor had the wrong sign, and DATCOM needs no invented constant |
| **L-7.3** | **Off by default**, computed default + override, `FuselageMomentInput`-shaped | On by default. Rejected: it moves loads *up* on one DOF and *down* on another (§7), so it is a user's decision |
| **L-7.4** | The **static-stability** check (G3) is the hard gate; the net-moment check (G4) applies only to rudder-neutral conditions | Revision 1's blanket net-moment gate. **Rejected**: it would reject 23.441(a)(2), where divergence is the correct answer (§4) |
| **L-7.5** | The side force acts at the **body side-area centroid**, with the balance of the moment as a free couple | Apply it at the CG. Rejected: exact resultants but an indefensible station, and the deck would put the whole body side load at the CG node |
| **L-7.6** | `β_eff` for `SIDE GUST` is **published by SELECT**, not re-derived in `balance` | Re-derive `Kgt·Ude/V`. Rejected: second opinion of an oracle-locked quantity |
| **L-7.7** | `munk_couple` becomes the single owner of the apparent-mass couple; `estimate()` is a view of it | Copy the integrand. Rejected — practice 3 |
| **L-7.8** [R3] | **G1 rescoped** to the applicable subsonic body-alone / wing-body printed values, enumerated (§8) | Keep "11 cases" by also porting DATCOM's fin method (5.3.1.1) to match the total `CNB`. Rejected: a second method the suite does not use, ported only to make a number match. Running Digital DATCOM locally on the RJ/ga6 as extra evidence: not gating, optional |
| **L-7.9** [R3] | **`Cn_β,body` evaluated once at the fixture's reference CG** (the `ref` `balance` already uses) and **transferred linearly** to each `CgCase`, `Cn_β,case = Cn_β,ref + Cy_β·(x_case − x_ref)/b` — automatic through the fixed force station of L-7.5. The override means "about the reference CG". The note carries the `K_N` nonlinearity over the fixture CG range as the bound | Per-case `K_N` at each CG (exact to DATCOM, more plumbing); or one value with no transfer (wrong by `Cy_β·Δx/b`, inconsistent with G6) |
| **L-7.10** [R3] | The v54 hop **carries the Pri 3 thrust field** as a reserved additive passenger | L-7 hops alone and Pri 3 waits for 0.8, or Pri 3 goes first — both break either the one-hop rule or the agreed order |
| **L-7.11** [R3] | **SELECT publishes `Cy_β,fin`/`Cn_β,fin`** per vtail condition, from the same `AVT`, `S_v`, arm that made the load; `balance` reads, never re-derives (same seam as L-7.6). The report states the stability margin in-band | New module derives the fin term (second producer of a SELECT quantity); or test-side fit only (no in-band margin) |
| **L-7.12** [R3] | **Body geometry from the entered `FuselageSection`s**: linear `height(x)`, trapezoidal `S_BS`, heights at 0.25/0.75 `l_B` by interpolation — G4's treatment of the same outline. DATCOM's `ZU/ZL` cases convert as `height = ZU − ZL` in the G1 literals; the trapezoid is stated in-band | Add per-station upper/lower profile inputs on the hop. Rejected: pre-empts M4-19's design |
| **L-7.13** [R3] | **`Re_l` from TAS and local viscosity** via a new `atmosphere.py` owner (ISA T + Sutherland); **top-of-chart `K_Rl` follows `datcom.f` literally** (closed form, whatever it does past figure 5.2.3.1-9's plotted range — deviating would break G1) | EAS + sea-level `ν` shortcut with a stated bound (a few % on `K_Rl` at 20 kft only) |
| **L-7.14** [R3] | **Follow the Fortran wherever the scratch method and `datcom.f` differ** — `CL_α,B` in particular is whatever `datcom.f` computes for `CLAB`, settled by G1 on `ex1`, not the note's `2·S_base/S_ref` guess | Keep the slender-body value; rejected because it is a second opinion of the oracle |
| **L-7.15** [R3] | **`cy_beta`/`cn_beta` stored per degree** — matches `FuselageMomentInput.d_cm_dalpha` and DATCOM's printout, so oracle literals enter untransformed; §7's per-radian tables are re-expressed at implementation | Per radian (matches the note's tables only) |
| **L-7.16** [R3] | **Two stamped wordings**, both pinned in `test_methods_stamp.py`: *off* — "not applied (`enabled=False`); estimated on this fixture `Cy_β`=…, `Cn_β`=…; enabling raises `\|n_y\|` and lowers `\|ψ̈\|`"; *on* — "applied about the reference CG; net `Cn_β`=… (stable, margin …)" | One wording regardless of flag — untrue in one of the two states |
| **L-7.17** [R3] | **One lumped side force at the body side-area centroid**, labelled in-band as lumping the wing-dihedral share (the M4-19 seam) | Split body share (body centroid) / wing share (wing AC) now. Rejected: pre-empts the distributed step without its cross-flow term |

## 10. Open items

1. **The `n_y` direction defect (§1) is filed separately** and should be
   corrected whether or not this step is worked — it is wrong text in a shipped
   deliverable, and the fix is one sentence in three places.
2. **`ga6_normal` body outline.** Not an isolated fixture edit: ga6's fin root
   waterline comes from the `fuselage-top` fallback `root_waterline_z +
   fuselage_height/2` = **78.5 in** today (`tail_geometry.fin_root_waterline`,
   `assumed=True`), so entering a real body height moves the fin root by ~`H/2`
   and changes the roll arm of every fin load on the Appendix A fixture. It also
   feeds `tail_span`'s h-tail attachment `fuselage_width` — backlog **Pri 1**, the fixture-data pass (#9) —
   and `configuration`'s `h_tail_z`. No oracle is at risk; a digest wave is.
   **Recommended sequence:** (i) enter `vtail_root_waterline_z = 78.5`
   explicitly, a zero-movement change that pins today's assumed value as a stated
   one; (ii) add the outline merged with Pri 10, with its own digest wave;
   (iii) then implement L-7. Without (i), L-7's digest wave is un-attributable.
   The RJ is unaffected either way — its fin root comes from the T-tail branch.
   **Status 2026-08-17: (i) and (ii) shipped** in the fixture-data pass
   (`changes/fixture-data-pass.changed.md`): `vtail_root_waterline_z = 78.5`
   entered (zero movement) and the Appendix A outline entered (26.522 ft ×
   3.833 ft, height 68.7 in from the printed 17.231 sq ft frontal area as an
   ellipse) — so §7's "other lateral fixture cannot exercise this at all" no
   longer holds, and the step lands on **both** lateral fixtures.
3. **`K_Rl` at the top of its chart.** `Re_l = 1.8e8` gives `K_Rl = 2.07`, at or
   just past figure 5.2.3.1-9's tabulated range. **Resolved [R3]: L-7.13** —
   TAS + local viscosity via `atmosphere.py`; follow `datcom.f` past the chart.
   AFFDL-TR-79-3032 Vol II still worth sourcing for the citation.
4. **`CL_α,B` for the `Cy_β` term.** Taken here as the slender-body base-area
   value `2·S_base/S_ref`. **Resolved [R3]: L-7.14** — follow the Fortran; G1
   on `ex1` settles it.
5. **[R3] Left for implementation, not decisions:** the ga6 numbers for §7's
   tables and G3/G4/G5 expectations (the outline now exists); the `K_N`
   nonlinearity bound for L-7.9; confirmation in `datcom.f` that `SBS` is the
   trapezoid on `ZU − ZL` (L-7.12).

## 11. What moves, and closure

**Moves:** with the feature enabled — the `sbeam/balanced_deck`, `csv/balance`
and `txt/balance` digests on `concept_regional_jet` only, through both the
yaw-relief and the lateral-relief inertia cards. With it disabled — nothing, and
G8 is the guard. Independently of the flag: the methods stamp and the case notes,
because `LATERAL_AERO_NOTE` is replaced.

**Tier L** closure (`CLAUDE.md`): `CHANGELOG.md` + backlog removal + full step
format in `docs/40_history/00_completed_development.md`, plus
`PROGRAM_SPEC.md` (balance + select), `CONVENTIONS.md` §1 (the L-7 bullet,
including the §1 direction correction), `docs/20_theory/balanced_cases.md`
(method + the §7 worked example), `docs/20_theory/00_theory_sources.md` (DATCOM
5.2.3.1 / 5.2.1.1 and Digital DATCOM rows), `reference/fuselage_pitching_moment.md`
(its "deliberate omissions" section currently names the lateral axis as out of
scope) and `DATA_DICTIONARY.md` via its generator. Effort **M**.
