# M4 maintainability sequence — execution plan (M4-12 → M4-11 → G8 views → M4-10 → M4-9)

**Status:** **Steps 1–3 complete** — M4-12a + M4-12b (2026-08-03, M4-12 closed)
and **M4-11a** (2026-08-04, the scaffold helpers; the complexity-splitting half
is backlog **M4-11b** and does not block G8). See the history entries in
[`../40_history/00_completed_development.md`](../40_history/00_completed_development.md).
**Step 4 (G8) is partially shipped 2026-08-04**: G8.1 (the `report/` package),
G8.2 (schema v36 document control), G8.3 (the methods statement in every export
channel) and G8.4's coverage matrix are done; the report document itself
(`content.py`, `latex.py`, `plots_tex.py`, `export/pdf.py` + UI) is backlog
**M3-3b**, and is blocked on **M4-20** for unit conformance. Steps 5–6 planned,
not started. **All design decisions resolved 2026-08-03**
(D-12 … D-18, §2). **Written:** 2026-08-03.
**Scope:** the five pre-F25 maintainability items, in the order the dependency
analysis below justifies. **Not in scope:** any calc-math change. The invariant
throughout is the one in [`00_backlog.md`](00_backlog.md): Appendix A oracles pass
unchanged, concept mode still reduces exactly to FAR 23 on GA inputs, the
ultimate-load contract holds, `workflow.py` stays the single source of navigation
truth.

Related: [`00_backlog.md`](00_backlog.md) (the items themselves),
[`05_step_g8_summary_report_plan.md`](05_step_g8_summary_report_plan.md) (G8 in
full — this plan only sequences its view work),
[`../10_standard/GUI_design.md`](../10_standard/GUI_design.md) (page anatomy and
the unit-boundary pattern M4-11 formalises).

---

## 1. Measured baseline (2026-08-03, `main` @ 44ae294, clean tree)

Everything below is measured, not quoted from the 2026-07-21 review.

| Quantity | Value |
|---|---|
| Suite | **536 passed, 28.5 s**, 93 % total coverage |
| `ruff check sloads/ cli.py` | clean |
| `SCHEMA_VERSION` | **35** (M4-1 consumed 35 for `front_spar_pct`/`rear_spar_pct`) |
| `app/views/*.py` | 20 views, **6 451 lines** |
| `app/components.py` | 121 lines — `workflow_page_link`, `gate`, `render_applicability_banner`, `_switch_to_concept` |
| `number_input` call sites | **145** across 11 views (`configuration_layout` 51, `engine_mount` 25, `structural_speeds` 17) |
| `to_display` / `to_imperial_scalar` sites | **136** across 13 views |
| Duplicated test `_value`/`_values` helpers | **9** (`test_engine`, `test_units`, `test_configuration`, `test_mach_limit`, `test_structural_speeds`, `test_weight_onecg`, `test_weight_envelope`, `test_wing_geometry`, `test_weight_estimate`) |
| Tests importing from `test_engine` | 7 files (`test_engine_far25`, `test_io` ×2, `test_report`, `test_registry`, `test_units`, `test_wing_geometry`) |
| AppTest-based test files | 7, incl. `test_views_smoke.py` (parametrized over **every** view) |
| Example fixtures | 6 (`ga6_normal`, `cessna_210`, `concept_heavy`, `concept_regional_jet`, `atr42_100`, `dhc8_dash8`) |

**No cyclomatic-complexity tool is installed** (`radon`/`xenon`/`mccabe` absent
from `.venv`). The CC figures in M4-11 (`_tab_design_speeds` 72, `landing_reactions`
66, `_three_view` 52, `_tab_vn` 44) are from the 2026-07-21 review and are
**indicative only** — re-measure at step start with `radon`, added to the `dev` extra per D-17.

---

## 2. Design decisions — **all resolved 2026-08-03**

D-12 … D-18 were put to the user on 2026-08-03 and **every one was resolved as
recommended**. They are recorded in
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md);
the analysis behind each is kept below because the steps in §4 depend on the
reasoning, not just the verdict. **Nothing in this section is still open.**

