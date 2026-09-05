# sloads Project Review — 2026-09-04

Two-phase in-depth review of the sloads project at `dev/v0.8.2` (working tree as it sat,
including uncommitted docs changes). Phase 1: software implementation, maintainability,
development process and controls. Phase 2: analysis-method accuracy, safety-factor
application, deliverable accuracy and usability for a third-party structures analyst,
and a full triage of the backlog and future-development notes.

**Filed 2026-09-05 as issues #172–#191**, with the folds recorded as comments on
their host issues (R-8→#170, R-22→#17, R-25→#19); the backlog rows the triage
produced are Pri 26–35 of [`../30_future/00_backlog.md`](../30_future/00_backlog.md),
appended to their bands rather than re-cutting the 2026-08-29 order.

Findings are numbered **R-1 … R-27** and collected in §5 with ready-to-run
`gh issue create` / `gh issue comment` commands and a proposed milestone each
(0.8.2, 0.8.3, 0.9.0, 1.0.0, 2.0.0). The backlog triage tables are §4.

---

## Executive summary

**The project is in unusually good shape for its class.** Every quality gate is green
(3,455 tests passed, ruff clean, mypy clean, the 61-test sbeam roundtrip gate passed
against the pinned solver). The pure-calc/I-O architecture holds under inspection; the
oracle-coverage matrix has **no module with neither an oracle nor a closure gate**; all
spot-checked approved-corrections register entries match the code exactly; the
"factor applied once" invariant holds on every traced path with **no double-application
defect found**; and an independent re-derivation of global equilibrium from the shipped
balanced deck's cards (written for this review, not using project code) closed to a
worst normalized residual of **5.5×10⁻⁸** (Imperial) / **2.2×10⁻⁶** (SI) across all 44
subcases on both the GA6 oracle fixture and the flagship concept fixture.

**The most significant new findings, in order:**

1. **Two shipped example fixtures export LRA beam-model decks that do not solve in the
   pinned sbeam** (R-1). `ga6_normal` — the Appendix A oracle aircraft — fails with an
   RBE2 dependent-DOF chain conflict; `cessna_210` fails with a singular stiffness
   matrix. The roundtrip gate's LRA leg covers only `concept_regional_jet` and
   `atr42_100`, so the gate is structurally blind to exactly the fixtures that fail.
   The mission claim is "the exported deck solves in sbeam"; for this deck family on
   these aircraft it currently does not, and the CLI exports the broken deck without
   refusal or warning.
2. **The methods statement shipped on every deliverable declares only 3 of the 7
   approved oracle deviations** (R-3), and the CI guard that is supposed to catch this
   is circular (it checks the statement against its own source tuple, not against the
   register). An analyst comparing outputs against the printed manual pages has no way
   to know about the LANDLOAD sign corrections or the WINGGEOM closed-form change.
3. **The balanced free-free deck — the primary deliverable — is an elementless load
   cloud that cannot be solved as delivered, and nothing in the deck says so** (R-2).
   It carries `SOL 101` and `SPC = 1`, which invite a direct solve; running
   `sbeam <deck>` yields "Singular stiffness matrix" with no hint that this is by
   design. This review hit exactly that wall before finding the explanation in the
   roundtrip test's docstring — a third-party analyst has only the test source to
   learn it from.
4. **The safety-factor system is sound but has a small defect class at its edges**:
   the #170 non-load-factored class is three rows wide, not one (R-8); single-module
   runs in `oracle_app` bypass the governing table entirely, so a project SF override
   is silently ignored on that surface (R-6); one classifier path can silently take an
   unconservative factor on a compound reference (R-9); and the `engine_ultimate`
   table row's basis text names the wrong FAR case (R-7).
5. **Process controls guard drift superbly but closure weakly.** Everything about
   *statements drifting apart* has a guard test; everything about *closure obligations*
   (tier content, design-note status flips, tagging on a green main) rests on
   discipline — and the discipline is now measurably failing (three of the last four
   tier-L design notes were never flipped from AGREED to SHIPPED; 0.8.0 was tagged on
   a red main-push matrix) (R-13, R-14, R-15, R-16).
6. **The backlog is healthier than it feels.** The open-work set is coherent and
   synchronized between the backlog file and GitHub. The "bloat" is ~60% of
   `00_backlog.md` being stacked historical re-cut preambles, six shipped design notes
   never archived, four stale status headers, and three fresh CRITICAL defects
   (#164/#165/#170) sitting with no milestone. One cut-hygiene pass fixes nearly all
   of it (R-20).

**Phase 2 verdict on the analysis itself:** no wrong number was found on any delivered
load surface. The two CRITICAL open accuracy items are ones the project had already
found and filed (#164 — every GA6 case states 0 ft where Appendix A names 12,000 ft;
#165 — the GA6 wing case set carries no negative-g case and therefore does not envelop
the wing); this review confirms both verdicts and recommends merging them into one
0.8.3 work package.

---

## 0. Review basis and method

- **Baseline:** working tree at `dev/v0.8.2` (HEAD `4eb0717`), 2026-09-04.
- **Gates run:** full pytest suite (3,455 passed, 32 skipped, 1 xfailed, 224 s wall
  with parallelism), `ruff check` (clean), `mypy` (clean, 94 files),
  `pytest -m roundtrip` against the pinned solver (60 passed, 1 xfailed, 23 s).
- **Solver:** the sbeam pin (`ed23b26`) was verified to be an ancestor of the local
  sbeam checkout at `/Users/seanomeara/Documents/99-Tests/sbeam` (HEAD `7c5f758`, one
  commit ahead). All solve results below were reproduced with the **pinned** solver
  installed in the sloads venv; the local HEAD solver gave identical results on every
  deck tried, so no pin-drift effect contaminates the findings.
- **End-to-end runs performed:** `sloads engine` CSV; balanced full-span deck exports
  for `ga6_normal` (Imperial and SI) and `concept_regional_jet`; LRA model exports and
  solves for all seven exportable example fixtures; wing bundle with `--stick-model`;
  consolidated summary report (`--report`, 110 KB of LaTeX in 1.8 s).
- **Independent equilibrium check:** a standalone parser/summation script (no sloads
  imports) reassembled ΣF and ΣM about the origin from GRID/FORCE/MOMENT cards per
  subcase. Results: `ga6_normal` Imperial worst 5.5e-8, SI worst 2.2e-6,
  `concept_regional_jet` worst 3.9e-7 (normalized by Σ|F| and a 100 in reference arm).
  The free-free balance claim is verified independently of the project's own tests.
- **Breadth reading** of `sloads/`, `tests/`, `docs/`, `changes/`, `.github/`,
  `scripts/`, all 25 open GitHub issues, all of `docs/30_future/`, and sampled
  traceability chains in `docs/40_history/` and the git log.

---

## 1. Phase 1 — Software implementation

### 1.1 Architecture and code quality — PASS

- **Calc/I-O separation is real.** No `print`, `streamlit`, or `open()` anywhere in
  `sloads/` outside `io.py` and the sanctioned `export/` layer. App views contain
  input-echo only; the only view-side math found is display geometry for the
  three-view drawing.
- **Module contract is universally followed.** 23 `register(` calls across the module
  files; `safety_factor` is `Optional` and stamped by the governing table with sweep
  guards closing the silent-default hole; no upstream-quantity recomputation found in
  `modules/`, `export/`, or `report/` — the one historical instance (SELECT vs
  ONENGOUT v-tail helpers) is consolidated in `_vtail.py` with 1e-12 parity tests.
- **Conversion ownership holds.** Every 295/57.3/144 literal in modules is a docstring
  transcription; code reads `constants.py` owners and the literal is forbidden by
  guard test. `units.py` is the sole display/SI mapping.
- **Hygiene:** zero TODO/FIXME markers in shipped code; 9 `type: ignore` in the whole
  package; `git ls-files` shows zero tracked junk (the working-dir `_staging_tmp2/`,
  `scrap.txt` are untracked scratch; the ~121 MB snapshot tarball in `_staging_tmp2/`
  is worth deleting locally).
- One doc/code mismatch: `docs/10_standard/00_program_overview.md` §74 says "`io.py`
  is the only place dataclasses meet JSON/CSV", but 25 `open()` sites live in
  `sloads/export/` (R-24).

### 1.2 Maintainability — GOOD, with five growth hotspots

The pressure is size, not structure:

| File | Lines | Worst functions |
|---|---|---|
| `sloads/modules/balance.py` | 2,832 | `assemble` 146, `_closure` 128, `assemble_ground` 123 |
| `sloads/export/sbeam_bridge.py` | 2,701 | (14 of the package's 25 `open()` sites) |
| `sloads/report/content.py` | 2,609 | `_manifest_rows` 155 |
| `sloads/report/oracle_sections.py` | 2,457 | — |
| `sloads/io.py` | 1,910 | 95 `Any`-typed lines — more than the rest of the package combined |

Issue #17's numbers have drifted (`landing_reactions` is now 276 lines, not 200), and
new >140-line calc functions exist that #17 doesn't name (`envelope` 195 in
weight_envelope, `build_tail_span` 176, `_export_sbeam` 173 in cli.py) — R-22.
`balance.py` and `sbeam_bridge.py` are where every full-airplane change lands and are
the two candidates for package splits along their existing section boundaries (R-23).
The mypy ratchet plan (stage 2 `export/`, stage 3 `modules/`) skips `io.py`, which is
the schema boundary where a typing hole most directly becomes a silently wrong load
(R-25). Issue #16's four dead functions were re-verified consumer-free and can close
on a small deletion pass.

**Test architecture is strong**: 132 test files, tiny shared fixtures, and a complete
drift-guard inventory — every cross-cutting convention named in CLAUDE.md rule 3
(units, SF, case IDs, LIMIT channel, schema, layout, nav, set_page_config, CI shape,
doc currency, axes/equilibrium) has a live guard test. No unguarded convention was
found.

### 1.3 Development process and controls

**What is excellent** (and rare): `tests/test_ci_conformance.py` asserts the branch
protection snapshot, CI matrix, and three process docs against each other — including
guarding its own regexes against vacuity. `tests/test_doc_currency.py` bans volatile
literals from standard docs and checks the INDEX against the tree both ways. The
fragment→changelog machinery is pure, tested to byte-identity, and never hand-edited.
The sbeam roundtrip gate runs the real pinned solver with `SLOADS_REQUIRE_SBEAM=1` so
a missing solver fails rather than skips, and a weekly non-blocking drift workflow
tracks sbeam `main`.

**The systematic weakness: closure obligations are discipline-only, and discipline is
now the failing control.**

- **Design-note statuses are stale on 3 of the last 4 tier-L closures** (R-13). Notes
  46, 47 and 48 still read AGREED after their work shipped 2026-09-03/04
  (commits `cd72d70`, `b863dd`, `44c01e2`, `4eb0717`). The #128 guard only fires on
  explicit "unbuilt" phrasing, so a stale AGREED sails through — and the release
  process rolls notes to history **by status header**, so unflipped notes get skipped
  by the roll and a wrong status enters the permanent record.
- **The release tag is not gated on the main-push full matrix being green** (R-14),
  and this has already bitten: 0.8.0 was tagged while main's full-matrix run was red
  at install on 3.9 (#132). The classifier half was fixed; the tag-on-red-main half
  was not.
- **Tier assignment and tier content are self-declared** (R-15). `solo_close.sh`
  checks that a fragment exists and its lead says "tier X"; nothing verifies a
  physics change got tier L, that tier M updated `PROGRAM_SPEC.md`, or that tier L
  added a theory citation. A physics change closed as tier S would pass every gate.
  Related: hand-git bypasses of the script are visibly degrading the commit-subject
  record (`0fdce9a` has a bare issue number as its whole subject; `fb781dd`/`4ed017e`
  carry doubled parentheticals).
- **Benchmark-first has no presence guard** (R-16): no test asserts that a newly
  registered module carries an oracle or closure test at all.
- Smaller: INDEX rows have grown into ~600-word decision summaries carrying a second
  hand-maintained copy of each note's status — already drifting in step with R-13
  (R-17); sbeam-drift failures notify nobody actively (R-18); the backlog header's
  open-notes list is wrong, `DEVELOPMENT_PROCESS.md` §5's "nothing else" claim is
  contradicted by the plan files, and `GIT_FLOW_GUIDE.docx` is an unguardable process
  doc in the standard tree (R-19).

**Process weight:** for a solo project the drift-guard investment is paying for
itself (the guards demonstrably catch real defects) and the design-note discipline is
doing real work — note 46 caught a 151/190/120 % torsion defect and note 49 caught the
LIMIT-report defect before code. The genuinely over-heavy parts are the four
restatements of the git flow (only two cross-guarded) and the INDEX transcription
labor (negative control value — it creates drift). Nothing else is worth cutting.

---

## 2. Phase 2 — Analysis method and output

### 2.1 Accuracy and oracle deviations (input → output)

**Oracle coverage matrix: complete.** Every FAR23-core module with printed Appendix A
figures is oracle-locked at ±0.1% with page citations (engine, weight_estimate,
weight_onecg, wing_geometry, weight_envelope, structural_speeds, mach_limit, airloads,
flight_envelope, select, balloads, wing_inertia, net_loads, taildist, aileron, flap,
tab, landing). Every module without a printed oracle has a stated closure gate
(balance, body_loads, tail_span, one_engine_out, concept modules). **No module has
neither.** The weak spots are the ones the project itself declares in
`00_theory_sources.md`: `one_engine_out` and the engine FAR 25 supplemental cases are
formula-vs-formula (the closure re-types the same .BAS lines the port came from — a
transcription error would agree with itself), and the AIRLOAD4 swept-CL renormalizer
is checked partly against its own target. These remain the most exposed families until
Appendix B (#20) or any independent worked example is in hand.

**Corrections register: code matches.** All four spot-checked deviations
(23.361(a)(1) takeoff-torque factor, 23.427(a) restored candidate set, LANDLOAD
#133/#134 sign derivation, WINGGEOM closed-form) are implemented exactly as
registered, with citations in code. But the **deliverable-facing methods statement is
4 entries behind the register** (R-3): `sloads/report/methods.py` lists only the three
2026-08-16-era corrections; the truncated-constants entry, LANDLOAD #133/#134, and
the WINGGEOM closed-form entry — the three that change printed-page numbers a reader
would compare — are missing, and the guard at `tests/test_methods_stamp.py:110` is
circular (statement vs its own source tuple), so CI cannot see the drift. In the
project's own P-2 vocabulary this is a P-2-shaped gap on the highest-visibility
surface.

**Tolerance discipline: near-uniform.** Everything oracle-shaped is at 1e-3 except
four assertions in `test_structural_speeds.py` (2e-3–1e-2) sitting uncommented in a
file whose header claims ±0.1% — almost certainly rounding-limited by 3-digit printed
values, but the justification is unstated (R-4). Every other looser tolerance found
carries an inline reason (SELECT CL inherits FLTLOADS convergence ±0.005; Euler
step-halving; cross-route consistency checks that are not oracles).

**Concept mode:** the reduction test is maximal strength (bit-for-bit identity on GA
inputs) and the closure lattice is deep — wing lift = n·W at 1e-6, nodal sums = root
shear at 1e-9, mass partition at 1e-12, export equilibrium at 1e-6, and the external
solver closing the loop. The stated residual exposure: closure gates verify resultants
and first moments, not distribution *shape* off-GA planforms — a wrong Schrenk/swept
redistribution preserving ∫load and ∫y·load would pass. Documented, ranked, not a
defect; noted here for the record.

**Independent verification performed by this review:** global equilibrium of the
shipped balanced decks re-derived from the card text alone closed at ≤2.2e-6
normalized on all 44 subcases × 3 deck exports (GA6 Imperial/SI, concept regional
jet). The SI deck's header correctly states the consistent-unit channel
(N, mm, N·mm, MPa) and the reasoning for it.

### 2.2 Safety-factor application

**The core contract holds.** Modules always emit LIMIT; the factor rides the result
(`safety_factor` carrier) from one governing table; each output surface multiplies
exactly once at its own boundary; `ULT SF=1.0` cases are stored unfactored with
SF=1.0 so the single multiply cannot over-factor. **No double-application path was
found.** Surface assignment matches the contract on every surface checked (decks
ULTIMATE, CLI/app LIMIT-stated, oracle_app frozen ULTIMATE), the `-ULT` marker
behaves, `N/A` renders for factorless conditions, and the unclassifiable-case path
really does flag rather than default (zero defaulted rows asserted on every shipped
fixture).

**Edge findings:**

- **R-8 — the #170 class is three rows, not one.** "Max continuous torque"
  (`engine.py:297`) and "Max accelerating torque" (`engine.py:554`) are the same
  machine-characteristic class as the filed mean-takeoff-torque row and are equally
  factored on ULTIMATE surfaces. Balance-closure residual diagnostics
  (`balance.py:2759/2764`) are the same class again — factored and marked `-ULT`
  despite being equilibrium-quality diagnostics. #170's fix should cover the class by
  construction (`quantity` flag on `LoadValue`), not the one row.
- **R-6 — unstamped single-module runs.** `oracle_app/results.py:214` (and
  `app/views/aircraft_comparison.py:73`) call modules directly without `stamp()`:
  a project SF override is silently ignored on those blocks, and non-load conditions
  keep the dataclass default 1.5 instead of the stamped `None` — the #154 defect
  surviving on one surface. Partly deliberate (OR-77 freeze), but "an override is
  silently not honored" is the one thing the G-11 mitigations promise never happens.
- **R-9 — `_EXACT` classifier bypass.** An exact-match reference returns before the
  multi-reference agreement check, so a compound string naming a LIMIT section plus
  the exact ultimate section would silently take the unconservative 1.0. No current
  producer emits such a string — latent, one-line fix.
- **R-7 — wrong basis text.** The `engine_ultimate` row (`safety_factors.py:134-137`)
  describes 23.367(a)(2) as "the sudden-stoppage torque case"; 23.367 is engine
  *failure* (compressor disconnection), and sudden stoppage is 23.361(b)(1), a LIMIT
  case in this suite. Factor is right; prose on a certification-facing table is wrong,
  and `models/results.py:134` repeats it.
- **R-10 — two surviving `getattr(..., ULTIMATE_FACTOR)` fallbacks**
  (`content.py:1539`, `oracle_sections.py:2099/2291`) — the exact pattern M4-16
  banned from the export side; dead today, which is when a rename silently resurrects
  a flat 1.5.
- **R-11 — no detail-factors statement.** The report ships a "Wing-attach fitting
  loads" table as ULTIMATE with only the case SF; a reader could take those as fitting
  design loads without 23.625's 1.15. One sentence in the methods statement fixes it.
- **R-12 — the 0.8.3 plan contradicts itself.** Note 49's gate G-OR-49 ("no
  `sloads/report/**` path multiplies") is unsatisfiable as written because OR-93 keeps
  the summary report ULTIMATE and its multiplies live in `report/content.py`, which
  the §5.1 change table omits. Fix the note before implementation starts.

### 2.3 Deliverables — accuracy and analyst usability

**What a third-party analyst gets right now is genuinely good**: every CSV and deck
opens with a complete METHODS AND LIMITATIONS statement (status, LIMIT/ULTIMATE
basis, units, category applicability, verification pedigree, known limitations with
quantified conservatism directions); the balanced deck maps every SUBCASE to its case
identity, V-n point, CG and Nz in the header, mints stable subcase IDs from case
identity rather than position, and **itemizes the conditions it does not assemble,
each with its reason** — this is better condition-traceability than most commercial
loads output. The wing bundle (span CSV + loads deck + optional stick model) and the
1.8 s consolidated LaTeX report round out a coherent deliverable set.

**Usability defects found by actually consuming the deliverables cold:**

- **R-1 (CRITICAL) — LRA decks that don't solve.** `sloads --export-sbeam X
  --export-target lra` on `ga6_normal` produces a deck the pinned solver rejects
  (`RBE2 12006: GN=7605 DOF 1 is a dependent DOF of another constraint element` —
  GRID 7605 is dependent in RBE2 12003 and then independent in RBE2 12006/12007, a
  chain sbeam forbids). `cessna_210`'s LRA deck fails singular. The roundtrip LRA leg
  is parametrized over `SOB_MATRIX = (concept_regional_jet, atr42_100)` only — the
  docstring notes ga6/concept_heavy "have no body data and ship no SOB node, by
  design", but the CLI neither refuses nor warns for them (contrast `concept_heavy`,
  which is properly refused with a stated reason at the export boundary). Either the
  no-body-data LRA export must refuse with a stated absence (the BM-1 posture), or
  the skeleton must be fixed to solve and the fixtures added to the gate.
  `dhc8_dash8` and `baron_58` solve fine, so the defect is fixture-conditional.
- **R-2 (MAJOR) — the balanced deck invites a solve it cannot survive.** The primary
  deliverable is an elementless load-on-node-cloud (0 CBARs, 168 GRIDs, 10,390 FORCE
  cards) — correct by design, but it carries `SOL 101` and `SPC = 1`, and its 40-line
  limitations header never states that it has no stiffness and will not solve as
  delivered. A cold consumer's first action (`sbeam deck.bdf`) produces "Singular
  stiffness matrix: model may have unconstrained DOFs" — a misdiagnosis pointing at
  constraints, not at the missing elements. One header paragraph ("this deck is a
  load set on a node cloud; apply it to your own beam model or use the `lra` target /
  `--lra-import` for a solvable model") turns a wall into a signpost.
- **R-5** — the CLI's `24 condition(s) not assembled` stdout line doesn't say where
  the itemized list is (deck header line ~124); one clause in the message fixes it.
- Already filed, confirmed by this review as the top analyst-data items: **#165** (the
  GA6 wing export ships 3 cases, no negative-g — the delivered distributions do not
  envelop the wing) and **#164** (every delivered case states 0 ft where Appendix A
  names 12,000 ft — condition identity wrong on the deliverable even though the loads
  reproduce). And **#161** (`format_value` precision inconsistency) is real on the
  report surface.

### 2.4 Backlog and future development

Detailed tables in §4. Summary: 25 open issues + the parked file + 14 design notes
were triaged. The open set is coherent; backlog↔GitHub synchronization is intact
(`backlog_issues.py check` is working). The real problems: (a) ~60% of `00_backlog.md`
is stacked historical preambles, one of which now states falsehoods ("There is no
0.8.2 band and no 0.8.2 milestone"); (b) six shipped/closed notes (09, 11, 24, 32,
34, 45) were never archived and four live notes carry stale status headers
(44, 46, 47, 48); (c) the header's open-notes list omits notes 45–49 and includes a
closed one; (d) three CRITICAL defects (#164, #165, #170) and two USEFUL ones
(#161, #171) have no GitHub milestone, so GitHub and the defects index disagree on
scheduling state. The mission plan (note 01) is essentially complete — all 22 programs
ported and the balanced free-free model shipped at 0.6.0 — so the plan file deserves a
"phase complete" banner instead of reading as active work.

---

## 3. Verdicts by review area

| Area | Verdict |
|---|---|
| a) Analysis-method accuracy and oracle deviations | **Strong.** Complete oracle/closure coverage, register matches code, independent equilibrium check passes. One deliverable-facing drift (methods statement, R-3); the known formula-vs-formula exposure on twin-only cases is honestly declared and remains the top residual risk. |
| b) Safety-factor application | **Sound core, defect class at the edges.** Applied-once verified everywhere; findings are misclassified non-loads (R-8), one bypassed surface (R-6), one latent classifier hole (R-9), and prose errors (R-7). |
| c) Deliverables accuracy and usability | **Accurate; two real usability defects.** No wrong number found; LRA decks that don't solve on two fixtures (R-1) and the unexplained elementless balanced deck (R-2) are the gaps between "correct" and "usable cold". |
| d) Backlog/future development | **Content healthy, hygiene overdue.** Verdicts and ordering in §4; one cut-hygiene pass (R-20) resolves most of the perceived bloat. |

---

## 4. Backlog triage

Verdicts: **CRITICAL** = corrects an error or provides needed analyst data;
**USEFUL** = significant efficiency/accuracy improvement; **NICE** = nice-to-have;
**NOT-NEEDED** = not needed now (park or drop). Rule 6 (effect vs error bar) applied
throughout.

### 4.1 Open GitHub issues

| # | Title (short) | Now | Verdict | Proposed milestone | Rationale |
|---|---|---|---|---|---|
| #151 | Oracle technical report (note 44) | 0.8.2 | CRITICAL | 0.8.2 | The milestone *is* this item; §3+ sections, WE-8 figure, appendices remain. |
| #160 | Baron 58 fin symmetric+zero-based | 0.8.2 | USEFUL | 0.8.2 | Loads unaffected (proven), but the shipped §2.1 figure is visibly wrong; correctly the OR-11 end-of-report pass. |
| #165 | GA6 wing set has no negative-g case | — | CRITICAL | 0.8.3 | Delivered wing distributions do not envelop the wing. Merge with #164 (one V-n renumber). |
| #164 | ga6_normal balances at sea level only | — | CRITICAL | 0.8.3 | Wrong stated condition identity on every deliverable case. Merge with #165. |
| #170 | Mean takeoff torque factored | — | CRITICAL | 0.8.3 | Extend to the 3-row class (R-8); sequence inside the note-49 thread (same predicate as `prescribes_factor`). |
| #156 | Tail geometry from boundary lines | 0.8.3 | USEFUL | 0.8.3 | Well-specified; correctly gated on the freeze lift. |
| #161 | `format_value` precision/notation | — | USEFUL | 0.8.3 | Report-surface credibility; ride the baseline-regeneration wave. Design note first. |
| #171 | Two examples at 1-space JSON indent | — | USEFUL | 0.8.3 | One commit, early in the branch before anything re-stamps examples. |
| #163 | No flaps-down span load (OR-53) | — | NOT-NEEDED (as filed) | 1.0.0 | By rule 6 it cannot be ranked until the delivered-load effect number exists; the open action is *produce the number*. |
| #148 | No-op Apply still writes | 0.9.0 | CRITICAL | 0.9.0 (first) | Silently erases a shipped input on two fixtures — outranks every [V] row in the milestone. |
| #29 | GUI review vs deliverables | 0.9.0 | USEFUL | 0.9.0 | The milestone anchor; its re-cut promotes parked M4-11b, L-8c/d/e/f. |
| #78 | Mass-item seeding/hardening | 0.9.0 | USEFUL | 0.9.0 | Open half is a destructive-button data-integrity gap. |
| #130 | oracle form reaches `fr._locate` | — | NICE | 0.9.0 | When `field_registry` is next touched (GUI work). |
| #111 | Wing fuel is a point mass | 1.0.0 | USEFUL | 1.0.0 | Owner-requested; real fidelity defect for wet-wing concepts; design note first. |
| #92 | Split whole-pipeline tests | — | NICE | 0.9.0 | Re-aimed at the CI coverage leg; milestone hygiene. Title contains a literal newline — fix when touched. |
| #47 | Cert-basis / case-coverage matrix | 1.0.0 | USEFUL | 1.0.0 | Mission-credibility deliverable; generated + drift-guarded. |
| #32 | Past-fit coefficients unmarked | 1.0.0 | USEFUL | 1.0.0 | 0/9 affected rows SELECTed; marking-only. |
| #31 | Ground per-station fuselage view | 1.0.0 | NICE | 1.0.0 | Consumer-gated (no frame-sizing consumer yet). |
| #14 | Aileron lift increment lumped | 1.0.0 | NICE | 1.0.0 | Decision of record; consumer-gated; absence stated on decks. |
| #19 | mypy ratchet stages 2–3 | — | NICE | 1.0.0 (opportunistic) | Add `io.py` to the plan (R-25). |
| #18 | 2026-08-10 minor findings sweep | — | NICE | 1.0.0 (standing) | Explicitly opportunistic. |
| #17 | Calc-side function size | — | NICE | 1.0.0 | Re-cut with current numbers (R-22); view half folds into #29/M4-11b. |
| #16 | Dead code | — | NICE | 0.9.0 | List re-verified current by this review; small deletion pass. |
| #15 | Deck-writing primitives out of sbeam_bridge | — | NICE | 0.8.3 | Do WITH note 49 — it rewrites the same `_sf`/`_sf_str` helpers. |
| #20 | D-5 Appendix B twin fixture | — | NOT-NEEDED (blocked) | none | A question to the user, not schedulable work. |

### 4.2 Parked items (`02_parked.md`)

Verdicts: **stay parked** — M4-10b, F25 pack (→2.0.0), L-2, L-3 (correctly held: the
naive fix breaks the oracle −47%), L-4, L-5, L-6, L-7, L-8h (parked *with* its
number — the model entry), L-9 (blocked on #20), M4-19, M4-21, M4-4, M4-3(a)(c),
M4-8 Layer 2 (revisit after note 49), CG-dependent MTOW, upset criterion, Mach margin,
flutter-Mach, gust-Δα (parked with number 0 — exemplary), OpenVSP/deeper-sbeam/DER
placeholders.

**Promote at #29's re-cut** (they are pre-assigned there, not really parked):
M4-11b, L-8b, L-8c, L-8d (mutation half), L-8e, L-8f — move them into the 0.9.0 band
so the parked file returns to meaning "off-mission".

**Revive cheap:** `concept_heavy` gear geometry — tier S fixture data, and the only
way the never-fired 23.473(g) floor warning and a sixth gear-report fixture get
exercised. Ride any 0.8.3+ fixture-touching session.

**Rule-6 hygiene (R-21):** M4-19, M4-21, M4-4 are parked without the number that
parks them (M4-19 quotes a coefficient error, not a delivered-load effect — likely 0
since the term is off by default; state that). The step-14 indeterminate-path half is
parked with neither body nor number — give it a stub or delete the mention.

### 4.3 Notes hygiene

- **Archive to `40_history/` at the 0.8.2 cut:** 09 (closed 2026-08-13, still listed
  as open), 11 (status frozen at 2026-08-08; residue is #14), 24 (all amendments
  applied), 32 and 34 (both say "rolls at the 0.8.0 cut" — 0.8.0 was cut 2026-08-28),
  45 (SHIPPED; WE-8 belongs to #151).
- **Fix status headers now:** 46, 47 → SHIPPED (work landed 2026-09-03); 48 → 0.8.2
  half SHIPPED with a pointer to 49 for the OR-85/86 deferrals; 44's "nothing built"
  header is stale against iterations 1–2 shipped.
- **Live and correct:** 49 (the 0.8.3 spine — after fixing R-12), 21 (properly
  PARKED), 01 (add a "phase complete" banner).
- **Contradictions to remove:** backlog header's open-notes list ("09/11/21/24/32/
  34/44" — includes a closed note, omits 45–49); the 2026-08-29 preamble's "there is
  no 0.8.2 milestone"; note 03's pointer to a "Phase G" that no longer exists.
- **Backlog file:** roll everything before the current re-cut (~lines 43–450 of
  history/preambles) into a `40_history/` narrative file per the file's own
  precedent. This alone removes ~60% of the file.

### 4.4 Recommended ordering

**0.8.2 (close the milestone; add nothing except hygiene):**
1. #151 — finish the report. 2. #160 — the OR-11 Baron pass. 3. R-3 — the methods
statement register catch-up (it is report-milestone content and analyst-facing).
4. R-20 — the cut-hygiene pass (archive notes, fix statuses, roll preambles,
milestone the unmilestoned defects). 5. R-14 — add the tag-gate precondition to
RELEASE_PROCESS §4 *before* this cut uses it.

**0.8.3 (the stated-never-applied milestone):**
1. Fix note 49's R-12 contradiction, then the note-49 endpoint (OR-85/86).
2. #170 extended to the R-8 class, inside the note-49 thread. 3. #15 with the note-49
export sweep. 4. R-1 — the LRA refuse-or-fix decision (first-order deliverable
defect; the freeze lift opens the producers). 5. R-2 — balanced-deck header
paragraph. 6. #164+#165 merged — the GA6 altitude/case-set decision (renumber the V-n
matrix once). 7. #156. 8. #161 (note first). 9. #171 early. 10. R-6, R-7, R-9, R-10,
R-11 — the SF edge sweep (same code region, same session as note 49). 11. R-16 —
the module-must-have-oracle guard. 12. R-18 — sbeam-drift auto-issue.

**0.9.0:** #148 first (shipped-input defect), then #29 (promoting M4-11b, L-8c/d/e/f),
#78, #130, #16, #92; R-15 (closure-content checks in solo_close) as milestone
hygiene.

**1.0.0:** #111 (note first), #47, #32, #31, #14, #163 (produce the number, then
rank), #17 re-cut, #19 (+io.py), R-23 (package splits) opportunistically.

**2.0.0 / stay parked:** F25 pack + VB cluster (L-4/F25-1/Mach-margin as one "gust
pack" when revived), power-effects wake (note 21), M4-19/21/4, M4-8 L2, CG-MTOW,
upset, flutter-Mach, OpenVSP, deeper sbeam, methods manual/DER.

---

## 5. Findings register and issue commands

Notes on use: run one command at a time. Bodies carry the tier suggestion. Milestones
assume `0.8.3`, `0.9.0`, `1.0.0` exist (they do). Findings marked *fold* are additions
to existing issues (a `gh issue comment`), not new issues. Cut-hygiene items are
bundled into one issue (R-20) to avoid ticket confetti.

### R-1 · CRITICAL · LRA decks for ga6_normal and cessna_210 do not solve — and the gate cannot see it

```bash
gh issue create --milestone 0.8.3 --title "LRA decks for ga6_normal and cessna_210 fail to solve in the pinned sbeam; the roundtrip LRA leg excludes exactly those fixtures" --body "$(cat <<'EOF'
Tier L candidate (design note first: refuse vs fix is a contract decision).

**Defect.** `sloads --export-sbeam X --export-target lra examples/ga6_normal.project.json` writes a deck the pinned solver (ed23b26) rejects:

    Solver error: RBE2 12006: GN=7605 DOF 1 is a dependent DOF of another constraint element

GRID 7605 is the dependent node of RBE2 12003 (`RBE2, 12003, 7801, 123456, 7605`) and then the independent node of RBE2 12006/12007 — a constraint chain sbeam forbids. `cessna_210`'s LRA deck fails differently: "Singular stiffness matrix". `dhc8_dash8`, `baron_58`, `concept_regional_jet`, `atr42_100` all solve; `concept_heavy` is properly refused at export ("no side of body resolves… BM-1").

**Gate blindness.** `tests/test_sbeam_roundtrip.py` `test_the_lra_model_solves_and_reacts_only_the_residual` is parametrized over `SOB_MATRIX = (concept_regional_jet, atr42_100)` only. The docstring says ga6/concept_heavy "have no body data and ship no SOB node, by design" — but the CLI still exports for ga6_normal and cessna_210 instead of refusing, and the exported deck is broken. The mission claim is "the exported deck solves in sbeam"; for this family on these fixtures it does not.

**Fix direction (decide in the note):** either (a) the LRA export refuses with a stated absence when the skeleton cannot be well-posed (the BM-1 posture concept_heavy already gets), or (b) the no-body skeleton is fixed (collapse the RBE2 chain: make 7801 or a common independent node own all dependents) and ga6_normal/cessna_210 join the solve matrix. Either way, every fixture the CLI will export for must be in a solve gate — the current matrix hole is the control failure that let this ship.

Found by the 2026-09-04 project review (review.md R-1).
EOF
)"
```

### R-2 · MAJOR · The balanced deck invites a solve it cannot survive, and never says so

```bash
gh issue create --milestone 0.8.3 --title "Balanced deck is an elementless load cloud but carries SOL 101 + SPC and no statement that it will not solve as delivered" --body "$(cat <<'EOF'
Tier M (behavior of an existing deliverable's stated contract; header + spec touch).

The primary deliverable (`--export-target balanced`) is by design a load set on a node cloud: 0 elements, 168 GRIDs, 10,390 FORCE cards on ga6_normal. But the deck carries `SOL 101` and `SPC = 1`, and its KNOWN LIMITATIONS header (which covers the wing-stick clamp, pressurization, ground families…) never states the deck has no stiffness. A cold consumer's first action — `sbeam deck.bdf` — yields "Singular stiffness matrix: model may have unconstrained DOFs", a misdiagnosis pointing at constraints rather than the missing elements. This review hit that wall and only found the explanation in `tests/test_sbeam_roundtrip.py::_assembled_deck`'s docstring.

Fix: one KNOWN LIMITATIONS paragraph in the balanced-deck header: this deck is a load set on a node cloud; apply it to your own beam model (the `$ SLOADS-NODE` families map it), or use `--export-target lra` / `--lra-import` for a solvable model; the roundtrip gate solves it by wrapping it in a stick tree. Consider also whether SOL 101 belongs in a deck that is not meant to be solved bare, or a `$ NOT SOLVABLE AS-IS` sentinel above it.

Found by the 2026-09-04 project review (review.md R-2), by consuming the deliverable cold.
EOF
)"
```

### R-3 · CRITICAL (deliverable-facing) · Methods statement is 4 corrections behind the register; guard is circular

```bash
gh issue create --milestone 0.8.2 --title "methods.py APPROVED_CORRECTIONS lists 3 of 7 register entries; test_methods_stamp guard is circular and cannot see the drift" --body "$(cat <<'EOF'
Tier M (report/spec surface; guard change).

`sloads/report/methods.py:72-86` declares only 23.361(a)(1), 23.361(a)(3), 23.427(a). Missing from the statement shipped on every CSV and deck: the truncated-constants-go-exact entry (2026-08-17), LANDLOAD #133 and #134 (2026-08-29), and the WINGGEOM closed-form entry (2026-08-30) — the last three change printed-page numbers an analyst would compare against the manual. The module's own docstring: "a correction that is not declared here is invisible to the analyst… which is the whole point of declaring it." The header text still says "The three approved deviations".

The guard `tests/test_methods_stamp.py:110` (`test_statement_lists_every_approved_correction`) checks the rendered statement against the same `APPROVED_CORRECTIONS` tuple it is rendered from — circular, so CI is blind to this drift (a P-2-shaped gap in the project's own vocabulary).

Fix: add the four entries, and re-point the guard at the register — parse `docs/20_theory/02_approved_corrections.md` for its `### … (approved …)` headings and assert the statement covers them (the doc-currency test family already does this kind of parsing).

Proposed 0.8.2 because it is report-milestone, analyst-facing content; if the freeze rules say otherwise, first slot of 0.8.3.

Found by the 2026-09-04 project review (review.md R-3).
EOF
)"
```

### R-4 · LOW · Four oracle tolerances looser than the file's stated ±0.1%, unjustified inline

```bash
gh issue create --milestone 0.8.3 --title "test_structural_speeds: four assertions at 2e-3..1e-2 in a file headed ±0.1%, with no inline rounding-limited justification" --body "$(cat <<'EOF'
Tier S.

`tests/test_structural_speeds.py:55,82` (W/S, VC_min 141.8) at 2e-3; `:88-89` (MC 0.323 / MD 0.403) at 3e-3; `:284` (mach_margin) at 1e-2 — all inside a file whose header claims ±0.1% relative. Almost certainly rounding-limited by 3-digit printed values (and mach_margin is a small difference of large numbers), but unlike every other loose tolerance in the suite (SELECT CL, Euler convergence — all justified inline) these carry no comment. Add the one-line justification, or tighten where the printed precision allows.

Found by the 2026-09-04 project review (review.md R-4).
EOF
)"
```

### R-5 · LOW · CLI "N condition(s) not assembled" doesn't point at the itemized list

```bash
gh issue create --milestone 0.8.3 --title "Balanced-export CLI message states a count of unassembled conditions without pointing at the deck's itemized list" --body "$(cat <<'EOF'
Tier S.

`Wrote 44 balanced case(s) to: X.balanced_airframe.bdf; 24 condition(s) not assembled` — the deck header itemizes all 24 with per-condition reasons (excellent), but the stdout line gives no pointer. Append "…(itemized with reasons in the deck header)" so the analyst knows the answer already exists.

Found by the 2026-09-04 project review (review.md R-5).
EOF
)"
```

### R-6 · MEDIUM · Unstamped single-module runs bypass the governing SF table

```bash
gh issue create --milestone 0.8.3 --title "oracle_app per-module blocks render unstamped results: SF overrides silently ignored, #154 banner survives on that surface" --body "$(cat <<'EOF'
Tier M. Sequence inside the note-49 / 0.8.3 thread (the freeze lift opens the files).

`oracle_app/results.py:214` (and `app/views/aircraft_comparison.py:73`) call `registry.get(name)(project)` directly with no `stamp()`. Consequences on the oracle GUI (ULTIMATE channel default): (a) a project `safety_factors.overrides` entry is silently ignored on per-module blocks — the one thing the G-11 mitigations promise never happens; (b) non-load conditions keep the dataclass default 1.5 instead of the stamped None, so the SF column states a factor for conditions that prescribe none (#154 surviving on one surface); (c) #170's torque rows are factored here (554.4 → 831.6).

Fix: stamp at these call sites (or make the registry entry point stamp unconditionally so an unstamped render becomes impossible — the structural fix per CLAUDE.md rule 3).

Found by the 2026-09-04 project review (review.md R-6).
EOF
)"
```

### R-7 · MEDIUM · engine_ultimate basis text names the wrong FAR case

```bash
gh issue create --milestone 0.8.3 --title "safety_factors.py engine_ultimate basis mislabels 23.367(a)(2) as the sudden-stoppage case" --body "$(cat <<'EOF'
Tier S (prose on a certification-facing table; factor value is correct).

`sloads/safety_factors.py:134-137` says "23.367(a)(2) prescribes the sudden-stoppage torque case as an ULTIMATE load." 23.367 is unsymmetrical loads due to engine FAILURE (the project's own `report/coverage.py:130`), and (a)(2) is the compressor-disconnection / turbine-blade-loss case — exactly what `modules/one_engine_out.py:330-336` calls it. Sudden stoppage is 23.361(b)(1), a LIMIT case in this suite (`modules/engine.py:391`). `models/results.py:134` repeats the wrong pairing. Fix both prose sites.

Found by the 2026-09-04 project review (review.md R-7).
EOF
)"
```

### R-8 · MEDIUM · *fold into #170* — the non-load-factored class is wider than one row

```bash
gh issue comment 170 --body "$(cat <<'EOF'
2026-09-04 review (review.md R-8): the class this issue names is three rows wide plus a diagnostics family, not one row. Same defect, same fix site:

- `engine.py:297` "Max continuous torque" and `engine.py:554` "Max accelerating torque" — machine-characteristic ratings in ft-lb, factored 1.5x on ULTIMATE surfaces exactly like the filed mean-takeoff-torque row.
- `balance.py:2759,2764` "Residual Fz (pre-closure)" / "Residual My (pre-closure)" — equilibrium-quality diagnostics in lb / lb-in; factored and marked -ULT, and eligible for load-extremes tables via `_load_dimension`. Proportional so not unsafe, but a residual stated in -ULT units misdescribes it.

The fix should cover the class by construction (a `quantity` flag on `LoadValue`, per the units.py docstring "the fix belongs to this function"), not enumerate rows. Sweep per CLAUDE.md rule 4 when closing. Also note prescribes_factor / note 48 OR-83 shares the predicate — sequence inside the note-49 thread.
EOF
)"
```

### R-9 · LOW-MED · `_EXACT` classifier match bypasses the factor-agreement check

```bash
gh issue create --milestone 0.8.3 --title "safety_factors classify: exact-match reference returns before the multi-reference agreement check — latent unconservative slip-through" --body "$(cat <<'EOF'
Tier S/M (one-line logic fix + guard test).

`sloads/safety_factors.py:238-242`: an `_EXACT` hit returns immediately, so a compound reference like "23.361(a)(1) / 23.367(a)(2)" resolves to `engine_ultimate` (SF 1.0) outright, where the equivalent all-range compound with disagreeing factors would be flagged unclassified. A combined case naming a LIMIT section plus the exact ultimate section would silently take the unconservative 1.0. No current producer emits such a string (checked) — latent, but it is the one hole where "flagged, never defaulted" degrades to "silently first-match". Fix: after an exact hit, still classify the remaining references and demand factor agreement; add the guard case.

Found by the 2026-09-04 project review (review.md R-9).
EOF
)"
```

### R-10 · LOW · Two surviving `getattr(..., ULTIMATE_FACTOR)` silent fallbacks

```bash
gh issue create --milestone 0.8.3 --title "report side keeps two getattr(..., ULTIMATE_FACTOR) fallbacks the M4-16 rule banned from export" --body "$(cat <<'EOF'
Tier S (sweep per CLAUDE.md rule 4; do with the note-49 report-side work).

