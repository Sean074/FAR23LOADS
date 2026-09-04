# Conventions Charter — Axes, Signs, Units, Load Contract, Case Identity

**Authoritative single source** for every axis/sign/unit/reference convention in sloads
(2026-08-05 process review, R8). The rules:

1. **Every physics or export step's design note must cite the sections of this charter
   it relies on, before code is written** (CLAUDE.md rule 1).
2. **Make it structural:** any cross-cutting convention gets a single-source code owner
   **plus a drift-guard test** the first time it is needed (§7 table) — never a prose
   rule alone. The units/SI history (three rebuilds before M4-20) is the cautionary
   precedent.
3. **A change to any convention here is a breaking change** — L-tier step, update this
   file, sweep every consumer.

Facts verified against code 2026-08-05, with citations. Line numbers drift — the cited
file + symbol is the anchor.

---

## 1. Frames and axes

- **sloads internal frame:** Imperial airplane axes, all lengths in **inches** —
  `x` = fuselage station, **+aft**; `y` = butt line, **+right** (starboard);
  `z` = waterline, **+up**. Loads: `fz` = lift (+up), `fx` = drag (+aft), `myy` = wing
  torsion about the spanwise y-axis (`sloads/export/coordinates.py:3-11`).
- **sbeam deck frame:** NASTRAN basic CID 0, right-handed; the sloads frame already
  matches, so the transform is the **identity** (`coordinates.py:13-16`,
  `SBEAM_CID = 0`).
- **`export/coordinates.py` is the single edit-point** for any sign flip, axis swap, or
  unit scale in the export channel — the **only** place a load or coordinate is
  multiplied by anything on its way to a deck. `sbeam_bridge` arithmetic is unit-free
  and routes every dimensional value through `to_grid`/`to_force`/`to_moment`/
  `to_pressure`; `_checked()` rejects dimensionally inconsistent unit sets at
  deck-write time.
- **Reporting rules** (`SUMMARY_REPORT.md` §3.3): torsion always names its axis (wing
  LRA as %chord); moments state their sign convention; maxima carry a station;
  envelopes are two-sided.
- **Mass units are a distinct channel, and the one exemption from the all-1.0
  Imperial identity (C-5, 2026-08-08).** `CONM2` carries **mass**; the database
  stores **weight**. `DeliverableUnits.mass`/`.mass_inertia` on the SOLVER channel
  are lbf·s²/in and t; the HUMAN channel keeps lb and kg. The identity is
  `force / (mass × length) == g` — exact, and the *same number* in both systems
  (one standard gravity, expressed per length unit, derived once) — plus
  `mass_inertia == mass × length²`. `is_mass_consistent` is separate from
  `is_consistent` so the human channel can fail it without changing what any
  existing caller sees, and a writer refuses a set that fails it.
- **Inertia is never applied twice (C-6).** The `FORCE`/`MOMENT` deck is the
  *total* applied load and already contains inertia. No deck may both apply it
  and accelerate a mass set: the mass-check deck therefore carries **no load
  cards at all**, and sloads' inertia-only set is marked a comparison artifact
  in-band. This is structural, not a warning, because the failure reads as a
  heavier airplane rather than as a crash.
- **`weight.items` is the mass single source of truth (B-2, 2026-08-08).** One mass
  model, owned by `sloads/mass_distribution.py`. `MassItem.component` tags which
  structural component reacts each item's weight (`wing` / `fuselage` / `htail` /
  `vtail`); the tag is **explicit**, because every item in every project sits at
  `y = 0` (lumped airplane totals on the centreline) and no geometric inference can
  separate a wing-mounted engine from a fuselage one. The Ch 15 fuselage beam is
  *derived* from the tagged database; `fuselage_mass.stations` is an explicit
  override, and the difference is always reported, never silently taken. **The
  empennage surface weights follow the same rule since 2026-08-10**
  (`tail_surface_weight`, with `TailMassInput.panel_weight_lb` as the override) —
  they were the one consumer B1 left on a parallel model, and the cost was six
  airplanes' worth of air-only h-tail decks. **A row the wing carries part of
  states the share (design note 29, 2026-08-17):** `MassItem.wing_fraction` is the
  fraction of a row — weight and own inertias — reacted by the wing (both sides
  together), the remainder by `component`; both parts sit at the row's position,
  so WTONECG/WTENV read rows and are unchanged, and only the reaction partition
  splits — through **one owner, `mass_distribution.reacted_parts`**, which every
  by-component consumer (the partition, `balance`, the CONM2 header) reads.
  `component_of` is exact only on a part. It is a fraction, not a pound figure,
  so G-5 burn-down and a D-25 loading fraction leave the split invariant. Written
  for the wing-tank fuel that sat inside an undivided fuel row on three fixtures
  and so rode both beams (3,800 / 4,000 / 1,200 lb); the wing tie
  (`wing_mass_tie`, validator `wing_mass_tie_open`) is what says whether the item
  model and WINGINER describe one wing.
- **The fuselage beam carries everything except the wing.** The empennage included
  — it hangs off the aft fuselage, so that beam reacts its weight. The wing is the
  one exclusion: it enters as the carry-through *reaction*, and applying it as mass
  as well would count it twice (the seam rule below). Hence the invariant
  `Σ(wing items) + Σ(beam stations) == Σ(all items) == W`, guarded by
  `mass_distribution.partition_closes`.
- **A cumulative torsion is not a free moment (2026-08-08).** `WingStationLoad.myy`
  is the torsion about the *root* reference and already contains the sweep and
  dihedral transfer of outboard shear inboard. Only the section `Cm` is a free
  moment. Any assembly that applies a strip's position offset must use the free
  moment alone, or it double-counts the transfer — worth 20 % of n·W·MAC.
- **An assembled balanced case closes in six DOF, by one rigid-body field**
  (plan 13 decision L-2, 2026-08-09 — this replaces the three-symmetric-DOF rule
  B2 shipped with). The relief is the d'Alembert field `f_i = −m_i(a_cg + ω̇ × r_i)`,
  owned by `sloads/rigid_body.py`. The three translational DOF stay decoupled
  ratios `n = F/W`, because the loading's centroid *is* the CG; the three
  rotational DOF are **one coupled 3×3 solve** on the assembled inertia tensor,
  because `Ixz` is 8 % of the ga6's pitch inertia and larger on the regional jet.
  The x DOF is not optional: nothing else in an assembled model reacts drag, and
  FAR 23's `nx` is that quantity. From the hub thrust card (§7) it reacts thrust
  too — `n_x = (D − ΣT)/W` — so a case whose entered thrust cancels its drag
  closes at `n_x = 0`.
  - **Every angular acceleration applies two force components, not one.** That is
    the difference between `Σw·d²` and a moment of inertia, and it is not
    uniformly small: pitch's omitted companion was worth ≤ 0.08 % of a node load,
    roll's was *larger than the roll term already in the deck*, and yaw's would
    have been 55 %. Slicing the field per axis is how a suite acquires three
    different errors from one omission.
  - **A mass the assembly carries as a point contributes its own inertia as a
    free moment** (decision L-3); a mass the assembly *spreads* does not, or the
    spread is counted twice. The predicate has one owner,
    `mass_distribution.assembly_distributes_mass`.
  - Angular accelerations are carried in **weight-space `1/in`** (g per inch of
    arm), the same convention that makes the translational DOF come out directly
    as load factors. `rigid_body.radians_per_s2` is the only conversion.
- **The residual is part of the deliverable.** A balanced case states its
  pre-closure residual and the relief applied, in the result, the UI and the deck
  header — the gate is on the physics, not on the correction.
- **A residual the airplane is not meant to balance is reported, never gated**
  (plan 11 §10, extended by plan 13 decision L-5, 2026-08-09). Two of the six DOF
  can carry an *applied* load by design: `residual_mx` on a rolling case is the
  aileron couple (FAR 23.349), and on a **lateral** case `residual_fy`/`residual_mz`
  are the fin's side load **in full** — nothing in an airplane cancels a rudder
  kick; it yaws and rolls, and the closure *is* that motion. Applying a 1 % gate
  to those components would either be vacuous or force a fictitious balancing
  load into the case. What is gated instead is the case's **symmetric half**:
  remove the fin set and the force and pitch residuals must be what they always
  were. They are, to the last digit, because a fin set carries `fy` and `mz` only
  — asserted rather than argued, since a frame-map slip landing the fin's normal
  force back on `fz` is exactly what would break it.
  - Where a residual ceiling has to be stated above the 1 % gate, it is stated
    **per fixture and per family** (`symmetric`/`lateral`), never widened for
    everyone: the lateral cases sit at V-n points the symmetric families never
    visit, and one merged number would stop the symmetric bounds from biting.
