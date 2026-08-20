- **`WorkflowStep.bas` said "—" where it meant "none"** (design note 32 OG-3,
  tier S, 2026-08-19). `bas` names the original McMaster program behind a step
  and is `None` for a modern page, but `tail_span_loads` and `balanced_cases`
  — both sloads-only capability (plans 09 and 11) — carried the em dash `"—"`
  instead. An em dash is truthy, so the natural "original programs only" filter
  `[s for s in STEPS if s.bas]` silently claimed two modern pages as ported
  ones (15 steps, not the true 13), and the Home dashboard rendered a dangling
  `" · —"` beside each. Both are now `None`. New guard
  `tests/test_workflow.py::test_bas_is_a_program_name_or_none` asserts the
  *shape* — every non-`None` `bas` is a `+`-joined uppercase program name — so
  any future sentinel fails rather than the two known values being pinned.
  Metadata only: no module, no load, no schema field changes.
