# 10. Flap Loads

*Original program(s):* `FLAPLOAD`.

## What this page is for

`FLAPLOAD` computes the flap design loads of 14 CFR 23.345 — the flap-down
condition at the flap design speed with its leading-edge-peaked chord
pressure — and the 23.457(b) check that a flap sitting in the **propeller
slipstream** sees the slipstream's higher dynamic pressure, not free
stream. The flap's planform facts were entered on Geometry; this page adds
the flap-condition load factor and the slipstream description.

## Before this page

[Structural Speeds](04_structural_speeds.md) — the flap design speed comes
from there. The flap area, chord ratio and deflection live on
[Geometry](01_configuration_layout.md); the engine data the slipstream case
reads comes from [Engine Mount](12_engine_mount.md), and on a fresh project
you can enter it later — the free-stream condition stands on its own.

## The inputs

The generated field table for this page:
[`_generated/flap_loads.md`](_generated/flap_loads.md).

**Surface and span limits.** The flap surface name, with optional
inboard/outboard butt-line overrides and the hinge/actuator stations, as on
the aileron page.

**Gust load factor.** The 23.345(b) flaps-extended gust factor the flap
condition is checked at — the regulation's flaps-down envelope is capped at
2 g with its own gust criterion, and this is that entry.

**Slipstream description.** The nacelle frontal area and the engine butt
line: together with the engine's power and propeller disc from the engine
page they set the slipstream's velocity increment and where its washed span
sits. A centreline single enters butt line zero — the slipstream straddles
the fuselage and washes the inboard flap; a wing-mounted engine puts the
washed band at its butt line.

## Screenshots

![The Flap Loads page with the Appendix A single loaded: the flap inputs
and both flap conditions](img/10_flap_loads__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

Flap area 10.7 ft² per side at 0.27 chord ratio, 40° full down (all
Appendix A values from Geometry), gust factor 1.9, nacelle frontal area
8.2 ft² at butt line 0 — the nose engine's slipstream washing the inboard
wing. The results show both conditions: the 23.345 flap load with its
leading-edge pressure, and the slipstream case with its computed factor
(≈1.5 on this airplane) and the washed butt-line band straddling the
centreline.

## Worked example — twin (`baron_58`)

Flap 12 ft² per side at 0.25 chord (estimates), 30° full down — the
type-certificate's flap setting for the landing placard — gust factor 1.9,
and the slipstream entered per nacelle: frontal area 12 ft² at the
estimated butt line 66, so the washed band sits over the flap's outboard
half instead of the root. On a twin this case is the one that moves: two
discs, wing-mounted, directly ahead of the flaps.

## Results on this page

Two conditions (both ULTIMATE, SF stated):

- **Critical flap loads (23.345)** — the surface load at the flap design
  speed with the chordwise pressure (leading edge peak, trailing edge at
  half), plus the flap CLs the condition ran at.
- **Flap loads in the propeller slipstream (23.457(b))** — the slipstream
  factor, the effective velocity at the flap, and the inboard/outboard
  butt lines of the washed band.

Sanity checks: the slipstream velocity exceeds the free-stream flap speed
(that is the point of the case); the washed band is centred on the entered
engine butt line with a width of the order of the propeller disc; and the
flap pressure scales with deflection — re-running at a reduced placard
deflection should visibly reduce it.

## Common mistakes

- **Flap area per side vs total.** The entry is one side; doubling it
  doubles the load.
- **A slipstream case with no engine data.** The condition needs the
  engine's power and disc from the engine page — enter that page before
  trusting this block on a fresh project.
- **Butt line zero on a wing-engine airplane.** The washed band lands on
  the wrong part of the flap; enter the nacelle's real butt line.
- **Using the clean-gust factor.** The flaps-extended gust criterion is its
  own, smaller number — the clean envelope's factor does not belong here.
