- **The word travels with the value: frame and application point stated in-band
  in the delivered CSV (tier M, schema v59, 2026-08-29)** — the 2026-08-29
  independent review of `dev/v0.8.1` raised that the corrected landing output
  #133/#134/#139 shipped is not self-describing: the CSV names neither the frame
  its numbers are in nor the point each force acts at. Both facts already existed
  on the calc side — `LoadValue.frame` since schema v58 (note 38 GF-6/GF-7), the
  point in `landing.case_note()` and both GUI captions — and this one channel
  dropped them, because `results_to_rows` reads neither the note nor the frame
  for output. The point therefore reached a consumer as coordinates alone, and
  the axle and the ground contact point are a rolling radius apart, so guessing
  wrong is a moment arm rather than a caption. Two channels were on the table
  (the issue left it open): the project-scoped methods preamble, which prints on
  every module's CSV and could not name a *per-case* point when cases 1–33 split
  between the two, and per-row columns. The columns won, and the point took the
  same posture the frame already had rather than a second one: `LoadValue.point`,
  a vocabulary (`gear_loads.POINTS`) and not free text, stamped per leg from
  `application_point_of` — the single owner design note 39 AP-1 already
  established — and read once, at the render boundary, into an `Applied at`
  column beside a new `Frame` column. Deriving it there instead, by parsing the
  note or re-deriving from the case number, was rejected: it re-establishes
  exactly the label/note string-matching M4-9 removed, where a reworded sentence
  silently blanks a column. The reference-node rows deliberately name no point —
  the node is where the reaction is transferred *to*, and stamping it would say
  one force is applied in two places at once. No load moved: five landing CSV
  digests changed, every other frozen Imperial channel is byte-identical, and the
  Appendix A oracles and twin closures are untouched. Guards:
  `test_the_delivered_csv_states_its_frame_and_its_application_point` (every
  delivered force row on every fixture names both),
  `test_the_csv_point_is_appendix_as_printed_column_case_by_case` (the column is
  the manual's, so a constant word would read correct on half the matrix),
  `test_the_reference_node_names_no_application_point`,
  `test_every_landing_value_names_a_known_point_or_none` and
  `test_a_module_that_names_neither_gets_neither_column` — the last pinning that
  #141 states the landing output and does not widen every CSV. **The schema hops
  v58 → v59**, an identity (`_hop_58`; `""` means exactly what v58 meant) for the
  reason v58 itself hopped: `LoadValue` is persisted inside
  `critical.conditions[].loads`, so a display-neutral addition is still a shape
  change. It stays tier M under the 2026-08-29 re-cut's second ruling — no load,
  no quantity, no physics and no theory citation to make — with the hop named
  here so the schema move is on the record rather than inferred from a diff
  (issue #141).