| ID | Resolution |
|----|------------|
| D-12 | **(a)** — swap the order: M4-10 before M4-9, key arrives by migration |
| D-13 | **(a)** — `NamedTuple`, lowercase attributes |
| D-14 | **(a)** — underscore-drop in place + `__all__`, no facade |
| D-15 | **(a)** — document in M4-12b, retire in M4-10 |
| D-16 | **(a)** — one `_active_system()` resolver over session state |
| D-17 | **(a)** — `radon` in the `dev` extra, reporting only, no CI gate |
| D-18 | **(a)** — three named functions |

### D-12 ✅ *(a)* — `LoadValue.key` is a **persisted** field. Does M4-10 come before M4-9? ⚠️ *biggest finding*

`LoadValue` is serialized — `io.py:635`,
`loads=[LoadValue(**_filtered(LoadValue, v)) for v in d.get("loads", [])]` inside
`_critical_condition_from_dict`, i.e. every `CriticalCondition.loads` in the
persisted `envelope` slice. So M4-9's `key: str` lands **inside the persisted
schema**, not just in memory. Consequences:

- It needs a `SCHEMA_VERSION` bump and a **backfill migration** (old files carry
  no `key`; `_filtered` tolerates the absence and produces `key=""`).
- Without the backfill, a reloaded pre-M4-9 project silently produces
  key-less `LoadValue`s → report/CSV columns blank out. **That is the exact
  failure mode M4-9 exists to eliminate**, reintroduced through the file path.

Options:

| | Approach | Cost | Risk |
|---|---|---|---|
| **(a)** | **M4-10 first**, then M4-9 registers a normal `MIGRATIONS[35] → 36` label→key backfill | reorders the last two steps | lowest — M4-9 becomes the migration chain's first real customer, which also *validates* the chain |
| (b) | Keep M4-9 → M4-10; hand-write the backfill in `_critical_condition_from_dict`, M4-10 folds it into the chain later | one throwaway shim | the shim is exactly the "key-presence sniffing" M4-10 is deleting — churn |
| (c) | `key` defaults `""`; readers fall back to `label` when key is empty | cheapest | **rejected** — permanently keeps the label path alive, so M4-9 doesn't actually de-string anything |

**Resolved: (a) — the last two steps swap to … → M4-10 → M4-9.** The rest of the
sequence is unaffected.

### D-13 ✅ *(a)* — `htail_balance` NamedTuple: attribute naming

Today `htail_balance` (`select.py:204`) returns `Dict[str, float]` with keys
`LT25, LT50, AT, DELTA, LT, CP`. Consumers: `select.py:267,333,421`,
`balloads.py:72`, `tests/test_select.py:181`. NamedTuple conversion is contained
(5 sites), but the attribute case is a convention call:

- `b.LT25` — preserves the manual's symbols verbatim, matches the existing
  BASIC-derived naming the ruff config already accommodates (`E741` ignored);
  unusual for Python attributes.
- `b.lt25` — idiomatic; costs a mental hop against Ref 1 Ch 9.

**Resolved: `typing.NamedTuple` with lowercase attributes** — `lt25`, `lt50`,
`at`, `delta`, `lt`, `cp` — each field carrying its Ref 1 Ch 9 symbol in the
docstring. The function's own locals are already lowercase (`lt25`, `lt50`,
`aht`), so the attributes match the file they live in; `NamedTuple` keeps the
result tuple-unpackable and is 3.9-compatible.

### D-14 ✅ *(a)* — What "public" means for the promoted symbols

Six cross-module private imports exist today:

| Symbol | Defined | Imported by |
|---|---|---|
| `_interp_x` | `wing_geometry.py:83` | `wing_inertia.py:54`, `net_loads.py:41`, **`app/views/configuration_layout.py:64`** |
| `_sigma` | `flight_envelope.py:89` | `select.py:77` |
| `_design_inputs` | `flight_envelope.py` | `select.py:77` |
| `_maneuver_load_factors` | `structural_speeds.py:61` | `flight_envelope.py:74`, **`app/components.py:21`** |
| `_elevator_load`, `_envelope`, `_flaps_by_config_name` | `select.py` | `balloads.py:34` |

The two **bold** rows are the live violations of "`app/` must not import `sloads`
underscore names". Options: (a) drop the underscore in place + add `__all__` to
each module; (b) build a curated public facade (`sloads/api.py`) and route `app/`
through it.

**Resolved: (a).** There is no facade today and inventing one is a larger
architectural change than this batch warrants; `__all__` on each module plus the
rename gives a reviewable public surface.

