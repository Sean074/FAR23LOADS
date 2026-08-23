# Backlog review before the 0.7.0 cut — the beta scope re-cut (2026-08-22)

**Charge (user, 2026-08-22):** before closing 0.7.0 development, review the
backlog for items that should be in **0.7.0 — a beta release of the oracle
GUI**: everything that supports a *usable* oracle GUI belongs in the release,
and #50, #51 and #52 are in by direction. This file is the body of record
(`CLAUDE.md` rule 5: findings filed with bodies, same session).

**Yardstick:** the release theme — *does the item change what a beta user of
the oracle GUI experiences?* — applied to bands B–D and `02_parked.md`.
`CLAUDE.md` rule 6 still governs physics/fidelity items (nothing here is one);
defects with first-order effect on shipped content outrank everything.

**Inputs:** the priority table as left when band A emptied on 2026-08-22
(band B rows 9–12, band C 13–16, band D 17–22), `02_parked.md`, the issue
bodies of #50/#51/#52 (pasted by the user; #51's 2026-08-22 reopen comment is
the scope of record for its residual), and two measurements taken this
session (BB-4, BB-5).

**Decisions taken by the user in this review (2026-08-22):** #50 closes as a
duplicate of #51; **#44 comes into 0.7.0 with #51** (same call sites, one
pass); **#52's schema hop happens inside 0.7.0**, one hop retiring **both**
duplicate fields, with the reconciling migration.

---

## 1. Findings

