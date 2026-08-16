# Design note 27 — static typing and lint depth

**Status:** AGREED 2026-08-16 (user: "implement mypy --strict incrementally and
widen ruff") — ✅ **shipped 2026-08-16**, same session; kept as the plan of
record. Tier M closure (tooling + a CI gate + a standard-doc section; no physics,
no schema, no output byte changed).

## 1. The problem

Before this note `ruff` ran only `E`/`F`/`W` — the pycodestyle/pyflakes floor —
and no type checker ran at all, on a codebase whose whole error philosophy is
"flagged, never silently defaulted" and whose `Project` bundle is built from
`Optional` slices. Measured on the tree at 2026-08-16 (before any fix):

- plain `mypy sloads/`: **141 errors in 28 files**; `--strict`: 417. Of the
  141, **60 were `union-attr`** — an `Optional` dereferenced as if present, i.e.
  a latent `AttributeError` on a project that lacks the slice — plus `index`,
  `arg-type` and `assignment` findings in `safety_factors.py` and `workflow.py`,
  the SSOT owners the rest of the code leans on. Heaviest files: `balance.py`
  (38), `engine.py` (29), `configuration.py` (15), `sbeam_bridge.py` (11).
- 139 `Any`, 104 `Dict[str, Any]` signatures, 43 `getattr(..., default)` in
  `sloads/` — each a hole the checker cannot see through; CH-2 (silent export
  defaults) is this class found by hand.
- wider ruff families: `B` 3, `SIM` 9, `RUF` 252 (165 of them the deliberate
  `→ ± ×` glyphs), `I` 67, `C4` 62, `ARG` 13, `PERF` 20, `UP` 1,571 (all 3.10+
  syntax — an artifact of `requires-python`, not a defect), `N` 25 (the ported
  FAR names).

The type checker is cheaper than another drift-guard test for the same class:
a guard asserts one invariant you already thought of; the checker asserts "no
`None` reaches an attribute" across every file, including new ones, with no
test authored.

## 2. Decisions

| ID | Decision | Rationale |
|---|---|---|
| **ST-1** | **mypy, not pyright.** `mypy>=1.10` in `[dev]`; `[tool.mypy]` in `pyproject.toml` is the owner; `files = ["sloads"]` — never `app/` (Streamlit, unmeasured by design) or `tests/`. | Fits the pytest/ruff toolchain, no Node in CI, and per-module `[[tool.mypy.overrides]]` is the cleanest ratchet. |
| **ST-2** | **Default mode at zero errors is the CI gate now** (own job, Python 3.12 — mypy 2.x targets the running interpreter and refuses a 3.9 pin; 3.9 compatibility stays the test matrix's claim). Shipped: 153 → **0** errors (the count grew from 141 after the ruff wave exposed a few more). | A gate that is green from day one is a gate that stays on. |
| **ST-3** | **Strictness ratchets per package**, SSOT owners first. Stage 1 (shipped): `disallow_untyped_defs`, `disallow_incomplete_defs`, `check_untyped_defs` on `sloads.models.*`, `safety_factors`, `units`, `case_ids`, `load_keys`, `constants`, `registry`. Stage 2: `export/`. Stage 3: `modules/`. Then `warn_return_any`/`disallow_any_generics` package by package toward `--strict`. Each stage is a config-list edit plus its fixes, tier S. | The owners are where a type error costs most; the ratchet is a list, not a flag day. |
| **ST-4** | **Narrow, never silence.** No `# type: ignore` (except a stub-less third-party import, with code + reason); no widening to `Any`; `cast` only with a provable invariant and a one-line reason. A reachable `Optional` dereference is fixed per the error contract (`MissingInputError` for an absent slice, `ValueError` for present-but-invalid input); an unreachable one gets a guard that names *why* it is unreachable. **Runtime behaviour on every valid input is unchanged** — the frozen Imperial digest and all oracles are the proof (they passed unmodified). | The checker only helps if the fixes are real narrowings; an `ignore` is a hole with a label. |
| **ST-5** | **ruff select = `E F W B SIM PLE PLW ARG RUF I C4`.** Ignored, each with a reason in `pyproject.toml`: `E741` (ported FAR names), `RUF001-003` (deliberate glyphs), `RUF005` (multi-line list builders read better as concatenation, and the fixer mangles them), `C408` (`dict(width=3)` is the plotly idiom). Off: `UP` (until 3.9 leaves the matrix), `N` (E741's reason), `PERF` (perf-only; its two hit classes here are the intentional per-module `try/except` in the registry and loop-vs-comprehension nits). | Every family on is a defect class; every family off has a stated reason, so turning it on later is a decision, not an oversight. |
| **ST-6** | A `# noqa` carries its rule and a reason. `ARG001` on a public/protocol signature marks a **signature contract** (callback protocol in `equilibrium.py`, uniform tab signature in the views, ported FLAPLOAD input list, `infer_component`'s deliberate refusal to guess); private helpers with a genuinely dead parameter lost it (`_alpha_band`, `_attach_gid`, `_header`, `_derived_elements`, `wing_sets`'s unused `condition`). | The lint stays honest: an unused argument is either a documented contract or a removed parameter, never a silenced warning. |
| **ST-7** | isort (`I`) is on, but the two side-effect import blocks (`sloads/modules/__init__.py` — one line per module for self-registration; `sloads/models/__init__.py` — the star-import resolution order) are `# ruff: noqa: I001` with the reason in place: the auto-fix silently dropped their `noqa` markers and reordered the star imports. | Found in this session; the auto-fixer is not safe on those two files and says so where it matters. |

## 3. What ships (2026-08-16)

- `pyproject.toml`: `mypy` in `[dev]`, `[tool.mypy]` + stage-1 override, wider
  `[tool.ruff.lint]` with reasoned ignores.
- `.github/workflows/ci.yml`: `typecheck` job (mypy on 3.12); ruff scope gains
  `scripts/`.
- **153 mypy errors → 0** across 31 files; **243 new ruff findings → 0** (auto-fixes
  reviewed; the `RUF005` unsafe fixes that collapsed multi-line builders were
  reverted; ~30 hand fixes). Behaviour-affecting sites — all on inputs that were
  already refused earlier on the same path, so unreachable from `run()`; listed
  so the claim is checkable:
  - `modules/balance.py`: new `_wing_slices()` / `_flight_loads()` helpers raise
    `MissingInputError` where a `None` slice would previously have raised
    `AttributeError` when a helper was called directly (`run()` refuses first);
    ground cases refuse a missing `landing` slice the same way (unreachable —
    `gear_case_loads` refuses first). `ConditionResult.note` now `""` not `None`
    when empty (the field is `str`; every consumer tests truthiness).
  - `modules/engine.py`: new `_required()` raises `ValueError` naming the missing
    `EngineInput` field (`takeoff_hp`, `max_cont_hp`, `cylinders`,
    `max_engine_torque`, `cruise_torque`, `stop_time_s`) where the arithmetic
    would previously have raised `TypeError`; the 25.361(a)(3)(ii) `note` is `""`
    not `None` when a value was supplied (`tests/test_engine_far25.py` updated
    from `is None` to `not r.note`).
  - `modules/tail_span.py`, `modules/flap.py`, `modules/net_loads.py`,
    `modules/wing_inertia.py`, `modules/weight_estimate.py`,
    `modules/flight_envelope.py`, `modules/one_engine_out.py`,
    `export/lra_model.py`, `validation.py`: narrowing guards that re-state a
    refusal already made upstream on the same path.
  - `gear_loads.py`: `GearCaseLoads.case_ref` typed `Optional[CaseRef]` (was
    `Optional[object]`); `export/roundtrip.py`: `total_reaction` takes
    `Dict[int, Sequence[float]]` (was `"object"`).
- `docs/10_standard/00_program_overview.md` §Static typing & lint (the rules of
  engagement); `CLAUDE.md` merge gate + commands; `CODE_REVIEW_PROCESS.md` step 7
  and approval gate; `RELEASE_PROCESS.md` §3.2; `README.md`/`PROJECT_GUIDE.md`
  command blocks; `docs/00_INDEX.md` row.

## 4. Not done, on purpose

- `app/` is not type-checked (frozen per the 2026-08-16 scope review; the CLI
  is the delivery path). `tests/` is not type-checked.
- `--strict` globally is the direction, not the state: stages 2–3 (ST-3) are
  backlog rows, tier S each.
- `UP` stays off until the 3.9 leg leaves the CI matrix; turning it on then is
  one `--fix` commit.

## 5. Acceptance (met)

- `.venv/bin/mypy` → `Success: no issues found in 73 source files`.
- `.venv/bin/ruff check sloads/ cli.py app/ scripts/` clean.
- `pytest`: full suite green, including the frozen Imperial digest
  (`tests/imperial_baseline.py`) unmodified — no deliverable byte changed.