`report/content.py:1539` and `report/oracle_sections.py:2099,2291` default a missing `safety_factor` attribute to 1.5. `sbeam_bridge._sf` (:224-226) forbids exactly this ("no getattr fallback that would mask an attribute rename") and the safety_factors module docstring records removing the pattern. The fields are typed on every result today, so the defaults are dead code — which is precisely when a rename would silently resurrect a flat 1.5. Replace with direct attribute access.

Found by the 2026-09-04 project review (review.md R-10).
EOF
)"
```

### R-11 · LOW · No detail-factors statement on the fitting-loads table

```bash
gh issue create --milestone 0.8.3 --title "Methods statement / wing-attach fitting table: state that Subpart D detail factors (23.625 fitting 1.15 etc.) are the consumer's responsibility" --body "$(cat <<'EOF'
Tier S.

The governing table correctly carries no Subpart D detail-factor rows (they apply at part sizing), but the report ships "Wing-attach fitting loads" as ULTIMATE reactions with only the case SF — a reader could take those as fitting design loads without 23.625's 1.15. One sentence in the methods statement (and/or the table caption): detail factors — castings 23.621, bearings 23.623, fittings 23.625, hinges — are not applied and are the consuming analysis's responsibility. Pairs naturally with R-3's methods-statement update.

