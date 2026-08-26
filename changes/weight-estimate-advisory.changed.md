- **The weight estimate now says what reads it, and shows the gap** (C210-9, issue #78,
  tier M, 2026-08-26). WTESTIMA sits at the top of the oracle Weight & Mass page above
  WTONECG and WTENV, and nothing on the page said that neither of them reads it: the mass
  properties every downstream program uses come from the itemized data base the user
  enters. The block is captioned with that (`weight_estimate.ADVISORY`) and the estimate's
  empty weight and max take-off weight are shown beside the entered figures with the delta
  (`compare_with_itemized`) — on the Cessna 210 that is +22 % on empty weight, ordinary
  scatter for a GA statistical correlation and, until now, a gap nothing framed. Both
  entered figures come from their owners rather than being re-summed: the empty weight from
  `WeightInput.database_totals`, MTOW from `cg_cases.max_takeoff_weight` (G-14) — **not**
  the database's first element, which holds full fuel and full payload at once and is
  documented as a ceiling. The comparison is shown plainly and never thresholded: there is
  no sourced figure for "too far", and inventing one would put a verdict on the page where
  the finding asked only for the two numbers side by side.
- **`PROGRAM_SPEC` said the estimate feeds the two programs under it** (C210-9, #78,
  tier M, 2026-08-26). The WTESTIMA section stated "feeds WTONECG *and* WTENV — parallel
  siblings off WTESTIMA", which is the suite's data flow (UG Table 2.2) and runs **through
  the weight data base**. Here that base is authored by the user, so the estimate reaches
  it only when the seed button copies it there; absent that click nothing reads the
  estimate at all. Both halves are now stated, so the caption and the spec cannot be read
  against each other.
