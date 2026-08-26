- **The non-owner mark reaches composite fields, and an empty result block no longer
  crashes the page (#89, code review 2026-08-24 §4.3, tier S, 2026-08-25).**
  `_copy_note` was reachable from `render_scalar` alone, so the first non-owner tuple,
  curve or enum set would have rendered bare and silently editable — the #36/CR-A-2
  defect returning through a door never closed. Marking the external owners walked
  straight through it: `engines[].engine_cg` is a three-member tuple copied from the
  weight database. `render_field` now forwards the project to every branch and the
  composite renderers caption; a display-only composite would need a mark the renderer
  cannot give, so the registry may no longer hold one. Separately,
  `st.columns(len(block.artifacts))` is guarded for the empty case, which would have
  taken down any results page carrying a table and no download.
