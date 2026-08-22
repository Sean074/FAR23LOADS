- **Solo close loop: the issue is optional, the gate scales to the change set, docs close on `main` (tier M, 2026-08-19).**
  `DEVELOPMENT_PROCESS.md` §0 calls issues and branches *optional* under the solo
  profile, but `solo_start.sh` / `solo_close.sh` required both — an open GitHub
  issue and a `<type>/<slug>` branch — so the two mechanisms the profile
  switched off were mandatory in the tooling that implements it, at four `gh`
  round-trips per item. The issue number is now an optional positional on both
  scripts: omit it and neither calls `gh` at all (no auth check, no issue read,
  no `gh issue close`, no `backlog_issues.py check`); pass it and the old
  behaviour is unchanged. A **docs-only change set** — every path either `*.md`
  or under `docs/` or `changes/` — may be closed directly on `main` (`--slug`
  names the fragment) and skips the checkout, merge and branch delete, and its
  gate is `ruff` · `mypy` plus the five guard files §0 already names rather than
  the whole suite: ~3 s against ~150 s. Any path outside that allowlist takes a
  branch and the full suite; `--full-gate` forces the suite either way, and CI
  on the push to `main` is the gate as before. Re-measured while doing it and
  recorded in `.pre-commit-config.yaml`, whose standing argument against a fast
  subset ("36 s, no test over 10 s", 2026-08-16) is now false in both halves:
  the suite is ~150 s, thirteen tests exceed 10 s, and the longest single test
  (~43 s) is a hard parallel floor no core count can beat. Guard:
  `tests/test_solo_scripts.py`.
  *Superseded in part later in this cycle:* the optional issue number and the
  change-set-scaled gate stand, but closing a docs-only set on `main` was
  removed with the branch-per-item loop — every item now closes the same way on
  the milestone branch (see the milestone-branch entry).
