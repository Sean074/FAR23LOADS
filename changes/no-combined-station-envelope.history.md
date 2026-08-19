- **No combined flight + ground station envelope (D-28, issue #11 closed as decided, tier M, 2026-08-18)** —
  step 10's decision G-9 kept ground and flight as separate governing families
  but filed one follow-on: a two-sided per-station envelope over both, each
  extreme labelled with its case id, on the argument that a consumer sizing a
  fuselage frame wants the worst of both and that labelling preserves the case
  identity a cross-family `max()` destroys. Closed here without building it, on
  a reason G-9 did not have. D-24 had already made pressurization a permanent
  exclusion and recorded that the "for pressurized airplanes, ground cases
  cannot be down-selected against flight" rule departed with it, to be re-decided
  on its own merits; this is that decision. On the fuselage the two families are
  assessed with different internal-pressure companion cases, so their station
  extremes are not comparable quantities — they belong to different total load
  states — and a tool that computes no pressure case cannot assemble the correct
  combined state in the first place. The labelling half would not have rescued
  it: identity survives the aggregation, but the aggregated number is still one
  no design condition produces. Wing and empennage carry no such companion, and
  the deliverable stays per family uniformly rather than becoming a
  per-component rule. The change is therefore one standing-limitation string —
  `ground-flight-separate-families` now states the pressure-companion reason and
  points at the `pressurization` exclusion, and drops nothing except G-9's
  safety-factor argument, which G-10 had already retracted (both families are
  limit × 1.5) — plus the decision record and the backlog row. What the closure
  did surface is that "delivered separately" is only honest if both halves are
  usable: flight has a station-by-station distribution and ground has none,
  `body_loads` and `net_loads` being flight-only, so the ground family reaches a
  frame-sizer as reactions and assembled decks alone. That gap is filed as #31
  in band B, scoped as a per-family view that D-28 does not re-open. No calc, no
  oracle and no shipped load number moves.
