# Critical Code & Documentation Review — 2026-07-21

**Process:** per `docs/10_standard/CODE_REVIEW_PROCESS.md` (severity ladder §4, output format §6, approval gate §7).
**Emphasis (as requested):** (1) code maintainability · (2) GUI ease of use and coverage · (3) documentation.
**Scope:** full tree at SCHEMA_VERSION 31, snapshot 2026-07-21 ~12:10. Three parallel review passes (maintainability; GUI driven live under Playwright across all 20 pages with both example projects, 52 screenshots; documentation compliance audit of all 13 changes shipped since 2026-07-19). Headline findings independently re-verified (the io.py forward-compat crash was reproduced live; the landing-page mutation and the stale schema line confirmed at file:line).

## Baseline (process §7 gate inputs)

`pytest`: **466 passed / 0 failed** in ~72 s, coverage ~93%. `ruff check farloads/ cli.py`: clean. All 21 modules registered, imported, and raising on missing slices. The sprint since the 2026-07-19 review closed **all of M1 (11 items) and all of M2 (11 items)** with, in nearly every case, full six-artifact doc sync — the lifecycle rule is now demonstrably being followed (zero stale done-but-listed backlog entries found on a reverse-check). This is a dramatically healthier repo than two days ago.

**Approval-gate status:** one `[CRITICAL]` (stale schema line in GUI_design.md — the process's own non-negotiable Step 1) and six `[MAJOR]`s below block a clean approval; all are small-to-medium fixes. No load-value correctness findings this round (that was the 07-19 review's scope; its M1 fixes are confirmed landed with their oracle tests).

---

## 1 · Code maintainability

**Executive read.** The calc core has genuinely held the porting contract under sprint pressure: no I/O in any module, uniform registration, missing-slice guards, average cyclomatic complexity A(4.1), and a 466-test suite that runs in 30 s. The debt is concentrated in exactly two walls the planned doubling (FAR 25 supplements, OpenVSP, sloads rename) will hit first: the **schema/io layer** and the **label-string coupling**. The app layer is ~6.3k lines of which an estimated 25–35% is repeated scaffold.

```
[MAJOR] farloads/io.py:1101-1106 — schema_status() promises "unrecognized fields are
ignored" for newer files, but most *_from_dict readers crash on them.
WHY: Reproduced live: adding one unknown key to weight.items raises
     TypeError ("MassItem.__init__() got an unexpected keyword argument ...") because
     readers splat raw dicts (io.py:184, :199, :433); only configuration_from_dict
     (io.py:906) filters to __dataclass_fields__. Two app versions sharing a project
     file = crash on load; FAR 25 supplements will add fields fast.
FIX: One shared _filtered(cls, d) helper used by every from_dict + a test injecting an
     unknown key into every slice of ga6_normal.
```
```
[MAJOR] farloads/io.py:929-1019 — 31 schema versions, no migration chain;
project_from_dict is CC 51 (radon F); io.py has the repo's worst maintainability index.
WHY: "Migration" is key-presence sniffing (the 19-clause or-gate at :936-945 plus
     scattered legacy shims) with the version history kept as prose in models.py.
     By v50 nobody can say which guard serves which version or delete one safely.
     Only 2 of 31 historical versions exist as frozen test fixtures (v20, v24).
FIX: MIGRATIONS: dict[int, callable] applied hop-by-hop before one tolerant reader;
     one frozen fixture file per version; a fields-hash test that fails when models
     change without a SCHEMA_VERSION bump (currently unenforced).
```
```
[MAJOR] farloads/report.py:204-260,307 — load-case semantics carried by display-label
strings and a label regex, coupled across ~150 sites.
WHY: _VERTICAL_LABELS, _GYRO_CASE_RE, 13 view lookups (vals["..."]) and 144 test
     lookups mean a cosmetic relabel silently blanks CSV columns (report.py:278 returns
     "" — no error) and breaks tests. LoadValue has no machine-readable key.
FIX: Add key: str to LoadValue; match on key in report/sbeam/views/tests; label stays
     cosmetic. Mechanical, prerequisite for FAR 25 supplements emitting new quantities.
```
```
[MAJOR] farloads/registry.py:47-52 — run_all_modules swallows every ValueError, not
just missing-slice ones.
WHY: A genuine calc defect raising ValueError (landing.py has 8 raise sites) makes the
     module silently vanish from run-all/export — indistinguishable from "inputs not
     entered". A regression ships as a quietly missing report chapter.
FIX: MissingInputError(ValueError) raised at the ~21 missing-slice guards; registry
     catches only that.
```
```
[MAJOR] farloads/modules/select.py:92-97 — _envelope() silently rebuilds the FLTLOADS
envelope (fallback to build_envelope) instead of requiring the persisted slice, from
7 call sites; balloads.py imports the same fallback.
WHY: Two sources of truth (stale Project.envelope wins when present, fresh rebuild when
     not) and up to 7 full V-n matrix rebuilds per SELECT run — a §3 Step 4 contract
     deviation ("no recomputation of another module's quantity").
FIX: Compute once in run(), thread it down; raise MissingInputError when absent (or
     keep one justified fallback call site).
```
```
[MAJOR] 9 cross-module private-symbol imports, incl. app/ reaching into farloads
internals (select.py:76, balloads.py:33, body_loads.py:41, flap.py:56,
airloads.py:64, app/components.py:21, app/views/weight_mass.py:50, ...).
WHY: Underscore names have no stability contract; the rename + FAR 25 work will
     refactor against an undeclared API.
FIX: Promote the genuinely shared helpers (_interp_x, _sigma, _maneuver_load_factors,
     htail_balance family) to public homes; ban cross-boundary _imports in review.
```

