- **`Series` says whether a polyline bounds a region (tier L, 2026-09-01).**
  `report.content.Series` gains `closed`, and `planform_tex` closes a path only when it is
  set. A planform outline is a closed region; the loads reference axis drawn on the same
  figure is not, and closing it would cut a chord from tip back to root that no part of the
  airplane follows. `report.content.Units` gains `load_value`/`plain_value`, the number forms
  of the conversions its string methods already made, so a plotted load goes through the
  ULTIMATE boundary by the same route as the tabulated one beside it.
