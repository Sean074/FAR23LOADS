- **The 2026-08-20 review's MINOR/NIT sweep: two silent zeros, a lossy name, and
  three guards that had stopped guarding (#43, tier M, 2026-08-22)** — the row
  that empties band A, and the one whose findings were individually small enough
  that the interesting part was what measuring them changed. Three of the eight
  did not survive contact with their own numbers. **CR-B-4** proposed raising at
  the two sites that read a CG name; measurement said the mismatch it describes
  can only arise from a *persisted* envelope, which means every number in that
  matrix belongs to weights and CGs the project no longer has — so the refusal
  went to `default_envelope`, the owner, and the two sites got a shared read that
  refuses for a caller threading its own envelope. **CR-C-4** proposed
  "disambiguate or raise"; no shipped fixture collides, so raising would only
  ever have blocked a user's own naming over an eight-character field that is
  sbeam's and a truncation that is ours — the second claimant takes a suffix, and
  the whole derivable list is passed to the mint, because a signature that cannot
  see the other labels cannot check uniqueness against them. **CR-B-5** guessed
  that print granularity or the convergence band explained the widened
  Appendix-A tolerances; measuring all of them showed the split is not where the
  guess put it — case 21's speed is 0.22 % out against a 0.08 % print resolution,
  and case 21's tail load never needed widening at all — so writing the review's
  suggested one-line reason beside each would have recorded the wrong reason for
  at least three. Each tolerance is now computed from the effect that justifies
  it, and the angle-of-attack one falls out of the NZ band through the local
  slope at 0.018 deg against a measured 0.020, which is the kind of agreement
  that says the mechanism is the right one. The other half of the row is guards
  that had rotted into always-passing, each in a different way: one waiting for
  an event that had already happened and been decided against (D-28), one
  exempting a whole file on a comment's say-so, one scanning half the running app
  because the other half lives in a different directory, and one accepting a
  stamp anywhere in a payload rather than where a reader would look. None of them
  was wrong when written. That is the recurring lesson of this review, and the
  reason the replacements are bounded by content rather than by location, and
  come with companions that fail when a named exemption stops naming anything.
  Swept in: `stamp()`'s silent `hasattr` skip, recorded like `defaulted`; the
  oracle GUI's LIMIT caption, which described one of its three tables; and
  `02_parked.md`'s **L-8a**, closed as shipped against the round-trip test that
  drives the very widgets it named. CR-A-9 and CR-D-9 were found already fixed in
  the tree and are recorded as verified.