- **A lateral balanced case states its wing-body sideslip term, in-band**
  (decision L-7; design note 19 rev. 3, shipped 2026-08-17). Beside the fin's
  load the suite computes the **wing-body side force and yawing moment in
  sideslip** — `Cy_β`/`Cn_β` per degree from DATCOM 5.2.1.1 / 5.2.3.1 on the
  fuselage outline (`sloads/lateral_body_aero.py`, oracle-locked to Digital
  DATCOM's printed sample output at ±0.1 %) — and applies them as one
  `body-aero` load (side force at the body side-area centroid, free couple
  closing `Cn_β` about `xw`) when `aero_coeffs.lateral_body_aero.enabled`.
  **Off by default**, because the term is not conservative in one direction:
  the body's yawing couple is destabilizing and **opposes** the fin's, so with
  the term off the yaw acceleration is **over-stated** and the inertia it drives
  conservative; the body-and-wing side force acts the same way as the fin's
  restoring load at `+β` — it **adds** — so with the term off `n_y` is
  **under-stated** and the lateral translational inertia it drives is **not**
  conservative on any component. Every lateral case states which it did
  (decision L-7.16): the *estimated* force and moment it does not carry, or the
  applied numbers, and either way the fin + body `Cn_β` about `xw` with its
  static-directional-stability verdict (FAR 23.177; flagged, never silently
  emitted). Signs: DATCOM's `+Cy` = starboard matches this frame; DATCOM's
  `+Cn` = nose starboard is **negated** into `+mz` = nose to port, so a
  destabilizing body `Cn_β` is *positive* here. The fin's own design load is
  SELECT's, unchanged; SELECT publishes each condition's `β` and the fin's own
  derivatives, and the balance re-derives neither. The caveat travels as a case
  note into the deck `$` header and the report; it does not live only in
  documentation.
- **A ground case is a balanced free-free case, and it carries no base load
  factor** (decision **G-1**/**G-6**, step 10 piece 3). Ground conditions are born
  in the assembled deck — a ground case is irreducibly three-dimensional (drag and
  side load at a contact patch well below and off the fuselage beam line), so
  building it in a planar per-component view first would put the primary
  deliverable second. Its inertia set enters at `n_z = 0` and the **whole**
  rigid-body field is solved, which is what FAR **23.471** asks for: *"the
  external reactions must be placed in equilibrium with the linear and angular
  inertia forces in a rational or conservative manner."*
  - LANDLOAD's `NVP`/`NDP`/`NS` are **never consumed** — they are translation
    only, and they are stated about the **ground line**, so consuming them would
    put a frame rotation in the load path. They are the independent closed-form
    **check**: rotate the solved field back to the ground line through the case's
    own `ρ` and it reproduces all three, exactly. The rotation lives in the gate,
    where an error is loud.
  - `RESIDUAL_GATE` does **not** apply to the ground family, and that is physics
    rather than an exemption — the same standing as the lateral and 23.427(a)
    cases. A ground case has nothing to trim against, so its pre-closure residual
    *is* the applied gear load by construction.
- **The ground reaction is applied at the point Appendix A's own column names,
  and transferred to the gear reference point** (decisions **G-2**/**G-12**,
  amended by design note 39 **AP-1**, 2026-08-29). The point is per family and is
  the manual's, not a choice: the **axle** on the landing attitudes (cases 1–12)
  and on 25/26, 28/29, 31/32; the **ground contact point** on the handling ones
  (13–24) and on 27, 30, 33. The split is physical — the level-landing drag is a
  *spin-up* load reacted through the bearing at the axle, while braking torque is
  internal to the wheel/leg free body and leaves the patch force where it acts —
  and it is measurable: applying every case at the patch instead invents up to
  524,302 lb-in of pitching moment on the landing attitudes (#139).
  The move to the trunnion
  is ours and carries the lever-arm couple, which makes it a change of
  *description* and not of load. The reference point is an **explicit input**
  with an explicit carrier (`BODY`/`WING`): a wing-carried reaction relieves or
  reverses inboard wing bending and reaches the fuselage only through the
  carry-through, so applying it to the body beam over-loads the fuselage *and*
  hides a real wing sizing case — wrong in both directions at once. `±tread/2` is
  not the answer; that is a **wheel** dimension, and the axle butt line is not the
  trunnion butt line. **The mass model must agree with the carrier** (guard
  `gear_carrier_mass_disagrees`): a `WING`-carried leg's weight belongs to
  `MassComponent.WING` *and* to WINGINER's `wing_mass.concentrated`, per side, or
  the same structure carries the load but not the weight and the wing loses the
  inertia relief its own gear provides. Corrected on `dhc8_dash8`, 2026-08-15.
- **Ground and flight are separate governing families** (decision **G-9**). They
  are never compared for a maximum and no single envelope over both is claimed:
  the two load different structure by different paths, and the value of a
  governing table is naming *which* case governs, which a cross-family `max()`
  destroys. Stated as a standing limitation, not left to be inferred from the
  absence of a comparison. The engineer's opt-out filter *does* reach `LG-` ids —
  a family that is scopable, but never auto-enveloped. **The combined station
  envelope G-9 filed as a follow-on is decided against permanently** (**D-28**,
  2026-08-18, issue #11 closed as decided): on the fuselage the two families are
  assessed with *different internal-pressure companion cases*, so their station
  extremes belong to different total load states, and sloads — which excludes
  pressurization permanently (**D-24**) — cannot form the correct combined state
  from its own outputs at all. Wing and empennage carry no such companion; the
  deliverable stays per family uniformly rather than per component. Combining is
  the consumer's act, performed with their own pressure cases in hand.
- **A surface's inertia is built on the acceleration along *its own* normal axis**
  (2026-08-10, superseding decision L-8 for the per-condition view). The h-tail's
  normal axis is the airplane's vertical, so one term does it: `−n_z·W_ht`,
  bending. The **fin's normal axis is lateral**, so the same acceleration does
  something else entirely to it and it takes two terms: `−n_y·W_vt` bending
  (sideways) and `−n_z·W_vt` **axial** along the span, which compresses the
  surface and bends nothing. `n_y` is the fin's own side load over the case
  weight — the free-free lateral response to the only lateral aero this suite
  models, so it carries decision L-7's caveat and its **relieving** effect
  (exactly `W_vt/W_case`) is stated in-band as unconservative. A condition naming
  no V-n point has no case weight and therefore no lateral term, said rather than
  guessed. Owner: `tail_span.distribute`'s separate `n_normal`/`n_axial`
  parameters, so a vertical factor cannot be passed for a fin's bending direction.
- **The assembled case still applies each mass exactly once** (decision L-8's
  surviving half). The balanced case accelerates the `VTAIL`-tagged mass items in
  its closure field at its own `n_y`/`ω̇`, so the **applied aerodynamic set** it
  reads from `tail_span` must be air only: `balance.fin_sets` takes
  `fz - f_inertia`, never `fz`. The per-component deck and the assembled case
  each carry the fin's mass — in different fields, once each.
- **An empennage surface's weight comes from the mass SSOT** (2026-08-10).
  `mass_distribution.tail_surface_weight` sums the `htail`/`vtail`-tagged
  `weight.items`; `TailMassInput.panel_weight_lb` is an explicit override only,
  marked by `weight_is_override`, and the gap is reported by
  `tail_reconciliation` either way. This is plan 11 B-2/B1's rule applied to the
  surface the step left behind — before it, no fixture set a `tail_mass` and
  every h-tail deck the suite shipped was silently air-only.
- **A load that a free-body cut introduces is never applied in the assembled model**
  (plan 11 §4). Each per-component deck takes a cut and carries the cut reaction as
  an applied load; those reactions must not reappear in an assembled deck, where the
  solver recovers them.
- **Per-component moment reference for an exported deck (E-2, 2026-08-08).** A deck's
  moment resultant is meaningless without the point it is about, and there is no single
  airplane-wide point every deck can use — the decks are per-component beam models, not
  an assembled airframe. Each therefore states its closure about **its own** reference,
  taken from the deck's own `GRID` cards so the claim is verifiable from the file alone:
  **wing → its root station**, **body → its aft-most station** (the point the terminal
  cumulative `Myy` is stated about), **tail → its leading-edge chord station**. Control
  decks carry no geometry and state a force closure only.
- **Beam torsion is not a rigid-body moment.** The exported wing `Myy` is a beam torsion
  about the LRA. Because the station `x` sweeps aft and the station `z` rises with
  dihedral, the rigid transfer term `Σ (p − ref) × F` is of the *same order* as the
  torsion itself (≈ −93,300 lb-in against a −91,400 lb-in root torsion on `ga6_normal`
  PHAA). A deck's torsion claim is therefore about its applied `MOMENT` cards; only the
  bending claim integrates the `FORCE` lever arms. `export/equilibrium.Resultant` carries
  both sums (`m0` and `m`) so a checker cannot silently use the wrong one.
- **Torsion reference = the LRA = the assumed elastic axis (closed 2026-08-16,
  note 24 R-7d).** The formerly-open load-application-axis vs elastic-axis
  question is closed by one sentence, stamped in the LRA model's deck header:
  *grid line = LRA = the assumed elastic axis at the entered `ref_axis_pct`
  chord; torsion is about it.* The fixtures enter 0.40; the schema default
  stays unset (effective 0.25, the original reporting), and the LRA beam-model
  exporter **refuses** an unset axis rather than assuming one (R-7c). An
  **imported** beam line (step 12 import) is the consumer's elastic axis by
  definition, so the question does not arise there.

### 1.1 Airplane state and control signs (verified extraction 2026-08-09; SC-1…SC-6 approved 2026-08-10)

Documented from code — clarifications of existing behavior, not changes. Full
evidence trail: `docs/40_history/20_sign_convention_report_section.md`. The
formerly-absent conventions are now **decisions of record** (user-approved
2026-08-10, labels only — no computed number changed):

- **SC-1 — Sideslip:** `+β` = relative wind from **starboard** (nose left of
  the flight path); the fin's restoring load is then `−fy`, so SELECT's
  negative entered yaw angles (−19.5°/−15°) are the `+β` cases.
- **SC-2 — Rudder:** positive `δr` = trailing edge toward **port** (left
  pedal), producing `+fy` and `+mz` (nose-left) — matching the code's unsigned
  `RD → +fy`.
- **SC-3 — Rates:** rates/accelerations are stated right-handed about
  `(x, y, z)` with the physical senses below; attitude angles are stated **not
  modelled**, never given an invented sign.
- **SC-4 — Twist:** twist-table entries are the section zero-lift angle,
  **nose-up-positive in the same α sense**, relative to the waterline
  ("WL to section zero-lift", `airloads.py` `_twist_angle` use); washout (tip
  nose-down) enters as more-negative tip values. Verified in the basic-lift
  formula `c·cl_b = (mo/2)(ac − Awo)c` — a more positive entry lifts more.
- **SC-5 — Gear reactions:** stated per wheel in airplane axes — V +up,
  D +aft, S +starboard; the FAR 23.485 inboard/outboard literals keep their
  printed signs.
- **SC-6 — Aileron hand:** deflections stay per-direction magnitudes; a handed
  rolling case names its pair from the case suffix ("R = right TE-down / left
  TE-up"), never a global `δa` sign.

The report states all of this once, in its required **"Axes and sign
conventions"** section (`SUMMARY_REPORT.md` §4.2.1), single-sourced in
`sloads/report/conventions_tex.py` (§7 table).

- **Physical senses of positive moments** (forced by the right-handed
  +aft/+right/+up frame, not a choice): `+mx` = starboard wing up (roll to
  port), `+my` = nose-up pitch (the one stated instance: `validation.py:609`),
  `+mz` = nose to port (yaw left).
- **α is nose-up positive, waterline to relative wind** (`alpha_wl`); +α ⇒
  +lift, `C1 > 0` enforced (`flight_envelope.py:154-176`, `validation.py:631`).
  Tail: `AT = alpha_wl + IT − E`, downwash `E` positive-defined and
  subtractive; +IT = tail chord nose-up vs the waterline; +AT ⇒ up (+`fz`)
  tail load (`select.py:237-250`).
- **Elevator is TE-down positive** ("TE dn +", `select.py:216, 303`); travel
  limits `EUP`/`EDN` are stored magnitudes, the −1 applied at use
  (`select.py:369-376`). **Aileron** deflections are stored magnitudes per
  direction (down = TE-down +, up applied negative, `aileron.py:68-75`); which
  wing is deliberately unstated — hand exists only at assembly (§7.1).
  **Rudder** `RD` is an unsigned magnitude; +RD always yields +`fy`
  (starboard) fin load (`select.py:591-595`); sideslip yaw angles enter
  negative (−19.5°/−15°, `select.py:646-662`), so the yaw and rudder terms
  oppose.
- **Load factors:** `nz` +up; `nx = −DX/W` (the inertia/deceleration factor,
  negative for ordinary aft drag, `select.py:117-169`); `n_y = L_v/W` +
  starboard (`balance.py:632`). Station inertia `fz = −NZ·w`
  (`body_loads.py:188`); wing-inertia inputs enter as `Nz = −NZ`
  (`wing_inertia.py:22-25`).
- **Gusts:** `Ude` is a positive magnitude; the ±hand is the caller's factor
  (`ng = ±1`, `flight_envelope.py:227`) or, laterally, reflection
  (`select.py:603-616`).
- **Wing torsion physical sense:** `+Myy` = leading-edge-up (derived from
  `my = (x_lra − x_load)·fz`, `coordinates.py:218-222`); a lift resultant aft
  of the axis gives the negative root torsion the Appendix-A oracles print.
  Spanwise bending `Mxx`/`Mzz` are positive-magnitude integrals; the CID-0
  vector map (owner `bending_moment_vector`, reached for the applied set through
  `sbeam_bridge.applied_body_moments`) sends `Mxx → +x` unchanged and
  `Mzz → −z` negated (`coordinates.py:93-122`).
- **Attitude angles (φ/θ/ψ) and body rates as state do not exist in the
  suite** — only the closure accelerations `p̈/q̈/r̈` (§1) and the unsigned
  gyroscopic body rates (§5, all four sign permutations enumerated,
  `engine.py:294-339`). No document may imply otherwise.

## 2. Units

- **Imperial is canonical internal**; calc runs in the original program's units. SI is
  presentation only, converted at the boundary (`sloads/units.py:1-12`,
  `00_program_overview.md` Units).
- **Two deliverable channels (M4-20 decision D-19):** `Channel.HUMAN` (reports, CSVs,
  workbook: N·m, kPa) vs `Channel.SOLVER` (sbeam span CSVs + bulk data: **N·mm**,
  **MPa** — every derived unit is the base units combined). Resolve the set **once per
  bundle** with `units.deliverable_units(system, channel)` and pass it to every writer;
  never mint one per file. `DeliverableUnits.is_consistent` enforces
  moment = force×length and pressure = force/length².
- **Airspeed/altitude carve-out:** KEAS and ft in both systems, never converted
  (`units.py:95-99`).
- **In-band statement mandatory:** every deliverable file states its unit set
  (`units_statement`, `units.py:530`).
- **The `-ULT` marker is part of the units string** — it converts with the unit
  (`lbs-ULT`/`N-ULT`, `lb-in-ULT`/`Nmm-ULT`, `lb/in^2-ULT`/`MPa-ULT`); mapping table
  `_ULT_UNITS` in `sloads/report/render.py:101`. Non-load units never carry it.

## 3. LIMIT → ULTIMATE contract

- **Calc emits LIMIT; every deliverable is ULTIMATE.** The factor is applied exactly
  once, at the render/export boundary: `report/render.py` (`results_to_rows`,
  `to_ultimate`) and `export/sbeam_bridge.py` (`_sf()`).
- **Loads only** — forces/moments/pressures. Never geometry, weights, inertias, areas,
  speeds, angles, or dimensionless load factors (`_is_load_unit`,
  `render.py:66-95`; `load_keys.py` marks application points "geometry, never scaled").
- **The governing safety-factor table owns the policy** (`sloads/safety_factors.py`,
  M4-8 / decision G-11, 2026-08-14). It is the **single authority** every factor is
  read from: one row per condition family — the family boundaries are 14 CFR Subpart
  C's own section groupings — each stating factor, **basis** and status (`derived` /
  `override` / `defaulted`). `GoverningTable.factor_for(case)` classifies a case from
  its FAR reference, so a case cannot be missed by omitting a row; an unclassified
  case takes 1.5 and is **flagged**, never silently accepted, and
  `tests/test_safety_factors.py` fails on a defaulted case in any shipped fixture.
  The other way a case can miss the table is by having nowhere to put the answer:
  `stamp()` writes the factor onto each result's `safety_factor` carrier and used
  to pass over an item without one on a bare `hasattr` gate. That is recorded in
  `GoverningTable.unstampable` exactly as `defaulted` records an unclassifiable
  case (review CR-B-6, #43) — an unstamped result is one whose report figure and
  whose bulk-data card can still state different factors, which is the F-R1
  defect class — and a test asserts it is empty on every shipped path.
  Layer 1 is `DERIVED_FACTOR`: `LIMIT → 1.5`, `ULTIMATE → 1.0` (14 CFR 23.303/25.303).
- `ConditionResult.safety_factor` is the **carrier** (default
  `constants.ULTIMATE_FACTOR = 1.5`); **1.0 means "already at ultimate"** — still
  ULTIMATE output, marked `ULT SF=1.0`. The table **writes** the carrier at three
  boundaries (`registry.run_all_modules`, `report.content.component_loads`,
  `balanced_run`), so the report's SF column and a deck's `SF=` marker cannot
  disagree about one case (the defect class review finding **F-R1** closed).
- **The table is fully user-editable, including the regulation rows**
  (`Project.safety_factors`, schema v46) — safe for the oracles, since the factor is
  applied at the render/export boundary only, but *not* for the deliverable. Four
  mitigations are part of the contract: an override is declared in the report **and**
  the methods stamp, it must state a basis, an override **below** the derived value
  raises a certification-risk warning (`validation._check_safety_factor_overrides`),
  and no shipped fixture carries one.
- Uniform per-case scaling preserves closure: `sum(dFz) == sf × root` survives the
  boundary (`sbeam_bridge.py:234`).
- Per-module analysis pages may display LIMIT only with the explicit LIMIT marker and a
  pointer to the ultimate deliverables (the CLAUDE.md carve-out).

## 4. Case identity

- `CaseRef` (`models/results.py:17-40`): `case_id = "<component>-<seq>"` (`W-01`,
  `HT-03`, `VT-02`, `F-04`, `EM-01`, `LG-05`), minted **once** by the first module that
  names the condition, never re-minted. Prefix taxonomy + banded allocator:
  `sloads/case_ids.py`.
- Row identity: stable `LoadValue.key` (machine identity) vs cosmetic `label` (M4-9);
  cross-module keys centralized in `sloads/load_keys.py`.
- **One ID per physical condition (M4-2).** Two modules delivering the same case carry
  the *same* `CaseRef` — SELECT's wing `CriticalCondition` and the WINGINER/NETLOADS
  distribution derived from it are one case with one id, not two. The wing `seq` is a
  property of the condition (`case_ids.WING_SLOTS`), not of its position in a list, so
  ids do not float when the envelope or the case list changes. Modules that mint their
  own sequence into a shared prefix are **banded** (`case_ids.py`; ONENGOUT at
  `VT-30..`), and `tests/test_case_ids.py` fails on any collision.
- **Deck-side identity (M4-2).** A solver deck's `SUBCASE` and load-set `SID` are one
  integer derived from the case id — `case_ids.subcase_id` (`W-03` → 103) — never the
  case's position in the export, so a filtered export cannot renumber what survives.
  Each deck carries a `$` subcase-map block, led by the case id in every family.
  The **assembled full-span deck** mints through `case_ids.balanced_subcase_id`
  (**D-R7**, 2026-08-10): the same map inside a per-hand block — symmetric `5000`,
  starboard `7000`, port `8000`, so `W-05R` → `7105` and its twin `W-05L` → `8105`.
  Handedness is a block, not a suffix, because a `SUBCASE` id is an integer; the
  unhanded id still names the physical condition. Minted ids can collide where
  positional ones could not, so `balanced_deck.case_sids` refuses two cases sharing
  one id and hand.
- **One identity, three notations (design note 17).** The case id *is* the deck's
  `LABEL`, and the `LOAD` selecting a card set *is* that deck's `SUBCASE` integer
  (`LOAD = 103` inside `SUBCASE 103`). Two minters mean one case can hold two
  numbers, so every deliverable states them **qualified by deck family** and never
  as one unqualified column: the case index (report + CSV) carries
  `LOAD/SUBCASE (component)` and `LOAD/SUBCASE (assembled)`, filled only where the
  case is in that deck; the report's governing tables and every GUI case label
  quote the one family they are showing. A case with no number in that family
  shows an em dash — never the `sid_base + index` fallback, which is the
  position-dependent id M4-2 decision 8 retired.

## 5. Preserved ENGLOADS conventions (verified in code)

- Engine-mount reaction torque is reported **negative**
  (`sloads/modules/engine.py:165, 195, 256, 285`).
- **Clockwise from the pilot's view is positive** for rotor RPM and stoppage torque
  (`engine.py:8`, `models/inputs.py:50`).
- **BASIC truncation is preserved where the `.BAS` truncated, and only there** — never
  added or removed without checking the Appendix C listing. Both forms (the 3-decimal
  `INT(v*1000)/1000` and the whole-integer `INT()` of ENGLOADS line 944's reported
  stoppage torque) go through the one owner, `sloads/basic.py`
  (`basic_trunc3`/`basic_int`), because **GW-BASIC `INT()` floors where Python `int()`
  truncates toward zero**: they agree on non-negative arguments and differ by exactly
  one unit on every negative one. That is not academic — the 23.361(b)(1) reaction
  torque is negative by construction (row above), a left-hand engine's Y c.g. is
  negative, and LANDLOAD's printed lever arms go negative forward of the datum. Guard:
  `tests/test_basic_semantics.py`.

## 6. Concept-mode benchmark rule (R10)

Where a printed oracle exists, the ±0.1% page-cited oracle test is the gate. Where none
exists (concept mode), the gate is a **stated physics-closure or invariant test in CI,
written with the feature** — e.g. free-free closure residuals, ΣF/ΣM equilibrium at the
export boundary, reduction-to-FAR23 identity on GA inputs. "No oracle" never means
"no gate".

## 7. Single-source owners and their drift guards

| Convention | Owner | Guard test |
|---|---|---|
| Nav / step graph | `sloads/workflow.py` (`STEPS`, `PHASES`) | `tests/test_workflow.py::test_every_registered_module_has_a_step` |
| **Whether an Apply creates an `Optional` project slice** — #143's rule on the main GUI, where the named gesture is the Apply button itself: an Apply may fill a slice in and may empty one out, but it may **not create one out of nothing**. A page whose form nobody filled in used to attach a whole zero-valued slice, which then saved into the `.project.json`; a zero-area `flap_loads` and a zero-cylinder engine took Results Review and Export down on three of the seven bundled examples (#145). "Entered nothing" is read off the dataclass defaults, so a field added later is covered the day it is added, with a `seed=` form for the pages whose widget defaults are not the dataclass's. The asymmetry is deliberate: an existing slice is written back unconditionally, or clearing a field would not land. | `app_shell/optional_slice.py` (`store`/`entered_nothing`) | `tests/test_gui_journey.py` — the whole-GUI walk, so a new page that writes an `Optional` slice directly fails the day it is written |
| **The derive-by-default collapsed overrides** (note 36 OV-1…OV-12, #97) — an input that duplicates a value the project already holds is **falsy-means-derive / typed-means-override at calc level**: one named resolver per quantity (`value or derive(project)`, the `select.py` idiom generalized), the derivation an existing owned computation, and the copy's registry row linked to its owner. The collapsed set is enumerated once; the resolvers the captions show are the same functions the calc calls, so the shown and used numbers cannot drift | `sloads/field_registry.py` (`COLLAPSED_OVERRIDES` + `EXTERNAL_VALUES`) with the derivations at their owners: `derived_geometry.planform_aspect_ratio`/`wing_aspect_ratio`/`taper_ratio_from_planform`/`tip_ratio_from_planform`, `flight_envelope.gust_at_vf`, `select.wing_lift_slope_per_rad`/`effective_tail_inputs`/`resolved_full_down_aileron_deg`, `flap.resolved_ng`, `engine.effective_engine`/`resolved_engines`, `airloads.resolved_tau`/`resolve_aero_surfaces`, `cg_cases.max_takeoff_weight` | `tests/test_derive_override.py::test_every_collapsed_path_is_linked_and_resolvable` (OV-11: every member carries `derived_from`, `governs` and a resolver) + `::test_no_owned_quantity_copy_lacks_its_link` + the G-OV-2 derive-equals-owner identities (rel 1e-9; NG/LIMNZ exact) + the G-OV-3 defect-dies set |
| **Fields the user must state are never filtered off the oracle pages** (#98, C210-46/49/29) — the OG-2/OG-5 reduction may omit only a field whose declared default is a real answer. Two classes are not: a **row selector** (a `name`/`surface` leaf on a list record — a page resolves a scalar selector positionally, never a row's, so hiding it hardcodes every row), and a **sentinel default** (a value the consumers refuse, assume-with-a-note or leave a free body open on — "leave it at its default" is not available). Both are rendered (`supplied=True`, each mark demonstrated in `tests/test_oracle_inputs.py`); an **empty list table** captions what it hides, generated from the page's own field set, never hand-written | `sloads/field_registry.py` (`SENTINEL_DEFAULTS` — the register of sentinel-default fields, each entry citing the consumer that refuses it; `ROW_SELECTOR_CHOICES` — the fixed row-selector vocabularies, owned in `models/inputs.py` as `TAB_SURFACES`/`TAIL_SURFACES` with `require_surface` the refusal) + `oracle_app/form.py` (`_empty_table_note`) | `tests/test_field_registry.py::test_a_list_row_selector_is_always_asked` (structural: any hidden `name`/`surface` leaf on a built list record fails) + `::test_a_sentinel_default_field_is_always_asked` + `tests/test_selectors.py::test_the_tab_component_map_matches_the_vocabulary` + `tests/test_oracle_gui.py::test_an_empty_list_table_says_what_it_hides` |
| **One summary-table shape per module, both channels** (#95, C210-8/26/27 — owner directive: "one line per case, and every summary table so far revised"; CSV ruling 2026-08-26: the screen and the module CSV are the same rows) — the shape a module's conditions summarise in is registered once and every channel renders through the one dispatch: SELECT one row per condition with its per-case SF (sharing `governing_loads_table`'s one-line core, M2-4), WTENV one row per (weight, station) point, everything else the data-shaped generic floor (all-empty columns dropped). Re-shaping one channel alone prints the same data two ways | `sloads/report/render.py` (`summary_rows` — the dispatch; `SUMMARY_SHAPES` — the per-module registrations, `critical_rows` / `weight_station_rows`; `_union_rows` — the shared one-line core; `SUMMARY_GROUP_BY` — the screen's per-component grouping, presentation only) — read by `io.load_cases_csv`, `oracle_app/results.py` and `app/views/results_review.py` | `tests/test_summary_shapes.py` (`test_the_select_csv_is_the_screen_table`, `test_the_oracle_page_shows_the_same_rows_the_csv_holds`, `test_the_dispatch_is_the_single_source_of_summary_shapes`, `test_select_load_cells_match_the_governing_loads_table`) |
| **The wing scalars every slice used to copy** — MAC, reference area S, the 25 %-MAC station and waterline, the wing plane (root waterline + dihedral), and the tricycle-gear geometry. They were fields on `flight_loads`/`wing_mass`/`landing`, filled from geometry on every run and never persisted, so one number was editable in up to four places and two modules resolved the wing area with **opposite** precedence (note 33 §2.1). Removed as fields (note 33, DS-1): resolved at the point of use, and absent geometry is a refusal naming the page rather than a silent zero | `sloads/derived_geometry.py` (`wing_reference` / `require_wing_reference` / `wing_plane` / `planform_area_sqft` — the strip integral itself, #70; `require_integrable_planform` / `require_positive_planform_area` — its precondition, #71: five functions walk the edge polylines strip by strip and each one used to decide for itself, so two carried the check, one carried half of it and two carried none and answered a half-entered planform with a raw `IndexError`; the callers keep only their *policy* for an absent planform) + `sloads/modules/landing.py` (`gear_geometry`) | `tests/test_field_registry.py::test_no_quantity_regains_a_second_field` (the surviving multi-copy quantities pinned **by name**, not counted) + `::test_the_consolidated_quantities_have_exactly_one_field` + `tests/test_derived_geometry.py::test_no_module_integrates_the_wing_planform_behind_the_resolvers_back` (all of `sloads/` since #70 — it scanned `modules/` alone, so `validation.py` grew a third copy unseen; checked against a deliberate violation) + `::test_the_landing_and_speeds_wing_areas_agree_on_every_fixture` + `::test_every_strip_sweep_asks_the_precondition_owner` + `::test_a_mid_entry_planform_is_refused_by_name_not_by_traceback` (every module, every fixture, every surface, in each state a planform passes through while it is being typed) |
| **The two quantities that were persisted twice** — the MC/MD shoulder altitude (`speeds.shoulder_altitude_ft`; the MACHLIM copy let the Mach-limit table start at one altitude while MC/MD were derived at another) and SELECT's airplane length LF (`geometry.empennage.airplane_length_in`; each tail carried its own for its own inertia default). Retired at v55 (note 33 §8, #52): the hop that folded each pair kept the value that governed the shipped output and warned on disagreement, and went out with the rest of the chain at #93 — the shipped files were re-stamped through it, so what is left to guard is that neither quantity regains a second field | `StructuralSpeedsInput.shoulder_altitude_ft` (passed to `mach_limit_lines` as an argument beside MC/MD) + `sloads/derived_geometry.py` (`airplane_length_in`) | `tests/test_field_registry.py::test_no_quantity_regains_a_second_field` (the pinned set shrank by these two) + `tests/test_mach_limit.py` (Appendix A p160 unchanged) |
| **GW-BASIC `INT()` semantics** — `INT()` returns the largest integer ≤ x (floor); Python's `int()` truncates toward zero. They agree on non-negative arguments and differ by exactly one unit on every negative one, so a port that spells one as the other is correct only until the truncated quantity first goes negative — which 23.361(b)(1)'s reported stoppage torque is *by construction* (reaction torque is reported negative, §5), and where the port under-reported by 1 ft-lb in the non-conservative direction (CR-B-3, #40). Both truncation forms — whole-integer and the 3-decimal `INT(v*1000)/1000` — read the owner rather than re-deriving it per site (the open-coded copies in `engine.py`, `landing.py`, `wing_inertia.py`, `weight_estimate.py` were the defect class) | `sloads/basic.py` (`basic_int` / `basic_trunc3`) | `tests/test_basic_semantics.py::test_basic_int_floors_where_python_int_truncates` + `::test_no_open_coded_basic_int_in_the_calc_modules` + `::test_the_three_decimal_idiom_has_one_owner` + the closure gates `tests/test_engine.py::test_361_b1_closes_on_the_angular_momentum_formula` / `::test_361_b1_torque_is_floored_as_basic_int_did` |
| **How an iterative solve ended** — a bounded fixed-point search reports **converged**, **clamped** or **failed**, never just its last iterate. *Clamped* is the iterate reaching a fixed point outside its acceptance band, so no further trip can move it: on `atr42_100` that is the nine Mach-capped stall-limited corners decision **D-30** ruled ordinary flight (**23.333(b)** applies the manoeuvring envelope "except where limited by maximum (static) lift coefficients"), and exiting on it is bit-identical to spinning the loop out. *Failed* is trips exhausted with the iterate still moving, and **raises** (`SolverFailure`, a `ValueError` per the error contract) — a load is never reported from a solve that did not close. The clamped set is the one owner of that predicate, so the marker #32 publishes reads the state the balance reached rather than re-deriving it from the published CL (#33; the silent shape was `_balance`'s two loops, WINGINER's root density and FLAPLOAD's slipstream search) | `sloads/convergence.py` (`SolveState`, `SolverFailure`, `solver_failure`) + `models/results.py` (`EnvelopeResult.clamped_cases` / `is_clamped`, derived and never persisted) | `tests/test_convergence.py::test_no_bounded_search_in_the_package_falls_out_in_silence` (an **AST** walk: a trip-counted loop that `break`s and has no `else: raise` fails, or is classified with its reason) + `::test_a_clamped_solve_is_a_fixed_point_not_an_abandoned_search` + `::test_every_shipped_fixture_balances_or_says_why` (the nine pinned by condition/CG/altitude) + `::test_an_unreachable_load_factor_is_refused_instead_of_reported` |
| **Which balanced cases the pre-closure residual acceptances apply to, and at what value** — the ground (23.471-23.499), unsymmetrical-h-tail (23.427(a)) and powered families are exempt because their pre-closure `Fz`/`My` **is** an applied load in full; the lateral family is **not**, because what 23.441/23.443 exempts is `Fy`/`Mz` and neither appears in the two gated fractions. Every surface that summarises a *worst* residual reads this predicate, so the report, the Balanced Cases page, the deck `$` header and the case-table note cannot disagree about what the maximum was taken over (CR-C-2, #41 — they did: 143.885 % in §6, 100.000 % on the page, 0.624 % in fact) | `sloads/modules/balance.py` (`residual_gate_applies` + `residual_gate_exemptions` + `residual_gate_family`, and the two acceptances themselves: `RESIDUAL_GATE` 1 % for pitch, `FORCE_RESIDUAL_ACCEPTANCE` 2.5 % for force — owner's decision 2026-08-22, the value `tests/test_balance.py` already enforced as its hard stop, since the balanced model has no printed oracle behind it; the per-fixture `_FORCE_RESIDUAL_RATCHET` stays test-side as the regression guard, and a **clamped** case, out of trim by exactly the un-applied non-wing axial force, is split out by `residual_gate_family` and gated per case) | `tests/test_report_content.py::test_the_balanced_sections_residual_verdict_is_over_the_gated_family_only` (the **rendered** sentence, on a ground-assembling fixture) + `tests/test_balance.py::test_the_residual_gate_family_is_the_predicates` + `::test_the_judged_family_excludes_the_clamped_cases` |
| Deliverable unit sets | `units.deliverable_units` | `tests/test_deliverable_units.py` (identity, consistency, channel) |
| **Human-channel Imperial→SI display factors** (one row per dimension; `SI_PER_IMPERIAL`, `UNIT_LABELS`, `_RESULT_TO_SI`, `_SI_BY_QUANTITY`, `_SCALAR_TO_SI`, `_KIND_FACTORS` and `report/content._EXTRA_DIMENSIONS` are *views* of it — finding (d)/CH-7, 2026-08-17) | `units.HUMAN_SI` (every factor a named constant, products derived: `FT2_TO_M2 = FT_TO_M**2`, `SLUG_FT2_TO_KG_M2 = FT_LB_TO_N_M`, …) | `tests/test_units.py::test_every_si_view_reads_the_one_owner` + `::test_si_factor_literals_have_one_owner` |
| **Every shared physical constant and suite-internal unit factor** — ρ₀ (`0.002378 slug/ft³`), the atmosphere (σ **and** the speed of sound; FLTLOADS' private 518.688 °R retired), `G`, `DEG_PER_RAD`/`RAD_PER_DEG`, `IN_PER_FT`/`IN2_PER_FT2`, `KT_TO_FPS`, `FT_LB_S_PER_HP`/`HP_TO_TORQUE`, dynamic pressure (`dynamic_pressure_psf`/`eas_from_dynamic_pressure`, the `.BAS` `V²/295`), the FAR 23.341(c) gust numbers (`gust_alleviation_factor`, `GUST_LOAD_FACTOR_DIVISOR` 498). **Value policy: exact by default** — a `.BAS`-truncated value survives only as a named `*_SUITE` twin beside its exact owner with the printed oracle that pins it cited (today one: `KT_TO_FPS_SUITE` for `VSF`, the ENGLOADS gyro-thrust `/101.2`); each survivor and each value move has a line in `02_approved_corrections.md`. A per-module engineering parameter (a cited FAR ratio, a tolerance) stays in its module — but a value that has an owner is never re-declared (`_DEG = 57.3`, `_G = 32.2`, `_SQIN_PER_SQFT` were the defect class; CH-6 generalised, issue #26, 2026-08-17) | `sloads/constants.py` (`flight_envelope.density_ratio`/`_speed_of_sound` delegate — M4-23) | `tests/test_constants.py::test_imperial_factors_have_one_owner` (the literal set — 57.3/57.29…, 114.6, 32.2/32.17, 295, 498, 0.88/5.3, 144, 550/33000, 1.688/1.15·88, 518.x/35332/575/29.02436/0.003566, 3.1416, 0.002378 — in code lines of no other file under `sloads/`, `app/`, `app_shell/`, `oracle_app/`, `scripts/`, `cli.py`) + `::test_no_private_aliases_of_owned_constants` + `::test_exact_by_default_values` + `::test_sigma_is_read_from_the_shared_atmosphere` + `::test_flight_envelope_reads_the_shared_speed_of_sound` |
| **What unit a project-JSON field carries** — a **three-way, total** classification of every numeric schema leaf: *converted* (a quantity with a factor), *aviation-standard* (KEAS/ft, stated and never converted), or *dimensionless* (with its reason). Name-keyed, so a force and a weight sharing the `_lb` suffix must be classified apart — the factors are ~9.8× different. A classified key converts whether its value is a scalar or a list of numbers; an `[[a, b], …]` curve is classified per member, because the planform edges are (station, station) and a spanwise curve is (station, coefficient). **The totality is the point** (2026-08-19): the guard used to ask *does this name look dimensional?* from a suffix regex, so a length whose name breaks the suffix convention was invisible to it rather than reported by it — thirty-four were, `xt25` showing 261.0 unconverted beside `htail_semispan_in`'s 1856.7 mm on the same record | `units._PROJECT_FIELD_KIND` + `units._PROJECT_PAIR_KIND` + `units.AVIATION_STANDARD` + `units._DIMENSIONLESS_RULES` + `units._NOT_DIMENSIONAL`, read through `units.field_classification` | `tests/test_project_units.py::test_every_numeric_project_field_is_classified` — walks the **type graph** from `Project`'s input slices (the set from `field_registry.schema_paths`, not one example's, so `one_engine_out` and `tail_mass` are covered), not the fixtures, so a field no project has set is still covered (how `thrust_lb` slipped: unclassified, unset everywhere, and lossless in round trip) + `::test_no_field_is_classified_twice` + `::test_every_classification_is_of_a_field_that_exists` + `::test_every_exemption_states_a_reason` + `::test_every_dimensionless_rule_still_covers_something` |
| **The `constants.py` / `units.py` demarcation** — `constants.py` holds physical constants, FAR-mandated numbers and every **Imperial↔Imperial** factor; `units.py` holds **only the Imperial↔SI boundary** (base factors, `HUMAN_SI` and its views, `deliverable_units`, the deck channel's ISO gravity `G_MM_S2`/`G_IN_S2` — deliberately exact and distinct from `constants.G`, see the note there); `units.py` imports `constants`, never the reverse (`FT_PER_NMI` states its SI origin as a comment and is asserted against `units.FT_TO_M` in the guard, so kt→ft/s can live on the Imperial side) | `sloads/constants.py` ↔ `sloads/units.py` | `tests/test_units.py::test_si_factor_literals_have_one_owner` (every factor `units.py` declares, derived from it rather than transcribed, matched numerically against the float literals of `sloads/`, `app/`, `app_shell/` and `oracle_app/` — the two hand-kept regex lists it replaced each missed factors the other had and neither read the GUI packages, PB-12) + `tests/test_constants.py::test_si_factors_live_only_in_units_py` (the dependency direction: no `units` import in `constants.py`) |
| **Deck `LOAD`/`SUBCASE` number a deliverable quotes** (which minter, which deck family, and what a case without one in that family shows) | `case_ids.deck_load_id` (+ `case_label` for display; `export/sbeam_bridge.LOAD_ID_COLUMN` names the two columns) | `tests/test_case_ids.py::test_the_index_quotes_the_decks_own_numbers` (against the decks' own text) + `::test_a_case_in_the_index_always_carries_at_least_one_deck_number` + `::test_a_handed_case_is_numbered_in_the_assembled_deck_only` + `::test_the_report_case_index_states_the_same_pairs_as_the_csv` |
| Export axes/scale | `export/coordinates.py` | `tests/test_sbeam_bridge.py::test_grids_match_station_geometry` + closure/SF tests |
| **Centreline reflection** (`y -> -y`; force is a true vector, moment an axial one) | `export/coordinates.py` (`reflect_point`/`reflect_force`/`reflect_moment`/`reflect_side`) | `tests/test_balance.py::test_the_reflection_operator_is_an_involution` + `::test_the_handed_twins_are_mirror_images` |
| **The applied wing load set's moments → body axes** (all six components published; `Fy`, `Mx`, `Mz` are structural zeros, printed) | `export/sbeam_bridge.py` (`applied_body_moments`, over `coordinates.bending_moment_vector`) — the report's Appendix B.1 and `wing_applied_loads.csv` are both views of it and neither restates the sign | `tests/test_sbeam_bridge.py::test_the_applied_set_states_all_six_components` + `::test_the_applied_set_reproduces_the_whole_vmt_at_every_station` + `tests/test_oracle_report.py::test_the_appendix_table_and_the_exported_csv_are_one_load_set` |
| **Empennage local frame → airplane axes** (h-tail spans `y`/loads `fz`/twists `myy`; v-tail spans `z`/loads `fy`/twists **`mzz`**; a span-axis *axial* load follows the span, so `y` for the h-tail and `z` for the fin) | `export/coordinates.py` (`tail_station_to_airplane`/`tail_force_to_airplane`/`tail_torsion_to_airplane`/`tail_axial_to_airplane`) | `tests/test_tail_transforms.py` (direct: axial follows the span, torsion sign closes on `r × F`, T-tail transfer is `Fz`/`Myy`) + `tests/test_export_equilibrium.py::test_vtail_span_deck_resultants` + `::test_tail_deck_resultants` (the chordwise family takes the same map — D-R4) |
| **An empennage surface's mass, and which acceleration acts on it** (derived from the tagged items; the fin's bending factor is lateral, its axial factor vertical) | `sloads/mass_distribution.py` (`tail_surface_weight`) + `modules/tail_span.py` (`lateral_load_factor`, `distribute`'s `n_normal`/`n_axial`) | `tests/test_tail_span.py::test_the_surface_weight_is_derived_from_the_tagged_items` + `::test_the_fin_lateral_inertia_is_exactly_the_weight_ratio_of_the_air_load` + `::test_no_shipped_fixture_produces_an_air_only_htail_deck` |
| **Empennage planform vs. the scalar area/span** (1 % agreement; scalars stay oracle-authoritative) | `sloads/tail_geometry.py` (`resolve_tail_planform`/`validate_tail_planform`) | `tests/test_tail_geometry.py` |
| **How a control-surface load enters its parent surface** (smeared vs. discrete; the load is SELECT's where published and TAILDIST-derived-and-marked where not; the hinge moment's arm is a third of the aft-of-hinge chord and the actuator reacts `−HM`) | `modules/tail_span.py` (`control_load_mode`/`control_load_parts`/`control_point_loads`/`control_centre_of_pressure`) — `modules/select.py` owns the load itself (`elevator_load_parts`/`rudder_load_parts`) and `modules/taildist.py` the hinge line (`surface_geom`) | `tests/test_tail_span.py::test_the_two_modes_apply_exactly_the_same_total_force` + `::test_the_hinge_moment_is_a_third_of_the_aft_of_hinge_chord` + `::test_the_hinge_and_actuator_torsion_is_the_load_at_its_own_cp` + `::test_the_cross_mode_torsion_difference_is_the_chordwise_relocation` |
| **The T-tail transfer** (gated on `tail_type`; the set is the concurrent balancing h-tail load + its inertia, applied at the fin's **last** `GRID`; `Fz`/`Myy` only, in airplane axes) | `modules/tail_span.py` (`ttail_transfer`) + `export/coordinates.py` (`ttail_transfer_to_airplane`) | `tests/test_tail_span.py::test_only_a_t_tail_carries_a_tip_transfer` + `::test_the_transferred_moment_is_the_two_lever_arms` + `tests/test_export_equilibrium.py::test_vtail_span_deck_resultants` |
| **Vertical-tail root waterline** (where the fin sits; explicit → T-tail relation → fuselage top → a loud zero) | `sloads/tail_geometry.py` (`fin_root_waterline`) — read by both the load path and the three-view | `tests/test_tail_geometry.py::test_the_three_view_and_the_load_path_place_one_fin_once` + `::test_the_fin_root_waterline_is_pinned_per_fixture` |
| **Where the h-tail beam is reacted** (T-tail fin-tip joint → fuselage outline interpolated at the h-tail LRA station → the innermost strip pair; the **maximum** section is never used, and the outline branch is marked assumed) | `modules/tail_span.py` (`htail_attachment`, returning `HTailAttachment`) + `derived_geometry.py` (`fuselage_width_at` — the single owner of "how wide is the body *here*", as `fuselage_summary` is of "how wide at most") | `tests/test_tail_span.py::test_the_ttail_htail_is_reacted_at_the_fin_tip_not_at_the_fuselage` + `::test_the_attachment_interpolates_the_body_at_the_htail_and_never_its_maximum` + `::test_the_attachment_falls_back_to_the_strip_pair_without_a_body_outline` |
| **Body drag waterline** (where the assembled model applies the airplane's non-wing drag; explicit → the wing reference plane with a loud note. Deliberately **two** branches: the suite has no body-centreline datum, and `root_waterline_z` is the *wing* root — deriving from it puts `ga6_normal` over the 1 % pitch gate) | `sloads/derived_geometry.py` (`body_drag_waterline`) — the only free parameter of `balance.body_axial_set`, whose magnitude is fixed by definition and whose fuselage station carries no pitching moment | `tests/test_balance.py::test_the_body_drag_waterline_is_stated_and_is_the_only_free_parameter` + `::test_the_applied_axial_force_is_the_airplanes_drag_not_the_wings` + `::test_the_longitudinal_closure_is_the_trims_own_drag` |
| **Entered engine thrust** (one user-entered value per engine, applied as an axial `FORCE` at that engine's hub — `prop_cg`, falling back to `engine_cg`, and a **refusal** when neither exists; `fx = −T`, §1's `x` being +aft; **flight cases only**, ground cases state the entered value and do not take it. Nothing balances it: `n_x = (D − ΣT)/W` and `q̇` carry it, so the 1 % pre-closure gate does not apply to a powered case's `My`. The thrust line is axial — the incidence/toe angles and every wake term stay parked with design note 21. An **asymmetric** entry yaws the airplane and is stated, not handled: no twin is minted from it, and a twin got from another source mirrors the installation — note 21 §4.4's parked decision) | `modules/balance.py` (`hub_thrust_set`, `HUB_THRUST_SOURCE`, `is_powered`, `hub_thrust`) — read by `export/lra_model.py`, which routes it to the engine member's hub node | `tests/test_hub_thrust.py` (G-1…G-11; G-3 the closed-form residual, G-4 `ΣT = D ⇒ n_x = 0`, G-6 the hub node with a zero transfer couple) |
| **Rigid-body relief field and the inertia tensor** (`f = −m(a + ω̇ × r)`; products of inertia stored as sums `Σw·a·b`, negated only in `matrix()`; weight-space `1/in`) | `sloads/rigid_body.py` (`InertiaTensor`/`inertia_tensor`/`relief_force`/`relief_moment`) | `tests/test_rigid_body.py::test_the_field_produces_exactly_minus_the_inertia_times_omega_dot` |
| **Which components the assembly spreads** (decides whose entered self-inertia joins the closure tensor — L-3) | `sloads/mass_distribution.py` (`assembly_distributes_mass`) | `tests/test_rigid_body.py::test_the_distributed_mass_predicate_is_the_wing_and_only_the_wing` |
| **A database row's reacted parts** (`wing_fraction` → the wing share and the `component` share, one position, weight and own inertias in the fraction; the only place a row becomes the masses the beams react — design note 29 WF-3) | `sloads/mass_distribution.py` (`reacted_parts`) — read by `distribution()`, `modules/balance.py`, `export/mass_cards.py` | `tests/test_mass_distribution.py::test_reacted_parts_splits_a_row_by_weight_and_inertia_at_one_position` + `::test_every_consumer_agrees_with_the_owner_on_the_wing_share`; validator `wing_mass_tie_open` (`tests/test_validation.py`) |
| **Whether a load set has a hand** (reads the *applied* distribution `Σ\|fy\|`, not the resultant, and pre-closure so it cannot feed on its own relief — L-6) | `modules/balance.py` (`is_handed`) | `tests/test_balance.py::test_the_handedness_predicate` |
| **The load-transfer rule** (a load at `p` applied at node `n` carries the exact couple `(p − n) × F` — every mover in the export channel is an instance: the gear point→trunnion transfer, the concentrated-mass offset couples, `sob_internal_loads`/`sob_collapsed_load`, the LRA model's routing) | `sloads/gear_loads.py` (`transfer_couple`, note 24 R-11 / note 25 LM-1), re-exported by `export/coordinates.py` so no export call site moves — it was implemented **twice, identically**, each copy's docstring claiming to be R-11's single owner, until #139 consolidated it onto the layer the calc side can reach | `tests/test_lra_model.py::test_the_transfer_couple_is_the_exact_lever_arm_cross_product` + `::test_the_transferred_set_has_the_balanced_decks_resultant` (the plan-07 invariant on the whole transferred set) |
| **Where a ground reaction acts** (design note 39 **AP-1**/**AP-2**) — Appendix A's printed column per family, one construction of the point, read by the transfer to the reference node, the gear free-body report and the landing module's emitted location. A load and its point are one statement; a second construction is how they come apart, and it did — the deck transferred cases 1–12 from the tyre while the manual applied them at the axle, with an exact transfer and a green suite on both sides of the disagreement (#139). **The word travels with the value** (#141, schema v59): the point is a vocabulary on `LoadValue.point`, exactly as the frame is, and the delivered CSV states it in an `Applied at` column beside a `Frame` column — before it, the point reached a standalone consumer as coordinates alone, the word living in a condition note and GUI captions the CSV drops | `sloads/gear_loads.py` (`application_point` / `application_point_of`, `AXLE` / `GROUND_CONTACT` / `POINTS`; `GearLegLoad.point`, `AppliedWheel.point`; carried out on `sloads/models.LoadValue.point`, read once in `report.render.results_to_rows`) | `tests/test_gear_report.py::test_the_application_point_is_the_manuals_printed_column` (against a transcription of the column, never against the code) + `::test_the_application_point_is_built_in_exactly_one_place` + `::test_the_ground_closure_reproduces_landloads_unbalanced_moments` (G-AP-1: `residual My − the G-7a lift moment == PITCHP` on every balanced ground case of every fixture, 1e-4 · n·W·MAC) + `::test_the_static_contact_patch_breaks_the_level_landing_gate` + `tests/test_landing_deliverable.py::test_the_delivered_csv_states_its_frame_and_its_application_point` + `::test_the_csv_point_is_appendix_as_printed_column_case_by_case` + `::test_the_reference_node_names_no_application_point` + `::test_every_landing_value_names_a_known_point_or_none` + `::test_a_module_that_names_neither_gets_neither_column` |
| **The frame a ground load is stated in**, its words, and the rotation between them (design note 38 **GF-6**/**GF-7**). LANDLOAD prints its whole matrix twice — "VALUES ARE WITH RESPECT TO GROUND LINE -- DENOTED BY P (PRIME)" and "VALUES ARE WITH RESPECT TO AIRPLANE DATUM" — and the replication carried both sets and named neither, while the deck consumed one of them. The frame now rides on the value (`LoadValue.frame`, schema v58), the render boundary reads it to keep the delivered CSV in the body frame while the text report keeps both, and both GUIs caption their tables from the one function that has the manual's words. `ρ` is **measured** from a case's own two resolutions of one reaction, never written out as `±GRA`: the two sign defects of #133 and #134 were both a ground angle typed longhand | `sloads/frames.py` (`GROUND_LINE` / `AIRPLANE_DATUM`, `caption`, `is_report_only`, `rotation_deg`, `to_airplane_datum` / `to_ground_line`) | `tests/test_landing_deliverable.py::test_the_delivered_csv_is_body_frame_and_the_text_report_keeps_both` (both directions) + `::test_the_frame_split_is_owned_by_one_predicate` + `::test_neither_gui_writes_the_frame_words_itself` + `::test_every_landing_value_names_a_known_frame_or_none` |
| **The delivered ground load: three wheels, each with its point** (design note 38 **GF-6**). Nose, left main and right main on **every** case — an unloaded gear at zero rather than omitted — built *from* the deck's own wheels rather than beside them, so the statement a stress model reads and the load the deck applies cannot come to differ. The LANDLOAD case families (lift / one-wheel / side / balanced) are owned by the module that draws them | `sloads/gear_loads.py` (`DeliveredLeg`, `delivered_legs` / `delivered_gear_legs`, `MAIN_LEFT` / `MAIN_RIGHT`); `sloads/modules/landing.py` (`GROUND_LIFT_CASES`, `GROUND_ONE_WHEEL_CASES`, `GROUND_SIDE_CASES`, `BALANCED_GROUND_CASES`, `side_partner`, `attitude_of` — moved here from `balance`/`gear_loads` by #134) | `tests/test_landing_deliverable.py::test_every_case_of_every_example_carries_all_three_legs` + `::test_the_unloaded_wheels_are_the_families_that_should_be_unloaded` + `::test_the_three_delivered_legs_sum_to_the_printed_page` + `::test_the_side_family_puts_different_side_loads_on_the_two_wheels` |
| **The named-node identity contract** (`$ SLOADS-NODE <family> <side>` on every special GRID; families each in their own registered band; import maps by tag with nearest-node as the marked-assumed fallback and validates tagged positions at `LRA_IMPORT_TOL_IN`) | `export/lra_model.py` (tags + families, decision BM-5 / note 24 R-10) + `export/bands.py` (the bands) + `export/lra_import.py` (`read_lra_model`/`validate_imported_model`) | `tests/test_lra_model.py::test_the_skeleton_carries_every_named_node_family` + `::test_an_exported_model_reimports_with_every_family_mapped` + `::test_a_divergent_tagged_node_fails_loudly` + `tests/test_bands.py` |
| **What a balanced case's source-case number is called** (`BalancedCaseResult.vn_case` holds FLTLOADS' V-n point on a flight case and LANDLOAD's case number on a ground one — two tables that both number from 1, so the label must name the family; short form for the case map and the parenthesised titles, none for the ground stem) | `modules/balance.py` (`source_case_name` / `case_source_name`, family from `is_ground`) | `tests/test_balance.py::test_no_surface_calls_a_ground_case_a_v_n_point` + `::test_the_source_case_label_has_one_owner` |
| **What makes a case *lateral*, and how lateral** (the sole readers of the `vtail-air` source tag, for the deck header, the row table and the gates) | `modules/balance.py` (`is_lateral` / `fin_load`) | `tests/test_balance.py::test_the_lateral_cases_are_pinned` + `::test_the_symmetric_half_of_a_lateral_case_still_closes` |
| **What the Export bundle carries** — the zip's member list, each member named together with the manifest row that states its basis. The Export page loops over this owner rather than deciding its own members, so Appendix A's two SHALLs (`SUMMARY_REPORT.md` §4.7 — name every file, name no absent file) are gated against the **real namelist** in both directions instead of against a hand-kept list. A row whose artifact can refuse (the LRA model) is gated on the artifact *building*, never on its inputs existing (CR-C-1, #42 — three members had drifted past the manifest: `lra_model.bdf` and the report's own `.tex`/`.pdf`) | `sloads/report/bundle.py` (`bundle_members`, `bundle_zip_bytes`, `manifest_name_for`) + `sloads/report/content.py` (`_manifest_rows`, and `_lra_model` for the refusal gate) | `tests/test_bundle_manifest.py::test_every_file_the_bundle_carries_is_named_by_the_manifest` + `::test_the_manifest_names_no_file_the_bundle_does_not_carry` + `::test_a_refused_lra_model_is_neither_shipped_nor_manifested` + `::test_the_page_writes_no_zip_member_of_its_own` + `tests/test_report_content.py::test_every_manifest_row_states_the_basis_its_file_actually_carries` (the basis cell pinned by text, not by filename — CR-C-3) |
| **Report sign-convention statements** (the "Axes and sign conventions" section: prose, table rows, the three static TikZ figures) | `sloads/report/conventions_tex.py` | `tests/test_report_conventions.py` (frame fragments vs `export/coordinates.py`; §3.3 sentences verbatim; SC-1…SC-6 cited; figures static/greyscale/ASCII) |
| **Deck id bands** (every GID/EID/SID run: who owns it, how wide, and that no two collide) | `export/bands.py` (`BANDS`, `Band.allocate`) — `case_ids.SUBCASE_BLOCK` allocates the per-component subcase SIDs and the registry mirrors it | `tests/test_bands.py::test_no_two_bands_overlap` + `::test_every_export_base_constant_is_a_registered_band` |
| **The V-n envelope and the critical set a module works from** ("the persisted `Project.envelope`, else built from the flight-loads inputs" — one rule, one place, because `registry.run_all_modules` never assigns `Project.envelope` and every deliverable goes down that path). The owner also **checks what it hands back**: a persisted matrix naming a CG case the project no longer carries is refused, not read as a case at zero weight (CR-B-4, #43 — it used to become `nx = 0.0` in a WINGINER case and a dropped candidate in the 23.421 h-tail search) | `modules/select.py` (`default_envelope` + `_check_envelope_cg_cases`, `default_critical`, the per-read `_cg_weight`/`_cg_case`, and `vn_points`/`vn_by_case` for consumers with a documented in-band fallback) — `modules/wing_inertia.py` (`wing_case_sources`) resolves both once per build and threads them | `tests/test_envelope_owner.py::test_no_calc_code_reads_project_envelope_outside_the_owners` (AST scan of `sloads/`, allowlist with stated reasons) + the per-site behaviour gates in the same file + `tests/test_select.py::test_a_persisted_envelope_naming_a_lost_cg_case_is_refused` |
| **Platform-stable deliverable bytes** (a byte in a deck or report must not depend on libm build, FMA, or the Python version's `sum()`: (a) **every** keyed pick — a critical case, a nearest node, a pivot row — between candidates whose keys agree to `TIE_REL` relative goes to the **first in list order**, never to whichever landed an ulp higher, and no built-in `min`/`max` with a `key=` argument survives anywhere in `sloads/`; (b) a FORCE/MOMENT/GRID/CONM2 component below `_TOL ×` its own card's scale prints as `0.000000E+00`, never as its residue and never as `-0.000000E+00`; (c) every float summation is `math.fsum` — exactly rounded, so identical on 3.10/3.11/3.12 — never the built-in `sum()`, which 3.12 compensates and earlier versions do not; (d) a printed report/CSV cell is **quantized to twelve significant figures before it is formatted**, so the choice between the formatter's two far-apart spellings — an integral value in full, everything else at four significant figures — cannot turn on the last bit: `-687258.0` printed `-687258` and `-687257.9999999999` printed `-6.873e+05`, and both shipped in one landing case, because macOS and glibc disagree in the last ulp of `sin`/`cos` — #147) | `picks.py` (`extreme` — the owner of every keyed pick in the package) + `export/sbeam_bridge.py` (`_fmt3` for every vector card; `_closed` for stated totals) + `math.fsum` at every summation site in `sloads/` + `report/render.py` (`format_value`, the owner of every printed human-channel cell) | `tests/test_platform_stability.py::test_extreme_pick_is_first_in_order_across_a_platform_ulp_tie` + `::test_every_keyed_pick_in_sloads_goes_through_picks_extreme` (an **AST** walk over the package: a built-in `min`/`max` call with `key=`, however it is spelled — a pick written as an accumulation loop is outside any static walk and outside this row's claim) + `tests/test_sbeam_bridge.py::test_card_components_snap_dust_and_negative_zero` + `tests/test_platform_stability.py::test_every_float_summation_in_sloads_is_fsum` (the latter two grep for bypasses; the pick guard walks the AST — review 2026-08-20 CR-B-1: a substring grep missed a live `(min if want_min else max)(…, key=…)` and four multi-line calls) + `tests/test_platform_stability.py::test_no_printed_deliverable_cell_hangs_on_the_last_ulp` (every value of every condition of the trig-heaviest module of the example that failed, invariant under ±4 ulp) + the frozen Imperial digest run on the Linux CI matrix |
| **No silent defaults in the export namespace** (a result field is read as the typed attribute it is; a name lookup is an explicit map that refuses an unknown key; `getattr(obj, name, default)` does not occur — CH-2, 2026-08-16) | every `sloads/export/*.py` reader; `00_program_overview.md` §Error handling states the rule | `tests/test_sbeam_bridge.py::test_the_export_package_takes_no_silent_defaults` (AST walk) + `::test_tail_span_export_refuses_an_unknown_component` |
| **The wing-body sideslip derivatives and where they act** (`Cy_β`/`Cn_β` per degree, suite sign, `Cn_β` about `xw`; the side force at the body side-area centroid, the free couple closing the moment; DATCOM's yaw sign negated into `+mz` = nose to port — L-7) | `sloads/lateral_body_aero.py` (`estimate`, `transfer_cn_beta`) + `modules/balance.py` (`lateral_aero_terms` / `body_aero_loads`, the only writer of the `body-aero` source) | `tests/test_lateral_body_aero.py` (Digital DATCOM printed oracle, G1) + `tests/test_l7_lateral_balance.py` (G2–G12) |
| **A lateral condition's sideslip and the fin's own derivatives** (`beta_deg` in the SC-1 sense, `cy_beta_fin`/`cn_beta_fin` about `xw`, from the same `AVT`/`S_v`/arm as the load; the balance never re-derives them — L-7.6/L-7.11) | `modules/select.py` (`select_vtail`, `_vt_side_gust_terms`, `fin_sideslip_derivatives`) | `tests/test_l7_lateral_balance.py::test_select_publishes_the_sideslip_and_the_fin_derivatives`, `…::test_a_persisted_critical_set_without_beta_says_so_instead_of_guessing` |
| **Air viscosity / Reynolds number** (Sutherland on the suite's own temperature law, TAS — L-7.13; `standard_temperature_f` is the lapse-rate owner) | `sloads/atmosphere.py` (+ `constants.standard_temperature_f`) | `tests/test_lateral_body_aero.py::test_sea_level_viscosity_and_reynolds` |
| Case IDs | `sloads/case_ids.py` | `tests/test_case_ids.py` |
| **Where a %MAC is measured from, and the relation itself** (`X = XLEMAC + (pct/100)·MAC` and its inverse — plus the prior question the relation cannot answer for itself: *which* XLEMAC and MAC. The typed `weight.envelope.xlemac`/`mac` pair wins, else the WINGGEOM planform (the C210-13 blank-derive fallback), and the resolved reference carries which of the two it was so a display can say so. Aerodynamic sites — the tail-volume neutral point, the 25%-MAC station — deliberately pass a planform reference rather than resolve one, and share the relation only) | `sloads/derived_geometry.py` (`MacReference`, `mac_reference`, `require_mac_reference`, `pct_mac_to_station`, `station_to_pct_mac`) | `tests/test_derived_geometry.py::test_no_second_spelling_of_the_mac_station_relation` (AST scan over `sloads/`, `app/`, `app_shell/`, `oracle_app/` for arithmetic combining an XLEMAC-ish name with a MAC-ish one outside the owner) + `::test_the_report_column_and_wtenv_measure_the_same_wing` (an override made to disagree with the planform on purpose — no shipped example carries one, which is why the two frames could part unnoticed) |
| **Airspeed measure conversion** (KEAS ↔ KCAS ↔ KTAS over the suite's own atmosphere, both directions of one relation: KEAS is what the manual and every module mean by a speed, KCAS is what a POH and a placard quote) | `sloads/constants.py` (`convert_airspeed`, `eas_from_airspeed`) | `tests/test_constants.py::test_eas_from_airspeed_inverts_convert_airspeed_exactly` + `::test_airspeeds_order_themselves_the_way_altitude_makes_them` |
| Load-case row keys | `sloads/load_keys.py` | **flagged — see §8** |
| Data dictionary | `docs/generate_data_dict.py` (generated doc) | `tests/test_data_dictionary.py::test_committed_doc_matches_generator` |
| ULT unit mapping | `report/render.py` `_ULT_UNITS` | render/SF tests in `tests/test_report_render.py` |
| **The mass slice a project carries** (`Project.mass` is WTONECG over `weight.items`, rebuilt by one refresher after every write of the items — the `app/` Weight page's Apply, the oracle form's persist, gate G5's reduction — and `None` when the items derive nothing; never a second fact an ulp off its source) | `sloads/derived.py` (`DERIVED_SLICES`, `refresh_derived`) + `modules/weight_onecg.py::refresh_mass` | `tests/test_derived.py::test_every_example_stores_the_mass_it_derives` (bit-identical on every shipped example) + `tests/test_oracle_inputs.py::test_the_reduction_drops_the_stored_slices_and_rederives_the_mass` + `tests/test_oracle_journey.py` (a typed-from-blank twin reaches One Engine Out) |
| **Selector names and coded inputs** (a surface / CG case / coefficient-set name is a key: seeded meaningfully, unique by `same_name` — case and edge spaces forgiven — and refused when duplicated rather than collapsed; a FAR 23 category or strut type is a code from its table, upper-cased at construction and refused by name when unknown, never read as the default) | `sloads/selectors.py` (`NAME_SEEDS`, `keyed`, `duplicate_selectors`) + `models/inputs.py` (`same_name`, `CATEGORIES`, `STRUT_TYPES`, `normalise_code`) + `field_registry.CODED_FIELDS` | `tests/test_selectors.py` (every supplied `.name` has a seed; every coded path is a registered `str`; SELECT refuses the review's blank-name reproduction; the page withholds results) |
| **How many digits a GUI shows a value at** (a dimensionless coefficient at `%g`, so FLTLOADS' `0.004128` is not displayed `0.0041`; a value with a unit at four decimals, where `%g`'s six significant figures would lose precision instead — precision is a property of the quantity, not of the page rendering it) | `sloads/units.py` (`display_format`, `DIMENSIONLESS_FORMAT` / `DIMENSIONAL_FORMAT`) | `tests/test_oracle_gui.py::test_no_renderer_writes_a_number_format_of_its_own` (AST scan over `oracle_app/` + `app_shell/`; `app/views/` is frozen pending #29) + `::test_a_coefficient_is_shown_at_the_precision_it_was_entered` |
| **What the airspeed unit is called on screen** (`KEAS`, one word — a renderer appends a unit as `label (unit)`, so a parenthesised unit string nests) | `sloads/units.py` (`KEAS`, re-exported by `app_shell/components.py` as the widgets' `fixed_unit=`) | `tests/test_oracle_gui.py::test_no_widget_label_nests_its_units_in_parentheses` + `::test_the_aviation_units_agree_with_the_shell` |
| **What a grid tells the user about committing a cell** (Streamlit's `st.data_editor` keeps the cell editor open on Enter and the next keystroke discards the value — upstream behaviour, reproduced in a bare app, so the remedy is one sentence and both GUIs must say the same one) | `app_shell/components.py` (`GRID_COMMIT_NOTE`) | `tests/test_oracle_gui.py::test_a_page_with_a_grid_says_how_a_cell_commits` (two-sided: every page that renders a grid says it, every page that does not stays silent) + `::test_the_grid_commit_note_is_spelled_once` (scans `app/views/` too, which is frozen pending #29 and adopts the note by import rather than by retyping it) |

When a new sign/unit/ID-sensitive quantity appears, create its owner + guard test first
and add the row here.

### 7.1 Handedness (plan 11 decisions B-6/B-7)

Every asymmetric load case has an **opposite-hand twin** — `+beta` yaw implies
`-beta`, an aileron roll right implies roll left, an engine-out on the left
implies the right. The convention, stated once:

* the twin is **derived by reflection at the balanced-case assembly**, never
  recomputed and never obtained by re-running SELECT or the V-n core — so the
  oracle-locked FAR 23 path never sees handedness at all;
* reflection is `y -> -y`. A **force** is a true vector, so only `fy` changes
  sign; a **moment** is an axial vector, so `mx` and `mz` reverse and `my` does
  not. Applying the force rule to a moment mirrors a rolling case into itself
  and negates its pitch — it balances, and it means nothing;
* handedness is a **suffix on the existing case id** (`W-05L` / `W-05R`), minted
  by the balance layer via `case_ids.handed_case_id`. The unhanded id remains the
  physical condition; this is not a new ID series (naming rule, 2026-08-05);
* a **symmetric case has no hand** and gets no twin: it is its own mirror image,
  and minting one would put the same load set in the deck twice. Whether a case
  has a hand is decided by **content, not by name** — one predicate,
  `balance.is_handed` (§7), asked of the **applied** set before closure.

**Worked example: the ±β empennage family** (plan 13 decision L-6, 2026-08-09).
The four vertical-tail conditions are the family this convention was written for,
and they exercise three parts of it the rolling family never did:

* **The predicate reads the distribution, not the resultant.** `ga6_normal`'s
  `YAW TO SIDESLIP` nets only −97.8 lb of side force out of parts worth −683
  (yaw) and +586 (rudder): `Σ|fy| ≈ 1270` against `|Σfy| ≈ 98`. A net-based test
  would mint a rudder-kick case **unhanded** on the strength of a
  near-cancellation and assemble it as a symmetric one — the same silent-symmetry
  failure plan 11 §10 records for `TORS`, reached from the opposite direction.
* **It is evaluated pre-closure.** From B8a-2 the closure gives any rolling case
  a lateral relief field, so a predicate reading the *final* load set would find
  lateral content in every case that rolls and hand all of them.
* **The applied set is odd under the mirror, not just the closure.** The port
  twin of a rudder kick is the opposite kick — the `−β` of a `+β` case — so the
  fin's `fy` **and** its `mz` torsion both reverse. A rolling case's applied
  loads are all symmetric, so nothing before B8a-3 tested that half of the
  reflection rule.

Ids follow the same suffix rule: `VT-01R`/`VT-01L` … `VT-04R`/`VT-04L`, from the
unhanded `VT-0n` SELECT already minted.

### 7.2 Empennage axes and bookkeeping (plan 09 decisions T-1/T-8)

* **The horizontal tail maps exactly like the wing** — span along `y`, air load
  `fz`, torsion `myy` about the load reference axis. **The vertical tail does
  not**: it spans along `z`, its air load is the **side force `fy`**, and its
  torsion is about its own span axis, so it is **`mzz`** — with the sign of the
  stored strip torsion *negated*, because `r × F` reverses for a side force.
  Both mappings have one owner (§7) and a drift guard; a fin deck written with
  the h-tail's convention parses, solves, and loads the fin in the one direction
  it is not designed for.
* **Half and full.** `SurfaceInput` polylines are one side of a symmetric
  surface, while every *scalar* tail quantity in the suite is whole-surface:
  `htail_area_sqft` is both sides, and SELECT's `LT25`/`LT50` are both-sides
  totals. So the h-tail compares `2 × polyline_area` against the scalar and its
  polyline span against the **semi**span; the v-tail is a single surface and
  compares both directly, with no factor. Owned by `tail_geometry`.
* **The h-tail beam is full span, tip to tip through the centreline**, reacted at
  the fuselage attachment stations — not a semispan table doubled. It is the only
  topology that carries the FAR 23.427(a) left/right asymmetry in one model, and
  it keeps SELECT's both-sides totals end-to-end with no factor-of-two seam.
* **Tail inertia is d'Alembert**: `−n · W_surface`, signed by the case's load
  factor **alone**, never "opposing the air load". The conditions that size a GA
  horizontal tail are down-load ones, so an opposing rule would relieve exactly
  those.
* **The fin has a vertical position, and it is never implicitly zero (B8a-1,
  2026-08-09).** The roll moment a fin side load makes about the CG is
  `−Fy·(z − z_cg)`, so the fin's root waterline is a first-order load quantity,
  not presentation. It is resolved once by `tail_geometry.fin_root_waterline` —
  explicit input, else the T-tail relation, else the fuselage top, else a zero
  that says so — and both the load path and the three-view read that one owner.
  A fin placed on the waterline datum is not merely imprecise: on `ga6_normal` it
  sat 64.5 in *below* the CG and reversed the sign of the moment.
  **The fuselage-top branch has a body datum (2026-08-16, closing the T-8a
  finding).** With a fuselage outline present the branch is
  `z_centre(x_fin) + height(x_fin)/2` — the section-centre line
  (`derived_geometry.fuselage_centreline`, note 24 R-4, itself defaulted from
  the body-drag waterline and marked assumed) plus half the **local** body
  height, both at the fin's `xv25` — so the fin sits on the tail cone's own
  top. The formula it replaced, `root_waterline_z + fuselage_height/2`, read
  the **wing** root as the body centreline (the substitution the body-drag row
  of the table above refuses for D-1) and on the three high-wing outline
  fixtures stacked half a body above the real top (`atr42_100` 223.15 →
  191.17 in; `cessna_210`'s lateral `p_dot` came down ~24 %). It survives
  only as the no-outline fallback, and its note now names the substitution it
  makes. A pointed tail cone (zero local height at `x_fin`) states no top, so
  the outline branch declines and the fallback answers.
* **A v-tail station stores its root in `z` and its span in `y`.** The airplane
  waterline is composed by `export/coordinates.tail_station_to_airplane`, which
  is the only place the two are added. Reading a fin station's `z` as its
  waterline gives the root for every station on the surface.
* **The spanwise tail deck supersedes the fuselage deck's point tail-load
  station** (GID 1001 band) in any combined-airframe sum — apply one
  representation, never both. Stated in the deck's own `$` header.
* **A control surface's load enters its parent surface one of two ways, and the
  deck says which** (plan 09 T6, 2026-08-13). `"smeared"`: the control load is
  inside the spanwise distribution, because `LT50` *is* the camber/elevator load
  and it is spread with the rest. `"discrete"`: it leaves the strips and enters
  at the hinge stations, with the hinge-moment couple at the actuator. The load
  itself is **SELECT's** (`elevator_load` / `load_on_rudder`, oracle-locked) where
  the condition publishes one and derived from TAILDIST's aft-of-hinge block —
  marked — where it does not. Selecting `"discrete"` without hinge and actuator
  span stations **raises**: a silent fall back would report a localized load path
  the deck does not contain.
* **The hinge moment is on a third of the aft-of-hinge chord.** TAILDIST's net
  trailing-edge pressure is identically zero, so the block aft of the hinge line
  is always a triangle and its centroid is closed-form. `HM = L_cs · c_e/3` is
  the suite's first hinge-moment output, and the actuator reacts `−HM`, which is
  what makes hinge torsion plus actuator couple equal the control load acting at
  its **own** centre of pressure.
* **On a T-tail, the horizontal tail reaches the airplane through the fin, and
  the fin deck carries it at its tip node** (plan 09 T7, 2026-08-13). The
  transfer reference point is the **last v-tail `GRID`** — no new node — and the
  set is the concurrent balancing h-tail load at the fin case's own V-n point
  plus that point's h-tail inertia. It is the one load in a fin deck that is not
  in the fin's local frame: a vertical `Fz` and a pitching `Myy`, mapped by
  `coordinates.ttail_transfer_to_airplane`, never through the fin's side-force
  map. Roll and yaw transfer are zero — a balancing condition is symmetric, so
  the h-tail's halves cancel about the centreline. A conventional layout carries
  none of this, to the byte.

## 8. Flagged inconsistencies (2026-08-05 extraction — **all closed 2026-08-17**, backlog Pri 5)

1. ~~`tests/test_load_keys.py` does not exist~~ — written: asserts `LoadValue` key
   uniqueness within every `ConditionResult` across every registered module on every
   example project (the claim `load_keys.py` makes).
2. ~~`constants.py` cites 25.303 alone~~ — `constants.py` and `models/results.py` now cite
   "14 CFR 23.303 / 25.303", the phrasing of the SF authority `safety_factors.py`.
3. ~~`coordinates.py` module-level default undocumented~~ — already carries the explicit
   back-compat comment at `IMPERIAL`.
4. ~~three partially-shared SI factor maps in `units.py`~~ — consolidated under one owner,
   `units.HUMAN_SI` (§7 row); the six tables are views of it and drift-guarded.
