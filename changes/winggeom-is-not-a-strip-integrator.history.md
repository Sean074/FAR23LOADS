- **WINGGEOM is not a strip integrator any more, and the prose says so (#155, tier M,
  2026-08-30)** — the closed-form planform integration approved the same day
  (`02_approved_corrections.md`) changed the method but not the twelve places that
  described it, one of which the oracle report prints verbatim in §2.1. This is
  CLAUDE.md rule 4 applied to a documentation defect: the false statement was swept
  across `sloads/`, `tests/` and the standard docs in one change rather than fixed at
  the single site #155 named, and the true uses of "strip" — AIRLOADS' own span loop
  over the load stations, `tail_geometry`'s spanwise integrator, and the historical
  references in the correction register — were deliberately left in place. Two
  substantive consequences came out of the sweep. The WINGGEOM surface table's
  `Integration elements` row became `Load stations`, because `elements` stopped being
  an integration parameter when the integral went closed-form and is now only the
  user's load-station count; and the Appendix A aileron oracle, loosened to ±2 %
  precisely because the strip result depended on an untabulated element count, was
  tightened back to the suite's ±0.1 % (it reaches 0.037 %). The Imperial baseline
  drifts in the `wing_geometry` and `configuration` channels only, and within those
  only in that row label and that note — no load number moves, which is the oracle
  lock holding. **Authority:** `wing_geometry.py`, `configuration.py` and
  `airloads.py` are hash-frozen for 0.8.2 by design note 44 OR-13; the owner admitted
  this change under **OR-15** in session, on the reasoning that OR-14 defers defects
  the report *exposes* while this one the milestone's own correction *created*. The
  manifest hashes are updated in the same commit. Supersedes the "#155 filed, not
  fixed" line in the preceding entry; #153 was admitted separately, on its own
  reasoning, in the entry that follows.
