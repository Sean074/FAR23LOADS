- **Whole-project results zip in the shared sidebar (C210-45 / backlog 19c,
  tier M, 2026-08-23)** — The C210 oracle-GUI build review left the owner
  collecting thirteen pages of results one hand-clicked download at a time;
  no control delivered a complete results set. The shared sidebar now builds
  one zip per project: every registered module run in registration order,
  each contributing the CLI's own text report and load-case CSV (same owners:
  `module_text_report`, `io.load_cases_csv` + `csv_comment_block`, results
  stamped from the governing safety-factor table exactly as
  `registry.run_all_modules` does), plus the serialized project and a
  `MANIFEST.txt` naming every module's outcome — skip-and-manifest per the
  error contract (`MissingInputError` = skipped, `ValueError` = failed and
  said so; anything else propagates, M2R-8). The builder
  (`sloads/report/results_zip.py`) is pure and clock-free, so two builds of
  one project are byte-identical; `tests/test_results_zip.py` asserts on the
  zip bytes (manifest completeness, member pairing, ULT header, basis
  statement, project round-trip, determinism), and the oracle GUI's G7
  call-site gate was extended to admit the zip by its naming owner with the
  payload gate stated in place.
