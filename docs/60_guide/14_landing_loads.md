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
reproduce the printed sink rate, N and NLG, and the ground-line wheel-load
matrix — this is one of the suite's page-cited oracle locks.

**Two approved deviations sit in the airplane-datum half**, and are worth
knowing before you cross-check against the book's p232 table. The manual
resolves the ground-roll attitude with the ground angle's sign reversed
against its own construction figures, and carries the same reversal into the
datum drag load factor; this tool follows the figures. So the braked-roll,
side-load and supplementary-nose families' body-frame components differ from
p232 — the side family's body drag reads 186 lb **forward** where the book
prints it aft (LIMIT, the basis the book prints on) — and case 1's datum
load factors read 3.269 / 3.216 / 0.585 against the printed
3.287 / 3.216 / 0.679. The ground-line ("primed") set,
which is what p230/p231 print, is untouched by both. Each deviation is
documented in the
[approved-corrections register](../20_theory/02_approved_corrections.md).

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

One block — LANDLOAD's whole case set, 40 conditions — with its CSV and text
downloads. Loads are ULTIMATE with the SF stated; the load factors, the
fuselage axis angle and every position are dimensionless, angular or
geometric and are never scaled.

**Two frames, and every row names its own.** LANDLOAD works each reaction out
against the **ground line** — perpendicular and parallel to the runway
through the contact patches, the frame a gear engineer reads — and then
resolves the same reaction into the **airplane datum**, the FS/WL body axes of
[Conventions](03_conventions.md). The manual prints the whole matrix twice for
exactly that reason, and the two tables differ by a rotation of the ground
angle, so a number without its frame is not a load. The split here:

- **The airplane-datum set is the deliverable** — it is what the screen table
  and the **CSV** carry, and what a beam model or an export deck applies. A
  `Frame` column states it in-band, so a CSV forwarded on its own still says
  which axes its numbers are in.
- **The ground-line ("primed") set is the manual's analysis view** — VMP/DMP/
  SMP and VNP/DNP/SNP per wheel, the resultants, NVP/NDP/NS, and the
  unbalanced moments whose labels carry no "(datum)". It rides in the **text**
  download, beside the datum set, and is deliberately not in the CSV. It is
  also where you find the cells the book prints on p231 when you cross-check.

The blocks, in order:

- **The LGFACTOR condition** — sink rate, the computed airplane load factor N
  and gear factor NLG, and the governing pair the matrix actually runs at.
  Frameless: none of these is a force.
- **The 33 ground cases, one condition each**, named by family, case number
  and the landing CG case it runs at — `3-wheel level landing — case 1 (aft
  max landing)` through `supplementary nose-wheel — case 33 (fwd light)`.
  Each case delivers **three wheels — nose, left main, right main, all three
  on every case**, an unloaded gear reported at zero rather than left out:

  - `Fx, Fy, Fz` per wheel in the airplane datum — the force itself;
  - `x, y, z` per wheel — **the point that force acts at**, which is the
    axle on some families and the ground contact point on others (the
    manual's own printed point-of-load column, restated in words in the
    condition note and in the CSV's `Applied at` column);
  - `node x, y, z` per wheel — the gear reference point the reaction is
    *transferred to*, which is where a structural model picks it up. It is a
    destination, not a point of application, so it names no `Applied at`.

  Then, per case: the **fuselage axis angle** (the attitude's ground angle),
  the airplane-datum load factors **NR / NV / ND**, and the **datum unbalanced
  moments** in pitch, roll and yaw. Cases 25–33, the supplementary nose-wheel
  family, are nose-only reactions with no airplane in equilibrium behind them,
  so they carry neither datum load factors nor moments.
- **Six critical-reaction summaries**, one per FAR ground family — level
  landing, tail-down, one-wheel, side load, braked roll, supplementary nose
  wheel — each the governing case of its family, reported in the same shape.

Sanity checks: sink rate lands in the regulation's 7-to-10 ft/s band; N sits
above NLG by exactly the lift factor's share; the two main verticals of a
level landing roughly balance weight × NLG; side and braked cases split per
the regulation's fixed fractions; nose-gear verticals stay positive — a
negative one means the CG or gear geometry is off. Two that are new with the
frames: the fuselage axis angle equals the attitude's ground angle, and the
airplane sits **nose-up** on the ground, so a purely ground-vertical reaction
must show a **forward** (negative `Fx`) body drag component, never an aft one.

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
- **Reading one frame's numbers as the other's.** The CSV is airplane datum
  throughout and says so in its `Frame` column; the primed set is ground line
  and lives in the text download. Comparing a `Fz` against a printed VMP, or
  handing a ground-line resultant to a beam model, is comparing across a
  rotation of the ground angle.
- **Taking a wheel's reference node as its point of application.** The `node
  x/y/z` rows are where the reaction is *transferred to*; the force acts at
  the `x/y/z` rows, at the axle or the ground contact point per the case. The
  two are a strut and a rolling radius apart — a moment arm, not a label.
