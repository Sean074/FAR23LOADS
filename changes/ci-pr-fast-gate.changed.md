- **The PR CI leg runs uninstrumented; coverage enforces on the push to
  `main`, under the sysmon core (process, tier S, 2026-08-22).** Coverage
  instrumentation on the 2-core runner had grown `test (3.12)` on a PR past
  27 minutes (vs ~2.5 uninstrumented local minutes); the 80 % floor is one
  number a PR almost never moves, so it now rides the merge push with the
  3.9/3.11 compatibility legs, fixed forward (`DEVELOPMENT_PROCESS.md` §0).
  The instrumented leg measures with `COVERAGE_CORE=sysmon` (Python 3.12's
  `sys.monitoring`, near-zero overhead), which is line-only below 3.14 —
  `branch = true` leaves `[tool.coverage.run]`; branch figures remain
  available locally with `--cov-branch`.
