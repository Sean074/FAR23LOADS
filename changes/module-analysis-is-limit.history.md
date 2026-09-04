## Step — Module analysis is a LIMIT channel (design note 48, tier L, 2026-09-04)

**Objective.** Close **#154** — a `ConditionResult` holding no load still
carrying `safety_factor = 1.5`, so a geometry table prints an ULTIMATE banner —
and the larger finding the review of it turned up: the factor was applied on far
more surfaces than the contract's purpose requires. The `engine` CLI report was
scaling a mean takeoff torque 554.4 → 831.6 ft-lb, and every per-module analysis
page was reporting ultimate loads to an engineer reading limit values.

**Deliverables.** `report.LoadChannel` splits the per-module renderers
(`results_to_rows`, `critical_rows`, `summary_rows`, `load_cases_to_rows`,
`module_text_report`, `text_report`) into two channels, threaded through
`io.load_cases_csv`, `report.results_zip`, `report.methods` and
`app_shell.sidebar`. Fourteen call sites opt into LIMIT: `cli.py` (2),
`app/Home.py`, and eleven in `app/views/`. The parameter **defaults to
ULTIMATE** — the inversion of the usual instinct, and the only arrangement in
which the frozen `oracle_app` output is unchanged by construction rather than by
inspection. `ConditionResult.safety_factor` becomes `Optional[float]` with
`safety_factors.prescribes_factor` as the single owner of "prescribes none";
`units.LOAD_UNITS` / `units.is_load_unit` move to `units.py` now that the
boundary has a second consumer. `CONVENTIONS.md` §3, `CLAUDE.md`,
`PROGRAM_SPEC.md` and `GUI_design.md` record the contract;
`ORACLE_REPORT.md` is deliberately unchanged (OR-78).

**Test / Acceptance.** New `tests/test_limit_channel.py` (G-OR-44, G-OR-47): the
renderers default to ULTIMATE and the frozen `oracle_app/results.py` names no
channel; a LIMIT render emits no `-ULT`, states its basis, points at the ultimate
deliverables, and reports the calc's own value; a factorless condition prints no
factor on either channel. `tests/test_safety_factors.py` gains G-OR-46 — both
directions of the factorless rule across all seven fixtures, the stamp path
rather than the constructor, and the `case_ref` clause asserted against SELECT.
`tests/test_ultimate_contract.py` inverts into a channel table: a download built
by a channelled renderer must name its channel, because the ULTIMATE default
means silence is not neutral. That gate found a fourteenth call site
(`engine_mount.py`'s `load_cases_to_rows`) on its first run, which the note's
inventory had missed. The Imperial baseline was regenerated deliberately —
**184 of 330 digests moved**, all 118 `txt/*` and 66 of 118 `csv/*`, with every
`sbeam/*` (83), `case_index` (6) and `gear_report` (5) unmoved. `case_index`'s
immobility is the empirical check that SELECT's six critical wing cases were not
blanked. Full suite green; `ruff` and `mypy` clean.

**Key decisions.** OR-76 … OR-86, design note 48, agreed by the owner in session
on 2026-09-03 (R1–R4) and 2026-09-04 (R5, D-a … D-f). Four of the six D-items
were ruled against the note's first recommendation, each because tracing or
measuring the code changed the answer: D-a's scope (thirteen callers in four
groups, including the results zip reached from both GUIs), D-b (flipped to LIMIT
once the same string proved to have a second exit as a bare page download), D-c
(the marking convention already existed as M4-15, so the ruling retires it
rather than inventing another), and D-e (the family/`_EXACT` approach withdrawn;
the discriminator was already in the data model). **OR-86** adopts the owner's
principle that the factor is *stated, never applied*, and splits its scope:
0.8.2 takes the module-view half, and 0.8.3 removes the last multiply from
`sloads/export/` under its own boundary note, where `CONVENTIONS.md` §3 and the
Phase C mission statement change together. The `safety_factor` field survives
that endpoint because two families are computed already-ultimate at SF = 1.0
(23.367(a)(2), 23.561(b)) and nothing else records it. **G-OR-44 was amended
during implementation**: it promised byte-identity for the ULTIMATE default,
which cannot hold alongside OR-82, since a factorless condition now prints `N/A`
on both channels. The owner ruled the change correct on its merits — geometry,
weights and speeds should never have carried a factor — so the oracle GUI's
Results page shows `N/A` where it showed `1.5`. No number moves, no frozen file
is edited, and no OR-15 admission arises. Two items are filed and not fixed:
`is_load_unit` tests the unit alone, so ENGLOADS' mean takeoff torque still
reads as a load; and two examples are stored at 1-space JSON indent.