Found by the 2026-09-04 project review (review.md R-11).
EOF
)"
```

### R-12 · MEDIUM · Note 49's gate contradicts its own OR-93 — fix before implementation

```bash
gh issue create --milestone 0.8.3 --title "Note 49: gate G-OR-49 (no report/** multiply) is unsatisfiable while OR-93 keeps the summary report ULTIMATE via report/content.py" --body "$(cat <<'EOF'
Tier S (note amendment, before any 0.8.3 implementation starts).

`docs/30_future/49_stated_never_applied_note.md:356` gates "no `sloads/report/**` path multiplies by a safety factor, the export package being the only one that may" — but OR-93 (:303, :343) keeps the summary report ULTIMATE, and that report's multiplies live in `report/content.py` (`Units.load_value` :373-376, plus the inline sites at :1546, :1809), which the §5.1 change table does not list. As written, either the gate fails on day one or content.py's scaling must migrate under export/ — a refactor the plan doesn't budget. Amend the note (re-scope the gate, or add the content.py migration to §5.1 with its cost) while it is still AGREED-not-started.

Found by the 2026-09-04 project review (review.md R-12).
EOF
)"
```

### R-13 · MEDIUM · Tier-L note-flip closure rule violated 3×, no guard, and unflipped notes escape the history roll

```bash
gh issue create --milestone 0.8.2 --title "Design-note statuses stale on 3 of last 4 tier-L closures; add a guard (history fragment citing note N => note N marked SHIPPED)" --body "$(cat <<'EOF'
Tier S+guard.

