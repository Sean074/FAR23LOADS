- **The oracle report defines every symbol it prints (design note 47, tier L, 2026-09-03).**
  Section 3.3 shipped the column heading `Root chord bending Mzz` against a 3.2
  notation table that defined no `Mzz` — a break of the report's own rule that a
  column heading anywhere in section 3 names a symbol from that table and
  nothing else. The guard covered the two appendix tables only, so the rule was
  unguarded exactly where it was broken. `LoadValue` gains `symbol`, the notation
  symbol held as data on the value rather than as a substring of its display
  label (OR-74, the third instance of the move `frame` and `point` already
  made), and the guard reads it. Parsing was never an option: `Root torsion Myy
  (25% chord)` does not end in its symbol, and two different labels carry the
  same one. The guard now walks section 3's own tables as well as the appendix's
  (OR-75) and additionally asserts that each label prints the symbol it declares,
  so heading and notation cannot drift apart in either direction. Second **OR-15
  admission** of 2026-09-03: `sloads/modules/net_loads.py` is frozen, and the
  manifest is updated in the same commit per G-OR-9. `LoadValue` is persisted
  inside `critical.conditions[].loads`, so the addition is an on-disk shape
  change and `SCHEMA_VERSION` bumps to 60 with an identity hop — the third of
  exactly this shape, after v58's `frame` and v59's `point`.
