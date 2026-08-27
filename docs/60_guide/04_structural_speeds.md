# 4. Structural Speeds

*Original program(s):* `STRSPEED+MACHLIM`.

## What this page is for

`STRSPEED` turned the certification category and the wing loading into the
structural design speeds — cruise VC, dive VD, maneuver VA, flap VF — and
the limit maneuver load factors, per FAR 23.335 and 23.337. `MACHLIM`
converted the speed set to Mach across altitude, so a high-flying airplane's
equivalent-airspeed limits can be checked against compressibility. This page
runs both: you state the category and what you know of the speeds, and it
derives the rest, showing the regulatory minimum beside every choice.

## Before this page

[Aerodynamic Data](03_aero_coefficients.md) must be entered — the stall CLs
bound VA and the stall end of the speed set. The wing area and design weight
resolve from [Geometry](01_configuration_layout.md) and
[Weight & Mass Properties](02_weight_mass.md); the page shows the values it
is using, disabled, with their source.

## The inputs

The generated field table for this page:
[`_generated/structural_speeds.md`](_generated/structural_speeds.md).

**Category and design point.** The certification category code (normal /
utility / acrobatic) sets the load-factor formulae and speed minima of
FAR 23.337 and 23.335. The design weight and wing area shown here are reads
of their owners — the MTOW from the weight page, the area from your planform
— because the wing loading W/S is the variable everything on this page
scales with.

**Maximum level-flight speed VH and the shoulder altitude.** VH feeds the
speed minima (the regulation ties VC to a fraction of VH for some
categories); the shoulder altitude is where the gust-line construction and
the Mach conversion are anchored.

**Chosen speeds.** VC and VD as you intend to certify them, entered in knots
EAS; VA, VF and the load factors may be chosen too or left blank to derive.
The rule throughout: **a blank derives the regulatory value; a typed value
is your choice, and the regulatory minimum governs underneath it** — a
choice below the minimum is superseded by the minimum in the derived set,
so compare the result against what you typed.
`vd_basis` selects how VD relates to VC (the classic speed-ratio route, or a
Mach-margin route for airplanes that need it); the target-speed fields let
you state published operating limits (Vne, Vno, Vfe) so the derived set can
be compared against the placard you are aiming at.

**Mach limits.** The maximum operating altitude and the altitude increment
`MACHLIM` tabulates over.

## Screenshots

![The Structural Speeds page with the Appendix A single loaded: category,
chosen speeds and the derived set](img/04_structural_speeds__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

Category **N**, design weight 3,400 lb over the Appendix A wing. VH is
190 kt; VC is chosen at 170 kt against the 33·√(W/S) minimum, and VD at
212.5 kt — exactly 1.25 × VC on the speed-ratio basis, the book's own
choice. VA and the load factors are left to derive: n₁ comes out of the
23.337 formula at this weight, and VA from the stall speed and n₁. Shoulder
altitude 12,000 ft, Mach table to 18,000 ft. Every one of these is the
manual's value, and the derived set on this page is the first place the tool
reproduces printed Appendix A numbers.

## Worked example — twin (`baron_58`)

The certificate publishes operating limits, not design speeds, so the twin
shows the working-backwards case. VC is entered at 195 kt — the published
Vno — and VD at 248 kt, an estimate constructed from the published
Vne 223 kt through the customary Vne = 0.9 VD, because no dive speed is
published. VA is left blank: the derived value (≈161 kt at MTOW from the
estimated CLmax) lands within a few knots of the certificate's 156 kt
operating VA, which is the sanity check working. Weight 5,500 lb, category
N, VH 202 kt (estimate), Mach table to 20,000 ft. In SI display the speeds
remain in knots — the aviation carve-out of
[Conventions](03_conventions.md).

## Results on this page

Three blocks, all pre-load quantities — factors and speeds, so nothing is
ULTIMATE and nothing carries an SF:

- **Limit maneuver load factors** — n₁ positive and n_neg negative from
  23.337, with the wing loading they were computed at.
- **Structural design speeds** — the derived/chosen VC, VD, VA, VF set in
  knots EAS beside the regulatory minima.
- **Cruise/dive Mach at the shoulder altitude** — `MACHLIM`'s conversion,
  with the equivalent-airspeed-to-Mach bookkeeping at altitude.

Sanity checks: n₁ between 2.5 and 3.8 for a normal-category airplane by the
formula's own bounds; VD comfortably above VC by the basis you chose; VA at
or below the published operating VA (the operating limit may be set below
the structural value, never above); the Mach numbers small for a piston
airplane — if they are not, check the shoulder altitude.

## Common mistakes

- **Entering placarded IAS/CAS as design EAS.** The page works in knots EAS;
  at these speeds and altitudes the difference is small but real — convert
  before typing.
- **Choosing VC or VD below the regulatory minimum** and not noticing the
  minimum governed instead — the derived set floors your choice at the
  regulation's value, so a result equal to VC(min) when you typed something
  smaller is the tool overruling you, silently in the numbers.
- **The wrong category code.** Everything scales from it; a utility-category
  run of a normal-category airplane is wrong on every later page.
- **Backing out VD from Vne with the wrong factor** — state your basis. The
  twin's 0.9 relation is customary, not universal, and the guide marks it as
  the estimate it is.
- **Ignoring the target-speed fields.** If the derived set contradicts the
  placard you intend (a derived VNO above your target Vno), this page is
  where that surfaces cheaply.