Minor findings (summarized; full details available): the four F/E-rated functions — `_tab_design_speeds` CC 72 (290 lines), `landing_reactions` CC 66, `_three_view` CC 52, `_tab_vn` CC 44 — should each split into seed/form/render (resp. per-attitude) parts; ~25–35% of the app layer is repeated per-field unit/form/apply idiom (139 `number_input`s hand-pairing `to_display`/`to_imperial_scalar` 71+41 times, 22 hand-rolled apply handlers, 20 identical page headers) that a `unit_number_input` + `page()` helper pair would absorb (~1.5–2k lines, and it removes a silent-unit-bug hazard); `htail_balance` returns stringly-keyed dicts consumed across module boundaries (make it a NamedTuple); the `tail_loads`/`vtail_loads` property proxies have two trap-doors (silent no-op None assignment; invisibility to `dataclasses.fields/replace/asdict`) that a pattern-copier will trip on — document, don't replicate; 9 test files duplicate a `_value` label-lookup helper and 7 import from `test_engine` (move to conftest/helpers); serializers hand-enumerate fields so a new field can silently not persist (add a generic sentinel round-trip test); `run()` is not pure w.r.t. the Project because load-chain modules call `sync_geometry_derived(project)` internally — deliberate, but write it into the contract before FAR 25 authors guess. Nits: the process requires cspell.json updates but no cspell config exists; `farloads.egg-info/` sits in the tree and will be stale garbage at the rename.

**Metrics.** farloads core 5,955 LOC (models.py 1,842 / 66 classes; io.py 1,190); modules 7,013; app 6,298 (components.py only 121); tests 8,459 / 466 tests / 30 s. Calc avg CC A(4.13), app B(8.95). Rename surface: 391 `farloads` refs in .py + 257 in docs + pyproject — but the JSON schema, registry names, and session-state keys are clean (no package-branded strings persist to disk), so saved projects survive the rename untouched.

**Top refactors before the codebase doubles (payoff÷effort):** (1) `LoadValue.key` de-stringing; (2) io.py overhaul (tolerant reader + MIGRATIONS chain + per-version fixtures + version-bump enforcement test); (3) `unit_number_input`/`page()` app helpers *before* the FAR 25/OpenVSP views are written; (4) MissingInputError + single envelope computation; (5) split models.py into a package in the same commit as the sloads rename (one churn event, not two).

---

## 2 · GUI — ease of use and coverage

**Live run.** Installed fresh, drove all 20 pages under Playwright with both `ga6_normal` and `concept_regional_jet` loaded through the real UI; full workflow exercised through export (zip with 19 CSVs + report + workbook + sbeam files, all verified by actual download). Page loads 1.2–2.4 s; no tracebacks anywhere in either example or the empty project.

**Prior findings — 4 of 5 fixed, verified:** G2 Loads Plots now recomputes live and renders (fixed); G3 nav fully expanded with shared `page_link` gate components (fixed); G5 Results Review tables carry `(units-ULT)` headers + SF column, zero literal "None" on any page (fixed); G7 Aircraft Comparison fully populated for both examples (fixed; Export placement kept by documented decision). G4 (phantom dirty flag) is fixed on the two named pages but has **one residue**:

