# Design note 26 — documentation volume: archive, fragments, tier S

**Status:** AGREED 2026-08-16 (user review of the three recommendations, all
accepted) — ✅ **shipped 2026-08-16**, same session; kept as the plan of record.
Closes backlog **R11** ("Split `40_history/00_completed_development.md` by
era", 2026-08-05 process review). Tier M closure.

## 1. The problem

The 2026-08-05 process review (F1) measured the closure machinery's cost:
40 % of commits docs-only; the three most-churned files in the repo were the
backlog (131×), `CHANGELOG.md` (131×) and the completed-development file
(108×). The tiered closure rule (R1) cut the *depth* of a closure but not its
*shape*: every closure still edited the same three large append-only markdown
files, and two of them kept growing — on 2026-08-16 the history file was
9,127 lines and the changelog 5,143, with 82 commits since 2026-08-05 touching
the history 65×, the changelog 68× and the backlog 75×.

Three costs, in order of weight:

1. **A memory-less collaborator pays for volume every session.** The AI reads
   the pointers in `CLAUDE.md` and then whatever they point at; a 9k-line record
   whose first 1,100 lines are the current cycle is 8k lines of history that no
   current task needs but that any grep, review or "what did we decide" question
   wades through.
2. **Append-only files are merge and attention hazards.** Every closure is an
   edit near the top of a 5k-line file; the 0.6.0-candidate review found the
   closure entries themselves correct but the *surrounding* documentation
   currency drifting (R6-D1…D8) — attention spent on the mechanics of the edit
   is attention not spent on the doc that actually describes the code.
3. **The Tier S history line duplicated the changelog line.** Same sentence,
   two files, both edited by hand — exactly the "prose that exists twice drifts"
   defect class that R5/F6 named for `CLAUDE.md`.

## 2. Decisions

| ID | Decision | Rationale |
|---|---|---|
| **DV-1** | The live history file holds the **current cycle plus the previous release-cut block**; everything older rolls into a frozen, do-not-edit archive `40_history/NN_completed_development_to_<version>.md`. First cut: at the 0.5.0 block → `11_completed_development_to_0.5.0.md` (7,970 lines, verbatim). | The release-cut block is a natural, unambiguous cut line and is already the regression-baseline anchor. Verbatim move = zero information loss; "do not edit" = an archive is a record, not a document. |
| **DV-2** | `CHANGELOG.md` `[Unreleased]` is **never hand-edited**. Each closure writes one fragment `changes/<slug>.<type>.md` (`type` ∈ breaking/added/changed/fixed/removed; body = the CHANGELOG bullet(s) verbatim). `scripts/build_changelog.py X.Y.Z --date …` assembles them at release cut, merges by subsection (fragments first, then any legacy text), opens a fresh `[Unreleased]`, deletes the consumed fragments. Released sections are byte-untouched. | Closure becomes *one new small file* — no edit to a 5k-line file, no merge hazard, and the release note is generated rather than curated. In-repo script (~150 lines, stdlib only) rather than `towncrier`: no new dependency on the 3.9 matrix, and the format is the project's own. |
| **DV-3** | Legacy: the hand-written `[Unreleased]` text present on 2026-08-16 stays and is folded into 0.6.0 by the builder (its subsections are preserved, fragments lead). Fragments start now. | Zero-risk migration; the alternative (splitting ~250 lines into ~20 fragments) is churn for the sake of purity. |
| **DV-4** | **Tier S = fragment + backlog removal. No history entry.** Tier M = S + standard-doc sections + a one-paragraph history entry. Tier L = M + `theory_sources.md` + full step format. | The Tier S history line was the same sentence as its changelog line. History now records *decisions and behaviour changes*; the changelog records *everything*. |
| **DV-5** | `RELEASE_PROCESS.md` §4 gains a **history-roll step** — mechanical and bounded: build the changelog from fragments; move `30_future/` notes whose status reads *shipped* to `40_history/`; if the live history exceeds **1,500 lines** (guard test warns), cut at the previous release block into a new archive. Statuses and line counts are the only inputs — it is not an audit. | Answers the user's question ("should the pre-release review clean the history?"): yes, provided it is a mechanical roll, not a re-read. An unbounded doc audit at release is what R3 removed in 2026-08-05; this re-adds only a bounded one. |
| **DV-6** | Guard test `tests/test_changelog_fragments.py`: fails on a mis-named fragment or a non-bullet body (found now, not at release); exercises the builder's pure functions on strings; **warns** (does not fail) when the live history passes 1,500 lines. | Rule 3 in `CLAUDE.md`: a convention gets a code owner plus a drift guard, never prose alone. Size is a roll trigger, not a defect in the change that crossed it, hence warn. |

## 3. What ships (2026-08-16)

- `docs/40_history/00_completed_development.md` — 1,155 → live cycle only, header
  gains the archive pointer and the tier rule; `11_completed_development_to_0.5.0.md`
  — the frozen pre-0.5.0 record.
- `changes/README.md` (the fragment contract), first fragment
  `changes/doc-volume-history-archive-fragments.changed.md`.
- `scripts/build_changelog.py` (`--dry-run` previews; verified against the live
  `CHANGELOG.md`: fragment leads `### Changed`, legacy `### Added`/`### Fixed`
  preserved, 0.5.0 and below byte-identical).
- `tests/test_changelog_fragments.py` (14 tests).
- `CLAUDE.md` tier table; `CODE_REVIEW_PROCESS.md` §0/§1 closure checklist;
  `RELEASE_PROCESS.md` §3.1, §4 (steps 2–3), §5; `docs/00_INDEX.md` rows;
  backlog R11 removed.

## 4. Not done, on purpose

- **`PROGRAM_SPEC.md` (1,480 lines) and the 25 plan notes** are untouched. The
  spec is *live* per-module documentation and test-guarded against the registry;
  its size is proportional to the module count, not to time. Plan notes are
  addressed by DV-5's per-release move, not by a one-off sweep — nine of the 25
  are already `40_history/` candidates and will move at the 0.6.0 cut.
- **`docs/40_history/10_backlog_state_narrative_to_2026-08-16.md`** stays as
  archived on 2026-08-16.
- **No CI job** for the builder beyond the guard test; the release cut is a
  human step and `--dry-run` is its preview.

## 5. Acceptance (met)

- `pytest tests/test_changelog_fragments.py` green; `ruff` clean.
- `scripts/build_changelog.py --dry-run` on the live changelog reproduces every
  legacy `[Unreleased]` bullet plus the new fragment, in subsection order.
- Live history ≤ 1,500 lines (1,166 after this note's own entry).
- Archive line count + live line count = original 9,127 + header lines added.