**Naming carve-out (verified 2026-08-03).** `_envelope` is defined at
`select.py:93` and `_resolve_envelope` at `select.py:111` — same module, two
functions apart. There is no symbol collision, but `envelope(project)` sitting
beside `_resolve_envelope(project, envelope)` is unreadable, and the parameter
named `envelope` at six call sites would shadow it. `_envelope` therefore takes a
**chosen** public name (suggest `default_envelope` — it is the "build one if the
caller passed none" path); `_design_inputs` likewise (suggest `design_inputs`,
which is unambiguous). The other four are safe mechanical strips.

### D-15 ✅ *(a)* — Retirement of the `tail_loads`/`vtail_loads` property proxies

`Project.tail_loads` / `.vtail_loads` (`models/project.py:246-272`) are Step-G6
properties proxying `geometry.empennage.htail/.vtail`. Two documented hazards:
they are invisible to `dataclasses.fields`/`replace`/`asdict`, and the **setter
silently no-ops** when assigning `None` to a project with no geometry
(`project.py:255-258`, `269-272`). The backlog says "document, do not replicate,
retire at the rename break" — but **there is no rename break scheduled** after
M3-1. Options: (a) document-only in M4-12 and leave the trap-door indefinitely;
(b) fold the retirement into M4-10, where `project_from_dict` is being rebuilt
anyway and the migration chain can carry the field move.

**Resolved: (a).** M4-12b documents the trap-door (warning at the definition, a
`PROJECT_GUIDE.md §5` "do not replicate" note); **M4-10 owns the retirement** —
retiring the proxies changes ~40 call sites across modules, views and tests,
which does not belong inside a test-architecture cleanup, and M4-10 is already
rebuilding the read path that would carry the field move. Add the retirement to
M4-10's scope in §4 step 5.

### D-16 ✅ *(a)* — Where `unit_number_input` gets its unit system (M4-11 ↔ M4-20)

M4-20 (dated 2026-08-03, still open) adds a unit-system field to `Project` and
makes deliverables render in it. M4-11's helper needs a unit source *now*.
Options: (a) the helper reads today's session-state selection, switched to the
`Project` field when M4-20 lands; (b) pull M4-20's `Project` field forward into
M4-11.

**Resolved: (a).** The read is isolated in one module-level resolver,
`_active_system()` in `app/components.py`, so M4-20 re-points exactly one
function at the `Project` field. **Binding requirement:** the helper expresses the
**aviation carve-out** per-field — airspeed (KEAS) and altitude (ft) are never
converted — through an explicit "not converted" path in the signature, never by
inferring it from the unit string.

### D-17 ✅ *(a)* — Do we add a complexity tool to the dev extra?

M4-11's scope is stated in CC terms but nothing in `.venv` measures CC. Options:
(a) add `radon` to the `dev` extra and record before/after per refactored view;
(b) drop the CC framing and scope M4-11 by line count + call-site count (both of
which §1 already measures).

**Resolved: (a).** `radon` joins the `dev` extra in `pyproject.toml` as a
**reporting tool only — explicitly not a CI gate** (a gate would fail today on
files this plan does not touch, and `ruff`+`pytest` remain the merge gate per
CLAUDE.md). M4-11 records before/after CC per refactored view in its history
entry; those numbers are the objective evidence the refactor achieved something.

### D-18 ✅ *(a)* — Consolidated test-helper API shape

The 9 duplicated helpers are **not** interchangeable — three distinct contracts:

| Contract | Files |
|---|---|
| `(ConditionResult, label) -> float` | `test_engine`, `test_weight_onecg`, `test_wing_geometry` |
| `(List[ConditionResult], label) -> float` | `test_mach_limit`, `test_structural_speeds`, `test_weight_envelope`, `test_weight_estimate` |
| `(ConditionResult, label) -> LoadValue` | `test_units` |
| `(project) -> Dict[label, value]` (flatten-all) | `test_configuration` |

**Resolved: (a) — three named functions in `tests/helpers.py`**, not one
overload:

```python
value_of(source, label)        -> float        # the common case
load_value(source, label)      -> LoadValue    # when units/quantity are asserted
values_by_label(source)        -> Dict[str, float]   # flatten-all
```

