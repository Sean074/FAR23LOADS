# Design note 28 — multi-developer development: process, ownership, and the shape of `30_future/`

**Owner:** @Sean074 · **Reviewers:** — *(design note 28 MD-6: the owner of what a note touches reviews it as a PR)*

**Status:** AGREED 2026-08-16 (user, decision by decision) — ✅ **shipped
2026-08-16**, same session; kept as the plan of record. Tier M (process + docs
+ the history-fragment tooling; no physics). Answers the "single-author bus
factor" finding of the 2026-08-16 code-standard summary (§5.4). **The four
user calls:** MD-2 → **1 reviewer ≠ author; `self-merge-ok` for tier-S
docs/hygiene PRs (nothing under `sloads/`) on green CI**; MD-5 → **GitHub Issues
+ Project board**; MD-8 → **`@Sean074` on every CODEOWNERS line for now**; MD-4
timing → **now, whole build list in one pass**. Two things remain **yours to do
in GitHub settings** (they are not files): branch protection on `main` per
`DEVELOPMENT_PROCESS.md` §2, and the one-off `scripts/backlog_issues.py create
--milestone 0.6.0` + `rewrite` (review `plan` first).

## 1. What changes when there are two of you

Everything the project does today assumes one head and one working tree:
`main` is pushed to directly; "closure in the same session" is enforced by
habit; the backlog is a single 500-line file edited by hand; the history file
grows from the top; `SCHEMA_VERSION` and the Imperial digest are bumped/regenerated
whenever a step needs it; a design note is "agreed in chat"; the AI's rules
live in one file that one person keeps under budget. None of that is wrong —
it is what made 252 commits in 8½ weeks possible — but each item is a
**collision point** the moment two branches exist:

| Today | Collision with two developers | Fix (decision) |
|---|---|---|
| direct pushes to `main` | untested code lands; nobody reviewed it | branch + PR + protection (MD-1, MD-2) |
| "closure in the same session" | closure of a PR-in-flight is invisible to the other branch | "closure travels **in the PR**" (MD-3) |
| `CHANGELOG.md` `[Unreleased]` | — already solved: `changes/` fragments (note 26) | keep |
| history file appended at the top | every concurrent tier-M/L PR conflicts on the same lines | history **fragments**, rolled at release like the changelog (MD-4) |
| `00_backlog.md` as the system of record | two people editing one file; no assignee; no "who is on it" | GitHub Issues + Project as the record; the markdown keeps the *plan* (MD-5) |
| `SCHEMA_VERSION` bump per step | two branches both mint v53; migration chain forks | bump-at-rebase rule + guard (MD-7) |
| Imperial digest regeneration "is a claim" | two branches both regenerate; the second to merge silently overwrites the first's claim | one digest wave per PR, regenerate on rebase, reviewer confirms the wave (MD-7) |
| design note "agreed in chat" | the agreement is in one person's chat history | design-note **PR** before code, agreed by review (MD-6) |
| plan-note numbers `NN_` | two branches both claim `29_` | claim by opening the PR; gaps allowed (MD-6) |
| `CLAUDE.md` + memory per developer | each developer's AI has a different picture | one `CLAUDE.md` in the repo (already), per-developer `settings.local.json` git-ignored, AI-authored PRs marked (MD-9) |
| no `CONTRIBUTING.md`, no PR template, no CODEOWNERS | a second contributor's only on-ramp is `CLAUDE.md`, written for the AI | the human documents (MD-10) |
| one release manager by default | releases stall when that person is busy | named role, rotates (MD-11) |

## 2. Decisions

### Branching and merging

