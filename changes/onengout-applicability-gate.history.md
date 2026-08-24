- **A 23.367 applicability gate, single-sourced across the module, both GUIs and
  the coverage table (issue #84, C210-43, tier M, 2026-08-24)** — The finding was
  a false verdict: on the C210's centreline single, One Engine Out printed zero
  tail load and zero yaw rate at all three speeds while stating the airplane was
  uncontrollable and likely below VMC. The arithmetic was never wrong. FAR
  23.367's forcing is `thrust · BLENG`, and with the only engine at BL 0 that
  product is identically zero, so the simulation marched sixty seconds of nothing
  and then reported — correctly, on its own terms — that recovery never happened.
  Every intermediate around it verified to the digit, which is precisely why the
  result was believable. What was missing was the question that comes before the
  simulation: does this airplane have the condition at all. The predicate turned
  out to exist already, in `report/coverage.py`, whose 23.367 row has always
  marked the C210 not-applicable — so the tool held the right answer in one place
  and acted on the wrong one in three others. The fix was therefore consolidation
  rather than a new rule: `applicability.engine_failure_not_applicable` states it
  once, and the module's refusal, the oracle GUI's withheld form and the coverage
  row are readers of it. Coverage's old test was also weaker than the physics —
  `len(engines) > 1` calls a twin applicable even when the *failed* engine is the
  centreline one, which is the same zero moment arm — so the shared predicate
  covers a case none of the three had. Coverage keeps its own turbopropeller
  clause layered on top, deliberately: 23.367(a)'s regulatory scope is a
  statement about which airplanes must show the condition, while the module
  models any propeller installation, and `PROPELLER_ONLY_NOTE` already records
  that split. Two boundaries were drawn rather than blurred. An empty engine list
  is *not* an applicability finding — it is an unfinished project, and the
  module's existing "needs Project.engines" refusal says so better — so the
  predicate stays silent there unless the layout settles it. And the GUI table
  keying pages to predicates lives in `sloads`, not the front-end: the oracle
  GUI's own drift guard rejected the first attempt for writing a workflow step
  key as a literal (OG-2/G2), and the key set is guarded against the #82 stale-tag
  defect in the same move.
