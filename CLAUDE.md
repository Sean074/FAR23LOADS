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
  Set the `ConditionResult.safety_factor` for every case (see **Ultimate-load
  output** below).
- **Self-register** at import (`register("name", run)`), and add the import to
  `farloads/modules/__init__.py`.
- **Constants centralized** in `constants.py`.
- **One manual-example test** per module under `tests/`, asserting `run(project)`
  against the Appendix A and/or B figures.

### Ultimate-load output (mandatory)

**All deliverable load output SHALL be ULTIMATE.** Every *deliverable* — the
load-case CSV, the sbeam `FORCE`/`MOMENT` cards and span CSV, the shared
`report.py` tables/text, and the Review/Export consolidation pages — reports
ULTIMATE loads; none may emit a bare limit load. The internal calc stays **LIMIT**
so the Appendix A/B oracles are unaffected (math fidelity above); the
limit→ultimate factor is applied once, at the render/export boundary (`report.py`,
`export/sbeam_bridge.py`), to load quantities only (forces/moments/pressures —
never geometry, weights, inertias, areas, speeds, angles, or the dimensionless
load factors).

**Scope — per-module analysis pages may show LIMIT.** A per-module *analysis*
Streamlit page (e.g. `flap_loads`, `tab_loads`, `one_engine_out`, the
`balanced_tail_verification` check tool) may display the calc's **LIMIT** values —
they are the oracle-traceable numbers an engineer cross-checks against the manual —
**provided they are explicitly marked LIMIT** (a caption plus a `LIMIT` marker on
each load column/metric) and the page points to the ultimate deliverables. This is
the *only* exception; everything that is exported or consolidated is ultimate.

The rules that make this unambiguous:

- **The `ULT` marker is part of the load's units string.** A reported load
  carries it inline: force `lbs-ULT` (SI `N-ULT`), moment/torque `ft-lb-ULT` /
  `lb-in-ULT` (SI `Nm-ULT`), design pressure `lb/in^2-ULT` (`psi-ULT`). Treat
  "limit vs. ultimate" as a property of the unit, exactly like lb vs. N.
  Non-load quantities keep plain units with no `-ULT` suffix.
- **Every load case SHALL state its safety factor.** Carry it on
  `ConditionResult.safety_factor` and surface it in output (the `SF` column / an
  `SF=` marker). The default is **1.5 per 14 CFR 23.303** (the Part 25 equivalent
  is 25.303; see `reference/14CFR_factor_of_safety.md`). The per-case field is the
  hook for a future 14 CFR 23.302/25.302 / Appendix K probability-based factor
  (1.0–1.5) on failure conditions.
- **A load already at ultimate is `ULT SF=1.0`.** When a case's printed/derived
  value is itself the ultimate (or an inherently-limit quantity is reported
  as-ultimate with no amplification), set `safety_factor = 1.0` — it is still
  ULTIMATE output, marked `ULT SF=1.0`, not a limit load.

### Math fidelity (important, non-obvious)

Decision 3 of the project is **"modernize the math"**: use `math.pi` and clean
equations, *not* the original program's `3.1416` literal. Consequently the
manual's printed figures are **tolerance-based regression oracles (±0.1%)**, not
exact oracles. Tests use `math.isclose(..., rel_tol=1e-3)` against the manual's
printed numbers (keep the printed number + a page citation in the test so drift is
traceable). Use exact equality only for integer/dimensionless quantities. Keep
constants in `constants.py` so reverting this decision stays a one-file change.

### Approved corrections to the source (oracle deviations)

The FAR23 replication core is oracle-locked to McMaster's manual, **but the manual
and its `.BAS` source may themselves contain errors** (e.g. encoding a regulation
that was later found defective). A deliberate deviation from the oracle is allowed
**only when it is (1) approved by the user and (2) documented** — in the calc
docstring + a `note` on the affected `ConditionResult`, in the test (assert the
corrected value, keep the manual's original figure in a comment for traceability),
in `PROGRAM_SPEC.md` / `docs/20_theory/00_theory_sources.md`, in `CHANGELOG.md`, and
cited to an authoritative reference in `reference/`. Until both conditions are met,
replicate the manual exactly (warts and all). Record each correction here:

- **23.361(a)(1) takeoff-torque factor** *(approved 2026-06-22)* — the manual leaves
  the takeoff-case engine torque **unfactored** (Appendix A prints 554.39 ft-lb for
  the IO-520-BB), encoding the **Amendment 23-26** drafting error. **AC 23-19A**
  states that error was non-conservative (lower loads) and corrected by **Amendment
  23-45**: 23.361(c) applies the mean-torque factor to *all* of paragraph (a),
  takeoff case included. `condition_361_a1` now applies `factor x mean takeoff torque`
  (IO-520-BB → 737.34 ft-lb; turbopropeller → 1.25× mean, identical to
  25.361(a)(1)(i)). Source: `reference/AC_23-19A_engine_torque.md`.
- **23.361(a)(3) turboprop-malfunction mean-torque factor** *(approved 2026-06-23)* —
  the manual / `ENGLOADS.BAS` (`TTP=1.6*ENGTORQ`) apply only the 1.6 propeller-
  control-malfunction factor, encoding the same **Amdt 23-26** omission. The (a)(3)
  base "limit engine torque corresponding to takeoff power and propeller speed" is the
  same quantity as (a)(1), so by the same **AC 23-19A** / 23.361(c) / **Amdt 23-45**
  authority the 1.25 turbopropeller mean-torque factor applies before the 1.6 factor.
  `condition_361_a3` now reports `1.6 x 1.25 x mean takeoff torque` (= 2.0× mean). No
  printed Appendix B engine-mount oracle exists in the bundled PDF, so it is
  formula-checked (`test_361_a3_applies_mean_torque_factor`). Source:
  `reference/AC_23-19A_engine_torque.md`.

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