`source` accepts a `ModuleResult`, a `ConditionResult`, or a list of either —
the normalisation `io._as_conditions` (`io.py:1219`) already models. All three
raise `KeyError` on a missing label, matching today's helpers. **This signature
is the one M4-9 re-points at `key`** (step 6), so it is fixed here deliberately.

---

## 3. Open issues found (defects in the plan documents, not the code)

1. **G8.2's schema bump is stale.**
   `05_step_g8_summary_report_plan.md` §6 G8.2 says bump `SCHEMA_VERSION`
   **34 → 35**. M4-1 already consumed 35. G8.2 must say **35 → 36** — and if
   D-12(a) is accepted, M4-9's backfill takes another number after that. Fix the
   G8 plan text before G8.2 starts. *(Doc-only.)*
2. **M4-12's cspell sub-item is already closed.** The item says "add a cspell
   config or delete the CODE_REVIEW_PROCESS cspell bullet" — `cspell.json`
   exists (created 2026-08-03) and the `CODE_REVIEW_PROCESS.md:89` bullet is
   valid. Drop the sub-item from M4-12's scope at close-out.
3. **The backlog's `io.py:936-945` line citation has drifted.** The 19-clause
   or-gate is now `io.py:998-1007`, inside `project_from_dict` (`io.py:991`).
   Refresh when M4-10 is written up.
4. **M4-10's "only v20/v24 exist today" understates the legacy surface.**
   `project_from_dict` carries at least five distinct legacy paths: the flat
   engine-only file, `legacy_configuration` (pre-v25 top-level `configuration`),
   `legacy_tail_loads`/`legacy_vtail_loads` (pre-G6), `_legacy_cg_cases_from_flight_loads`,
   and `_legacy_aero_coeffs_from_flight_loads`. The migration chain must account
   for all five, and **no document records which `SCHEMA_VERSION` each break
   corresponds to** — that archaeology is a real sub-step, not a footnote.
5. **`app/components.py` is where M4-11 lands, and it already has two of the
   four pieces.** `gate()` and `render_applicability_banner()` exist; the
   `page()` context manager should compose them rather than duplicate them. Good
   news for scope; worth stating so the step doesn't grow a parallel helper module.

---

## 4. The sequence

Ordering rationale in one line each:

| # | Step | Must precede | Because |
|---|---|---|---|
| 1 | **M4-12a** (button keys + test helpers) | M4-11 | `test_dirty_flag` selects Apply buttons **positionally**; M4-11 rewrites the 22 apply handlers, so positional selection silently rebinds and the test passes while asserting nothing |
| 2 | **M4-12b** (symbol promotions) | M4-11 | `app/views/configuration_layout.py` and `app/components.py` import `sloads` private names; fix the import contract before rewriting the importers |
| 3 | **M4-11** (app scaffold) | G8 view work | G8.6 adds a Summary-report section to `export_report.py`; writing it against the new `page()` helper is free, retrofitting it is not |
| 4 | **G8** (M3-3, all sub-steps) | — | highest-value item; G8.1 is calc-side and independent, G8.6 is the only view collision |
| 5 | **M4-10** (io migration chain) | M4-9 | **per D-12** — `LoadValue.key` is persisted and needs a real migration |
| 6 | **M4-9** (`LoadValue.key`) | Phase F25 | last wall before F25 supplements emit new quantities |

*(Steps 5 and 6 sit in the **resolved** D-12(a) order — M4-10 before M4-9,
swapped from the order this plan was originally requested in.)*

---

### Step 1 — M4-12a: test-architecture cleanup ✅ *complete 2026-08-03*

**Decisions applied:** D-18 (resolved). **Shipped as written**, with three
additions the work turned up: `parse_cards` also moved out of
`test_sbeam_bridge` (an eighth test-imports-test); the form-key conversion
covered `test_configuration_layout_view` and `test_landing` as well as
`test_dirty_flag`; and two `__main__` self-runners that drove views without
`app/` on `sys.path` were repaired. It also exposed an app defect the positional
selection had been masking — backlog **M4-22**.

1. **`tests/helpers.py`** — new module with the D-18 API, docstringed, importable
   via the existing `conftest.py` `sys.path` entry (no packaging change).
2. **Migrate the 9 helpers** file by file, deleting each local copy. Do the 7
   `from test_engine import …` sites in the same pass: `io520bb`/`turboprop`
   move to `tests/helpers.py` (or a `tests/fixtures.py` — decide with D-18) so
   no test file imports another test file.
