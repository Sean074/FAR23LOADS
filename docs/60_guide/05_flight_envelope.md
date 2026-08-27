# 5. Flight Envelope (V-n)

*Original program(s):* `FLTLOADS+SELECT`.

## What this page is for

This is the page where inputs become load cases. `FLTLOADS` constructs the
V-n diagram — the maneuver and gust envelope of FAR 23.333–23.341 — and
balances the airplane at every corner of it: each combination of CG case,
altitude and envelope point gets a trimmed solution with its balancing tail
load. `SELECT` then prunes that matrix to the handful of **critical
conditions** per component — the wing, tail and fuselage cases every
distribution page after this one actually loads. The pages before this one
fed it; the pages after it consume what it selects.

## Before this page

[Structural Speeds](04_structural_speeds.md) and
[Aerodynamic Data](03_aero_coefficients.md) must both be complete — the
envelope is built from the speed set and bounded by the stall CLs, and the
balance uses the polars. The CG cases come from
[Weight & Mass Properties](02_weight_mass.md). Until they exist the results
block names what is missing and which page owns it.

## The inputs

The generated field table for this page:
[`_generated/flight_envelope.md`](_generated/flight_envelope.md).

The page's own form is deliberately small — the envelope is mostly built
from upstream data:

**Coefficient Mach number.** The Mach at which the entered coefficient set
was determined, used for the compressibility bookkeeping. For a piston GA
airplane the customary small nominal value is fine.

**Tail CP stations, flaps up and flaps down (`Xtc`, `Xtf`).** The fuselage
stations the balancing tail load acts at in the two configurations. The
flaps-up CP sits well forward on the tail chord; flaps down it moves aft.
The page derives a suggestion from your tail geometry and says so — the
caption states the two stations it would use — but the typed values are what
the analysis uses, so either accept the suggestion or state your own from
tail aerodynamic data.

**Altitudes.** The altitude list the envelope is evaluated over. Gust
intensities fall with altitude while true speeds rise, so different rows of
the matrix govern at different altitudes; sea level alone is the classic
single-row case, and adding rows widens the search `SELECT` prunes from.

## Screenshots

![The Flight Envelope page with the Appendix A single loaded: the tail CP
suggestion caption and the altitude list](img/05_flight_envelope__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

Sea level only — Appendix A runs its envelope at one altitude, so the
altitude table is the single row 0 ft. The tail CP stations are the book's:
`Xtc = 253.364` and `Xtf = 261.027` — the flaps-down station is exactly the
tail's 25 %-MAC station from the Geometry page, and the flaps-up station
sits forward of it, both consistent with the derived suggestion the caption
shows. Coefficient Mach 0.1. With the four `CG1`…`CG4` cases from the weight
page, the balanced matrix reproduces the manual's Chapter 9 tail-load
tables case for case.

## Worked example — twin (`baron_58`)

Three altitudes — sea level, 10,000 ft and 20,000 ft — spanning the Baron's
operating band, so the gust rows compete realistically. The tail CP
stations are taken from the page's own geometry-derived suggestion
(`Xtc = 308`, `Xtf = 316.66` — the constructed tail's 5 % and 25 % MAC
stations), which is the honest choice when no tail wind-tunnel data exists;
the sources register marks them accordingly. Three flight CG cases at the
certificate's corners, so the matrix balances the airplane at forward,
aft and light-forward loadings across all three altitudes.

## Results on this page

Two families of output:

- **The envelope and balance matrix** — the V-n corner speeds and load
  factors (speeds and dimensionless factors: never factored, no `-ULT`),
  and one balanced condition per CG × altitude × envelope point with its
  **balancing tail load**. Tail loads are deliverable loads: **ULTIMATE**,
  units carrying the `-ULT` marker, each case stating its SF per
  [Conventions](03_conventions.md).
- **SELECT's critical conditions** — one line per selected case with its
  per-case safety factor: the governing wing conditions (by load factor and
  by torsion), the governing tail cases, and the fuselage set. These case
  IDs (`W-…`, `HT-…`, `F-…`) are the identities the
  [Wing Loads](06_wing_loads.md), [Fuselage Loads](07_fuselage_loads.md)
  and [Tail Loads](08_tail_loads.md) pages distribute — minted here, kept
  everywhere.

Sanity checks: VA/VC/VD on the envelope match the speeds page; the positive
corner reaches n₁ exactly; the 1-g stall speed reads back your CLmax (the
twin's reproduces its published stall speed); balancing tail loads are
down-loads (negative lift) for conventional forward-CG trim and grow toward
the forward CG case; and the selected wing case is at or near the positive
corner unless a gust row genuinely governs.

## Common mistakes

- **Typing tail CP stations that contradict the tail geometry.** The caption
  shows the derived pair; a hand-typed station far from it puts the tail
  load on a lever arm your geometry cannot justify. Overriding is allowed —
  it is an entry, not a derivation — but know why.
- **A single altitude for a high-flying airplane.** Gust severity trades
  against true speed with altitude; sea level alone can miss the governing
  gust row.
- **Expecting loads at every matrix point downstream.** The distribution
  pages consume SELECT's critical set, not the whole matrix — a condition
  you can see in the matrix but not on a later page was considered and not
  selected.
- **Blank rows in the altitude grid** — the grid-entry rules of
  [Getting started](01_getting_started.md) apply here first: a row with an
  empty cell is not saved.
