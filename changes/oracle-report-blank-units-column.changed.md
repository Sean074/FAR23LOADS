- **A paired table with nothing to put in its units column no longer prints one (tier S, 2026-08-31).**
  The oracle report's §2.3 *Limit manoeuvre load factors* table stated a blank `Units` cell on
  every row, which reads as a unit somebody forgot to enter. A limit load factor is
  dimensionless — the subsection's own text says so, and "g" would name an acceleration the
  table does not state — so the column is dropped where no row fills it. The structural design
  speeds table beside it keeps its column. The rule is in `_paired_table`, not at the one
  table, so any dimensionless pairing added later behaves the same way.