```
[MAJOR] farloads/modules/landing.py:453-456,472-474 — build_landing() mutates the live
Project on every render (gear sync onto project.landing; gross_weight_lb and n written
onto the input slice).
WHY: Verified by per-page bisection: merely opening Landing Loads flips "🟠 Unsaved
     changes" — the last G4 residue, and a pure-calc contract break in the calc layer
     itself (run() writes inputs).
FIX: Read gear geometry into a local effective input (dataclasses.replace); return
     n/gross rather than storing them.
```
```
[MAJOR] app/views/landing_loads.py:106-107 — landing.cg_cases has no GUI editor, and
the shipped concept RJ example dead-ends on it.
WHY: The RJ ships only 2 cg_cases → red error "landing.cg_cases must have exactly 3
     entries" with the page instructing the user to edit raw JSON. A required calc
     input reachable only through the JSON editor, on the flagship example.
FIX: 3-row data_editor seeded from project.mass.cases; fix the example to ship 3 cases.
```
```
[MAJOR] farloads/modules/select.py:172-174,645-647 — SelectInput fields
(full_down_aileron_deg, basic_airfoil_cm, wing_weight_lb) are exposed on no page.
WHY: They drive the governing wing-torsion score and critical-fuselage weight; a
     user-built project silently gets defaults (0/0/0.09·MTOW) — the TORS row can be
     wrong with no visible knob.
FIX: Add the three fields (with help=) to the Critical Loads tab.
```
```
[MAJOR] app/views/fuselage_loads.py:107 — 5 of 6 shipped examples (incl. ga6) open
Fuselage Loads to a red error, and the fuselage never reaches Loads Plots/sbeam.
WHY: Only the RJ ships fuselage_mass stations; the error leaks internal slice names
     ("body_loads needs 'fuselage_mass' stations") where every other page uses the
     polished gate; the Weight DB already holds the station weights (§5 read-don't-
     re-ask miss).
FIX: Seed the grid from Weight DB fuselage items; use the standard gate; ship
     fuselage_mass in ga6_normal.
```
```
[MAJOR] app/views/configuration_layout.py:260,274-278 — Apply persists an invalid
layout (Area S=0), then st.error + st.stop() blanks the rest of the Geometry page,
incl. the unrelated empennage/gear forms.
FIX: Validate before persisting; keep the page alive on error.
```

Minor: the G6/G6b empennage + landing-gear sections are Imperial-native (hardcoded ft²/in labels ignoring the SI toggle — a direct GUI_design §7 deviation — and ~30 widgets with no tooltips); help-coverage collapses outside the definition pages (flap 0/6, OEO 0/7, wing loads 2/10 vs speeds 21/21 — app-wide ~45%); Results Review's "All results by section" silently drops the 8 folded modules' results despite its own caption; export CSV labels leak registry keys ("balloads (CSV)"); 9 model fields have no widget anywhere (incl. `chosen_va`/`chosen_vf`, `one_engine_out.speeds_kt`). Nits: primary parametric wing form and the altitude-table Apply live in the sidebar below a 20-item nav ("where do I type?"), first-run Loads Plots info lacks links, internal slice names in error strings.

**Coverage matrix (the new emphasis):** modules→pages **complete** — all 21 registered modules are hosted (13 primary + 8 folded), zero CLI-only, verified both directions. Results→visible+exported: complete except the folded-eight roll-up gap above. Fields→widgets: ~230 fields sampled, **9 without any GUI path** (listed above — two of them user-blocking). FAR 25 flag: exposed with an exemplary help tooltip on Engine Mount. Concept mode: fully reachable and consistently bannered (12 pages verified on the RJ).

**What the GUI now does well:** the dashboard is a real workflow map (per-step status, every row a link, slice progress); gating is calm and linked; LIMIT/ULT discipline is airtight; single-source read-throughs show provenance ("from the Geometry page"); export is one-stop and never stale; unit round-trip is lossless; both examples load cleanly through schema migration.

**Top 5 ease-of-use actions:** (1) fix the two example JSONs (3 CG cases in RJ, fuselage_mass in ga6) — trivial, removes the only two red errors a first-time user meets; (2) kill the landing.py on-render write; (3) add the SELECT-inputs + cg_cases editors; (4) move the Geometry/altitude forms out of the sidebar or anchor them visually; (5) finish the help= rollout + de-jargonize error strings and CSV labels.

---

