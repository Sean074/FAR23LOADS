- **The loader stores numbers, not the text a grid happened to write (C210-7
  residual, issue #76, tier S, 2026-08-24).** `io._points` coerced a polyline's
  *shape* (JSON array → tuple) and passed its members through, so a project saved
  mid-entry — the C210-7 state, where an object-typed grid column hands every
  typed cell back as text — reloaded with `("45", "0")` where a wing corner
  belongs. The file loaded cleanly and died later: `TypeError: unsupported
  operand type(s) for -: 'str' and 'str'` at `wing_geometry.py:112`. The
  mitigation recorded at review time ("the fixed grid repairs them on the next
  Geometry render") turns out to be oracle-GUI-only — in the main GUI the same
  strings kill `to_display` at `configuration_layout.py:818`, which is the page
  that would have done the repairing. The loader is the only boundary that
  reaches both.
- **Stated for the class, not for the corner that found it (rule 4).** Reading
  the numeric containers off the model's own annotations turns up 18, of which
  exactly one — `FlightLoadsInput.altitudes_ft` — coerced. The rest arrived raw:
  both WINGGEOM polylines, the three aero curves (`twist`, `profile_drag`,
  `section_cm`), three `hinges_span_in` lists (an sbeam control-surface export
  input), `OneEngineOutInput.speeds_kt`, the three gear axle points, `attach`,
  and both engine vectors. All are grid-writable, which is how the strings are
  produced in the first place.
- **One rule, read off the annotations (rule 3).** `io._numeric_shape` /
  `_numeric_containers` derive `{field: shape}` from the dataclass type hints, so
  a numeric container added tomorrow is covered the day it is added rather than
  the day someone remembers a list. `_filtered` — the single splat gate every
  `*_from_dict` passes through — coerces on the way in; the three paths that
  bypass it (the polylines via `_points`, the engine vectors, the gear axles)
  call the same coercer instead of growing a second copy of the rule, and the
  hand-written `tuple(...)` passes in `_gear_from_dict` are gone. Guard:
  `tests/test_io.py::test_the_coerced_field_set_is_read_off_the_model_not_a_hand_list`
  asserts the rule over every dataclass in the model, and
  `test_every_numeric_container_survives_a_file_written_as_text` reloads the
  whole GA-6 fixture with every list member written as text and requires 17
  modules to return bit-identical values.
- **Repaired out loud, refused when unreadable.** `"45"` becomes `45.0` with a
  `warnings.warn` naming the field — the #66/PB-7 load-path channel, which
  `project_state.safe_load` renders as a toast — one warning per field, not per
  member, so a 20-point polyline is one message rather than forty. `"abc"` raises
  `ValueError: SurfaceInput.leading_edge[0][0] is 'abc', which is not a number`,
  one of the types the load path already catches and shows as `st.error`. A file
  saved during the crash still opens, which is what lets the grid finish the
  repair; a file that cannot be read as numbers is not guessed at.
- **Scope, deliberately.** Numeric *containers* only. Scalars are the same class
  one step wider, but blanket-coercing every numeric field has to reason about
  `Optional`, enums and bools, and no observed defect points at it. Residual: the
  JSON editor (`app/views/project_editor.py`) works on the raw dict rather than a
  loaded `Project`, so a string typed directly into it still reaches
  `to_display`; the units converter deliberately leaves non-numeric lists alone
  (`test_an_empty_or_mixed_list_is_left_alone`), which is also why no coerced
  value can be a millimetre read as an inch — a string corner was never scaled.
