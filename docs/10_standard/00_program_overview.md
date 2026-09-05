# sloads — Program Code Standard & Developer Guide

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

**The package tree has one owner:** [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) §4,
guarded file-for-file by `tests/test_package_layout.py`. It used to be drawn
here as well, and the second copy is what rotted (R6-D5, 2026-08-15) — so this
section states the *shape* and links for the listing.

- **`sloads/`** — the shared, pure-calc package: `constants.py`, `units.py`, the
  `models/` schema, `io.py`/`migrations.py`, `registry.py`, `workflow.py` (the
  nav SSOT), the cross-cutting single-source owners (`safety_factors.py`,
  `cg_cases.py`, `mass_distribution.py`, `case_ids.py`, `rigid_body.py`,
  `gear_loads.py`, …), `report/` (rendering + the summary document), `export/`
  (bridges to external tools — renderers, **not** registered modules) and
  `modules/` (one file per suite program plus the modern additions, each
  self-registering on import).
- **`app/`** — the multi-page Streamlit UI: `Home.py` builds the nav from
  `sloads/workflow.py`; `views/` holds one view per workflow step.
- **`cli.py`** — the argparse front-end (`sloads` console script);
  **`tests/`** — pytest, one test file per module; **`examples/`** — the shipped
  `project.json` fixtures.

Data flow for one run: `project.json` → `io.load_project` → `Project` →
`registry.get(name)(project)` → `ModuleResult` → `report`/`io` renders text or the
load-case CSV. The GUI builds the `Project` from widgets; everything downstream is
identical.

The GUI is organised as a six-section workflow — **Start → Airplane → Envelopes &
Critical Conditions → Analysis → Loads Plots → Export** (Phase D; see
`docs/40_history/05_phase_d_gui_workflow_plan.md`) — built explicitly with `st.navigation`
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

- **Python 3.10+**, with `from __future__ import annotations` at the top of each
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
- **Key the values; the label is cosmetic.** Every `LoadValue` carries a stable
  snake_case `key`, unique within its `ConditionResult`, and that is the only
  thing `report`, the sbeam bridge, the views and the tests match on. Cross-module
  keys live in `sloads/load_keys.py`. Rewording a `label` must never change a
  number, a column or a row — before M4-9 it silently blanked the cell. See
  `PROJECT_GUIDE.md` §5.
- **Self-register** at import (`register("name", run)`) and add the import to
  `sloads/modules/__init__.py`.
- **Never recompute another module's quantity** — read it from the `Project`
  slice that owns it.
