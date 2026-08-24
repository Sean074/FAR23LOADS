**Flap slipstream applied to the deliverable (issue #85, C210-47/C210-40 family,
tier M, 2026-08-24).** The C210 build review reached the flap page with an engine
record present for the first time in the project's history — no prior fixture
carried both a flap slice and an engine — and the FAR 23.457(b) block finally
computed. It computed, printed, and was then discarded: `build_flap` exported
`max(critical, gust-combined)` as the single flap case, so the deck shipped 972.8
lbs-ULT against a slipstream design load of 1,156.6, understating shipped content
by 19 %. The fix delivers the slipstream as a second case beside the
gust-combined one rather than folding it in, on two owner rulings taken in chat
before code (rule 1): the two are **independent** worst cases and are enveloped,
never stacked; and the factored load is stated over the whole flap because
`ControlSurfaceLoadResult` has no spanwise dimension — the review's preferred
per-strip banded envelope would be an L-tier schema change, and inventing the
flap's span extent from a project that leaves `inboard_y_in`/`outboard_y_in`
unset would violate T-17. One implementation rule was settled on the physics
rather than by owner call: the factor is `(Vss/VF)²`, so it scales the VF-governed
condition, not the stall-speed ones — a distinction with no numeric effect on the
manual's airplane (whose critical condition is 2G at VF) and a real one on any
airplane where a stall-speed condition governs. Closing the item exposed a second
defect in the same file: the main GUI's slipstream block tested a display label
against a key-keyed dict and so had never rendered at all, which is why C210-47
was verified through the oracle GUI's report path. It was folded in under rule 4,
and since a sweep found it to be the only instance in `app/views`, its drift
guard is stated as an absolute. No printed oracle exists for an applied
slipstream load — Appendix A prints the factor and the gust-combined 819 lb and
nothing built from the two together — so the definition of done is the stated
closure gate rule 2 requires in place of one: `factor × max(LF 2G-at-VF, LF
gust-at-VF)`, not the factors stacked, with an engine-less project exporting
byte-identically to before. The frozen Imperial digests moved on the flap
channels of the propeller examples, which is the intended change announcing
itself, and were regenerated.
