# 11. Tab Loads

*Original program(s):* `TABLOADS`.

## What this page is for

`TABLOADS` computes the trim/control-tab surface loads of 14 CFR 23.409:
for each tab you define, the tab load at its governing speed and deflection
with the leading-edge-peaked pressure over the tab chord. Tabs are small
and their loads are small — but they are the last surface in the control
chain, and 23.409 is the paragraph that sizes them.

## Before this page

[Structural Speeds](04_structural_speeds.md) — the governing speed comes
from the design speed set. The parent surface (which tail or wing surface
the tab rides on) must exist on [Geometry](01_configuration_layout.md).

## The inputs

The generated field table for this page:
[`_generated/tab_loads.md`](_generated/tab_loads.md).

**One row per tab.** Each states: the **parent surface** it rides on (a
fixed-vocabulary pick — elevator tab on the h-tail, rudder tab on the
v-tail, aileron tab on the wing); the tab **area** and **mean chord**; the
**parent airfoil chord** at the tab's station (the ratio of tab chord to
airfoil chord is the method's shape parameter); the **butt-line station**
where the tab sits; and its **deflection** limit. All of it comes off the
control-surface drawing — a tab has no aerodynamic subtlety here, only
geometry.

## Screenshots

![The Tab Loads page with the Appendix A single loaded: the tab row and
its load](img/11_tab_loads__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

One elevator trim tab on the h-tail: area 1.57 ft², mean chord 7.478 in on
a 42.166-in parent chord at butt line 17.828, 15° deflection — the
Appendix A tab, as printed. Its load comes out under a hundred pounds at
the cruise design speed, with the half-pound-per-square-inch class
leading-edge pressure typical of a GA trim tab.

## Worked example — twin (`baron_58`)

One elevator trim tab, all-estimate (the certificate does not publish tab
geometry): 1.6 ft², 8-in mean chord on a 44-in parent chord at butt line
30, 15° deflection — statistical values marked in the sources register.
Add rows for the rudder and aileron tabs the same way when their drawings
are on your desk; the analysis is per row.

## Results on this page

One condition per tab (ULTIMATE, SF stated): the governing speed, the
tab chord ratio the method derived, the **tab load** and its leading-edge
pressure. Sanity checks: the load scales with area, deflection and the
square of speed; the chord ratio should be a sensible fraction (a tab is a
minority of its parent's chord); and a tab load rivalling its parent
surface's load means an entry error, usually the area or the chord units.

## Common mistakes

- **The parent chord entered as the tab chord** (or vice versa) — the
  ratio silently inverts and the load with it.
- **Area for both sides of a paired tab.** One row describes one tab;
  enter each side's tab as its own row if both exist.
- **A deflection the system cannot reach at speed.** As with the aileron,
  the stated throw is assumed available at the governing speed.
- **Skipping tabs entirely.** A missing row is a surface with no design
  load — the page analyses what you define, and only that.
