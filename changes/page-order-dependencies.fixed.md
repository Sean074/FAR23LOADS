- **A page states the later page its numbers depend on (#69, PB-15/PB-19, tier M, 2026-08-25).**
  Flap Loads computes its FAR 23.457(b) slipstream case from an engine record entered
  two pages later, and WTESTIMA correlates against the engine list's combined power
  rather than the horsepower typed beside it. Run either page first and it showed a
  complete-looking answer that moved once the Engine page was filled — ~19 % of the
  governing flap load on the C210, the slipstream being a whole delivered case that
  did not exist yet — with nothing on the page saying the dependency existed.
  `WorkflowStep.reads` now declares those dependencies and
  `app_shell.components.render_page_order_reads` states them: the slice and the page
  that enters it on every visit, escalating from caption to warning while that page
  is still empty. `requires` was the wrong instrument — it blocks, and both calcs are
  correct with no engine at all. Seven declarations across four steps (Geometry,
  Weight & Mass, Balanced Cases, Flap Loads), found by sweep rather than by report.
- **A copy whose owner is not a field is marked too (#69, C210-41 step 1, tier M, 2026-08-25).**
  `_copy_note` returned early on `owner_is_external`, so the half of the registry that
  records "owned, but not by a field" was dark: engine weight and CG (owner: the weight
  database, D-25), the engine-mount limit load factor (the computed 23.337 limit), and
  the weight estimate's engine count and horsepower all rendered as silent peer inputs.
  All six are now captioned with their owner in words. They are never disabled — an
  external owner is an expression with no value to substitute, and one of them is the
  fallback the calc uses when the owner is empty — and where `governs` alone would
  state the rule wrongly the row carries the true sentence in a new `FieldEntry.resolves`.
