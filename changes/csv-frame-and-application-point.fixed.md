- **The delivered CSV states its frame and the point each force acts at (tier M,
  schema v59, 2026-08-29).** The landing CSV carried the application point
  **numerically only** — `x`/`y`/`z` per gear — while the word for it (`axle` vs
  `ground contact point`) and the "with respect to airplane datum" frame words
  lived in the condition note and the GUI captions, neither of which this channel
  carries. A standalone consumer could not tell case 1 acts at the axle except by
  comparing coordinates back to the geometry, and the two points are a rolling
  radius apart — a moment arm, not a label. `LoadValue` now carries `point`
  beside `frame` (vocabulary `gear_loads.POINTS`, owner `application_point_of`,
  design note 39 AP-1), the landing module stamps it per leg from Appendix A's
  own printed column, and `report.render.results_to_rows` emits both words in a
  `Frame` column and an `Applied at` column. The force row and the location row
  of a wheel name the point; the **reference-node** row names none, because the
  node is where the reaction is transferred *to*, not where it acts. Both are
  ordinary columns under the data-shaped floor, so the all-empty prune drops them
  from every module that names neither — five landing CSV digests move and no
  other channel changes. Schema hops v58 → v59 (identity: `""` means exactly what
  v58 meant), because `LoadValue` is persisted inside
  `critical.conditions[].loads` (issue #141).