Notes 46, 47, 48 still read AGREED after their work shipped (commits cd72d70, b863dd, 44c01e2, 4eb0717, 2026-09-03/04); note 44's header still says nothing built against iterations 1-2 shipped. The #128 guard (`tests/test_doc_currency.py:212`) only fires on explicit "unbuilt" phrasing, so a stale AGREED passes CI — and RELEASE_PROCESS §4 step 3 rolls notes to 40_history BY STATUS HEADER, so unflipped notes are skipped by the roll and a wrong status enters the permanent record.

Fix: (a) flip 44/46/47/48 now (the R-20 hygiene pass); (b) extend the #128 guard — a note whose number is cited by a `changes/*.history.md` fragment must carry SHIPPED/BUILT in its Status line; the `_fragments_citing` machinery already exists in the same test file.

Found by the 2026-09-04 project review (review.md R-13).
EOF
)"
```

### R-14 · MEDIUM · Release tag not gated on the main-push full matrix — already bit once (0.8.0/#132)

```bash
gh issue create --milestone 0.8.2 --title "RELEASE_PROCESS §4: gate the tag on the merge push's full-matrix run on main being green" --body "$(cat <<'EOF'
Tier S (process doc + one scripted check). Do BEFORE the 0.8.2 cut uses §4.

The compatibility legs (3.10/3.11) and the coverage floor run only on the push to main, "fixed forward" — but §4 step 4 tags immediately after the merge with no requirement that that run is green. This already happened: 0.8.0 was tagged while main's full-matrix run was red at install (#132). The classifier half was fixed; the tag-on-red half was not. Add a step-4 precondition — "the merge push's run on main is green (`gh run list --branch main --limit 1`)" — and put it in the scripted release checks alongside `branch_protection_snapshot.py --check`.

