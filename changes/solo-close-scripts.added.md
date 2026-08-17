- **Solo close loop as scripts — `scripts/solo_start.sh` + `scripts/solo_close.sh` (issue #27, tier S, 2026-08-17).**
  `DEVELOPMENT_PROCESS.md` §0's loop is now a guarded command sequence rather
  than a chat transcript (rule 3). `solo_start.sh <issue> <type>/<slug>`
  preflights (on `main`, clean tree, `gh` authenticated, issue open, branch
  new) and opens the branch; `solo_close.sh <issue> "<Subject>"` refuses until
  the tier's `changes/` fragment(s) exist and the item's `(#N)` row has left
  the priority table, then runs gate → commit → `--ff-only` land + push →
  `gh issue close` with the `main` SHA → verify (branch delete,
  `backlog_issues.py check`, issue state, last CI run), stopping at the first
  failure with the recovery printed; `--dry-run`, `--skip-gate`, `--yes`,
  `--slug`, `--suffix`. Guard: `tests/test_solo_scripts.py` (`bash -n`,
  `--help`, dry-run step order). §0 points at the scripts. Closes #27.
