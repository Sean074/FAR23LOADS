- **"Download project.json" and the dirty flag describe this run's edit, not
  the last one** (review 2026-08-22 PB-4, issue #64, tier M, 2026-08-23). The
  shell sidebar rendered above `pg.run()`, so the rerun that carried a widget
  edit serialised the download and read the dirty flag *before* the page
  persisted the edit: the button served the previous interaction's project
  while the caption said clean — every last edit in the oracle GUI (no Apply),
  the Apply's own merge in `app/`. `render_shell_sidebar` is now a context
  manager around the page (`with render_shell_sidebar(project): pg.run()`,
  both GUIs): units and About render on entry, the project-file block into a
  slot reserved between them on exit. A page's early exit is
  `app_shell.components.stop_page()` — Streamlit discards everything emitted
  after `st.stop()`, the slot included, so the 45 `st.stop()` calls across the
  `app/` views were swept to it in the same change (standalone it *is*
  `st.stop()`; a guard refuses a new `st.stop()` in `app/views`). The oracle
  form's row-expander titles, which lagged the typed name for the same reason,
  read the widget state first. Guards on the real oracle entry point: one edit,
  then payload, caption and expander title in the same run; a stopping page
  keeps Save/Download. Found along the way: the shell's upload tests stubbed
  `st.file_uploader` in-process and never restored it, so any later sidebar
  test in the file was adopting a fake upload — the stubs are restored on exit.
