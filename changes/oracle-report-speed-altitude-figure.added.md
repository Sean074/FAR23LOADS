- **Section 2.4 opens with the speed and altitude envelope (tier M, 2026-08-31).**
  The oracle report's §2.4 gains, ahead of its V-n diagrams, the operating envelope in speed
  and altitude: V(MC), V(MNE) and V(MD) from **sea level** to the maximum operating altitude,
  each constant in equivalent airspeed below the shoulder altitude and Mach-limited above it,
  with Vh marked at sea level where it is entered. The Mach-limited half is tabulated beside
  it from MACHLIM's own `ModuleResult`. The V-n diagrams are slices of this envelope, so the
  envelope now comes before its cuts. The figure has **one builder**,
  `report.content.speed_altitude_plot_data`, shared with the summary report (OR-7) — so the
  summary report's speed/altitude figure now begins at sea level and marks Vh in place of
  starting at the shoulder altitude.
