# 7. Fuselage Loads

*Original program(s):* `NETLOADS`.

## What this page is for

The body-side counterpart of the wing page: the fuselage's critical flight
conditions — selected on the [Flight Envelope](05_flight_envelope.md) page —
are distributed along the body as running load, shear and bending, station
by station, following the manual's fuselage net-load method. What this page
asks of you is only the **fuselage mass distribution**: how the body's
weight is lumped along its length, because the inertia part of every
fuselage case comes from it.

## Before this page

[Flight Envelope](05_flight_envelope.md) must have run — the conditions
distributed here are its fuselage selections — and the fuselage stations
mean nothing without the body geometry and weight database from
[Geometry](01_configuration_layout.md) and
[Weight & Mass Properties](02_weight_mass.md).

## The inputs

The generated field table for this page:
[`_generated/fuselage_loads.md`](_generated/fuselage_loads.md).

**Fuselage stations.** The body's mass as station/weight pairs — the classic
five-or-six-lump representation of the original method. By default the tool
**derives this list from the component-tagged weight database** (everything
tagged `fuselage`, lumped), and the override flag says whether the table you
see is that derivation or your own entry. If you override, the difference
against the database is reported, never silently absorbed — the two describe
the same airplane and should agree.

**Reference waterline.** The waterline the body bending is taken about.

## Screenshots

![The Fuselage Loads page with the Appendix A single loaded: the station
table and the distributed cases](img/07_fuselage_loads__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

Five lumps, the manual's own: 185 lb at station 3.3 (the nose), 933 at 44.9
(engine and forward fuselage), 483 at 99.1 and 572 at 110.4 (the cabin), and
405 at 169.7 (aft body and tail), about reference waterline 55. Summed they
are the fuselage-carried weight of the Appendix A loading, positioned to
reproduce the book's body CG — which is why the distributed cases match the
printed chapter.

## Worked example — twin (`baron_58`)

Six lumps spanning stations 7 to 320, an estimated split of the
fuselage-carried empty weight plus occupants, about waterline 100. On the
twin most of the airplane's weight is **not** here — engines, propellers,
gear and fuel are wing-carried and belong to the
[Wing Loads](06_wing_loads.md) concentrated list instead; the fuselage
lumps carry the shell, systems, furnishings and people. Tagging an item to
the wrong beam is the mistake the component tags on the weight page exist
to prevent.

## Results on this page

One block: **Fuselage stations** (**LIMIT, marked as such**) — for each
selected fuselage condition (maximum down-load on the wing, maximum up,
and the rest of the selected set), the running vertical load, integrated
shear and body bending moment at each station, nose to tail. There is no
separate summary-condition table on this page; the station table *is* the
program's output, kept LIMIT so it reads against the manual directly.

Sanity checks: the shear integrates the running load (a spot check at any
two adjacent stations confirms the sign convention); bending peaks at the
wing carry-through, where the balancing lift enters; the summed station
weights equal the fuselage-carried loading weight; and the tail end of the
bending curve reflects the balancing tail load of the case — a case with a
big down tail load bends the aft body accordingly.

## Common mistakes

- **Overriding the derived stations and letting them drift.** After any
  weight-database edit, a hand-entered station list is stale; either
  re-derive or re-justify. The reported difference against the database is
  the tell.
- **Wing-carried items lumped into the body.** Engines on a twin, wing
  fuel, wing-mounted gear — tagging them `fuselage` inflates every body
  case and starves the wing of relief.
- **A station list whose total is not the loading weight.** The lumps are
  the airplane's body weight, not a sampling of it.
- **Reading the LIMIT table as ULTIMATE.** The basis column says LIMIT;
  the deliverable factor lives downstream, per
  [Conventions](03_conventions.md).
