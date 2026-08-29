# Conventions

The rules below are stated once, here, and every chapter leans on them. Their
single owner in the repository is
[`CONVENTIONS.md`](../10_standard/CONVENTIONS.md) — this page summarises what
a user needs and links the authority; where the two could ever disagree, the
owner wins.

## Axes and stations

All positions are entered in **airplane axes, in inches**:

- **x** — fuselage station, positive **aft**;
- **y** — butt line, positive **right** (starboard);
- **z** — waterline, positive **up**.

The **datum** (x = 0) is yours to choose; every station in the project simply
measures from it. Use your airplane's established datum — the worked twin
keeps its type-certificate datum so the certificate's arms can be typed in
unchanged. Loads follow the same frame: lift is +z, drag is +x, and every
reported torsion names the axis it is taken about.

Spanwise positions on a surface are butt lines from the centreline; planforms
are entered as leading- and trailing-edge corner points in these same
station/butt-line coordinates on the [Geometry](01_configuration_layout.md)
page.

## Frames: airplane datum and ground line

The axes above are the **airplane datum**, and almost every page in the guide
works in it alone. The ground-loads chain is the exception, because the
original suite works there in two frames and prints both:

- **Airplane datum** — the body FS/WL axes above. This is the **delivered**
  frame: what a beam model applies, what the export decks carry, and what the
  downloaded CSV states.
- **Ground line** — perpendicular and parallel to the runway through the
  wheels' contact patches, the frame a gear engineer reads a reaction in.
  LANDLOAD computes in it and the manual prints it as the "primed" set
  (VMP, DMP, NVP…). It is an analysis view, and it rides in the **text**
  report rather than the CSV.

The two differ by a rotation of the attitude's ground angle, so the same
reaction has different components in each and the frame is part of the
number's meaning. Wherever a value names a frame, that name travels with it:
on screen, in the text report, and as a `Frame` column in the CSV.
[Landing Loads](14_landing_loads.md) is where you will meet both.

A delivered force also names **where it acts** — its point of application, in
the same airplane-datum coordinates, stated both as `x/y/z` numbers and, where
the point has a name (a wheel's axle, its ground contact point), as a word in
an `Applied at` column. A force without a point is not yet a load a structural
model can take.

## Units and the Imperial/SI boundary

The calculation, like the original suite, runs in **Imperial units**
(lb, in, kt), and the project file stores Imperial values. The sidebar's
units toggle is a **display boundary**: with SI selected, every input widget
and result table converts on the way in and out, and nothing about the stored
project or the computed loads changes. Two consequences worth trusting:

- You can enter an airplane wholly in SI — the guide's twin is worked that
  way end to end — and reopen it in Imperial to see the same airplane.
- **Airspeeds and altitudes never convert**: knots EAS and feet in both
  systems, the aviation standard.

Every downloaded file states its unit set in-band, so a CSV on its own says
what its columns mean.

## LIMIT and ULTIMATE

This is the guide's one statement of the contract; each chapter's *Results*
section only says which of the two its blocks carry.

FAR 23 distinguishes **limit** loads (the largest expected in service) from
**ultimate** loads (limit × the factor of safety, normally 1.5 per
14 CFR 23.303). In this tool:

- The calculation works in LIMIT internally.
- **Every deliverable load is ULTIMATE.** The factor is applied exactly once,
  at the render/export boundary, and to load quantities only — never to
  speeds, angles, weights, geometry, or dimensionless load factors.
- **The `-ULT` marker is part of the units string** (`lbs-ULT`,
  `lb-in-ULT`), so a number's units always say what it is.
- **Every case states its SF.** The factor comes from the governing
  safety-factor table, one row per FAR condition family, each with a stated
  basis. `SF=1.5` is the normal limit→ultimate factor; **`ULT SF=1.0` means
  the case is already defined at ultimate** (some FAR conditions are), not
  that the factor was skipped.
- A page may show a LIMIT quantity only when it is explicitly marked LIMIT —
  the One Engine Out time histories are the example you will meet.

When you cross-check the single against the manual's printed Appendix A
figures, remember the book prints LIMIT loads: compare against the tool's
values *before* the factor, i.e. divide the ULT figure by its stated SF.

## Reading a results table

Every page renders its program's results as one table per result block,
below the input form. The recurring columns:

- **ID** — the case identity (`W-01`, `HT-03`, `LG-05`…), minted once by the
  first program that names the condition and kept by every later view of it.
- **FAR** — the regulation paragraph the case implements (`23.421`…).
- **Condition** — the case in words, as the original program named it.
- **Component / CG / Speed / Altitude** — the state the case is computed at.
- **Quantity, Value, Units** — one row per reported quantity, units carrying
  the `-ULT` marker where the ULTIMATE contract applies.
- **SF** — the case's stated safety factor, as above.
- **Frame / Applied at** — the frame the value is stated in and the named
  point the force acts at, per the section above.

A column that no row on the page fills is dropped rather than shown empty, so
a page of properties renders as Condition / Quantity / Value / Units, and only
the pages that work in two frames carry `Frame` and `Applied at`.

## Reading a downloaded CSV

Each result block offers its table as CSV (and formatted text). The files
carry the same rows and columns as the screen — the two are written from the
same data, so they cannot disagree — plus the in-band units statement. Open
them in any spreadsheet; nothing in them is scaled, renamed, or rounded
differently from what you saw on the page.

The **text** download is the one place that can carry *more*: where a program
states a quantity in a frame that is an analysis view rather than a
deliverable, the text report keeps it beside the delivered set and the CSV
does not. LANDLOAD's primed (ground-line) rows are the case in point.
