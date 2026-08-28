# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository. It holds **rules and
pointers only** — status, feature descriptions and per-module detail live in `docs/`
(budget: keep this file under ~160 lines; move prose out, not in).

## What this project is

A modern Python + Streamlit **replication** of the **FAR 23 LOADS** suite (Hal C.
McMaster, Aero Science Software): 22 GW/QBasic programs that compute the structural
design loads a small aircraft must sustain under FAR Part 23 Subpart C, ported into one
shared calc package + a multi-page UI.

**Mission (Phase C):** a demonstrated **concept-loads → sbeam sizing loop** — a
concept configuration (which may exceed the FAR23 caps) goes in, per-component
distributed ULTIMATE loads come out as `FORCE`/`MOMENT` bulk-data cards, and the
exported deck solves in sbeam with verified global equilibrium, continuously in CI.
The primary deliverable is the **full-span balanced free-free airplane model** (aero +
inertia together, left and right cases, CONM2 mass export) — per-component decks
remain analysis views. The FAR23 replication core stays **oracle-locked** (Appendix A
±0.1%; twin cases closure-locked); concept mode is a superset that reduces exactly to
it on GA inputs. Plan of record: `docs/30_future/01_concept_loads_plan.md`; working
backlog: `docs/30_future/00_backlog.md` (open items only; off-mission items in
`02_parked.md`).

**Reference sources (consult when writing/modifying analysis code — never derive load
equations from memory; cite the page in the test):**
- `reference/FAR23Loads_Code.pdf` — McMaster's theory manual; Appendix A (p131) is the
  printed oracle (±0.1%); Appendix B is not bundled (twin cases closure-locked, see
  `docs/20_theory/00_theory_sources.md`); Appendix C `.BAS` source (p373).
- `reference/FAR23Loads_UserGuide.pdf` — DOT/FAA/AR-96/46, module data-flow (Table 2.2).

## Authoritative single sources (never duplicate — link instead)

- **Conventions (axes, signs, units channels, ULT/SF contract, case identity):**
  `docs/10_standard/CONVENTIONS.md` — cite it in every physics/export design note.
- **Per-module spec (inputs/outputs/FAR conditions) + module naming map:**
  `docs/10_standard/PROGRAM_SPEC.md`
- **Package layout, `Project` schema, porting conventions:**
  `docs/10_standard/PROJECT_GUIDE.md`
- **Code standard (error contract, units, entry points, testing/coverage):**
  `docs/10_standard/00_program_overview.md`
- **How work moves (branches, PRs, closure-in-the-PR, issues, design-note PRs, owners):**
  `docs/10_standard/DEVELOPMENT_PROCESS.md`; human on-ramp `CONTRIBUTING.md`
- **Equation/oracle citations per module:** `docs/20_theory/00_theory_sources.md`
- **Approved oracle deviations (register of record):**
  `docs/20_theory/02_approved_corrections.md`
- **Project data model:** `docs/10_standard/DATA_DICTIONARY.md` (generated — edit the
  generator, never the file)
- `docs/00_INDEX.md` maps the whole tree.

## Step Completion Requirement (tiered)

**HARD REQUIREMENT — when any backlog item, defect, or step is closed, its closure tier
must be completed in the same session — and, with branches, in the same PR
(`DEVELOPMENT_PROCESS.md` §3). Open work is GitHub Issues; the backlog file is the plan.
Never batch or defer closure.**

| Tier | Applies to | Required closure |
|------|-----------|------------------|
| **S** | Small fix, hygiene, docs, display-only | one `changes/<slug>.<type>.md` fragment (see `changes/README.md`) + backlog removal. **No history entry.** |
| **M** | Behavior change to an existing capability | Tier S + the affected `PROGRAM_SPEC.md` / standard-doc section(s) + a **one-paragraph** `changes/<slug>.history.md` fragment |
| **L** | New module, new load case, new physics, schema/contract change | Tier M + `theory_sources.md` citation + the history fragment in **full step format**; design note merged at AGREED first |

`CHANGELOG.md` `[Unreleased]` and the top of the history file are never hand-edited:
`scripts/build_changelog.py` assembles both at release cut (`RELEASE_PROCESS.md` §4).

Additional rules (rationale in `docs/50_reviews/`):

1. **Design note before code (physics/L steps):** theory reference,
   `CONVENTIONS.md` citations, oracle or closure target with expected numbers, and
   acceptance tolerances — agreed before implementation: as a `note/NN-slug` PR merged
   at AGREED (`DEVELOPMENT_PROCESS.md` §5); in chat only when working alone.
2. **Benchmark-first definition of done:** an oracle test (±0.1%, page-cited) where a
   printed oracle exists; otherwise a **stated physics-closure/invariant gate in CI**,
   written with the feature — this applies to concept-mode physics with the same force
   as the oracle rule applies to the FAR23 core.
3. **Make it structural:** any cross-cutting convention (units, safety factors, case
   IDs, schema, axes) gets a single-source code owner **plus a drift-guard test** the
   first time it is needed — never a prose rule alone (SSOT table: `CONVENTIONS.md` §7;
   the units/SI history is the cautionary precedent).
4. **Generalize on first find:** a defect fix sweeps the same defect class across the
   codebase in the same change and adds a guard test where feasible.
5. **Review findings are filed with bodies** in the same session they are raised, and
   **no new parallel ID series** — descriptive names in the backlog, plain step
   identity at promotion.
