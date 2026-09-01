- **Section 2.2 draws the weight and centre-of-gravity envelope (note 44 OR-45 / note 45 WE-8, tier M, 2026-08-31).**
  The oracle report's §2.2 gains the figure the manual prints at Appendix A p140,
  *"USEFUL LOAD ENVELOPE AND STRUCTURAL LIMITS"*: both loading edges swept from the
  minimum flight weight, the closed structural CG-limit envelope, and every entered
  weight/CG case marked — cases sharing a point sharing one marker and both names. The
  plotted vertices are tabulated beside it, weight, station and waterline, read from
  WTENV's own `ModuleResult` rather than re-swept. The figure has **one builder**,
  `report.content.weight_cg_plot_data`, shared with the summary report (OR-7), so the
  summary report's weight/CG figure gains the aft edge and the closed limit envelope in
  place of its three vertical limit rules. `report.oracle_content.run_sections` now runs
  a step's **folded** modules as well as its primary one, keyed by module name —
  `sloads.workflow.step_modules` owns that set — so a page whose `bas` names three
  programs can report from all three without a second run point.
