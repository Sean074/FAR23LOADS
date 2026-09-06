- **A deck value on a rounding tie printed two different loads (tier M,
  2026-09-06).** `dev/v0.8.2` had been red on the Linux CI leg for four
  consecutive commits — the frozen Imperial digest failing on
  `concept_regional_jet`'s `sbeam/balanced_deck` while the same commit passed on
  the developer's Mac. `_fmt` states **seven** significant digits, which is finer
  than a computed load reproduces across platforms, so a value sitting on the
  decimal rounding tie of its seventh digit took round-half-even off the last
  bit: `-341426.25` in the regional jet's `MOMENT` cards printed
  `-3.414262E+05` here and `-3.414263E+05` there, for one load. Every emitted
  value is now canonicalised to twelve significant figures first —
  **248 of the 159,407 values the six baseline decks emit were tie-fragile under
  ±3 ulp; none are now**, and 36 emitted lines moved, every one a single digit in
  the seventh place where no information was carried.
- **The same load printed as two different numbers on one row of a shipped gear
  report.** `atr42_100`'s `LG-19…LG-22` stated *Ground-line V* as
  `2.448331E+04` and *Datum Fz* — the same load — as `2.448330E+04`, because the
  two columns straddled the tie from opposite sides. They now agree. This was
  live in a delivered artifact, not only in CI.
- **The twelve-figure rule has one owner instead of two copies.** The human
  channel got this fix at #147 (`report/render.py`); the solver channel never
  did, and the class recurred one channel over. `units.canonical` is now the
  single owner both read (`CONVENTIONS.md` §7, clauses (d) and (e)), guarded by
  `test_platform_stability.py::test_no_emitted_deck_value_hangs_on_the_last_ulp`
  over every value every deck actually emits on all six examples.
