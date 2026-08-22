- **Sidebar Upload edge-triggered (#34, review 2026-08-20 CR-D-1/CR-D-9, tier
  M, 2026-08-20)** — the first row of the 0.7.0 band: the shared shell's Upload
  handler acted on `st.file_uploader`'s *presence* (state) as if it were an
  *event*, so a clean load looped adopt → rerun → re-adopt unboundedly
  (resetting the dirty baseline each pass) and a dirty load reopened the
  discard dialog on every run — Cancel's own `st.rerun()` landed back in the
  same branch, so the dialog could not be dismissed until the file was cleared
  from the widget. Both GUIs inherited it via `render_shell_sidebar`. The fix
  latches on the upload's identity (`file_id`, falling back to name+size),
  recorded before `load_with_guard` runs, giving Upload the same
  once-per-action semantics the button-gated Open/Load-example paths always
  had: Cancel cancels, a parse failure is shown once not looped, and a fresh
  upload (new `file_id`) re-arms. The CR-D-9 rider landed with it: Download
  now writes `<name>.project.json`, the suffix Save and Open agree on.
  AppTest guards in `tests/test_app_shell.py` stub the uploader and count
  `load_with_guard` calls — the edge invariant itself. `GUI_design.md` §4
  states the once-per-action rule for every load path.
