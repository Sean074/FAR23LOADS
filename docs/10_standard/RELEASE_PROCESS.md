# Release Process — sloads

Authoritative guide for versioning, validating, and releasing the suite.

---

## 1. Version numbering

Semantic versioning: `MAJOR.MINOR.PATCH`.

| Component | When to increment |
|---|---|
| `MAJOR` | Breaking change to the `project.json` schema or the load-case CSV shape |
| `MINOR` | A new module ported (a new suite program runs), or a new GUI/CLI capability |
| `PATCH` | Bug fix that does not change the public interface |

The version lives in `pyproject.toml` under `version =`. The `project.json`
schema has its own `SCHEMA_VERSION` (in `sloads/models/project.py`) — bump it
when the input schema changes, and ensure `io.py` still loads older saves.

Pre-release tags: `0.2.0-beta.1` for candidates shared externally.

---

## 2. What constitutes a release

**Cadence rule (2026-08-05, process review R3): release small and often.** Cut a release
whenever the §3 gate passes and any of the following is true:

- **~2–3 weeks have passed since the last tag, or ~5 steps have closed** — whichever
  comes first. Accumulated small improvements are a valid release; do not wait for a
  phase milestone. Never let `[Unreleased]` grow past roughly a release-worth of work —
  unreleased work has no regression baseline.
- A critical numerical-fidelity bug is fixed and verified.
- A new module is production-ready and passes its Appendix A/B acceptance test.
- A breaking change to the `project.json` schema or CSV output has been made.

Do **not** cut a release for documentation-only changes or in-progress modules.

---

## 3. Pre-release checklist

Each item is a hard gate.

### 3.1 Backlog & documentation (bounded — no unbounded drift audit)

Documentation consistency is enforced **per-change** by the tiered closure requirement
in `CLAUDE.md`, not re-audited at release time.

