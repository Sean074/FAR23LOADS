# Step 10 — ground/landing cases: design note

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: COMPLETE — all three pieces shipped (2026-08-14, 2026-08-14,
2026-08-15).** Kept as the design note of record; the closure trail is in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md). Backlog: [`00_backlog.md`](00_backlog.md) priority 1
(M4-6, step 10) and priority 2 (plan 11 B8b, step 11). Conventions:
[`../10_standard/CONVENTIONS.md`](../10_standard/CONVENTIONS.md). Balancing
physics: [`../20_theory/balanced_cases.md`](../20_theory/balanced_cases.md) and
[`11_balanced_airframe_cases_plan.md`](11_balanced_airframe_cases_plan.md).

**Scope note (decision D-24, 2026-08-14):** pressurization is **out of scope**
for sloads. This step is the ground/landing distributed loads and the gear
reactions alone.

---

## 1. What is already in place

- **All 33 LANDLOAD ground conditions ship** (M4-17e), each with per-wheel
  V/D/S/R, the **airplane-datum** reactions `vm/dm/vn/dn` (computed, never yet
  surfaced — `PROGRAM_SPEC.md` calls them "an M4-6 hook"), the unbalanced
  pitch/roll/yaw moments about the CG, and the ground-line inertia factors
  NVP/NDP/NS.
- **Case identity is minted** — `LG-01…LG-33` with a `CaseRef` each, and the ids
  already map into every deck band: `LG-07` → component SID 607
  (band `subcase-LG`), assembled SID 5607, handed 7607/8607. Nothing needs
  renumbering.
- **Gear geometry is single-sourced** on `geometry.landing_gear` (step G6b) —
  axle `(x, z)` at three strut states, rolling radius, strut type, `tread_in` —
  on five of six fixtures (`concept_heavy` has neither gear geometry nor a
  `landing` slice).
- **Gear mass is in `weight.items`** on every fixture (ga6: wheel + structure at
  x = 97 main, x = 1 nose).
- **The six-DOF closure, handedness/reflection, offset couples, CONM2 and the
  round-trip CI harness are shipped and verified in the real solver** — none of
  that machinery knows or cares that its loads have been aerodynamic so far.

## 2. Decisions of record

### G-1 — Ground cases are born in the **assembled free-free deck**, not the per-component body deck *(user, 2026-08-14)*

A ground case is assembled as a balanced case: gear reactions and the wing lift
fraction applied, inertia from the mass model, closed by the shipped six-DOF
residual machinery, with the deck's determinate-support reaction as the
equilibrium proof. The per-component fuselage deck **stays flight-only**.

*Why.* The per-component body deck is planar by construction —
`sbeam_bridge._shared_grid_block` puts every fuselage `GRID` at `y = z = 0`
("the component's beam line in isolation, not its position on the airplane"),
`body_force_moment_cards` emits `Fz` only, and `body_loads._integrate` carries
`fz → sz → myy`. A ground case is irreducibly three-dimensional, and not
marginally: on `ga6_normal`, braked roll (case 16) is 2,261 lb vertical against
**1,809 lb drag** per wheel, and the side family (case 19) 2,261 lb against
**−1,700 lb side** — applied at the contact patch, ~41 in below the fuselage
beam line and ±57 in off the centreline. Those lever arms *are* the load case.
Building that in a **view** first and in the primary deliverable second is
backwards under the 2026-08-08 mission extension, and the view's output would be
superseded the moment the assembled case landed.

