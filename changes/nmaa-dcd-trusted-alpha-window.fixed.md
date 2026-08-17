- **A forward non-wing "drag" is no longer applied where the polar is not
  trusted (backlog Pri 2, fixture aero-data defect, tier M, 2026-08-17).**
  Design note 20 D-4 revised (§8.2): the airplane-less-tail polar less the wing
  strips (`balance.body_axial_set`) is a physical `body-axial` load only where
  both drag models are trusted, and the trim `α` is now tested against a
  **one-sided** window, the single owner `constants.POLAR_TRUSTED_ALPHA_DEG =
  (−10°, +15°)` (`balance.polar_alpha_trusted`, read by the code and by the G10
  gate). Outside it a forward difference is **not applied** — no card,
  `body_axial = 0`, new result flag `BalancedCaseResult.body_axial_clamped`, the
  raw value and the window in the case note — while `ΔC_D` is still reported
  unclamped, so the diagnostic that found the defect keeps its signal. Inside
  the window a forward value is a fixture-data defect and fails G10; the three
  excused `NMAA` entries the test carried are gone. What this removes from the
  decks: **1,004 / 1,097 / 1,445 lb forward** on `atr42_100` / `dhc8_dash8` /
  `concept_heavy` `NMAA` (α = −12.9…−14.3°, 3–8 % of `W`) and the regional
  jet's four high-`α` cases (1.7–2.6 klb). Stated consequence: on those cases
  and only those, both pre-closure residuals re-open by the un-applied force
  and its couple about the CG (pitch **1.5–2.1 %** of `n·W·MAC` on the three
  `NMAA` points, the wing plane being ~40 in from the CG), reacted by the
  closure and pinned per case in `test_balance.py::_CLAMPED_BODY_AXIAL` under a
  2.5 % hard stop; G1/G5 and G2 read the same flag. `ga6_normal`, `cessna_210`
  and every in-window case are byte-identical. Imperial digest regenerated for
  the four fixtures' `balance` channels and three `lra_model` channels; polars
  not re-derived (out of scope by the row's own words).
