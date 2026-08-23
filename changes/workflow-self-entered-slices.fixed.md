- **Self-sufficient pages no longer send the user upstream for their own
  inputs** (CR-D-3, issue #45, tier M, 2026-08-22): on a fresh project, 2 of
  the 14 oracle pages said "run the pages before this one first" for a slice
  **their own form enters** (`weight_mass`/`weight`, `engine_mount`/`engines`).
  `WorkflowStep` gains `edits` — the slices a page's own form enters, declared
  minimally — and `workflow.missing_upstream` / `missing_self_entered` split a
  missing requirement by remedy: the oracle blocked note now points a
  self-entered slice at the form above, and the Dashboard shows those steps as
  ready-to-enter rather than blocked. A DAG-completeness guard
  (`tests/test_workflow.py`) holds every `requires` to some step's `produces`
  or some step's `edits` (the Step-G6 `tail_loads`/`vtail_loads` proxies are
  declared on Geometry, guarded to fall out when #52 retires them), with a
  field-registry rot companion on each declaration. The never-called `page()`
  context manager and its `_PRODUCER` map were removed from
  `app_shell/components.py` — every view gates with its own page-specific
  `gate()` call, which is now the documented pattern of record.
