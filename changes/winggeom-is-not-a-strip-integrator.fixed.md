- **WINGGEOM is no longer described as a strip integrator (#155, tier M, 2026-08-30).**
  The closed-form planform integration shipped earlier in 0.8.2 left the surrounding
  prose behind: `wing_geometry`'s own module docstring still taught the strip method
  its `surface_properties` had stopped using, and `configuration` reported
  MAC/XLEMAC/AR as coming "via the WINGGEOM strip integrator" — a note the oracle
  report reproduces verbatim in §2.1. Corrected everywhere the claim appears
  (`wing_geometry`, `configuration`, `airloads`, `models/inputs`, three test headers,
  `PROGRAM_SPEC.md`, `00_theory_sources.md`, `01_concept_loads_plan.md`), while
  statements about strips that are still true — AIRLOADS' own span loop, the spanwise
  load stations, `tail_geometry` — were left standing.
- **The WINGGEOM surface table reports `Load stations`, not `Integration elements`
  (tier M, 2026-08-30).** `elements` is the user's spanwise load-station count and no
  longer drives any integral, so the row now says what it is (key
  `integration_elements` → `load_stations`; nothing read it). No number changes.
- **The Appendix A aileron is a tight oracle again (tier M, 2026-08-30).** Its ±2 %
  band existed only because the strip sum's result depended on an element count the
  manual never tabulates. Closed-form integration reaches area 932, MAC 11.645 and
  AR 7.036 within 0.037 %, so the tolerance returns to the suite's ±0.1 %.
