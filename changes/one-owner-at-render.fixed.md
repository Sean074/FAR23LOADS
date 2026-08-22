- **A copied input now says whose copy it is, and a copy the analysis ignores no
  longer pretends to be an input (#36, review 2026-08-20 CR-A-2 `[MAJOR]`, tier M,
  2026-08-21).** The field registry has always recorded which field *owns* each
  shared quantity; nothing in the oracle GUI's renderer read it, so every holder
  rendered as an ordinary editable widget and a user could enter one wing
  reference area on Geometry and a different one on Structural Speeds with
  nothing saying they disagreed. `render_scalar` now reads the registry, and the
  marking follows a new structural flag, `FieldEntry.governs` — *does the calc
  honour this copy?* — because the two answers must render differently:
  a **display-only** copy (`governs=False`) renders **disabled**, showing the
  value that actually governs, and an **override** (`governs=True`) stays
  editable, captioned with its owner and the owner's current value, and warns
  when the two disagree. It warns rather than corrects: disagreeing is what an
  override is for, and substituting the owner's value would change results.
  The case that named the rule is `speeds.wing_area_sqft`, the "dead input" from
  the #29 review — STRSPEED integrates the wing planform and reaches this field
  only when the geometry carries no wing surface, which no GUI-built project
  lacks, so a value typed there was silently discarded (an 18 % divergence
  measured on `atr42`). It is the one display-only copy; the other four are
  overrides the calc reads verbatim, so disabling them would have removed a
  capability rather than fixed a defect. Rendering a display-only copy still
  writes nothing back, so visiting a page cannot dirty a project (OG-F). Guards:
  `tests/test_oracle_gui.py` renders every copy's page and fails on one that does
  not name its owner, on a display-only one that is still editable, on a silent
  disagreement, and on the marking becoming vacuous if the last copy ever goes;
  `tests/test_field_registry.py` fails if an owner row claims `governs`.