| ID | Decision | Rationale |
|---|---|---|
| **MD-1** | **Trunk-based with short-lived branches.** `main` is always releasable. One branch per backlog item / defect / step, named `<type>/<slug>` (`step/14-pbar-passthrough`, `fix/gear-csv-ult-marker`, `note/28-multi-dev`, `docs/…`, `chore/…`). Branch from `main`, rebase on `main` before merge, delete on merge. No long-lived integration branches, no release branches except the hotfix branch `RELEASE_PROCESS.md` §6 already defines. | The project's cadence rule ("release small and often") is a trunk-based rule already; branches that live longer than a release-worth of work re-create the `[Unreleased]`-has-no-baseline problem R3 removed. |
| **MD-2 (user)** | **Branch protection on `main`:** PRs only (the owner included); required checks `test (3.9/3.11/3.12)`, `typecheck`, `sbeam-roundtrip (3.11/3.12)`; **1 approving review** from someone other than the author; linear history — **squash-merge**, PR title becomes the commit subject in the project's existing style (`Step 14: … (tier M, 2026-08-20)`); stale approvals dismissed on new pushes; conversation resolution required. | Squash keeps `git log` as the step-per-commit record it is today (a branch's 15 WIP commits are noise in the history file's terms); linear history keeps `git bisect` against the oracle baselines trivial. The alternative — merge commits — preserves branch detail nobody reads here. **Your call**: 1 vs 2 reviewers, and whether the owner may self-merge tier-S docs-only PRs after CI (recommend: yes, labelled `self-merge-ok`, so a typo fix does not wait a day). |

### Closure, history, backlog

| ID | Decision | Rationale |
|---|---|---|
| **MD-3** | **"Closure travels in the PR."** The Step Completion Requirement's "same session" becomes "same PR": a PR that closes an item carries its fragment, its docs at tier depth, its history entry (as a fragment, MD-4), its backlog/issue closure (`Closes #N` in the body, MD-5), and its guard tests. The PR template is the tier table as a checklist; the reviewer's approval gate (`CODE_REVIEW_PROCESS.md`) already lists "closure tier complete". A PR that leaves closure to "a follow-up" is a `[MAJOR]`. | The rule's *purpose* — no batch, no deferred closure — is unchanged; the unit that can be checked by someone else is the PR, not the session. |
| **MD-4** | **History entries become fragments too.** `changes/<slug>.history.md` (tier M: one paragraph; tier L: full step format), consumed by `scripts/build_changelog.py` at release cut into the **top** of `docs/40_history/00_completed_development.md`, newest first, exactly as the changelog fragments are. Until the cut, the history of the current cycle *is* the fragment folder — `ls changes/` reads as the release's history. The one exception is the release-cut block itself, written by the release manager at the cut. | Removes the last hand-edited append-only file from the per-PR path; two tier-M PRs no longer conflict on the history's first line. One mechanism, two destinations. |
| **MD-5 (user)** | **GitHub Issues + a Project board become the system of record for open work; `00_backlog.md` becomes the *plan* — mission, definition of done, the priority table with bands, the reference-authority hierarchy — each table row linking to its issue.** Labels: `tier:S/M/L`, `tag:E/V`, `band:A/B/…`, `kind:defect/step/note/hygiene`, `needs-design-note`, `physics`, `self-merge-ok`; a milestone per release (`0.6.0`). Item bodies (the "detail below" text) move to the issue; parked items are issues labelled `parked` and closed-as-not-planned, and `02_parked.md` retires. Migration: a one-off `gh issue create` script from the current backlog rows, then the markdown rows shrink to `| Pri | title (#N) | ships | tag | tier | depends |`. The AI reads issues with `gh issue list/view` (already in the allowlist pattern); the doc-currency guard adds "every priority-table row names an open issue, and every open issue labelled `band:*` appears in the table" (both ways, like the INDEX guard). **Alternative if you want to stay in-repo:** one file per item in `docs/30_future/backlog/<slug>.md` with a YAML header (`tier`, `tag`, `band`, `owner`, `depends`), the table generated from the headers by a script the guard test re-runs. Same conflict-freedom, no GitHub dependency, but no assignee/notification/board and the AI can't `Closes #N`. **Your call.** Recommend Issues: the assignment/notification half is the part two developers actually need. | A single mutable file cannot say *who is on it*; two developers will edit adjacent rows on the same day; and PR↔item linkage (`Closes #N`) makes backlog removal automatic instead of a checklist line. |

### Design notes, ownership, and the shape of `30_future/`

