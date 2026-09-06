- **`SurfaceInput.front_spar_pct` / `.rear_spar_pct` (design note 50, tier L, 2026-09-05).**
  Replaced by the entered station, not kept beside it: two stored fields for one
  quantity with only one of them on the page is the duplicate-owner shape this
  project removes rather than marks. The **v60 → v61** hop is the first in the
  live chain that converts a value rather than being an identity — a file that
  *entered* a fraction has its station computed from that airplane's own
  polylines, so a carry-through survives the hop as the same physical station
  instead of reverting to the (also changed) default. All seven bundled examples
  wrote both keys `null`, so no fixture data moved (OR-124, OR-127).
