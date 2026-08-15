# sloads — Capabilities Summary

**What it is.** sloads is a modern Python replication of the FAR 23 LOADS suite
(Hal C. McMaster, Aero Science Software; FAA repackaging DOT/FAA/AR-96/46) —
the 22-program package that computes the structural design loads a small
aircraft must sustain under **14 CFR Part 23 Subpart C — Structure** — extended
into an **initial-concept distributed-loads tool**. A concept configuration
(which may exceed the FAR 23 weight/seat caps) goes in; per-component and
full-airframe distributed **ULTIMATE** loads come out, ready for beam-model
structural sizing in the sbeam solver. All 22 original suite programs are
ported, plus modern modules for configuration assessment, fuselage net loads,
and the balanced free-free airframe. The package is pure calculation with three
interchangeable front-ends: a multi-page Streamlit GUI, a CLI, and the test
suite; one reloadable `project.json` carries every input.

---

## 1. Scope of analysis

### Mass properties
- **Weight estimation** (WTESTIMA): empty/takeoff weight from mission inputs
  and statistical fractions, component weight breakdown with stations,
  operating empty weight, FAR 23.25 minimum-weight rule.
- **Weight/CG envelope** (WTENV): the envelope of all discretionary loadings,
  structural CG limits, and the ballast weight/station required to meet each
  limit.
- **Weight, CG and inertia** (WTONECG): total weight, 3-axis CG, and mass
  moments of inertia (Ixx, Iyy, Izz + products) at the four structural-limit
  CG loadings, gear up/down.
- A single shared **weight/CG case model**: each named loading case states the
  analyses it feeds (flight and/or ground), so the V-n balance and the landing
  cases run from one list with one owner.

### Geometry, design speeds, and the flight envelope
- **Surface geometry** (WINGGEOM): MAC, XLEMAC, area, aspect ratio, spanwise
  station tables and hinge geometry for wing, tails, and every control surface.
- **Design airspeeds and maneuver load factors** (STRSPEED, per 23.335/23.337):
  minimum-required and chosen V_A/V_C/V_D/V_S, gust speeds, positive/negative
  limit maneuver factors by category (normal/utility/acrobatic), plus advisory
  Subpart-G operating-limitation placards (VNE/VNO/VMO/MMO/VFE). Concept mode
  adds the 14 CFR 25.335(b) **Mach-margin dive-speed route**.
- **Mach limit lines** (MACHLIM): the speed–altitude flight-limits diagram,
  EAS-limited below the shoulder altitude and Mach-limited above it.
- **Balanced V-n envelope** (FLTLOADS, per 23.333/23.337/23.341/23.345/23.421):
  the full maneuver + gust corner set balanced in pitch at every condition ×
  CG case × altitude — angle of attack, load factor, wing lift, drag, and the
  **balancing horizontal-tail load** per point; cruise and flaps-down sets;
  optional fuselage pitching-moment increment; trim-vs-CG and static-margin
  sweeps.

### Critical loads per component
**SELECT** computes and prunes the governing rational flight loads across the
envelope for all four major components:
- **Wing**: PHAA/PLAA/PMAA/NMAA corner conditions plus accelerated-roll and
  steady-roll torsion (23.349).
- **Horizontal tail**: balancing (23.421), unchecked/checked maneuver (23.423),
  up/down gust (23.425), and unsymmetrical (23.427(a)) loads, flaps retracted
  and extended.
- **Vertical tail**: maneuver and gust conditions (23.441, 23.443).
- **Fuselage**: the critical flight conditions (23.301/23.331), with the net
  fuselage distribution computed by the modern `body_loads` module (including
  the carry-through spar-reaction moment closure).

### Distributed loads
- **Spanwise wing loads**: Schrenk lift distribution (AIRLOADS), with the
  swept/high-Mach branch (AIRLOAD4) auto-selected; spanwise air-load
  shear/bending/torsion; wing **inertia relief** from panel and concentrated
  masses (WINGINER); and the **net** spanwise shear, bending moment, and
  torsion per critical case (NETLOADS), reported about a user-defined loads
  reference axis (elastic axis) with the axis named on every output.
- **Chordwise tail distribution** (TAILDIST) and simplified control-surface
  distributions: **aileron** (23.455), **flap** with slipstream and head-on
  gust (23.345/23.457), and **tab** loads (23.409).
- **Rational balanced-tail verification** (BALLOADS): independent CP
  cross-check of the balancing tail loads.

