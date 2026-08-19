- **Three long-open questions recorded as decisions, not carried as work** (decisions
  **D-29**/**D-30**/**D-31**, issue #13, tier S, 2026-08-18; #12 merged in at the 0.7.0
  re-cut, review BR-6). Each was pinned by a test and described in the backlog as an
  open defect; none was, and the bodies leave the *Open defects* index under the
  removal rule while both pins stay.
  **D-29 — the derived `ACRL` point.** With `wing_mass.cases` empty the derived wing
  case names SELECT's own 23.349(a)(2) pick (CL ≈ 1.30 at 117.4 kt), which differs
  ~19 % from the worked example's entered point (CL 1.55 at 116 kt, Ref 1 p217-221) and
  carries `unbal_moment = 0`. Accepted and stated rather than reconciled: there is no
  printed oracle for the derived route and every shipped fixture enters its cases
  explicitly, so no oracle or deliverable is affected. The consequence is now stated
  where the route is offered — the derived route is a **first pass**, and an `ACRL`
  case used for sizing is entered, never derived.
  **D-30 — the ATR-42's Mach-capped points.** The nine points at 25,000 ft that sit
  above the Mach-adjusted stall CL are **ordinary stall/Mach-limited flight, not a
  defect**: an airplane commonly cannot reach its manoeuvre load factor at altitude, and
  the regulation says so — **23.333(b)**'s manoeuvring envelope applies "*except where
  limited by maximum (static) lift coefficients*" (Ref 1 p62; Ref 2 §11.2.1.2 p68), so
  these points lie **outside** the envelope the rule defines rather than being design
  conditions the airplane fails to reach, and the Mach cap that produces them is
  **23.335** a.(4)'s own compressibility-limited MC at altitudes where an MD is
  established (Ref 2 §7.2.1 p45-46; here MC = 0.4555), design speeds being EAS otherwise.
  The point is nonetheless *not* re-reported at a reduced "attainable" load factor — on
  conservatism and method consistency, **not** on an obligation to design to n = 2.5
  there, which the rule does not impose — and the fixture is *not* edited to hide a true
  statement about a real airplane. This retires the previous framing that those
  loads are "not physically attainable": `nz = n` is enforced, so the load factor and
  the total `n·W` are exact and the entire effect is on the LZW/LT split. Measuring it
  (2026-08-18) found the real content — the balance closes at alpha 14.1–16.3 deg
  against a fitted stall edge of 13.18 deg, so CM and CD are extrapolated 0.9–3.1 deg
  past their fits, and frozen at the fit edge instead the published tail quantities move
  3.3–44 % (LT), 6.5–20.4 % (LT25/LT50), 8.5–20.8 % (elevator load) and 1.1–4.8 deg
  (elevator deflection), against a base-method band of 5–10 %. Above the bar, so it is
  ranked (rule 6) — but **0 of the 9 are SELECTed as a governing critical condition**,
  so no sizing case, critical-condition table or exported deck load moves anywhere. It
  is a published-number marking item: BALLOADS publishes all 300 V-n points, so nine
  published rows carry the extrapolation unmarked. Filed as **#32** (mark them — rows
  stay published and marked, never withheld, the marker derived at publication from the
  point's own CL against its Mach-adjusted stall CL, so no schema field) and **#33**
  (the solver's own silence: both iteration loops return their last iterate with no
  signal, swept across both loops per rule 4).
  **D-31 — gust spanwise shape.** The gust cases reuse the manoeuvre spanwise shape;
  the difference is inside the Schrenk band *by construction*, Schrenk being this
  method's own approximation of that shape, so it is recorded with the ±5–10 % that
  parks it (`docs/20_theory/00_theory_sources.md` §Base-method uncertainty) and
  re-opens only if the wing airload basis moves off Schrenk.
  Swept in passing (rule 4): removing the table's first row exposed a latent hole in
  `tests/test_backlog_issues.py::test_render_round_trips_the_live_table_and_drops_closed_rows`.
  `render_backlog` keys a row to its **first** `(#N)` — the one `row_from_issue` emits —
  so a later `(#N)` in the same line is a cross-reference and closing *that* issue must
  leave the row alone; the test instead expected every row line *mentioning* the closed
  issue to disappear. The two agreed only while the table led with an issue nothing else
  cited, and stopped agreeing the moment #29 led it and #17's row cites it. The test now
  encodes ownership, and asserts positively that a citing row survives with its text
  intact — the production behaviour was correct throughout, and no shipped table row
  changes.
  No calc, no oracle and no shipped load number moves; the two pinning tests keep their
  assertions and gain the decision each now pins.
