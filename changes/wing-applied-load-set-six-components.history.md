## Step — Six components, and a deck built from them (design note 46, tier L, 2026-09-03)

**Objective.** Make the wing's applied load set usable as what it claims to be:
the deliverable a stress analyst builds a model from. Two defects stood between
it and that claim. It published three of the six components a body-axis load
needs — leaving the reader to decide whether a missing column was a zero or an
omission — and the sbeam deck written from the same wing results carried a
torsion that did not survive being applied at a point.

**Deliverables.** `AppliedLoad` carries `fx`/`fy`/`fz` and
`mxx_free`/`myy_free`/`mzz_free`, with the three structural zeros named at their
single point of construction (`_NO_SPANWISE_STRIP_LOAD`, `_NO_FREE_BENDING`)
rather than written `0.0` inline, so the day a lateral wing condition arrives
the search finds everything that assumed it away. `applied_body_moments` maps
the record's moments to right-handed CID-0 components through
`coordinates.bending_moment_vector`, and both views of B.1 — the report table
and `applied_load_csv` — go through it, so neither carries sign logic.
`wing_nodal_loads` is rebuilt from the applied set: each strip's own load at its
own node, each concentrated mass reduced to the node inboard of it as a force
plus the full three-component `r × F` couple. `_moment_defect` and its relative
tolerance are deleted — the defect they recovered from the cumulative column is
now read from the mass's own coordinates. `sob_internal_loads` and
`sob_collapsed_load` transfer torsion to a shared `sob_reference_point` (the LRA
interpolated at the cut), which a free-moment card set makes load-bearing where
a differenced one did not. Both wing CSVs state their moment conventions in-band.
`equilibrium.py`'s wing claim strengthens from `m0.y` to `m.y`, and its
tolerance scale stops understating the budget of a cancelling cross product.

**Test.** `test_the_applied_set_reproduces_the_whole_vmt_at_every_station`
(G-OR-35) — the applied set's six-component resultant against `Sx`, `Sz`,
`Mxx`, `Myy` and `−Mzz` at **every** station of every case of `ga6_normal` and
`baron_58`, the latter with four concentrated wing masses; worst residual
2.5e-15 relative. `test_the_applied_set_states_all_six_components` (G-OR-36)
pins the zeros as published values and fails if a real component is dropped into
one. `test_wing_deck_resultants` and
`test_wing_deck_reproduces_the_station_table_at_every_node` (G-OR-37) assert the
rigid-body `m.y` from the deck's own text, in both unit systems, on every
example. `test_the_appendix_table_and_the_exported_csv_are_one_load_set`
(G-OR-38) compares all six columns row for row.
`test_each_wing_csv_states_the_moment_convention_it_uses` (OR-69).

**Key decisions.** *The zeros are printed, not omitted, and that reverses an
earlier rule.* The standard had said `Fy` must not be a column lest a zero read
as a measured zero; a partial vector traded one misreading for a worse one, and
the fix is to print the zero **with its reason** in the table's own note.
*Differencing was not a shortcut, it was the only thing available before
`myy_free` and `point_loads` were published* — which is why the deck kept it
after those fields arrived, and why the error survived a full closure sweep:
shear and both bending columns close under differencing, and only torsion does
not. *Building from additive fields needs a guard, not a hope.* `myy_free` and
`point_loads` both default to empty on a `Project` written before they existed,
and a deck built from such a result would be short the whole free torsion and
look exactly like a complete one — so `wing_nodal_loads` checks the root closure
of its source and raises with the recompute instruction rather than exporting a
short deck. *The tolerance owner had a real defect of its own.* `equilibrium`'s
moment scale budgeted each cross-product component by `|t|`, after its two
products had cancelled; on a swept, dihedralled wing the torsion is a small
difference of two large products, and the understated budget called a 44 N·mm
text-rounding residue a physics failure. It now budgets the products separately
and against the absolute coordinate the card format rounds. *Appendix B.2 is not
widened to match.* It states what the structure carries, in the beam's own
convention; putting `Mzz` beside B.1's body-axis `Mz` would place two
conventions in one appendix without a reader-visible reason (OR-70, filed).
*No frozen file was touched:* the whole change lives in `sloads/export/` and
`sloads/report/`, the FAR23 core is untouched, and B.2's numbers are the same
numbers they were.
