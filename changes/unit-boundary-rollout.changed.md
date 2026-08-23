- **Unit-boundary rollout completed: `unit_number_input` everywhere**
  (CR-D-2, issue #44, tier M, 2026-08-22, one pass with #51): the seven
  remaining hand-paired views (`structural_speeds`, `weight_mass`,
  `aileron_loads`, `flap_loads`, `landing_loads`, `wing_loads`,
  `flight_envelope`'s SELECT inputs) moved their scalar `number_input`s onto
  the boundary helper — the `to_display`-seed / `to_imperial_scalar`-on-Apply
  idiom is gone from `app/views/`; the `data_editor` grids remain the one
  hand-converted surface. A no-op-Apply-in-SI bit-identity test per converted
  view (`tests/test_view_unit_roundtrip.py`) guards the untouched-field
  return path, and `GUI_design.md` §7/§11's rollout claim is now true.