Found by the 2026-09-04 project review (review.md R-14).
EOF
)"
```

### R-15 · MEDIUM · Closure-tier content obligations are discipline-only

```bash
gh issue create --milestone 0.9.0 --title "solo_close.sh verifies fragment existence but no tier-content obligations (spec touch for M, theory citation for L, note-first for physics)" --body "$(cat <<'EOF'
Tier M (script + guard design; a design note is probably warranted for what is checkable).

`scripts/solo_close.sh:216-248` checks a fragment exists and its lead says "tier [SML]"; nothing verifies that a tier-M closure touched PROGRAM_SPEC.md, that a tier-L closure added a theory_sources citation and ships a full-format history fragment, or that a physics change had a design note at AGREED first (solo "agreed in chat" leaves no artifact). A physics change closed as tier S with one fragment passes every gate today. Related symptom: hand-git bypasses are degrading the commit-subject record (0fdce9a's subject is a bare issue number; fb781dd/4ed017e carry doubled parentheticals) — the preflight should also validate the subject it is about to write.

Checkable subset worth automating: tier M/L fragment present => the same commit/PR touches PROGRAM_SPEC.md (M) / theory_sources.md (L); tier lead format validated; subject-line format validated. The unautomatable remainder (is the tier RIGHT?) stays discipline — but name it as such in DEVELOPMENT_PROCESS.

Found by the 2026-09-04 project review (review.md R-15).
EOF
)"
```

### R-16 · MEDIUM · Benchmark-first has no presence guard

```bash
gh issue create --milestone 0.8.3 --title "No guard that a newly registered module carries an oracle or closure test (benchmark-first is prose-only)" --body "$(cat <<'EOF'
Tier S+guard.