3. **Button selection by form key.** `test_dirty_flag.py:66` defines
   `_apply_buttons(at)` as *every* button whose label contains "Apply", then
   indexes it positionally (`[0]`, `[1]` at lines 88 and 103). Replace with
   selection through the enclosing form.
   **Verified 2026-08-03: no `app/` change is needed** — all **24** `st.form(...)`
   calls across 13 views already carry unique string keys
   (`structural_speeds_form`, `mach_limit_form`, `layout_form`, …), so the form
   is addressable today. This sub-step is test-only.

**Acceptance:** 536 tests still pass, unchanged count and unchanged assertions;
zero test-file-imports-test-file remaining; every AppTest button lookup resolved
through a form key, with an assertion that the lookup **found** something (a
silently-empty selector is the failure mode being designed out). **No `sloads/`
or `app/` change at all** — this sub-step touches `tests/` only.
**Risk:** low. The one trap is a key rename that makes an AppTest silently find
nothing — assert the button was found, not just that Apply worked.

### Step 2 — M4-12b: symbol promotions + contract documentation ✅ *complete 2026-08-03*

**Decisions applied:** D-13, D-14, D-15 (all resolved). **Shipped as written.**
The oracle gate was met by a stronger check than the plan asked for: rather than
diffing `LT`/`CP` on `ga6_normal`, a full result snapshot (every module, every
`LoadValue`, every safety factor, all 6 examples) was taken before the first
edit and re-taken after — **byte-identical**. The D-14 chosen-name carve-out
took a third symbol, `_sigma` → `density_ratio` (see the register); the
duplication it exposed is logged as **M4-23**.

1. **Promote** the six symbols per D-14, with `__all__` on each touched module.
   Update the 2 `app/` importers and the 6 `sloads/` importers.
2. **`htail_balance` → NamedTuple** per D-13. 5 call sites + 1 test.
3. **Document the property-proxy trap-door** per D-15: an explicit warning in
   `models/project.py` beside the properties, a note in `PROJECT_GUIDE.md §5`
   ("do not replicate this pattern"), and a backlog entry for the retirement.
4. **Write `sync_geometry_derived`-inside-`run()` into the porting contract.**
   It is called at the top of `run()` in 6 modules (`body_loads`, `wing_inertia`,
   `select`, `net_loads`, `flight_envelope` ×2, `balloads`) plus `io.py:1077` —
   currently convention by imitation. → `PROJECT_GUIDE.md §5`.
5. **Drop the cspell sub-item** (§3 issue 2).

**Acceptance — this is the oracle re-run gate.** Steps 1–2 touch `select.py`,
`balloads.py`, `flight_envelope.py`, `structural_speeds.py`, `wing_geometry.py`,
`wing_inertia.py`, `net_loads.py` — the Appendix-A oracle-locked and twin
closure-locked path. Required: full suite green with **identical numeric
assertions** (no tolerance loosened, no expected value edited — a changed number
means the rename changed behaviour and the change is wrong), `ruff` clean, and
both concept fixtures still run end-to-end.
**Risk:** medium-low. The dict→attribute conversion is where a silent typo hides
— a `KeyError` becomes an `AttributeError` at the same site, which is fine, but a
*wrong* attribute that happens to exist is not. Mitigate by converting all 5
sites in one commit and diffing the computed `LT`/`CP` on `ga6_normal` before and
after.

### Step 3 — M4-11: app scaffold helpers ⚠️ *partially complete 2026-08-04 (M4-11a)*

**Decisions applied:** D-16, D-17 (both resolved). **Sub-steps 1–3 shipped**
(re-measured baseline, `unit_number_input` built and tested alone first, the page
scaffold — split into `page_header` + `page` because most views are top-level
scripts a context manager would force a whole-file reindent on). **Sub-step 4,
the worst-first CC splitting, did not ship** and is backlog **M4-11b**; the six
CC-E/F functions are unchanged, and the app layer *grew* ~170 net lines rather
than shrinking by 1.5–2 k. The step's blocking purpose is met — G8.6 needs
`page()`/`unit_number_input`, and both exist.

