- **The applied wing load set is an export, not just an appendix (OR-64, tier M,
  2026-09-03).** `export.sbeam_bridge.applied_load_rows` /
  `applied_load_csv` publish the loads a structures model is built from — `Fz`,
  `Fx` and the section free moment `Myy free` at each strip's own point, plus one
  row per concentrated wing mass at its own coordinates — as
  `wing_applied_loads.csv`, ULTIMATE, in the solver unit channel, with its
  torsion axis and per-case `SF` in-band. Offered as **Download applied load
  set** on the Wing Loads page (stated about the wing's loads reference axis,
  like the Export page's) and carried in the Export bundle with its own manifest
  row. The applied moment is the **free** moment, never the increment of the
  cumulative `Myy`: the two carry different physics and differ in sign on
  `ga6_normal` PHAA's inboard strips, because `ΔMyy` includes the sweep and
  dihedral transfer of outboard shear that a model applying these forces at these
  coordinates regenerates for itself.
- **The oracle report's Appendix B.1 is now a view of that one owner (OR-64,
  tier M, 2026-09-03).** The table and the downloadable file are assembled from
  the same list and gated against each other row for row, so the appendix a
  stress analyst reads and the deck they build cannot disagree about what is
  applied.
