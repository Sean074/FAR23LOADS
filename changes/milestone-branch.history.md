- **Milestone branch replaces the per-item branch-and-PR loop (solo profile, tier M, 2026-08-22)** —
  The solo profile's closing half had two paths — `solo_close.sh`'s `--ff-only`
  land on `main`, and a hand-made branch → PR → squash-merge — and the failures
  of the previous week were all at their seam rather than in the middle of
  either: #38 used both at once, so the PR body's `Closes #38` closed the issue
  and the script's own `gh issue close` then failed on an already-closed issue;
  #53/#54 pushed a follow-up to a branch whose PR had squash-merged, whose
  commits then conflicted with their own squashed copy; and every scripted land
  needed an admin bypass, because `main` requires a pull request and the script
  pushes. The revision keeps exactly one path. `dev/vX.Y.Z` is opened off `main`
  once per release and every item is committed directly onto it; the item's
  issue is closed and its priority-table row deleted in its own commit, which is
  what preserves `backlog_issues.py check` as a live mid-milestone guard rather
  than something suspended until the merge. The release is cut on that branch —
  `RELEASE_PROCESS.md` §4 gains a solo paragraph saying so, and §6 gains the one
  case that still puts a commit on `main` out of band (a hotfix to an
  already-released version), with the instruction to merge `main` back into the
  milestone branch immediately and re-check the three shared counters. The
  milestone lands as one pull request with a **merge commit**: squashing a whole
  release into one commit would have cost the step-per-commit `git log` that §0
  and §2 both lean on, so "require linear history" comes off `main` while the
  solo profile is in force and §2's bullet records that the switch-over restores
  it. CI was re-keyed to match: the fast gate on every PR *and* every `dev/**`
  push, the full 3.9/3.11 + coverage matrix only on the push to `main`. The
  budget question that shaped this — a per-step CI under five minutes — was
  answered with measurement rather than configuration: the fast gate is 7.3 min
  of which pytest is 7.2, and at four xdist workers the suite is ~1,700
  CPU-seconds spread broadly, the slowest fifteen tests being only ~13 % of it.
  No leg can be dropped to buy two minutes and no slow-test split moves it; a
  suite-wide fixture reduction would, and is filed as band B. The 7.3 min is
  accepted instead, on the ground that an advisory signal nothing waits on does
  not need to be fast — the gate that costs time is the local one. `rule 3` is
  served by `tests/test_solo_scripts.py`, which now holds the two scripts,
  `ci.yml`'s triggers and matrix conditionals, and the prose in §0 and
  `WORKFLOW_COMMANDS.txt` in step with one another.
