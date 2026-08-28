# 8. Tail Loads

*Original program(s):* `TAILDIST+BALLOADS`.

## What this page is for

`TAILDIST` takes each critical tail condition — horizontal and vertical —
and distributes it chordwise: the load that comes from angle of attack acts
at the quarter chord, the camber load at mid chord, and the program prints
the resulting net pressure across the chord stations. `BALLOADS` is the
independent cross-check that re-derives the balancing tail loads. Between
them, this page turns the tail cases selected upstream into the pressures a
tail structure is actually designed to.

## Before this page

Everything. This is the first page with **no inputs of its own** — the
banner at the top says exactly that: it reads what the pages before it
produced. The critical tail cases come from the
[Flight Envelope](05_flight_envelope.md) selection; the tail geometry,
areas, arms and throws were entered on [Geometry](01_configuration_layout.md);
the aero quantities on [Aerodynamic Data](03_aero_coefficients.md). If the
results block names a missing slice, the remedy is on those pages.

## The inputs

The generated field table for this page:
[`_generated/tail_loads.md`](_generated/tail_loads.md) — which states the
same thing the page does: this page enters nothing; every quantity it uses
is entered earlier.

That is worth a sentence of *why*: `TAILDIST` in the original suite was a
pure post-processor, fed by the files the earlier programs wrote. The page
preserves that honestly instead of inventing inputs for it.

## Screenshots

![The Tail Loads page with the Appendix A single loaded: the no-input
banner and the TAILDIST results with each case's aero
state](img/08_tail_loads__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

Nothing to type — the worked example here is reading. With the Appendix A
project, the results open with the **component constants** printed once (the
tail lift-curve slope, and for the fin its slope with the rudder
effectiveness), then one block per selected case. The first horizontal-tail
case, the retracted balancing condition at the aft-CG point, states the
state that produced it — tail angle of attack about 7.6°, elevator about
−5.5° (trailing-edge up), dynamic pressure ≈ 45 lb/ft² at its 115-kt
balance point — and then its two chordwise components (the
angle-of-attack load at 25 % chord, the camber load at 50 %) with the net
pressure at each chord station. The book's Chapter 9 tables are these,
case for case.

## Worked example — twin (`baron_58`)

Again nothing to type; the reading differs. The twin's vertical-tail set is
richer — the maneuvering fin cases run at the regulation's fixed fin angles
with the full rudder throw, the gust case at its gust sideslip — and each
states its own β, rudder angle and q. Where a case's method defines no value
for a quantity (the checked-maneuver elevator increment, the side-gust q),
the page prints the **stated reason** rather than a number: "cannot supply"
is a statement here, never a blank. A project saved before these states were
recorded says *re-run SELECT* — see
[Appendix C](C_troubleshooting.md).

## Results on this page

- **TAILDIST cases** (ULTIMATE, `-ULT` units, per-case SF): per condition —
  its aero state (angle of attack, control deflection, dynamic pressure,
  sideslip where defined), the quarter-chord and mid-chord load components,
  and the chord-station net pressures. The state block is not decoration:
  the published state reconstructs the loads through the method's own
  equations, so you can audit any case by hand.
- **Chordwise tail distribution** (**LIMIT, marked**): the printed-table
  form of the same distributions, kept LIMIT to read against the manual.
- **BALLOADS** (ULTIMATE): the independent re-derivation of the balancing
  loads — its agreement with the envelope page's tail loads is the built-in
  cross-check.

Sanity checks: the two chordwise components sum to the case's total tail
load; balancing cases carry down-loads at forward CG; the printed dynamic
pressure squares with the case's speed; and the stated deflections sit
inside the throws you entered on Geometry.

## Common mistakes

- **Hunting for the missing form.** There isn't one; the banner says so.
  Every "input" question about this page is answered on Geometry (areas,
  arms, throws), Aerodynamic Data (slopes, zero-lift lines) or the Flight
  Envelope (which cases exist).
- **Ignoring the aero-state rows.** A tail load whose stated state looks
  wrong (a deflection beyond the throw, a q that doesn't match the speed)
  is upstream data wrong — this page is where such errors first become
  visible.
- **Comparing ULTIMATE case tables against the book.** The manual prints
  LIMIT; use the LIMIT-marked chordwise table, or divide by the stated SF
  ([Conventions](03_conventions.md)).
- **A stale critical set after upstream edits.** Changing speeds, weights
  or coefficients without revisiting the Flight Envelope page leaves this
  page distributing yesterday's selection.
