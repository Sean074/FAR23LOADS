- **A `null` in a project file is refused by name instead of crashing a widget
  three modules later (#121, tier M, 2026-08-29).** `sloads.io` coerced numeric
  *containers* (#76) and said in its own comment that scalars were out of scope,
  so a scalar `null` went straight through into whatever field it named:
  `"full_down_aileron_deg": null` landed on a field declared `float = 0.0`, the
  file loaded clean, and the main GUI's Flight Envelope page died on
  `float(None)` — a raw `TypeError` out of an `st.number_input`, on a page the
  user had only opened. The loader now refuses a `null` where the field's own
  annotation does not admit one (`io._reject_nulls`, called by `_filtered` and
  at the head of the ten readers that name their fields explicitly), with a
  message naming the record and the key to fix. An `Optional` field keeps its
  `null` — "not entered" (`SurfaceInput.front_spar_pct`) and "not stated"
  (the gear `carrier`) are answers, not accidents. It is refused rather than
  read as the field's default: which of the two the author meant is not
  recoverable from the file, and defaulting is the silent zeroing the LIMNZ
  derive refuses for the same reason (#122) — `fuselage_mass.stations_are_override`
  was doing exactly that, `bool(None)` → `False`, and is now refused with the
  rest. No shipped example changes: every `null` in all seven is on an `Optional`
  field, and no model field defaults to `None` under a non-`Optional`
  annotation, so no project this app writes can trip the new refusal.
