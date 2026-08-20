- **Solo close loop, cycle-time revision (tier M, 2026-08-19)** — The solo
  profile (§0, 2026-08-17) made branch-per-item and issues-as-record optional,
  but `scripts/solo_start.sh` and `scripts/solo_close.sh`, written to implement
  it, required an open GitHub issue and a `<type>/<slug>` branch on every
  invocation; each closed item therefore paid an issue it did not need and four
  `gh` round-trips (`auth status`, `issue view`, `issue close`,
  `backlog_issues.py check`) for a system of record §0 had already handed to
  `00_backlog.md`. Three changes bring the tooling back to what the profile
  says. The issue number became an optional positional on both scripts, and
  omitting it drops every `gh` call rather than degrading to a warning. A
  docs-only change set — every path `*.md` or under `docs/` or `changes/` — may
  now be closed on `main` without a branch, `--slug` supplying the fragment
  name; the allowlist is deliberately narrow so that anything touching `.py`, a
  fixture or config still takes a branch and keeps somewhere to abort to. And
  the gate scales to that same predicate: a docs-only set runs `ruff` · `mypy`
  and the five guard files §0 already recommends for docs edits, ~3 s against
  the suite's ~150 s, with `--full-gate` to override and CI on the push to
  `main` unchanged as the real gate. Measuring the gate to size it produced the
  fourth change: `.pre-commit-config.yaml` had argued since 2026-08-16 that no
  fast subset could pay, on the basis that the suite ran in 36 s with no test
  over 10 s. Re-measured 2026-08-19 the suite is ~150 s, thirteen tests exceed
  10 s, and the slowest single test (~43 s, `test_deliverable_units.py`) sets a
  parallel floor the whole suite cannot go below — so the comment was replaced
  with the measurements and their two consequences, and §0's advice to run
  `test_deliverable_units.py` *while iterating* was re-timed to once before
  closing, that file now being the slowest in the repository. The growth is
  concentrated in four fixture-driven files and splitting them, not a slow
  marker, is the fix; it is left as a separate item rather than folded in here.
  `tests/test_solo_scripts.py` gained guards for the optional issue (asserting
  each named `gh` call disappears with it), the docs-only allowlist and gate
  set, and the two refusals that keep closing on `main` honest.
