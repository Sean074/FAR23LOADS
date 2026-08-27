# 1. Geometry

*Original program(s):* `WINGGEOM`.

## What this page is for

The original suite began with `WINGGEOM`, which asked the user to type the
wing planform as (X, Y) corner points and divided it into spanwise strips for
every later program to load. This page is that step for the whole airplane:
the lifting-surface planforms, the fuselage outline, the empennage scalars,
the landing-gear geometry and the engine layout all live here, entered once
and read by every page after it. Nothing on this page is a load — it is the
airplane's shape, in numbers.

## Before this page

Nothing. Geometry is the first page and consumes no upstream results; it is
where a blank project starts. Have the three-view or general-arrangement
drawing on your desk (see [Before you start](02_before_you_start.md)) —
almost every number here is read off it.

## The inputs

The generated field table for this page:
[`_generated/configuration_layout.md`](_generated/configuration_layout.md).

**Surfaces.** One record per lifting surface — wing, aileron, horizontal
tail, vertical tail — each entered exactly as `WINGGEOM` asked: a
**leading-edge polyline** and a **trailing-edge polyline** of (station,
butt line) points in inches, root to tip. A kinked planform simply gets more
points; the polylines need not have the same number. `elements` is the strip
count the span is divided into (the Appendix A wing uses 20). `symmetric`
marks a mirrored pair entered as one half — true for wing and tails, false
for an aileron entered on its real side. The spar and reference-axis
percentages position the structural box and the axis torsion is reported
about; the tip-cap width closes the tip. Read every station from **your**
datum, consistently — the datum is yours to choose
([Conventions](03_conventions.md)).

**Parametric wing.** The scalar summary of the wing: reference area, aspect
ratio, taper, dihedral, leading-edge sweep and root station, plus the root
waterline. Where a scalar can be derived from the planform you entered, the
page derives and shows it — a value you type instead is an override and is
marked as one, with the planform's own value beside it. Let the planform
govern unless you have a reason.

**Fuselage.** Three or more cross-sections — station, width, height — nose
to tail. They bound the body for the fuselage load distribution and the mass
checks; the first section's station is the nose, the last the tail.

**Empennage.** The tail quantities the original programs asked for as
scalars: areas, spans, aspect ratios, the elevator and rudder areas each
side of the hinge, the deflection limits, and the chordwise stations
`xt25`/`xt50` (`xv25`/`xv50` for the fin) where the balancing programs place
the tail load. These scalars must agree with the tail planform you drew
above — the tool refuses a tail whose stated 25 %-MAC station disagrees with
its own polyline, because a load cannot sit on two lever arms.

**Aileron and flap.** The control-surface areas each side of the hinge line,
chord ratio and deflection limits used by the simplified control-surface
programs. The aileron's planform is drawn under **Surfaces**; these scalars
must describe the same surface.

**Landing gear.** Each leg's axle position at the three strut states —
extended, static, compressed — as (station, waterline) pairs, with the
rolling radius, the strut type code, the attach point and the tread. This is
the geometry `LANDLOAD` resolves its ground reactions on; collect it from
the gear drawing, not by eye.

**Engine layout.** The layout selector — single nose engine, twin wing
engines, four wing engines — which sets how many engine records the
[Engine Mount](12_engine_mount.md) page carries and where they sit.

## Screenshots

![The Geometry page with the Appendix A single loaded: the Surfaces group
with the wing record expanded](img/01_configuration_layout__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

The Appendix A airplane keeps the manual's own numbers. Its wing leading
edge is a **three-point polyline** — root (45, 0), a kink at (64.313, 46.5)
where the inboard strake ends, tip (72, 201) — against a straight two-point
trailing edge from (146, 0) to (116, 201): a real wing rarely stays
trapezoidal, and the polyline entry is how `WINGGEOM` absorbed that. Twenty
elements, symmetric, reference axis at 40 % chord. The aileron is its own
unsymmetric surface spanning butt lines 109–190 along the wing trailing
edge. The empennage scalars are Appendix A's: h-tail area 36.944 ft² with
the tail load stations `xt25 = 261.027` / `xt50 = 270.357`, elevator throws
30° up / 20° down. Dihedral 6°, datum at station 0 ahead of the nose
(fuselage sections run −12 to 306.26).

## Worked example — twin (`baron_58`)

The Baron enters its published geometry and anchors the estimated rest to
it. Span 454 in and area 199.2 ft² are the type-certificate figures; the
chords are estimates (root 84, tip 42) *constructed* so the straight
quarter-chord — the certificate says the wing is unswept at 25 % chord —
falls at station 83.0, which is where the certificate's datum note puts the
front-spar jack pads (83.1 in aft of datum). Entering LE (62, 0)→(72.5, 227)
and TE (146, 0)→(114.5, 227) encodes all of that, and keeping the
certificate's datum means every arm in the type certificate can be typed in
unchanged on the weight page. The engine layout is **twin wing**; the gear
tread is the published 115 in, and the tail spans are published while the
tail areas are marked estimates — the split between certified and estimated
values is itemised in
[`examples/baron_58.sources.md`](../../examples/baron_58.sources.md).

## Results on this page

The results block echoes what the geometry *implies*, so you can check the
shape before any load exists: the derived planform properties (areas, mean
aerodynamic chord and its butt line, sweep), the resolved tail planform, and
a first-order CG and gear-position estimate once mass data exists. These are
geometry and estimates, not loads — nothing here is LIMIT or ULTIMATE, and
none of it carries a safety factor. Sanity checks: the derived area against
the drawing's stated reference area; the MAC station against the
manufacturer's %-MAC reference; the tail arm (tail station minus wing MAC
quarter-chord) against the drawing.

## Common mistakes

- **Mixing datums.** Stations read from a drawing with one datum and arms
  from a weight statement with another. Pick the datum first; convert
  everything to it.
- **Entering a mirrored surface twice** — the wing is entered as one half
  with `symmetric` on; typing both halves doubles the area.
- **Polyline points out of order or with duplicate stations.** Enter root to
  tip; the page refuses a planform it cannot walk, by name.
- **Tail scalars that disagree with the tail planform.** The stated
  `xt25`/`xv25` must be the polyline's own 25 %-MAC station — the refusal
  message tells you both numbers; move whichever is wrong.
- **Gear axle states from the wrong reference.** The three axle positions
  are (station, waterline) pairs in airplane coordinates, not strut-local
  travel.
