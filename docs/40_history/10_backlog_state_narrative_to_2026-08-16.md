# Backlog "Current state" narrative — archived 2026-08-16

Moved verbatim from `docs/30_future/00_backlog.md` on 2026-08-16 when the backlog header was cut to rules-and-pointers only. It is the running what-has-shipped narrative as it stood at the 2026-08-16 re-cut (through step 12, schema v52). Nothing here is maintained; the records of what shipped are `CHANGELOG.md` and `00_completed_development.md`.

---

## Current state (as of 2026-08-16)

All 22 Appendix-C programs are ported plus 4 modern modules (`configuration`,
`body_loads`, `tail_span`, `balance`). Phases 0–2, C, D, E, F, Phase 1, Phase G Steps **G0–G7**,
milestones **M1, M2, M2R, M3** and mission-extension **steps 1–9** are complete
(step 8 = the lateral empennage closure, plan 13 B8a-1…B8a-5, 2026-08-09;
step 9 = discrete control surfaces with the suite's first hinge moment, and the
T-tail transfer, plan 09 T6–T8, 2026-08-13), plus
the **concentrated-mass offset couples** (plan 14, 2026-08-09 — the exported
wing deck now reproduces the NETLOADS shear *and* bending at every node, on a
concentrated-mass wing, verified in the real solver) and the **empennage mass
SSOT** (2026-08-10 — the tail surface weight is derived from `weight.items`, so
every h-tail deck carries inertia instead of being silently air-only; the fin
gains its lateral and axial inertia terms; and the export path's `n = 1.0`
fallback, which understated h-tail inertia up to 3.8×, is fixed) and the
**SI `GRAV` fix + CONM2 round-trip CI leg** (2026-08-10, the 0.5.0 review's
CRITICAL **C1** and **F-G2**: the SI mass-check deck's gravity was 25.4× low and
the mass family was the one deck family the harness never solved — both closed
together, in both unit systems) and the **CLI deliverable completion**
(2026-08-10 — every deliverable reachable headless including the balanced deck,
the CLI wing export through the LRA transfer, the G8.3 methods stamp on every
headless CSV/BDF, and one error contract) and the **balanced deck + CONM2 made
first-class** (2026-08-10, D-R2/F-D2 — report §6 states the assembled model per
case with its residuals, handed twin pairs and mass-case identity; both
artifacts join the Export bundle and the manifest; the two page-level downloads
are stamped). The suite is green (ruff clean, smoke test
PASS), the FAR23 GA path is Appendix-A oracle-locked, and both concept fixtures
run end-to-end.