| # | Finding | Disposition |
|---|---|---|
| BB-1 | **#50 and #51 are the same defect.** Identical title and near-identical body (the L-8d data-loss class: `adopt()` must invalidate form widget state); #50's only difference is a "Band A Pri 2" prefix from the original row mint. #51 carries the paper trail — the keyed half shipped 2026-08-21 against it, and its 2026-08-22 reopen comment holds the residual's scope, reproduction and acceptance. | **#50 closed as duplicate of #51** (user). The table names #51 only. |
| BB-2 | **#51 residual — the unkeyed half of `app/views/`.** 98 of 187 project-seeded widgets carry no `key=`; an unkeyed widget's Streamlit identity derives from its *arguments*, so retained state survives a project load whenever the loaded field repeats the seed (the common case — the seed is `Project(name="")`). Reproduced on a real view and shipped example: a value typed into `structural_speeds`' VB before loading `atr42_100` survives the load, enters the project on Apply, and reaches disk. `test_widget_freshness.py`'s `_stamped` waves unkeyed widgets through on a premise that does not hold. | **Band A Pri 1** (defect; data loss on shipped fields). Tier M per the issue. `_stamped` inverts to fail closed; behavioural guard edits a widget *before* the load. |
| BB-3 | **#44 unit-boundary rollout rides the same call sites.** #51's fix touches the same ~7 hand-paired views; `unit_number_input` stamps `key=widget_key(...)` for all its callers, so doing the two together is most of #51's work for free — the note both rows already carried. Leaving #44 in 0.8.0 would touch the same lines twice across two releases. | **Pulled into band A, Pri 2** (user). One pass with #51. The `app/views/` freeze lifts **for exactly these call sites** — `key=` + the boundary helper; layout/behaviour rework stays frozen pending #29. |
| BB-4 | **#45 (CR-D-3) reproduces in the oracle GUI — measured this session.** On a fresh project, 2 of the 14 oracle pages tell the user to "run the pages before this one first" for a slice **their own form enters**: `weight_mass` (missing `weight`) and `engine_mount` (missing `engines`). The form above the note works (`form.py` renders on missing slices by design — "the GUI's job is to *make* the slices"), so the guidance is wrong, not blocking — but it is wrong on the beta's first-run path, on the very pages a from-scratch concept starts at. The other 11 blocked notes are genuine cross-page requirements. | **Promoted to band A, Pri 3** under the beta criterion. Tier M / effort S: `WorkflowStep.edits` (or equivalent) + the DAG-completeness guard, workflow-side — no frozen view is touched. |
| BB-5 | **#52's two duplicate entries are an oracle-GUI defect, not only a schema wart — measured this session.** Both members of each pair are in the field registry **on the same oracle page**: `speeds.mach_limit.shoulder_altitude_ft` and `speeds.shoulder_altitude_ft` both render on `structural_speeds`; the vtail and htail `airplane_length_in` both render on `configuration_layout`. A beta user is shown two widgets for one physical quantity with nothing reconciling them, and MC/MD can be computed at two different altitudes with no warning. | **Pulled into band A, Pri 4** (user): one **v55 schema hop** retiring both duplicates, migration takes the owner's value and warns on disagreement. The band-A schema freeze is amended for exactly this hop (ordering rule added). Tier L per note 33 DS-7. |
| BB-6 | **#46 docs/CI conformance sweep.** No user-visible effect in either GUI. | Stays band B (0.8.0). |
| BB-7 | **Band C (#14, #31, #32, #47)** — analysis capability. #32 was checked against the criterion because the oracle GUI's tail-loads page publishes the BALLOADS rows that include the nine past-fit points unmarked: D-30 adjudicated them as ordinary Mach-capped stall-limited flight, 0 of 9 are SELECTed, no sizing load moves — disclosure fidelity, not beta usability; and its marker's owner (`EnvelopeResult.is_clamped`, from #33) is already shipped, so nothing rots by waiting. | Unchanged, 1.0.0. |
| BB-8 | **Band D (#15, #16, #17, #18, #19)** — hygiene when the module is next touched. | Unchanged. |
| BB-9 | **Parked sweep against the criterion.** L-8b (tooltips), L-8c (Results Review parity), L-8e (uncovered fields) are `app/views/`-only: the oracle form is registry-generated, and every L-8e field is in the registry with an oracle page (verified: `chosen_va`/`chosen_vf`, `one_engine_out.speeds_kt`, the envelope nose/tail stations). L-8h's 17 unconverted result cells (ft², lb/ft², ft/s) do reach oracle result tables in SI mode, but none is a load quantity and the beta is Imperial-first oracle replication — stays parked with the number. L-8d's mutation-case residual stays parked (no generation bump can cover a project that was never replaced); its replacement-case half **is** #51 (BB-2). | Nothing promoted. |
| BB-10 | **The cut signal is unchanged in form:** cut **0.7.0** when band A is empty — now four rows instead of zero. The 2026-08-20 preamble's "no schema hop anywhere in band A" is superseded by BB-5's amendment; everything else in that re-cut stands. | Re-cut below. |

## 2. The 0.7.0-beta order (band A) and the cut signal

| Pri | Item | Issue | Tier / effort |
|---|---|---|---|
| 1 | The unkeyed half of `app/views/` — 98 project-seeded widgets keyed; `_stamped` fails closed; edit-before-load guard | #51 | M / M |
| 2 | Unit-boundary rollout `unit_number_input` everywhere — one pass with #51 | #44 | M / M |
| 3 | `workflow.requires` vs self-entered slices — `WorkflowStep.edits` + DAG guard (wrong first-run guidance on 2 of 14 oracle pages) | #45 | M / S |
| 4 | Retire the two duplicate entries — one v55 hop, both pairs, reconciling migration | #52 | L / S |
| 5 | Pre-cut beta review — the oracle GUI's function end-to-end (delta since `4b1ddcc` + the fresh-project journey + gate-rot re-check); after rows 1–4 | #61 | S (review) / S–M |

**Cut 0.7.0 when band A is empty** — five rows: two M-effort (one shared
pass), one S, one S-effort schema hop, and the pre-cut review last (added by
the user after this review's §1, on the 2026-08-15 candidate-review pattern —
the cut signal includes it by construction). Band B = #29, #46; band C and D
unchanged.

## 3. What this review did not do

No code was changed and no view was reworked; the two measurements (BB-4,
BB-5) are read-only probes of `workflow.missing_requirements` and the field
registry, quoted above with their subjects. The main GUI was not reviewed —
that is #29's job, and #51/#44's touch on `app/views/` is call-site-scoped,
not a review. Parked bodies beyond the L-8 family were not re-read (none is a
GUI item).

## 4. Closure

Tier S: this file; the table and prose re-cut in `00_backlog.md` (band A
repopulated, ordering rule added, freeze paragraphs amended); the L-8d
paragraph in `02_parked.md` repointed at band A; `00_INDEX.md` row;
`changes/backlog-recut-0-7-0-beta.changed.md`; issue labels/milestone updated
(`band:A` + milestone `0.7.0` on #44/#45/#51/#52); **#50 closed as duplicate
of #51**.
