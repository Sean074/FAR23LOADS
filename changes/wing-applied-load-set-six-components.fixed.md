- **The exported wing deck's torsion is applied, not differenced (design note 46, tier L, 2026-09-03).**
  `sbeam_bridge.wing_nodal_loads` built its `MOMENT` cards by differencing the
  cumulative `Myy` between adjacent stations. That column already contains the
  sweep and dihedral transfer of the shear carried outboard, so a solver
  applying the card at a point — and generating the transfer itself, from the
  geometry — counted the transfer twice. Under the rigid-body accumulation a
  solver performs, the exported wing torsion was wrong by **151 / 190 / 120 %**
  on `ga6_normal` (PHAA / TORS / ACRL) and **34 / 21 %** on `baron_58`; shear
  and both bending columns closed exactly, which is why the error survived a
  full closure sweep. The nodal set is now the **applied** set on the deck's
  nodes — each strip's own `fx`, `fz` and free torsion `myy_free` at its own
  point, each concentrated wing mass reduced to the node inboard of it as its
  force plus the **full** three-component `r × F` offset couple (the couple's
  torsion member is the one the differencing had been supplying wrong). It
  reproduces the published `Sx`, `Sz`, `Mxx`, `Myy` and `Mzz` at **every**
  station of every case of both example airplanes to ~1e-15 relative. `FORCE`
  cards are unchanged — a strip's own load and the difference of the cumulative
  shear are the same number — so only `MOMENT(My)` moves. The deck's
  equilibrium claim strengthens with it: the wing now asserts the full
  rigid-body `m.y`, where before only the bare card sum `m0.y` could be
  asserted and `equilibrium.py` recorded the weaker claim as a convention.
  Side-of-body internal and collapsed loads state their torsion about a shared
  reference point (`sob_reference_point`), which a free-moment card set makes
  load-bearing where a differenced one did not.
