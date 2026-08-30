- **The report's front matter became editable, and deselection became silent
  (`ORACLE_REPORT.md` §3, §3.2, §5, tier M, 2026-08-30)** — Four owner decisions
  from the GUI review, one of which reverses a standing rule and is recorded as
  a deviation rather than quietly applied.

  Section 1's prose and a new *Limitations and scope* subsection are now spec
  fields the page pre-fills and the author owns. The limitations default comes
  from `sloads.report.methods.methods_statement`, the single owner of that
  statement across every export channel, so the report opens saying what the
  CSVs and decks say; its own banner is stripped because the subsection already
  carries the title. Author ownership makes both a **snapshot** — they will not
  track a later change to the project or to the shared statement — which was the
  explicit trade: a signed issue must keep saying what it said when it was
  signed. An empty field still means *not yet edited*, so the renderer falls back
  to the default and a spec written before these fields existed renders in full.

  The analysis basis drops to project name and FAR 23 category, the category
  spelled out through `models.inputs.CATEGORIES` rather than a second mapping
  that could disagree with the widgets. The cost is stated in `ORACLE_REPORT.md`
  §5 rather than glossed: with weight, wing area and the design speeds gone,
  name and category are a weak answer to *is this the same airplane*, so the
  fingerprint is now the only thing printed in the document that detects a
  changed input — which is why it was kept. `_fmt` and `_wing_area_sqft` were
  deleted rather than left behind; an unused helper reads as one still wired in.

  **Deselection is now silent**, reversing OR-19 and departing from
  `SUMMARY_REPORT.md` §3.4, which this document otherwise inherits verbatim
  under OR-5 and whose purpose is that an analyst never receives a reduced
  document without being told. The deviation is recorded in `ORACLE_REPORT.md`
  §3.1 with its reasoning; `SUMMARY_REPORT.md` governs a different document and
  is untouched. The half that bites is numbering: sections are numbered by
  position among those that *render*, because numbering by workflow position
  would leave a hole in the printed sequence and every reference after it would
  name the wrong section. The excluded step keeps its plan row so the page's
  preflight still shows the author their choice registered.

  Two follow-ups from the same review. The limitations pre-fill drops six of the
  statement's blocks, and the filtering lives in the report's `default_limitations`
  rather than in `methods.py` — that statement is the single owner for the CSV
  and deck exports too, and dropping blocks at the source would silently thin
  what a forwarded file carries, which is the one thing an in-band
  self-describing block exists to prevent. The guard asserts both halves: gone
  from the pre-fill, still present in the shared statement.

  The analysis basis regained two rows: the sloads version that wrote the
  document and the schema version of the project definition it read. The tool
  version is handed to `anchors()` rather than looked up there — reading
  installed package metadata is filesystem work `sloads.report` does not do, and
  the build already resolves it once for `build.json`, so resolving it twice is
  how a document and its own stamp come to disagree. With no version supplied
  the row is omitted rather than invented: a document naming a build it did not
  come from is worse than one that is silent.

