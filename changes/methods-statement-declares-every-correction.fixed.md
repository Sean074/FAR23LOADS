- **The methods statement declares every approved correction, and its guard reads
  the register (#174, review R-3, tier M, 2026-09-05).** `report.methods`
  declared 3 of the register's 7 approved deviations, so four reached no analyst:
  the truncated-constants sweep (2026-08-17), both LANDLOAD sign corrections
  (#133/#134, 2026-08-29) and WINGGEOM's closed-form integration (2026-08-30) —
  the last three move printed-page figures an analyst compares against the
  manual. All four are now stamped in band on every channel: CSV headers, sbeam
  deck comments, `METHODS.txt`, the workbook's *Methods* sheet and report §5.
  `test_statement_lists_every_approved_correction` no longer checks the rendered
  statement against the tuple it was rendered from — a circular guard CI could
  not fail — but parses
  [`docs/20_theory/02_approved_corrections.md`](docs/20_theory/02_approved_corrections.md)
  and asserts set, order and text against its `## Register` section, with a
  companion asserting no *withdrawn* or *declined* heading is ever declared.
