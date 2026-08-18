- **Seven dimensional project fields displayed unconverted in the SI view**
  (units-table completeness, tier S, 2026-08-18). `units._PROJECT_FIELD_KIND`
  classifies a project-JSON leaf by field *name*, and seven fields it did not
  classify passed through the Project JSON Editor's SI view unconverted and
  unlabelled beside neighbours that converted: `thrust_lb` (lbf → N — the
  force/weight split exists precisely to keep it off the ~9.8×-different mass
  factor), `max_takeoff_weight_lb` (lb → kg) and the five lengths
  `actuator_span_in`, `hinges_span_in`, `inboard_y_in`, `outboard_y_in` and
  `sob_y_in` (in → mm). Display only — an unclassified field is unconverted in
  **both** directions, so the round trip was always lossless and no project's
  numbers ever drifted. One rule replaced the `engine_cg`/`prop_cg` special
  case: **a classified key converts whether its value is a scalar or a list of
  numbers**, which is what `hinges_span_in` (a list of hinge stations) needed
  and what the two CG vectors now ride on as ordinary rows. **The guard is the
  point** (`CLAUDE.md` rule 3): new
  `tests/test_project_units.py::test_every_dimensional_project_field_is_classified`
  walks the **type graph reachable from `Project`** rather than the fixtures —
  a round-trip test cannot see an unconverted field and no fixture entered a
  thrust, which is exactly why this class went unnoticed — and fails naming the
  field and its owning dataclass unless it is classified or listed in the new
  `units._NOT_DIMENSIONAL` with its reason (`override_max_continuous_hp` is a
  bool, not a horsepower). `CONVENTIONS.md` §7 gains the owner row.
