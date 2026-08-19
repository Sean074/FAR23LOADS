- **No combined flight + ground station envelope — decided against permanently, not deferred**
  (decision **D-28**, issue #11 closed as decided, tier M, 2026-08-18). The
  follow-on decision **G-9** filed in step 10 — two-sided max/min per station
  over both families with each extreme naming its governing case — will not be
  built. On the **fuselage** the two families are assessed with *different
  internal-pressure companion cases*, so a station extreme from one and a
  station extreme from the other belong to different total load states: a
  pointwise `max()` over both would present a number that no single design
  condition produces. sloads excludes pressurization permanently (**D-24**), so
  it cannot form the correct combined state from its own outputs at all — the
  combination is unsupportable here, not merely less useful. This reinstates, on
  its own merits, the "for pressurized airplanes ground cases cannot be
  down-selected against flight" rule that D-24 recorded as leaving with the
  pressurization scope. The **wing and empennage** carry no such companion, but
  the deliverable stays per family uniformly — one rule, not a per-component
  exception. **What the user gets is unchanged and unreduced:** each family's own
  critical set as today — SELECT's governing conditions for flight, LANDLOAD's
  six per-FAR critical-reaction summaries plus the 33-case matrix and the
  assembled ground decks for ground — and combining them stays the consumer's
  act, performed with their own pressure cases in hand. The
  `ground-flight-separate-families` standing limitation now carries that reason
  in every report and deck header, beside the `pressurization` exclusion it
  depends on; G-9's original safety-factor argument is deliberately **not**
  restated, having been retracted by **G-10** (both families are limit × 1.5).
  The ground family's genuinely missing piece — no per-station distributed view
  at all, `body_loads`/`net_loads` being flight-only — is filed as **#31**
  (band B), where it stays a *per-family* deliverable. Swept in passing (rule 4,
  the stale-index class #10 corrected the day before): `docs/00_INDEX.md` still
  described design note 19 as "Revision 2 … PROPOSED — not agreed, no code"
  after L-7 shipped on 2026-08-17 — corrected to SHIPPED at revision 3 with its
  implementation named. No calc, no oracle and no shipped load number moves.
