- **A blank LIMNZ no longer resolves to zero through a half-entered planform
  (#122, tier M, 2026-08-29).** `engine.effective_engine`'s note 36 OV-7 derive
  — blank `limit_load_factor` → `design_speed_values(project).n`, added by
  C210-41 because a 0 LIMNZ silently zeroes every mount case — reads the wing
  planform through STRSPEED's area resolver, but wrapped the whole chain in
  `contextlib.suppress(ValueError)` under a comment about incomplete *speeds*.
  The suppress was wide enough to swallow the planform's own refusal, so a wing
  caught mid-entry (truncated polyline, swapped LE/TE, zero span — the #71
  mutation set) handed the mount loads LIMNZ = 0 with no typed value on the page
  to show what had gone wrong: C210-41's failure mode restored, silently, by the
  guard meant to prevent a traceback. The derive now asks the precondition's
  owner (`derived_geometry.planform_area_sqft`) before the suppress, so an
  unresolvable planform propagates as the named refusal every other geometry
  consumer states, and the suppress covers only what its comment claims. A
  project with no wing surface is unaffected — that is `None`, not a refusal,
  and STRSPEED's typed `wing_area_sqft` fallback stays live.
