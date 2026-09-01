- **WTENV computes both edges of the loading envelope (design note 45, tier L, 2026-08-31, issue #157).**
  `WTENV.BAS` sorts the discretionary weight items by fuselage station, sweeps them
  cumulatively from the minimum flight weight, then re-sorts in the opposite order and
  sweeps again — one subroutine (`GOSUB 657`) called twice, printing a **forward** and an
  **aft** edge. The port emitted the ascending sweep alone. Both edges now come from one
  direction-taking sweep, each vertex carrying the weight, station **and waterline** the
  original prints, and both are oracle-locked to Appendix A p139 — all 16 printed rows on
  all three printed columns, within ±0.1 %. The aft edge is a new
  `ConditionResult` appended after the four that existed; nothing that existed changed, and
  the ballast reference selection still reads the forward edge alone, so no delivered load,
  load factor, CG case or balanced condition moves. `sloads.modules.weight_envelope`
  gains the public `loading_envelope(project, aft=...)` and the `EnvelopeVertex` triple;
  `loading_envelope_points` stays as its station-only projection for existing callers.
  WTENV's summary shape (`report.render.weight_station_rows`) gains a **Waterline** column,
  shown only for a result set that has one.
