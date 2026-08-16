- **Multi-developer development process (design note 28, MD-1…MD-12, tier M,
  2026-08-16).** Trunk-based branches + protected `main` (PRs only, 1 reviewer ≠
  author, CODEOWNERS review, squash-merge; `self-merge-ok` for tier-S docs/hygiene
  PRs on green CI); **closure travels in the PR**; **history entries become
  `changes/<slug>.history.md` fragments** rolled to the top of the history file
  at release cut by `scripts/build_changelog.py` (tier M paragraph / tier L step;
  guarded in `tests/test_changelog_fragments.py`); **GitHub Issues + Project are
  the system of record** for open work with `00_backlog.md` as the plan
  (`scripts/backlog_issues.py plan|create|rewrite|check`, parser guarded in
  `tests/test_backlog_issues.py`); design note as a PR before code, `Owner:` /
  `Reviewers:` lines on every live note; concurrency rules for `SCHEMA_VERSION`,
  the Imperial digest and case-ID bands ("rebase before you regenerate");
  `.github/CODEOWNERS` (`@Sean074`), `CONTRIBUTING.md`, `PULL_REQUEST_TEMPLATE.md`,
  three issue templates, `docs/10_standard/DEVELOPMENT_PROCESS.md`; `CLAUDE.md`
  points at them (still ≤160 lines); `.claude/settings.local.json` git-ignored.
  Branch protection and the one-off issue migration are the owner's GitHub steps.
