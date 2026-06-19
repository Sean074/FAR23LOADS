# Changelog

All notable changes to FAR 23 LOADS are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- **First-class multi-engine layout** — the `Project` engine slice is now a list
  (`engines: List[EngineInput]`) plus an `EngineLayout` enum constrained to the
  modelled layouts (`SINGLE_NOSE` = 1 nose, `TWIN_WING` = 2 wing, `QUAD_WING` =
  4 wing, symmetric). `Project.__post_init__` validates the engine count against
  the layout; a read-only `Project.engine` property returns the first engine so
  single-engine call sites are unchanged. `io.py` reads either the new
  `"engines"`/`"engine_layout"` JSON or the legacy single `"engine"` key, and the
  engine module's `run(project)` loops over every engine (single-engine output is
  byte-identical; multi-engine prefixes each condition with the engine
  designation). Resolves PROJECT_GUIDE open decision #2 ("model the field now").
  Full one-engine-out *loads* still land at `ONENGOUT`.
- **Phase 1 mass properties** — two modules ported against Appendix A:
  `weight_estimate` (WTESTIMA, statistical weight estimate; reproduces the p133
  figures exactly) and `weight_onecg` (WTONECG, one-loading weight/CG/inertia;
  matches the p136 figures within ±0.1%). New `Project.weight` slice
  (`WeightInput` = mission `estimation` + itemized `items` mass list), with
  `EngineWeightType`/`MassItemKind` enums and the installed-engine-weight
  correlation centralised in `constants.py`. New Streamlit pages
  `01_Weight_Estimate.py` and `02_Weight_CG_Inertia.py`, example weight slice in
  `examples/ga6_normal.project.json`, and `tests/test_weight_estimate.py` /
  `tests/test_weight_onecg.py`. The pages offer an SI **output** toggle (weight →
  kg, inertia → kg·m², CG → mm). `WTENV` re-scoped to Phase 2 (needs `WINGGEOM`'s
  `XLEMAC`/`MAC`).
- `report.module_text_report` — module-agnostic text output, used by the
  generalised `cli.py` stdout path so non-engine modules render correctly.
- **Packaging & tooling** — `pyproject.toml` (editable install via
  `pip install -e '.[dev]'`; `ruff` and `pytest`/coverage config), `cspell.json`
  domain wordlist, and a GitHub Actions CI workflow running `ruff` + `pytest` on
  Python 3.9 / 3.11 / 3.12.
- **Documentation structure** — `docs/` reorganised by type
  (`10_standard` / `20_theory` / `30_future` / `40_history`) with an index
  (`docs/00_INDEX.md`). Added `docs/20_theory/00_theory_sources.md`,
  `docs/30_future/00_backlog.md`, and `docs/40_history/00_completed_development.md`.
- **Process guides** — `docs/10_standard/CODE_REVIEW_PROCESS.md` and
  `RELEASE_PROCESS.md`, specialised for the module-porting workflow.
- **`LICENSE`** (MIT) backing the `pyproject.toml` license declaration, plus
  README License and Disclaimer sections (results are not certified for design).
- **`docs/10_standard/00_program_overview.md`** — consolidated program code
  standard & developer guide (coding standards, an error-handling contract,
  units, entry points, testing/coverage), with `docs/00_INDEX.md` and `CLAUDE.md`
  pointing to it as the authoritative standard.
- **CI coverage floor** — the pytest step now runs with `--cov-fail-under=80` so
  coverage cannot silently regress (a ratchet, to be raised toward 85%).

### Changed

- **SI mass vs Imperial force units.** `LoadValue` gained an optional `quantity`
  hint so the SI converter can tell a pounds-*mass* weight (→ kg) from a
  pounds-*force* load (→ N) — both labelled `lb`. Added `lb-in² → kg·m²` to the
  result converter; weights set `quantity="mass"`. Engine load output is
  unchanged.
- `cli.py` text output is now module-agnostic (was engine-specific), and
  `io.load_cases_csv` falls back to the generic property table for modules that
  emit no structural load cases, so the mass-properties modules export usable CSV.
- `farloads` and `cli` are now an editable install, so they import from any cwd;
  removed the `sys.path` shims from `app/Home.py` and `app/pages/19_Engine_Mount.py`.
- Renamed the ambiguous local helper `l` to `ln` in `farloads/units.py` (lint).
- Fixed stale `calc.py` references (the module is `farloads/modules/engine.py`) in
  `farloads/models.py` and `farloads/report.py` comments/docstrings.
- `CLAUDE.md` mandate strengthened: consult the `reference/` PDFs when generating
  analysis code, keep `docs/` in sync with every code change, and follow the
  backlog → history → changelog move-on-completion rule.
- `docs/PROGRAM_SPEC.md` and `docs/PROJECT_GUIDE.md` moved to `docs/10_standard/`;
  cross-references in `README.md` and `CLAUDE.md` updated.

---

## [0.1.0]

Phase 0 baseline — the package restructure with the engine-mount module ported.
See `docs/40_history/00_completed_development.md` for the full record.

### Added

- `farloads/` pure-calc package (`models`, `modules/engine`, `registry`, `io`,
  `units`, `report`, `constants`), the `app/` Streamlit multi-page UI, and
  `cli.py`. Engine-mount module (`ENGLOADS`) validated against Appendix A/B.
