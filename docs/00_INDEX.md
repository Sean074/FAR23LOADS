# FAR 23 LOADS Documentation — Index

This directory is organised into four numbered sections by **document type**.
Lower numbers are the day-to-day references; higher numbers are planning and
historical record.

| Section | Type | Contents |
|---------|------|----------|
| `10_standard/` | **Code standard** | The authoritative description of how the suite works *today* — architecture, the per-module spec, and the process guides. Update these whenever code changes. |
| `20_theory/` | **Theory & equation sources** | Where each module's equations and regression oracles come from (the `reference/` PDFs), plus per-module page citations as modules are ported. |
| `30_future/` | **Future development** | The backlog & step-by-step plan: the two-phase plan (Phase 1 concept-loads enablement, Phase 2 refinements), deferred refinements and open design decisions (all 22 suite programs are now ported). |
| `40_history/` | **Historic record** | What has shipped — completed modules/phases, key decisions, and resolved defects. |

---

## 10_standard — Code standard

| File | Scope |
|------|-------|
| [`00_program_overview.md`](10_standard/00_program_overview.md) | **Start here** — program code standard & developer guide: structure, coding standards, error-handling contract, units, entry points, testing/coverage |
| [`PROJECT_GUIDE.md`](10_standard/PROJECT_GUIDE.md) | Architecture, package layout, porting conventions, validation strategy, dependency-ordered roadmap |
| [`PROGRAM_SPEC.md`](10_standard/PROGRAM_SPEC.md) | Per-module specification for all 22 programs (inputs, outputs, FAR conditions, `.BAS` mapping) |
| [`GUI_design.md`](10_standard/GUI_design.md) | **GUI design & structure** — navigation model, global sidebar, page anatomy/conventions, unit-boundary input pattern, definition-page standards, FAR 23 applicability/concept-awareness, JSON persistence |
| [`CODE_REVIEW_PROCESS.md`](10_standard/CODE_REVIEW_PROCESS.md) | Critical code-review process for module ports |
| [`RELEASE_PROCESS.md`](10_standard/RELEASE_PROCESS.md) | Versioning and release process |

## 20_theory — Theory & equation sources

| File | Scope |
|------|-------|
| [`00_theory_sources.md`](20_theory/00_theory_sources.md) | The authoritative references (`reference/` PDFs) and how to cite them in code and tests |
| [`engine_loads.md`](20_theory/engine_loads.md) | **Engine-mount loads (ENGLOADS)** — equations for FAR 23.361/363/371 with a worked IO-520-BB example |

## 30_future — Future development

| File | Scope |
|------|-------|
| [`00_backlog.md`](30_future/00_backlog.md) | **Authoritative backlog & development plan** — the two-phase plan (Phase 1: make concept-loads development possible; Phase 2: priority-ordered refinements & nice-to-haves) and the open design decisions requiring user input (all 22 suite programs ported) |
| [`01_concept_loads_plan.md`](30_future/01_concept_loads_plan.md) | **Phase C plan** — growing the suite into an initial-concept distributed-loads tool (concept mode, Schrenk airloads, per-component distributed loads, sbeam export bridge) |
| [`02_gui_workflow_plan.md`](30_future/02_gui_workflow_plan.md) | **Phase D plan** — GUI workflow restructure: assessment, six-section target structure, load-case IDs, locked decisions, page conventions |
| [`03_gui_rework_plan.md`](30_future/03_gui_rework_plan.md) | **Phase G plan** — workflow-aligned GUI rework: one-unit-per-dimension policy, single-source-of-truth geometry, re-sequenced analysis-flow navigation, and the new fuselage-moment/trim-plot/elevator-chord features (assessment vs. current code, locked decisions G-1…G-4) |

## 40_history — Historic record

| File | Scope |
|------|-------|
| [`00_completed_development.md`](40_history/00_completed_development.md) | Record of completed modules/phases, key decisions, and resolved defects |

---

> Root-level docs live outside `docs/`: [`../README.md`](../README.md) (user
> front page), [`../CHANGELOG.md`](../CHANGELOG.md) (release notes), and
> [`../CLAUDE.md`](../CLAUDE.md) (guidance for Claude Code). The authoritative
> theory/oracle PDFs live in [`../reference/`](../reference/).
