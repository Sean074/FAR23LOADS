# Code Review Process — FAR 23 LOADS

Authoritative process guide for critical code review in this repository. Reviews
**must** be critical: identify defects, non-conformance to the documentation and
the reference manual, and deviations from the porting contract — not just style.

The unit of work here is **porting one suite program** (`.BAS` → a
`farloads/modules/<name>.py` module) or changing an existing one. This guide is
specialised for that.

---

## 1. Objectives

| Objective | Why it matters |
|---|---|
| **Numerical fidelity to the manual** | A load module that is silently 5% off produces an unsafe or uneconomic structure. The Appendix A/B figures are the oracle. |
| **Reference-traceability** | Every equation must trace to Reference 1; an un-cited formula cannot be reviewed or trusted. |
| **Documentation conformance** | `CLAUDE.md` mandates `docs/` stay in sync with every code change. |
| **Porting-contract conformance** | The module pattern (pure calc, shared result types, self-registration) is what keeps modules copy-of-the-pattern. |
| **Preserved engineering conventions** | Sign conventions and BASIC truncations are deliberate; "fixing" them silently changes results. |
| **Maintainability** | 22 modules will share this code; debt compounds. |

---

## 2. Pre-Review Checklist

Complete before reading a single line of diff:

- [ ] Read the commit/PR intent.
- [ ] Open the module's section in [`PROGRAM_SPEC.md`](PROGRAM_SPEC.md) and the relevant Reference 1 chapter (`reference/FAR23 loads (1).pdf`).
- [ ] Confirm the diff includes documentation updates (`docs/`) — flag immediately if absent.
- [ ] Confirm [`../30_future/00_backlog.md`](../30_future/00_backlog.md) was updated (item removed) and [`../40_history/00_completed_development.md`](../40_history/00_completed_development.md) + `CHANGELOG.md` updated if a module/step closed.
- [ ] Confirm a `tests/test_<module>.py` exists with Appendix A and/or B assertions.

---

## 3. Review Process (ordered)

### Step 1 — Documentation compliance audit (non-negotiable)

Per `CLAUDE.md`, every code change updates `docs/` in the same session. Check:

- [ ] `docs/10_standard/PROGRAM_SPEC.md` — the module's spec row/section reflects the actual inputs, outputs, and FAR conditions implemented.
- [ ] `docs/10_standard/PROJECT_GUIDE.md` — any change to package layout, the `Project` schema, or a porting convention is reflected.
- [ ] `docs/20_theory/00_theory_sources.md` — the module has a per-module equation-citation row.
- [ ] `docs/30_future/00_backlog.md` — the ported module is **removed** from the backlog.
- [ ] `docs/40_history/00_completed_development.md` — the module is **added** with its full step record.
- [ ] `CHANGELOG.md` — an `[Unreleased]` entry exists.

**Raise as `[CRITICAL]`** if documentation was not updated. Do not approve until docs are in sync.

### Step 2 — Reference traceability

- [ ] Every non-trivial equation cites its source (FAR section and/or Reference 1 page) in a comment or the spec.
- [ ] Constants come from `farloads/constants.py`, not bare literals — and `math.pi`, **not** `3.1416` (the modernize-the-math decision).
- [ ] The test keeps the manual's **printed figure plus a page citation** next to each assertion, so drift is traceable.

### Step 3 — Numerical fidelity

- [ ] Tolerance oracle is used correctly: `math.isclose(..., rel_tol=1e-3)` (±0.1%) for real-valued figures; **exact** equality only for integer/dimensionless quantities (counts, load factors).
- [ ] Preserved BASIC truncations (`int(x*1000)/1000`) are kept **where and only where** they affect a compared figure — verify against the `.BAS` source in Appendix C.
- [ ] Unit handling: calc runs in the original **Imperial** units; SI is a presentation layer applied at the boundary only (`units.py`). No SI constants leak into calc.
- [ ] Both worked examples are checked where applicable: Appendix A (6-place GA single, p131) and Appendix B (10-place twin turboprop, p251).

### Step 4 — Porting-contract conformance

- [ ] **Pure calc, no I/O.** The module exposes `run(project: Project) -> ModuleResult` and does no file/Streamlit access.
- [ ] **No recomputation of another module's quantity.** Upstream values (weights, CG, geometry, speeds, aero coefficients) are read from the `Project` slice, not recomputed.
- [ ] **Reuses result types.** Emits `LoadValue`/`ConditionResult`/`ModuleResult` so `report.py`, `units.py`, and the CSV writer work unchanged. The CSV stays "one row per load case" via `load_cases_to_rows` — generalised, not reinvented per module.
- [ ] **Self-registers** at import (`register("name", run)`) and is imported in `farloads/modules/__init__.py`.
- [ ] **Missing-slice behaviour:** the module raises `ValueError` when its input slice is absent (so `run_all_modules` skips it cleanly).

