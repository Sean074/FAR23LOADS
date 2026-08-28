# 14. Landing Loads

*Original program(s):* `LGFACTOR+LANDLOAD`.

## What this page is for

Two programs close the ground-loads chain. `LGFACTOR` estimates the landing
load factor from the drop-test energy method of 14 CFR 23.473/23.725: sink
rate from wing loading, energy absorbed through tire and strut at their
efficiencies, out comes the airplane load factor N and the gear factor NLG.
`LANDLOAD` then works the full FAR ground-condition matrix — level landing,
tail-down, one-wheel, side load, braked roll, and the supplementary
nose-wheel cases — resolving each into wheel reactions through the gear
geometry entered on the Geometry page, at the three roled landing CG cases
from the weight page.

## Before this page

[Geometry](01_configuration_layout.md) must carry the full landing-gear
geometry (axle positions at three strut states, tread, strut types) and
[Weight & Mass Properties](02_weight_mass.md) the design weights and the
three roled ground cases — aft max landing, fwd max landing, fwd light.
The page blocks the reaction solve until every ground case has a positive
weight, station and waterline, and says so.

## The inputs

The generated field table for this page:
[`_generated/landing_loads.md`](_generated/landing_loads.md).

**Energy-method inputs.** The strut stroke (fully extended to compressed),
tire outer diameter and hub diameter — the two deflections the drop energy
is absorbed over — and the strut type code from Geometry sets the
efficiency. The **wing lift factor** is the certification basis's allowance
for wing lift carried during the impact — 0.667 under FAR 23.473, 1.0 under
FAR 25.473(a)(2); the widget states both as guidance and enforces neither.

**Tail-down angle.** The ground-line-to-waterline angle for the tail-down
landing attitude, off the side view.

**Airplane load factor N (governing).** The load factor the reaction matrix
runs at — customarily the LGFACTOR result **rounded up** as a design choice.
Leave "Computed N governs" checked and LGFACTOR's energy value carries
through; enter a value and that is the design N. Either way the gear factor
is **derived**: `NLG = N − L`, never entered, so changing the lift factor
always moves the wheel loads. The results show the computed and governing
pairs side by side, and the page cautions when an entered N sits below the
energy value.

## Screenshots

![The Landing Loads page with the Appendix A single loaded: the energy
inputs and the ground-case matrix](img/14_landing_loads__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

Appendix A's inputs: 7-in strut stroke, 19-in tire on a 7-in hub, lift
factor 0.667, tail-down angle 15°, and the governing airplane load factor
**typed as 3.167** — the book's own rounded design point (its LANDLOAD runs
at NLG 2.5 = 3.167 − 0.667, where LGFACTOR computes 2.428), and the page
shows both pairs so the rounding is a visible decision, not a mystery.
The three ground cases are the book's landing corners. The results
reproduce the printed sink rate, N and NLG, and the wheel-load matrix's
legible cells — this is one of the suite's page-cited oracle locks.

## Worked example — twin (`baron_58`)

Estimated energy inputs on published anchors: 8-in oleo stroke, 20-in tire
on a 10-in hub (statistical for the class), lift factor 0.667, tail-down
12°, and the governing N left on "computed" so LGFACTOR's energy value
carries through — the honest choice when no certificated design factor is
published. The three roled cases are the entered loadings from
the weight page (aft and forward at max landing weight, the light-forward
case), all inside the certified envelope; the retractable gear's geometry
is the estimated set anchored to the published 115-in tread.

## Results on this page

Three families (loads ULTIMATE with SF stated; the factors themselves
dimensionless and unfactored):

- **The LGFACTOR condition** — sink rate, airplane load factor N, gear
  factor NLG, with the energy bookkeeping.
- **One critical-reaction summary per FAR ground family** — the governing
  case of each family with its wheel reactions.
- **The full case matrix** — every ground condition as its own row: main
  and nose vertical/drag/side reactions, resultants, and the unbalanced
  moments, at the weight each case is computed at.

Sanity checks: sink rate lands in the regulation's 7-to-10 ft/s band;
N sits a little above NLG by exactly the lift factor's share; level-landing
main reactions times two roughly balance weight × NLG; side and braked
cases split per the regulation's fixed fractions; and nose-gear reactions
stay positive — a negative one means the CG or gear geometry is off.

## Common mistakes

- **Ground cases missing or unroled.** The three loadings are required by
  role, not by name; the page refuses to solve without all three, and the
  weight page is where they are made.
- **Stroke or tire deflection in the wrong units or sense.** The stroke is
  the full extended-to-compressed travel; the tire's share is outer
  diameter minus hub, halved by the method — entering a loaded radius here
  double-counts.
- **Confusing the two load-factor pairs.** LGFACTOR's computed (energy)
  N/NLG and the governing pair both appear; the matrix runs on the
  governing pair, and NLG is always N − L — derived, never entered.
  The single's 2.5-vs-2.428 pair is the worked illustration.
- **A waterline-free CG.** The ground moments need the CG height; a ground
  case without a credible waterline solves to nonsense lever arms, which
  the page's warnings call out.
