- **A sidebar that does the arithmetic the build was doing by hand — and one
  answer to "which MAC?" (#80, C210 build review 2026-08-23, tier M,
  2026-08-26)** — The row asked for two conversions; building them found a
  defect underneath. The %MAC↔station relation was spelled four times across the
  calc package, the report and a view, and the spellings had quietly diverged
  not on the arithmetic but on the reference: WTENV honoured the weight
  envelope's typed XLEMAC/MAC override, the report's `% MAC` column read the
  planform regardless, and the two are drawn on the same chart. `mac_reference`
  now resolves that once — override, else planform (the C210-13 blank-derive
  fallback) — and carries which of the two it was, so a display can name it; the
  relation and its inverse live beside it, with an AST drift guard over every
  shipped package, and the aerodynamic consumers pass a planform reference
  explicitly rather than resolving one. The airspeed half needed the same
  completion in miniature: `convert_airspeed` only ever ran from KEAS, so the
  conversion a user actually has to make — from the KCAS on a POH or a placard —
  had no owner until `eas_from_airspeed` inverted it exactly. Both Tools are
  display-only and both delegate to those owners: the no-dual-path rule holds
  for a sidebar as firmly as for a page. Nothing in the frozen Imperial baseline
  moves, because no shipped example carries the override that made the two
  frames disagree — which is precisely why the guard builds one that does.
