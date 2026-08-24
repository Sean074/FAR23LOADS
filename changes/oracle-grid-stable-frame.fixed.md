- **Grid edits no longer vanish at typing pace in the oracle GUI (C210-4, build review 2026-08-23, tier S, 2026-08-23).**
  Every committed cell rebuilt the grid's input frame from the model, which changed
  `st.data_editor`'s widget identity (it includes the data bytes), which remounted the
  grid on the frontend — and any keystroke in flight when the remount landed was
  silently discarded (the write-back anti-pattern). At a normal typing rhythm roughly
  every other cell was lost, which made the 21-row Cessna 210 items table "impossible
  to enter" (owner); the same race turned a typed `-25` into `25` (the minus opened
  the cell editor, the remount reset it, the digits landed in a fresh overlay) and
  made Enter appear to drop entries. The base frame each grid renders from is now
  **stable for the page visit** (`_stable_frame` / `_FRAME_CACHE_KEY`): edits live in
  the widget's own state and are persisted to the model each run (equality-guarded,
  so idempotent); the frame rebuilds on page change, row-count change, unit toggle
  and project load. Numeric columns also carry an explicit `NumberColumn` config.
  All three symptoms confirmed gone by the owner on the fixed build (first-attempt
  commits, Enter commits, typed negatives land).
