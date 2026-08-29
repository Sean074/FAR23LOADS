- **Appendix A's LANDLOAD output is legible, and every printed cell of it is now
  an oracle (tier M, 2026-08-29).** p231 (ground line), p232 (airplane datum)
  and p233 (limit unbalanced moments) had been recorded since 2026-08-15 as
  OCR-garbled and unusable, so cases 13–33 were held by internal identities and
  a handful of legible cells — the ONENGOUT precedent. The pages are garbled,
  not illegible: rendered at 200 dpi they read cleanly. All three tables are
  transcribed and locked for all 33 cases — reactions, resultants, side loads,
  the NVP/NDP/NS ground-line inertia factors and the pitch/roll/yaw unbalanced
  moments — at the page's own print resolution (±0.5 in an integer column,
  ±0.0005 in a three-decimal one, or ±0.1 %, whichever is looser):
  `test_landload_p231_ground_line_table`, `..._p232_airplane_datum_table`,
  `..._p233_unbalanced_moments_table`, which subsume the two narrower
  spot-check tests. LANDLOAD moves from partially to fully oracle-locked.
  Closes the open sub-finding on design note 38 §1.11 (the braked-roll and
  supplementary-nose families had no printed oracle on any fixture, which is
  why a 40 % move in them left the suite green) and supplies GF-3″ with the
  transcribed deviated-from set it is blocked on. No calc changes: the port
  already reproduced every cell.
