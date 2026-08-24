- **The flap slipstream amplification is delivered, not just printed — the
  exported flap case was understated by the whole factor (C210-47, issue #85,
  tier M, 2026-08-24).** FAR 23.457(b)'s slipstream factor was computed,
  published as a `LoadValue` and then dropped: `build_flap` shipped
  `max(critical, gust-combined)` uniformly as the one exported flap case, so the
  C210 deck carried 972.8 lbs-ULT where the 23.345(d)/23.457(b) design load
  inside the band is 1,156.6 — **19 % low on shipped content**. FLAPLOAD.BAS
  printing the factor and leaving the application to the designer is defensible
  for a printed report; a solver deck has no such excuse. `build_flap` now emits
  the slipstream as a **second case** (`W-61`) beside the gust-combined one
  (`W-60`), with its own `ConditionResult` so the report prints the governing
  number, and the two are **enveloped, never multiplied** — a 25 fps head-on
  gust and full takeoff power at VF are independent worst cases (owner ruling).
  The delivered load is `factor × the VF-governed condition`: the factor is
  `(Vss/VF)²`, a ratio of dynamic pressures *at VF*, so scaling a load computed
  at VSF by it would multiply a `q` it has no relation to (on the manual's own
  airplane the critical condition *is* 2G at VF, so this is `factor × critical`
  there). The factor applies over the **whole** flap — `ControlSurfaceLoadResult`
  carries chord fractions and no span, which is why the deck emits no `GRID` —
  so the whole-surface application is conservative and is stated on the case
  rather than implied; a per-strip banded envelope needs a spanwise axis on the
  result type and is left as the L-tier schema change it is. No printed oracle
  exists for the applied load, so the gate is a stated closure (rule 2):
  `factor × max(LF 2G-at-VF, LF gust-at-VF)` = 1.407 × 629 = 885 lb on the
  Appendix A airplane, not the two factors stacked, and an engine-less project
  exports byte-identically to before. The frozen Imperial digests were
  regenerated for the intended flap-channel change on the propeller examples.
- **The main GUI's whole slipstream block had never rendered (found closing
  #85, folded in per rule 4).** `app/views/flap_loads.py` tested
  `if "Slipstream factor" in vals:` against a dict keyed by `LoadValue.key`, so
  the condition was always False and the 23.457(b) block was dead from the day
  it was written — the smoke tests passed over it in silence because a block
  that never renders raises nothing. The page now reads the key, flattens `vals`
  across every reported condition (the slipstream is its own condition since
  #85), and shows the flap load in the slipstream beside the factor and band.
  Guards: the page's rendered elements are asserted to carry the slipstream
  block on a propeller project (read the artifact, not the source — the G7
  lesson), and, since this was the only such line in `app/views`, a rule-3 drift
  guard states as an absolute that no view may test a display label against a
  key-dict (`tests/test_views_smoke.py`).
