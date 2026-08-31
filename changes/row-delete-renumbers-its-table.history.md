- **A deleted row is the row the button names (#153, tier M, 2026-08-30)** — the
  oracle form's per-row delete removed the last row instead of the named one, silently
  and with no undo, on the Geometry page the 0.8.2 report review is conducted from. The
  filed root cause was wrong: it blamed `_delete_row`'s `on_click` args binding a list
  detached by the next run, so that `del rows[index]` never reached the project.
  Instrumented, the callback receives the project's own attached list and the deletion
  lands every time; the *render* undid it, because a row widget keys itself by row index
  and Streamlit's retained state outvotes the model-seeded `value=`, renumbering every
  row below the deletion onto its neighbour's state. This is `app_shell.widget_keys`'
  generation argument at table scope — a renumbered row is a different widget and
  re-seeding cannot fix it — and it is now stated in `GUI_design.md` beside the row-counter
  rule it belongs with. Fixed as a class rather than in the shape that showed it: the flat
  grid's `st.data_editor` holds index-keyed pending edits and the cached frame of a
  polyline in a renumbered row draws the row that used to be there, so both are retired
  too, and both delete tests now snapshot whole rows rather than names — the shift moved
  values between rows, which is how the flat shape's test passed against a defect it
  shared. The defect was unreachable while every fixture carried two surfaces (deleting
  row 2 of 2 removes the last row either way) and this milestone made it reachable by
  giving `ga6_normal` seven. `oracle_app/form.py` is hash-frozen for 0.8.2 by design note
  44 OR-13; the owner lifted OR-14 and admitted the fix under OR-15 in session on
  2026-08-30, on the reasoning that the milestone created the exposure, and the manifest
  hash is updated in the same commit.
