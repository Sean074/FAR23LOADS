# 9. Aileron Loads

*Original program(s):* `AILERON`.

## What this page is for

`AILERON` computes the critical aileron surface loads of 14 CFR 23.455 —
the simplified method: the up- and down-aileron loads at the governing
speed and deflection, and the leading-edge-peaked chordwise pressure they
imply. These are the hinge and surface design loads for the aileron itself;
the *wing's* aileron-roll case (the rolling-moment condition) was handled
on the [Wing Loads](06_wing_loads.md) page as case `ACRL`.

## Before this page

[Structural Speeds](04_structural_speeds.md) — the loads scale with the
design speeds. The aileron's planform, areas each side of the hinge and
deflection limits were entered on [Geometry](01_configuration_layout.md);
this page picks the surface and adds the load-introduction detail.

## The inputs

The generated field table for this page:
[`_generated/aileron_loads.md`](_generated/aileron_loads.md).

**Surface.** Which Geometry surface is the aileron — a named pick from the
surfaces you drew, not a re-entry of its shape. The span-limit overrides
exist for an aileron whose loaded span differs from the drawn planform;
blank, the planform governs.

**SELECT's full-down aileron.** The full-down deflection the wing-torsion
selection used for the steady-roll case. It should be the aileron's own
down-limit from Geometry — the page warns when the two differ, because both
reach the calculation: one scores wing torsion, the other loads the
aileron.

**Hinges and actuator.** The hinge butt-line stations along the aileron
span and the actuator station: where the surface load is reacted. These
turn the surface load into hinge reactions downstream and are read straight
off the drawing.

## Screenshots

![The Aileron Loads page with the Appendix A single loaded: surface pick
and the critical loads](img/09_aileron_loads__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

The surface pick is the `aileron` drawn on Geometry (butt lines 109–190);
its areas each side of the hinge (1.3 / 5.188 ft²) and throws (10° up /
15° down) were entered there, and SELECT's full-down matches the 15° down
limit. No hinge stations are entered in the bundled example — the surface
loads stand alone, as Appendix A prints them.

## Worked example — twin (`baron_58`)

The same shape with the twin's estimates: the aileron drawn at butt lines
130–210 on the constructed planform, areas 1.6 / 6.0 ft² about the hinge,
throws 20° up / 14° down — all statistical values, marked as such in the
sources register. SELECT's full-down is the aileron's own 14°, so the two
consumers of "full down" agree by construction.

## Results on this page

One condition (ULTIMATE, SF stated): the **critical down-aileron and
up-aileron loads**, each with the speed it governs at, per 23.455's
simplified method. On the single, the down load lands at a few hundred
pounds at the cruise design speed. Sanity checks: the down load exceeds
the up load in magnitude when the down throw is larger; the loads scale
with the aft-of-hinge area (the fwd-of-hinge area is balance area); and the
governing speed is one of the speeds page's design speeds, not something
new.

## Common mistakes

- **Re-entering the aileron's geometry here.** The surface is a pick; its
  planform, areas and throws live on Geometry. Fix them there.
- **SELECT's full-down disagreeing with the aileron's down-limit** without
  a reason. Both are used; the warning names the two values — make them
  agree or know why they differ.
- **Areas swapped about the hinge.** The aft-of-hinge area carries the
  load; putting the big number forward of the hinge understates everything.
- **Deflections beyond what the control system can hold at speed** — the
  regulation's simplified method assumes the stated throw is available at
  the governing speed; if yours is limited, the limit is the input.
