- **`workflow.requires` vs self-entered slices (#45, CR-D-3, tier M,
  2026-08-22)** — `requires` conflated two different remedies: a slice another
  page must produce first, and a slice the page's own form enters. Both read
  as "blocked", so a fresh project's first two working pages — the very pages
  a from-scratch concept starts at — told the user to run the pages before
  them for inputs that had no other home. `WorkflowStep.edits` names the
  self-entered slices (minimally: only where a `requires` has no producer),
  the `missing_upstream`/`missing_self_entered` split gives each consumer the
  honest message, and the DAG-completeness guard makes the classification
  structural: a required slice nobody produces and nobody's form enters is now
  a test failure, not a dead end a user discovers. The fix also removed the
  `page()` scaffold that had promised a generic gate and accrued zero callers
  — the pinned "unlinkable requirements" set that tested it was the prose-rule
  form of this guard, superseded by the closed one.
