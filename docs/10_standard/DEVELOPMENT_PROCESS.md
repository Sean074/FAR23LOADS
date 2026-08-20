# sloads — Development Process (multi-developer)

The standard for **how work moves** from an idea to a released, oracle-locked
change when more than one person (and more than one person's AI) is working on
the repository. Design note 28 (MD-1…MD-12, agreed 2026-08-16) is the rationale;
this page is the rule. `CONTRIBUTING.md` at the repo root is the short human
on-ramp and links here; `CLAUDE.md` is the AI's operating contract and links here.
Nothing on this page changes *what* the standard requires (closure tiers,
benchmark-first, make-it-structural, review depth, release gate) — it re-homes
*where* each requirement is checked: **the session becomes the pull request.**
§0 states which of these mechanisms are switched off while the repository has a
single collaborator; §1–§9 apply in full from the day a second one is added.

---

## 0. Working alone — the solo profile (added 2026-08-17)

Note 28 buys its value from concurrency: a reviewer who is not the author,
counters that two branches can race on, an issue tracker two people can both
read. With **one collaborator** (the GitHub collaborator list is the test) those
mechanisms cost a CI round-trip and a bookkeeping channel per item and protect
nothing — the first week of the process on 0.6.0 (PR #25 / issue #1: template
placeholder left unfilled, the issue never closed, the backlog row-removal
conflicting with the next branch) is the evidence. While solo:

| Mechanism | Solo profile |
|---|---|
| Branch / PR per item (§1, §2) | **Optional.** Work on a short-lived branch; when `ruff` · `mypy` · `pytest` are green locally, merge to `main` (fast-forward or squash — **one commit per closed item**, subject in the project style, so `git log` stays the step-per-commit record) and push. CI on the push to `main` is the record. Batching independent tier-S items on one branch is fine; each still gets its own commit and its own closure. **A docs-only change set** — every path either `*.md` or under `docs/` or `changes/` — needs no branch at all: edit on `main` and close there (`solo_close.sh --slug <slug>`), because it cannot break the calc and its whole gate is the guard files below. Anything touching `.py`, a fixture or config takes a branch, so a failed gate has somewhere to abort to. |
| Non-author review, CODEOWNERS (§2, §7) | **Not applicable** — unsatisfiable with one person. Review depth (`CODE_REVIEW_PROCESS.md` §0) is still owed; it is the AI's review in the session, and its findings are filed with bodies (rule 5). |
| Issues as system of record (§4) | **Optional, and optional in the tooling too.** `00_backlog.md` is the record; the row leaves **in the closing commit** (no `Closes #N`, no `render`, no stale-row window). Issues may be kept for items with discussion; if kept, close them by hand with the merge SHA, or pass the number to `solo_close.sh` and it does it. The issue argument to both scripts is **optional**: omit it and neither script calls `gh` at all — no auth check, no issue read, no `gh issue close`, no `backlog_issues.py check` (which is the table ↔ issues guard and means nothing without issues). Requiring an issue in the scripts made mandatory the one mechanism this row calls optional, at four network round-trips per item. |
| Rebase before regenerating (§6) | **Unchanged**, and the priority table is a fourth shared counter — a closing commit deletes its own row and touches nothing else (no renumbering; rows never cite another row's ordinal, dependencies name the band or the `#N`). |
| Closure tiers, fragments, design-note-before-physics, rules 1–6, release gate (§3, §5, §8, §10) | **Unchanged.** These are the quality mechanisms; none of them needs a second person. A tier-L design note is agreed in chat and merged with the work (`CLAUDE.md` rule 1); §9's "agreed in chat is retired" resumes with the second collaborator. |
| Branch protection on `main` | Owner-applied to match: PR requirement off (or admin bypass on) while solo; the required checks are the **fast gate** — `test (3.12)`, `typecheck`, `sbeam-roundtrip (3.12)`. |
| CI shape (`ci.yml`) | **PR = fast gate, one interpreter** (3.12 with coverage, mypy, solver round-trip on 3.12; ~half the wall-clock of the full matrix). The 3.9/3.11 compatibility legs run on every push to `main` and are fixed forward. A re-push cancels the run in flight (`concurrency`). Applies in both profiles — the compatibility claim is not a per-PR question. |
| Local gate before merge/push | `ruff` · `mypy` (the pre-commit hook, ~10 s) and the suite **once**, on the whole tree, immediately before the merge/push (the pre-push hook) — not after every edit. **The gate scales to the change set:** a docs-only change set (above) runs `ruff` · `mypy` and the five guard files — `test_doc_currency`, `test_changelog_fragments`, `test_schema_guards`, `test_backlog_issues`, `test_workflow` — in ~3 s instead of the suite's ~150 s; `solo_close.sh` decides from the paths and `--full-gate` overrides. Any other change set takes the whole suite. CI on the push to `main` is the gate either way. While iterating run **the module's own test file**, and `test_deliverable_units.py` once before closing rather than per edit — it is where a physics change shows first (the Imperial digest) *and* now the slowest file in the suite, so per-edit it costs more than the whole suite did when this row was written (timings and the ~43 s parallel floor: `.pre-commit-config.yaml`, re-measured 2026-08-19). |

**The loop is scripted (issue #27, 2026-08-17; cycle-time revision 2026-08-19):**
`scripts/solo_start.sh [<issue>] <type>/<slug>` opens the branch (preflight: on
`main`, clean tree; with an issue: `gh` authenticated and the issue open) and
`scripts/solo_close.sh [<issue>] "<Subject>"` runs the closing half in order —
gate (`ruff` · `mypy` · `pytest`, scaled to the change set), one commit with
the project-style parenthetical, `--ff-only` land + push, `gh issue close` with
the `main` SHA, then branch delete / `backlog_issues.py check` / issue state /
last CI run. It refuses to start until the tier's fragment(s) exist, and — when
an issue is given — until that item's `(#N)` row has left the priority table;
it stops at the first failure with the recovery printed (`--dry-run` shows the
sequence; `--help` the options). **Three of those steps are conditional, matching
the three rows above:** the issue number is optional and drops every `gh` call
with it; a docs-only change set may be closed on `main` (`--slug` then names
the fragment, since there is no branch to take it from) and skips the checkout,
merge and branch delete; and the gate shrinks to the guard files for that same
docs-only set. The step between start and close — the work and the closure
artefacts — is the developer's; the scripts encode nothing that this section
does not already say (rule 3: the sequence is structural, not a chat
transcript), and `tests/test_solo_scripts.py` holds the two in step.

**Switch-over is mechanical:** the day a second collaborator is added, branch
protection goes back to §2, `scripts/backlog_issues.py create` opens the issues
for the rows then in the table, and this section stops applying. Nothing done
under the solo profile has to be redone.

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
  row leaves the priority table at the next `backlog_issues.py render` (§4) —
  the PR itself does not edit the table.
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
- **The table is a view of the issues, not a second record.** A closing PR
  does **not** edit the table: merging closes the issue, and
  `scripts/backlog_issues.py render` (owner-run — at review of a backlog PR
  and at release cut; needs `gh`) drops the rows whose issues are closed and
  re-emits every open row from its issue body, touching nothing else. Rows
  therefore never renumber and never cite another row's ordinal (dependencies
  name the band or `#N`), so two PRs cannot conflict on the table.
  `render` and `create` share one row-block writer (`row_body`) and
  `tests/test_backlog_issues.py` round-trips the live table through it. Under
  §0 (solo) the file is the record, the row leaves in the closing commit, and
  `render` is not run.
- **Guard (both ways):** every priority-table row names an open issue, and
  every open issue labelled `band:*` appears in the table
  (`scripts/backlog_issues.py check`; same cadence as `render` — it needs
  `gh`, so it is a script, not a pytest).
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
