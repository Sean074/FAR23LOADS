# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A modern Python + Streamlit **replication** of the **FAR 23 LOADS** suite (Hal C.
McMaster, Aero Science Software): 22 GW/QBasic programs that compute the
structural design loads a small aircraft must sustain under FAR Part 23 Subpart C.
The job is to port the original programs into one shared calc package + a
multi-page UI, module by module.

**Active direction (Phase C).** The suite is being grown into an **initial-concept
distributed-loads tool**: it generalizes the FAR23 caps (a `concept` category that
can exceed the 12,500 lb / GA-seat limits), assesses a configuration against
similar airplanes, emits per-component distributed loads (wing / body / tail +
*standard simplified* control-surface distributions), and exports them as
`FORCE`/`MOMENT` bulk-data cards for **sbeam** structural sizing. The FAR23
replication core stays oracle-locked (Appendix A/B ±0.1%); concept mode is a
superset that reduces exactly to it on GA inputs. The plan, locked decisions and
per-step detail are in
[`docs/30_future/01_concept_loads_plan.md`](docs/30_future/01_concept_loads_plan.md).

The two authoritative sources live in `reference/` as PDFs and matter when
porting:
- **Reference 1** — `reference/FAR23 loads (1).pdf` (371 pp), McMaster's theory
  manual. The source of truth for equations *and* the regression oracle:
  Appendix A (6-place GA single) p131, Appendix B (10-place twin turboprop) p251,
  Appendix C `.BAS` source p373.
- **FAA User's Guide** — `reference/ADA324952.pdf` (DOT/FAA/AR-96/46), the module
  data-flow reference (Table 2.2).

`docs/10_standard/00_program_overview.md` is the authoritative **code standard**
(coding conventions, the error-handling contract, units, entry points, testing/
coverage) — start there.
`docs/10_standard/PROGRAM_SPEC.md` (per-module spec) and
`docs/10_standard/PROJECT_GUIDE.md` (the phased build plan, package layout,
conventions, validation strategy) are the working design docs — read them before
adding a module. `docs/00_INDEX.md` maps the whole `docs/` tree.

## Required practices

These are mandatory, not advisory:

