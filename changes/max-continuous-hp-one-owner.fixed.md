- **The max-continuous-HP precedence is written once and read everywhere
  (#124, tier S, 2026-08-28; production-release review §3.1).** Step M2-6's rule
  — the engine-list total unless `override_max_continuous_hp` is set, the stored
  total as the fallback when no engine carries a rating — lived in
  [`weight_estimate.resolve_max_continuous_hp`](sloads/modules/weight_estimate.py)
  and again inline in [`app/views/weight_mass.py`](app/views/weight_mass.py),
  over a locally computed `sum(...)` where the owner used `math.fsum(...)`: two
  copies of one rule, agreeing on the day they were written, which is the drift
  practice 3 forbids. The view could not simply call the owner — it takes a
  `Project` and refuses one without a `weight.estimation`, while the page holds
  the form's values before Apply writes them — so the precedence now lives in a
  new input-level `resolve_max_continuous_hp_for(estimation, engines)`, with the
  project-level function a thin wrapper that locates the slice and applies it,
  and `engine_list_max_continuous_hp(engines)` owning the sum the page shows
  beside the override switch. The view reads both; the inline copy is deleted.
  No behaviour change: the two copies agreed. The structural half is two guards
  in `tests/test_derived_geometry.py` — the entry points are pinned to one
  answer across the override/fallback/empty-list cases, and a headless render of
  the Weight & Mass page with an engine list deliberately disagreeing with the
  stored total checks its powerplant weight against the owner's, in both
  override states, with the two required to differ so neither check can pass
  vacuously. Verified: reinstating a drifted inline copy fails the page guard.
