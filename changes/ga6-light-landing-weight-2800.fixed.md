- **The GA6 light-landing weight is 2800 lb, and the braked-roll family gets its
  first printed-value oracle (tier M, 2026-08-29).** `ga6_normal`'s `fwd light`
  ground case weighed **2803 lb**, a figure back-solved in Step C10 from an
  Appendix A p231 cell OCR'd as 1864 (`½·1.33·W`). The rendered page prints
  **1862**, and `1862/0.665 = 2800.0` — WTENV's forward-regardless weight, which
  p230 prints and which `cg_cases.seed_landing_cases` already gives this case.
  Corrected, closing the +0.107 % residual left by #135 and making the ground
  `fwd light` case identical to the flight `CG3` point it has always been.
  Cases 15, 18, 23, 24 and 31–33 move by 3 lb (0.107 %); no other fixture is
  touched. With the weight right, `test_landload_braked_roll_printed_cells`
  locks cases 16/17 (VMP 2261 / DMP 1808.8) and case 18 (VMP 1862 / DMP 1490)
  plus its p232 airplane-datum pair (Fz 1733 / Fx 1638) at ±0.1 % — the first
  printed-value oracle the 23.493 family has ever carried, on a page
  `theory_sources.md` had recorded as unusable. New drift guard
  `test_a_seeded_fwd_light_case_weighs_what_the_seed_gives_it` pins every
  fixture's seeded light case to the seed's own anchor (a case stating an
  entered D-25 loading is exempt — `baron_58`'s is one); mutation-verified
  against the 2803 value.