- **Consult the reference material.** The PDFs in `reference/` (Reference 1 and
  the FAA User's Guide) SHOULD be consulted when generating or modifying analysis
  code — they are the source of truth for equations, conventions, and the
  regression oracles. Do not derive load equations from memory or from the ported
  code alone; trace them back to the reference and cite the page in the test.
- **Keep the docs in sync.** Every code change SHALL update the documentation in
  `docs/` as appropriate (`docs/00_INDEX.md` maps the tree). A change that adds a
  module, alters a calc, changes the package layout, or revises a convention is
  not complete until the corresponding doc reflects it:
  - `docs/10_standard/PROGRAM_SPEC.md` — the module's inputs/outputs/FAR conditions.
  - `docs/10_standard/PROJECT_GUIDE.md` — package layout, `Project` schema, or a porting convention.
  - `docs/20_theory/00_theory_sources.md` — the per-module equation/oracle citation.
  Missing doc updates are a **`[CRITICAL]`** review finding — see
  `docs/10_standard/CODE_REVIEW_PROCESS.md`.
- **Move closed work out of the backlog (same session).** When a module/step or a
  defect is finished, in the same session: (1) **remove** it from
  `docs/30_future/00_backlog.md`, (2) **add** it to
  `docs/40_history/00_completed_development.md` in full step format, and (3) add a
  `CHANGELOG.md` `[Unreleased]` entry. Never leave a "done" item in the backlog or
  batch these updates for later. Releases follow
  `docs/10_standard/RELEASE_PROCESS.md`.
- **Keep the build green.** `ruff check farloads/ cli.py` clean and `pytest`
  passing are the merge gate (CI enforces both on 3.9 / 3.11 / 3.12). Add new
  domain terms (program names, variables, units) to `cspell.json`.
- **Git is the user's to run.** ANY and ALL git usage — `commit`, `add`, `push`,
  `branch`, `merge`, `checkout`, `tag`, `rebase`, `reset`, etc. — SHALL be
  performed by the user, NOT by Claude, UNLESS the user explicitly requests that
  specific git action. Do not stage, commit, or otherwise alter git state on your
  own initiative; make the file changes and let the user handle git, or tell the
  user the exact command to run.

## Commands

The project uses a local virtualenv at `.venv/`. The package is installed in
editable mode (`pip install -e '.[dev]'`), so `import farloads` and `import cli`
work from any cwd — there are no `sys.path` shims in `app/` or `cli.py`. Use the
venv directly:

```bash
.venv/bin/pip install -e '.[dev]'            # runtime deps + pytest, pytest-cov, ruff

# Tests (the green-build gate)
.venv/bin/python -m pytest                   # whole suite (testpaths=tests, with coverage)
.venv/bin/python -m pytest tests/test_engine.py            # one file
.venv/bin/python -m pytest tests/test_engine.py::test_361_a2   # one test
.venv/bin/python tests/test_engine.py        # zero-dependency fallback runner

# Lint (CI gate, alongside pytest)
.venv/bin/ruff check farloads/ cli.py

# Run the UI
.venv/bin/streamlit run app/Home.py

# Run one module from the CLI (installed entry point or the script directly)
.venv/bin/farloads engine examples/ga6_normal.project.json -o out.csv
.venv/bin/python cli.py engine examples/ga6_normal.project.json   # text to stdout
.venv/bin/python cli.py --list               # registered modules
```

Tooling lives in `pyproject.toml` (build metadata, deps, `ruff`, `pytest`/
coverage config) and `cspell.json` (domain wordlist). `ruff` config selects
`E`/`F`/`W` and ignores `E741` (single-letter structural-engineering variable
names ported from the BASIC source). CI (`.github/workflows/ci.yml`) runs `ruff`
and `pytest` on Python 3.9 / 3.11 / 3.12. When you add a new domain term (a
`.BAS` program name, a variable, a unit), add it to `cspell.json`.

## Architecture

The system is a **shared pure-calc package + thin I/O shells**. Calc never does
I/O; the GUI, CLI and tests are interchangeable front-ends over the same package.

- `farloads/` — the pure-calc package. No Streamlit, no file access in calc code.
  - `models.py` — `Project` (the single reloadable input bundle; holds every
    module's per-domain input/result slice — `engines`, `weight`, `geometry`,
    `speeds`, `aero`, `flight_loads`, `wing_mass`, `fuselage_mass`, `configuration`,
    and the result slices `mass`/`envelope`/`loads`), the per-module input/result
    dataclasses, `ConditionResult`/`LoadValue` (one FAR condition's labelled
    outputs), `ModuleResult` (a module's name + its conditions), `SCHEMA_VERSION`.
  - `modules/<name>.py` — one file per suite program. Each exposes
    `run(project: Project) -> ModuleResult` and calls `register(name, run)` at
    import time. `modules/__init__.py` imports every module so registration
    happens on `import farloads`.
  - `registry.py` — name → `run(project)` lookup. `run_all_modules(project)` runs
    every registered module whose input slice is present (a module raises
    `ValueError` when its slice is missing, and that is skipped).
  - `workflow.py` — the ordered Define→Analyze→Review→Export step graph (pure
    metadata + predicates over a `Project`; no Streamlit). Each `WorkflowStep` names
    its `module` and the slices it `requires`/`produces`; drives the GUI navigation
    and the dashboard completeness panel, and is the seed of a dependency DAG. A test
    asserts every registered module has a step (guarding against nav drift).
  - `io.py` — the **only** place that maps dataclasses ↔ JSON. Loads/saves
    `project.json` (also accepts a legacy flat engine-only file) and writes the
    load-case CSV.
  - `units.py` — Imperial↔SI conversion at the boundary only. Calc always runs in
    the Imperial units of the original program; SI is purely presentation.
  - `report.py` — shared rendering: `load_cases_to_rows` (one row per structural
    load case — the canonical CSV shape every module reuses) and `text_report`.
  - `constants.py` — the one home for `g`, `pi`, unit factors.
- `app/Home.py` + `app/views/*.py` — Streamlit multi-page UI. `Home.py` is the
  `st.navigation` entry point: it builds a four-phase sidebar (Define → Analyze →
  Review → Export) from `farloads/workflow.py` (the ordered step graph), so page
  order/titles come from workflow metadata, not filename prefixes. Each view is
  `app/views/<workflow-key>.py`; `dashboard.py`, `results_review.py` and
  `export_report.py` are the Overview / Review / Export consolidation pages. Only
  `Home.py` may call `st.set_page_config` (once, before `st.navigation`). The
  editable install (`pip install -e '.[dev]'`) puts `farloads` on the path, so the
  views import it directly — there are no `sys.path` shims.
- `cli.py` — argparse front-end: load project → `registry.get(module)` → CSV/text.
- `tests/` — pytest; `conftest.py` puts the repo root and `tests/` on `sys.path`
  (so `from test_engine import io520bb` works). Each test file also has a
  `__main__` self-runner that works without pytest installed.

### Data flow for one run
`project.json` → `io.load_project` → `Project` → `registry.get(name)(project)` →
`ModuleResult` → `report`/`io` renders text or the load-case CSV. The GUI builds
the `Project` from widgets instead of a file; everything downstream is identical.

## Conventions when adding a module (all 22 suite programs ported; conventions apply to new concept-mode modules)

These are the contract that makes modules copy-of-the-pattern (see PROJECT_GUIDE §5):

- **Pure calc, no I/O.** Module exposes `run(project) -> ModuleResult`; reads the
  upstream fields it needs from `Project`, returns results. It must not recompute
  a quantity another module owns — read it from the project slice.
- **Reuse the result types.** Emit `LoadValue`/`ConditionResult` so `report.py`,
  `units.py` and the CSV writer work unchanged. The CSV is always "one row per
  load case" via `load_cases_to_rows` — generalize it, don't reinvent per module.
- **Self-register** at import (`register("name", run)`), and add the import to
  `farloads/modules/__init__.py`.
- **Constants centralized** in `constants.py`.
- **One manual-example test** per module under `tests/`, asserting `run(project)`
  against the Appendix A and/or B figures.

### Math fidelity (important, non-obvious)

Decision 3 of the project is **"modernize the math"**: use `math.pi` and clean
equations, *not* the original program's `3.1416` literal. Consequently the
manual's printed figures are **tolerance-based regression oracles (±0.1%)**, not
exact oracles. Tests use `math.isclose(..., rel_tol=1e-3)` against the manual's
printed numbers (keep the printed number + a page citation in the test so drift is
traceable). Use exact equality only for integer/dimensionless quantities. Keep
constants in `constants.py` so reverting this decision stays a one-file change.

### Preserved engineering conventions

From the original ENGLOADS: engine-mount reaction torque is reported **negative**;
"clockwise from the pilot's view is positive" for rotor RPM and stoppage torque.
Some intermediate quantities are truncated to 3 decimals (`int(x*1000)/1000`) to
mirror the BASIC — preserve this when it affects a compared figure.

### Naming map (the suite uses two module counts, both correct)

Reference 1's Appendix C ships **22** programs; the FAA User's Guide repackages
them into a **20**-item menu. `TAU.BAS` (helper) and `BALLOADS.BAS` (a
post-`FLTLOADS` balanced-tail-load *verification* utility, off the main pipeline)
are the two off-menu programs. Module file names in `farloads/modules/` are the
modern names mapped to original `.BAS` names in
`docs/10_standard/PROGRAM_SPEC.md` and the `PROJECT_GUIDE.md §4` layout.
