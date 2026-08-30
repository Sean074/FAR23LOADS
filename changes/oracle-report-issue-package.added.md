- **The oracle technical report: the report page, the report spec and the issue package (note 44 §7–§9, tier L, 2026-08-30).**
  The oracle GUI gains a **Report** page — the one page of that front end that is
  not a workflow step — which edits a report specification and builds an **issue
  package**: a directory holding `report.tex`, the `report.json` the page edits,
  a `build.json` as-built stamp, a copy of `project.json`, and a `MANIFEST.txt`
  that meets `SUMMARY_REPORT.md` §4.7 in both directions. Iteration 1 delivers
  the front matter — cover, abstract, contents, list of figures, list of tables
  and §1 Introduction — with every derived analysis section already present as a
  stated placeholder, so the derived-section gate holds from the first commit
  rather than the last.
  New owners: `ReportSpec` + `REPORT_SCHEMA_VERSION` (`sloads/models/report.py`),
  the provenance fingerprint and anchors (`sloads/report/fingerprint.py`), the
  content model and its four section states (`sloads/report/oracle_content.py`),
  the document's furniture (`sloads/report/oracle_latex.py`), the package member
  list and manifest (`sloads/report/oracle_package.py`), and the package writer
  (`sloads/export/report_package.py`). The report's content rules accrue in the
  new `docs/10_standard/ORACLE_REPORT.md`.
