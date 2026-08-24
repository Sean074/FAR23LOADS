- **One Engine Out refuses the condition an airplane cannot have, instead of
  simulating nothing and calling it uncontrollable (C210-43, issue #84, tier M,
  2026-08-24).** FAR 23.367's yaw forcing is `thrust · BLENG` with
  `BLENG = |engine_cg[1]|`, identically zero for a single engine or for a multi
  whose *failed* engine sits on the centreline. Nothing gated it: the Euler march
  ran with no forcing in it and reported zero tail load, zero yaw rate and — since
  nothing ever moved back — `"NOT recovered within 60 s — the airplane is
  uncontrollable at this speed (likely below VMC)"`. A false uncontrollability
  verdict, on a condition the airplane does not have, with every thrust and
  windmill intermediate verifying to the digit beside it.
- **One predicate, three readers.**
  `applicability.engine_failure_not_applicable` states it once.
  `one_engine_out._case_inputs` refuses on it at the same choke point as the
  propeller-disc gate, so `run`, `time_history`, the CLI and the main GUI decline
  identically; the oracle GUI's `render_step` states the reason and **withholds
  the input form** — the #66/PB-7 shape one step earlier, since there is no input
  to take rather than merely nothing to show; and `report/coverage.py`'s 23.367
  row now reads it instead of its own `len(engines) > 1`, which called the
  centreline twin applicable. The report can no longer mark the condition
  analysable while the module declines it.
- **The main GUI's own gate was replaced, not duplicated.** `app/views/one_engine_out.py`
  carried a hand-written `len(project.engines) < 2` warning — right about the
  single, silent about the centreline twin, and worded differently from what the
  module said. It reads the shared predicate now. Its genuinely different case,
  an empty engine list, stays a `gate()` to the Engine Mount page: that is an
  unfinished project, not an airplane without the condition, and the form below
  indexes into the list.
- **Steps are keyed the way #82 taught.** `applicability._STEP_NOT_APPLICABLE`
  maps workflow step key → predicate, guarded by
  `tests/test_applicability.py::test_every_step_predicate_names_a_real_workflow_step`
  so a key naming a page no GUI has fails there rather than silently never
  running. The table lives in `sloads` rather than the front-end for a second
  reason the GUI's own guard enforced: the oracle GUI's page set is derived from
  `workflow` and may not write a step key as a literal (OG-2/G2).
