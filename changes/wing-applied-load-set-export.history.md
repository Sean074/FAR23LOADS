- **The applied wing load set becomes a deliverable (OR-64, tier M, 2026-09-03)**
  — Appendix B.1 was written as a report table, but the ruling that opened design
  note 44 §12 makes it a deliverable *format*: it exists to give the sectional
  loads to a structures model. A format only the report can produce is one the
  analyst retypes, so the row shape moved to the export channel
  (`sbeam_bridge.applied_load_rows`) with a CSV writer beside it
  (`wing_applied_loads.csv`), and B.1 became a consumer that converts and marks
  at the report's own boundary — the pattern §6 already uses for `mass_case_rows`
  and `balanced_case_rows`. The file is offered on the Wing Loads page and in the
  Export bundle. Two facts made this worth doing rather than exporting the
  existing span-load CSV: that file's applied moment `My` is the *increment of
  the cumulative* `Myy`, which on `ga6_normal` PHAA is opposite in sign to the
  free moment at the inboard strips and double-counts the sweep/dihedral transfer
  a geometric model regenerates for itself; and its concentrated masses are
  lumped onto the nearest node with a synthetic offset couple, so on `baron_58`
  PHAA an exported station force reads −2,612.9 lb-ULT where the strip load is
  +883.3. Both are properties of `wing_nodal_loads`, which the sbeam deck still
  uses and which this step deliberately did **not** change — reworking the deck
  means reworking its equilibrium gate, is tier L, and is filed rather than done
  inside a report milestone. The new set's own gate is stronger than the deck's:
  the free moments plus the applied forces' own arms reproduce the cumulative
  root `Myy` exactly on both example airplanes, `baron_58`'s four concentrated
  masses included, where the deck can only claim its `MOMENT` cards sum to the
  root torsion about nothing in particular.
