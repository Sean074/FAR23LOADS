- **Doc volume: history archived to 0.5.0, changelog fragments, tier S trimmed
  (backlog R11 closed, tier M, 2026-08-16).** Design note
  `docs/30_future/26_doc_volume_reduction_note.md`, all three recommendations
  accepted at user review. (a) `docs/40_history/00_completed_development.md`
  cut at the 0.5.0 release block; ~7,970 pre-0.5.0 lines moved verbatim to the
  frozen `11_completed_development_to_0.5.0.md`. (b) `[Unreleased]` is no
  longer hand-edited: each closure drops one `changes/<slug>.<type>.md`
  fragment (this entry is the first) and `scripts/build_changelog.py X.Y.Z
  --date …` assembles them at release cut; `tests/test_changelog_fragments.py`
  guards fragment names/shape and warns when the live history passes 1,500
  lines. (c) Tier S closure = fragment + backlog removal, no history entry
  (`CLAUDE.md`, `CODE_REVIEW_PROCESS.md` §0). `RELEASE_PROCESS.md` §4 gains a
  mechanical history-roll step. Legacy hand-written `[Unreleased]` text folds
  into 0.6.0 verbatim.
