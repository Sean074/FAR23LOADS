- **Workflow command crib sheet** (`docs/10_standard/WORKFLOW_COMMANDS.txt`,
  tier S, 2026-08-22): copy-paste command sequences for a release under the
  solo profile — opening the `dev/vX.Y.Z` milestone branch, closing each item
  on it with `solo_close.sh`, cutting the release on that branch and landing
  the milestone on `main` as one merge-commit pull request, and the recoveries
  (a mid-sequence script stop, a moved remote, the one out-of-band hotfix). A
  plain-text summary of `DEVELOPMENT_PROCESS.md` §0, which stays the authority.
  (First written for the branch → PR → squash-merge loop and rewritten later
  the same day, when that loop was replaced — see the milestone-branch entry.)
