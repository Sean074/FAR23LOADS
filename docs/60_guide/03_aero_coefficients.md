# 3. Aerodynamic Data

*Original program(s):* none — a modern page the workflow needs.

## What this page is for

No single original program owned the aerodynamic coefficients; each one
prompted for the few it needed, and the same number was typed again and
again. This page enters them once. It is deliberately prose-light on theory:
the tool does not estimate aerodynamics for you, and this guide does not
teach how — what it does state, for each coefficient, is *what it is, where
an engineer gets it, what it drives downstream, and how to sanity-check it*.
Derivations live in the [theory sources](../20_theory/00_theory_sources.md).

The sourcing ladder, in order of preference, is the same for every entry:
**measured or wind-tunnel data → a published handbook method (DATCOM,
Roskam, the airfoil's own published data) → a defensible estimate, marked as
an estimate.** Both worked examples name their source per value.

## Before this page

Nothing must have run first, but have the airfoil data and any
wind-tunnel/flight-test lift and drag data collected
([Before you start](02_before_you_start.md)). The wing planform from
[Geometry](01_configuration_layout.md) tells you the aspect ratio the
finite-wing corrections need.

## The inputs

The generated field table for this page:
[`_generated/aero_coefficients.md`](_generated/aero_coefficients.md).

**Maximum lift coefficients.** `CLmax` clean, its negative counterpart, and
`CLmax` with flaps down.
*What they are:* the airplane's usable lift limits, positive and negative,
in the stability-axis sense (positive lift up).
*Where from:* stall speeds, if the airplane has flown — `CLmax` follows
directly from stall speed, weight and wing area; otherwise the airfoil's
section data corrected for finite span by a handbook method.
*What they drive:* the curved stall boundary of the V-n diagram, the
maneuver-speed corner VA, and which gust points can actually be reached —
they bound nearly every flight condition
([Flight Envelope](05_flight_envelope.md)).
*Sanity:* clean values sit near the airfoil's section maximum less a finite-
wing decrement; the flap value exceeds the clean one; the negative value is
roughly half the positive, negative sign.

**Lift, drag and moment polynomials.** Each polar record (cruise, and
optionally flaps-down) states CL, CD and Cm as polynomial coefficients in
angle of attack **in degrees**: constant term first, then the linear slope,
then curvature terms.
*What they are:* the trimmed-airplane-less-tail aerodynamics `FLTLOADS`
balances against — the linear lift term is the airplane lift-curve slope per
degree, the drag record is the polar (constant CD0 plus the induced term on
CL²-like curvature), the moment record is the pitching moment about the
reference.
*Where from:* flight-test or tunnel polars fitted to polynomials; otherwise
CD0 from a drag build-up, induced drag from aspect ratio and a span
efficiency, lift slope from the section slope with a finite-wing correction,
Cm from the airfoil's section moment and the wing's geometry.
*What they drive:* every balanced flight condition — the tail load that trims
the airplane, the chordwise (nx) load factors, and through them the wing,
fuselage and tail load pages.
*Sanity:* lift slope near `2π/(1 + 2/AR)` radians converted to per-degree;
CD0 of a few hundredths for a clean GA airframe; Cm0 small and negative for
a conventional cambered wing.

**Wing-line quantities for tail balance.** The wing aspect ratio, lift-curve
slope per radian, and the zero-lift-line angles (cruise, en-route, landing
configuration).
*What they are:* how the tail programs convert airplane attitude into wing
lift and downwash.
*What they drive:* the balancing and maneuvering tail loads
([Tail Loads](08_tail_loads.md)).
*Sanity:* the per-radian slope should be the per-degree lift slope × 57.3 —
they describe the same wing.

**Basic airfoil moment for SELECT.** The section zero-lift pitching moment
the selection program uses for wing torsion.
*Sanity:* the airfoil's published `cm0`, sign negative for conventional
camber; it should agree with the moment polynomial's constant term in
spirit.

**Optional body terms.** The fuselage pitching-moment slope and the lateral
body derivatives (`Cy_β`, `Cn_β`) — off by default, and the analyses state
when they are excluded. Enable them only with a number you can defend; the
defaults reproduce the original suite.

## Screenshots

![The Aerodynamic Data page with the Appendix A single loaded: CLmax
values and the cruise polar record](img/03_aero_coefficients__page-ga6-normal.png)

## Worked example — single (`ga6_normal`)

Appendix A's own coefficients, typed as printed: CLmax 1.4068 clean /
−0.59 negative / 1.5857 flapped; cruise lift polynomial 0.320479 +
0.080358·α (a lift slope of 0.0804 per degree — ×57.3 gives the 4.605 per
radian the tail-balance group repeats); drag 0.026917 + 0.053647·α²-term;
moment −0.017328 + 0.004128·α. These are the manual's fitted polars, and
keeping them exact is what lets every downstream page reproduce the printed
figures.

## Worked example — twin (`baron_58`)

No polar is published for the Baron, so every entry is a marked estimate
anchored to something published: CLmax clean 1.15 and flapped 1.53 are
**derived from the published stall speeds** (~84 kt clean, ~73 kt landing)
through the constructed wing loading — entering them makes the tool's
computed 1-g stall reproduce those speeds, which is the sanity loop closed.
Lift slope 0.080 per degree from the 230-series section slope corrected for
aspect ratio 7.19; CD0 0.028 for a tidy retractable twin with nacelles;
induced term from AR and a 0.8 span efficiency; cm0 −0.008 for the
NACA 23016-class sections, echoed in SELECT's basic airfoil moment. Item by
item: [`examples/baron_58.sources.md`](../../examples/baron_58.sources.md).

## Results on this page

The page renders the coefficient set back as entered — the stall CLs, the
polar records and the configuration each applies to — as a check readout;
there is no load output here and nothing carries a safety factor. The real
"result" of this page appears one page later, when the flight envelope's
stall boundary and corner speeds land where your data says they should.

## Common mistakes

- **Per-radian and per-degree confusion.** The polynomial slopes are per
  degree; the tail-balance slope is per radian. The ×57.3 between them is
  the first thing to check when tail loads look wrong.
- **CLmax from the wrong weight.** Deriving CLmax from a stall speed at some
  test weight, then running the envelope at MTOW — derive at the weight you
  state.
- **A drag polar without its induced term.** CD0 alone balances to
  optimistic chordwise load factors; the curvature term is load-bearing.
- **Signs.** Negative CLmax is negative; cm0 for conventional camber is
  negative. The page takes what you type.
- **Enabling the optional body terms with placeholder numbers.** Off, they
  reproduce the original suite and say so; on, they move real loads — enable
  them only with sourced values.