### Powerplant and asymmetric conditions
- **Engine-mount loads** (ENGLOADS): torque, side, vertical, and gyroscopic
  conditions per 23.361/363/371.
- **One-engine-out** (ONENGOUT): the vertical-tail transient for multiengine
  configurations.

### Ground and landing loads
- **Landing-gear load factors** (LGFACTOR) and the full tricycle-gear
  **LANDLOAD** condition set (level/tail-down landing, braked roll, side load,
  one-wheel landing, supplementary conditions) per 23.471–23.499, at the three
  roled ground loading cases.
- A **gear free-body report**: per case and per leg, the reaction at the tyre
  contact patch in the ground-line frame (with strut state, ground angle, and
  stroke) and the same reaction where the airframe receives it — verified
  through the solver as one load seen from two sides.

### Balanced free-free airframe (the primary deliverable)
The assembled **full-span airplane model**: aero and inertia applied together
as free-free balanced cases — flight cases closed by a six-DOF rigid-body
d'Alembert closure, left/right handed twins by reflection, and the FAR 23
**ground cases as balanced three-dimensional cases in the same deck** (checked
in closed form against LANDLOAD's independently derived load factors). Ground
and flight cases are kept as **separate governing families** — never silently
merged into one maximum.

Two operating modes share one code path: the **FAR 23 replication core** stays
locked to the manual's worked examples, and **concept mode** is a strict
superset (direct-weight path, explicit chosen load factors, Mach-margin dive
speeds) that reduces exactly to the core on GA inputs.

---

## 2. Outputs

**Everything deliverable is ULTIMATE.** Internal calculation stays LIMIT (the
oracle basis), and the safety factor is applied once at the render/export
boundary. Every case states its factor (a governing safety-factor table with a
FAR basis per condition family is the single authority), the `-ULT` marker is
part of every load's units string, and per-module analysis pages may show LIMIT
only when explicitly marked. Results present in Imperial or SI at the user's
selection; solver decks use a consistent N/mm/MPa channel.

- **Load-case CSV files** — one per module, one row per case with the case ID,
  the load quantities, and the `SF` column; station-distribution CSVs for wing
  and fuselage (LIMIT-basis files carry the basis in-band and pair with an
  ULTIMATE twin).
- **sbeam bulk-data decks** — `GRID`/`FORCE`/`MOMENT` cards per component
  (wing, body, h-tail, v-tail, control surfaces) and the assembled balanced
  full-span deck, plus **`CONM2`/`MASSSET` distributed-mass decks** per payload
  case with a gravity-based independent inertia check. Case identity is
  joinable end-to-end: report case ID ↔ deck `LABEL` ↔ `LOAD`/`SUBCASE`
  integer. Every deck carries a **global-equilibrium invariant**, and a pinned
  **sbeam round-trip harness in CI** proves the exported decks actually solve.
- **Consolidated loads summary report** — a self-contained LaTeX/PDF document
  written for a structural analyst who did not run the analysis: airplane
  identity, flight envelope, governing ULTIMATE loads with location and safety
  factor, axes/sign-convention section with figures, an explicit
  statement-of-limitations section, and an index of the companion data files.
  Deterministic (same project + units → byte-identical output).
- **Gear load report** — the stamped free-body companion CSV, report section,
  GUI view, and CLI export target described above.
- **Workbook export** — a multi-sheet spreadsheet with per-sheet unit
  statements.
- **Interactive GUI** — dashboard with workflow status and validation
  warnings, per-module analysis pages with charts (CG envelope, V-n diagram,
  speed–altitude placard chart, spanwise load plots, three-view planforms,
  trim/static-margin sweeps), an engineer's opt-in/opt-out **critical-case
  selection**, and a Results Review / Export phase. The CLI runs any registered
  module or export target headlessly from the same `project.json`.

---

## 3. Verification basis and limits

Every FAR 23 module is locked against the manual's printed 6-place GA worked
example (Appendix A) to **±0.1%**, with the printed figure and page citation
kept in the test; twin/turboprop-only cases are closure-locked to the original
BASIC source. Concept-mode physics carries stated closure/invariant gates in CI
with the same force (e.g. the six-DOF balance residual, exact ground-case
factor recovery, deck equilibrium, solver round-trip). Deliberate deviations
from the oracle are recorded in an approved-corrections register.

sloads is an independent open replication (MIT-licensed) intended as an
educational and exploratory engineering tool. Results are **not certified** for
regulated or certification structural design; the report states its own
limitations, and outputs should be verified by competent engineering judgement
before use in design or airworthiness decisions.
