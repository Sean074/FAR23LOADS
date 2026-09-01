## Step — WTENV's aft edge: the half of the envelope we never ported (design note 45, tier L, 2026-08-31, issue #157)

**Objective.** Complete the WTENV port. `WTENV.BAS` (Appendix C p382–383) sorts
the discretionary items ascending by fuselage station, sweeps them cumulatively
from the minimum flight weight (line 330, *"NOW PRINTING FORWARD EDGE OF
ENVELOPE"*), re-sorts descending and calls the identical subroutine again (line
500, *"NOW PRINTING AFT EDGE OF ENVELOPE"*), printing `XBAR`, `ZBAR` and the
cumulative weight per vertex. The replication emitted the ascending sweep alone,
in `(weight, station)` pairs — so three of the original's outputs were missing:
the aft edge, the per-vertex waterline, and the name of the item added. Found by
reading frozen code while specifying §2.2 of the oracle technical report, where
the p140 figure is to be drawn.

**Deliverables.** `_forward_sequence` becomes `_sweep(start, items, *, aft)` —
one walk, two calls, mirroring the `.BAS`'s one subroutine and two `GOSUB`s — and
returns `EnvelopeVertex(weight, station, waterline)`. New public
`loading_envelope(project, aft=...)`; `loading_envelope_points` remains as its
station-only projection, so the Weight/CG Envelope page and the ballast calc are
untouched. `_weight_and_cg` adds the waterline the sweep needs while
`_weight_and_station` stays exactly as its three existing callers use it. A fifth
`ConditionResult`, *"Aft loading envelope (weight, station, waterline)"*, is
**appended** after the four that existed, its keys `aft_`-prefixed so the edges
stay distinguishable wherever conditions are flattened. WTENV's summary shape
(`report.render.weight_station_rows`) learns a third column: `_waterline` joins
the pair-folding suffixes, and routing moves from `LoadValue.quantity` to the key,
because a waterline and a station are both lengths with the same empty dimension
hint. The frozen-set manifest is re-hashed with its authority named beside it.

**Test.** `test_both_edges_reproduce_appendix_a_p139` — both printed blocks, all
16 rows, all three printed columns, ±0.1 %; worst disagreement 0.01 in on a
waterline, the page's own last digit. It runs on a **test-local transcription of
the Appendix A p138 data base, not `ga6_normal`**. Four further gates:
`test_the_two_edges_close_the_envelope` (both sweeps share their first and last
vertex, which is what makes them one envelope);
`test_the_aft_edge_adds_a_condition_and_changes_no_existing_one` (G-WE-2, the
additive claim);`test_the_forward_edge_has_exactly_one_owner` across four
fixtures; `test_an_edge_is_invariant_to_the_entry_order_of_equal_station_items`.
Every pre-existing test in `test_weight_envelope.py` passes **unedited**, which is
where the numeric invariance actually lives.

**Key decisions.** *The fixture is not the manual's fixture, and that is
load-bearing.* The manual runs WTENV twice on two different data bases:
Chapter 3's, with no baggage row and a maximum loading of 3322 @ 84.56, and
Appendix A's, which adds `BAGGAGE 120 @ 180` and reaches 3442 @ 87.89.
`ga6_normal` is the Chapter 3 one, and the standing ballast oracle (78 / 418 /
158 lb) is computed *from* its no-baggage maximum — so "completing" the fixture to
match Appendix A, the obvious move, would have broken an existing lock to gain a
new one. The only printed edge tables are p139's, on the other data base, hence a
transcription in the test rather than a shipped example. *The manual's printed tie
order is not an oracle.* Simulating its own sort on its own data base reproduces
the forward edge's labels exactly and fails on the aft edge: lines 220/420 compare
strictly, so equal elements swap, and the sort runs over the whole dimensioned
array whose blank records migrate through it — the printed order is a function of
the user's answer to *"maximum number of weight items"*, not of the airplane. It
cannot move a number, because tied items share a station. Ties are therefore
broken stably and the gate asserts invariance to their entry order. *The item name
was dropped, not deferred by choice.* `LoadValue`'s value is a float and its
`label` is cosmetic with M4-9 forbidding downstream matching on it;
`ConditionResult.title` is per-group; `CaseRef` is the delivered-load-case identity
with a fixed component taxonomy. Emitting a per-row string needs a
`models/results.py` contract change, which is its own note — so the note's WE-3 was
amended mid-implementation and the vertex→item mapping is left recoverable by the
reader instead of restated. *And the freeze was honoured by proof rather than by
distance:* this is milestone 0.8.2's first OR-15 row 1 admission, and what makes it
safe is not that the diff is small but that the four pre-existing `ConditionResult`s
are asserted unchanged and every prior oracle passes unedited.
