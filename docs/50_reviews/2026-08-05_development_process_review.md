# Development Process Review — 2026-08-05

**Scope:** critical assessment of sloads development progress (2026-06-18 → 2026-08-04,
including the uncommitted working tree), with recommendations to improve velocity at
minimal risk — including which of the sbeam 2026-08-04 process changes
(`sbeam/docs/50_reviews/2026-08-04_development_process_review.md`) should be adopted here,
and which sloads practices should flow the other way.

**Evidence base:** full read of `CHANGELOG.md` (235 entries across 3 releases +
`[Unreleased]`), all 8 `docs/40_history/` files (9,001 lines, 113 completed steps),
`docs/30_future/00_backlog.md` + `01_concept_loads_plan.md`, the process docs
(CLAUDE.md, CODE_REVIEW_PROCESS, RELEASE_PROCESS, PROGRAM_SPEC, PROJECT_GUIDE), and git
history (168 commits). This review document is new; no existing code or documentation was
modified.

---

## 1. Executive summary

sloads is in **materially better shape than sbeam was** at its review: it ships (v0.2.0
and v0.3.0 tagged, with archived verification baselines), its oracle discipline held the
22-module port to near-zero physics defects, its concept-loads plan (C0–C11) is 100%
executed, and its recent maintainability sequence (M4) has already fixed most of the seam
defects the review waves found. Velocity is objectively high — 113 completed steps in 7
weeks (~16/week), a flat ~41–43 changelog entries/week.

The drags on velocity are almost entirely **process-shape, not engineering**, which makes
them cheap and low-risk to fix:

- **The bookkeeping tax is worse than sbeam's was.** A small fix must touch 5–8 files
  (uniform full-step-format closure, no size tiers); the three most-churned files in the
  repo are the backlog (131 of 168 commits), CHANGELOG (131) and the 6,038-line history
  file (108); **40% of all commits are docs-only** (sbeam: 28%).
- **Rework rose from ~5% (port era) to ~40% (post-0.2.0)** — but the defects are seams,
  not physics: GUI unit handling was rebuilt **three times** before the architectural fix
  (M4-20); the safety-factor/ULTIMATE chain took **seven** correction passes; the same
  doc line went stale three times before a guard test ended it.
- **The backlog overstates the distance to the mission.** Of 40 open items, only ~5 are
  essential to "concept loads → sbeam sizing works end-to-end" — and the genuinely
  mission-critical gaps (a continuous sbeam round-trip harness, a global equilibrium
  check on exported decks) are **not in the backlog at all**. Mission-complete is
  roughly 2–3 weeks of focused work at the recent cadence.
- **`[Unreleased]` is already release-sized** (77 entries, 84% of 0.3.0's scope, 13 days
  old) — the event-triggered release rule is starting to reproduce sbeam's stall.

The headline recommendation: adopt sbeam's tiered closure/review/cadence rules (pure
process, zero verification-depth change), codify sloads' own hard-won "make it
structural" lesson as a rule, and re-point the near-term backlog at the export boundary.
None of this touches the oracle locks or the review waves — the things that demonstrably
protect correctness stay exactly as they are.

---

## 2. Where the time went

| Metric | Value |
|---|---|
| Duration / commits | 7 weeks (Jun 18 – Aug 4), 168 commits (Jun 34, Jul 112, Aug 22) |
| Code / tests / docs | 19.3k calc + 7.3k GUI / 13.4k test lines (~702 tests) / 14.6k docs + 2.7k changelog |
| Completed steps | 113 across 14 numbering series; mean entry 52 lines (range 17–118) |
| Releases | v0.2.0 (07-08), v0.3.0 (07-23), both tagged with verification baselines; `[Unreleased]` since 07-23 already 84% of 0.3.0's size |
| Rework : feature | ~1:20 in 0.2.0 → ~1:1 in 0.3.0 → ~1.2:1 in `[Unreleased]`; ~40% overall post-0.2.0 |
| Defects | ~35 resolved (+51 M-series IDs in changelog); worst density: GUI/unit handling (~14); oracle-fidelity defects: 8, all caught by the M1 review |
| Effort by record volume | core calc ~28% · GUI/views ~35% · export/units/report ~15% · process/hygiene/release ~22% |
| Top-3 churn files | `00_backlog.md` (131×), `CHANGELOG.md` (131×), `00_completed_development.md` (108×) — all bookkeeping |
| Docs-only commits | 67 / 168 (40%) |

