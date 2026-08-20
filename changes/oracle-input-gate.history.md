- **Gate G5: running the field registry, and what that cost it (design note 32 step OG-C2, tier M, 2026-08-19)** —
  OG-C shipped a 323-row registry in which every row cited its evidence, and the
  guards checked that the citations *existed*. G5 checks what they *claim*: build
  the project the oracle GUI would produce, run it, and compare. The first run
  failed on three modules, and every failure was the table rather than the gate.
  Twelve rows called sloads capability are inputs of a named `.BAS` program, and
  in each case the repo already said so somewhere the table's author had not
  looked — `MassItemKind` "mirrors the data-base partition of WTONECG.BAS"; the
  surface edge polylines are entered "exactly as the original program prompts for
  them" and `elements` **is** WINGGEOM.BAS's `H`; a `CgCase` is one of the four
  corners "FLTLOADS.BAS prompts for"; `EngineWeightType` holds "the two-letter
  codes of the original program". The decisive one needed no docstring at all:
  drop the weight database's per-item inertias and Appendix A p136's IXX comes
  out **66.7 slug-ft²** against the printed **1201.527**, which is the
  parallel-axis transfer of a centreline point-mass database and not what
  WTONECG prints — so the oracle the suite has passed all along *depends* on
  those fields being entered, and calling them a sloads addition was a claim the
  existing test suite had already falsified without anyone reading it that way.
  The gate also forced a column. `origin` answers *who asked*; G5 needs *what the
  project contains*, and the two differ exactly where this model carries as data
  what the original carried by position — which surface a planform describes,
  which of LANDLOAD's three loadings a CG case is, whether an aileron is mirrored.
  Folding those into `ORIGINAL` would have corrupted a historical fact to make a
  gate pass, so they carry `supplied` instead, and the mark is **earned** rather
  than granted: either the field has no declared default (the record cannot be
  constructed without it — read off `dataclasses.fields`, not judged) or omitting
  it demonstrably moves a number, which is G5 itself. Eleven fields qualify
  against 219 asked for, and a guard keeps that ratio from drifting, because
  `supplied` is the one mark that could silence any future G5 failure. Two
  smaller things fell out. `structurally_required()` turns an accident into a
  rule: the wing planform survived the first reduction only because
  `SurfaceInput.leading_edge` happens to have no default, and a `default_factory`
  added one afternoon would have quietly deleted the wing from the oracle GUI's
  input set. And the reduction is exact on five of the six shipped examples —
  the sixth, `concept_regional_jet`, is excused in the file with its reason,
  since an airplane certified through 25.335(b)'s Mach-margin route is outside
  the original suite's scope by construction and requiring the second front-end
  to reproduce it would be claiming ground the first suite never had. Final
  shape: 323 fields, 219 `ORIGINAL`, 11 supplied, **93 omitted** — a real
  reduction, and 29 % rather than the note's estimated half.
