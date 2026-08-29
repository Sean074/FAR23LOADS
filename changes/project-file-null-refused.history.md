- **The crash was in the widget; the defect was in the loader (#121, tier M, 2026-08-29)** —
  The row was filed as a view bug: `select_input.full_down_aileron_deg` defaults
  to `None`, the registry's sentinel-default class (#98/C210-49), and
  `app/views/flight_envelope.py:345` dies on `float(None)`. Two thirds of that
  is wrong, and the correction is what moved the fix. The field is declared
  `float = 0.0` and is not in `field_registry.SENTINEL_DEFAULTS`; the oracle GUI
  cannot produce a `None` for it, because `form._clear_optional` writes `None`
  only where the annotation admits it. The `None` came from the **file**:
  `io._filtered` coerced numeric containers (#76) and declared scalars out of
  scope, so a JSON `null` was passed through to a field that had no such state,
  and every consumer downstream inherited it. The aileron field was the instance
  that surfaced; the class is every non-`Optional` scalar in the schema.
  That relocated the fix from the widget to the boundary, and the owner ruled it
  there. Hardening the ~137 `float(...)` calls in `app/views` would have covered
  one directory, left `oracle_app/`, the CLI and the calc modules holding the
  same `None`, opened the frozen views tree, and rotted at the next widget
  written; the loader is the one place JSON becomes a dataclass, so one guard
  covers all of it and covers a field added later on the day it is added
  (rule 3 + rule 4). `_reject_nulls` reads the nullable set off the annotations
  and is called from `_filtered` plus the ten readers that name their fields
  explicitly, so the rule has one owner and one message rather than a second,
  driftable copy — the same discipline `_coerced` took for #76.
  The refusal is deliberate, not a default. Reading the `null` as the field's
  declared default would leave the file and the loaded project disagreeing with
  nothing said, which is #122's silent zeroing wearing the other face — and one
  reader was already doing it: `fuselage_mass_from_dict` wrote
  `bool(d.get("stations_are_override", False))`, turning a `null` into `False`
  and an override the user had asked for into an override they had not. That
  came out of the guard's own sweep, not out of the report (rule 4).
  The gate is stated over the class in both directions, because closing either
  half alone re-opens the other:
  `test_a_null_is_refused_by_name_or_lands_as_a_meaningful_none` nulls every
  scalar leaf of every shipped example in turn — 3,591 of them — and allows only
  two outcomes, a `ValueError` naming the field or a round-trip that visibly
  changes, so neither a traceback nor a swallowed default can pass. A sweep
  asserting only "nothing escaped" would pass with every null defaulted, which
  is the lesson #122 wrote down. Two guards stand behind the refusal being safe
  to turn on: `test_no_model_field_defaults_to_none_outside_an_optional_annotation`
  fails the build the day a field is added that this app would write as `null`
  and then refuse to read, and `test_an_optional_field_keeps_its_null` pins the
  states where `None` is the answer.
  The row's remaining third — the `float(field)` sweep of `app/views` — is
  discharged as a guard rather than as 137 edits, and it found nothing:
  `test_render_survives_every_optional_blank` blanks every `Optional` scalar on
  the project (65–88 per example, read off the annotations, not off a fixture)
  and renders each view, and all 21 combinations pass. The views already handle
  their genuine blanks; the only `None` they could not survive was the one the
  loader should never have admitted. The half the row leaves open is unchanged —
  rendering the blank *as the oracle GUI does*, an empty widget with the derived
  value stated, is a layout question and stays with #29's freeze lift. The
  `app/views/` freeze was not opened: nothing under it changed.