6. **Effect vs error bar:** a physics/fidelity item is ranked only if its stated effect
   on a delivered load exceeds the base method's own uncertainty
   (`theory_sources.md` §Base-method uncertainty); below that it is parked **with the
   number that parks it**. A defect with first-order effect on shipped content outranks
   every fidelity item regardless of mission trace.

## Required practices

- **Standard docs point at owners, never copy their values.** No schema number, test
  count, coverage %, or "currently N" in `README.md`/`CLAUDE.md`/`10_standard/`/`20_theory/`
  (`00_program_overview.md` §Documentation currency; guard `tests/test_doc_currency.py`).
- **Keep the build green.** `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/ scripts/` clean, `mypy` clean (zero
  errors on `sloads/`; strictness ratchets per package in `pyproject.toml`) and `pytest` passing
  are the merge gate. **CI is asymmetric — `ci.yml` is the authority** (guard
  `tests/test_ci_conformance.py`): PRs and `dev/**` pushes run the fast gate (3.12,
  `typecheck`, `sbeam-roundtrip (3.12)`); 3.9/3.11 and coverage run on the push to `main`.
- **The git workflow is REQUIRED for all development work** — no change lands outside
  it. The operative mode is the **solo profile** (`DEVELOPMENT_PROCESS.md` §0) unless
  collaboration is explicitly in play: `scripts/solo_start.sh dev/vX.Y.Z` opens the
  milestone branch; every item closes with `scripts/solo_close.sh` (gate → commit →
  push → issue close → verify) — never by hand-run equivalents.
- **Git is the user's to run.** ANY and ALL git and `gh` usage — `commit`, `add`,
  `push`, `branch`, `merge`, `checkout`, `tag`, `rebase`, `reset`, etc., and the
  solo scripts (they run git/gh internally) — SHALL be performed by the user, NOT by
  Claude, UNLESS the user explicitly requests that specific action. Make the file
  changes and present the exact command **ONE AT A TIME**: give one command, stop the
  turn, and wait for the user's pasted output before offering the next — never a
  batched list. The AI never pushes, opens or merges a PR; the developer is the
  author of record.

## Commands

Local venv at `.venv/`; editable install (`pip install -e '.[dev]'`); no `sys.path` shims.

```bash
.venv/bin/python -m pytest                   # whole suite (testpaths=tests, parallel; coverage is CI-only)
.venv/bin/python -m pytest tests/test_engine.py::test_361_a2   # one test
.venv/bin/ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/ scripts/   # lint gate
.venv/bin/mypy                               # type gate (sloads/ only)
.venv/bin/streamlit run app/Home.py          # UI
.venv/bin/streamlit run oracle_app/Oracle.py # the oracle GUI (or: .venv/bin/sloads-oracle)
.venv/bin/sloads engine examples/ga6_normal.project.json -o out.csv   # CLI
.venv/bin/python cli.py --list               # registered modules
```

## Architecture (summary — authoritative layout in PROJECT_GUIDE §4/§7)

**Shared pure-calc package + thin I/O shells.** Calc never does I/O; GUI, CLI and tests
are interchangeable front-ends. Data flow: `project.json` → `io.load_project` →
`Project` → `registry.get(name)(project)` → `ModuleResult` → `report`/`io` render.

- `sloads/` — pure calc: `models/` (`Project` bundle, result types, `SCHEMA_VERSION`),
  `modules/<name>.py` (one per program; `run(project) -> ModuleResult`, self-registers),
  `registry.py`, `workflow.py` (step graph — **the** nav SSOT, drift-guarded), `io.py`
  (the only dataclass↔JSON mapping), `units.py` (Imperial-internal; convert at the
  boundary), `report/` (limit→ultimate boundary), `export/` (sbeam bridge +
  `coordinates.py`), `constants.py`.
- `app/Home.py` + `app/views/*.py` and `oracle_app/Oracle.py` — two Streamlit
  front-ends built from `workflow.py` over the shared `app_shell/`; **exactly one
  `st.set_page_config` per GUI entry point, none anywhere else** (guard:
  `tests/test_app_shell.py`). `cli.py` — argparse; `tests/` — pytest, each file
  with a zero-dependency `__main__` self-runner.

**Module contract** (every suite and concept module):
pure calc, no I/O; read upstream values from the `Project` slice — never recompute
another module's quantity; emit `LoadValue`/`ConditionResult` (set
`safety_factor` on every case); self-register; constants in `constants.py`; one
oracle/closure test per module.

## Load-output contract (summary — full rules in CONVENTIONS.md)

**All deliverable load output is ULTIMATE**; internal calc stays LIMIT (oracles
unaffected); the factor is applied once at the render/export boundary, to load
quantities only. The `-ULT` marker is part of the units string; every case states its
SF (`ULT SF=1.0` = already-ultimate). **The authority for every factor is the governing
safety-factor table, `sloads/safety_factors.py`** (M4-8 / G-11) — one row per condition
family, each with a basis; every per-case SF is a derived view of it, and a case it
cannot classify is flagged, never silently defaulted. Solver decks use the consistent-unit
channel (N·mm, MPa) via `units.deliverable_units(system, channel)` resolved once per
bundle; per-module analysis pages may show LIMIT only when explicitly marked.

**Math fidelity:** modernized math (`math.pi`, clean equations) — the manual's figures are
tolerance oracles (±0.1%, `math.isclose(rel_tol=1e-3)`), printed number + page citation kept
in the test. **Oracle deviations** need the owner's approval (in the PR) + the full trail —
register: `docs/20_theory/02_approved_corrections.md`.
