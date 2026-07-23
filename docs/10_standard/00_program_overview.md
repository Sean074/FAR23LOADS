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
sloads/                 # shared, pure-calc package — no I/O in calc code
├── constants.py          # g, pi (math.pi), unit factors, atmosphere — the one home for constants
├── models.py             # Project + per-domain input/result slices, ConditionResult/LoadValue, ModuleResult, SCHEMA_VERSION
├── units.py              # Imperial<->SI conversion at the I/O boundary only
├── io.py                 # the only dataclass<->JSON mapping; project.json + load-case CSV
├── registry.py           # name -> run(project) -> ModuleResult lookup; run_all_modules
├── report.py             # shared text/CSV rendering (load_cases_to_rows, text_report)
├── export/               # output renderers to external tools (NOT registered modules)
│   ├── coordinates.py    # FAR23LOADS axes -> sbeam CID 0 map (single edit-point)
│   └── sbeam_bridge.py   # net wing/body load -> span CSV + FORCE/MOMENT cards + CBAR stick model
└── modules/              # one file per suite program; each self-registers on import
    ├── __init__.py       # imports every module so registration happens on import
    ├── engine.py         # ENGLOADS                weight_estimate.py  # WTESTIMA
    ├── weight_onecg.py   # WTONECG                 weight_envelope.py  # WTENV
    ├── wing_geometry.py  # WINGGEOM                structural_speeds.py# STRSPEED
    ├── mach_limit.py     # MACHLIM                 airloads.py         # AIRLOADS (+ TAU helper)
    ├── flight_envelope.py# FLTLOADS                select.py           # SELECT
    ├── wing_inertia.py   # WINGINER                net_loads.py        # NETLOADS
    ├── body_loads.py     # net fuselage (Ch 15)    configuration.py    # Configuration & Layout (modern)
