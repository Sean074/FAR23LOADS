- **Self-containment split into an image rule and a data rule (`SUMMARY_REPORT.md`
  §2, tier M, 2026-08-30)** — The standard read "the `.tex` SHALL NOT reference
  external image files", and the oracle technical report (design note 44, OR-23)
  needed its LaTeX to read the CSVs shipped in the issue package so the document
  draws the delivered data instead of restating it — the only way two renderings of
  the same numbers cannot drift. The clause was first *read* as already permitting
  it, a CSV being no image; that reading was rejected as a rule meaning something
  its words do not say, and the standard was amended instead. The image prohibition
  is unchanged and absolute, and §2 now states the properties it exists to protect
  (deterministic, diffable, unit-testable as text, vector in the document's own
  fonts, no non-TeX toolchain) — none of which a plain-text data file costs. The
  new *Data reference* clause is scoped to **delivery mode, not to the document**:
  a packaged report may read in-package data given manifest membership, a relative
  in-root path, §3.1 self-description and whole-package determinism; a standalone
  `.tex` may reference nothing. That scoping is what keeps the Export page's own
  `.tex` download from becoming a file that fails to compile, and it is held by a
  new guard rather than by the sentence
  (`test_report_latex.py::test_the_standalone_tex_references_no_external_file`,
  which rejects `\input`, `\includegraphics`, `\pgfplotstableread` and the
  `\addplot table {file}` form alike). The amendment formalises what §1.5, §4.7 and
  §5 already required — that the report travel with companion data files and point
  the reader at them — by making the reference mechanical instead of editorial, so
  the document can no longer misquote its own companion. Note 44 OR-26, which had
  carried the reading, is now a citation of the rule.