CLAUDE.md rule 2 makes an oracle test or a stated closure gate the definition of done for every module — but no test asserts a registered module HAS one. Cheap structural fix: a guard that walks `registry` and requires each registered name to appear in a tests/ file that asserts against a page-cited value or a named closure (a per-module manifest mapping module -> its gate test, drift-guarded, would also give the review-facing coverage matrix a single source).

Found by the 2026-09-04 project review (review.md R-16).
EOF
)"
```

### R-17 · LOW-MED · INDEX rows duplicate note decision summaries and statuses

```bash
gh issue create --milestone 0.8.2 --title "Cap docs/00_INDEX.md note rows at one line + pointer; stop carrying a second hand-maintained status per note" --body "$(cat <<'EOF'
Tier S (fold into the R-20 hygiene pass or do standalone).

Note 44's INDEX row (~600 words restating OR-13..OR-37 with its own copy of the status) and the 46/47 rows mirroring the stale AGREED are a second hand-maintained statement per note — exactly the drift class rule 3 exists for, and it is already drifting in step with R-13. Cap rows at one sentence + pointer, or generate the status half from each note's own Status line (doc-currency test machinery can check it either way).

Found by the 2026-09-04 project review (review.md R-17).
EOF
)"
```

### R-18 · LOW · sbeam-drift failures notify nobody

```bash
gh issue create --milestone 0.8.3 --title "sbeam-drift weekly workflow: file/update an issue on failure instead of relying on the Actions page" --body "$(cat <<'EOF'
Tier S.