**The five biggest rework chains:**

1. **Units/SI display** (~25+ entries): Phase-D toggle → 0.3.0 "16 pages ignored the
   toggle" → G0 canonical units → M4-11a ("~40 fields ignored the SI toggle"; "a 184 ft²
   wing was stored as 1982 ft²") → M4-20 (7 approved sub-steps; "twelve views read
   `st.session_state['unit_system']` directly"; 1,580 unconverted SI values). The same
   requirement was rebuilt three times before the boundary was made structural.
2. **Safety-factor/ULTIMATE chain** (7 passes): the ULT contract (0.2.0) → M2-4 → M1-5
   double-factoring → M4-7 (bridge hardcoded `_SF = 1.5`) → M4-13 → M4-14 (corrupt SF
   "under-scaled every exported card", MAJOR) → M4-15.
3. **Geometry single-source** (6 steps): D4 → G1 unified geometry → G6/G6b/G6c → M4-17
   (whose root finding: `build_mass` had **zero production callers** — `Project.mass` was
   never produced in shipped 0.3.0).
4. **Landing loads tail**: C10 port → M2-8 → M2R-3/4 → M4-17a–e (five sub-defects).
5. **Fuselage moment closure**: C6 closed by ΣFz only → caveat stamped on every
   deliverable for 11 days → M4-1 two-spar closure (+ breaking GID renumber).

**The signature datum:** the M1 calc review found two `[CRITICAL]` oracle deviations
(VD floor, BAL 1.4·VSF) *after* 0.2.0 shipped — but every one of the ~35 defects was
found internally (reviews ~60%, building/new tests ~25%, oracle/closure gates ~15%);
none by a user. The verification net works; it just fires late on seams that were never
given a structural owner.

---

## 3. What is working — keep, and export to sbeam

These are demonstrably effective and none should change:

- **Oracle discipline** — one manual-example test per module, ±0.1%, page-cited; twin
  closure locks; the approved-corrections register
  (`docs/20_theory/02_approved_corrections.md`) for deliberate, documented deviations.
- **Release practice** — real tags, archived per-release verification baselines
  (`40_history/01`/`02`), pre-release oracle rerun. (sbeam adopted exactly this after
  its review; sloads already had it.)
- **Structural single-sourcing where it exists** — `workflow.py` as nav SSOT **with a
  drift-guard test**, `units.deliverable_units()` resolved once per bundle,
  `load_keys.py`, the *generated* DATA_DICTIONARY. Every place a convention got a code
  owner plus a guard test, its churn stopped.
- **Plan-docs with locked decisions before execution** (C-plan, M4 sequence D-19…D-22,
  G8 plan) — design-note-before-code in practice, unwritten as a rule.
- **Byte-identical whole-suite snapshots** for refactors (M4-9's 405k-line snapshot,
  M4-12b) — cheap total-regression evidence.
- **Review waves with severity grading** — they caught both CRITICALs and drove the M4
  sequence.
- **Late-record size discipline** — M4-20 shipped as seven separately-approved steps;
  M4-10b/M4-11b deliberately deferred with stated rationale.

