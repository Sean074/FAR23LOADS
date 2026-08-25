- **The load boundary types its own numbers (issue #76, C210-7 residual, tier M,
  2026-08-24)** — The reported defect was narrow: a project saved while the
  oracle GUI's geometry grid was handing text back kept its wing corners as
  strings, and reloading it re-crashed WINGGEOM with `TypeError: unsupported
  operand type(s) for -: 'str' and 'str'`. The review's mitigation — the repaired
  grid fixes the corners on the next Geometry render — turned out to hold only in
  the GUI the defect was found in: in the main GUI the same strings kill
  `to_display` on the Configuration & Layout page, which is the page that would
  have done the repairing, so the file was unopenable there in a way nothing had
  noticed. That made the loader the only boundary worth fixing, since the module,
  both front-ends and the CLI all sit behind it. Reading the model's own
  annotations for the class rather than the field then showed how thin the
  existing coverage was: of eighteen numeric containers in the schema, exactly one
  — `FlightLoadsInput.altitudes_ft` — coerced its members, and the rest, including
  three `hinges_span_in` lists that feed the sbeam control-surface export and both
  engine CG vectors, took whatever JSON held. So the rule is now stated once and
  derived: `io._numeric_shape` reads the shape off the dataclass hint, `_filtered`
  applies it to every splat, and the three readers that name their fields
  explicitly call the same coercer instead of keeping a second copy that could
  drift. Text that parses is repaired out loud through the load path's existing
  warning channel (one message per field, not per member — a twenty-point polyline
  is one event), which keeps a crash-damaged file openable so the grid can finish
  the repair; text that does not parse raises `ValueError` naming the field and the
  member, which the GUI already renders as `st.error` rather than a traceback.
  Scalars were left out deliberately: the class that produces this damage is the
  grid-writable container, and a blanket numeric coercion would have to reason
  about `Optional`, enums and bools for no observed defect. The guard is the whole
  fixture rather than the one field — the GA-6 project reloaded with every list
  member written as text must return bit-identical values from seventeen modules.
