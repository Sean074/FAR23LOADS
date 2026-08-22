- **Single-dev merge discipline recorded, and the backlog removal rule
  de-conflicted (process, tier S, 2026-08-22).** `DEVELOPMENT_PROCESS.md` §0
  now states the PR-mode rules while solo — one open PR at a time, sync on
  `origin/main` before opening, and a squash-merged branch is dead (never
  committed to again; the #53/#54 duplicate-history conflict is the evidence).
  `00_backlog.md`'s removal rule drops "renumber the remaining rows freely",
  which contradicted §0's no-renumbering row and was the priority table's
  standing merge-conflict source (87ebaf1's reconciliation merge being the
  prior instance); a closing change now deletes its own row and touches
  nothing else, with dense numbering returning only at a re-cut.
  *Superseded in part later in this cycle:* the PR-mode rules went with the
  per-item PR itself — one milestone branch replaced both, and the #53/#54
  evidence is now recorded there as the reason. The row-removal rule stands
  unchanged and is what lets the priority table close items mid-milestone.
