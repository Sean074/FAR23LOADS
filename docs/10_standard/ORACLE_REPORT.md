# The oracle technical report — content standard

The rules the **oracle technical report** conforms to, section by section, as
each is agreed. Created under design note 44 OR-9 and grown with each OR-8
iteration: chat is not a register, so every agreement lands here with the test
that guards it.

**Scope.** The report generated from the oracle GUI (`oracle_app`), covering the
analysis the original McMaster FAR 23 LOADS suite performs and nothing this
replication added. It is not `app/`'s summary report (`SUMMARY_REPORT.md`) and
not the user guide.

**Inherited rules, by citation.** `SUMMARY_REPORT.md` §2 (document identity,
self-containment, the *Data reference* clause, determinism) and §3 (content
rules: ULT marking, absence, filtered exports, one unit system per bundle) apply
to this report **verbatim and are not restated here** (OR-5). Where this document
adds a rule, it is one those sections do not already carry.

Axes, signs, units channels and the ULT/SF contract are
[`CONVENTIONS.md`](CONVENTIONS.md)'s throughout.

---

## 1. The issue package

A report issue is a **package**, not a file: the document, the data behind every
table and plot, the definition it was built from, and a manifest — in one
directory that can be archived, signed, and reopened years later.

- The package directory **SHALL** be named from the report number and revision,
  never from the clock. A rebuild must land on the same directory, which a
  timestamped name makes impossible.
- The **working spec lives inside the package** as `report.json` (OR-28). One
  issue, one directory. Opening a package is resuming work, not reading history.
- `report.json` **SHALL NOT** be written by a build (OR-30). It records what a
  person typed. The as-built stamp — fingerprint, build timestamp, generator —
  belongs in `build.json`, which the builder owns.
- Rebuilding an issue **overwrites in place, silently**; bumping the revision
  **SHALL** produce a new directory beside the old, so an issued revision is
  never destroyed by continued work.
- A build **SHALL NOT** delete a file it did not write. `report.pdf` from a local
  compile lives in the package and is not the builder's to remove. It **SHALL**
  clear `data/` first, so a file left over from a build whose section has since
  been excluded cannot survive as a stray.
- Every member path **SHALL** be relative and stay inside the package root.

## 2. The manifest

`MANIFEST.txt` **SHALL** be a full `SUMMARY_REPORT.md` §4.7 manifest, not a list
of hashes (OR-35): per file, its contents, units, sign and axis conventions, and
the section that summarises it, under an opening statement of the package's unit
system, with section references built from the numbering owner and never written
as a literal section mark.

It **SHALL** be exhaustive in both directions — it lists every file the package
carries, including itself, and names nothing the package does not carry. Its own
hash cannot be inside it, so that row states as much rather than being omitted.

Both rules exist because of real defects: an artifact shipped inside a bundle
with no row at all (review CR-C-1), and a basis cell that called a LIMIT artifact
ULTIMATE through two reviews because the conformance test read row names and
stopped (review CR-C-3).

## 3. Sections

The section set is **derived, never listed**: the owner is
`sloads.workflow.oracle_steps()`, and a step is an analysis section **iff it
produces a result** (it has a `module`). An input-only step has nothing to report
and belongs to the input sections. Adding a module-backed step to the workflow
adds a section with no edit to the report code.

Numbering has one owner, `oracle_content.section_number`, derived from position.
Section references **SHALL** be built from it. A reference that does not move
when a section is inserted above it is a reference to the wrong section.

### 3.1 The section states

A section that is **deselected is not printed at all** — no heading, no reason,
and the sections after it renumber to close the gap. Numbering is by position
among the sections that *render*: numbering by workflow position would leave a
hole in the printed sequence and every reference after it would name the wrong
section.

