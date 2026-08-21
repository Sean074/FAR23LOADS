- **The sidebar Upload is edge-triggered — the unbounded rerun loop and the
  inescapable discard dialog are gone from both GUIs (#34, review 2026-08-20
  CR-D-1/CR-D-9, tier M, 2026-08-20).** `st.file_uploader` returns the same
  file on every rerun while it sits in the widget; the shared shell re-loaded
  and re-adopted it each run (adopt → rerun → re-adopt), and on a dirty project
  reopened the discard dialog faster than Cancel could close it. The handler
  now latches on the upload's identity (`file_id`, recorded before the guard
  runs), so an upload loads exactly once, Cancel genuinely cancels, and a
  failed parse is not retried every rerun; a fresh upload re-arms the edge.
  Download writes `<name>.project.json` — the suffix Save and Open agree on —
  so a downloaded file dropped into `projects/` is listed by Open. Guards:
  `tests/test_app_shell.py` (once-across-reruns, Cancel-sticks, re-arm,
  filename convention).
