# FAR23LOADS — Critical Project Review

**Date:** 2026-07-19 · **Reviewer:** Claude (Cowork session) · **Snapshot:** working tree staged ~11:52 EDT, re-checked 12:20 EDT

**Scope requested:** (1) technical accuracy against the two main references, FAR23Loads_Code.pdf and FAR23Loads_UserGuide.pdf, including the suspicion that Code.pdf contains errors corrected in the UserGuide; (2) GUI usability; (3) documentation level; (4) project name; (5) backlog triage toward a concept-loads release.

**Method.** Full source tree, docs, tests, and both reference PDFs (text-extracted with page markers; original pages consulted where OCR was garbled) were reviewed by five parallel review passes: two technical-accuracy passes (envelope/speeds/weights and component loads), a GUI pass that installed and ran the Streamlit app end-to-end under Playwright with 64 screenshots, a documentation/naming pass, and a backlog/release pass that ran the full pytest suite, the CLI, and all six example projects. Headline findings were independently re-verified against the code before inclusion. Numeric claims below were reproduced by executing the `farloads` modules against the Appendix A inputs printed in the references.

**Important caveat — the tree moved during review.** Files were being actively edited on your machine while this review ran (configuration.py, configuration_layout.py, tail_loads.py, test_configuration.py, CHANGELOG, backlog and history all changed between 11:55 and 12:10). The Step G6 findings below were re-checked against the 12:10 versions and still reproduce (15 test failures), but if a G6 fix session is in flight, treat those specific items as "verify after that session lands."

---

## Executive summary

The engineering core of this project is unusually good. The BASIC-to-Python port is faithful to a degree rarely seen — dozens of Appendix A oracle values reproduce to the printed digit, the theory-source traceability is page-cited, and the LIMIT/ULTIMATE discipline is enforced consistently. The review nonetheless found **two Critical calculation defects** (dive-speed floor and the flaps-down balanced condition), **one Critical mid-migration breakage** (Step G6: 15 test failures, the Geometry page and the flagship concept fixture crash), and a cluster of Major issues concentrated exactly where no printed oracle test exists — which is also the answer to why they survived: the verification strategy is excellent where Appendix A prints a number and thin where it doesn't.

Your suspicion about the references is **confirmed and answered concretely**: the Code.pdf manual contains at least two demonstrable errors that the UserGuide corrects — and in one of them (§23.335 dive speed) the Python code followed the Code.pdf's wrong prose. But the relationship is not one-directional: the UserGuide has its own errors that Code.pdf gets right. The reliable authority hierarchy is: **(1) the BASIC listings + Appendix A printed outputs, (2) the UserGuide's CFR quotes (1994 text), (3) the Code.pdf theory prose (1990)** — in that order.

The GUI is architecturally sound and half-excellent, but a first-time user's first workflow click currently produces a raw stack trace, and an entire workflow phase (Loads Plots) can never display anything. Documentation is deep but drifting — the repo violates its own doc-sync rule at the newest change, and every reference citation in the repo points at PDF filenames that no longer exist. The project name is a genuine legal/branding problem: "FAR 23 LOADS" is the exact name of a commercial product currently marketed by McGettrick Structural Engineering / DARcorporation — the brochure proving it is in your own reference folder. The backlog is better-maintained than most but a third of it is closed work wearing open numbering, and the concept-loads release needs roughly three short milestones, detailed in §5.

---

## 1 · Technical accuracy vs the two main references

### 1.1 The Code.pdf-vs-UserGuide question, answered

Six places were found where the two references (or a reference and itself) disagree. The pattern that matters: **when the Code.pdf theory prose disagrees with its own BASIC listings, the listings are right**, and the UserGuide's regulation quotes (based on the CFR revised Jan 1 1994) are more reliable than the Code.pdf's 1990 paraphrases.

