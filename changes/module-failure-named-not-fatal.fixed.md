- **One module with an invalid input no longer takes a whole results page down
  (#145, tier M, 2026-08-29).** `run_all_modules` lets a plain `ValueError`
  propagate on purpose (M2R-8): an invalid domain input and an absent one are
  different answers, and the invalid one must not vanish. Right for the CLI and
  the export, which should fail the run — but the Results Review and Export
  *pages* render every module's results and died whole on the first bad slice,
  showing a traceback instead of the twenty modules that were fine. Three of the
  seven bundled examples carry an aileron or flap slice with no area, so both
  pages were dead on all three, reachable by opening a shipped example.
  `registry.run_all_modules_reporting` returns the failures beside the results
  instead, and both pages name the offending module and what is wrong with it.
  `MissingInputError` is still simply skipped, and `run_all_modules` itself is
  unchanged — the CLI still fails the run, as m2 requires.