`.github/workflows/sbeam-drift.yml` runs the roundtrip gate weekly against sbeam main, continue-on-error — but a failed scheduled run only shows on the Actions page nobody is forced to visit. Add a failure step that opens (or comments on) a pinned "sbeam drift" issue so drift becomes visible in the same place work is planned.

Found by the 2026-09-04 project review (review.md R-18).
EOF
)"
```

### R-19 · LOW · Small process-doc corrections (bundle)

```bash
gh issue create --milestone 0.8.2 --title "Process-doc corrections: backlog open-notes list, DEVELOPMENT_PROCESS §5 scope sentence, GIT_FLOW_GUIDE.docx, program_overview io.py claim" --body "$(cat <<'EOF'
Tier S bundle (fold into R-20's pass if preferred).

1. `docs/30_future/00_backlog.md` line ~14: open-notes list "09/11/21/24/32/34/44" includes closed 09 and omits 45-49. The INDEX guard makes a prose file list redundant — delete the list or point at the INDEX.
2. `DEVELOPMENT_PROCESS.md` §5 "30_future/ holds only 00_backlog.md, the live notes, and nothing else" — contradicted by the plan files and 02_parked.md; annotate for the solo profile.
3. `GIT_FLOW_GUIDE.docx` — an unguardable Word doc in 10_standard/ whose currency rests on a prose promise; retire it or demote it out of the standard tree (precedent: CR-D-4, two docs stating a dead setting).
4. `docs/10_standard/00_program_overview.md:74` "io.py is the only place dataclasses meet JSON/CSV" — 25 `open()` sites live in `sloads/export/`; scope the sentence to calc modules or say "io.py and export/".

Found by the 2026-09-04 project review (review.md R-19/R-24).
EOF
)"
```

### R-20 · The 0.8.2 cut-hygiene pass (highest-leverage single item)

```bash
gh issue create --milestone 0.8.2 --title "0.8.2 cut hygiene: archive shipped notes, fix stale statuses, roll backlog preambles, milestone the unmilestoned defects" --body "$(cat <<'EOF'
Tier S. The direct answer to "the backlog and notes are bloated and uncoordinated".