*Consequences accepted.*
1. The `flight-only-body-deck` standing limitation is **reworded, not retired**:
   ground cases exist, in the assembled deck; the per-component fuselage deck
   remains flight-only. (Its current wording — "no ground case is assembled into
   a balanced free-free case" — becomes false and must change in this step.)
2. `tests/test_export_equilibrium.py::test_body_deck_closes_in_force_and_moment`
   keeps its four zero-by-construction components; the comment predicting that
   ground cases would turn it red is **amended**, because they no longer land
   there.
3. Backlog rows 1 and 2 largely merge: step 11 (B8b) is no longer a separate
   build on top of step 10.
4. A consumer working from per-component decks gets no ground case. A
   ground-case body **view**, projected from the assembled case, is filed as a
   separate later item rather than built here.

### G-2 — The gear's load application point is an **explicit input**, with an explicit **carrier** *(user, 2026-08-14)*

`LandingGearInput` gains, per leg:

- `carrier: GearCarrier` — `BODY` | `WING`. **No default**; a project that
  exports ground cases without it **raises** (the suite's existing
  refuse-rather-than-fall-back habit, as `control_load_mode = "discrete"` does
  without hinge geometry).
- `attach: (x, y, z)` — the airframe attachment/trunnion node in airplane
  coordinates. **This is also the "gear reference point" of G-12** — one point,
  named once, serving both the airframe transfer and the gear report. A separate
  gear datum would mean two transfers and two lever arms to keep straight for no
  gain.

LANDLOAD computes the reaction at the tyre contact patch exactly as today; the
export transfers it to `attach` with the lever-arm couple (the plan-14
concentrated-mass offset-couple pattern, already verified against NETLOADS shear
*and* bending in the real solver), through `export/coordinates.py`. Where
`carrier == WING`, `attach` is additionally resolved onto the wing **loads
reference axis** via `net_loads.to_loads_ref_axis`, so a gear torsion is stated
about the same axis as every other wing torsion and the `torsion_axis` stamp
stays true.

*Why an input rather than an inference.* Wing-mounted main gear is most
transports, and body-carried and wing-carried gear are different load paths, not
different labels: a wing-carried reaction **relieves or reverses inboard wing
bending** (an up-load at a butt line, opposite in sense to flight) and only
reaches the fuselage through the carry-through. Applying it to the body beam
over-loads the fuselage *and* hides a real wing sizing case — wrong in both
directions at once. The same "explicit, not inferred" argument already settled
`MassComponent` (plan 11 §3.1; every fixture's items are centreline lumps, so
geometry carries no side information). The derived alternative is worse than it
looks: `±tread/2` is a **wheel** dimension, and the axle butt line is not the
trunnion butt line.

*Deliberately deferred.* A user-named **GID** for the application node (rather
than a coordinate) belongs with **step 12**, the LRA beam-model import, which
owns GID authority — "loads are transferred onto the imported nodes under the
imported GIDs". Gear is the strongest case for it, but two mechanisms for naming
a node would then need reconciling. For now the node comes from a new registered
band in `export/bands.py`.

*Guards that this decision owes* (required practice 3 — a convention gets a code
owner **and** a drift guard, not prose):
1. **carrier ↔ mass agreement.** A leg with `carrier = WING` whose gear mass
   items are tagged `MassComponent.FUSELAGE` is a contradiction — the same
   structure carrying the load but not the weight. This fires on
   `dhc8_dash8` today (main gear in wing-mounted nacelles, mass tagged
   `fuselage`), which is the point of writing it.
2. **`attach` plausibility.** `WING`: between the side of body and the tip, and
   inside the planform chordwise. `BODY`: inside the fuselage envelope. Loud
   failure, in the style of the T1 planform validator.
3. **the transfer preserves resultants.** The reaction set about the airplane CG
   is identical before and after the transfer to `attach` — the plan-07
   invariant re-run. A property of the construction, so it is gated exactly
   (`rel_tol 1e-12`), not to a tolerance.

*Fixture data owed:* five airplanes × two legs. `ga6_normal` and `cessna_210`
are body gear (their existing mass tags are right); **`dhc8_dash8` is the wing
case** and becomes the fixture that proves the wing path — its gear mass tag
needs correcting in the same change, with `mass_distribution.wing_mass_tie`
re-pinned. `atr42_100` (sponson) and `concept_regional_jet` (wing-body junction)
are judgement calls to be stated in the fixture, not guessed quietly.

*Regulatory support (added 2026-08-14 from the User Guide's CFR quotations).*
**23.485(d):** "The side loads prescribed in paragraph c. of this section are
assumed to be applied at the **ground contact point** and the drag loads may be
assumed to be zero." The reaction is therefore computed where LANDLOAD computes
it, and the transfer to `attach` is ours — which is exactly what the
resultant-preserving guard exists to police.

*Consequence:* ga6's and dhc8's ground cases become genuinely different physics,
so **the closure gate is stated per carrier**. That is a feature: a wing-carried
ground case that closes globally while putting nothing on the wing beam is a
defect the assembled residual alone would never catch.

### G-3 — One user-owned weight/CG case list, each case tagged with the **analyses** it is run for *(user, 2026-08-14)*

**D4a is option A, extended by the user:** rather than the derivation reading one
hard-coded list per analysis, the user enters **all** weight & CG cases once and
states, per case, **which analysis each is run for**. The analysis kinds are
**`FLIGHT`** and **`GROUND`** for now, and the field is deliberately shaped as a
set so kinds can be added later (taxi, towing, jacking, gust-on-ground …)
without another schema fight.

`derive_case_loadings` is generalized to take any `CgCase` list; each analysis
asks it for the cases tagged for that analysis. The `derivable` gate and the
`SkippedCondition` record are unchanged — a ground case whose loading the weight
database cannot produce is **skipped and recorded**, never invented, exactly as a
flight case is.

**Half of this already exists, which is why it is affordable.**
`WeightInput.cg_cases` has been "the shared list of named loading scenarios"
since **v19 (Step D5)**: entered once on the Weight/CG Grid & Payload Cases page,
overlaid on the WTENV chart, and **merged into `FlightLoadsInput.cg_cases` by the
Flight Envelope page** so the two cannot diverge. `flight_loads.cg_cases` is
therefore already a derived copy of the shared list. What is missing is (a) the
per-case analysis tag and (b) `landing.cg_cases`, the one case list that never
joined the SSOT — it is still entered separately on the Landing Loads page and
read straight by `landing.py`.

**Measured, on the shipped fixtures** (2026-08-14) — the landing cases are the
flight CG stations at the reduced landing weight, so the two lists are siblings,
not strangers: ga6 `aft max landing` 3,230 lb @ **85.10** against `CG1` 3,400 lb
@ **85.10**; `fwd light` 2,803 lb @ **72.64** against `CG3` 2,800 lb @ **72.64**;
the RJ's aft and fwd landing cases sit on `CG1`/`CG2`'s stations to the
hundredth. Running the existing derivation against the landing cases:
`ga6_normal` **3/3** derivable (78 / 248 / 161 lb of ballast, 2.4–8.9 %),
`concept_regional_jet` **2/3**, and `cessna_210` / `atr42_100` / `dhc8_dash8`
**0/3** — the same fixtures, and the same root cause, as the already-pinned
"payload cases are not loadings the weight database can produce" item. Ground
cases **inherit** that limitation; they do not create one, and they do not wait
on it.

**Sub-decisions, answered by the user 2026-08-14:**

**G-3a — LANDLOAD is fed by an explicit `role`, not by the tag and not by
position.** `CgCase` gains an optional `role: GroundCaseRole`
(`AFT_MAX_LANDING` | `FWD_MAX_LANDING` | `FWD_LIGHT`). LANDLOAD consumes the
three `GROUND` cases that carry roles, **in role order**; any further
`GROUND`-tagged case (a ramp loading, a second fuel state) is assembled and
distributed but never fed to LANDLOAD, so the tag is free to grow while the
oracle-locked module keeps its exact three-loading contract.

*Why this rather than "the tag is the contract".* LANDLOAD indexes its three
loadings **positionally** (`wl[19] = wcg[0]*wr`, and so on) and today recovers
the order by **matching names** against `validation.LANDING_CG_NAMES`, falling
back to entry order with a warning when they don't match. That is a latent trap
— a renamed case silently reorders the reaction table — and it is oracle-locked
to Appendix A p230, so it is exactly the kind of contract that should be a field
rather than a convention. An explicit role retires both the positional contract
and the name matching in one change, and lifts the three-case ceiling for
everything downstream of LANDLOAD.

**G-3b — both derived lists are retired, with a migration.**
`FlightLoadsInput.cg_cases` and `LandingInput.cg_cases` are **removed**
(`SCHEMA_VERSION` hop; older files still load). The migration tags existing
`weight.cg_cases` as `FLIGHT`, and folds `landing.cg_cases` into the shared list
as `GROUND` with roles assigned from the canonical names — which every shipped
fixture carries, and which `validation` already warns about when absent. Where a
landing case matches an existing shared case in name *and* in
`(weight_lb, xcg, zcg)`, the tags **merge onto the one case** rather than
duplicating it. This is the **G6b precedent** (single-source geometry; the
duplicated coarse `LayoutInput` gear fields retired), deliberately not the
`tail_loads` proxy precedent: a proxy would leave a second way to say the same
thing, which is what this decision exists to remove.

**G-3c — `analyses` is a set.** One case may be run for several analyses
(`[FLIGHT, GROUND]`) rather than being entered twice under two names and drifting
apart. An **empty** set is rejected by validation — a case that is run for
nothing is an entry error, not a state.

**Consequent contract, single-owned + drift-guarded** (practice 3):

- One resolver owns "the cases for analysis X" — every consumer
  (`build_envelope`/SELECT, `balance`, `mass_cards`, `wing_inertia`, `landing`)
  reads it, none filters for itself.
- **Oracle guard:** the landing module's output is unchanged on every fixture
  (Appendix A p236 `V/N/NLG`, p230 `K`/`GAMMA` and the AP-BP-DP-CP table) —
  bit-for-bit, since this is a plumbing change.
- **Migration guard:** the `FLIGHT`-tagged set after migration equals today's
  `flight_loads.cg_cases` exactly, per fixture, pinned.
- **Role guard:** among `GROUND` cases, exactly one of each role when the landing
  module runs; a `role` on a case not tagged `GROUND` is rejected.
- GUI: the Weight/CG page's **Payload Cases** tab gains the `analyses` and
  `role` columns and becomes the sole editor; the Landing Loads page's CG table
  becomes a read-only view of the three roled cases.

### G-4 — Max landing weight is a **user input on `WeightInput`**, and it is the single owner of the landing weight *(user, 2026-08-14)*

`WeightInput.max_landing_weight_lb` (moved off `LandingInput`, which keeps the
rest of its LGFACTOR scalars and reads MLW through a resolver, exactly as it
already reads gear geometry off `geometry.landing_gear`). It sits beside
`items`, `envelope` and the shared case list — where the estimate's own inputs
live, and where **MZFW** will need to go for F25-1.

**MLW is the SSOT for the landing weight.** The `AFT_MAX_LANDING` and
`FWD_MAX_LANDING` roled cases take their weight *from* MLW; only their CG station
is entered. A roled max-landing case whose weight disagrees with MLW is an
**error**, not a warning — it is one number, and it is a certified airplane-level
limit rather than a property of a loading.

**A derived estimate the user confirms, plus a floor check.** The estimate is
`OEW + max payload + reserve fuel`, computable from the item database today:
`Σ EMPTY` + `Σ MINIMUM` (crew + reserve fuel on every fixture) + `Σ DISCRETIONARY`
excluding consumable mission fuel (per **G-5**) and excluding ballast rows. The
GUI **offers** it for acceptance; it is never written silently, and the calc
**never falls back** to it (the suite's refuse-rather-than-fall-back habit —
`landing` already raises on missing `cg_cases`).

Measured on the shipped fixtures (2026-08-14), which is why the estimate is a
**floor** and not a prediction:

| fixture | OEW + max payload + reserve | entered MLW | MLW / MTOW |
|---|---|---|---|
| `ga6_normal` | 2,913 | 3,230 | 0.950 |
| `cessna_210` | 3,444 | 3,800 | 1.000 |
| `atr42_100` | 28,607 | 35,000 | 0.926 |
| `dhc8_dash8` | 29,840 | 32,800 | 0.951 |
| `concept_regional_jet` | 31,360 | **31,000** | 0.891 |

Entered MLW sits **above** the estimate on four fixtures — you land with more
than reserves, which is normal — and **below** it on `concept_regional_jet`,
which therefore *cannot land at MLW with full payload and reserve fuel*. That is
a real finding about that fixture, and it is what the floor check exists to
surface: **validation flags `MLW < OEW + max payload + reserve fuel`**, and it
fires on the RJ today.

### G-5 — `MassItem.consumable`, and burn fuel down before dropping payload (D4b) *(user, 2026-08-14)*

`MassItem.consumable: bool = False`. When deriving a loading for a **`GROUND`**
target, consumable items may take a **continuous partial value** — solved for the
weight delta, proportional across them so a tank layout is preserved — *before*
any discretionary payload subset is dropped. The generic subset search remains
the fallback when burn-down alone cannot reach the case's CG.

*Why.* A design landing weight is fuel burned off (23.473(b)/(c)), not a
passenger left behind. Measured on ga6: to lose the 170 lb between MTOW 3,400 and
MLW 3,230 the least-ballast subset search **drops the 6th person** (x = 150, aft
cabin) and keeps the full 409 lb of fuel (x = 70) — the right weight with the mass
80 in out of place, and on a wing-fuel airplane it is worse than out of place,
because burning fuel removes wing inertia relief and dropping a passenger does
not. With burn-down, ga6's aft landing case is reached by burning **317 lb** and
lands **within 0.12 in** of its target CG.

*Default `False` is the acceptance test:* every flight case is unchanged to the
pound, and the Appendix-A oracles cannot move.

*Three consumers, one field:* this rule, **Pri 10** (wing-tank fuel separability
— the same rows must be identifiable), and **G-4**'s estimate, which has to tell
mission fuel from reserve fuel. Which rows are fuel becomes an **input**, not a
name match, on the same reasoning that made `MassComponent` explicit.

*Measured limit, stated so it is not over-claimed:* burn-down fixes the **weight**
half only. The twins' and the Cessna's landing CG targets are 9–34 in forward of
anything their databases can load — the already-pinned Pri 9 fixture-data
problem — so they still need ballast and still come out non-derivable. Coverage
after G-5 is unchanged from the G-3 table: ga6 3/3, RJ 2/3, the rest 0/3, each
skipped and recorded.

### G-6 — The **six-DOF solve** closes the ground case; LANDLOAD's factors are the independent **closed-form** gate *(user, 2026-08-14)*

Ground cases enter the same closure as every other balanced family
(`balance._closure` + `rigid_body`): applied gear reactions, the lift fraction
where it applies (**G-7**) and inertia from the mass model, with the rigid-body
acceleration field solved to drive ΣF and ΣM to zero and the deck's determinate
support recovering ≈ 0. No ground-specific balance path is written.

**This is what the regulation asks for, not merely a convenient reuse** (citation
added 2026-08-14). **23.471:** "The **limit** ground loads … are the external
loads and inertia forces that act upon an airplane structure. In each specified
ground load condition, the external reactions must be placed **in equilibrium
with the linear and angular inertia forces** in a rational or conservative
manner." A six-DOF rigid-body closure over the itemized mass model *is* that
sentence; the earlier justification ("no oracle exists, so a closure gate") was
weaker than the authority actually available.

**Why not consume `NVP`/`NDP`/`NS` directly.** They are translation only — the
rotational half sits unreacted in `PITCHP`/`ROLLP`/`YAWP` (ga6 case 4:
−168,057 lb-in of pitch; case 10: 231,147 lb-in of roll *and* −75,000 lb-in of
yaw), so an angular solve is needed regardless. And they are stated about the
**ground line**, rotated from body axes by `GRA`/`BETA` and differently for each
of the three attitudes — consuming them would put a frame rotation in the *load
path*, which is the splice class `export/coordinates.py` exists to close. Under
this decision the rotation appears only in the **check**, where an error is loud.

**The cross-check is this step's benchmark-first gate** (`CLAUDE.md`: an oracle
where one exists, else a stated closure/invariant gate written *with* the
feature). LANDLOAD reaches these numbers by a completely different route — lever
arms and FAR percentages, not a mass matrix — so the agreement is content-carrying
rather than self-referential. Measured on ga6 (2026-08-14), the factors are
**exact closed forms**, so the gate is written as an identity at solver noise,
not as a tolerance:

| family (cases) | `NVP` | `NDP` | `NS` |
|---|---|---|---|
| level 3-/2-wheel, tail-down (1–9) | `NLG + L` = 3.167 | `K·NLG` = 0.811 | 0 |
| one-wheel (10–12) | `½NLG + L` = 1.917 | `½K·NLG` = 0.406 | 0 |
| braked roll, nose clear (16–18) | 1.33 | `0.8 × 1.33` = 1.064 | 0 |
| side load (19–24) | 1.33 | 0 | ∓0.83 |

    n_z_solved == NVP,  n_x_solved == NDP,  n_y_solved == NS      (per family, exact)
    Iyy·θ̈_solved == PITCHP + L·W·(x_lift − x_cg)                  (closed form, see G-7)
    Ixx·φ̈_solved == ROLLP,   Izz·ψ̈_solved == YAWP

Where a factor has **no** closed form — the 3-wheel (1–3) and braked-nose-down
(13–15) families, whose `NVP` follows from the lever-arm reaction solve — the
gate asserts against LANDLOAD's **computed** value instead of a formula. Same
gate, different right-hand side.

The `Iyy·θ̈` line carries the lift-lever-arm term **explicitly**, so the one place
the assembled case deliberately departs from LANDLOAD is stated in the gate
rather than hidden in slack — and the gate goes red if G-7 is ever changed
without revisiting it.

**The 23.499 supplementary nose-wheel family (cases 25–33) is not assembled.** It
carries nose reactions only — no main-gear reaction exists in the family — so it
is a local gear-design case, not an airplane in equilibrium. It is **skipped with
a recorded reason** through the existing `SkippedCondition` path
(`local gear-design case, no airplane equilibrium`), so its absence from the
assembled deck is visible rather than silent. All 33 cases continue to ship in
full in the LIMIT/ULTIMATE case tables and the gear-reaction CSV, exactly as
today.

*(Amended 2026-08-14 by **G-12**: this family is not merely excluded, it has a
home. 25–33 are gear-design cases, and the gear load report is where they were
always aimed. The two artifacts carry **different case sets** by design — 24
assemble, 33 report.)*

*Coverage:* the gate runs on the fixtures that produce ground cases at all — ga6
(3/3 loadings) and `concept_regional_jet` (2/3) per G-3/G-5. ga6 is the fixture
to write it against: it is the Appendix-A airplane and its LANDLOAD output is the
printed p230/p236 oracle.

### G-7 — Lift on the wing for the **landing** families only; ground handling is gear + inertia *(user, 2026-08-14)*

**The split is the manual's own, and the assembled case honours it rather than
re-deciding it.** Verified in `landing.landing_reactions`: the `nvp` expression
includes the `lf*WL` term for cases **1–12** and omits it for **13–24**.

*And the regulation draws the same line* (citation added 2026-08-14).
**23.473(a):** the ground load requirements "must be complied with at the design
maximum weight, **except that FARs 23.479, 23.481, and 23.483 may be complied
with at a design landing weight**". 23.479/481/483 are exactly cases 1–12 — the
lift-carrying families — and 23.485/23.493 (13–24) are the gross-weight ones,
which is the source of LANDLOAD's `WR = GW/MLW` scaling. The family split, the
lift split and the weight split are one split, drawn by the rule.

- **Landing families (1–12)** — level 3-/2-wheel (23.479), tail-down (23.481),
  one-wheel (23.483): the wing carries lift `L × W_case` (`L = lift_factor`,
  ≤ 0.667 per 23.473), and the `FORCE`/`MOMENT` cards must contain it or the case
  cannot balance.
- **Ground-handling families (13–24)** — braked roll (23.493), side load
  (23.485): **no wing lift.** The gear loads are balanced by inertia alone. The
  wing still carries its **own** inertia at the case's load factor, so it is not
  load-free — it is lift-free.
- **23.499 (25–33):** not assembled (G-6).

**Shape: the AIRLOADS Schrenk spanwise distribution, scaled so each side's
half-span integral is `L·W_case/2`.** Only the *shape* is borrowed — the
magnitude is `L·W`, so no speed, CL or V-n point is needed and no new aero is
invented. This reuses the shipped, oracle-locked spanwise integrator and gives
the inboard wing genuine ground-case bending relief, which a lumped force cannot.

**Nothing trims the case.** Distributing the lift at the wing rather than netting
it at the CG (as LANDLOAD does, via `NLG = N − L`) leaves a pitching moment —
measured on ga6 at **1.26 %** (aft, `x_lift − x_cg` = −4.15 in) and **1.47 %**
(fwd, +4.83 in) of `n·W·MAC`, i.e. *above* the 1 % residual gate the flight
families use. It is reacted by **pitch acceleration alone**: an airplane at
touchdown is an accelerating body, not a trimmed one, and no balancing tail load
exists in Ch 20 to invent. The magnitude is a known closed form, which is why
G-6's gate states it rather than absorbing it.

*Consequence for the residual gate:* the 1 % flight-family ceiling is **not**
transferable to the landing families as-is; the ground residual is stated per
fixture and per family, as the lateral families already are
(`_PITCH_RESIDUAL_CEILING`, plan 11 R3's "state the floor per fixture").

*`L` stays a parameter, never a constant:* **F25-4** wants the `lift = W` variant
(and 10/6 fps), so the lift fraction is read from the input on every path.

#### G-7a — The lift acts along the **ground line**, not along the airplane z axis *(user, 2026-08-15)*

Raised by implementation: G-7 above says "each side's half-span integral is
`L·W_case/2`", which reads as a load along airplane `z`, while **G-6 promises its
`NVP`/`NDP` gate as an identity at solver noise**. The two cannot both hold.
LANDLOAD sums `lf*WL` into the **ground-line** vertical (`nvp = (2*VMP + VNP +
lf*WL)/WL`, all ground-line quantities), so a lift applied along airplane `z`
enters that sum short by `cos ρ` — measured on `ga6_normal`, 0.053 % of `NVP`
(0.00167 g). Small, and *not* solver noise: it would turn G-6's identity into a
tolerance on exactly the families the tolerance was supposed to prove.

**Decision: the lift vector lies along the ground-line vertical.** Per strip,

    fz = L_i · cos ρ      fx = L_i · sin ρ

where `ρ` is the case's own ground rotation (below). This is also the physics
rather than a convenience: lift is perpendicular to the flight path, the ground
line *is* the flight path at touchdown to within the ~5° descent angle, and the
airplane sits at attitude `ρ` to it. On `ga6_normal`'s level-landing families the
tilt puts **152 lb** of the 2,154 lb lift forward (−x), which is the lift vector
leaning ahead of vertical in a nose-up touchdown attitude — a real term, not a
correction.

*Consequence, stated because G-7's sentence must be read with it:* it is the
**resultant** whose half-span integral is `L·W/2`, not the `fz` column. The deck's
wing lift cards therefore carry an `fx` component on families 1–12, which no
other family in the suite does, and the case note says so.

**`ρ` has one definition and it is LANDLOAD's own**, not a re-derivation of the
ground angle:

    ρ = PHIM − atan2(DMP, VMP)

i.e. the angle between the airplane-datum resolution the manual already computes
and the ground-line pair it resolved. It comes out `−GRA(1)` for the level and
one-wheel families, `−GRA(3)` tail-down and `+GRA(2)` for braked roll and side —
including the sign inconsistency between attitudes 0 and 1 that is in
LANDLOAD.BAS itself. Taking `ρ` from the manual's own numbers rather than from
`GRA` means this step never has to adjudicate that inconsistency, and the same
rotation serves the deck (nothing) and the gate (everything). Verified against
G-12's two printed figures: ga6 case 1 drag 1,020 lb ground-line → 795 lb
airplane-datum, and the side family's 0 lb ground-line drag → 186 lb.

Both halves of G-6's translational gate are then exact:

    NVP == n_z·cos ρ + n_x·sin ρ        NDP == n_x·cos ρ − n_z·sin ρ

### G-8 — Handedness: **reflection stays the single owner**, and LANDLOAD's own twins become the operator's check *(user, 2026-08-14)*

**Which ground families are asymmetric** (measured in `landing.landing_reactions`):

| family | cases | handed? | evidence |
|---|---|---|---|
| level 3-/2-wheel | 1–6 | no | both mains equal; `ROLLP` = `YAWP` = 0 |
| tail-down | 7–9 | no | same |
| **one-wheel (23.483)** | 10–12 | **yes** | one main loaded: `ROLLP = VMP·TREAD/2`, `YAWP = −DMP·TREAD/2` |
| braked roll | 13–18 | no | symmetric pair |
| **side load (23.485)** | 19–24 | **yes** | `SMP` = −0.5·GW / +0.33·GW; `ROLLP = ±0.83·W·CP`, `YAWP = ±0.83·W·BP` |

**The two families are handed differently in the source, and this is the reason
the decision could not be a single global rule.** The 23.485 family's six cases
are three loadings × **two drift directions** — not three loadings × two wheels:
`sign = -1 if m % 2 else 1` flips `ROLLP`/`YAWP` between the odd and even member
of each pair, `NS = (SMP − SMP_partner)/W` is −0.83 for the odd case and +0.83
for the even one, and ga6's pair is `SMP −1700` (LT drift) / `+1122` (RT drift),
i.e. −0.5·GW and +0.33·GW of the same 3,400 lb. **LANDLOAD supplies both hands
here.** The 23.483 one-wheel family has no sign flip anywhere — cases 10–12 are
the three loadings, one hand each — so LANDLOAD supplies **neither** twin.

**Decision.** Assemble **one hand per physical condition** and generate the twin
with the existing assembly-level reflection operator (B-6, single-owned in
`export/coordinates.py`): the one-wheel case as given, the side case from the
**odd** member (19/21/23) with the partner wheel's 0.33·W filled in. LANDLOAD's
even members (20/22/24) are **not assembled**; they become an **independent
verification of the reflection operator** — reflect(19) must reproduce case 20's
`NS`, `ROLLP` and `YAWP` sign-flipped and equal.

*Why this rather than assembling LANDLOAD's two hands directly.* Two handedness
mechanisms inside one step is what B-6 exists to prevent, and the alternative
throws away the only **external** check the reflection operator will ever get:
every other reflection in the suite is guarded against itself. This is the same
shape as G-6 — compute by our route, verify against the manual's independent one.

**Sub-decision (identity) — LANDLOAD's ids are kept; the hand is a field, not a
suffix.** The side twin already *has* an id (`LG-20`), unlike every other
reflected case in the suite, so minting `LG-19L`/`LG-19R` beside it would put two
ids on one physical condition — which M4-2 decision 1 forbids. Therefore:

- side family: `LG-19` = port, `LG-20` = starboard (ids unchanged, `hand` set);
- one-wheel: `LG-10L` / `LG-10R`, since only `LG-10` exists;
- `case_ids.balanced_subcase_id` reads the case's **hand** rather than parsing
  the id suffix, so both routes land in the right SID block (`LG-19` → 8619
  port, `LG-20` → 7620 starboard, `LG-10L` → 8610). Contained change to one
  function; drift-guarded.

*Consequence, stated because it must travel:* for the ground family a case's hand
is no longer readable from its id alone, so the hand must appear in the deck `$`
header and the case row — which the balanced deck already does for every handed
pair.

**No change needed to `is_handed`.** Its third source — "a net rolling moment
made by the distribution itself", added for the 23.427(a) h-tail — already
catches the one-wheel case (all the vertical reaction at one `y`, *no* side force
at all, which a lateral-content-only predicate would have minted unhanded), and
its lateral test catches the side case.

**Implementation note (unavoidable under any option):** `GearReactionCase` carries
a **single** `smp`, while an assembled side case needs *both* wheels — 0.5·W on
one and 0.33·W on the other, acting the same way globally and summing to the
0.83·W that `NS` states. The assembler reads the partner case for the second
wheel rather than re-deriving the percentages.

### G-9 — Ground cases are a **separate governing family**, never auto-compared with flight, but **within reach of the engineer's filter** *(user, 2026-08-14)*

Two distinct things are called "down-selection" here, and they get different
answers:

1. **SELECT's physics pick** (`CriticalLoadSet.conditions` — the governing
   condition per component per FAR condition). Ground cases **do not** enter it
   and are **never** compared against flight cases for a maximum.
2. **The engineer's opt-out filter** (`CriticalLoadSet.selected_case_ids`, a
   display/export scope that "never changes what the load-producing modules
   compute"). Ground cases **are** brought within its reach:
   `filter_by_selected_case_ids` and the Critical Loads page are extended to
   `LG-` ids.

*Why no automatic comparison.* Flight and ground load different structure by
different paths, and the deliverable's value is naming **which** case governs —
a cross-family `max()` destroys exactly that.

*(Corrected 2026-08-14, after D9.* This decision was first argued partly on the
two families carrying different safety factors. **They do not** — both are limit
× 1.5, per G-10. The structural argument above is the whole reason, and it stands
on its own. The factor argument does return in a weaker form once **G-11**'s
table allows a per-case override: a `max()` over cases at different declared
factors is not a load, which is the defect class review finding **F-R1** closed
when it made every governing row scale by its own case's factor.)*

*Why filterable anyway.* Doing nothing would silently enrol the ground family in
the `export-case-filter` standing limitation ("their case identities are minted
separately from the governing set, so the filter cannot reach them") — `LG-` ids
are minted by `landing.py`, not by SELECT, so the filter misses them by default.
Up to 24 assembled ground cases plus twins is precisely the family an engineer
will want to scope. Extending the filter closes the gap instead of widening it.
*Fallback if that turns out not to be contained:* ship unfiltered and extend the
limitation's wording to name ground cases explicitly — never leave it unsaid.

*The separation is stated in the report*, so a reader cannot mistake the absence
of a comparison for an oversight: ground and flight are separate governing
families and the deliverable claims no single envelope over both. The wording
travels with **D9**'s answer, since "they carry different safety factors" is part
of the reason.

*Nothing changes inside the ground family:* LANDLOAD's existing per-FAR-family
critical pick (the six "critical reaction" summaries, ranked on the full
`√(V²+D²+S²)` magnitude since M4-17e) stands as-is.

*Filed as a follow-on, not built here:* a **combined station envelope** over
flight *and* ground — two-sided max/min per station, each extreme labelled with
the case id that produced it. That is what a consumer sizing a fuselage frame
actually wants, it keeps case identity rather than destroying it, and its natural
home is the `loads_plots` VMT envelope rather than this step. Backlog: *"Combined
flight + ground station envelope"*.

### G-10 — Every FAR ground case is **LIMIT × 1.5**; the classification is cited, not assumed *(user, 2026-08-14)*

Settled from the regulation text (`reference/ug.txt`, quoting the CFR verbatim),
not from the current default:

| source | wording | multiplier |
|---|---|---|
| **23.471** | "The **limit** ground loads specified …" | (the whole subpart) |
| **23.485(b)(c)** | "The **limit** vertical load factor must be 1.33 … The **limit** side inertia factor must be 0.83 … 0.5 (W) inboard on one side and 0.33 (W) outboard on the other" | 1.33, 0.83, 0.5/0.33 |
| **23.493(a)(c)** | "The **limit** vertical load factor must be 1.33 … drag reaction equal to the vertical reaction … multiplied by a coefficient of friction of 0.8" | 1.33, 0.8 |
| **23.499(a)(b)** | "the **limit** force components at the axle must be … **2.25** times the static load … 0.8 times the vertical … a forward component of 0.4" | 2.25, 0.8, 0.4 |

Every embedded multiplier is prescribed as a **limit** quantity, so ultimate =
limit × **1.5** (`reference/14CFR_factor_of_safety.md`). **No ground case takes a
factor other than 1.5**, and the value the code applies today is already correct
— what changes is that the deliverable can now *say why*, through G-11's table,
with basis `LIMIT (14 CFR 23.471 — ground loads are limit loads) × 1.5 (23.303)`.

Unchanged: `NVP`/`NDP`/`NS` stay dimensionless load **factors** (units `""`) —
never marked `-ULT`, never scaled, blank SF column (M4-17e). The factor applies
to forces and moments only.

### G-11 — A **governing safety-factor table** is the authority for every case's factor *(user, 2026-08-14)*

**The table is the single place anything reads a factor from**, and it states, per
row: the load class / condition family, the factor, the **basis**, and whether
the row is a default, a derived value or a user **override**.

**Granularity: per load class / condition family**, not per case (~10 rows:
FAR 23 flight limit, limit ground loads 23.471, engine-failure, and future named
failure cases). Every per-case factor — including the `SF` column the report's
**case index** already carries — becomes a **derived view** of it. A case maps to
a class, so no case can be forgotten by omitting a row.

**Fully user-editable, including the regulation-fixed rows** *(user decision,
taken with the risk stated)*. This is deliberately wider than **M4-8**'s design,
which keeps Layer 1 (`LIMIT → 1.5`, `ULTIMATE → 1.0`) in code precisely because
14 CFR 23.303/25.303 decides it. The reason it is acceptable here is that the
factor is applied **only at the render/export boundary** — the calc stays LIMIT —
so **no override can move an Appendix-A oracle**. The exposure is the
*deliverable*: a deck could be shipped at a non-regulatory factor. Four
mitigations are therefore part of this decision, not follow-ons:

1. **An override cannot be silent.** Any row differing from its derived value is
   marked as an override in the table, in the report, and in the
   methods-and-limitations stamp — so a reader of *any single stamped file* knows
   an override is active. Precedent: `APPROVED_CORRECTIONS`, where "a correction
   that is not declared here is invisible to the analyst, which is the whole
   point of declaring it".
2. **An override requires a basis.** The `basis` string is mandatory on an
   overridden row; an override without one is rejected at validation.
3. **Below-regulation overrides raise a certification-risk warning.** An override
   under the derived regulatory value (e.g. 1.5 → 1.2) warns in `validation.py`
   and in the GUI, on the F25-2-d precedent — the floor constrains what may be
   *declared*, and the declaration is visible.
4. **Shipped fixtures carry no overrides**, so the default table reproduces
   today's output byte-for-byte. That equality is the acceptance test.

**An unresolved case defaults to 1.5 and is flagged** *(user decision)* — the row
is marked *defaulted* in the table and the deliverable, rather than raising. To
stop "flagged" from becoming "normal", a test asserts **zero defaulted rows on
every shipped fixture**, so a default appearing is a red build rather than a
footnote. This supersedes the silent
`getattr(item, "safety_factor", ULTIMATE_FACTOR)` fallback in
`report/content.py:1010`, which today reads 1.5 for a factorless case with no
trace at all.

**Travel: a numbered report section plus a stamped companion CSV** in the Export
bundle and the manifest, carrying the methods stamp like every other companion
file. Deck `$` headers keep quoting the per-case factor they already state, now
sourced from the table.

**Scope note — this is M4-8, and it should ship as its own change.** Backlog
Pri 6 (M4-8, `[E]`, "sequence-independent, ship in any gap") is exactly this
work, and the table is now the agreed *form* of it. It is recommended to land
**before** the rest of step 10 so the ground family consumes an existing
authority instead of creating a third ad-hoc factor site. `CLAUDE.md`'s
load-output contract and `CONVENTIONS.md` both describe the safety factor and
will need the table named as its owner.

### G-12 — Two artifacts: the **airframe** gets the load transferred to the gear reference point; the **gear report** states the contact patch, the stroke and both ends of the leg *(user, 2026-08-14)* — closes **D3**

The ground reaction is one load, delivered twice, for two different readers:

1. **Airframe** (assembled deck, and the wing/body/tail views): the reaction is
   transferred from the contact patch to the **gear reference point** — G-2's
   `attach` — with its lever-arm couple, so the airplane-level load is correct
   wherever the gear happens to be. Guarded by G-2's exact resultant-preservation
   test; the carrier (`BODY`/`WING`) decides which beam receives it.
2. **Gear**: a load report stating, per case and per leg, the reaction **at the
   contact patch** together with the **strut stroke** and ground angle it was
   computed at — the boundary condition a gear analysis actually starts from.

**D3's two questions are answered by building it this way:**

- **Strut state — follow LANDLOAD per attitude.** The contact patch is computed
  from the **compressed** axle for cases 1–12 (level, tail-down, one-wheel) and
  the **static** axle for 13–33 (ground roll, side, supplementary nose), each
  with its own ground angle, reusing LANDLOAD's own `x + r·sin(GRA)`,
  `z − r·cos(GRA)` under a single owner rather than a second copy of the formula.
  On ga6 the level and ground-roll contact points differ by 0.49 in in `x` and
  **3.71 in in `z`** — 6,706 lb-in of pitch on the braked-roll drag load — and
  `_geometry` already resolves all three attitudes, so following the manual costs
  nothing. **The application node does not move**: a trunnion is fixed to the
  airframe, so GIDs are stable and the attitude difference lands in the lever
  arm, where the physics puts it.
- **Frame — each artifact in its natural one, rotated once.** The airframe deck
  takes LANDLOAD's **airplane-datum** components `vm`/`dm`/`vn`/`dn` (the
  resolution through `PHIM`/`PHIN` that `PROGRAM_SPEC.md` describes as "computed
  but still unsurfaced — an M4-6 hook"); the gear report takes the **ground-line**
  set `VMP`/`DMP`/`SMP` with the ground angle stated, which is how a gear engineer
  reads it and how the manual prints it. Re-deriving the rotation in
  `coordinates.py` would put a second implementation of `PHIM`/`PHIN` beside the
  first. The difference is not cosmetic — ga6 case 1 drag is **1,020 lb
  ground-line against 795 lb airplane-datum (−22 %)**, and the side case carries
  0 lb of ground-line drag against 186 lb in the airplane datum.
  **`SMP` passes through unrotated** (it is normal to the pitch rotation) —
  correct but non-obvious, so it is asserted rather than assumed: the
  contact-patch resultant about the CG, rotated through `BETA`, must equal the
  applied airplane-datum resultant, per case.

**The gear report is a free body, not a load list.** It states *both* ends of the
leg — the contact-patch load in, and the reaction delivered at the gear reference
point out — so the two artifacts are provably one load seen from two sides. That
buys a drift guard for free and makes it checkable by eye: **the gear report's
reference-point reaction equals the airframe deck's applied load at that node,
sign-flipped, case by case.** This promotes the plan-07 resultant invariant from
a hidden test into a visible deliverable.

**Gear inertia closes the free body, and its limit is stated.** ga6's main gear
weighs 155 lb (wheel 45 + structure 110), which is **both legs** — the weight
database is the whole airplane — so one leg is 77.5 lb and at `NVP` 3.167 that is
**245 lb against a 4,038 lb reaction — 6.1 %**.

*(Corrected 2026-08-15, in implementation.* This paragraph first read "491 lb …
12 %", which paired the **whole main gear's** 155 lb with a **per-wheel**
reaction: `VMP` is per wheel — `landing.landing_reactions` says so and
`vmp = 0.5*NLG*WL` is why — so the two sides of the ratio counted different
numbers of legs. `LandingGearInput.weight_lb` is therefore defined **per leg**,
consistent with `attach`, which is likewise one leg's node with its twin got by
reflection. The term is half what the note claimed; it is still far too large to
leave out of the free body, which is what the paragraph exists to argue.)*

Contact-patch load **minus gear inertia** = the
attachment reaction, so the report shows the term rather than leaving the two
ends 12 % apart with no explanation. **Limitation, stated in-band:** sloads
carries gear mass at the **airplane** load factor; unsprung-mass amplification —
which is what actually sizes an axle — is **not modelled**.

#### G-12a — The leg weight is an **input**, one number per leg *(user, 2026-08-15)*

Raised by implementation: the paragraph above needs ga6's 155 lb, and **nothing
marks a `weight.items` row as gear**. On every shipped fixture the rows are
identifiable only by their names (`Main gear wheel`, `Main gear structure`), so
the no-schema-change route is a name match — which is precisely the
`LANDING_CG_NAMES` failure mode **G-3a** retired one layer up, where a renamed
row silently changed an oracle-locked number.

**Decision:** `LandingGearInput.weight_lb` — the whole leg, trunnion down (wheel,
tyre, axle, oleo and back-up structure), beside `carrier` and `attach`. Same
"explicit, not inferred" reasoning that made `MassItem.component` and
`MassItem.consumable` inputs. **`0.0` means *not stated***: the report prints the
inertia term blank and says why, and the free body is shown open rather than
closed with a guessed number.

*It is deliberately one number, not a sprung/unsprung split.* Only the **unsprung**
mass — wheel, tyre, axle, lower oleo — sees the impact amplification that actually
sizes an axle, and this report does not model that (stated above and unchanged).
What the free body needs is the whole leg at the **airplane** load factor, which
is one number; entering a split would imply a gear-design capability the tool
does not have.

*Fixture data owed:* five airplanes × two legs, **per leg**, taken as half the
database's main-gear rows and all of its nose-gear rows:

| fixture | main rows (both legs) | `main_gear.weight_lb` | `nose_gear.weight_lb` |
|---|---|---|---|
| `ga6_normal` | 155 (wheel 45 + structure 110) | 77.5 | 49.0 |
| `cessna_210` | 170 (wheels 50 + structure 120) | 85.0 | 57.0 |
| `atr42_100` | 1,050 | 525.0 | 260.0 |
| `dhc8_dash8` | 1,200 | 600.0 | 300.0 |
| `concept_regional_jet` | 1,150 | 575.0 | 300.0 |

These stay **consistent with** `weight.items` rather than replacing it: the
database still carries the gear mass that rides the closure field in the
assembled case, and this field is read by the gear report alone. Two statements
of one quantity is a drift risk, and it is held the way this project already
holds that class — **pinned per fixture** (the
`test_the_unmodelled_wing_mass_is_pinned_per_fixture` mechanism), so
`2 × main + nose` against the database's gear rows is a stated number that goes
red when either side moves. Deliberately *not* a name-matching reconciliation in
the code: that would put the failure mode G-12a exists to avoid back into the
calc, where the pin puts it in a test.

**What the report is, and is not.** It is the **gear interface load definition**.
sloads has no gear kinematic model, so it does not and must not claim
drag-brace, side-brace, trunnion or axle-bending loads. With contact patch,
components, ground angle, stroke and the reference-point reaction, a gear
engineer builds those; without this artifact they cannot. Overstating it would be
the "a wrong card outranks a missing card" failure in its purest form.

**No new inputs.** The stroke is already recoverable from the three axle states
and `strut_stroke_in`, and it is more informative than the state names suggest:

| ga6 main leg | axle (x, z) | from extended | % of 7-in stroke |
|---|---|---|---|
| extended | (96.2, 54.2) | — | 0 % |
| `axle_compressed` — level landing | (96.3, 55.9) | 1.70 in | **24 %** |
| `axle_static` — ground roll | (96.7, 59.6) | 5.42 in | **77 %** |

The landing families are computed near the top of the stroke and the handling
families near the bottom — impact versus sitting — which is exactly what a gear
analyst needs told, and which no current deliverable says.

**Travel:** a stamped companion CSV in the Export bundle and the manifest, plus a
numbered report section, like every other companion artifact. **Case set: all 33**
(against the assembled deck's 24) — see the G-6 amendment.

### G-13 — CI gate, negative controls, coverage and the digest wave *(user, 2026-08-14)* — closes **D10**

**What the step inherits for free.** Ground cases join the assembled deck (G-1),
and `test_assembled_deck_reacts_to_zero` already asserts
`set(sols) == set(by_sid)` — *every* balanced case must appear as a solved
subcase with six recovered reaction components at zero, in both unit systems, in
the real solver. No new round-trip leg is needed for the closure itself.

**One ground-specific solver assertion is added, because the inherited leg can
pass vacuously.** "Reactions ≈ 0" proves the assembled set balances; it does not
prove the gear reaction arrived at the right node with the right couple — a
transfer that dropped its lever arm *consistently* would still sum to zero at the
support. So: **the reaction recovered at the gear `attach` GID must equal the
gear report's reference-point reaction, sign-flipped, case by case.** This closes
the loop between G-12's two artifacts **through a third party** — sbeam
reassembles the load from the card text and its own `GRID` lever arms — so a
transfer error, a frame error and a dropped couple all surface in one assertion.

**Two negative controls**, on the established pattern that a gate is trusted only
once it has been shown to fail (`test_a_flipped_fin_load_breaks_the_assembled_solve`,
`test_a_displaced_body_grid_breaks_the_free_free_reaction`,
`test_a_scaled_wing_force_card_breaks_the_wing_assertions`):

1. **Drop the offset couple** in the gear transfer → the assembled reaction must
   go non-zero. Targets G-2's transfer.
2. **Use the static contact patch for a level-landing case** → G-6's closed-form
   factor gate must go red. Targets G-12's per-attitude geometry, otherwise the
   least-guarded new decision in this note.

**Coverage is pinned, not chased.** The two ground deliverables need different
things, and the asymmetry is stated rather than smoothed over:

| deliverable | needs | fixtures |
|---|---|---|
| assembled ground cases | a **derivable mass loading** (G-3/G-5) | **2** — ga6 (3/3), RJ (2/3) |
| gear load report (G-12) | LANDLOAD output + gear geometry, **no mass model** | **5** — all but `concept_heavy` |

Two coverage tests pin both sets and go red when the fixtures improve — the
mechanism `test_which_conditions_assemble_is_pinned` already uses. Giving
`concept_heavy` gear geometry and a `landing` slice is filed as **cheap fixture
data** (backlog): it buys a sixth gear-report fixture and the only concept-mode
exercise of the 23.473(g) `N ≥ 2.67` / `NLG ≥ 2.0` floor warning, but **no**
assembled ground cases — its single CG case is not derivable. The step is not
held for it.

**A digest wave per landable piece, and the middle one must be empty.** The
baseline's own rule is that "a regeneration is a claim that the change to
Imperial output is intended", so three pieces bundled into one wave make the
claim unfalsifiable. Expected signatures:

| piece | expected digest movement |
|---|---|
| **1. G-11 governing SF table** — ✅ **shipped 2026-08-14** | report/case-index channels gained the table; **no numeric value moved** (1.5 was already applied) |
| **2. the schema hop (G-2…G-5)** | **nothing at all.** Its acceptance is that the `FLIGHT`-tagged set after migration equals today's exactly — movement here is the migration failing to be output-neutral, i.e. a finding, not a chore |
| **3. ground cases + gear report** | `sbeam/balanced_deck` and `case_index` on ga6 and the RJ; a **new** gear-report channel on five fixtures |

**One cost to check rather than assume:** ga6's assembled deck goes from 7
symmetric + 8 lateral subcases to that plus up to 24 ground cases with twins —
roughly doubling the solve count in the round-trip job. Measure it against the CI
budget once the first deck exists.

### G-14 — **MTOW is a single input on `WeightInput`**, like MLW; the other five representations become reads *(user, 2026-08-14)* — closes **D11**

**Measured 2026-08-14 — MTOW is represented six ways, and five of them agree:**

| representation | ga6 | cessna | dhc8 | atr42 | RJ | concept_heavy |
|---|---|---|---|---|---|---|
| `speeds.weight_lb` (STRSPEED design weight) | 3,400 | 3,800 | 34,500 | 36,817 | 33,000 | 18,000 |
| `weight.envelope.gross_weight` (WTENV, **oracle-locked**) | 3,400 | 3,800 | 34,500 | 36,817 | 33,000 | — |
| `landing.gross_weight_lb` (GW, sets `WR`) | 3,400 | 3,800 | 34,500 | 36,817 | 33,000 | — |
| max flight CG case weight | 3,400 | 3,800 | 34,500 | 36,817 | 33,000 | 18,000 |
| **`weight.direct_totals()[0]`** (item sum) | 3,400 | 3,800 | 34,500 | **37,781** | **34,800** | 18,000 |

The item sum diverges on atr42 (+964) and the RJ (+1,800) **correctly** — a
database can hold full fuel *and* full payload at once, which no real loading
can. The defect is that `direct_totals` documents that value as "MTOW is every
item" and `applicability.design_weight_lb` consumes it as the **design weight**
behind the FAR 23 12,500 lb gate. It is an upper bound wearing the name of a
design limit.

**Decision:** `WeightInput.max_takeoff_weight_lb` is the SSOT, beside
`max_landing_weight_lb` (G-4) and the future MZFW. `LandingInput.gross_weight_lb`
is **removed**; `speeds.weight_lb` and `weight.envelope.gross_weight` become
derived reads; `direct_totals()`'s first element is renamed to what it is (the
database total); `applicability.design_weight_lb` is re-pointed at the SSOT.

**A latent defect leaves with the field.** `build_landing` today falls back to
`max(cg.weight_lb for cg in cgs)` when `gross_weight_lb` is unset — and `cgs` are
the **landing** loadings, so the fallback yields **MLW, not MTOW** (ga6: 3,230
against 3,400). That makes `WR = GW/MLW = 1.0` and understates cases 13–24
(braked roll, side, supplementary nose) by ~5 % on every fixture. Every shipped
fixture sets the field explicitly so it has never bitten; under G-3 the same
fallback would survive with the same wrong answer.

**One ordering chain replaces four scattered checks:**

    OEW  ≤  MLW  ≤  MTOW  ≤  Σ items

— "you must be able to land with reserves" (G-4's floor, which
`concept_regional_jet` fails today) and "you cannot weigh more than everything
you have" (the new ceiling). Violations are the fixture-data class this project
keeps finding by accident; one chain finds them in one place.

**Split across two claims, so piece 2's "nothing moves" stays true:**

1. **Piece 2 (the schema hop)** takes the byte-neutral part: the new field,
   the removed `gross_weight_lb`, the derived reads. Migration sets MTOW from
   `speeds.weight_lb` (equal to GW on every fixture), so **nothing moves** — and
   the STRSPEED and WTENV oracles are the guard, `weight.envelope.gross_weight`
   being oracle-locked.
2. **The `applicability` / `direct_totals` re-point is its own claim**, because
   it was expected to move output: the FAR 23 exceedance line 37,781 → 36,817 on
   atr42 and 34,800 → 33,000 on the RJ. Small, correct and declarable — but
   bundling it into a wave advertised as "nothing moves" would make that claim
   untrue.

   **[CORRECTION, 2026-08-15 — shipped]** It moved nothing. `design_weight_lb`
   preferred `speeds.weight_lb` and only fell back to the database total, and
   every shipped fixture sets that field, so the gate already read 36,817 and
   33,000. The defect was **latent** — live for a project whose STRSPEED weight
   is unset, which is exactly the state a new project is in when the
   applicability banner is first consulted. Splitting the claim was still right;
   the reason stated here was not what made it right.

**Stated assumption — MTOW is CG-independent** *(user, 2026-08-14)*. On some
airplanes the maximum take-off weight **varies with CG** (the Boeing 777 among
them): the weight–CG envelope's top edge is not flat, and the permissible weight
falls off toward one or both CG limits. The more common case, and the one this
implementation supports, is a **single scalar MTOW, constant between the forward
and aft CG limits**. That is recorded as a stated assumption in the weights basis
rather than left implicit.

Worth noting for whoever extends it: the envelope is **already** not a rectangle
— `WeightEnvelopeInput.fwd_regardless_weight` makes the *forward* CG limit
weight-dependent (ga6: 2,800 lb against a 3,400 lb gross). So a CG-dependent MTOW
is a change to the envelope's **upper boundary**, in machinery that already
expresses a weight-dependent boundary in the other direction — not a new concept.
Filed: backlog *"CG-dependent MTOW (non-flat weight–CG envelope top edge)"*.

## 3. Open decisions (working list)

| # | Question | Status |
|---|---|---|
| D1 | Which model carries the ground cases | **closed → G-1** |
| D2 | Where the reaction is applied (axle vs attachment; carrier) | **closed → G-2** |
| D3 | Which strut state per case; does the application node move; which frame | **closed → G-12** |
| D4a | Where the ground cases' inertia set comes from | **closed → G-3**, incl. G-3a/b/c |
| D4b | The landing-weight burn-down rule (`MassItem.consumable`) | **closed → G-5** |
| D4c | Max landing weight as an input, and who owns the landing weight | **closed → G-4** |
| D5 | What closes the case: LANDLOAD's NVP/NDP/NS, or the six-DOF solve | **closed → G-6** |
| D6 | The wing during a ground case (the `L = 0.667` lift fraction, and its shape) | **closed → G-7** |
| D7 | Handedness of the one-wheel and side-load families | **closed → G-8** |
| D8 | Down-selection: do ground cases meet the governing set | **closed → G-9** |
| D9 | Safety factor: LANDLOAD's embedded 1.33 / 2.25 / 0.83 / 0.8 multipliers | **closed → G-10** (classification) and **G-11** (the governing SF table — M4-8, ships first) |
| D10 | CI gate, digest wave and fixture coverage | **closed → G-13** |
| D11 | Does **gross/take-off** weight get the same treatment as MLW (G-4)? | **closed → G-14** |

**Two sub-decisions were raised by implementation and closed the same way**
(2026-08-15, user), and both are recorded above beside the decision they qualify
rather than as a new series:

| # | Question | Status |
|---|---|---|
| D12 | Which axis the ground-case wing lift acts along, given G-6 promises an exact gate | **closed → G-7a** (the ground-line vertical) |
| D13 | Where the gear report's leg inertia gets its leg weight from | **closed → G-12a** (`LandingGearInput.weight_lb`) |

**Every decision in this note is closed.** What remains before code is the
sequence in §5 and the re-rating of backlog priority 1.

---

## 4. Schema changes implied so far

One hop, planned once, rather than four (older files still load;
`SCHEMA_VERSION` bumped once for the set):

| change | decision | note |
|---|---|---|
| `CgCase.analyses: Set[AnalysisKind]` (`FLIGHT` \| `GROUND`), non-empty | G-3, G-3c | new enum; extensible by design |
| `CgCase.role: Optional[GroundCaseRole]` | G-3a | retires LANDLOAD's positional + name-matched contract |
| **remove** `FlightLoadsInput.cg_cases` | G-3b | already a derived copy of `weight.cg_cases` |
| **remove** `LandingInput.cg_cases` | G-3b | folded into the shared list, tagged `GROUND` + roles |
| `WeightInput.max_landing_weight_lb` | G-4 | **moved off** `LandingInput`; SSOT for the landing weight |
| `WeightInput.max_takeoff_weight_lb` | G-14 | SSOT for the design MTOW; a **single value, CG-independent** |
| **remove** `LandingInput.gross_weight_lb` | G-14 | the `max(landing cg_cases)` fallback — which yields MLW, not MTOW — leaves with it |
| `MassItem.consumable: bool = False` | G-5 | also serves Pri 10 and F25-1's MZFW |
| `LandingGearInput.carrier: GearCarrier` (`BODY` \| `WING`), no default | G-2 | export raises when unset |
| `LandingGearInput.attach: (x, y, z)` | G-2 | airframe attachment/trunnion node |

No schema change from G-6/G-7/G-8/G-10/G-11. **One correction to that claim,
found in implementation (2026-08-15):** G-12 was filed as "adds a deliverable, not
an input" on the strength of every printed number already existing in
`GearReactionCase` and `landing._geometry` — true of the contact patch, the
components, the ground angle and the strut stroke, and **false of the leg
inertia**, which needs a leg weight nothing in the schema carries. **G-12a** adds
it as a second, smaller hop:

| change | decision | note |
|---|---|---|
| `LandingGearInput.weight_lb` | G-12a | the whole leg, trunnion down; `0.0` = not stated, and the report says so rather than guessing |

Everything else in G-12 stands as filed: a new GID band for the gear nodes
(`export/bands.py`) plus a stamped companion CSV + manifest row. G-8 does change
one signature:
`case_ids.balanced_subcase_id` takes the case's **hand** explicitly instead of
parsing an id suffix — behaviour identical for every existing case (`W-05R` still
→ 7105), drift-guarded, so the ground family can be handed without a suffix.

**Standing acceptance for the whole hop:** every Appendix-A oracle unchanged
bit-for-bit (this is plumbing plus new inputs that default to today's
behaviour), every shipped fixture round-trips, and the `FLIGHT`-tagged case set
after migration equals today's `flight_loads.cg_cases` exactly, per fixture.

---

## 5. Sequence — three landable pieces

The decisions grew a prerequisite and a new deliverable, so this is no longer one
change. Each piece is independently landable, independently claimable in
`CHANGELOG.md`, and has its **own** digest wave (G-13):

| # | piece | decisions | why it is separable | digest expectation |
|---|---|---|---|---|
| **1** ✅ | **Governing safety-factor table** (M4-8) — **shipped 2026-08-14** | G-10, G-11 | Explicitly sequence-independent; shipped first so the ground family consumes an existing authority instead of becoming a third ad-hoc factor site | report/case-index channels gained the table; **no numeric value moved**, no digest changed |
| **2** ✅ | **The schema hop** — tagged case list, roles, MLW, consumable, gear carrier + attach — **shipped 2026-08-14** | G-2, G-3, G-4, G-5, G-14 | One `SCHEMA_VERSION` bump for the whole set rather than four; every new field defaults to today's behaviour | **nothing moved** — `digests.json` untouched, and the `FLIGHT` set after migration is pinned per fixture to the pre-hop list |
| **3** ✅ | **Ground cases + the gear report** — **shipped 2026-08-15** | G-1, G-6, G-7 (+G-7a), G-8, G-9, G-12 (+G-12a), G-13 | The physics, once its inputs and its factor authority exist | as predicted: `sbeam/balanced_deck` + `case_index` on ga6 and the RJ, a new `gear_report` channel on five fixtures, plus `csv`/`txt` landing on five from the case-labelling fix |

Backlog priority 1's original **L / L** rating predated pieces 1 and 2 and was
low; the backlog was re-rated to this sequence on 2026-08-14, and **pieces 1 and 2
both closed the same day** (history: "Step 10 piece 1 — the governing
safety-factor table" and "Step 10 piece 2 — the weight/CG case model + gear
inputs"). Piece 3 is backlog priority 1.

Two things piece 2 deliberately left firing rather than fixed, because either
would have made its "nothing moves" claim untrue — both filed with the guard that
found them: `dhc8_dash8`'s gear mass tag (backlog *"`dhc8_dash8` gear mass is
tagged `fuselage` but the leg is wing-carried"*; correcting it re-pins
`mass_distribution.wing_mass_tie`) and the `applicability` / `direct_totals`
design-weight re-point (its own backlog row — priorities are an order, not IDs,
so rows are named here rather than numbered). G-2's third guard — the transfer preserves
resultants about the CG at `rel_tol 1e-12` — tests the transfer and so lands with
piece 3.
