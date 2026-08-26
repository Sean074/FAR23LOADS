- **A file opened in either GUI now says it was migrated (PB-14, issue #68,
  tier S, 2026-08-25).** `apply_schema_check` asked
  `new_project.schema_version` — but `project_from_dict` runs `migrate`, which
  stamps the dict at the current `SCHEMA_VERSION` before the shell ever sees it,
  so the status was always `ok` and the 🔁 *"Migrated from schema N to 55"*
  notice could not fire: a v41 file (every bundled example) opened, was
  upgraded, and would be rewritten at v55 on save with nothing said. The
  pre-migration version is a fact about the raw dict and now has one reader,
  `io.source_schema_version`, with `io.read_project_dict` splitting the file read
  out of `load_project` so the question can be asked before the hops run.
  `safe_load` takes the dict reader rather than a project builder and builds the
  project itself, which keeps the project and the version it came from together
  for every load action in both GUIs; the JSON editor's Apply had the same dead
  check and was swept in the same change. The now-redundant stamp bump at both
  sites is gone — it was already current. Guards:
  `test_app_shell.py::test_opening_an_older_file_says_it_was_migrated` (a real
  v41 example through the sidebar, asserting the toast), its current-version
  twin, an AST guard that no GUI asks `schema_status` about a built object's
  stamp, and `test_io.py::test_the_version_a_file_was_written_at_survives_the_load`.
