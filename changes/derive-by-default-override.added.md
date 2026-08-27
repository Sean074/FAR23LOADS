- **One derive-by-default override mechanism for the duplicated inputs (design
  note 36 OV-1…OV-12, tier L, 2026-08-27, #97).** Eight C210 findings, one
  contract: a blank collapsed field **falsy-derives** through one named
  resolver per quantity — the `select.py` `value or derive(project)` idiom
  generalized — and a typed value overrides. Blank now derives: WTENV
  `gross_weight` ← the MTOW SSOT (C210-13); `taper_ratio` ← the paired
  planform's tip/centreline chord and `tip_ratio` ← the new
  `SurfaceInput.tip_cap_width_in` / semi-span (C210-31 — a blank taper no
  longer lands on the TAU fit's pointed-wing knot, τ = 0.206209, silently);
  the h-tail's `aspect_ratio_wing` ← the consolidated planform-AR owner
  (`derived_geometry.planform_aspect_ratio`, OV-5 — the unguarded downwash
  divide dies) and `wing_lift_slope_per_rad` ← the cruise set's C1 × 57.3
  (C210-36); SELECT's `full_down_aileron_deg` ← the aileron's own travel
  (C210-38); flap NG ← the envelope's own GUST VF corner factor,
  `flight_envelope.gust_at_vf`, bit-for-bit (C210-39, owner directive); engine
  LIMNZ ← the 23.337 limit, and — with the new `engine_mass_item`/
  `prop_mass_item` row selectors — engine/prop weight and CG ← the named
  weight-database row, every engine consumer reading through one resolver
  (C210-41, owner directive); an empty `aero.surfaces` seeds a schema-default
  row per unpaired symmetric planform (C210-29 seed half — the four fixtures
  with unpaired tails gain their htail/vtail spanwise views; only the
  `airloads` digests moved, every other channel byte-identical). The per-set
  stall CLs register their existing `normalize()` fill-through (C210-15
  ruling). Registry mechanics (OV-9/OV-11): every collapsed path carries
  `derived_from` + a resolver in `EXTERNAL_VALUES`
  (`field_registry.COLLAPSED_OVERRIDES`), the oracle GUI shows the derived
  value beside each field blank or typed and warns on a > 1e-9 typed
  disagreement, and the OV-11 drift guard fails CI on a future duplicated
  input without its link. New warnings `aileron_deflection_mismatch` /
  `engine_mass_row_mismatch`; a mass selector naming no row is refused by
  name. Schema **55 → 56** (additive; identity hop, v55 files load unchanged).
  Gates G-OV-1…G-OV-6 in `tests/test_derive_override.py`; the full Appendix A
  oracle and twin-closure suites pass untouched.
