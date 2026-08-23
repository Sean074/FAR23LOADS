- **Unit-boundary rollout completed (#44, CR-D-2, tier M, 2026-08-22)** — the
  helper existed, the rule existed ("a view that writes `to_imperial_scalar`
  around a `number_input` is a defect"), and seven views still did it by hand,
  each pairing a `to_display` seed with a conversion on Apply and a
  system-suffixed key. Landed as one pass with #51 because the fixes share
  their call sites: `unit_number_input` stamps the project generation for its
  callers, so moving a field onto the boundary was also the cheapest way to
  key it. Speeds and altitudes took the aviation carve-out (`KEAS` /
  `ALTITUDE_FT`), weights, powers, lengths and areas the converted kinds, and
  the Apply handlers dropped their hand conversions — the helper returns
  Imperial, which is the whole point. The `data_editor` grids remain the one
  hand-converted surface. A no-op-Apply-in-SI bit-identity test per converted
  view guards the rounding trap the helper's untouched-field return exists
  for, and `GUI_design.md`'s rollout claim stopped being aspirational.
