- **Static typing and lint depth (design note 27, tier M, 2026-08-16).** `mypy`
  joins the merge gate: `[tool.mypy]` in `pyproject.toml` checks `sloads/` (never
  `app/`/`tests/`), zero errors in default mode, in its own CI job on 3.12;
  strictness ratchets per package through `[[tool.mypy.overrides]]` — stage 1
  (`disallow_untyped_defs`/`disallow_incomplete_defs`/`check_untyped_defs`) on
  the single-source owners (`models/`, `safety_factors`, `units`, `case_ids`,
  `load_keys`, `constants`, `registry`). 153 errors → 0 across 31 files by
  narrowing only (no `type: ignore`, no `Any` widening, no `cast`); the frozen
  Imperial digest and every oracle passed unmodified. Latent `None`
  dereferences on already-refused paths now raise per the error contract
  (`balance.py` `_wing_slices`/`_flight_loads`, `engine.py` `_required`);
  `ConditionResult.note` is `""` not `None` when empty; `GearCaseLoads.case_ref`
  is `Optional[CaseRef]`. `ruff` select widens from `E F W` to
  `E F W B SIM PLE PLW ARG RUF I C4` (each ignore reasoned in `pyproject.toml`;
  `UP` off until 3.9 leaves the matrix, `N`/`PERF` off with reasons); 243 new
  findings → 0, five private helpers lost dead parameters, contract-signature
  `ARG001`s carry a reasoned `noqa`, the two side-effect import blocks are
  isort-skipped in place. Rules of engagement:
  `00_program_overview.md` §Static typing & lint; `CODE_REVIEW_PROCESS.md` step 7.