**What the risk section below predicted, and what happened.** The "real risk" it
names — a helper that renders fine and silently corrupts inputs — was not
hypothetical: building the round-trip tests found a double conversion (184 ft²
stored as 1982 ft²), a per-Apply rounding drift, unconverted bounds, and ~40
Geometry fields that ignored the unit toggle outright. Both required test classes
exist and are what caught them.

1. **Re-measure** the CC/line baseline per D-17 and record it in the step's
   history entry.
2. **`unit_number_input(...)`** in `app/components.py` — renders in the display
   system, returns Imperial, with an explicit non-converted path for KEAS and
   altitude (D-16). **Build and test this helper alone first**, before adopting
   it anywhere.
3. **`page(title, requires=...)` context manager** — composes the existing
   `gate()` and `render_applicability_banner()`; emits the title/caption header.
4. **Adopt, worst-first**, one view per commit: `configuration_layout` (51
   `number_input`s), `engine_mount` (25), `structural_speeds` (17),
   `landing_loads`, `flight_envelope`, then the rest.

**Acceptance:** `test_views_smoke.py` green for all 20 views (it parametrizes
over `app/views/*.py`, so a new or renamed view is covered automatically); the
measured line count down by the projected 1.5–2 k; **plus the new tests below**.
**Risk — the real one.** The smoke net asserts *exception-free render*, not
correct values. A `unit_number_input` that converts twice, or in the wrong
direction, renders fine and silently corrupts every input. Required additions to
this step's definition of done:

- A direct round-trip test on the helper: display → Imperial → display lossless
  for each unit kind, and **unconverted** for KEAS/ft.
- At least one AppTest per refactored view asserting a *numeric* value reaches
  `session_state["project"]` in Imperial after Apply, run in **both** unit
  systems. Without this, the step's own headline benefit ("removes the
  silent-unit-bug hazard") is unverified.

### Step 4 — G8 (M3-3) ⚠️ *partially complete 2026-08-04*

**Shipped:** G8.1 `report.py` → `report/` (with `_fmt` promoted to
`format_value`, a private cross-boundary import the move surfaced); G8.2 the
document-control fields at **schema v36**; G8.3 `methods.py` and its stamp in
every CSV/BDF/zip/workbook channel, with every in-repo CSV reader audited;
G8.4's `coverage.py`. **Outstanding:** `content.py`, `latex.py`, `plots_tex.py`,
`export/pdf.py` and the Export-page section — backlog **M3-3b**.

**A prerequisite this plan named and the sequence did not carry.** The G8 plan's
§10.1 resolution puts the report in the user's selected unit system and states
plainly that **M4-20 is a prerequisite for G8's conformance tests**. M4-20 is
still open, so G8.5 must not be written before it — a `.tex` renderer built
against the Imperial-only writers would have to be retrofitted, which is exactly
the trap this whole sequence exists to avoid. **M4-20 should be inserted before
the G8 remainder.**

Run [`05_step_g8_summary_report_plan.md`](05_step_g8_summary_report_plan.md)
as written, with two corrections from this analysis:

- **Fix the G8.2 schema number first** (§3 issue 1): 35 → 36.
- **G8.6 is written against `page()`/`unit_number_input`**, since M4-11 has
  landed. The Export page's existing `st.header` sections stay as-is; only the
  page header/gate/banner adopt the helper.

G8.1 (`report.py` → `report/` package) remains independent of everything in this
plan and could be pulled forward at any time — its own acceptance is "zero
importing-module changes, no test edits."

### Step 5 — M4-10: io.py migration chain *(per D-12(a))*

**Decisions applied:** D-12, D-15 (both resolved).

1. **Archaeology sub-step** (§3 issue 4): map each legacy path in
   `project_from_dict` to the `SCHEMA_VERSION` at which it was introduced, from
   `40_history/00_completed_development.md` + `CHANGELOG.md`. Record the table in
   the step's history entry — it is the specification for the chain.
2. **`MIGRATIONS: dict[int, callable]`** applied hop-by-hop, then **one** tolerant
   reader. Replaces the 19-clause or-gate (`io.py:998-1007`) and the five inline
   legacy shims.
3. **Frozen fixtures** — one file per historical shape actually reachable: flat
   engine-only, v20, v24, pre-G6 (tail_loads at top level), current. Declare
   pre-v20 unsupported in `PROJECT_GUIDE.md` rather than pretending otherwise.
