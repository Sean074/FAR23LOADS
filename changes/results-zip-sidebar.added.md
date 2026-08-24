- **A whole-project results zip in the shared sidebar (C210-45, backlog 19c,
  tier M, 2026-08-23).** "Build results zip" runs every registered module
  against the current project and serves one archive through the browser save
  dialog: `reports/<module>.txt` and `load_cases/<module>.csv` per module that
  ran — rendered by the same owners the CLI uses (`module_text_report`,
  `io.load_cases_csv` + the G8.3 basis statement) so the ULT marker and per-case
  SF are identical by construction — plus the serialized `.project.json` and a
  `MANIFEST.txt` stating every module's outcome (a page that refuses is skipped
  and listed, never silently absent). Both GUIs carry the button (shared
  `app_shell` sidebar); the built zip is keyed to the project's serialized
  identity, so an edit after Build invalidates the stale archive instead of
  serving it. Pure builder `sloads/report/results_zip.py`; payload guard
  `tests/test_results_zip.py` reads the artifact bytes (the G7 pattern).
