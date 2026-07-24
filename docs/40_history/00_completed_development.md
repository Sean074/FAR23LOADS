# Completed Development

The authoritative record of what has shipped: completed modules/phases, key
decisions, and resolved defects. Items move here from
[`../30_future/00_backlog.md`](../30_future/00_backlog.md) the moment they close,
with a matching `CHANGELOG.md` entry.

Each entry uses the step format: **Objective**, **Deliverables**, **Test /
Acceptance**, **Key decisions**.

---

## M4-16 — 2026-07-23 review nits batch (doc-currency CRITICAL + maintainability, complete 2026-07-23)

**Objective.** Close the four MINOR/NIT findings of the 2026-07-23 M4-7 review,
led by its CRITICAL: `GUI_design.md`'s hand-written "currently
`SCHEMA_VERSION = …`" paragraph stale for the **third** time (still 32 after the
M4-7 bump to 33; the 2026-07-21 review's single CRITICAL was the same line at
v31→v32). Fourth item of the M3 release gate.

**Deliverables.**
- **`GUI_design.md` schema paragraph** fixed to 33; the recent-steps migration
  list gains `v33 M4-7 per-case safety_factor`; the paragraph now names its own
  guard test. **New guard:**
  `tests/test_data_dictionary.py::test_gui_design_schema_line_current` asserts
  the doc contains `` `SCHEMA_VERSION = {models.SCHEMA_VERSION}` `` with a
  pointer failure message — verified to bite by perturbing the line locally
  (fails with the message) and restoring. A fourth regression is unmergeable
  (CI runs pytest). Sited in `test_data_dictionary.py` beside the generated-doc
  drift guards; the deeper fields-hash enforcement remains M4-10.
- **`sbeam_bridge._sf()`** typed (`Union[WingLoadResult, BodyLoadResult,
  TailChordResult, ControlSurfaceLoadResult]`) and reads `result.safety_factor`
  directly — the `getattr` fallback is gone (every producer mints the field
  since M4-13; the fallback only served hand-built doubles while masking a
  future attribute rename). `_SF` survives as the default constant the closure
  tests read; module docstring/comments updated to match.
- **`_sf_str()` helper** — deliverable SF formatting: always a decimal point
  (`SF=1.0`, `SF=1.5`, `SF=1.25`), replacing all eleven `f"{sf:g}"` sites
  (card `$` headers, closure comments, the four CSV `SF` columns). The six test
  assertions pinning `SF=1` / `{"1"}` moved with it.
- **`io.py`** intra-package imports ordered alphabetically
  (`.constants` → `.models` → `.report` → `.validation`).

**Test / Acceptance.** Suite green (**501** passed, +1), `ruff` clean (incl.
`app/`), self-runners pass (`test_data_dictionary.py`, `test_sbeam_bridge.py`
24/24). No calc, schema or persisted-format change; the only output change is
the cosmetic `SF=1` → `SF=1.0` rendering.

**Key decisions.**
- *Guard test lives with the existing doc-drift tests* — not a new file; the
  natural companion to `test_schema_version_recorded`.
- *`Union` over a `Protocol`* for `_sf` — the four concrete types are already
  imported in the module and the closed set is the point.
- *`_sf_str` helper over a format-spec* — no single format spec renders 1.0 as
  `1.0` and 1.25 as `1.25` without trailing-zero noise elsewhere.

---

## M4-15 — LIMIT-marked deliverables: analysis-page CSV downloads (defect, contract, complete 2026-07-23)

**Objective.** The CLAUDE.md analysis-page exception lets a per-module page show
LIMIT values only when explicitly marked and pointing at the ultimate
deliverables — but the marking must travel with a *download*. The 2026-07-23
review found `app/views/wing_loads.py`'s "Download net wing loads (CSV)"
(`net_loads.wing_load_rows`) shipped LIMIT station loads with no marker, no `SF`
column and a neutral filename; the mandated sweep found the same pattern on the
Fuselage Loads CSV and (partially) the Loads Plots comparison CSV, whose plot
axes said `(unit, LIMIT)` while its CSV `Field` column dropped the marker.
Tail-chordwise and one-engine-out downloads were already column-marked in-band;
everything else (aileron/flap/tab, engine mount, landing loads, airloads,
Export page) already routes through the ULTIMATE channels. Third item of the M3
release gate.

**Deliverables.**
- **`Basis = LIMIT` column** appended to the two canonical station-row shapes,
  `net_loads.wing_load_rows` and `body_loads.body_load_rows` — single source, so
  the on-page tables and every CSV built from the rows state the basis in-band.
- **Filename convention `*_LIMIT.csv`** applied to every LIMIT download: wing
  (`net_wing_loads_LIMIT.csv`), fuselage (`net_fuselage_loads_LIMIT.csv`),
  loads-plots comparison (`loads_plots_<comp>_LIMIT.csv`), tail chordwise and
  one-engine-out time history (already column-marked; renamed for uniformity).
  The Loads Plots CSV `Field` strings gain `, LIMIT`, matching the plot axes.
- **ULTIMATE twins (user decision 2026-07-23: offer both buttons).** Wing and
  Fuselage Loads pages add a side-by-side ULTIMATE download —
  `net_wing_loads_ULT.csv` via `sbeam_bridge.span_load_csv` and
  `net_fuselage_loads_ULT.csv` via `sbeam_bridge.body_span_load_csv` (renderers
  reused as-is; per-case `SF` column) — with a caption tying the LIMIT file to
  the on-page oracle-traceable table and the ULT file to the Export page.
- **`tests/test_ultimate_contract.py`** — source-scan guard: every view CSV
  `download_button` must be `*_LIMIT.csv`/`*_ULT.csv`, route through an ULTIMATE
  channel (`sbeam_bridge`/`load_cases_csv`/`load_cases_to_rows`/
  `case_index_csv`), or sit on the explicit non-load allowlist (geometry,
  speeds, mass-properties tables). A new page adding an unmarked load CSV fails
  the suite.
- Docs: `PROGRAM_SPEC.md` limit-vs-ultimate scope statement and
  `GUI_design.md` LIMIT-marking convention both extended with the in-band
  download rule and the guard test.

**Test / Acceptance.** Suite green (**500** passed, +1), `ruff` clean (incl.
`app/`), self-runners pass. Shape tests extended (`Basis` key + all-rows-LIMIT
assert); both edited pages render clean under headless `AppTest` on the GA
fixture. No calc/schema change (`SCHEMA_VERSION` stays 33); the SI display
converters spread `**r`, so the new string column passes through untouched.

**Key decisions.**
- *Both buttons* (user decision): keep the LIMIT download (the oracle
  cross-check artifact matching the on-page table) **and** add the ULTIMATE twin
  from the bridge, rather than replacing one with the other.
- *Basis column lives in the canonical row helpers*, not the views — the basis
  travels with the rows wherever they are rendered next.
- *Source-scan guard over a runtime test* — cheap, page-agnostic, and fails at
  the moment a new unmarked load CSV is added, which is when the author has the
  context to fix it.

---

## M4-14 — Validate `safety_factor` on load (defect, correctness, complete 2026-07-23)

**Objective.** The five `io.py` readers added by M4-7 took
`d.get("safety_factor", ULTIMATE_FACTOR)` with no type or range check, and the
field is persisted in `project.json` and hand-editable (Project JSON Editor page
or the file directly). Verified failure modes: `"safety_factor": null` →
`TypeError` out of `body_span_load_csv` (breaking the lenient-reader contract);
`"safety_factor": 0.5` → every exported card silently **under-scaled while still
labelled ULTIMATE** — the worst failure mode in the suite, and reachable on the
headless `cli.py --export-sbeam` path where no GUI warning can surface. From the
2026-07-23 M4-7 review (MAJOR); second item of the M3 release gate. **Policy
locked with the user 2026-07-23:** the legal band is **[1.0, 1.5] inclusive**,
per case, owned by the load-case definition (14 CFR 23.303; a case already at
ultimate is 1.0, an agreed 23.302/25.302 failure-case factor lies between) —
anything else is corrupt.

**Deliverables.**
- **`io._safety_factor(d)`** — one shared coercion helper replacing all five
  `d.get(...)` sites: anything non-numeric (null, string, bool, NaN/inf) **or
  outside [1.0, `ULTIMATE_FACTOR`]** falls back to the conservative
  `ULTIMATE_FACTOR` default (not clamped to the nearest bound — an out-of-band
  value is treated as corrupt, and coercing a high value *down* or a low value
  *up to 1.0* would silently trust corrupt data). Read-time coercion is what
  makes the headless CLI path safe, not just the GUI.
- **`validation.safety_factor_valid(value)`** — the public shared predicate
  (public because `app/` must not import underscore names, M4-12), used by the
  reader, the new check and the JSON editor.
- **`validation._check_safety_factors`** — advisory `safety_factor_out_of_range`
  `ConsistencyWarning` (one per offending case, case named in the message)
  scanning `envelope.critical.conditions` plus all six `Project.loads` families;
  new `PAGE_EXPORT = "export_report"` tag, rendered by the Export page (which
  previously rendered no consistency warnings). Catches in-session/programmatic
  values — a corrupt *persisted* value is coerced before validation ever sees it.
- **Project JSON Editor** — Apply now scans the **raw** edited dict (recursive
  `_bad_safety_factors` walk) and warns, per field path, that an invalid value
  was reset to 1.5: `project_from_dict` has already coerced by the time the
  project is built, so only the raw dict can show what the user typed.
- No schema change (`SCHEMA_VERSION` stays 33 — readers got *more* lenient).
  Docs: `PROGRAM_SPEC.md` "Read-side validation (defect M4-14)" bullet,
  `GUI_design.md` §8.3, `validation.py` docstring check list.

**Test / Acceptance.** Suite green (**499** passed, +6), `ruff` clean (incl.
`app/`), both no-pytest self-runners pass. `tests/test_io.py`: corrupt fixtures
(null / `"1.25"` string / `True` / NaN / inf / 0.5 / −1.5 / 0 / 0.999 / 1.6)
each coerce to 1.5 across all five readers; the legal band (1.0/1.25/1.5) loads
verbatim; the exact null-then-`body_span_load_csv` repro no longer raises.
`tests/test_validation.py`: `safety_factor_out_of_range` fires per case with the
right page tag for 0.9 and 2.0, is silent across [1.0, 1.5], plus direct
predicate coverage; the GA fixture stays warning-free (the module's documented
invariant). GA path unchanged.

**Key decisions.**
- *Coerce-to-safe-default over warn-only or hard-reject* (user-ratified D1):
  warn-only leaves the CLI export emitting under-scaled ULTIMATE cards with no
  human in the loop; hard-reject bricks a saved project over one field. Coercion
  keeps every deliverable conservative and the file loadable; the warnings
  explain what happened.
- *Band is [1.0, 1.5] inclusive, both sides enforced* (user decision 2026-07-23:
  "the safety factor can be any number between 1.0 and 1.5", set by the case
  definition). This supersedes the plan's earlier keep-with-warning treatment of
  values above 1.5 and the backlog's literal `(1.0 …` exclusive lower bound
  (SF = 1.0 is legal — `one_engine_out` ships such cases).
- *Warnings surface at the consequence (Export page) and the cause (JSON editor
  Apply)* — not on Results Review or the Dashboard, kept small (D2).

---

## M4-13 — Wing + control-surface producers mint the per-case safety factor once (defect, correctness/latent, complete 2026-07-23)

**Objective.** Finish what M4-7 started. M4-7 threaded the factor for the tail
and fuselage families only; `net_loads` (`WingLoadResult`) and
`aileron`/`flap`/`tab` (`ControlSurfaceLoadResult`) left their result slice
**and** their rendered `ConditionResult` to default `safety_factor`
*independently* — two sources of truth for the same case. Harmless while every
factor is 1.5, but the first non-default case (M4-8 Layer 1, or a 25.302 named
case) would make the rendered report and the exported FORCE/MOMENT cards
disagree — the exact failure M4-7 closed for tail/body. `PROJECT_GUIDE.md` §5
already asserted the stronger invariant ("minted by the module that owns the
condition and copied unchanged by everything derived from it"); this brings the
code up to the doc. Promoted from M4 to the M3 release gate (first item),
2026-07-23 consolidation; from the 2026-07-23 M4-7 review (MAJOR).

**Deliverables.**
- **`net_loads.build_net_loads`** mints the wing case's factor once per case
  (`sf = ULTIMATE_FACTOR`, the line M4-8's Layer-1 resolver will replace) and
  sets it on the **air, inertia and net** `WingLoadResult`s of that case — the
  three families describe the same case and are all accepted by the export's
  `ResultsArg` API. `run()` copies `r.safety_factor` onto each `ConditionResult`
  (the taildist pattern).
- **`aileron.build_aileron`** mints one shared factor for both throws (up/down
  can never diverge); **`run()` now consumes `build_aileron()`** instead of
  recomputing `aileron_loads` a second time — the rendered loads/speeds/pressures
  and the exported records now have a single source — and its `ConditionResult`
  gains the previously missing `case_ref` (the down-throw's) plus the copied
  factor.
- **`flap.build_flap` / `tab.build_tabs`** pass `safety_factor=ULTIMATE_FACTOR`
  explicitly at the mint site; each `run()` copies `case_ref` **and**
  `safety_factor` from the built result.
- No model/io/schema change: the fields shipped with M4-7 (`SCHEMA_VERSION`
  stays 33); `sbeam_bridge._sf()`'s `getattr` fallback now never fires for a
  project-produced result (its annotation cleanup is M4-16).
- Docs: `PROGRAM_SPEC.md` sbeam-bridge section gains a "Factor mint sites
  (defect M4-13)" bullet naming the mint per producer.

**Test / Acceptance.** Suite green (**493** passed, +2), `ruff` clean, the
no-pytest self-runner passes. Two new tests in `tests/test_sbeam_bridge.py`
(the acceptance shape of `test_taildist_and_body_copy_the_condition_factor`,
adapted because these four modules own their conditions and have no persisted
upstream to mutate): an **agreement test** asserting per-case equality between
every result slice (incl. `wing_air`/`wing_inertia`) and its rendered
`ConditionResult` on the GA fixture, and a **mutation test** that wraps each
module's `build_*` to force a 1.25 mint and asserts `run()`'s conditions carry
it — failing against the old independent-default code. **Numbers unchanged**
at SF 1.5 (full suite incl. the Appendix-A oracles p222/p200/p201/p202).

**Key decisions.**
- *Mint locally in `net_loads`* (option (a)): wing cases have no upstream
  `CriticalCondition` (their W- case-id band is disjoint from
  `envelope.critical`), and linking them upstream is M4-2's case-identity
  unification, kept out of scope. When M4-2 lands, the wing mint moves upstream.
- *Aileron keeps one `ConditionResult`* covering both exported throws (report
  shape unchanged); splitting it 1:1 with the export was deferred until after
  M4-9 de-strings the label lookups.
- *`wing_air`/`wing_inertia` carry the factor too*, not just `wing_net` —
  scoping to net only would recreate the two-sources problem for anyone
  exporting those families directly.

---

## M4-7 — sbeam export honours the per-case safety factor (defect, correctness/latent, complete 2026-07-23)

**Objective.** Close the double-factor trap in `export/sbeam_bridge`. The bridge
hardcoded a flat `_SF = ULTIMATE_FACTOR` at every scaling site and ignored
`ConditionResult.safety_factor`. The root cause sat one level deeper: the four
distributed-load result types the bridge consumes (`WingLoadResult`,
`BodyLoadResult`, `TailChordResult`, `ControlSurfaceLoadResult`) — and the
`CriticalCondition` upstream of two of them — carried **no** factor at all, so
there was nothing to read. Latent while every case is 1.5, but (a) a case already
at ultimate (`SF = 1.0`, per the CLAUDE.md ultimate-load contract) would be
multiplied by 1.5 a second time, and (b) a future 14 CFR 23.302 / 25.302 /
Appendix K probability-based factor (1.0–1.5) set on a failure case could reach
`report.py` but never the exported cards — the report and the deliverable would
disagree.

**Deliverables.**
- **`safety_factor: float = ULTIMATE_FACTOR`** added to `CriticalCondition`,
  `WingLoadResult`, `BodyLoadResult`, `TailChordResult` and
  `ControlSurfaceLoadResult` (`sloads/models/results.py`), each docstring stating
  that the stored station values are **LIMIT** and this is the factor the
  render/export boundary applies.
- **Producers propagate it:** `modules/taildist.py` and `modules/body_loads.py`
  copy the governing `CriticalCondition`'s factor into the slice they emit;
  TAILDIST's rendered `ConditionResult` carries the same value, so the report path
  and the export path are structurally incapable of disagreeing. The
  wing/control-surface producers have no upstream factor today and keep the
  default — the field is now the single place a future refinement sets it.
- **Bridge scales per result:** new module-private `_sf(result)` (a defensive
  `getattr` falling back to `_SF`) replaces all nine flat `* _SF` sites across the
  wing, fuselage, tail-chordwise and control-surface families. `_SF` survives only
  as the fallback default (and as the constant `tests/test_sbeam_bridge.py` reads).
- **Cards state the factor they used:** the four hardcoded
  `$ Loads are ULTIMATE (limit x 1.5)` comment lines, plus the two closure comments
  spelling out `1.5 x …`, now interpolate the applied factor (`limit x SF=<sf>`).
- **`SF` column** appended (last, so positional parsers are unaffected) to all four
  span/chordwise CSVs — the "every load case SHALL state its safety factor"
  mandate, mirroring `report.py`'s existing `SF` column.
- **Persistence:** the five `io.py` readers round-trip the field with a lenient
  `d.get(..., ULTIMATE_FACTOR)`. `SCHEMA_VERSION` 32 → **33**; bundled
  `examples/*.project.json` restamped. En route, fixed
  `_critical_condition_from_dict` silently dropping `CriticalCondition.note` on
  reload (it carried approved-correction provenance).

**Test / Acceptance.** Suite green (491 passed), `ruff check sloads/ cli.py` clean.
Six new tests in `tests/test_sbeam_bridge.py`: closure against *that case's* factor
for SF ∈ {1.0, 1.25, 1.5}; two cases with different factors in one export each
scaling by its own; the card header quoting the actual SF (and never `SF=1.5` when
the case is 1.0); the `SF` column present and correct on all four CSVs; and the
taildist/body producers copying a mutated `CriticalCondition.safety_factor`. Plus
`tests/test_io.py::test_safety_factor_round_trips_on_result_slices` (save/load
survival + the missing-key default). **Numbers unchanged:** the GA wing span CSV
load columns and the FORCE/MOMENT cards diff byte-identical against a pre-change
run — only the new `SF` column and the reworded `$` comment differ.

**Key decisions.**
- *Full propagation over a bridge-local patch.* A `getattr` in the bridge alone
  would have been a no-op (no result carried the field); wiring the 23.302 hook
  end-to-end is what actually closes the defect.
- *Factor stays per **case**, not per station.* Uniform within one exported load
  set, which is exactly what the C4 force/moment-closure guarantee requires
  (`sum(dFz) == safety_factor × root`).
- *`SF` appended last* in every CSV, so existing positional consumers
  (`app/views/export_report.py`, `export/workbook.py`, `cli.py`) are unaffected.

---

## M3-1 — Full rename `FAR23LOADS`/`farloads` → **`sloads`** + `models/` package split (decided 2026-07-20, complete 2026-07-23)

**Objective.** Retire the `FAR23LOADS`/`farloads` name — it is the exact mark of a
commercial product marketed by McGettrick Structural Engineering / DARcorporation
(`reference/FAR-23-Loads-Brochure-2023.pdf`), and the tool's identity is now a
concept-development tool extending beyond FAR 23. Adopt `sloads` (joining the
**sbeam** / **smodal** family) across package/import, CLI, GUI/brand, and docs,
**batched** (same churn event, per the 2026-07-21 review) with splitting the
1,862-line `models.py` monolith into a lifecycle-ordered `models/` package. Executed
per the step-by-step runbook
[`../30_future/04_m3-1_rename_procedure.md`](../30_future/04_m3-1_rename_procedure.md).

**Key decisions (2026-07-23 consultation).**
- *Display brand:* lowercase **`sloads`** (app `page_title`, dashboard title, README
  H1, package/module docstrings, doc-set H1 titles). The pyproject `description` and
  README/CLAUDE intros keep "*the FAR 23 LOADS suite (McMaster)*" as **attribution**,
  not rebranded.
- *sbeam export headers:* rebranded the `$ FAR23LOADS …` deck comments and `export/`
  axis-convention references to uppercase **`SLOADS`** (machine deck-tag), with
  `tests/test_workbook.py`'s `startswith("$ …")` assertion updated in lockstep.
- *History kept verbatim:* `CHANGELOG.md` and `docs/40_history/*` past entries retain
  their `farloads/…` path references (Keep-a-Changelog convention); the two
  point-in-time review docs (`PROJECT_REVIEW_2026-07-19.md`,
  `CODE_REVIEW_2026-07-21.md`) argue *about* the `farloads` name and are untouched.
- *Repo folder name* (`Loads_Programs/FAR23LOADS`) left as-is — out of scope (renaming
  it would break the local `.venv`/absolute paths); folder name ≠ package name.

**Deliverables (no calc/oracle/schema change — `SCHEMA_VERSION` stays 32).**
- **Package move:** `farloads/` → `sloads/` (history-preserving `git mv`).
- **`models/` package split:** `models.py` → `sloads/models/{enums,inputs,results,project}.py`
  + a re-exporting `__init__.py` (each submodule with an explicit `__all__`; 72 public
  names). Dependency order enums → inputs → results → project; every prior import form
  (`from sloads.models import X`, the `sloads/__init__.py` re-export block) resolves
  unchanged. Split done AST-deterministically and verified byte-identical (68 defs, 0
  missing/extra/different).
- **Import rewrite:** mechanical `farloads` → `sloads` across ~100 `.py` files
  (imports, attribute paths, Sphinx xrefs, the `farloads_io` alias). Registry
  `MODULE_NAME` values, JSON schema keys and session-state keys carry no `farloads`
  token — saved projects load untouched.
- **`pyproject.toml`:** `name`, `[project.scripts]` (`sloads = "cli:main"`),
  `packages.find include`, `--cov=sloads`, `[tool.coverage.run] source`.
- **Brand strings:** `app/Home.py` (docstring + `page_title`), `app/views/dashboard.py`
  title, README H1, `sloads/__init__.py` docstring → `sloads`; seven doc-set H1 titles
  (`00_INDEX`, `PROGRAM_SPEC`, `PROJECT_GUIDE`, `RELEASE_PROCESS`, `GUI_design`,
  `00_program_overview`, `CODE_REVIEW_PROCESS`) → `sloads`.
- **Docs / CI / scripts sweep:** 17 living docs, `.github/workflows/ci.yml`
  (`ruff check sloads/`), `scripts/smoke_test.sh`, `.claude/settings.local.json`,
  `docs/generate_data_dict.py`, and the generated `DATA_DICTIONARY.md` regenerated.
- **Reinstall:** deleted stale `farloads.egg-info`, `pip install -e '.[dev]'` →
  `sloads 0.2.0`; `sloads --list` prints all 21 modules.

**Test / Acceptance.** Full suite green (**483 passed**, ~93% cov); `ruff check
sloads/ cli.py app/` clean; `scripts/smoke_test.sh` exit 0 (headless GUI HTTP 200, no
traceback, under the new name). Acceptance grep proves **zero** `farloads`/`FAR23LOADS`
in any `.py`/`.toml`/`.yml`/`.sh`; every remaining brand token is an intended keep
(the "FAR 23 LOADS suite/manual" attribution family, the DARcorporation disclaimer, the
kept-verbatim history/review docs, and the repo-folder path). Disclaimer present in
README and the GUI About.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M3-1 removed (its D-6
decision-log row and the `01_concept_loads_plan.md §7` naming note reconciled to point
here). Supersedes decision **D-6** (2026-07-16 "keep FAR23LOADS"). Feeds **M3-2** (the
`sloads 0.3.0` release cut).

---

## M2R-8 — MissingInputError in the registry + single SELECT envelope build (2026-07-21 review, MAJOR, complete 2026-07-22)

**Objective.** `registry.run_all_modules` caught *every* `ValueError`, so a genuine
calc defect in a module vanished from run-all/export, indistinguishable from "inputs
not entered". Distinguish the two so defects surface while incomplete-project modules
still skip. The existing error-handling contract
(`docs/10_standard/00_program_overview.md`) already drew the line ("required slice
absent → skip" vs "invalid domain input → surface"); this formalizes it in code.

**Key decisions (2026-07-22 consultation).**
- *Classification (borderline guards):* "present but not yet filled in" — an empty
  required list, or an absent required **upstream** slice/named surface — is treated as
  **not-ready → `MissingInputError` → skip**, preserving run-all's tolerance of
  partially-built projects. Only genuinely malformed/contradictory data (`<2` cylinders,
  non-positive area/weight/MC/MD, `>=2` element/point counts, out-of-range index,
  exactly-3-CG-cases, aero-surface-with-no-matching-geometry, an unknown V-n case
  reference) stays a plain `ValueError` and now surfaces.
- *Scope:* both parts — the `MissingInputError` core **and** the "while in the area"
  SELECT single-envelope-build refactor.

**Deliverables (no calc/oracle change).**
- `farloads/models.py` — `class MissingInputError(ValueError)`; exported from
  `farloads/__init__.py`.
- `farloads/registry.py` — `run_all_modules` catches **only** `MissingInputError`;
  a plain `ValueError` propagates.
- The 21 modules — input-absence guards converted from `raise ValueError` to
  `raise MissingInputError` (slice `None`, absent upstream result/geometry/aero slice,
  empty required list); malformed-data guards left as `ValueError`.
- `farloads/modules/select.py` (Part 2) — `_envelope` is the single fallback site
  (raises `MissingInputError` when no V-n matrix is obtainable); every `select_*`
  helper (`select_wing`/`select_htail{,_balancing,_maneuver,_gust}`/`select_vtail`/
  `select_fuselage`/`_stamp_case_refs`) takes an optional `envelope=` parameter
  resolved by `_resolve_envelope`; `build_critical` builds it **once** and threads it
  in — was up to 7 rebuilds. Backward-compatible: `body_loads.select_fuselage(project)`,
  `balloads._envelope(project)` and the tests keep the `(project)` form.
- `docs/10_standard/00_program_overview.md` — error-handling contract table updated to
  name `MissingInputError` and the surface-vs-skip split.

**Test / Acceptance.** New `tests/test_registry.py`:
`test_missing_input_error_is_value_error`; `test_run_all_skips_missing_input_but_propagates_value_error`
(a `MissingInputError` module skips, a genuine `ValueError` propagates out of run-all);
`test_run_all_skips_all_modules_on_engine_only_project` (the ~21 guards are complete);
`test_build_critical_builds_envelope_once` (spies `build_envelope`, asserts exactly 1
call). Full suite green (483 passed); ruff clean; suite runtime dropped (~44s → ~27s)
from the removed rebuilds. SELECT oracles unchanged.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M2R-8 removed (M2R section
now complete — all eight items in history).

---

## M2R-7 — io.py tolerant readers: unknown fields no longer crash load (2026-07-21 review, MAJOR, complete 2026-07-22)

**Objective.** Make good on `schema_status()`'s forward-compat promise ("unrecognized
fields are ignored"). A project file carrying one field this app version doesn't know
(saved by a newer/older build, or hand-edited) crashed load with e.g.
`MassItem.__init__() got an unexpected keyword argument …` because ~21 `*_from_dict`
readers splatted the raw dict (`cls(**d)`) straight into the dataclass constructor.
Matters for release users sharing files across app versions.

**Deliverables (no schema or calc change).**
- `farloads/io.py` — one shared `_filtered(cls, d)` helper (keep only keys that are
  fields of dataclass `cls`) routed through **every** `*_from_dict` splat: the raw
  splats (`_case_ref`, `engine`, `_mass_item`, weight `estimation`/`envelope`/
  `cg_cases`, `_legacy_cg_cases_from_flight_loads`, `speeds`+`mach_limit`,
  `flight_loads` cg_cases, `_critical_condition` loads, `_vn_point`, `envelope`
  tail_balance, `mass`, `fuselage_mass`, `wing_mass` concentrated/cases, and the
  wing/body/tail/control station-load result readers) **and** the pre-existing ad-hoc
  `{k: v … if k in fields}` comprehensions (select/tail/vtail/oeo/gear/landing/
  aileron/flap/tab/configuration), which now call the shared helper. Explicit-key
  readers (`.get(...)`) were already tolerant and unchanged.

**Test / Acceptance.** `tests/test_io.py`: `test_unknown_field_in_every_ga6_slice_is_ignored`
recursively injects an unknown key into every dict (all depths, incl. list items) of
the serialized `ga6_normal` and asserts it loads and re-serializes identically (garbage
dropped); `test_unknown_field_in_every_result_slice_is_ignored` does the same for a
project augmented with the result slices ga6 lacks (envelope/mass/loads/one_engine_out
with nested VnPoint+CaseRef, CriticalCondition+LoadValue, the four station-load
families). Full suite green (479 passed); ruff clean.

**Key decision.** Minimal tolerant-read guard now (unblocks cross-version file sharing
for the release); the full migration-chain overhaul — per-version `MIGRATIONS` hops +
one frozen fixture per historical schema + a fields-hash version-bump gate — stays
**M4-10** (pre-F25), which now builds on this helper.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M2R-7 item and its
Known-defects bullet removed; M4-10 note updated to reference the shared readers.

---

## M2R-6 — Geometry Apply: validate before persisting (2026-07-21 review, MAJOR, complete 2026-07-21)

**Objective.** The **Geometry** page's sidebar *Apply geometry* button did a
wholesale replace of `Project.geometry.parametric` with no validation. Applying an
invalid wing (e.g. Area S = 0) stored it, then `configuration_properties` in the
page body raised (`wing_planform` requires positive area/AR) and the
`try/except → st.error + st.stop()` blanked everything below — including the
*unrelated* empennage / landing-gear / fuselage-outline / surfaces forms, which live
past that `st.stop()`.

**Deliverables (GUI-only; no calc or schema change).**
- `app/views/configuration_layout.py` — new `_layout_errors(layout)` helper (positive
  wing area, aspect ratio, taper λ) run on the candidate `LayoutInput` **before**
  `_set_geometry`. An invalid Apply is rejected with a targeted `st.error` listing the
  offending field(s) and is **not** persisted; the last valid layout survives, so the
  page body and the downstream forms keep rendering. A valid Apply is unchanged.

**Key decision.** Chose *reject-before-persist* over *persist + warn*: never store a
layout that would crash the geometry-derived consumers (three-view, assessment,
downstream seeds, exports), so the invalid value cannot propagate to other pages or a
saved file.

**Test / Acceptance.** New `tests/test_configuration_layout_view.py` drives the page
via `AppTest`: setting Area S = 0 and pressing Apply leaves
`geometry.parametric.wing_area_sqft` unchanged, shows a "not applied" error, and the
`Apply empennage` / `Apply landing gear` buttons still render (page not blanked); a
valid edit (S = 200) still persists. Full suite green (477 passed); ruff clean.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M2R-6 removed.

---

## M2R-5 — GUI editors for the blocking uncovered fields (2026-07-21 review, MAJOR, complete 2026-07-21)

**Objective.** Two inputs that govern the results had **no on-screen widget** —
editable only by hand-editing `project.json`: (a) `landing.cg_cases`, the three
distinct landing loadings LANDLOAD requires (aft-max / fwd-max / fwd-light); (b)
`SelectInput.full_down_aileron_deg` / `basic_airfoil_cm` / `wing_weight_lb`, which
drive the 23.349(b) steady-roll wing-torsion score and the critical-fuselage wing
weight and defaulted silently (0 / 0 / 0.09·MTOW).

**Key decision (2026-07-21 consultation).** Seed the landing CG editor from the
**WTENV structural CG envelope**, not `project.mass.cases` as the backlog literally
said: `weight_onecg.build_mass` emits only **one** `MassCase` ("itemized loading"),
so `mass.cases` cannot supply three *distinct* fwd/aft/light rows (the very
degeneracy M2-8 removed auto-derivation to avoid). WTENV gives the fwd-most/aft-most
structural CG stations (`validation.wtenv_cg_limits`) plus the gross /
fwd-regardless weights; the waterline comes from the itemized loading when present.
The fwd/aft split is a seed the engineer confirms (WTENV cannot distinguish it per
loading).

**Deliverables (no schema change; `SCHEMA_VERSION` stays 32).**
- `app/views/landing_loads.py` — a fixed 3-row `st.data_editor` (`_seed_cg_rows`
  helper) in the page form; Apply writes `landing.cg_cases`; the hard "provide
  WTONECG results or edit the JSON" gate replaced by an in-place info until three
  positive-weight rows are applied.
- `app/views/flight_envelope.py` — a `_select_inputs_form` (`st.expander` + form) on
  the Critical Loads tab for the three `SelectInput` fields, each with `help=`;
  Apply writes `project.select_input`.
- `farloads/validation.py` — promoted `_wtenv_cg_limits` → public
  `wtenv_cg_limits`; re-pointed the existing `app/views/weight_mass.py` importer
  (removes one `app/`-imports-`farloads`-underscore violation — partial M4-12).

**Test / Acceptance.** `tests/test_dirty_flag.py`: `landing_loads.py` added to the
render-leaves-project-unchanged parametrization (both new forms persist only on
Apply); `test_landing_cg_editor_seeds_and_persists_on_apply` (WTENV seed → Apply →
3 CG cases at the fwd/aft stations & gross/fwd-regardless weights);
`test_select_inputs_persist_only_on_apply` (DN / Cm / WW → Apply →
`project.select_input`). Full suite green (475 passed); ruff clean. No calc change —
the SELECT/landing oracles are untouched.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M2R-5 removed and the
M4-12 note updated for the `wtenv_cg_limits` promotion.

---

## M2R-4 — Kill the last on-render Project mutation (2026-07-21 review, MAJOR, complete 2026-07-21)

**Objective.** Make rendering the **Landing Loads** page non-mutating.
`landing.build_landing()` wrote three things back onto the live `Project` on every
render — gear geometry synced from `geometry.landing_gear` onto `project.landing`,
the derived gross-weight default (`gross_weight_lb`), and the LGFACTOR result
(`n`) — so merely opening the page flipped 🟠 *Unsaved changes* (the last G4
residue, verified by per-page bisection) and `run()` was impure in the calc layer.

**Deliverables (`SCHEMA_VERSION` 31 → 32).**
- `farloads/modules/landing.py` — replaced the mutating `_sync_gear_from_geometry`
  (returned `None`, wrote onto `project.landing`) with the pure
  `_effective_gear_input(project, inp)`, which returns a `dataclasses.replace` copy
  carrying the single-source `geometry.landing_gear`. `build_landing` resolves the
  gear geometry **and** the heaviest-CG gross-weight default onto that local
  effective copy and passes it to `landing_reactions`; the `inp.n =` write-back is
  deleted (N is already returned on `LoadFactorResult.airplane_load_factor`).
- `farloads/models.py` — removed the redundant write-back `LandingInput.n` field
  (a mirror of the returned load factor that nothing consumed); updated the
  `LandingInput`/`LandingGearGeometry` docstrings and the `SCHEMA_VERSION`
  changelog comment (v32).
- `examples/*.project.json` — bumped `schema_version` 31 → 32 and dropped the dead
  `"n"` key from the `landing` block (data-only; loads are byte-identical).
- `docs/10_standard/DATA_DICTIONARY.md` regenerated; `PROGRAM_SPEC.md` LGFACTOR/
  LANDLOAD **Writes/Reads** rows updated (pure; effective-input copy, no
  write-back).

**Test / Acceptance.** New `test_landing.py::test_render_leaves_project_unchanged`
asserts `io.project_to_dict(p)` is unchanged after `build_landing(p)` + `run(p)`
(the exact `_has_unsaved_changes` predicate) on both the full GA-6 fixture and a
`gross_weight_lb = 0` project (the derived-default path). `test_landload_pipeline_and_run`
updated to read `lf.airplane_load_factor` instead of the removed `p.landing.n`. The
Appendix-A ground-load oracle is byte-identical
(`test_landloads_reactions_unchanged_bit_for_bit` unchanged — the math runs on an
identical effective input). Full suite green (467 passed); ruff clean.

**Key decisions.** `LandingInput.n` **removed**, not merely left unwritten — it was
a result-shaped duplicate of `LoadFactorResult.airplane_load_factor` with no
consumer; migration stays lenient (the tolerant `landing_from_dict` ignores an
older file's `"n"` key), so a `SCHEMA_VERSION` bump with no migration code suffices.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]` entry; backlog M2R-4 item and
its Known-defects bullet removed.

---

## M2R-3 — Ship working examples (2026-07-21 review, MAJOR, complete 2026-07-21)

**Objective.** Remove the red errors a first-time user meets when loading a
bundled example: **Fuselage Loads** hard-errored on the 5 examples missing
`fuselage_mass`, and **Landing Loads** hard-errored on `concept_regional_jet`
(2 of the required 3 `cg_cases`) and the examples with none.

**Key decisions (2026-07-21 consultation).** Widened the backlog's literal
two-edit scope after finding every example is also a **test fixture** (loaded
directly from `examples/`): (1) **complete five** examples to a clean end-to-end
run rather than the scoped two; (2) **remove nothing** — deletion would only
trade example-authoring for test-rewriting and lose category coverage; (3) keep
`concept_heavy` as the **deliberate minimal-core** fixture (it anchors
`test_concept.py`; no engines/select_input by design), documented as such.

**Deliverables (data-only; `SCHEMA_VERSION` unchanged at 31).**
- `examples/concept_regional_jet.project.json` — added the 3rd landing `cg_case`
  (`fwd light`, 26000 lb @ xcg 595).
- `examples/ga6_normal.project.json`, `examples/cessna_210.project.json` — added
  `fuselage_mass` (stations binned from the file's own non-wing weight items;
  centroid ≈ the airplane CG).
- `examples/dhc8_dash8.project.json`, `examples/atr42_100.project.json` — added
  `fuselage_mass`, a `landing` slice with 3 CG cases (fwd/aft from the wing MAC +
  weight-envelope pct-MAC limits), and `geometry.landing_gear` (main aft of the
  aft CG for tip-back; consistent ground plane).
- `docs/10_standard/GUI_USER_GUIDE.md`, `README.md` — a bundled-examples table;
  `concept_heavy` annotated as the minimal concept core (V-n → Flight Envelope).
- Three fixture-coupled tests updated to the completed state:
  `test_body_loads.py` (clears `fuselage_mass` locally to still exercise the
  guard), `test_io.py` (GA6 now runs `body_loads` in run-all), `test_workbook.py`
  (a module with an empty cases-CSV, like `body_loads`, gets no module sheet).

**Test / Acceptance.** All five completed examples run `body_loads` + `landing`
and `run_all_modules` with no missing-slice error; the sbeam fuselage span CSV
exports for each; `concept_heavy` stops cleanly at Flight Envelope. Full suite
green (466 passed); ruff clean.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]` entry; backlog M2R-3 item and
its Known-defects bullet removed.

---

## M2R-2 — Non-affiliation & attribution sentence (2026-07-21 review, MAJOR, complete 2026-07-21)

**Objective.** State plainly, in both the README and the GUI, that this project
is an independent open replication and is **not affiliated with** the vendor of
the commercial "FAR 23 LOADS" product — legal-exposure mitigation, decoupled
from the M3-1 rename ("immediately, regardless", per the 2026-07-19 review).

**Deliverables.**
- **`README.md` Disclaimer.** Reworded the opening to "modern **open
  replication** of the FAR23 loads suite (DOT/FAA/AR-96/46; Hal C. McMaster's CAE
  theory manual)" and added a dedicated paragraph: **not affiliated with,
  endorsed by, or associated with McGettrick Structural Engineering, Inc. or
  DARcorporation**, whose "FAR 23 LOADS" is a separate commercial product.
- **`app/Home.py` sidebar.** Added an app-wide **ℹ️ About** expander plus a
  one-line footer caption, built once in the sidebar block so they appear on
  every page under `st.navigation`. The About text carries the open-replication
  description, the not-certified caveat, and the same non-affiliation sentence.

**Test / Acceptance.** Documentation/GUI-copy only — no calc/schema/test change.
`app/Home.py` compiles and passes `ruff`; the About/footer render in the sidebar
on every page.

**Key decisions.** Placed the GUI notice in the **sidebar** (built once in
`Home.py`) rather than per-view, so it shows app-wide with no per-page
duplication; kept it collapsed in an expander plus a persistent one-line footer.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]` Documentation entry; backlog
M2R-2 removed.

---

## M2R-1 — Doc currency sweep (2026-07-21 review, 1 CRITICAL + 3 MAJOR, complete 2026-07-21)

**Objective.** Retire the stale and contradictory documentation the 2026-07-21
code & documentation review flagged, so no shipped doc asserts a false schema
version or oracle-lock claim.

**Key decisions (2026-07-21, user-confirmed).** (1) The stale `GUI_design.md`
schema line is fixed by **pointing at the generated `DATA_DICTIONARY.md`** (the
single source, currently v31) rather than re-baking a number that would rot at
the next bump. (2) The `CLAUDE.md` oracle-lock sweep fixes the three cited lines
**plus** a grep-sweep for exact duplicates; the "Appendix A **and/or** B"
per-module test convention and the frozen `40_history` record are correct and
left untouched.

**Deliverables.**
- **(a) `docs/10_standard/GUI_design.md`.** Replaced `SCHEMA_VERSION = 28` + its
  baked migration trail with a pointer to `DATA_DICTIONARY.md` (v31) and the
  per-step history in `40_history/`.
- **(b) `CLAUDE.md`.** Retired the "Appendix A/B ±0.1%" oracle-lock claim at
  `:19`/`:28`/`:189` → "Appendix A ±0.1%; twin cases closure-locked", linking the
  Oracle-status anchor in `00_theory_sources.md#oracle-status` (Appendix B is not
  in the bundled scan). Repo-wide grep confirmed no remaining exact dupes of the
  false present-tense claim.
- **(c) `docs/10_standard/PROGRAM_SPEC.md`.** Filled the schema-version trail —
  inserted **v29** (single-source CLmax stall, M1-1b), appended **v31** (M2-10
  operational placards).
- **(d) Cross-doc currency.** `00_INDEX.md`: added rows for
  `01_far25_gap_analysis.md` and `01_verification_baseline_0.2.0.md`, enumerated
  the `reference/` CFR/AC text extracts, and replaced the "two-phase plan"
  backlog description with the M2R→M3→M4→F25 milestone structure.
  `00_theory_sources.md`: corrections-register pointer `CLAUDE.md` →
  `02_approved_corrections.md`. `README.md`: examples line → all six fixtures
  (added `atr42_100`, `concept_regional_jet`).

**Test / Acceptance.** Documentation-only — no calc/schema/test change,
`SCHEMA_VERSION` stays 31. Re-grep shows no `SCHEMA_VERSION = 28`, no false
"Appendix A/B ±0.1%" oracle-lock assertion, and no orphaned docs in `00_INDEX.md`.
Suite unaffected (no code touched).

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]` Documentation entry; backlog
M2R-1 removed.

---

## M2-11 — Input data dictionary + short GUI user guide (review D4 part 1, complete 2026-07-20)

**Objective.** Give the project two missing references: a `project.json` **data
dictionary** (the schema is `SCHEMA_VERSION` 31 deep and `models.py` was its only
reference) and a task-oriented **GUI user guide**.

**Key decisions (2026-07-20, user-confirmed).** (1) The data dictionary is
**generated by an introspection script**, not hand-written — type/default from
`dataclasses`/`typing.get_type_hints`, units parsed from each field's inline
comment (suffix fallback). (2) Owning-page / consuming-modules columns are
**slice-level** (the honest granularity `workflow.py` records), not per-field.
(3) **Input slices only** (result slices `envelope`/`mass`/`loads` excluded).
(4) The user guide is written **brand-neutral now** and takes a rename pass at
M3-1 rather than being deferred.

**Deliverables.**
- **`docs/generate_data_dict.py`.** Introspects `farloads.models` Project input
  slices → `docs/10_standard/DATA_DICTIONARY.md`: per-slice map (type, owning
  page, consuming modules from a source scan, role) + one field table per input
  dataclass (field, type, units/notes, default) + an enums appendix. Owning page
  from `workflow.py` `produces` plus a small override table for slices workflow
  doesn't attribute; consumers from a word-bounded `.<slice>` scan of
  `farloads/modules/*.py`.
- **`docs/10_standard/DATA_DICTIONARY.md`** (generated, 581 lines).
- **`docs/10_standard/GUI_USER_GUIDE.md`.** Workflow phases + page map, the
  seed chain, what-to-enter-where tour, LIMIT-vs-ULTIMATE reading rules, the
  `ga6_normal` end-to-end walkthrough with four hand-checkable numbers
  (WTESTIMA MTOW 3468, WTONECG XBAR 84.99936 / IYY 2058.209, STRSPEED n₊ 3.8 /
  VA 121.3, FLTLOADS MAN A NZ 3.80) traced from the 0.2.0 verification baseline.
- **`docs/00_INDEX.md`.** Both new docs indexed under 10_standard.

**Test / Acceptance.** `tests/test_data_dictionary.py`: committed doc equals the
generator output (drift guard — a schema change that skips regeneration fails
CI), every input slice documented, schema version recorded. Full suite green
(466 passed); ruff clean on `docs/generate_data_dict.py`.

**Docs.** This entry; `CHANGELOG.md` `[Unreleased]`; backlog M2-11 removed.

---

## M2-10 — Operational-speed linkage on the Design Speeds page (all three tiers, complete 2026-07-20)

**Objective.** Make the Design Speeds page explain and surface how the structural
design speeds (Subpart C) bound the eventual **operating limitations / cockpit
placards** (Subpart G) — advisory only, no loads-math change.

**Key decisions (2026-07-20, user-confirmed).** (1) **All three tiers ship now**
(Explain + Derive + Constrain), closing M2-10 before the 0.3.0 cut. (2) **Both
placard families are always shown** in the Derive advisory — the recip yellow-arc
set (VNE/VNO/MNE) and the turbine VMO/MMO set — each captioned with when it
applies, rather than inferring one from project data. (3) **Targets are warn-only:**
an infeasible operational target produces a concrete warning and never mutates a
design speed or blocks Apply (display/validation only).

**Reference (mandatory consult).** New `reference/14CFR_operating_limitations.md`
(web-verified 2011 CFR ed.): 14 CFR 23.1505(a) VNE ≤ 0.9·VD; 23.1505(b) VNO ≤
min(VC, 0.89·VNE); 23.1511 VFE ≤ VF; and Ref 1 p47 (`code.txt` 4147–4152) for
VNE/MNE = 0.9·VD/MD, the yellow arc, and the turbine/23.335(b)(4) VMO/MMO ≤ VC/MC
rule. MC→MD 0.05 Mach margin per 23.335(b)(4)(ii) (`14CFR_MC_MD_speed_margin.md`).

**Deliverables.**
- **`farloads/modules/structural_speeds.py`.** `operational_placards(ds)` →
  `OperationalPlacards` (VNE=0.9·VD, VNO=min(VC, 0.89·VNE), MNE=0.9·MD, VMO=VC,
  MMO=MC, VFE=VF); `operational_target_checks(inp, ds)` → `List[TargetCheck]`
  inverting the ladder into required design minima; `operational_implications(
  project, inp)` → the advisory `ConditionResult`s (both families + optional
  feasibility). No load quantity involved, so plain (non-`ULT`) units.
- **`farloads/models.py`.** `StructuralSpeedsInput` gains `no_yellow_arc` +
  `target_vne`/`vno`/`vmo`/`mmo`/`vfe`; **SCHEMA_VERSION 30 → 31** (lenient — older
  files lack the keys and take the defaults; io round-trips via `asdict`/`**d`).
- **`farloads/validation.py`.** `_check_operational_targets` emits the
  `operational_target_infeasible` warning (page `structural_speeds`) so infeasible
  targets also surface on the dashboard.
- **`app/views/structural_speeds.py`.** Explain expander (constraint ladder +
  citations); optional operational-target inputs on the form (turbine flag + the
  five targets); read-only "Operating-limitation implications (advisory)" panel
  rendering the placards, feasibility and any infeasibility warning.
- **Examples.** All six fixtures bumped to `schema_version` 31 (pure metadata).

**Test / Acceptance.** `tests/test_structural_speeds.py`:
`test_operational_placards_ga6` (VNE 191.25, VNO 170, MNE 0.363, VMO 170, MMO
0.3226, VFE 105.5 within ±0.1%), `test_operational_implications_shows_both_families`,
`test_operational_target_feasible_and_infeasible`, `test_operational_target_mmo_margin`.
`tests/test_validation.py`: `test_operational_target_infeasible_fires`,
`test_operational_target_feasible_silent`. The M2-7 persistence field-coverage guard
round-trips the new v31 fields. Full suite green (463 passed); ruff clean.

**Docs.** `PROGRAM_SPEC.md` (STRSPEED reads/advisory writes + Notes),
`20_theory/00_theory_sources.md` (placard-ladder citations), this move,
`CHANGELOG.md`.

---

## M2-9 — `scripts/smoke_test.sh` portability (release-mechanics, complete 2026-07-20)

**Objective.** Make the release smoke test run under any install layout, not only a
project-local `.venv`.

**Problem.** The script hardcoded `$ROOT_DIR/.venv/bin/{python,streamlit,farloads}` and
guarded each with an `-x` executable check, so any machine that installed into a
differently-named venv, a conda env, or a `pyenv`/system interpreter failed the guard
immediately even with a perfectly good editable install.

**Key decisions (2026-07-20, user-confirmed).** (1) **Interpreter = venv-preferred with
PATH fallback** — honour an explicit `PYTHON` env override, else prefer
`$ROOT_DIR/.venv/bin/python` when present, else fall back to `python3`/`python` on PATH;
keeps the existing dev flow unchanged while unbreaking other layouts. (2) **Invoke through
the one resolved interpreter** — `"$PYTHON" -m streamlit run …` and `"$PYTHON" cli.py
engine …` replace the hardcoded `streamlit`/`farloads` binaries.

**Deliverables.**
- **`scripts/smoke_test.sh`.** Interpreter-resolution block (`PYTHON` override → `.venv` →
  PATH); the three-way `-x` guard collapses to one usable-interpreter check plus a single
  `"$PYTHON" -c 'import streamlit, farloads'` importability probe with a generalized
  `pip install -e .[dev]` hint; both invocation sites routed through `"$PYTHON"`.

**Test / Acceptance.** `bash scripts/smoke_test.sh` passes under the default `.venv`; the
PATH-fallback path verified via `PYTHON="$(command -v python3)" bash scripts/smoke_test.sh`
(both: Streamlit HTTP 200 + no traceback, CLI writes 3 load-case rows). Script-only change —
no calc, schema, or module touched; suite unaffected.

**Key decisions.** See above.

---

## M2-8 — Landing CG cases: require explicit distinct loadings + concept 23.473(g) floor (review — landing minor, complete 2026-07-20)

**Objective.** Remove the degenerate landing CG-case fallback and flag the FAR 23.473(g)
load-factor floors in concept mode.

**Problem.** `landing._cg_cases` auto-derived the "aft max landing" and "fwd max landing"
loadings from the **single heaviest** `Project.mass` case, so the two were byte-for-byte
identical (same weight, `xcg`, `zcg`). LANDLOAD's nose-gear and braked-roll reactions turn
on the fwd/aft `xcg` through the `AP/BP/CP` lever arms, so the degenerate pair
**under-predicted** those reactions whenever a project relied on the fallback. UG fig 18.2
uses three genuinely distinct loadings.

**Key decisions (2026-07-20, user-confirmed).** (1) **Require explicit `cg_cases`** —
stop auto-deriving entirely and raise a clear error unless three distinct loadings are
supplied (rejected the alternative of deriving fwd/aft from the WTENV envelope: it cannot
supply a per-corner weight or waterline, only the longitudinal station). The WTENV
structural fwd/aft CG limits (`validation._wtenv_cg_limits`) remain the intended *authoring*
source. (2) **23.473(g) floors → warn-only, concept mode.** A note on the LGFACTOR
condition when `N < 2.67` or `NLG < 2.0`, gated on `project.is_concept`; the computed
`N`/`NLG` are left untouched (Appendix-A 3.0951 / 2.4281 sit above the floors, oracle
unaffected).

**Deliverables.**
- **`farloads/modules/landing.py`.** `_cg_cases(inp)` (no longer takes `project`) requires
  a non-empty, exactly-three `cg_cases` and raises otherwise — the `Project.mass` fallback
  is gone. `run` appends the concept-mode 23.473(g) floor note when a load factor is short.
- **`tests/test_landing.py`.** `test_landing_requires_explicit_cg_cases` (empty `cg_cases`
  raises with a `cg_cases` message); `test_landing_473g_floor_warning_concept` (soft-strut
  GA gear drives `N`/`NLG` below the floors → the note appears in concept mode);
  `test_landing_473g_floor_not_warned_in_far23` (the same project in FAR23 mode is silent).
- **Docs.** `PROGRAM_SPEC.md` (LANDLOAD reads/notes), `20_theory/00_theory_sources.md`
  (473(g) floor + distinct-CG requirement), this move, `CHANGELOG.md`.

**Test / Acceptance.** Full suite green (457 passed), `ruff` clean. All six shipped
examples already carry explicit `cg_cases`, so none regress. Calc-local; no schema change.

---

## M2-7 — Step G7 — Persistence verification (G-3, complete 2026-07-20)

**Objective.** Verify (and lock) decision **G-3**: every input-bearing value lives on a
`Project` slice `io.py` round-trips, with no input data stranded in `st.session_state`;
save→reload of each example is a no-op.

**Audit result (already satisfied by the D5/G-series/M2-6 single-source work).**
(1) All six example projects are save→reload no-ops (JSON-normalized dict comparison).
(2) The only session_state keys the GUI writes are UI state — `project` (the canonical
store), `unit_system` (display preference), `_saved_project_snapshot` (the dirty-flag
baseline), `engine_sel` (the Engine Mount radio selection), the Project Editor's re-seeded
JSON text scratchpad, and Streamlit-managed widget keys — none holding un-persisted
airplane input. Transient in-form edits before **Apply** are the deliberate Form+Apply
design (M2-3/G-4), not a violation: the acceptance reads as *persistent* input data.

**Key decisions (2026-07-20, user-confirmed).** (1) **Completeness guard**, not just an
example no-op check: a field-coverage test constructs each input dataclass with every
field set to a distinct non-default sentinel (recursively, through nested dataclasses /
lists / enums), round-trips it through its `io` pair, and asserts every field survives —
so a field added later without `io` wiring fails the build. Intentionally-derived fields
(the M2-6 single-source set + the G6/G6b geometry moves) sit in a `DERIVED_NOT_PERSISTED`
allowlist, itself guarded against rename drift. (2) **Defer** the Streamlit `key=`+`value=`
display-freshness footgun (orthogonal to data persistence; no data is lost today) to the
L-8 long-tail UX batch.

**Deliverables.**
- **`tests/test_persistence.py` (new).** `test_every_example_save_reload_is_a_noop`
  (relocated from `test_derived_geometry.py`); `test_input_dataclasses_round_trip_every_field`
  (the completeness guard, with the recursive filler + `DERIVED_NOT_PERSISTED` allowlist);
  `test_derived_allowlist_entries_are_real_fields` (guards the allowlist against renames);
  `test_no_input_data_written_outside_project_session_state` (static scan of `app/` — every
  `st.session_state[...] =` write uses an allow-listed UI key, tripping a review when a new
  key appears).

**Test / Acceptance.** Full suite green (454 passed), ruff gate clean; the completeness
guard verified to catch a dropped field (removing an allowlist entry fails the test).

---

## M2-6 — Step G6c — Geometry single-source cleanup (wing + fuselage + power, complete 2026-07-20)

**Objective.** Close the remaining *softer* geometry/power double-entry the G6 audit
surfaced (after G6/G6b single-sourced the empennage and landing-gear geometry): the wing
scalars several downstream slices carried as independently-editable copies, the fuselage
length/width/height that duplicated the outline, and the weight-estimate power that
restated the engine list.

**Key decisions (2026-07-20, user-confirmed).** (1) **Wing → pure proxy, no override.**
`FlightLoadsInput.mac`/`wing_area_sqft`/`xw`/`zw`, `WingMassInput.dihedral_deg`/
`wrp_waterline`, `LandingInput.wing_area_sqft` derive from `Project.geometry`; not
persisted; GUI read-only. Rather than remove the dataclass fields (dozens of tests
construct these slices directly), they stay as a derived cache filled by a sync at calc
entry (mirroring `landing._sync_gear_from_geometry`), and fall back to the stored value
when no wing geometry is present (the STRSPEED pattern) so bare unit tests are unaffected.
(2) **Full fixture work now.** GA6 had no `geometry.parametric`, so ZW/dihedral/wrp had no
source; a parametric wing slice (wing scalars backed out of the WINGGEOM surface +
`root_waterline_z = 78.5`, `dihedral_deg = 6.0`) was added, and the real derivation
`ZW = wrp + Y_MAC·tan(dihedral)` implemented (GA6 87.734 vs the old stored 87.725, +0.01%,
inside the ±0.1% oracle band). (3) **Concept S drift accepted** — the RJ closure fixture's
reference area 500 re-baselines to the WINGGEOM strip integral 497.75 (no printed oracle).
(4) **Fuselage → outline sole editable**, `LayoutInput` L/W/H a derived read-only summary.
(5) **Power → derive from `sum(engines[].max_cont_hp)` + override toggle.**

**Deliverables.**
- **`farloads/derived_geometry.py` (new).** `wing_reference(project)` (the shared wing
  derivation, subsuming the three scattered copies in `structural_speeds`,
  `flight_envelope` and `landing`), `fuselage_summary(outline)`, and
  `sync_geometry_derived(project)` — called at the top of `build_envelope`/`trim_sweep`/
  `build_critical`/`build_body_loads`/`verify_balancing`/`build_wing_inertia`/
  `build_net_loads` and by `io.project_from_dict` after load.
- **`weight_estimate.resolve_max_continuous_hp(project)`** — engine-list total unless
  `override_max_continuous_hp`; `run` applies it; `estimate` itself unchanged.
- **`models.py`** — `WeightEstimationInput.override_max_continuous_hp` (default False);
  `FlightLoadsInput.merged()` drops the wing-geometry args; derived-field docstrings;
  `SCHEMA_VERSION` 29 → 30.
- **`io.py`** — `flight_loads_to_dict`/`wing_mass_to_dict`/`landing_to_dict`/
  `configuration_to_dict` drop the derived wing/fuselage fields; `from_dict` still reads
  them (migration); post-load `sync_geometry_derived`.
- **GUI** — Flight Envelope, Wing Loads, Landing show the wing geometry read-only;
  Geometry page shows fuselage L/W/H as a read-only summary of the outline (the outline
  the sole editable shape); Weight & Mass adds the engine-total caption + override toggle.
- **Fixtures** — all six examples migrated to schema 30 (GA6 gained the parametric slice;
  derived copies dropped).

**Test / Acceptance.** New `tests/test_derived_geometry.py` (wing derivation, sync,
no-persistence, no-geometry fallback, fuselage summary, power resolver). The
save→reload-no-op check now lives in `tests/test_persistence.py` (Step M2-7).
Updated `test_flight_envelope`/`test_io`/`test_empennage` for the
derived/dropped fields and the newly-running `configuration` module on GA6. Full suite
green (451 passed), ruff clean; Appendix A oracles bit-for-bit.

---

## M2-5 — Aircraft Comparison: surface-planform fallback + Develop-phase link (GUI fix, complete 2026-07-20)

**Objective.** Review finding **G7**: the Aircraft Comparison subject showed "None"
for W/S, wing area, span and aspect ratio on nearly every shipped example.
`_subject_from_project` (`aircraft_comparison.py`) read wing geometry only from
`geometry.parametric` (the `LayoutInput`) — area `parametric.wing_area_sqft →
speeds.wing_area_sqft`, AR `parametric.aspect_ratio` only, span back-derived from
`√(AR·area)`. But of the six shipped examples only `concept_regional_jet` carries a
parametric layout; the rest carry `geometry.surfaces` (WINGGEOM planforms), so AR and
span were `None` on every non-parametric example (and area/W/S `None` wherever
`speeds.wing_area_sqft` was also absent, e.g. `ga6_normal`). Also (G7 second half):
the fleet check lived in the **Export** phase, after the load analysis, when it is
most useful at *definition* time.

**Key decisions (2026-07-20, user-confirmed).** (1) **Surface-planform fallback with
area priority `parametric → surface → speeds`.** Add a `geometry.by_name("wing")`
fallback via `wing_geometry.surface_properties` (which yields **Total area** in²,
**Aspect ratio**, and **Span** in — full-planform figures), the same pattern
`flight_envelope.py:89-96` uses; AR and span use the surface as their sole
non-parametric source. The computed planform is trusted over the scalar
`speeds.wing_area_sqft`. (2) **Link, do not move.** Keep the page in the Export phase
(unchanged `workflow.py` order — `03_gui_rework_plan.md §4 Phase 6` placement holds)
and add a workflow-derived `page_link` from the Develop phase, so the single source
of navigation truth is untouched.

**Deliverables.**
- **`aircraft_comparison.py` — `_wing_surface_props(project)`** returns the WINGGEOM
  `wing`-surface properties keyed by label (`{}` on a missing/degenerate wing).
  `_subject_from_project` now resolves wing **area** `parametric → surface (Total
  area ÷ 144) → speeds`, **AR** `parametric → surface`, and sets
  `Subject.wingspan_ft` directly from the surface **Span** (÷ 12) instead of
  back-deriving it. The `Subject` constructor now receives `wingspan_ft`.
- **`weight_mass.py`** — a `components.workflow_page_link("aircraft_comparison")` at
  the top of the Weight & Mass Properties page (the definition-time point where
  MTOW/OEW/power are set), captioned as the fleet W/S / W/P check.

**Test / Acceptance.** Extended `tests/test_aircraft_comparison.py`:
`test_subject_geometric_axes_from_wing_surface` (GA-6 recovers area/W/S and the
Appendix-A wing AR 6.095 / span 33.5 ft from its planform with no parametric layout
and no `speeds.wing_area_sqft`); `test_area_priority_surface_over_speeds` (the
computed planform wins over the scalar `speeds.wing_area_sqft`); the existing
example/synthetic/no-MTOW tests still hold (parametric still wins where present).
Every shipped example now places fully on the fleet scatters. Presentation-only — the
reference fleet is never a FAR input, so no calc/oracle/schema change; `workflow.py`
step order unchanged. Full suite green (443 passed); `ruff` clean.

**Observation (not blocking, logged).** With the chosen `parametric → surface →
speeds` order, `atr42_100`'s wing-surface area (≈480 ft²) — a coarser WINGGEOM
planform — now supersedes its scalar `speeds.wing_area_sqft` (586.6 ft²), shifting
its displayed W/S. This is the intended "trust the planform" behavior; the underlying
fixture-area discrepancy is a data-quality item for the ATR planform, not a logic
defect.

---

## M2-4 — Results Review header tables: units, ULT marking, SF (GUI fix, complete 2026-07-20)

**Objective.** Review finding **G5**: the "Governing loads (SELECT)"
per-component tables on **Results Review** and the **Flight Envelope → Critical
Loads** tab hand-built each row as `row[lv.label] = round(lv.value, 2)` — dropping
`LoadValue.units`, the mandatory `-ULT` marker and the safety factor, and printing
literal `None`/NaN in the sparse cells where components carry different label sets.
The substantive bug: the shared `_display_loads` did only the Imperial→SI
conversion and **never applied the limit→ultimate factor**, so the headline an
engineer screenshots into a design review was showing **unmarked LIMIT loads as if
they were the deliverable** — violating the ultimate-output contract on a
consolidation page while contradicting the lower per-section tables (which render
correctly through `report.py`).

**Key decisions (2026-07-20, user-confirmed).** (1) **Flat SF 1.5 at the render
boundary.** `CriticalCondition` carries no `safety_factor` field, but every SELECT
governing condition is a standard limit flight-load (SF 1.5 per 14 CFR 23.303);
apply `constants.ULTIMATE_FACTOR` at the helper and show `SF 1.5` — no
`models.py`/`io.py`/`SCHEMA_VERSION` change. The per-case carrier is deferred to
**M4-8** (centralized two-layer SF policy), which is where a non-1.5 governing case
would first arise. (2) **One shared helper for both tables** so they can't diverge;
both render ULTIMATE.

**Deliverables.**
- **`report.py` public wrappers.** `ultimate_units(units, quantity="") -> str` and
  `to_ultimate(value, units, quantity="", sf=ULTIMATE_FACTOR)` — thin public
  exposures of the existing privates (`_ult_units`/`_ult`), keeping the
  limit→ultimate boundary owned by `report.py` (CLAUDE.md: applied "once, at the
  render/export boundary").
- **`report.governing_loads_table(conditions, system, sf=ULTIMATE_FACTOR)`.**
  Returns row dicts (pandas stays in the views). For a list of `CriticalCondition`,
  it converts each condition's `loads` to display units (the `_display_loads`
  unit-conversion path, factored out of the two views into `report.py`), builds one
  row per condition (`Condition`, `FAR`, `V-n case`, then one column per load label
  headed `f"{label} ({ultimate_units(units, quantity)})"`), scales load cells via
  `to_ultimate` and formats with `_fmt`, appends an `SF` column, and fills cells
  absent from a given condition with `"—"` across the column union.
- **Both views rewired.** `results_review.py` (headline) and `flight_envelope.py`
  `_tab_select` now call `governing_loads_table(...)`; the duplicated
  `_display_loads` in each view is deleted. Captions on both surfaces state the
  tables are ULTIMATE (`-ULT` + `SF`), and the unused `ConditionResult` import is
  dropped from `flight_envelope.py`.

**Test / Acceptance.** New `tests/test_results_review.py`: (a) a force column
header carries `-ULT` and its value is `limit × 1.5`; (b) dimensionless columns
(load factor NZ / CL) are unscaled with no `-ULT`; (c) every row's `SF` column is
`1.5`; (d) sparse cells render `"—"` with no `None`/NaN and every row spans the
full column union; plus a determinism check (both views, same helper → identical
table). Render-only — no calc/oracle/model/schema change (the calc still emits
LIMIT; Appendix A oracles untouched). Full suite green (441 passed); `ruff` clean.
Closes the last unmarked-LIMIT deliverable surface found by the review; dovetails
with **M4-8** (which will let `governing_loads_table` read `c.safety_factor`
instead of the flat `sf` argument).

---

## M2-3 — Dirty flag: move on-render writes into Apply handlers (GUI fix, complete 2026-07-20)

**Objective.** Review finding **G4**: `flight_envelope.py` and
`structural_speeds.py` mutated the project **on render** (auto-seeding
derived/defaulted sub-slices outside any Apply handler), so the sidebar's "Unsaved
changes" flag — `project_to_dict(p) != saved_snapshot` (`Home.py`) — tripped with
zero user edits and the discard-confirm dialog fired spuriously (reviewer: load
ATR-42 → "No unsaved changes"; three page-visits later → "Unsaved changes"). Root
cause: seeding a slice on visit violates the app's own **"Form + Apply, merge not
replace"** design principle (`03_gui_rework_plan.md §7`). All three written slices
(`flight_loads`, `speeds.mach_limit`, `envelope.critical`) round-trip through
`io.py`, so a render-time seed genuinely changed the persisted dict.

**Key decision (2026-07-20, user-confirmed): require an explicit Apply.** Persist
only on submit; compute the live diagram from an in-memory *effective* input.
Accepted consequence: visiting no longer seeds downstream slices — the engineer
clicks Apply once, and the existing downstream gates ("Define the flight-loads
inputs on the Flight Envelope (V-n) page first") now correctly mean "hit Apply".
No `SCHEMA_VERSION`/calc-math change; oracles untouched.

**Deliverables (the three write sites fixed; a fourth was already correct).**
- **`flight_envelope.py` — `flight_loads` (primary).** Wrapped the sidebar
  FLTLOADS geometry + reference Mach in `st.form("flight_geometry_form")` with an
  "Apply geometry & altitudes" submit. Each render builds `fl_effective =
  fl.merged(...)` locally; the page then computes from a **shallow-copy probe** —
  `session_project = project; project = copy.copy(session_project);
  project.flight_loads = fl_effective` — so the V-n / SELECT / trim tabs and
  `build_envelope`/`flt_run` see the effective input without mutating the saved
  project. `project.flight_loads` is written to the real `session_project` **only**
  on Apply. Dropped the redundant per-render `st.session_state["project"] =
  project`. (The page's calc modules were verified pure — no `project.X =`
  mutation — so the probe sharing the other slices by reference is safe.)
- **`structural_speeds.py` — `speeds.mach_limit` (primary).** The Speed–Altitude
  tab (`_tab_speed_altitude`) had **no form**: `max_operating_altitude`/`increment`
  were bare widgets and the `MachLimitInput` was persisted every render. Wrapped
  them in `st.form("mach_limit_form")` + Apply; the Mach-limit chart renders live
  from the local `inp`, and `speeds.mach_limit` persists only on submit. `axis_unit`
  stays outside the form (display-only). Mirrors the Design Speeds tab, whose form
  (`if applied:` at :212) was already the correct pattern.
- **`flight_envelope.py` — SELECT selection.** `_tab_select` reassigned the whole
  recomputed `critical` object every render (which could differ from stored even
  with no deselection). Now it writes **only** `selected_case_ids`, and **only when
  it differs** from the stored value, onto `project.envelope.critical` (shared with
  the saved project via the probe) — a no-op render leaves the project untouched;
  a real deselection dirties (correct).

**Test / Acceptance.** New `tests/test_dirty_flag.py`: (1) parametrized over both
views × all six example projects — an `AppTest` render with **no** widget
interaction leaves `project_to_dict(session_state["project"])` byte-for-byte equal
to the loaded project (12 cases); (2) positive path — clearing `mach_limit` /
`flight_loads`, rendering, then clicking the form's Apply persists the slice.
GUI-only; full suite green (**438 passing**, `ruff` clean); no calc/oracle/schema
change.

**Notes / follow-on.** Persistence-hygiene sibling of **M2-7** (Step G7 — full
save→reload no-op audit); M2-3 fixes the two known offenders, M2-7 verifies the
whole app. The `flight_loads` geometry-echo fields kept behind the form become pure
read-throughs under **M2-6** (G6c) — the form is where the override-behind-a-toggle
pattern will live.

---

## M2-2 — Navigation: show the whole workflow; link between pages (GUI fix, complete 2026-07-20)

**Objective.** Two review findings, one step. **G3:** half the workflow — phases
3–6, *including Export* — was collapsed behind a "View 10 more" expander in the
sidebar on first run. **G6:** the app had zero `st.page_link`s; the dashboard
checklist and every "define X on the Y page first" gating message were dead text,
and two messages named pages that the Step-G1 geometry merge had renamed away
("Wing Geometry", "Configuration & Layout"). Display/navigation only — no
calc-math and no schema change; `farloads/workflow.py` stayed the single source of
navigation truth.

**Deliverables.**
- **(a) Root-cause link helper (`app/components.py`).** `workflow_page_link(key,
  *, label, icon, help, disabled)` renders an `st.page_link` to `views/<key>.py`
  with the label defaulting to the step's canonical `wf.BY_KEY[key].title` — so a
  page rename re-labels every link automatically and stale hand-typed names can't
  recur (the G6 root cause). `gate(message, *keys, kind="warning"|"info")` renders
  the notice plus one link per unblocking page. The helper degrades to a
  non-clickable `st.markdown` label when `st.page_link` can't resolve a target
  (standalone execution outside `st.navigation`, e.g. AppTest), so a dashboard row
  or gate hint never silently vanishes.
- **(b) Un-hid the workflow (G3).** `app/Home.py` → `st.navigation(sections,
  expanded=True)`; all eight groups (Start + six analysis phases incl. Export)
  render open. Bumped the `streamlit` floor `>=1.30` → `>=1.36` in `pyproject.toml`
  (`expanded=` was added in 1.36).
- **(c) Linked the dashboard checklist (G6).** `app/views/dashboard.py` rows are
  now `workflow_page_link`s (status emoji as `icon=`, `summary`/status/BAS folded
  into the `help=` tooltip). Blocked (⛔) steps stay navigable so the user lands on
  the page and reads its own now-linked gating message.
- **(d) Linked + de-staled every gating message (G6).** Converted the "define X
  first" gates across 14 views to `gate(...)`/`workflow_page_link(...)`:
  `wing_loads`, `flight_envelope` (×3 + the static-margin info), `fuselage_loads`,
  `tail_loads`, `weight_mass`, `structural_speeds` (×2, incl. migrating the one
  pre-existing raw `st.page_link`), `aero_coefficients`, `flap_loads`,
  `aileron_loads`, `tab_loads`, `one_engine_out` (×2), `results_review` (×2),
  `loads_plots` (×2), `export_report` (×2), `configuration_layout` (weight-seed
  gate). Fixed the stale page names: "Wing Geometry" / "Configuration & Layout" →
  **Geometry**, "Flight Envelope" → **Flight Envelope (V-n)**; and the stale phase
  word "Airplane pages" / "Analysis page" → concrete page links.

**Test / Acceptance.** GUI-only, no calc/schema change; full suite green (424
passing, `ruff` clean). New `tests/test_page_links.py`: (1) every `wf.BY_KEY` key
has a matching `app/views/<key>.py` (the helper's path assumption); (2) an AST
scan of all views asserts every literal key handed to `gate`/`workflow_page_link`
is a real workflow step (guards future stale links). The existing `test_views_smoke`
AppTest suite exercises the rendered links (it caught the standalone
`st.page_link` `url_pathname` failure, which the helper's fallback resolves). A
grep for the old page-name references in gating strings is clean.

**Key decisions.** (1) Dashboard rows render as `st.page_link` with icon+help
(BAS name folds into the tooltip) rather than keeping the markdown row and adding
a separate link — user-confirmed 2026-07-20. (2) Blocked steps stay **navigable**,
not disabled — user-confirmed 2026-07-20. (3) Links derive label+path from
`workflow.py` via one helper, making stale names structurally impossible rather
than a discipline to maintain. (4) `st.page_link` can't deep-link to a tab within
a merged page — the tab name stays in prose and the link points at the page.

---

## M2-1 — Loads Plots must recompute from the project (GUI fix, complete 2026-07-20)

**Objective.** The **Loads Plots** page (Load-case plotting phase) read
`Project.loads`, which **no code path ever constructs** — the slice is always
`None`, so the page stopped at its "No distributed loads computed yet" info box
with instructions (visit Wing/Fuselage/Tail/Aileron/Flap/Tab Loads) that could
never succeed. The five Analysis views each carried a matching dead
`if project.loads is not None:` write-back that never executed. (Review finding
G2; known defect M2-1, Major/GUI.)

**Deliverables.**
- **(a) Recompute in `loads_plots.py`.** Removed the `loads = project.loads` /
  `if loads is None: st.stop()` gate. The page now recomputes the four
  distributed-load channels live from the project inputs — `build_net_loads`
  (`.wing_net`), `build_body_loads`, `build_tail_chordwise`, and
  `build_aileron`/`build_flap`/`build_tabs` (control surfaces) — behind the same
  defensive `_try` wrapper `export_report.py` uses (catches
  `ValueError`/`ZeroDivisionError`/`KeyError`/`IndexError` so a channel whose
  upstream inputs are absent degrades to an empty list). Results are bound to a
  `SimpleNamespace` with the `LoadsResult` attribute names so the existing
  curve-extraction and plotting code is unchanged. The page stops only when
  **all four** channels are empty.
- **(b) Deleted the five dead write-backs.** Removed the
  `if project.loads is not None:` guarded writes (and their stale "Persist so the
  sbeam … export can reuse it" comments) from `fuselage_loads.py`,
  `tail_loads.py`, `aileron_loads.py`, `flap_loads.py`, `tab_loads.py`. Fixed the
  one remaining `project.loads.tail_chordwise`-referencing comment in
  `tail_loads.py`.

**Test / Acceptance.** GUI-only (no calc change); full suite green (422 passing,
`ruff` clean). Verified the recompute against both shipped fixtures:
`ga6_normal` → wing 3 / tail 13 / control 4 (body 0 — no fuselage-mass inputs,
correctly empty); `concept_regional_jet` → wing 3 / body 4 / tail 13 /
control 4. The page now displays the same distributions the Export page ships.

**Key decisions.** Match the Export page exactly — recompute-from-inputs, never
read a persisted result slice — so the two pages can never diverge. `LoadsResult`
stays a valid schema type (the build functions still return those objects); only
the never-constructed `Project.loads` *slice* is now unused by the GUI.

---

## M1-10 — Documentation consistency sweep (docs, complete 2026-07-20)

**Objective.** Retire the review's three documentation-inconsistency findings
(D1–D3): stale reference filenames, stale currency claims, and the contradictory
Appendix-B/oracle status — plus move the approved-corrections register to a durable
home.

**Deliverables.**
- **(a) Reference filenames.** Global replace of `FAR23 loads (1).pdf` →
  `FAR23Loads_Code.pdf` and `ADA324952.pdf` → `FAR23Loads_UserGuide.pdf` across 8
  docs (`README.md`, `CLAUDE.md`, both history docs, `PROJECT_GUIDE.md`,
  `CODE_REVIEW_PROCESS.md`, `PROGRAM_SPEC.md`, `00_theory_sources.md`). Left
  verbatim in `PROJECT_REVIEW_2026-07-19.md` (the dated finding that *describes* the
  stale→correct mapping) — rewriting it would make it self-contradictory.
- **(b) Currency.** `README.md` no longer bakes `SCHEMA_VERSION 15`/`242 tests` into
  prose (points at the CI badge + `CHANGELOG.md`); the "4-phase sidebar
  (Define→Analyze→Review→Export)" nav description in `README.md`, `CLAUDE.md` (×2)
  now names the real 7 phases from `workflow.py` (`Start → Develop V-n diagram →
  Flight loads → Other loads → Landing loads → Load-case plotting → Export`).
- **(c) Appendix-B status.** New **canonical "Oracle status"** section in
  `00_theory_sources.md` (`#oracle-status`): Appendix A in-hand/oracle-locked;
  Appendix B absent from the bundled scan → twin/turboprop-only cases closure-locked;
  partial-OCR cases noted. `README.md` (which had claimed Appendix B "prints full
  loads reports" and "each module" is appendix-checked) and `PROGRAM_SPEC.md` now
  defer to it. Resolves the engine-doc casualty (`one_engine_out` no oracle; `engine`
  `23.361(a)(3)` formula-checked).
- **(d) Register move.** The approved-corrections **register of record** moved from
  `CLAUDE.md` into [`docs/20_theory/02_approved_corrections.md`](../20_theory/02_approved_corrections.md);
  CLAUDE.md keeps the policy + a link. `docs/00_INDEX.md`, `00_theory_sources.md` and
  `PROGRAM_SPEC.md` repoint at the register. Added the **FAA User's Guide §17.2.1**
  (post-1994 CFR text of 23.361(c)) corroboration to `engine_loads.md`.

**Test / Acceptance.** Docs-only; `ruff`/`pytest` unaffected (422 passing). No
remaining `FAR23 loads (1).pdf`/`ADA324952.pdf`, `4-phase`, `SCHEMA_VERSION 15`, or
`242 tests` outside the two intentional description lines.

**Key decisions.** Single canonical oracle-status statement lives in the theory doc;
all other docs link rather than restate. Historical review artifacts that describe a
now-fixed defect are left intact.

---

## M1-9 — FLAPLOAD slipstream power: takeoff HP (fix, complete 2026-07-20)

**Objective.** `flap._engine_power` preferred `max_cont_hp` (`max_cont_hp or
takeoff_hp`) for the flap slipstream MAXHP; FAR 23.457(b) sizes the slipstream on
**takeoff power**. Flip the preference to `takeoff_hp`. (Review finding, was
backlog item 2-15.)

**Verification.** Both authoritative sources quote takeoff power — Ref 1 p109 and
the FAA User's Guide p14-2. The sole ambiguity is `FLAPLOAD.BAS`'s "MAX HP OF ONE
ENGINE" input prompt, which does not distinguish the rating; the surrounding text
in both PDFs resolves it to takeoff power.

**Resolution.** `flap._engine_power` now reads `takeoff_hp or max_cont_hp` (was
`max_cont_hp or takeoff_hp`), falling back to max-continuous only when takeoff
power is unset. The Appendix A "Critical Flap Loads" oracle (`tests/test_flap.py`)
calls `flap_loads(..., maxhp=250.0)` directly and is unaffected by the selection
order — the manual's 250 hp is a **stale figure** (user-confirmed 2026-07-20) that
matches neither the GA6 example's `takeoff_hp=285` nor `max_cont_hp=265`; the
oracle tolerance test remains the authority for the slipstream math, and the
example pipeline now feeds takeoff power (285) as 23.457(b) requires.

**Deliverables.** `farloads/modules/flap.py` `_engine_power` preference flip +
docstring citing 23.457(b); `docs/10_standard/PROGRAM_SPEC.md` (FLAPLOAD Reads
line) and `docs/20_theory/00_theory_sources.md` (FLAPLOAD row) note MAXHP = takeoff
power; `CHANGELOG.md`.

**Test / Acceptance.** `tests/test_flap.py` (5 tests) green — Appendix A oracle
unchanged.

**Key decisions.** 250 hp is a stale manual figure, not reconciled to the example
engine data; the tolerance-based oracle stays the math authority (per project
Decision 3). A separate single-source concern — `WeightEstimationInput.max_continuous_hp`
duplicating `sum(engines[].max_cont_hp)` — is **out of scope** here and left for the
G6-series single-source cleanup (M2-6).

---

## M1-8 — AIRLOAD4 Mach threshold 0.4 vs 0.5 (verify, complete 2026-07-20)

**Objective.** Resolve whether `airloads._AIRLOAD4_MACH = 0.4` (the design-Mach
gate that auto-selects the swept/high-Mach AIRLOAD4 branch) is sourced, given the
FAA User's Guide (§9.1, §10.1) states the trigger as **0.5**. (Review finding,
was backlog item 2-14.)

**Verification.** Both authoritative sources were checked directly:
- **Ref 1** (McMaster, the primary source of truth) — Ch 12 aileron-torsion
  air-loads section states the trigger as *"AIRLOAD4.BAS for Mach >.4 or sweepback
  > 15 degrees"* (`FAR23Loads_Code.pdf`). So **0.4 is sourced.**
- **FAA User's Guide** §9.1 and §10.1 — *"If the Mach number is greater than 0.5,
  then AIRLOAD4 should/must be used"*. The **0.5** is the outlier.
- **No `.BAS` oracle** pins the value either way: AIRLOAD4 selection in the
  original suite is a human-operator choice ("should be used when…"), not a
  hardcoded `IF MN > …` — the AIRLOAD4.BAS listing carries no Mach comparison.

**Resolution.** Keep Ref 1's **0.4**. It is the higher-authority source and the
conservative gate (swept branch triggers earlier), and it is nearly moot for
output regardless — compressibility is carried upstream by FLTLOADS' Glauert `CL`,
so high Mach alone leaves the span-load shape unchanged. Per the backlog decision
rule ("if 0.4 is unsourced → 0.5, else document the conservatism"), this is the
"else" branch: **no code value change**, documentation only. The 15° sweep trigger
matches across both sources.

**Deliverables.** Source-conflict note on `_AIRLOAD4_MACH` in
`farloads/modules/airloads.py`; matching notes in `docs/20_theory/00_theory_sources.md`
(AIRLOAD4 row) and `docs/10_standard/PROGRAM_SPEC.md` (AIRLOADS §); `CHANGELOG.md`.

**Test / Acceptance.** No behavior change (constant unchanged); existing AIRLOAD4
suite (`test_airloads.py`) stays green. Documentation-only closure.

**Key decisions.** Ref 1 outranks the User's Guide on a source conflict (CLAUDE.md
source hierarchy); the conservative value is retained; a source is documented on
the constant so the discrepancy is traceable and does not re-open.

---

## M1-5 — One-engine-out 23.367(a)(2) case: safety factor 1.0 (complete, 2026-07-20)

**Objective.** Stop double-factoring the one-engine-out **VC (ultimate)** load. The
23.367(a)(2) loads are defined as ultimate, but the `ConditionResult` carried the
default SF 1.5, so the render/export layer multiplied an already-ultimate load by
1.5. (Review finding T7.)

**Regulatory basis.** 14 CFR 23.367(a) (turbopropeller; Ref 1 Ch 11 p87, verbatim
quote) prescribes two failure modes whose severity fixes both the safety factor and
the speed ceiling — VMC is the minimum control speed, and the Method allows VS/VSF
to be substituted for it:
- **(a)(1)** power failure from **fuel-flow interruption**, VMC→**VD**, loads are
  **LIMIT** → SF 1.5 (the VD case).
- **(a)(2)** **compressor-from-turbine disconnection / turbine-blade loss**,
  VMC→**VC**, loads are **ULTIMATE** → SF 1.0 (the VC case — "limit treated as
  ultimate").
- **VS** substitutes for VMC (the shared floor of both ranges) and is taken as a
  **LIMIT** design point → SF 1.5 (decided 2026-07-20 — the conservative reading;
  the VD limit case envelopes the fuel-flow load at any lower speed).

**Deliverables.**
- `one_engine_out._load_cases` returns a case-definition table of `_LoadCase`
  (new `NamedTuple`: label, far_reference, **load_class**, **safety_factor**,
  **v_lo_kt/v_hi_kt** speed range, **basis**). The SF is owned by the case definition
  (its LIMIT/ULTIMATE classification), *not* the speed; the case also carries the
  speed range it is considered over and is evaluated at the critical high end.
  `run()` carries `safety_factor` and the basis `note` onto each `ConditionResult`.
  Explicit `speeds_kt` overrides are single-speed LIMIT cases (SF 1.5).
- Doc syncs: `PROGRAM_SPEC.md` (ONENGOUT §), `docs/20_theory/00_theory_sources.md`
  (ONENGOUT row), `CHANGELOG.md`. Backlog **M4-3** extended with the turbopropeller-
  gate citation and a VSF-substitution note surfaced here.

**Test / Acceptance.** `test_safety_factors_by_failure_mode` (SF 1.0 / 1.5 / 1.5 by
case + basis note), `test_load_case_owns_sf_and_speed_range` (classification owns the
SF; the case carries its speed range and evaluates at the high end) and
`test_rendered_loads_are_ultimate_with_correct_sf` (rendered load-case rows carry
`-ULT` and `SF` 1 for VC, 1.5 for VD). Full suite green (413 passed), `ruff` clean.
Not an oracle change — no printed ONENGOUT oracle exists and the factor applies only
at the render/export boundary.

**Key decisions.** (1) The safety factor is an attribute of the **load-case
definition** — set by the regulation's LIMIT/ULTIMATE classification of the load, not
by the speed — and the same definition fixes the speed range the case is considered
over. Being a *failure* case does not by itself reduce the factor (the (a)(1)
fuel-flow failure is a failure and stays LIMIT / 1.5). Future flight-test / 14 CFR
23.302/25.302 probability-interpolated (1.0–1.5) cases slot in as new rows with their
own classification. (2) VS = limit (SF 1.5), the reported VMC-substitute floor.
(3) An SF *basis* string is carried now (`_LoadCase.basis` → the `note`); a
first-class `safety_factor_basis` field and a cross-module case-spec are deferred
until a second module needs them.

## M1-11 — Ballast station rejected when outside the fuselage extent (complete, 2026-07-20)

**Objective.** Stop `weight_envelope` from printing a nonphysical moment-balance
ballast station on synthetic over-gross concept databases (e.g. `dhc8_dash8`
forward-regardless → −112 in, forward of the nose datum). Surfaced by M1-7 and
deferred as a follow-up.

**Investigation (overturned the backlog premise).** The backlog assumed a clean
"mirror M1-7's aft direction guard for the forward points." Empirically that is
**oracle-unsafe** and mis-scoped:
- Forward-gross is already safe — its candidate set is station-filtered (≤ fwd_s),
  so its reference is always forward of the limit; it cannot produce the bug.
- Forward-regardless is selected by *weight only*, so its reference CG can land aft
  of the forward limit. On **every** database — including the GA6, whose oracle
  reference (2642 @ 72.74) sits 0.1 in aft of the reg limit 72.64 — a direction-only
  "reference aft of the limit → marker" guard would fire, destroying the 158 lb @
  71.08 oracle. The real defect is narrower: only `dhc8` produced a station outside
  the physical airplane (−112, ahead of the datum); `atr42_100` (+112) and
  `concept_regional_jet` (+64) are physical nose-ballast stations that must be kept.

**Decision (2026-07-20, user).** Guard on **"outside the fuselage extent,"** not a
direction mirror. A physical fore/aft station extent gates every computed ballast
station: an explicit `envelope.fuselage_nose_x`/`fuselage_tail_x` override, else the
Step G1 fuselage outline (`Project.geometry.fuselage` min/max section station), else
the station-0 datum with an unbounded tail (only a station *ahead of the nose* is
rejected — the graceful fallback for databases carrying no outline, as `dhc8` does).

**Deliverables.**
- `WeightEnvelopeInput` — new optional `fuselage_nose_x`/`fuselage_tail_x` (round-trip
  automatically via `io`'s generic `**dict`).
- `weight_envelope.py` — `_fuselage_extent(project, env)` helper; `add_ballast` rejects
  a computed station outside `[nose, tail]` (tail `None` ⇒ only `< nose`) with a
  `"(none — moment-balance station … {ahead of the station-N datum | outside the
  fuselage extent […]})"` marker. Module + `WeightEnvelopeInput` docstrings updated.
- PROGRAM_SPEC, theory-source row, CHANGELOG updated.

**Test / Acceptance.** GA6 p28 triple unchanged (158 @ 71.08 physical). New in
`test_weight_envelope.py`: `test_fwd_regardless_station_inside_extent_kept` and
`test_fwd_regardless_station_outside_extent_marks_none` (synthetic DB, ~580 in station,
explicit extent both sides of it), `test_fwd_regardless_negative_station_marks_none_via_datum`
(`dhc8_dash8` −112 → datum-branch marker), `test_fwd_regardless_extent_from_geometry_outline_kept`
(`concept_regional_jet` +64 inside its G1 outline [0, 1056] → kept, exercising the
outline path). Full suite 422 passing; ruff clean.

**Key decisions / notes.** (1) The direction-only mirror the backlog proposed was
rejected as oracle-unsafe (would fire on the GA6). (2) Applied with the *actually
available* extents the guard flags only `dhc8`: `atr42_100` carries no outline (datum
fallback, +112 kept) and `concept_regional_jet`'s +64 sits inside its [0, 1056]
outline. To also flag those the operator would supply their fuselage extents — the
override fields exist for exactly that. (3) The guard is centralized in `add_ballast`,
so it covers all three ballast points, complementing (not replacing) M1-7's aft
direction-degeneracy guard.

## M1-7 — Aft-gross ballast reference point (complete, 2026-07-20)

**Objective.** Stop `weight_envelope`'s aft-gross ballast case from collapsing to
0 lb whenever the full discretionary loading exceeds gross weight. The reference was
the *full* (max) loading, so `WB = gross − max_load` went negative and `_ballast`
returned `None` → 0 lb — on the twin/concept databases (`concept_regional_jet`,
`atr42_100`). Inert on the GA6 (max load 3322 < gross 3400, so the full loading is
itself the correct reference → 78 lb). (Review finding T8.)

**Regulatory / source basis.** Reference 1 Ch 3 p21-22: the aft-gross ballast
reference is "the heaviest loading not exceeding gross," the same "≤ target"
selection already used for the forward-regardless point (WTONECG/WTENV data base).

**Deliverables.**
- `weight_envelope.py` — aft-gross reference is now the heaviest forward-loading
  vertex with `weight ≤ gross_weight` (mirroring `reg_cands`). Docstring updated.
- **Degenerate-case hardening** (decided 2026-07-20, "harden all three"): all three
  ballast references emit an explicit `"(none — <reason>)"` marker row instead of
  silently dropping the structural point (empty candidate set) or, for aft-gross,
  printing a nonphysical moment-balance station when the heaviest ≤-gross loading
  already sits at/aft of the aft-CG limit (the aft-CG case is then reached with no
  ballast).
- Theory-source row + CHANGELOG updated.

**Test / Acceptance.** GA6 p28 triple unchanged (78/418/158; stations 108.4/80.27/
70.97 — the existing 6 tests stay green). New: `test_aft_gross_uses_heaviest_loading_below_gross`
(synthetic over-gross DB → 100 lb from the 1100-lb reference, not 0 from the 1500-lb
full loading), `test_aft_gross_degenerate_reference_reports_marker` and
`test_ballast_marker_rows_not_dropped` (`concept_regional_jet`). Full suite 418
passing; ruff clean.

**Key decisions.** (1) The aft-gross ballast **station** stays the exact moment
balance (~108.4); the manual's hand-rounded 103.7 (which used limit station 85.0 vs
the exact 85.107) remains a *documented* deviation and is **not** reintroduced — the
backlog's "@ 103.7" target was stale. (2) Degeneracy is reported, not hidden: a real
loading that already achieves the aft-CG extreme yields "no ballast," parallel to the
existing "already at/above target weight" guard. (3) The pre-existing forward-*
nonphysical-station behavior on synthetic concept databases (e.g. `dhc8_dash8`
forward-regardless) is out of scope — it is not introduced by this change and lives
in the oracle-validated forward paths; deferred as a follow-up (M1-11).

## M1-6 — VC/VD coefficient clamp at W/S ≥ 100 (complete, 2026-07-20)

**Objective.** Stop the FAR 23.335(a)/(b) minimum-speed coefficients Kc/Kd from
extrapolating past their tabulated range. `constants.cruise_speed_coefficient` /
`dive_ratio_coefficient` taper linearly from W/S = 20 to 100 (Kc → 28.6, Kd → 1.35)
but kept tapering *below* those endpoints for W/S > 100, understating VC(min)/VD(min).
Inert for GA (W/S ≈ 20) but non-conservative for the heavy-concept band this tool
targets. (Review finding T9.)

**Regulatory basis.** FAR 23.335(a)/(b) tabulate the coefficients only to a wing
loading of 100 lb/ft²; STRSPEED.BAS clamps Kc/Kd at 28.6 / 1.35 there. Above W/S = 100
the schedule is outside the certification basis, so the GA-calibrated minimum becomes
an extrapolated advisory rather than a governing floor.

**Deliverables.**
- `constants.py` — both coefficient functions clamp `wing_loading` to 100 before the
  taper (holds Kc = 28.6, Kd = 1.35 for W/S ≥ 100); docstrings updated.
- `structural_speeds.py` — the design-speeds `ConditionResult` carries an OUT-OF-BAND
  note for W/S > 100 flagging VC(min)/VD(min) as GA-extrapolated advisories and
  pointing to chosen VC/VD (warn-only, mirroring the P1-5 pattern; decided 2026-07-20).
- Docs/theory-source row + CHANGELOG updated.

**Test / Acceptance.** `test_speed_coefficients_clamp_at_wing_loading_100` (continuity
at 100; Kc/Kd held at 28.6/1.35 for W/S = 180, all categories) and
`test_out_of_band_note_above_wing_loading_100` (note present for a W/S ≈ 143 concept,
absent for the GA6). Appendix A oracle unchanged (W/S ≈ 20, below the clamp). Full
suite green (incl. the 2 new tests); ruff clean.

**Key decisions.** Above-100 policy is **clamp + warn note** (not silent clamp, not a
hard error): the clamped minimum is emitted *and* flagged, so the no-chosen-speeds
concept path degrades safely. The clamp is continuous — the taper reaches 28.6/1.35
exactly at W/S = 100 — so no boundary discontinuity is introduced.

## M1-4 — 23.427 unsymmetrical tail: restore the full candidate set (complete, 2026-07-20) **[Major]**

**Objective.** Restore SELECT.BAS's full 12-condition candidate set for the
23.427(a) unsymmetrical horizontal-tail load — specifically, stop excluding the
**unchecked** maneuvers from the search. (Review finding T6; decision D-9.)

**Problem fixed.** `select_htail_unsymmetrical` filtered `"UNCHECKED" not in
c.label` out of the candidate list (citing a "FAA CAM 3.216" rationale). That was
an undocumented, non-conservative deviation from the BASIC: `SELECT.BAS` lines
6070–6175 (Ref 1 Appendix C p440–441; PDF pp315–316) load the unchecked maneuvers
into the candidate array (`L(5)=U1CK`, `L(6)=U2CK`) and take the max over all 12
conditions, and 23.427(a) applies the unsymmetrical distribution to "the loads
prescribed in 23.421 **through** 23.425" — which spans the 23.423 unchecked case.
On the Appendix A GA6 the DN unchecked maneuver (`U2CK` = −1397.835, ref case 274
BAL A) governs over the down gust (−1292.8), so the exclusion under-predicted the
unsymmetrical load.

**Approved oracle deviation.** The Appendix A **sample output** prints the
unsymmetrical governed by GUST −C (total −1111.8, RH −646.4) — which the current
code reproduced. That printout is **inconsistent with its own Appendix C listing**
(the `FOR I=1 TO 12` search would select the larger unchecked case, not the gust);
it was produced by a **superseded SELECT.BAS revision that excluded the unchecked
cases**. The two Reference-1 tier-1 sources conflict; the listing + the CFR are
authoritative. Approved 2026-07-20. Full trace:
`reference/23_427_unsymmetrical_candidate_set.md`; register entry in `CLAUDE.md`.

**Deliverables.**
- `select.py::select_htail_unsymmetrical` searches the full candidate set (unchecked
  included); docstring documents the deviation, the sign rule (`SELECT.BAS` 6180
  `RHSIDE=.5*HTMAX*SGN(LT(HZCASE))`, which coincides with the condition's total-load
  sign for the governing cases), and the confirmed-faithful 80% clamp (6010/6020).
- The governing `CriticalCondition` carries a documented `note`; `models.py`
  `CriticalCondition` gains a `note: str = ""` field, merged into the emitted
  `ConditionResult.note` by `_critical_conditions`.
- `reference/23_427_unsymmetrical_candidate_set.md` (new) — the listing transcription
  + the inconsistency analysis + the regulation citation.
- Doc syncs: `CLAUDE.md` approved-corrections register, `PROGRAM_SPEC.md`,
  `docs/20_theory/00_theory_sources.md`, `CHANGELOG.md`.

**Test / Acceptance.** `test_htail_gust_and_unsymmetrical_match_appendix_a` asserts
the restored unsymmetrical: total **−1204.7** (RH −700.4, LH −504.3, 72%), with the
stale −1111.8 sample-output figures preserved in comments. Full suite green
(410 passed), `ruff` clean.

**Key decisions.** (1) The Appendix C listing (unchecked included) + 23.427(a)'s
"23.421 through 23.425" scope override the stale Appendix A sample output — this is
the tie-break where two tier-1 sources disagree. (2) `rh = 0.5 * total` is retained
for the RH sign because it reproduces `SGN(LT(HZCASE))` for the governing
conditions (verified vs Appendix A). (3) The 80% other-side cap is faithful to
`SELECT.BAS` 6020, not a defect.

## M1-3 — AIRLOAD4 sweep: restore the renormalization step (complete, 2026-07-19) **[Major]**

**Objective.** Restore AIRLOAD4.BAS's sweepback renormalization (the
`COL20 = COL19/CLCOL19` divide) so a swept concept wing's span load re-integrates
to the operating CL. (Review finding T4.)

**Problem fixed.** `airloads._apply_sweep` subtracted the Pope & Haney sweep term
(`(1−2y/b)·2(1−cosΛ)`) from the additive distribution but never renormalized, so
the swept span load integrated to **less** than the operating CL — measured
**recovered_cl 0.452 vs target 0.50 (−9.6%)** on the shipped flagship
`concept_regional_jet` (Λ=24°); 0.94 at Λ=20°, 0.87 at Λ=30°. Non-conservative,
and it reached the deliverables: `net_loads.build_net_loads` →
`air_load_distribution` reads the swept `cl_additive`, feeding the sbeam
FORCE/MOMENT export. The regression was unguarded because the only closure test
used the **unswept** `concept_heavy` fixture.

**Deliverables.**
- **`airloads.py`:** `_apply_sweep` replaced by `_sweep_operating(...)`, which
  applies the Pope subtraction **and** the `COL20` renormalization to the
  **combined operating** distribution (matching AIRLOAD4.BAS's `COL16 = c·kcl/(MAC·CL)`,
  so wing twist is redistributed too — not additive-only). `schrenk_distribution`
  sweeps `ccl_total` at `target_cl` (report/closure path), leaving the
  additive/basic split as the unswept decomposition; `air_load_distribution` sweeps
  the assembled operating distribution per condition at that condition's CL
  (deliverable path). Renormalization uses the physically-correct span-load integral
  (Decision 3 "modernize the math"): the literal chord-weighted `COL16`/`CLCOL19`
  line is OCR-garbled and closes only to ~0.3% (0.4983), so the port renormalizes to
  the operating CL exactly. Documented in the `_sweep_operating` docstring.
- **Tests (`tests/test_airloads.py`):** `test_swept_closure_recovers_target_cl`
  (Λ≠0 closure on the regional-jet fixture — the guard the branch lacked);
  `test_sweep_operating_matches_basic_listing` (listing-traceable COL18/COL19/COL20
  per-station reconstruction + closure); `test_swept_deliverable_recovers_case_cl`
  (the fix reaches `build_net_loads` — each case's root shear implies its own CL).
  `tests/test_taildist.py::test_airload4_sweep_shifts_load_outboard` updated to
  assert on the swept `ccl_total` (root reduced, tip ~unchanged) + closure, since
  the additive split is now left unswept.
- **Docs:** `00_theory_sources.md` AIRLOAD4 row and `PROGRAM_SPEC.md` AIRLOAD4
  validation line record the renormalization as the method's final step and the new
  closure + listing-traceable checks; backlog M1-3 removed (M1 entry + Known-defect
  bullet); `CHANGELOG.md` `[Unreleased] → Fixed`.

**Test / Acceptance.** `ruff` (`farloads/ cli.py`) clean; full suite green (410
passed). `recovered_cl` on the flagship moves 0.452 → 0.500; the unswept GA
Appendix-A additive (`CC(LA1)` 91.05576) and the Λ=0 reduction invariant are
unchanged.

**Key decisions (with the user, 2026-07-19).** (1) **Sweep the combined operating
distribution, not additive-only** — matches AIRLOAD4.BAS (`COL16`), redistributes
twist, and is oracle-faithful (the flagship wing is twisted 3°→0°, so it changes
that deliverable). (2) **Validate with closure + a listing-traceable per-station
test** (no printed Appendix B swept oracle exists). (3) **Renormalize on the
span-load integral, not the literal chord-weighted `CLCOL19`** — the COL16 line is
OCR-garbled and the chord-weighted form closes only to ~0.3%; the span-load form
closes exactly and matches Decision 3. A documented ~0.3% normalization deviation.

---

## M1-2 — BAL 1.4VSF: balance at 1.4× the 1-g flaps-down stall (complete, 2026-07-19) **[Critical]**

**Objective.** Correct the flaps-extended envelope's `BAL 1.4VSF` condition to
balance the airplane at **1.4× the 1-g flaps-down stall (`STALL 1GL`)** speed, per
`FLTLOADS.BAS` (Code.pdf p300–302, which saves the STALL 1GL speed for this case).
(Review finding T2; was old 2-6 in part.)

**Problem fixed.** `flight_envelope._flap_config_points` captured the **STALL 2G**
speed (`v3 = add("STALL 2G", …).v_eas`) and ran `BAL 1.4VSF` at `1.4·v3`. Because
STALL 2G ≈ √2 × STALL 1G, the balance speed was ~1.4× too high and the balancing
tail load (∝ q ∝ V²) ~2.2× too large — a wrong load that fed the SELECT search and
the sbeam export. Against Appendix A p181 (LANDING CG5, case 89 `BAL 1.4VS`), the
oracle is V 83.6 kt / LT −430 lb; the defect produced ~116 kt / −957 lb. The defect
was masked because the shipped `examples/ga6_normal.project.json` carries no
`aero_coeffs.flaps_down` set, so the flaps-extended branch was dormant and the only
prior flapped test used a *synthetic* landing config (closure-checked, no oracle).

**Deliverables.**
- **`flight_envelope.py`:** `_flap_config_points` now captures the STALL 1GL
  balanced EAS (`v_1gl = add("STALL 1GL", …).v_eas`) and runs `add("BAL 1.4VSF",
  1.0, 1.4 * v_1gl, di.mc)`; STALL 2G stays a plain corner point. Docstring updated
  to state the STALL 1GL basis + the T2 history.
- **Test:** the real Appendix A p179 landing-config aero polynomials
  (`lift/drag/moment`) are transcribed into `tests/test_flight_envelope.py` as
  module-level `_LANDING`, replacing the synthetic deepcopy in `_with_landing()`
  (whose stale comment claiming the polynomials "are not in the repo" is corrected).
  New `test_bal_1p4vsf_balances_at_one_g_flaps_down_stall` asserts the exact fix
  invariant (`BAL 1.4VSF v == 1.4·STALL 1GL v`, and **not** `1.4·STALL 2G v`) plus
  the p181 case-89 oracle (V 83.6 kt / LT −430 lb / α −2.54° / CL 0.89) within print
  precision (LT is a small CG-moment residual, so it carries the widest tolerance).
- **Docs:** `00_theory_sources.md` FLTLOADS + TAILDIST rows; `PROGRAM_SPEC.md`
  FLTLOADS notes + the SELECT flaps-extended known-limit; backlog M1-2 removed and
  L-2 updated; the 0.2.0 verification-baseline "no landing polynomials in the repo"
  deferrals annotated with the M1-2 correction; `CHANGELOG.md` `[Unreleased] → Fixed`.

**Test / Acceptance.** `ruff` (`farloads/ cli.py`) clean; full suite green (407
passed) — the new p181 oracle passes; all cruise Appendix-A oracles and the
concept fixture are unchanged (the shipped example has no `flaps_down` set, so no
existing SELECT/TAILDIST/export result moved).

**Key decisions (folded into the plan, 2026-07-19).** (1) **Dedicated test
fixture, not the shipped example** — the p179 landing polynomials are injected in
the test only; `examples/ga6_normal.project.json` is left without `flaps_down`, so
the full flaps-extended SELECT→TAILDIST→export activation stays with **L-2** and
this `[Critical]` fix stays small and reviewable (mirrors M1-1). (2) **Oracle scope
= the one fixed case** (`BAL 1.4VSF`, p181 case 89); the fuller p181 landing rows
stay L-2. (3) **Uniform fix, no concept carve-out** — capturing the wrong speed was
a pure correctness bug, so FAR23 and concept both use the 1-g flaps-down stall.
(Note: the review cited the pages as p176/p178; the actual printed pages are p179
for the input listing and p181 for the LANDING CG5 block.)

---

## M1-1b — CLmax → stall-speed single-source (complete, 2026-07-19)

**Objective.** Enter the maximum lift coefficients **once** and derive the stall
speeds from them, instead of hand-entering `stall_clean_kt`/`stall_flap_kt` on the
speeds slice (closes old 2-13(b), User's Guide p7-5; split out of M1-1).

**Locked decisions (AskUserQuestion, 2026-07-19).** (1) Level B — CLmax is the
single stall-speed source across STRSPEED and the flight envelope. (2) CLmax lives
on `aero_coeffs` (not `speeds`). (3) No back-compat — remove the scalars and edit
the example files; CLmax is the input. (4) CLmax entered on the Aerodynamic Data
page, which **moves before** Structural Speeds in the workflow.

**Deliverables.**
- `AeroCoefficientsInput.clmax_clean`/`clmax_clean_neg`/`clmax_flap` — the single
  authored stall-speed source, decoupled from the polynomial sets so an airplane
  with stall data but no balance polynomials still carries its CLmax.
- `constants.stall_speed_kt(W, S, CLmax)` = `√(295·(W/S)/CLmax)`; STRSPEED derives
  VS/VSF (exposed on `DesignSpeeds.vs`/`.vsf`), `flap` and `one_engine_out` read
  them. `StructuralSpeedsInput.stall_clean_kt`/`stall_flap_kt` removed; STRSPEED
  `requires=("aero_coeffs",)`; workflow reordered (Aerodynamic Data before
  Structural Speeds). `SCHEMA_VERSION` → 29; `io.py` (de)serializes `clmax_*`;
  GUI: CLmax entered on the Aerodynamic Data page, VS/VSF read-only on Structural
  Speeds with a page link. Six example projects migrated.

**Key finding — the two stall representations cannot be a single number.** The
STRSPEED stall *speed* (simple `√(295·(W/S)/CLmax)`) and the FLTLOADS stall *CL*
(the 0.9-margin balance clamp `AeroCoeffSet.stall_cl`) are entered independently in
the manual and differ by ~0.1% (Appendix A ga6: `clmax_clean` 1.4068 from the
printed VS 62.226 vs FLTLOADS `stall_cl` 1.41). Both Appendix-A oracles are tight
enough to pin each (VA 121.3 needs 1.4068; the SELECT ACRL CL 1.328 needs 1.41), so
forcing them equal breaks one. Resolution: `clmax_*` is the stall-*speed* source;
`AeroCoeffSet.stall_cl` stays the FLTLOADS clamp, authored per config;
`AeroCoefficientsInput.__post_init__` fills either from the other only when one is
missing (never overwrites). Both round-trip in JSON.

**Test / Acceptance.** `ruff` (`farloads/ cli.py`) clean; full suite green (406);
all Appendix-A oracles preserved exactly (STRSPEED VA/VF and the FLTLOADS/SELECT
envelope); ga6 derived VS 62.228 / VSF 58.612 / VA 121.304 / VF 105.502; every
example project save→reload is a no-op.

**Key decisions.** As above — CLmax on aero_coeffs; hard-replace (no migration);
stall-speed CLmax kept distinct from the FLTLOADS clamp to preserve both oracles.

---

## M1-1 — VD floor: enforce `K_d·VCmin` (complete, 2026-07-19) **[Critical]**

**Objective.** Correct the `structural_speeds` (STRSPEED) dive-speed minimum to
enforce **both** FAR 23.335(b) floors — `VD ≥ max(K_d·VCmin, 1.25·VC)` — with the
K_d term applied to the *minimum* cruise speed VCmin, matching `STRSPEED.BAS`
(`V2DMIN=K2·V1CMIN`, lines 380/390). (Review finding T1; was old 2-13(a).)

**Problem fixed.** `design_speed_values` computed the K_d dive term as `K_d·VC` and
folded it only into a "recommended" advisory (`vd_recommended`), enforcing just the
`1.25·VC` floor. On the **no-chosen-speeds** path VD therefore collapsed to
1.25·VCmin. On the Appendix A Cat-N case (p155) the manual prints VD(min) **198.53
kt** (= K_d·VCmin = 1.40·141.8); the code returned **177.26** — 10.7% non-
conservative, propagating into MD/MACHLIM and every downstream case evaluated at VD.
The chosen-speeds worked example (p156, chosen VD 212.5, which clears both floors)
masked the defect, which is why the 0.2.0 baseline missed it.

**Locked decisions (AskUserQuestion, 2026-07-19).**
1. **Concept mode (Cat C) — advisory.** The GA-calibrated K_d term is *not*
   enforced for concept; Cat C retains only the pre-existing absolute 1.25·VC floor
   (behavior byte-for-byte unchanged), and reports K_d·VCmin as advisory. Preserves
   the "concept governs / reduces exactly to FAR23 on GA inputs" invariant.
2. **CLmax → stall-speed path (old 2-13(b)) split out** into new backlog item
   **M1-1b** at **Level B** (single-source everywhere); M1-1 lands the VD floor
   alone to keep the `[Critical]` fix small and reviewable.

**Deliverables.**
- **`structural_speeds.py`:** `vd_min = max(kd*vc_min, 1.25*vc)`; `hard_floor =
  1.25*vc` for Cat C else `vd_min`; `vd = max(chosen_vd, hard_floor)` (or the floor
  when no chosen VD). `DesignSpeeds.vd_recommended` → **`vd_min`**; reported
  `LoadValue` "Recommended dive VD (gust, K*VC)" → **"Minimum dive VD(min)"**.
  Module docstring rewritten to state the two-term floor + the Cat-C carve-out.
- **Test:** new `test_vd_floor_no_chosen_speeds` — Cat N, no chosen speeds, asserts
  VD and VD(min) = 198.53 kt (Appendix A p155, printed number + citation inline).
- **Docs:** `00_theory_sources.md` STRSPEED row (equation `VD=max(Kd·VCmin,
  1.25·VC)` + the p155/p156 distinction, replacing the Code-manual prose error);
  `PROGRAM_SPEC.md` STRSPEED notes; `CHANGELOG.md` `[Unreleased] → Fixed`.

**Test / Acceptance.** `ruff` clean; full suite green (406 passed) — the new p155
oracle passes, the p156 chosen-speeds oracle (VD 212.5) and the concept fixture are
unchanged (no regression).

**Key decisions.** As above — Cat C advisory; CLmax split to M1-1b (Level B).

---

## Phase G — Step G6b: Single-source landing-gear geometry (complete, 2026-07-19)

**Objective.** Make the Geometry page the single source of truth for the landing
gear, using the parameters native to LANDLOAD (axle stations at each strut state,
tread, rolling radius, strut type — not a synthetic coarse gear station). The
three-view depicts the gear from that data, and the ground-load analysis reads it —
every value entered once. Sibling to Step G6.

**Problem fixed.** Gear geometry was entered twice, unreconciled: the coarse
`LayoutInput` `main_gear_x`/`nose_gear_x`/`track`/`gear_height` (three-view +
tip-back/overturn/clearance) and the detailed `LandingInput` axle geometry (LANDLOAD).
In `concept_regional_jet` the stations/tread agreed but the stored `gear_height`
(75 in) contradicted the axles (static Z 20 − rolling radius 14 → ground WL 6 → ~39
in) — a silent divergence.

**Locked decision (AskUserQuestion, 2026-07-19).** `gear_height` → *derive from the
axles* (ground = static axle Z − rolling radius; fully single-source), shifting the
no-oracle tip-back/overturn/clearance estimate where the old stored value disagreed.
Plus the three backlog-locked decisions: data home = `GeometryInput.landing_gear`;
analysis wiring = derive/sync (calc math untouched); scope = landing gear only.

**Forced by fixture inspection.** Only the regional jet has both homes; cessna/ga6
carry gear only in `LandingInput` and have no parametric geometry — so
`LandingGearGeometry` **stores the native axle geometry verbatim** (LANDLOAD reads
the one authoritative copy; the reactions are byte-identical).

**Deliverables.**
- **`LandingGearGeometry{main_gear, nose_gear: LandingGearInput, tread_in}`** on
  `GeometryInput.landing_gear` (`farloads/models.py`); the coarse `LayoutInput` gear
  fields retired. `SCHEMA_VERSION` 27 → 28.
- **`farloads/io.py`** — `geometry.landing_gear` (de)serialization; `landing_to_dict`
  strips the gear (written under geometry); migration of a pre-v28 file's top-level
  `landing` gear (and legacy `LayoutInput` gear) into `geometry.landing_gear`.
- **`farloads/modules/landing.py`** — `_sync_gear_from_geometry(project)` fills the
  landing slice's gear from `geometry.landing_gear` at the top of `build_landing`
  (math unchanged → LANDLOAD oracle bit-for-bit).
- **`farloads/modules/configuration.py`** — `gear_stations(layout, landing_gear)`
  derives `{main_x, nose_x, track, gear_height, ground_z}` from the native axles;
  `component_stations` and `_gear_condition` read it (ground = static axle Z −
  rolling radius).
- **`app/views/configuration_layout.py`** — a *Landing gear* form (per-leg axle
  3-states + rolling radius + strut, tread); the three-view draws the strut + wheels
  and the derived ground line. **`app/views/landing_loads.py`** — drops the gear/tread
  widgets, reads the gear read-only, keeps the non-geometry LANDLOAD inputs.

**Test / Acceptance** (`tests/test_landing_gear_geometry.py`, 4 tests; plus updated
`test_landing`/`test_configuration`/`test_io`). The gear serializes under
`geometry.landing_gear` (not the landing block); a pre-v28 top-level file migrates;
`gear_stations` derives the coarse values from the axles (ground = static Z − rolling
radius); the LANDLOAD reactions are **bit-for-bit** across a JSON round-trip. Full
suite **405 passing**; `ruff` clean (`farloads/`, `cli.py`, `app/`).

**Key decisions.** Store (not derive) the native axle geometry → LANDLOAD oracle-safe;
`gear_height` derived from the axles (single-source, shifts the no-oracle estimate);
gear synced onto `Project.landing` at calc time (mixed slice — the non-geometry
LANDLOAD params stay stored there).

---

## Phase G — Step G6: Single-source empennage & control-surface geometry (complete, 2026-07-19)

**Objective.** Make the Geometry page the single source of truth for the empennage
and its control surfaces (elevator + rudder), using the parameters native to the
analysis programs (areas, spans, stations, deflections, effectiveness — not a
synthetic hingeline/overhang). The three-view depicts the elevator/rudder from that
same data, and the tail-load analysis reads it — every value entered once. Fixes the
double-entry (h-/v-tail area/span duplicated between `LayoutInput` and the tail-load
slices) and the elevator/rudder geometry that had no GUI home (JSON-only) and was
undrawn.

**Locked decisions (AskUserQuestion, 2026-07-19).** (1) **Representation** → *fully
derived*: `Project.tail_loads`/`.vtail_loads` become properties proxying to
`GeometryInput.empennage`; removed from stored JSON (nothing stored twice). (2)
**Depiction** → *hinge line + shaded band*: the three-view draws the elevator/rudder
as the aft `Saft/S` chord band. Plus the three carried from the backlog plan: data
home = `GeometryInput.empennage`; analysis wiring = derive at the boundary (calc
untouched); scope = elevator + rudder only (ailerons/flaps/tabs later).

**Forced by fixture inspection.** 4 of 5 tail fixtures (incl. GA/Appendix A) carry
*no* parametric geometry — the tail data lives only in the analysis slices — so
`EmpennageInput` **stores the native analysis values verbatim** and the property is
an identity (bit-for-bit). Where the two old homes disagreed (regional-jet h-tail
span 278.0 analysis vs 278.4 sketch), the analysis value wins.

**Deliverables.**
- **`EmpennageInput{htail: Optional[TailLoadsInput], vtail: Optional[VTailLoadsInput]}`**
  on `GeometryInput.empennage` (`farloads/models.py`); `Project.tail_loads`/
  `.vtail_loads` are now `@property` + setter proxying to it (via `_ensure_empennage`);
  the duplicated `LayoutInput` `h_tail_area`/`h_tail_arm`/`h_tail_span_in`/`v_tail_area`/
  `v_tail_arm`/`v_tail_span_in` fields retired (kept `tail_type`, `h_tail_z`).
  `SCHEMA_VERSION` 26 → 27.
- **`farloads/io.py`** — `geometry.empennage` (de)serialization (`{htail, vtail}` via
  the existing `tail_loads_to_dict`/`vtail_loads_to_dict`); migration of a pre-v27
  file's top-level `tail_loads`/`vtail_loads` into it; top-level write removed.
- **`farloads/modules/configuration.py`** — `tail_planform(layout, empennage)`,
  `component_stations(layout, empennage)` and `_stability_condition` read the
  single-source empennage (area/span/`xt25`/`xv25`; arm derived); `tail_planform` adds
  `elevator`/`rudder` panels (aft `_hinge_fraction(Saft, S)` chord band).
- **`app/views/configuration_layout.py`** — an *Empennage & control surfaces* form
  (all native h-/v-tail + elevator/rudder fields); the Tail expander drops the
  area/span/arm widgets (arrangement only); the three-view shades the elevator/rudder.
  **`app/views/tail_loads.py`** — analysis-only: drops the semi-span/span widgets
  (now on Geometry), reads the geometry read-only.

**Test / Acceptance** (`tests/test_empennage.py`, 4 tests; plus updated
`test_configuration`/`test_io`/`test_taildist`). The property proxies to
`geometry.empennage` (set/get/clear); the slice round-trips and serializes under
`geometry.empennage` (no top-level keys); a pre-v27 top-level file migrates; the
governing SELECT horizontal-tail loads are **bit-for-bit** across a JSON round-trip
(the exact Appendix A values stay locked in `test_select.py`, which now feeds the
tail input through the property → empennage and still passes). `test_configuration`
asserts the three-view draws the elevator/rudder when the hinge areas are set. Full
suite **401 passing**; `ruff` clean (`farloads/`, `cli.py`, `app/`).

**Key decisions.** Store (not derive) the native analysis values so the mapper is an
identity → oracle-safe; analysis value authoritative where the old homes disagreed;
non-geometry tail-aero params the manual bundles (wing zero-lift IW, wing lift-slope
AW, ARW, LF) kept on `EmpennageInput` for now (the wing/fuselage read-through cleanup
is the separate Step G6c).

---

## Phase G — Step G5: Longitudinal-stability / trim plots (complete, 2026-07-19)

**Objective.** Add standard longitudinal-stability plots to the flight-loads
section to check trim and balancing tail loads across the CG range
(CG-vs-balanced-tail-load; static-margin sweep). GUI plots over existing calc — no
new load equations.

**Scope decisions (AskUserQuestion, 2026-07-19).** (1) **CG axis** → *continuous
sweep*: re-run the existing `_balance()` at ~15 interpolated CG stations across the
forward–aft range (reuses the calc, no new math) rather than plotting only the 2–4
discrete stored CG cases. (2) **Condition** → *BAL trim cases (n = 1)*: trace the
BAL A / BAL C / BAL D balanced 1-g tail loads (the true "trim" loads), one line
each. (3) **Placement** → a *new "Trim & Stability" tab* on the merged Flight
Envelope page (alongside V-n and Critical Loads), keeping all balance-derived plots
together.

**Deliverables.**
- **`flight_envelope.trim_sweep(project, *, weight_lb, zcg, xcg_stations,
  altitude_ft=0)`** (new, pure) → `List[TrimCurve]` — re-runs the FLTLOADS balance
  (`_balance`, subroutine 3900) at each CG station for BAL A/C/D at `n = 1`, holding
  weight/waterline and every other flight-loads/speeds input fixed. Adds no load
  equations, so a station coinciding with a project CG case reproduces that case's
  `build_envelope` BAL load exactly. Uses the cruise (flaps-up) coefficient set
  including the Step-G4 fuselage increment when enabled. **LIMIT** output
  (`TrimCurve.lt_lb`).
- **`flight_envelope._balance_configs(aero)`** (refactor) — the flaps-up-then-down
  coefficient list (with the G4 fuselage-moment augmentation) extracted from
  `build_envelope` and shared with `trim_sweep`, so both see identical coefficients.
  `build_envelope` behaviour is bit-for-bit unchanged.
- **`app/views/flight_envelope.py`** — a third **Trim & Stability** tab: a
  "reference loading" selector (sets the swept weight & waterline), forward/aft CG
  station bounds and a station-count slider; a *balancing tail load vs CG* Plotly
  chart (BAL A/C/D lines, with the real CG cases at that weight overlaid as open
  markers that land on the curve), a swept-value table, and — when the project
  carries a parametric layout — a *static margin vs CG* chart (`SM = NP − CG`, %MAC)
  using the Configuration module's tail-volume neutral point, with the WTENV
  forward/aft CG limits overlaid. Tail loads are marked **LIMIT** with a caption
  pointing to the ULTIMATE deliverables (Critical Loads tab / Results Review /
  exports).

**Test / Acceptance** (`tests/test_trim_sweep.py`, 5 tests). The sweep reproduces
the Appendix A `build_envelope` BAL A/C/D loads exactly at the CG1/CG2 stations
(both share 3400 lb / zcg 93, so one sweep validates both — the traceability
guarantee); the tail load rises monotonically moving aft (physical shape); the
balanced `NZ ≈ 1` at every station; the Configuration neutral point is exposed as a
sensible %MAC for a layout project and the static-margin arithmetic shrinks moving
aft; the sweep raises without a cruise coefficient set. No schema change; full suite
396 passing, `ruff` clean.

**Key decisions.** Continuous sweep (not discrete scatter) reusing `_balance`;
LIMIT display on this analysis/check tab (marked, deliverables ULTIMATE elsewhere)
consistent with the sibling V-n tab; static-margin sweep gated on the Configuration
neutral point so oracle fixtures without a parametric layout degrade to the trim
plot alone.

---

## Phase G — Step G4: Fuselage pitching-moment estimator (Munk slender-body) (complete, 2026-07-19)

**Objective.** Derive the fuselage's contribution to the airplane-less-tail
pitching-moment slope `dCm/dα` from the G1 fuselage outline and feed it into the
FLTLOADS balance, so a **concept** airplane built from a planform no longer has to
hand-fold the fuselage into the input coefficients. The FAR23 GA/twin oracles
(whose coefficients already include the fuselage) must reduce exactly.

**Scope decisions (AskUserQuestion, 2026-07-19).** (1) **Method** → *Munk
slender-body* (apparent-mass), integrating the G1 ellipse-area station table —
geometry-only, matches the reading `FuselageSection` committed to in G1. (2)
**Coupling** → *separate off-by-default field*: a new `fuselage_moment` sub-slice,
disabled by default, added to the balance only when enabled (raw stored
coefficients stay pristine; a SCHEMA bump). (3) **Terms** → *dCm/dα slope only*:
for an uncambered outline the Munk moment is a pure α-couple, so the estimator
populates only ΔM1 and leaves the zero-α free moment M0 as a user input (it
depends on wing downwash the outline can't supply).

**Deliverables.**
- **`farloads/fuselage_moment.py`** (new, pure helper) — `estimate(outline, S, mac)
  → FuselageMomentEstimate` computing `dCm/dα (per rad) = (k₂−k₁)·Vol/(S·mac)`,
  returned per degree to match M1. Section area = ellipse `π/4·w·h`; `Vol` = the
  trapezoidal integral; fineness `l/d` = length ÷ max equivalent diameter
  `√(w·h)`; `(k₂−k₁)` from the Munk prolate-spheroid table (interpolated, clamped).
  Returns `None` on insufficient geometry (< 2 stations, non-positive S/mac). The
  result is reference-point independent (volume-based) → no CG station needed.
- **`FuselageMomentInput{enabled=False, d_cm_dalpha=0.0}`** on
  `AeroCoefficientsInput.fuselage_moment` (`farloads/models.py`); serialized in
  `io.py`; `SCHEMA_VERSION` 25 → 26 (additive, older files load with no fuselage
  moment).
- **`flight_envelope.build_envelope`** — when `fuselage_moment` is enabled and
  non-zero, augments each config's M1 by ΔM1 via `dataclasses.replace` on a **local
  copy** (stored coefficients untouched); `_balance` is unchanged, so the Glauert
  `g/gmn` compressibility factor applies to the increment automatically. Disabled →
  no change.
- **`app/views/aero_coefficients.py`** — a *Fuselage pitching-moment (Munk
  slender-body)* section: shows volume / fineness / `k₂−k₁` / estimated ΔM1 from
  the Geometry outline + the Flight-Envelope wing S & MAC, with an enable checkbox
  and an overridable ΔM1 input. The main aero form's Apply now carries the
  `fuselage_moment` sub-slice through unchanged.
- **`reference/fuselage_pitching_moment.md`** — method derivation + the `(k₂−k₁)`
  table, cited to Munk (NACA TR-184), USAF DATCOM 4.2.1.1, and Perkins & Hage.

**Test / Acceptance** (`tests/test_fuselage_moment.py`, 6 tests). The estimator
matches the closed form on a known cylinder (volume, fineness, `k₂−k₁`, ΔM1) and
the interpolation table endpoints; returns `None` on insufficient geometry; a
**disabled** (or zero) fuselage moment leaves the Appendix A V-n matrix
bit-for-bit unchanged (`m_wf`/`lt`/`nz` exact); an **enabled** positive ΔM1 shifts
the balancing tail load (wiring reaches the balance); the field round-trips through
`io.save/load`. Full suite **391 passed**; `ruff` clean. Oracles unchanged.

**Key decisions.** Off-by-default is the oracle-safety mechanism (the manual's
coefficients already include the fuselage; enabling on GA inputs would
double-count). Slope-only keeps the estimate honestly geometric. Local-copy M1
augmentation (not baking into stored coefficients) keeps the raw coefficients
auditable and the fuselage term toggleable. Reduces exactly to the FAR23 core on
GA inputs (estimator disabled).

---

## Phase G — Step G3: Phase-1 page consolidation (Develop V-n diagram) (complete, 2026-07-19)

**Objective.** Collapse the *Develop V-n diagram* section from ten nav pages into
the five sub-steps 1a–1e of `03_gui_rework_plan.md` §4, so "define the airplane &
load environment" is one coherent sequence and each shared quantity is entered once.

**Scope decisions (AskUserQuestion, 2026-07-19).** (1) **Merge layout** → *tabs*:
each merged page uses `st.tabs` for its sub-pages (rather than one long scrolling
page of stacked sections). This introduces tabs as the multi-page merge convention
(previously only Aircraft Comparison used tabs). (2) **1e V-n inputs** → *keep on
1e*: the FLTLOADS balance-geometry/CG inputs (MAC, wing area, X/Z at 25% MAC,
tail-CP stations, reference Mach, altitudes) stay on the V-n page where they run;
1e is input + compute + display + SELECT, not results-only.

**Deliverables.**
- **`app/views/weight_mass.py`** (new, **1b Weight & Mass Properties**) — one page,
  four tabs: *Estimate* (WTESTIMA), *Weight, CG & Inertia* (WTONECG), *Payload
  Cases* (shared `weight.cg_cases`), *Weight / CG Envelope* (WTENV). The single
  owner of all weight/mass data (decision G-2). Each tab is a function so a
  missing-prerequisite guard `return`s instead of `st.stop()` (which would kill the
  sibling tabs); sub-page inputs moved from the sidebar into the tab body so the
  sidebar doesn't stack four forms.
- **`app/views/structural_speeds.py`** (rewritten, **1c**) — two tabs: *Design
  Speeds* (STRSPEED) + *Speed–Altitude Envelope* (MACHLIM). The Design Speeds tab
  preserves the existing `speeds.mach_limit` sub-slice on Apply.
- **`app/views/flight_envelope.py`** (rewritten, **1e**) — two tabs: *V-n diagram*
  (FLTLOADS) + *Critical Loads (SELECT)*. Balance inputs stay in the sidebar
  (shared by both tabs); the SELECT include/exclude selection persists to
  `envelope.critical.selected_case_ids` as before.
- **`app/views/aero_coefficients.py`** (**1d**) — unchanged (the reference-Mach
  input stayed on 1e per the decision, so 1d needed no move).
- **Deleted views** (folded into the tabs above): `weight_estimate.py`,
  `weight_cg_inertia.py`, `payload_cases.py`, `weight_envelope.py`, `mach_limit.py`,
  `critical_loads.py`.
- **`farloads/workflow.py`** — the ten Develop-V-n steps become five
  (`configuration_layout`, `weight_mass`, `structural_speeds`, `aero_coefficients`,
  `flight_envelope`); `FOLDED_MODULES` gains `weight_estimate`, `weight_envelope`,
  `mach_limit`, `select` (each still a registered/tested calc module without its own
  nav step — the wing_inertia precedent). `weight_onecg`/`structural_speeds`/
  `flight_envelope` are the named primary modules.
- **Cross-page copy** — warnings/captions in `one_engine_out.py`, `tail_loads.py`,
  `export_report.py`, `results_review.py`, `configuration_layout.py`, and the merged
  pages themselves updated to point at the new tab locations (the six deleted pages
  are no longer nav destinations).
- **`tests/test_views_smoke.py`** — the beyond-GA power-cap regression fixture
  repointed from the deleted `weight_estimate.py` to `weight_mass.py`.

**Test / Acceptance.** Full suite green (**385 tests**; the −5 vs. G2's 390 is purely
the six folded views leaving / one new view joining the auto-globbed smoke
parametrization). `ruff check farloads/ app/ cli.py` clean. The nav-drift guard
(`test_every_registered_module_has_a_step`) stays green via `FOLDED_MODULES`.
Functional render check (headless `AppTest`, ga6 fixture): weight_mass = 4 tabs / 12
dataframes / 2 plots; structural_speeds = 2 tabs / 1 chart; flight_envelope = 2 tabs
/ 1 V-n plot. Appendix A/B oracles unchanged (no calc touched).

**Key decisions.** G-4 phase-1 consolidation into 1a–1e; tabs as the merge
convention; balance inputs stay on 1e; keep the validation page-tags stable and
filter for them in the merged views (the G1 `wing_geometry`-tag precedent), so
`validation.py` and its tests are untouched.

---

## Phase G — Step G2: Re-sequence `workflow.py` into the analysis-flow phases (complete, 2026-07-18)

**Objective.** Reorder the GUI navigation (decision G-4) into the six analysis-flow
sections of `03_gui_rework_plan.md` §4 so page order follows how a FAR 23 analysis
is actually performed, not the historical 22-program packaging.

**Scope decisions (AskUserQuestion, 2026-07-18).** (1) **Shell pages** → *keep a
"Start" section*: the two non-analysis app-shell pages (Project Dashboard, JSON
Editor) stay in a dedicated un-numbered **Start** group above the six analysis
phases, rather than being folded into an analysis phase (§4 defines only the six
analysis phases; the shell needs a home). (2) **Label style** → *numbered + §4
names*: the six analysis phases carry a numeric prefix (`1 · Develop V-n diagram`
…`6 · Export`); Start is un-numbered to mark it as the shell.

**Deliverables.**
- **`farloads/workflow.py`** — the `PHASES` constants renamed/re-grouped to
  `START, DEVELOP_VN, FLIGHT_LOADS, OTHER_LOADS, LANDING, LOADS_PLOTTING, EXPORT`;
  every `WorkflowStep`'s `phase` reassigned and the `STEPS` tuple reordered into
  analysis-flow order. The old **Airplane**/**Envelopes & Critical Conditions**
  split dissolves — geometry, all four weight/CG pages, both speed pages, aero, and
  the V-n + SELECT pages now sit together under **Develop V-n diagram** in §4's
  1a→1e order; **Landing Loads** moves *after* the control-surface/engine **Other
  loads** group. Module docstring updated to point at `03_gui_rework_plan.md §4`.
- **`app/Home.py`** — `_PHASE_LABEL` remapped to the new phases with the
  Start-un-numbered / analysis-numbered scheme; module docstring nav diagram updated.
- **`app/views/dashboard.py`** — the left-to-right section caption updated to the
  new phase names.
- **No page bodies changed** — grouping/labels only; the per-page consolidation into
  §4's 1a–1e sub-steps is the separate Step G3.

**Test / Acceptance.** Full suite green (390 tests, unchanged count — the workflow
tests are phase-name-agnostic: they read `wf.PHASES`/`wf.by_phase()` dynamically, so
`test_keys_unique_and_phases_valid`, `test_by_phase_partitions_all_steps`, and the
nav-drift guard `test_every_registered_module_has_a_step` all validate the new
grouping automatically). `ruff check farloads/ cli.py` clean. Probe confirms the
sidebar order: Start → Develop V-n (Geometry…Critical Loads) → Flight loads →
Other loads → Landing loads → Load-case plotting → Export. Oracles untouched (no
calc change).

**Key decisions.** G-4 (genuine re-sequence, not relabel); keep a Start shell
section (7 groups); numbered analysis phases + §4 names. Page consolidation deferred
to G3 so this step is a safe metadata-only move.

---

## Phase G — Step G1: Geometry single source of truth, incl. fuselage (complete, 2026-07-18)

**Objective.** All geometry (parametric fuselage/wing/tail/gear, the WINGGEOM
lifting-surface planforms, and a new fuselage outline) is defined on **one** page;
every downstream page reads it read-only and never re-asks it. Closes the doc's
"Is geometry before weight?" decision (geometry first) and the perceived
"data-not-stored" issue (G-3): re-entry, not true loss.

**Scope decisions (AskUserQuestion, 2026-07-18).** (1) **Fuselage outline** →
*station-area table* (`FuselageSection` width/height vs. station), because it
serves both the three-view body profile and the Step G4 slender-body moment
estimator (cross-section area ≈ π/4·w·h) from one model. (2) **Slice strategy** →
*unify into one slice* (the heavier refactor): the parametric `LayoutInput`
(formerly the top-level `Project.configuration`) and the fuselage outline move onto
`GeometryInput`, alongside the unchanged `.surfaces`. (3) **Nav / guard** → *one
step, relax guard*: one **Geometry** step, the `wing_geometry` module folded via
`FOLDED_MODULES` (the existing "one step, multiple modules" mechanism).

**Deliverables.**
- **`farloads/models.py`** — `GeometryInput` gains `parametric: Optional[LayoutInput]`
  and `fuselage: Optional[FuselageOutline]` beside `surfaces`; new `FuselageSection`
  /`FuselageOutline` dataclasses + `default_fuselage_outline(parametric)` (nose →
  0.35·L max section → tapered tail cone). `Project.configuration` **removed**.
  **`SCHEMA_VERSION` 24 → 25** with a v25 migration note.
- **`farloads/io.py`** — `geometry_from_dict`/`geometry_to_dict` carry
  `parametric` + `fuselage`; `project_from_dict` folds a legacy top-level
  `"configuration"` block onto `geometry.parametric` and defaults the fuselage
  outline from the scalars; the top-level `configuration` write is dropped.
- **`farloads/modules/configuration.py`**, **`validation.py`** — read
  `project.geometry.parametric`. Oracle-locked `.surfaces` consumers (AIRLOADS,
  WINGINER, NETLOADS, …) are untouched.
- **`app/views/configuration_layout.py`** — retitled **Geometry**; the sole editor
  of the unified slice (`_set_geometry` preserves the other fields on every write).
  New **Fuselage outline** editor (station-area `data_editor`) and **Lifting-surface
  planforms** editor (WINGGEOM surface polylines, merged in from the deleted
  `wing_geometry.py`). Three-view draws the fuselage from its outline sections.
- **Downstream read-through** — `flight_envelope.py`, `tail_loads.py`,
  `wing_loads.py`, `aircraft_comparison.py` read `geometry.parametric` read-only
  (they never wrote geometry — only the Geometry page does).
- **`farloads/workflow.py`** — one `configuration_layout`/**Geometry** step
  (`produces="geometry"`); `wing_geometry` added to `FOLDED_MODULES`.
- **`app/views/wing_geometry.py` deleted** (folded onto the Geometry page).

**Test / Acceptance.** Full suite green (390 tests: +`test_default_fuselage_outline_*`
and +`test_legacy_configuration_folds_into_geometry` /
+`test_explicit_fuselage_outline_round_trip_and_not_defaulted`; the smoke suite
loses one param with the removed view). Appendix A/B oracles unchanged (fixtures
re-expressed as `geometry=GeometryInput(parametric=…)`, same outputs). Views smoke
test renders the merged Geometry page. `ruff check farloads/ cli.py` clean. Verified
`examples/concept_regional_jet` migrates (`configuration` → `geometry.parametric` +
defaulted fuselage sections) and round-trips with no top-level `configuration` key.

**Key decisions.** G-2 (one geometry page, geometry first); unify into one slice;
fuselage = station-area table (feeds G4); one nav step + fold `wing_geometry`.
G0 already consumed the schema bump's predecessor, so G1 builds on v24 → v25.

---

## Phase G — Step G0: One unit per dimension, app-wide (complete, 2026-07-18)

**Objective.** Every quantity type has exactly one display unit per system, so no page
shows the same physical dimension two ways (the pre-G0 Configuration page mixed `in`,
`ft` and `ft²`). **Canonical units (locked 2026-07-18, decision G-1):** length →
**`in`** (SI **`mm`**), area → **`ft²`** (SI **`m²`**).

**Scope decision (deviation from the planned display-only G0).** The backlog framed G0
as display-only (relabel at the widget boundary, no schema change). On review the only
offending fields (tail spans in ft, tab area in in²) are *stored* with their unit baked
into the field name and feed oracle-locked calc, so a display-only relabel would have
put an `in` label on a feet value. The user chose the **strict rename** option
(AskUserQuestion, 2026-07-18): rename the fields to canonical-unit names, store
canonical units, and bump the schema — accepting that G0 thereby overlaps G1's schema
work. Calc results are held identical by converting back to the original ft/in² inside
the calc, so the Appendix A/B oracles are untouched.

**Deliverables.**
- **`farloads/models.py`** — renamed `TailLoadsInput.airplane_length_ft` and
  `VTailLoadsInput.{airplane_length_ft, wing_span_ft, vtail_mac_ft}` → `*_in` (store
  inches); `LayoutInput.{h_tail_span_ft, v_tail_span_ft}` → `*_in`;
  `TabSpec.area_sqin` → `area_sqft`. **`SCHEMA_VERSION` 23 → 24** with a v24 migration
  note.
- **`farloads/modules/select.py`** — the `Iyy`/`IZZ` default formulas substitute
  `LF_ft = LF_in/12`, `B_ft = B_in/12`, `VMAC_ft = VMAC_in/12` so the results are
  unchanged. **`configuration.py`** — tail-planform spans read inches directly (drop
  the `×12`). **`tab.py`** — `STAB_in = area_sqft × 144` at the call sites; the
  `LTAB = M·δ·Q·STAB/144` math is unchanged.
- **`farloads/units.py`** — removed the redundant `length_ft` and `area_sqin` kinds
  from `SI_PER_IMPERIAL`, `UNIT_LABELS` and `_KIND_FACTORS`; `_PROJECT_FIELD_KIND` maps
  the renamed keys to `length_in`/`area_sqft`.
- **`farloads/io.py`** — `_rename_legacy_units` migrates old files on load (feet keys
  `×12` → `*_in`, `area_sqin` `/144` → `area_sqft`), wired into
  `tail_loads_from_dict`, `vtail_loads_from_dict`, `configuration_from_dict`,
  `tab_loads_from_dict`. The new key wins if both are present (no double-conversion).
- **Views** — `configuration_layout.py` (spans as `length`/inches), `tail_loads.py`
  (span defaults read inches), `tab_loads.py` (area column as `area_sqft`).
- The bundled `examples/*.json` (older schema versions) are left to migrate via the
  load path rather than rewritten, matching existing practice.

**Test / Acceptance.** Full suite green (387 tests: +`test_one_display_unit_per_dimension`
in `test_units.py`, +`test_legacy_ft_sqin_keys_migrate_to_canonical` in `test_io.py`).
Appendix A/B oracles unchanged (`test_select`, `test_balloads`, `test_tab`,
`test_configuration` fixtures re-expressed in the new units, same asserted outputs).
`ruff check farloads/ cli.py` clean. Verified `examples/ga6_normal` and
`examples/concept_regional_jet` migrate and round-trip to the expected canonical values.

**Key decisions.** G-1 (one unit per dimension; length `in`, area `ft²`); strict rename
over display-only relabel (user, 2026-07-18) — calc-result-preserving, oracle-locked.

## Phase 1 — Step P1-5: Concept engine gyroscopic rates — guard + warn (complete, 2026-07-16)

**Objective.** `engine.py`'s `condition_25_371` (the optional FAR 25 gyroscopic
concept case) uses a fixed FAR 23.371(b) stand-in (2.5 rad/s yaw, 1 rad/s pitch) in
lieu of the maneuver-derived 25.371 rates the tool does not solve. The gyro moment is
linear in body rate, so the stand-in is conservative *only while the concept's real
rates stay at or below it* — for an agile concept it under-predicts silently. Add a
guard so the non-conservative case cannot pass silently, per decision **D-2 (guard +
warn, keep the fixed stand-in)**.

**Deliverables.**
- **`farloads/models.py`** — `EngineInput` gains two optional advisory fields,
  `design_yaw_rate_rad_s` / `design_pitch_rate_rad_s` (default `None`), the concept's
  real 25.371 body rates if known. `SCHEMA_VERSION` **22 → 23** (additive; older files
  load with both unset → no guard, fixed stand-in unchanged). No `io.py` change needed
  — `engine_from_dict`/`engine_to_dict` use `**d`/`asdict`, so the fields round-trip
  automatically; `units.to_imperial` uses `replace`, and rad/s are system-independent
  (like RPM), so they pass through both unit systems unchanged.
- **`farloads/modules/engine.py`** — `condition_25_371` keeps computing Myy/Mzz at the
  **fixed** stand-in rates (the moment never changes — advisory rates, not a
  re-derivation). When a declared rate exceeds its stand-in, the `ConditionResult.note`
  is replaced with a `WARNING -- gyroscopic loads UNDER-PREDICTED …` message naming the
  offending axis, the rate, and the moment ratio (`Myy x1.40`), pointing the engineer
  to scale by the ratio or solve the real 25.371 rates.
- **`app/views/engine_mount.py`** — two advisory rate inputs under the FAR 25 block
  (0 = leave unset), wired into the `EngineInput`; the per-condition note now renders as
  `st.warning` (not `st.info`) when it starts with `WARNING`, so the under-prediction
  case is visually flagged.
- **`tests/test_engine_far25.py`** — five tests: no-rates → no warning + stand-in note;
  rates at/below stand-in → no warning, moment unchanged; yaw > 2.5 and pitch > 1.0 →
  `WARNING`/`UNDER-PRED` note with the moment value **identical** to the fixed
  stand-in; and a JSON round-trip of the new fields (schema v23) that re-fires the
  warning through `calc.run`.

**Test / Acceptance (met).** A concept declaring a rate above the stand-in produces a
load result carrying an explicit under-prediction warning while the reported moment is
unchanged; the GA/light path (no declared rates) is untouched — no warning, oracle
intact. Full suite **385 passed** (379 → 385), `ruff check farloads/ cli.py` clean, the
edited view compiles.

**Key decisions.** **Warn-only, keep the fixed value** (D-2 literal / the acceptance's
"under-prediction warning" wording) — the declared rates are *advisory*, driving only
the guard, not the moment (the "solve for real rates" re-derivation stays deferred). The
override lives on `EngineInput` (per-engine, local to the case that uses it) rather than a
global concept slice. **Phase 1 is now complete** (P1-1…P1-5 all shipped).

## Phase 1 — Step P1-4: Complete the export package public API (complete, 2026-07-16)

**Objective.** The concept deliverable is "all components to sbeam", but
`farloads/export/__init__.py`'s `__all__` advertised only the **wing + tail**
families — `body_span_load_csv`, `body_force_moment_cards`, `control_surface_csv`,
`control_surface_force_moment_cards`, their `write_*` variants, and
`case_index_csv`/`filter_by_selected_case_ids` were reachable only via the
`sbeam_bridge` submodule. Re-export the missing surface and rewrite the wing-only
package docstring to describe all four component families + the case index.

**Deliverables.**
- **`farloads/export/__init__.py`** — imports and `__all__` extended with the body
  family (`body_span_load_csv`, `body_force_moment_cards`), the control-surface
  family (`control_surface_csv`/`control_surface_force_moment_cards` + their
  `write_*` variants), and the case-index family (`case_index_csv`,
  `write_case_index_csv`, `filter_by_selected_case_ids`). `__all__` is now grouped
  by component family (Wing / Body / Tail / Control / Case index). The module
  docstring is rewritten from "wing-only" to enumerate all four families plus the
  case index. (Body has no `write_*` CSV/card variants in `sbeam_bridge`, so none
  were invented; the case-index `write_case_index_csv` companion is included to keep
  the family's public surface complete.)
- **`tests/test_sbeam_bridge.py`** — `test_export_package_exposes_all_component_families`
  imports the full body/control/case-index surface directly `from farloads.export`,
  and asserts each re-exported name is in `export.__all__` and resolves (identity) to
  the `sbeam_bridge` implementation (no accidental shadowing).

**Test / Acceptance (met).** `from farloads.export import body_force_moment_cards,
control_surface_force_moment_cards` (and the rest of the surface) now works; the new
test imports the full surface. Full suite **379 passed** (378 → 379), `ruff check
farloads/ cli.py` clean. **API-surface-only step:** no calc-math change, no new
function, no `SCHEMA_VERSION` bump — only which names the package re-exports.

**Key decisions.** Re-export only functions that already exist (no new `write_body_*`
variants were invented, since the body family never had them); include
`write_case_index_csv` alongside `case_index_csv` so every CSV/cards producer that is
re-exported carries its `write_*` companion.

## Phase 1 — Step P1-3: True concept↔FAR23 identity test (complete, 2026-07-16)

**Objective.** The C-1 invariant ("concept mode reduces **exactly** to FAR23 on GA
inputs") was only *assumed* — guarded indirectly by the absence of regression on the
GA Appendix-A oracles, never verified *through the concept branch itself*. Add a
direct identity test: take a GA project, flip it to `category="C"` with the
FAR23-computed load factors, run the whole pipeline through the concept code path,
and assert the per-component loads reproduce the FAR23 result.

**Deliverables.**
- **`tests/test_concept.py`** — two tests + a comparison helper on
  `examples/ga6_normal.project.json` (Normal category, MTOW 3400 lb):
  - `test_concept_load_factors_match_far23_caps` pins the single numeric divergence
    point (`structural_speeds._maneuver_load_factors`): the FAR23 Normal cap
    (n = 3.8, nneg = −0.4·3.8 = −1.52 per 14 CFR 23.337), fed back as explicit
    `chosen_n`/`chosen_nneg` in concept mode, is echoed verbatim.
  - `test_concept_reduces_to_far23_on_ga_inputs` runs `run_all_modules` twice —
    baseline (`category="N"`) and concept (`category="C"` with the *derived* FAR23
    load factors) — and asserts full-pipeline parity: `_assert_modules_identical`
    compares by module name → condition `(title, far_reference)` → `LoadValue` label,
    checking equal `units`, `safety_factor`, and `value` (`math.isclose(rel_tol=1e-3)`,
    exact for dimensionless/int). `ConditionResult.note` is deliberately ignored — the
    appended concept note is the *only* permitted difference.
  - The file docstring is updated to record that the invariant is now guarded
    directly (not only via the oracle tests). Load factors are *derived* from the
    baseline STRSPEED result and fed forward (with a `3.8 / −1.52` citation assert),
    so the test stays robust if the fixture changes.

**Test / Acceptance (met).** GA-as-concept run reproduces the FAR23 loads to
`rel_tol=1e-3` across every module `run_all_modules` produces; the sweep fails if any
concept branch diverges numerically on GA inputs. Full suite **378 passed** (376 →
378), `ruff check farloads/ cli.py` clean. **Test-only step:** no calc-math change, no
new module, no `SCHEMA_VERSION` bump. (Removed one pre-existing unused import
(`StructuralSpeedsInput`) from the touched test file.)

**Key decisions.** Test lives in `test_concept.py` (extended, not a new file) —
concept tests stay together. Assertion breadth is the **full-pipeline sweep** (every
`LoadValue` of every module) rather than a few representative modules, since the whole
point is guarding *any* concept branch. N-factors are **derived from the baseline**
rather than hardcoded. Confirmed by investigation that
`_maneuver_load_factors` is the sole numeric concept↔FAR23 branch; every other
`is_concept` branch is note-text only — so the sweep's note exclusion is exactly the
permitted-difference boundary.

## Phase 1 — Step P1-2: Concept distributed-loads end-to-end + closure suite (complete, 2026-07-16)

**Objective.** Concept mode has no printed oracle above 12,500 lb, so physics
*closure* is its only validation — yet before P1-2 the only concept closure test
(`test_sbeam_bridge.py::test_concept_closure`) covered the **wing alone**. Drive
`net_loads`, `body_loads`, `taildist`, `aileron`, `flap`, `tab` through the P1-1
concept fixture and assert closure for every component, so concept results for the
tail/body/control surfaces stop being unverified.

**Deliverables.**
- **`tests/test_concept_closure.py`** (10 tests) on
  `examples/concept_regional_jet.project.json`, with its envelope + SELECT critical
  set materialised. Three kinds of check:
  - **Physics closure** (equilibrium identities evaluated through the concept code
    path, so a concept blow-up can't pass silently): wing
    `LZW + LT = Nz·W` (FLTLOADS vertical equilibrium) over all 120 V-n points; tail
    `LT·(Xt−Xcg) = LZW·(Xcg−Xw) − DX·(Zcg−Zw) + M(W+F)` (balancing load reacts the
    pitching moment about the CG); body terminal cumulative shear `= 0` (the
    fuselage net distribution is built free-free from inertia + tail air load + wing
    reaction).
  - **Cross-module ties** (per the chosen closure-depth decision): TAILDIST carries
    SELECT's `lt25`/`lt50` split verbatim (exact field equality across all 13 tail
    conditions — chosen over label-matching the "Total tail load" `LoadValue`, which
    diverges for the UNSYMMETRICAL and v-tail conditions); each control surface's
    `build_*` critical load matches a `lb`-unit `LoadValue` in that module's `run`
    analysis report (the distributed and analysis paths agree on the concept
    airframe).
  - **Export integrity**: every component family's nodal FORCE set — and its
    re-parsed `FORCE` cards (via the shared free-field reader imported from
    `test_sbeam_bridge`) — sums to that component's root/total at ULTIMATE
    (`limit × 1.5`); `test_full_airframe_exports_cleanly` is the P1-2 acceptance —
    wing + body + tail + control all export cleanly through `sbeam_bridge`.

**Test / Acceptance (met).** All closure identities hold to machine precision
(wing/tail rel ≈ 1e-16, body terminal shear ≈ 1e-12 lb) on the concept fixture;
the whole component set exports parseable, self-consistent decks. Full suite **376
passed** (366 → 376), `ruff` clean. **Test-only step:** no calc-math change, no new
module, no `SCHEMA_VERSION` bump — the FAR23 oracles are untouched.

**Key decisions.** Closure tests live in one dedicated `test_concept_closure.py`
(not scattered per-module); closure depth is nodal-sum + export integrity **plus
cross-module ties** (SELECT→TAILDIST field equality, control build↔run agreement),
not an independent physics re-derivation of tail balancing / control hinge moments.
The wing `Nz·W` and tail-moment identities re-use the FLTLOADS equilibrium formulas
deliberately — their value is asserting the concept branch stays balanced, not
re-deriving the aero.

## Phase 1 — Step P1-1: Full-airframe concept reference fixture (complete, 2026-07-16)

**Objective.** Concept mode (`category="C"`) was broadly wired into calc but its
headline deliverable — per-component distributed loads for a beyond-FAR23 airframe —
was only ever demonstrated for the *wing*. The one concept fixture
(`concept_heavy.project.json`) defined a wing surface only; run through
`run_all_modules` it fired 7 modules and skipped `net_loads`, `body_loads`,
`taildist`, `aileron`/`flap`/`tab`. P1-1 builds the full-airframe concept example so
the whole pipeline can be validated (closure checks are the follow-on Step P1-2).

**Deliverables.**
- **`examples/concept_regional_jet.project.json`** — "RJ-50 concept": a swept-wing,
  high-subsonic twin-turbofan regional jet (MTOW 33,000 lb, S 500 ft², b 66 ft,
  AR 8.7, c/4 sweep 24°, cruise M 0.74, 50 seats), `category="C"` with Part 25
  maneuver load factors (`chosen_n=2.5`, `chosen_nneg=-1.0`, `include_far25=true`).
  Carries every input slice — including the two no GA fixture had: `fuselage_mass`
  (body longitudinal mass stations) and `configuration` (`LayoutInput`). Drives
  **all 19** applicable modules with no missing-slice skip and selects the swept
  `AIRLOAD4` branch. Airplane chosen per **decision D-1** (2026-07-16); the twin
  turbofan is modelled with an empty propeller + a fan-spool `Rotor` (gyroscopic
  case via the 25.371 path, per **D-2**).
- **`farloads/io.py`** — bug fix: `_aero_surface_from_dict` / `aero_to_dict` now
  serialize `sweep_deg` and `design_mach`. These `AeroSurfaceInput` fields were
  added in Step C7 but never wired into the JSON round-trip; no GA fixture set them,
  so the gap was invisible until this swept concept fixture. Additive and defaulted
  (0.0), so every existing project loads unchanged and no oracle moves.
- **`tests/test_concept_regional_jet.py`** — 4 tests: fixture is concept + Part 25
  load factors; all required component modules run; AIRLOAD4 swept branch selected;
  `sweep_deg`/`design_mach` round-trip through `io` (the regression guard for the
  fix above).

**Test / Acceptance (met).** `run_all_modules` on the fixture reaches wing, body,
tail and all three control-surface modules without a `ValueError`; `airloads`
selects the AIRLOAD4 swept branch; the project round-trips through `io.py`. Full
suite **366 passed**, `ruff` clean. No FAR23 oracle change (concept path only; the
io fix is additive with GA-preserving defaults).

**Key decisions.** D-1 (regional-jet archetype), D-2 (fan-spool rotor for the
turbofan gyro case). **Accepted limitation:** the suite's `EngineLayout` has no
aft-fuselage option, so the aft-mounted twin is encoded as `2W` (symmetric mirror
butt lines) — a layout-sketch limitation, not a structural one; noted in the
backlog for a possible future `EngineLayout` addition.

## Phase F — Step F2: Aircraft Comparison page (complete, 2026-07-16)

**Objective.** Give the fleet comparison a first-class home. Before F2 the
comparison was bolted onto two *input* pages (Configuration & Layout, Weight
Estimate) via one shared helper, showing the same scatters twice with split subject
metrics and no single "how does this airplane compare?" view. F2 consolidates it
onto one dedicated **Aircraft Comparison** page in the Export phase and adds the
geometric plots the F1 data enables. Input-assessment only — no calc-math, no oracle
change; the reference set never enters a FAR computation.

**Deliverables.**
- **`app/views/aircraft_comparison.py`** — new GUI-only page (Export phase, before
  Results Review). Assembles the comparison subject from the best-available slices
  (`_subject_from_project`: MTOW ← speeds/direct-weight/WTESTIMA; OEW ← direct/
  WTESTIMA; area ← configuration/speeds; power ← Σ engines/estimation; AR ←
  configuration; seats ← speeds/estimation), showing a clear "—" when a metric is
  absent rather than dropping the subject. Renders the quantitative readout (nearest-3,
  W/S & W/P percentile band, outliers), a **parameter table** (subject on top + the
  nearest-N over MTOW/OEW/power/W-S/W-P/wingspan/area/AR/seats), **six scatter tabs**
  (W/S-vs-W/P, MTOW-vs-OEW, wingspan/area/AR/seats-vs-MTOW), and the reference-fleet
  expander. Owns its own `_REFERENCE_CSV` + `_fleet_points`.
- **`farloads/fleet.py`** — `Subject` gains presentation-only `wingspan_ft`,
  `aspect_ratio`, `seats` fields plus `span` (= `wingspan_ft`, else `√(AR·S)`) and
  `aspect_ratio_effective` (= `aspect_ratio`, else `span²/S`) derivations; the same
  two derivations added to `FleetPoint` for uniform handling. `fleet_stats` is
  untouched — geometry is never a distance term.
- **`farloads/workflow.py`** — new
  `WorkflowStep("aircraft_comparison", "Aircraft Comparison", EXPORT, module=None, …)`
  positioned immediately before `results_review`.
- **`app/views/configuration_layout.py` / `app/views/weight_estimate.py`** — the
  fleet block and its subject-metric assembly removed; the `render_fleet_comparison`
  imports dropped.
- **`app/components.py`** — `render_fleet_comparison`, `_fleet_readout`,
  `_fleet_points` and `_REFERENCE_CSV` deleted (no remaining callers); the module now
  holds only the FAR 23 applicability banner. Imports trimmed.
- **`tests/`** — new `test_aircraft_comparison.py` (subject assembly from an example
  project, the geometric-axis path from a synthetic project, and `None` without
  MTOW); `test_fleet_compare.py` extended with span/AR derivation tests and a
  distance-invariance test proving geometry adds no distance term.

**Test / Acceptance.** `ruff check farloads/ cli.py app/` clean; full `pytest` suite
passes (362, +15 over F1's 354). `test_workflow` still passes (GUI-only steps exempt
from the module↔step coverage assertion); the auto-discovered view smoke test runs
the new page without exception; `grep` confirms no remaining `render_fleet_comparison`
reference.

**Key decisions (locked with user, 2026-07-16).** **D-F2-a** — the nearest-N
similarity distance stays on MTOW / W/S / W/P; the new geometry is presentation-only
(table columns + plot axes), so the `fleet_stats` oracle is byte-identical.
**D-F2-b** — six tabs, one plot each (not a grid). **D-F2-c** — no category coloring
/ no `category` CSV column in F2 (kept as an Open question). The larger
comparator-set curation and in-UI user-supplied comparators remain **open questions
on Phase F** in the backlog.

---

## Phase F — Step F1: Reference-fleet expansion (complete, 2026-07-16)

**Objective.** Groundwork for the proposed Aircraft Comparison page (Phase F, see
`../30_future/00_backlog.md`): grow and enrich the reference-fleet data set so the
new page's geometric plots (span / area / aspect-ratio vs. MTOW) and parameter
table have the columns and spread they need. Data-only step — no calc-math, no
oracle change; the reference set never enters a FAR computation.

**Deliverables.**
- **`app/data/reference_aircraft.csv`** — new `aspect_ratio` column on every row
  (span²/area from the same row, so the geometric plots and the loading scatters
  stay consistent). Six aircraft added to broaden the geometric spread —
  Piper PA-28-181 Archer, Cirrus SR22, Diamond DA40, Extra 300 (low-AR aerobatic
  endpoint), Piper PA-44 Seminole (light twin), Daher TBM 940 (fast single
  turboprop) — 23 → 29 aircraft. Header comment updated (page reference + the
  aspect-ratio provenance note).
- **`farloads/fleet.py`** — `FleetPoint` gains optional `seats`, `wingspan_ft` and
  `aspect_ratio` fields (defaults, so `fleet_stats` and older callers are
  unaffected — the loading placement still runs on MTOW / W/S / W/P only).
- **`app/components.py`** — `_fleet_points` now maps the three new fields onto
  `FleetPoint`, tolerating a missing/NaN cell (an `_opt` helper) so a partially
  populated row still loads.
- **`tests/test_reference_aircraft.py`** — `aspect_ratio` added to the required
  columns; new `test_aspect_ratio_consistent_with_geometry` (positive and within
  5% of span²/area); the four added aircraft asserted present.

**Test / Acceptance.** `ruff check farloads/ cli.py` clean; full `pytest` suite
passes (354). The CSV round-trips through `_fleet_points` with all 29 rows carrying
the new geometry.

**Key decisions.** `aspect_ratio` is **stored** (not derived at plot time) so the
geometric plots need no computation and can honour a published AR that differs from
naïve span²/area for a cranked/tapered reference wing; the F1 rows use the
consistent span²/area value. The larger comparator-set curation (specific
concept-tier types, extra columns like `cruise_kt` / a `category` tag) and in-UI
user-supplied comparators remain **open questions on Phase F** in the backlog,
pending user direction; F1 ships the unambiguous column + a confident GA→turboprop
spread.

---

## Phase E — Step E7: Speed–altitude envelope consolidation (complete, 2026-07-16)

**Objective.** Remove the input redundancy between **Structural Speeds** and **Mach
Limit**, and upgrade the Mach-limit chart into a transport-category-style
speed–altitude flight-limits diagram (altitude on y, selectable KEAS/KCAS/KTAS on
x, constant-Mach fan + the composite design-speed boundary). No calc-math or oracle
change — `mach_limit_lines` is untouched; the airspeed conversions are a new
presentation-layer helper.

**Deliverables.**
- **`farloads/constants.py`** — new `convert_airspeed(eas_kt, altitude_ft, unit)`
  (KEAS/KTAS/KCAS), plus `eas_to_mach`/`mach_to_eas` and `SEA_LEVEL_SOUND_KT`. KTAS =
  KEAS/√σ; KCAS via the standard subsonic compressible impact-pressure relation
  (`qc/P0 = δ·((1+0.2M²)^3.5−1)`, `δ = σ·(a/a0)²`), exact at sea level. Pure calc,
  no I/O.
- **`app/views/mach_limit.py`** — retitled **Speed–Altitude Envelope**. MC, MD and
  the shoulder altitude are now READ from the `speeds` slice
  (`design_speed_values`) instead of re-entered — only the max operating altitude
  and increment remain as inputs (same unused-upstream-data fix class as Config &
  Layout). The old V-vs-altitude chart is replaced by a speed–altitude diagram:
  altitude on y; a **KEAS/KCAS/KTAS** radio for the x-axis; a thin constant-Mach
  fan; and the operating boundary drawn as EAS-limited (constant) below the shoulder
  and Mach-limited (V=M·a·√σ) above it, so VC/MC and VD/MD kink at the shoulder
  exactly like a placard chart. `use_container_width` replaced by `width="stretch"`.
- **`farloads/workflow.py`** — the `mach_limit` step is retitled "Speed–Altitude
  Envelope" with an updated summary (module name unchanged, so the CLI/oracle path
  and the every-module-has-a-step nav test are unaffected).
- **`tests/test_airspeed_conversions.py`** — new: sea-level unit equality,
  KTAS = KEAS/√σ, EAS < CAS < TAS at altitude, Mach round-trip, unknown-unit error.
- **Docs** — `PROGRAM_SPEC.md` MACHLIM notes and `docs/20_theory/00_theory_sources.md`
  updated; `cspell.json` gains KCAS/KTAS.

**Test / Acceptance.** `ruff check farloads/ cli.py` clean; full `pytest` suite
passes (353). Smoke-checked against `examples/ga6_normal.project.json`: the VC/MC
boundary is ~170 KEAS constant to the 12000 ft shoulder then curves in to ~151 KEAS
at 18000 ft; VA/VF are constant-EAS lines; the Mach fan and MNE/MFC lines render.

**Key decisions.** The diagram stays on its own page (following the Step E6 V-n
precedent: inputs on the owning page, picture on a dedicated page). MC/MD/shoulder
are read-only echoes of Structural Speeds; the page adds only the two quantities
Structural Speeds does not carry. All chart speeds are design *limit* speeds — the
diagram is a speed boundary, not a load deliverable, so the ULT rule does not apply.

---

## Phase E — Step E6: V-n diagram consolidation (complete, 2026-07-15)

**Objective.** Remove the redundant second V-n diagram: consolidate the two V-n
plots (the continuous LIMIT textbook envelope on **Structural Speeds**, added in
Step E3, and the rigorous Mach-corrected balanced corner points on **Flight
Envelope (V-n)**) into a single figure on the Flight Envelope page. GUI-only:
**no schema change** and **no calc-math change** — `farloads/vn_diagram.py` and its
oracle/closure tests are untouched.

**Deliverables.**
- **`app/views/flight_envelope.py`** — the continuous LIMIT design envelope
  (`build_vn_diagram` from `farloads/vn_diagram.py`) is now drawn as a grey backdrop
  behind the rigorous balanced markers, so the envelope visibly *bounds* them. It is
  rebuilt from `project.speeds` (a required slice here) via `design_speed_values` —
  no new input widgets. Gust lines (altitude-dependent, textbook Pratt) are drawn
  only for a single selected altitude; the altitude-independent maneuver envelope is
  always drawn. Backdrop build is wrapped in `try/except (ValueError,
  ZeroDivisionError)` so it degrades to the rigorous-points-only plot rather than
  erroring. The `gust_approximate` caption (missing lift-curve slope / MAC) carried
  over from Structural Speeds.
- **`app/views/structural_speeds.py`** — the Step E3 V-n block removed; the page now
  shows only its numeric design-speed tables plus a caption pointing to the Flight
  Envelope (V-n) page. Now-unused imports (`plotly.graph_objects`, `build_vn_diagram`,
  `resolve_gust_inputs`, `design_speed_values`) dropped.
- **Docs** — `docs/10_standard/GUI_design.md` §8.2/§11 updated to reflect the single
  consolidated V-n on the Flight Envelope page.

**Test / Acceptance.** `ruff check` clean (no unused imports left); full `pytest`
suite passes unchanged (347) — no calc or schema change. Manual: the Flight Envelope
V-n renders the balanced markers on the LIMIT-envelope backdrop; toggling single
altitude (gust lines shown) vs "Overlay all altitudes" (gust lines suppressed,
maneuver envelope still drawn) behaves; a project missing aero/MAC degrades
gracefully. Structural Speeds shows no diagram, only tables + pointer.

**Key decisions.** The two diagrams were *complementary*, not literal duplicates
(continuous textbook envelope vs discrete rigorous points), but share LIMIT
load-factor-vs-KEAS axes — so they were overlaid rather than one simply deleted
(user choice), keeping the classic envelope shape as a bound on the rigorous points.
This supersedes the Step E3 "V-n lives on Structural Speeds only" decision.

---

## Phase E — Step E5: Load-path robustness (complete, 2026-07-15)

**Objective.** Make the sidebar project load fail gracefully and be schema-aware.
GUI-only: **no schema change** (`SCHEMA_VERSION` stays 22) and **no calc-math
change** — the Appendix A/B oracles pass unmodified.

**Deliverables.**
- **`farloads/io.py`** — a new pure, unit-tested `schema_status(version) ->
  (status, message)` helper (no Streamlit): classifies an on-disk
  `schema_version` as `"ok"` / `"newer"` (loads anyway; unrecognized fields
  ignored) / `"older"` (its field-presence migration already ran in
  `project_from_dict`; the caller bumps the stamp to `SCHEMA_VERSION`).
- **`app/Home.py`** — a `_safe_load(build, source) -> Project | None` wrapper
  around all three sidebar load actions (Open saved, Load example, Upload) that
  catches `(json.JSONDecodeError, OSError, TypeError, ValueError, KeyError,
  AttributeError)` and shows `st.error("Couldn't load …: …")` instead of an
  uncaught traceback, returning `None` so the load is skipped. On success it runs
  `_apply_schema_check`: a newer file toasts a ⚠️ warning, an older file is
  migrated in place and toasts a 🔁 notice. Toasts (not `st.warning`) because the
  adopt path ends in `st.rerun()`, which would discard an ordinary message.
- **`app/views/project_editor.py`** — the same schema check wired into **Apply**
  after the existing graceful `project_from_dict` guard (this page does not rerun
  before render, so it surfaces `st.warning` / `st.info` inline rather than a
  toast).
- **Tests** — `tests/test_io.py` (+4): `schema_status` for older/current/newer and
  a malformed-dict guard asserting `project_from_dict` raises one of the caught
  types (the contract `_safe_load` relies on to show `st.error`).

**Test / Acceptance.** Full suite (**347 passed**, +4) + `ruff check farloads/
cli.py app/` clean, confirming the no-calc-change invariant. A malformed /
newer-schema file shows a message, not a traceback (sidebar and editor); a valid
older file (e.g. `examples/ga6_normal.project.json`, schema 12) still loads and is
migrated. Docs synced (`GUI_design.md §10/§11`, this history + `CHANGELOG.md`,
backlog E5 removed / Phase E marked complete).

**Key decisions.** (D-E5-1) The classification is a **pure, unit-tested**
`schema_status` in `io.py` (mirroring `fleet.py` / `applicability.py`), exceeding
the backlog's manual-only acceptance so the version logic is regression-safe.
(D-E5-2) The schema check is **shared into both** the sidebar and the JSON Editor
(user-approved 2026-07-15), not sidebar-only, so behavior is consistent wherever a
project is built from raw JSON. (D-E5-3) An older file is **migrated with a visible
toast** ("Migrated from schema N to 22"), not silently — nothing is written to disk
until the user Saves. A newer file **warns and still loads** rather than blocking,
per the backlog direction.

---

## Phase E — Step E4: Fleet comparison upgrade (complete, 2026-07-15)

**Objective.** Turn the visual, duplicated fleet comparison into a shared,
quantitative one. GUI-only in effect: **no schema change** (`SCHEMA_VERSION` stays
22) and **no calc-math change** — the Appendix A/B oracles pass unmodified; the new
`fleet.py` is an additive pure helper.

**Deliverables.**
- **`farloads/fleet.py`** — a pure, unit-tested placement helper (no pandas / file
  access / Streamlit): `FleetPoint` / `Subject` records (with derived `w_s`/`w_p`,
  `w_p = None` for a jet), `fleet_stats(subject, fleet, *, n=3, band=(10, 90))
  -> FleetStats`, and `percentile_rank` / `percentile` helpers. Nearest-N uses a
  normalized-Euclidean distance over whichever metrics the subject supplies (always
  `log10(MTOW)`, plus W/S and W/P when known), each divided by the fleet spread so
  the axes are commensurate; a fleet point missing an axis (a jet's W/P) simply
  drops that term. Percentile rank + p10–p90 outlier band on the subject's W/S and
  W/P.
- **`app/components.render_fleet_comparison(project, *, name, mtow, oew, wing_area,
  power)`** — the single shared presentation wrapper: loads
  `app/data/reference_aircraft.csv`, builds the `FleetPoint`s + `Subject`, renders
  the quantitative readout (W/S & W/P percentile-band metrics, a nearest-3 table
  with distances, an outlier warning) then the W/S-vs-W/P and MTOW-vs-OEW scatters.
- **`configuration_layout.py` / `weight_estimate.py`** — the duplicated ~65-line
  fleet blocks are deleted; each page now calls `render_fleet_comparison` with the
  subject values it already computes (Configuration supplies wing area + installed
  power; Weight Estimate supplies estimated MTOW/OEW + power, no subject wing area
  → its W/S shows "—").
- **Tests** — `tests/test_fleet_compare.py` (10): nearest-N ordering/count, the
  jet-as-neighbour case, percentile rank + band, outlier firing / silence on a
  central design, the no-wing-area (Weight-Estimate) subject, the standalone
  percentile helpers, and an empty-fleet guard.

**Test / Acceptance.** Full suite (**343 passed**, +10 for the new test file) +
`ruff check farloads/ cli.py app/` clean, confirming the no-calc-change invariant;
`app/components.py` imports cleanly and exposes `render_fleet_comparison`. The
existing `tests/test_reference_aircraft.py` still guards the CSV shape. Docs synced
(`GUI_design.md §8.4/§11`, `PROJECT_GUIDE.md` package layout, this history +
`CHANGELOG.md`, backlog E4 removed).

**Key decisions.** (D-E4-1) The numeric core lives in a **pure, unit-tested
`farloads/fleet.py`** (mirroring `applicability.py` / `validation.py`) with the CSV
load + rendering in an `app/components.py` wrapper, exceeding the backlog's
manual-only acceptance to keep the math regression-safe. (D-E4-2) Nearest-N is an
**adaptive normalized-Euclidean** metric over the metrics the subject has; the
outlier flag is the fleet **p10–p90** band. (D-E4-3) The readout lists the
**nearest 3** from the **whole fleet**, with jets (`max_hp = 0`) excluded from W/P
distance and the W/P percentile only, never from the comparator pool. Both pages
now render **both** scatters (the readout is the unification), where previously
Weight Estimate showed only MTOW-vs-OEW.

---

## Phase E — Step E3: Graphical review + input-consistency validation (complete, 2026-07-15)

**Objective.** Give the input-heavy definition pages a visual sanity check and
explicit input-consistency warnings. GUI-only in effect: **no schema change**
(`SCHEMA_VERSION` stays 22) and **no calc-math change** — the Appendix A/B oracles
pass unmodified, and the two new modules are additive pure helpers, not edits to
any oracle-locked calc.

**Deliverables.**
- **`farloads/vn_diagram.py`** — a pure, unit-tested V-n diagram builder:
  `build_vn_diagram(...)` returns the plottable polylines — the curved stall
  boundary `n = (V/VS)²` sampled VS→VA (fixing the corner-to-corner straight line),
  the closed positive/negative flaps-up manoeuvre envelope, the flaps-down envelope
  off VSF/VF capped at n = 2.0 (14 CFR 23.337(b)), and the up/down gust lines at
  VC/VD (textbook Pratt form, 14 CFR 23.341). `resolve_gust_inputs(...)` resolves
  the wing lift-curve slope + MAC from the aero/geometry slices when present, else
  textbook defaults (flagged `approximate`).
- **`farloads/validation.py`** — pure input-consistency predicates,
  `consistency_warnings(project) -> list[ConsistencyWarning]`, each tagged with the
  page that renders it: taper ratio > 1, non-positive reference area,
  leading-/trailing-edge ordering, Configuration-vs-WINGGEOM wing-area mismatch
  (5% tol), and CG outside the WTENV structural CG envelope (skipped when that
  envelope or the wing geometry is absent).
- **Structural Speeds page** — a **V-n diagram** section (Flaps up/down/both radio,
  gust-line toggle) rendered from `vn_diagram`, LIMIT-marked, captioned that the
  gust lines are approximate and pointing to the rigorous Flight Envelope V-n.
- **Weight/CG/Inertia page** — a **CG marker + mass-distribution** plot (per-item
  weight stem at its fuselage station, coloured by mass kind, the loading CG line,
  and the WTENV fwd/aft structural limits when defined) plus the CG-outside-envelope
  warning.
- **Wing Geometry** and **Configuration & Layout** pages render their tagged subset
  of `consistency_warnings` as `st.warning`.
- **Tests** — `tests/test_vn_diagram.py` (8) and `tests/test_validation.py` (10):
  physics-closure on the V-n geometry and each predicate firing on crafted bad
  input while silent on the Appendix-A GA fixture.

**Test / Acceptance.** Headless `AppTest` on the four touched pages: all render with
**no exceptions** on the GA fixture; the CG warning fires on a far-aft ballast
loading and is silent on good input. Full suite (**333 passed**, +18 for the two new
test files) + `ruff check farloads/ cli.py app/` clean, confirming the
no-calc-change invariant. Docs synced (`GUI_design.md §8.2/§8.3/§11`,
`PROJECT_GUIDE.md` package layout, `20_theory/00_theory_sources.md`, this history +
`CHANGELOG.md`, backlog E3 removed).

**Key decisions.** The V-n lives on **Structural Speeds only** (user choice); its
gust lines use the **textbook Pratt form** rather than FLTLOADS' Mach-corrected
iteration, so the **Flight Envelope page is left unchanged** and the two can differ
slightly — the Structural Speeds caption makes this explicit. The CG check is
against the **WTENV structural envelope** (not the simpler `cg_cases` extents),
skipped silently when undefined. Predicates live in a **pure, unit-tested
`farloads/validation.py`** (mirroring `applicability.py`) rather than an app-side
helper, exceeding the backlog's manual-only acceptance to keep the warnings
regression-safe.

---

## Phase E — Step E2: Parameter explanation (tooltips + guides) (complete, 2026-07-15)

**Objective.** Make every airplane-definition input self-explanatory. GUI-only:
no schema change (`SCHEMA_VERSION` stays 22) and no calc-math change — the
Appendix A/B oracles pass unmodified. Scope is the six Airplane-section pages;
the Analysis-phase pages are out of scope.

**Deliverables.**
- **`help=` hover tooltips** on every non-grid domain input widget across
  `app/views/configuration_layout.py` (23 widgets — fuselage/wing/tail/gear
  geometry + tail-type + engine X/Y/Z), `weight_estimate.py` (airplane, power,
  engines, seats, endurance, baggage, pressurized, engine type),
  `structural_speeds.py` (category, design weight, wing area, VH/VS/VSF, shoulder
  altitude, VC/VD, concept n/n_neg), `aero_coefficients.py` (config names, stall
  CL / neg-stall CL, include-flaps-down), and `wing_geometry.py` (symmetric,
  integration elements). The `configuration_layout._num` helper gained a
  pass-through `help` parameter. Each tooltip cites the FAR paragraph and/or the
  Reference-1 program/chapter (regulation + chapter, not exact PDF pages).
- **"ℹ️ Parameter guide" expanders** (collapsible, `expanded=False`) on the five
  pages that need one: Configuration & Layout (MAC / XLEMAC / neutral point /
  static margin / tip-back / overturn / datum convention), Wing / Surface
  Geometry (XLE/YLE/XTE/YTE / symmetric / integration elements / derived
  Area·MAC·XLEMAC·AR·span), Weight/CG/Inertia (weight_lb / x·y·z stations /
  ixx·iyy·izz per-item inertias with the parallel-axis note / mass `kind`),
  Structural Speeds (VS/VSF/VA/VC/VD/VF/VH / shoulder altitude / KEAS / concept
  factors), and Aerodynamic Data (the `C0…C4` lift/drag/moment polynomials, α in
  degrees / stall CL / cruise-vs-flaps-down balancing).
- **Grid (`st.data_editor`) pages** (Weight/CG inertias, Wing Geometry LE/TE
  points, the Aero `C0…C4` table) explain their columns in the guide expander
  rather than per column (no per-column `help=`).

**Test / Acceptance.** Headless `AppTest` end-to-end on all six pages: every page
renders with **no exceptions**; widgets carry their tooltips (config 23, speeds
12, aero 7, wing-geometry 2 once a surface exists) and each guide expander +
glossary term renders. Full suite (**314 passed**) + `ruff check farloads/ cli.py
app/` clean, confirming the GUI-only / no-calc-change invariant. Docs synced
(`GUI_design.md §8.1`/§11, this history + `CHANGELOG.md`, backlog E2 removed).

**Key decisions.** Citations are **regulation paragraph + Reference-1
program/chapter**, not exact PDF page numbers (user choice — avoids a per-field
371-page trawl for equivalent traceability). Grid inputs are covered by the
**guide expander only**, not per-column `help=` (user choice — the column-header
tooltip is more limited and the grids' fields are better defined together).
Tooltips are **inline `help=` strings** next to each widget (matching the existing
E1 pattern on `occupants`/`crew`), not a shared help-text module. Guide expanders
landed on **five** pages, not only the three "dense" pages the backlog named,
because the grid pages' "guide-only" decision makes the expander the sole
explanation vehicle for their columns.

---

## Phase E — Step E1: FAR 23 applicability + occupants/crew fields (complete, 2026-07-15)

**Objective.** Detect and surface — never block — when an airplane exceeds FAR 23
applicability (higher MTOW / more occupants), so a beyond-FAR23 configuration no
longer runs GA-calibrated math silently; add the occupant count the seat-limit
check needs and a user-set flight-crew count carried in the operating empty weight.
No calc-math change: the Appendix A/B oracles pass unmodified and concept mode still
reduces exactly to FAR 23 on GA inputs.

**Deliverables.**
- **Limits block** in `farloads/constants.py`: `FAR23_MAX_WEIGHT_LB = 12500`,
  `FAR23_MAX_PASSENGER_SEATS = 9`, the encoded-but-dormant commuter tier
  (`FAR23_COMMUTER_MAX_WEIGHT_LB = 19000` / `FAR23_COMMUTER_MAX_PASSENGER_SEATS = 19`),
  and `DEFAULT_FLIGHT_CREW = 1` (the crew assumed when no weight-estimation slice is
  present), cited to 14 CFR 23.1.
- **Pure helper** `farloads/applicability.py`: `Exceedance(field, value, limit,
  label)`, `effective_occupants` (speeds.occupants, else Weight Estimate seats),
  `effective_crew` (weight.estimation.crew, else `DEFAULT_FLIGHT_CREW`),
  `design_weight_lb` (speeds.weight_lb, else Weight DB total), and
  `far23_applicability(project)` (`passenger seats = occupants − crew`) — no
  Streamlit, unit-tested, yields `[]` on Appendix-A GA inputs. Exported from
  `farloads` (`far23_applicability`, `Exceedance`).
- **Schema fields** (`SCHEMA_VERSION` **20 → 22**, additive; older files load with
  defaults): `StructuralSpeedsInput.occupants: Optional[int] = None` (falls back to
  `weight.estimation.seats`), entered on **Structural Speeds** and echoed read-only
  on **Configuration & Layout**; and `WeightEstimationInput.crew: int = 1`, entered
  on **Weight Estimate**, subtracted from occupants for the seat check and carried
  in a derived **operating empty weight** line WTESTIMA reports
  (`OEW = empty + crew×170`; reporting-only, `MTOW`/`useful`/`empty` and their
  Appendix-A oracles untouched, so it is not re-summed with the useful load).
- **Shared banner** `app/components.render_applicability_banner(project)` on the
  Dashboard + definition pages: non-blocking `st.warning` + per-exceedance rows +
  a one-click **"Switch to Concept"** button that sets `speeds.category = "C"` and
  seeds `chosen_n`/`chosen_nneg` from the computed FAR 23.337 factors (via
  `structural_speeds._maneuver_load_factors`) so the flip never raises. Suppressed
  when the project is already concept. `tests/conftest.py` adds `app/` to the path
  so the view smoke test resolves `components` (Streamlit provides it at runtime via
  the `app/Home.py` entrypoint).

**Test / Acceptance.** `tests/test_applicability.py` (new): GA Appendix-A →
no exceedances; a 20,000 lb / 12-occupant Normal → weight (20,000 > 12,500) + seat
(12 − 1 crew = 11 > 9) exceedances; crew reduces the passenger-seat count;
`effective_occupants`/`effective_crew`/`design_weight_lb` fallbacks.
`tests/test_weight_estimate.py`: the derived OEW line (empty 2150 + crew×170) with
the empty/MTOW oracles unchanged. `tests/test_io.py`: `occupants`/`crew` round-trip
and old files (no key) load with the defaults. Headless `AppTest` end-to-end: banner
renders for an over-limit Normal airplane, "Switch to Concept" seeds n=2.9 /
n_neg=−1.16 with no exception and hides the banner, GA inputs show none. Full suite
(314 passed) + `ruff check farloads/ cli.py app/` clean. Docs synced
(`PROGRAM_SPEC.md`, `20_theory/00_theory_sources.md`, `GUI_design.md §9`, this
history + `CHANGELOG.md`).

**Key decisions.** Seat limit counts **passenger seats excluding crew**, where crew
is the **user-set `WeightEstimationInput.crew`** (default 1), not a hardcoded
constant. Crew weight is carried in a **derived OEW reporting line** (`empty +
crew×170`) rather than reclassifying the itemized crew items into the `EMPTY`
bucket — that keeps the WTESTIMA empty (2150) and WTENV empty-weight-station (85.1)
oracles intact (the oracle-safe option the user chose over a documented oracle
deviation). `occupants` is an **independent field seeded from `weight.seats`**
(seed-chain), not a re-use of it. The MTOW check reads **`speeds.weight_lb`, falling
back to the Weight DB total**. "Switch to Concept" **auto-seeds the concept load
factors** from the FAR 23.337 values. The commuter tier (19,000 / 19) is **encoded
but dormant** — the merged "Normal / commuter" category maps to `"N"`, so the check
uses the non-commuter tier until a distinct Commuter category lands (see backlog
"Distinct Commuter category").

## GUI fix — Imperial/SI input widgets & upstream-data seeding (complete, 2026-07-15)

**Objective.** Complete the session-wide Imperial/SI toggle so it governs
**inputs**, not just results, and stop the definition pages re-asking for data
the project already holds. The global toggle (`app/Home.py`,
`st.session_state["unit_system"]`) was advertised as applying "everywhere," but
only *results* respected it — every input widget (sidebar forms, `data_editor`
tables) accepted and displayed Imperial regardless, so an SI user entered SI-
looking numbers that were stored as Imperial (bug A). Separately, several pages
opened with blank/duplicate fields for quantities an upstream slice already
owned (bug B). Pure GUI/presentation-boundary work: no calc-math change, the
Appendix A/B oracles pass unmodified, no new `Project` slice, `SCHEMA_VERSION`
stays at 20. 19 files, ~698 insertions.

**Deliverables.**
- **Bug A — input widgets respect the toggle.** Extended `farloads/units.py`'s
  scalar kind tables (`SI_PER_IMPERIAL`/`UNIT_LABELS`) with `area_sqft`,
  `length_ft`, `inertia_lbin2` and `area_sqin`, then applied the
  `engine_mount.py` input pattern to every remaining page with domain inputs:
  read `system`, `U = labels_for(system)`, seed via `to_display(value, kind,
  system)`, unit-suffix the label, suffix the widget `key` with `system.value`
  (so switching units re-seeds the widget), and convert back with
  `to_imperial_scalar` on Apply so the `Project` stays canonical Imperial.
  Pages: `configuration_layout`, `structural_speeds`, `wing_geometry`,
  `weight_cg_inertia`, `aileron_loads`, `flap_loads`, `flight_envelope`,
  `fuselage_loads`, `landing_loads`, `mach_limit`, `payload_cases`,
  `tab_loads`, `tail_loads`, `weight_envelope`, `weight_estimate`,
  `wing_loads`. `loads_plots.py` — which never referenced the toggle at all —
  gained display-only conversion of its plotted values and axis/legend labels
  (its external-comparison CSV overlay is forced Imperial, since imported span-
  load CSVs are always canonical Imperial). Airspeed (KEAS) and altitude (ft)
  stay aviation-standard in both systems, unchanged.
- **Bug B — seed from upstream data.** New
  `farloads.modules.configuration.wing_layout_from_surface()` (the inverse of
  `wing_polylines`) lets **Configuration & Layout** seed its parametric wing
  fields (area / aspect ratio / taper / LE sweep / LE station) from an existing
  WINGGEOM `wing` surface when no `configuration` slice exists yet. **Flight
  Envelope** seeds MAC / wing area / 25%-MAC station from the `wing` surface
  (and waterline from `configuration`) instead of hardcoded Appendix-A literals;
  **Mach Limit** seeds `MC`/`MD`/shoulder altitude from STRSPEED's
  `design_speed_values`; **Tail Loads** seeds the h/v-tail spans from
  `configuration.h_tail_span_ft`/`v_tail_span_ft`; **Wing Loads** seeds dihedral
  from `configuration.dihedral_deg`. Every seed fires only when the page's own
  field is still unset, so an explicit value is never overwritten.

**Test / Acceptance.**
- Full suite (`pytest -q`): **303 passed**; `ruff check farloads/ cli.py app/`
  clean. No test change needed — the calc core, `Project` schema and
  CSV/report units are untouched.
- Runtime verification via `streamlit.testing.v1.AppTest` (no browser tooling
  in-env): confirmed the Imperial→SI display conversion and the SI→Imperial
  Apply round-trip on representative pages (e.g. Configuration & Layout
  fuselage length 5000 mm → stored 196.85 in; Structural Speeds 1000 kg →
  2204.62 lb), that VH/VS/VC/VD/altitude stay kt/ft under SI, and each bug-B
  seed (Config wing area 138.89 ft² from a surface; Flight Envelope MAC 50.665;
  Mach Limit MC/MD from STRSPEED; Wing Loads dihedral 5.5° from Config).

**Key decisions.**
- **Input-boundary conversion, not a stored unit.** `project.json` and the calc
  core stay Imperial-only; the toggle converts at each widget's seed/Apply
  boundary exactly like the results path — no unit tag is ever written to disk,
  so oracle fixtures and older files are unaffected.
- **Occupancy/`seats` left as-is.** Time-in-hours and the weight-regression
  `seats` count have no unit kind and were not converted (consistent with the
  airspeed/altitude aviation-standard exception); a real applicability
  occupants field is scoped to backlog **Phase E1**, not this fix.
- **Aero-coefficient page unchanged.** Its inputs are dimensionless polynomial
  coefficients, so no unit handling applies.

---

## Phase D — Step D8: Export & report upgrades (complete, 2026-07-09)

**Objective.** Close out Phase D (the six-section GUI restructure) with the
last Export-page item: a multi-sheet `.xlsx` workbook alternative to the
`.zip` bundle, and wiring the D5 Critical Loads case selection into the
sbeam/case-index exports where the case-id lineage actually supports it. Pure
GUI/export-layer step, no calc-math change; no new `Project` slice, so
`SCHEMA_VERSION` stays at 19. D8.1 (the case-index table) had already shipped
as part of D1.

**Deliverables.**
- **D8.2 — `.xlsx` workbook.** New `farloads/export/workbook.py::build_workbook`
  (pure renderer, `openpyxl` dependency added to `pyproject.toml`): re-shapes
  the strings/rows the Export page already computes for the CSV/`.zip`
  channel into one workbook — a `Project` sheet, one tab per module with
  results, a `Case Index` sheet, and the tabular sbeam span-load CSVs (wing/
  fuselage span loads, tail chordwise, control-surface loads); BDF card text
  is excluded (not tabular). Export page gained a "📊 Download workbook
  (.xlsx)" button, a sibling alternative to the `.zip` (not nested inside it).
- **D8.3 — export scope filter.** New pure helper
  `sbeam_bridge.filter_by_selected_case_ids(results, selected_ids)`
  (`selected_ids is None` = unfiltered; a result with no `case_ref` is always
  kept). The Export page gained an "Export scope" toggle (Full set /
  Governing set), disabled when nothing is deselected on the Critical Loads
  page. Tracing the case-id lineage found the filter is **exact only for
  fuselage and tail** (`body_loads.py`/`taildist.py` copy `case_ref` verbatim
  from `envelope.critical.conditions`) — wing (`WingMassInput.cases`, user-
  authored) and control-surface (aileron/flap/tab) results mint independent
  case ids on disjoint bands that never overlap `envelope.critical`'s (the
  known "Unify select_wing/one_engine_out case identity" gap), so those two
  always export the full set with an explanatory caption rather than
  silently filtering to nothing.

**Test / Acceptance.**
- `tests/test_workbook.py` (new): builds a workbook from `ga6_normal
  .project.json`, re-opens it with `openpyxl.load_workbook`, and asserts
  expected sheet names, `Project`-sheet field/value round-trip, module-sheet
  row counts matching their source CSVs, and that no BDF card text leaked
  into any sheet.
- `tests/test_sbeam_bridge.py`: three new cases for
  `filter_by_selected_case_ids` (unfiltered passthrough, keep-only-selected,
  empty-selection drops all tagged cases).
- Full suite (`pytest -q`): 290 passed; `ruff check farloads/ cli.py app/`
  clean.
- Manual verification: `streamlit run app/Home.py` against `examples/
  ga6_normal.project.json` — Export page loads, the workbook button produces
  a valid `.xlsx`, the scope toggle is disabled until a condition is
  deselected on Critical Loads, and the wing/control-surface caption appears
  once the toggle is enabled.

**Key decisions** (resolved with the user before implementation).
- **xlsx library.** `openpyxl` (pandas' default xlsx engine) over `xlsxwriter`
  — no rich formatting needed here.
- **D8.3 scope for the wing/control-surface gap.** Filter where the case-id
  lineage genuinely matches (fuselage/tail); leave wing/control-surface always
  full-set with a caption, rather than deferring D8.3 until the id-unification
  mini-step lands.
- **Toggle blast radius.** The scope toggle affects only the sbeam BDF/CSV
  artifacts and the case index; per-module load-case CSVs and the combined
  text report always show every computed case (the oracle-traceable record,
  not the structural hand-off).

Closes Phase D (Steps D0–D8) — the six-section GUI restructure is complete;
remaining work is the deferred calc refinements and open design decisions in
`docs/30_future/00_backlog.md`.

---

## Phase D — Step D7: Loads Plots page (complete, 2026-07-09)

**Objective.** Add the sixth workflow section's page: a consolidated,
read-only viewer over the distributed-load results the Analysis pages already
persist on `Project.loads` — overlay shear/moment/torsion by case ID, an
enveloped (max |value|) curve, a wing+fuselage whole-airframe snapshot, and an
external-comparison CSV import — plus the "confirm every plot the original
suite rendered has a Streamlit equivalent" graphics audit. Pure GUI/view-layer
step, no calc-math change; no new `Project` slice, so `SCHEMA_VERSION` stays
at 19.

**Deliverables.**
- `app/views/loads_plots.py` (new): component picker (Wing / Fuselage /
  Horizontal Tail / Vertical Tail / Aileron / Flap / Tab — the six
  `case_ids.py` structural-component prefixes, control surfaces folded into
  their host per the D-1 taxonomy) reading `Project.loads.wing_net` /
  `body_net` / `tail_chordwise` / `control_surface`; a case-ID multiselect per
  component; one overlay figure per load quantity (thin trace per selected
  case + a dotted max-|value| envelope trace); a "Total loads" section
  combining one wing case + one fuselage case into a single two-subplot figure
  (shear on the primary axis, moments on a secondary axis); and a CSV importer
  that reuses `farloads.export.sbeam_bridge.span_load_csv` /
  `body_span_load_csv`'s exact column schema, auto-detects wing vs. fuselage
  shape by column-subset match, and overlays the imported curve (dashed)
  against a computed one. Writes nothing back to `Project` — no `st.form`/
  Apply (page convention #1 doesn't apply to a pure viewer).
- `farloads/workflow.py`: one new `WorkflowStep("loads_plots", "Loads Plots",
  LOADS_PLOTS, module=None, produces=None, ...)`, mirroring the other
  GUI-only consolidation steps (`dashboard`, `results_review`,
  `export_report`). This is the only step in the `LOADS_PLOTS` phase, so
  `Home.py`'s existing "hide empty section" guard now shows "5 · Loads Plots"
  in the sidebar with no `Home.py` change needed.
- **Graphics audit (item 3): no gaps found.** Every plot an original program
  rendered already has a Streamlit equivalent: weight/CG envelope
  (`weight_envelope.py`), V-n diagram (`flight_envelope.py`), spanwise shear/
  bending/torsion (`wing_loads.py`, `fuselage_loads.py`), Mach-limited speed
  boundary (`mach_limit.py`), and the three-view (`configuration_layout.py`).
  Engine Mount and Landing Gear are scalar reaction-load components with no
  spanwise distribution to plot — the original suite never rendered a chart
  for them either, so they are intentionally **not** in the Loads Plots
  component picker (a locked design decision, see Key decisions).

**Test / Acceptance.**
- `tests/test_workflow.py` (the registered-module ↔ workflow-step guard) —
  passes unchanged; `module=None` steps are already tolerated (three prior
  precedents).
- Full suite (`pytest -q`): 283 passed, no calc module touched.
- Manual verification via `streamlit.testing.v1.AppTest` on
  `app/views/loads_plots.py`: (1) an empty project shows the "visit an
  Analysis page first" message with no exception; (2) `examples/ga6_normal
  .project.json` run through `net_loads`/`taildist`/`aileron`/`flap`/`tab`
  renders the wing-component overlay (3 quantity charts, no exception); (3)
  `span_load_csv(project.loads.wing_net)`'s column set round-trips through the
  page's wing/fuselage schema-detection logic correctly, including the
  case where a wing CSV's columns are also a superset of the body schema (the
  wing check is ordered first, so it always wins when both match).

**Key decisions** (resolved with the user before implementation).
- **Component-picker scope.** Distributed components only (wing, fuselage,
  htail, vtail, aileron, flap, tab) — Engine Mount / Landing Gear stay off the
  picker; they're scalar and have no curve to overlay, and the original suite
  didn't plot them either.
- **Envelope definition.** Max |value| per station across the selected case
  IDs (the classic structural-design envelope), not SELECT's governing-set
  filter — the user picks the cases to overlay freely.
- **Total-loads view.** A combined wing+fuselage figure (one case each), not
  just a metrics table — gives a whole-airframe-at-a-glance read.
- **Import schema.** Reuses the existing `sbeam_bridge` span-load export
  schema exactly rather than inventing a new generic station/value mapping —
  a user can export, optionally round-trip through sbeam, and re-import to
  compare on the same axes with zero new format to document. (The more
  generic station/value CSV mapping remains a possible future extension, not
  needed for this step.)

---

## Phase D — Step D6: Merge Analysis into nine component pages (complete, 2026-07-09)

**Objective.** Reorganize the 11 per-BAS-program Analysis pages into the target
nine component pages (decision D-2), and apply the Phase-D page conventions
(`02_gui_workflow_plan.md` §5 — form+Apply, merge-writes, read-don't-re-ask, no
airplane-shaped defaults, LIMIT-marked analysis views) to every one of them.
Design decisions locked 2026-07-09 (`02_gui_workflow_plan.md` §3 D-7). No
calc-math change throughout — Appendix A/B oracles pass unmodified;
`SCHEMA_VERSION` stays at 19 (pure GUI reorg, no new project fields).

**Deliverables.**
- **Wing Loads** (`app/views/wing_loads.py`, new) merges `airloads.py` +
  `net_wing_loads.py`: one `st.form` + Apply for the Schrenk aero inputs and the
  WINGINER/NETLOADS mass distribution. Fixes the `Project.aero.surfaces`
  wholesale-replace on Apply (upsert-by-name instead, so a future non-wing aero
  surface would survive this page); scrubs the Appendix-A-shaped widget
  defaults (section-slope/taper/TAU/target-CL/panel-weight/density-ratio/rib/
  waterline/dihedral/case-row literals); adds the missing LIMIT caption/column
  markers to the net-load output.
- **Tail Loads** (`app/views/tail_loads.py`, new) merges `tail_distribution.py`
  + `balanced_tail_verification.py` behind one `st.form` + Apply for the
  chordwise geometry; the balancing-load cross-check keeps its existing
  correct LIMIT caption.
- The other 7 pages (Engine Out, Fuselage Loads, Aileron, Flap, Tab, Engine
  Mount, Landing Gear) converted 1:1 to the conventions: every page's inputs
  moved into `st.form` + Apply; Fuselage Loads' hardcoded 5-row station table
  and Engine Mount's baked-in Continental IO-520-BB `default_engine()` (weight/
  CG/RPM/HP/rotor literals) replaced with blank defaults; Aileron/Fuselage/
  Landing Gear/Engine Mount gained the LIMIT caption+marker they were missing
  (Flap/Tab/Engine Out already had it); Landing Gear's max-landing-weight/
  gross-weight/wing-area inputs got read-only-derivation help text pointing at
  `Project.mass`/`Project.geometry` (max landing weight stays a page-only
  input — FAR 23.473(b)/(c) is an engineering judgment call, not derivable).
- **Engine Mount normalization** (decision D-7): retired the page's separate
  `st.session_state["engine_inputs"]` store and the ad hoc local `Project(...)`
  built only for compute/export. The page now reads/writes
  `Project.engines`/`Project.engine_layout`/`Project.include_far25` directly
  via `st.session_state["project"]`, matching every other page; an unapplied
  per-engine edit is discarded on engine/unit switch (Phase-D convention, not a
  regression — the old separate store's job was working around exactly this).
  A partially-filled multi-engine layout (a newly-added, still-blank engine)
  now surfaces as a caught, friendly warning on the export bundle instead of
  crashing the page.
- `farloads/workflow.py`: the 11 Analysis steps collapsed to 9. `wing_loads`
  (`module="net_loads"`) and `tail_loads` (`module="taildist"`) are each the
  shared nav step for two independently-registered calc modules; `"airloads"`
  and `"balloads"` were added to `FOLDED_MODULES` (decision D-7, reusing the
  existing `wing_inertia` precedent rather than adding a `modules` tuple to
  `WorkflowStep`). `dashboard.py` and `Home.py` needed no code change — both
  already derive their content purely from `wf.STEPS`/`wf.by_phase()`.

**Key decisions (D-7, locked 2026-07-09).**
- Merged-page nav steps reuse the `FOLDED_MODULES` precedent rather than adding
  a `modules: Tuple[str, ...]` field to `WorkflowStep` — zero dataclass/test-
  shape churn, consistent with the existing `wing_inertia` fold.
- Engine Mount's state-management is normalized onto the standard
  `st.session_state["project"]` pattern in this same step, rather than deferred
  — D6 is exactly the step meant to retire this kind of one-off pattern, and
  the other convention fixes there are small by comparison.

**Test/Acceptance.** Full suite: 282 tests pass, `ruff check farloads/ cli.py
app/` clean. `tests/test_workflow.py` updated for the `wing_loads` key (drops
the `"aero"` requirement, now internal to the merged page).
`tests/test_views_smoke.py` globs `app/views/*.py` so it picked up the 2 new
files and dropped the 4 retired ones with no test-code change (24 view/entry
smoke tests still pass). Every changed page verified with a
`streamlit.testing.v1.AppTest` script against `examples/ga6_normal.project.json`
— ran each form's Apply and inspected the resulting `Project` mutation
(including a multi-engine Engine Mount round-trip: layout switch to Twin,
edit + Apply both engines, confirm `Project.name` is untouched and both
engines' data matches what was typed).

---

## Phase D — Step D5: Envelopes & Critical Conditions section (complete, 2026-07-09)

**Objective.** Give the Envelopes & Critical Conditions section a shared
weight/CG input (so the CG envelope and the flight-envelope balance cannot
diverge), a combined speed–altitude chart, real multi-altitude V-n, and a
persisted critical-case selection Review/Export can reuse. Design decisions
locked 2026-07-09 (`02_gui_workflow_plan.md` §3 D-6). No calc-math change
throughout — Appendix A/B oracles pass unmodified.

**Deliverables.**
- **D5.1 — Weight/CG Grid & Payload Cases page.** New `WeightInput.cg_cases`
  field (`SCHEMA_VERSION` 18 → 19) holding named `CgCase` loading scenarios,
  owned by the new GUI-only `payload_cases` workflow step
  (`app/views/payload_cases.py`). `FlightLoadsInput.cg_cases` — the field
  SELECT/WINGINER/NETLOADS/BALLOADS all read directly — is **not removed**
  (unlike the D4.1 `aero_coeffs` precedent, cg_cases has too many calc
  consumers to safely relocate); instead the Flight Envelope page reads
  `weight.cg_cases` read-only and merges it into `FlightLoadsInput.cg_cases` on
  every Apply, so there is exactly one place an engineer edits the numbers.
  `weight_envelope.py`'s chart (new: `loading_envelope_points()` exposes the
  forward-boundary vertices `envelope()` already computed) overlays the same
  cases as read-only markers. Old project files migrate via
  `io._legacy_cg_cases_from_flight_loads` (copies `flight_loads.cg_cases` into
  `weight.cg_cases` on load; the calc-facing field is unaffected either way).
- **D5.2 — Speed–altitude chart.** `app/views/mach_limit.py`'s EAS-vs-altitude
  chart converted from `st.line_chart` to `plotly`, with VA/VC/VD/VF
  (`structural_speeds.design_speed_values`) added as horizontal reference
  lines over the existing V(MC)/V(MNE)/V(MD)/V(FC) boundary — display only, no
  calc change.
- **D5.3 — Multi-altitude V-n.** `FlightLoadsInput.altitudes_ft` exposed as a
  real, fully-editable list on the Flight Envelope page (previously a single
  `number_input` that only ever touched `altitudes_ft[0]`); `merged()`'s
  `altitude_ft: float` param replaced with `altitudes_ft: List[float]`. The
  V-n chart gained a CG-case selector, an altitude selector, and an "overlay
  all altitudes" checkbox. `build_envelope`'s `for alt in fl.altitudes_ft`
  loop already supported this since Step C2 — confirmed by regression test
  (`test_multi_altitude_vn_regression`), no equation change.
- **D5.4 — Critical-case selection.** `CriticalLoadSet.selected_case_ids`
  (additive, empty = unfiltered) + `.selected()` helper. The Critical Loads
  page adds a per-condition checkbox (default checked); Results Review reads
  `.selected()` instead of `.conditions` for its governing-loads summary.
  Deliberately scoped to that one GUI page — WINGINER/NETLOADS, `body_loads`
  and the sbeam export bridge all keep reading `.conditions` unfiltered, so a
  deselected condition can never silently drop out of a structural
  deliverable (D8.3 is expected to wire the export bundle to this same
  selection later).

**Test/Acceptance.** `SCHEMA_VERSION` 19 round-trip + legacy-migration tests
(`tests/test_io.py`: `test_weight_cg_cases_round_trips_through_io`,
`test_legacy_flight_loads_cg_cases_migrate_to_weight`,
`test_critical_load_set_selected_case_ids_round_trip`); multi-altitude
regression (`tests/test_flight_envelope.py::test_multi_altitude_vn_regression`);
`merged()` signature test rewritten
(`test_merged_replaces_altitudes_and_cg_cases`); `CriticalLoadSet.selected()`
unit tests (`tests/test_select.py`). No automated UI test suite exists, so
every page change (`payload_cases`, `weight_envelope`, `flight_envelope`,
`mach_limit`, `critical_loads`, `results_review`) was verified with a
`streamlit.testing.v1.AppTest` script against `examples/ga6_normal.project.json`
— no exception, expected `Project` slice mutations. Full suite: 284 tests
pass, `ruff check farloads/ cli.py` clean.

**Key decisions** (locked 2026-07-09, `02_gui_workflow_plan.md` §3 D-6): manual
weight/CG rows over item-toggle scenario derivation; `WeightInput.cg_cases` as
the schema home with `FlightLoadsInput.cg_cases` kept as the untouched
calc-facing field; the speed–altitude chart extends Mach Limit rather than a
new page; critical-case selection is opt-out (default = everything), display-
only, never a structural-calc input.

---

## Phase D — Step D4: Authoritative shared inputs + Aero Coefficients page (complete, 2026-07-09)

**Objective.** Kill duplicate wing-area/MAC/weight/CG entry across the
Airplane-section pages, remove Appendix-A-shaped widget defaults from those
pages, seed component stations into the Weight DB, compute the true CG from
`Project.mass`, wire up engine three-view write-back, and apply the Phase-D
page conventions (`02_gui_workflow_plan.md §5` — `st.form`+Apply, merge-writes,
read-don't-re-ask, no airplane-shaped defaults) across the section. Design
decisions locked 2026-07-09 (`02_gui_workflow_plan.md` §3 D-5). No calc-math
change throughout — Appendix A/B oracles pass unmodified at every sub-step.

**Deliverables (D4.1–D4.7).**
- **D4.1 — `Project.aero_coeffs` slice.** New `AeroCoefficientsInput`
  (`cruise`/`flaps_down` `AeroCoeffSet`s) replaces `FlightLoadsInput.
  configurations`; `SCHEMA_VERSION` 17 → 18 with a legacy-file migration
  (`io._legacy_aero_coeffs_from_flight_loads`); new `aero_coefficients`
  workflow step; `select`/`balloads` read the new slice via
  `select._flaps_by_config_name`.
- **D4.2 — Aero Coefficients page.** `app/views/aero_coefficients.py` owns the
  whole slice as a single `st.form`+Apply (cruise + optional flaps-down
  coefficient tables, 0/blank defaults); `flight_envelope.py` dropped its
  interim cruise-coefficient editor for a read-only caption + a
  no-aero-coefficients guard.
- **D4.3 — Station derivation + Weight DB seeding.** `configuration.
  component_stations(layout) -> Dict[str, Vec3]` and `match_component_station`
  (alias substring matching, most-specific first) derive approximate component
  stations from `LayoutInput`'s existing scalars, no new schema; a
  "Seed component stations into Weight DB" button on `configuration_layout.py`
  fills only zero-station `MassItem`s, never overwriting a hand-entered one.
- **D4.4 — `XLEMAC`/`MAC`/weight read-through.** `structural_speeds.py` and
  `weight_envelope.py` read the Weight DB total
  (`project.weight.direct_totals()[0]`) read-only with an explicit "Override"
  checkbox, replacing hardcoded `3400.0`/`184.125`-shaped fallbacks with
  0/info-message defaults when no Weight DB exists.
- **D4.5 — True CG from `Project.mass`.** `configuration.cg_estimate(project,
  layout, geom) -> (x_cg, z_cg, source)` returns the weight-averaged station
  from `Project.mass.cases[0]` when present, else the prior 25%-MAC/wing-
  waterline first cut; the gear tip-back/overturn condition and the three-view
  CG marker both switch to it automatically, with the source named in the
  label/legend.
- **D4.6 — Engine write-back + mass-item overlay.** The three-view overlays a
  marker per `Project.weight.items` `MassItem` (colored by `MassItemKind`,
  sized by weight) and a diamond per `Project.engines[]` at its `engine_cg`; a
  new "Engine positions" expander offers numeric X/Y/Z overrides (not
  drag-and-drop) that write back into `Project.engines[i].engine_cg` and
  re-render via `st.rerun()`.
- **D4.7 — Form+Apply conversion.** `configuration_layout.py`, `wing_geometry.
  py`, `weight_estimate.py`, `weight_cg_inertia.py` and `structural_speeds.py`
  converted to `st.form`+explicit-Apply (matching `aero_coefficients.py` from
  D4.2); every remaining Appendix-A-shaped literal default (GA6 wing/fuselage/
  tail/gear geometry, WTESTIMA mission figures, STRSPEED VH/VS/VSF/altitude/
  VC/VD/load-factor figures, the WINGGEOM Appendix-A wing polyline) replaced
  with 0/blank/derived defaults; conditionally-hidden form fields (override
  checkboxes, the Concept-category load-factor inputs) changed to always-
  rendered-but-conditionally-applied, since `st.form` fields don't react live
  to a sibling widget's value. While verifying the D4 regression check below,
  found and fixed a **merge-write defect** predating D4.7: `configuration_
  layout.py`'s station-seed button, and both `project.weight` writes in
  `weight_estimate.py` and `weight_cg_inertia.py`, constructed a fresh
  `WeightInput(estimation=..., items=...)` without carrying forward
  `envelope`, silently dropping the Weight Envelope page's inputs on the next
  write from any of those three pages — now all three pass `envelope=project.
  weight.envelope` through.

**Test/Acceptance.** `aero_coefficients` step registered and the nav-drift
test (`tests/test_workflow.py`) green; `SCHEMA_VERSION` bump with an
old-project-file load test (`tests/test_flight_envelope.py`); `tests/
test_configuration.py` gained 8 direct-function tests across D4.3/D4.5
(`component_stations`, `match_component_station`, `cg_estimate`); no automated
UI test suite exists, so every page change was verified with a
`streamlit.testing.v1.AppTest` script (blank project, populated project, and —
where relevant — clicking Apply/seed buttons), each confirming no exception
and the expected `Project` slice mutation. D4's regression DoD item — loading
`examples/ga6_normal.project.json`, running the D4.3 seed logic, and comparing
`design_speeds`/`weight_envelope.envelope` output before vs. after — confirmed
bit-identical (the example's 24 items already carry real stations, so the seed
is a no-op there; the check also caught the merge-write defect above, since
the pre-fix seed silently cleared `weight.envelope` and made the "after" run
raise instead of matching). Full suite: 277 tests pass throughout D4.1–D4.7,
`ruff check farloads/ cli.py` clean at every sub-step.

**Key decisions** (locked 2026-07-09, `02_gui_workflow_plan.md` §3 D-5): the
default-scrub scope is the five Airplane-section pages + Aero Coefficients
only (`flight_envelope`/`weight_envelope`/`mach_limit`/`airloads` keep their
literals until their own D5/D6 rework); aero coefficients get a dedicated
owned slice rather than nesting in `FlightLoadsInput`; component stations are
derived from `LayoutInput`'s existing scalars rather than a new per-component
sub-model; engine three-view write-back is numeric-override, not
drag-and-drop, and landed in D4 rather than deferred.

---

## Phase D — Step D3: Start (landing) page & local-disk persistence (complete, 2026-07-09)

**Objective.** Decision D-3: give the locally-run app real project persistence —
Open/Save against a local `projects/` directory (recent list, New-from-example),
a global sidebar file widget on every page, and optional `engineer`/`date`
project metadata carried in the JSON and shown in exports. No autosave; no calc
change.

**Deliverables.**
- `farloads/models.py`: `Project.engineer: str = ""`, `Project.date: str = ""`
  (freeform text, additive). `SCHEMA_VERSION` 16 → 17.
- `farloads/io.py`: `project_from_dict`/`project_to_dict` round-trip
  `engineer`/`date` (omitted from the dict when blank, so old files are
  byte-identical on save). New `default_projects_dir()` (resolved from
  `io.py`'s own file location — repo root / `projects` — not the process cwd,
  so it's stable regardless of where `streamlit run app/Home.py` is invoked
  from) and `list_saved_projects(directory)` (`*.project.json` files,
  newest-mtime-first, `[]` if the directory doesn't exist yet).
- `app/Home.py`: the project (`st.session_state["project"]`) and the global
  **Project file** sidebar widget now live here, above `pg.run()`, so they
  render on every page regardless of the active view. The widget offers Open
  (a selectbox of `list_saved_projects`), New from example
  (`examples/*.project.json`), Save to disk (writes/overwrites
  `<name>.project.json` into `projects/`, created lazily on first save), the
  existing browser upload/download, and an unsaved-changes caption (diffs the
  live project's dict against a snapshot taken on every load/save).
  Discarding unsaved edits via Open/New-from-example is guarded by an
  `st.dialog` confirmation.
- `app/views/dashboard.py`: dropped its own sidebar uploader/download block
  (superseded by `Home.py`'s); added **Engineer**/**Date** text inputs beside
  the project-name field.
- `app/views/export_report.py`: the combined text report and zip bundle now
  open with a `Project: … / Engineer: … / Date: …` header line (fields omitted
  when blank); fixed a leftover D2 doc-sync miss ("fill in the Define pages
  first" → "Airplane pages").
- `.gitignore`: added `projects/`.

**Test/Acceptance.** New `tests/test_io.py` cases: engineer/date round-trip
through `project_to_dict`/`project_from_dict`, blank-by-default omission from
the serialized dict (old files unaffected), `default_projects_dir()` resolves
repo-relative, `list_saved_projects()` sorts newest-first and returns `[]` for
a missing directory. Full suite: 266 tests pass; `ruff check farloads/ cli.py`
clean. Manual: `scripts/smoke_test.sh` passes; a headless Streamlit run hit
`dashboard`, `export_report`, `configuration_layout` and `results_review` with
no traceback in the server log.

**Key decisions** (resolved 2026-07-09, see the conversation that opened this
step for the options considered):
- **Save overwrite:** silent overwrite of an existing `<name>.project.json` in
  `projects/` — matches the pre-existing browser-download Save behavior; the
  directory listing itself is the snapshot/undo mechanism (each file is a full
  project snapshot; nothing is merged in place).
- **Unsaved-edit guard:** Open and New-from-example both confirm via a
  `st.dialog` before replacing `st.session_state["project"]` if the
  unsaved-changes indicator is active; no guard existed before this step (the
  old browser uploader silently replaced).
- **Date field default:** blank, freeform text — no auto-fill to today's date,
  consistent with page convention §5.4 (no non-project-derived widget
  defaults).

---

## Phase D — Step D2: Six-section navigation restructure (complete, 2026-07-08)

**Objective.** Regroup the GUI navigation from the four generic Define →
Analyze → Review → Export phases into the six Phase-D sections — Start,
Airplane, Envelopes & Critical Conditions, Analysis, Loads Plots, Export — per
`docs/30_future/02_gui_workflow_plan.md §2`. Regroup only: no page merges (those
land in Step D6), no calc-math or schema change.

**Deliverables.**
- `farloads/workflow.py`: `PHASES` replaced with `(START, AIRPLANE, ENVELOPES,
  ANALYSIS, LOADS_PLOTS, EXPORT)`. Every `WorkflowStep.phase` reassigned per the
  target table: **Airplane** = `configuration_layout`, `wing_geometry`,
  `weight_estimate`, `weight_cg_inertia`, `structural_speeds`; **Envelopes &
  Critical Conditions** = `weight_envelope`, `mach_limit`, `flight_envelope`,
  `critical_loads`; **Analysis** = `airloads` (moved from Define),
  `net_wing_loads`, `fuselage_loads`, `tail_distribution`,
  `balanced_tail_verification` (moved from Review), `aileron_loads`,
  `flap_loads`, `tab_loads`, `landing_loads`, `engine_mount`,
  `one_engine_out`; **Loads Plots** = no steps yet (new page lands in Step D7);
  **Export** = `results_review` (moved from Review) and `export_report`.
  `requires`/`produces` on every step are byte-identical to before the move.
- New `dashboard` `WorkflowStep` (`phase=START`, `module=None`,
  `produces=None`), so the dashboard is a first-class step instead of a
  `Home.py` special case.
- `app/Home.py`: dropped the hardcoded `dashboard = st.Page(...)` /
  `{"Overview": [dashboard]}` special case; every sidebar group (including
  Start) is now built uniformly from `wf.by_phase()`, with `default=True` set
  via `step.key == "dashboard"`. Sections with no steps (`Loads Plots`) are
  skipped rather than shown empty.
- `app/views/dashboard.py`: per-section status-board columns now iterate the
  non-empty sections (excluding the dashboard step's own Start entry, to avoid
  self-listing); docstring/caption updated to the six-section language.
- `app/views/results_review.py`: docstring/captions updated ("Review-phase" →
  "Export-section pre-export summary"); no logic change (`step_by_module`
  already filters on `s.module`, so the module-less `dashboard`/
  `results_review`/`export_report` steps were already excluded from its
  module-results rollup).
- Docs synced: `docs/10_standard/00_program_overview.md`,
  `docs/10_standard/PROJECT_GUIDE.md` (nav description + package-layout
  comments); `docs/30_future/02_gui_workflow_plan.md` narrative status.

**Test/Acceptance.** `tests/test_workflow.py` (phase/key validity, the
registered-module ↔ workflow-step nav-drift guard, `produces`-path resolution)
passes unchanged with 6 phases instead of 4. Full suite: 262 tests pass;
`ruff check farloads/ cli.py` clean.

**Key decisions.**
- `results_review` is not named in the `02_gui_workflow_plan.md §2` target
  table (which only lists the future D6-merged Analysis pages). Placed in
  **Export** (alongside `export_report`) as the pre-export consolidated
  summary, rather than Envelopes & Critical Conditions or Start.
- The dashboard becomes a real `WorkflowStep` rather than staying a `Home.py`
  special case, so `wf.by_phase()` is the single uniform builder for all six
  sections including Start.
- `Loads Plots` is omitted from the sidebar entirely while it has zero steps,
  rather than shown as an empty placeholder group, until Step D7 adds its page.

---

## Phase D — Step D1: Structured load-case IDs (complete)

**Objective.** Decision D-1: replace `report.py`'s render-time, per-module,
unstable `LC{idx}` with a stable, traceable `case_id` (`"<component>-<seq>"`)
on every delivered load case, assigned by the **calc** modules, so a loads
release can trace a case from the V-n matrix through SELECT to a component
load case and its sbeam card. No calc-math change — `CaseRef` is an added
field; the Appendix A/B oracles pass unmodified (`SCHEMA_VERSION` 15 → 16,
additive).

**Deliverables.**
- `CaseRef` dataclass (`case_id`, `component`, `condition`, `cg`, `speed_kt`,
  `altitude_ft`, `far_reference`) plus an optional `case_ref` field on
  `ConditionResult`, `VnPoint`, `CriticalCondition`, `WingLoadResult`,
  `BodyLoadResult`, `TailChordResult`, `ControlSurfaceLoadResult`,
  `GearReactionCase` (`farloads/models.py`).
- `farloads/case_ids.py` (new): the six-entry `COMPONENT_PREFIX` map (`wing`→`W`,
  `htail`→`HT`, `vtail`→`VT`, `fuselage`→`F`, `engine_mount`→`EM`,
  `landing_gear`→`LG`) and `CaseIdAllocator`, a per-call-site sequential
  counter with no shared/global state.
- Minting sites, each in its own already-deterministic emission order:
  `select.py` (`build_critical`, one allocator for wing/htail/vtail/fuselage,
  the `CaseRef` also copied back onto the originating `VnPoint`);
  `wing_inertia.py`/`net_loads.py` (`wing_case_ref`, a pure function of
  position in `WingMassInput.cases` so both modules agree without shared
  state); `engine.py` (`EM-`, incl. the 23.371(b) gyro condition's single base
  id whose 4 sign-combination sub-ids are *derived* at render time —
  `report.py`'s `_gyro_subcase_id`, an a/b/c/d suffix, since one
  `ConditionResult` can't carry 4 `CaseRef`s); `landing.py` (`LG-` per
  `GearReactionCase`, the manual's own 1-based case number kept separately for
  oracle traceability); `aileron.py`/`flap.py`/`tab.py` (`W-`/`HT-`/`VT-` from
  their own bands); `one_engine_out.py` (its own `VT-` sequence).
  `taildist.py`/`body_loads.py` **copy** `case_ref` from SELECT's
  `CriticalCondition` rather than re-minting.
- Numeric banding wherever two independent allocators mint into the same
  prefix (not just across modules but *within* `wing`, since `select_wing`'s
  own list and WINGINER/NETLOADS's are genuinely separate — see Key decisions):
  `W-01..39` WINGINER/NETLOADS, `W-40..49` `select_wing`, `W-50..59` AILERON,
  `W-60..69` FLAPLOAD, `W-70+` a wing tab; `HT-50+`/`VT-50+` for TABLOADS'
  htail/vtail-hosted tabs.
- `report.py`: `load_cases_to_rows`/`results_to_rows` emit `ID` from
  `case_ref.case_id` (falling back to `LC{idx}` only when absent) plus
  `Component`/`Condition`/`CG`/`Speed (kt)`/`Altitude (ft)` traceability
  columns.
- `export/sbeam_bridge.py`: the case id is stamped into the `$`-comment header
  of every wing/body/tail/control-surface `FORCE`/`MOMENT` card block; new
  `case_index_rows_from`/`case_index_csv_from` (explicit result groups) and
  `case_index_rows`/`case_index_csv` (from a `Project`'s persisted slices)
  build the ID → full-definition case-index table, deduplicated by
  `case_id`. Wired into the Export page (`app/views/export_report.py`): a new
  "Case index" section + download button, and the CSV included in the `.zip`
  bundle.
- `io.py`: `CaseRef` (de)serialization for the persisted result slices
  (`EnvelopeResult.vn`/`.critical`, `LoadsResult.*`); `ConditionResult`/
  `GearReactionCase` are transient (never written to `project.json`), so they
  need none.
- `tests/test_case_ids.py`: ids present across all four bundled example
  projects; the real uniqueness invariant (a `case_id` may legitimately repeat
  across pipeline stages for the *same* case, but never means two different
  conditions); stability across two identical runs; the wing-gap bands
  verified disjoint; `CaseIdAllocator` is a pure per-call counter. Full
  existing suite (262 tests) passes unmodified, confirming no oracle drift.

**Test / Acceptance.** `pytest` (262 passed, incl. the 5 new D1 tests);
`ruff check farloads/ cli.py app/views/export_report.py` clean. Manual smoke
run against all four `examples/*.project.json`: every project emits at least
one `case_ref`, and — after the banding fix below — zero id collisions
(no `case_id` maps to two different `condition` labels) across 51-53 cases
per project.

**Key decisions.**
- `CaseRef` is a standalone dataclass (not inline fields on eight result
  types), assigned once by the module that first names a physical condition
  and copied downstream, with exactly six component prefixes (control
  surfaces fold into their host — no `AIL`/`FLP`/`TAB` prefix) and stability
  from each module's own fixed emission order rather than a persisted
  registry — all locked 2026-07-08 (see `docs/30_future/
  02_gui_workflow_plan.md` D-1).
- **Banding bug caught and fixed during implementation.** The original plan
  text claimed `select_wing`'s own `W-` sequence and WINGINER/NETLOADS's could
  safely share the `W-01..49` numeric range "so no collision" — a smoke run
  immediately disproved this (`select_wing`'s `W-02` = PLAA, WINGINER's
  `W-02` = TORS, same id, two different cases): two independent counters over
  the same range collide by construction. Fixed by splitting the range
  (`select_wing` → its own `W-40..49` sub-band) and adding
  `test_wing_gap_is_banded_not_colliding` to lock it. This is a narrower
  problem than the accepted "two independent case lists" gap below — banding
  fixes the collision; it does not unify the lists.
- **Accepted, not closed:** `select_wing`'s wing `CriticalCondition` list and
  `WingMassInput.cases` (which actually drives WINGINER/NETLOADS) remain two
  independent, unlinked case lists — same for `one_engine_out` vs.
  `select_vtail`. Banding prevents an id collision between them but they are
  still not the same case object. Tracked as a deferred refinement ("Unify
  `select_wing`/`one_engine_out` case identity...") — needs its own oracle
  re-check since closing it changes which case list WINGINER/NETLOADS iterate.
- Transient results (`ConditionResult`, `GearReactionCase`) get no `io.py`
  round-trip since they're never persisted on `Project` — only `case_ref` on
  the persisted result slices needs (de)serialization.

---

## Release 0.2.0 — Step R2: GUI / CLI smoke test (complete)

**Objective.** Close `RELEASE_PROCESS.md` §3.5 as a permanent, repeatable
check instead of a manual checklist pass, so every future release runs the
same script.

**Deliverables.** `scripts/smoke_test.sh`: starts `app/Home.py` headless on a
fixed local port, polls Streamlit's `/_stcore/health` endpoint until it comes
up, curls the root page (asserts HTTP 200) and scans the server log for a
traceback, stops the server, then runs `farloads engine
examples/ga6_normal.project.json -o out.csv` and asserts the CSV is non-empty
with an `ID` header and at least one load-case row. `RELEASE_PROCESS.md` §3.5
now points at the script instead of prose steps. No `SCHEMA_VERSION` bump, no
calc change — tooling-only.

**Test / Acceptance.** `scripts/smoke_test.sh` run against a clean `.venv`
checkout: exits 0, root page 200 with no traceback, CLI wrote 3 load-case rows
for the `engine` module against `ga6_normal.project.json`.

**Key decisions.** Committed as a standalone bash script rather than a pytest
case in the main suite — the headless-server subprocess is slow and
port/timing-sensitive, so it stays out of the default `pytest` gate rather
than risk flaking CI; not wired into CI in this step. Uses
`examples/ga6_normal.project.json` only (matches the CLI bullet the release
process already named). "Renders without error" is checked by process +
HTTP 200 + log scan, not a manual browser pass.

---

## Release 0.2.0 — Step R3: docs-drift check (complete)

**Objective.** `RELEASE_PROCESS.md` §3.1 — confirm `PROGRAM_SPEC.md`,
`PROJECT_GUIDE.md` and `20_theory/00_theory_sources.md` match the released
code (verification pass, not a writing pass).

**Deliverables.** Reviewed all three docs against `farloads/modules/__init__.py`
(the registered-module list), `models.py` (`Project` slices, `SCHEMA_VERSION`),
`registry.py`/`workflow.py`, and recent `CHANGELOG.md`/history entries.
`PROJECT_GUIDE.md` and `20_theory/00_theory_sources.md` matched the code with
no changes needed. `PROGRAM_SPEC.md` had one gap: `body_loads.py` (registered,
shipped in Step C6) was documented only as a subordinate mention inside
SELECT's write-up, with no `### body_loads` entry of its own (unlike
`configuration`, its sibling "modern addition"), and the cross-module
field-ownership table omitted the `fuselage_mass` slice it reads. Fixed by
adding a full `### body_loads — Fuselage net-load distribution (Step C6)`
entry (FAR §/Source/Reads/Writes/Validation/Notes, matching the template) and
a `fuselage_mass | direct input | body_loads` row to the ownership table.

**Test / Acceptance.** Cross-checked the new entry's Reads/Writes claims
directly against `farloads/modules/body_loads.py` (it calls
`select.select_fuselage(project)` rather than reading a persisted
`Project.envelope.critical` slice, and reads `Project.tail_loads`/
`Project.fuselage_mass`) and `models.py`'s `FuselageMassInput`/`FuselageStation`
dataclasses before writing the doc text, so the fix itself doesn't introduce
new drift.

**Key decisions.** No code/schema change — docs-only. Did not flag anything
already tracked as an open item in `docs/30_future/00_backlog.md` (known-open
≠ drift).

---

## Release 0.2.0 — Step R4: archive verification baseline (complete)

**Objective.** `RELEASE_PROCESS.md` §4.4 — create a permanent regression-
baseline artifact recording every printed Appendix A/B figure the test suite
locks against, since none existed yet.

**Deliverables.** `docs/40_history/01_verification_baseline_0.2.0.md`: one
table per module — condition, printed figure, reference-page citation,
tolerance — for all 22 ported Appendix-C programs plus the two modern
modules (`configuration`, `body_loads`), extracted directly from the current
`tests/test_*.py` assertions (fanned out across four parallel read-only
sweeps of the test files, one per pipeline stage: mass/geometry/speeds;
envelope/critical; wing/tail component loads; control-surface/engine/gear/
body). Modules with no printed oracle — ONENGOUT, the LANDLOAD wheel-load
table past the legible p231 spot-check cells, AIRLOAD4's swept branch, the
FAR 25 optional engine cases, `body_loads`, `configuration`, and concept-mode
AIRLOADS/NETLOADS — are recorded in a dedicated "Closure-locked modules"
section with the specific closure or sub-formula check each relies on,
instead of an invented printed figure. Also captures the WTENV aft-gross-
ballast-station approved deviation and the AC 23-19A engine-torque
corrections (ENGLOADS), calling out the manual's raw pre-correction figure
alongside the corrected value the code asserts.

**Test / Acceptance.** Every row traces to a currently-passing assertion; the
document states the run it was extracted against (`pytest`: 257 passed, 0
failed, coverage ~92%, `ruff check farloads/ cli.py` clean) rather than
re-deriving numbers by hand. No code/schema change — docs-only.

**Key decisions.** Presented as "what the suite locks against" (printed
figure + tolerance + citation) rather than a duplicate "computed" column,
since a passing `math.isclose` assertion already proves computed == printed
within tolerance; re-stating the computed number would just be the same
literal copied twice.

---

## Release 0.2.0 — Step R5: version bump + changelog dating (complete)

**Objective.** `RELEASE_PROCESS.md` §4.1–4.2 — bump the package version and
date the changelog so the release is cuttable.

**Deliverables.** `pyproject.toml` `version` `0.1.0` → `0.2.0` (MINOR: new
modules ported and new GUI/CLI capability since `0.1.0`, per §1's version-
numbering table). `CHANGELOG.md` `[Unreleased]` renamed to
`## [0.2.0] — 2026-07-08`, with a fresh empty `[Unreleased]` opened above it.
No code/schema change.

**Test / Acceptance.** `pytest` and `ruff check farloads/ cli.py` unaffected
(metadata-only change); `grep version pyproject.toml` shows `0.2.0`.

**Key decisions.** None — mechanical application of §4.1–4.2's two steps.

---

## Release 0.2.0 — Step R6: tag & GitHub release (complete)

**Objective.** `RELEASE_PROCESS.md` §4.3 — tag the version-bump commit and
publish the GitHub Release.

**Deliverables.** Annotated tag `v0.2.0` (`git tag -a v0.2.0 -m "Release
v0.2.0"`) on `50e2c9c` ("Version bump and change log", the commit where
`pyproject.toml` reads `0.2.0`), pushed to `origin`. GitHub Release `v0.2.0`
published from that tag with the `CHANGELOG.md` `[0.2.0]` section as the
release body. No code/schema change; user-run per `CLAUDE.md` (all git/GitHub
actions are the user's to execute).

**Test / Acceptance.** `git ls-remote --tags origin` shows `v0.2.0` resolving
to `50e2c9c`; GitHub Release page confirmed published.

**Key decisions.** A `v0.2.0` tag already existed pointing at `a182006`
("Archive verification baseline", release step R4) — one commit *before* the
version bump, where `pyproject.toml` still read `0.1.0`. Deleted that tag
locally and on `origin` and recreated it at `50e2c9c` so the released tag
matches the versioned commit, rather than leaving the release one commit
short of its own version bump.

---

## Release 0.2.0 — Step R7: post-release (complete)

**Objective.** `RELEASE_PROCESS.md` §5 — close out the release-priority work
in the backlog now that `0.2.0` has shipped, and hand off to the next active
step.

**Deliverables.** Removed the "Release 0.2.0 — priority work" section (steps
R1–R7) from `docs/30_future/00_backlog.md` in full — all seven steps closed,
nothing open remains for the release. Updated the Phase D intro in the same
file: the release gate is recorded as met (tag `v0.2.0` on `50e2c9c`, GitHub
Release published, 2026-07-08) and **Step D1 (structured load-case IDs)** is
marked the active step.

**Test / Acceptance.** N/A — docs-only backlog/history bookkeeping; no
code/schema change.

**Key decisions.** No new defects surfaced during final release testing, so
§5's "add any new defects found" bullet is a no-op this release.

---

## ULTIMATE load output with a per-case factor of safety (complete)

**Objective.** The suite emitted LIMIT loads everywhere, so downstream structural
sizing (the sbeam FORCE/MOMENT export and the load-case CSV) consumed limit loads
where it needed ULTIMATE, producing spurious sizing failures. Report ultimate =
limit × factor of safety and state the factor, keeping the factor **per-case** (14
CFR 25.302 / Appendix K make it failure-probability-dependent).

**Deliverables.**
- `constants.ULTIMATE_FACTOR = 1.5` (14 CFR 25.303) and a per-case
  `ConditionResult.safety_factor` (default 1.5).
- `report.py`: a unit-gated `_is_load_unit` classifier scales only force/moment/
  pressure quantities; `load_cases_to_rows` (new `SF` column, `ULT`-marked headers),
  `results_to_rows`, `text_report` and `module_text_report` now report ultimate.
- `export/sbeam_bridge.py`: wing/body/tail/control-surface FORCE/MOMENT cards,
  span-load CSVs and closure comments scaled to ultimate (`_SF`).
- `reference/14CFR_factor_of_safety.md` documenting the FS basis.
- Docs synced: `PROGRAM_SPEC.md`, `PROJECT_GUIDE.md §5`, `theory_sources.md`,
  `01_concept_loads_plan.md` (C4), `CHANGELOG.md`.

**Test / Acceptance.** Calc oracle tests unchanged (assert on the calc's LIMIT
`run()` results). Render/export tests updated to ultimate: `test_report.py` adds
ultimate-value + `SF`-column + locations-unscaled asserts; `test_io.py` checks the
`SF`/`ULT` header; `test_sbeam_bridge.py` closure now sums to 1.5 × root/total. Full
suite green (254 passing); `ruff` clean.

**Key decisions.** (1) Apply the factor at the **render/export boundary only** — the
calc stays oracle-locked, so Appendix A/B regressions are unaffected. (2) Factor is
**per-case** (the hook for a future 25.302/Appendix K probability curve), but every
case is **1.5** today, including **sudden engine stoppage** (held conservative; the
1.0 relief floor is reserved for failures substantiated at ≤1e-9/flt-hr). (3) Scaling
is **unit-gated** so weights/inertias/geometry/load-factors are never scaled, which
makes "all rendered output → ultimate" safe for the mass-properties modules that share
the renderers.

---

## Reduced the FAR 25 supplement to the non-duplicative cases (complete)

**Objective.** After the AC 23-19A correction factored the FAR 23 takeoff case, the
FAR 25 torque cases became near-identical to the FAR 23 set for a turbopropeller. Trim
the opt-in superset to only what is genuinely additive, removing the duplication that
was doubling the load-case CSV with equal numbers.

**Deliverables.**
- `farloads/modules/engine.py`: removed `condition_25_361_a1i/_a1ii/_a1iii` — for a
  turbopropeller they are bit-for-bit equal to the corrected
  23.361(a)(1)/(a)(2)/(a)(3). `run_far25` now returns only the three additive cases:
  `condition_25_361_a3i` (stoppage + 1g vertical), `condition_25_361_a3ii` (max engine
  acceleration torque — no FAR 23 analog), `condition_25_371` (gyro on the A2 vertical).
- The additive cases stay **behind `Project.include_far25`** rather than being folded
  into the FAR 23 path: making them unconditional would change the Appendix B turboprop
  case count (6) and gyro vertical (2.5g), breaking oracle-lock. `Project.include_far25`,
  `EngineInput.max_accel_torque`, and the JSON/units plumbing are unchanged.
- GUI checkbox relabelled "Add **supplemental** FAR 25 cases" with help text explaining
  the duplicates were dropped (`app/views/engine_mount.py`).
- Docs synced: PROGRAM_SPEC § ENGLOADS, PROJECT_GUIDE §3.4.4, theory sources, CHANGELOG.

**Test / Acceptance.** `tests/test_engine_far25.py` updated: the duplicate-case tests
were removed and replaced by `test_far25_supplement_drops_duplicate_torque_cases`
(asserts `run_far25` = `[25.361(a)(3)(i), 25.361(a)(3)(ii), 25.371]`); the turboprop
opt-in count is now 6 + 3 = 9 (was 12). Full suite green (`ruff` clean, `pytest` 252
passing).

**Key decisions.** Chose *partial* removal over deleting the whole FAR 25 block — the
max-engine-acceleration-torque case (25.361(a)(3)(ii)) has no FAR 23 equivalent and can
govern, and the stoppage-with-1g / A2-gyro cases add marginal conservatism. Kept the
opt-in gate (not unconditional) to preserve the oracle lock.

---

## Correction — FAR 23.361(a)(1) takeoff-torque factor (AC 23-19A) (complete)

**Objective.** Correct a non-conservative error inherited from the original
ENGLOADS.BAS / McMaster manual: the 23.361(a)(1) takeoff-case engine torque was left
**unfactored**, encoding the **Amendment 23-26** drafting error that **AC 23-19A**
identifies (it "failed to require the multiplying factor," yielding lower loads) and
that **Amendment 23-45** corrected — 23.361(c) applies the mean-torque factor to all
of paragraph (a).

**Deliverables.**
- `condition_361_a1` now applies `factor × mean takeoff torque` (`torque_factor`,
  i.e. 1.25 turboprop / 1.33·2·3·4 by cylinder), echoes the torque factor + mean
  takeoff torque, and carries an explanatory `note`. IO-520-BB takeoff mount torque
  554.39 → **737.34 ft-lb**; turbopropeller → 1.25× mean takeoff = identical to
  25.361(a)(1)(i).
- `reference/AC_23-19A_engine_torque.md` — verbatim AC 23-19A policy + corroborating
  2013 CFR text (the citable basis).
- CLAUDE.md gains an **"Approved corrections to the source"** policy (deviations from
  the oracle allowed only when user-approved *and* documented) with this correction
  recorded; PROGRAM_SPEC, theory sources, CHANGELOG updated.

**Test / Acceptance.** `test_361_a1` asserts the corrected −737.34 ft-lb (and retains
554.39 as the "mean takeoff torque" figure for traceability). Full suite green
(`ruff` clean, `pytest` passing).

**Key decisions.** Approved as a documented deviation from the Appendix A oracle (the
manual reproduces a rule the FAA declared defective). The replication charter is
preserved for everything else; the manual's original figure is retained in the test
as the unfactored mean torque so the deviation stays traceable.

---

## Optional FAR 25 engine cases — concept superset (complete)

**Objective.** Let the engine-mount module emit the **14 CFR 25.361 / 25.371**
engine-torque cases as an *additive, opt-in* superset on top of the oracle-locked
FAR 23 set, for the concept-loads direction — without altering FAR 23 output or its
appendix regression.

**Deliverables.**
- `Project.include_far25` (default `False`) + optional `EngineInput.max_accel_torque`
  (ft-lb; blank → `max_engine_torque`); both round-trip through `io.py`, and
  `max_accel_torque` is unit-converted in `units.to_imperial`.
- `farloads/modules/engine.py`: six new turbopropeller-only conditions —
  `condition_25_361_a1i/_a1ii/_a1iii/_a3i/_a3ii` and `condition_25_371` — assembled
  by `run_far25(inp)` and appended by `run_all(inp, include_far25=...)` /
  `run(project)`. The FAR 23 functions are untouched (oracle lock preserved by
  construction). 25.371 reuses the fixed FAR 23.371(b) rates (2.5/1.0 rad/s) as a
  conservative concept stand-in for the maneuver-derived rates the rule references,
  with the vertical load on the A2 limit load factor. *(Superseded — see "Reduced the
  FAR 25 supplement to the non-duplicative cases" above: `_a1i/_a1ii/_a1iii` were
  later removed as duplicates of the corrected FAR 23 set, leaving three cases.)*
- GUI: an **"Add FAR 25 cases"** sidebar checkbox + a FAR-25-only max-accel-torque
  input on `app/views/engine_mount.py`.
- `reference/14CFR_Part25_engine_torque.md` — verbatim 25.361 + 25.371 source text
  (user-supplied from eCFR), the citable basis for the equations.

**Test / Acceptance.** `tests/test_engine_far25.py` (+13) — formula-closure (no
Part-25 oracle exists): FAR 23 unchanged when off; recip/jet emit nothing; the 1.25
factor applied to takeoff (a)(1)(i) = 1.25× the FAR 23 takeoff torque; max-accel
default + override; 25.371 on A2 load factor; `Project.include_far25` JSON round-trip.
Full suite green (`ruff check farloads/ cli.py` clean, `pytest` 255 passing); GUI
`AppTest` shows six FAR 25 expanders on a turboprop with no exception.

**Key decisions.** Turbopropeller scope only — 25.361(a)(2) defines a factor only for
turbopropeller (1.25) and "other turbine engines" (= max accelerating torque), is
silent on recip, and the tool's mass/gyro math is propeller-centric. Conservative
fixed-rate gyro stand-in accepted for initial-concept use (valid while the concept's
real pitch/yaw rates stay ≤ 1 / 2.5 rad/s), flagged in the condition note and the
reference file as an assumption to revisit with real maneuver analysis.

---

## GUI — workflow-phased restructure (complete)

**Objective.** Reorganise the Streamlit UI to mirror the engineering workflow —
**Define → Analyze → Review → Export** — replacing the flat, filename-numbered page
list (which had drifted: a Phase-0 Home page, a duplicate `06_` index, no review or
export surface) with a navigation driven by a single source of truth.

**Deliverables.**
- `farloads/workflow.py` — the ordered, dependency-aware step graph. Each
  `WorkflowStep` names its calc `module` and the slices it `requires`/`produces`,
  grouped into the four phases. Pure metadata + predicates over a `Project` (no
  Streamlit), the seed of a future dependency DAG.
- `app/Home.py` rewritten as the `st.navigation` entry point: a four-phase sidebar
  built from `workflow.py`, so page order/titles come from workflow metadata, not
  filename prefixes. `set_page_config` is called once, here only.
- `app/pages/NN_*.py` → `app/views/<workflow-key>.py` (20 pages, clean names, no
  numeric prefixes — the duplicate-`06` collision is gone); each view's own
  `set_page_config` removed.
- New `app/views/dashboard.py` (Overview: load/save project + per-step completeness
  panel), `results_review.py` (Review: consolidated governing loads, recomputed live
  from inputs), `export_report.py` (Export: project JSON, per-module load CSVs +
  combined text report, sbeam wing/fuselage/tail/control-surface BDF cards, and a
  single **Download all `.zip`** bundle).
- Fixed a pre-existing crash in the engine-mount page (still used the removed
  single-engine `Project(engine=...)` API → `engines=[...]` + `SINGLE_NOSE`).

**Test / Acceptance.** `tests/test_workflow.py` (graph well-formedness; every
registered module has a step) and `tests/test_views_smoke.py` (headless `AppTest`
runs the entry point + all 20 views with the example project, asserting no uncaught
exception — the guard that would have caught the engine-mount regression). Full
suite green (242 tests).

**Key decisions.**
1. **`st.navigation`, not the implicit `pages/` directory** — explicit page list
   decouples nav order/titles from filenames and removes numeric-prefix coupling.
2. **One workflow source of truth** (`workflow.py`) drives both the nav and the
   dashboard completeness, so the GUI can never silently omit a shipped module.
3. **Consolidation pages recompute from inputs**, never from persisted result slices
   (which were only half-wired and could go stale) — Review/Export are always current.
4. **JSON stays the spine, CSV stays at the edges** — `project.json` remains the
   single typed source of truth; CSV/BDF are export-only hand-offs (CSV *import* for
   bulk tabular inputs deferred — see backlog).

---

## Phase 0 — Package restructure (complete)

**Objective.** Recast the standalone `engloads` program into the shared
pure-calc package + thin-shell architecture that every subsequent module will
follow, with the engine-mount module as the proof of pattern.

**Deliverables.**
- `farloads/` pure-calc package: `models.py` (`Project`, `EngineInput`/`Rotor`,
  `ConditionResult`/`LoadValue`, `ModuleResult`, `SCHEMA_VERSION`),
  `modules/engine.py` (port of `ENGLOADS.BAS`), `registry.py`, `io.py`,
  `units.py`, `report.py`, `constants.py`.
- `app/` Streamlit multi-page UI (`Home.py` + `pages/19_Engine_Mount.py`).
- `cli.py` argparse front-end.
- `tests/` suite vs the manual's Appendix A/B figures.

**Test / Acceptance.** Green build — full `pytest` suite passing, engine module
checked against Appendix A (p131) and Appendix B (p251) figures within ±0.1%.

**Key decisions.**
1. **Hybrid architecture** — one shared calc package, interchangeable GUI/CLI/test
   front-ends; calc does no I/O.
2. **Single reloadable `Project`** — one JSON bundle carries every module's input
   slice; `schema_version` from day one.
3. **Modernize the math** — `math.pi` and clean equations, *not* the BASIC's
   `3.1416`. The manual's printed figures become **tolerance-based** regression
   oracles (±0.1%), not exact oracles. Constants centralised in `constants.py` so
   this stays a one-file decision.
4. **Preserved engineering conventions** — engine-mount reaction torque reported
   negative; "clockwise from the pilot's view is positive"; selected intermediate
   quantities truncated to 3 decimals (`int(x*1000)/1000`) to mirror the BASIC.

---

## Phase 1 — Mass properties: WTESTIMA + WTONECG (complete)

**Objective.** Port the head of the mass-properties pipeline: weight estimation
(`WTESTIMA`) and one-loading weight/CG/inertia (`WTONECG`), establishing the
shared `Project.weight` slice the downstream load modules will read. `WTENV` was
**re-scoped to Phase 2** (its structural-CG-limit math needs `XLEMAC`/`MAC` from
`WINGGEOM`); see the backlog.

**Deliverables.**
- `farloads/models.py` — `Project.weight` slice (`WeightInput`) carrying mission
  `estimation` inputs (`WeightEstimationInput`) and the itemized `items` mass list
  (`MassItem`), plus `EngineWeightType` and `MassItemKind` enums.
- `farloads/modules/weight_estimate.py` (`WTESTIMA.BAS`) and
  `farloads/modules/weight_onecg.py` (`WTONECG.BAS`), self-registered as
  `weight_estimate` / `weight_onecg`. Mass-properties constants and the
  installed-engine-weight correlation centralised in `constants.py`.
- `farloads/io.py` — `weight_from_dict`/`weight_to_dict` wired into the project
  JSON round-trip; `load_cases_csv` falls back to the generic property table for
  modules that emit no structural load cases.
- `report.module_text_report` and a generalised `cli.py` text path so non-engine
  modules render to stdout.
- `app/pages/01_Weight_Estimate.py`, `app/pages/02_Weight_CG_Inertia.py` (Imperial
  units; the CG page edits the weight data base in a `st.data_editor`).
- `examples/ga6_normal.project.json` extended with the Appendix A weight slice;
  `tests/test_weight_estimate.py` and `tests/test_weight_onecg.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing with the coverage floor held (≥80%). `WTESTIMA` reproduces
Appendix A p133 exactly (integer-truncated figures); `WTONECG` matches Appendix A
p136 within ±0.1% (weight and lb-in² accumulators are g-independent and exact).

**Key decisions.**
1. **One input slice, pure-calc outputs.** `Project.weight` is the shared input
   "weight database"; modules stay pure (`run → ModuleResult`). No persisted
   `Project.mass` slice yet — it is added when a consumer (FLTLOADS/LANDLOAD)
   exists.
2. **Property table, not load cases.** Mass-properties results render via
   `results_to_rows`/`module_text_report`, not the engine-specific
   `load_cases_to_rows`.
3. **Force vs mass units.** A weight is pounds-*mass* and must convert to kg, but
   a load in `lb` is pounds-*force* and converts to N — the same `"lb"` label.
   `LoadValue` gained an optional `quantity` hint; a weight sets `quantity="mass"`
   so `units.py` routes it to kg, while loads (blank hint) convert by unit string
   to N. Inertia (slug-ft²/lb-in²) → kg·m². The mass-properties pages expose an SI
   output toggle on this basis; inputs stay Imperial.
4. **Preserved BASIC quirks** — `INT(...)` truncation on `WTESTIMA` outputs, and
   the single-engine "misc other system wt = 0" (the program prints an unset
   variable there).

---

## Phase 2 — Geometry: WINGGEOM + first-class multi-engine (complete)

**Objective.** Port aerodynamic-surface geometry (`WINGGEOM`) — the wing's
`MAC`/`XLEMAC` seed `WTENV` and `STRSPEED` — and, alongside it, promote the engine
slice to first-class multi-engine support (resolving PROJECT_GUIDE open decision
#2) so geometry/weight/speeds can reference the engine layout now and `ONENGOUT`
can exercise it fully later.

**Deliverables.**
- **Multi-engine schema** — `EngineLayout` enum (`SINGLE_NOSE`/`TWIN_WING`/
  `QUAD_WING`, symmetric); `Project.engines: List[EngineInput]` + `engine_layout`
  with `__post_init__` count validation and a read-only `Project.engine` compat
  property. `io.py` reads the new `engines`/`engine_layout` JSON or the legacy
  single `engine` key; `modules/engine.py` `run()` loops over every engine
  (single-engine output byte-identical, multi-engine prefixed by designation).
- `farloads/models.py` — `Project.geometry` slice (`GeometryInput` →
  `SurfaceInput` per surface: LE/TE point polylines, `symmetric`, `elements`).
- `farloads/modules/wing_geometry.py` (`WINGGEOM.BAS`), self-registered as
  `wing_geometry`: strip-sum area/MAC/YBAR/XLEMAC/AR/span per surface, plus
  wing-mounted engine spanwise stations driven by `engine_layout`.
- `farloads/io.py` — `geometry_from_dict`/`geometry_to_dict`; `units.py` gained
  area (`in²`→m²) and airspeed (`knot`→m/s) SI output conversions.
- `app/pages/03_Wing_Geometry.py` (per-surface point editors, SI output toggle);
  `examples/ga6_normal.project.json` extended with wing + aileron surfaces and the
  multi-engine layout form; `tests/test_wing_geometry.py` and new multi-engine
  assertions in `tests/test_engine.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). The **wing** reproduces
Appendix A p141 within ±0.1% (AREA/SIDE 13257, MAC 69.246, YLE(MAC) 87.854,
XLE(MAC) 63.641, AR 6.095) at the manual's 20-element strip count; the aileron
exercises the unsymmetric path (checked loosely, since Appendix A does not
tabulate its element count).

**Key decisions.**
1. **Strip count is an input, oracle is H-specific.** The manual's printed figures
   *are* the `H`-element midpoint strip sum, so `elements` must match the manual's
   value (20 for the wing) to reproduce them — kept as a per-surface field.
2. **Multi-engine first-class now.** Engine list + layout modelled this phase;
   the engine module loops over engines, but one-engine-out *loads* remain at
   `ONENGOUT`. Backward-compatible: legacy single-`engine` JSON still loads.
3. **Wing is the authoritative oracle.** `XLEMAC`/`MAC` (the figures the whole
   pipeline cites) are matched tightly; secondary surfaces use the same calc.

---

## Phase 1 (deferred item) — WTENV weight/CG envelope (complete)

**Objective.** Complete the mass-properties phase by porting `WTENV` — the
discretionary-loading envelope, structural CG limits and ballast — which was
re-scoped to land after `WINGGEOM` because its limit stations need the wing
`XLEMAC`/`MAC`.

**Deliverables.**
- `farloads/models.py` — `WeightEnvelopeInput` under `Project.weight.envelope`
  (gross weight, the three %-MAC CG limits, the forward-regardless reduced weight,
  and an optional XLEMAC/MAC override).
- `farloads/modules/weight_envelope.py` (`WTENV.BAS`), self-registered as
  `weight_envelope`: empty / minimum-flight / maximum loadings; structural-limit
  stations `X = XLEMAC + pct·MAC` (reading the wing geometry through WINGGEOM's
  `surface_properties`, not re-deriving it); the forward loading envelope; and the
  ballast per limit by moment balance.
- `farloads/io.py` — envelope (de)serialization on the weight slice;
  `app/pages/04_Weight_Envelope.py`; envelope inputs in the example;
  `tests/test_weight_envelope.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). Reproduces Chapter 3 p21-22:
stations 85.1 / 77.49 / 72.64, minimum flight weight 2063 @ 73.09, maximum loading
3322 @ 84.56, and ballast weights 78 / 418 / 158 lb (forward-gross/forward-
regardless ballast *stations* also match: 80.27 / 70.97).

**Key decisions.**
1. **Read geometry, don't re-derive.** WTENV obtains XLEMAC/MAC by calling
   WINGGEOM's pure `surface_properties` on the wing surface — honouring "read
   shared, write own".
2. **Ballast is the exact moment balance.** Per Decision 3 the aft-gross ballast
   station is reported as the precise balance (~108.5 in); the original manual's
   hand calc rounded the limit station to 85.0 (giving the 103.7 its own WTONECG
   data base then carried). The ballast *weights* match exactly.
3. **Documented reference-point selection.** The ballast reference loadings are
   chosen as in the worked example (full load for aft gross; the forward-boundary
   knee for forward gross; the heaviest forward point ≤ reduced weight for forward
   regardless), reproducing all three manual ballast weights.

---

## Phase 2 — Structural design speeds: STRSPEED (complete)

**Objective.** Port the design-airspeed and limit-maneuver-load-factor module
(`STRSPEED`), which seeds the flight-envelope and control-surface load modules
(FLTLOADS, AILERON, FLAPLOAD) and shares its standard-atmosphere/Mach machinery
with `MACHLIM`.

**Deliverables.**
- `farloads/models.py` — `StructuralSpeedsInput` and the `Project.speeds` slice
  (category, design weight, stall speeds, VH, shoulder altitude, chosen speeds and
  load factors).
- `farloads/modules/structural_speeds.py` (`STRSPEED.BAS`), self-registered as
  `structural_speeds`: FAR 23.337 maneuver load factors, FAR 23.335 design speeds
  (VA/VC/VD/VF) with their minimums, and cruise/dive Mach at the shoulder altitude.
- `farloads/constants.py` — shared `standard_atmosphere(altitude)` (a, sigma, with
  the tropopause branch) plus `cruise_speed_coefficient`/`dive_ratio_coefficient`,
  reused by MACHLIM next.
- `farloads/io.py` — speeds (de)serialization; `app/pages/05_Structural_Speeds.py`;
  speeds slice in the example; `tests/test_structural_speeds.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). Reproduces the Appendix A V-n
table within ±0.1%: VA 121.3, VC 170, VD 212.5, VF 105.5 kt (EAS); n = +3.8 /
−1.52; MC 0.323 / MD 0.403 at the 12000 ft shoulder altitude; VC(min) 141.8 kt;
wing area 184.1 ft².

**Key decisions.**
1. **Wing area from geometry.** S is read from the WINGGEOM wing surface
   (total area in² → ft²), not re-entered — "read shared, write own".
2. **VD floor is 1.25·VC.** The worked example's governing dive-speed bound is the
   absolute FAR 23.335(b) floor 1.25·VC (212.5 kt); the gust-based K_d·VC (238 kt)
   is reported as the recommended value but not enforced, matching the manual.
3. **Shared atmosphere helper.** `standard_atmosphere` lives once in
   `constants.py` so STRSPEED and MACHLIM cannot drift; the shoulder altitude
   (12000 ft for the example) is an input.

---

## Phase 2 — Mach-limit lines: MACHLIM (complete)

**Objective.** Port the Mach-limit-line module (`MACHLIM`) — the V-vs-altitude
limit lines for the flight-limits diagram — completing Phase 2.

**Deliverables.**
- `farloads/models.py` — `MachLimitInput` on `Project.speeds.mach_limit` (MC, MD,
  shoulder/max altitudes, increment).
- `farloads/modules/mach_limit.py` (`MACHLIM.BAS`), self-registered as
  `mach_limit`: `MNE = 0.9·MD`, `MFC = 1.2·MD`, and the per-altitude
  Mach-limited equivalent airspeeds `V(M) = M·a·√σ` (reusing
  `constants.standard_atmosphere`, including its tropopause branch).
- `farloads/io.py` — nested `mach_limit` (de)serialization on the speeds slice;
  `app/pages/06_Mach_Limit.py` (with a V-vs-altitude line chart);
  mach_limit inputs in the example; `tests/test_mach_limit.py`.

**Test / Acceptance.** Green build — `ruff check farloads/ cli.py` clean, full
`pytest` suite passing, coverage floor held (≥80%). Reproduces Appendix A p160
within ±0.1%: MNE 0.3627, MFC 0.4836, and the EAS table from V(MC) 170.16 /
V(MD) 212.31 at 12000 ft down to V(MC) 150.77 / V(MD) 188.11 at 18000 ft.

**Key decisions.**
1. **Reuses the shared atmosphere.** No second copy of the atmosphere law; the
   program's `a = 29.02` vs the helper's `29.02436` is a ~0.01% difference
   absorbed by the ±0.1% tolerance (Decision 3).
2. **Per-altitude condition rows.** Each altitude is its own `ConditionResult`, so
   the CSV/text/GUI render the limit-line table directly and the GUI can chart it.

---

## Phase C — Step C0: concept-mode foundation & mission reframe (complete)

**Objective.** Remove the two GA-only assumptions that block >12,500 lb /
greater-than-GA-seat configurations — the FAR 23.337 maneuver-load-factor
formula/cap and WTESTIMA's statistical estimate — without disturbing the
oracle-locked FAR23 path. (Prerequisite for the Phase-C concept loads tool;
narrative in [`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md).)

**Deliverables.**
- `models.py` — `StructuralSpeedsInput.category` gains `"C"` (concept), documented
  as requiring explicit `chosen_n`/`chosen_nneg`; `WeightInput.direct_totals()`
  (the direct-weight path: MTOW/OEW/useful summed from the itemized `items` by
  `MassItemKind`); `Project.is_concept` (single concept read-point); `SCHEMA_VERSION`
  bumped 1 → 2 (additive — v1 files load unchanged via the `from_dict` defaults).
- `modules/structural_speeds.py` — `_maneuver_load_factors` branches on concept,
  using the user's load factors verbatim with no FAR floor/cap; the load-factor
  result note flags the unverified extrapolation. The GA-calibrated VC(min)/VD(min)
  coefficients remain as out-of-band advisories (concept supplies chosen speeds).
- `modules/weight_estimate.py` — `run()` flags the WTESTIMA summary as a GA
  sanity estimate in concept mode; `estimate()` is unchanged so the Appendix-A
  oracle still holds.
- UI — Structural Speeds page adds the Concept (C) category with `n`/`n_neg`
  inputs and an unverified-extrapolation warning; the Weight Estimate page shows a
  concept sanity banner.
- `examples/concept_heavy.project.json` — an 18,000 lb concept commuter twin.

**Test / Acceptance.** All pre-existing tests pass unchanged (FAR23 identity
invariant). New `tests/test_concept.py` (`direct_totals` by kind; end-to-end
fixture run; IO round-trip) and concept cases in `tests/test_structural_speeds.py`
(cap bypassed; missing load factors raise). The fixture (MTOW > 12,500, user n)
runs STRSPEED and WTESTIMA end-to-end with the chosen factors (4.0 / -2.0) honoured
verbatim. **Confirmed** no hard ≤12,500 lb / seat-count assertion was load-bearing
(STRSPEED only checks `w > 0`; WTESTIMA only `engines >= 1` / `seats >= 1`; WTENV
none).

**Key decisions.**
1. **Concept is a strict superset** — `category == "C"` switches off the GA caps;
   the physics is unchanged and reduces exactly to FAR23 on GA inputs.
2. **Direct-weight = sum the itemized data base by kind** — one source of truth (no
   parallel direct-MTOW field that could disagree with the items list).
3. **Docs scope reframe landed with the plan** — CLAUDE.md / README.md /
   PROJECT_GUIDE.md were reframed when the Phase-C plan was adopted; C0 is the code.

---

## Phase C — Step C1: AIRLOADS (Schrenk spanwise lift) + TAU (complete)

**Objective.** Compute the wing spanwise lift distribution (`c·cl` span load) —
the first real distributed-load deliverable and the input every downstream
wing-load module (FLTLOADS balancing, WINGINER, NETLOADS, the sbeam export)
consumes. Method: **Schrenk's** (Reference 1 Ch 7, p46-47; CAA-accepted per CAM 04
App V) — average the planform-chord and elliptic lift distributions. (Narrative in
[`../30_future/01_concept_loads_plan.md`](../30_future/01_concept_loads_plan.md) §C1.)

**Equations (Ref 1 Ch 7).** Per strip (mid-station `ye`, chord `c`, width `dy`),
reusing the WINGGEOM strip integrator so stations align with the geometry table:
- additive (CL=1): `c·cl = 0.5·( mo·c/Mo + 4S/(π·B)·√(1−(2ye/B)²) )`, with
  `Mo = Σ(mo·c·dy)/(S/2)`, `S = 2·Σ(c·dy)`, `B = 2·ytip`;
- basic (twist): `Awo = Σ(mo·c·ac·dy)/Σ(mo·c·dy)`, `aa = ac − Awo`,
  `c·cl_basic = (mo/2)·aa·c`;
- combine at target CL: `c·cl = c·cl_additive·CL + c·cl_basic` (basic integrates to
  zero net wing lift);
- TAU planform correction from the `TAU.BAS` quartic curve-fit in taper ratio,
  interpolated by tip ratio (p407); wing slope `M = mo_rad/(1 + mo_rad/(π·AR)·(1+τ))`.

**Deliverables.**
- `models.py` — `AeroSurfaceInput` (section slope `mo`, taper/tip ratio, optional
  `tau` override, spanwise `twist` table, `target_cl`) + `AeroInput`; `Project.aero`;
  `SCHEMA_VERSION` 2 → 3 (additive — older files load unchanged).
- `modules/airloads.py` — registers `"airloads"`; `_tau` curve-fit helper;
  `schrenk_distribution()` returns the per-strip `SpanwiseTable` (additive/basic/
  total `c·cl` and `cl`, plus `Mo`/`M`/`τ`/`Awo`/area/span and the integrated-CL
  closure); `spanwise_distribution()` wraps it as a reportable `ConditionResult`;
  `run(project)` flags concept mode as an unverified extrapolation. Reuses
  `wing_geometry._interp_x` for chord and twist interpolation.
- `io.py` — `aero_from_dict`/`aero_to_dict` round-trip; wired into the project
  load/save. `modules/__init__.py` imports `airloads` for self-registration.
- UI — `app/pages/06_Airloads.py`: aero inputs + editable twist table, a span-load
  plot (additive / basic / total), and the recovered-CL closure metric.
- Fixtures — the GA (`ga6_normal`) and concept (`concept_heavy`) projects gain an
  `aero` wing slice (concept also gains a wing planform).

**Test / Acceptance.** New `tests/test_airloads.py` (10 tests). FAR23 oracle
(±0.1%, `math.isclose(rel_tol=1e-3)`) vs Appendix A p161-162: additive `CC(LA1)`
elem 1/10/20 = 91.05576 / 69.44847 / 31.82978, `C(LA1)` elem 1 = 0.9275981, additive
integral CL = 1.00061; basic `Awo` = 3.988146, `CC(lb)` elem 1 = +5.09762, `Clb`
elem 1 = 0.05193; area/span/AR match WINGGEOM (26513.4 / 402 / 6.095). TAU curve-fit
(square-tip `τ(λ=0)` = 0.206209; `τ = 0` at tip ratio 1). Concept closure: the
`concept_heavy` integral recovers `target_cl` and the basic distribution carries
zero net lift. IO round-trip + missing-slice `ValueError`. All pre-existing tests
pass unchanged (FAR23 identity) — 93 passing.

**Key decisions.**
1. **Full Schrenk (additive + basic + combine)** — needed to reproduce the Appendix A
   wing, which has washout (root 5° → tip 1.9°).
2. **Aero slice carries inputs; the distribution flows out as a `ModuleResult`** —
   no persisted result-in-project field until a consumer (C2) needs one (avoids
   speculative state); matches the existing module pattern.
3. **Basic-distribution fairing deferred** — the cosine fairing across a flap/aileron
   lift discontinuity (Ref 1 p47) only arises with deflected flaps and is absent from
   the Appendix A wing; left as a documented limitation for a later step.

---

## Phase C — Step C2: FLTLOADS (V-n envelope + balancing tail loads) (complete)

**Objective.** Port the FAR 23.333 maneuver + gust flight envelope and the
balancing horizontal-tail load at every corner — the candidate-condition matrix
SELECT later prunes and WINGINER/NETLOADS consume.

**Deliverables.**
- `farloads/models.py` — new **`Project.flight_loads`** input slice
  (`FlightLoadsInput`: `mac`/`wing_area_sqft`/`xw`/`zw`/`xtc`/`xtf`, reference Mach
  `mn`, altitude list, per-configuration `AeroCoeffSet` aero-coefficient polynomials
  CL(α)/CD(CL)/CM(α) + stall CLs, weight-CG `CgCase` list) and the new
  **`Project.envelope`** result slice (`EnvelopeResult.vn` / `.tail_balance`:
  `VnPoint` + `TailBalanceLoad`). `SCHEMA_VERSION` bumped to **4** (additive — older
  files load unchanged); `io.py` round-trip extended for both slices.
- `farloads/modules/flight_envelope.py` — faithful port of FLTLOADS.BAS subroutine
  **3900** (iterate AoA to the required load factor, then dynamic pressure to the
  Mach-adjusted stall line; Glauert `G/Gmn`; CLmax-vs-Mach 5th-order fit) and **4864**
  (gust load factor, FAR 23.341). Balancing
  `LT = [M(W+F) + LZ·(Xcg−Xw) − DX·(Zcg−Zw)]/(XT−Xcg)` with approximate tail CP
  (XTC≈5% / XTF≈25% tail MAC). Reads VA/VC/VD/VF, MC/MD and the limit load factors
  from STRSPEED (`design_speeds` + `_maneuver_load_factors`, the single owner).
  Registered `"flight_envelope"`; pure entry `build_envelope(project) → EnvelopeResult`.
- New Streamlit page `app/pages/07_Flight_Envelope.py` (V-n diagram + balanced-
  condition table + editable aero coeffs / CG cases). Example fixtures gain a
  `flight_loads` slice.

**Test / Acceptance.** `tests/test_flight_envelope.py` oracle-locks the Appendix A
"V-n Data" cruise matrix (p179-180) for CG1/CG2: corner speeds, load factors, α, G,
and the balancing tail load LT (e.g. STALL 1G LT 132, MAN A LT 493 / LZW 12419,
GUST +C NZ +3.96, AC ROLL LT 412, CG2 MAN A LZW 12970 / LT −59). The AoA balance
converges NZ to ±0.005 (FLTLOADS.BAS line 4130), so LT and corner speeds/factors
use tight tolerances while low-load-factor quantities use the ~0.5% convergence
floor. Concept mode checked by physics closure (the balance attains the user load
factor with no GA cap; LZ+LT = NZ·W). Full suite green (106 tests), ruff clean.

**Key decisions.**
1. **Aero coefficients are inputs** — the airplane-less-tail CL/CD/CM polynomials
   come from the Ch 7 aero-coefficients program and are entered via `AeroCoeffSet`
   (AIRLOADS/C1 does not yet emit them), faithful to the BAS prompts.
2. **Explicit CG cases, no `Project.mass`** — the balance uses the four weight-CG
   envelope cases entered directly (matching the BAS), so the original data-flow's
   `Project.mass`/WTONECG read is unnecessary for C2; seeding the CG cases from
   WTENV is a later refinement. The planned WTONECG `MassProperties` refactor was
   dropped from C2 as unneeded.
3. **Cruise scope** — the cruise maneuver+gust corner set (20 conditions); the
   flapped LANDING/ENROUTE envelopes share the balance engine and drop in later.
4. **Local atmosphere constant** — FLTLOADS' own speed-of-sound constant (518.688
   vs the shared `standard_atmosphere`'s 518.4) is replicated locally for oracle
   fidelity near the Mach cap; documented in the module.

---

## Phase C — Step C3: WINGINER + NETLOADS (wing net span loads) (complete)

**Objective.** The headline structural deliverable: net spanwise wing **shear,
bending moment and torsion** (air load + inertia) along the 25% chord at the
critical conditions.

**Deliverables.**
- `farloads/models.py` — new **`Project.wing_mass`** input slice (`WingMassInput`:
  panel weight, tip/root area-density ratio, inboard rib, wing-reference-plane
  waterline + dihedral, `ConcentratedWeight` list, `WingLoadCase` list) and the
  **`Project.loads`** result slice (`LoadsResult` = `wing_air`/`wing_inertia`/
  `wing_net`, each `WingLoadResult` of `WingStationLoad`). `AeroSurfaceInput`
  gains the section `profile_drag` (CDO) and `section_cm` (CM) tables.
  `SCHEMA_VERSION` 4→5 (additive); `io.py` round-trip extended.
- `farloads/modules/airloads.py` — `air_load_distribution()` (AIRLOADS load option,
  subr 4500/4600-5060): scales the C1 Schrenk section lift to the operating CL,
  builds per-strip lift/drag/moment at `Q=V²/295`, rotates by `α=CL/M−Awo`, and
  integrates tip→root to Sz/Mxx/Myy and Sx/Mzz; drag = induced `cl·ai/57.3` +
  profile CDO.
- `farloads/modules/wing_inertia.py` (`register("wing_inertia")`) — tapered
  panel-mass distribution (root density iterated to panel weight), 1g-vertical /
  1g-drag / unit-roll unit cases combined per `(Nz, Nx, UNB)`; concentrated
  weights as spanwise steps.
- `farloads/modules/net_loads.py` (`register("net_loads")`) — net = air + inertia
  per station; per-station CSV (`wing_load_rows`). The C3-before-SELECT bridge:
  `Nz=−NZ`, `Nx=−DX/W`, CL/V read from the FLTLOADS `envelope.vn` point.
- New Streamlit page `app/pages/08_Net_Wing_Loads.py` (air/inertia/net shear, BM,
  torsion plots + station table + CSV). Example fixtures gain a `wing_mass` slice
  (and the GA wing aero gains `tau=0.05`, profile drag and section CM).

**Test / Acceptance.** `tests/test_wing_inertia.py` + `tests/test_net_loads.py`
oracle-lock the Appendix A worked example to ±0.1%: the air-load Case 22 PHAA
table (p206 — root Sz +6470, Mxx +516955, Myy −79003, Mzz −91283), the WINGINER
density (2.213/2.102 lb/ft²) and unit/combined inertia tables (p217-221), and the
Net Loads Case 22 table (p222 — root Sz +5837, Mxx +455555, Myy −60940). Concept
mode checked by the net = air + inertia identity and a trapezoidal-Schrenk root-BM
closure. Full suite green (123 tests), ruff clean.

**Key decisions.**
1. **Air-load shear/BM/torsion lives in AIRLOADS** (its "load distribution" option),
   not NETLOADS — faithful to the original; NETLOADS is the algebraic sum.
2. **TAU = 0.05 override** on the GA wing aero reproduces the manual's printed wing
   lift-curve slope exactly (C1's computed 0.0397 differs), making the full
   distribution oracle-exact; C1's oracle is independent of TAU.
3. **Full fidelity** — all of Fx/Fz/Sx/Sz/Mxx/Myy/Mzz (added the section profile-drag
   and pitching-moment inputs the drag/torsion components need), per the locked C3
   scope decision.
4. **Explicit load cases / no `Project.mass`** — the critical conditions come from
   the V-n matrix (C2) as `WingLoadCase`s (SELECT, C6, will pick them automatically);
   `Nz`/`Nx` default from the V-n point. Concentrated wing masses are supported.

---

## Phase C — Step C4: sbeam export bridge (complete)

**Objective.** Turn the NETLOADS net wing load into an sbeam-consumable
structural load set, proving the sbeam integration on the wing vertical slice.

**Deliverables.**
- `farloads/export/` — new output-renderer subpackage (pure strings + thin
  `write_*` wrappers; **not** a registered calc module).
  - `coordinates.py` — FAR23LOADS station-X / butt-Y / waterline-Z inches → sbeam
    global CID 0, identity map (single edit-point for any future sign/axis/unit
    change).
  - `sbeam_bridge.py` — consumes `Project.loads.wing_net` (accepts a `Project`, a
    list of `WingLoadResult`, or one result) and emits: (1) `span_load_csv` (one
    row per station per case: applied nodal `Fx/Fz/My` + cumulative
    `Sx/Sz/Mxx/Myy/Mzz`); (2) `force_moment_cards` — comma free-field unit-scale
    `FORCE, SID, GID, 0, 1.0, Fx, Fy, Fz` / `MOMENT …` (`%.6E`, ~zero components
    skipped), one SID per case, mirroring `sbeam/results/load_export.py`; (3)
    `stick_model_bdf` — a minimal SOL 101 CBAR cantilever (root clamp node + GRID
    per station + CBAR chain + PBAR/MAT1 placeholder + SPC1 + one subcase/load set
    per case).
- The applied nodal load at each station is the **increment of the cumulative**
  NETLOADS column (`dFz[i]=sz[i]−sz[i+1]`), so the FORCE set sums to the root
  shear and the MOMENT(My) set to the root torsion exactly, and (under the
  WINGINER quadrature `y[i]−y[0]=i·dy`) the FORCE moments reproduce the root
  bending exactly.
- `cli.py` — `--export-sbeam <prefix> <project.json> [--stick-model]` writes
  `<prefix>.span_loads.csv`, `<prefix>.loads.bdf` (and `<prefix>.stick.bdf`).

**Test / Acceptance.** `tests/test_sbeam_bridge.py` (10 tests) validates by
closure (no printed oracle in concept mode): re-summed FORCE/MOMENT = NETLOADS
root totals (exact); a **self-contained** free-field reader (no sbeam import)
round-trips the cards; stick-deck structure (one root clamp, connected CBAR
chain, one load set per case) and station-grid geometry checked; runs on both the
GA and concept examples. Manually verified that the real sbeam
(`/Users/seanomeara/Documents/99-Tests/sbeam`) parses the deck and **solves all
SOL 101 subcases** (`run_sol101`) with the load sets summing to the NETLOADS root
shear. Full suite green (133 tests), ruff clean.

**Key decisions.**
1. **Export bridge, not a calc module** — `farloads/export/` is a renderer
   alongside `io.py`; physics stays in `modules/net_loads.py`.
2. **Increment-of-cumulative nodal loads** — gives exact force/torsion/bending
   closure even with concentrated wing masses, since the cumulative columns
   telescope.
3. **Card style copied from sbeam** — comma free-field, unit scale + `%.6E`
   components, one SID per case, matching `sbeam/results/load_export.py`.
4. **Self-contained test parser** (no sbeam dependency in CI); the
   parses-and-solves-in-sbeam check is a documented manual step.
5. **Stick model behind a flag** — both deliverables (load-cards-only for splicing
   into a user's model, and the auto stick model) per the C4 working assumption;
   nominal placeholder PBAR/MAT1 (reactions are stiffness-independent for the
   determinate cantilever).

---

## Phase C — Step C5: Configuration & Layout page + fleet assessment (complete)

**Objective.** Satisfy "assess the configuration against similar airplanes": a
modern Configuration & Layout page that owns the high-level parametric geometry,
derives the wing/stability/gear assessment, seeds the geometry downstream, and
places the design against an extended reference fleet. No original `.BAS`; **no
manual regression oracle** (Appendix A/B geometry used only as a sanity fixture).

**Deliverables.**
- `models.py` — new `Project.configuration` slice (`LayoutInput`: fuselage L/W/H +
  datum; parametric wing area/AR/taper/dihedral/LE-sweep/LE-root/root-waterline;
  H/V tail areas + arms; gear nose/main stations, track, height). `SCHEMA_VERSION`
  bumped 5 → 6 (additive); `io.py` round-trip extended (`configuration_*_dict`).
- `modules/configuration.py` (pure, registered `"configuration"`) — trapezoidal
  wing planform → WINGGEOM LE/TE polylines; MAC/XLEMAC/Y_MAC/AR/span obtained by
  running the generated polylines through the WINGGEOM strip integrator (WINGGEOM
  stays the owner); tail-volume neutral point + static margin; tip-back / overturn
  angles; prop ground clearance.
- `app/pages/00_Configuration_Layout.py` — fuselage/wing/tail/gear input groups,
  Plotly three-view (top/side/front) with CG (25% MAC) and neutral-point markers,
  assessment panel, a "Seed wing geometry (WINGGEOM)" button, and a fleet
  comparison (W/S-vs-W/P and MTOW-vs-OEW).
- `app/data/reference_aircraft.csv` — extended with a heavier/concept tier (twin
  pistons, commuters, a bizjet, light transports); jets carry `max_hp = 0` and are
  excluded from the W/P plot.

**Test / Acceptance.** `tests/test_configuration.py` — analytic-vs-WINGGEOM-strip
MAC/Y_MAC/XLEMAC consistency ±0.1%; area/AR round-trip; Appendix A trapezoid
plausibility (MAC 69.246 / MAC butt line 87.854 within ±10%, the real wing having
an inboard strake); stability + gear quantities present when data given.
`tests/test_io.py` configuration round-trip; `tests/test_reference_aircraft.py`
extended for the new tier. Full suite green; `ruff` clean.

**Key decisions.**
1. **WINGGEOM stays the MAC owner** — configuration generates polylines and reads
   MAC/XLEMAC back from `wing_geometry.surface_properties` rather than integrating
   independently (per the "don't recompute another module's quantity" rule).
2. **First-order estimates, flagged** — tail-volume NP (`h_acw=0.25`, `a_t/a_w=1`,
   `1−dε/dα=0.6`), CG at 25% MAC when no mass slice is present; concept-mode results
   labelled unverified extrapolation. No oracle (documented).
3. **Seeding scoped to WINGGEOM** — the wing surface seed is enough for WTENV /
   STRSPEED (they read `XLEMAC`/`MAC`/area from `Project.geometry`); WTONECG station
   seeding and engine write-back deferred (recorded in the backlog).

---

## Phase C — Step C7: TAILDIST + AIRLOAD4 (complete)

**Objective.** The chordwise horizontal/vertical-tail load distribution for
SELECT's critical tail conditions (TAILDIST, Reference 1 Ch 10), and the
sweepback / high-Mach spanwise-airload branch for concept jets (AIRLOAD4,
Ch 12). The FAR23 path is oracle-locked against the Appendix A chordwise tables;
concept mode reduces to it on GA inputs.

**Deliverables.**
- `modules/taildist.py` (registers `"taildist"`) — `chordwise_pressures()` builds
  the five-station net pressure profile (additive angle-of-attack distribution at
  25% chord + camber distribution at 50% chord, TAILDIST.BAS subroutine 3000) for
  each critical h-tail / v-tail condition; `build_tail_chordwise()` reads
  `Project.envelope.critical` (SELECT) + the chordwise geometry and persists
  `Project.loads.tail_chordwise`.
- `modules/select.py` — every h-tail / v-tail `CriticalCondition` now carries the
  rational `lt25`/`lt50` split (balancing / unchecked / checked / gust /
  unsymmetrical / rudder / yaw / side-gust), the uniform TAILDIST input.
- `modules/airloads.py` — the AIRLOAD4 swept branch (`_apply_sweep`,
  `use_airload4`): the Pope & Haney sweep redistribution of the additive Schrenk
  span load, auto-selected when 25%-chord sweep > 15° or design Mach > 0.4, exactly
  identity at zero sweep / low Mach.
- `models.py` — `TailLoadsInput.htail_semispan_in`, `VTailLoadsInput.vtail_span_in`,
  `AeroSurfaceInput.sweep_deg`/`design_mach`, the `TailChordResult`/`TailChordStation`
  result types on `LoadsResult.tail_chordwise`, `CriticalCondition.lt25`/`lt50`;
  `SCHEMA_VERSION` 11 → 12 (additive, older files load unchanged).
- `io.py` — `tail_chordwise` + `CriticalCondition.lt25`/`lt50` round-trip;
  `export/sbeam_bridge.py` — `tail_chordwise_csv` / `tail_force_moment_cards`
  (FORCE set scaled to the total tail load); `cli.py` — `--export-target tail`.
- `app/pages/11_Tail_Distribution.py` — the chordwise tail-distribution page.
- `examples/ga6_normal.project.json` — the Appendix A tail slices + chordwise spans.

**Test / Acceptance.** `tests/test_taildist.py`: the Appendix A "Chordwise
Distribution of Tail Loads" oracle — all **13 horizontal** (p237) + **4 vertical**
(p245) conditions' `PSI(X1..X5)` within ±0.1%; the SELECT→TAILDIST pipeline (9
flaps-retracted h-tail + 4 v-tail); the AIRLOAD4 reduction invariant + swept
closure; the schema-12 round-trip (older files still load). 174 tests pass.

**Key decisions.**
- **Full-area unified form.** TAILDIST.BAS halves the both-sides `LT25/LT50` over
  the half (LH) tail area; the suite stores full both-sides areas, so the two
  factors of two fold into the unified `WATT=LT25/S`, `WCAM=LT50/(S−Saft)` —
  verified to reproduce the oracle exactly (PSI(X1)=4·907.62/5320=0.682).
- **Deferred (recorded in the backlog):** the *printed* Appendix B swept spanwise
  oracle (needs a legible swept fixture; the reduction invariant + closure stand
  in), and the 4 flaps-extended chordwise rows (need the C6-deferred flapped V-n
  landing aero; `chordwise_pressures` covers all 13 rows directly).

## Phase C — Step C8: control-surface simplified distributions (AILERON / FLAPLOAD / TABLOADS) (complete)

**Objective.** The explicit concept-tool requirement that control surfaces use
**standard simplified distributions** — port AILERON (Ch 16), FLAPLOAD (Ch 17) and
TABLOADS (Ch 18) as FAR-style simplified pressure distributions with hinge
loads + distributed loads + CSV + sbeam bridge. The FAR23 path is oracle-locked
against the Appendix A control-surface tables; concept mode reduces to it on GA
inputs.

**Deliverables.**
- `modules/aileron.py` (registers `"aileron"`) — `aileron_loads()` computes the
  deflected up/down rolling loads (`LAIL=0.04·DEFL·SA·V²/295`, the VA/VC/VD
  deflection schedule, FAR 23.455 / CAM 3.222) and the constant-LE→taper-to-TE
  pressure; `build_aileron()` returns the two `ControlSurfaceLoadResult`s.
- `modules/flap.py` (registers `"flap"`) — `flap_loads()` over the four-condition
  flaps-extended envelope (Abbott & von Doenhoff Fig 98), the momentum-theory
  slipstream (FAR 23.457(b), sub 500) and the head-on 25 fps gust (FAR
  23.345(c)(1)); reads stall speeds/VF/weight from STRSPEED, wing area from
  geometry and MAXHP/prop diameter from the engine.
- `modules/tab.py` (registers `"tab"`) — `tab_load()` per `TabSpec` at full
  deflection at VC (FAR 23.409 / CAM 3.224, trapezoid LE = 2× TE).
- `models.py` — `AileronLoadsInput`, `FlapLoadsInput`, `TabLoadsInput`/`TabSpec`
  input slices; `ControlSurfaceLoadResult`/`ControlSurfaceStation` on
  `LoadsResult.control_surface`; `Project.aileron_loads`/`flap_loads`/`tab_loads`;
  `SCHEMA_VERSION` 12 → 13 (additive, older files load unchanged). `constants.py` —
  `KT_TO_FPS_SUITE`, `DYNAMIC_PRESSURE_DIVISOR`.
- `modules/structural_speeds.py` — `design_speed_values()` exposes the scalar
  VA/VC/VD/VF + load factors the control-surface modules read (extracted from
  `design_speeds`).
- `io.py` — round-trip for the three new slices + `control_surface`;
  `export/sbeam_bridge.py` — `control_surface_csv` / `control_surface_force_moment_cards`
  (FORCE set scaled to the critical surface load, closure-checked).
- `app/pages/12_Aileron_Loads.py`, `13_Flap_Loads.py`, `14_Tab_Loads.py`.
- `examples/ga6_normal.project.json` — the Appendix A aileron/flap/tab slices.

**Test / Acceptance.** `tests/test_aileron.py`, `test_flap.py`, `test_tab.py` vs
the Appendix A reports (p200/p201/p202): aileron down 271.44 / up −180.96 lb,
psi +0.484 / −0.323; flap CLf 1.7046/1.7046/1.5593/1.5476, critical 629 lb, LE
0.545 psi, slipstream ×1.407 (BL 22.828…113.172), gust ×1.301, combined 819 lb;
tab E 0.17735, LTAB 84.62 lb, LE 0.4992 / TE 0.2496 — all within ±0.1%. Plus io
round-trip (older files load) and the sbeam control-surface FORCE-closure test.
187 tests pass.

**Key decisions.**
- **Separate per-surface input slices** (not folded into `Project.geometry`),
  mirroring `TailLoadsInput`/`VTailLoadsInput` — geometry has no hinge split.
- **Aileron oracle uses the manual's rounded VA=121**; the integrated pipeline's
  computed VA≈121.3 shifts the load ~0.3% (tested at 0.4%) — an artifact of the
  original separate-programs workflow, not an error.
- **Suite knots→ft/s factor** (`1.15·88/60`) kept verbatim for the FLAPLOAD
  slipstream so the BL band reproduces the oracle (22.828…113.172) exactly.
- **Full FLAPLOAD scope** — slipstream and head-on-gust amplifications implemented
  now (not deferred), matching the full Appendix A flap table.

## Phase C — Step C10: landing / ground loads (LGFACTOR + LANDLOAD) (complete)

**Objective.** The FAR Part 23 Subpart C ground-load conditions: the landing load
factor (LGFACTOR, FAR 23.473) and the tricycle-gear reaction loads for the level,
tail-down, one-wheel, braked-roll, side and supplementary-nose-wheel conditions
(LANDLOAD, FAR 23.473–23.499), Reference 1 Ch 20.

**Deliverables.**
- `modules/landing.py` (registers `"landing"`) — `landing_load_factor()` (LGFACTOR
  drop-test work-energy: descent `V = 4.4·(W/S)^0.25` clamped 7–10 fps, tyre/strut
  energy efficiencies, `N` and `NLG = N − L`); `landing_reactions()` (LANDLOAD: the
  drag factor `K`, ground angles, `BETA`, the `AP/BP/DP/CP` lever arms, then the 24
  main-wheel + 33 nose-wheel ground-line and airplane-datum reactions and the
  unbalanced PITCHP/ROLLP/YAWP moments); `build_landing()` resolves inputs (wing
  area from `geometry`, per-CG weight/CG from `mass` or `landing.cg_cases`) and
  persists `N → Project.landing.n`; `run()` emits one summary `ConditionResult` per
  FAR ground-load family (the critical wheel reaction).
- `models.py` — `LandingInput` + `LandingGearInput` (the dedicated `Project.landing`
  slice carrying the gear strut geometry, which has no home in the aerodynamic
  `Project.geometry`); `GearReactionCase` result record; `Project.landing`;
  `SCHEMA_VERSION` 14 → 15 (additive, older files load unchanged).
- `io.py` round-trip for the nested slice (gear tuples + CG cases);
  `farloads/__init__.py` exports `LandingInput`/`LandingGearInput`/`GearReactionCase`;
  `modules/__init__.py` self-registration import.
- `app/pages/15_Landing_Loads.py` — LGFACTOR inputs + sink-rate/factor metrics, the
  gear geometry editor, the full ground-line reaction table and CSV download.
- `examples/ga6_normal.project.json` — the Appendix A GA-6 landing slice (p230 gear
  geometry, p236 LGFACTOR inputs); the file stays at `schema_version 12` to keep the
  "old file loads under v15 code" regression coverage.

**Test / Acceptance.** `tests/test_landing.py` (9 tests). **LGFACTOR fully
oracle-locked** against Appendix A p236 (V 9.0048 / N 3.0951 / NLG 2.4281; N within
+0.07% — the Decision-3 `G=32.174` vs `32.2` drift) plus the velocity-clamp and
spring-vs-oleo branches. **LANDLOAD's gear-geometry intermediates oracle-locked**
against p230 (K 0.324, GAMMA 17.978, ground angles, BETA, the AP/BP/DP/CP table).
The printed wheel-load table (p231–233) is **OCR-garbled** in the bundled PDF, so
the 24-main/33-nose matrix is **formula-closure + legible-cell spot-checked** (case
1 VMP 3144 / VNP 1787 / nose resultant 1879; level case 4 VMP 4038 / RMP 4245; side
cases VMP 2261, SMP −1700/1122). 207 tests pass; coverage ~89%.

**Key decisions.**
- **Dedicated `Project.landing` slice** rather than overloading `geometry`
  (aerodynamic surfaces) or `configuration` (which lacks the three strut-deflection
  states, rolling radii and tail-down angle LANDLOAD needs).
- **Gear load factor is a rounded design input** (2.5 on p230), kept distinct from
  LGFACTOR's computed 2.428 (`gear_load_factor` override; 0 → use `N − L`) — the
  oracle's `NAP = NLG + L = 3.167` confirms 2.5, not 2.428.
- **OCR-garbled wheel-load table → closure + legible-cell validation** (the ONENGOUT
  C9 precedent), recorded as a deferred item: add the printed ±0.1% wheel-load oracle
  if a legible Appendix A/B or `LANDLOAD.OUT` surfaces. The light-landing CG weight
  (2803 lb) was back-solved from the legible side-load cell (½·1.33·W = 1864).
- **Terminal module** (no downstream consumer), so reactions render via `ModuleResult`
  + a `build_landing()` table rather than a persisted result slice, mirroring ENGLOADS.

## Phase C — Step C9: ONENGOUT (one-engine-out vertical-tail loads) (complete)

**Objective.** Asymmetric vertical-tail loads from a critical-engine failure
(FAR 23.367, Reference 1 Ch 11) — the first module to exercise the first-class
multi-engine `Project`. Unlike SELECT's static v-tail conditions, ONENGOUT is a
**time-marching yaw simulation**: the failed engine's thrust/windmill-drag asymmetry
yaws the airplane about its vertical axis (`IZZ`) until the pilot — at peak yaw rate
but ≥2 s after failure (23.367(b)) — applies full rudder and recovers; the headline
output is the maximum vertical-tail load.

**Deliverables.**
- `modules/one_engine_out.py` (registers `"one_engine_out"`) — `simulate()` Euler-marches
  the yaw transient (thrust `MAXHP·550·.85/VTFPS`, Glauert windmill drag, tail loads
  `LT25`/`LT50` at 25%/50% MAC, moment about the CG, integrate `THETA`/`THETADOT` to
  recovery); `run()` emits one `ConditionResult` per speed (VC ultimate / VD limit / VS)
  with engine thrust, windmill drag, max yaw rate, **max tail load**, 25%/50% MAC loads
  at peak and time to recovery; `time_history()` returns the full table on demand. Below
  VMC the run is bounded (60 s) and flagged non-recovered.
- `modules/_vtail.py` — shared v-tail aero helpers (`vtail_lift_slope` AVT,
  `rudder_effectiveness` EFFECTV, `large_deflection_factor` EF); `select.py`'s private
  `_avt`/`_effectv`/`_ef` refactored to delegate (pure refactor, SELECT oracle unchanged).
- `models.py` — `OneEngineOutInput` (failure-transient timing + failed-engine index);
  `VTailLoadsInput.xv50` (FS of 50% v-tail MAC); `Project.one_engine_out`;
  `SCHEMA_VERSION` 13 → 14 (additive, older files load unchanged).
- `io.py` round-trip for the new slice + `xv50`; `farloads/__init__.py` exports
  `OneEngineOutInput`; `modules/__init__.py` self-registration import.
- `app/pages/20_One_Engine_Out.py` — per-speed summary table + an on-demand time-history
  re-run (THETA/THETADOT and LT25/LT50/LT charts + CSV).

**Test / Acceptance.** The printed Appendix B (10-place twin turboprop) oracle is
**unavailable** — Appendix B is absent from the bundled `reference/FAR23Loads_Code.pdf`
(only the Appendix A GA single is present, physical pp. 128–247; Appendix C source from
248) and the FAA User's Guide Ch 22 gives partial/illegible inputs and **no output
numbers**. C9 is therefore locked at the **sub-formula level** (`tests/test_one_engine_out.py`:
engine thrust, windmill drag, AVT, EFFECTV exact to `ONENGOUT.BAS`) plus
**integration/physics closure** (recovery, yaw-rate peak, `DT`-halving convergence,
below-VMC non-recovery) and **refactor-parity** with SELECT's v-tail helpers. 11 new
tests; 198 pass; SELECT oracle unchanged.

**Key decisions.**
- **No printed oracle → closure + sub-formula validation** (user-confirmed), recorded as
  a deviation from the usual ±0.1% Appendix oracle because the reference data is missing,
  not optional. The printed twin oracle + an `examples/twin_turboprop.project.json`
  fixture (also unblocks the C7 swept oracle) are deferred items.
- **Reuse SELECT's validated EF chart** (`_vtail.large_deflection_factor`) rather than the
  garbled `ONENGOUT.BAS` subr-10000 OCR; the same Dommasch fig 12:3 fits both. Wiring this
  recovered curve into SELECT's static v-tail loads (replacing `rudder_large_deflection_factor=1.0`)
  is left as a deferred mini-step.
- **Output = per-speed summary, time history on demand** (user direction): the headline
  max tail load is the primary result; the full transient is recomputed for a chosen case
  in the UI and not persisted in the schema.
- **Below-VMC handling**: the march is time-bounded (60 s) and the case flagged
  "NOT recovered" rather than looped to a step cap, mirroring the manual's note that
  recovery performance is an aero/flight-test responsibility.

## Phase C — Step C6: SELECT + fuselage/body distributed loads (complete)

**Objective.** Compute the critical flight load on each major component (wing,
horizontal tail, vertical tail, fuselage) from the FLTLOADS V-n matrix (SELECT,
Reference 1 Ch 9), and emit the fuselage longitudinal net distribution (Ch 15) +
sbeam body export. The FAR23 path stays oracle-locked against the Appendix A loads
report; concept mode reduces to it on GA inputs.

**Deliverables (R1–R10).**
- `models.py` — new slices: persisted `Project.mass` (`MassResult`/`MassCase`),
  `Project.fuselage_mass` (`FuselageMassInput`/`FuselageStation`), SELECT
  `EnvelopeResult.critical` (`CriticalLoadSet`/`CriticalCondition`), the fuselage
  net result `LoadsResult.body_net` (`BodyLoadResult`/`BodyStationLoad`),
  `Project.select_input` (`SelectInput`: aileron/airfoil-cm + wing weight),
  `Project.tail_loads` (`TailLoadsInput`: h-tail geometry/aero + elevator/maneuver/
  gust fields) and `Project.vtail_loads` (`VTailLoadsInput`). `SCHEMA_VERSION`
  6 → 11 (all additive); `io.py` round-trip extended for every slice.
- `modules/select.py` (registered `"select"`) — **wing** (PHAA/PLAA/PMAA/NMAA,
  accelerated + steady-roll TORS); **horizontal tail** balancing (23.421),
  unchecked/checked maneuver (23.423), gust (23.425(a)(1)/(2)) and unsymmetrical
  (23.427(a)), flaps retracted and extended, with the exact SELECT.BAS subr-10000
  large-deflection chart; **vertical tail** (23.441(a)(1)/(2)/(3), 23.443(b));
  **fuselage** critical conditions (23.301/23.331).
- `modules/flight_envelope.py` — the flaps-extended (LANDING) V-n corner set at VF
  (FLTLOADS subr 3000), n-limited to 2 (FAR 23.345), sea level.
- `modules/body_loads.py` (registered `"body_loads"`) — Ch 15 fuselage net shear/
  bending per critical condition → `Project.loads.body_net` + CSV.
- `modules/weight_onecg.py` — `build_mass` emits the persisted `Project.mass`.
- `export/sbeam_bridge.py` — `body_span_load_csv` / `body_force_moment_cards`.
- `app/pages/09_Critical_Loads.py`, `app/pages/10_Fuselage_Loads.py`.

**Test / Acceptance.** Oracle-locked against Appendix A (±0.1%, plus FLTLOADS'
~0.5% V-n noise): wing PHAA STALL +N (CL +1.519/V 117.40), PLAA/PMAA/NMAA/ACRL/
TORS; h-tail balancing +519.85/−613.92 (Ch 9 case-202 hand-calc LT 519.845),
unchecked −1397.8/+1227.2, checked −671.5/+787.8, gust +908.6/−1292.8,
unsymmetrical −1111.8; v-tail rudder +591 / sideslip −92 / yaw-15 −526 / side gust
+604; fuselage 13347.6 / 12569.6 / −6390.3 / Nz 5.81. Modern/closure-validated:
the fuselage net distribution (equilibrium `ΣFz=0`, shear→0 aft) and the
flaps-extended tail loads (the flapped points achieve their target NZ; the rational
balancing tail load zeroes the flapped pitching moment). Full suite green; `ruff`
clean.

**Key decisions / known limits.**
1. **Modernized-math tolerances** — selected CL/V/LT inherit FLTLOADS' ±0.005-NZ
   convergence noise (~0.5%); the renumbered envelope assigns different integer case
   indices than the manual, so tests assert the selected *condition* + values, not
   the case number.
2. **Illegible effectiveness charts modelled exactly where possible** — the
   elevator/rudder large-deflection factor `EF(δ, Se/St)` is reconstructed from
   SELECT.BAS subr 10000; the v-tail rudder-deflection loads carry an `EFV≈1.0`
   factor (a `VTailLoadsInput` input, default 1.0) since its chart is illegible in
   the scan (the AoA/gust loads are exact).
3. **Flaps-extended oracle deferred** — the real landing-config aero polynomials
   (and CG5–7 loadings) are not in the repo fixtures, so R3/R4 are closure-validated
   rather than matched to Appendix A cases 81/106/88/108. Recorded as a follow-up.
   *(Update, M1-2: the landing polynomials — printed at Appendix A p179 — are now in
   the `flight_envelope` test fixture and the envelope `BAL 1.4VSF` point is
   oracle-matched at p181; the SELECT→TAILDIST cases 81/106/88/108 with the CG5–7
   loadings remain L-2.)*
4. **`Project.mass` persisted but not yet consumed by SELECT** — the checked-
   maneuver `Iyy` and v-tail `IZZ` use the documented Ch 9 approximations (which
   match the oracle); per-CG precise inertia from `Project.mass` is a follow-up.

---

## Tooling & documentation standard (complete)

**Objective.** Bring the project's tooling and documentation standard in line
with the sibling `sbeam` project before the module-porting work scales up.

**Deliverables.**
- `pyproject.toml` — editable install (`pip install -e '.[dev]'`), so `farloads`
  and `cli` import from any cwd; the `sys.path` shims were removed from `app/`.
  `ruff` (select `E`/`F`/`W`, ignore `E741`) and `pytest`/coverage config.
- `cspell.json` domain wordlist.
- `.github/workflows/ci.yml` — `ruff` + `pytest` on Python 3.9 / 3.11 / 3.12.
- `docs/` reorganised by type (`10_standard` / `20_theory` / `30_future` /
  `40_history`) with `docs/00_INDEX.md`.
- `docs/10_standard/CODE_REVIEW_PROCESS.md` and `RELEASE_PROCESS.md`;
  `CHANGELOG.md` (Keep a Changelog).
- `CLAUDE.md` mandate strengthened: consult `reference/`, keep `docs/` in sync,
  and the backlog→history→changelog move-on-completion rule.

**Test / Acceptance.** `ruff check farloads/ cli.py` clean; full `pytest` suite
passing after the `sys.path` shims were removed.

**Key decisions.**
- CI lints `farloads/` and `cli.py` (the pure calc + CLI). Streamlit pages in
  `app/` are not lint-gated: their long widget-label lines and the deliberate
  late `from farloads.modules import engine` import are acceptable there.
- `requires-python = ">=3.9"` to match `sbeam` (the code uses
  `from __future__ import annotations`, so 3.9 is safe).

---

## Phase C — Step C11: BALLOADS (balanced-tail-load verification utility) (complete)

**Objective.** Port the off-pipeline `BALLOADS.BAS` cross-check: recompute the
horizontal-tail balancing load **rationally** (AoA load at 25% tail MAC + camber/
elevator load at 50%) per flaps-retracted V-n condition and verify FLTLOADS'
*approximate* tail centre of pressure (`XTC`~5% MAC flaps-up / `XTF`~25% flaps-down,
Ch 8). This closes the **last** of Reference 1's 22 Appendix-C programs.

**Deliverables.**
- `modules/balloads.py` (registered `"balloads"`) — `verify_balancing(project)`
  iterates every flaps-retracted V-n point (the search set of SELECT's
  `select_htail_balancing`), **reuses** `select.htail_balance` for the rational
  `LT25`/`LT50`/`DELTA`/`LT`/`CP` split and `select._elevator_load` for the elevator
  load, converts the rational CP (% tail MAC) to a fuselage station `XT` and reports
  it against FLTLOADS' assumed `XTC` (`DXT = XT − XTC`). `run(project)` emits a
  `ConditionResult` per point (FAR 23.421); raises `ValueError` (skipped by
  `run_all_modules`) when `tail_loads`/`flight_loads` are absent.
- `farloads/modules/__init__.py` — `balloads` self-registration import.
- `app/pages/16_Balanced_Tail_Verification.py` — read-only report: up/down headline
  metrics + the per-condition rational-vs-approximate CP table.
- `tests/test_balloads.py` — the Ch 9 case-202 oracle and SELECT-consistency check.
- **No schema change, no new pipeline output** (a verification report only).

**Test / Acceptance.** Oracle-locked against the Ch 9 case-202 hand-calc: the
largest up balancing load is `LT = 519.845 lb` (LT25 +907.62, LT50 −387.78, δ
−5.39°, CP 6.35% tail MAC), within the FLTLOADS ±0.5% V-n noise. The rational
up/down loads equal SELECT's `BAL UP/DN RETRACTED` conditions exactly (same
routine), and the rational CP station tracks FLTLOADS' assumed `XTC`. Full suite
green (211 tests); `ruff` clean.

**Key decisions.**
1. **Reuse over re-derivation.** Per the project convention ("must not recompute a
   quantity another module owns"), BALLOADS calls SELECT's oracle-locked
   `htail_balance`/`_elevator_load` rather than transcribing `BALLOADS.BAS`'s own
   balance equations — the verification can never silently drift from production.
   The cross-check value is preserved by comparing the rational CP station to
   FLTLOADS' *approximate* `XTC`/`XTF`.
2. **Search set = all flaps-retracted points**, not only the trimmed `BAL`
   conditions: the governing case-202 up load falls on `STALL +N` (CG1, 18000 ft),
   mirroring `select_htail_balancing`.
3. **Off-pipeline.** Runs under `run_all_modules` when its slices exist but writes
   nothing to the `Project` schema — a teaching/verification report only,
   demonstrating the elevator load is not always opposite the stabilizer load.

---

## Phase D — Step D0: flight-envelope destructive slice overwrite fix (complete, 2026-07-08)

**Objective.** Close the data-loss defect found in the 2026-07-08 GUI review
before cutting release `0.2.0` (release step **R1**; §3.2 of the release process
requires no open critical findings). `app/views/flight_envelope.py` rebuilt
`FlightLoadsInput` wholesale (`configurations=[cruise]`,
`altitudes_ft=[altitude]`) on every rerun, so merely opening the page deleted
any flaps-down configuration or extra altitudes a loaded project carried.

**Deliverables.**
- `farloads/models.py` — `FlightLoadsInput.merged(...)`: a pure method that
  merges one page-edit into the existing slice. The edited altitude replaces
  `altitudes_ft[0]` (the entry a single-altitude widget displays); the edited
  configuration replaces the first entry with the same `flaps_down` state
  (appended if there is none); every other altitude/configuration is carried
  over unchanged. Returns a new instance; no I/O, no schema change.
- `app/views/flight_envelope.py` — persists via `fl.merged(...)` instead of the
  wholesale `FlightLoadsInput(...)` rebuild. Write-on-rerun behavior otherwise
  unchanged (the `st.form` + Apply conversion is Step D6 scope).
- `tests/test_flight_envelope.py` — two regression tests: a slice with a
  flaps-down configuration and two altitudes survives the persist path (edits
  land, unedited content preserved, original slice untouched); an empty slice
  simply gains the edited configuration.
- `CHANGELOG.md` `[Unreleased]` `Fixed` entry.

**Test / Acceptance.** Full suite green (257 tests, was 255); `ruff` clean;
Appendix A/B oracles unmodified (no calc-math change).

**Key decisions** (user-approved 2026-07-08).
1. **Merge helper lives on the model** (`FlightLoadsInput.merged`) — pure
   dataclass logic, directly unit-testable, and the reusable seed of the
   Phase-D "Apply merges into the project slice" page convention
   (`30_future/02_gui_workflow_plan.md §5.2`) that Step D6 applies suite-wide.
2. **Altitude merge = replace first, keep rest** — the widget displays
   `altitudes_ft[0]`, so an edit updates entry 0 and preserves the tail; the
   real multi-altitude UI arrives in Step D5.
3. **Merge-write only** — minimal defect fix appropriate for a pre-release
   patch; the form+Apply rework stays in Step D6.

---

## Phase D — GUI: session-wide Imperial/SI toggle + Project JSON Editor (complete, 2026-07-14)

**Objective.** The Imperial/SI display toggle existed on only 5 of 24 GUI
pages, each with its own independent, uncoordinated `st.radio` (no shared
session state), and 4 of those 5 converted output only (inputs stayed
Imperial regardless). The remaining 19 pages had no SI display at all. No page
let a user review/hand-edit the project file itself in their preferred units.

**Deliverables.**
- `app/Home.py` — a single sidebar "Units" control
  (`st.session_state["unit_system"]`), read by every view; the 5 pages with a
  local radio now read this shared value instead.
- `farloads/units.py` — `to_si_scalar`/`si_scalar_label`, scalar display
  converters for per-station/per-case dataclasses (wing/fuselage/tail/
  landing-gear results) that are not `ConditionResult`/`LoadValue`-based, so
  `convert_results` doesn't reach them.
- All 19 previously Imperial-only view files wired to the shared toggle,
  display-only: metrics/tables render in the selected system, but every
  object feeding sbeam BDF export, `Project` persistence
  (`st.session_state["project"]`) or a CSV/BDF download stays canonical
  Imperial, untouched. Airspeed (KEAS) and altitude (ft) are never converted
  (aviation-standard units in both systems, an explicit user decision).
  `structural_speeds`/`mach_limit` needed no changes — every field they show
  is speed/altitude/dimensionless, already outside the toggle's scope.
- New `app/views/project_editor.py` (Start section, new `WorkflowStep
  ("project_editor", ...)` in `farloads/workflow.py`): the whole project shown
  as hand-editable JSON in the selected units. New
  `farloads.units.project_dict_to_display`/`project_dict_to_imperial` — a
  field-name-driven whole-project converter (`_PROJECT_FIELD_KIND`, audited
  against every dimensional field in `models.py`) distinct from the two
  `_lb`-suffixed *force* fields (`load_lb`, `tail_load_lb`) that must not use
  the mass factor. Apply parses the edited JSON, converts back to Imperial,
  and rebuilds the session `Project` via the existing `io.project_from_dict`;
  the sidebar's existing Open/Save/Download widget is unchanged and still
  reads/writes one Imperial `project.json`, unmodified format, no unit tag.
- `tests/test_project_units.py` — round-trip fidelity on all 4 example
  projects, a regression test pinning the mass-vs-force `_lb` distinction to
  its correct (different) factors, and confirms airspeed/altitude/unknown
  fields pass through unconverted.
- `CHANGELOG.md` `[Unreleased]` `Added` entry;
  `docs/10_standard/PROJECT_GUIDE.md` file-tree + units-convention updates.

**Test / Acceptance.** Full suite green (297 tests, was 290); `ruff` clean; a
`streamlit.testing.v1.AppTest` sweep of every view file against 2 example
projects, in both unit systems, found zero new exceptions (one pre-existing,
unrelated `st.number_input` `max_value` issue on `weight_estimate.py`,
reproduced identically on the pre-change branch). No calc-math change, no
`SCHEMA_VERSION` change (still 19).

**Key decisions** (user-directed 2026-07-14).
1. **One session-wide toggle, not per-page.** A structural engineer needs
   consistent units across a session; per-page-independent toggles (the prior
   state) risked a wing sized in SI next to a fuselage read in Imperial.
2. **`project.json` stays Imperial-only.** Rejected tagging the file with a
   stored unit system (see the in-conversation risk review): the schema's
   field names are themselves unit-suffixed (`_lb`, `_in`, `_kt`...), so a
   file whose *content* changes meaning under a stored flag while its *field
   names* don't would silently mislead a hand-editor. The Project JSON Editor
   page solves the actual need (review/edit in preferred units) at the
   display layer instead, with no schema/migration risk.
3. **KEAS/ft stay aviation-standard in SI mode.** Airspeed and altitude are
   never converted by this toggle, in either the per-page views or the whole-
   project editor.
4. **Weight-database externalization considered and declined.** A separate
   referenced weights (and future aero) JSON file was considered for the
   project's largest section, but rejected: it would fragment the "one
   reloadable project.json" architecture (multi-file Open/Save/upload,
   drift-if-edited-independently risk) for a problem better solved by a
   readable in-app editor — exactly what this step delivers.

---

## Airplane-phase GUI usability pass: tail geometry, wing planform plot, aero-data naming (complete, 2026-07-14)

**Objective.** A GUI review requested by the user (mental model: Geometry →
Weight/CG → Three-view → Aerodynamic data) found the existing 6-step Airplane
phase already matched that order structurally, but with three real gaps: (1)
the three-view (`configuration_layout.py`) drew wing/fuselage/gear/CG/NP but
**no tail at all** — `LayoutInput` stored the tail as area+arm only, with no
type or enough geometry to sketch one; (2) `wing_geometry.py` (WINGGEOM
surface-polyline tables) had **zero visualization**; (3) aerodynamic data was
split across two schema slices in two phases (`aero_coeffs` on its own
Airplane-phase page, `aero` — per-surface spanwise Schrenk — buried inline on
the Analysis-phase Wing Loads page) with no naming/cross-link connecting them.

**Deliverables.**
- `farloads/models.py` — `TailType` enum (`CONVENTIONAL`/`T_TAIL`/`V_TAIL`/
  `CRUCIFORM`, default `CONVENTIONAL`) and four new additive `LayoutInput`
  fields (`tail_type`, `h_tail_span_ft`, `h_tail_z`, `v_tail_span_ft`, all
  zero-valued defaults). `SCHEMA_VERSION` bumped 19 → 20.
- `farloads/modules/configuration.py` — `tail_planform(layout)`, a pure
  function returning per-panel `top`/`side`/`front` outline polylines for the
  three-view, branching on `tail_type` (T-tail places the h-tail atop the fin,
  cruciform mid-fin, V-tail derives two mirrored diagonal panels from
  `v_tail_area` at a fixed 40° dihedral instead of separate h/v rectangles).
  Returns `{}` (draws nothing) when both span fields are unset, so older
  projects render identically to before this change.
- `farloads/modules/wing_geometry.py` — `surface_top_outline(le, te,
  symmetric)`, a shared presentation helper (polyline → plotly-ready top-view
  outline) used by both `configuration_layout.py` (wing outline, replacing
  duplicated inline logic) and the new `wing_geometry.py` planform plot.
- `app/views/configuration_layout.py` — tail-type selector + span/offset
  inputs in the existing form; the three-view now draws the tail panel(s) in
  Top/Side/Front alongside the existing wing/fuselage/gear/mass-item/engine
  overlays.
- `app/views/wing_geometry.py` — a lightweight top-view planform plot above
  the per-surface polyline tables, one trace per surface.
- `app/views/aero_coefficients.py` / `farloads/workflow.py` — the
  `aero_coefficients` step retitled "Aerodynamic Data" (key unchanged); a
  cross-link caption added pointing to the Wing Loads page for per-surface
  spanwise aero, with a matching caption added there pointing back.
- `tests/test_configuration.py` — 6 new tests covering each `TailType` branch
  and the empty-when-unset backward-compat case.
- Docs: `docs/10_standard/PROGRAM_SPEC.md` updated for the `configuration` and
  `WINGGEOM` module entries and the `aero_coefficients` rename; `cspell.json`
  extended.

**Test / Acceptance.** Full suite green (303 tests); `ruff check farloads/
cli.py app/` clean; `tests/test_views_smoke.py`'s headless `AppTest` sweep
passes for both changed views (this caught an initial relative-import mistake
— the shared trace helper had to live in `farloads/modules/wing_geometry.py`,
not a same-directory `app/views/_*.py` module, since Streamlit executes each
page as a standalone script, not as a package member, so `from .x import y`
fails both in `AppTest` and in the real multipage app).

**Key decisions** (user-directed, via `AskUserQuestion` during planning).
1. **Geometry editor and three-view stay one combined page**, not split into
   two — matches the existing `weight_envelope.py` precedent (edit + its own
   chart on one page) and avoids duplicating `LayoutInput` editing state
   across two `st.navigation` pages.
2. **Tail-type field and its three-view drawing built now**, not deferred —
   this was the one genuine functional gap (no tail geometry existed at all).
3. **Aero-data consolidation kept to a rename + cross-link**, not a full
   `AeroInput` migration onto the Airplane phase — moving spanwise aero input
   away from Wing Loads' immediate per-strip-distribution feedback loop was
   judged a net usability loss for a naming-only complaint.
4. **`workflow.py` step order left unchanged** — investigation found the
   existing Airplane-phase step order already matches the user's Geometry →
   Weight/CG → (three-view, combined) → Aero mental model; no reorder needed.

**Deferred (flagged as recommendations, not built this pass).** Full
`AeroInput`-onto-Airplane-phase migration if the rename+cross-link proves
insufficient; seeding `tail_type` into the example `.project.json` fixtures.

---

## Resolved defects

- **Weight Estimate page crashed opening a beyond-GA project** *(resolved
  2026-07-15)*. The Mission-inputs form hard-capped its widgets at GA-tier limits
  (`max_value = 3000 hp` / 12 seats / 6 engines / 10 hr) while seeding each widget
  from the loaded project, so a project whose stored value exceeded a cap raised
  `StreamlitValueAboveMaxError` before the page rendered (e.g.
  `examples/dhc8_dash8.project.json` at 4000 hp / 39 seats: value 2982.8 kW > max
  2237.1 kW in SI). Pre-existing (from the earlier input-units work, not Step E2,
  which only added the widget's `help=`). Fixed by removing the hard `max_value`
  caps (keeping `min_value` for physical sanity), consistent with the concept-aware
  superset that must accept airplanes beyond the GA band (`GUI_design.md §9` — warn,
  don't block; WTESTIMA's ≤12,500 lb calibration limit is surfaced as a concept-mode
  warning, not enforced on the inputs). Regression:
  `tests/test_views_smoke.py::test_weight_estimate_accepts_beyond_ga_power` loads the
  DHC-8 into the page and asserts no exception.

- **Flight Envelope page destroyed unedited `flight_loads` data** *(resolved
  2026-07-08, Phase D Step D0 / release step R1 — see above)*. Wholesale
  `FlightLoadsInput` replacement on every rerun deleted flaps-down
  configurations and extra altitudes from loaded projects. Fixed by the pure
  `FlightLoadsInput.merged()` merge-write; regression-tested in
  `tests/test_flight_envelope.py`.
