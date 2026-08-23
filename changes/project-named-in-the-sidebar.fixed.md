- **The project is named in the sidebar, and Save never overwrites unasked**
  (review 2026-08-22 PB-6, issue #65, tier S, 2026-08-23). `project.name` is
  document metadata, so no oracle page rendered it: a project built in the
  oracle GUI was called `""` for its whole life, every *Save to disk* wrote
  `projects/project.project.json` over the last one, Open could never list
  more than that entry, and a *named* project reached the filesystem raw
  (`ATR 42-300 ("ATR 42-100" prototype … analog) — 2x PW120.project.json`:
  legal on macOS, an `OSError` on Windows). The **Project name** widget is now
  the shared sidebar's, beside the file it names, for both GUIs — the `app/`
  dashboard's copy is removed, since two widgets for one field write their
  retained state over each other. One sanitiser, `io.project_filename`
  (`[^A-Za-z0-9._-]` → `_`, runs collapsed, edges trimmed, stem capped at 64,
  never empty), names the saved and the downloaded file alike. Save remembers
  the `projects/` file a project was opened from or last saved to and writes it
  back unasked; any *other* existing file gets an overwrite dialog first. The
  `.project.json` suffix is one constant (`io.PROJECT_SUFFIX`) that Open,
  Save and the examples listing share. Guards: the sanitiser's cases, the
  widget naming the download, a fresh save then an unasked re-save, the
  overwrite refused until confirmed, Open → Save going back to the same file.
