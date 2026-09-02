- **Figure labels are placed clear of the lines, and axes print readable ticks (tier M, 2026-09-01).**
  Two display defects in `report.plots_tex`, the emitter behind every figure in both the
  summary report and the oracle technical report. Marker labels were all emitted directly
  above their point, so any marker near a line had its label written through it — on the GA6
  that was `Vh` on the never-exceed boundary, two CG cases on the loading edges and all four
  gust points on the V-n boundary. Each label is now placed by a rule evaluated against the
  figure's own geometry: the box the text occupies is scored for clearance from every plotted
  segment, reference line and other marker, and the first position that clears wins — so a
  label with room stays above its marker and only an obstructed one moves. Separately, an axis
  with a large range printed under a shared `·10⁴` multiplier (the speed/altitude figure's
  altitude axis read `0.5 1 1.5`); axes now print fixed ticks with thousands separators.
