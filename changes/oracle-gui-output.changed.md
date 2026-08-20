- **`FOLDED_MODULES` names the step that runs each folded program (design note 32 step OG-E, tier M, 2026-08-20).**
  `sloads.workflow.FOLDED_MODULES` was a flat tuple of the calc modules with no
  page of their own; the owning step was in the comment above it and nowhere
  else. It is now a `module → owning step key` mapping, with
  `workflow.step_modules(key)` returning a page's programs primary-first. A page
  headed "WTESTIMA+WTONECG+WTENV" has to be able to run all three, and a tuple
  cannot say which page WTESTIMA belongs to. Membership reads (`name in
  FOLDED_MODULES`, `set(FOLDED_MODULES)`) are unaffected — they read the keys —
  and three guards in `tests/test_workflow.py` now hold the mapping to a
  partition: every folded module is registered, names a real step, is not also
  that step's primary, and every registered module runs on exactly one page.