**Release status:** **sloads 0.4.0 cut 2026-08-08**, tag `v0.4.0` — the mission
extension's first seven steps (mass SSOT, CONM2/MASSSET export, balanced
free-free cases, the handedness machinery, the sbeam round-trip CI harness and
distributed empennage loads) plus M4-20, M3-3b, M4-2 and F25-2. `[Unreleased]`
holds **step 8 entire** — the fin root waterline (B8a-1), the six-DOF closure
(B8a-2) and the lateral ±β empennage cases (B8a-3…5) — plus the
balancing-method theory document
(`docs/20_theory/balanced_cases.md`), the concentrated-mass offset couples
(plan 14) and the **empennage mass SSOT** (2026-08-10: tail decks gain inertia,
the fin gains its two-axis inertia, and the `n = 1.0` export fallback is fixed)
and the **SI `GRAV` fix + CONM2 round-trip CI leg** (2026-08-10, review C1/F-G2)
and the **CLI deliverable completion** (2026-08-10, review F-D1/F-C2/F-D3 + m2,
absorbing L-8g) and the **balanced deck + CONM2 first-class** step (2026-08-10,
D-R2/F-D2 — report §6, manifest rows, Export bundle, stamped page downloads) and
the **wing deck `$` width + centerline-clamp header line** (2026-08-10 — the
stick deck states its centerline clamp and its half-span-total reaction, and the
72-column comment sweep covers the wing decks; the release's last Phase-1 row) and the **manifest § renumber + pin**
(2026-08-10, F-R2 — the companion-file cross-references corrected and the
report's section numbering given a single owner with four drift guards) and
**limitations completeness** (2026-08-11, F-R4/D-R3 — the four missing open
caveats, the conditional assumed-planform statement and a pinned key set behind
the completeness claim; alongside it the body deck's platform-dependent negative
zero, found from a CI digest failure) and the **per-case SF in the
governing-loads tables** (2026-08-11, F-R1 — the report-side pre-slice of M4-8
Layer 1: each governing row scales by its own case's factor and the `sf`
override is gone, so the report and the deck cannot state different factors for
one case) and the **standing disclaimer in the methods statement** (2026-08-11,
F-R3 — the "not a certification document" sentence leads the block that travels
in every stamped file, and the title page quotes the one wording; Phase 2's last
row).

**0.5.0 is cut (2026-08-13).** Decision D-R1 held the release for the
deliverable — the report plus wing/body/tail and balanced/CONM2 sbeam output —
and every phase of the 2026-08-10 review's scope
(`docs/50_reviews/2026-08-10_code_review_0_5_0.md`) is now closed: Phase 0
correctness & gates, Phase 1 deliverable completion, Phase 2 the report's own
basis and limits, and Phase 3 release mechanics (workbook per-sheet units m14,
the root/lint hygiene m19–m21, version bump, dated changelog with the four
standing caveats, and the archive verification in
[`../40_history/09_verification_baseline_0.5.0.md`](../40_history/09_verification_baseline_0.5.0.md)).
Every row below is post-0.5.0. Per D-R3 the ground/landing case families are the
0.6.0 headline; the cadence rule (RELEASE_PROCESS §2) restarts from this tag.
Shipped since the tag: the ONENGOUT fixture data, the case-identity ↔ deck
`LOAD` linkage, the **wing case row's flight condition** (D-23, 2026-08-13 — a
row now states the speed its loads were computed at, keeping SELECT's `case_id`),
**step 9 entire** (2026-08-13 — discrete control surfaces with the suite's first
hinge moment, T6, and the T-tail fin deck carrying the h-tail at its tip, T7;
plan 09 closed), the **permanent pressurization exclusion** (D-24 — the standing
limitation now states an exclusion with its basis, not a "not yet")
and **step 10 entire** — the governing safety-factor table (piece 1, M4-8/G-11),
the weight/CG case model and gear inputs (piece 2, schema v47) and the
**ground/landing cases + gear load report** (piece 3, 2026-08-15, schema v48),
and the **`CgCase` explicit loading definition** (2026-08-15, schema v50,
decision D-25 with D-25a…d — a payload case can now *state* the loading behind
it instead of the mass model being searched for; the regional jet's third
payload case and its `NMAA` condition join the assembled deck with it).
Piece 3 is the 0.6.0 headline per D-R3 and it **closes step 11** with it: under
G-1 the ground families are born as balanced free-free cases in the assembled
deck, so plan 11's phase 4 (B8b) has no separate build. The FAR 23 ground
conditions now assemble with their `NVP`/`NDP`/`NS` reproducing LANDLOAD exactly,
and the gear has a free-body report of its own on five. **Since Pri 5 / D-26
(2026-08-15) every shipped fixture assembles**: balanced flight cases on 6 of 6
and the complete 27-case ground family on all 5 with gear geometry, against 2 and
1 before — the fixtures' CG cases were corrected to the loadings their own weight
databases can produce, and every case now states one, with no ballast anywhere.
**Step 12 phase 0 + step 13 shipped 2026-08-16** (schema v51): decisions
BM-1…BM-5 recorded, `SurfaceInput.sob_y_in` + the one-owner SOB resolver, the
wing stick deck's tagged side-of-body reporting node (`lra-sob`, the first
`$ SLOADS-NODE` tag), and the SOB internal loads stated two ways — closed-form
in the deck/report, solver `CBAR` end force in round-trip CI — and gated.
**Step 12 shipped in full 2026-08-16** (schema v52; implementation note
[`25_lra_model_implementation_note.md`](25_lra_model_implementation_note.md)):
the **LRA beam model** — the third deliverable — exports as `lra_model.bdf`
(LRA node lines, split-fuselage posts, fin/h-tail/gear/engine ties, the
balanced cases transferred onto the nodes by the one-owner `transfer_couple`
rule) and imports (loads onto an external `GRID`/`CBAR` model under its own
GIDs, mapped by the `$ SLOADS-NODE` contract); the plan-07 invariant, the
free-free solver proof and the SOB/post internal-load gates run in CI, and the
fixtures enter `ref_axis_pct = 0.40` (one digest wave). The torsion-reference
question closed with it (R-7d).

