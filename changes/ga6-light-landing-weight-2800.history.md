- **A back-solved input, an unusable oracle page, and the loop that closed between them (tier M, 2026-08-29)** —
  Step C10 recorded that Appendix A's wheel-load table was OCR-garbled and that
  the GA6 light-landing weight "was back-solved from the legible side-load cell
  (½·1.33·W = 1864)". Two consequences followed from that one move and neither
  was visible from inside the codebase: the fixture carried **2803 lb** where
  every other statement of the same quantity said 2800 (WTENV's
  forward-regardless weight, the `CG3` flight point at the identical station and
  waterline, and `cg_cases.seed_landing_cases`, which takes this case's weight
  straight from the envelope anchor), and the braked-roll family was left with
  **no printed-value oracle at all** — an input derived from an output cannot
  also test it. The family ran on internal identities, which is what let #135's
  `WR` defect sit undetected in shipped ULTIMATE loads.
  Reading the rendered p231 broke the circle: the cell prints **1862**, not
  1864, and `1862/0.665 = 2800.0` exactly. The fixture is corrected to 2800,
  which closes the +0.107 % residual #135 deliberately left rather than absorbed
  into a widened tolerance, and the ground `fwd light` case becomes identical to
  the flight `CG3` point it was always the same corner of. Cases 15, 18, 23, 24
  and 31–33 move 0.107 %; no other fixture is affected. The page then yields
  what it had been assumed not to: `test_landload_braked_roll_printed_cells`
  locks cases 16/17 and 18 on p231 and case 18's airplane-datum pair on p232 at
  ±0.1 %, the 23.493 family's first printed-value oracle, and the cells are
  recorded in `theory_sources.md` as **transcriptions from the rendered page,
  not OCR extractions**, since that distinction is exactly what failed here.
  Two structural consequences beyond the number. The drift that hid for a year
  was that `seed_landing_cases` is only ever *offered* to the GUI and never
  checked against what a project carries, so
  `test_a_seeded_fwd_light_case_weighs_what_the_seed_gives_it` now makes the
  seed a checked invariant on every fixture, exempting a case that states its
  own D-25 loading (`baron_58`'s fwd light closes at 4,440 lb against a 4,200 lb
  anchor — a different quantity, correctly not a drift). And the p232 pair
  settles design note 38's open GF-1 question against the correction: the shipped
  `PHIM = atan(0.8) + GRA2` gives Fz 1733.0 / Fx 1637.9 and GF-1's
  `atan(0.8) − GRA2` gives 1978.4 / 1331.2, a 14 %/19 % separation. Three
  sessions of frame reasoning — the DP-wheelbase argument and the axle-vs-patch
  self-consistency argument both favoured GF-1 — are overruled by one printed
  number, which is the benchmark-first rule working as intended and the reason
  no GF-1 code ever reached `main`.
