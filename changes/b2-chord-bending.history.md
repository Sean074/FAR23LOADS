## Step — Chord bending is stated, and a symbol is data (design note 47, tier L, 2026-09-03)

**Objective.** Close OR-70, which note 46 had filed as *not done*, by testing its
reasoning rather than inheriting it — and fix what testing it turned up. OR-70
held that Appendix B.2 should not gain `Mzz` because a beam-convention `Mzz`
beside B.1's body-axis `Mz` would put two conventions in one appendix without a
reader-visible reason.

**What the review found.** The reason does not survive. B.2 already prints `Mxx`
beside B.1's `Mx` — the same pair of conventions — and section 3.2's notation
table already carried the sentence that separates them, written as a forward
reference to a column that was not there: *"so `Mxx` and `Mx` share a sense and a
chordwise bending would not."* OR-69 had settled the identical question one file
away, for `wing_span_loads.csv`, which prints both in the same row. Meanwhile
three statements in the tree disagreed about `Mzz`'s status: the code called it
"not delivered by this analysis" (it is delivered, and oracle-locked at the root
to Appendix A p222), OR-55 omitted it from the *figures* for a reason about
plotting that was never claimed to cover tables, and the standard's own closure
gate named it among "the published" quantities while the appendix did not publish
it. Measured at the root on today's build, `|Mzz|` exceeds the `|Myy|` that does
get both a column and a figure on four of the five example cases — 1.80x on
`ga6_normal` ACRL, 1.34x on its PHAA, 1.05x on `baron_58` PHAA.

**Deliverables.** B.2 states `Mzz` as its fifth cumulative column and 3.2 prints
its recurrence `Mzz(i) = Mzz(i+1) + Sx(i+1) dy` beside the other four, naming the
`Sx`-into-`Mzz` term as a position transfer a structural model generates for
itself (**OR-71**, superseding OR-70). 3.4 gains the fifth figure, and the
figures are tied to B.2's columns by gate rather than by list (**OR-72**,
superseding OR-55 on this point). B.2's note restates the sign instead of only
citing it, because the reader it is written for looks a number up rather than
reading the section through, and B.1's `Mz` being identically zero means nothing
else on the page would warn them (**OR-73**). The notation table gains its `Mzz`
row and its note now names all three beam symbols.

Found in passing and independent of the ruling: 3.3 was printing the heading
`Root chord bending Mzz` against a notation table that defined no `Mzz`, against
the report's own SHALL, and the guard walked only the two appendix tables.
`LoadValue` gains `symbol` — the notation symbol as data on the value, the third
instance of the move `frame` and `point` already made — and `net_loads`
populates it for the six wing root values (**OR-74**). The guard reads the field
and now walks section 3's own tables as well (**OR-75**), additionally asserting
that each label prints the symbol it declares. Parsing the heading was never
available: `Root torsion Myy (25% chord)` does not end in its symbol, and both
torsion labels carry the same one.

**Test.** `test_the_cumulative_table_carries_the_chord_bending` (G-OR-39) checks
every printed `Mzz` against the module's own station value scaled by that case's
safety factor, for every row of every case;
`test_the_cumulative_table_says_its_moments_are_the_beams_own` (G-OR-40) holds
OR-73's restatement; `test_every_cumulative_column_is_also_plotted` (G-OR-41)
asserts the figure set and the column set are the same set;
`test_section_three_defines_every_symbol_its_tables_use` (G-OR-42) is widened to
3.3 and to the label-prints-its-symbol check;
`test_section_three_states_how_the_cumulative_loads_are_built` (G-OR-43) requires
a recurrence for every column B.2 carries.

**Key decisions.** OR-71 … OR-75, design note 47, agreed by the owner in session
2026-09-03. `sloads/modules/net_loads.py` is frozen; the `symbol=` keywords are
the **second OR-15 admission of 2026-09-03**, granted on the ground that the
report cannot be built truthfully while it breaks a rule it prints about itself,
and that the guard cannot be widened without the fix. No oracle moves and no
Imperial digest moves: the change is a defaulted field on a result type,
`report.render.results_to_rows` builds its columns explicitly, and nothing in
`sloads/export/` changed. `SCHEMA_VERSION` **does** bump, to 60 with an identity
hop: `LoadValue` is persisted inside `critical.conditions[].loads`, so a
display-neutral addition to it is still an on-disk shape change — the third
instance of exactly that, after v58's `frame` and v59's `point`. The fields-hash
tripwire is what established it, against a first reading that had filed the
class as an unpersisted result.
