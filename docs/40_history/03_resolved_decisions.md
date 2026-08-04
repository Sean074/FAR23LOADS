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
| D-6 | ~~Keep "FAR23LOADS"~~ **Superseded → full rename to `sloads` at 0.3.0 (M3-1)** | 2026-07-20 | [`04_m3-1_rename_procedure.md`](../30_future/04_m3-1_rename_procedure.md) |
| D-7 | sbeam export: load-cards-only default; assembled stick model behind a flag (scopes long-tail **L-1**) | 2026-07-16 | [`01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md) |
| D-8 | Full-airplane project JSONs are the canonical input form; per-module slices derived | 2026-07-16 | [`../10_standard/PROJECT_GUIDE.md`](../10_standard/PROJECT_GUIDE.md) |
| D-9 | 23.427 unsymmetrical search: restore the full `SELECT.BAS` candidate set incl. unchecked (shipped as M1-4) | 2026-07-20 | [`../20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md) |
| D-10 | Aero-coefficient curve plot: include (backlog **M4-5**) — supersedes the 2026-07-15 decline | 2026-07-20 | M4-5 (backlog) |
| D-11 | Backlog restructured to release milestones; rename ships with the release as **sloads 0.3.0** | 2026-07-20 | M3-2 (history) |

**Still open:** **D-5** (Appendix B twin fixture — blocks long-tail **L-9**);
see the backlog.
