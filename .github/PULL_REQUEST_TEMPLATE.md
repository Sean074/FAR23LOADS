<!-- PR title = the squash commit subject, project style:
     "Step 14: PBAR/MAT1 pass-through (tier M, 2026-08-20)"  /  "Fix: gear CSV -ULT marker (R6-C2, tier S, …)" -->

**Closes** #___            **Tier:** S / M / L            **AI-assisted:** yes / no
<!-- Replace ___ with the issue number — GitHub only auto-closes on a literal
     "Closes #N"; a leftover placeholder renders as "Closes #" and closes nothing
     (PR #25 / issue #1, 2026-08-17). Several items: "Closes #3, closes #4". -->

<!-- Working alone (DEVELOPMENT_PROCESS.md §0)? Fill "Closes" only if the item
     has an issue; the backlog row leaving in this commit is the closure. -->
**Design note (tier L / physics):** `docs/30_future/NN_….md` — merged at AGREED? yes / n.a.

## What changed and why
<!-- two to five lines; the fragment says it in the changelog voice, this says it to the reviewer -->

## Closure in this PR (`DEVELOPMENT_PROCESS.md` §3 — tick what your tier requires)
- [ ] `changes/<slug>.<type>.md` fragment (S, M, L)
- [ ] `changes/<slug>.history.md` — one paragraph (M) / full step format (L)
- [ ] affected `PROGRAM_SPEC.md` / standard-doc sections (M, L)
- [ ] `theory_sources.md` citation; design note flipped to *shipped* (L)
- [ ] backlog priority-table row updated (issue closes on merge)
- [ ] guard test added for any new cross-cutting convention (rule 3) / same-class sweep done (rule 4)

## Shared counters (`DEVELOPMENT_PROCESS.md` §6)
- **`SCHEMA_VERSION` bumped:** no / yes → v__ (rebased on `main` first)
- **Imperial digest regenerated:** no / yes — the wave: <!-- what changed, why it is a claim -->
- **New case-ID band:** no / yes → <!-- band -->

## Gates
- [ ] `ruff check sloads/ cli.py app/ scripts/` · `mypy` · `pytest` green locally
- [ ] oracle/closure test present for any new physics (benchmark-first)

## For the reviewer (`CODE_REVIEW_PROCESS.md` §Approval gate — n/a under the solo profile, `DEVELOPMENT_PROCESS.md` §0)
- [ ] review depth matches the tier (§0); reviewer ≠ author; CODEOWNERS owner for SSOT paths
- [ ] no `[CRITICAL]`/`[MAJOR]` open; closure complete for every item this PR closes
- [ ] digest wave (if any) confirmed as intended; no silent default introduced
