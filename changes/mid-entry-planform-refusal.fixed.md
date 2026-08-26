- **A half-entered planform is refused by name instead of crashing the page (#71, PB-21, tier S, 2026-08-25).**
  The oracle GUI's curve editor persists a one-point leading or trailing edge
  after the first complete row, and Wing Loads answered that with a raw
  `IndexError` traceback rather than a note. Every strip sweep now asks one
  precondition — `derived_geometry.require_integrable_planform` (two or more
  points per edge, butt lines ordered inboard → outboard, two or more
  integration elements) and `require_positive_planform_area` for what can only
  be known after the sweep — so the refusal names the surface and what is wrong
  with it, and the page shows it as "cannot run yet". It stays a plain
  `ValueError`, not a `MissingInputError`: a mid-entry planform is
  present-but-invalid input, so a run-all or an sbeam export refuses it rather
  than skipping the wing and shipping a deck without one.

- **Four more sites of the same class, found by sweeping for it (#71, tier S, 2026-08-25).**
  The finding named one function. Five walk the edge polylines strip by strip,
  and only two carried the check: `tail_geometry`'s two polyline integrals
  reached `[0]` on an empty tail edge and came back through SELECT and the
  balance as an `IndexError`, the Schrenk distribution had the point check but
  still divided by an area of zero, and `wing_inertia` had nothing. Coincident
  edges, a zero span, a repeated butt line and a trailing edge entered ahead of
  the leading edge are all ordinary mid-entry states and all produced a bare
  `float division by zero`, which `_NOT_READY` deliberately does not catch. The
  gear-placement consistency check, which renders on every page, now skips a
  planform still being typed rather than interpolating it.

- **The broad `except` around the wing-area resolver is narrowed (#70 follow-up, tier S, 2026-08-25).**
  `validation` and the field registry caught `(ValueError, ZeroDivisionError,
  StopIteration)` around `planform_area_sqft` because the calc underneath could
  still divide by zero. It cannot now, so both catch the declared `ValueError`.
