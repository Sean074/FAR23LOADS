- **Full-project review filed, and the backlog given the milestones it was missing (review `2026-09-04_project_review.md` R-1…R-27, issues #172–#191, tier S, 2026-09-05).**
  A two-phase pass at `dev/v0.8.2` — implementation, maintainability and process
  controls, then analysis-method accuracy, safety-factor application and
  third-party-analyst usability. **No wrong number was found on any delivered
  load surface**, and an independent re-derivation of global equilibrium from the
  shipped balanced deck's own cards (written outside the project, using no sloads
  code) closed to 5.5e-8 Imperial / 2.2e-6 SI across all 44 subcases on both the
  `ga6_normal` oracle fixture and `concept_regional_jet`. The findings are filed
  as issues, the folds as comments on their host issues (R-8→#170, R-22→#17,
  R-25→#19), and the triage lands as Pri 26–35 of `docs/30_future/00_backlog.md`
  — an **addition, not a re-cut**: the 2026-08-29 order stands, and the
  milestone-less **band D is dissolved**, its rows keeping their Pri numbers and
  taking the milestones the triage assigned. The three first-order rows are
  deliverable-facing: the LRA decks for `ga6_normal` and `cessna_210` do not
  solve in the pinned sbeam while the roundtrip gate covers only the two
  fixtures that pass (#172), the shipped methods statement declares 3 of 7
  approved oracle deviations behind a guard that checks itself (#174), and the
  balanced deck ships `SOL 101` + `SPC = 1` over zero elements with the
  explanation living only in a test docstring (#173). Defects #170 and #171 gain
  bodies in the backlog's open-defect index and issue numbers in design note 48's
  findings list. The dissolution itself is guarded: it left **#92 and #130 in the
  table twice**, in two bands and two milestones with two bodies, which
  `test_backlog_issues.py`'s render round-trip caught at closure — the band-C
  originals are removed and the 0.9.0 copies the triage assigned are the ones
  that stand.
