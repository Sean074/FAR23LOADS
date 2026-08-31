- **A deleted row is the row the button names (#153, tier M, 2026-08-30).**
  The per-row delete in the oracle form removed the *last* row rather than the one
  it named: clicking "Delete row 2 · aileron" on `ga6_normal` removed `flap`. The
  deletion always reached the project — what undid it was the render that
  followed. A row widget keys itself by row index and Streamlit's retained state
  outvotes the value seeded from the model, so every row below the deleted one was
  renumbered onto its neighbour's state and the tail of the table was typed back
  over itself one place up. `_retire_renumbered_rows` now retires the state of the
  rows a deletion renumbers, and only those: a row above the deletion did not move
  and keeps an edit typed in the same interaction as the click. Swept across both
  table shapes — the flat grid is one `st.data_editor` whose pending edits are an
  index-keyed map, and a polyline inside a renumbered row had a cached frame
  drawing the row that used to be there. Unreachable before this milestone, which
  gave `ga6_normal` seven surfaces where every fixture had held two.
