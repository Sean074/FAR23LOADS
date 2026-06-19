# FAR 23 LOADS — Program Code Standard & Developer Guide

The authoritative description of how the suite is built and the standard every
ported module must meet. Read this before adding or changing a module.

**See also:** [`PROGRAM_SPEC.md`](PROGRAM_SPEC.md) — the per-module specification
(inputs/outputs/FAR conditions for all 22 programs); [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md)
— architecture rationale and the dependency-ordered roadmap;
[`../20_theory/00_theory_sources.md`](../20_theory/00_theory_sources.md) — where
each module's equations and oracle figures come from.

---

## Purpose

A modern Python + Streamlit **replication** of the FAR 23 LOADS suite (Hal C.
McMaster, Aero Science Software): 22 GW/QBasic programs that compute the
structural design loads a small aircraft must sustain under FAR Part 23 Subpart C.
The programs are ported into one shared pure-calc package plus thin I/O shells,
module by module.

---

## Project structure

```
farloads/                 # shared, pure-calc package — no I/O in calc code
├── constants.py          # g, pi (math.pi), unit factors — the one home for constants
├── models.py             # Project, EngineInput/Rotor, ConditionResult/LoadValue, ModuleResult
├── units.py              # Imperial<->SI conversion at the I/O boundary only
├── io.py                 # the only dataclass<->JSON mapping; project.json + load-case CSV
├── registry.py           # name -> run(project) -> ModuleResult lookup; run_all_modules
├── report.py             # shared text/CSV rendering (load_cases_to_rows, text_report)
└── modules/
    ├── __init__.py       # imports every module so registration happens on import
    └── engine.py         # ENGLOADS (port of ENGLOADS.BAS)
app/
├── Home.py               # load/save project, summary, run-all (primary entry point)
└── pages/NN_*.py         # one Streamlit page per suite program
cli.py                    # argparse front-end; `farloads` console script
tests/                    # pytest; one manual-example test per module vs Appendix A/B
```

Data flow for one run: `project.json` → `io.load_project` → `Project` →
`registry.get(name)(project)` → `ModuleResult` → `report`/`io` renders text or the
load-case CSV. The GUI builds the `Project` from widgets; everything downstream is
identical.

---

## Coding standards

- **Python 3.9+**, with `from __future__ import annotations` at the top of each
  module.
- **Type hints** on all function signatures.
- **`@dataclass`** for every input and result object (`EngineInput`, `Rotor`,
  `LoadValue`, `ConditionResult`, `ModuleResult`, `Project`). Use **`Enum`** for
  closed sets (engine type, rotor type, rotor direction).
- **Pure calc, no I/O.** A module exposes `run(project: Project) -> ModuleResult`,
  reads the upstream fields it needs from `Project`, and returns results. No file
  access, no Streamlit, no printing inside `farloads/` calc code — `io.py` is the
  only place dataclasses meet JSON/CSV.
- **Reuse the result types.** Emit `LoadValue`/`ConditionResult`/`ModuleResult`
  so `report.py`, `units.py`, and the CSV writer work unchanged. The CSV is always
  "one row per load case" via `load_cases_to_rows` — generalise it, don't reinvent
  per module.
- **Self-register** at import (`register("name", run)`) and add the import to
  `farloads/modules/__init__.py`.
- **Never recompute another module's quantity** — read it from the `Project`
  slice that owns it.
- **Constants centralised** in `constants.py`; no bare magic numbers in calc.
- **Imperial in, SI at the edge.** Calc always runs in the Imperial units of the
  original program; `units.py` converts to/from SI at the boundary only.

### Math fidelity (non-obvious)

The project decision is to **modernise the math**: use `math.pi` and clean
equations, **not** the original program's `3.1416` literal. Consequently the
manual's printed figures are **tolerance-based regression oracles (±0.1%)**, not
exact oracles. Tests use `math.isclose(..., rel_tol=1e-3)` against the printed
numbers (keep the printed number + a page citation in the test so drift is
traceable); use exact equality only for integer/dimensionless quantities. Keeping
constants in `constants.py` keeps reverting this decision a one-file change.

### Preserved engineering conventions