| # | Topic | Code.pdf says | UserGuide says | Who's right | What the Python does |
|---|-------|---------------|----------------|-------------|----------------------|
| R1 | §23.335(b) VD minimum | Theory prose (p. 44–45): "VD(min) = K·VC" (ambiguous/wrong) | p. 46 quotes FAR correctly: VD ≥ 1.40·**VCmin** (normal), etc. | **UserGuide** — and STRSPEED.BAS (p. 265–267) agrees with the UserGuide: `V2DMIN = K2*V1CMIN`, enforced | **Follows the wrong Code.pdf prose** → Critical finding T1 below |
| R2 | §23.361(c) engine torque | p. 117 quotes the pre-Amdt 23-45 defective CFR text (factor applies only to (a)(2)); ENGLOADS.BAS implements the defective text | §17.2.1 (p. 17-2) quotes the corrected 1994 CFR: factor applies to all of (a) | **UserGuide** | Correct — the project's documented AC 23-19A deviation already fixes this; the UserGuide is additional primary-source corroboration worth citing in `engine_loads.md` |
| R3 | Tail-gust downwash constant | p. 75 prose: 114.6·aw/(π·AR) "identical to 36·aw/AR" — but 114.6/π = 36.48 | (SELECT.BAS line 5590 uses 36, per CAM 3.217(c)) | **BASIC/CAM (36)** | Correct — `select.py:395` uses 36.0; worth a code comment |
| R4 | Chordwise inertia factor Nx sign | Ch 13 (p. 96): Nx = −Dx/W, with correct worked values | §15.1 prints nx = Dx/W (sign dropped) | **Code.pdf** | Correct — `wing_inertia.py` follows Code.pdf |
| R5 | LANDLOAD tail-down drag components | Ch 20 flowchart: "DMP = K·VMP, cases 1–18" (includes tail-down 7–9) | — (internal Code.pdf conflict) | **The BASIC listing** (p. 468): DMP(7-9) = 0 | Correct — follows the listing |
| R6 | Single-engine misc-system weight | BASIC prints 0 (unset-variable quirk); Appendix A p. 131 prints 0 | Table 3.2 (p. 29) lists 0.22% | Oracle = BASIC | Correct — documented preserved quirk |

**Bottom line:** treat neither PDF as uniformly authoritative. R1 is the concrete instance of your concern — a Code.pdf error corrected in the UserGuide that the Python inherited. R4 is the reverse. When porting or verifying anything further, check prose → listing → printed output, and prefer the printed output.

### 1.2 Calculation defects (most severe first)

**T1 · [CRITICAL] VD omits the §23.335(b)(2) minimum (Kd·VCmin) — default dive speed ~10.7% low.**
`farloads/modules/structural_speeds.py:146-150` computes `vd = max(chosen_vd, 1.25·VC)` and reports `kd·VC` as merely "recommended." STRSPEED.BAS enforces *both* minimums: `V2DMIN = K2·V1CMIN` and `1.25·V6C` (Code.pdf p. 265–267, lines 170/380/390); the UserGuide (p. 46) quotes the FAR correctly. Verified failure: the Appendix A "Cat N, no chosen speeds" case (p. 155) prints VDmin = **198.53 kt**; the code returns **177.26 kt** — non-conservative by 10.7%, and it propagates into every downstream envelope point, MNE/MFC, and all component loads at VD. The chosen-speeds case (p. 156) happens to pass, which is why the 0.2.0 verification baseline missed it. The theory doc (`00_theory_sources.md:59`) documents the wrong version as if it were the source. **Fix:** `vd_min = max(kd*vc_min, 1.25*vc)`; rename the "recommended" figure to `kd·vc_min`; add the p. 155 no-chosen-speeds oracle as a test; correct the theory doc.

**T2 · [CRITICAL] Flap-envelope "BAL 1.4VSF" balanced at 1.4× the 2-g stall speed instead of 1.4× the 1-g flaps-down stall.**
`farloads/modules/flight_envelope.py:356-363`: `v3` captures the STALL **2G** speed and BAL 1.4VSF runs at `1.4·v3`. FLTLOADS.BAS (Code.pdf p. 300–302) saves the STALL **1GL** speed for this condition. Verified against Appendix A p. 178 case 9 (using the landing-config polynomials printed on p. 176): oracle V = 83.6 kt / LT = −430 lb; code produces V = 116.0 kt / LT = −957 lb — the balancing tail load is **2.2× too large** (conservative direction, but wrong, and it contaminates the SELECT search and export). Note: the 0.2.0 baseline says the repo lacks landing-config aero polynomials — Code.pdf p. 176 prints them; using them is what exposed this. **Fix:** capture the STALL 1GL speed and balance at 1.4× that; add the p. 178 landing rows as oracle tests; correct the baseline note. All 28 other cruise/flap rows of the same run reproduce the manual within print precision.

