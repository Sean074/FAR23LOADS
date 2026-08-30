- **`SUMMARY_REPORT.md` §2 splits self-containment into an image rule and a data
  rule (tier M, 2026-08-30, design note 44 OR-23/OR-26).** The prohibition on
  external **image** files is unchanged and absolute — figures remain pgfplots/TikZ
  source — and the standard now states the properties it protects: deterministic,
  diffable, unit-testable as text, vector in the document's own fonts. A new *Data
  reference* clause permits a report **delivered as a package** to read plain-text
  data files from inside that package, so a table or figure is drawn from the
  delivered data rather than restating it, on four conditions: the file is listed
  in the §4.7 manifest, its path is relative and stays inside the package root, it
  is self-describing to §3.1 (units, `-ULT`, safety factor and basis), and
  determinism holds for the whole package. A report delivered as a **standalone
  `.tex`** — which the Export page's summary-report download is — SHALL NOT
  reference any external file, now held by
  `test_report_latex.py::test_the_standalone_tex_references_no_external_file`.