## 3 · Documentation

**Sprint doc-sync audit (process §3 Step 1):** 13 shipped changes sampled — including M1-1, M1-2, all three schema bumps, and the M2 GUI batch — against all six required artifacts (spec row, theory row, backlog removal, history entry, changelog, code). **Result: strong compliance — 6/6 artifacts present for nearly every change**, the prior review's theory-doc errors (the VD line) were corrected as part of the fixes, the approved-corrections register moved to `docs/20_theory/02_approved_corrections.md`, and the backlog shows **zero** stale done-but-listed entries. Docstring quality in the four most-changed modules still exceeds the bar (the sweep-renormalization fix even documents its ~0.3% deviation rationale). The exceptions:

```
[CRITICAL] docs/10_standard/GUI_design.md:354 — "Schema is at SCHEMA_VERSION = 28";
actual is 31.
WHY: Three bumps (29 CLmax single-source, 30 M2-6 derived geometry, 31 M2-10 placards)
     shipped without updating the doc that declares itself authoritative — the exact
     §3 Step 1 condition the process marks CRITICAL; the same line was dutifully
     updated at 28, so the chain broke mid-sprint.
FIX: Extend the version parenthetical with v29/v30/v31 — or replace the baked number
     with a pointer to models.py / DATA_DICTIONARY.md (which is correct at 31).
```
```
[MAJOR] CLAUDE.md:19,:28,:189 — still claims "oracle-locked (Appendix A/B ±0.1%)".
WHY: Last remnant of the D3 contradiction; README/PROGRAM_SPEC/theory-sources now carry
     the canonical "Appendix B absent — closure-locked" statement, but the file that
     primes every AI session kept the strong wrong claim.
FIX: Reword to "Appendix A ±0.1%; twin cases closure-locked", link the Oracle-status
     anchor.
```
```
[MAJOR] docs/20_theory/01_far25_gap_analysis.md — no CHANGELOG entry, no history
entry, missing from docs/00_INDEX.md (as are the backlog restructure and decisions
D-9/D-10/D-11; reference/14CFR_MC_MD_speed_margin.md is reachable only from the
backlog).
FIX: One Documentation changelog entry + INDEX rows.
```
```
[MAJOR] docs/10_standard/PROGRAM_SPEC.md:359-362 — schema-version trail records
"…27, 28, 30": skips 29, stops before 31.
FIX: Insert 29, append 31.
```

Minor: `00_INDEX.md` still omits the 0.2.0 verification baseline and still describes the backlog as "the two-phase plan" (restructured 07-20); the backlog's own "Current state" header lags its item list ("G0–G6b", "401 passed" — actual G0–G7, 466) and retains two empty M1/M2 headers; theory-sources line 89 points the corrections register at CLAUDE.md (moved); README's examples line lists 4 of 6 fixtures (omits the concept flagship); the `[Unreleased]` changelog has grown to ~1,083 lines with ten duplicate `### Changed` headings (tracked as M3-2, but it is the release gate); the McGettrick/DARcorporation non-affiliation sentence is still absent from README/GUI — the 07-19 review said "immediately, regardless of rename"; don't couple it to M3-1.

**Prior doc findings status:** D1 (broken reference filenames) **fixed** — zero live citations to the phantom PDFs; D2 (README/CLAUDE staleness) **fixed** except the examples line; D3 **mostly fixed** (CLAUDE.md remnant above); D4 (no user docs) **half fixed** — `GUI_USER_GUIDE.md` and a generated, drift-guarded `DATA_DICTIONARY.md` now exist and are indexed; the methods manual remains the largest outstanding gap for a DER-facing package, along with a 0.3.0 verification baseline covering the new M1 oracle rows.

---

## Verdict & the short path to a clean approval gate

The sprint transformed the repo: every calculation finding from the 07-19 review is fixed with oracle tests, the GUI's five worst usability defects are four-fifths gone, doc-sync is being practiced, and user-facing docs exist. What blocks the §7 gate now is small and concentrated: **one afternoon of doc currency fixes** (the CRITICAL schema line, CLAUDE.md oracle claim, spec version trail, INDEX/changelog entries for the FAR 25 doc, non-affiliation sentence), **two example-JSON fixes plus the landing on-render write**, and — before any new feature wave — the two structural investments the maintainability review ranks first: the io.py tolerant-reader/migration chain (the forward-compat crash is real and reproduced) and `LoadValue.key`. Everything else can ride the M3 release train as planned.
