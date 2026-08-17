- **One-engine-out refuses non-propeller installations (M4-3(b), issue #4, tier S, 2026-08-16).**
  `one_engine_out._case_inputs` raises `MissingInputError` when the failed engine
  has no propeller diameter, so `run`, `time_history` and the UI page all refuse
  instead of simulating with a 0-in windmilling disc; `PROPELLER_ONLY_NOTE` now
  states the enforcement. The gate is the propeller disc rather than
  `engine_type` — `EngineType` has no turbofan member (a fan is entered as `T`
  with a 0-in disc) and the schema is frozen. Reciprocating twins still run;
  the turboprop scope of 23.367(a) stays a coverage-table statement.
  Guard: `tests/test_one_engine_out.py::test_no_propeller_disc_is_refused`.
  (a)/(c) remain parked. Closes #4.
