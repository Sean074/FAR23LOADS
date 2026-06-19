# Release Process — FAR 23 LOADS

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
schema has its own `schema_version` (in `farloads/models.py`) — bump it when the
input schema changes, and ensure `io.py` still loads older saves.

Pre-release tags: `0.2.0-beta.1` for candidates shared externally.

---

## 2. What constitutes a release

Cut a release when one or more is true:

- A roadmap phase is complete (e.g. all Phase 1 mass-properties modules ported).
- A critical numerical-fidelity bug is fixed and verified.
- A new module is production-ready and passes its Appendix A/B acceptance test.
- A breaking change to the `project.json` schema or CSV output has been made.

Do **not** cut a release for documentation-only changes or in-progress modules.

---

## 3. Pre-release checklist

Each item is a hard gate.

### 3.1 Backlog & documentation
- [ ] [`../30_future/00_backlog.md`](../30_future/00_backlog.md) — every module in this release is removed (closed items don't live in the backlog).
- [ ] [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md) — every module/step in this release is recorded in full step format.
- [ ] All `docs/` files are consistent with the released code (no drift): `PROGRAM_SPEC.md`, `PROJECT_GUIDE.md`, `20_theory/00_theory_sources.md`.
- [ ] `CHANGELOG.md` `[Unreleased]` section is complete; ready to be dated.

### 3.2 Code quality
- [ ] No open `[CRITICAL]`/`[MAJOR]` findings from the latest review (see [`CODE_REVIEW_PROCESS.md`](CODE_REVIEW_PROCESS.md)).
- [ ] `ruff check farloads/ cli.py` is clean.
- [ ] Public functions in `farloads/` have type hints and docstrings.

### 3.3 Test suite
- [ ] `pytest` passes — zero failures, zero errors.
- [ ] No `skip`/`xfail` without a reason logged in the backlog.

### 3.4 Numerical acceptance (the oracle)
- [ ] Every ported module's `tests/test_<module>.py` passes against its Appendix A and/or B figures within **±0.1%** (`rel_tol=1e-3`); integer/dimensionless quantities exact.
- [ ] For releases that touch a shared upstream module (weights, geometry, aero), re-run the **full** suite — downstream modules read those slices.

### 3.5 GUI / CLI smoke test
- [ ] `streamlit run app/Home.py` starts headless without error; a representative project loads, runs, and renders.
- [ ] `farloads <module> examples/<project>.json -o out.csv` writes the expected load-case CSV.

---

## 4. Cutting the release

1. **Bump the version** in `pyproject.toml`. Commit: `Bump version to X.Y.Z`.
2. **Date the changelog** — rename `[Unreleased]` to `## [X.Y.Z] — YYYY-MM-DD` (Added / Fixed / Changed / Breaking), and start a fresh empty `[Unreleased]`.
3. **Tag:** `git tag -a vX.Y.Z -m "Release vX.Y.Z"` then `git push origin vX.Y.Z`. Create a GitHub Release from the tag with the changelog entry as the body.
4. **Archive verification** — record the numerical output (module figure vs. Appendix figure) for the modules in this release under `docs/40_history/` as a permanent regression baseline.

---

## 5. Post-release
- [ ] `docs/30_future/00_backlog.md` — remove anything resolved by this release; add any new defects found in final testing.
- [ ] Confirm the release tag/date are noted in `docs/40_history/00_completed_development.md`.
- [ ] Identify the next phase/module from the backlog.

---

## 6. Hotfix process

A hotfix is a `PATCH` release correcting a critical defect in a released version.

1. Branch from the release tag: `git checkout -b hotfix/vX.Y.Z+1 vX.Y.Z`.
2. Apply the minimal fix — **no new modules, no refactoring**.
3. Run the pre-release checklist (§3), focused on the affected module + any downstream readers.
4. Bump to `X.Y.Z+1`, date the changelog, tag, release.
5. Merge back to `main`; record the resolved defect under "Resolved defects" in the history.
