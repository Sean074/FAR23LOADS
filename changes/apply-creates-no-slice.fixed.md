- **An Apply that entered nothing no longer creates a project slice, and a
  rebuild no longer drops what its form does not render (#145, tier M,
  2026-08-29).** #143 settled that an `Optional` record is created and removed by
  a named gesture; that fix was registry-driven and reached `oracle_app/` only.
  In the main GUI, pressing **Apply** on a page nobody had filled in wrote a whole
  zero-valued slice into the project and saved it into the `.project.json` —
  `aileron_loads`, `flap_loads`, `tab_loads`, `select_input`, `fuselage_mass`,
  `landing`, `one_engine_out`, `engine_layout` and the first engine.
  `app_shell/optional_slice.py` now owns the rule for this front-end — an Apply
  may fill a slice in and may empty one out, but it may not create one out of
  nothing — with the whole-GUI journey walk as its drift guard. A form whose
  whole subject *is* one optional block (the fuselage-moment and lateral-body-aero
  Applies) is unaffected: there the button is the named gesture.
  Swept with it (practice 4), three rebuilds that dropped fields their own form
  does not show: the Aero Apply destroyed a populated `lateral_body_aero` block
  outright and re-stamped `cruise.stall_cl` from CLmax (ga6 1.41 → 1.4068,
  atr42_100 1.55 → **2.009**, moving the FLTLOADS balance clamp on an Apply that
  entered nothing), the Payload Cases Apply deleted each case's
  `LoadingDefinition` (three of baron_58's six), and the engine form turned unset
  `Optional` power fields into a stated zero.
