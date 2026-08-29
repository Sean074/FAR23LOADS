- **LANDLOAD's light loading took the gross-weight ratio it is not given (tier M, 2026-08-29)** —
  Reviewing the GA6 braked-roll nose-clear family (cases 16–18) against Appendix A
  turned up a defect the closure tests could not see. `LANDLOAD.BAS` states the
  per-case weight table three times (lines 820–900) and the light loading is the
  exception throughout: `WL(15) = WL(18) = WL(23) = WL(24) = WCG(3)`, with no
  `WR = GW/MLW`, because that loading already sits below the landing weight. The
  port's braked-roll loop wrote `wcg[(m - 13) % 3] * wr` for all three loadings,
  overstating cases 15 and 18 by the ratio — 5.0 % on the GA6, 6.1 % on the
  regional-jet fixture. The suite stayed green because the braked-roll family
  carried **no printed-value oracle**: `theory_sources.md` records p231–233 as
  OCR-garbled in the bundled PDF, so the family was held by internal identities
  (`DMP = 0.8·VMP`, `VNP = 1.33W − 2·VMP`), every one of which the defect
  satisfies. It surfaced only when the page was read directly — printed VMP 1862
  / DMP 1490 against 1962 / 1570 as shipped. Fixed by carrying the BASIC's
  exception, which the module already spelled out correctly at its three other
  sites; the guard therefore pins the rule at all four (and at the two
  max-landing loadings that *do* take `WR`) rather than regression-testing the
  single line that was wrong, per the generalize-on-first-find rule. A residual
  +0.107 % remains and is **not** absorbed: the fixture's light-landing weight,
  2803 lb, was itself back-solved from this same printed cell when it was read as
  1864, and `1862/0.665 = 2800.0` — the fwd-regardless weight p230 prints. That
  correction is filed separately because it moves a shared input with a wider
  blast radius, so case 18 is guarded here by the weight-independent identity
  `VMP(18) = VMP(23) = VMP(24)` instead of a ±0.1 % lock. Two findings came out
  of the same reading and are filed rather than fixed here: the braked-roll and
  supplementary-nose families still have no printed-value oracle on any fixture,
  and the p232 datum pair (Fz 1733 / Fx 1638) reproduces under the shipped
  `PHIM = atan(0.8) + GRA2`, which pins the fidelity of the port and supplies
  design note 38's GF-1 with transcribed deviated-from cells — not, as first
  read, evidence about the rotation's sign, since `LANDLOAD.BAS` derives that
  pair from the printed angle on the same line (withdrawn the same day, note 38
  §1.12).
