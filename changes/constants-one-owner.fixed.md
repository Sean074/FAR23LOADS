- **Constants and conversion factors — one owner, one value, one rule (issue #26, review 2026-08-17 C-1…C-12, tier M, 2026-08-17).**
  `sloads/constants.py` now owns every shared physical constant and suite-internal
  (Imperial↔Imperial) factor — `DEG_PER_RAD`/`RAD_PER_DEG`, `IN_PER_FT`, `IN2_PER_FT2`,
  `KT_TO_FPS`, `FT_LB_S_PER_HP` (→ `HP_TO_TORQUE`), `dynamic_pressure_psf`/
  `eas_from_dynamic_pressure`, `gust_alleviation_factor` + `GUST_LOAD_FACTOR_DIVISOR`
  (FAR 23.341(c)) — and the ~60 open-coded sites (`57.3`, `114.6`, `_G = 32.2`, six
  `144` aliases, `/12.0`, `550`, `V²/295` ×16, the gust triple ×5) read it; the
  `PI`/`TWO_PI` aliases are gone (`math.pi` everywhere). **Exact by default:** 57.3,
  32.2, 295 and FLTLOADS' private 518.688 °R speed of sound go to their exact owners
  (measured: no printed oracle moves; digest and SELECT/dCD/VA-VF self-pins re-pinned,
  register line in `02_approved_corrections.md`); `KT_TO_FPS_SUITE` survives for `VSF`
  only (ENGLOADS `/101.2` oracle). The `constants.py` (Imperial↔Imperial) vs `units.py`
  (Imperial↔SI only) demarcation is written into `CONVENTIONS.md` §7 with grep drift
  guards both ways (`tests/test_constants.py`); UI help text quotes `√(2(W/S)/(ρ₀·CLmax))`.
