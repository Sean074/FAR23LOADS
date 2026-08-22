- **The solo loop is one milestone branch per release, not one branch and one PR
  per item (`DEVELOPMENT_PROCESS.md` §0, tier M, 2026-08-22).**
  `scripts/solo_start.sh dev/vX.Y.Z` opens a single branch off `main` for a
  release; every item of that milestone is worked and committed directly on it
  by `scripts/solo_close.sh --slug <slug> [<issue>] "<Subject>"` — one commit
  per closed item, with the item's issue closed and its priority-table row
  removed *in that commit*, so the backlog stays a live view of what is still
  open mid-milestone. The release is then cut on the same branch
  (`RELEASE_PROCESS.md` §4 — there is no separate `release/x.y.z` while solo)
  and reaches `main` as **one** pull request merged with a **merge commit**, so
  every per-item commit survives and `git log` stays the step-per-commit record.
  The defect class this closes is two closing paths both claiming to close the
  item: #38 mixed a hand-made PR with `solo_close.sh`, and the PR body's
  `Closes #38` closed the issue before the script's own `gh issue close` ran;
  #53/#54 committed to a branch whose PR had already squash-merged; and the
  `--ff-only` push needed an admin bypass because `main` requires a PR. With one
  path, `main`'s branch protection stays fully on and no bypass is used.
  `solo_close.sh` no longer checks out, fast-forwards or pushes `main`, no
  longer deletes a branch, and no longer has a close-on-`main` docs-only path
  (the docs-only predicate now sizes the gate and nothing else); `--slug` became
  required, since the branch names the milestone rather than the item.
- **CI runs the fast gate on `dev/**` and reserves the full matrix for the merge
  to `main` (tier M, 2026-08-22).** Pushes to a milestone branch run one
  interpreter (3.12 uninstrumented), `mypy` and the 3.12 solver round-trip —
  measured 7.3 min — as an **advisory** signal: `dev/**` is unprotected, nothing
  waits on it, and it runs while the next item is already being worked. The
  3.9/3.11 compatibility legs and the coverage-instrumented 3.12 leg run on the
  push to `main`, which under this model is the milestone merge. The three
  matrix conditionals now key on *push to `main`* rather than on "is this a pull
  request" — keyed the old way, a `dev/**` push would have taken the other arm
  and run the ~27-minute instrumented matrix on every item.
- **The design-note issue template asked for a label that does not exist (tier S,
  2026-08-22).** `.github/ISSUE_TEMPLATE/design-note.md` requested `kind:note`,
  which was never created — `gh` refuses the whole `issue create` on an unknown
  label, so every design note opened from the template failed or lost its kind.
  Found while filing this item's own issue. The template now asks for
  `kind:decision`, which exists and is what a design note records, and
  `DEVELOPMENT_PROCESS.md` §4's label enumeration was corrected to the live set
  (it listed `kind:note` too, and omitted `kind:decision`).