### Step 5 — Preserved engineering conventions

- [ ] Sign conventions match the original (e.g. engine-mount reaction torque reported **negative**; "clockwise from the pilot's view is positive" for rotor RPM and stoppage torque).
- [ ] Any new convention introduced by the module is recorded in `PROJECT_GUIDE.md` / `PROGRAM_SPEC.md`.

### Step 6 — Error handling & robustness

- [ ] Optional inputs (blank fields that the BASIC approximated from geometry) are handled, not assumed present.
- [ ] No silent `nan`/`None` propagation into a reported load value without an explicit reason.
- [ ] Multi-engine / twin inputs (Appendix B) are handled where the module supports them.

### Step 7 — Code quality

- [ ] `ruff check farloads/ cli.py` is clean (single-letter structural names are allowed via the `E741` ignore — do not work around the linter with noqa for other rules without justification).
- [ ] New domain terms (program names, variables) are added to `cspell.json`.
- [ ] Public functions in `farloads/` have type hints and a one-line docstring.
- [ ] No magic numbers — load factors, tolerances, and unit factors are named constants.

### Step 8 — Test coverage

- [ ] One manual-example test per module, asserting `run(project)` against the Appendix A and/or B figures.
- [ ] Happy path **and** at least one edge case (missing optional input, twin layout, zero rotor speed, etc.).
- [ ] `pytest` passes with no failures; report pass/fail in the review.

---

## 4. Issue severity

| Severity | Label | Criteria | Action |
|---|---|---|---|
| **Critical** | `[CRITICAL]` | Wrong load value, un-cited equation, lost sign convention, docs not updated | Block merge — must fix |
| **Major** | `[MAJOR]` | Recomputes another module's quantity, missing manual-example test, SI leak into calc | Block merge — must fix or justify |
| **Minor** | `[MINOR]` | Magic number, missing type hint, suboptimal-but-correct code | Non-blocking — fix in PR or follow-up |
| **Nit** | `[NIT]` | Style, naming, comment wording | Optional |

---

## 5. Common defect patterns

| Pattern | Where to look | Risk |
|---|---|---|
| `3.1416` or other hard-coded constant instead of `constants.py` / `math.pi` | the module | Drift vs the tolerance oracle; defeats the modernize-the-math decision |
| BASIC `int(x*1000)/1000` truncation dropped (or added where it doesn't belong) | the module vs Appendix C `.BAS` | Compared figure off in the last places |
| Sign convention flipped (reaction torque, rotor direction) | the module | Sign-wrong load fed downstream |
| Recomputing weight/CG/geometry instead of reading the `Project` slice | the module | Two sources of truth diverge |
| Exact `==` used where a tolerance oracle is required (or vice-versa) | `tests/test_<module>.py` | Brittle or false-passing test |
| SI constant used inside calc | the module / `units.py` | Calc no longer matches the Imperial manual |
| Module doesn't `register()` or isn't imported in `modules/__init__.py` | `farloads/modules/__init__.py` | Module invisible to registry/CLI/GUI |
| Docs not updated; backlog item left in place after completion | `docs/` | Documentation drift; violates `CLAUDE.md` |

---

## 6. Review output format

```
[SEVERITY] file.py:line — Short description.
WHY: The defect or risk, in one sentence.
FIX: Concrete suggestion (snippet if helpful).
```

Example:

```
[CRITICAL] farloads/modules/engine.py:212 — Reaction torque returned positive.
WHY: The suite reports engine-mount reaction torque negative; a positive sign
     reverses the load direction fed to the mount-structure check.
FIX: Negate at the LoadValue boundary and add a test asserting torque < 0 for
     the Appendix A case (p131).
```

---

## 7. Final approval gate

A change may be approved **only** when:

- [ ] All `[CRITICAL]` and `[MAJOR]` items are resolved or explicitly justified.
- [ ] `pytest` passes; the module's Appendix A/B assertions pass within ±0.1%.
- [ ] `ruff check farloads/ cli.py` is clean.
- [ ] All relevant `docs/` files (spec, theory citation, backlog, history) and `CHANGELOG.md` are in sync with the code.
