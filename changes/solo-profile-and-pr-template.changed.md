- **Development process simplified: solo profile, PR-fast CI, derived backlog
  table, template placeholder made visible (tier S, 2026-08-17).**
  `DEVELOPMENT_PROCESS.md` §0 states which note-28 mechanisms are off while the
  repository has one collaborator — PR-per-item, non-author review and the
  issue mirror become optional; one commit per closed item, the backlog row
  leaving in that commit, and every closure tier / rule stay in force — and
  how the full flow switches back on with a second collaborator. **CI:** a
  pull request now runs the fast gate only (`test (3.12)` with coverage,
  `typecheck`, `sbeam-roundtrip (3.12)`); the 3.9/3.11 compatibility legs run
  on push to `main` and are fixed forward; a re-push cancels the run in flight
  (`concurrency`). **Backlog:** the priority table is a *view* of the issues
  under the multi-developer flow — new `scripts/backlog_issues.py render`
  drops closed rows and re-emits open ones from their issue bodies (one
  row-block writer shared with `create`, round-tripped on the live file by
  `tests/test_backlog_issues.py`), so a closing PR never edits the table, rows
  never renumber, and dependencies name the band or `#N`; the eleven "Body
  moved to issue #N" stubs and their two "Item detail" headings are gone.
  Prompted by the first week on 0.6.0: PR #25 merged with the template's
  invisible `#<!-- issue -->` placeholder unfilled, so issue #1 never
  auto-closed; the template now reads `Closes #___` with the rule beside it.
