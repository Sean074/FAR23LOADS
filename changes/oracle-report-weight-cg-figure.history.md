- **Section 2.2's weight/CG envelope figure (note 44 OR-45, note 45 WE-8, tier M, 2026-08-31)** —
  section 2.2 stated the mass properties and the CG cases in tables and drew nothing, while
  the analysis it documents has a figure in the manual: Appendix A p140 plots the useful-load
  envelope against the structural limits, and Ch 3 p21 tells the reader to plot both. It now
  carries that figure. Three decisions shaped it. The limits are drawn as one **closed**
  envelope rather than as the manual's three vertical rules, and are omitted entirely when a
  corner is unentered — a boundary with a side missing reads as permission, which is the one
  way this figure could actively mislead. Both loading edges are drawn, which is why design
  note 45 preceded this step at all: the port computed only the forward one, and on the GA6
  that is the edge which never approaches a limit while the aft edge passes 2.2 in beyond the
  aft-gross station, so the figure that was buildable before this work would have shown
  containment it had not demonstrated. And the figure has one builder shared with the summary
  report (OR-7) rather than an oracle-only copy, which means the summary report's own weight/CG
  figure gained the aft edge and the closed limit envelope in the same change — a tier-M
  behaviour change to a delivered capability, taken deliberately rather than as a side effect,
  because two documents drawing one airplane two ways is the defect the shared-owner rule
  exists to prevent. Two smaller things fell out. The vertices are tabulated from WTENV's own
  `ModuleResult` rather than swept in the report, which required `run_sections` to run a step's
  **folded** modules as well as its primary one — `weight_mass` names `WTESTIMA+WTONECG+WTENV`
  and its numbers legitimately come from all three — and the guard that says section 2 invents
  no number was widened the same way, through `workflow.step_modules` rather than by exemption.
  The table does **not** name the item added at each vertex: the analysis does not carry it
  (note 45 WE-3, amended), so the note under the table says so rather than the report inferring
  it from a sort it does not own.
