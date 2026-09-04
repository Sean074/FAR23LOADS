# Oracle technical report — scope, shape and development protocol

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: AGREED 2026-08-29 (owner, in session — `CLAUDE.md` rule 1's
working-alone path); nothing built. Milestone: 0.8.2.** The three §5 open
questions were answered the same day and are recorded as OR-10 … OR-12 (§5),
on the same footing as OR-1 … OR-9. §6 (2026-08-30) adds the milestone's
development constraints (OR-13 … OR-15) and §7 (2026-08-30) settles the report
file and the report page (OR-16 … OR-21) ahead of iteration 1, and §8
(2026-08-30) settles the issue package the build produces (OR-22 … OR-27); §9 (2026-08-30)
settles iteration 1 and supersedes OR-24 (OR-28 … OR-37). This note settles the shape of an
**automatic technical report generated from the oracle GUI's analysis** — what
document it is, where its content comes from, where it is triggered, and the
unusual development protocol (one section at a time, each agreed by the owner
before the next is built) — so that writing the sections is mechanical rather
than a fresh judgement call per section.

**Scope.** A formal technical report limited to the **oracle GUI capability**
(`oracle_app/`, design note 32): the analysis the original McMaster FAR 23
LOADS suite performs, and nothing this replication added. It is a **clean,
modern formal document that covers the same capability** — it does not imitate
the original programs' printouts (owner ruling 2026-08-29, consistent with the
C210-15 fidelity ruling: the contract is the analysis, not the presentation).
It is **not** the consolidated loads summary report
(`10_standard/SUMMARY_REPORT.md`, the export-bundle deliverable) and not the
user guide (`docs/60_guide/`, note 34): the summary report tells a structural
analyst *what to size to*; this report tells a reviewer *what analysis was
performed, by what method, on what inputs, with what results* — module by
module, with figures.

**Strategic intent.** The existing summary report needs substantial further
development. The plan of record is: the oracle report is developed first and
agreed section by section; once agreed, it becomes the **starting point and
reference implementation for the rebuilt main-GUI report**. Decisions taken
here are therefore taken as future main-report decisions unless explicitly
marked oracle-only.

Sources reviewed: `CLAUDE.md`, `docs/10_standard/SUMMARY_REPORT.md`,
`docs/10_standard/CONVENTIONS.md`, `docs/30_future/32_oracle_gui_note.md`,
`docs/30_future/34_oracle_user_guide_note.md`, `sloads/report/*.py`,
`sloads/workflow.py`, `oracle_app/*.py`, `app/views/export_report.py`.

---

## 1. Decisions (OR-1 … OR-9)

| # | Decision | Rationale |
|---|---|---|
| **OR-1** | The report is built **inside `sloads/report/`**, sharing the existing infrastructure: the `Section`/`Table`/`Figure`/`ReportDocument` content model, the `latex.py` renderer, the `Units` limit→ultimate boundary, and the pgfplots figure machinery. A new content builder (`sloads/report/oracle_content.py`) answers *what this report says*; nothing about *how it looks* is duplicated. | One renderer, one ULT boundary, one figure engine — the consolidation rule. A parallel generator would fork the exact machinery the main-report rebuild is meant to inherit. |
| **OR-2** | **The section set is derived, not listed**: one numbered analysis section per step in `sloads.workflow.oracle_steps()`, in workflow order, bracketed by fixed front sections (identity, introduction & scope, conventions, input data) and back sections (governing summary, references, input-echo appendix). Adding a `bas` to a workflow step adds a report section with **no report-code edit**. | Inherits note 32 gate G2 exactly as the user guide did (UG-7). A hand-maintained section list is the page-list defect wearing a third hat. |
| **OR-3** | The trigger is a **new page in `oracle_app`**, appended after the derived analysis pages. This **amends note 32's "deliberately does not have" list**: the LaTeX *summary* report remains `app/`-only; the *oracle technical report* is oracle capability reporting on itself and belongs where the analysis runs. Note 32's docstring statement in `oracle_app/Oracle.py` is updated in the same change. | The report's whole scope rule is "what the oracle GUI can do"; generating it from `app/` would put the document's home outside its own scope boundary. The amendment is recorded here and cross-linked from note 32. |
| **OR-4** | **Format: LaTeX → PDF.** The `.tex` is the primary artifact (downloadable always); the PDF is compiled when a TeX engine is available, exactly as the summary report does it. Self-contained: standard-distribution packages only, figures as pgfplots/TikZ source, no external image files. | Matches `SUMMARY_REPORT.md` §2 verbatim, keeps the two documents compilable by one toolchain, and hands the main-report rebuild a format it already speaks. Word/Markdown would create a migration at the exact moment of reuse. |
| **OR-5** | `SUMMARY_REPORT.md` **§2 (identity) and §3 (whole-document content rules) apply verbatim**: determinism (byte-identical renders at the same unit selection, caller-supplied timestamp), every load ULTIMATE with the `-ULT` marker and a stated SF per case, non-loads never scaled, traceable case IDs, absence-is-content (a section whose inputs are missing renders with its `absent_reason`, never disappears). | These rules are the document standard, not a summary-report peculiarity. Restating them per document is the drift the SSOT rule exists to prevent. |
| **OR-6** | **Nothing is recomputed.** Every figure and table value comes from the same pure builders the GUI pages consume (`run_all_modules` and the per-module `ModuleResult` slices, the plot builders behind `plots_tex.py`). The report is a *view* of the analysis, with a guard test asserting table values equal `ModuleResult` values. | `content.py`'s first rule, inherited. A report that computes its own numbers eventually disagrees with the pages it documents. |
| **OR-7** | **Graphics are computed plots from oracle data** — V–n envelope, spanwise/chordwise distributions, and per-module figures — generated through the owners behind `plots_tex.py` and the `app/` plot pages. One plot owner per figure, shared between GUI display and report; the report never grows a parallel plotting path. The oracle GUI's own pages remain plot-free (note 32 unchanged on that point): the plots exist in the *document*, not on the pages. | Consolidation rule again; and it keeps the oracle GUI's original-suite fidelity intact while the formal document gets the figures a formal document needs. |
| **OR-8** | **Development protocol: one section at a time, agreed before the next.** Each iteration: (1) a content spec for one section — its tables, figures, `ModuleResult` fields, and sample values from `examples/ga6_normal.project.json`; (2) owner agreement on the spec; (3) implementation + rendered sample PDF; (4) owner approval of the rendered section; (5) next section. The first iteration is the document skeleton + front matter, which fixes the visual and formal register everything else follows. | The owner's explicit working requirement for this feature. Encoding it here makes "agreed" a recorded state per section, not a memory. |
| **OR-9** | The report's own content standard (the per-section SHALL list, as it is agreed section by section) accrues in a **new standard doc, `docs/10_standard/ORACLE_REPORT.md`**, created with the first section and grown with each agreement. It cites `SUMMARY_REPORT.md` §2–§3 rather than restating them (OR-5). When the main report is rebuilt, the shared rules migrate up rather than being copied. | The section-at-a-time protocol needs somewhere durable for each agreement to land; chat is not a register. A standard doc per document matches the existing pattern. |

---

## 2. Document skeleton

Fixed front and back matter; the analysis body is derived (OR-2). Numbering
comes from a `SECTIONS`-style single source in `oracle_content.py`, exactly as
`content.py` owns the summary report's numbering (its F-R2 lesson).

### Front matter (fixed)

| § | Section | Contents |
|---|---|---|
| — | Title page | Project identity, aircraft, date (caller-supplied), code version, `SCHEMA_VERSION`, unit system, the load-basis statement in words (`SUMMARY_REPORT.md` §3.1). |
| 1 | Introduction & scope | What analysis this report documents: FAR Part 23 Subpart C structural design loads per the McMaster suite capability; what it excludes (concept mode, sbeam decks, everything sloads-only); references — `FAR23Loads_Code.pdf`, DOT/FAA/AR-96/46, `14 CFR 23` Subpart C. |
| 2 | Axes, sign conventions and units | Cites `CONVENTIONS.md` via the existing `conventions_tex.py` owner; the LIMIT→ULTIMATE contract stated once. |
| 3 | Input data | The airplane as analysed: configuration, geometry, weights, aero data, speeds — the traceability section, from the `Project` slices the oracle pages populate. |

### Analysis body (derived — one section per `oracle_steps()` step, workflow order)