4. **Generic sentinel round-trip test** — every persisted dataclass field
   survives `to_dict`/`from_dict` (manual field lists silently drop new fields).
5. **Fields-hash test** — fails when a persisted dataclass changes without a
   `SCHEMA_VERSION` bump.
6. **Retire the `tail_loads`/`vtail_loads` property proxies (per D-15).**
   `Project.tail_loads`/`.vtail_loads` become plain reads of
   `geometry.empennage.htail`/`.vtail` at the ~40 call sites; the properties and
   their silent-`None` setters are deleted. The migration chain built in (2)
   carries the legacy top-level `tail_loads`/`vtail_loads` keys, which is why
   this lands here and not in M4-12b. Do it as the **last** sub-step, after the
   chain and both new tests are green, so a regression is attributable.

**Acceptance:** all 6 `examples/*.project.json` load byte-identically to today
(assert on the round-tripped dict, not the file); every frozen fixture loads;
the fields-hash test fails when deliberately broken (test the test).
**Risk:** medium. This is the only step that can break a user's saved project.

### Step 6 — M4-9: `LoadValue.key`

**Decisions applied:** D-12 (M4-10 lands first, so the key arrives by migration) and D-18 (the helpers re-point here).

1. Add `key: str = ""` to `LoadValue`; assign a key at every producing site.
2. Register the label→key **backfill migration** in the M4-10 chain, bumping
   `SCHEMA_VERSION` (the fields-hash test from step 5 will demand it — good).
3. Re-point `report.py:219-227,321,348,410` (`_VERTICAL_LABELS`, `_LOC_LABELS`,
   `_GYRO_CASE_RE`, `has_load_case_data`, `_find`/`_find_any`/`_detect_unit`),
   the 13 view lookups, `sbeam_bridge`, and the test helpers (one file now, not
   nine — the payoff from step 1).
4. `label` stays cosmetic; add a test that **renaming every label leaves the CSV
   columns intact** — the regression this whole item exists to prevent.

**Acceptance:** the relabel test above passes; CSV output byte-identical for all
6 examples before/after; oracles untouched (no calc in this path).
**Risk:** low mechanically, but wide. The `_GYRO_CASE_RE` label regex
(`report.py:224`) parses case number, description **and** component out of a
label string — that one is a genuine redesign, not a lookup swap. Scope it
explicitly.

---

## 5. Global gates (every step)

- `ruff check sloads/ cli.py` clean; `.venv/bin/python -m pytest` green
  (**536 baseline**; the count may only go up).
- Appendix A oracle assertions numerically unchanged. **Any edited expected
  value is a stop-and-review, not a fix.**
- Both concept fixtures (`concept_heavy`, `concept_regional_jet`) run end-to-end.
- New domain terms → `cspell.json`.
- Git stays the user's: this plan describes changes; the user commits.

## 6. Doc-sync obligations

Per CLAUDE.md, each step is incomplete until its docs land in the same session.

| Step | Docs |
|---|---|
| M4-12a | `PROJECT_GUIDE.md` (test-helper location + "tests do not import tests"), backlog → history, CHANGELOG |
| M4-12b | `PROJECT_GUIDE.md §5` (public-symbol contract, `sync_geometry_derived` convention, property-proxy warning), `PROGRAM_SPEC.md` if any public name changes, backlog → history, CHANGELOG |
| M4-11 | `GUI_design.md` (page anatomy + unit-boundary pattern become the helpers), `GUI_USER_GUIDE.md` if any page visibly changes, backlog → history, CHANGELOG |
| G8 | as `05_step_g8_summary_report_plan.md` §G8.7 |
| M4-10 | `PROJECT_GUIDE.md` (schema/migration policy, supported-version floor), `DATA_DICTIONARY.md` regen, backlog → history, CHANGELOG |
| M4-9 | `PROJECT_GUIDE.md` (`LoadValue.key` contract), `00_program_overview.md` if the CSV shape is documented there, `DATA_DICTIONARY.md` regen, backlog → history, CHANGELOG |

Every step also updates `00_backlog.md` (**remove**) and
`40_history/00_completed_development.md` (**add**, full step format) in the same
session, and resolved D-numbers move to
[`../40_history/03_resolved_decisions.md`](../40_history/03_resolved_decisions.md).