From the original ENGLOADS, carried into every port that touches them:

- Engine-mount reaction torque is reported **negative**.
- "Clockwise from the pilot's view is positive" for rotor RPM and stoppage torque.
- Some intermediate quantities are truncated to 3 decimals (`int(x*1000)/1000`) to
  mirror the BASIC — preserve this **only where** it affects a compared figure.

---

## Error handling

Raise with a descriptive message; never silently emit a wrong or `nan` load.

| Condition | Behaviour |
|---|---|
| A module's required `Project` slice is absent | `raise ValueError` — `run_all_modules` catches it and skips that module, so "run all" works on a partially-filled project (`registry.py:43-51`, `modules/engine.py:332`) |
| Invalid domain input (e.g. a reciprocating engine with < 2 cylinders) | `raise ValueError` with a descriptive message (`constants.py:59`) |
| Unknown module name requested | `raise KeyError` listing the registered modules (`registry.py:30`) |
| An optional input is omitted (e.g. measured polar inertia) | Approximate from geometry where the manual does; never emit `nan` as a reported load value |

The "missing slice → `ValueError` → skipped by `run_all_modules`" idiom is load-
bearing: it is how a module signals "not my turn" on a project that doesn't carry
its inputs yet. A new module SHALL follow it rather than returning an empty result.

---

## Units

| Quantity | Imperial (canonical) | SI (presentation) |
|----------|----------------------|-------------------|
| Weight | lb | kg |
| Length | in | mm |
| Torque | ft-lb | N·m |
| Power | hp | kW |
| Inertia | slug-ft² | kg·m² |

Calc always runs in Imperial; a sidebar toggle and `units.py` convert for display
only. Saved `project.json` is always canonical Imperial.

---

## Entry points

- **Streamlit UI (primary):** `streamlit run app/Home.py` — load/save the
  project, see a summary, run all modules, and open per-program pages.
- **CLI (secondary, batch/automation):** the `farloads` console script (from the
  editable install) or `python cli.py <module> <project.json> [-o out.csv]`;
  `--list` shows registered modules. Text report to stdout, or `-o` writes the
  load-case CSV.
- **Library:** `import farloads` — `registry.get(name)(project)` over a `Project`
  you build yourself.

---

## Dependency requirements

Runtime (`pyproject.toml` `[project.dependencies]`): `streamlit>=1.30`,
`pandas>=2.0`. Dev extras (`[project.optional-dependencies].dev`): `pytest>=8.0`,
`pytest-cov`, `ruff`. Install with `pip install -e '.[dev]'`.

---

## Testing & coverage

- **One manual-example test per module** under `tests/`, asserting `run(project)`
  against the Appendix A (6-place GA single, p131) and/or Appendix B (10-place
  twin turboprop, p251) figures within **±0.1%** (`rel_tol=1e-3`); exact equality
  only for integer/dimensionless quantities.
- `ruff check farloads/ cli.py` clean and `pytest` passing are the merge gate; CI
  runs both on Python 3.9 / 3.11 / 3.12.
- **Coverage floor.** `pytest` emits a per-file branch-coverage table (configured
  via `addopts` in `pyproject.toml`). CI additionally enforces
  `--cov-fail-under=80` so coverage cannot silently regress. This floor is a
  **ratchet**: raise it toward 85% as `report.py` and `constants.py` gain tests,
  and tighten to a per-module gate on `farloads/modules/` (the load math) as the
  suite grows.
- A zero-dependency fallback runner exists (`python tests/test_engine.py`) for
  environments without pytest.

---

## Version & phase

Semantic versioning in `pyproject.toml`; `project.json` carries its own
`schema_version` (`models.py`), bumped when the on-disk shape changes. Phase 0
(restructure + the engine-mount module) is complete; the dependency-ordered
roadmap for modules #2..#22 is in [`PROJECT_GUIDE.md §7`](PROJECT_GUIDE.md) and the
open list in [`../30_future/00_backlog.md`](../30_future/00_backlog.md). Releases
follow [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md); reviews follow
[`CODE_REVIEW_PROCESS.md`](CODE_REVIEW_PROCESS.md).
