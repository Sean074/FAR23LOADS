- **A printed load no longer hangs on the last ulp (#147, tier M, 2026-08-29).**
  `report/render.format_value` chose between two far-apart spellings — an
  integral value in full, everything else at four significant figures — on the
  raw double, so the printed cell was a discontinuous function of the last bit:
  `-687258.0` printed `-687258` while `-687257.9999999999`, the same load
  rotated through one more cosine, printed `-6.873e+05`. Both spellings shipped
  in one landing case of `concept_regional_jet`, and the wing area printed
  `71676` in one place and `7.168e+04` in another. Which spelling a cell took
  moved with the libm build — macOS and glibc disagree in the last ulp of
  `sin`/`cos` — so the frozen Imperial digest passed on the developer's Mac and
  failed on the Linux CI leg, red since 7cdc609 (#134) put the landing
  rotations in. The formatter now quantizes to twelve significant figures
  before choosing, four orders above a double's ulp and far below anything a
  load means. **The Imperial baseline was regenerated deliberately:** 67 lines
  across 22 channels of four examples, every one of them a near-integer joining
  its exact twin (`7.168e+04` → `71676`) or a four-significant-figure boundary
  settling on one side (`NV 1.668` → `1.669`). No calc changed; the Appendix A
  oracles and the twin closure suites are unmoved.
