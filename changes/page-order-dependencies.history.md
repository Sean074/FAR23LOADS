- **Page-order dependencies are declared and stated; the non-owner mark reaches
  external owners and composites (#69 + #89, tier M, 2026-08-25)** — Two defects with
  one root: the GUI knew a thing about a field's provenance and did not say it.
  `WorkflowStep` gains `reads`, the slices a step's numbers depend on that neither
  gate the run nor are entered on the page, and `app_shell.components.render_page_order_reads`
  states them on every visit — caption when the dependency is filled, warning while it
  is not. The instrument matters: `requires` blocks, and the flap and weight-estimate
  calcs are correct with no engine at all, so enforcing would have refused a valid
  glider run to fix a page-order problem. Declaring and stating leaves the calc alone.
  The dependencies were found by sweeping every step's modules by AST rather than from
  the two reported instances: seven across four steps, and that sweep is now the guard
  (`test_every_page_order_dependency_is_declared`), with a reverse test failing on a
  stale declaration. On the marking side, `_copy_note`'s early return on
  `owner_is_external` is gone — all six EXTERNAL rows are captioned with their owner in
  words, never disabled (the owner is an expression, and one of them is the calc's
  fallback), and a new `FieldEntry.resolves` carries the true sentence where `governs`
  alone would state the rule wrongly. Marking them exposed #89's latent door in the
  same session: `engines[].engine_cg` is a tuple, and the mark only ever reached
  scalars, so `render_field` now forwards the project to every branch. The render guard
  counts marks per owner phrase rather than searching for it once — two fields on the
  Engine Mount page name the same external owner, and a substring test passed while the
  tuple beside the scalar rendered bare. `st.columns(0)` guarded with it. No calc
  changed: the Imperial baseline digests and every oracle are untouched.