Illustratively today (the report derives this; the note does not own it):
structural speeds; flight envelope (V–n); wing loads; fuselage loads; tail
loads; aileron loads; flap loads; tab loads; engine mount; one engine out;
landing loads — each section following one template (§3 below). Input-only
steps (geometry, weight & mass, aero data) appear in §3 Input data rather than
as analysis sections; the derivation rule is *steps with a `bas` that produce
results* — settled precisely in the first OR-8 iteration.

### Back matter (fixed)

| § | Section | Contents |
|---|---|---|
| n−1 | Summary of governing loads | The governing cases across the analysis body, ULT-marked, SF stated, located. |
| n | Methods and limitations | What the analysis does not cover and how much to trust it, scoped to the oracle capability; base-method uncertainty per `theory_sources.md`. |
| A | Input echo | Complete input listing from the project file — the reproducibility appendix. |

### Per-section template (analysis body)

1. **Condition and requirement** — the FAR paragraph(s) and original program(s), one paragraph.
2. **Method** — one paragraph naming the method with its `theory_sources.md` citation; never a re-derivation.
3. **Inputs used** — the slice values this module consumed (from the `Project`, not retyped).
4. **Results** — tables from the module's `ConditionResult`s: ULTIMATE, `-ULT` marked, SF stated, located.
5. **Figures** — the section's computed plot(s) (OR-7), where the module has one.

The template is finalised — possibly amended — when the first analysis-body
section goes through OR-8; after that it is fixed and a guard test holds every
section to it.

---

## 3. Acceptance gates

| Gate | Statement |
|---|---|
| **G-OR-1** | The report builds from `examples/ga6_normal.project.json` in CI without error, and the `.tex` compiles to PDF where a TeX engine is present. Extends the existing report build test rather than duplicating it. |
| **G-OR-2** | Every result-producing step in `sloads.workflow.oracle_steps()` has exactly one analysis section, and every analysis section maps to a step. Guard test (the G2 inheritance, OR-2). |
| **G-OR-3** | Every load table value equals the corresponding `ModuleResult` value × its case's SF — asserted through the content model, never by matching LaTeX strings (OR-6). |
| **G-OR-4** | Every load carries `-ULT` and a stated SF; no non-load quantity is scaled or marked. Reuses the summary report's marking checks (OR-5). |
| **G-OR-5** | Two builds of the same project at the same unit selection are byte-identical (OR-5). **Amended 2026-08-30 (§7, OR-20):** the unit selection is a `ReportSpec` field, so the statement is *two builds of the same project **and the same report spec** are byte-identical* — the spec plus the project is the complete recipe. **Extended 2026-08-30 (§8, OR-26):** G-OR-16 carries the same statement to every file of the issue package, not the `.tex` alone. |
| **G-OR-6** | The report contains no concept-mode or sloads-only content: building from a project with concept fields populated yields the same oracle-scope document as the same project with them absent. Guard test — this is the scope rule made structural. |
| **G-OR-7** | A half-filled project yields a complete document with `absent_reason` sections, never a traceback and never a silently missing section (OR-5, absence-is-content). |
| **G-OR-8** | Each agreed section's SHALL list in `ORACLE_REPORT.md` (OR-9) has a corresponding assertion in the report tests — an agreement without a guard is prose, not a gate. Checked at each section's closure. |

---

## 4. Closure tier and delivery

**Tier L** — a new capability, a note-32 scope amendment, and a new standard
doc. Design note agreed first (this note); `theory_sources.md` is cited via the
per-section method citations rather than gaining new equations (the report adds
no physics).