app/
├── Home.py               # st.navigation entry point: 6-section sidebar (Start→Airplane→Envelopes & Critical Conditions→Analysis→Loads Plots→Export)
├── views/                # one view per step; named by workflow key (no numeric prefixes)
│   ├── dashboard.py      #   Start    — load/save project + workflow completeness panel
│   ├── results_review.py #   Export   — consolidated governing loads (recomputed live)
│   └── export_report.py  #   Export   — project JSON + per-module CSVs + sbeam BDF cards
└── data/reference_aircraft.csv
cli.py                    # argparse front-end; `sloads` console script
tests/                    # pytest; one manual-example test per module vs Appendix A/B
examples/                 # ga6_normal (Appendix A), cessna_210 (normal cat), concept_heavy + dhc8_dash8 (concept) project.json
```

Data flow for one run: `project.json` → `io.load_project` → `Project` →
`registry.get(name)(project)` → `ModuleResult` → `report`/`io` renders text or the
load-case CSV. The GUI builds the `Project` from widgets; everything downstream is
identical.

The GUI is organised as a six-section workflow — **Start → Airplane → Envelopes &
Critical Conditions → Analysis → Loads Plots → Export** (Phase D; see
`docs/30_future/02_gui_workflow_plan.md`) — built explicitly with `st.navigation`
from `sloads/workflow.py`, the ordered, dependency-aware step graph (each step
names the calc `module` it runs and the slices it `requires`/`produces`). That one
source of truth drives both the sidebar grouping (a section with no steps yet is
omitted rather than shown empty) and the Home dashboard's completeness panel, so
the navigation can never silently drift from the shipped modules. The Results
Review and Export & Report pages (both in the Export section) recompute from the
project inputs rather than reading persisted result slices, so they are never
stale.

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
  access, no Streamlit, no printing inside `sloads/` calc code — `io.py` is the
  only place dataclasses meet JSON/CSV.
- **Reuse the result types.** Emit `LoadValue`/`ConditionResult`/`ModuleResult`
  so `report.py`, `units.py`, and the CSV writer work unchanged. The CSV is always
  "one row per load case" via `load_cases_to_rows` — generalise it, don't reinvent
  per module.
- **Self-register** at import (`register("name", run)`) and add the import to
  `sloads/modules/__init__.py`.
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
| A module's required `Project` slice (or a required upstream result/geometry/aero slice, or a required-but-empty input list) is absent | `raise MissingInputError` (a `ValueError` subclass, `models.py`) — `run_all_modules` catches **only** this and skips that module, so "run all" works on a partially-filled project (M2R-8) |
| Invalid domain input (e.g. a reciprocating engine with < 2 cylinders, a non-positive area, a mismatched element count) or a genuine calc defect | `raise ValueError` with a descriptive message (`constants.py:59`) — **not** caught by `run_all_modules`, so the failure surfaces in run-all/export instead of vanishing |
| Unknown module name requested | `raise KeyError` listing the registered modules (`registry.py:30`) |
| An optional input is omitted (e.g. measured polar inertia) | Approximate from geometry where the manual does; never emit `nan` as a reported load value |

The "missing slice → `MissingInputError` → skipped by `run_all_modules`" idiom is
load-bearing: it is how a module signals "not my turn" on a project that doesn't
carry its inputs yet. A new module SHALL follow it (raising `MissingInputError` at
its entry guards) rather than returning an empty result. A plain `ValueError` is
reserved for present-but-invalid data and genuine defects, which must remain visible
— before M2R-8 the registry swallowed *every* `ValueError`, hiding those defects.

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

### Loads are ULTIMATE (mandatory)

**All deliverable load output is ULTIMATE** — every force/moment/pressure in a
deliverable (the `report.py` tables/text, the load-case CSV, the sbeam export, the
Review/Export pages) is `ultimate = limit × SF`, never a bare limit load. The calc
layer itself stays LIMIT (oracle-lock); the factor is applied once at the
render/export boundary. **Exception:** a per-module *analysis* page may show the
calc's LIMIT values (the oracle-traceable numbers) **only when explicitly marked
`LIMIT`** — a caption plus a `LIMIT` marker on each load column/metric — and it
points to the ultimate deliverables. Today that covers `flap_loads`, `tab_loads`,
`one_engine_out` and the `balanced_tail_verification` check tool.

| Load quantity | Imperial (canonical) | SI (presentation) |
|---------------|----------------------|-------------------|
| Force | lbs-ULT | N-ULT |
| Moment / torque | ft-lb-ULT, lb-in-ULT | Nm-ULT |
| Design pressure | lb/in²-ULT (psi-ULT) | — |

The `-ULT` marker is treated as **part of the units string** (like lb vs. N).
Every load case carries its **safety factor** (the `SF` column / an `SF=` marker),
default **1.5 per 14 CFR 23.303** (Part 25 equivalent: 25.303). A quantity already
at ultimate — or an inherently-limit value reported as-ultimate with no
amplification — is `ULT SF=1.0`. Non-load quantities (weights, lengths, inertias,
areas, speeds, angles, dimensionless load factors) are **not** scaled and carry
plain units with no `-ULT` suffix.

---

## Entry points

- **Streamlit UI (primary):** `streamlit run app/Home.py` — the six-section
  workflow (Start → Airplane → Envelopes & Critical Conditions → Analysis →
  Loads Plots → Export). The Start dashboard loads/saves the project and shows
  per-step completeness; each section groups its pages in the sidebar; the
  Results Review and Export & Report pages (both in Export) consolidate
  governing loads and all exports.
- **CLI (secondary, batch/automation):** the `sloads` console script (from the
  editable install) or `python cli.py <module> <project.json> [-o out.csv]`;
  `--list` shows registered modules. Text report to stdout, or `-o` writes the
  load-case CSV.
- **Library:** `import sloads` — `registry.get(name)(project)` over a `Project`
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
- `ruff check sloads/ cli.py` clean and `pytest` passing are the merge gate; CI
  runs both on Python 3.9 / 3.11 / 3.12.
- **Coverage floor.** `pytest` emits a per-file branch-coverage table (configured
  via `addopts` in `pyproject.toml`). CI additionally enforces
  `--cov-fail-under=80` so coverage cannot silently regress. This floor is a
  **ratchet**: raise it toward 85% as `report.py` and `constants.py` gain tests,
  and tighten to a per-module gate on `sloads/modules/` (the load math) as the
  suite grows.
- A zero-dependency fallback runner exists (`python tests/test_engine.py`) for
  environments without pytest.

---

## Version & phase

Semantic versioning in `pyproject.toml`; `project.json` carries its own
`schema_version` (`models.py`, currently **15**), bumped when the on-disk shape
changes. **Status:** Phases 0–2 and Phase-C Steps **C0–C11** are complete — all 22
of Reference 1's programs are ported, plus the modern `configuration` and
`body_loads` modules. The remaining deferred refinements and open decisions
are in [`../30_future/00_backlog.md`](../30_future/00_backlog.md); the
architectural roadmap is in [`PROJECT_GUIDE.md §7`](PROJECT_GUIDE.md) and the
Phase-C narrative in
[`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md).
Releases follow [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md); reviews follow
[`CODE_REVIEW_PROCESS.md`](CODE_REVIEW_PROCESS.md).
