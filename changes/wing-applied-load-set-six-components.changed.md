- **The applied wing load set states all six body-axis components (design note 46, tier L, 2026-09-03).**
  Appendix B.1 of the oracle technical report and the `wing_applied_loads.csv`
  download beside it published `Fz`, `Fx` and `Myy free`. A consumer writing
  `FORCE`/`MOMENT` cards needs the whole vector, and from three columns cannot
  tell whether a missing one is zero or merely unpublished. Both views now
  carry `Fx`, `Fy`, `Fz`, `Mx`, `My`, `Mz`, with the three structural zeros
  **printed** and their reason stated: the wing chain has no producer for a
  spanwise strip load and no delivered wing condition is lateral (`Fy`), and a
  strip applies forces and a section moment and nothing else, so all of the
  cumulative `Mxx`/`Mzz` is those forces acting through arms the coordinates
  already state (`Mx`, `Mz`). The map from the calc's positive-magnitude beam
  convention to right-handed body axes has one owner, `applied_body_moments`
  over `coordinates.bending_moment_vector`, so neither view carries sign logic.
  Both wing CSVs now state in-band which moment convention each column block
  uses — the span-load file carries applied card components and cumulative beam
  integrals side by side, and its `Mz` and `Mzz` have opposite senses.
