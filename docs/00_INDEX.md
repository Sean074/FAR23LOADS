# sloads Documentation — Index

This directory is organised into four numbered sections by **document type**.
Lower numbers are the day-to-day references; higher numbers are planning and
historical record.

| Section | Type | Contents |
|---------|------|----------|
| `10_standard/` | **Code standard** | The authoritative description of how the suite works *today* — architecture, the per-module spec, and the process guides. Update these whenever code changes. |
| `20_theory/` | **Theory & equation sources** | Where each module's equations and regression oracles come from (the `reference/` PDFs), plus per-module page citations as modules are ported. |
| `30_future/` | **Future development** | The backlog & the live plan documents for **open** work: milestone **M4** (post-0.3.0), **Phase F25**, the long-tail refinements, and the open design decision. Plans whose work has shipped move to `40_history/`. |
| `40_history/` | **Historic record** | What has shipped — completed modules/phases, key decisions, and resolved defects. |

---

## 10_standard — Code standard

| File | Scope |
|------|-------|
| [`00_program_overview.md`](10_standard/00_program_overview.md) | **Start here** — program code standard & developer guide: structure, coding standards, error-handling contract, units, entry points, testing/coverage |
| [`PROJECT_GUIDE.md`](10_standard/PROJECT_GUIDE.md) | Architecture, package layout, porting conventions, validation strategy, dependency-ordered roadmap |
| [`PROGRAM_SPEC.md`](10_standard/PROGRAM_SPEC.md) | Per-module specification for all 22 programs (inputs, outputs, FAR conditions, `.BAS` mapping) |
| [`GUI_design.md`](10_standard/GUI_design.md) | **GUI design & structure** — navigation model, global sidebar, page anatomy/conventions, unit-boundary input pattern, definition-page standards, FAR 23 applicability/concept-awareness, JSON persistence |
| [`GUI_USER_GUIDE.md`](10_standard/GUI_USER_GUIDE.md) | **GUI user guide** — task-oriented walkthrough: workflow phases, what to enter where, the seed chain, LIMIT-vs-ULTIMATE reading rules, and an end-to-end `ga6_normal` example with hand-checkable numbers |
| [`SUMMARY_REPORT.md`](10_standard/SUMMARY_REPORT.md) | **Summary-report document standard** (Step G8) — purpose and audience, whole-document content rules (ultimate-load marking, traceability, axes/signs/stations, absence handling, units), the required section structure, the **excluded-content** list, and the conformance checklist |
| [`DATA_DICTIONARY.md`](10_standard/DATA_DICTIONARY.md) | **`project.json` data dictionary** (generated) — every input field's type, units, default, owning page, and consuming modules; produced by [`generate_data_dict.py`](generate_data_dict.py) |
| [`CODE_REVIEW_PROCESS.md`](10_standard/CODE_REVIEW_PROCESS.md) | Critical code-review process for module ports |
| [`RELEASE_PROCESS.md`](10_standard/RELEASE_PROCESS.md) | Versioning and release process |

## 20_theory — Theory & equation sources

| File | Scope |
|------|-------|
| [`00_theory_sources.md`](20_theory/00_theory_sources.md) | The authoritative references (`reference/` PDFs) and how to cite them in code and tests |
| [`01_far25_gap_analysis.md`](20_theory/01_far25_gap_analysis.md) | **FAR 25 gap analysis** (Phase F25) — the FAR 23 → FAR 25 comparison table, per-condition disposition, and what stays out of scope (tuned-gust, continuous turbulence, full Appendix K) |
| [`02_approved_corrections.md`](20_theory/02_approved_corrections.md) | **Approved corrections register** — the authoritative list of deliberate oracle deviations (CLAUDE.md states the policy and links here) |
| [`engine_loads.md`](20_theory/engine_loads.md) | **Engine-mount loads (ENGLOADS)** — equations for FAR 23.361/363/371 with a worked IO-520-BB example |

## 30_future — Future development

