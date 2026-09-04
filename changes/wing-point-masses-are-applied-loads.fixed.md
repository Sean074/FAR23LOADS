- **Concentrated wing masses are published as applied point loads (#166, tier L, 2026-09-03).**
  `WINGINER` adds each concentrated wing mass — engine, gear, fuel, a store — to the
  cumulative shears, bending and torsion of every station inboard of it, and leaves the
  per-strip `Fz`/`Fx` panel-only. The mass was therefore published nowhere as an *applied*
  load, so any set of strip loads handed to a structural model was short by the whole of it:
  on `examples/baron_58.project.json` PHAA, **4,821.5 lb of a 5,004.1 lb root shear**, exactly
  the load factor times the four entered masses. It is inertia relief, so the omission is
  unconservative in shear and, with the masses at 57-95 in span, substantially so in root
  bending. `WingLoadResult` now carries a `point_loads` list of `ConcentratedLoad`, each a
  pure force at its own `X`, `Y`, `Z` — a concentrated mass has no free moment, since every
  moment it produces is that force acting through an arm the geometry already states.

- **`WingStationLoad.myy_free` is populated by the wing chain (tier L, 2026-09-03).**
  The field existed and was left `0.0`, so the free per-strip torsion had to be reconstructed
  from the cumulative column by undoing the sweep and dihedral transfer. That reconstruction is
  exact for an air load and **wrong** once a concentrated mass steps the shear — the step is
  not a transfer, so it lands in the recovered free moment as a spurious term. It is now
  published at source: the section pitching moment from `AIRLOADS`, the panel mass' 50%-chord
  offset from `WINGINER`, summed by `NETLOADS` and shifted with the reference axis on the
  strip's own force. No cumulative value moves and no oracle is affected.
