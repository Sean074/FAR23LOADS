# Design note — CONM2 distributed-mass export per payload case

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Raised:** 2026-08-08 (user), to enable the balanced-airframe work by giving
sbeam an **independent** mass model against which sloads' inertia loads can be
checked. **Status: SHIPPED — C1–C5 and C7 2026-08-08, C6 with the round-trip harness** — see the history entry
"CONM2 distributed-mass export" in
[`11_completed_development_to_0.5.0.md`](11_completed_development_to_0.5.0.md).
**C6's solver-side gate shipped with the step-2 round-trip harness**
(`tests/test_sbeam_roundtrip.py` M-a…M-c: sbeam accelerates the exported
`CONM2` set and reproduces sloads' inertia-only set) — **status: SHIPPED,
C1–C7 complete** (status corrected 2026-08-17, backlog review BR-12; the plan
rolls to `40_history/` at the 0.7.0 cut). **Closure tier:** L — new export artifact,
a new unit channel member, GUI + CLI surface, and a new CI gate.

> **Corrections applied while implementing** (the plan text below is left as
> written, as the record of what was agreed):
>
> 1. **C-1's premise does not hold.** "Per-case itemization is derived from
>    WTENV's ballast machinery … reproduces CG1–CG4 with no new user input"
>    is true for `ga6_normal` and **no other fixture**: the reference aircraft's
>    `cg_cases` are free-standing CG-envelope corners, not WTENV's structural
>    points (RJ's sit at 619/599/595 in against WTENV's 594/574/569). Targeting
>    the cases through WTENV's forward-loading *sequence* derives 6 of 18 cases.
>    The derivation therefore searches **discretionary subsets** (any combination
>    aboard, not the station-sorted prefix) and targets each `cg_case` directly.
> 2. **A credibility gate was added** (user, 2026-08-08). The subset search
>    reaches 16 of 18, but six need ballast worth 12–31 % of the airplane, which
>    is a fiction — and C-2's whole point is that the CONM2 set is *independent*,
>    which it is not if it contains invented mass. Cases over a 10 % ballast
>    fraction (or whose solved ballast waterline sits outside the airframe) are
>    reported, not exported: **7 of 18**, including all four ga6 cases.
> 3. **Acceptance 1 is weaker than it reads.** "Each derived case reproduces its
>    `cg_cases` weight, xcg and zcg within a stated tolerance" is *exact by
>    construction* wherever a ballast row exists, because the ballast is solved
>    from those three numbers. The real content of the step is elsewhere — in the
>    gate, and in acceptance 3.
> 4. **C-5's Imperial factor is not 1.0**, and cannot be: the canonical stored
>    quantity is a pound of *force*. The mass channel is documented as the one
>    exemption from the all-1.0 identity, with its own `is_mass_consistent`
>    property rather than an extension of `is_consistent` (so no existing caller
>    of the latter changes behaviour).
> 5. **Wing items attach to the fuselage beam**, not to left/right wing bands:
>    those arrive with plan 11 **B5**. Mass, CG and inertia are exact regardless
>    (the CONM2 offsets carry the true position), and the deck header says so.
>
> One defect was found *by* the work, by running sbeam's own grid-point-weight
> generator over the exported deck: an overlay `CONM2` that no `MASSSET` names is
> **baseline** to sbeam, so it is counted in every case. See the history entry.

Related: [`11_balanced_airframe_cases_plan.md`](../30_future/11_balanced_airframe_cases_plan.md)
(shares the mass SSOT; step B1 there is a hard dependency),
[`10_sbeam_roundtrip_ci_harness_plan.md`](17_sbeam_roundtrip_ci_harness_plan.md)
(the solver gate this rides on). Conventions:
[`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md).

---

## 1. The idea, and why it is worth building

sloads' `FORCE`/`MOMENT` export is the **total** applied load — aero **plus**
inertia — and stays that way (user, 2026-08-08). That total is self-sufficient
and is the deliverable. But it is also *self-consistent by construction*: the
inertia half is computed by the same code that writes the cards, so nothing
outside sloads can contradict it.

Exporting the mass distribution as `CONM2` cards breaks that circularity.
sbeam can then apply the case acceleration to an **independently parsed** mass
model, recover the nodal inertia loads itself, and compare. That is a genuine
external check on the half of the load set that has no printed oracle — and it
is precisely the class of error the balanced-airframe baseline turned up (a
427 lb discrepancy between `weight.items` and `fuselage_mass.stations`, plan 11
§1.3).

## 2. What exists today

**sbeam is ready.** Its parser handles `CONM2` with the full tensor
(`eid, gid, cid, m, x1, x2, x3, i11, i21, i22, i31, i32, i33`,
`sbeam/model/mass.py:30`) and — more usefully — it implements **`MASSSET`**, a
card that adds / deletes / replaces sets of CONM2s per subcase, with a
duplicate-reference guard. That is purpose-built for one mass configuration per
payload case in a single deck.

**sloads has one itemization, but four payload cases.**

| | weight | xcg | itemized? | WTENV source |
|---|---|---|---|---|
| CG1 | 3400 | 85.10 | ≈ yes | aft gross, 78 lb ballast @ 103.7 |
| CG2 | 3400 | 77.49 | no | fwd gross, 418 lb ballast |
| CG3 | 2800 | 72.64 | no | fwd regardless, 158 lb ballast |
| CG4 | 2063 | 73.09 | no | minimum flight weight |

`flight_loads.cg_cases` defines all four and the whole V-n envelope runs on them
(`CaseRef.cg`). `weight.items` (24 items) yields exactly **one** loading —
3400 lb @ cg_x 85.00 — and `weight_onecg.build_mass`'s own docstring concedes
the point: *"the full per-CG-loading set … is a later refinement."* So three of
the four payload cases have no item list to turn into CONM2 cards.

They are, however, **derivable**: `weight_envelope` already computes each
structural limit's reference loading (which discretionary items are aboard) and
the ballast weight and station, and its Appendix A figures (78 / 418 / 158 lb)
are oracle-checked.

**A units gap.** `DeliverableUnits` carries force / length / moment / torque /
pressure and **no mass**. `CONM2`'s `M` is mass, not weight, and the item
inertias in `weight.items` are lb-in² — a *weight* basis.

### 2.1 The acceleration mechanism, verified (2026-08-08 critical review)

The check's mechanism is sbeam's **`GRAV` card**: selected by LOAD SID like any
load, assembled as `f = scale · M_global · a_field`
(`sbeam/assembly/load_vector.py::_apply_grav_to_vector`), so a mass-check
subcase is `MASSSET` + one `GRAV` carrying the case's `n·g` vector. Verified
limitation: **sbeam has no `RFORCE`** — `GRAV` is a uniform translational
acceleration field, so **rotational inertia terms** (`θ̈` pitch, `ψ̈` yaw —
plan 11 decisions B-3/B-8, M4-21) **cannot be recovered by sbeam from the
CONM2 set.** The C6 comparison gate is therefore scoped to the translational
terms (`n_z`, and `n_y` when the lateral cases land); rotational-acceleration
inertia stays checked by sloads-side closure only, until/unless sbeam grows an
`RFORCE`. State this scope in the gate and in the mass-check deck's `$` header.

**Full-span consequence (plan 11 decision B-5):** the CONM2 fragment is a
**full-airplane** mass model — wing (and tail) item weights split per side onto
the left/right GID bands, fuselage items on the body band — so the assembled
free-free deck and the mass deck share one geometry. `MassItemKind`
(EMPTY / MINIMUM / DISCRETIONARY, `models/enums.py`) is the existing partition
C1's WTENV derivation keys on; the new `component` tag (plan 11 §3.1) is
orthogonal to it.

## 3. Agreed decisions

| # | Decision | Rationale |
|---|---|---|
| C-1 | **Per-case itemization is derived from WTENV's ballast machinery**: base items, minus the discretionary items that loading drops, plus a computed ballast item | §2 — the machinery and its oracle already exist. Reproduces CG1–CG4 with no new user input and no fixture data entry |
| C-2 | **The check is an inertia-load comparison.** sbeam applies the case acceleration to the CONM2 set and recovers nodal inertia loads; **sloads additionally emits its own inertia contribution as a separate, clearly-marked load set** for comparison. The total `FORCE`/`MOMENT` set remains the deliverable and is unchanged | A properties-only check passes when a mass is in the wrong place with the right total. The distribution is the thing under test |
| C-3 | **One deck, one `MASSSET` per payload case**; each `CONM2` attaches to a **beam `GRID`** via plan 11's item→station map, with `x1/x2/x3` carrying the offset to the item's true CG | No new grids, no RBE plumbing, no dense solve path — and the offset fields keep each item at its exact CG, so nothing is approximated by the attachment |
| C-4 | **The Weights page emits both** a `CONM2`+`GRID` bulk-data fragment (pasteable into any model) **and** a self-contained runnable mass-check deck; **`cli.py` gains `--export-conm2`** | A GUI-only artifact cannot be gated in CI, and continuous gating is the mission's standard |
| C-5 | **`DeliverableUnits` gains `mass` and `mass_inertia` on the SOLVER channel** — lbf·s²/in (g = 386.088 in/s²) Imperial, tonne (g = 9806.65 mm/s²) for N·mm — with an arithmetic drift guard alongside the existing `moment == force × length` one | `CLAUDE.md` practice 3. The units history is the cautionary precedent; a mass channel invented at a call site is exactly the failure mode |
| C-6 | **Double-counting inertia is made structurally impossible**, not warned about | The total `FORCE`/`MOMENT` cards already contain inertia. A deck that applies those *and* accelerates the CONM2 masses counts it twice. The mass-check deck therefore carries **no** `FORCE`/`MOMENT` load cards at all, and a guard test asserts the two never appear in one subcase |

## 4. Steps

| Step | Scope | Tier | Effort |
|---|---|---|---|
| ~~**C1**~~ ✅ | Per-case itemization derived from WTENV (C-1): `weight_envelope` exposes each loading's item list + ballast item; validator that each derived case reproduces its `flight_loads.cg_cases` weight/xcg/zcg within tolerance. **ga6 CG1 must come out at 3400 @ 85.10 against the itemized 85.00** — the documented rounding, so the tolerance is set deliberately, not fitted. | L | M (~1) |
| ~~**C2**~~ ✅ | `DeliverableUnits.mass` / `.mass_inertia` on the SOLVER channel + the arithmetic drift guard (C-5). | M | S (~0.5) |
| ~~**C3**~~ ✅ | `sloads/export/mass_cards.py`: `CONM2` + `MASSSET` writer, attaching via plan 11's item→station map with CG offsets (C-3). GID/EID band added to the disjointness guard. | L | M (~1) |
| ~~**C4**~~ ✅ | Inertia-only load set alongside the total in the export (C-2), clearly marked in its `$` header as **not** to be applied with the total set. | M | S–M (~0.5) |
| ~~**C5**~~ ✅ | Weights page download (fragment + runnable deck) and `cli.py --export-conm2` (C-4). | M | S–M (~0.5) |
| **C6** (blocked on step 2; sloads-side half shipped) | CI gates: derived-case properties reconcile to `cg_cases`; sbeam-recovered inertia loads match sloads' inertia-only set within tolerance; **double-count guard test** (C-6). Rides on plan 10's harness. | L | M (~1) |
| ~~**C7**~~ ✅ | Closure trail: `CONVENTIONS.md` (mass units + the no-double-count rule), `PROGRAM_SPEC.md`, `PROJECT_GUIDE.md`, `DATA_DICTIONARY.md` regen, `theory_sources.md`, CHANGELOG, history. | S | S (~0.5) |

**Dependency:** C3 needs plan 11 **B1** (`mass_distribution.py`, the item→station
map). Land B1 first, or C3 will hand-roll a second mapping — the exact
duplication `CLAUDE.md` practice 3 exists to prevent.

## 5. Acceptance

1. Each derived payload case reproduces its `flight_loads.cg_cases` weight, xcg
   and zcg within a stated tolerance, on every fixture that has a weight
   database.
2. The CONM2 set for each case sums to that case's weight, CG and Iyy.
3. sbeam, given the mass deck and the case acceleration, recovers nodal inertia
   loads matching sloads' inertia-only set within tolerance — **the point of the
   whole step**.
4. `u.mass` and `u.mass_inertia` satisfy their dimensional identities in both
   unit systems.
5. No subcase anywhere applies both the total `FORCE`/`MOMENT` set and an
   accelerated CONM2 set (guard test).
6. Appendix A oracles unchanged; existing decks byte-unchanged — this is
   additive.

## 6. Risks

| # | Item | Notes |
|---|---|---|
| R1 | The derived CG2/CG3/CG4 itemizations are **new numbers with no printed oracle** — Appendix A prints the ballast weights, not per-case item lists | Acceptance 1 (reconcile to `cg_cases`, which *are* oracle-backed) is the substitute gate. State it as a closure gate in `theory_sources.md`, per `CLAUDE.md` practice 2 |
| R2 | Item inertias are lb-in² about the item's own axes, and `MassItem` carries no products of inertia (`ixy`, `iyz`) | CONM2's `i21`/`i31`/`i32` are emitted as 0 with an explicit `$` note. Correct for the laterally symmetric case the suite assumes; document rather than silently zero |
| R3 | Double-count (C-6) is the one error here that produces a *plausible* wrong answer — inertia at 2× reads as a heavier airplane, not as a crash | Hence the structural guard rather than a warning, and hence the mass-check deck carrying no load cards at all |
| R4 | The item→station map moves masses onto the beam axis | CONM2 offsets (C-3) preserve the true CG exactly, so this is presentational, not numerical. Verify with acceptance 2 (Iyy, which is offset-sensitive) |
