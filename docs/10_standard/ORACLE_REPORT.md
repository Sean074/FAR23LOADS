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

### 3.1 The four section states

Every derived section always exists. What varies is whether it carries its
analysis, and **why** — four states, kept apart because each names a different
party's decision (OR-32):

| State | Means | Bold lead | Sentence |
|---|---|---|---|
| **Included** | the section carries its analysis | — | the analysis |
| **Not yet implemented** | the generator cannot build it yet | *Not yet implemented.* | this revision of the report generator does not yet produce this section. Nothing about this project or this issue is missing. |
| **Excluded** | a person deselected it for this issue | *Not included in this issue.* | excluded by user selection at report generation. |
| **Absent** | the inputs it needs are missing | *Not analysed.* | the inputs this section needs are not present in the project. |

No state's wording **SHALL** be produced by another's cause. Collapsing any two
would tell the reader that a colleague chose to omit a section, or that their own
data was incomplete, when neither is true.

**The lead is part of the rule, not presentation.** It is printed in bold ahead
of the sentence and is what a reader skimming the document takes in, so three
states sharing one lead say the same thing three times however carefully the
sentences differ. The first build of this document gave the three states
distinct sentences and then printed all of them under a hard-coded
*"Not analysed"* — absence's wording — telling readers their inputs were missing
when it was the generator that was incomplete. The guard therefore asserts the
**rendered** lead, not the model's strings.

The title page **SHALL NOT** itemise not-yet-implemented sections alongside
excluded and absent ones. An exclusion or an absence is a fact about *this
issue*, which a reader checks; a section the generator cannot build is a fact
about the tool, identical in every issue, and itemising thirteen of them buries
the ones that are about the reader's own report.

**Precedence, and that it changes.** While a section has no builder,
*not yet implemented* outranks everything: a section the tool cannot produce must
not claim the reader's inputs are missing. Once implemented, `SUMMARY_REPORT.md`
§3.4's rule takes over and *absent* outranks *excluded* — **absent is not
excluded**.

Selection is limited to analysis-body sections and the input echo. Front matter,
the governing-loads summary and methods & limitations are never selectable: they
carry the load basis and the traceability statements.

Sections not carried **SHALL** be stated on the title page — itemised for the
per-issue states, summarised in one sentence for the tool-wide one, per the rule
above. An analyst never receives a reduced document without being told on the
face of it.

## 4. Identity, signatures and DRAFT

The title block carries report number, revision, issue date, issuing
organisation, customer/programme, classification marking, distribution statement
and three signature rows — prepared, checked, approved.

- **Any empty signature name makes the document a DRAFT**: a watermark and a
  footer sentence. All three present clears it. The build **SHALL NOT** be
  blocked by an unsigned spec — a signed and an unsigned report are built by the
  same control, and the document says which it is. There is no user toggle for
  the draft state; it is a fact about the signatures.
- An unsigned signature row **SHALL** still be rendered, with a ruled blank. The
  reader must see *that* a signature is missing.
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

- **Anchors** — project name, category, design weight, wing area, design speeds —
  answer *is this the same airplane* for a reader holding a drawing. They
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
| Cover / title block | 2026-08-30 | `test_oracle_report.py::test_the_draft_mark_follows_the_signatures`, `::test_the_classification_marking_is_on_every_page` |
| Abstract | 2026-08-30 | `test_oracle_report.py::test_it_builds_for_both_example_airplanes` |
| Contents, figures, tables | 2026-08-30 | `test_oracle_report.py::test_it_builds_for_both_example_airplanes` |
| 1. Introduction | 2026-08-30 | `test_oracle_report.py::test_section_numbers_come_from_the_owner_not_from_literals` |
| Analysis-body placeholders | 2026-08-30 | `test_oracle_report.py::test_every_result_producing_oracle_step_has_exactly_one_section`, `::test_the_gap_states_have_distinct_wording`, `::test_each_gap_state_renders_under_its_own_lead` |

## 8. Conformance

- [x] The section set is `oracle_steps()`'s result-producing steps, both
      directions — `test_oracle_report.py`
- [x] The four section states are distinct in wording, in rendered lead, and in
      precedence — `test_oracle_report.py`
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
