# sloads — Development Process (multi-developer)

The standard for **how work moves** from an idea to a released, oracle-locked
change when more than one person (and more than one person's AI) is working on
the repository. Design note 28 (MD-1…MD-12, agreed 2026-08-16) is the rationale;
this page is the rule. `CONTRIBUTING.md` at the repo root is the short human
on-ramp and links here; `CLAUDE.md` is the AI's operating contract and links here.
Nothing on this page changes *what* the standard requires (closure tiers,
benchmark-first, make-it-structural, review depth, release gate) — it re-homes
*where* each requirement is checked: **the session becomes the pull request.**

---

## 1. The flow

```
issue (#N, labelled tier/tag/band)            <- the system of record for open work
   |
   |  tier L / physics: note/NN-slug PR  ->  design note merged at AGREED  (MD-6)
   v
branch  <type>/<slug>  off main               <- one item per branch, short-lived   (MD-1)
   |
   |  work; closure artefacts land IN the PR   (MD-3)
   |  rebase on main before you regenerate anything (schema, digest, bands)  (MD-7)
   v
PR -> CI (test x3, typecheck, sbeam-roundtrip) -> review at tier depth (>=1, != author; owner per CODEOWNERS)
   |
   |  squash-merge; PR title = commit subject; branch deleted   (MD-2)
   v
main (always releasable)  ->  release manager cuts release/x.y.z per RELEASE_PROCESS.md §4  (MD-11)
```

## 2. Branches and merging (MD-1, MD-2)

- **Trunk-based.** `main` is always releasable. Branch from `main`; rebase on
  `main` before merge; delete on merge. No long-lived integration branches. The
  only other branch kind is the hotfix branch of `RELEASE_PROCESS.md` §6 and the
  release manager's `release/x.y.z` (§8 below).
- **Names:** `<type>/<slug>` — `step/14-pbar-passthrough`, `fix/gear-csv-ult-marker`,
  `note/28-multi-dev`, `docs/…`, `chore/…`. The slug is the fragment slug.
- **`main` is protected** (settings, owner-applied): PRs only, the owner
  included; required checks `test (3.9)`, `test (3.11)`, `test (3.12)`,
  `typecheck`, `sbeam-roundtrip (3.11)`, `sbeam-roundtrip (3.12)`; **one
  approving review from someone other than the author**; review from Code
  Owners required (`.github/CODEOWNERS`); stale approvals dismissed on push;
  conversations resolved; **linear history — squash-merge only**.
- **Squash-merge, PR title = commit subject** in the project's existing style
  (`Step 14: PBAR/MAT1 pass-through (tier M, 2026-08-20)`), so `git log` stays
  the step-per-commit record it is today.
- **`self-merge-ok`:** a PR labelled so — tier S, docs/hygiene only, **no change
  under `sloads/`** — may be merged by its author once CI is green. Anything
  else waits for its reviewer.

## 3. Closure travels in the PR (MD-3, MD-4)

The Step Completion Requirement (`CLAUDE.md`) reads "same session"; with more
than one developer it means **same PR**. A PR that closes an item carries, at
its tier:

| Tier | In the PR |
|---|---|
| **S** | `changes/<slug>.<type>.md` fragment; `Closes #N` in the body |
| **M** | S + the affected `PROGRAM_SPEC.md`/standard-doc sections + `changes/<slug>.history.md` (one paragraph) |
| **L** | M + `theory_sources.md` citation + the design note flipped to *shipped* + `changes/<slug>.history.md` (full step format) |

- **History entries are fragments** (`<slug>.history.md`), rolled to the top of
  `docs/40_history/00_completed_development.md` at release cut by
  `scripts/build_changelog.py`, so concurrent PRs never edit the same line
  there. Until the cut, `ls changes/` is the release's history. Only the
  release-cut block is written directly, by the release manager.
- **Backlog removal is `Closes #N`.** Merging the PR closes the issue; the
  priority table in `00_backlog.md` is updated in the same PR (its row goes).
- "Closure in a follow-up" is a `[MAJOR]` review finding, exactly as before.
- The PR template is the tier table as a checklist; the reviewer's approval
  gate is `CODE_REVIEW_PROCESS.md` §Approval gate.

## 4. Issues are the record; `00_backlog.md` is the plan (MD-5)

- **Every open item is a GitHub issue** with labels `tier:S|M|L`, `tag:E|V`,
  `band:A|B|…`, `kind:defect|step|note|hygiene`, plus `physics`,
  `needs-design-note`, `parked`, `self-merge-ok` as apply; a **milestone per
  release** (`0.6.0`); an assignee when someone is on it. The GitHub Project
  board is the view.
- **`docs/30_future/00_backlog.md` keeps the plan**: mission, definition of done,
  the reference-authority hierarchy, and the **priority table** with bands —
  each row `| Pri | title (#N) | what ships | tag | tier | depends |`. The
  detail bodies live in the issues. `02_parked.md` retires: a parked item is an
  issue labelled `parked` and closed as not-planned.
- **Guard (both ways):** every priority-table row names an open issue, and
  every open issue labelled `band:*` appears in the table
  (`scripts/backlog_issues.py check`; run at review of any backlog PR and at
  release cut — it needs `gh`, so it is a script, not a pytest).
- Migration from the single-file backlog: `scripts/backlog_issues.py plan`
  (prints the issue set), `create` (opens them via `gh`, records `title → #N`),
  `rewrite` (adds `#N` to the table rows). Owner-run, once.

## 5. Design notes and the shape of `30_future/` (MD-6)

- **Tier L and every physics change: a design note PR before code.** Open
  `note/NN-slug` with the note at `PROPOSED`; the owner of what it touches
  reviews (theory reference, `CONVENTIONS.md` citations, target numbers,
  tolerances — `CLAUDE.md` rule 1); merge at `AGREED — no code`. The
  implementing PR references it and flips it to `shipped <date>`.
- **Numbers are claimed by opening the note PR.** Gaps and out-of-order numbers
  are fine; `docs/00_INDEX.md` is the index (guarded both ways by
  `tests/test_doc_currency.py`).
- Every note carries `**Owner:** @handle` and `**Reviewers:** …` under its title.
- `30_future/` holds only `00_backlog.md`, the live notes, and nothing else.
  Shipped notes move to `40_history/` at release cut (note 26 DV-5).

## 6. The three shared counters — rebase before you regenerate (MD-7)

| Counter | Rule | Collision guard |
|---|---|---|
| `SCHEMA_VERSION` (`sloads/models/project.py`) | bump on the branch; **re-bump at rebase** if `main` moved past you, keeping the migration chain linear | `tests/test_migrations.py` contiguity check |
| Imperial digest (`tests/fixtures_imperial/digests.json`) | a PR carries **at most one** digest wave; regenerate *after* rebasing on `main`; the fragment names the wave; the reviewer confirms it (`PROJECT_GUIDE.md` §"Imperial output is frozen") | `test_imperial_output_matches_the_frozen_baseline` |
| Case-ID bands (`sloads/case_ids.py`) | claim a new band on the branch | `tests/test_case_ids.py` uniqueness |

Two PRs with digest waves serialize: the second rebases and regenerates.

## 7. Ownership and review (MD-8)

- `.github/CODEOWNERS` lists the single-source owners (`CLAUDE.md` rule 3 with a
  human attached): the calc SSOT files, the oracle register and digest fixtures,
  and the standard every developer's AI reads. **An oracle deviation is approved
  by the owner of `02_approved_corrections.md`, in the PR** — the "user approval"
  of `CLAUDE.md` now has a place where it is recorded.
- Review depth follows `CODE_REVIEW_PROCESS.md` §0 (tier S checklist, M scoped
  steps, L full process + design-note check). The reviewer is never the author.

## 8. Releases (MD-11)

- A **release manager** is named on the milestone and rotates. They cut per
  `RELEASE_PROCESS.md` §4 on a `release/x.y.z` branch — version bump, changelog
  build (which also rolls the history fragments), history roll, plan-note moves,
  baseline — as one PR reviewed like any other, then tag from `main`.

## 9. The AI with more than one developer (MD-9)

- **One `CLAUDE.md`** in the repo is every developer's AI contract; it is in
  CODEOWNERS and is reviewed like code. Per-developer settings live in
  `.claude/settings.local.json` (git-ignored); the shared allowlist is
  `.claude/settings.json`.
- **The AI never pushes, opens, or merges a PR.** The developer does and is the
  author of record ("Git is the user's to run", unchanged).
- A PR whose diff is substantially AI-generated says so in the template's
  `AI-assisted:` line; the reviewer reads accordingly.
- "Agreed in chat" is retired: the AI's design-note check is "the note is
  merged at AGREED".

## 10. What did not change (MD-12)

The closure tiers, benchmark-first done, make-it-structural, generalize-on-first-find,
the review steps and severities, the release gate, the documentation-currency rule,
the fragment mechanism, and the AI's git rule.
