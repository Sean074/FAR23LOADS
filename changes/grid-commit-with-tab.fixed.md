- **A grid cell typed and confirmed with Enter was still discarded** (C210-4 residual,
  issue #77, tier S, 2026-08-25). Streamlit's `st.data_editor` keeps the cell editor
  **open** on Enter — the value is on screen but not in the frame the widget returns —
  and the next Tab or click closes the editor by throwing it away. Reproduced in a bare
  Streamlit 1.58.0 app during the Cessna 210 build, so it is the grid's behaviour and
  there is no version of `form.py` that fixes it: every oracle page that renders a grid
  now says **"commit a grid cell with Tab, not Enter"**, above the first one.
  The sentence is owned by `app_shell.components.GRID_COMMIT_NOTE` rather than by the
  GUI that says it today, because fourteen of the sixteen `st.data_editor` call sites
  are in `app/views/`, whose layout is frozen pending #29 — that page set adopts the
  note by importing it, not by retyping a sentence that would then drift.
- **The warning had been withdrawn for a defect it did not cover** (#77, tier S,
  2026-08-25). Enter dropping an entry was *also* a symptom of C210-4, the remount race
  that was ours, and when `_stable_frame` closed that race on 2026-08-23 the Enter
  warning went out with it — the two presented identically as "Enter loses my entry"
  and only one of them was fixed. The guard is therefore two-sided: a page that renders
  a grid must say it *and* a page that does not must stay silent, so the note and the
  grids cannot part company again.
- **The loader half of #77 was already closed.** "The loader coerces or refuses a
  non-numeric corner, under a guard" (C210-7 residual) shipped on 2026-08-24 as #76 —
  `io._numeric_shape` reading the numeric containers off the model's own annotations,
  swept across all 18 of them. Recorded here because the issue asked for both halves.
- **The geometry-presentation family had been recorded under this issue's number**
  (#77/#95, tier S, 2026-08-25). Backlog row 20, the 2026-08-24 code review's
  existing-rows list and the completed-development history all pointed the C210
  geometry family at `#77`, which is this grid defect — and the geometry family had
  no issue at all, while `#77` appeared in no planning document. Found by reading the
  issue before working the row. Filed as **#95** with a body (rule 5) and the backlog
  corrected; the two reviews and the history keep what they said, as dated records,
  and row 20 says how to read them.
