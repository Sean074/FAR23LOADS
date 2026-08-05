# Resolved Design Decisions (register)

The permanent record of project design decisions that were **put to the user and
resolved**. Open decisions awaiting user input stay in
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) (§ *Open design
decisions requiring user input*); once answered, they move here.

Full rationale for each decision lives in the step record in
[`00_completed_development.md`](00_completed_development.md) and in the plan
document named in the *Rationale* column.

| ID | Decision | Resolved | Rationale |
|----|----------|----------|-----------|
| D-1 | Concept reference airplane = swept twin-turbofan regional jet (forces the AIRLOAD4 swept branch) | 2026-07-16 | [`01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md) |
| D-2 | Concept gyroscopic rates: keep 23.371(b) fixed rates + guard/warn on exceedance | 2026-07-16 | Phase 1 Step P1-5 (history) |
| D-3 | No sbeam-VLM validation backend; closure + fleet plausibility. **Revisit trigger:** an OpenVSP/VSPAERO aero import would supply the cross-check whose absence this decision accepted (see the backlog's *Future directions*) | 2026-07-16 | [`01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md) |
| D-4 | Fleet comparison set (29 aircraft) sufficient as-is | 2026-07-16 | Phase F Step F1 (history) |
| D-6 | ~~Keep "FAR23LOADS"~~ **Superseded → full rename to `sloads` at 0.3.0 (M3-1)** | 2026-07-20 | [`06_m3-1_rename_procedure.md`](06_m3-1_rename_procedure.md) |
| D-7 | sbeam export: load-cards-only default; assembled stick model behind a flag (scopes long-tail **L-1**) | 2026-07-16 | [`01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md) |
| D-8 | Full-airplane project JSONs are the canonical input form; per-module slices derived | 2026-07-16 | [`../10_standard/PROJECT_GUIDE.md`](../10_standard/PROJECT_GUIDE.md) |
| D-9 | 23.427 unsymmetrical search: restore the full `SELECT.BAS` candidate set incl. unchecked (shipped as M1-4) | 2026-07-20 | [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md) |
| D-10 | Aero-coefficient curve plot: include (backlog **M4-5**) — supersedes the 2026-07-15 decline | 2026-07-20 | M4-5 (backlog) |
| D-11 | Backlog restructured to release milestones; rename ships with the release as **sloads 0.3.0** | 2026-07-20 | M3-2 (history) |
| D-12 | `LoadValue.key` is a **persisted** field (`io.py` `CriticalCondition.loads`), so **M4-10 lands before M4-9**: the key arrives via a normal label→key backfill migration, making M4-9 the migration chain's first customer | 2026-08-03 | [`07_m4_maintainability_sequence_plan.md`](07_m4_maintainability_sequence_plan.md) |
| D-13 | `htail_balance` returns a `typing.NamedTuple` with **lowercase** attributes (`lt25`, `lt50`, `at`, `delta`, `lt`, `cp`); Ref 1 Ch 9 symbols kept in the field docstrings | 2026-08-03 | [`07_m4_maintainability_sequence_plan.md`](07_m4_maintainability_sequence_plan.md) |
| D-14 | Cross-module private symbols are promoted by **underscore-drop in place + `__all__`** per module — no `sloads/api.py` facade; `_envelope` gets a chosen name rather than a mechanical strip. **Applied 2026-08-03 (M4-12b):** the chosen-name carve-out took three symbols, not two — `_envelope` → `default_envelope`, `_design_inputs` → `design_inputs`, and `_sigma` → **`density_ratio`** (a public `sigma` would have collided in meaning with `constants.standard_atmosphere`'s sigma, which it duplicates — logged as M4-23) | 2026-08-03 | [`07_m4_maintainability_sequence_plan.md`](07_m4_maintainability_sequence_plan.md) |
| D-15 | The `Project.tail_loads`/`.vtail_loads` property proxies are **documented (not replicated) in M4-12b and retired in M4-10**, where `project_from_dict` is rebuilt anyway | 2026-08-03 | [`07_m4_maintainability_sequence_plan.md`](07_m4_maintainability_sequence_plan.md) |
| D-16 | `unit_number_input` reads the active unit system through a **single `_active_system()` resolver** over session state; M4-20 re-pointed that one function at the `Project` field (step 2), and step 6 removed the twelve views that had been reading the session key directly | 2026-08-03 | [`07_m4_maintainability_sequence_plan.md`](07_m4_maintainability_sequence_plan.md) |
| D-17 | **`radon` added to the `dev` extra** to measure M4-11 before/after complexity — a reporting tool, explicitly **not** a CI gate | 2026-08-03 | [`07_m4_maintainability_sequence_plan.md`](07_m4_maintainability_sequence_plan.md) |
| D-18 | Consolidated test helpers expose **three named functions** — `value_of`, `load_value`, `values_by_label` — each accepting a `ModuleResult`, `ConditionResult`, or list of either | 2026-08-03 | [`07_m4_maintainability_sequence_plan.md`](07_m4_maintainability_sequence_plan.md) |
| D-19 | The sbeam solver deck uses **one dimensionally consistent unit set** — N / mm / **N·mm**, extended in step 4 to **MPa** (N/mm²) for pressure. Human-readable deliverables keep N·m / kPa, so a bundle carries two moment units *deliberately*, one per channel. A deck whose GRIDs are millimetres and whose FORCE cards are newtons is only correct with N·mm moments; an N·m one (or a kPa stress) is wrong by 1000× in a file that parses cleanly and sizes structure | 2026-08-04 | [`06_m4-20_deliverable_units_plan.md`](../30_future/06_m4-20_deliverable_units_plan.md) §2 |
| D-20 | SI design pressure is **`kPa-ULT`** in the human channel (the docs' `Pa-ULT` was amended); the solver channel's is `MPa-ULT` per D-19 | 2026-08-04 | [`06_m4-20_deliverable_units_plan.md`](../30_future/06_m4-20_deliverable_units_plan.md) §2 |
| D-21 | The **in-band unit statement wins** over byte-identical Imperial output: every file gains a units line, and the Imperial-unchanged guard is therefore strip-and-compare rather than raw equality | 2026-08-04 | [`06_m4-20_deliverable_units_plan.md`](../30_future/06_m4-20_deliverable_units_plan.md) §2 |
| D-22 | The sidebar Imperial/SI toggle **writes `Project.unit_system`** and marks the project dirty — the selection is a project edit, not a session preference, so it saves and reloads with the project | 2026-08-04 | [`06_m4-20_deliverable_units_plan.md`](../30_future/06_m4-20_deliverable_units_plan.md) §2 |
| G8-5 | Summary-report `revision` is **free text** the engineer maintains, not a tool-managed auto-incrementing counter — a tool counter would disagree with the drawing/report system of record the moment a project is copied, and revision identity belongs to the engineering process | 2026-08-04 | [`05_step_g8_summary_report_plan.md`](../30_future/05_step_g8_summary_report_plan.md) §10 |

**Still open:** **D-5** (Appendix B twin fixture — blocks long-tail **L-9**);
see the backlog.