| ID | Decision | Rationale |
|---|---|---|
| **MD-6** | **A design note is a PR before code.** For tier L (and any physics change): open `note/NN-slug` with the note at `PROPOSED`, get review from the code owner of what it touches (MD-8), merge it at `AGREED — no code`; the implementing PR then references it and flips it to `shipped`. Numbers: **claim by opening the note PR**; gaps and out-of-order numbers are fine (the INDEX row is the index, not the number). Every note gains two header lines: `Owner: @handle` and `Reviewers: @handle …`. `30_future/` therefore holds only: `00_backlog.md` (the plan, MD-5), the live notes, and — if MD-5's in-repo alternative is chosen — `backlog/`. Shipped notes move to `40_history/` at release cut (note 26 DV-5, unchanged). | "Agreed in chat" is invisible to the second developer and to the reviewer; the PR is where the agreement is recorded, and review by the owner of the touched SSOT is the check that the note cites `CONVENTIONS.md` correctly. |
| **MD-7** | **Concurrency rules for the three shared counters**, each with a guard where one is feasible: (a) **`SCHEMA_VERSION`** — bump on the branch as today, **re-bump at rebase** if `main` moved past you (the migration chain must stay linear); `tests/test_migrations.py` already asserts the chain is contiguous, so a fork fails CI. (b) **Imperial digest** — a PR may carry **one** digest wave; regenerate *after* rebasing on `main`; the fragment states the wave and the reviewer confirms it (`PROJECT_GUIDE.md` §"Imperial output is frozen" — unchanged, now with two people). Two PRs with waves serialize: second rebases and regenerates. (c) **case-ID bands** (`case_ids.py` allocators): a new band is claimed in the band table on the branch; `test_case_ids.py`'s uniqueness guard fails on a collision at rebase. Rule of thumb: **rebase before you regenerate anything**. | These are the three places two branches can both be "right" and merge to something wrong; each already has a guard that fails on the collision, so the rule is *when* to run it, not a new test. |
| **MD-8** | **`.github/CODEOWNERS`** — review by the owner is required for: `sloads/safety_factors.py`, `sloads/units.py`, `sloads/case_ids.py`, `sloads/models/`, `sloads/migrations.py`, `sloads/export/coordinates.py`, `docs/10_standard/CONVENTIONS.md`, `docs/20_theory/02_approved_corrections.md` (oracle deviations — the "user approval" rule becomes "owner approval, recorded in the PR"), `docs/10_standard/PROGRAM_SPEC.md`, `tests/imperial_baseline.py` + `tests/fixtures_imperial/`, `CLAUDE.md`, `.github/`. Everything else: any maintainer. Start with one owner (you) on every line; add names as people take ownership. | The SSOT-owner-plus-drift-guard rule (`CLAUDE.md` rule 3) gets a *human* owner too; the register of approved oracle deviations stays a gated door. |

### The AI with more than one developer

| ID | Decision | Rationale |
|---|---|---|
| **MD-9** | **One `CLAUDE.md`, per-developer local settings, marked AI PRs.** `CLAUDE.md` stays the shared operating contract (in the repo, reviewed like code — it is in CODEOWNERS). `.claude/settings.json` (shared allowlist) is committed; `.claude/settings.local.json` is git-ignored (**check `.gitignore` — it is not listed today**). "Git is the user's to run" is unchanged, and now means: the AI never pushes, never opens or merges a PR — the developer does, and is the author of record. A PR whose diff was substantially AI-generated says so in the template's `AI-assisted:` line, so the reviewer reads with that in mind (the 2026-08-05 review's finding — all ~35 defects found internally, ~60 % by review — is the reason review depth matters more with an AI producing volume). Design-note agreement moves from chat to the note PR (MD-6), so the AI's "agreed before implementation" check becomes "the note is merged at AGREED". | Two developers with two Claudes and one rules file is fine; two rules files is the drift the 2026-08-05 review already paid for once. |

### The human documents