- [ ] [`../30_future/00_backlog.md`](../30_future/00_backlog.md) — every item in this release is removed (**spot-check**, not an audit; closed items don't live in the backlog).
- [ ] [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md) — every tier-M/L step in this release is recorded at its closure-tier depth (tier S has no history entry — its `changes/` fragment is the record).
- [ ] `changes/` — every closed item has its fragment; `.venv/bin/python scripts/build_changelog.py --dry-run` runs clean and reads as the release note (`changes/README.md`).
- [ ] **The band being cut is retired from the priority table** and the band that
      follows becomes the milestone in flight (§Where things stand says so). A band
      left in the table naming a released version is caught by
      `tests/test_backlog_issues.py::test_no_open_row_sits_in_a_band_whose_release_is_already_cut`
      — it was missed at the 0.7.2 cut, which is why the assertion exists.
- [ ] `.venv/bin/python scripts/branch_protection_snapshot.py --check` — the live
      protection on `main` still matches `.github/branch-protection.json`, which the
      process docs are asserted against. **This is the one comparison CI cannot make**
      (the test job has no `gh` auth), and the cut is when it matters: the 0.7.2
      milestone PR was refused at exactly this point by a linear-history rule three
      documents denied (issue #46, CR-D-4).

### 3.2 Code quality
- [ ] No open `[CRITICAL]`/`[MAJOR]` findings from the latest review (see [`CODE_REVIEW_PROCESS.md`](CODE_REVIEW_PROCESS.md)).
- [ ] `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/ scripts/` and `mypy` are clean.

### 3.3 Test suite
- [ ] `pytest` passes — zero failures, zero errors.
- [ ] No `skip`/`xfail` without a reason logged in the backlog.

### 3.4 Numerical acceptance (the oracle)
- [ ] Every ported module's `tests/test_<module>.py` passes against its Appendix A and/or B figures within **±0.1%** (`rel_tol=1e-3`); integer/dimensionless quantities exact.
- [ ] For releases that touch a shared upstream module (weights, geometry, aero), re-run the **full** suite — downstream modules read those slices.

### 3.5 GUI / CLI smoke test
- [ ] `scripts/smoke_test.sh` exits 0 — it starts `app/Home.py` headless, checks the root page renders (HTTP 200, no traceback in the server log), then runs `sloads engine examples/ga6_normal.project.json -o out.csv` and checks the CSV.

---

## 4. Cutting the release

**Who and where (design note 28 MD-11):** the **release manager** named on the
milestone cuts the release on a `release/x.y.z` branch — steps 1–3 below are one PR,
reviewed like any other; the tag (step 4) is made on `main` after it merges. The
role rotates.

**Working alone (`DEVELOPMENT_PROCESS.md` §0, 2026-08-22): there is no
`release/x.y.z` branch.** The milestone branch `dev/vX.Y.Z` *is* the release
branch — it has carried every item of the release, so cutting on a second
branch would only move the same commits again. Steps 1–3 below are commits on
`dev/vX.Y.Z` (they are docs, `pyproject.toml` and generated history, so the
gate scales accordingly); then open **one** pull request into `main` and
**rebase-merge** it (`gh pr merge <N> --rebase`), so every per-item commit
survives on `main` and `git log` stays the step-per-commit record. **Never
squash:** that collapses the whole milestone into one commit, which is the
record this model exists to keep. Rebase — not a merge commit — because `main`
enforces **linear history**: a merge commit is refused outright ("This branch
must not contain merge commits", found at the 0.7.2 cut, 2026-08-25, where this
paragraph had said *merge commit* since 2026-08-22 and the setting had said
otherwise all along). Rebase satisfies both: linear history for the protection
rule, one commit per item for the record. It rewrites the branch's SHAs onto
`main`'s tip, so delete `dev/vX.Y.Z` after the merge rather than reusing it, and
it drops any merge commit the branch itself picked up. That push to `main` runs the full
3.9/3.11 + coverage matrix — the gate of record for the whole milestone. Step 4
tags `main` after the merge, unchanged. The issues of this milestone are
already closed, each in its own commit, so the PR body carries **no**
`Closes #N`.

1. **Bump the version** in `pyproject.toml`. Commit: `Bump version to X.Y.Z`.
2. **Build the changelog and roll the history fragments** — `.venv/bin/python scripts/build_changelog.py X.Y.Z --date YYYY-MM-DD` assembles the `changes/` fragments into `## [X.Y.Z] — YYYY-MM-DD` (Breaking / Added / Changed / Fixed / Removed), inserts every `changes/*.history.md` entry at the top of `docs/40_history/00_completed_development.md` (design note 28 MD-4), opens a fresh empty `[Unreleased]`, and deletes the consumed fragments. Then write the release-cut block in the history file by hand (the one entry that is not a fragment). Run `scripts/backlog_issues.py check` — every priority-table row names an open issue and vice versa (MD-5). Never hand-edit `[Unreleased]`; fix a fragment and re-run instead. Commit: `Changelog for X.Y.Z`.
3. **Roll the history (mechanical, bounded — design note 26, 2026-08-16):**
   - move every plan/design note in `docs/30_future/` whose status header reads *shipped* to `docs/40_history/` (next free number; update its `docs/00_INDEX.md` row);
   - if [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md) exceeds **1,500 lines** (`tests/test_changelog_fragments.py` warns), cut it at the *previous* release's "Release cut" block and move everything below that block verbatim into a new frozen `docs/40_history/NN_completed_development_to_<prev>.md` (header text: copy `11_completed_development_to_0.5.0.md`); the live file keeps this release's cycle plus its own release-cut block; add the INDEX row and the pointer line in the live file's header.
   Nothing here is an audit: statuses and line counts are the only inputs.
4. **Tag:** `git tag -a vX.Y.Z -m "Release vX.Y.Z"` then `git push origin vX.Y.Z`. Create a GitHub Release from the tag with the changelog entry as the body.
5. **Archive verification** — record the numerical output (module figure vs. Appendix figure) for the modules in this release under `docs/40_history/` as a permanent regression baseline.

---

## 5. Post-release
- [ ] `docs/30_future/00_backlog.md` — remove anything resolved by this release; add any new defects found in final testing.
- [ ] Confirm the release tag/date are noted in `docs/40_history/00_completed_development.md` (a "Release cut" block, tier M depth — it is also the next history-roll's cut line).
- [ ] Identify the next phase/module from the backlog.

---

## 6. Hotfix process

A hotfix is a `PATCH` release correcting a critical defect in a released version.

1. Branch from the release tag: `git checkout -b hotfix/vX.Y.Z+1 vX.Y.Z`.
2. Apply the minimal fix — **no new modules, no refactoring**.
3. Run the pre-release checklist (§3), focused on the affected module + any downstream readers.
4. Bump to `X.Y.Z+1`, date the changelog, tag, release.
5. Merge back to `main`; record the resolved defect under "Resolved defects" in the history.

**With a milestone branch open (`DEVELOPMENT_PROCESS.md` §0):** this is the only
path that puts a commit on `main` mid-milestone, so it is also the only time
`dev/vX.Y.Z` has to take `main` back — do it immediately after step 5
(`git checkout dev/vX.Y.Z && git rebase main`), before the next item, and
re-check the three shared counters of §6 (`SCHEMA_VERSION`, the Imperial
digest, case-ID bands) since that replay is exactly where they can collide.
**Rebase, not `git merge main`** (corrected 2026-08-25): a merge commit on the
milestone branch is what makes the milestone PR unmergeable at the cut under
`main`'s linear-history rule, and nothing surfaces it until then.
A defect found mid-milestone in *unreleased* work is **not** a hotfix — it is
the next item on the milestone branch.
