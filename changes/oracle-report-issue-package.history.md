## Step 0.8.2-1 — The oracle technical report: page, spec and issue package (note 44 §7–§9, tier L, 2026-08-30)

**Objective.** Deliver iteration 1 of the oracle technical report (backlog row
24, #151): a working end-to-end artifact — fill in a report's identity in the
oracle GUI, press *Build issue package*, and get a directory on disk holding a
compilable document and everything needed to reproduce and audit it. The report
is a *view* of an analysis that is already oracle-locked, so the milestone runs
under note 44 §6's freeze throughout.

**Deliverables.**
- `oracle_app/report.py` — the Report page: package location and picker,
  document identity, abstract, signatures, distribution and marking, the
  document's unit system, section selection, a preflight table, provenance, and
  the build control. Registered on `st.navigation` in `oracle_app/Oracle.py`
  (the one admitted edit to a frozen file, OR-13 item 2 as widened by OR-16) and
  deliberately **not** in `register_pages`, which stays exactly `oracle_steps()`.
- `sloads/models/report.py` — `ReportSpec`, `SignatureRow`, `RevisionRow`,
  `ProjectIdentity`, `REPORT_SCHEMA_VERSION`, `default_spec`, `is_draft`.
- `sloads/io.py` — `load_report`/`save_report`/`report_spec_to_json` and the
  package's path owners (`report_package_dirname`, `default_report_root`).
- `sloads/report/fingerprint.py`, `oracle_content.py`, `oracle_latex.py`,
  `oracle_package.py`; `sloads/export/report_package.py` for the writing.
- `docs/10_standard/ORACLE_REPORT.md`, created per OR-9 with its section
  register and conformance list.

**Test.** `tests/test_report_spec_io.py`, `tests/test_oracle_report.py` and
`tests/test_oracle_report_package.py` carry G-OR-1 (both example airplanes),
G-OR-2, G-OR-5/16, G-OR-6, G-OR-7, G-OR-10, G-OR-11, G-OR-12, G-OR-13, G-OR-14
as widened by OR-35, and the new G-OR-18/G-OR-19. G-OR-15 and G-OR-17 are
written but **vacuous until the first analysis section ships data**, and their
docstrings say so rather than letting a green tick imply coverage. The
summary report gained a structural companion to its standalone guard
(`test_the_summary_content_sets_no_data_ref`).

**Key decisions.**
- *One renderer, two emission modes.* `Table` gained an optional `data_ref` and
  `report/latex.py`'s emitters were promoted to public names; the oracle
  renderer owns only its furniture and borrows every emitter. Forking the
  renderer would have duplicated the column-width model and the `longtable`
  machinery, and would have made the eventual main-report merge a rewrite. The
  summary report's bytes did not move, which its existing byte-identical test
  proves.
- *The package directory is the spec's home* (OR-28, superseding OR-24), and the
  as-built stamp moved to `build.json` (OR-30). One issue, one directory; and
  because the builder never writes the file the user edits, the byte-identical
  rebuild gate needs no list of stamped fields to exclude — a carve-out that
  would have had to be maintained for every field the spec ever grows.
- *A third gap state.* "Not yet implemented" is distinct from "excluded by user
  selection" and "absent for missing inputs" (OR-32), with a precedence that
  changes once a section is built. Collapsing it into either would have told the
  reader that a colleague chose to omit a section, or that their own data was
  incomplete, when neither was true — and it is what lets G-OR-2 hold from the
  first commit.
- *The manifest is a real §4.7 manifest* (OR-35). The `SUMMARY_REPORT.md` §2
  *Data reference* clause conditions the packaged-report permission on a §4.7
  manifest, so the lighter name-and-hash list OR-22 described would not have met
  the rule this milestone itself wrote.
- *The fingerprint rides on `field_registry.reduce_to_oracle_inputs`*, the
  existing owner of oracle scope, so G-OR-6 and G-OR-13 are the same guarantee
  rather than two scope lists that can drift. Free-text document control is
  excluded from the hash: renaming the engineer cannot move a load, and a
  warning that fires on noise is ignored on signal.
- *The DRAFT watermark adds no LaTeX package* — TikZ machinery the shared
  preamble already loads. The preamble is shared with the summary report, and
  acquiring a dependency there should be earned.
- *The page computes nothing* — no path, hash or clock read. The oracle GUI's
  import gate forbids `os`, `json`, `hashlib` and `datetime` outright, which
  turns that from a convention into something enforced.
- *Deferred, with reasons stated:* the PDF compile (OR-36 — `compile_pdf` takes
  a source string and cannot resolve a package's relative reads) and the example
  report file (OR-37 — OR-28 leaves nowhere for it to live).

**Found by compiling the document rather than by reading it.** Five defects
survived a green test suite and were only visible in the rendered PDF, which is
the argument for OR-8's rendered-sample approval step:

1. Every placeholder printed under a bold **"Not analysed"** — *absence's*
   wording — because that lead was hard-coded in the shared renderer. The model
   had three correct sentences and the reader saw one wrong phrase. `Section`
   gained an `absent_lead`, the states own their leads, and the guard now
   asserts the **rendered** lead rather than the model's strings.
2. The title page listed all thirteen not-yet-implemented sections as though the
   reader's issue had been cut down. They are now summarised in one sentence,
   with only the per-issue exclusions and absences itemised.
3. The footer overprinted the classification marking, the load basis and the
   draft sentence on one line. The centre slot is stacked and the footskip grows
   on a draft.
4. `\begin{titlepage}` reset the page counter, so a two-sheet cover produced
   "Page 1 of 4" on the third sheet — and suppressed the page style, dropping the
   classification marking from the page most likely to be photocopied alone.
   Dropped in favour of a plain page and `\clearpage`.
5. The provenance block printed a fingerprint with no anchors, because the
   builder never computed them. It does now: the human half of OR-21 is the half
   that actually gets used.

Also fixed before it could bite: Streamlit resolves a keyed widget from session
state and ignores a later `value=`, so opening a second issue would have redrawn
the first one's fields over it and saved them back. The page retires its spec
widgets on a switch, with a drift guard over the retirement list — the failure
mode of forgetting one is silent data loss, not an error.

**Found by using the page.** A GUI review against `ga6_normal` changed how the
report's location is chosen, twice. The first build offered a free-text path
box, which is the one control the rest of the app deliberately does not have:
the sidebar's *Save to disk* offers no location choice at all (#94, C210-48)
because a browser page cannot open an OS dialog for a server-side write. That
was replaced with a resolved root and a click-through folder browser — and the
answer was still wrong, because a new report has to be able to go somewhere the
browser cannot reach in a reasonable number of clicks.

The resolution takes the constraint apart rather than working around it: the
oracle GUI is run **locally**, so the machine serving the page is the machine
the user is sitting at (OR-22), and the operating system's own folder chooser is
reachable after all. `sloads/export/directory_dialog.py` runs it in a
subprocess — `osascript` on macOS, `FolderBrowserDialog` on Windows,
`zenity`/`kdialog` otherwise — on the same footing as `export/pdf.py` shelling
out to a TeX engine. Not `tkinter`: this interpreter has no `_tkinter`, and on
macOS Tk must own the main thread, which a Streamlit script never does, so an
in-process dialog would abort the app rather than open one. Every non-answer —
no helper, Cancel, timeout, a path that is not a directory — returns `None`
alike, because the caller's response to all four is to leave the folder alone;
the click-through browser stays as the fallback, since a chooser that silently
does nothing would leave no way to set the location at all.

Three defects came out of the same review, one of them shipped:

1. **Browsing to `~/Desktop` crashed the page.** macOS keeps Desktop, Documents
   and Downloads behind TCC, and `discover_packages` called `listdir`
   unguarded. The first fix was worse than none: it hardened the sibling
   `list_subdirs` and left `discover_packages` bare, which is precisely the
   half-swept fix rule 4 exists to forbid. Swept properly, the same shape turned
   up in shipped code — `io.list_saved_projects` guarded a *missing* projects
   directory and not an unreadable one, carrying the identical crash into the
   sidebar for anyone whose projects folder sat somewhere protected. Both now
   answer "no packages / no projects *that this process can open*", which is the
   question the caller is actually asking, and both are held by a test that
   `chmod 000`s a real directory.
2. **Choosing a folder is not being granted it.** The OS chooser returns a
   TCC-protected path quite happily and the write then fails at the end of a
   page the user has already filled in. `is_writable` is checked when the folder
   is chosen, and the warning names the remedy; `Save spec` now reports that
   failure as a message, which only *Build* did before.
3. **Opening a package discarded unsaved spec edits silently.** Selection change
   loaded immediately, where the sidebar puts the same act behind a button and a
   guard. Selecting is now browsing, an explicit **Open** does the discard, and
   an unsaved spec warns first.

And one caught before it could ship: the first test written for the folder
dialog *called it*, which on any machine with a desktop session opens a Finder
window and holds the suite behind it — visible only as a jump from 2 s to 31 s.
It is stubbed at the subprocess boundary now, testing the decision logic without
opening a window. The same test carried an `assert x is None or True`, which
would have passed for ever.

