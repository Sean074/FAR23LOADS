- **The GUI no longer claims ULTIMATE on LIMIT deliverables, and G-OR-74 now
  reaches the screen (#192, tier M, 2026-09-05).** Note 49's OR-116 made every
  delivered load LIMIT, but its AST sweep was a one-off discovery pass, so the
  gate that replaced it read only rendered documents. **21 live false claims
  survived in 15 `app/` files** — including a *"Download net wing loads —
  ULTIMATE (CSV)"* button whose bytes are byte-identical to the module's LIMIT
  values, so an analyst who trusted the label under-sized by 1.5, and captions
  on Wing, Fuselage, Tail, Landing, Flight Envelope and Results Review stating
  *"= limit × 1.5 (14 CFR 23.303)"* of numbers nothing multiplies. All are now
  LIMIT statements naming the factor they do not apply.
- **The Wing and Fuselage download buttons name their channel, not their basis.**
  Both files on each page have been LIMIT since OR-116, so a basis marker no
  longer distinguishes them: they are now *analysis table* and *sbeam bridge*.
  The `*_ULT.csv` file names are unchanged and stay stale until OR-81 (0.8.3).
- **G-OR-74's checker could be defeated by typography.** `_CLAIMS` was a
  substring list, so markdown emphasis split `**ULTIMATE** = limit` and the
  U+00D7 `×` in `limit × SF` never matched its ASCII spelling; text is now
  normalised before the scan. The claim boundary also excludes a trailing
  hyphen, so Structural Speeds' true *"ULTIMATE-independent design limit
  speeds"* is no longer a false hit.
- **A green test was pinning the false claim.**
  `test_deliverable_units.py::test_the_export_page_states_the_system_it_will_write`
  asserted the Export page caption *contains* "ULTIMATE"; it now requires LIMIT.
