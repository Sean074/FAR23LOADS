# Contributing to sloads

The short human on-ramp. Rules and pointers only — the standard lives in
`docs/10_standard/` (start at [`00_program_overview.md`](docs/10_standard/00_program_overview.md));
the process lives in [`DEVELOPMENT_PROCESS.md`](docs/10_standard/DEVELOPMENT_PROCESS.md);
the AI's operating contract is [`CLAUDE.md`](CLAUDE.md) and says the same things
in the same words. When they disagree, the standard doc wins and the other is fixed.

## 1. What you are working on

A Python replication of the FAR 23 LOADS suite (McMaster) whose FAR23 core is
**oracle-locked** to the manual's printed worked examples (±0.1 %), extended
into a concept-loads → beam-solver loop whose deliverable is a balanced
free-free airplane model exported as bulk-data cards. Read the mission in
[`docs/30_future/00_backlog.md`](docs/30_future/00_backlog.md) §Mission first;
never derive a load equation from memory — cite the reference page in the test.

## 2. Setup

```bash
git clone https://github.com/Sean074/sloads.git && cd sloads
python3.11 -m venv .venv && .venv/bin/pip install -e '.[dev]'     # 3.9–3.12 supported
.venv/bin/pip install -e '.[solver]'    # optional: the pinned sbeam solver for the round-trip gate
.venv/bin/pre-commit install --hook-type pre-commit --hook-type pre-push   # optional: ruff+mypy on commit, suite on push
```

The hooks run the venv's own `ruff`/`mypy` (pinned in `pyproject.toml`, the same
versions CI runs) so a green commit here is a green lint step there; skip once
with `git push --no-verify`. CI is the gate either way.

The gates, all local:

```bash
.venv/bin/ruff check sloads/ cli.py app/ scripts/   # lint
.venv/bin/mypy                                       # types (sloads/ only)
.venv/bin/python -m pytest                           # suite (parallel; add -n 0 to debug)
.venv/bin/python -m pytest -m roundtrip              # solver round trip (skips without the solver extra)
```

## 3. How work moves (the one-page version of `DEVELOPMENT_PROCESS.md`)

*Working alone?* `DEVELOPMENT_PROCESS.md` §0 is the solo profile: steps 1, 6–8
below become "one commit per closed item on `main`, backlog row out in that
commit"; steps 2–5 (design note, tier closure, counters) apply unchanged.

1. **Pick or open an issue.** Open work is GitHub Issues (labels
   `tier:*`, `tag:*`, `band:*`, `kind:*`); the priority order is the table in
   `00_backlog.md`. Assign yourself.
2. **Tier L or any physics change: design note first.** Open `note/NN-slug`
   with a `PROPOSED` note in `docs/30_future/` (theory reference,
   `CONVENTIONS.md` citations, expected numbers, tolerances); the owner reviews;
   merge at `AGREED`. Then implement.
3. **Branch** `<type>/<slug>` off `main` (`step/`, `fix/`, `note/`, `docs/`, `chore/`).
4. **Do the work at its tier**, and put the closure **in the same PR**:

   | Tier | Closure in the PR |
   |---|---|
   | S — small fix, hygiene, docs, display-only | `changes/<slug>.<type>.md` + `Closes #N` |
   | M — behaviour change to an existing capability | S + affected `PROGRAM_SPEC.md`/standard-doc sections + `changes/<slug>.history.md` (one paragraph) |
   | L — new module / load case / physics / schema or contract change | M + `theory_sources.md` citation + note flipped to *shipped* + full-step `history.md` |

   Fragments: [`changes/README.md`](changes/README.md). Never hand-edit
   `CHANGELOG.md` `[Unreleased]` or the top of the history file.
5. **Rebase on `main` before you regenerate anything** — `SCHEMA_VERSION`, the
   Imperial digest (one wave per PR, reviewer confirms), case-ID bands. Guards
   fail on collisions; the rule is *when* you run them.
6. **Open the PR** with the template filled in (tier, `Closes #N`, digest/schema
   yes-no, `AI-assisted:`). CI must be green: `test ×3`, `typecheck`,
   `sbeam-roundtrip ×2`.
7. **Review**: one approval from someone other than you; the CODEOWNERS owner
   for SSOT paths; depth per
   [`CODE_REVIEW_PROCESS.md`](docs/10_standard/CODE_REVIEW_PROCESS.md) §0.
   `self-merge-ok` (tier S, docs/hygiene, nothing under `sloads/`) may merge on
   green CI.
8. **Squash-merge**, PR title = commit subject in the project style
   (`Step 14: … (tier M, 2026-08-20)`). Delete the branch.

## 4. Writing calc code — the contract in one breath

Pure calc, no I/O; `run(project) -> ModuleResult`, self-registered; read
upstream values from the `Project` slice, never recompute another module's
quantity; constants in `constants.py`; Imperial internal, convert at the
boundary; every case states its safety factor; one oracle test (±0.1 %,
page-cited) or a stated closure gate in CI; missing slice →
`MissingInputError`, present-but-invalid → `ValueError`, never `nan`. Full text:
`00_program_overview.md` §Coding standards / §Error handling / §Units;
conventions (axes, signs, units channels, ULT/SF): `CONVENTIONS.md`.

Type-check and lint rules of engagement (narrow, never silence; every `noqa`
carries a reason): `00_program_overview.md` §Static typing & lint.

## 5. Docs rules you will hit

- Standard docs **point at owners, never copy values** (no schema numbers, test
  counts, "currently N") — `tests/test_doc_currency.py` fails on them.
- Every file under `docs/` has a row in `docs/00_INDEX.md` (same guard).
- `PROJECT_GUIDE.md` §4's tree, `PROGRAM_SPEC.md`'s sections, `workflow.py`'s
  nav, and `DATA_DICTIONARY.md` are generated or test-guarded — edit the owner.
- New domain terms go in `cspell.json`.

## 6. Working with Claude Code here

`CLAUDE.md` is loaded into every developer's session and is the same file for
everyone — treat it as code (it is in CODEOWNERS). Your local permission
allowlist is `.claude/settings.local.json` (git-ignored). The AI never runs
git for you: it makes the file changes and tells you the command; you push,
open, and merge, and you are the author of record. Say `AI-assisted: yes` in
the PR when the diff is substantially generated.

## 7. Who to ask

`.github/CODEOWNERS` lists the owner of each single-source file; the release
manager for the current milestone is named on the milestone.
