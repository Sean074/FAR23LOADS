# 6. Wing Loads

*Original program(s):* `AIRLOADS+WINGINER+NETLOADS`.

## What this page is for

Three original programs turn the selected wing conditions into spanwise
structural loads. `AIRLOADS` distributes the air load across the span by the
Schrenk approximation from the section data you enter here; `WINGINER`
distributes the wing's own mass the same way, so the inertia relief that
opposes the air load is spanwise too; `NETLOADS` subtracts one from the
other and integrates: net shear, bending and torsion at every strip the
Geometry page divided the wing into. This is the page where the airplane
first gets a beam-loads answer.

## Before this page

[Geometry](01_configuration_layout.md) must carry the wing planform (the
strips come from it), and the load cases this page distributes are
[Flight Envelope](05_flight_envelope.md) selections — each case row can name
the SELECT condition it represents. The section aero inputs below are this
page's own.

## The inputs

The generated field table for this page:
[`_generated/wing_loads.md`](_generated/wing_loads.md).

**Spanwise section data.** Per surface, the quantities `AIRLOADS` needs at
each span station: the section lift-curve slope, the spanwise **twist**
polyline (station, degrees — washout entered as the real distribution, with
as many points as the wing needs), profile drag and section pitching-moment
polylines, taper and tip ratios, and the Schrenk blending parameter. These
come from the airfoil data and the loft; the section `cm` drives torsion
directly, so source it as carefully as the lift.

**Wing panel mass.** `WINGINER`'s smeared structure: the panel weight **per
side**, the tip-to-root density ratio that tapers it, and the inboard rib
station where the panel starts. The panel weight must be the wing structure
your weight database carries — the page's consistency check compares the two
and says when they disagree.

**Concentrated masses.** Anything on the wing that is not smeared structure:
engines, gear, tip tanks, fuel — one row per item **per side**, at its
station, butt line and waterline. Each concentrated row is a step in the
spanwise inertia diagram; on a twin, the engine row is the largest single
relief on the wing.

**Load cases.** The conditions to distribute: each row carries the
normal and chordwise load factors, the CL, the speed and any unbalanced
rolling moment, either copied from a SELECT condition by name or entered
directly — the sign conventions are the original program's, exactly as
Appendix A prints them.

## Screenshots

![The Wing Loads page with the Appendix A single loaded: section data,
panel mass and the case table](img/06_wing_loads__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

The section data is Appendix A's: slope 0.1075 per degree, a four-point
twist polyline from 5° at the root through the strake kink down to 1.9° at
the tip, flat 0.01 profile drag and −0.03 section moment. Panel weight
165 lb per side tapering at 0.95, inboard rib at butt line 23, and **no
concentrated masses** — the book's single carries its engine on the nose and
its gear on the body, so the wing panel is all there is. Three cases, the
manual's own: `PHAA` (the positive high-angle-of-attack corner), `TORS` (the
torsion-critical dive-speed case) and `ACRL` (the aileron-roll case with its
unbalanced rolling moment), each with the book's printed factors, CLs and
speeds.

## Worked example — twin (`baron_58`)

The same entry with the twin's estimates: slope 0.107, a straight 3°-to-0°
washout, panel 280 lb per side at 0.9 taper, inboard rib at the fuselage
side. The difference that matters is the **concentrated list**: per side, the
engine+propeller+nacelle lump at the estimated butt line 66, the main-gear
leg at the 57.5-in half-track, the wing fuel at its tank centroid and a
systems lump — together they carry most of what the wing lifts, and the
consistency tie (wing-tagged database rows = panel + concentrated, per side)
is what keeps this list honest against the weight page. Two cases, PHAA and
TORS, at the twin's derived corner and dive speeds.

## Results on this page

Two blocks:

- **Net wing loads per case** (ULTIMATE, `-ULT` units, SF stated): the root
  values — net shear, bending and torsion at the side of body — one
  condition per case.
- **Spanwise wing stations** (**LIMIT, marked as such**): the full station
  table — running air and inertia loads, integrated shears, bending and
  torsion at every strip, with the torsion axis named (25 % chord unless
  your reference axis says otherwise). This is the printed `NETLOADS` table,
  kept LIMIT so it can be compared with the book directly.

Sanity checks: bending grows monotonically root-ward and is maximum at the
side of body; a concentrated mass shows as a visible step in the shear
curve at its butt line; PHAA governs bending while TORS governs torsion;
and on the single the root bending reproduces Appendix A within the oracle
tolerance.

## Common mistakes

- **Panel weight entered for both sides.** It is per side; doubling it
  doubles the inertia relief and undercuts the net loads.
- **Forgetting the wing-mounted masses.** A twin whose engines are missing
  from the concentrated list overloads its wing root bending by the whole
  missing relief — the page's mass tie warns, read it.
- **Twist as a single number.** The polyline is the distribution; one point
  makes the wing untwisted from that station outward.
- **Comparing the LIMIT station table against ULTIMATE summaries.** The two
  blocks differ by exactly the safety factor; the basis column says which
  you are reading.
- **Case signs.** The case table keeps the original program's sign
  convention — enter cases the way Appendix A prints them, or copy them
  from SELECT by name and do not retype.