- **Constants centralised** in `constants.py`; no bare magic numbers in calc.
- **Imperial in, selected units out.** Calc always runs in the Imperial units of
  the original program; `units.py` converts at the boundary only, into whichever
  system the user selected (see *Units* below).

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
| A bounded iterative solve exhausts its trips with the iterate still moving | `raise SolverFailure` (a `ValueError` subclass, `convergence.py`) quoting the trip bound and the case — a load is never reported from a solve that did not close (#33). A non-converged solve that has reached a **fixed point** is a third outcome, *clamped*: it returns its iterate with the state attached, because a solver with no lever left is sometimes a real flight condition (`CONVENTIONS.md` §7) |
| A project file is not at the current `SCHEMA_VERSION` (older, newer or unversioned) | `raise SchemaVersionError` (a `ValueError` subclass, `migrations.py`) naming both versions — pre-production there is no migration, so a file this build cannot read is refused rather than reshaped (#93). Raised once, inside `io.project_from_dict`, so every front-end refuses identically |
| Unknown module name requested | `raise KeyError` listing the registered modules (`registry.py:30`) |
| An optional input is omitted (e.g. measured polar inertia) | Approximate from geometry where the manual does; never emit `nan` as a reported load value |

The "missing slice → `MissingInputError` → skipped by `run_all_modules`" idiom is
load-bearing: it is how a module signals "not my turn" on a project that doesn't
carry its inputs yet. A new module SHALL follow it (raising `MissingInputError` at
its entry guards) rather than returning an empty result. A plain `ValueError` is
reserved for present-but-invalid data and genuine defects, which must remain visible
— before M2R-8 the registry swallowed *every* `ValueError`, hiding those defects.

**No silent defaults at a read (CH-2, 2026-08-16).** `getattr(obj, name, default)`
is the shape that hides a missing attribute behind a quiet fallback; a value the
exporters read is a declared field on a typed result and is read as one, an
optional is `Optional` and tested for `None`, and a lookup by name is an explicit
map that refuses an unknown key. Guard:
`tests/test_sbeam_bridge.py::test_the_export_package_takes_no_silent_defaults`
(AST, `sloads/export/`); a two-argument `getattr` — a dynamic attribute *name*, no
default — is not this class.

---

## Units

| Quantity | Imperial (canonical) | SI (presentation) |
|----------|----------------------|-------------------|
| Weight | lb | kg |
| Length | in | mm |
| Torque | ft-lb | N·m |
| Power | hp | kW |
| Inertia | slug-ft² | kg·m² |

Calc always runs in Imperial; `units.py` converts at the boundary. Saved
`project.json` values are always canonical Imperial.

### Deliverable units follow the user's selection (mandatory)

**Every deliverable SHALL be rendered in the unit system the user selected**, not
in the calc's internal Imperial units:

- **Where the selection comes from.** GUI: the sidebar **Imperial / SI** toggle
  (`st.session_state["unit_system"]`). Headless: the persisted `Project`
  unit-system field, overridden per-run by the CLI `--units imperial|si` flag.
  Default **Imperial**, so an unspecified run is byte-identical to today's output.
- **What it governs.** The whole export bundle in one system — the summary report,
  the load-case CSV, the span-load CSVs, and the sbeam `FORCE`/`MOMENT` bulk-data
  cards. Two files of one bundle in different systems is a `[CRITICAL]` finding.
- **Two channels, one system (M4-20 D-19).** *Which* units a system means depends
  on the channel the file belongs to, because a solver deck is only correct in a
  **dimensionally consistent** set:

  | Channel | Files | Imperial | SI |
  |---|---|---|---|
  | **Human** | report, load-case CSV, case index, text report, workbook | lb, in, lb-in, ft-lb, lb/in² | N, mm, **N·m**, **kPa** |
  | **Solver** | sbeam span/chordwise CSVs, all `.bdf` | lb, in, lb-in, lb/in² | N, mm, **N·mm**, **MPa** |

  The solver set's derived units are its base units combined — `N·mm = N × mm`
  and `MPa = N / mm²` — which is the whole point: with GRID coordinates in mm and
  forces in N, an `N·m` moment is wrong by 1000× in a deck that parses cleanly
  and sizes structure, and a `kPa` stress is wrong by 1000× the same way. Resolve the set **once per
  bundle** with `units.deliverable_units(system, channel)` and pass it to every
  writer — that is what makes "one system per bundle" structural rather than a
  convention. Imperial is the all-1.0 identity set, so no writer needs an
  `if system == IMPERIAL` branch.
- **In-band statement.** Every deliverable states its unit system in itself: the
  report's title page and manifest, a header comment in the BDF, a header row or
  column-header unit in a CSV. Units are never left to be inferred from magnitude.
  The carrier is the **methods & limitations block** (`report/methods.py`), which
  is built once per bundle and wrapped per channel — so `methods_statement(project,
  system=…)`'s `UNITS:` paragraph reaches every CSV as `# UNITS: …` and every BDF
  as `$ UNITS: …` from one place. The statement is *bundle*-wide, not per-file: one
  stamp lands on both the human-readable CSVs and the sbeam decks, so in SI it
  names **both** sets (`N·m, kPa` and `N·mm, MPa`) and says which files use which.
  The `.xlsx` workbook has no comment rows and carries a `Units` row on its
  *Project* sheet instead.
- **Markers convert with the unit** — `N-ULT` / `Nm-ULT` / `kPa-ULT` in SI, exactly
  as `lbs-ULT` / `ft-lb-ULT` / `lb-in-ULT` / `lb/in²-ULT` in Imperial. No dual
  display (one system, no parenthetical conversions).
- **Aviation-standard exception.** Airspeed (KEAS) and altitude (ft) are held in
  aviation units in *both* systems and are never converted. Which fields those
  are is **declared**, not implied by absence from the conversion table
  (`units.AVIATION_STANDARD`): *stated in KEAS* and *dimensionless* are different
  answers, and a reader — or a form renderer — needs to be able to tell them
  apart from a field the table simply forgot.
- **Calc and storage are unaffected.** Conversion happens once, at the
  render/export boundary. The calc stays Imperial and oracle-locked; the persisted
  unit-system field is a *preference*, never a claim about the units of the stored
  values.

The standard for the summary report's application of this rule is
[`SUMMARY_REPORT.md`](SUMMARY_REPORT.md) §3.5.

### Loads are LIMIT, and every artifact says so (mandatory)

**Every load sloads delivers is LIMIT** — every force/moment/pressure in every
deliverable (the `report.py` tables/text, the load-case CSV, both reports, the
sbeam export, the Review/Export pages) is the calc's own value. The 14 CFR 23.303
safety factor is **stated per case and applied nowhere**, including in the
exported deck; the sizing analysis applies it (design note 49 OR-116/OR-117).
**No path in `sloads/` may multiply a load by a safety factor** — G-OR-71 scans
the tree, and G-OR-73/G-OR-74 hold every deck, every rendered document and
every on-screen GUI string to stating the factor they did not apply. The `-ULT` marker survives only on a load
the regulation prescribes already ultimate (23.367(a)(2), 23.561(b)).

Load quantities carry **plain units** (`lbs`, `ft-lb`, `lb-in`, `lb/in²`; `N`,
`Nm`, `Nmm`, `kPa`). The `-ULT`-marked forms below are reserved for the two
already-ultimate families, and are rare enough to be conspicuous — which is the
whole purpose of a marker:

| Load quantity | Imperial (canonical) | SI (presentation) |
|---------------|----------------------|-------------------|
| Force | lbs-ULT | N-ULT |
| Moment / torque | ft-lb-ULT, lb-in-ULT | Nm-ULT (`Nmm-ULT` in an sbeam deck) |
| Design pressure | lb/in²-ULT (psi-ULT) | kPa-ULT |

The `-ULT` marker is treated as **part of the units string** (like lb vs. N).
Every load case carries its **safety factor** (the `SF` column / an `SF=` marker),
default **1.5 per 14 CFR 23.303** (Part 25 equivalent: 25.303). That factor is not
decided at the case: it is read from the **governing safety-factor table**
(`sloads/safety_factors.py`, M4-8 / G-11), one row per condition family, which the
report states as a numbered section and the bundle ships as
`<project>_safety_factors.csv`. A quantity already
at ultimate — 23.367(a)(2) sudden engine stoppage and 23.561(b) emergency-landing
inertia, the only ultimate loads left in the project — is `ULT SF=1.0` and asks for
nothing further. Non-load quantities (weights, lengths, inertias, areas, speeds,
angles, dimensionless load factors) take no factor at all and carry plain units
with no `-ULT` suffix.

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
  load-case CSV. `--export-sbeam PREFIX --export-target <t>` writes the sbeam
  deck set — **every** deliverable is reachable headless (`wing`, `body`, `tail`,
  `htail-span`, `vtail-span`, `control`, `balanced`, `mass`; see
  `PROGRAM_SPEC.md` §sbeam bridge) — and `--report PATH` renders the Step-G8
  summary report (`.tex` always; a `.pdf` path also compiles it when a TeX engine
  is available, `--generated` supplies the title-page timestamp). Output units
  follow `--units imperial|si`. Every file written carries the G8.3 methods &
  limitations stamp; every failure is one `error:` line on stderr with status 1.
- **Library:** `import sloads` — `registry.get(name)(project)` over a `Project`
  you build yourself.

---

## Dependency requirements

**`pyproject.toml` is the single owner of every dependency and every version
floor; this page names none of them.** Runtime requirements are
`[project.dependencies]`, the supported developer set is
`[project.optional-dependencies].dev` (it pins `ruff` and `mypy` to the versions
the pre-commit hooks run, so hook and CI agree). Install with
`pip install -e '.[dev]'`; add `,solver` for the sbeam round-trip gate. A floor
copied here drifts from the one that is enforced — this page carried a
`streamlit` floor six minor versions below the real one (2026-08-20 review,
CR-D-5); the reason for each floor is a comment beside it there (the
`streamlit` one has since moved from `st.navigation(expanded=…)` to the layout
parameter that replaced `use_container_width`). The doc-currency
guard now treats a version specifier beside a dependency name as a volatile
literal, so the class cannot come back — including in a sentence like this one,
which is why the numbers here are words.

**Ceiling policy: there is deliberately no upper bound on a runtime dependency,
and the reason is written beside the requirement it applies to.** The bet is
that CI installs the runtime set unpinned on every run, so an upstream release
that removes an API this code calls fails here before it reaches an installed
user — which is why a pinned or constrained CI install is itself a guarded
condition (`tests/test_ci_conformance.py`), and why a floor exists only where a
named API needs it (`tests/test_app_shell.py` compares the declared Streamlit
floor against the layout parameter both front-ends pass).

---

## Testing & coverage

- **One manual-example test per module** under `tests/`, asserting `run(project)`
  against the Appendix A (6-place GA single, p131) and/or Appendix B (10-place
  twin turboprop, p251) figures within **±0.1%** (`rel_tol=1e-3`); exact equality
  only for integer/dimensionless quantities.
- `ruff check sloads/ cli.py oracle.py app/ app_shell/ oracle_app/ scripts/` clean, `mypy` clean and `pytest` passing are the
  merge gate. **The CI matrix is asymmetric and `.github/workflows/ci.yml` is its
  authority** (guard: `tests/test_ci_conformance.py`): every pull request and every
  push to a `dev/**` milestone branch runs ruff + pytest on **3.12 only**, with `mypy`
  and `sbeam-roundtrip (3.12)` in their own jobs — that trio is the required-check set
  on `main`. The **3.10 / 3.11 compatibility legs, `sbeam-roundtrip (3.11)` and the
  coverage-instrumented leg run on the push to `main` only**, i.e. on the milestone
  merge, and are fixed forward (`DEVELOPMENT_PROCESS.md` §0): a change that breaks 3.10
  merges green by design. See §Static typing & lint below for what each checks.
- **Parallel by default (CH-1).** `addopts` in `pyproject.toml` carries
  `-n auto` (`pytest-xdist`), so every `pytest` invocation — local and CI —
  runs across all cores. To debug with `-s`/pdb, disable workers with
  `-p no:xdist` (or `-n 0`).
- **Coverage floor.** Coverage is **CI's concern**: the `test` job passes
  `--cov=sloads --cov-report=term-missing --cov-fail-under=80` explicitly
  (`.github/workflows/ci.yml`), so coverage cannot silently regress while local
  runs skip the instrumentation cost. **On one leg, on the push to `main` only**
  (the 3.12 leg, via the matrix `include`; item 8, 2026-08-16; moved off the PR
  leg 2026-08-22, where instrumentation had grown the run past 27 minutes): the floor is one number and needs
  measuring once, and branch instrumentation was what made every leg a
  ten-minute job — the 3.10/3.11 legs are the compatibility claim and run
  uninstrumented. Opt in locally with `--cov=sloads`; the `[tool.coverage.*]`
  tables in `pyproject.toml` still configure branch mode and reporting. This
  floor is a **ratchet**: raise it toward 85% as `report.py` and `constants.py`
  gain tests, and tighten to a per-module gate on `sloads/modules/` (the load
  math) as the suite grows.
- **Suite runtime is a measured thing, not a tier.** `--durations=15` runs on
  every CI leg and **that output, not this page, is the number** — a figure in
  prose here rots (the 2026-08-20 review, CR-D-6: this bullet still claimed "the
  suite in the tens of seconds and no test over ten" against a measured parallel
  suite several times that, with the revisit threshold below already crossed and
  nothing filed). A test that dominates the parallel critical path is fixed (the
  2026-08-16 case: one sweep re-ran the whole pipeline once per (example,
  module) key — 40 s of a 59 s suite — for an assertion that needs one run per
  example). There is deliberately **no `slow` marker**: a fast subset would add a
  second thing to keep in step, and the measured shape has been one or two
  whole-pipeline-per-assertion tests on the critical path, which is a fix and not
  a marker. **The revisit threshold has tripped and is owned:** the split of the
  whole-pipeline-per-assertion tests is a backlog row, not a standing claim on
  this page. Read `--durations` (or `.pre-commit-config.yaml`, which records the
  last measurement beside the hook timings) before asserting a runtime anywhere.
- **Git hooks (opt-in).** `.pre-commit-config.yaml` runs ruff + mypy on
  commit and the whole suite on push, all as *local* hooks on the venv's own
  tools, so hook and CI use the same pinned `ruff`/`mypy` versions
  (`[project.optional-dependencies] dev` — the pin exists because a newer ruff
  on the runner than on the desk turned a green local run into a red PR).
  Install once per clone: `.venv/bin/pre-commit install --hook-type pre-commit
  --hook-type pre-push`. The hook is a convenience; CI is the gate.
- A zero-dependency fallback runner exists (`python tests/test_engine.py`) for
  environments without pytest.

---

## Documentation currency (mandatory)

**A standard doc never states a number that describes the code's current state.**
Schema version, test count, coverage percentage, "currently N", "version is now
X" — each has an owner (`SCHEMA_VERSION` in `sloads/models/project.py`, CI, the
generated `DATA_DICTIONARY.md`, the release baseline) and the doc **points at
the owner** instead of copying the value. Provenance is not volatile:
"added at schema v46" is a fact that never rots and is written that way —
`schema vN`, never `SCHEMA_VERSION` beside a number. Anything that *describes*
code (the package tree, the module list, the spec sections, the nav, the data
dictionary) is generated or drift-guarded; a doc file exists only with a
`docs/00_INDEX.md` row. Scope: `README.md`, `CLAUDE.md`, `docs/00_INDEX.md`,
`docs/10_standard/`, `docs/20_theory/`; plan notes, history and reviews are
dated statements and are exempt. Guard: `tests/test_doc_currency.py` (both
halves: literal patterns, and INDEX ↔ tree both ways). Rationale: R6-D1…D8
and this file's own stale schema line found 2026-08-16 (37 versions behind) —
prose that copies a value drifts the moment the value moves.

## Static typing & lint (design note 27, 2026-08-16)

**mypy** is a merge gate over `sloads/` (never `app/` or `tests/`), zero errors in
default mode; `pyproject.toml [tool.mypy]` is the owner. Strictness **ratchets per
package** through `[[tool.mypy.overrides]]` -- stage 1 (shipped) puts
`disallow_untyped_defs`/`disallow_incomplete_defs`/`check_untyped_defs` on the
single-source owners (`models/`, `safety_factors`, `units`, `case_ids`,
`load_keys`, `constants`, `registry`); later stages add `export/` then `modules/`.
Rules of engagement: **narrow, never silence** -- no `# type: ignore` except for
a stub-less third-party import (with the error code and a reason), no widening
to `Any`, `typing.cast` only with a provable invariant and a one-line reason.
When the checker flags an `Optional` dereference that is genuinely reachable,
the fix is the error contract above (`MissingInputError` for an absent slice,
`ValueError` for present-but-invalid input), never a bare guard that changes a
number. The checker is the code owner of the "no `None` reaches an attribute"
convention (rule 3 in `CLAUDE.md`); the CI job is its drift guard.

**`cspell.json` is an editor convenience, not a gate.** No CI step and no hook
runs it, and the prose rule that used to say "new domain terms → `cspell.json`"
has been removed from `CLAUDE.md` rather than given one (2026-08-20 review,
CR-D-11; rule 3 forbids a convention with no owner, and the honest resolution of
an ungated rule is to drop the rule). Keep the word list current if your editor
uses it; nothing fails if you do not.

**ruff** runs `E F W B SIM PLE PLW ARG RUF I C4` (`pyproject.toml [tool.ruff.lint]`
is the owner, with each ignore explained in place). `UP` (pyupgrade) stays off
as a deliberate churn decision -- its findings are style, not defects; `N`
stays off for the ported single-letter FAR names (`E741`); `PERF` is off as
performance-only. A `# noqa` carries its rule and a reason (`-- ...`); an
unused-argument `noqa` marks a *signature contract* (callback protocol, uniform
tab signature, ported BASIC input list), never a forgotten parameter.

## Version & phase

Semantic versioning in `pyproject.toml`; `project.json` carries its own
`schema_version` (`SCHEMA_VERSION` in `sloads/models/project.py` — the constant is
the current value; not repeated here), bumped when the on-disk shape changes. **Status:** Phases 0–2 and Phase-C Steps **C0–C11** are complete — all 22
of Reference 1's programs are ported, plus the modern `configuration` and
`body_loads` modules. The remaining deferred refinements and open decisions
are in [`../30_future/00_backlog.md`](../30_future/00_backlog.md); the
architectural roadmap is in [`PROJECT_GUIDE.md §7`](PROJECT_GUIDE.md) and the
Phase-C narrative in
[`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md).
Releases follow [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md); reviews follow
[`CODE_REVIEW_PROCESS.md`](CODE_REVIEW_PROCESS.md).
