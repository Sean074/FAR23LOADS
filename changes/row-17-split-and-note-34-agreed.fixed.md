- **Row 17 is split by mechanism, note 34 reaches AGREED, and the suite-runtime
  row is re-measured (tier S, 2026-08-26).** Three corrections to the 0.8.0
  record, none of them a code change. **The split:** the C210 family the
  2026-08-24 re-cut folded into row 17 was 26 findings across 14 pages sharing
  nothing but a review date, and its one tier-L member — TAILDIST recording the
  aero state of each case — would have gated twenty-five presentation findings
  behind a schema change. It is now five rows by mechanism: the text-only
  residue stays at row 17 (#94), the derive-by-default overrides go to #97, the
  fields filtered off the page to #98, the placement/validation pair to #99, and
  the tier-L aero-state contract to #100, which carries its own design-note-first
  requirement.
- **Design note 34 (oracle GUI user guide) moves PROPOSED → AGREED**, milestone
  0.8.0. Its four open questions were answered by the owner on 2026-08-25 as
  UG-9 … UG-12, but the note carried them for a day still marked PROPOSED — the
  state that blocked note 32's step OG-B and would have blocked the guide's
  first chapter under `CLAUDE.md` rule 1.
- **The suite-runtime revisit clause (#92) is re-measured, and the figure that
  tripped it was a coverage-instrumented run.** Plain `pytest`, the documented
  local command: 62.1 / 62.7 s, one call over 16 s, none over 30 s — inside all
  three of the clause's thresholds. Under `--cov=sloads` with
  `COVERAGE_CORE=sysmon`, as CI's coverage leg runs it: 265.6 s, 13 calls over
  16 s and 8 over 30 s, reproducing the recorded 269 s. The test named as the
  critical-path floor at the trip measures 2.3 s in isolation and enters the top
  20 in neither mode. The row keeps both readings and states the scoping
  question it now poses — close as no-longer-tripped, or re-aim at the coverage
  leg that gates the push to `main` — as the owner's to answer.