1. Fix status headers NOW: notes 46, 47 -> SHIPPED (work landed 2026-09-03); note 48 -> 0.8.2 half SHIPPED, pointer to note 49 for OR-85/86; note 44 header updated to reflect iterations 1-2 shipped.
2. Archive to 40_history/ at the cut: notes 09 (closed 2026-08-13), 11 (residue is #14), 24, 32, 34 (both said "rolls at the 0.8.0 cut" — 0.8.0 was cut 2026-08-28), 45 (SHIPPED; WE-8 belongs to #151), plus 46/47/48 once flipped.
3. Roll `00_backlog.md`'s historical preambles (~lines 43-450: "Where things stand" + six stacked re-cut preambles, one of which now states "there is no 0.8.2 milestone") into a 40_history/ narrative file per the file's own precedent. Leaves mission + current re-cut + priority table + defects index (~40% of current size).
4. Note 03: re-point its dead "Phase G" reference at #29/0.9.0. Note 01: add a "phase complete — open capability items are the backlog" banner.
5. Assign GitHub milestones so GitHub and the defects index agree: #164 -> 0.8.3, #165 -> 0.8.3 (merge them, see R-26), #170 -> 0.8.3, #171 -> 0.8.3, #161 -> 0.8.3, #148 stays 0.9.0, #16 -> 0.9.0, #15 -> 0.8.3.
6. Move the #29-pre-assigned parked rows (M4-11b, L-8b/c/d/e/f) from 02_parked.md into the 0.9.0 band so the parked file returns to meaning "off-mission".
7. Rule-6 hygiene in 02_parked.md: M4-19, M4-21, M4-4 get the delivered-load number that parks them (likely 0 for M4-19 — the term is off by default; say so, like the gust-delta-alpha entry does). The step-14 indeterminate-path mention gets a stub body or is deleted.
8. Delete the local `_staging_tmp2/` snapshot tarball (~121 MB, untracked).

Found by the 2026-09-04 project review (review.md R-20 / §4.3).
EOF
)"
```

### R-21 — covered inside R-20 item 7 (parked-without-number entries). No separate issue.

### R-22 · *fold into #17* — stale numbers, new offenders

```bash
gh issue comment 17 --body "$(cat <<'EOF'
2026-09-04 review (review.md R-22): re-cut this row with current numbers — `landing_reactions` is now 276 lines (sloads/modules/landing.py:452-727), not 200; `build_lra_model` stable at 337. New calc-side functions past the threshold this issue doesn't name: `envelope` 195 (modules/weight_envelope.py:220), `build_tail_span` 176 (modules/tail_span.py:1017), `_export_sbeam` 173 / `main` 158 (cli.py:185/403), `_manifest_rows` 155 (report/content.py:2277), `assemble` 146 / `_closure` 128 / `assemble_ground` 123 (modules/balance.py). View half (largest: `_tab_design_speeds` 401, app/views/structural_speeds.py:81) folds into #29/M4-11b per the existing plan.
EOF
)"
```

### R-23 · NICE (1.0.0) · Package-split balance.py and sbeam_bridge.py

```bash
gh issue create --milestone 1.0.0 --title "Split balance.py (2,832 lines) and sbeam_bridge.py (2,701) into packages along their existing section boundaries" --body "$(cat <<'EOF'
Tier S per move (pure moves, no behavior change, existing oracle/closure tests guard).

The two files where every full-airplane change lands. Both are internally well-factored (60-90 top-level defs) but are single files carrying whole subsystems. Proposal: `modules/balance/` (air / ground / axial case sets + closure), `export/sbeam_bridge/` (per deck family), sequenced AFTER note 49's export sweep and #15's primitive extraction so nothing is moved twice. Also `report/content.py` (2,609) and `io.py` (1,910) as later candidates.

Found by the 2026-09-04 project review (review.md R-23).
EOF
)"
```

### R-24 — folded into R-19 item 4.

### R-25 · *fold into #19* — io.py belongs in the mypy ratchet plan

```bash
gh issue comment 19 --body "$(cat <<'EOF'
2026-09-04 review (review.md R-25): `sloads/io.py` carries 95 Any-typed lines — more than the rest of the package combined (next: report/content.py at 26) — and is the schema boundary where a typing hole most directly becomes a silently wrong load. The documented stage plan (export/ then modules/) skips it; add io.py as its own stage, arguably before modules/.
EOF
)"
```

### R-26 · *administrative* — merge #164 and #165 into one work package

```bash
gh issue comment 164 --body "$(cat <<'EOF'
2026-09-04 review (review.md R-26): merge this with #165 into one 0.8.3 work package ("GA6 fixture altitude + case-set decision"). Same fixture, same review origin, and each fix renumbers the V-n case indices the other depends on — done separately the oracle-case-renumber cost is paid twice. Both confirmed CRITICAL by the review: #164 is a wrong stated condition identity on every deliverable case; #165 means the delivered wing distributions do not envelop the wing (the wing export ships 3 cases, none negative-g — reproduced during the review).
EOF
)"
```

### R-27 · *administrative* — close #16 after the deletion pass

The four #16 symbols (`all_checks`, `write_conm2_fragment`, `write_mass_check_deck`,
`write_balanced_deck`) were re-verified consumer-free on this tree. The list is
current; a small deletion pass closes it (proposed 0.9.0 in §4.1). No new command —
the existing issue stands.

---

## Appendix A — What was NOT found (negative assurance)

For the record, the review looked for and did **not** find: any wrong number on a
delivered load surface; any double application of a safety factor on any traced path;
any silently defaulted safety factor on a shipped fixture; any I/O in calc code; any
module recomputing an upstream quantity; any unit conversion outside `units.py`
ownership; any unregistered code deviation from the manual beyond the documented
`body_loads` method choice (module- and theory-sources-documented, arguably out of
register scope); any cross-cutting convention without a drift-guard test; any tracked
repo junk; and no pin-drift effect between the pinned and local sbeam on any deck
tried. The Appendix A oracle chain (input → modules → report → export) re-verified
clean end-to-end at the stated tolerances, and the free-free balance claim was
reproduced from the shipped card text by an independent implementation.

## Appendix B — Milestone assignment summary

| Milestone | New from this review | Existing issues (confirmed/moved) |
|---|---|---|
| 0.8.2 | R-3, R-13, R-14, R-17*, R-19*, R-20 | #151, #160 |
| 0.8.3 | R-1, R-2, R-4, R-5, R-6, R-7, R-9, R-10, R-11, R-12, R-16, R-18 | #156, #161→, #164→(+#165 merged), #170→, #171→, #15→ |
| 0.9.0 | R-15 | #148 (first), #29, #78, #130, #16→, #92→ |
| 1.0.0 | R-23 | #111, #47, #32, #31, #14, #163→, #17, #19 |
| 2.0.0 | — | F25 pack, note-21 wake, remaining parked set |

*R-17 and R-19 can fold into R-20's pass. Folds (comments, no new issue): R-8→#170,
R-22→#17, R-25→#19, R-26→#164. Unschedulable: #20 (a question, not work).
