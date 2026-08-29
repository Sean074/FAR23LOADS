- **The light landing loading no longer takes the gross-weight ratio (tier M, 2026-08-29).**
  `LANDLOAD.BAS` applies `WR = GW/MLW` to the two *max landing* loadings only — the
  third (light) loading is already below the landing weight and lines 860/870/900
  carry it bare. sloads applied `WR` to all three in the braked-roll loop, so
  **cases 15 and 18 were overstated by the ratio** (up to 6.1 % on the shipped
  fixtures; on the Appendix A GA6, VMP 1962.1 instead of 1864.0). Found reading
  Appendix A p231 against the module: the printed case-18 pair is VMP **1862** /
  DMP **1490**, and the p232 airplane-datum pair Fz **1733** / Fx **1638**. The
  same rule was already correct at the three other sites it appears (`WL(23)`,
  `WL(24)` and the 23.499 supplementary-nose branch), so the guard
  `test_the_light_loading_never_takes_the_gross_weight_ratio` pins all four at
  once rather than the one that was wrong. Affects every example with a distinct
  light loading and `WR > 1` (`ga6_normal`, `atr42_100`, `dhc8_dash8`,
  `baron_58`, `concept_regional_jet`); `cessna_210` has `WR = 1` and is unmoved.
  Deliverable ULTIMATE loads change, so the frozen Imperial digest baseline is
  regenerated with it.
