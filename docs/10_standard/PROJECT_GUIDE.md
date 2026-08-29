# sloads — Project Guide

A development plan to replicate the **FAR 23 LOADS** computer-aided engineering
suite (Aero Science Software, Standard v3.0 / Professional v1.0 — Hal C.
McMaster) as a modern **Streamlit** application, with a single **JSON project
file** for input and **per-module CSV** load-case output.

The suite is **22 GW/QBasic programs** (reference 1, Appendix C) that together
compute the FAR Part 23 Subpart C structural loads for an airplane under 12,500
lb. **All 22 are ported today** (through Phase-C Step C11) plus four modern
modules (`configuration`, `body_loads`, `tail_span`, `balance` — the last two
carrying the mission's distributed-empennage and assembled-airplane work); the
live backlog is deferred refinements and open
decisions, in [`../30_future/00_backlog.md`](../30_future/00_backlog.md). This
guide covers the architecture and the dependency order that grew the original
`engloads/` engine-mount port into the present suite. The project is being grown
beyond a faithful ≤12,500 lb replication into an **initial-concept
distributed-loads tool** (Phase C) — see
[`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md).

### Source documents (two — both in the repo, keep them distinct)

- **Reference 1** — McMaster, *"FAR23 LOADS"* (Aero Science Software, Std v3.0 /
  Pro v1.0); file `FAR23Loads_Code.pdf` (371 pp). The theoretical development and
  the equation + validation oracle: 20 chapters, **Appendix A** (6-place GA loads
  report, p131), **Appendix B** (10-place twin, p251), **Appendix C** `.BAS`
  source for all **22 programs** (p373). Its chapter numbering is what
  `PROGRAM_SPEC.md` cites as "Ch N".
- **User's Guide** — *DOT/FAA/AR-96/46* (UDRI / Miedlar, March 1997;
  `FAR23Loads_UserGuide.pdf`): the operational guide for a later FAA repackaging. Its
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
| 1 | **App architecture** | **Hybrid** — one shared pure-calc package + a multi-page Streamlit UI, with every module *also* runnable standalone from JSON/CLI. | `engloads` is refactored into a package module (`sloads.engine`); the GUI becomes one page among many. |
| 2 | **Data model** | **One unified project JSON in, per-module CSV out.** A single reloadable `project.json` carries all inputs; each module emits its own load-case CSV. | One shared schema (`sloads.models.Project`); each module reads the slice it needs and appends results. |
| 3 | **Math fidelity** | **Modernize the math** (`math.pi`, accurate constants, clean equations). | The manual's printed figures become **tolerance-based** regression checks, *not* exact oracles. See §6 — this changes how `engloads` is validated today. |
| 4 | **Scope** | **Full-suite roadmap** — spec all 22 programs now, build in dependency order. | This guide + `PROGRAM_SPEC.md` cover every program; implementation is phased (§7). |

### Decision 3 — the escape hatch

The math is modernized (`math.pi`, clean equations), so the manual's Appendix A/B
figures are tolerance-based regression oracles (±0.1%), not exact. If exact manual
reproduction is ever required for certification traceability, it is a one-line
constant change per module plus tightening the tolerances — so constants stay
centralized in `constants.py` (§4) to preserve that escape hatch. (The Phase-0
relaxation that switched `PI = 3.1416` → `math.pi` is recorded in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).)

---

## 2. What the suite does (program inventory)

22 programs (20 FAA menu modules + the `TAU` and `BALLOADS` utilities), grouped by role. "Status" marks the porting phase; all 22 are now done.

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
| `AIRLOAD4` | As AIRLOADS, for sweepback and high-Mach airloads | **done** (C7, swept branch in `airloads.py`) |
| `TAU` (helper) | Lift-curve-slope correction factor; `TAU.EXE`, folds into airloads | **done** (C1, in `airloads.py`) |

### Flight envelope & load selection
| Program | Purpose | Status |
|---------|---------|--------|
| `FLTLOADS` | V-n (flight envelope) diagram data **+ balancing tail loads** (approx CP) | **done** (C2 cruise; C6 flapped corner set) |
| `SELECT` | Search/compute critical flight loads — wing, rational horizontal & vertical tail, fuselage | **done** (C6) |
| `BALLOADS` (utility) | Verify rational balanced-tail-load CP; `BALLOADS.BAS`, off-pipeline | **done** (C11; reuses SELECT's balance routine) |

### Component loads
| Program | Purpose | Status |
|---------|---------|--------|
| `WINGINER` | Wing inertia loads | **done** (C3) |
| `NETLOADS` | Net wing loads (airload + inertia) | **done** (C3) |
| `ENGLOADS` | Engine mount loads | **done** ✅ (Phase 0) |
| `TAILDIST` | Chordwise load distribution (tail) | **done** (C7) |
| `AILERON` | Aileron loads | **done** (C8) |
| `FLAPLOAD` | Flap loads | **done** (C8) |
| `TABLOADS` | Tab loads | **done** (C8) |
| `ONENGOUT` | One-engine-out loads (multi-engine turboprop) | ✅ done (C9) |
| `LGFACTOR` | Estimate landing load factor | ✅ done (C10) |
| `LANDLOAD` | Landing loads | ✅ done (C10) |

> **Modern modules (no `.BAS`):** `configuration` (the unified **Geometry**
> page, Step G1) **done** (C5); `body_loads` (Ref 1 Ch 15 net fuselage
> distribution) **done** (C6); `tail_span` (spanwise empennage loads incl. the
> suite's first hinge moment, plan 09) **done** (steps 7–9); `balance` (balanced
> free-free airplane cases, flight and ground — the mission's primary
> deliverable, plans 11/13/18) **done** (steps B2–B8a, step 10 piece 3). None
> counts against the 22-program total; each has its own `PROGRAM_SPEC.md`
> section.

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

Component-load deliverables: WINGINER ✅, NETLOADS ✅, AILERON ✅, FLAPLOAD ✅,
TABLOADS ✅, TAILDIST ✅, ENGLOADS ✅, ONENGOUT ✅, LGFACTOR ✅, LANDLOAD ✅.

Implication for the data model: upstream results (weights, CG, inertia, geometry,
design speeds, critical V-n points) are **shared fields** that many downstream
modules read. They belong in the project schema, written once and consumed many
times — not recomputed per module.

---

## 4. Repository structure (as built)

> **The authoritative package layout** (CLAUDE.md points here). Refreshed
> 2026-08-15 from the shipped tree — review finding **R6-D5**, which found it
> missing every single-source owner added since the restructure — and **guarded**:
> `tests/test_package_layout.py` asserts the `sloads/` half of this tree is
> exactly the package on disk, in both directions, so a new module cannot ship
> unlisted and a listed file cannot vanish. The `.BAS` → module-name map is in
> [`PROGRAM_SPEC.md`](PROGRAM_SPEC.md). This section used to hold the *proposed*
> restructure layout instead, under which some names landed differently
> (`geometry.py` → `wing_geometry.py`, `speeds.py` → `structural_speeds.py` +
> `mach_limit.py`); the restructure itself is recorded in
> [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).

```
FAR23LOADS/
├── sloads/                       # the shared, pure-calc package — no I/O in calc code
│   ├── constants.py              # ONE home for g, pi, unit factors, atmosphere (Decision 3)
│   ├── units.py                  # Imperial<->SI boundary conversion + deliverable_units (the unit-channel SSOT)
│   ├── basic.py                  # ONE home for GW-BASIC numeric semantics: `INT()` floors where Python's `int()` truncates (CR-B-3)
│   ├── convergence.py            # THE iterative-solver outcome vocabulary: converged / clamped / failed, and the refusal an exhausted loop raises (#33)
│   ├── models/                   # the Project schema, split from models.py at M3-1
│   │   ├── enums.py              # schema enumerations (categories, kinds, tail types)
│   │   ├── inputs.py             # per-module input dataclasses
│   │   ├── project.py            # the Project aggregate root + SCHEMA_VERSION
│   │   └── results.py            # result dataclasses (ConditionResult/LoadValue, per-module results)
│   ├── io.py                     # the only dataclass<->JSON mapping; project.json + load-case CSV
│   ├── migrations.py             # normalise any historical project.json to the current schema
│   ├── registry.py               # module registry: name -> run(project) -> ModuleResult; run_all_modules
│   ├── spec_names.py             # registry name -> PROGRAM_SPEC heading (+ the non-module allowlist), guarded (R6-D6)
│   ├── field_registry.py         # THE input-field registry: path │ slice │ page │ origin │ quantity │ owner │ supplied (note 32, OG-14/G5)
│   ├── workflow.py               # THE nav SSOT: ordered Start→Develop V-n→Flight loads→Other loads→Landing→Load-case plotting→Export step graph (GUI nav + dashboard; Step G2)
│   ├── load_keys.py              # canonical LoadValue.key constants for the load-case schema (M4-9)
│   ├── case_ids.py               # structured load-case / subcase / deck LOAD id allocation (D1, M4-2)
│   ├── safety_factors.py         # THE governing safety-factor table: one row per condition family (M4-8 / G-11)
│   ├── picks.py                  # THE platform-stable keyed pick (`extreme`): ties go first-in-order, no built-in keyed max/min in the package (CONVENTIONS §7)
│   ├── cg_cases.py               # the one resolver for weight/CG cases and the two design weights (step 10 piece 2)
│   ├── mass_distribution.py      # MASS SSOT: weight.items -> per-component station inertia (B1/B-2)
│   ├── derived_geometry.py       # single-source geometry derivations (wing/fuselage/carry-through; M2-6)
│   ├── derived.py                # derived slices (`Project.mass` from `weight.items`) and their one refresher (#62)
│   ├── selectors.py              # selector names (surface / CG case / coefficient set): seeds, uniqueness, `keyed` lookups (#63)
│   ├── tail_geometry.py          # the empennage planform the spanwise strip integrator runs on (plan 09 T1)
│   ├── aero_curves.py            # airplane-less-tail aero-coefficient curves + their closure checks (M4-5)
│   ├── vn_diagram.py             # pure V-n diagram geometry: stall/manoeuvre/gust polylines (Phase E3)
│   ├── fuselage_moment.py        # pure Munk slender-body fuselage dCm/dα estimator (off-by-default; Step G4) + the Munk-couple single owner (L-7.7)
│   ├── lateral_body_aero.py      # DATCOM 5.2.1.1/5.2.3.1 wing-body Cy_β/Cn_β in sideslip, oracle-locked to Digital DATCOM (L-7)
│   ├── atmosphere.py             # air viscosity + Reynolds number on the suite's standard atmosphere (L-7.13)
│   ├── rigid_body.py             # the rigid-body d'Alembert relief field — single owner of the closure (L-2)
│   ├── gear_loads.py             # the landing gear as a free body: contact patch in, reference point out (step 10 piece 3)
│   ├── frames.py                 # the two frames a ground load is stated in, their words, and the rotation between them (note 38 GF-6/GF-7)
│   ├── applicability.py          # pure FAR 23 applicability detection (Exceedance list; Phase E1)
│   ├── validation.py             # pure input-consistency predicates (ConsistencyWarning list; Phase E3)
│   ├── fleet.py                  # pure fleet placement: nearest-N / percentile / outlier (FleetStats; Phase E4)
│   ├── report/                   # rendering + the controlled summary document (Step G8)
│   │   ├── render.py             # shared text/CSV tables + the limit→ultimate boundary (was report.py)
│   │   ├── methods.py            # the ONE methods & limitations statement (+ CSV `#` / BDF `$` wrappers)
│   │   ├── coverage.py           # FAR 23 Subpart C coverage matrix (covered / n-a / not analysed / out of scope)
│   │   ├── content.py            # Project + module results → ReportDocument (sections/tables/figures) — no LaTeX
│   │   ├── bundle.py             # THE Export zip's member list: every file it carries, with the manifest row that names it (CR-C-1)
│   │   ├── results_zip.py        # the sidebar's whole-project results zip: every module run, skip-and-manifest (C210-45)
│   │   ├── conventions_tex.py    # the report's "Axes and sign conventions" section, from CONVENTIONS.md's owners
│   │   ├── latex.py              # ReportDocument → .tex (escaping, longtable, document control)
│   │   └── plots_tex.py          # pgfplots figures: V-n, weight/CG, speed–altitude
│   ├── export/                   # output bridges to external tools (renderers, NOT registered modules)
│   │   ├── bands.py              # THE GID/EID/SID band registry: one owner per id run, disjointness proved by test
│   │   ├── coordinates.py        # SLOADS axes -> sbeam CID 0 map + the reflection operator (single edit-point)
│   │   ├── sbeam_bridge.py       # net wing/body/tail/control/gear loads -> span-load CSV + FORCE/MOMENT cards + CBAR stick model + case index + export-scope filter
│   │   ├── mass_cards.py         # CONM2/MASSSET mass model for sbeam (C1–C5)
│   │   ├── balanced_deck.py      # the assembled full-span free-free deck — the primary deliverable (B5)
│   │   ├── lra_model.py          # the LRA beam model — the third deliverable (step 12): skeleton + transferred balanced cases
│   │   ├── lra_import.py         # loads onto an imported GRID/CBAR beam model, mapped by the $ SLOADS-NODE contract
│   │   ├── equilibrium.py        # deck-derived force/moment resultants: the export-boundary closure gate
│   │   ├── workbook.py           # multi-sheet .xlsx workbook (Step D8.2): one tab per module/component + case index
│   │   ├── roundtrip.py          # solve an exported deck in the real sbeam (step 2; test-only use)
│   │   └── pdf.py                # ⚠ the ONE impure export helper: TeX engine discovery + subprocess compile (G8.6)
│   └── modules/                  # one file per suite program + the modern additions; each self-registers on import
│       ├── configuration.py      # Geometry (modern; no .BAS) -> Project.geometry.{parametric,empennage,landing_gear} (G1/G6/G6b)
│       ├── weight_estimate.py    # WTESTIMA
│       ├── weight_envelope.py    # WTENV
│       ├── weight_onecg.py       # WTONECG
│       ├── wing_geometry.py      # WINGGEOM
│       ├── structural_speeds.py  # STRSPEED
│       ├── mach_limit.py         # MACHLIM
│       ├── airloads.py           # AIRLOADS / AIRLOAD4 (+ the TAU helper, folded)
│       ├── flight_envelope.py    # FLTLOADS (V-n + balancing tail loads)
│       ├── select.py             # SELECT
│       ├── balloads.py           # BALLOADS (off-pipeline verification; reuses select)
│       ├── wing_inertia.py       # WINGINER
│       ├── net_loads.py          # NETLOADS
│       ├── body_loads.py         # net fuselage loads — the body analogue of NETLOADS (modern; Ch 15)
│       ├── aileron.py            # AILERON
│       ├── flap.py               # FLAPLOAD
│       ├── tab.py                # TABLOADS
│       ├── taildist.py           # TAILDIST (chordwise)
│       ├── tail_span.py          # spanwise empennage loads incl. the hinge moment (modern; plan 09)
│       ├── _vtail.py             # shared vertical-tail aero helpers (rational v-tail loads)
│       ├── engine.py             # ENGLOADS
│       ├── one_engine_out.py     # ONENGOUT
│       ├── landing.py            # LGFACTOR + LANDLOAD
│       └── balance.py            # balanced free-free airplane cases, flight + ground (modern; plans 11/13/18)
├── app_shell/                    # the app-layer shell — ONE owner, shared by every GUI (note 32, OG-B)
│   ├── components.py             # page scaffold, unit-input boundary, page links, applicability banner
│   ├── project_state.py          # the project in session state + the unsaved-changes / discard guard
│   ├── sidebar.py                # the global sidebar: units toggle, project Open/Save/upload, About
│   ├── nav.py                    # which page a step key is in the running GUI — links resolve to a page, not a path (OG-F)
│   └── limit_csv.py              # the analysis pages' LIMIT tables + downloads (pure, no Streamlit)
├── app/                          # multi-page Streamlit UI (st.navigation, 6 sections — Phase D)
│   ├── Home.py                   # entry point: set_page_config + its own nav from sloads.workflow
│   ├── views/                    # one view per workflow step (clean names, no prefixes)
│   │   ├── dashboard.py          #   Start    — load/save + completeness panel
│   │   ├── project_editor.py     #   Start    — whole project as JSON, in the sidebar's Imperial/SI units
│   │   ├── configuration_layout.py … one_engine_out.py   # one per suite program
│   │   ├── results_review.py     #   Export   — consolidated governing loads
│   │   └── export_report.py      #   Export   — project JSON + CSVs + sbeam BDF + .xlsx workbook + summary report (.tex/.pdf) + export-scope toggle (D8, G8)
│   └── data/reference_aircraft.csv
├── oracle_app/                   # the ORACLE GUI — the original suite only (note 32, OG-D/OG-E)
│   ├── Oracle.py                 # entry point: its one set_page_config + nav from workflow.oracle_steps()
│   ├── form.py                   # ONE generic input renderer for all 14 pages, built from sloads.field_registry
│   ├── results.py                # ONE generic results renderer: workflow.step_modules → the report/io owners (OG-E)
│   └── labels.py                 # the spelling table both renderers head their blocks with
├── cli.py                        # `python cli.py engine project.json -o out.csv`; `--export-sbeam --export-target <t>` (every deliverable, incl. `balanced`/`mass`); `--report out.tex|out.pdf`
├── oracle.py                     # `sloads-oracle` — launches oracle_app/Oracle.py under Streamlit (OG-11)
├── tests/                        # pytest; each file also has a zero-dependency __main__ self-runner
│   ├── test_<module>.py          # one per module — Appendix A/B oracles, else a stated closure gate
│   ├── imperial_baseline.py      # renders every deliverable channel of every example (M4-20)
│   ├── fixtures_imperial/        #   ...digested and frozen: the D-21 "Imperial is unchanged" guard
│   └── fixtures_schema/          # one frozen file at the current schema; the shape tripwire lives in test_schema_guards.py
├── examples/
│   ├── ga6_normal.project.json   # Appendix A — 6-place GA single (category N); the oracle fixture
│   ├── cessna_210.project.json   # a second GA single (category N)
│   ├── atr42_100.project.json    # ATR 42-100 turboprop twin (concept mode, category C)
│   ├── dhc8_dash8.project.json   # Dash-8 twin turboprop (concept mode, category C)
│   ├── concept_heavy.project.json     # 18,000 lb concept commuter twin (concept mode, category C)
│   └── concept_regional_jet.project.json  # concept regional jet — the T-tail / lateral fixture
│   # (a dedicated Appendix B twin_turboprop.project.json is still a backlog item;
│   #  the engine module's Appendix-B turboprop case is currently inline in
│   #  tests/test_engine.py)
├── docs/                         # organised by type — see docs/00_INDEX.md
│   ├── 00_INDEX.md
│   ├── 10_standard/              # PROJECT_GUIDE.md (this file), PROGRAM_SPEC.md, process guides
│   ├── 20_theory/               # equation sources (the reference/ PDFs) + per-module citations
│   ├── 30_future/               # 00_backlog.md — open modules / decisions
│   ├── 40_history/              # 00_completed_development.md — what shipped
│   └── 50_reviews/              # dated code / process reviews
├── pyproject.toml                # build metadata, THE dependency source, ruff + pytest/coverage config
├── cspell.json                   # domain wordlist
└── README.md
```

> The `engloads` → `sloads` restructure (Phase 0) is complete; the migration
> record is in
> [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).

---

## 5. Conventions (the contract every module follows)

So that every module is copy-of-the-pattern, these are fixed once:

- **Pure calc, no I/O.** Each module exposes `run(project: Project) -> ModuleResult`. No Streamlit, no file access inside calc.
- **Read shared, write own.** A module reads upstream fields from `Project` and returns results; it must not silently recompute an upstream quantity that another module owns.
- **Results are keyed values.** Reuse the existing `LoadValue(label, value, units, quantity, key)` / `ConditionResult` types so `report.py`, the units layer and the CSV writer work unchanged for every module. A `ConditionResult` also carries `safety_factor` (default `constants.ULTIMATE_FACTOR = 1.5`, 14 CFR 25.303) — see below.
- **`LoadValue.key` is the identity; `label` is cosmetic (M4-9).** Every `LoadValue` SHALL carry a non-empty snake_case `key`, unique within its `ConditionResult`. **Downstream code matches on `key` only** — `report`, `export/sbeam_bridge.py`, the views and `tests/helpers.py`. `label` is display text and may be reworded, re-annotated or translated freely; nothing may branch on it. (Rendering it, as `report.results_to_rows` does in its `Quantity` column, is not branching on it.)
  Keys that cross a module boundary — the load-case schema's `loc_x`/`fz_vertical`/`fy_side`/`fx_thrust`/`mx_mount_torque` and the `gyro_case{n}_{myy,mzz}` sub-cases — are named once in **`sloads/load_keys.py`** and imported by both producer and consumer. Keys internal to one module are written inline at the producing site. Never derive a key from the label at runtime (`load_keys.key_from_label` exists for the one case where the "label" *is* data — `weight_estimate`'s rows, whose names are the keys of the `WT_*_FRACTIONS` tables).
  Why: before M4-9 the semantics rode on the label, so rewording a report column silently blanked it — the lookup returned `None`, the renderer wrote an empty cell, and no error was raised anywhere. `tests/test_report.py::test_relabelling_every_load_value_leaves_the_csv_intact` is the standing guard. `key` is **persisted** (the envelope slice), so adding or renaming one is a `SCHEMA_VERSION` bump plus a hop — see `sloads/migrations.py`'s `_v36_load_value_keys` and its frozen table.
- **Calc is LIMIT; ALL output is ULTIMATE.** Modules return **limit** loads (the oracle figures), so the Appendix A/B regressions are unaffected — but nothing that leaves the calc may report a bare limit load. `report.py` and `export/sbeam_bridge.py` multiply the **load** quantities (forces/moments/pressures, never geometry/weights/inertias/load factors) by the case `safety_factor` to report **ultimate = limit × 1.5**. The `ULT` marker is part of the units string (force `lbs-ULT`/`N-ULT`, moment `ft-lb-ULT`/`lb-in-ULT`/`Nm-ULT`, pressure `lb/in^2-ULT`), and **every case states its SF** (default 1.5 per 14 CFR 23.303; Part 25 equivalent 25.303). The per-case field is the hook for a future 14 CFR 23.302/25.302 / Appendix K probability-based factor (1.0–1.5); for now every case is 1.5 (incl. sudden engine stoppage). A value already at ultimate is **`ULT SF=1.0`**. See `reference/14CFR_factor_of_safety.md`.
  The factor lives **on the result**, not in the renderer (defect M4-7): `safety_factor` is a field on `ConditionResult`, `CriticalCondition` and all four distributed-load results (`WingLoadResult`, `BodyLoadResult`, `TailChordResult`, `ControlSurfaceLoadResult`), minted by the module that owns the condition and copied unchanged by everything derived from it. `report.py` and `sbeam_bridge._sf()` each read it off the object they are rendering, so the report and the exported cards can never disagree, and a case at `SF = 1.0` is never double-factored. Every deliverable states the factor it used — the `SF` column in `report.py`'s load-case rows and in the four sbeam span/chordwise CSVs (last column), and the `$ Loads are ULTIMATE (limit x SF=…)` header on every card block.
- **One CSV shape per module = load cases.** Each row is one structural load case: `ID`, `FAR §`, `Case description`, an `SF` column (always populated), application point `Loc X/Y/Z`, then the applied **ultimate** loads/moments with `-ULT` units (`lbs-ULT`/`ft-lb-ULT`/…). This is exactly the `load_cases_to_rows` pattern engloads already established — generalize it, don't reinvent per module.
  **The sbeam deck uses the *solver* unit set, and `export/coordinates.py` is the one place anything is scaled (M4-20 step 4).** Every `sbeam_bridge` writer takes `*, system=` and resolves `deliverable_units(system, Channel.SOLVER)` — in SI **N / mm / N·mm / MPa**, where every derived unit is its base units combined. No arithmetic in `sbeam_bridge` scales: card fields *and* CSV cells both go through `to_grid`/`to_force`/`to_moment`/`to_pressure`, so a span CSV cannot disagree with the deck beside it, and those four **raise** on a unit set that fails `DeliverableUnits.is_consistent` (the human set, which `deliverable_units(SI)` returns by default, is a plausible thing to pass and must never reach a deck).

  **Every deliverable carries the methods & units stamp (M4-20 step 5).** All the CSV writers *and* all five BDF writers (`force_moment_cards`, `stick_model_bdf`, and the body/tail/control-surface card sets) take `header_comment=`, which the Export page fills from `report.methods.csv_comment_block` / `bdf_comment_block`. `$` and `#` are inert to a bulk-data parser and to `strip_comment_lines`/`pandas(comment="#")` respectively, and an empty `header_comment` returns the payload byte-identical, so the stamp is free. The statement carries the bundle's `system=` and names both channels' unit sets — see `00_program_overview.md` §Units, *In-band statement*.
  **The writer owns the unit conversion, the renderer does not (M4-20 step 3).** `io.load_cases_csv(results, header_comment="", *, system=…)` calls `units.convert_results` **once** and hands the converted conditions to the unit-agnostic `load_cases_to_rows`/`results_to_rows`, which read each `LoadValue.units` string into the column header. So a new module needs no unit code to export correctly in either system — and callers pass **Imperial** results plus `system=`, never pre-converted results plus `system=` (that is a double conversion). `load_cases_csv` is the *only* `convert_results` call in `io.py`, and a test keeps it that way.
- **Units at the boundary only.** Calc stays in one internal system; `units.py` converts JSON-in and display/CSV-out. (Already implemented.) **Deliverables render in the user-selected system** — report, load-case CSV, span CSVs and the sbeam BDF, one system per bundle, each stating it in-band; the selection is the GUI toggle, persisted in the project's unit-system field and overridable headless by CLI `--units imperial|si` (default Imperial). See `00_program_overview.md`, *Deliverable units follow the user's selection*, and `SUMMARY_REPORT.md` §3.5. The GUI's Imperial/SI choice is a single sidebar control (`app_shell/sidebar.py`, shared by every front-end); it is not a per-page setting. Since **M4-20 step 2** it writes **`Project.unit_system`** (schema v38), so changing units is a project edit and shows as an unsaved change (decision D-22), and **`app_shell.components.active_system()` is the one function in the whole app layer that reads it** (D-16) — every view follows automatically through `unit_number_input`/`page`, and `st.session_state["unit_system"]` survives only as the fallback for a render that has no project yet. The field is a **preference**: it says nothing about the units of the values stored beside it. Parse it with `units.unit_system_from`, which degrades any unrecognised value to Imperial rather than raising — a junk preference must never block the load of an otherwise-valid project. Airspeed (KEAS) and altitude (ft) are aviation-standard and are never converted by this toggle. `project.json` on disk stays Imperial-only regardless of the toggle — `units.project_dict_to_display`/`project_dict_to_imperial` convert the whole project dict for the **Project JSON Editor** page only (hand-edit in your chosen units, Apply converts back to Imperial before it re-enters the session); no unit tag is ever written to the file.
- **A GUI is an entry point plus its pages, and the shell knows neither.** There
  are two front-ends over one calc package (`app/`, `oracle_app/`), sharing
  `app_shell/` and nothing else. Two rules hold the boundary, both guarded in
  `tests/test_app_shell.py`: **exactly one `st.set_page_config` per GUI entry
  point, and none anywhere else** — not in a view, not in the shell, which is
  imported by both (note 32, OG-10); and **a cross-page link names a step, never
  a path** — `components.workflow_page_link` resolves the key to the running
  GUI's own page object through `app_shell.nav`, so it cannot point at a page
  that GUI does not carry (OG-F). A third rule has no guard because it is a
  consequence of the first two: the shell contains no directory name of either
  front-end.
- **A render pass must not mutate the project** (M2-3; both GUIs since OG-F,
  `tests/test_dirty_flag.py`). Visiting a page must leave `project_to_dict`
  byte-identical, or the sidebar's unsaved-changes flag and its discard dialog
  fire on a user who typed nothing. `app/`'s views persist on an explicit
  **Apply**; the oracle GUI's generic renderer persists live but writes only
  what changed, and attaches a record it created only if the pass put something
  in it.
- **A project file is read at the current schema — or a version the hop chain
  reaches it from — or refused** (`sloads/migrations.py`, #93). This project is
  pre-production: no analysis made with an earlier build has to stay readable,
  so `SUPPORTED_FLOOR` is the oldest version a registered hop starts from
  (v55, note 36's additive-identity hop) and `migrations.migrate` raises
  `SchemaVersionError` — a `ValueError`, so it lands in the documented error
  contract — for anything below the floor, newer, or unversioned.
  The gate sits inside `io.project_from_dict`, the funnel every front-end loads
  through, so no GUI classifies versions for itself
  (guard: `tests/test_app_shell.py::test_no_gui_decides_whether_a_file_is_readable`).
  When you change a persisted dataclass, bump `SCHEMA_VERSION` — not optional
  even for a purely additive field, because the fields-hash tripwire fails on any
  persisted-shape change, which is what stops a field being added to the
  dataclass and forgotten in `io.py` — and **re-stamp the bundled examples**,
  which the guard in `tests/test_schema_guards.py` requires and which the
  Imperial digests then prove changed no delivered number. Never add legacy
  handling *inside* a reader: that is the five-shims-in-five-places pattern the
  chain replaced.
  **The migration chain is live again.** `MIGRATIONS` is a
  `{from_version: hop}` map applied in ascending order; its one hop today is
  the v55→v56 identity of note 36's additive fields (#97), with the frozen
  per-shape fixtures under `tests/fixtures_schema/`. The schema ledger — which
  version added what — is the annotated `EXPECTED_FIELDS_HASH` block in
  `tests/test_schema_guards.py` plus the comment above `SCHEMA_VERSION` in
  `sloads/models/project.py`. The twelve hops that covered v18–v55 and the v0
  bare-`EngineInput` branch retired with #93; they are recorded in
  `docs/40_history/11_completed_development_to_0.5.0.md` (M4-10).
- **Numbers in, numbers stored (the load boundary's typing contract, #76).** A
  field annotated as a container of numbers — `Vec3`/`XYPoint`, a list of
  numbers, a list of numeric tuples — is loaded as numbers. The shapes are
  derived from the dataclass annotations (`io._numeric_shape` /
  `_numeric_containers`), so a numeric container added to the model is covered
  without touching a list; `_filtered` coerces every splat, and the readers that
  name their fields explicitly (the WINGGEOM polylines, the engine vectors, the
  gear axle points) call the same coercer rather than repeating the rule. Text
  that parses is repaired with a `warnings.warn` naming the field — the load
  path's warning channel, shown as a toast by `app_shell.project_state.safe_load`
  — and text that does not parse raises `ValueError` naming the field and the
  member. This exists because a grid rendered from an object-typed column writes
  its cells back as text, so a project can be *saved* with string wing corners;
  the loader is the one boundary both GUIs and the CLI share. **Scalars are not
  in scope** — the class is grid-writable containers, and a blanket coercion
  would have to reason about `Optional`, enums and bools.
- **Deliverables state their own basis.** Anything that leaves the tool as a file
  (CSV, BDF, zip, workbook, report) carries the methods & limitations statement
  in band — `report.csv_comment_block` (`#`) or `report.bdf_comment_block` (`$`),
  both built from the single source in `sloads/report/methods.py` (Step G8.3). An
  on-page caption does not travel with a downloaded file. A **new export channel
  is not complete until it is stamped**, and `tests/test_methods_stamp.py` is the
  guard. Any code that *reads* an exported CSV must skip the `#` block
  (`report.strip_comment_lines`, or `pandas.read_csv(..., comment="#")`).
- **The summary report is a render channel, not a calc (Step G8).**
  `sloads/report/content.py` turns a `Project` plus its module results into a
  `ReportDocument`; `latex.py` turns that into `.tex`; `plots_tex.py` emits the
  three figures as pgfplots source. All three are **pure** — no filesystem, no
  subprocess, no clock (the generation timestamp is a caller argument, or two
  renders of one project would not be byte-identical). The report **recomputes
  nothing**: its governing tables are `report.governing_loads_table`'s output and
  its distributions come from `report.content.component_loads()`, the one builder
  the Export page uses for the CSV/BDF channels too — so a bundle's document and
  its data files cannot describe different numbers. Content rules live in
  [`SUMMARY_REPORT.md`](SUMMARY_REPORT.md), not here.
- **⚠ `sloads/export/pdf.py` is the documented I/O exemption.** Compiling `.tex`
  needs a subprocess and a temp directory, which the "calc never does I/O" rule
  forbids. It is an *export-side* helper on the same footing as `io.py`: it holds
  no math, produces no engineering number, and **nothing in `sloads/report/`
  imports it** — the pure renderer never touches the filesystem. It also never
  raises: a missing engine or a failed compile returns a `CompileResult` carrying
  the log, because decision G8-1 makes the `.tex` the deliverable and the PDF
  best-effort. Engine order `tectonic` → `latexmk` → `pdflatex`, overridden by
  the `SLOADS_TEX_ENGINE` environment variable.
- **Constants centralized** in `sloads/constants.py` so Decision 3 (and any future "go back to exact") is a one-file change.
- **Call `sync_geometry_derived(project)` first inside `run()`** — not in the
  caller, not at import. Any module that reads geometry-derived quantities
  (MAC/span/areas/stations resolved from the Step-G1 single-source geometry)
  opens `run()`/its build function with it, so the module is correct whether it
  is reached through the registry, the CLI, a view, or a test that hand-builds a
  `Project`. Seven sites do this today (`body_loads`, `wing_inertia`, `select`,
  `net_loads`, `flight_envelope` ×2, `balloads`, plus `io.py` on load); it was
  convention-by-imitation until M4-12b wrote it down. It is idempotent — calling
  it twice is free, forgetting it is a silent wrong answer.
- **Public surface is explicit; the app layer never imports an underscored name
  from `sloads`** (M4-12b / D-14). A leading underscore means module-private, and
  cross-module use of one is a defect, not a shortcut — the fix is to promote the
  symbol (drop the underscore, or give it a clearer public name where a bare
  strip would read badly) and list it in that module's `__all__`. The four
  modules with a promoted surface carry an `__all__` block:
  `wing_geometry` (`interp_x`), `flight_envelope` (`design_inputs`,
  `density_ratio`), `structural_speeds` (`maneuver_load_factors`) and `select`
  (`default_envelope`, `default_critical`, `vn_points`, `vn_by_case`,
  `elevator_load`, `flaps_by_config_name`, `htail_balance`,
  `HtailBalance`). There is deliberately **no `sloads/api.py` facade** — per-module
  `__all__` is the contract.
- **Cross-module results are typed, not stringly-keyed.** A helper whose result
  crosses a module boundary returns a `NamedTuple` (or dataclass) with named
  fields, never a `Dict[str, float]` whose keys are the real API — a typo in a
  key is a runtime `KeyError` at best and a silent wrong branch at worst.
  `select.htail_balance` → `HtailBalance(lt25, lt50, at, delta, lt, cp)` is the
  worked example; attribute names are lowercase Python, with the manual's Ch 9
  symbols (LT25, AT, DELTA, CP…) recorded in the class docstring.
- **Do not add property proxies to `Project`.** `Project.tail_loads` /
  `.vtail_loads` proxy `geometry.empennage.htail/.vtail` and are the pattern *not*
  to copy: they are invisible to `dataclasses.fields`/`asdict`/`replace`, and
  their setters silently no-op when assigning `None` to a project with no
  geometry. The warning block sits beside them in `models/project.py`; their
  retirement is backlog **M4-10**. New slices are real dataclass fields.
- **Each module has a manual example test** (Appendix A and/or B) under `tests/`.
- **Structured load-case IDs (Step D1).** Every delivered case carries a
  `CaseRef` (`case_id`, `component`, `condition`, `cg`, `speed_kt`,
  `altitude_ft`, `far_reference`) — see `docs/10_standard/PROGRAM_SPEC.md`
  "Structured load-case IDs" for the full contract. In short, for a **new**
  module: mint with a fresh `sloads.case_ids.CaseIdAllocator()` inside your
  own build function, in whatever order you already emit results (no
  reshuffling to get a "canonical" order — the existing order *is* canonical
  once it's fixed); if your module is the first to name a physical case (not
  reading someone else's `CriticalCondition`/`WingLoadCase`), pick one of the
  six `component` keys in `case_ids.COMPONENT_PREFIX` — never invent a new
  prefix for a control surface, fold it into its host; if you mint into a
  prefix another module also mints into, claim a disjoint numeric sub-band in
  `case_ids.py` (two independent counters over the same range collide, not
  just diverge — see the wing-gap note in `PROGRAM_SPEC.md`) and `seed()` your
  allocator to it.

- **Imperial output is frozen (M4-20, decision D-21).** `tests/imperial_baseline.py` renders every deliverable channel (load-case CSVs, text reports, all five sbeam CSVs, all five decks, the case index) for all six examples and digests each into `tests/fixtures_imperial/digests.json` — 256 channels. Any change to an Imperial byte fails `test_imperial_output_matches_the_frozen_baseline`, which names the drifted channel. Regenerate with `.venv/bin/python tests/imperial_baseline.py` **only** when the change to Imperial output is intended, and say so in `CHANGELOG.md`: a regeneration is a claim, not a cleanup.

---

## 6. Validation strategy (given "modernize the math")

**Reference 1** (McMaster's theory manual) prints full example loads reports for
two airplanes in its Appendix A/B:

- **Appendix A** — 6-place general-aviation single (the `engloads` reciprocating example lives here). Sample data set `M2002576` / `WTENV36`-series.
- **Appendix B** — 10-place twin turboprop (swept wing, altitudes to 50,000 ft, gyroscopic engine loads, one-engine-out — the `engloads` turboprop example lives here). Sample data set `BB*` (`BBFLTLDR`, `BBSELECT`, `PHAABB36`, `ACCELROL`, `TORBB36`).

> ✅ **Oracle is in hand.** Reference 1 is `FAR23Loads_Code.pdf` (371 pp) in the
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
5. **Test-suite architecture (M4-12a).** Shared test code lives in two support
   modules under `tests/`, and **a test module never imports another test
   module** — `test_engine.py` was a de-facto library for seven other files,
   which coupled unrelated suites to its import side effects.
   - `tests/helpers.py` — the **key** lookups `value_of` (float), `load_value`
     (`LoadValue`, for units/quantity assertions) and `values_by_key` (flatten
     all). Each accepts a `ModuleResult`, a `ConditionResult` or a nested list
     of either, and all three match `LoadValue.key`, never the display label
     (M4-9). **Do not re-roll a local `_value`** — consolidating these was what
     made re-pointing ~150 assertions one edit to three functions.
     Also home to `apply_button(at, form_key)` and `parse_cards`.
     Asserting on a *label* is correct in exactly one situation: when the label
     itself is the subject (`test_net_loads.py` checks that every reported root
     torsion names its axis; `test_weight_envelope.py` checks the ballast marker
     rows explain *why* there is no ballast).
   - `tests/fixtures.py` — shared input builders (`io520bb`, `turboprop`).
     Plain functions, not pytest fixtures, so the `__main__` self-runners can
     import them.
   - **AppTest button selection is by form key, never by position or label.**
     `at.button` flattens every form's submit button into one list, so an index
     silently rebinds when a view gains, loses or reorders a form and the test
     passes while asserting something else. Use `helpers.apply_button(at,
     "<form_key>")`, which asserts it found exactly one match. Every
     `st.form(...)` in `app/views/` therefore carries a unique string key.
   - A view-driving self-runner must put the **repo root** on `sys.path` itself
     so the view's `app_shell` imports resolve; `conftest.py` only does that
     under pytest. (`app/` itself is not on the path: since note 32 step OG-B
     the shell is a real package, not bare modules on Streamlit's implicit
     entrypoint path.)
6. **Concept-mode identity guard.** The C-1 invariant ("concept mode reduces exactly to FAR23 on GA inputs") is asserted *through the concept branch itself* by `tests/test_concept.py::test_concept_reduces_to_far23_on_ga_inputs`: `ga6_normal` is run twice through `run_all_modules` — once as Normal, once flipped to `category="C"` with the FAR23-computed load factors — and every module's every `LoadValue` must match at `rel_tol=1e-3` (only the appended concept `note` may differ). Concept mode above the 12,500 lb oracle band has no printed figure, so it is instead validated by physics-closure checks (`test_concept_closure.py`).

---

## 7. Roadmap (dependency-ordered phases)

Each phase ends with: the module(s) merged, a `tests/test_<module>.py` passing
against Appendix A/B, a GUI page, and the project JSON schema extended.

> **Phases 0–2 are complete, and the original Phases 3–4 were re-sequenced by the
> Phase-C plan** (vertical-slice-first; concept-mode generalization) — see
> [`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md).
> All 22 suite programs (Steps C0–C11) are now ported; the live backlog is
> deferred refinements and open decisions. The phase descriptions below are the
> historical roadmap that produced the present suite.

**Phase 0 — Restructure** ✅ (no new physics)
`engloads` → `sloads` package + `app/` multipage + `cli.py` + `Project` model +
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
Steps C1/C2/C6; complete)
`TAU` ✅ → `AIRLOADS` ✅ / `AIRLOAD4` ✅ (C7) → `FLTLOADS` ✅ (incl. balancing tail
loads) → `SELECT` ✅ (rational critical wing/tail/fuselage loads) → `BALLOADS` ✅
(C11, off-pipeline verification). The analytical heart; produces the critical-load
set everything downstream is sized to.

**Phase 4 — Component loads** (re-sequenced into Phase-C Steps C3/C7–C10)
`WINGINER` ✅, `NETLOADS` ✅, `ENGLOADS` ✅; `TAILDIST` (C7), `AILERON`/`FLAPLOAD`/
`TABLOADS` (C8), `ONENGOUT` (C9), `LGFACTOR`/`LANDLOAD` (C10).

The **vertical-slice** value path (`WTESTIMA → WINGGEOM → STRSPEED → FLTLOADS →
SELECT → NETLOADS` end-to-end, plus the sbeam export) is the path the Phase-C plan
actually took, and it is now complete.

---

## 8. Open user decisions (for later phases, not blocking Phase 0)

1. **Graphics.** The original has a separate graphics program (weight envelope, V-n diagram, spanwise plots). Replicate these as Streamlit charts (Altair/Matplotlib)? Default: yes, per module, deferred to that module's phase.
2. **Multi-engine / twin layout.** ✅ **RESOLVED (Phase 2): first-class now.** `Project.engines: List[EngineInput]` + `EngineLayout` (`SINGLE_NOSE`/`TWIN_WING`/`QUAD_WING`, symmetric). The engine module loops over every engine; full one-engine-out *loads* are still built at `ONENGOUT`. The engine-mount **GUI** now exposes this: a sidebar layout selector drives the engine count and an engine selector picks which engine is assessed, with per-engine inputs held canonically in `st.session_state["engine_inputs"]` (see PROGRAM_SPEC § ENGLOADS).
   - **Supplemental FAR 25 cases (concept).** `Project.include_far25` (default off, optional `EngineInput.max_accel_torque`) appends only the **non-duplicative** 14 CFR 25.361/25.371 engine cases (turbopropeller only) on top of the oracle-locked FAR 23 set — additive by construction, FAR 23 output unchanged. The FAR 25 torque cases 25.361(a)(1)(i)/(ii)/(iii) were **removed** as exact duplicates of the corrected 23.361(a)(1)/(a)(2)/(a)(3) (post AC 23-19A); what remains is `(a)(3)(i)` stoppage @1g, `(a)(3)(ii)` max-accel torque (no FAR 23 analog), and 25.371 gyro on the A2 load factor. Kept opt-in (not unconditional) to preserve the Appendix B oracle (6 conditions, 2.5g gyro). Sourced from `reference/14CFR_Part25_engine_torque.md`, formula-closure tested; 25.371 uses the fixed FAR 23.371(b) rates as a conservative concept stand-in. See PROGRAM_SPEC § ENGLOADS.
3. **Project JSON versioning.** Add a `schema_version` to `project.json` from day one so old saves migrate cleanly as the schema grows? Default: yes.
4. **Standalone vs project-only inputs.** Hybrid allows a module to run from a partial JSON (just its own slice). Confirm we want to maintain per-module example JSONs in addition to the two full-airplane projects. Default: full projects are canonical; per-module slices are derived for tests.
5. **CSV vs combined workbook.** ✅ **RESOLVED (Phase D, Step D8.2, 2026-07-09).** Both: the Export page offers the `.zip` of per-module CSVs *and* a single multi-sheet `.xlsx` workbook (`sloads/export/workbook.py`, `openpyxl` dependency) as a sibling alternative — one tab per module/component plus the case index, BDF card text excluded (not tabular).

---

## 9. Getting started

```bash
pip install -e '.[dev]'          # editable install + dev tools (pytest, ruff)
streamlit run app/Home.py        # the multi-page UI
python cli.py engine examples/ga6_normal.project.json -o engine_loads.csv
pytest                           # the green-build gate
ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/ scripts/  # lint
mypy                             # type check (sloads/)
```

See [`PROGRAM_SPEC.md`](PROGRAM_SPEC.md) for the per-module specification.

### The `solver` extra and the sbeam pin

The round-trip gate (step 2) solves the exported decks in the **real sbeam**, so
it needs that repository installed. It is a separate extra, and `dev` does not
pull it in — `pip install -e '.[dev]'` stays `scipy`-free and fast for everyone
not working at the export boundary:

```bash
pip install -e '.[solver]'       # the pinned sbeam, for the round-trip gate
pytest -m roundtrip              # just that gate (skips if sbeam is absent)
```

Without sbeam those tests **skip**; with `SLOADS_REQUIRE_SBEAM=1` set (as the
`sbeam-roundtrip` CI job does) a missing sbeam is a **failure** instead, so a
broken install cannot report green.

**The pin is a claim, not a convenience.** `pyproject.toml` pins sbeam by commit
SHA. Bumping it asserts that the new sbeam still honours the deck contract — the
same posture `tests/imperial_baseline.py` takes about digest regeneration — so
the bump is a deliberate act with a recorded result:

1. run the weekly `sbeam drift` workflow on demand (`workflow_dispatch`) to see
   what `main` does with the current gate, or install the candidate SHA locally;
2. change the SHA in `pyproject.toml`, `pip install -e '.[dev,solver]'`;
3. `pytest -m roundtrip` must be green **before** the bump is committed;
4. record the bump in `CHANGELOG.md` with the sbeam commit subject.

A red drift run is a notification that the pin needs a look — never a merge
block. Design note:
[`../40_history/17_sbeam_roundtrip_ci_harness_plan.md`](../40_history/17_sbeam_roundtrip_ci_harness_plan.md).
