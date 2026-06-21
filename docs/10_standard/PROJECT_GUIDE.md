# FAR 23 LOADS — Project Guide

A development plan to replicate the **FAR 23 LOADS** computer-aided engineering
suite (Aero Science Software, Standard v3.0 / Professional v1.0 — Hal C.
McMaster) as a modern **Streamlit** application, with a single **JSON project
file** for input and **per-module CSV** load-case output.

The suite is **22 GW/QBasic programs** (reference 1, Appendix C) that together
compute the FAR Part 23 Subpart C structural loads for an airplane under 12,500
lb. **13 are ported today** (through Phase-C Step C6) plus two modern modules
(`configuration`, `body_loads`); the remaining 9 and the step-by-step plan are in
[`../30_future/00_backlog.md`](../30_future/00_backlog.md). This guide covers the
architecture and the dependency order that grew the original `engloads/`
engine-mount port into the present suite. The project is being grown beyond a
faithful ≤12,500 lb replication into an **initial-concept distributed-loads tool**
(Phase C) — see [`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md).

### Source documents (two — both in the repo, keep them distinct)

- **Reference 1** — McMaster, *"FAR23 LOADS"* (Aero Science Software, Std v3.0 /
  Pro v1.0); file `FAR23 loads (1).pdf` (371 pp). The theoretical development and
  the equation + validation oracle: 20 chapters, **Appendix A** (6-place GA loads
  report, p131), **Appendix B** (10-place twin, p251), **Appendix C** `.BAS`
  source for all **22 programs** (p373). Its chapter numbering is what
  `PROGRAM_SPEC.md` cites as "Ch N".
- **User's Guide** — *DOT/FAA/AR-96/46* (UDRI / Miedlar, March 1997;
  `ADA324952.pdf`): the operational guide for a later FAA repackaging. Its
  **Table 2.2** is the authoritative module input→output map (the basis for the
  data flow in §3 and the ownership table in `PROGRAM_SPEC.md`), it lists the FAR
  regs per module, and it defines the two sample airplanes. Regs through
  Amendment 42.

> **Two counts, both correct.** Reference 1 Appendix C ships **22 programs**; the
> FAA User's Guide exposes **20** of them as menu modules. The two off-menu ones
> are real utilities: **`TAU.BAS`** (lift-curve-slope helper → folds into the
> airloads module) and **`BALLOADS.BAS`** (a post-FLTLOADS verification tool for
> the balanced-tail-load centers of pressure — *not* a pipeline stage). The
> pipeline balancing tail load is computed in **FLTLOADS** (approximate CP) and
> refined rationally in **SELECT**; **TAILDIST** does the chordwise distribution.

---

## 1. Decisions taken (the basis for this plan)

These were chosen up front; the rest of the document follows from them.

| # | Decision | Choice | Consequence |
|---|----------|--------|-------------|
| 1 | **App architecture** | **Hybrid** — one shared pure-calc package + a multi-page Streamlit UI, with every module *also* runnable standalone from JSON/CLI. | `engloads` is refactored into a package module (`farloads.engine`); the GUI becomes one page among many. |
| 2 | **Data model** | **One unified project JSON in, per-module CSV out.** A single reloadable `project.json` carries all inputs; each module emits its own load-case CSV. | One shared schema (`farloads.models.Project`); each module reads the slice it needs and appends results. |
| 3 | **Math fidelity** | **Modernize the math** (`math.pi`, accurate constants, clean equations). | The manual's printed figures become **tolerance-based** regression checks, *not* exact oracles. See §6 — this changes how `engloads` is validated today. |
| 4 | **Scope** | **Full-suite roadmap** — spec all 22 programs now, build in dependency order. | This guide + `PROGRAM_SPEC.md` cover every program; implementation is phased (§7). |

### ⚠️ Decision 3 has a cost worth re-confirming

`engloads` currently reproduces the manual to the last decimal (it deliberately
keeps `PI = 3.1416` and asserts e.g. takeoff torque `554.3884 ft-lb` exactly).
"Modernize the math" means:

- switching to `math.pi` shifts those figures in the 4th–5th significant digit;
- the exact-match tests must be relaxed to engineering tolerances (recommended
  **±0.1%**, or per-quantity absolute tolerances where the manual rounds);
- the manual's Appendix A/B example reports remain the regression oracle, just
  compared with tolerance instead of equality.

This is recorded as accepted. If exact manual reproduction is later required for
certification traceability, it is a one-line constant change per module plus
tightening the tolerances — so keep constants centralized (§4) to preserve that
escape hatch.

---

## 2. What the suite does (program inventory)

22 programs (20 FAA menu modules + the `TAU` and `BALLOADS` utilities), grouped by role. "Status" marks the one already ported.

### Mass properties
| Program | Purpose | Status |
|---------|---------|--------|
| `WTESTIMA` | Estimate empty, max take-off and component weights | **done** (Phase 1) |
| `WTENV` | Envelope of weight & CG over the full range of loadings | **done** (Phase 2) |
| `WTONECG` | CG and inertia for one particular loading | **done** (Phase 1; persisted `mass` slice C6) |

### Geometry & speeds
| Program | Purpose | Status |
|---------|---------|--------|
| `WINGGEOM` | Aerodynamic & control-surface geometry (wing, tails, ailerons, flaps, tabs, rudder, elevator) | **done** (Phase 2) |
| `STRSPEED` | FAR minimum design speeds + chosen design speeds & maneuver load factors | **done** (Phase 2) |
| `MACHLIM` | Mach limit lines | **done** (Phase 2) |

### Aerodynamic coefficients
| Program | Purpose | Status |
|---------|---------|--------|
| `AIRLOADS` | Spanwise aero coefficients (airplane-less-tail) & spanwise airloads | **done** (C1 spanwise; C3 load distribution) |
| `AIRLOAD4` | As AIRLOADS, for sweepback and high-Mach airloads | planned (C7) |
| `TAU` (helper) | Lift-curve-slope correction factor; `TAU.EXE`, folds into airloads | **done** (C1, in `airloads.py`) |

### Flight envelope & load selection
| Program | Purpose | Status |
|---------|---------|--------|
| `FLTLOADS` | V-n (flight envelope) diagram data **+ balancing tail loads** (approx CP) | **done** (C2 cruise; C6 flapped corner set) |
| `SELECT` | Search/compute critical flight loads — wing, rational horizontal & vertical tail, fuselage | **done** (C6) |
| `BALLOADS` (utility) | Verify rational balanced-tail-load CP; `BALLOADS.BAS`, off-pipeline | planned (C11, optional) |

### Component loads
| Program | Purpose | Status |
|---------|---------|--------|
| `WINGINER` | Wing inertia loads | **done** (C3) |
| `NETLOADS` | Net wing loads (airload + inertia) | **done** (C3) |
| `ENGLOADS` | Engine mount loads | **done** ✅ (Phase 0) |
| `TAILDIST` | Chordwise load distribution (tail) | planned (C7) |
| `AILERON` | Aileron loads | planned (C8) |
| `FLAPLOAD` | Flap loads | planned (C8) |
| `TABLOADS` | Tab loads | planned (C8) |
| `ONENGOUT` | One-engine-out loads (multi-engine turboprop) | planned (C9) |
| `LGFACTOR` | Estimate landing load factor | planned (C10) |
| `LANDLOAD` | Landing loads | planned (C10) |

> **Modern modules (no `.BAS`):** `body_loads` (Ref 1 Ch 15 net fuselage
> distribution) **done** (C6); `configuration` (Configuration & Layout page)
> **done** (C5). Neither counts against the 22-program total.

Per-module FAR references, inputs, outputs, dependencies and validation examples
are in [`PROGRAM_SPEC.md`](PROGRAM_SPEC.md).

---

## 3. Data flow (why this is a pipeline, not 22 islands)

The original passes data between programs as `.INP` (input) and `.OUT` (output)
files — e.g. `WTESTIMA.OUT` feeds downstream programs; `WINGGEOM` emits a `.OUT`
per surface that the load programs consume. That handoff graph is the backbone we
preserve, just with one JSON project file instead of dozens of `.INP/.OUT` pairs.

Redrawn from **User's Guide Table 2.2** (WTONECG and WTENV are parallel siblings
off WTESTIMA; AIRLOADS⇄SELECT iterate; FLTLOADS computes balancing tail loads with
approximate CP, SELECT refines them rationally; `BALLOADS` is an off-pipeline
verification side-tool):

```
   WTESTIMA ──┬──► WTONECG ──► (weight/CG) ──► FLTLOADS, LANDLOAD
              └──► WTENV ─────────────────────► FLTLOADS
                       WTONECG ── (inertia) ──► SELECT, ONENGOUT

   WINGGEOM ──► STRSPEED ──► MACHLIM
        │          └────────► AILERON, FLAPLOAD
        │
        ▼
   AIRLOADS ⇄ SELECT          FLTLOADS ──► SELECT, WINGINER ··► BALLOADS (verify)
   AIRLOAD4   │  ▲                │
        │     ▼  └── SELECT ──────┘
        └──► NETLOADS ◄── WINGINER

   SELECT ──► TAILDIST              LGFACTOR ──► LANDLOAD
   ENGLOADS ✅ (standalone)         TABLOADS (standalone)
```

Component-load deliverables: WINGINER, NETLOADS, AILERON, FLAPLOAD, TABLOADS,
TAILDIST, ENGLOADS ✅, ONENGOUT, LGFACTOR, LANDLOAD.

Implication for the data model: upstream results (weights, CG, inertia, geometry,
design speeds, critical V-n points) are **shared fields** that many downstream
modules read. They belong in the project schema, written once and consumed many
times — not recomputed per module.

---

## 4. Target repository structure (the engloads restructure)

> **As-built note.** This was the *proposed* layout at restructure time; some
> module file names landed differently (`geometry.py` → `wing_geometry.py`,
> `speeds.py` → `structural_speeds.py` with `mach_limit.py` separate). The
> **authoritative as-built tree** is in
> [`00_program_overview.md`](00_program_overview.md); the `.BAS` → module-name map
> is in [`PROGRAM_SPEC.md`](PROGRAM_SPEC.md).

`engloads` becomes one module in a shared package. Proposed layout:

```
FAR23LOADS/
├── farloads/                     # the shared, pure-calc package (renamed/grown engloads/engloads)
│   ├── __init__.py
│   ├── constants.py              # ONE home for g, pi, unit factors  (centralized — see Decision 3)
│   ├── units.py                  # Imperial<->SI boundary conversion (already exists)
│   ├── models.py                 # Project dataclass + per-domain sub-models
│   ├── io.py                     # load/save project JSON; CSV writers
│   ├── registry.py               # module registry: name -> run(project) -> results
│   ├── report.py                 # shared text/CSV rendering (already exists)
│   ├── export/                   # output bridges to external tools (renderers, NOT registered modules)
│   │   ├── coordinates.py        # FAR23LOADS axes -> sbeam CID 0 map (single edit-point)
│   │   └── sbeam_bridge.py       # net wing load -> span-load CSV + FORCE/MOMENT cards + CBAR stick model
│   └── modules/
│       ├── __init__.py
│       ├── configuration.py      # Configuration & Layout (modern; no .BAS) -> Project.configuration
│       ├── weight_estimate.py    # WTESTIMA
│       ├── weight_envelope.py    # WTENV
│       ├── weight_onecg.py       # WTONECG
│       ├── geometry.py           # WINGGEOM
│       ├── speeds.py             # STRSPEED (+ machlim.py)
│       ├── airloads.py           # AIRLOADS / AIRLOAD4 / tau.py (TAU helper)
│       ├── flight_envelope.py    # FLTLOADS (V-n + balancing tail loads)
│       ├── select.py             # SELECT (+ balloads.py verification utility)
│       ├── wing_inertia.py       # WINGINER
│       ├── net_loads.py          # NETLOADS
│       ├── aileron.py, flap.py, tab.py, taildist.py
│       ├── engine.py             # ENGLOADS  ← current engloads/engloads/calc.py
│       ├── one_engine_out.py     # ONENGOUT
│       └── landing.py            # LANDLOAD (+ lgfactor.py)
├── app/                          # multi-page Streamlit UI
│   ├── Home.py                   # load/save project JSON, project summary, run-all
│   └── pages/
│       ├── 00_Configuration_Layout.py  # Configuration & Layout (three-view + fleet)
│       ├── 01_Weight_Estimate.py
│       ├── 02_Weight_Envelope.py
│       ├── ...
│       └── 19_Engine_Mount.py    # current engloads/app.py content
├── cli.py                        # `python cli.py engine project.json -o out.csv`
├── tests/
│   ├── test_engine.py            # current test_calc.py (renamed)
│   ├── test_units.py, test_report.py, test_io.py
│   └── test_<module>.py          # one per module, vs manual Appendix A/B
├── examples/
│   ├── ga6_normal.project.json   # Appendix A — 6-place GA single
│   └── concept_heavy.project.json  # 18,000 lb concept commuter twin (concept mode)
│   # (an Appendix B twin_turboprop.project.json is a backlog item; the engine
│   #  module's Appendix-B turboprop case is currently inline in tests/test_engine.py)
├── docs/                         # organised by type — see docs/00_INDEX.md
│   ├── 00_INDEX.md
│   ├── 10_standard/              # PROJECT_GUIDE.md (this file), PROGRAM_SPEC.md, process guides
│   ├── 20_theory/               # equation sources (the reference/ PDFs) + per-module citations
│   ├── 30_future/               # 00_backlog.md — open modules / decisions
│   └── 40_history/              # 00_completed_development.md — what shipped
├── pyproject.toml                # build metadata, deps, ruff + pytest/coverage config
├── cspell.json                   # domain wordlist
├── requirements.txt
└── README.md
```

### Migration of `engloads` (mechanical, low-risk)
1. `engloads/engloads/` → `farloads/`. Keep `calc.py` as `farloads/modules/engine.py` (or keep the name; update imports).
2. `engloads/app.py` → `app/pages/19_Engine_Mount.py`; add a thin `app/Home.py`.
3. Tests move under top-level `tests/`; rename `test_calc.py` → `test_engine.py`.
4. Introduce `models.Project` and make `EngineInput` a *view* over the engine slice of `Project` (or keep `EngineInput` and have `Project.engine: EngineInput`). The second is less churn — recommended.
5. Add `farloads/io.py` and `registry.py`. ENGLOADS registers itself; "run all" iterates the registry.

Do the restructure as **step 0** of Phase 1, with the engine module as the proof
that the new package + JSON + CSV + tests all still pass before adding any new
program.

---

## 5. Conventions (the contract every module follows)

So that every module is copy-of-the-pattern, these are fixed once:

- **Pure calc, no I/O.** Each module exposes `run(project: Project) -> ModuleResult`. No Streamlit, no file access inside calc. (engloads already does this.)
- **Read shared, write own.** A module reads upstream fields from `Project` and returns results; it must not silently recompute an upstream quantity that another module owns.
- **Results are labelled values.** Reuse the existing `LoadValue(label, value, units)` / `ConditionResult` types so `report.py`, the units layer and the CSV writer work unchanged for every module.
- **One CSV shape per module = load cases.** Each row is one structural load case: `ID`, `FAR §`, `Case description`, application point `Loc X/Y/Z`, then the applied loads/moments. This is exactly the `load_cases_to_rows` pattern engloads already established — generalize it, don't reinvent per module.
- **Units at the boundary only.** Calc stays in one internal system; `units.py` converts JSON-in and display/CSV-out. (Already implemented.)
- **Constants centralized** in `farloads/constants.py` so Decision 3 (and any future "go back to exact") is a one-file change.
- **Each module has a manual example test** (Appendix A and/or B) under `tests/`.

---

## 6. Validation strategy (given "modernize the math")

**Reference 1** (McMaster's theory manual) prints full example loads reports for
two airplanes in its Appendix A/B:

- **Appendix A** — 6-place general-aviation single (the `engloads` reciprocating example lives here). Sample data set `M2002576` / `WTENV36`-series.
- **Appendix B** — 10-place twin turboprop (swept wing, altitudes to 50,000 ft, gyroscopic engine loads, one-engine-out — the `engloads` turboprop example lives here). Sample data set `BB*` (`BBFLTLDR`, `BBSELECT`, `PHAABB36`, `ACCELROL`, `TORBB36`).

> ✅ **Oracle is in hand.** Reference 1 is `FAR23 loads (1).pdf` (371 pp) in the
> repo: Appendix A loads report starts p131, Appendix B p251, Appendix C `.BAS`
> source p373. Both the worked example numbers (regression oracle) and the exact
> equations (per-module transcription source) are therefore available — no
> reconstruction needed. Page-map the Appendix A/B quantities per module as the
> tests are written.

Strategy:
1. Encode both airplanes once as `examples/*.project.json`.
2. For each module, assert its `run(project)` matches the corresponding Appendix figures **within tolerance** (recommended ±0.1%; widen only where the manual visibly rounds an intermediate).
3. Keep the comparison values in the test as the manual's *printed* numbers, with a comment citing the page — so drift is loud and traceable.
4. CI/locally: `pytest tests/` runs every module against both airplanes.

> Action item from Decision 3: when migrating `engloads`, relax its current
> exact-equality asserts to the ±0.1% tolerance and switch `constants.PI` to
> `math.pi`. Do this in the same PR so the change in figures is reviewed in one
> place.

---

## 7. Roadmap (dependency-ordered phases)

Each phase ends with: the module(s) merged, a `tests/test_<module>.py` passing
against Appendix A/B, a GUI page, and the project JSON schema extended.

> **Phases 0–2 are complete, and the original Phases 3–4 were re-sequenced by the
> Phase-C plan** (vertical-slice-first; concept-mode generalization) — see
> [`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md).
> The live, dependency-ordered open plan (Steps C7–C11) is the backlog. The
> phase descriptions below are the historical roadmap that produced the present
> suite.

**Phase 0 — Restructure** ✅ (no new physics)
`engloads` → `farloads` package + `app/` multipage + `cli.py` + `Project` model +
`io.py`/`registry.py`. Relax engine tests to tolerance, switch to `math.pi`. Green
build is the gate.

**Phase 1 — Mass properties** ✅ (`WTESTIMA` + `WTONECG`)
`WTESTIMA` → `WTONECG` (shared weight database, `Project.weight`). Establishes the
weight/CG/inertia fields the downstream pipeline reads. `WTENV` was **re-scoped to
Phase 2**: its structural-CG limits need `XLEMAC`/`MAC` from `WINGGEOM`, so it is
built there reading `Project.geometry` rather than via an interim direct input.

**Phase 2 — Geometry & speeds** ✅
`WINGGEOM` (largest single module — all surfaces), then `WTENV` (weight/CG
envelope, now that `XLEMAC`/`MAC` are available), then `STRSPEED` + `MACHLIM`.
These plus Phase 1 unlock most component-load modules.

**Phase 3 — Aero coefficients & flight envelope** (re-sequenced into Phase-C
Steps C1/C2/C6; `AIRLOAD4` and the optional `BALLOADS` remain)
`TAU` ✅ → `AIRLOADS` ✅ / `AIRLOAD4` (C7) → `FLTLOADS` ✅ (incl. balancing tail
loads) → `SELECT` ✅ (rational critical wing/tail/fuselage loads). The analytical
heart; produces the critical-load set everything downstream is sized to.

**Phase 4 — Component loads** (re-sequenced into Phase-C Steps C3/C7–C10)
`WINGINER` ✅, `NETLOADS` ✅, `ENGLOADS` ✅; `TAILDIST` (C7), `AILERON`/`FLAPLOAD`/
`TABLOADS` (C8), `ONENGOUT` (C9), `LGFACTOR`/`LANDLOAD` (C10).

The **vertical-slice** value path (`WTESTIMA → WINGGEOM → STRSPEED → FLTLOADS →
SELECT → NETLOADS` end-to-end, plus the sbeam export) is the path the Phase-C plan
actually took, and it is now complete.

---

## 8. Open user decisions (for later phases, not blocking Phase 0)

1. **Graphics.** The original has a separate graphics program (weight envelope, V-n diagram, spanwise plots). Replicate these as Streamlit charts (Altair/Matplotlib)? Default: yes, per module, deferred to that module's phase.
2. **Multi-engine / twin layout.** ✅ **RESOLVED (Phase 2): first-class now.** `Project.engines: List[EngineInput]` + `EngineLayout` (`SINGLE_NOSE`/`TWIN_WING`/`QUAD_WING`, symmetric). The engine module loops over every engine; full one-engine-out *loads* are still built at `ONENGOUT`.
3. **Project JSON versioning.** Add a `schema_version` to `project.json` from day one so old saves migrate cleanly as the schema grows? Default: yes.
4. **Standalone vs project-only inputs.** Hybrid allows a module to run from a partial JSON (just its own slice). Confirm we want to maintain per-module example JSONs in addition to the two full-airplane projects. Default: full projects are canonical; per-module slices are derived for tests.
5. **CSV vs combined workbook.** "Per-module CSV out" is set. Optionally also offer a single multi-sheet export (zip of CSVs or xlsx) for hand-off? Default: zip of per-module CSVs from the Home page.

---

## 9. Getting started

```bash
pip install -e '.[dev]'          # editable install + dev tools (pytest, ruff)
streamlit run app/Home.py        # the multi-page UI (after Phase 0)
python cli.py engine examples/ga6_normal.project.json -o engine_loads.csv
pytest                           # the green-build gate
ruff check farloads/ cli.py      # lint
```

See [`PROGRAM_SPEC.md`](PROGRAM_SPEC.md) for the per-module specification.
