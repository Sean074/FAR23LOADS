- **Entered tail planforms conserve SELECT's total and sit on the scalar 25 %-MAC station (issue #9, tier M, 2026-08-17).**
  Found by the first entered fixture polylines: `tail_span.distribute` normalised
  each strip by the *scalar* area, so a polyline inside the validator's ±1 % put
  that same fraction onto the deck total (atr42 h-tail +0.025 %, cessna fin
  +0.045 % against SELECT). Strips are now normalised by the quadrature's own
  area (`TailPlanform.strip_area`), so `sum(frac) == 1` on every planform and
  the derived rectangle is bit-identical. Same find, second leg (practice 4):
  `validate_tail_planform` gains a third check — the polyline's own quarter-MAC
  station must land on `xt25`/`xv25` within 1 % of the MAC — because area and
  span can agree while the strips sit fore or aft of the station the balance
  states the load at. Guards: `tests/test_tail_geometry.py`
  (`…is_tapered_and_sits_on_its_scalar_station`, `…off_its_scalar_station_is_refused`)
  and the fin-load/`n_y` identity in `test_balance.py`'s lateral pins.
