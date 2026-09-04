- **Appendix B.2 and section 3.4 state chord bending (design note 47, tier L, 2026-09-03).**
  `Mzz` was left out of the report's cumulative appendix as "not delivered by
  this analysis" and out of its distribution figures as a load nobody reads off
  a plot. Neither was true: it is computed for every case, oracle-locked at the
  root (Appendix A p222), printed by `wing_span_loads.csv`, printed at the root
  by 3.3, and named by the closure gate the appendix is written under — and at
  the root it *exceeds* the torsion beside it on four of the five example cases
  (`ga6_normal` ACRL, 86,959 against 48,244 lb-in). B.2 gains it as a fifth
  column and 3.2 gains its recurrence `Mzz(i) = Mzz(i+1) + Sx(i+1) dy`
  (**OR-71**, superseding note 46's OR-70); 3.4 gains a fifth figure and the
  figure set is tied to the column set by gate, so a further column cannot
  arrive unplotted by omission rather than by decision (**OR-72**, superseding
  note 44's OR-55 on this point). B.2's note now restates that its moments are
  the beam's own positive-magnitude integrals — `Mzz` being the negation of a
  body-axis `Mz` — rather than only pointing at the notation table, because the
  reader B.2 is written for looks a number up and B.1's `Mz` is identically zero
  (**OR-73**). No calculated value changes: a column the result already carried
  becomes a column that is printed.
