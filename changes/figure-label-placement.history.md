- **Marker-label placement and axis ticks in the shared figure emitter (tier M, 2026-09-01)** —
  both documents' figures come from one emitter, and it had two habits that only showed up once
  the figures got crowded enough to matter. Every marker label was emitted `anchor=south`,
  directly above its point, which is the right answer until something is there: the GA6's V-n
  diagrams wrote all four gust labels across the manoeuvre boundary, the weight/CG figure wrote
  two CG cases across the loading edges, and the new speed/altitude figure put `Vh` on the
  never-exceed line. The fix is a placement rule rather than a table of offsets — a per-figure
  offset is correct for the project it was tuned on and silently wrong for the next one, and
  these figures are built for whatever project a reader loads. Each candidate position is scored
  by the clearance of the **box the text occupies** from every plotted segment, every reference
  line and every other marker, in normalised axis units so the two axes are comparable. Two
  earlier attempts are recorded in the code because both were wrong in instructive ways: scoring
  a single point beside the marker placed `CG3 / fwd light` so that its first character cleared
  the loading edge and its remaining fourteen did not, and taking the *roomiest* position rather
  than the first acceptable one moved every label in the document, including the ones nothing was
  near — a figure whose labels sit above their markers except where they cannot reads as a
  convention, one whose labels each point a different way reads as a fault. The box-to-segment
  distance is exact (Liang-Barsky clip, then corner and endpoint distances) because sampling
  points around the box let a box straddle a line with samples either side and none on it. The
  second defect was smaller: pgfplots reaches for a shared `·10ⁿ` multiplier past a certain
  exponent, so the altitude axis read `0.5 1 1.5` under a `·10⁴`. Every other axis in both
  documents was already fixed-notation, so turning scaled ticks off changed the one figure with a
  large range and no other — and forecloses the question for the next one.