| ID | Decision | Rationale |
|---|---|---|
| **MD-10** | **Build the on-ramp:** (1) `CONTRIBUTING.md` at the root — the human translation of `CLAUDE.md`: setup (`.venv`, `pip install -e '.[dev]'`, the solver extra), the branch/PR flow (MD-1/2), the tier table and "closure travels in the PR" (MD-3/4), how to write a fragment, how to add a module (pointer to `00_program_overview.md` module contract), how to run the gates locally (`ruff`, `mypy`, `pytest`, `pytest -m roundtrip`), the three concurrency rules (MD-7), and who owns what (MD-8). Rules-and-pointers like `CLAUDE.md`, budget ~150 lines, and **CLAUDE.md links to it rather than repeating it**. (2) `.github/PULL_REQUEST_TEMPLATE.md` — closes-issue line, tier, the closure checklist for that tier, digest-wave yes/no, schema-bump yes/no, `AI-assisted:` line, reviewer's approval-gate checklist from `CODE_REVIEW_PROCESS.md`. (3) `.github/ISSUE_TEMPLATE/` — `defect.md` (found by / expected / observed / oracle or closure gate affected / tier), `backlog-item.md` (mission tag / band / depends / tier), `design-note.md` (theory reference / CONVENTIONS citations / target numbers / tolerances — rule 1's four lines). (4) `CODEOWNERS` (MD-8). (5) `docs/10_standard/DEVELOPMENT_PROCESS.md` — one page: the flow diagram issue → branch → design-note PR (L) → implementation PR → review at tier → squash → release cut; the same content as CONTRIBUTING §flow but as the *standard*, so CONTRIBUTING can stay short. `00_INDEX.md` rows for all of it; `test_doc_currency.py` covers the new standard doc automatically. | Today the only description of how work is done is written for the AI. |
| **MD-11** | **Release manager role.** Named per release in the milestone; cuts per `RELEASE_PROCESS.md` §4 (now including the history-fragment roll, MD-4) on a `release/x.y.z` branch that is itself a PR; rotates. | A release is the one activity that touches everything; naming who does it is what makes "release small and often" survive one person's vacation. |
| **MD-12** | **What does *not* change:** the closure tiers, the benchmark-first rule, the make-it-structural rule, the review process's steps and severities, the release gate, the doc-currency rule, the AI's git rule. This note re-homes the *where* (session → PR, chat → note PR, file → issue), not the *what*. | The process works; the review of 2026-08-15 verified it. Multi-developer is a change of substrate, not of standard. |

## 3. Build list — shipped 2026-08-16 (one session, single-developer; from here on, each such item is its own PR)

1. `.gitignore` gains `.claude/settings.local.json`; `CODEOWNERS` with one owner; branch protection switched on with the current check names (MD-2 — settings, not code; **you**). *(S)*
2. `changes/` gains the `history` fragment type; `build_changelog.py` writes them into the history file at cut; `changes/README.md`, `test_changelog_fragments.py`, `RELEASE_PROCESS.md` §4, `CLAUDE.md` tier table (M/L: "history fragment") updated. *(M — this is the tooling change)*
3. `CONTRIBUTING.md`, `PULL_REQUEST_TEMPLATE.md`, `ISSUE_TEMPLATE/`, `DEVELOPMENT_PROCESS.md`; `CLAUDE.md` links; INDEX rows. *(S)*
4. Backlog migration per MD-5 (script + the table rewrite + the both-ways guard), `02_parked.md` retired. *(M)*
5. `CODE_REVIEW_PROCESS.md` §0 gains "the PR is the review unit; reviewer ≠ author; owner review per CODEOWNERS"; `RELEASE_PROCESS.md` gains the release-manager line and the `release/x.y.z` branch. *(S)*
6. Design notes 01–27 gain `Owner:` lines (mechanical). *(S)*

## 4. The questions that were open (answered above, kept for the record)

- **MD-2:** 1 or 2 reviewers; owner self-merge for `self-merge-ok` tier-S PRs — yes/no.
- **MD-5:** GitHub Issues + Project (recommended) or in-repo per-item files.
- **MD-8:** who else, if anyone, is an owner today; otherwise every line is you until it isn't.
- Do you want the history-fragment change (MD-4) now, before the second developer arrives, or with the rest of the build list? It is the one item that changes tooling; the others are documents and settings.
