- **Flutter clearance leaves the tool, and the register learns a third category
  (#79, C210-19, tier M, 2026-08-26)** — MACHLIM printed a flutter-clearance Mach
  `MFC = 1.2·MD` and its per-altitude `V(FC)` because `MACHLIM.BAS` does, and this
  project's default is to replicate what the manual prints. The owner's directive at the
  Cessna 210 build review reversed that here on two grounds: flutter substantiation is
  23.629 rather than a design load, so nothing downstream sizes to it; and the symbol is
  actively misleading to the Part 25 audience this tool now serves, who read `VFC`/`MFC`
  as §25.253's maximum-speed-for-stability pair. A quantity nobody uses, under a name
  that means something else, is worse than an absent one. Removed from the calc, the
  report series, the workbook column, the Speed–Altitude chart and the theory document;
  MNE and the V(MC)/V(MNE)/V(MD) lines are untouched and still oracle-locked, which is
  why this was surgery rather than a sweep — both quantities live in the same six lines.
  The interesting part is the record. Dropping a printed Appendix A output is not an
  approved *correction*: the corrections register exists to say "the manual is wrong and
  here is the right number", and Appendix A's MFC 0.4836 is the right answer to the
  equation the original program runs. Recorded under a new **Withdrawn from scope**
  heading that states the difference explicitly, so a later reader cannot mistake a
  narrowed replication for a fault found in the source. The drift guard is an AST scan
  over every shipped package rather than a test of the module's output, because the
  quantity was computed in two places — `mach_limit.py` and the main GUI's chart, which
  carried its own `1.2 * md` — and removing only the first would have left the line still
  drawn from a local copy. That is the same shape as the defect the removal was about.