**T3 · [CRITICAL, in flight] Step G6 is half-migrated; suite red; Geometry page and concept fixture crash.**
Verified live at both the 11:52 and 12:10 snapshots: **15 failed / 382 passed**. `EmpennageInput` exists, `SCHEMA_VERSION` bumped to 27, tail fields removed from `LayoutInput` — but `configuration.py:400` (`component_stations`) and the Geometry/Tail Loads views still read the removed fields. Consequences: `AttributeError: 'LayoutInput' object has no attribute 'h_tail_area'` on the Geometry page (raw traceback in the GUI — the workflow's step 1), and `concept_regional_jet` — the flagship concept fixture — cannot complete a full run. The views smoke test *does* catch it, which means the change shipped (or is being made) against a red suite. Files were being edited during this review, so this is likely being fixed as you read — but the process finding stands: a schema bump landed with consumers unmigrated and no changelog entry at the time of the snapshot.

**T4 · [MAJOR] Swept-wing span-load correction omits the BASIC's renormalization — swept wings lose 6–13% of total lift.**
`airloads.py:242-264` (`_apply_sweep`) subtracts the Pope sweep term but never renormalizes the integrated CL back to the operating value. AIRLOAD4.BAS explicitly renormalizes (COL19→COL20 divide; Pope & Haney's actual procedure). Measured: at target CL = 1.0 the recovered CL is **0.940 at Λ = 20°, 0.866 at Λ = 30°** (1.000 at Λ = 0). Root shear/bending under-predicted on exactly the swept concept configurations the concept mode targets — **non-conservative**. The docstring cites Pope while omitting Pope's step. Fix is a few lines (rescale + closure assert `recovered_cl ≈ target_cl`).

**T5 · [MAJOR] Fuselage body loads leave the pitching moment unbalanced — terminal Myy ≠ 0.**
`body_loads.py:51-74` applies a single vertical wing reaction and checks force closure only. Code.pdf Ch 15 (p. 103) requires the unbalanced moment to be reacted at the front/rear spar attachments (and includes the pitching load factor, also omitted). Verified: a toy case closes ΣFz exactly but ends with Myy = +257,000 lb-in — the exported body load set carries a net couple. Fix: two-unknown spar-reaction solve; validate terminal Myy ≈ 0.

**T6 · [MAJOR] §23.427 unsymmetrical tail search excludes the unchecked-maneuver loads.**
`select.py:456` filters out "UNCHECKED" candidates; SELECT.BAS loads all 12 conditions including both unchecked maneuvers, and both PDFs' regulation text requires combination with §23.421–425 loads. The unchecked maneuver is frequently the largest H-tail load, so this is non-conservative — and it is not in the approved-deviations register, which the project's own protocol requires. Fix: include them (matching the BASIC) or document the deviation with justification.

**T7 · [MAJOR] One-engine-out "VC (ultimate)" case gets ×1.5 again at export.**
§23.367(a)(2) loads *are* ultimate (both PDFs agree); the condition is titled "(ultimate)" but carries the default `safety_factor = 1.5` (`one_engine_out.py:346-373` + `models.py:1141`). Conservative direction, but it violates the suite's own SF-marking convention and distorts VC-vs-VD criticality. Fix: `safety_factor=1.0` on that condition.

**T8 · [MAJOR] Aft-gross ballast reference point wrong — reports 0 lb where the manual computes 78 lb @ FS 103.7.**
`weight_envelope.py:203` uses the full discretionary loading (3442 lb incl. baggage) as the aft-gross reference; the manual's hand calc (Code.pdf p. 28) uses the heaviest loading **not exceeding gross** (3322 lb). With the manual's own database the module returns 0-lb ballast where the manual prints 78 lb @ 103.7 — and the module docstring claims the 78/418/158 triple matches. Fix: mirror the "not exceeding gross" candidate logic already used for the regardless case.

**T9 · [MAJOR, concept-mode] VC/VD category coefficients extrapolate below the FAR floor above W/S = 100.**
`constants.py:261-276` keeps tapering K1/K2 past W/S = 100 (e.g., K1 = 27.5 at 120); FAR 23.335 and STRSPEED.BAS clamp at 28.6/1.35. Irrelevant for GA wing loadings; directly relevant to the >12,500-lb concept band the roadmap targets. Two-line fix.

**Minor / notes (summarized):** landing default CG derivation gives "aft" and "fwd" max-landing cases the same CG (under-predicts nose-gear loads unless explicit `cg_cases` given); §23.473(g) energy-absorption floors (N ≥ 2.67, NLG ≥ 2.0) not enforced (faithful to the BASIC, but clamp or warn in concept mode); flap slipstream uses max-continuous HP where §23.457(b) says takeoff power; the flap corner set omits the LEV LAND balanced point (Appendix A case 90) without documenting the cut; cruise stall-line Mach cap uses MD where the BASIC uses MC (numerically inert for GA); the V-n diagram plot closes the negative envelope at 0 at VD for all categories where utility/acrobatic should show −1.0 (the loads themselves are right — display only); chosen VA is silently clamped to VC (the BASIC only raises, never caps); the 170-lb occupant weight should be 190 lb for utility/acrobatic per §23.25(a)(2) (the BASIC also uses 170 — caption it).

### 1.3 What was confirmed correct

This deserves emphasis because it is most of the codebase. Verified numerically against the listings and Appendix A during this review: the §23.337 load-factor schedule (exact to p. 155); VCmin/VAmin/VFmin; the complete §23.341 gust model (μ, Kg, Ude schedule with altitude taper — byte-for-byte vs FLTLOADS subr 4864); the FLTLOADS balance solver (all 20 cruise rows of p. 177 reproduced, e.g. MAN A 121.3 kt/+3.80/LT 493); MACHLIM; the atmosphere model incl. the 518.688 quirk; WTESTIMA (every component row of p. 131); WTONECG (±0.05%); WINGGEOM (exact); WTENV forward sequence (every printed digit); engine mounts (§23.361/363/371 — torque, side load, stoppage, gyro all exact to the Ch 19 hand calc); the rational tail balance (case 202: 907.27 vs 907.624 etc., within the documented π-precision drift); checked/unchecked maneuver and tail-gust formulas; the full vertical-tail chain incl. the EFFECTV cubic; TAILDIST pressures; ONENGOUT statement-for-statement; LANDLOAD all 33 cases incl. K interpolation; aileron/flap/tab to the last printed digit (271.44 / 629→819 / 84.62 lb); Schrenk + TAU quartics; the sbeam bridge coordinate convention and closure-by-construction; units (NIST-exact). The two theory docs' citations were also spot-audited and are honest — with the three exceptions already noted (T1's doc line, T4's overstated Pope citation, T6's undocumented narrowing).

**Assessment.** Where a printed oracle exists, the code is essentially perfect. Every Critical/Major above sits where the oracle net has a hole (no-chosen-speeds path, landing-config polynomials unused, swept wing, fuselage moment closure, unsymmetrical-case candidate set). The lesson for the release: close the holes in the net, not just the bugs.

---

## 2 · GUI and usability

The app was installed fresh, launched headless, and driven end-to-end with Playwright (empty project, ATR-42 concept twin, GA6 oracle single; 64 screenshots, kept in the session workspace, available on request).

### What's broken

**G1 · [CRITICAL] The Geometry page — step 1 of the workflow — crashes with a raw traceback on every project** (same root cause as T3). The user's first analysis click yields `AttributeError` with Streamlit's "Ask Google / Ask ChatGPT" links. The three-view sketch and parametric seed are unreachable.

**G2 · [CRITICAL] The Loads Plots page (workflow phase 5) can never show anything.** It reads `project.loads`, which no code path ever constructs — every writer is guarded by `if project.loads is not None` and nothing creates it. Even with a fully-computed GA6 project and every loads page visited, phase 5 permanently says "visit Wing Loads … first," instructions that cannot succeed. The Export page proves the fix: it recomputes via `build_net_loads`/`build_body_loads` directly. Make Loads Plots do the same and delete the dead guarded writes.

**G3 · [MAJOR] Half the workflow is hidden behind "View 10 more" in the sidebar.** Phases 3–6 — including Export — are collapsed on first run. One argument fixes it: `st.navigation(..., expanded=True)`.

**G4 · [MAJOR] The "Unsaved changes" flag lies.** Merely visiting Structural Speeds or Flight Envelope mutates the project on render (writes outside the Apply handlers, violating the app's own form convention), so the dirty flag trips with zero user edits and the discard-confirm dialog fires spuriously. Verified: load ATR-42 → "No unsaved changes"; three page-visits later → "Unsaved changes." Move the writes into the submit handlers.

**G5 · [MAJOR] Results Review's headline "Governing loads (SELECT)" tables have no units, no LIMIT/ULT marking, no SF column, and print literal "None" in dozens of cells.** This is the page an engineer screenshots into a design review, and it is the least trustworthy-looking one — while the project's own rule says the ULT marker is part of the units string. The lower per-section tables do it right; the top of the page contradicts the bottom.

**G6 · [MAJOR] No page links anywhere.** The dashboard checklist ("open the page to compute") and every gating message ("Set design speeds on the Structural Speeds page first") are plain text — zero `st.page_link` calls in the app. Two messages name pages that no longer exist ("Wing Geometry", "Configuration & Layout").

**G7 · [MAJOR] Aircraft Comparison — the concept-mode flagship — shows mostly "None" for the subject aircraft with the shipped examples** (reads the parametric layout; the examples carry `geometry.surfaces` planforms). It also lives under "6 · Export," which is backwards: you compare against the fleet while defining the airplane.

**Minor:** dashboard headline metrics are developer-facing ("Schema version 27"; checklist annotated with 1990s BASIC program names); balanced-conditions table shows `M(W+F)`/`LZW`/`DX` with no units or help; strut selectbox offers the bare code "O"; save-filename generation doesn't sanitize (the ATR example's sentence-long name becomes the filename); zero `st.spinner` calls despite multi-second recomputes; the app is past Streamlit's `use_container_width` deprecation date.

### What's genuinely good

Navigation order matches how a loads engineer actually works, driven from a single workflow metadata source with a drift guard. The LIMIT/ULTIMATE discipline on analysis pages is excellent. Gating on missing inputs is graceful (info box + stop, not tracebacks — Geometry being the exception). The unit system (global Imperial/SI toggle, unit-suffixed labels, KEAS/ft aviation exceptions) is a hard problem done right. Help density is high, with FAR citations in tooltips. The Export page is the best page in the app: recomputes everything so exports are never stale, honest scope filtering, zip/xlsx/CSV/sbeam in one place. Save/load with schema migration and a discard-confirm dialog is a solid persistence story (undermined only by G4).

### Top 5 usability actions for the concept release, by value ÷ effort

1. Fix the Geometry crash (with T3) and keep the views smoke test green.
2. Make Loads Plots recompute from the project (copy the Export pattern).
3. `expanded=True` + `st.page_link` in the checklist and every gating message; fix stale page names.
4. Move on-render project writes into Apply handlers so the dirty flag means something.
5. Finish the Results Review header tables: units, `-ULT ×1.5`, SF column, "—" for absent values.

---

## 3 · Documentation

### The headline problem: the repo violates its own doc-sync rule, at the newest change

CLAUDE.md declares missing doc updates a `[CRITICAL]` review finding, yet at the review snapshot Step G6 had shipped its schema bump (v27) with: the backlog still listing G6 as open work, no CHANGELOG entry, `GUI_design.md` still saying "SCHEMA_VERSION = 26," and PROGRAM_SPEC still presenting `tail_loads`/`vtail_loads` as real top-level slices. (The backlog/CHANGELOG/history files were updated during this review — re-check after the in-flight session lands.) The process is good; enforcement is the gap.

### Findings

**D1 · [CRITICAL] Every reference citation in the repo points at files that don't exist.** Seventeen citations across eight docs (CLAUDE.md, README, PROGRAM_SPEC, PROJECT_GUIDE, CODE_REVIEW_PROCESS, theory sources, backlog, verification baseline) cite `reference/FAR23 loads (1).pdf` and `reference/ADA324952.pdf`; the actual files are `FAR23Loads_Code.pdf` and `FAR23Loads_UserGuide.pdf`. Zero docs cite the actual filenames. For a project whose central claim is traceability to the reference, the trace chain's first link is broken everywhere — CODE_REVIEW_PROCESS literally instructs reviewers to open a file that isn't there. One find-and-replace fixes it.

**D2 · [MAJOR] README is generations stale and actively wrong.** "SCHEMA_VERSION 15" (actual: 27), "242 tests pass" (actual: 397 collected; baseline says 257; backlog says 385 — four numbers, none current), "4-phase sidebar Define→Analyze→Review→Export" (actual: Start + 6 numbered phases, two redesigns later). CLAUDE.md's architecture summary has the same stale 4-phase model — and since CLAUDE.md "overrides default behavior" for AI sessions, an assistant will confidently describe a GUI that was deleted two phases ago.

**D3 · [MAJOR] Internal contradiction about the Appendix B oracle.** PROGRAM_SPEC's header says Appendix B is in the repo and is a validation oracle; the ONENGOUT entry, the theory doc, and the 0.2.0 baseline all state no Appendix B printed table exists in the bundled PDF. README repeats the stronger, wrong version ("oracle-locked (Appendix A/B ±0.1%)"). A certification-minded reader would form a false belief about twin verification status. Pick one canonical statement and link it everywhere.

**D4 · [MAJOR] No user-facing documentation exists at all.** Everything in `docs/10_standard/` is for developers. There is no GUI user guide (workflow tutorial, what to enter where, how to read outputs), no consolidated methods manual for a chief engineer or DER (the material exists, scattered across theory-sources' wall-of-table, PROGRAM_SPEC, and docstrings), and no input data dictionary for `project.json` — the product's single input artifact, 27 schema versions deep, whose only field reference is models.py itself. `engine_loads.md` proves the team can write the per-module methods doc; it was written once.

**Minor:** the ULTIMATE-loads contract is restated near-verbatim in six places (each a drift liability — several of the drift findings above are restatements disagreeing); PROGRAM_SPEC interleaves spec with GUI-step archaeology (615 lines, roughly half spec); the approved-corrections *register of record* lives in CLAUDE.md, an AI-config file a human reviewer would never open (move to `docs/20_theory/`, have CLAUDE.md point at it); `docs/00_INDEX.md` omits the verification baseline; the CHANGELOG carries a ~670-line `[Unreleased]` section spanning three completed phases while RELEASE_PROCESS says to cut per phase; attribution names only "Hal C. McMaster / Aero Science Software" while the 2023 brochure says the program is copyrighted by McGettrick Structural Engineering and distributed by DARcorporation — both should be acknowledged.

### What's genuinely good

Module docstrings are the best documentation in the repo — mini theory manuals with equations, BASIC subroutine line numbers, FAR citations, and sign conventions; better than most commercial loads codes. `00_theory_sources.md` is an exceptional traceability artifact in substance (hostile in format). The 0.2.0 verification baseline (687 lines of condition-by-condition printed-figure tables with tolerances) is the kind of document a DER can actually review. CODE_REVIEW_PROCESS's "common defect patterns" table was clearly written from experience. The honesty of the disclaimers is the right instinct throughout.

### Doc work before the concept release vs deferrable

Blocking: the reference-filename sweep (D1); the consistency sweep for README/CLAUDE.md/backlog numbers and phase names (D2) with one canonical Appendix-A/B status statement (D3); G6 documentation (in flight); a `project.json` data dictionary (generate from the dataclasses); a 5–10-page GUI user guide walking one end-to-end GA6 example with three or four hand-checkable numbers (the baseline doc already contains the numbers — it needs narrative). Strongly recommended: a ~15-page methods-manual front section (scope, assumptions, method per FAR condition group, the two approved deviations, oracle-vs-closure status table — mostly assembly); cut 0.3.0 so the changelog dates. Deferrable: per-module methods walkthroughs for the other 21 modules (do SELECT and FLTLOADS first), de-duplicating the six-fold boilerplate, pruning PROGRAM_SPEC archaeology into history, archiving the superseded GUI plan docs.

---

## 4 · Project name

**This is a real problem, not a nit.** "FAR 23 LOADS" is not just the name of the 1990s reference program — per the brochure in your own reference folder (`FAR-23-Loads-Brochure-2023.pdf`), it is the exact name of a **currently marketed commercial product**, copyrighted by McGettrick Structural Engineering, Inc. and distributed by DARcorporation. This project uses that name as its repo name, GUI title (`page_title="FAR 23 LOADS"`), README H1, and package description, and the README's disclaimer never states non-affiliation. An open-source reimplementation bearing a live commercial product's exact name is a genuine passing-off/confusion exposure. The honest-attribution upside is fully achievable in a description line ("a modern open replication of…") without adopting the mark as your own title.

Secondary issues: "FAR" is doubly dated (the FAA says "14 CFR" — your own reference notes already do — and Amdt 23-64 rewrote Part 23 in 2017, so the prescriptive Subpart C this tool implements is now "legacy Part 23" method, while the roadmap explicitly goes beyond Part 23: concept mode, Part 25 supplemental cases, sbeam handoff). And the name is already fragmented four ways: repo `FAR23LOADS`, package/CLI `farloads`, GUI brand "FAR 23 LOADS", and prose "the suite."

PyPI check (live): `farloads`, `far23loads`, `part23loads`, `conceptloads`, `airframeloads` are all unclaimed.

**Recommendation.** (1) Immediately — regardless of any rename — add a non-affiliation sentence to the README and GUI disclaimer naming McGettrick/DARcorporation alongside the McMaster attribution. (2) Short term, converge repo, GUI title, and prose on **farloads** — it is already the import name and console script, so it is the cheapest possible unification. (3) Before the public concept release, decide the long-term identity: if the product is the replication, `part23loads` with the heritage in the subtitle; if the product is the concept tool (the roadmap says it is), **ConceptLoads** or **AirframeLoads**, with the validated Part 23 core described, not titled. "FAR" should not appear in the title either way. Candidates considered and rejected: `SubpartC` (cryptic), `SpanLoads` (generic-term collision), `LegacyLoads23` (clunky), `McMasterLoads` (a living person's/company's name plus McMaster-Carr confusion).

---

## 5 · Backlog triage — path to the concept-loads release

**Verified current state (12:20 EDT):** version 0.2.0 (2026-07-08), SCHEMA_VERSION 27, **pytest: 15 failed / 382 passed** (all 15 from the G6 half-migration), ruff clean, editable install clean on a fresh machine. CLI end-to-end works (engine module → CSV with correct `-ULT`/SF columns). Full pipeline: `ga6_normal` 18 modules/238 conditions OK; `cessna_210` 18/556 OK; `atr42_100` 14/440 OK; `concept_regional_jet` **crashes** in `configuration` (G6) — its other 18 modules run clean. sbeam export works on both GA6 and the concept jet. `smoke_test.sh` hardcodes `.venv/bin/*` paths and won't run as-is on a fresh machine (its two checks pass when run manually).

### Must-have for the concept-loads release (blocking)

| Item | Why | Effort |
|---|---|---|
| Finish Step G6 + suite green (in flight) | The tool is currently broken at its flagship use case | M |
| **Fix T1 (VD floor)** + add the p. 155 no-chosen-speeds oracle test | Non-conservative envelope speeds — "silently wrong numbers" is the one absolute disqualifier | S |
| **Fix T2 (BAL 1.4VSF)** + add p. 178 landing-config oracle rows | Wrong balanced condition feeding SELECT/export | S |
| **Fix T4 (sweep renormalization)** + closure assert | 6–13% missing lift on precisely the swept concept wings the release is for | S |
| Fix T6 (23.427 candidates) or document the deviation | Non-conservative tail case, undocumented deviation | S |
| Fix T7 (OEO double SF) and T9 (W/S>100 clamp) | Small, load-magnitude/marking correctness | S |
| Backlog 2-14 (AIRLOAD4 Mach threshold) and 2-15 (flap slipstream HP — same as T-minor above): verify vs the BASIC and close | Method-selection and load-magnitude correctness for concepts | S |
| G7 persistence verification (save→reload no-op on every example) after the schema-27 bump | "Import/export cleanly" is a release criterion | S |
| Doc consistency sweep: D1 filenames, D2 README/CLAUDE numbers and phases, D3 Appendix-B statement | Credibility; their own standard calls this CRITICAL | S–M |
| GUI items G1–G3 (crash, dead Loads Plots page, hidden nav) | First-run experience is currently a stack trace and an un-completable instruction | S–M |
| Cut the release: 0.3.0, changelog cut, refreshed verification baseline (incl. the new oracle tests), fixed smoke test | Un-tagged fixes don't exist; the baseline is the traceability artifact | M |

### Should-have (ship without if needed)

T5 (fuselage moment closure — flight-loads deliverables for wing/tail are unaffected; body loads should carry a caveat until fixed), T8 (ballast reference), G4/G5/G6/G7 GUI polish, Step G8 summary report (the natural "kick off structural development" deliverable, but Export already ships JSON/CSV/workbook/sbeam/case-index), backlog 2-1 (case-identity unification), 2-17(b) (turboprop gate on OEO), G6b/G6c (gear/geometry single-sourcing), 2-2 (per-CG inertia), landing default-CG derivation fix (T-minor; or require explicit `cg_cases`), a concept-methods/limitations note stamped into exported deliverables (fold into G8).

### Defer to later releases

2-12 ground-case distributed fuselage loads + pressurization (the big one — flight loads suffice to start sizing); 2-4 sbeam real-stiffness/assembled airframe; 2-6 flaps-extended tail oracle (note: T2's use of the p. 176/178 printed data partially unblocks this); 2-10 printed-oracle backfills needing reference material; 2-3 V-tail EFV wire-in (correctly parked — the naive fix breaks the 591-lb oracle); 2-7 commuter category; 2-18 coefficient generation; 2-19 enroute config (23.373); 2-20 WINGINER table completeness; per-module methods docs beyond SELECT/FLTLOADS.

### Question / drop (backlog hygiene)

Roughly a third of the backlog is closed work wearing open numbering, violating its own lifecycle rule: 2-5, 2-9, 2-11 are resolved decisions still holding numbered slots; 2-8's resolution text is garbled and self-contradictory ("decision revised include… Revisit not do."); 2-16 is fully resolved in-place with strikethroughs; the P1-1 entry and "Phase 1 is complete" narrative are shipped work; seven of eight decision checkboxes (D-1…D-8 minus D-5) are closed and should archive to history. The "Current state" snapshot bakes in hard numbers ("385 tests," "SCHEMA_VERSION 23") that rot — reference the CI/CHANGELOG instead of restating counts. The G6-size full design specs inside the backlog duplicate the plan docs and rot the moment implementation deviates — which G6 just demonstrated.

**Gaps not in the backlog at all:** the technical-accuracy items T1/T2/T4–T9 above (none are tracked); doc drift as a work item; example-fixture inventory management (`atr42_100` appeared and is documented only in the theory doc); a release-planning item for 0.3.0 itself; the smoke-test portability fix; the exported-deliverables methods statement.

### Suggested milestones

- **M1 — Green and honest (days):** land G6 fully, suite green; fix T1/T2/T4 (+T6/T7/T9, all small) with their new oracle tests; doc consistency sweep (D1–D3).
- **M2 — Usable (days):** G1–G3 GUI fixes + G7 persistence check; smoke-test fix; `project.json` data dictionary; short GUI user guide.
- **M3 — Cut 0.3.0 "Concept Loads v1":** refreshed verification baseline including the new oracle rows and a one-page oracle-vs-closure status table; changelog cut; tag. Stretch: G8 summary report with the methods/limitations statement.
- **M4 — post-release:** T5/T8, GUI polish batch, case-identity unification, then the 2-12 ground-loads epic as its own release.

---

## Appendix — housekeeping from this review

- **Cleanup needed on your machine:** the review had to split the 134 MB Code.pdf to transfer it (it exceeded the file-bridge transfer window). The temporary chunks were moved to `FAR23LOADS/_to_delete/_staging_tmp/` (~260 MB) — this session cannot delete files on your disk, so please delete that folder.
- Screenshots of every GUI page (64 PNGs, including the evidence for each GUI finding) are in the session workspace; ask if you'd like them delivered.
- Five sub-reviews' full raw findings (including the complete confirmed-correct inventories with page-by-page reference citations) are available on request; this report is the verified synthesis.