**Milestone 0.8.2, one backlog row, solo profile.** The whole report is **one
backlog item** pointing at this note — **issue #151**, the row's owning issue —
worked on `dev/v0.8.2`. **#152 is this note's design-note PR** (`note/44-slug`,
merged at AGREED per `DEVELOPMENT_PROCESS.md` §5), **not an issue** — the two
numbers share a series on GitHub, so cite #151 for the work and #152 only for
the agreement that authorised it. The row is owned by #151, which carries the
band, tier, tag and milestone. Issues are not
opened per section (`DEVELOPMENT_PROCESS.md` §0: the backlog is the record;
OR-9's accruing standard doc is the per-section register). Delivery follows
OR-8 as **one commit per agreed iteration** — ordinary work commits, keeping
the step-per-commit `git log` record — with a single `solo_close.sh` closure
(fragments, history entry, row removal) when the final section is agreed.
0.8.2 slots ahead of 0.9.0 (band B2, main-GUI development) deliberately: this
report is B2's declared starting point.

| Commit | Contents |
|---|---|
| 1 | `oracle_content.py` skeleton + section derivation + the oracle_app report page + `ORACLE_REPORT.md` created + gates G-OR-1/2/5/6/7. **Amended 2026-08-30 (§7):** also `ReportSpec` + `REPORT_SCHEMA_VERSION` + the `io` load/save/fingerprint owners (OR-17, OR-21), `examples/ga6_normal.report.json`, and gates G-OR-10 … G-OR-13. **Amended 2026-08-30 (§8):** also the issue-package builder + `MANIFEST.txt` + the `data/` emitters (OR-22, OR-23) and gates G-OR-14 … G-OR-17 |
| 2 | Front matter (title, §1–§3) — the register-setting iteration |
| 3… | Analysis-body sections, one OR-8 iteration each, in workflow order; G-OR-3/4 land with the first results section |
| final | Governing summary, methods & limitations, input echo appendix, note-32 cross-link, tier-L closure |

---

## 5. Answers to the open questions (OR-10 … OR-12)

*Resolved by the owner 2026-08-29, in session. Decisions, on the same footing
as OR-1 … OR-9; §3's gates apply to them.*

### OR-10 — CI builds the `.tex`; the PDF compile is a local check

`ci.yml` carries no TeX engine today. G-OR-1's CI leg therefore asserts the
**`.tex` build** (the report builds from the example without error and the
source renders); compiling to PDF is checked **locally at each OR-8 iteration**
— the rendered sample PDF is what the owner approves, so every agreed section
has in fact compiled. This matches the summary report's existing practice: the
`.tex` is the primary artifact and is self-contained for any standard engine
(`tectonic`, `latexmk`, `pdflatex` — `SUMMARY_REPORT.md` §2). Adding a
`tectonic` compile job to CI is a candidate 0.9.0 improvement, not a
prerequisite here.

**Amended 2026-08-30 (§8, OR-22/OR-26):** the CI leg builds the **issue package** and asserts its manifest (G-OR-14), the `.tex` being one file of it; and self-containment is read at package level (OR-26), the `.tex` reading `data/` at compile time.

### OR-11 — Both examples build the report in CI

`examples/baron_58.project.json` already exists (note 34, UG-9). G-OR-1 runs
over **both** `ga6_normal` and `baron_58`: the single is the Appendix A oracle
case; the twin exercises the engine-mount and one-engine-out sections as
*present* rather than `absent_reason`, and (per UG-12) is the SI-channel case,
so the two builds together cover both unit selections of G-OR-5.

**Amended 2026-08-30 (owner):** the *machine* covers the twin every section —
G-OR-1 has built both packages on every push since iteration 1 — but the
**owner's read of the Baron report is one pass at the end of report
development**, not a second review per section. The GA6 is the review vehicle
throughout (it is the Appendix A oracle case, so a wrong number there is a
*known*-wrong number), and reviewing both per section doubles the reading for a
second opinion on the same renderer.

What that end pass is for is the half CI cannot assert: that the twin's report
*reads* correctly where it differs from the oracle case — the `absent_reason`
wording on sections the GA6 has and it does not (and the reverse), the DERIVED
planform provenance where the GA6 now says entered (Appendix B is not bundled,
so the Baron has no printed polylines), the SI channel's number formatting under
UG-12, and the engine-mount and one-engine-out sections appearing as *present*.
The deferral is safe because those are stated by guards rather than by eye —
`test_a_tail_table_states_where_its_planform_came_from` asserts the provenance
label in both directions, and the package manifest and determinism gates assert
the rest — so what is deferred is judgement, not detection. A GA6-shaped
assumption reaching the renderer fails CI on the twin the same day it lands.

### OR-12 — Iteration order is workflow order

The default stands: analysis-body sections are developed in
`oracle_steps()` order, matching the section numbering, so each iteration's
sample values are values the already-agreed sections produced (the note 34
UG-10 lesson — writing a downstream section first means inventing numbers the
tool later contradicts).

---

## 6. Development constraints for milestone 0.8.2 (OR-13 … OR-15)

*Owner ruling 2026-08-30, in session (`CLAUDE.md` rule 1's working-alone path).
Milestone-scoped: these constraints govern `dev/v0.8.2` only, and lapse at the
0.8.2 cut. They are decisions on the same footing as OR-1 … OR-12; §3's gate
discipline applies to them via G-OR-9.*

The report is a **view** of an analysis that is already oracle-locked and
already agreed (OR-6, OR-7). Building a view is therefore not an occasion to
adjust what is being viewed. These three rules make that structural rather than
a matter of restraint.

### OR-13 — The frozen set: solver and existing oracle GUI, additive-only

For the duration of 0.8.2 the following are **frozen** — no edit, including
refactors, renames, formatting and type-annotation churn:

| Frozen | Why |
|---|---|
| `sloads/modules/**` | The solver. Appendix A holds it to ±0.1 %, but an oracle test only catches a change that moves a printed number; the freeze also catches the ones that do not. |
| `oracle_app/Oracle.py`, `form.py`, `labels.py`, `results.py`, `__init__.py` | Every existing oracle GUI page and its input/output behaviour. The C210-15 fidelity ruling makes these the consumed-value contract the report reads from. |

**Permitted, and only these:**

1. **New files** — `sloads/report/oracle_content.py`, the new `oracle_app`
   report page, `docs/10_standard/ORACLE_REPORT.md`, new tests. Additive work in
   `oracle_app` is the milestone's own first commit (OR-3) and is not a change
   to the frozen set.
2. **The one OR-3 amendment** to `oracle_app/Oracle.py` — note 32's
   "deliberately does not have" statement, updated to record the amendment.
   **Widened 2026-08-30 (§7, OR-16):** the amendment is the docstring **and** the
   report page's registration in the page dict / `st.navigation`, since a derived
   page set has no other way to carry a non-step page. One commit, one manifest
   update, the authority named in the message.
3. **A blocking-defect fix admitted under OR-15**, which carries its issue
   number and updates the manifest in the same commit.

Shared code outside the frozen set (`sloads/report/*.py`, `sloads/workflow.py`)
stays open under the ordinary rules — but a change there that alters the
**summary report's** output is a behaviour change to a delivered capability
(tier M), not report plumbing, and is ticketed like any other.

### OR-14 — A defect found in frozen code is filed, not fixed

Reading the solver and the oracle GUI closely is the point of writing this
report, so it will surface defects. Every one is **written up as a GitHub issue
with a body** the session it is found (`CLAUDE.md` rule 5), and left in place.
Diagnosing a suspected defect far enough to file it accurately is expected; the
line is the edit, not the investigation. The report renders what the frozen code
actually produces — a document that quietly papers over a defect is worse than
one that exposes it, and the issue is the exposure.

This does not weaken `CLAUDE.md` rule 4 (generalize on first find): the sweep of
the defect class is part of the *ticketed* fix, wherever that fix lands.

### OR-15 — Triage of what is found

| Finding | Milestone |
|---|---|
| **Prevents progress** — the report cannot be built, or cannot be built truthfully, without the fix | **0.8.2**, admitted by explicit owner decision, with an issue number and a manifest update in the fixing commit |
| Concerns **oracle GUI output** — a value, label, unit, frame or presentation the report consumes — but the report can be written correctly around it | **0.8.3** |
| Anything else — solver fidelity, main GUI, concept mode, hygiene | **0.9.0** |

"Prevents progress" is deliberately narrow: a wrong number the report can state
accurately (because the report states what the analysis produced) does **not**
prevent progress — it is an 0.8.3 or 0.9.0 ticket and, where the error is
material, a `Methods and limitations` entry in the back matter until it is
fixed.

### G-OR-9 — the freeze is a test, not a promise

`tests/test_frozen_set.py` holds a SHA-256 manifest of every frozen path and
fails on any change to one. Updating the manifest is the deliberate act that
records an OR-13 exception: the commit that changes a frozen file updates the
manifest beside it and names its authority (OR-13 item 2, or an OR-15 issue
number) in the commit message. `CLAUDE.md` rule 3 — a cross-cutting convention
gets a code owner and a drift guard, never a prose rule alone.

---

## 7. The report file and the report page (OR-16 … OR-21)

*Owner rulings 2026-08-30, in session (`CLAUDE.md` rule 1's working-alone path),
settling the shape of the OR-3 page and the artifact it edits before iteration 1
is built. Decisions on the same footing as OR-1 … OR-15; §3's gate discipline
applies via G-OR-10 … G-OR-13.*

### OR-16 — The trigger page, and what OR-13 admits

The OR-3 page is a **new file, `oracle_app/report.py`**, appended after the
derived analysis pages (title *Report*, url_path `report`). Its blocks, top to
bottom: report file (load / download / new); document identity; abstract;
signatures; distribution and marking; content selection; preflight; generate and
download.

A derived page set has no way to carry a non-step page except through the entry
point, so registering it necessarily touches a frozen file. **OR-13 item 2 is
widened accordingly**: the admitted OR-3 amendment to `oracle_app/Oracle.py` is
the docstring statement **and** the page's registration in the page dict /
`st.navigation` — one commit, one manifest update, the authority named in the
message. Nothing else in that file moves.

### OR-17 — Report metadata is its own artifact, not a `Project` slice

A report is a **document instance**, not a property of the airplane: one project
yields many issues (different customers, revisions, scope selections). Metadata
therefore lives in a **new `ReportSpec` dataclass** with its own
`REPORT_SCHEMA_VERSION`, serialised to a **`report.json`** file mapped in
`sloads/io.py` (`load_report`, `save_report`) — **amended 2026-08-30 (§9,
OR-28): that file lives inside the issue package directory, not beside
`<stem>.project.json`** — — which stays the only dataclass↔JSON mapping. **`Project` and
`SCHEMA_VERSION` are not touched**, so note 32's OG-13/G6 promise (a project
saved by either GUI opens in the other unchanged) is untouched, and no migration
is owed.

The page holds one active spec at a time in session state; the user swaps files
to switch issues. The file widget is **page-local**, deliberately not in the
shared `app_shell` sidebar: that sidebar is shared with `app/`, and the report
file belongs to the report page. Editing the spec marks the session dirty by the
same rule the project file uses.

The artifact is also what makes a headless build expressible later
(`sloads oracle-report <project> --report <spec>`). Not iteration 1; the door is
open rather than walled.

### OR-18 — Title block, and DRAFT until signed off

`ReportSpec` carries: title, report number, revision/issue, issue date, issuing
organisation, customer/programme, abstract, revision history (rows of date /
revision / description / by), distribution statement, classification marking
(rendered in every page footer), and three signature rows — **prepared, checked,
approved**, each name / role / date.

**Any empty signature name makes the document a draft**: a DRAFT watermark and a
footer marking, still fully buildable and downloadable. All three names present
clears it. The document never silently presents itself as approved, and the page
never blocks the build to force the point.

### OR-19 — Section selection is stated exclusion, never omission

The user selects which analysis sections an issue carries. **Every derived
section always exists** — G-OR-2 stays literally true. A deselected section
renders its heading and *"not included in this issue — excluded by user
selection at report generation"*, and the title page lists the exclusions: this
is `SUMMARY_REPORT.md` §3.4's filtered-export rule applied at section level, and
an analyst never receives a reduced document without being told.

Selection is limited to **analysis-body sections and the Appendix A input echo**.
Front matter, the governing-loads summary and methods & limitations are never
selectable — they carry the load basis and traceability statements. Exclusions
are stored **by workflow step key**, never by section number, which moves as
steps are added.

**Absent is not excluded.** A step whose inputs are missing renders its
`absent_reason` (OR-5) whether or not it was selected; the two states are
distinct in the preflight table and in the document.

### OR-20 — The document's unit system is a `ReportSpec` field

`spec.unit_system` governs the document, so a report file plus a project is a
complete, reproducible recipe. The sidebar toggle continues to govern what the
**analysis pages display**; the report page carries its own control bound to the
spec field and states the split in a caption.

That is a second owner of a selection the sidebar otherwise owns alone, so it is
made structural rather than remembered (`CLAUDE.md` rule 3): **G-OR-12**. And
**G-OR-5 is reworded** to fold the qualifier in — *two builds of the same project
and the same report spec are byte-identical*.

### OR-21 — Provenance: identity, anchors, fingerprint — stamp and warn

The spec records what airplane definition it was written for, and the document
prints it. Two questions are answered by two different things, and the stamp
carries both:

| Question | Answered by |
|---|---|
| *Is this the same airplane?* | **Human identity** — project name, aircraft designation, and anchor values (MTOW, wing area, design speeds). This is what a reader of the PDF actually checks; a hex string tells them nothing. |
| *Has the definition changed since this issue was signed?* | **The fingerprint** — nothing else answers it cheaply. |

The fingerprint is a SHA-256 over a **canonical projection of the inputs the
oracle report consumes** — the slices behind `oracle_steps()`, sorted keys,
round-trip float repr — **not** over the project file. Hashing the whole file
would fire on a concept-mode field, an sloads-only field or a re-save with
different key ordering: a warning about a document none of them can affect, and a
warning that fires on noise is ignored on signal. The scope boundary is asserted,
not described: **G-OR-13**.

The stamp carries its own **`fingerprint_version`**. When a later milestone adds a
field to an oracle-consumed slice, every existing report's fingerprint goes stale;
on a version mismatch the page states *"cannot compare — stamped by an earlier
fingerprint definition"* rather than crying wolf, and the human anchors still
compare.

On load against a different project the page **warns and builds anyway** — a
banner naming both sides, and a note in the document's identity block. It never
refuses: a project is legitimately revised under the same report number, and
refusing would obstruct the normal case to police the rare one.

The fingerprint is **not a signature** — there is no key, so it detects accident,
not tampering. And it is not the record of what was analysed: the **Appendix A
input echo is** the definitive record; the fingerprint is the fast comparator that
says *go read Appendix A, something moved*.

### Gates added by this section

| Gate | Statement |
|---|---|
| **G-OR-10** | No `ReportSpec` field reaches any `ModuleResult` or any load value — document metadata cannot move a number. |
| **G-OR-11** | `ReportSpec` round-trips through `save_report`/`load_report` stably; a missing or unreadable report file yields a default unsigned draft, never a traceback. |
| **G-OR-12** | The report build path reads `spec.unit_system` and never `active_system()` — the document's unit owner asserted, not conventional. |
| **G-OR-13** | Mutating any oracle-consumed field changes the fingerprint; mutating any field outside the oracle scope does not (the OR-21 scope boundary, the same structural move as G-OR-6). |

---

## 8. The issue package (OR-22 … OR-27)

*Owner rulings 2026-08-30, in session, settling what the report page's build
button actually produces. A report issue is a **package**, not a file: the
document plus the data behind every table and plot plus the definition it was
built from, in one directory that can be archived, signed and re-opened years
later. Decisions on the same footing as OR-1 … OR-21; gates G-OR-14 … G-OR-17.*

### OR-22 — Build produces a directory, not a download

The page's build action writes an **issue package** — a real directory on the
local filesystem, since the oracle GUI is a locally-run tool (`sloads-oracle`)
and the user's machine is the server. The page carries an output-root control;
the directory name is derived from the report number and revision
(`LR-0142_RevB/`), never from the clock.

```
LR-0142_RevB/
  report.tex          the document (OR-4)
  report.json         the spec the page edits (OR-28; never machine-written)
  build.json          the as-built stamp: fingerprint, timestamp, generator (OR-30)
  project.json        a copy of the airplane definition it was built from
  MANIFEST.txt        a full SUMMARY_REPORT.md §4.7 manifest (OR-35)
  data/<step_key>.csv one file per table or plot the document draws (OR-23)
  report.pdf          present only after a local compile (OR-26)
```

`app/`'s export page delivers a zip through the browser instead
(`export_report.py`, "Download all"); that is the right shape for a page that
may be served remotely, and the wrong shape here. A zip of the same tree is a
candidate convenience later, built from the same builder — not iteration 1.

### OR-23 — The shipped data is the document's source, not a copy of it

Tables are generated `.tex` fragments the document `\input`s; plots are
pgfplots reading `data/<step_key>.csv` at compile time. **The document therefore
cannot disagree with the shipped data, because it is reading it** — the
architecture is the guarantee, so no drift-guard between two renderings is owed
(`CLAUDE.md` rule 3 is satisfied by removing the duplication rather than
policing it). It also makes OR-6 auditable from outside: a reviewer diffs the
CSV against the analysis page instead of trusting the sentence.

Files are named by **workflow step key**, never by section number, for OR-19's
reason. Each carries a comment header stating the **units string including the
`-ULT` marker, the safety factor and its basis, the step key, and the
fingerprint** — a data file lifted out of the folder and mailed onward is still
self-describing, which is what `SUMMARY_REPORT.md` §3.1 requires of every
load-bearing number. **G-OR-15**; no orphans in either direction, **G-OR-17**.

### OR-24 — The package's `report.json` is a snapshot; the working spec stays put

**Superseded 2026-08-30 by OR-28 (§9): the package directory is the spec's home,
and the as-built stamp moved to `build.json` (OR-30). The reasoning below is kept
because it is what OR-28 had to answer, not because it still governs.**

OR-17's placement stands: the **working** spec lives at `<stem>.report.json`
beside the project, and is what the page loads and edits. The build **copies it
into the package**, stamped with the OR-21 fingerprint and the build timestamp
supplied by the caller. The two copies have different jobs — one is the editable
recipe for the next issue, the other is the immutable record of this one — and
loading a package's `report.json` back into the page is reading history, not
resuming work.

`project.json` is copied in for the same reason: anyone holding the folder can
rebuild the document without hunting for the airplane file, and the fingerprint
has its subject present to compare against rather than merely named.

### OR-25 — Rebuild clobbers the revision; a new revision is a new directory

Building again into the same report number and revision **overwrites in place,
silently** — it is a build product, and the edit-build-read loop must not carry
friction. Bumping the revision in the spec produces a **new directory beside**
the old one, so an issued revision is never destroyed by continued work. The
package is disposable; the revision history in the spec (OR-18) is not.

### OR-26 — Self-containment is a property of the package

**Superseded by an amendment to the standard itself, 2026-08-30 (owner).** This
section first recorded a *reading* of `SUMMARY_REPORT.md` §2 — that a CSV is not
an image, so OR-23 was already permitted. A rule that says one thing and means
another leaves the next person to re-derive the reading from a design note, which
is the prose-rule-without-an-owner failure `CLAUDE.md` rule 3 exists to prevent.
So §2 was amended instead, tier M, and OR-26 is now a **citation** of it:

- The **image prohibition is unchanged and absolute** — figures are pgfplots/TikZ
  source, never `\includegraphics`. Every property that rule protects
  (deterministic, diffable, unit-testable as text, vector in the document's own
  fonts, no non-TeX toolchain) is untouched by reading a text data file.
- A new **§2 *Data reference*** clause permits a report **delivered as a package**
  to read plain-text data from inside it, on four conditions the issue package
  already meets: the file is in the manifest (G-OR-14), the path is relative and
  stays inside the package root, the file is self-describing to §3.1 (G-OR-15),
  and determinism holds for the whole package (G-OR-16).
- A report **delivered as a standalone `.tex`** — which `app/`'s summary report
  still is, via its own download button — **SHALL NOT** reference any external
  file, and now has the guard that says so
  (`test_report_latex.py::test_the_standalone_tex_references_no_external_file`).

The amendment is not a liberty taken for this milestone: §1.5, §4.7 and §5 already
require the report to travel with companion data files and to point the reader at
them. Reading them makes that reference **mechanical instead of editorial**, so the
document cannot misquote its own companion — §4.7's intent, finally with teeth.

The PDF (OR-10, local) is **compiled out of tree** and only the PDF copied back:
no `.aux`, `.log`, `.out` or engine cache ever enters the package, or the
determinism gate becomes a fight with the toolchain. **G-OR-14**.

Determinism now applies to the whole tree: **G-OR-16** extends G-OR-5 from the
`.tex` to every file in the package. CI's OR-10 leg builds the **package** and
asserts its manifest, not the `.tex` alone.

### OR-27 — The button is *Build*; DRAFT stays the unsigned state

OR-18 already gives DRAFT a meaning — the document is unsigned. The build action
is therefore called **Build issue package**, and it fires identically for signed
and unsigned specs: a signed report is built by the same button, and an unsigned
one is built with the watermark. Naming the button *Draft* would make the two
meanings collide on one page.

### Gates added by this section

| Gate | Statement |
|---|---|
| **G-OR-14** | The package contains exactly the files its `MANIFEST.txt` lists, with matching hashes — no engine aux files, no strays, nothing listed but absent. **Widened 2026-08-30 (§9, OR-35): the manifest also meets `SUMMARY_REPORT.md` §4.7.** |
| **G-OR-15** | Every shipped data file's header states its units string (with the `-ULT` marker), safety factor and basis, step key and fingerprint (`SUMMARY_REPORT.md` §3.1 applied to detached files). |
| **G-OR-16** | Two builds of the same project and the same report spec produce byte-identical **packages**, file for file — G-OR-5 extended from the document to the tree. |
| **G-OR-17** | Every file in `data/` is referenced by the `.tex`, and every table or plot in the `.tex` is backed by a file in `data/` — no orphans in either direction. |

---

## 9. Iteration 1 — amendments settled in planning (OR-28 … OR-37)

*Owner rulings 2026-08-30, in session, settling iteration 1 before it is built.
Several of these **override** §7 and §8 as written; where they conflict, §9 wins
and the superseded text says so. Decisions on the same footing as OR-1 … OR-27.*

### OR-28 — The package directory is the spec's home

**Supersedes OR-24, and amends OR-17 and OR-22.** The working `report.json`
lives **inside the package directory** and is what the page loads and edits.
There is no `<stem>.report.json` beside the project.

OR-24 split the spec in two — an editable recipe beside the project, an immutable
snapshot in the package — and gave them different jobs. In practice the split
costs more than it buys: a user with six issues of one report keeps six spec
files in the project folder with no directory to disambiguate them, and every
build has to answer *which* spec it came from. One issue, one directory, holding
everything about that issue, is the model the analyst already has in their head.

A real consequence, and a gain: `MANIFEST.txt` must match the tree (G-OR-14), and
`report.json` is now in the tree. A stale manifest hash for `report.json`
therefore means **the spec has been edited since the last build** — a
freshness signal that would otherwise have had to be invented, and that the
preflight block states rather than computing separately.

### OR-29 — Report root, and how a package is opened

Packages live under **`<project dir>/reports/`** by default, overridable by a
path field on the page. The page lists the report directories it finds there in a
selectbox, plus *New*.

Streamlit has no directory picker and the file uploader returns files, not
folders — so discovery plus a path override is not a compromise, it is the only
mechanism available to a locally-run app. It is also what makes the page testable
without a browser: a test points the root at `tmp_path`.

### OR-30 — The as-built stamp is `build.json`; `report.json` is never machine-written

**Amends OR-24's stamping.** The fingerprint, the caller-supplied build timestamp
and the generator version go in a **`build.json`** the builder owns. `report.json`
holds only what the user typed.

With OR-28 putting one `report.json` in the tree, stamping it in place would mean
the build writes the file the user edits — and G-OR-16 (byte-identical rebuilds)
would then need a by-name exclusion list for the stamped fields, maintained
forever as the spec grows. Separating the two files removes the carve-out instead
of maintaining it, and keeps `report.json` diffable as a record of human intent.

### OR-31 — Iteration 1 is the front matter, and the abstract is the spec's

Iteration 1 delivers: cover/title page, **abstract** (OR-18's free text), table of
contents, list of figures, list of tables, and **section 1 Introduction**.

The **governing-loads summary is not this iteration.** It is computed from
delivered loads and cannot honestly exist before the sections it summarises; OR-19
already rules it never-selectable for that reason. Naming both "the summary" is
what made this worth stating.

### OR-32 — Not-yet-built is a third state, distinct from excluded and absent

A derived analysis section that the generator does not yet build renders its
heading and *"not yet implemented in this revision of the report generator"*.

This is a **third state**, and the document and the preflight table both keep the
three apart:

| State | Means | Ruled by |
|---|---|---|
| **Excluded** | a user deselected it for this issue | OR-19 |
| **Absent** | the inputs it needs are missing | OR-5 |
| **Not yet implemented** | the tool cannot produce it yet | OR-32 |

Collapsing the third into either of the others would be a false statement about
whose decision produced the gap — the reader would be told a person chose to omit
a section, or that their data was incomplete, when neither is true. It also lets
**G-OR-2 hold from the first commit** rather than waiting for the last section:
every derived step has a section throughout, and the section says what it is.

### OR-33 — `REPORT_SCHEMA_VERSION` stays at 1 for the milestone

Sections will add spec fields as they are agreed. The version stays **1** until
the 0.8.2 cut: no report file has shipped, so there is nothing to migrate, and
bumping a version against no readership teaches the number to mean nothing. It
starts carrying information at the cut.

### OR-34 — The empty lists still render

`\listoffigures` and `\listoftables` are emitted from iteration 1, empty. A
document that silently drops its own front matter while incomplete is harder to
trust than one showing an empty list — and the empty list is itself accurate.

### OR-35 — `MANIFEST.txt` is a full `SUMMARY_REPORT.md` §4.7 manifest

**Widens OR-22 and G-OR-14.** OR-22 described `MANIFEST.txt` as every file with
its SHA-256. That is not enough: the §2 *Data reference* clause (OR-26) conditions
the packaged-report permission on the package "carrying a manifest (**§4.7**)",
so §4.7 binds — per-file contents, units, sign and axis conventions and the
section that summarises it, under an opening statement of the package's unit
system, with section references from the numbering owner and never a literal
`§N`, exhaustive **in both directions**.

Both of §4.7's SHALLs were written after real defects (CR-C-1, an artifact
shipped with no row; CR-C-3, a basis cell wrong through two reviews), so this is
not ceremony. The shape is already built: `content._section_manifest` renders
**File / Contents / Units / Conventions / Summarised in**, and
`tests/test_bundle_manifest.py` holds it in both directions. The issue package
reuses that shape rather than inventing a lighter one.

### OR-36 — The PDF compile is a later iteration

`sloads/export/pdf.py`'s `compile_pdf` takes the LaTeX **source string** and
compiles it in a temporary directory — which is exactly OR-26's out-of-tree
requirement, and exactly why it cannot compile this document: a `.tex` that
`\input`s `data/*.tex` and reads `data/*.csv` will not find them there.

Extending it to compile a package tree is its own change with its own gate, and
it is not on iteration 1's critical path: CI asserts the `.tex` build (OR-10), and
front matter is reviewable as source. G-OR-1's PDF leg lands with that change.

### OR-37 — No example report file

The note's §4 commit-1 row called for `examples/ga6_normal.report.json`. OR-28
leaves nowhere beside the project for it to live, and an example *package
directory* checked into `examples/` would be a build product in source control.
Tests construct a spec with `default_spec()` into `tmp_path` instead. The headless
build path (OR-17's `sloads oracle-report`) is unaffected — it will take a
package directory.

### Gates

| Gate | Statement |
|---|---|
| **G-OR-14** | **Widened by OR-35:** the package contains exactly the files `MANIFEST.txt` lists, with matching hashes, and the manifest meets `SUMMARY_REPORT.md` §4.7 — the five columns, the opening unit-system statement, section references from the numbering owner, exhaustive both ways. |
| **G-OR-18** | The three gap states (OR-32) are distinguishable in the rendered document and in the page's preflight: no state's wording can be produced by another's cause. |
| **G-OR-19** | `report.json` is byte-identical before and after a build — the builder never writes the user's spec (OR-30). |

**Note on vacuous gates.** G-OR-15 (data-file headers) and G-OR-17 (no orphans)
are written in iteration 1 but have no `data/` files to act on until the first
analysis section. Their tests say so in the docstring: a gate that passes because
there is nothing to check must not read as a gate that passed.

## 10. Iteration 2 — Section 2, Loads Configuration (OR-38 … OR-44)

*Agreed with the owner in session, 2026-08-30, during the live GUI review. Content
spec per OR-8; SHALL list in `ORACLE_REPORT.md` §3.3; decisions on the same
footing as OR-1 … OR-37.*

| # | Decision | Amends |
|---|---|---|
| **OR-38** | **Section 2 groups four steps as subsections** — geometry, weight and mass properties, structural design speeds, flight envelope — under one numbered section, "Loads Configuration". Subsections rather than a flat merge, so every step keeps exactly one home and **G-OR-2 is unchanged**. Grouping is declared as data (`SECTION_GROUPS`), and a group's members must be contiguous in workflow order. | OR-2 (extends) |
| **OR-39** | **The document owns its own section titles** (`DOCUMENT_TITLES`). A heading is never `WorkflowStep.title`: the workflow is our machinery, the reader of the PDF has no concept of it, and a nav rename must not retitle a signed report. Both directions guarded. | new |
| **OR-40** | **The V-n envelope is the polyline through FLTLOADS' produced design points**, one figure per loading/altitude block. `vn_diagram.build_vn_diagram` is not used: its own docstring calls it an approximate Structural-Speeds sanity plot whose stall boundary assumes constant CLmax. On the reference GA wing it predicts n = 3.51 at the STALL +N corner where the analysis computes 3.80 — **8% low**, because the real boundary follows CL rising 1.395 → 1.512 with α and the compressibility correction. Plotting it would put the report's own design points visibly off their own boundary. | OR-6 (applies) |
| **OR-41** | **The SELECT case list belongs to the load-case section**, not to 2.4. Section 2.4 carries the figures and the corner load factors; the case table is the next iteration. Same source, different projection — no number is tabulated twice. | new |
| **OR-42** | **Tables and plots render inline for now.** OR-23's `data/*.csv` externalisation becomes its own iteration, with **G-OR-15 and G-OR-17 landing there**; they stay vacuous until it. Deferral, not reversal: the manifest stays consistent because no `data/` files exist yet. | OR-23 (defers) |
| **OR-43** | **`build_oracle_document` reduces its project through `reduce_to_oracle_inputs` first.** The document is a function of the oracle projection, hashed by the same reducer the fingerprint uses — one guarantee, one owner. Found by G-OR-6 failing: section 2 quotes each module's certification basis, and on a concept project the speeds module takes the Part 25 Mach-margin route and says so, so a concept-only field reached the printed page through a module note. | OR-21, G-OR-6 (implements) |
| **OR-44** | **Section 2 states no load in force or moment units.** Nothing in it is scaled to ultimate or marked `-ULT`, and no table states a safety factor — but every value still passes through the `render` ultimate boundary rather than being hand-formatted, so the section never decides what a load is. **G-OR-4 holds by construction.** **Amended by the owner, 2026-08-30:** the first draft said "section 2 carries no loads" and put a note under every table saying geometry, mass, speeds and load factors *are not loads*. That is wrong — **n is a limit load factor, so a load factor is a load** — and the note was removed outright rather than reworded. What section 2 may state about them is that they are **LIMIT**, which the V-n captions and the corner table do at point of use. | OR-5, G-OR-4 |

### Section 2.1 and 2.2 extended (owner, in session 2026-08-30)

**OR-45 — 2.1 states every surface, one table each.** Wing planform, horizontal
tail and elevator, vertical tail and rudder, aileron, flap, and one table per
trim tab; each with its area, planform figures, tail arm stations where it has
them, and its control deflections.

**OR-46 — the report may echo a project input, and must label it.** These are the
first values section 2 reads from the project rather than from a `ModuleResult`:
no module returns a control-surface area or a throw. This does not weaken OR-6,
which forbids *re-deriving* a value and not *reporting* one, but the distinction
is the reader's to see, so 2.1 states once that the empennage and control-surface
values are the configuration as entered. The field lists are declared as data so
a renamed input fails the suite instead of silently emptying a row, and G-OR-3's
guard was widened from "every number came from a `ModuleResult`" to "every number
came from a result **or** from the project as entered, and none is invented".

**OR-47 — 2.2 states the weight and CG cases**: name, role, weight, Xcg, Zcg and
analysis, with a note explaining what role and analysis govern. `CgCase.analyses`
is a `set` by design (G-3), so the printed order is declared rather than taken
from iteration — set order is not a document property, and resting the
determinism gates on it is the kind of defect that passes locally and fails on
another interpreter.

### Findings recorded, not fixed

- **A condition holding no loads still carries `safety_factor = 1.5`** — the
  geometry, mass-properties and design-speed conditions. No value is affected
  (the boundary scales by units and quantity, not by the stamp) but the claim is
  false: a wing span has no safety factor.

  **Not an OR-14 finding, on inspection.** The first reading of this blamed the
  frozen modules. It is not theirs: `1.5` is the dataclass default on
  `ConditionResult.safety_factor` (`sloads/models/results.py`) and
  `safety_factors.GoverningTable.stamp` overwrites it from `registry`. None of
  those is in the frozen set, so the fix is ordinary work at its own owner rather
  than something the freeze defers.

  `flight_envelope` is **not** affected and was wrongly listed at first: its
  conditions carry M(W+F), LZW, LT and DX in lb and lb-in, so a factor is a true
  statement about them.

  **Owner's ruling, 2026-08-30:** non-loads do not have safety factors. A
  condition with no load value **SHALL** carry `None`, rendered "N/A", and a
  mixed condition keeps its factor while showing N/A against its non-load rows.
  Fixed at the data model, after section 2 closes — filed as **#154** with a body,
  backlog row below. Section 2 prints no safety factor at all, so nothing in the report
  states the false claim in the meantime.
- **The stall boundary is only sampled at its design points.** Drawing the true
  curve between them needs FLTLOADS to sample intermediate speeds, which is
  frozen-module work. Backlogged and **parked with the 8% number** that parks it
  (CLAUDE.md rule 6): below that, the polyline and the true boundary differ by
  less than the base method's own uncertainty at every plotted vertex, because
  the vertices are exact.

### #155 moved from OR-14 to OR-15 (owner, 2026-08-30)

**#155** — the modules describing WINGGEOM's geometry integral as a *strip
integrator* — was first recorded above as an OR-14 finding: filed, not fixed,
because `configuration.py` is frozen. The owner admitted it under **OR-15**
instead, on the reasoning that OR-14 defers defects the report merely *exposes*,
while this one the report's own correction *created*: the closed-form integration
landed in the same milestone and made the surrounding prose false in the same
commit. Leaving it would have shipped a report whose §2.1 reproduces, verbatim, a
description of a method the milestone removed.

Three frozen files carry the fix — `wing_geometry.py` (its module docstring still
taught the strip method its own `surface_properties` no longer uses),
`configuration.py` (the four sites #155 names, one of them the report-visible
note) and `airloads.py` (whose docstring credited its strips to WINGGEOM). The
sweep is CLAUDE.md rule 4: the same false statement was corrected everywhere it
appears, including `models/inputs.py`, three test headers, `PROGRAM_SPEC.md`,
`00_theory_sources.md` and `01_concept_loads_plan.md`. Statements about strips
that remain *true* — AIRLOADS' own span loop, the spanwise load stations,
`tail_geometry`, and every historical reference in the correction register — were
left standing.

Two consequences beyond the prose. The WINGGEOM table's `Integration elements`
row was renamed **`Load stations`** (key `integration_elements` → `load_stations`,
which nothing read): the value is the user's load-station count and had stopped
being an integration parameter. And the Appendix A **aileron oracle was tightened
from ±2 % to ±0.1 %** — it had been loosened only because the result depended on a
strip count the manual never tabulates, and closed-form integration reaches
0.037 %. No load number moves: the Imperial baseline drifts in the
`wing_geometry` and `configuration` channels only, and only in that row label and
that note.

### #153 moved from OR-14 to OR-15 (owner, 2026-08-30)

**#153** — the per-row delete removing the wrong row — was recorded above as an
OR-14 finding: a live defect in `oracle_app/form.py` that the report *exposed*
rather than caused, and therefore one the freeze defers. The owner lifted the
rule for it on 2026-08-30. The reasoning that carried it is the exposure, not the
defect: it was unreachable while every fixture held two surfaces, because
deleting row 2 of 2 removes the last row either way, and **this milestone made it
reachable** by giving `ga6_normal` seven surfaces. What it costs to leave is
silent data loss — the wrong surface goes, with no warning and no undo — on the
Geometry page the section 2 review is conducted from.

**The filed root cause was wrong, and the fix is not where it said.** The filing
blamed `_delete_row`'s `on_click` args binding a list detached by the next run,
so that `del rows[index]` never reached the project. Instrumented, the callback
receives the project's own attached list and the deletion lands every time. What
undid it was the *render* that followed: a row widget keys itself by row index,
Streamlit's retained state outvotes the `value=` seeded from the model, and every
row below the deleted one was renumbered onto its neighbour's state — so the tail
of the table was typed back over itself one place up and the row that visibly
disappeared was the last one. `_retire_renumbered_rows` retires the state of the
rows a deletion renumbers, and only those; a row above the deletion did not move
and keeps an edit typed in the same interaction as the click.

Swept as one class (CLAUDE.md rule 4) rather than fixed in the shape that showed
it. The flat grid is a single `st.data_editor` whose pending edits are an
index-keyed map, so it is renumbered by the same deletion — as are the cached
grid frames of a polyline sitting inside a renumbered row. Both tests now
snapshot whole rows instead of names: the shift moved *values* between rows, and
a name-only snapshot passes while the data has moved, which is how the flat
shape's test passed against a defect it shared. The contract is stated in
`GUI_design.md` beside the counter rule it belongs with.

`oracle_app/form.py` is hash-frozen by OR-13; the manifest hash is updated in the
same commit and the authority named in the commit message.

---

## 11. Iteration 3 — Section 3, Wing Loads (OR-48 … OR-58)

*Agreed with the owner in session, 2026-09-01. Section 3 is the first section that
states a load in force and moment units, so the rulings below are mostly about
which basis a number carries and where it comes from — not about layout.
Content spec per OR-8; SHALL list to `ORACLE_REPORT.md` §3.4; decisions on the
same footing as OR-1 … OR-47.*

| # | Decision | Amends |
|---|---|---|
| **OR-48** | **Section 3 is Wing Loads, built from the `wing_loads` step** (`AIRLOADS+WINGINER+NETLOADS`, primary module `net_loads`), in four subsections: 3.1 the wing input data the loads were run from, 3.2 the run register of cases and their FAR conditions, 3.3 the summary of load cases assessed, 3.4 the load distributions themselves. The per-station numbers go to an appendix, not into the body. | OR-8 (iteration) |
| **OR-49** | **Every load case in section 3 is stated ULTIMATE; input distributions are stated LIMIT; both carry the label.** The load-output contract is not relaxed for the report — a span loading at a target `CL` is an input to the analysis, not a delivered load, so it stays LIMIT and says so, while every shear, bending moment and torsion the section delivers is scaled at the render boundary and marked `-ULT` with its case's factor. **No number in section 3 is printed without a LIMIT or ULT label.** This is where G-OR-4 stops being vacuous: section 2 could hold by carrying no force or moment (OR-44); section 3 holds only by marking every one of them. | OR-44 (extends), G-OR-4 |
| **OR-50** | **The Appendix A input echo takes a reserved slot that renders as an OR-32 "not yet implemented" appendix page.** `APPENDICES` stops being empty. Appendix lettering is derived from position, so shipping Wing Loads into an empty tuple would print it as Appendix A today and silently move it to B when the echo lands — and a signed issue would then disagree with its own reissue. A reserved, stated slot makes **Wing Loads Appendix B from the first build**, and reuses the state machinery a section already has rather than inventing a second way to say "not yet". | OR-32 (applies), OR-35 |
| **OR-51** | **3.1 defines the loads reference axis, and for oracle loads the 25% chord *is* the LRA.** The suite computes about the 25% chord (AIRLOADS/WINGINER/NETLOADS, oracle-locked) and transfers to the surface's entered `ref_axis` at the render boundary; in sloads the LRA is user-defined, so 3.1 states which axis this project's loads are about rather than assuming. It carries **a table of the LRA point (X, Y, Z) against station** and **a planform figure with the LRA drawn on it**. Live in the report's own example: `ga6_normal` enters `ref_axis: 0.4`, so its wing torsion is delivered about the LRA 40% chord with the 25%-chord oracle value beside it — the report must not print one and call it the other. | `CONVENTIONS.md` §1, OR-6 |
| **OR-52** | **3.1's aero input data is the wing span loading and the airplane tail-off / tail-on data.** Span loading is `c*cl` — the span load, **not** the running load in lb/in — plotted at three wing lift coefficients, `CL = 0` (the basic distribution alone), `CL = 1.0`, and `CL = CLmax`, following the oracle's own three-case presentation. `CLmax` is `AeroCoeffSet.stall_cl`, an owner, never a typed constant. The three curves are obtained by **calling AIRLOADS' own `spanwise_distribution` with the target `CL` replaced**; the report never evaluates the additive/basic sum itself, which is what keeps OR-6 true of a figure with three curves the analysis did not run. Tail-off is the entered airplane-less-tail polynomial (`AeroCoeffSet.lift` / `moment`); tail-on is FLTLOADS' balanced per-case result (`wing_cl`, `lift_less_tail_lzw`, `balancing_tail_load_lt`) — the same values, one balanced and one not, which is what makes the tail load visible as a difference. | OR-6, OR-46 |
| **OR-53** | **The flaps-down set is stated absent, never quietly omitted.** The oracle prints two sets of span-load plots, clean and flaps-down. sloads can print the clean set only: `AeroCoefficientsInput.flaps_down` is optional and `ga6_normal` carries none, and AIRLOADS does not model the cosine fairing of the basic distribution across a deflected-flap lift discontinuity — its own documented limitation, since the Appendix A wing has no such discontinuity. So the flaps-down half renders as an ABSENT state with its reason, becoming present the moment a project carries the set, and **the missing span-load capability is filed rather than fixed here** (OR-14,
filed as #163). | OR-5, OR-14 |
| **OR-54** | **3.2 is the run register: what was run, at what condition, under which rule.** One row per selected wing case carrying the case ID, the condition, the FAR reference, the CG case and weight, the speed and altitude, and `Nz`/`Nx`. Every field of it already exists on `CaseRef` and the resolved case — this is a projection of case identity, not a new record of it, which is what OR-41 deferred to this iteration. 3.2 also states the coordinate and sign convention the section's loads are in, citing `CONVENTIONS.md` and naming the torsion axis of OR-51. | OR-41 (discharges) |
| **OR-55** | **SELECT's chosen subset *is* the critical set; 3.3 tabulates it and 3.4 plots all of it.** No second criticality rule is invented for the report — the wing cases the analysis ran are the wing cases the section shows. 3.3 gives root values per case; 3.4 gives one figure per quantity with every selected case on it: **vertical shear `Sz`, bending `Mxx`, torsion `Myy`, and drag shear `Sx`**. Chord bending `Mzz` is omitted. The figures show the **net** loads only, and state that shear, bending and torsion are **summed from tip to root** — a cumulative quantity read as a running one is the misreading the caption exists to prevent. | OR-6 |
| **OR-57** | **The register states where its case list came from.** The suite has two paths to a wing case set: the critical-load selection's own search of the V-n matrix, and a case list entered on the project, which **wins when it is present** (`wing_inertia.resolve_wing_cases`). A section that presents an entered list as the outcome of a search describes an analysis nobody ran, so 3.2 **SHALL** say which it is, **SHALL** state what the matrix it was searched from enumerates — every combination of configuration, weight/CG case, altitude and flight condition, not the twenty conditions a V-n diagram shows — and, where a list is entered, **SHALL** tabulate every condition the selection names with whether it was run. Found in the owner's review of iteration 3, 2026-09-03: the shipped prose claimed selection while `ga6_normal` runs an entered three of the selection's six. An entered list is legitimate and sometimes necessary — an accelerated-roll case carries an unbalanced rolling moment the selection cannot name — but it is the project's list, and the difference is the reader's to see. | OR-46 (extends), OR-54, OR-55 |
| **OR-58** | **The register states the sign convention of its load factors, and says when the set holds no negative-load-factor case.** `Nz` in a wing case is the **inertia** load factor — the negative of the airplane's flight load factor, since the inertia opposes the air load (`wing_inertia._resolve_case`: `Nz = −NZ`) — so a +3.8 g manoeuvre prints as −3.8. Every load factor in the table is a negative number whichever kind of condition it is, so *which* kind cannot be read off the page: 3.2 **SHALL** state the convention, and **SHALL** state, from the analysed set rather than by assertion, whether it contains a negative-load-factor condition. A set of positive-g cases alone does not envelop the wing — 23.333(c)'s negative manoeuvre and negative gust reverse the bending — and a section that leaves that to be worked out from a column of minus signs is not stating what it analysed. Found in the owner's review, 2026-09-03, by misreading exactly this table. The analysis half — that `ga6_normal` runs no negative case at all — is **#165**. | OR-54 (extends) |
| **OR-56** | **Appendix B is the per-station table of the selected wing cases, carrying the increment total load at each station — not the running load.** One row per station per case: the station coordinates, the strip's own increment `Fz` and `Fx`, and the cumulative `Sz`, `Sx`, `Mxx`, `Myy` with its axis named. ULTIMATE per OR-49. `net_loads.wing_load_rows` is already the canonical shape of that row, so the appendix is a view of an existing owner rather than a second layout of the same data. | OR-6, OR-49 |

### Gates added by this section

| Gate | Statement |
|---|---|
| **G-OR-20** | Every load value section 3 or Appendix B prints carries a LIMIT or an ULT label; a value with neither fails the suite. |
| **G-OR-21** | Every delivered shear, bending moment and torsion in section 3 is the ULTIMATE value — the LIMIT value times that case's own stated safety factor — and no input distribution is scaled. |
| **G-OR-22** | Wing Loads is Appendix B in a document whose input echo is not yet built, and the reserved slot renders its state rather than a blank page. |
| **G-OR-23** | Every torsion printed in section 3 names its reference axis, and the axis named is the project's entered LRA. |
| **G-OR-24** | The three span-load curves come from AIRLOADS' own distribution function at three target `CL`s, and the `CLmax` curve's `CL` is the aero set's `stall_cl`. |
| **G-OR-25** | A project with no flaps-down aero set renders the flaps-down figure as ABSENT with a reason, and prints no clean-configuration curve in its place. |
| **G-OR-26** | The cases 3.2, 3.3, 3.4 and Appendix B each state are the same set, in the same order — the selected wing cases, no more and no fewer. |
| **G-OR-27** | 3.2 states which path produced its case list, counts the V-n matrix the selection searched by every dimension it enumerates, and marks each named condition run or not run. |
| **G-OR-28** | 3.2 states what the sign of a load factor means, and says from the analysed set whether it holds a negative-load-factor condition. |

### Findings to file (OR-14 — file, do not fix here)

- **`examples/ga6_normal.project.json` balances at sea level only.**
  `flight_loads.altitudes_ft` is `[0.0]`, so the V-n matrix is 80 points over
  four CG cases, twenty conditions and **one** altitude. Appendix A names five of
  its six critical wing conditions **at 12,000 ft** (`modules/select.py`'s own
  validation list: PLAA MAN D, PMAA GUST +C, NMAA GUST −C, ACRL, TORS). The
  loads still reproduce — these are equivalent-airspeed points and the module's
  oracle tests pass — but every case in the report's own register therefore reads
  `0 ft` where the manual reads 12,000, and the compressibility factor at those
  points is the sea-level one. Raised in the owner's review of iteration 3,
  2026-09-03; **filed as #164**, which also records why adding the altitude is
  not a free change (it renumbers every V-n case).

- **The GA6 wing case set holds no negative-load-factor condition.** The entered
  three (PHAA, TORS, ACRL) are all positive-g, and the selection's **NMAA**
  (23.333(c), V-n point 53, GUST −C at CG3) is one of the three the entered list
  overrides. So the wing distributions do not envelop the wing. A plain deletion
  of the entered list is not the fix: the entered three are the set Appendix A
  prints net loads for, and the entered ACRL carries an `unbal_moment` the
  selection cannot name — so the shape is additive. **Filed as #165**; the
  reporting half is OR-58 and is done.

- **No flaps-down span loading.** AIRLOADS does not fair the basic distribution
  across a deflected-flap lift discontinuity, so the oracle's second set of
  span-load plots cannot be produced for any project. Not a defect in what is
  built — a documented limitation of the ported method — but it is the gap OR-53
  renders as an absence, and the absence should point at a filed item rather than
  at nothing. **Filed 2026-09-01 as #163.**

---

## 12. Appendix B as a structures deck (OR-59 … OR-63)

*Owner rulings 2026-09-03, in session, in the review of iteration 3's Appendix B.
Same footing as OR-1 … OR-58. The ruling that starts them: **the aim of the
Appendix B table is to give the sectional loads to apply to a structures
model.** Everything below follows from taking that literally.*

| # | Decision | Amends |
|---|---|---|
| **OR-59** | **Appendix B is split: B.1 the applied loads, B.2 the loads carried.** They are different quantities and a reader who takes one for the other builds the wrong model, so the distinction is enforced by the table boundary and the heading rather than by a word in a note. B.1 gives, per row, the point the load acts at (`X`, `Y`, `Z`) and the load applied there (`Fz`, `Fx`, `Myy` free) — a deck, self-contained, with no coordinate to fetch from another section. B.2 gives `Sz`, `Sx`, `Mxx`, `Myy` against station: what a model built from B.1 should return. | **OR-56 (supersedes)** |
| **OR-60** | **The applied moment is the *free* moment, never a difference of the cumulative column.** `AIRLOADS` forms `myy = tyy + tvyy + trq`, of which only `trq` accumulates a strip increment; `tyy` and `tvyy` are position transfers of the outboard shear across the bay's sweep and dihedral, which a structural model generates for itself from the geometry. `ΔMyy` and the free moment are not close — at `ga6_normal` PHAA's outboard strip they are −5,313 and +5,917 lb·in, opposite in sign — so applying the difference double-counts the transfer, which is the 20 % error `balance._free_moments` was written to prevent. By the same argument **`Mxx` and `Mzz` have no applied increment at all**: a strip applies forces and a section moment and nothing else. | OR-6 |
| **OR-61** | **`Fy` is not a column, because the wing has no producer for it.** `WingStationLoad.f_span` is the fin's — a v-tail's span is airplane `Z`, so vertical acceleration is an axial column load in its deck — and is `0.0` at every wing station by construction, a wing carrying its spanwise inertia as `fz`. A column of zeros in a deck reads as a measured zero; the absence is stated in the derivation instead. | OR-32 |
| **OR-62** | **Section 3.2 owns the notation and the derivation.** It carries a symbol table — symbol, quantity, units, **and whether the quantity is an applied increment or a cumulative load** — and writes out the recurrences that build `Sz`, `Sx`, `Mxx`, `Myy` from the applied set, naming which terms are position transfers. A column heading anywhere in section 3 or Appendix B names a symbol from that table and nothing else. The prose form this replaces carried the same facts and let the ambiguity through, which is the argument for the table: increment-versus-cumulative is a property of each symbol, and prose that states it for ten symbols at once is prose nobody checks a heading against. | OR-54 (extends) |
| **OR-63** | **Every appendix starts a fresh page; Appendix B is landscape throughout.** Back matter is reference material a reader turns to, and an appendix that begins halfway down the last page of the section before it reads as a continuation of it. One orientation per appendix rather than a per-table rule, so the orientation survives a column being added. `Section` gains `page_break` and `landscape`; `pdflscape` joins the shared preamble. | `SUMMARY_REPORT.md` §2 |

### Gates added by this ruling

| Gate | Statement |
|---|---|
| **G-OR-29** | The applied set closes onto the cumulative one: `Fz`, `Fx` and `myy_free` summed tip inboard, with each concentrated mass entering as a point force through the arms its own coordinates state, reproduce the published `Sz`, `Sx`, `Mxx` and `Myy` at every station of every case, on `ga6_normal` **and** on `baron_58`. |
| **G-OR-30** | Every symbol a section 3 or Appendix B column heading uses is defined in 3.2's notation table, with its sense stated. |
| **G-OR-31** | Appendix B renders as two lettered subsections, applied and cumulative, with no load column shared between them. |
| **G-OR-32** | Every concentrated wing mass is a row of B.1 at its own coordinates, carrying zero free moment; the row count is the station count plus the mass count. |
| **G-OR-33** | Every appendix sets `page_break`; Appendix B sets `landscape`, and the rendered document opens and closes the environment exactly once. |

### The OR-15 admission of 2026-09-03

**Finding.** `WINGINER` adds each concentrated wing mass to the cumulative
shears, bending and torsion of every station inboard of it and leaves the
per-strip `fx`/`fz` panel-only — stated outright at `wing_inertia.py:212-215`.
The mass is therefore published nowhere as an applied load, and an Appendix B
built from the strip table alone is short by the whole of it: on `baron_58` PHAA,
**4,821.5 lb of a 5,004.1 lb root shear**, exactly `nz × ΣW` over the four entered
masses. It is inertia relief, so a model built from the short deck is
unconservative in shear and, with the masses at `y = 57–95 in`, substantially so
in root bending. `ga6_normal` enters no concentrated wing mass, which is why the
closure was exact there and the defect invisible until the Baron ran.

**Why it prevents progress.** OR-15's first row is narrow by design — a wrong
number the report can state accurately is not blocking. This is not that. The
appendix's stated purpose is to be applied to a structures model; a table that
cannot be applied without silently losing most of the inertia relief cannot be
written truthfully around the gap.

**Admitted by the owner in session, 2026-09-03, filed as #166.** Frozen files changed:
`sloads/modules/wing_inertia.py` (publish each mass as a `ConcentratedLoad`),
`sloads/modules/airloads.py` and `sloads/modules/wing_inertia.py` (populate
`WingStationLoad.myy_free`, which the wing chain left `0.0`), and
`sloads/modules/net_loads.py` (sum and transfer both). The manifest is updated in
the same commit per G-OR-9.

**Why `myy_free` had to be published rather than recovered.**
`balance._free_moments` reverses the transfer recurrence from the cumulative
column, which is exact for an air load and **wrong** once a point mass steps the
shear: the step is not a transfer, so it lands in the recovered free moment as a
spurious term. The two owners are guarded against each other on the air loads,
where both are valid.

**No oracle moved.** Every change is additive — a new field, a field that was
`0.0`, a new list — and no cumulative value is touched. The oracle tests and the
Appendix A ±0.1 % gates are unchanged, which is asserted rather than assumed.
`SCHEMA_VERSION` does not bump: `WingLoadResult` is a result, `Project` holds no
field of that type, and nothing on disk has this shape (the `BalancedCaseResult`
precedent in `tests/test_schema_guards.py`).
