- **A polyline typed from blank in the oracle GUI no longer crashes WINGGEOM (C210-7, Cessna 210 build review 2026-08-23, tier S, 2026-08-23).**
  The leading-/trailing-edge grid of a blank surface is an empty frame, and an empty
  frame's columns are object-typed, which the grid renders as *text* — so every corner
  typed from blank came back as strings, was stored as string tuples and the Geometry
  page died on `ytip - yroot` (`TypeError: unsupported operand type(s) for -: 'str' and
  'str'`). The curve frame is now built numeric (`dtype=float`) even with no rows, and a
  cell that still arrives as text is parsed on the way in, never stored
  (`oracle_app/form.py` `render_curve` / `_numeric`). Found by the owner typing the 210
  wing; the beta review never saw it because its replays handed the renderer floats.
  Guard: `tests/test_dirty_flag.py::test_a_curve_typed_from_blank_is_numeric`.