> **Documented deviation (2026-08-30, owner's decision).** This reverses OR-19
> and departs from `SUMMARY_REPORT.md` §3.4, which this document otherwise
> inherits verbatim under OR-5, and whose stated purpose is that an analyst
> never receives a reduced document without being told. It is recorded here
> rather than by amending `SUMMARY_REPORT.md`, which governs a different
> document and is unchanged. The reasoning is that deselection is the reader's
> own act in this tool, so there is no second party to inform.

Of the sections that **do** print, the state says why it carries no analysis —
three states, kept apart because each names a different cause (OR-32):

| State | Means | Bold lead | Sentence |
|---|---|---|---|
| **Included** | the section carries its analysis | — | the analysis |
| **Not yet implemented** | the generator cannot build it yet | *Not yet implemented.* | This revision of the report generator does not yet produce this section. Nothing about this project or this issue is missing. |
| **Absent** | the inputs it needs are missing | *Not analysed.* | The inputs this section needs are not present in the project. |

No state's wording **SHALL** be produced by another's cause. Collapsing the two
would tell a reader their own data was incomplete when it was the generator that
was.

**The lead is part of the rule, not presentation.** It is printed in bold ahead
of the sentence and is what a reader skimming the document takes in, so two
states sharing one lead say the same thing twice however carefully the sentences
differ. The first build of this document gave each state a distinct sentence and
then printed all of them under a hard-coded *"Not analysed"* — absence's wording
— telling readers their inputs were missing when the generator was incomplete.
The guard therefore asserts the **rendered** lead, not the model's strings. The
sentences are capitalised: they follow the lead and a full stop.

**Precedence.** Deselection is decided first, because it is the state that stops
the section printing and there is then no reader to owe a reason to. Among the
states that print, *not yet implemented* outranks *absent*. When every section
is implemented that ordering stops mattering and *absent* is the only one left.

Selection is limited to analysis-body sections and the input echo. Front matter,
the governing-loads summary and methods & limitations are never selectable: they
carry the load basis and the traceability statements.

The cover carries identity and the approval record and nothing that has to be
read through. With the analysis basis and a thirteen-item list of unbuilt
sections on it, the signature block was pushed onto a second sheet, leaving the
approval record on a page carrying none of the document's identity — the one
page that must never travel alone.

## 3.2 Section 1: introduction, analysis basis, limitations

Section 1 carries the introduction prose, then two unnumbered subsections:
**Analysis basis** (§5) and **Limitations and scope**. Both appear in the
contents.

- The introduction prose and the limitations text are **the author's**. The GUI
  pre-fills each with the generator's default; from then on the spec carries what
  was typed, and a later change to a default **SHALL NOT** reword a report that
  has already been written. Each is a snapshot, deliberately: a signed issue must
  keep saying what it said when it was signed.
- The limitations default **SHALL** come from
  `sloads.report.methods.methods_statement` — the single owner of that statement
  across every export channel — so the report opens saying what the CSVs and the
  decks say. Its own banner is stripped; the subsection already carries the title.
- An empty field means *not yet edited*, not *empty section*: the renderer falls
  back to the same default, so a spec written before these fields existed still
  produces a complete document.

## 4. Identity, signatures and DRAFT

The title block carries report number, revision, issue date, issuing
organisation, customer/programme, classification marking, distribution statement
and three signature rows — prepared, checked, approved. It carries **only**
those: the analysis basis and the not-carried list belong to the introduction
(§3), so the signature block stays on the same sheet as the identity it signs
for.

- **Any empty signature name makes the document a DRAFT**: a watermark and a
  footer sentence. All three present clears it. The build **SHALL NOT** be
  blocked by an unsigned spec — a signed and an unsigned report are built by the
  same control, and the document says which it is. There is no user toggle for
  the draft state; it is a fact about the signatures.
- An unsigned signature row **SHALL** still be rendered, with a ruled blank. The
  reader must see *that* a signature is missing.
- An unsigned row **SHALL NOT** print a date. A date beside a ruled name blank
  reads as an approval that happened on that day and was signed illegibly — the
  document asserting an event that did not occur, on the page a reader trusts
  most. The value is kept in the spec (a planned date is legitimate); it is the
  printing of it against an absent name that is refused. The role is not
  suppressed: naming who is due to sign claims nothing about whether they have.
- Dates **SHALL** be entered through a picker and stored as ISO `YYYY-MM-DD`, so
  one document cannot carry `30/8/26` and `Aug 30 2026` in the same block. The
  picker **SHALL** open empty rather than at today: a control that defaults to
  the current date puts an issue date and three signature dates into the
  document that nobody stated. A stored value that is not a date is preserved
  and reported, never silently replaced — the spec is a file a person edits.
- The classification marking **SHALL** appear on every page, not only the cover.
  A marking that appears once is one photocopied page away from being absent.
- The DRAFT mark **SHALL NOT** be the sole carrier of its meaning: the footer
  states it in words, so the document stays legible in greyscale and to a screen
  reader.
- The watermark **SHALL NOT** add a LaTeX package. The preamble is shared with
  the summary report, and `SUMMARY_REPORT.md` §2 limits the document to a
  standard distribution; the machinery needed is already loaded.
  *Note: the overlay needs two LaTeX passes to position itself. `tectonic` and
  `latexmk` do this; a single bare `pdflatex` run does not.*

## 5. Provenance

The spec records what airplane definition the report was authored against, and
the document prints it. Two questions, two answers, and the document carries
both:

Both are printed in the **introduction**, under *Analysis basis* — not on the
cover, per §4.

- **Anchors** — project name, FAR 23 category (spelled out from
  `models.inputs.CATEGORIES` rather than left as a letter to look up), the
  sloads version that wrote the document and the schema version of the project
  definition it read — answer *is this the same airplane, produced by what* for
  a reader holding a drawing. The tool version is **handed to** the anchors, not
  looked up by them: the build resolves it once for `build.json`, and resolving
  it twice is how a document and its own stamp come to disagree. Where no
  version is supplied the row is omitted rather than invented. They
  **SHALL** be computed at build time, never stored: stored text goes stale
  exactly when it matters, and would be frozen in whichever unit system was
  selected when it was written.
- **The fingerprint** answers *has anything moved*. It **SHALL** be taken over a
  canonical projection of the inputs the oracle report consumes — never over the
  project file, which would fire on a concept-mode field, an sloads-only field or
  a re-save with different key ordering. Free-text document control is excluded
  for the same reason: renaming the engineer cannot move a load.
- The fingerprint **SHALL** carry its own version, so a later milestone widening
  the projection makes existing reports say *"cannot compare"* rather than
  *"does not match"*. Those are different statements.
- On a mismatch the page **SHALL** warn and build anyway. A project is
  legitimately revised under the same report number; refusing would obstruct the
  normal case to police the rare one.
- The fingerprint is **not a signature** — there is no key, so it detects
  accident, not tampering — and it is not the record of what was analysed. The
  input echo is that.
- **The anchors were reduced from six rows to two** on 2026-08-30 (design
  weight, wing area, VC and VD removed as analysis outputs a reader meets in the
  body). The consequence is stated rather than glossed: name and category are a
  weak answer to *is this the same airplane*, so the fingerprint is now the only
  thing printed in the document that detects a changed input.

## 6. Units and determinism

The document's unit system is a property of the **spec**, so a report plus a
project is a complete, reproducible recipe. The build path **SHALL NOT** read the
GUI's unit toggle: that governs what the analysis pages display, which is a
different question with a different owner.

Two builds of the same project and the same spec **SHALL** produce byte-identical
packages, file for file.

**The qualifier is real and is stated rather than hidden:** `build.json` carries
the build timestamp, which the caller supplies. Determinism is over the recipe,
not over the wall clock. A builder that read the clock itself would make this
rule impossible to assert, and it would quietly mean nothing.

## 7. Section register

One row per agreed section, with the guard that holds it (G-OR-8: an agreement
without a guard is prose, not a gate).

| Section | Agreed | Guarded by |
|---|---|---|
| Dates and signatures | 2026-08-30 | `test_oracle_report.py::test_an_unsigned_row_prints_no_date`, `::test_the_report_page_never_defaults_a_date_to_today`, `::test_a_date_is_stored_as_an_iso_string_and_a_non_date_survives` |
| Cover / title block | 2026-08-30 | `test_oracle_report.py::test_the_draft_mark_follows_the_signatures`, `::test_the_classification_marking_is_on_every_page` |
| Abstract | 2026-08-30 | `test_oracle_report.py::test_it_builds_for_both_example_airplanes` |
| Contents, figures, tables | 2026-08-30 | `test_oracle_report.py::test_it_builds_for_both_example_airplanes` |
| 1. Introduction | 2026-08-30 | `test_oracle_report.py::test_section_numbers_come_from_the_owner_not_from_literals` |
| 1. Introduction prose and limitations | 2026-08-30 | `test_oracle_report.py::test_the_default_introduction_claims_nothing_about_omitted_sections`, `::test_the_report_page_renders_every_block` |
| Deselection is silent | 2026-08-30 | `test_oracle_report.py::test_a_deselected_section_is_omitted_entirely_and_numbering_closes_up` |
| Analysis-body placeholders | 2026-08-30 | `test_oracle_report.py::test_every_result_producing_oracle_step_has_exactly_one_section`, `::test_the_gap_states_have_distinct_wording`, `::test_each_gap_state_renders_under_its_own_lead` |

## 8. Conformance

- [x] The section set is `oracle_steps()`'s result-producing steps, both
      directions — `test_oracle_report.py`
- [x] The printing section states are distinct in wording, in rendered lead, and
      in precedence — `test_oracle_report.py`
- [x] A deselected section is omitted and the numbering closes up behind it —
      `test_oracle_report.py`
- [x] The document numbers its pages continuously and marks every page —
      verified at each iteration's local compile
- [x] No report metadata reaches a `ModuleResult` or a table cell —
      `test_oracle_report.py`
- [x] The build reads the spec's unit system and never the GUI toggle —
      `test_oracle_report.py`
- [x] The package is exactly its manifest, hashes included —
      `test_oracle_report_package.py`
- [x] The manifest meets `SUMMARY_REPORT.md` §4.7 —
      `test_oracle_report_package.py`
- [x] Two builds of one recipe are byte-identical —
      `test_oracle_report_package.py`
- [x] The build never rewrites the user's spec —
      `test_oracle_report_package.py`
- [x] The spec round-trips; a missing file opens a blank draft —
      `test_report_spec_io.py`
- [x] The fingerprint moves on an oracle input and not on document control —
      `test_oracle_report.py`, `test_report_spec_io.py`
- [ ] Every shipped data file states units, SF and basis, step key and
      fingerprint — `test_oracle_report_package.py`, **vacuous until the first
      analysis section ships data**
- [ ] No orphan data files in either direction — `test_oracle_report_package.py`,
      **vacuous for the same reason**
- [ ] Every load value equals its `ModuleResult` value × its case's SF — lands
      with the first analysis section
- [ ] The `.tex` compiles to PDF from inside the package — lands with the
      package-aware compile