| File | Scope |
|------|-------|
| [`00_backlog.md`](30_future/00_backlog.md) | **Authoritative backlog & development plan** — the open items in priority order (**M4** post-0.3.0 → **Phase F25** → long tail → future directions) and the open design decision requiring user input (all 22 suite programs ported) |
| [`01_concept_loads_plan.md`](30_future/01_concept_loads_plan.md) | **Phase C plan** — growing the suite into an initial-concept distributed-loads tool (concept mode, Schrenk airloads, per-component distributed loads, sbeam export bridge) |
| [`03_gui_rework_plan.md`](30_future/03_gui_rework_plan.md) | **Phase G plan** — workflow-aligned GUI rework: one-unit-per-dimension policy, single-source-of-truth geometry, re-sequenced analysis-flow navigation, and the new fuselage-moment/trim-plot/elevator-chord features (assessment vs. current code, locked decisions G-1…G-4) |
| [`06_m4-20_deliverable_units_plan.md`](30_future/06_m4-20_deliverable_units_plan.md) | **M4-20 plan — ✅ complete 2026-08-04** — deliverables render in the user-selected unit system: the human/solver **two-channel** unit split (N·m vs. the consistent N/mm/N·mm solver set), decisions D-19…D-22, seven sub-steps, the two `units.py` defects it fixes, and the test/doc-sync matrix |
| [`05_step_g8_summary_report_plan.md`](30_future/05_step_g8_summary_report_plan.md) | **Step G8 plan** — the consolidated loads summary report: locked decisions (LaTeX/PDF, pgfplots figures, methods-statement stamping, report depth), the `sloads/report/` package layout, seven ordered sub-steps, risks, and the test matrix. **✅ complete 2026-08-05** — the M3-3b remainder (`content.py`, `latex.py`, `plots_tex.py`, `export/pdf.py`) shipped; kept as the plan of record |

## 40_history — Historic record

| File | Scope |
|------|-------|
| [`00_completed_development.md`](40_history/00_completed_development.md) | Record of completed modules/phases, key decisions, and resolved defects |
| [`01_verification_baseline_0.2.0.md`](40_history/01_verification_baseline_0.2.0.md) | Verification baseline (0.2.0) — superseded by the 0.3.0 baseline below |
| [`02_verification_baseline_0.3.0.md`](40_history/02_verification_baseline_0.3.0.md) | **Verification baseline (0.3.0, current)** — the per-condition table of every checked FAR condition and the printed Appendix A (or worked-example) figure the suite locks against, plus the one-page oracle-vs-closure status table; refreshed per release (`RELEASE_PROCESS.md`) |
| [`03_resolved_decisions.md`](40_history/03_resolved_decisions.md) | **Resolved design-decision register** — D-1 … D-11 with resolution date and a pointer to the rationale; open decisions stay in the backlog until answered |
| [`04_m4-1_body_moment_closure.md`](40_history/04_m4-1_body_moment_closure.md) | **M4-1 design note (closed 2026-08-03)** — fuselage body-load moment closure: diagnosis of the unreacted wing-attachment couple, the A–E options trade, the shipped carry-through distributed spar reaction (formulas, fallback, per-step verification figures) |
| [`05_phase_d_gui_workflow_plan.md`](40_history/05_phase_d_gui_workflow_plan.md) | **Phase D plan (executed; nav grouping superseded by Phase G)** — GUI workflow restructure: assessment, six-section target structure, load-case IDs, locked decisions D-1…D-7, page conventions. Still the citation target for the D-numbered GUI decisions |
| [`06_m3-1_rename_procedure.md`](40_history/06_m3-1_rename_procedure.md) | **M3-1 execution runbook (executed 2026-07-22)** — step-by-step git + shell procedure for the `farloads` → `sloads` rename batched with the `models.py` → `models/` split |
| [`07_m4_maintainability_sequence_plan.md`](40_history/07_m4_maintainability_sequence_plan.md) | **M4 maintainability sequence plan (executed 2026-08-03/04)** — execution order and per-step detail for M4-12 → M4-11 → G8 views → M4-10 → M4-9: measured baseline, design decisions D-12…D-18, per-step acceptance/risk, doc-sync matrix. Remainders M3-3b / M4-10b / M4-11b are carried in the backlog |

---

> Root-level docs live outside `docs/`: [`../README.md`](../README.md) (user
> front page), [`../CHANGELOG.md`](../CHANGELOG.md) (release notes), and
> [`../CLAUDE.md`](../CLAUDE.md) (guidance for Claude Code). The authoritative
> theory/oracle PDFs live in [`../reference/`](../reference/), alongside the
> **CFR/AC text extracts** cited by the calc and the F25 gap analysis —
> `14CFR_factor_of_safety.md`, `14CFR_operating_limitations.md`,
> `14CFR_MC_MD_speed_margin.md`, `14CFR_Part25_engine_torque.md`,
> `AC_23-19A_engine_torque.md`, `23_427_unsymmetrical_candidate_set.md`, and
> `fuselage_pitching_moment.md`.
