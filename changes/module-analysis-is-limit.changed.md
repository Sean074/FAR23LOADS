- **Module analysis is a LIMIT channel (design note 48, tier L, 2026-09-04).**
  The CLI's text and CSV output, the app's per-module tables and download
  buttons, the export bundle's `_report.txt` and per-module CSVs, and the
  sidebar's results zip now render **LIMIT** loads: the calc's own values, plain
  units with no `-ULT` marker, and the safety factor named in the `SF` column
  without being applied. ULTIMATE remains the channel of case selection, the
  sbeam export deck, the case index and the oracle technical report — none of
  which moves. `report.LoadChannel` is the parameter and it **defaults to
  ULTIMATE**, so the frozen `oracle_app` renders exactly as before without
  passing one (**OR-77**); `app/` and `cli.py` opt in explicitly.
  `methods_statement` takes the channel too, so a stamped CSV forwarded on its
  own states **its own** basis rather than the bundle's — the old block asserted
  "All loads reported here are ULTIMATE" into every CSV header, which stopped
  being true of the file it was stamped into.
- **The load-unit vocabulary has one owner (tier L, 2026-09-04).**
  `units.LOAD_UNITS` / `units.is_load_unit`, moved out of `report/render.py` now
  that the limit/ultimate boundary is no longer its only consumer
  (CLAUDE.md rule 3).
