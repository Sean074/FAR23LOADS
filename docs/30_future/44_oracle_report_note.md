# Oracle technical report — scope, shape and development protocol

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status: AGREED 2026-08-29 (owner, in session — `CLAUDE.md` rule 1's
working-alone path); nothing built. Milestone: 0.8.2.** The three §5 open
questions were answered the same day and are recorded as OR-10 … OR-12 (§5),
on the same footing as OR-1 … OR-9. This note settles the shape of an
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
| **G-OR-5** | Two builds of the same project at the same unit selection are byte-identical (OR-5). |
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
backlog item** pointing at this note, worked on `dev/v0.8.2`. Issues are not
opened per section (`DEVELOPMENT_PROCESS.md` §0: the backlog is the record;
OR-9's accruing standard doc is the per-section register). Delivery follows
OR-8 as **one commit per agreed iteration** — ordinary work commits, keeping
the step-per-commit `git log` record — with a single `solo_close.sh` closure
(fragments, history entry, row removal) when the final section is agreed.
0.8.2 slots ahead of 0.9.0 (band B2, main-GUI development) deliberately: this
report is B2's declared starting point.

| Commit | Contents |
|---|---|
| 1 | `oracle_content.py` skeleton + section derivation + the oracle_app report page + `ORACLE_REPORT.md` created + gates G-OR-1/2/5/6/7 |
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

### OR-11 — Both examples build the report in CI

`examples/baron_58.project.json` already exists (note 34, UG-9). G-OR-1 runs
over **both** `ga6_normal` and `baron_58`: the single is the Appendix A oracle
case; the twin exercises the engine-mount and one-engine-out sections as
*present* rather than `absent_reason`, and (per UG-12) is the SI-channel case,
so the two builds together cover both unit selections of G-OR-5.

### OR-12 — Iteration order is workflow order

The default stands: analysis-body sections are developed in
`oracle_steps()` order, matching the section numbering, so each iteration's
sample values are values the already-agreed sections produced (the note 34
UG-10 lesson — writing a downstream section first means inventing numbers the
tool later contradicts).