**Worth back-porting to sbeam** (noted for that project's backlog): the drift-guard-test
pattern, generated docs, the approved-corrections register, per-release verification
baselines, snapshot regression, and the `MissingInputError`-vs-`ValueError` contract.

---

## 4. Findings

**F1 — Uniform closure depth is the single largest avoidable cost.** Every closed item —
typo through new module — requires the full step-format history entry + backlog removal +
CHANGELOG + spec/theory sync, enforced as `[CRITICAL]` review findings. Result: 5–8 files
per small fix, 40% docs-only commits, a 6,038-line history file, and the bookkeeping trio
as the three most-churned files in the repository.

**F2 — Seam defects recur until the convention gets a code owner and a guard test.**
Units/SI (3 rebuilds), SF/ULT (7 passes), schema line stale ×3, geometry (6 steps),
`build_mass` (zero callers). In every chain, the churn ended the moment a single-source
helper + drift/guard test landed (M4-20 `deliverable_units`, M4-16 guard test, workflow
SSOT). The lesson is already proven in-repo; it is not yet a rule.

**F3 — The review process is one-size** ("porting one suite program or changing an
existing one") — no light path, no touched-area scoping — and the release gate contains
the same unbounded "all docs consistent, no drift" audit that stalled sbeam. Recurring
pre-release doc sweeps (M1-10, M2R-1, the 0.3.0 gate sweep) are its visible cost.

**F4 — Release cadence is event-triggered and beginning to stall.** Nothing has shipped
since 07-23 while `[Unreleased]` reached 84% of 0.3.0's (already large, 92-entry) scope.
The M4 sequence + M4-20 + M3-3b + the G8 report are complete and unshipped.

**F5 — The backlog is not pointed at the mission, and the mission's hardest gaps aren't
in it.** 40 open items; ~5 essential (M4-6 ground-case distributed loads, F25-2 VD
Mach-margin defect, L-1 real-stiffness stick model, M4-2 case-identity unification,
M4-8 Layer 1 SF resolver). Missing entirely: a **continuous sbeam round-trip harness**
(C4's "parses and solves in sbeam" was checked once, never gated), a **global equilibrium
invariant** (nothing asserts an exported case's wing+body+tail cards sum to n·W with zero
net moment), the gust spanwise-distribution decision, the load-application-axis vs
elastic-axis question, sloads-case→SUBCASE mapping, and gear-reaction FORCE cards.

**F6 — Duplicated prose rules with no single-source designation.** The module inventory
lives in 4+ places (CLAUDE.md naming map, PROGRAM_SPEC tables, PROJECT_GUIDE §2/§4,
overview tree); the units/ULT rules in 3–4; conventions/math-fidelity near-verbatim in 3.
CLAUDE.md is 278 lines of embedded rule text loaded every session. (Doc-currency defects
— F2's class (d) — are the direct product.)

**F7 — Numbering churn.** Seven parallel ID series (C/D/E/F/G/P1/R/M1–M4/L/L-8a–i/D-x),
gap-riddled M4 numbers, one ID collision (M4-18 minted twice), IDs coined mid-step.
Minor, but it is the same disease sbeam retired.

---

## 5. Recommendations

Emphasis per the review brief: **velocity, minimal risk.** Group A is process-only
(no change to verification depth — the oracle locks, closure locks, review waves and
snapshot gates all stay). Group B is sloads-specific. Items marked **[doc]** are concrete
edits for a follow-up documentation session; nothing has been changed yet.

### A. Adopt from the sbeam 2026-08-04 process changes

**R1. Tiered S/M/L closure. [doc]** Small fix → CHANGELOG line + backlog removal +
one-line history entry; behavior change → + affected spec/guide section; new capability →
the current full step format. Directly attacks F1 (the 5–8-file tax). This is the single
biggest low-risk velocity lever available.

**R2. Tiered, scoped review. [doc]** Light checklist (CI green, oracle/closure suite
green, tiered closure done, defect-class sweep done) for S changes; touched-area scoping
for M; the full 8-step process only for new modules/physics. Reclassify "docs not
updated" from `[CRITICAL]` to blocking-but-MAJOR.

**R3. Release cadence + bounded gate. [doc]** Cut a release every ~2–3 weeks or ~5
steps; drop the unbounded "all docs consistent" audit from the gate (consistency is
enforced per-change by R1) — the gate becomes: CI green + oracle/closure suite +
changelog cut + tag + verification baseline. **First action: `[Unreleased]` is
release-ripe now — cut 0.4.0.**

**R4. Generalize-on-first-find + guard test. [doc]** A defect fix sweeps its class
across the codebase in the same change and adds a guard/drift test where feasible.
sloads' own record proves both halves: M4-11a found four sibling defects "by building
the helper", and the stale schema line recurred until M4-16's guard test.

**R5. Single-source designation + CLAUDE.md diet. [doc]** Name one authoritative home
per duplicated fact (module inventory → PROGRAM_SPEC; units/ULT contract → overview;
conventions → one charter section, see R8) and reduce CLAUDE.md to rules + pointers
with a size budget. Kills the F6 sync chains that generate the doc-currency defect class.

**R6. Mission-tag the backlog + parked file. [doc]** Tag the ~5 essentials [E]; move the
17 long-tail L-items, the 4 placeholders, and deferrable M4/F25 items to a
`docs/30_future/02_parked.md` with their write-ups intact. The working backlog then shows
the true distance to mission (~a dozen items). Retire parallel ID series going forward
(plain sequential step numbers at promotion) — F7.

**R7. Codify design-note-before-code. [doc]** Already the de facto practice (C-plan, M4
D-decisions, G8 plan); writing it into CLAUDE.md costs nothing and protects the habit.

### B. sloads-specific

**R8. "Make it structural" rule + conventions charter. [doc]** Elevate the in-repo
lesson to a standing rule: *any cross-cutting convention (units, safety factors, IDs,
schema, axes/frames) gets a single-source code owner plus a drift-guard test the first
time it is needed — never a prose rule alone.* Pair it with a one-page conventions
charter (axes/stations/signs, the two-channel unit sets, ULT/SF contract, case-identity
scheme, `export/coordinates.py` map) that physics/export steps must cite. This is the
F2 chain-breaker, and it is prevention for exactly the seams the export boundary is
about to stress.

**R9. Re-point the near-term backlog at the export boundary. [doc]** The mission-complete
set is: the 5 essentials (F5) **plus** the missing gap items, which should be filed:
a **sbeam round-trip CI harness** (export the flagship cases, run an actual sbeam solve,
gate on success + spot values — the single highest-value new test in the project), a
**global equilibrium invariant** per exported case (Σ cards = n·W, zero net moment —
cheap, catches everything), the gust-distribution decision, the elastic-axis/application
-axis note, and case→SUBCASE mapping. Roughly 9–12 M4-sized steps ≈ 2–3 weeks at recent
cadence.

**R10. Concept-mode benchmark rule. [doc]** The FAR23 core has the oracle rule; concept
mode has the looser "physics-closure where no oracle exists." Codify it per-condition:
every new concept-mode load case ships with a stated closure/invariant gate (equilibrium
residual, reduction-to-FAR23 identity on GA inputs) in CI, benchmark-first — the
concept-mode analog of the one-manual-example-test rule.

**R11. Split the history file. [doc]** `00_completed_development.md` is 6,038 lines and
the third-most-churned file. Split by era/area (as sbeam did) and, with R1, record S-tier
closures as one-liners.

---

## 6. Expected impact

- R1+R2 halve the small-change overhead (5–8 files → 2–3) and should pull the 40%
  docs-only commit share toward ~20% — worth roughly 10–15% of total effort at the
  current mix, immediately.
- The ~40% rework share is mostly *already paid* — M4 fixed the seams it found. R4+R8
  are prevention: the export-boundary work ahead (R9) is precisely where new seams
  would otherwise breed.
- R3 removes the mega-release risk while keeping the verification baseline practice.
- R6+R9 shrink "work to go" from 40 listed items to a mission path of ~a dozen, with a
  defensible 2–3 week estimate to a demonstrated sloads→sbeam loop.

## 7. Suggested order for the documentation session

1. R6 backlog re-point + file the R9 gap items (smallest, unblocks planning)
2. R1 tiered closure + R2 tiered review — amend CLAUDE.md, CODE_REVIEW_PROCESS.md
3. R3 release rule — amend RELEASE_PROCESS.md; then cut 0.4.0
4. R5 single-source designation + CLAUDE.md diet
5. R8 conventions charter + "make it structural" rule
6. R11 history split (any time; mechanical)

## Appendix — uncommitted work (included per review brief)

The working tree carries the in-flight G8/M3-3b PDF report feature (7 new files under
`sloads/report/`/`sloads/export/`, +461/−109 lines) **with its tests
(`test_pdf_compile`, `test_report_content`, `test_report_latex`) and plan-doc updates in
the same change** — i.e., the healthy pattern this review recommends codifying. Two
hygiene notes for its closure: the shipped G8/M4-20 plan files should move from
`30_future/` to `40_history/` per the stated lifecycle rule, and stale cross-references
noted by the backlog audit (plan §7 D-refs, `models.py` → `models/`, the INDEX D-count)
are one-line fixes to batch with it.
