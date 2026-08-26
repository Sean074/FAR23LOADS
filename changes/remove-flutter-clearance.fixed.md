- **An `AppTest` script was permanently stubbing a real module** (found while working
  #79, tier S, 2026-08-26). `AppTest.from_string` execs its script in the *running*
  process, so `_NO_ARTIFACT_SCRIPT`'s `r.step_results = lambda …` (added with #89) rebound
  the attribute on `oracle_app.results` for the rest of the session — every later test
  that imported it got a one-block stub for a page called "flap". Harmless when written,
  because nothing after it read `step_results`; it stopped being harmless the moment
  something did, and the symptom was a `KeyError` in an unrelated test that came and went
  with the xdist worker split. Restored in a `finally` (the stub is the point of that
  test), and a new guard reads every `*_SCRIPT` constant and fails on any other
  module-attribute assignment — including in the one script that is a `str.format`
  template and cannot be parsed, which is scanned textually so it cannot become the hole.
