- **The oracle technical report printed 1.5× Appendix A's figures, and nothing
  caught it (design note 49 E-c, tier L, 2026-09-05).** Appendix A is a **limit**
  oracle and the oracle tests compare at calc level — they never cross the render
  boundary — so §3's tables rendered ultimate against a document whose whole
  purpose is to be read against p131, and the entire oracle suite stayed green.
  `oracle_sections._load_cell` no longer scales.
- **Seven deck comments asserted the loads were ultimate over LIMIT cards
  (2026-09-05).** Five said *"Loads are ULTIMATE (limit x SF=1.5)"* — the wing
  card block, fuselage, chordwise tail, spanwise tail and control surface — and
  two of those printed a derivation, `= 1.5 x (LT25 + LT50)` and
  `(= 1.5 x critical load …)`, for sums that no longer contained the 1.5. Two
  more said it in different words: the balanced deck's *"the cards below are
  ULTIMATE"*, ten times per deck, and the wing stick deck's
  *"(closed-form, ULTIMATE)"*. Found by **G-OR-73** on its first run.
- **Appendix A's bundle manifest called the per-module CSVs ULTIMATE, and had
  since design note 48 (2026-09-05).** Those CSVs moved to LIMIT then and the
  manifest was never re-read, so the controlling document's statement of what
  each bundle file *is* contradicted the file for a whole release.
  `test_every_manifest_row_states_the_basis_its_file_actually_carries` could not
  see it: it pins the manifest's prose against a hand-written map in the test
  file, so it detects drift between the two and not falsehood in the pair. Both
  were wrong and it stayed green. **G-OR-74** is the truth side; the pin keeps
  its own job, and `SUMMARY_REPORT.md` §4.7 now requires both.
- **`tests/test_report_latex.py` had a gate that passed on prose (2026-09-05).**
  `test_ultimate_markers_and_sf_columns_are_present` asserted `"lbs-ULT" in tex`
  and passed after the sweep — satisfied by the methods stamp *explaining* the
  marker (*"…carry a '-ULT' marker (lbs-ULT, …)"*) rather than by any data cell.
  Replaced by a check on table content with the explanatory prose excluded.
- **`tests/test_data_dictionary.py`'s self-runner was broken (2026-09-05).** Its
  `__main__` block called `test_gui_design_schema_line_current`, a name that no
  longer exists, so the zero-dependency self-runner CLAUDE.md requires of every
  test file died with `NameError`. Found by the new citation guard, which caught
  `GUI_design.md` naming the same dead test.
- **Five test citations in the standard docs named tests that no longer exist
  (2026-09-05).** Two in `ORACLE_REPORT.md`'s conformance table and two in
  `SUMMARY_REPORT.md`'s checklist (renamed by this milestone), one in
  `GUI_design.md` (predating it), and one in `02_approved_corrections.md`'s
  superseded ground-roll entry — reworded to past tense rather than renamed, so
  the historical record stands and the reference still resolves. A conformance
  row naming a deleted test claims a gate that is not there.
