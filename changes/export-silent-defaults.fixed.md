- **No silent defaults in the export namespace (CH-2, code-standard review item
  9, tier M, 2026-08-16).** Seven `getattr(obj, name, default)` reads in
  `sloads/export/sbeam_bridge.py` — the shape the error contract forbids
  ("flagged, never silently defaulted") — are gone: `case_ref`, `case`,
  `tip_transfer` and `hand` are declared fields on every exportable result and
  are now read as the typed attributes they are (`_sid`, `subcase_map`,
  `_tail_span_case_block`, the case-index builder, where the assembled case's
  `hand` is **passed** to `add()` and a component-deck item takes the bare id by
  statement, not by a probe that happened to miss); the one lookup by name (the
  `htail`/`vtail` span slice in `_tail_span_results`) is an explicit map that
  refuses an unknown component with a `ValueError` instead of reading as "no
  loads". Frozen Imperial digest unchanged — no default was ever being taken on
  a fixture, which is what makes this hygiene rather than a load change. Guards:
  `tests/test_sbeam_bridge.py::test_the_export_package_takes_no_silent_defaults`
  (AST walk over `sloads/export/`, three-argument `getattr` forbidden; the
  two-argument dynamic-name form stays allowed) and
  `::test_tail_span_export_refuses_an_unknown_component`. `00_program_overview.md`
  §Error handling and `PROGRAM_SPEC.md` §Export bridges state the rule;
  `CONVENTIONS.md` §7 gains the row; CH-2 struck from backlog row 5 (issue #5's
  remaining clauses stay open).
